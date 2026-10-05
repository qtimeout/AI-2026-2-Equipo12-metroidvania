"""MODO BASE: elige una arista al azar. Sin percepción del jugador."""
import random

from .base import Agent


class RandomAgent(Agent):
    name = "Aleatorio (base)"

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def decide(self, graph, start, goal):
        options = graph.neighbors(start)
        yield  # expande 1 nodo: el actual
        return self.rng.choice(options) if options else None
