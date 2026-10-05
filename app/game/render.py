"""Dibujo del mundo con pygame. Solo LEE el estado de World; nunca lo modifica."""
import random

import pygame

from .assets import edge_fade, scale, tint, whiten
from .config import ATTACK_TIME, PLAYER_W, TILE

ROCK_BASE = (5, 7, 13)
NODE = (90, 110, 160)
# color por técnica: etiquetas sobre los enemigos y rutas planificadas (tecla G)
TECH_COLORS = {"Aleatorio (base)": (170, 175, 190), "Reflejo": (130, 220, 150), "BFS": (110, 170, 255),
               "A*": (245, 200, 90)}
SHORT = {"Aleatorio (base)": "Base: aleatorio"}     # etiqueta sobre el enemigo (técnica, no tipo)


class WorldRenderer:
    def __init__(self, assets, level, graph, seed=11):
        self.a, self.level, self.graph = assets, level, graph
        self.terrain = self._build_terrain(random.Random(seed))
        self.show_graph = False
        self.fx = []                     # (anim_surface, x, y, ttl, max_ttl)
        self.sparks = []                 # partículas de impacto [x, y, vx, vy, ttl]
        self.flash = {}                  # caché de siluetas blancas
        self.slash = scale(assets.anims["slash"].frames[0], 0.85)
        self.slash_flip = pygame.transform.flip(self.slash, True, False)
        self.hit_img = assets.anims["hit_fx"].frames[0]
        self._pstate, self._pt = None, 0.0
        self.font = assets.font(20)
        self._tags = {}

    # ---------- terreno precalculado ----------
    def _build_terrain(self, rng):
        lv = self.level
        surf = pygame.Surface((lv.w * TILE, lv.h * TILE), pygame.SRCALPHA)
        rocks = [edge_fade(img, 0.12) for img in self.a.env["rock"]]
        floors = self.a.env["floor"]
        boundary = []
        for r in range(lv.h):
            for c in range(lv.w):
                if lv.solid(c, r):
                    open_dirs = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if not lv.solid(c + dx, r + dy)]
                    if open_dirs:
                        boundary.append((c, r, open_dirs))
                    else:
                        surf.fill(ROCK_BASE, (c * TILE - 2, r * TILE - 2, TILE + 4, TILE + 4))
        rng.shuffle(boundary)
        # pasada 1: siluetas oscuras que rellenan las celdas de borde con contorno orgánico
        # pasada 2: rocas con detalle encima
        dark = [tint(img, (14, 18, 30), 255) for img in rocks]
        for pieces, size_range, inset in ((dark, (1.5, 1.9), 0.3), (rocks, (1.2, 1.7), 0.22)):
            for c, r, open_dirs in boundary:
                img = rng.choice(pieces)
                size = TILE * rng.uniform(*size_range)
                img = scale(img, size / max(img.get_size()))
                if rng.random() < 0.5:
                    img = pygame.transform.flip(img, True, False)
                # el centro se mete hacia dentro de la roca para no invadir el espacio jugable
                ox = -sum(dx for dx, _ in open_dirs) * TILE * inset
                oy = -sum(dy for _, dy in open_dirs) * TILE * inset
                cx, cy = c * TILE + TILE / 2 + ox, r * TILE + TILE / 2 + oy
                surf.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))
        # bordes de suelo: tramos horizontales con aire encima
        for r in range(lv.h):
            c = 0
            while c < lv.w:
                if lv.solid(c, r) and not lv.solid(c, r - 1):
                    c0 = c
                    while c < lv.w and lv.solid(c, r) and not lv.solid(c, r - 1):
                        c += 1
                    w = (c - c0) * TILE + 18
                    img = edge_fade(pygame.transform.smoothscale(rng.choice(floors), (w, 30)), 0.05)
                    surf.blit(img, (c0 * TILE - 9, r * TILE - 9))
                else:
                    c += 1
        return surf

    # ---------- por frame ----------
    def consume_events(self, world, camera):
        for kind, rect in world.events:
            x, y, w, h = rect
            cx, cy = x + w / 2, y + h / 2
            if kind == "hit_enemy":
                self._burst(cx, cy, 1.0, 12)
                camera.shake(5)
            elif kind == "enemy_dead":
                self._burst(cx, cy, 1.6, 26)
                camera.shake(9)
            elif kind == "hit_player":
                self._burst(cx, cy, 1.3, 18)
                camera.shake(12)
        world.events.clear()

    def _burst(self, x, y, size, n):
        img = scale(self.hit_img, size * random.uniform(0.8, 1.2))
        img = pygame.transform.rotate(img, random.uniform(0, 360))
        self.fx.append([img, x, y, 0.16, 0.16])
        for _ in range(n):
            ang = random.uniform(0, 6.283)
            sp = random.uniform(150, 520) * size
            self.sparks.append([x, y, sp * pygame.math.Vector2(1, 0).rotate_rad(ang).x,
                                sp * pygame.math.Vector2(1, 0).rotate_rad(ang).y, random.uniform(0.2, 0.45)])

    def update_fx(self, dt):
        for f in self.fx:
            f[3] -= dt
        self.fx = [f for f in self.fx if f[3] > 0]
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 900 * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]

    def draw(self, screen, world, view, t, dt):
        vx, vy = view
        sw, sh = screen.get_size()
        screen.blit(self.terrain, (0, 0), (vx, vy, sw, sh))
        if self.show_graph:
            self._draw_graph(screen, world, vx, vy)
        for slot in world.slots:
            self._draw_enemy(screen, slot.enemy, vx, vy, t)
        self._draw_player(screen, world, vx, vy, dt)
        if world.mode == "manual":
            for slot in world.slots:
                if slot.enemy.alive:
                    self._draw_tag(screen, slot, vx, vy)
        for img, x, y, ttl, mx in self.fx:
            img.set_alpha(int(255 * ttl / mx))
            screen.blit(img, (x - vx - img.get_width() / 2, y - vy - img.get_height() / 2))
        for x, y, _, _, ttl in self.sparks:
            pygame.draw.circle(screen, (235, 240, 255), (x - vx, y - vy), max(1, int(ttl * 8)))

    def _sprite(self, img, flash):
        if not flash:
            return img
        key = id(img)
        if key not in self.flash:
            self.flash[key] = whiten(img)
        return self.flash[key]

    def _blit_feet(self, screen, img, rect, vx, vy):
        x, y, w, h = rect
        screen.blit(img, (x + w / 2 - img.get_width() / 2 - vx, y + h - img.get_height() + 4 - vy))

    def _draw_player(self, screen, world, vx, vy, dt):
        p, A = world.player, self.a.anims
        if p.hurt_t > 0:
            state = "knight_hurt"
        elif p.attacking:
            state = "knight_attack"
        elif not p.on_ground:
            state = "knight_jump" if p.vy < 0 else "knight_fall"
        elif abs(p.vx) > 1:
            state = "knight_run"
        else:
            state = "knight_idle"
        if state != self._pstate:
            self._pstate, self._pt = state, 0.0
        self._pt += dt
        t = p.attack_t if state == "knight_attack" else self._pt
        img = A[state].frame(t, flip=A[state].flip_for(p.facing))
        if p.invuln > 0 and int(p.invuln * 14) % 2 == 0:
            img = self._sprite(img, True) if p.hurt_t > 0 else None
        if img is not None:
            self._blit_feet(screen, img, p.rect, vx, vy)
        if p.attacking and p.attack_t < ATTACK_TIME * 0.6:
            s = self.slash_flip if p.facing > 0 else self.slash
            s.set_alpha(int(255 * (1 - p.attack_t / (ATTACK_TIME * 0.6))))
            cx = p.x + PLAYER_W / 2 + p.facing * 62
            screen.blit(s, (cx - s.get_width() / 2 - vx, p.y + 26 - s.get_height() / 2 - vy))

    def _draw_enemy(self, screen, e, vx, vy, t):
        A, k = self.a.anims, e.anim
        if not e.alive:
            anim = A[k + "_death"]
            img = anim.frame(e.dead_t, anim.flip_for(e.facing))
            img.set_alpha(max(0, int(255 * (1 - e.dead_t / 1.2))))
        else:
            if e.stun > 0 and e.flash > 0:
                anim, i = A[k + "_hurt"], 0
            elif e.edge is None:
                anim, i = A[k + "_idle"], int(t * A[k + "_idle"].fps)
            elif e.edge.kind == "walk":
                anim, i = A[k + "_walk"], int(t * A[k + "_walk"].fps)
            else:
                anim, i = A[k + "_leap"], int(e.phase * len(A[k + "_leap"]))
            if anim.loop:
                i %= len(anim)
            img = anim.at(i, anim.flip_for(e.facing))
            img.set_alpha(255)
        self._blit_feet(screen, self._sprite(img, e.flash > 0), e.rect, vx, vy)

    def _draw_tag(self, screen, slot, vx, vy):
        """Etiqueta con la técnica que controla a cada enemigo (clave en el modo mixto)."""
        name = slot.technique
        if name not in self._tags:
            color = TECH_COLORS.get(name, (230, 230, 240))
            txt = self.font.render(SHORT.get(name, name), True, color)
            bg = pygame.Surface((txt.get_width() + 12, txt.get_height() + 4), pygame.SRCALPHA)
            bg.fill((5, 8, 16, 170))
            bg.blit(txt, (6, 2))
            self._tags[name] = bg
        tag = self._tags[name]
        x, y, w, _ = slot.enemy.rect
        screen.blit(tag, (x + w / 2 - tag.get_width() / 2 - vx, y - 46 - vy))

    def _draw_graph(self, screen, world, vx, vy):
        half = TILE // 2
        for n, edges in self.graph.edges.items():
            a = (n[0] * TILE + half - vx, n[1] * TILE + half - vy)
            for ed in edges:
                b = (ed.target[0] * TILE + half - vx, ed.target[1] * TILE + half - vy)
                pygame.draw.line(screen, NODE, a, b, 1)
            pygame.draw.circle(screen, NODE, a, 3)
        for slot in world.slots:
            cells = list(slot.enemy.cells) + list(slot.agent.debug_path())
            if len(cells) > 1:
                pts = [(c * TILE + half - vx, r * TILE + half - vy) for c, r in cells]
                pygame.draw.lines(screen, TECH_COLORS.get(slot.technique, (235, 170, 80)), False, pts, 3)
        gc, gr = world.goal
        pygame.draw.rect(screen, (235, 235, 245), (gc * TILE + 4 - vx, gr * TILE + 4 - vy, TILE - 8, TILE - 8), 2)
