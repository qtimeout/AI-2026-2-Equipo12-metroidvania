"""Escena de juego: nivel 1 con el Knight, el Husk controlado por la técnica de IA elegida y la tabla.

mode="manual" -> partida (combate real).  mode="auto" -> laboratorio de comparación con objetivos sembrados.
"""
import pygame

from .background import Backdrop
from .camera import Camera
from .config import DT, SCREEN_H, SCREEN_W, SEED, TILE
from .hud import Hud
from .level import Level
from .navgraph import NavGraph
from .render import WorldRenderer
from .world import MIX, World

SPEEDS = [1, 5, 20]
JUMP_KEYS = (pygame.K_SPACE, pygame.K_z, pygame.K_w, pygame.K_UP)
ATTACK_KEYS = (pygame.K_x, pygame.K_j)
HEAL_KEYS = (pygame.K_c, pygame.K_k)


class PlayScene:
    def __init__(self, app, mode):
        self.app = app
        self.level = Level()
        self.graph = NavGraph(self.level)
        self.world = World(self.level, self.graph, mode=mode, seed=SEED, selection=app.technique)
        wpx, hpx = self.level.w * TILE, self.level.h * TILE
        self.backdrop = Backdrop(app.assets, wpx, hpx)
        self.renderer = WorldRenderer(app.assets, self.level, self.graph)
        self.hud = Hud(app.assets)
        self.camera = Camera(wpx, hpx)
        self.camera.snap(*self._focus())
        self.acc = 0.0
        self.t = 0.0
        self.frame_dt = 1 / 60
        self.speed_i = 0
        self.jump_pressed = self.attack_pressed = self.heal_pressed = False
        self.leaving = None
        self.fade = 1.0
        self.shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

    def _focus(self):
        if self.world.mode == "auto":
            x, y, w, h = self.world.enemy.rect
        else:
            x, y, w, h = self.world.player.rect
        return x + w / 2, y + h / 2

    def handle(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        w = self.world
        if ev.key in JUMP_KEYS:
            self.jump_pressed = True
        elif ev.key in ATTACK_KEYS:
            self.attack_pressed = True
        elif ev.key in HEAL_KEYS:
            self.heal_pressed = True
        elif ev.key == pygame.K_ESCAPE and not self.leaving:
            from .menu import MenuScene
            self.leaving = [lambda: MenuScene(self.app), 0.0]
        elif ev.key == pygame.K_TAB:
            w.set_mode("auto" if w.mode == "manual" else "manual")
            if w.mode == "manual":
                w.set_selection(self.app.technique)
            self.camera.snap(*self._focus())
        elif ev.key == pygame.K_m:
            self.hud.show_table = not self.hud.show_table
        elif ev.key == pygame.K_r:
            w.reset_metrics()
        elif ev.key == pygame.K_g:
            self.renderer.show_graph = not self.renderer.show_graph
        elif ev.key == pygame.K_f:
            self.speed_i = (self.speed_i + 1) % len(SPEEDS)
        elif ev.key == pygame.K_0 and w.mode == "manual":
            self.app.technique = MIX
            w.set_selection(MIX)
        elif pygame.K_1 <= ev.key <= pygame.K_9 and w.mode == "manual":
            i = ev.key - pygame.K_1
            if i < len(w.names):
                self.app.technique = w.names[i]
                w.set_selection(w.names[i])

    def update(self, frame_dt):
        self.t += frame_dt
        self.frame_dt = frame_dt
        self.fade = max(0.0, self.fade - frame_dt / 1.0)
        if self.leaving:
            self.leaving[1] += frame_dt
            if self.leaving[1] >= 0.5:
                return self.leaving[0]()

        keys = pygame.key.get_pressed()
        move = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        jump_held = any(keys[k] for k in JUMP_KEYS)
        speed = SPEEDS[self.speed_i] if self.world.mode == "auto" else 1

        # Simulación con paso fijo DT, desacoplada del framerate real
        self.acc += min(frame_dt, 0.1)
        while self.acc >= DT:
            for _ in range(speed):
                self.world.update(DT, (move, self.jump_pressed, jump_held, self.attack_pressed, self.heal_pressed))
                self.jump_pressed = self.attack_pressed = self.heal_pressed = False
            self.acc -= DT

        self.renderer.consume_events(self.world, self.camera)
        self.renderer.update_fx(frame_dt)
        self.hud.update(frame_dt, self.world)
        fx, fy = self._focus()
        lead = self.world.player.facing * 90 if self.world.mode == "manual" else 0
        self.camera.follow(fx, fy, frame_dt, lead)
        return None

    def draw(self, screen):
        cx, cy = self.camera.view
        self.backdrop.draw_back(screen, cx, cy, self.t)
        self.renderer.draw(screen, self.world, (cx, cy), self.t, self.frame_dt)
        self.backdrop.draw_front(screen, cx, cy, self.t)

        w = self.world
        if w.mode == "manual":
            self.hud.draw_vitals(screen, w.player, self.t)
            self.hud.draw_badge(screen, f"Enemigos: {w.selection}   (1-{len(w.names)} técnica · 0 mixto)")
            if self.hud.show_table:
                self.hud.draw_table(screen, w)
            self.hud.draw_hint(screen, "Mover: flechas/A-D · Saltar: Espacio/Z · Atacar: X · Curar: C · "
                                       "M tabla · G grafo · TAB laboratorio · ESC menú")
            alpha = int(255 * max(0.0, min(1.0, (self.t - 0.6) / 0.8, (5.0 - self.t) / 1.0)))
            self.hud.draw_area_title(screen, "PASO OLVIDADO", "Nivel 1", alpha)
        else:
            self.hud.draw_badge(screen, f"LABORATORIO IA  x{SPEEDS[self.speed_i]}   ·   TAB volver a la partida")
            self.hud.draw_table(screen, w, big=True)
            self.hud.draw_pairwise(screen, w)

        fade = self.fade if not self.leaving else min(1.0, self.leaving[1] / 0.5)
        if fade > 0:
            self.shade.fill((0, 0, 0, int(255 * fade)))
            screen.blit(self.shade, (0, 0))
