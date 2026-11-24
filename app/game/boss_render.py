"""Dibujo de Hornet, su aguja y la barra de vida del jefe. Solo LEE el estado de BossWorld."""
import pygame

from .assets import whiten
from .boss import ATTACKS, BOSS_HEADERS, THREAD_REACH, WINDUP
from .config import BOSS_HP, EPISODE_TIMEOUT, SCREEN_H, SCREEN_W

TEXT = (232, 236, 245)
MUTED = (150, 158, 182)
GOLD = (240, 214, 150)
COLS = [150, 64, 64, 70, 92, 96, 56]


class BossRenderer:
    def __init__(self, assets):
        self.A = assets.anims
        self.white = {}
        self.f_small, self.f_med, self.f_name = assets.font(22), assets.font(26), assets.font(30)
        self.f_tiny, self.f_head = assets.font(18), assets.font(20)

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

    def draw_table(self, screen, world, big=False, mode="compacta"):
        """Tabla del jefe arriba a la derecha. Compacta: estrategia, acierto % y aciertos/min."""
        if mode == "oculta":
            return
        rows = world.metrics[world.mode].rows()
        cols = [(0, 150), (3, 70), (4, 92)] if mode == "compacta" else [(i, cw) for i, cw in enumerate(COLS)]
        w = sum(cw for _, cw in cols) + 20
        h = 50 + 20 * len(rows) + (22 if big else 0)
        x, y = SCREEN_W - w - 14, 44
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((6, 9, 18, 185))
        pygame.draw.rect(panel, (120, 135, 170, 110), panel.get_rect(), 1, border_radius=8)
        screen.blit(panel, (x, y))
        title = "Jefe · partida con humano" if world.mode == "manual" else "Jefe · laboratorio (robot sembrado)"
        screen.blit(self.f_head.render(title, True, GOLD), (x + 10, y + 7))
        xx = x + 10
        for i, cw in cols:
            screen.blit(self.f_tiny.render(BOSS_HEADERS[i], True, MUTED), (xx, y + 29))
            xx += cw
        for r, row in enumerate(rows):
            yy = y + 48 + 20 * r
            if row[0] == world.technique:
                hl = pygame.Surface((w - 10, 18), pygame.SRCALPHA)
                hl.fill((110, 130, 190, 60))
                screen.blit(hl, (x + 5, yy - 2))
            xx = x + 10
            for i, cw in cols:
                screen.blit(self.f_tiny.render(row[i], True, TEXT), (xx, yy))
                xx += cw
        if big:
            info = f"En curso: {world.technique} · t {world.t:4.1f} s"
            screen.blit(self.f_tiny.render(info, True, MUTED), (x + 10, y + h - 20))
