"""Dibujo de Hornet, su aguja y la barra de vida del jefe. Solo LEE el estado de BossWorld."""
import pygame

from .assets import whiten
from .boss import ATTACKS, BOSS_HEADERS, THREAD_REACH, WINDUP
from .config import BOSS_HP, EPISODE_TIMEOUT, SCREEN_H, SCREEN_W

TEXT = (232, 236, 245)
MUTED = (150, 158, 182)
GOLD = (240, 214, 150)
COLS = [210, 82, 78, 92, 116, 120, 70]


class BossRenderer:
    def __init__(self, assets):
        self.A = assets.anims
        self.white = {}
        self.f_small, self.f_med, self.f_name = assets.font(22), assets.font(26), assets.font(30)

    def _anim_frame(self, b, t):
        A = self.A
        if b.dead_t >= 0:
            return A["hornet_land"].at(5), True
        if b.state == "windup":
            k = b.t / WINDUP[b.attack]
            if b.attack == "lanza":
                return A["hornet_throw"].at(int(k * 4)), False
            return A["hornet_land"].at(int(k * 2)), False
        if b.state == "active":
            if b.attack == "lanza":
                return A["hornet_throw"].at(4 + int(min(1.0, b.t / 0.4) * 3)), False
            if b.attack == "embestida":
                return A["hornet_dash"].frame(b.t), False
            return A["hornet_jump"].at(int(min(0.99, b.t / 0.8) * len(A["hornet_jump"]))), False
        if b.state == "recover" and b.attack == "salto":
            return A["hornet_land"].frame(b.t), False
        return A["hornet_idle"].frame(t), False

    def draw(self, screen, world, view, t):
        b = world.boss
        vx, vy = view
        img, fade = self._anim_frame(b, t)
        anim = self.A["hornet_idle"]
        if anim.flip_for(b.facing):
            img = pygame.transform.flip(img, True, False)
        if b.flash > 0:
            key = id(img)
            img = self.white.setdefault(key, whiten(img))
        if fade:
            img = img.copy()
            img.set_alpha(max(0, int(255 * (1 - b.dead_t / 2.0))))
        x, y, w, h = b.rect
        screen.blit(img, (x + w / 2 - img.get_width() / 2 - vx, y + h - img.get_height() + 8 - vy))
        if b.state == "active" and b.attack == "lanza" and b.thread > 0:
            self._draw_thread(screen, b, vx, vy, t)

    def _draw_thread(self, screen, b, vx, vy, t):
        frames = self.A["hornet_thread"]
        img = frames.frame(t)
        length = max(8, int(b.thread))
        line = pygame.transform.smoothscale(img, (length, img.get_height()))
        if b.facing > 0:
            line = pygame.transform.flip(line, True, False)
        hx = b.center[0] + b.facing * 18
        x = hx if b.facing > 0 else hx - length
        cy = b.y + b.rect[3] * 0.42
        screen.blit(line, (x - vx, cy - line.get_height() / 2 - vy))
        tip = x + length if b.facing > 0 else x                     # punta de la aguja
        pygame.draw.polygon(screen, (235, 235, 245), [(tip - vx, cy - 6 - vy), (tip + b.facing * 22 - vx, cy - vy),
                                                       (tip - vx, cy + 6 - vy)])

    # ---------- HUD del jefe ----------
    def draw_bar(self, screen, world):
        b = world.boss
        w, h = 620, 14
        x, y = (SCREEN_W - w) // 2, SCREEN_H - 62
        name = self.f_name.render("HORNET", True, (240, 236, 244))
        screen.blit(name, (SCREEN_W / 2 - name.get_width() / 2, y - 34))
        pygame.draw.rect(screen, (20, 14, 22), (x - 3, y - 3, w + 6, h + 6), border_radius=4)
        frac = max(0, b.hp) / BOSS_HP
        pygame.draw.rect(screen, (160, 40, 60), (x, y, int(w * frac), h), border_radius=3)
        pygame.draw.rect(screen, (230, 220, 235), (x - 3, y - 3, w + 6, h + 6), 1, border_radius=4)

    def draw_table(self, screen, world, big=False):
        rows = world.metrics[world.mode].rows()
        w = sum(COLS) + 28
        h = 66 + 26 * len(rows) + (30 if big else 0)
        x = (SCREEN_W - w) // 2 if big else SCREEN_W - w - 18
        y = 150 if big else 18                    # arriba: el suelo de la arena queda abajo y no se tapa
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((6, 9, 18, 200))
        pygame.draw.rect(panel, (120, 135, 170, 120), panel.get_rect(), 1, border_radius=8)
        screen.blit(panel, (x, y))
        title = "Jefe: ¿qué ataque elegir? — " + ("partida con humano" if world.mode == "manual"
                                                  else "laboratorio (jugador robot sembrado)")
        screen.blit(self.f_med.render(title, True, GOLD), (x + 14, y + 10))
        self._row(screen, BOSS_HEADERS, x + 14, y + 38, MUTED)
        for i, row in enumerate(rows):
            yy = y + 64 + 26 * i
            if row[0] == world.technique:
                hl = pygame.Surface((w - 16, 24), pygame.SRCALPHA)
                hl.fill((110, 130, 190, 60))
                screen.blit(hl, (x + 8, yy - 4))
            self._row(screen, row, x + 14, yy, TEXT)
        if big:
            info = (f"Estrategia en curso: {world.technique}   ·   t = {world.t:4.1f} s   ·   "
                    f"L/E/S = lanza / embestida / salto   ·   F velocidad   R reiniciar")
            screen.blit(self.f_small.render(info, True, MUTED), (x + 14, y + h - 28))

    def _row(self, screen, values, x, y, color):
        for v, cw in zip(values, COLS):
            screen.blit(self.f_small.render(v, True, color), (x, y))
            x += cw
