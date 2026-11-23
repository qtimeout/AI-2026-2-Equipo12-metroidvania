"""Benchmark en consola (sin ventana): misma simulación y mismos objetivos que el laboratorio del juego.

Uso:
  python benchmark.py --rounds 100 --seed 2026 --budget 200       una semilla, tabla completa + pares
  python benchmark.py --rounds 100 --seeds 2026 2027 2028          varias semillas: media ± desviación
  python benchmark.py --level 2 ...                                  laboratorio en otro nivel
  python benchmark.py --level 4 --rounds 30 [--seeds ...]            jefe: rondas de 60 s por estrategia
"""
import argparse
import statistics
import time

from game.config import AI_BUDGET, DT, SEED
from game.level import Level
from game.navgraph import NavGraph
from game.boss import BossWorld
from game.world import World


def run_boss(rounds, seed, level):
    world = BossWorld(level, mode="auto", seed=seed)
    while world.round < rounds * len(world.names):
        world.update(DT)
    return world


def boss(rounds, seeds, level_n):
    level = Level(level_n)
    per = {}
    for s in seeds:
        t0 = time.perf_counter()
        world = run_boss(rounds, s, level)
        print(f"semilla {s}: {time.perf_counter() - t0:.1f}s")
        if len(seeds) == 1:
            print()
            print(world.metrics["auto"].as_text())
        for name, st in world.metrics["auto"].stats.items():
            per.setdefault(name, []).append((100 * st.hits / st.attacks, 60 * st.hits / st.time))
    if len(seeds) > 1:
        fmt = lambda xs: f"{statistics.mean(xs):6.2f} ± {statistics.stdev(xs):5.2f}"
        print(f"\nJefe · {len(seeds)} semillas x {rounds} rondas de 60 s por estrategia (media ± desviación)\n")
        print(f"| {'Estrategia':22s} | {'Acierto %':15s} | {'Aciertos/min':15s} |")
        print(f"|{'-' * 24}|{'-' * 17}|{'-' * 17}|")
        for name, vals in per.items():
            print(f"| {name:22s} | {fmt([v[0] for v in vals]):15s} | {fmt([v[1] for v in vals]):15s} |")


def run(rounds, seed, budget, level=None, graph=None, level_n=1):
    level = level or Level(level_n)
    graph = graph or NavGraph(level)
    world = World(level, graph, mode="auto", seed=seed, budget=budget)
    total = rounds * len(world.names)
    while world.auto_episode < total:
        world.update(DT)
    return world


def single(rounds, seed, budget, level_n=1):
    t0 = time.perf_counter()
    world = run(rounds, seed, budget, level_n=level_n)
    print(f"Nivel {level_n} | grafo: {len(world.graph.nodes)} nodos | {rounds} objetivos x {len(world.names)} técnicas | "
          f"semilla {seed} | presupuesto {budget} nodos/frame | {time.perf_counter() - t0:.1f}s reales\n")
    print(world.metrics["auto"].as_text())
    print("\nComparación por pares en los mismos objetivos (fila gana a columna):\n")
    print(world.metrics["auto"].pairwise_text())


def multi(rounds, seeds, budget, level_n=1):
    level = Level(level_n)
    graph = NavGraph(level)
    per = {}                                   # técnica -> [(alcanza %, t. penalizado)] por semilla
    for s in seeds:
        t0 = time.perf_counter()
        world = run(rounds, s, budget, level, graph)
        for name, st in world.metrics["auto"].stats.items():
            per.setdefault(name, []).append((100 * st.captures / st.episodes, st.penal_time / st.episodes))
        print(f"semilla {s}: {time.perf_counter() - t0:.1f}s")
    fmt = lambda xs: f"{statistics.mean(xs):6.2f} ± {statistics.stdev(xs):5.2f}" if len(xs) > 1 else f"{xs[0]:6.2f}"
    print(f"\n{len(seeds)} semillas x {rounds} objetivos por técnica (media ± desviación entre semillas)\n")
    print(f"| {'Técnica':16s} | {'Alcanza %':15s} | {'T. penal. (s)':15s} |")
    print(f"|{'-' * 18}|{'-' * 17}|{'-' * 17}|")
    for name, vals in per.items():
        print(f"| {name:16s} | {fmt([v[0] for v in vals]):15s} | {fmt([v[1] for v in vals]):15s} |")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=50, help="objetivos distintos (cada técnica corre todos)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--seeds", type=int, nargs="+", help="varias semillas: reporta media ± desviación")
    ap.add_argument("--budget", type=int, default=AI_BUDGET)
    ap.add_argument("--level", type=int, default=1)
    args = ap.parse_args()
    if Level(args.level).boss:
        boss(args.rounds, args.seeds or [args.seed], args.level)
    elif args.seeds:
        multi(args.rounds, args.seeds, args.budget, args.level)
    else:
        single(args.rounds, args.seed, args.budget, args.level)
