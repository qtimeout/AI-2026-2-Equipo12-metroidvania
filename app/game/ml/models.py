"""Inferencia en Python puro de los modelos entrenados con tools/train_models.py.

Cada modelo expone predict(x): un generador que puede hacer `yield PAUSE` para repartir el
cálculo entre frames, y que retorna un vector de probabilidades sobre features.CLASSES.
"""
import json
import math
import os

from .features import CLASSES

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
PAUSE = "pausa"          # el scheduler lo cuenta contra el presupuesto, pero NO como nodo expandido
# Puntos comparados por pausa. Calibrado midiendo: expandir un nodo de A* cuesta ~5.6 µs y comparar
# una demostración ~2.4 µs, así que 1 unidad del presupuesto por frame ≈ 2 comparaciones del KNN.
# Así el presupuesto (AI_BUDGET) vale lo mismo en tiempo para búsqueda y para aprendizaje.
KNN_CHUNK = 2


def _full(probs_by_class, classes):
    out = [0.0] * len(CLASSES)
    for cls, p in zip(classes, probs_by_class):
        out[cls] = p
    return out


class KNNModel:
    """Vecinos más cercanos: compara el estado con TODAS las demostraciones guardadas (distancia euclídea)."""

    def __init__(self, d):
        self.k, self.X, self.y = d["k"], d["X"], d["y"]

    def predict(self, x):
        best = []                                   # (distancia², etiqueta) de los k más cercanos
        for i, (row, label) in enumerate(zip(self.X, self.y)):
            d2 = 0.0
            for a, b in zip(row, x):
                d2 += (a - b) * (a - b)
            if len(best) < self.k or d2 < best[-1][0]:
                best.append((d2, label))
                best.sort()
                del best[self.k:]
            if i % KNN_CHUNK == KNN_CHUNK - 1:
                yield PAUSE
        votes = [0.0] * len(CLASSES)
        for _, label in best:
            votes[label] += 1.0 / self.k
        return votes


class TreeModel:
    """Árbol de decisión: baja de la raíz a una hoja comparando una característica con un umbral por nivel."""

    def __init__(self, d):
        self.left, self.right = d["izq"], d["der"]
        self.feature, self.threshold, self.prob, self.classes = d["feature"], d["umbral"], d["prob"], d["clases"]

    def predict(self, x):
        n = 0
        while self.left[n] != -1:
            n = self.left[n] if x[self.feature[n]] <= self.threshold[n] else self.right[n]
        return _full(self.prob[n], self.classes)
        yield


class MLPModel:
    """Perceptrón multicapa: entrada normalizada -> capas ocultas ReLU -> salida softmax."""

    def __init__(self, d):
        self.mean, self.scale, self.W, self.b, self.classes = d["media"], d["escala"], d["W"], d["b"], d["clases"]

    def predict(self, x):
        h = [(v - m) / s for v, m, s in zip(x, self.mean, self.scale)]
        for layer, (W, b) in enumerate(zip(self.W, self.b)):
            z = [bj + sum(h[i] * W[i][j] for i in range(len(h))) for j, bj in enumerate(b)]
            h = [max(0.0, v) for v in z] if layer < len(self.W) - 1 else z
        top = max(h)
        exp = [math.exp(v - top) for v in h]
        total = sum(exp)
        return _full([e / total for e in exp], self.classes)
        yield


LOADERS = {"knn": KNNModel, "tree": TreeModel, "mlp": MLPModel}


def load(filename):
    """Carga un modelo exportado; None si todavía no se entrenó (el juego funciona sin él)."""
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        d = json.load(f)
    return LOADERS[d["tipo"]](d)
