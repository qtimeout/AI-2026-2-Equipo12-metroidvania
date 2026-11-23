"""Graba las demostraciones del experto (A*) para entrenar a los agentes de aprendizaje.

Uso (desde la raíz): python tools/make_dataset.py [nivel]

Para cada par (nodo del enemigo, nodo del jugador) del nivel se ejecuta A* y se guarda
la decisión que tomaría el experto en ese estado: la clase de la PRIMERA arista de su ruta.
Es exactamente la decisión que A* toma en el juego, porque replanifica en cada nodo.

Salida: data/expert_level{N}.csv con columnas FEATURES + "clase".
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from game.agents.astar_agent import AStarAgent  # noqa: E402
from game.agents.base import reconstruct  # noqa: E402
from game.level import LEVELS, Level  # noqa: E402
from game.ml.features import FEATURES, action_class, features  # noqa: E402
from game.navgraph import NavGraph  # noqa: E402


def run(gen):
    """Ejecuta un generador de búsqueda hasta el final (offline no hace falta repartir por frames)."""
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        return stop.value


def main(n=1):
    level = Level(n)
    graph = NavGraph(level)
    expert = AStarAgent()
    out = os.path.join(ROOT, "data", f"expert_level{n}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    rows = 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FEATURES + ["clase"])
        for start in graph.nodes:
            for goal in graph.nodes:
                if start == goal:
                    continue
                parent = run(expert.search(graph, start, goal))
                if parent is None:
                    continue
                _, edges = reconstruct(parent, goal)
                x = features(graph, start, goal)
                w.writerow([round(v, 5) for v in x] + [action_class(start, edges[0])])
                rows += 1
    print(f"{rows} demostraciones del experto -> {out}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
