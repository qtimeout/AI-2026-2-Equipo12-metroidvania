"""Ambientación: cielo, capas de parallax, haces de luz, niebla, polvo flotante y viñeta.

Todo se precalcula al crear la escena (tintes, desenfoques, escalados); por frame solo se hacen blits.
"""
import math
import random

import pygame

from .assets import blur, edge_fade, scale, tint
from .config import SCREEN_H, SCREEN_W


def additive(img, rgb, intensity):
    """Versión premultiplicada sobre negro para blits aditivos (BLEND_ADD ignora el alfa)."""
    out = pygame.Surface(img.get_size())
    out.fill((0, 0, 0))
    out.blit(img, (0, 0))
    k = [int(c * intensity) for c in rgb]
    out.fill(k, special_flags=pygame.BLEND_RGB_MULT)
    return out


def vertical_gradient(w, h, top, bottom):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / (h - 1)
        surf.fill([int(a + (b - a) * t) for a, b in zip(top, bottom)], (0, y, w, 1))
    return surf


def vignette(w, h, strength=200):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    small = pygame.Surface((w // 8, h // 8), pygame.SRCALPHA)
    cx, cy = small.get_width() / 2, small.get_height() / 2
    for y in range(small.get_height()):
        for x in range(small.get_width()):
            d = math.hypot((x - cx) / cx, (y - cy) / cy)
            a = max(0.0, min(1.0, (d - 0.55) / 0.75))
            small.set_at((x, y), (0, 0, 0, int(strength * a * a)))
    return pygame.transform.smoothscale(small, (w, h), surf)


class Layer:
    def __init__(self, parallax, items):
        self.parallax = parallax
        self.items = items          # (surface, x, y) en coordenadas de capa

    def draw(self, screen, cam_x, cam_y):
        ox, oy = cam_x * self.parallax, cam_y * self.parallax
        for surf, x, y in self.items:
            sx, sy = x - ox, y - oy
            if sx < SCREEN_W and sx + surf.get_width() > 0 and sy < SCREEN_H and sy + surf.get_height() > 0:
                screen.blit(surf, (sx, sy))


class Backdrop:
    def __init__(self, assets, world_w, world_h, seed=7):
        rng = random.Random(seed)
        self.sky = vertical_gradient(SCREEN_W, SCREEN_H, (5, 8, 18), (20, 30, 52))
        bg, deco, rocks = assets.env["bg"], assets.env["deco"], assets.env["rock"]

        def spread(parallax, pieces, count, size, rgb, alpha, blur_k, y_band):
            span_w = world_w * parallax + SCREEN_W
            span_h = world_h * parallax + SCREEN_H
            items = []
            for i in range(count):
                img = scale(rng.choice(pieces), rng.uniform(*size))
                img = tint(edge_fade(img), rgb, alpha)
                if blur_k:
                    img = blur(img, blur_k)
                x = (i + rng.uniform(-0.3, 0.3)) * span_w / count - img.get_width() / 2
                y = span_h * rng.uniform(*y_band) - img.get_height()
                items.append((img, x, y))
            return items

        self.far = Layer(0.2, spread(0.2, bg, 16, (1.8, 2.8), (70, 95, 140), 90, 6, (0.55, 1.05)))
        self.mid = Layer(0.45, spread(0.45, bg, 20, (1.3, 2.0), (55, 72, 110), 170, 3, (0.6, 1.05)))
        self.near = Layer(0.75, spread(0.75, deco + bg[:3], 18, (1.1, 1.7), (30, 38, 60), 235, 2, (0.75, 1.05)))
        self.front = Layer(1.35, spread(1.35, rocks, 10, (2.6, 3.6), (4, 5, 9), 255, 3, (1.0, 1.25)))

        beam = assets.images["beam"]
        self.beams = []
        for i in range(7):
            w = rng.randint(140, 300)
            img = pygame.transform.smoothscale(beam, (w, SCREEN_H + 300))
            img = additive(img, (150, 180, 230), rng.uniform(0.35, 0.6))
            self.beams.append((img, rng.uniform(0, world_w * 0.4 + SCREEN_W), rng.uniform(0, math.tau)))

        fog = assets.images["fog"]
        self.fog_back = tint(pygame.transform.smoothscale(fog, (1600, 520)), (120, 145, 190), 80)
        self.fog_front = tint(pygame.transform.smoothscale(fog, (1900, 600)), (90, 110, 150), 55)

        soft = assets.images["soft"]
        # 5 tamaños x 4 intensidades (titileo sin set_alpha, que no aplica en blits aditivos)
        self.motes = [[additive(scale(soft, s / soft.get_width()), (190, 215, 255), k) for k in (0.25, 0.5, 0.75, 1.0)]
                      for s in (5, 7, 9, 12, 16)]
        self.particles = [(rng.uniform(0, SCREEN_W), rng.uniform(0, SCREEN_H), rng.randrange(5),
                           rng.uniform(6, 22), rng.uniform(0, math.tau), rng.uniform(0.6, 1.2)) for _ in range(70)]
        self.vignette = vignette(SCREEN_W, SCREEN_H)
        self.world_h = world_h

    def draw_back(self, screen, cam_x, cam_y, t):
        screen.blit(self.sky, (0, 0))
        self.far.draw(screen, cam_x, cam_y)
        for img, x, phase in self.beams:
            sx = x - cam_x * 0.4 + math.sin(t * 0.3 + phase) * 25
            if -img.get_width() < sx < SCREEN_W:
                screen.blit(img, (sx, -150 - cam_y * 0.2), special_flags=pygame.BLEND_RGB_ADD)
        self.mid.draw(screen, cam_x, cam_y)
        self._fog(screen, self.fog_back, cam_x * 0.5 + t * 12, SCREEN_H - 420 - (cam_y - self.world_h) * 0.3)
        self.near.draw(screen, cam_x, cam_y)

    def draw_front(self, screen, cam_x, cam_y, t):
        for i, (x, y, k, speed, phase, tw) in enumerate(self.particles):
            px = (x - cam_x * 0.9 + math.sin(t * 0.4 + phase) * 30) % (SCREEN_W + 40) - 20
            py = (y - cam_y * 0.9 - t * speed) % (SCREEN_H + 40) - 20
            level = int((math.sin(t * tw * 2 + phase) + 1) * 1.99)
            screen.blit(self.motes[k][level], (px, py), special_flags=pygame.BLEND_RGB_ADD)
        self._fog(screen, self.fog_front, cam_x * 1.2 + t * 25, SCREEN_H - 330 - (cam_y - self.world_h) * 0.5)
        self.front.draw(screen, cam_x, cam_y)
        screen.blit(self.vignette, (0, 0))

    @staticmethod
    def _fog(screen, img, offset, y):
        w = img.get_width()
        x = -(offset % w)
        while x < SCREEN_W:
            screen.blit(img, (x, y))
            x += w
