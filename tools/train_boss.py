"""Entrena la regresión logística que estima P(acierto | ataque, situación) para el jefe Hornet.

Uso (desde la raíz): python tools/train_boss.py [rondas]

1. Registra ataques del jefe ALEATORIO contra el jugador robot (cada ataque se elige al azar, así cada
   uno se prueba en todo tipo de situaciones, sin sesgo). Usa la semilla 7: el laboratorio evalúa con
   2026+, así que los datos de entrenamiento y de evaluación son trayectorias distintas.
2. Por cada ataque entrena LogisticRegression sobre términos de grado 2 de boss_features
   (distancia, altura, velocidad hacia el jefe, en el suelo), con validación cruzada de 5 particiones.
3. Exporta app/models/boss_logreg.json (el juego predice en Python puro) y reporta exactitud, AUC y Brier.
"""
import json
import os
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from game.boss import ATTACKS, BossMetrics, BossWorld, boss_features  # noqa: E402
from game.config import DT  # noqa: E402
from game.level import LEVELS, Level  # noqa: E402

TRAIN_SEED = 7
OUT = os.path.join(ROOT, "app", "models", "boss_logreg.json")


def record(rounds):
    level = Level(max(n for n, v in LEVELS.items() if v.get("jefe")))
    w = BossWorld(level, mode="auto", seed=TRAIN_SEED)
    w.strategies = {k: v for k, v in w.strategies.items() if k == "Aleatorio (base)"}
    w.names = list(w.strategies)
    w.metrics["auto"] = BossMetrics(w.names)
    w.reset_episode()
    data, current = [], None
    decide = w._decide

    def logged():
        nonlocal current
        decide()
        current = [w.boss.attack, boss_features(w.last_obs), 0]
        data.append(current)

    w._decide = logged
    while w.round < rounds:
        w.update(DT)
        if current is not None and w.boss.hit_this_attack:
            current[2] = 1
    return data


def main(rounds=60):
    data = record(rounds)
    report = {"semilla_datos": TRAIN_SEED, "rondas": rounds, "ataques": len(data), "modelos": {}}
    export = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=2026)
    for a in ATTACKS:
        X = np.array([f for k, f, _ in data if k == a])
        y = np.array([h for k, _, h in data if k == a])
        pipe = make_pipeline(PolynomialFeatures(2, include_bias=False), StandardScaler(),
                             LogisticRegression(C=1.0, max_iter=2000))
        sc = cross_validate(pipe, X, y, cv=cv, scoring=["accuracy", "roc_auc", "neg_brier_score"])
        pipe.fit(X, y)
        s, lr = pipe.named_steps["standardscaler"], pipe.named_steps["logisticregression"]
        export[a] = {"media": s.mean_.round(6).tolist(), "escala": s.scale_.round(6).tolist(),
                     "coef": lr.coef_[0].round(6).tolist(), "intercepto": round(float(lr.intercept_[0]), 6)}
        report["modelos"][a] = {
            "muestras": int(len(y)), "acierto_real": round(float(y.mean()), 3),
            "cv_exactitud": round(float(sc["test_accuracy"].mean()), 3),
            "cv_auc": round(float(sc["test_roc_auc"].mean()), 3),
            "cv_brier": round(float(-sc["test_neg_brier_score"].mean()), 3),
            "brier_base": round(float(brier_score_loss(y, np.full(len(y), y.mean()))), 3),
        }
        m = report["modelos"][a]
        print(f"{a:10s} n={m['muestras']:4d}  acierto real {m['acierto_real']:.2f}  CV exactitud {m['cv_exactitud']:.3f}  "
              f"AUC {m['cv_auc']:.3f}  Brier {m['cv_brier']:.3f} (base {m['brier_base']:.3f})")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"modelos": export}, f)
    with open(OUT.replace(".json", "_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(f"{len(data)} ataques registrados -> {OUT}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
