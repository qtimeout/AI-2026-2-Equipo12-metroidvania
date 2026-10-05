"""Carga de recursos generados por tools/build_assets.py (app/assets/manifest.json)."""
import json
import os

import pygame

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONT_PATH = None          # None = fuente por defecto de pygame; reemplazar por un .ttf en assets/ si se agrega


class Anim:
    def __init__(self, frames, fps, loop, faces=-1):
        self.faces = faces          # hacia dónde mira el sprite original (-1 izquierda, 1 derecha)
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self._flipped = [pygame.transform.flip(f, True, False) for f in frames]

    def __len__(self):
        return len(self.frames)

    def flip_for(self, facing):
        return facing != self.faces

    def frame(self, t, flip=False):
        i = int(t * self.fps)
        i = i % len(self.frames) if self.loop else min(i, len(self.frames) - 1)
        return (self._flipped if flip else self.frames)[i]

    def at(self, i, flip=False):
        i = max(0, min(i, len(self.frames) - 1))
        return (self._flipped if flip else self.frames)[i]


class Assets:
    def __init__(self):
        path = os.path.join(ASSET_DIR, "manifest.json")
        if not os.path.exists(path):
            raise SystemExit("Faltan los assets: ejecuta `python tools/build_assets.py` desde la raíz del proyecto.")
        with open(path) as f:
            m = json.load(f)
        self.anims = {k: Anim([self._load(n) for n in v["frames"]], v["fps"], v["loop"], v.get("faces", -1)) for k, v in m["anims"].items()}
        self.images = {k: self._load(v) for k, v in m["images"].items()}
        self.env = {k: [self._load(n) for n in v] for k, v in m["env"].items()}
        self._fonts = {}

    @staticmethod
    def _load(name):
        return pygame.image.load(os.path.join(ASSET_DIR, name)).convert_alpha()

    def font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(FONT_PATH, size)
        return self._fonts[size]


def tint(img, rgb, alpha=255):
    """Multiplica el color del sprite (para oscurecer y teñir capas lejanas)."""
    out = img.copy()
    out.fill((*rgb, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def blur(img, k=4):
    """Desenfoque barato: reducir y volver a ampliar."""
    w, h = img.get_size()
    small = pygame.transform.smoothscale(img, (max(1, w // k), max(1, h // k)))
    return pygame.transform.smoothscale(small, (w, h))


def scale(img, f):
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (max(1, int(w * f)), max(1, int(h * f))))


def edge_fade(img, margin=0.22):
    """Desvanece los bordes del sprite: oculta cortes rectos de piezas recortadas del escenario."""
    w, h = img.get_size()
    sw, sh = 32, 32
    small = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for y in range(sh):
        for x in range(sw):
            fx = min(x + 0.5, sw - x - 0.5) / (sw * margin)
            fy = min(y + 0.5, sh - y - 0.5) / (sh * margin)
            a = max(0.0, min(1.0, fx)) * max(0.0, min(1.0, fy))
            small.set_at((x, y), (255, 255, 255, int(255 * a)))
    out = img.copy()
    out.blit(pygame.transform.smoothscale(small, (w, h)), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def whiten(img):
    """Silueta blanca con el mismo alfa (destello al recibir daño)."""
    out = img.copy()
    out.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
    return out
