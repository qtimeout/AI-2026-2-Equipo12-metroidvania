"""Planificador por porciones: la IA nunca bloquea el bucle de juego.

Cada agente expone decide() como un generador que hace `yield` por cada nodo
expandido. El scheduler avanza como máximo `budget` expansiones por frame; si la
búsqueda no termina, continúa en el siguiente frame mientras el render sigue a 60 FPS.
(pygbag corre en WebAssembly sin hilos, por eso se usa time-slicing y no threading.)
"""
import time
from dataclasses import dataclass


@dataclass
class Decision:
    edge: object      # Edge elegida o None
    expanded: int     # nodos expandidos para decidir
    cpu_ms: float     # tiempo real de CPU consumido
    frames: int       # frames que tardó en decidir


class AIScheduler:
    def __init__(self, budget):
        self.budget = budget
        self.cancel()

    def cancel(self):
        self._gen = None
        self._expanded = 0
        self._cpu = 0.0
        self._frames = 0

    @property
    def pending(self):
        return self._gen is not None

    def request(self, agent, graph, start, goal):
        self._gen = agent.decide(graph, start, goal)
        self._expanded, self._cpu, self._frames = 0, 0.0, 0

    def step(self):
        """Ejecuta una porción. Devuelve Decision al terminar, o None si sigue pendiente."""
        if self._gen is None:
            return None
        self._frames += 1
        t0 = time.perf_counter()
        try:
            for _ in range(self.budget):
                next(self._gen)
                self._expanded += 1
        except StopIteration as stop:
            self._cpu += (time.perf_counter() - t0) * 1000
            d = Decision(stop.value, self._expanded, self._cpu, self._frames)
            self._gen = None
            return d
        self._cpu += (time.perf_counter() - t0) * 1000
        return None
