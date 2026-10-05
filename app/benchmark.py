"""Benchmark en consola (sin ventana): misma simulación y mismos objetivos que el modo AUTO del juego.

Uso: python benchmark.py --rounds 50 --seed 2026 --budget 200
"""
import argparse
import time

from game.config import AI_BUDGET, DT, SEED
from game.level import Level
from game.navgraph import NavGraph
from game.world import World


def run(rounds, seed, budget):
    level = Level()
    graph = NavGraph(level)
    world = World(level, graph, mode="auto", seed=seed, budget=budget)
    total = rounds * len(world.names)
    t0 = time.perf_counter()
    while world.auto_episode < total:
        world.update(DT)
    elapsed = time.perf_counter() - t0
    print(f"Grafo: {len(graph.nodes)} nodos | {rounds} objetivos x {len(world.names)} técnicas | "
          f"semilla {seed} | presupuesto {budget} nodos/frame | {elapsed:.1f}s reales\n")
    print(world.metrics["auto"].as_text())
    print("\nComparación por pares en los mismos objetivos (fila gana a columna):\n")
    print(world.metrics["auto"].pairwise_text())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=50, help="objetivos distintos (cada técnica corre todos)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--budget", type=int, default=AI_BUDGET)
    args = ap.parse_args()
    run(args.rounds, args.seed, args.budget)
