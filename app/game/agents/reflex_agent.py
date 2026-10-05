"""Agente reflejo simple: regla condición-acción sin memoria ni modelo del mapa.

Regla: "toma la arista cuyo destino quede más cerca del jugador en línea recta".
Cae en mínimos locales (paredes, techos): eso es lo que BFS/A* deben superar.
"""
from .base import Agent, manhattan


class ReflexAgent(Agent):
    name = "Reflejo"

    def decide(self, graph, start, goal):
        options = graph.neighbors(start)
        yield  # expande 1 nodo: el actual
        if not options or goal is None:
            return None
        return min(options, key=lambda e: (manhattan(e.target, goal), e.cost))
