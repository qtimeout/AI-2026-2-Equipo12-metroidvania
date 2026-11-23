"""Registro de técnicas comparadas. Agregar un agente aquí lo suma al juego, a la tabla y al benchmark.

Bloque 1: Aleatorio (base), Reflejo, BFS, A*.
Bloque 2: KNN, Árbol y MLP imitan a A* (modelos en app/models/, entrenados con tools/train_models.py).
Si un modelo no está entrenado, su agente simplemente no aparece.
"""
from ..ml.models import load
from .astar_agent import AStarAgent
from .bfs_agent import BFSAgent
from .ml_agent import MLAgent
from .random_agent import RandomAgent
from .reflex_agent import ReflexAgent

ML_MODELS = [("KNN", "knn.json"), ("Árbol", "tree.json"), ("MLP", "mlp.json")]
_cache = {}


def _model(filename):
    if filename not in _cache:          # los modelos se cargan una vez y se comparten (son solo lectura)
        _cache[filename] = load(filename)
    return _cache[filename]


def build_agents(seed):
    agents = [RandomAgent(seed), ReflexAgent(), BFSAgent(), AStarAgent()]
    for name, filename in ML_MODELS:
        model = _model(filename)
        if model is not None:
            agents.append(MLAgent(name, model))
    return {a.name: a for a in agents}
