"""Agente de aprendizaje (Bloque 2): imita a A* sin buscar en el grafo.

Percibe: su nodo, el del jugador y qué tipos de movimiento existen en su nodo (ml/features.py).
Decide: el modelo predice probabilidades por tipo de movimiento; se descartan los tipos que no
existen en el nodo y se toma el más probable. Entre las aristas de ese tipo, una regla simple
elige la que deja más cerca del jugador. No tiene memoria ni ruta: si el modelo se equivoca,
puede oscilar o atascarse, y eso se mide en el laboratorio.
"""
from ..ml.features import CLASSES, action_class, available, features
from .base import Agent, manhattan


class MLAgent(Agent):
    def __init__(self, name, model):
        self.name = name
        self.model = model

    def decide(self, graph, start, goal):
        options = graph.neighbors(start)
        if not options or goal is None or start == goal:
            return None
        x = features(graph, start, goal)                    # percepción
        probs = yield from self.model.predict(x)            # predicción (puede repartirse entre frames)
        mask = available(graph, start)
        best = max((i for i in range(len(CLASSES)) if mask[i]), key=lambda i: probs[i])
        chosen = [e for e in options if action_class(start, e) == CLASSES[best]]
        return min(chosen, key=lambda e: (manhattan(e.target, goal), e.cost))
