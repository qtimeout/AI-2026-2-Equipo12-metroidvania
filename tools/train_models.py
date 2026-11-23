"""Entrena KNN, árbol de decisión y MLP para imitar a A* y los exporta a JSON para el juego.

Uso (desde la raíz):
  python tools/train_models.py 1                 entrena con el nivel 1
  python tools/train_models.py 1 2               entrena con los niveles 1 y 2 juntos
  python tools/train_models.py 1 --eval 2        entrena con el 1 y mide la transferencia al nivel 2 (mapa no visto)

1. Lee data/expert_level{N}.csv (tools/make_dataset.py).
2. Separa 80 % entrenamiento / 20 % prueba, estratificado por clase (semilla 2026).
3. Elige hiperparámetros con validación cruzada de 5 particiones SOLO sobre entrenamiento.
4. Reporta exactitud y F1 macro en prueba (F1 macro porque "caminar" es el 78 % de los datos:
   un modelo que siempre camina tendría 78 % de exactitud y sería inútil).
5. Exporta app/models/{knn,tree,mlp}.json y app/models/metrics.json.

Se entrena con scikit-learn; el juego solo PREDICE, en Python puro (game/ml/models.py),
porque en el navegador (pygbag) no hay scikit-learn.
"""
import argparse
import csv
import json
import os
import sys
import time

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_validate, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from game.ml.features import CLASSES, FEATURES  # noqa: E402

SEED = 2026
OUT = os.path.join(ROOT, "app", "models")

CANDIDATES = {
    "KNN": (KNeighborsClassifier(), {"n_neighbors": [1, 3, 5, 9, 15], "weights": ["uniform", "distance"]}),
    "Árbol": (DecisionTreeClassifier(random_state=SEED), {"max_depth": [4, 8, 12, 16, None],
                                                           "min_samples_leaf": [1, 3, 10]}),
    "MLP": (make_pipeline(StandardScaler(), MLPClassifier(max_iter=600, early_stopping=True, random_state=SEED)),
            {"mlpclassifier__hidden_layer_sizes": [(32,), (64, 32)], "mlpclassifier__alpha": [1e-4, 1e-3]}),
}


def load(levels):
    rows = []
    for n in levels:
        with open(os.path.join(ROOT, "data", f"expert_level{n}.csv")) as f:
            rows += list(csv.DictReader(f))
    X = np.array([[float(r[c]) for c in FEATURES] for r in rows])
    y = np.array([CLASSES.index(r["clase"]) for r in rows])
    return X, y


def r4(a):
    return np.round(np.asarray(a, dtype=float), 5).tolist()


def export_knn(model):
    k = model.n_neighbors
    return {"tipo": "knn", "k": k, "pesos": model.weights, "X": r4(model._fit_X), "y": model._y.tolist(),
            "clases": model.classes_.tolist()}


def export_tree(model):
    t = model.tree_
    probs = t.value[:, 0, :]
    probs = probs / probs.sum(axis=1, keepdims=True)
    return {"tipo": "tree", "izq": t.children_left.tolist(), "der": t.children_right.tolist(),
            "feature": t.feature.tolist(), "umbral": r4(t.threshold), "prob": r4(probs),
            "clases": model.classes_.tolist(), "profundidad": int(model.get_depth()), "hojas": int(model.get_n_leaves())}


def export_mlp(pipe):
    sc, mlp = pipe.named_steps["standardscaler"], pipe.named_steps["mlpclassifier"]
    return {"tipo": "mlp", "media": r4(sc.mean_), "escala": r4(sc.scale_), "W": [r4(w) for w in mlp.coefs_],
            "b": [r4(b) for b in mlp.intercepts_], "activacion": mlp.activation, "clases": mlp.classes_.tolist()}


EXPORT = {"KNN": ("knn.json", export_knn), "Árbol": ("tree.json", export_tree), "MLP": ("mlp.json", export_mlp)}


def main(levels=(1,), eval_levels=()):
    X, y = load(levels)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    os.makedirs(OUT, exist_ok=True)
    report = {"niveles_entrenamiento": list(levels), "muestras": len(y), "entrenamiento": len(y_tr), "prueba": len(y_te),
              "clase_mayoritaria": round(float(np.bincount(y_te).max() / len(y_te)), 4), "modelos": {}}

    for name, (est, grid) in CANDIDATES.items():
        t0 = time.perf_counter()
        search = GridSearchCV(est, grid, cv=cv, scoring="f1_macro", n_jobs=-1).fit(X_tr, y_tr)
        best = search.best_estimator_
        scores = cross_validate(best, X_tr, y_tr, cv=cv, scoring=["accuracy", "f1_macro"], n_jobs=-1)
        pred = best.predict(X_te)
        fname, fn = EXPORT[name]
        with open(os.path.join(OUT, fname), "w") as f:
            json.dump(fn(best), f, separators=(",", ":"))
        report["modelos"][name] = {
            "archivo": fname,
            "hiperparametros": {k.split("__")[-1]: (list(v) if isinstance(v, tuple) else v)
                                for k, v in search.best_params_.items()},
            "cv_exactitud": [round(float(scores["test_accuracy"].mean()), 4), round(float(scores["test_accuracy"].std()), 4)],
            "cv_f1_macro": [round(float(scores["test_f1_macro"].mean()), 4), round(float(scores["test_f1_macro"].std()), 4)],
            "prueba_exactitud": round(float(accuracy_score(y_te, pred)), 4),
            "prueba_f1_macro": round(float(f1_score(y_te, pred, average="macro")), 4),
            "entrenamiento_s": round(time.perf_counter() - t0, 1),
        }
        for ev in eval_levels:                 # transferencia: el experto en un mapa que el modelo no vio
            Xe, ye = load([ev])
            pe = best.predict(Xe)
            report["modelos"][name].setdefault("transferencia", {})[f"nivel_{ev}"] = {
                "exactitud": round(float(accuracy_score(ye, pe)), 4),
                "f1_macro": round(float(f1_score(ye, pe, average="macro", zero_division=0)), 4)}
        m = report["modelos"][name]
        print(f"{name:6s} {m['hiperparametros']}  CV exactitud {m['cv_exactitud'][0]:.3f}±{m['cv_exactitud'][1]:.3f}  "
              f"CV F1 {m['cv_f1_macro'][0]:.3f}±{m['cv_f1_macro'][1]:.3f}  prueba exactitud {m['prueba_exactitud']:.3f}  "
              f"F1 {m['prueba_f1_macro']:.3f}"
              + "".join(f"  | {k}: exactitud {v['exactitud']:.3f} F1 {v['f1_macro']:.3f}"
                        for k, v in m.get("transferencia", {}).items()))

    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(f"Línea base (predecir siempre la clase mayoritaria): exactitud {report['clase_mayoritaria']:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("levels", type=int, nargs="*", default=[1], help="niveles con los que se entrena")
    ap.add_argument("--eval", type=int, nargs="*", default=[], help="niveles NO vistos donde medir transferencia")
    a = ap.parse_args()
    main(a.levels or [1], a.eval)
