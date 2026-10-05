"""Mapas de tiles. '#' sólido, '.' vacío, 'P' jugador.
Enemigos: 'E' Husk saltador (también es el spawn del laboratorio IA), 'S' saltador, 'W' errante, 'H' cornudo.

Reglas de diseño (verificadas por tools/check_level.py):
  - el grafo de navegación debe ser fuertemente conexo (el enemigo puede ir y volver a cualquier nodo);
  - toda celda pisable tiene al menos 2 celdas libres de altura (los sprites miden ~1.6 celdas).
"""

# Nivel 1 — "Paso Olvidado" (inspirado en King's Pass)
LEVEL_1 = [
    "########################################################################",
    "########################################################################",
    "######..............#####.....................####....................##",
    "######..............#####.....................####....................##",
    "######..............#####.............................................##",
    "######................................................................##",
    "######................................................................##",
    "######................................................................##",
    "######................................................................##",
    "##..........######..................................#####.............##",
    "##..................................##................................##",
    "##..................................##................................##",
    "##.....#####.....................H..##.....................#####......##",
    "##..............................######.####...........................##",
    "##..............W...................##..................S.............##",
    "##............#####.................##................#####...........##",
    "##............................####..##.....#####......................##",
    "##..................................##............................E...##",
    "##......#####.......................##......................############",
    "##...................#########......##..........####............########",
    "##..P................#########......##..........####............########",
    "#####################################################....###############",
    "########################################################################",
    "########################################################################",
]

LEVELS = {1: LEVEL_1}


from .config import SPAWN_CHARS


class Level:
    def __init__(self, rows=LEVEL_1):
        self.h = len(rows)
        self.w = len(rows[0])
        assert all(len(r) == self.w for r in rows), "todas las filas deben tener el mismo ancho"
        self.player_spawn = self.enemy_spawn = None
        self.enemy_spawns = []           # [(celda, tipo)] en orden de lectura
        grid = []
        for r, row in enumerate(rows):
            line = []
            for c, ch in enumerate(row):
                if ch == "P":
                    self.player_spawn = (c, r)
                elif ch in SPAWN_CHARS:
                    self.enemy_spawns.append(((c, r), SPAWN_CHARS[ch]))
                    if ch == "E":
                        self.enemy_spawn = (c, r)
                line.append(ch == "#")
            grid.append(line)
        self._solid = grid

    def solid(self, c, r):
        if c < 0 or r < 0 or c >= self.w or r >= self.h:
            return True
        return self._solid[r][c]

    def standable(self, c, r):
        """Una celda es pisable si está vacía y tiene suelo debajo."""
        return not self.solid(c, r) and self.solid(c, r + 1)
