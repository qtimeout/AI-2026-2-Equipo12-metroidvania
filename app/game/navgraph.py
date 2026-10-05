"""Grafo de navegación del enemigo (diseño de estado).

Estado = celda pisable (c, r). Acciones = aristas walk / fall / jump.
El costo de una arista es el número de celdas que recorre su trayectoria en L,
así que la distancia Manhattan nunca sobreestima (heurística admisible para A*).
"""
from dataclasses import dataclass

from .config import JUMP_ACROSS, JUMP_UP, TILE


@dataclass(frozen=True)
class Edge:
    target: tuple
    cost: int
    kind: str      # "walk" | "fall" | "jump"
    path: tuple    # celdas recorridas, sin el origen y con el destino al final


class NavGraph:
    def __init__(self, level, jump_up=JUMP_UP, jump_across=JUMP_ACROSS):
        self.level = level
        self.jump_up = jump_up
        self.jump_across = jump_across
        self.nodes = [(c, r) for r in range(level.h) for c in range(level.w) if level.standable(c, r)]
        self.edges = {n: self._build_edges(n) for n in self.nodes}

    def neighbors(self, node):
        return self.edges.get(node, [])

    def _fall_from(self, c, r, path):
        """Cae por la columna c desde la fila r hasta una celda pisable."""
        lv = self.level
        while not lv.standable(c, r):
            r += 1
            if lv.solid(c, r):
                return None
            path.append((c, r))
        return (c, r)

    def _build_edges(self, node):
        lv = self.level
        c, r = node
        best = {}

        def add(target, kind, path):
            if target is None or target == node:
                return
            e = Edge(target, len(path), kind, tuple(path))
            if target not in best or e.cost < best[target].cost:
                best[target] = e

        for sx in (-1, 1):
            # Caminar o caer por el borde
            nc = c + sx
            if not lv.solid(nc, r):
                path = [(nc, r)]
                target = self._fall_from(nc, r, path)
                add(target, "walk" if target == (nc, r) else "fall", path)

            # Saltar: subir k celdas, avanzar dx en horizontal, caer hasta aterrizar
            for k in range(1, self.jump_up + 1):
                rise = [(c, r - i) for i in range(1, k + 1)]
                if any(lv.solid(*cell) for cell in rise):
                    break
                for dx in range(1, self.jump_across + 1):
                    across = [(c + sx * i, r - k) for i in range(1, dx + 1)]
                    if any(lv.solid(*cell) for cell in across):
                        break
                    path = rise + across
                    target = self._fall_from(c + sx * dx, r - k, path)
                    add(target, "jump", path)
        return list(best.values())

    def locate(self, px, py_feet):
        """Nodo bajo un punto en píxeles (centro x, pies y). None si está en el aire."""
        c, r = int(px // TILE), int((py_feet - 1) // TILE)
        return (c, r) if self.level.standable(c, r) else None

    def reachable_from(self, start):
        """Nodos alcanzables desde start (utilidad offline para elegir objetivos válidos)."""
        seen, stack = {start}, [start]
        while stack:
            for e in self.neighbors(stack.pop()):
                if e.target not in seen:
                    seen.add(e.target)
                    stack.append(e.target)
        return seen
