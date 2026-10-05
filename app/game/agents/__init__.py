"""Registro de técnicas comparadas. Agregar un agente aquí lo suma al juego, a la tabla y al benchmark."""
from .astar_agent import AStarAgent
from .bfs_agent import BFSAgent
from .random_agent import RandomAgent
from .reflex_agent import ReflexAgent


def build_agents(seed):
    agents = [RandomAgent(seed), ReflexAgent(), BFSAgent(), AStarAgent()]
    return {a.name: a for a in agents}
