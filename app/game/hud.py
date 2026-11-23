"""HUD estilo Hollow Knight (orbe de alma + máscaras) y la tabla comparativa de técnicas en pantalla."""
import json
import os

import pygame

from .assets import scale
from .config import EPISODE_TIMEOUT, PLAYER_MAX_HP, SCREEN_H, SCREEN_W
from .metrics import HEADERS
from .ml.models import MODEL_DIR

TEXT = (232, 236, 245)
MUTED = (150, 158, 182)
GOLD = (240, 214, 150)
COLS = [190, 82, 92, 122, 112, 62, 90, 72]
SHORT = {"Aleatorio (base)": "Aleatorio"}


class Hud:
    def __init__(self, assets):
        self.a = assets
        self.orb = scale(assets.anims["soul_orb"].frames[0], 1.15)
        self.mask_full = scale(assets.anims["mask_full"].frames[0], 0.8)
        self.mask_empty = scale(assets.anims["mask_empty"].frames[0], 0.8)
        self.f_small, self.f_med, self.f_big, self.f_title = (assets.font(s) for s in (22, 26, 34, 74))
        self.show_table = True
        self._shown_hp = PLAYER_MAX_HP
        self.hit_flash = 0.0
        path = os.path.join(MODEL_DIR, "metrics.json")
        self.ml_report = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None

    def update(self, dt, world):
        self.hit_flash = max(0.0, self.hit_flash - dt * 2.5)

    # ---------- vida y alma ----------
    def draw_vitals(self, screen, player, t):
        ox, oy = 34, 26
        frac = player.soul / 99
        r = 30
        fill = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        pygame.draw.circle(fill, (235, 240, 255, 230), (r, r), r)
        cut = int(2 * r * (1 - frac))
        fill.fill((0, 0, 0, 0), (0, 0, 2 * r, cut))
        screen.blit(fill, (ox + self.orb.get_width() / 2 - r, oy + self.orb.get_height() / 2 - r + 4))
        screen.blit(self.orb, (ox, oy))
        x = ox + self.orb.get_width() + 6
        for i in range(PLAYER_MAX_HP):
            img = self.mask_full if i < player.hp else self.mask_empty
            screen.blit(img, (x + i * (self.mask_full.get_width() + 6), oy + 12))
        if player.heal_flash > 0:
            glow = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            glow.fill((255, 255, 255, int(70 * player.heal_flash)))
            screen.blit(glow, (0, 0))

    # ---------- tabla comparativa ----------
    def draw_table(self, screen, world, big=False):
        rows = world.metrics[world.mode].rows()
        w = sum(COLS) + 28
        h = 66 + 26 * len(rows) + (30 if big else 0)
        x = (SCREEN_W - w) // 2 if big else SCREEN_W - w - 18
        y = SCREEN_H - h - 18 if big else 18
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((6, 9, 18, 200))
        pygame.draw.rect(panel, (120, 135, 170, 120), panel.get_rect(), 1, border_radius=8)
        screen.blit(panel, (x, y))
        title = "Comparación de técnicas — " + ("partida con humano" if world.mode == "manual"
                                                else "laboratorio (objetivos sembrados)")
        screen.blit(self.f_med.render(title, True, GOLD), (x + 14, y + 10))
        self._row(screen, HEADERS, x + 14, y + 38, MUTED)
        for i, row in enumerate(rows):
            yy = y + 64 + 26 * i
            active = row[0] in world.active_techniques if world.mode == "manual" else row[0] == world.technique
            if active:
                hl = pygame.Surface((w - 16, 24), pygame.SRCALPHA)
                hl.fill((110, 130, 190, 60))
                screen.blit(hl, (x + 8, yy - 4))
            self._row(screen, row, x + 14, yy, TEXT)
        if big:
            p = world.params
            info = (f"En curso: {world.technique} · t {world.t:4.1f} s   |   +/- presupuesto {p['presupuesto']}   "
                    f"H peso A* {p['peso_h']:g}   N k={p['k']}   |   F vel.  R reinicia  G grafo")
            screen.blit(self.f_small.render(info, True, MUTED), (x + 14, y + h - 28))

    def draw_pairwise(self, screen, world):
        """Matriz por pares del laboratorio: % de objetivos compartidos en que la fila llega antes que la columna."""
        m = world.metrics["auto"]
        win, n = m.pairwise()
        names = m.names
        cw, lw = 86, 112
        w, h = lw + cw * len(names) + 24, 96 + 26 * len(names)
        x, y = SCREEN_W - w - 18, 18
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((6, 9, 18, 200))
        pygame.draw.rect(panel, (120, 135, 170, 120), panel.get_rect(), 1, border_radius=8)
        screen.blit(panel, (x, y))
        shared = min((n[a][b] for a in names for b in names if a != b), default=0)
        screen.blit(self.f_med.render("Por pares: fila llega antes que columna", True, GOLD), (x + 12, y + 10))
        for j, b in enumerate(names):
            screen.blit(self.f_small.render(SHORT.get(b, b), True, MUTED), (x + 12 + lw + j * cw, y + 38))
        for i, a in enumerate(names):
            yy = y + 62 + 26 * i
            screen.blit(self.f_small.render(SHORT.get(a, a), True, MUTED), (x + 12, yy))
            for j, b in enumerate(names):
                if a == b:
                    txt, col = "—", MUTED
                elif b in win[a]:
                    v = win[a][b]
                    txt, col = f"{v:.0f}%", (140, 225, 150) if v > 50 else (TEXT if v > 0 else MUTED)
                else:
                    txt, col = "-", MUTED
                screen.blit(self.f_small.render(txt, True, col), (x + 12 + lw + j * cw, yy))
        screen.blit(self.f_small.render(f"{shared} objetivos compartidos por par · fallo = {EPISODE_TIMEOUT:.0f} s",
                                        True, MUTED), (x + 12, y + h - 24))

    def draw_validation(self, screen):
        """Validación offline de los modelos del Bloque 2 (tools/train_models.py): qué tan bien imitan a A*."""
        rep = self.ml_report
        if not rep:
            return
        cols = [80, 140, 140, 70]
        models = rep["modelos"]
        w, h = sum(cols) + 28, 94 + 26 * len(models)
        x, y = 18, 156
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((6, 9, 18, 200))
        pygame.draw.rect(panel, (120, 135, 170, 120), panel.get_rect(), 1, border_radius=8)
        screen.blit(panel, (x, y))
        screen.blit(self.f_med.render("Validación: imitar a A* (offline)", True, GOLD), (x + 14, y + 10))
        heads = ["Modelo", "Exactitud CV", "F1 macro CV", "Prueba"]
        xx = x + 14
        for v, cw in zip(heads, cols):
            screen.blit(self.f_small.render(v, True, MUTED), (xx, y + 38))
            xx += cw
        for i, (name, m) in enumerate(models.items()):
            vals = [name, f"{m['cv_exactitud'][0]:.3f} ± {m['cv_exactitud'][1]:.3f}",
                    f"{m['cv_f1_macro'][0]:.3f} ± {m['cv_f1_macro'][1]:.3f}", f"{m['prueba_exactitud']:.3f}"]
            xx = x + 14
            for v, cw in zip(vals, cols):
                screen.blit(self.f_small.render(v, True, TEXT), (xx, y + 64 + 26 * i))
                xx += cw
        lv = ", ".join(str(n) for n in rep.get("niveles_entrenamiento", [1]))
        note = f"Niveles {lv} · 5 particiones · {rep['entrenamiento']} entren. / {rep['prueba']} prueba · base {rep['clase_mayoritaria']:.2f}"
        screen.blit(self.f_small.render(note, True, MUTED), (x + 14, y + h - 26))

    def draw_params(self, screen, world):
        """Parámetros en vivo: valor actual y tecla para cambiarlo."""
        p = world.params
        lines = [("Parámetros en vivo", GOLD),
                 (f"+/-  presupuesto: {p['presupuesto']} por frame", TEXT),
                 (f"H    peso heurística A*: {p['peso_h']:g}" + ("  (costo uniforme)" if p['peso_h'] == 0 else ""), TEXT),
                 (f"N    vecinos KNN: k = {p['k']}", TEXT)]
        w, h = 330, 22 + 24 * len(lines)
        x, y = 18, SCREEN_H - h - 48
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((6, 9, 18, 190))
        pygame.draw.rect(panel, (120, 135, 170, 120), panel.get_rect(), 1, border_radius=8)
        screen.blit(panel, (x, y))
        for i, (txt, col) in enumerate(lines):
            screen.blit(self.f_small.render(txt, True, col), (x + 12, y + 10 + 24 * i))

    def draw_toast(self, screen, text, alpha):
        img = self.f_med.render(text, True, (245, 240, 225))
        bg = pygame.Surface((img.get_width() + 30, img.get_height() + 16), pygame.SRCALPHA)
        bg.fill((40, 30, 10, int(210 * alpha)))
        img.set_alpha(int(255 * alpha))
        x = SCREEN_W / 2 - bg.get_width() / 2
        screen.blit(bg, (x, SCREEN_H * 0.42))
        screen.blit(img, (x + 15, SCREEN_H * 0.42 + 8))

    def _row(self, screen, values, x, y, color):
        for v, cw in zip(values, COLS):
            screen.blit(self.f_small.render(v, True, color), (x, y))
            x += cw

    # ---------- textos ----------
    def draw_area_title(self, screen, name, sub, alpha):
        if alpha <= 0:
            return
        t1 = self.f_title.render(name, True, (240, 240, 248))
        t2 = self.f_med.render(sub, True, MUTED)
        for img in (t1, t2):
            img.set_alpha(alpha)
        cy = SCREEN_H * 0.32
        screen.blit(t2, (SCREEN_W / 2 - t2.get_width() / 2, cy - 44))
        screen.blit(t1, (SCREEN_W / 2 - t1.get_width() / 2, cy))
        line = pygame.Surface((t1.get_width() + 80, 2), pygame.SRCALPHA)
        line.fill((220, 225, 240, alpha // 2))
        screen.blit(line, (SCREEN_W / 2 - line.get_width() / 2, cy + t1.get_height() + 8))

    def draw_hint(self, screen, text):
        img = self.f_small.render(text, True, MUTED)
        screen.blit(img, (18, SCREEN_H - 30))

    def draw_badge(self, screen, text):
        img = self.f_small.render(text, True, TEXT)
        bg = pygame.Surface((img.get_width() + 20, img.get_height() + 10), pygame.SRCALPHA)
        bg.fill((6, 9, 18, 170))
        screen.blit(bg, (18, 112))
        screen.blit(img, (28, 117))
