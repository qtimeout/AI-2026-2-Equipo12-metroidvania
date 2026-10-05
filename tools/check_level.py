"""Valida un nivel antes de usarlo: grafo fuertemente conexo y altura libre de 2 celdas.

Uso (desde la raíz): python tools/check_level.py [número_de_nivel]
Imprime el mapa: o = nodo válido, x = nodo sin ida o sin vuelta al spawn del enemigo, ! = sin altura.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
from game.level import LEVELS, Level  # noqa: E402
from game.navgraph import NavGraph  # noqa: E402


def main(n=1):
    lv = Level(LEVELS[n])
    g = NavGraph(lv)
    fwd = g.reachable_from(lv.enemy_spawn)
    back = {node for node in g.nodes if lv.enemy_spawn in g.reachable_from(node)}
    low = {node for node in g.nodes if lv.solid(node[0], node[1] - 1)}
    bad = [node for node in g.nodes if node not in fwd or node not in back]
    for r in range(lv.h):
        line = ""
        for c in range(lv.w):
            if lv.solid(c, r):
                line += "#"
            elif (c, r) in low:
                line += "!"
            elif (c, r) in g.edges:
                line += "x" if (c, r) in bad else "o"
            else:
                line += "."
        print(line)
    ok = not bad and not low and lv.player_spawn in g.edges and lv.enemy_spawn in g.edges
    print(f"\nNivel {n}: {len(g.nodes)} nodos, {sum(len(v) for v in g.edges.values())} aristas, "
          f"{len(bad)} sin conexión, {len(low)} sin altura -> {'OK' if ok else 'REVISAR'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 1) else 1)
