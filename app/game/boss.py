"""Jefe final (nivel 4): Hornet. Lógica pura, sin pygame.

PROBLEMA DE IA DEL JEFE: en cada pausa entre ataques, elegir QUÉ ataque usar para acertarle al jugador.
  Percepción: posición relativa del jugador (dx, dy), si está en el suelo y su velocidad estimada.
  Acciones:   "lanza" (aguja lanzada en horizontal), "embestida" (carga por el suelo), "salto" (cae sobre él).
  Métrica:    % de ataques que aciertan y aciertos por minuto, contra el MISMO jugador robot sembrado.

Estrategias comparadas:
  Aleatorio (base)       -> ataque al azar.
  Reflejo                -> reglas condición-acción según la distancia y la altura del jugador AHORA.
  Utilidad (a mano)      -> agente basado en utilidad (Bloque 1): utilidad = P(acierto) / duración, con
                            P(acierto) de un modelo geométrico escrito a mano (predice dónde estará el jugador).
  Utilidad (aprendida)   -> mismo agente, pero P(acierto) la estima una regresión logística (Bloque 2)
                            entrenada con ataques registrados (tools/train_boss.py).
"""
import json
import math
import os
import random
import time

from .config import (BOSS_COOLDOWN, BOSS_INTRO, BOSS_H, BOSS_HP, BOSS_LAB_ROUND, BOSS_W, GRAVITY, PLAYER_H, PLAYER_W,
                     SEED, SOUL_PER_HIT, TILE)
from .player import Player

ATTACKS = ["lanza", "embestida", "salto"]
THREAD_SPEED, THREAD_REACH = 950.0, 520.0
DASH_SPEED, DASH_TIME = 1150.0, 0.45
JUMP_TIME = 0.8
WINDUP = {"lanza": 0.35, "embestida": 0.30, "salto": 0.45}   # preparación visible: el jugador puede reaccionar
RECOVER = {"lanza": 0.25, "embestida": 0.30, "salto": 0.35}
DURATION = {"lanza": WINDUP["lanza"] + 2 * THREAD_REACH / THREAD_SPEED + RECOVER["lanza"],
            "embestida": WINDUP["embestida"] + DASH_TIME + RECOVER["embestida"],
            "salto": WINDUP["salto"] + JUMP_TIME + RECOVER["salto"]}


# ---------------------------------------------------------------- estrategias (agentes del jefe)
class BossStrategy:
    name = "base"

    def choose(self, obs):
        """obs: dx, dy (jugador - jefe, px; dy < 0 = arriba), pvx (px/s), on_ground, half_w (mitad de la arena).
        Devuelve (ataque, x objetivo del salto)."""
        raise NotImplementedError


class RandomBoss(BossStrategy):
    name = "Aleatorio (base)"

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def choose(self, obs):
        return self.rng.choice(ATTACKS), obs["px"]


class ReflexBoss(BossStrategy):
    name = "Reflejo"

    def choose(self, obs):
        if obs["dy"] < -90:                      # el jugador está arriba: caerle encima
            return "salto", obs["px"]
        if abs(obs["dx"]) < 260:                 # cerca: embestida
            return "embestida", obs["px"]
        return "lanza", obs["px"]                # lejos: aguja


class UtilityBoss(BossStrategy):
    """Elige el ataque con mayor utilidad = aciertos esperados por segundo = P(acierto) / duración."""
    name = "Utilidad (a mano)"

    def __init__(self):
        self.last = {}

    def choose(self, obs):
        best, best_u, target = None, -1e9, obs["px"]
        self.last = {}
        for a in ATTACKS:
            p, tx = self.hit_probability(a, obs)
            u = p / DURATION[a]
            self.last[a] = round(p, 2)
            if u > best_u:
                best, best_u, target = a, u, tx
        return best, target

    @staticmethod
    def _predict_dx(obs, t):
        """Modelo del mundo: el jugador sigue a la misma velocidad horizontal (acotado por la arena)."""
        dx = obs["dx"] + obs["pvx"] * t
        return max(-obs["half_w"] * 2, min(obs["half_w"] * 2, dx))

    def hit_probability(self, a, obs):
        dy = obs["dy"]
        if a == "lanza":
            t = WINDUP[a] + min(abs(obs["dx"]), THREAD_REACH) / THREAD_SPEED
            dx = abs(self._predict_dx(obs, t))
            vert = max(0.0, 1 - max(0.0, abs(dy + 10) - 30) / 60)          # la aguja va a media altura
            horiz = 1.0 if dx <= THREAD_REACH else max(0.0, 1 - (dx - THREAD_REACH) / 150)
            return vert * horiz * (0.6 if not obs["on_ground"] else 1.0), obs["px"]
        if a == "embestida":
            t = WINDUP[a] + min(abs(obs["dx"]), DASH_SPEED * DASH_TIME) / DASH_SPEED
            dx = abs(self._predict_dx(obs, t))
            vert = 1.0 if dy > -BOSS_H * 0.6 else 0.1                        # solo pega a ras de suelo
            horiz = 1.0 if dx <= DASH_SPEED * DASH_TIME else max(0.0, 1 - (dx - DASH_SPEED * DASH_TIME) / 120)
            return vert * horiz, obs["px"]
        t = WINDUP[a] + JUMP_TIME                                             # salto: cae donde estará
        dx = self._predict_dx(obs, t)
        reach = 1.0 if abs(dx) < 700 else 0.3
        vert = 0.85 if dy > -230 else 0.2                                     # altura máxima del salto ≈ 210 px
        return reach * vert, obs["boss_x"] + dx


def boss_features(obs):
    """Percepción del jefe convertida en números (la misma al registrar datos y al predecir).
    adx: distancia horizontal, dy: altura relativa, acerca: velocidad del jugador hacia el jefe, suelo: 0/1."""
    side = 1 if obs["dx"] >= 0 else -1
    return [abs(obs["dx"]) / 1000, obs["dy"] / 300, -side * obs["pvx"] / 300, 1.0 if obs["on_ground"] else 0.0]


def poly2(x):
    """Términos de grado 2 en el mismo orden que sklearn.PolynomialFeatures(2, include_bias=False)."""
    return list(x) + [x[i] * x[j] for i in range(len(x)) for j in range(i, len(x))]


BOSS_MODEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "boss_logreg.json")


class LearnedUtilityBoss(UtilityBoss):
    """Igual que la utilidad a mano, pero P(acierto | ataque, situación) sale de una regresión logística."""
    name = "Utilidad (aprendida)"

    def __init__(self, model):
        super().__init__()
        self.model = model                       # {ataque: {media, escala, coef, intercepto}}

    def hit_probability(self, a, obs):
        m = self.model[a]
        x = poly2(boss_features(obs))
        z = m["intercepto"] + sum(c * (v - mu) / sc for c, v, mu, sc in zip(m["coef"], x, m["media"], m["escala"]))
        p = 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))
        _, target = UtilityBoss.hit_probability(self, a, obs)          # el destino del salto se calcula igual
        return p, target


def build_boss_strategies(seed):
    strategies = [RandomBoss(seed), ReflexBoss(), UtilityBoss()]
    if os.path.exists(BOSS_MODEL):
        with open(BOSS_MODEL) as f:
            strategies.append(LearnedUtilityBoss(json.load(f)["modelos"]))
    return {s.name: s for s in strategies}


# ---------------------------------------------------------------- cuerpo y ataques del jefe
def collide(body, level, w, h, axis):
    c0, c1 = int(body.x // TILE), int((body.x + w - 1e-6) // TILE)
    r0, r1 = int(body.y // TILE), int((body.y + h - 1e-6) // TILE)
    hit = False
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if not level.solid(c, r):
                continue
            hit = True
            if axis == 0:
                if body.vx > 0:
                    body.x = c * TILE - w
                elif body.vx < 0:
                    body.x = (c + 1) * TILE
                body.vx = 0
            else:
                if body.vy > 0:
                    body.y = r * TILE - h
                    body.on_ground = True
                elif body.vy < 0:
                    body.y = (r + 1) * TILE
                body.vy = 0
    return hit


class Boss:
    def __init__(self, cell):
        c, r = cell
        self.x = c * TILE + (TILE - BOSS_W) / 2
        self.y = (r + 1) * TILE - BOSS_H
        self.vx = self.vy = 0.0
        self.on_ground = True
        self.facing = -1
        self.hp = BOSS_HP
        self.flash = 0.0
        self.state, self.attack, self.t = "idle", None, 0.0
        self.thread = 0.0                 # largo actual de la aguja
        self.jump_target = None
        self.hit_this_attack = False
        self.dead_t = -1.0

    @property
    def rect(self):
        return (self.x, self.y, BOSS_W, BOSS_H)

    @property
    def center(self):
        return self.x + BOSS_W / 2, self.y + BOSS_H / 2

    def start(self, attack, target_x, player_cx):
        self.attack, self.state, self.t = attack, "windup", 0.0
        self.facing = 1 if player_cx > self.center[0] else -1
        self.jump_target = target_x
        self.hit_this_attack = False

    def hitboxes(self):
        """Zonas que hacen daño en este instante (además del contacto con el cuerpo)."""
        if self.state == "active":
            if self.attack == "lanza" and self.thread > 0:
                hx = self.center[0] + self.facing * 18
                x = hx if self.facing > 0 else hx - self.thread
                return [(x, self.y + BOSS_H * 0.42 - 13, self.thread, 26)]
            return [self.rect]
        if self.state == "recover" and self.attack == "salto" and self.t < 0.15:
            cx = self.center[0]
            return [(cx - 100, self.y + BOSS_H - 40, 200, 40)]          # onda al aterrizar
        return []

    def update(self, dt, level):
        self.flash = max(0.0, self.flash - dt)
        self.t += dt
        if self.state == "windup" and self.t >= WINDUP[self.attack]:
            self.state, self.t = "active", 0.0
            if self.attack == "embestida":
                self.vx = self.facing * DASH_SPEED
            elif self.attack == "salto":
                self.vy = -GRAVITY * JUMP_TIME / 2
                self.vx = (self.jump_target - self.center[0]) / JUMP_TIME
                self.on_ground = False
        elif self.state == "active":
            if self.attack == "lanza":
                out = self.t * THREAD_SPEED
                self.thread = out if out <= THREAD_REACH else max(0.0, 2 * THREAD_REACH - out)
                if out >= 2 * THREAD_REACH:
                    self.thread, self.state, self.t = 0.0, "recover", 0.0
            elif self.attack == "embestida" and self.t >= DASH_TIME:
                self.vx, self.state, self.t = 0.0, "recover", 0.0
            elif self.attack == "salto" and self.on_ground and self.t > 0.1:
                self.vx, self.state, self.t = 0.0, "recover", 0.0
        elif self.state == "recover" and self.t >= RECOVER[self.attack]:
            self.state, self.t, self.attack = "idle", 0.0, None

        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        if collide(self, level, BOSS_W, BOSS_H, 0) and self.attack == "embestida" and self.state == "active":
            self.state, self.t = "recover", 0.0            # chocó con la pared
        self.y += self.vy * dt
        self.on_ground = False
        collide(self, level, BOSS_W, BOSS_H, 1)


# ---------------------------------------------------------------- jugador robot del laboratorio
class PlayerBot:
    """Controla al Knight en el laboratorio con una secuencia sembrada: corre, se detiene y salta al azar.
    No depende de lo que haga el jefe, así que la trayectoria es IDÉNTICA para todas las estrategias."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.move, self.timer, self.jump = 0, 0.0, False

    def controls(self, dt, player, level_w):
        self.timer -= dt
        jump = False
        if self.timer <= 0:
            self.timer = self.rng.uniform(0.3, 0.9)
            self.move = self.rng.choice([-1, -1, 0, 1, 1])
            jump = self.rng.random() < 0.35
        cx = player.x + PLAYER_W / 2
        if cx < TILE * 3:
            self.move = 1
        elif cx > level_w - TILE * 3:
            self.move = -1
        return (self.move, jump, jump or player.vy < 0, False, False)


# ---------------------------------------------------------------- métricas del jefe
BOSS_HEADERS = ["Estrategia", "Corridas", "Ataques", "Acierto %", "Aciertos/min", "L / E / S %", "ms/dec"]


class BossStats:
    def __init__(self):
        self.rounds = self.attacks = self.hits = 0
        self.time = 0.0
        self.cpu_ms = 0.0
        self.mix = {a: 0 for a in ATTACKS}

    def row(self, name):
        a = self.attacks
        mix = " / ".join(f"{100 * self.mix[k] / a:.0f}" for k in ATTACKS) if a else "-"
        return [name, str(self.rounds), str(a), f"{100 * self.hits / a:.0f}%" if a else "-",
                f"{60 * self.hits / self.time:.1f}" if self.time else "-", mix,
                f"{self.cpu_ms / a:.3f}" if a else "-"]


class BossMetrics:
    def __init__(self, names):
        self.names = list(names)
        self.stats = {n: BossStats() for n in names}

    def rows(self):
        return [s.row(n) for n, s in self.stats.items()]

    def as_text(self):
        rows = [BOSS_HEADERS] + self.rows()
        widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
        fmt = lambda r: "| " + " | ".join(v.ljust(w) for v, w in zip(r, widths)) + " |"
        return "\n".join([fmt(rows[0]), "|" + "|".join("-" * (w + 2) for w in widths) + "|"] + [fmt(r) for r in rows[1:]])


# ---------------------------------------------------------------- mundo del jefe
class BossWorld:
    """Misma interfaz que World para que la escena, el render y el HUD funcionen igual."""

    def __init__(self, level, mode="manual", seed=SEED, strategy=None):
        self.level, self.seed, self.mode = level, seed, mode
        self.strategies = build_boss_strategies(seed)
        self.names = list(self.strategies)
        self.selection = strategy if strategy in self.strategies else self.names[-1]
        self.metrics = {"manual": BossMetrics(self.names), "auto": BossMetrics(self.names)}
        self.events = []
        self.finished = self.won = False
        self.slots = []                       # sin Husks en la arena (el render los dibuja desde aquí)
        self.goal = level.player_spawn
        self.round = 0
        self.reset_episode()

    # compatibilidad con la escena
    @property
    def technique(self):
        return self.names[self.round % len(self.names)] if self.mode == "auto" else self.selection

    @property
    def active_techniques(self):
        return {self.technique}

    @property
    def strategy(self):
        return self.strategies[self.technique]

    def set_mode(self, mode):
        self.mode, self.round = mode, 0
        self.reset_episode()

    def set_selection(self, name):
        if name in self.strategies and name != self.selection:
            self.selection = name

    def reset_metrics(self):
        self.metrics[self.mode] = BossMetrics(self.names)
        self.round = 0
        self.reset_episode()

    def reset_episode(self):
        self.player = Player(self.level.player_spawn)
        self.boss = Boss(self.level.boss_spawn)
        self.t = 0.0
        self.cooldown = BOSS_INTRO if self.mode == "manual" else BOSS_COOLDOWN
        self.history = []                     # (t, x) del jugador para estimar su velocidad
        n = len(self.names)
        self.bot = PlayerBot(self.seed * 1000 + self.round // n) if self.mode == "auto" else None
        if self.mode == "auto":
            self.player.invuln = 1e9          # el robot no recibe daño: los aciertos se cuentan, no se aplican

    def _stats(self):
        return self.metrics[self.mode].stats[self.technique]

    # ---------- paso de simulación ----------
    def update(self, dt, controls=None):
        p, b = self.player, self.boss
        if self.mode == "auto":
            controls = self.bot.controls(dt, p, self.level.w * TILE)
        if controls is not None:
            p.update(dt, self.level, *controls)
        self.t += dt
        if self.mode == "manual" and p.hp <= 0:
            self.events.append(("player_dead", p.rect))
            self.reset_episode()
            return

        if b.dead_t >= 0:                     # jefe derrotado: pequeña pausa y fin del juego
            b.dead_t += dt
            if b.dead_t > 2.5:
                self.finished = self.won = True
            return

        pcx = p.x + PLAYER_W / 2
        self.history = [(t, x) for t, x in self.history if self.t - t <= 0.3] + [(self.t, pcx)]

        if b.state == "idle" and b.on_ground:
            self.cooldown -= dt
            if self.cooldown <= 0:
                self._decide()
        b.update(dt, self.level)
        self._stats().time += dt                 # tiempo de pelea (para aciertos por minuto), en vivo

        self._resolve_hits()
        if self.mode == "auto" and self.t >= BOSS_LAB_ROUND:
            self._stats().rounds += 1
            self.round += 1
            self.reset_episode()

    def _observe(self):
        p, b = self.player, self.boss
        (t0, x0), (t1, x1) = self.history[0], self.history[-1]
        pvx = (x1 - x0) / (t1 - t0) if t1 > t0 else 0.0
        bcx, _ = b.center
        return {"dx": p.x + PLAYER_W / 2 - bcx, "dy": (p.y + PLAYER_H) - (b.y + BOSS_H), "pvx": pvx,
                "on_ground": p.on_ground, "px": p.x + PLAYER_W / 2, "boss_x": bcx,
                "half_w": self.level.w * TILE / 2}

    def _decide(self):
        """Percibir -> decidir (estrategia) -> actuar (iniciar el ataque). Se mide el costo de la decisión."""
        obs = self._observe()
        self.last_obs = obs
        t0 = time.perf_counter()
        attack, target = self.strategy.choose(obs)
        ms = (time.perf_counter() - t0) * 1000
        lo, hi = TILE * 2.5, self.level.w * TILE - TILE * 2.5
        self.boss.start(attack, max(lo, min(hi, target)), obs["px"])
        s = self._stats()
        s.attacks += 1
        s.mix[attack] += 1
        s.cpu_ms += ms
        self.cooldown = BOSS_COOLDOWN

    def _resolve_hits(self):
        p, b = self.player, self.boss
        prect = p.rect
        if any(_overlap(h, prect) for h in b.hitboxes()):
            if b.attack and not b.hit_this_attack:
                b.hit_this_attack = True
                self._stats().hits += 1
            if self.mode == "manual" and p.take_hit(b.center[0]):
                self.events.append(("hit_player", prect))
        elif self.mode == "manual" and _overlap(b.rect, prect) and p.take_hit(b.center[0]):
            self.events.append(("hit_player", prect))          # contacto con el cuerpo

        box = p.attack_box()
        if self.mode == "manual" and box and "boss" not in p.attack_hit and _overlap(box, b.rect):
            p.attack_hit.add("boss")
            p.soul = min(99, p.soul + SOUL_PER_HIT)
            b.hp -= 1
            b.flash = 0.12
            self.events.append(("hit_enemy", b.rect))
            if b.hp <= 0:
                b.dead_t = 0.0
                b.state, b.attack = "idle", None
                self.events.append(("enemy_dead", b.rect))


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
