"""Enemigo (Husk): actuador del agente sobre el grafo de navegación.

El agente decide la arista; aquí solo se ejecuta. La trayectoria visual de los saltos y
caídas es una parábola entre nodos, pero el progreso se mide en celdas recorridas (costo
de la arista), igual que en el benchmark: la IA y el movimiento quedan separados.
"""
from .config import ENEMY_H, ENEMY_TYPES, ENEMY_W, TILE


class Enemy:
    def __init__(self, node, kind="saltador"):
        stats = ENEMY_TYPES[kind]
        self.kind = kind
        self.speed = stats["speed"]
        self.anim = stats["anim"]
        self.node = node
        self.edge = None
        self.cells = [node]
        self.progress = 0.0
        self.steps = 0
        self.facing = -1
        self.hp = stats["hp"]
        self.stun = 0.0          # aturdido: no avanza
        self.flash = 0.0         # destello blanco al recibir daño
        self.dead_t = -1.0       # >= 0 mientras está muerto

    @property
    def alive(self):
        return self.dead_t < 0

    def start_edge(self, edge):
        self.edge = edge
        self.cells = [self.node, *edge.path]
        self.progress = 0.0
        dx = edge.target[0] - self.node[0]
        if dx:
            self.facing = 1 if dx > 0 else -1

    def update(self, dt):
        """Avanza por la arista actual. Devuelve True al llegar al nodo destino."""
        self.flash = max(0.0, self.flash - dt)
        if self.stun > 0:
            self.stun -= dt
            return False
        if self.edge is None:
            return False
        self.progress += self.speed * dt
        if self.progress >= self.edge.cost:
            self.node = self.edge.target
            self.edge = None
            self.cells = [self.node]
            self.progress = 0.0
            self.steps += 1
            return True
        return False

    def take_hit(self, stun):
        self.hp -= 1
        self.flash = 0.12
        self.stun = stun
        return self.hp <= 0

    @property
    def phase(self):
        """Fracción recorrida de la arista actual (0..1)."""
        return self.progress / self.edge.cost if self.edge else 0.0

    def position(self):
        """Posición en celdas (float): lineal al caminar, parábola al saltar o caer."""
        if self.edge is None:
            return (float(self.node[0]), float(self.node[1]))
        t = self.phase
        (x0, y0), (x1, y1) = self.node, self.edge.target
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        if self.edge.kind == "jump":
            apex = min(c[1] for c in self.edge.path) - 0.25      # cruza por encima de la trayectoria en L
            h = (y0 + y1) / 2 - apex
            y -= h * 4 * t * (1 - t)
        elif self.edge.kind == "fall":
            # avanza en horizontal primero y cae acelerando
            x = x0 + (x1 - x0) * min(1.0, t * 3)
            y = y0 + (y1 - y0) * t * t
        return (x, y)

    @property
    def rect(self):
        c, r = self.position()
        return (c * TILE + (TILE - ENEMY_W) / 2, (r + 1) * TILE - ENEMY_H, ENEMY_W, ENEMY_H)
