"""Menú principal: fondo del bosque con haces de luz, logo, opciones y cursor de flor animado."""
import math
import random
import sys

import pygame

from .assets import tint
from .background import additive
from .config import SCREEN_H, SCREEN_W

WEB = sys.platform == "emscripten"


class MenuScene:
    def __init__(self, app):
        self.app = app
        a = app.assets
        bg = a.images["menu_bg"]
        k = max(SCREEN_W / bg.get_width(), (SCREEN_H + 80) / bg.get_height())
        self.bg = pygame.transform.smoothscale(bg, (int(bg.get_width() * k), int(bg.get_height() * k)))
        self.title = a.images["title"]
        self.pointer = [a.images[f"pointer_{i:02d}"] for i in range(11)]
        self.pointer_r = [pygame.transform.flip(p, True, False) for p in self.pointer]
        beam = a.images["beam"]
        rng = random.Random(3)
        self.beams = [(additive(pygame.transform.smoothscale(beam, (rng.randint(180, 340), SCREEN_H + 200)),
                                (170, 200, 240), rng.uniform(0.3, 0.55)), rng.uniform(0, SCREEN_W), rng.uniform(0, 6.28))
                      for _ in range(5)]
        soft = a.images["soft"]
        self.mote = additive(pygame.transform.smoothscale(soft, (10, 10)), (200, 220, 255), 0.9)
        self.motes = [(rng.uniform(0, SCREEN_W), rng.uniform(0, SCREEN_H), rng.uniform(8, 25), rng.uniform(0, 6.28))
                      for _ in range(45)]
        self.shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self.f_item, self.f_small = a.font(36), a.font(20)
        self.sel = 0
        self.sel_t = 0.0
        self.t = 0.0
        self.fade_in = 1.0
        self.leaving = None          # (siguiente escena, tiempo de fundido)

    @property
    def items(self):
        tech = self.app.technique
        items = [("Comenzar partida", "play"), ("Laboratorio IA", "lab"), (f"Enemigos: {tech}", "tech")]
        if not WEB:
            items.append(("Salir", "quit"))
        return items

    def handle(self, ev):
        if ev.type != pygame.KEYDOWN or self.leaving:
            return
        n = len(self.items)
        if ev.key in (pygame.K_UP, pygame.K_w):
            self.sel, self.sel_t = (self.sel - 1) % n, 0.0
        elif ev.key in (pygame.K_DOWN, pygame.K_s):
            self.sel, self.sel_t = (self.sel + 1) % n, 0.0
        elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d) and self.items[self.sel][1] == "tech":
            self.app.cycle_technique(1 if ev.key in (pygame.K_RIGHT, pygame.K_d) else -1)
        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            action = self.items[self.sel][1]
            if action == "tech":
                self.app.cycle_technique(1)
            elif action == "quit":
                self.app.running = False
            else:
                from .play import PlayScene
                self.leaving = [lambda: PlayScene(self.app, "manual" if action == "play" else "auto"), 0.0]

    def update(self, dt):
        self.t += dt
        self.sel_t += dt
        self.fade_in = max(0.0, self.fade_in - dt / 1.2)
        if self.leaving:
            self.leaving[1] += dt
            if self.leaving[1] >= 0.6:
                return self.leaving[0]()
        return None

    def draw(self, screen):
        t = self.t
        oy = -40 + math.sin(t * 0.15) * 40
        screen.blit(self.bg, ((SCREEN_W - self.bg.get_width()) / 2, oy))
        for img, x, ph in self.beams:
            screen.blit(img, (x + math.sin(t * 0.25 + ph) * 40 - img.get_width() / 2, -120),
                        special_flags=pygame.BLEND_RGB_ADD)
        for x, y, sp, ph in self.motes:
            px = (x + math.sin(t * 0.5 + ph) * 25) % SCREEN_W
            py = (y - t * sp) % SCREEN_H
            screen.blit(self.mote, (px, py), special_flags=pygame.BLEND_RGB_ADD)
        self.shade.fill((0, 0, 0, 110))
        screen.blit(self.shade, (0, 0))

        tx = SCREEN_W / 2 - self.title.get_width() / 2
        screen.blit(self.title, (tx, 60 + math.sin(t * 0.8) * 4))

        base_y = 410
        for i, (label, _) in enumerate(self.items):
            selected = i == self.sel
            img = self.f_item.render(label, True, (245, 245, 250) if selected else (150, 156, 175))
            x, y = SCREEN_W / 2 - img.get_width() / 2, base_y + i * 58
            screen.blit(img, (x, y))
            if selected:
                k = min(10, int(self.sel_t / 0.035))
                pl, pr = self.pointer[k], self.pointer_r[k]
                cy = y + img.get_height() / 2 - pl.get_height() / 2
                screen.blit(pr, (x - pl.get_width() - 16, cy))
                screen.blit(pl, (x + img.get_width() + 16, cy))

        hint = "Flechas: elegir · Enter: aceptar · Izq/Der en «Enemigos» elige la IA de todos los enemigos"
        foot = "Agentes Inteligentes · USIL 2026 — proyecto académico. Arte: Hollow Knight © Team Cherry"
        for txt, y in ((hint, SCREEN_H - 58), (foot, SCREEN_H - 32)):
            img = self.f_small.render(txt, True, (130, 136, 158))
            screen.blit(img, (SCREEN_W / 2 - img.get_width() / 2, y))

        fade = self.fade_in if not self.leaving else min(1.0, self.leaving[1] / 0.6)
        if fade > 0:
            self.shade.fill((0, 0, 0, int(255 * fade)))
            screen.blit(self.shade, (0, 0))
