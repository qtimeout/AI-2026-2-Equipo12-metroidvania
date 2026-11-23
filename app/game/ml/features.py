"""Percepción de los agentes de aprendizaje: estado -> vector de características, y arista -> clase.

Se usa igual al GRABAR las demostraciones del experto (tools/make_dataset.py) y al PREDECIR
dentro del juego (agents/ml_agent.py), así entrenamiento e inferencia ven exactamente lo mismo.
Python puro: debe correr en el navegador (pygbag), donde no hay numpy ni scikit-learn.
"""

# Clase = tipo de movimiento. El modelo elige el tipo; una regla elige la arista concreta de ese tipo.
CLASSES = [
    "walk_L", "walk_R",
    "fall_L", "fall_R",
    "jump_up_L", "jump_up_R",
    "jump_flat_L", "jump_flat_R",
    "jump_down_L", "jump_down_R",
]
INDEX = {c: i for i, c in enumerate(CLASSES)}

FEATURES = ["c", "r", "goal_c", "goal_r", "dx", "dy"] + [f"puede_{c}" for c in CLASSES]


def action_class(node, edge):
    """Tipo de movimiento de una arista: dirección horizontal + clase de desplazamiento vertical."""
    (c, r), (tc, tr) = node, edge.target
    side = "R" if tc > c else "L"
    if edge.kind == "jump":
        vert = "up" if tr < r else ("flat" if tr == r else "down")
        return f"jump_{vert}_{side}"
    return f"{edge.kind}_{side}"


def available(graph, node):
    """Máscara de clases disponibles en el nodo (qué tipos de movimiento existen ahí)."""
    mask = [0] * len(CLASSES)
    for e in graph.neighbors(node):
        mask[INDEX[action_class(node, e)]] = 1
    return mask


def features(graph, node, goal):
    """Vector de entrada del modelo. Posiciones normalizadas por el tamaño del nivel."""
    w, h = graph.level.w, graph.level.h
    (c, r), (gc, gr) = node, goal
    return [c / w, r / h, gc / w, gr / h, (gc - c) / w, (gr - r) / h] + available(graph, node)
