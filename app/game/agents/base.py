"""Interfaz común de los agentes perseguidores.

decide(graph, start, goal) es un generador:
  - percibe: nodo propio (start) y nodo del jugador (goal)
  - hace `yield` cada vez que expande un nodo (el scheduler los cuenta)
  - actúa: retorna la Edge que el enemigo recorrerá a continuación (o None)
"""


class Agent:
    name = "base"

    def reset(self):
        """Se llama al inicio de cada episodio."""

    def decide(self, graph, start, goal):
        return None
        yield  # convierte la función en generador

    def debug_path(self):
        """Celdas planificadas, para dibujarlas en pantalla. Vacío si el agente no planifica."""
        return []


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct(parent, goal):
    """Recorre parent[nodo] = (anterior, arista) desde el objetivo y devuelve (nodos, aristas) en orden."""
    nodes, edges = [goal], []
    while parent[nodes[-1]] is not None:
        prev, edge = parent[nodes[-1]]
        edges.append(edge)
        nodes.append(prev)
    return nodes[::-1], edges[::-1]


class PlannerAgent(Agent):
    """Agente basado en objetivos: replanifica la ruta completa en cada decisión y ejecuta la primera arista.

    Replanificar siempre (sin caché) mantiene la comparación limpia: "Nodos/dec" mide exactamente
    el costo de UNA búsqueda de cada algoritmo sobre el mismo grafo.
    """

    def __init__(self):
        self._path = []

    def reset(self):
        self._path = []

    def debug_path(self):
        return self._path[2:]       # el tramo inicial ya lo dibuja la arista en curso del enemigo

    def decide(self, graph, start, goal):
        self._path = []
        if goal is None or start == goal:
            return None
        parent = yield from self.search(graph, start, goal)
        if parent is None:
            return None             # objetivo inalcanzable desde aquí
        self._path, edges = reconstruct(parent, goal)
        return edges[0]

    def search(self, graph, start, goal):
        """Generador: `yield` por nodo expandido; retorna el dict parent o None."""
        raise NotImplementedError
        yield
