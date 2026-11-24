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
# columnas (ancho en px) de la tabla completa y de la compacta; la compacta muestra lo esencial
COLS = [118, 58, 60, 74, 74, 46, 64, 54]
COMPACT = [(0, 118), (2, 64), (4, 74), (7, 58)]          # Técnica, Alcanza %, T. penal., ms/dec
HEAD_SHORT = ["Técnica", "Corr.", "Alcanza", "T. alc.", "T. penal.", "Pasos", "Nodos", "ms/dec"]
ROW_H = 20
# Paneles que se muestran u ocultan (tecla o clic en la barra de botones de arriba a la derecha)
PANELS = [("tabla", "M", "Tabla"), ("pares", "P", "Pares"), ("valid", "V", "Validación"), ("params", "O", "Parámetros")]
SHORT = {"Aleatorio (base)": "Aleatorio"}


class Hud:
    def __init__(self, assets):
        self.a = assets
        self.orb = scale(assets.anims["soul_orb"].frames[0], 1.15)
        self.mask_full = scale(assets.anims["mask_full"].frames[0], 0.8)
        self.mask_empty = scale(assets.anims["mask_empty"].frames[0], 0.8)
        self.f_small, self.f_med, self.f_big, self.f_title = (assets.font(s) for s in (22, 26, 34, 74))
        self.f_tiny, self.f_head = assets.font(18), assets.font(20)
        # tabla: "compacta" -> "completa" -> "oculta"; los demás paneles: visible o no
        self.panels = {"tabla": "compacta", "pares": False, "valid": False, "params": False}
        self.buttons = []                                   # (rect, panel) de la barra, para detectar clics
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

    # ---------- paneles plegables ----------
    def toggle(self, name):
        if name == "tabla":
            order = ["compacta", "completa", "oculta"]
            self.panels["tabla"] = order[(order.index(self.panels["tabla"]) + 1) % 3]
        else:
            self.panels[name] = not self.panels[name]

    def click(self, pos):
        for rect, name in self.buttons:
            if rect.collidepoint(pos):
                self.toggle(name)
                return True
        return False

    def draw_toolbar(self, screen, available):
        """Botones pequeños arriba a la derecha: muestran el estado de cada panel y se pueden pulsar."""
        self.buttons = []
        x = SCREEN_W - 14
        for name, key, label in reversed([p for p in PANELS if p[0] in available]):
            state = self.panels[name]
            on = state not in (False, "oculta")
            text = f"{label} [{key}]" + (" +" if state == "completa" else "")
            img = self.f_tiny.render(text, True, TEXT if on else MUTED)
            r = pygame.Rect(0, 10, img.get_width() + 16, 24)
            r.right = x
            bg = pygame.Surface(r.size, pygame.SRCALPHA)
            bg.fill((70, 90, 150, 170) if on else (6, 9, 18, 150))
            pygame.draw.rect(bg, (120, 135, 170, 140), bg.get_rect(), 1, border_radius=6)
            screen.blit(bg, r.topleft)
            screen.blit(img, (r.x + 8, r.y + 4))
            self.buttons.append((r, name))
            x = r.x - 6

    @staticmethod
    def _panel(screen, x, y, w, h):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((6, 9, 18, 185))
        pygame.draw.rect(panel, (120, 135, 170, 110), panel.get_rect(), 1, border_radius=8)
        screen.blit(panel, (x, y))

    def draw_table(self, screen, world, big=False, y=44):
        """Tabla comparativa arriba a la derecha. Compacta: técnica, alcance, tiempo penalizado y ms/dec."""
        mode = self.panels["tabla"]
        if mode == "oculta":
            return y
        rows = world.metrics[world.mode].rows()
        if mode == "compacta":
            cols = COMPACT
        else:
            cols = list(enumerate(COLS))
        w = sum(cw for _, cw in cols) + 20
        h = 50 + ROW_H * len(rows) + (22 if big else 0)
        x = SCREEN_W - w - 14
        self._panel(screen, x, y, w, h)
        title = "Partida con humano" if world.mode == "manual" else "Laboratorio · objetivos sembrados"
        screen.blit(self.f_head.render(title, True, GOLD), (x + 10, y + 7))
        xx = x + 10
        for i, cw in cols:
            screen.blit(self.f_tiny.render(HEAD_SHORT[i], True, MUTED), (xx, y + 29))
            xx += cw
        for r, row in enumerate(rows):
            yy = y + 48 + ROW_H * r
            active = row[0] in world.active_techniques if world.mode == "manual" else row[0] == world.technique
            if active:
                hl = pygame.Surface((w - 10, ROW_H - 2), pygame.SRCALPHA)
                hl.fill((110, 130, 190, 60))
                screen.blit(hl, (x + 5, yy - 2))
            xx = x + 10
            for i, cw in cols:
                v = SHORT.get(row[i], row[i]) if i == 0 else row[i]
                screen.blit(self.f_tiny.render(v, True, TEXT), (xx, yy))
                xx += cw
        if big:
            info = f"En curso: {SHORT.get(world.technique, world.technique)} · t {world.t:4.1f} s · F vel. · R reinicia"
            screen.blit(self.f_tiny.render(info, True, MUTED), (x + 10, y + h - 20))
        return y + h + 8

    def draw_pairwise(self, screen, world, y=44):
        """Matriz por pares del laboratorio: % de objetivos compartidos en que la fila llega antes que la columna."""
        if not self.panels["pares"]:
            return y
        m = world.metrics["auto"]
        win, n = m.pairwise()
        names = m.names
        cw, lw = 54, 82
        w, h = lw + cw * len(names) + 18, 72 + ROW_H * len(names)
        x = SCREEN_W - w - 14
        self._panel(screen, x, y, w, h)
        shared = min((n[a][b] for a in names for b in names if a != b), default=0)
        screen.blit(self.f_head.render("Por pares: fila llega antes", True, GOLD), (x + 10, y + 7))
        abbrev = lambda t: SHORT.get(t, t)[:6]
        for j, b in enumerate(names):
            screen.blit(self.f_tiny.render(abbrev(b), True, MUTED), (x + 10 + lw + j * cw, y + 29))
        for i, a in enumerate(names):
            yy = y + 48 + ROW_H * i
            screen.blit(self.f_tiny.render(SHORT.get(a, a), True, MUTED), (x + 10, yy))
            for j, b in enumerate(names):
                if a == b:
                    txt, col = "—", MUTED
                elif b in win[a]:
                    v = win[a][b]
                    txt, col = f"{v:.0f}%", (140, 225, 150) if v > 50 else (TEXT if v > 0 else MUTED)
                else:
                    txt, col = "-", MUTED
                screen.blit(self.f_tiny.render(txt, True, col), (x + 10 + lw + j * cw, yy))
        screen.blit(self.f_tiny.render(f"{shared} objetivos por par · fallo = {EPISODE_TIMEOUT:.0f} s", True, MUTED),
                    (x + 10, y + h - 20))
        return y + h + 8

    def draw_validation(self, screen, y=150):
        """Validación offline de los modelos del Bloque 2 (tools/train_models.py): qué tan bien imitan a A*."""
        rep = self.ml_report
        if not rep or not self.panels["valid"]:
            return
        cols = [64, 118, 118, 56]
        models = rep["modelos"]
        w, h = sum(cols) + 20, 72 + ROW_H * len(models)
        x = 14
        self._panel(screen, x, y, w, h)
        screen.blit(self.f_head.render("Validación: imitar a A*", True, GOLD), (x + 10, y + 7))
        xx = x + 10
        for v, cw in zip(["Modelo", "Exactitud CV", "F1 macro CV", "Prueba"], cols):
            screen.blit(self.f_tiny.render(v, True, MUTED), (xx, y + 29))
            xx += cw
        for i, (name, m) in enumerate(models.items()):
            vals = [name, f"{m['cv_exactitud'][0]:.3f}±{m['cv_exactitud'][1]:.3f}",
                    f"{m['cv_f1_macro'][0]:.3f}±{m['cv_f1_macro'][1]:.3f}", f"{m['prueba_exactitud']:.3f}"]
            xx = x + 10
            for v, cw in zip(vals, cols):
                screen.blit(self.f_tiny.render(v, True, TEXT), (xx, y + 48 + ROW_H * i))
                xx += cw
        lv = ",".join(str(n) for n in rep.get("niveles_entrenamiento", [1]))
        note = f"Niveles {lv} · 5 part. · {rep['entrenamiento']}/{rep['prueba']} · base {rep['clase_mayoritaria']:.2f}"
        screen.blit(self.f_tiny.render(note, True, MUTED), (x + 10, y + h - 20))

    def draw_params(self, screen, world):
        """Parámetros en vivo: valor actual y tecla para cambiarlo."""
        if not self.panels["params"]:
            return
        p = world.params
        lines = [("Parámetros en vivo", GOLD),
                 (f"+/-  presupuesto: {p['presupuesto']} por frame", TEXT),
                 (f"H    peso heurística A*: {p['peso_h']:g}" + ("  (uniforme)" if p['peso_h'] == 0 else ""), TEXT),
                 (f"N    vecinos KNN: k = {p['k']}", TEXT)]
        w, h = 270, 16 + ROW_H * len(lines)
        x, y = 14, SCREEN_H - h - 42
        self._panel(screen, x, y, w, h)
        for i, (txt, col) in enumerate(lines):
            screen.blit((self.f_head if i == 0 else self.f_tiny).render(txt, True, col), (x + 10, y + 8 + ROW_H * i))

    def draw_toast(self, screen, text, alpha):
        img = self.f_med.render(text, True, (245, 240, 225))
        bg = pygame.Surface((img.get_width() + 30, img.get_height() + 16), pygame.SRCALPHA)
        bg.fill((40, 30, 10, int(210 * alpha)))
        img.set_alpha(int(255 * alpha))
        x = SCREEN_W / 2 - bg.get_width() / 2
        screen.blit(bg, (x, SCREEN_H * 0.42))
        screen.blit(img, (x + 15, SCREEN_H * 0.42 + 8))

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
