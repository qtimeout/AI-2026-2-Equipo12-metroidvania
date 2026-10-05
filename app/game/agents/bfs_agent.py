"""BFS: búsqueda en anchura sobre el grafo de navegación.

Expande por niveles (cola FIFO), así que encuentra la ruta con MENOS ARISTAS (saltos/pasos),
no necesariamente la de menos celdas recorridas: ignora el costo de cada arista.
"""
from collections import deque

from .base import PlannerAgent


class BFSAgent(PlannerAgent):
    name = "BFS"

    def search(self, graph, start, goal):
        parent = {start: None}
        frontier = deque([start])
        while frontier:
            node = frontier.popleft()
            yield                                  # nodo expandido
            if node == goal:
                return parent
            for edge in graph.neighbors(node):
                if edge.target not in parent:
                    parent[edge.target] = (node, edge)
                    frontier.append(edge.target)
        return None
