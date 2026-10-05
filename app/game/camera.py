"""Cámara que sigue a un objetivo con suavizado, mirada adelantada y temblor."""
import random

from .config import SCREEN_H, SCREEN_W


class Camera:
    def __init__(self, world_w, world_h):
        self.world_w, self.world_h = world_w, world_h
        self.x = self.y = 0.0
        self._shake = 0.0
        self.ox = self.oy = 0.0

    def _target(self, tx, ty, lead):
        x = tx - SCREEN_W / 2 + lead
        y = ty - SCREEN_H * 0.58
        return (min(max(0, x), self.world_w - SCREEN_W), min(max(0, y), self.world_h - SCREEN_H))

    def snap(self, tx, ty):
        self.x, self.y = self._target(tx, ty, 0)

    def follow(self, tx, ty, dt, lead=0.0):
        gx, gy = self._target(tx, ty, lead)
        k = min(1.0, dt * 5.0)
        self.x += (gx - self.x) * k
        self.y += (gy - self.y) * k
        self._shake = max(0.0, self._shake - dt * 30)
        self.ox = random.uniform(-1, 1) * self._shake
        self.oy = random.uniform(-1, 1) * self._shake

    def shake(self, amount):
        self._shake = max(self._shake, amount)

    @property
    def view(self):
        """Esquina superior izquierda en píxeles enteros (con temblor)."""
        return int(self.x + self.ox), int(self.y + self.oy)
