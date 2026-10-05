"""Simulación pura (sin pygame): física, combate, ciclo percibir-decidir-actuar y métricas.

Modos:
  manual -> partida: el humano controla al Knight y pelea contra TODOS los enemigos del nivel.
            Cada enemigo tiene su propio agente; la asignación sale del menú: una técnica para
            todos, o MIX = una técnica al azar por enemigo. Un episodio de un enemigo termina
            cuando alcanza al jugador (éxito), muere o se agota el tiempo.
  auto   -> laboratorio reproducible: UN Husk saltador desde el spawn 'E'; el jugador queda quieto
            en un objetivo sembrado y las técnicas se turnan sobre la misma secuencia (comparación justa).
"""
import random

from .agents import build_agents
from .config import (AI_BUDGET, ENEMY_RECOVER, ENEMY_RESPAWN, ENEMY_STUN, EPISODE_TIMEOUT,
                     MIN_TARGET_DIST, SEED, SOUL_PER_HIT)
from .enemy import Enemy
from .metrics import Metrics
from .player import Player
from .scheduler import AIScheduler

MIX = "Aleatorio (mixto)"      # selección del menú: cada enemigo recibe una técnica al azar


class Slot:
    """Un enemigo con su propio agente, scheduler y reloj de episodio."""

    def __init__(self, spawn, kind, technique, agent, budget):
        self.spawn, self.kind = spawn, kind
        self.technique, self.agent = technique, agent
        self.scheduler = AIScheduler(budget)
        self.enemy = Enemy(spawn, kind)
        self.t = 0.0

    def new_episode(self):
        self.scheduler.cancel()
        self.agent.reset()
        self.enemy.steps = 0
        self.t = 0.0


class World:
    def __init__(self, level, graph, mode="manual", seed=SEED, budget=AI_BUDGET, selection=None):
        self.level, self.graph = level, graph
        self.seed, self.budget = seed, budget
        self.lab_agents = build_agents(seed)          # laboratorio: una instancia por técnica, persistente
        self.names = list(self.lab_agents)
        self.selection = selection or self.names[0]    # técnica elegida en el menú, o MIX
        self.metrics = {"manual": Metrics(self.names), "auto": Metrics(self.names)}
        self.mode = mode
        self.rng = random.Random(seed)
        self.events = []          # eventos visuales para el render (golpes, muertes); no afectan la lógica
        self._build_targets()
        self.auto_episode = 0
        self.reset_episode()

    # ---------- configuración ----------
    def _build_targets(self):
        """Secuencia sembrada de objetivos alcanzables, igual para todas las técnicas."""
        spawn = self.level.enemy_spawn
        reach = self.graph.reachable_from(spawn)
        far = sorted(n for n in reach if abs(n[0] - spawn[0]) + abs(n[1] - spawn[1]) >= MIN_TARGET_DIST)
        rng = random.Random(self.seed)
        self.targets = [rng.choice(far) for _ in range(1000)]

    def _make_agent(self, name, i):
        """Instancia propia por enemigo (los agentes guardan estado: ruta, generador aleatorio)."""
        return build_agents(self.seed + i)[name]

    def set_mode(self, mode):
        self.mode = mode
        self.auto_episode = 0
        self.reset_episode()

    def set_selection(self, selection):
        """Técnica para todos los enemigos de la partida, o MIX."""
        if selection != self.selection:
            self.selection = selection
            if self.mode == "manual":
                self.reset_episode()

    def reset_metrics(self):
        self.metrics[self.mode] = Metrics(self.names)
        self.auto_episode = 0
        self.reset_episode()

    # compatibilidad: laboratorio y HUD usan "el" enemigo / "la" técnica en curso
    @property
    def enemy(self):
        return self.slots[0].enemy

    @property
    def technique(self):
        return self.slots[0].technique if self.mode == "auto" else self.selection

    @property
    def t(self):
        return self.slots[0].t

    @property
    def active_techniques(self):
        return {s.technique for s in self.slots}

    # ---------- episodios ----------
    def reset_episode(self):
        """Reinicio completo: posiciones, vida, enemigos y agentes."""
        if self.mode == "auto":
            n = len(self.names)
            name = self.names[self.auto_episode % n]
            self.goal = self.targets[(self.auto_episode // n) % len(self.targets)]
            self.player = Player(self.goal)
            self.slots = [Slot(self.level.enemy_spawn, "saltador", name, self.lab_agents[name], self.budget)]
        else:
            self.player = Player(self.level.player_spawn)
            self.goal = self.level.player_spawn
            self.slots = []
            spawns = self.level.enemy_spawns
            mix = self._mix_assignment(len(spawns)) if self.selection == MIX else None
            for i, (spawn, kind) in enumerate(spawns):
                name = mix[i] if mix else self.selection
                self.slots.append(Slot(spawn, kind, name, self._make_agent(name, i), self.budget))
        for s in self.slots:
            s.new_episode()

    def _mix_assignment(self, k):
        """Reparte las técnicas como una baraja: todas aparecen al menos una vez (si k >= nº de técnicas)
        y solo cambia, al azar, qué enemigo recibe cuál."""
        out = []
        while len(out) < k:
            bag = list(self.names)
            self.rng.shuffle(bag)
            out += bag
        return out[:k]

    def _end_episode(self, slot, reached):
        target = self.auto_episode // len(self.names) if self.mode == "auto" else None
        self.metrics[self.mode].record_episode(slot.technique, reached, slot.t, slot.enemy.steps, target)
        if self.mode == "auto":
            self.auto_episode += 1
            self.reset_episode()
        else:
            slot.new_episode()

    # ---------- paso de simulación ----------
    def update(self, dt, controls=None):
        if self.mode == "manual" and controls is not None:
            self._update_player(dt, controls)
            if self.player.hp <= 0:
                self.events.append(("player_dead", self.player.rect))
                self.reset_episode()
                return

        for slot in list(self.slots):
            e = slot.enemy
            if not e.alive:
                e.dead_t += dt
                if e.dead_t >= ENEMY_RESPAWN:
                    slot.enemy = Enemy(slot.spawn, slot.kind)
                    slot.new_episode()
                continue

            slot.t += dt
            self._update_enemy(slot, dt)

            if self.mode == "manual":
                self._resolve_combat(slot)
            elif _overlap(e.rect, self.player.rect):
                self._end_episode(slot, reached=True)
                return
            if slot.t >= EPISODE_TIMEOUT:
                self._end_episode(slot, reached=False)
                if self.mode == "auto":
                    return

    def _update_player(self, dt, controls):
        self.player.update(dt, self.level, *controls)
        node = self.graph.locate(*self.player.feet)
        if node is not None:
            self.goal = node                # percepción de los agentes: última celda pisada por el jugador

    def _update_enemy(self, slot, dt):
        """Ciclo del agente: percibir -> decidir (por porciones) -> actuar."""
        e = slot.enemy
        if e.edge is None and e.stun <= 0:
            if not slot.scheduler.pending:
                slot.scheduler.request(slot.agent, self.graph, e.node, self.goal)
            decision = slot.scheduler.step()
            if decision is not None:
                self.metrics[self.mode].record_decision(slot.technique, decision)
                if decision.edge is not None:
                    e.start_edge(decision.edge)
                else:
                    e.facing = 1 if self.player.x > e.rect[0] else -1
        else:
            e.update(dt)

    def _resolve_combat(self, slot):
        p, e = self.player, slot.enemy
        box = p.attack_box()
        key = id(slot)
        if box and key not in p.attack_hit and _overlap(box, e.rect):
            p.attack_hit.add(key)
            p.soul = min(99, p.soul + SOUL_PER_HIT)
            self.events.append(("hit_enemy", e.rect))
            if e.take_hit(ENEMY_STUN):
                e.dead_t = 0.0
                self.events.append(("enemy_dead", e.rect))
                self._end_episode(slot, reached=False)
                return
        if e.stun <= 0 and _overlap(e.rect, p.rect) and p.take_hit(e.rect[0] + e.rect[2] / 2):
            self.events.append(("hit_player", p.rect))
            e.stun = ENEMY_RECOVER
            self._end_episode(slot, reached=True)


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
