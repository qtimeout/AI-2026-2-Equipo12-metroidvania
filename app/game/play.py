"""Escena de juego: un nivel con el Knight, los Husks controlados por la técnica de IA elegida y la tabla.

mode="manual" -> partida (combate real).  mode="auto" -> laboratorio de comparación con objetivos sembrados.
Al tocar la salida 'X' se pasa al nivel siguiente conservando vida y alma.
En el nivel del jefe (Level.boss) el mundo es un BossWorld: la IA elige el ataque de Hornet.
"""
import pygame

from .background import Backdrop
from .boss import BossWorld
from .boss_render import BossRenderer
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
    def __init__(self, app, mode, level_n=None, carry=None):
        self.app = app
        self.level = Level(level_n or app.level)
        self.graph = NavGraph(self.level)
        if self.level.boss:
            self.world = BossWorld(self.level, mode=mode, seed=SEED, strategy=app.boss_strategy)
            self.boss_renderer = BossRenderer(app.assets)
        else:
            self.world = World(self.level, self.graph, mode=mode, seed=SEED, selection=app.technique)
            self.boss_renderer = None
        wpx, hpx = self.level.w * TILE, self.level.h * TILE
        if carry:                                    # vida y alma que trae el jugador del nivel anterior
            self.world.player.hp, self.world.player.soul = carry
        self.backdrop = Backdrop(app.assets, wpx, hpx, self.level.theme, self.level.palette)
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

    def _next_scene(self):
        p = self.world.player
        if self.level.has_next and not getattr(self.world, "won", False):
            return PlayScene(self.app, "manual", self.level.n + 1, carry=(p.hp, p.soul))
        return EndScene(self.app, victory=getattr(self.world, "won", False))

    def _focus(self):
        if self.boss_renderer and self.world.mode == "auto":
            x, y, w, h = self.world.boss.rect
        elif self.world.mode == "auto":
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
                w.set_selection(self.app.boss_strategy if self.boss_renderer else self.app.technique)
            self.camera.snap(*self._focus())
        elif ev.key == pygame.K_m:
            self.hud.show_table = not self.hud.show_table
        elif ev.key == pygame.K_r:
            w.reset_metrics()
        elif ev.key == pygame.K_g:
            self.renderer.show_graph = not self.renderer.show_graph
        elif ev.key == pygame.K_f:
            self.speed_i = (self.speed_i + 1) % len(SPEEDS)
        elif self.boss_renderer and pygame.K_1 <= ev.key <= pygame.K_9 and w.mode == "manual":
            i = ev.key - pygame.K_1                      # en la arena, 1..4 eligen la estrategia del jefe
            if i < len(w.names):
                self.app.boss_strategy = w.names[i]
                w.set_selection(w.names[i])
        elif ev.key == pygame.K_0 and w.mode == "manual" and not self.boss_renderer:
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
        if self.world.finished and not self.leaving:
            self.leaving = [self._next_scene, 0.0]

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
        if self.boss_renderer:
            self.boss_renderer.draw(screen, self.world, (cx, cy), self.t)
        self.backdrop.draw_front(screen, cx, cy, self.t)

        w = self.world
        if self.boss_renderer:
            self._draw_boss_hud(screen, w)
        elif w.mode == "manual":
            self.hud.draw_vitals(screen, w.player, self.t)
            self.hud.draw_badge(screen, f"Enemigos: {w.selection}   (1-{len(w.names)} técnica · 0 mixto)")
            if self.hud.show_table:
                self.hud.draw_table(screen, w)
            self.hud.draw_hint(screen, "Mover: flechas/A-D · Saltar: Espacio/Z · Atacar: X · Curar: C · "
                                       "M tabla · G grafo · TAB laboratorio · ESC menú")
            alpha = int(255 * max(0.0, min(1.0, (self.t - 0.6) / 0.8, (5.0 - self.t) / 1.0)))
            self.hud.draw_area_title(screen, self.level.name, f"Nivel {self.level.n}", alpha)
        else:
            self.hud.draw_badge(screen, f"LABORATORIO IA · Nivel {self.level.n}  x{SPEEDS[self.speed_i]}   ·   TAB volver a la partida")
            self.hud.draw_table(screen, w, big=True)
            self.hud.draw_pairwise(screen, w)
            self.hud.draw_validation(screen)

        fade = self.fade if not self.leaving else min(1.0, self.leaving[1] / 0.5)
        if fade > 0:
            self.shade.fill((0, 0, 0, int(255 * fade)))
            screen.blit(self.shade, (0, 0))

    def _draw_boss_hud(self, screen, w):
        br = self.boss_renderer
        n = len(w.names)
        if w.mode == "manual":
            self.hud.draw_vitals(screen, w.player, self.t)
            self.hud.draw_badge(screen, f"Hornet: {w.selection}   (1-{n} estrategia)")
            if self.hud.show_table:
                br.draw_table(screen, w)
            br.draw_bar(screen, w)
            self.hud.draw_hint(screen, "Mover: flechas/A-D · Saltar: Espacio/Z · Atacar: X · Curar: C · "
                                       "M tabla · TAB laboratorio · ESC menú")
            alpha = int(255 * max(0.0, min(1.0, (self.t - 0.6) / 0.8, (5.0 - self.t) / 1.0)))
            self.hud.draw_area_title(screen, self.level.name, "Jefe final", alpha)
        else:
            self.hud.draw_badge(screen, f"LABORATORIO DEL JEFE  x{SPEEDS[self.speed_i]}   ·   TAB volver a la partida")
            br.draw_table(screen, w, big=True)


class EndScene:
    """Pantalla al salir del último nivel disponible."""

    def __init__(self, app, victory=False):
        self.app = app
        self.victory = victory
        self.t = 0.0
        self.f_big, self.f_small = app.assets.font(64), app.assets.font(26)
        self.shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and self.t > 1.0:
            self.t = 99.0

    def update(self, dt):
        self.t += dt
        if self.t > 8.0:
            from .menu import MenuScene
            return MenuScene(self.app)
        return None

    def draw(self, screen):
        screen.fill((4, 6, 12))
        a = int(255 * max(0.0, min(1.0, self.t / 1.2)))
        title, sub = (("HORNET HA SIDO DERROTADA", "Has completado Paso Olvidado — gracias por jugar")
                      if self.victory else ("FIN DEL RECORRIDO", "Gracias por jugar"))
        for text, font, y, color in ((title, self.f_big, SCREEN_H * 0.38, (238, 240, 248)),
                                     (sub, self.f_small, SCREEN_H * 0.52, (150, 158, 182)),
                                     ("Pulsa una tecla para volver al menú", self.f_small, SCREEN_H * 0.62, (110, 116, 140))):
            img = font.render(text, True, color)
            img.set_alpha(a)
            screen.blit(img, (SCREEN_W / 2 - img.get_width() / 2, y))
