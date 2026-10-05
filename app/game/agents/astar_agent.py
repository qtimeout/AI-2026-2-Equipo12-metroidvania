"""A*: búsqueda informada con f(n) = g(n) + h(n).

g = celdas recorridas desde el inicio (costo real de las aristas).
h = distancia Manhattan al jugador. Es admisible y consistente porque cada arista recorre
una trayectoria en L de celdas: su costo nunca es menor que la Manhattan entre sus extremos.
Con eso A* devuelve la ruta de menor costo y expande menos nodos que BFS.
"""
import heapq
from itertools import count

from .base import PlannerAgent, manhattan


class AStarAgent(PlannerAgent):
    name = "A*"

    def __init__(self, heuristic_weight=1.0):
        super().__init__()
        self.w = heuristic_weight          # 1.0 = A* clásico; >1 sobreestima (más rápido, ya no óptimo)

    def search(self, graph, start, goal):
        tie = count()                      # desempate estable entre nodos con igual f
        g = {start: 0}
        parent = {start: None}
        frontier = [(self.w * manhattan(start, goal), next(tie), start)]
        closed = set()
        while frontier:
            _, _, node = heapq.heappop(frontier)
            if node in closed:
                continue
            closed.add(node)
            yield                                  # nodo expandido
            if node == goal:
                return parent
            for edge in graph.neighbors(node):
                ng = g[node] + edge.cost
                if ng < g.get(edge.target, float("inf")):
                    g[edge.target] = ng
                    parent[edge.target] = (node, edge)
                    f = ng + self.w * manhattan(edge.target, goal)
                    heapq.heappush(frontier, (f, next(tie), edge.target))
        return None
