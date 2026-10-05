"""Jugador: física de plataformas (gravedad, salto, colisiones AABB) + combate con aguijón."""
from .config import (ATTACK_ACTIVE, ATTACK_RANGE, ATTACK_TIME, GRAVITY, PLAYER_H, PLAYER_INVULN,
                     PLAYER_JUMP_VEL, PLAYER_KNOCKBACK, PLAYER_MAX_FALL, PLAYER_MAX_HP, PLAYER_SPEED,
                     PLAYER_W, SOUL_HEAL_COST, TILE)


class Player:
    def __init__(self, cell):
        self.hp = PLAYER_MAX_HP
        self.soul = 0
        self.place_on(cell)

    def place_on(self, cell):
        c, r = cell
        self.x = c * TILE + (TILE - PLAYER_W) / 2
        self.y = (r + 1) * TILE - PLAYER_H
        self.vx = self.vy = 0.0
        self.on_ground = True
        self.facing = 1            # 1 derecha, -1 izquierda
        self.attack_t = -1.0       # tiempo desde que empezó el golpe (-1 = sin golpe)
        self.attack_hit = set()    # ids golpeados en este swing (un golpe por swing)
        self.invuln = 0.0
        self.hurt_t = 0.0          # tiempo sin control tras un golpe recibido
        self.heal_flash = 0.0

    @property
    def rect(self):
        return (self.x, self.y, PLAYER_W, PLAYER_H)

    @property
    def feet(self):
        return (self.x + PLAYER_W / 2, self.y + PLAYER_H)

    @property
    def attacking(self):
        return self.attack_t >= 0

    def attack_box(self):
        """Zona de impacto del aguijón, solo durante la ventana activa del golpe."""
        a0, a1 = ATTACK_ACTIVE
        if not (a0 <= self.attack_t <= a1):
            return None
        w, h = ATTACK_RANGE
        x = self.x + PLAYER_W if self.facing > 0 else self.x - w
        return (x, self.y + PLAYER_H / 2 - h / 2, w, h)

    def take_hit(self, from_x):
        if self.invuln > 0:
            return False
        self.hp -= 1
        self.invuln = PLAYER_INVULN
        self.hurt_t = 0.22
        self.attack_t = -1.0
        side = 1 if self.x + PLAYER_W / 2 >= from_x else -1
        self.vx, self.vy = side * PLAYER_KNOCKBACK[0], -PLAYER_KNOCKBACK[1]
        return True

    def update(self, dt, level, move_dir, jump_pressed, jump_held, attack_pressed=False, heal_pressed=False):
        self.invuln = max(0.0, self.invuln - dt)
        self.heal_flash = max(0.0, self.heal_flash - dt)

        if self.hurt_t > 0:
            self.hurt_t -= dt                      # retroceso: sin control del jugador
        else:
            self.vx = move_dir * PLAYER_SPEED
            if move_dir:
                self.facing = 1 if move_dir > 0 else -1
            if jump_pressed and self.on_ground:
                self.vy = -PLAYER_JUMP_VEL
            if not jump_held and self.vy < 0:
                self.vy *= 0.85                    # salto variable: soltar corta el ascenso
            if attack_pressed and not self.attacking:
                self.attack_t = 0.0
                self.attack_hit = set()
            if heal_pressed and self.soul >= SOUL_HEAL_COST and self.hp < PLAYER_MAX_HP:
                self.soul -= SOUL_HEAL_COST
                self.hp += 1
                self.heal_flash = 0.5

        if self.attacking:
            self.attack_t += dt
            if self.attack_t > ATTACK_TIME:
                self.attack_t = -1.0

        self.vy = min(self.vy + GRAVITY * dt, PLAYER_MAX_FALL)
        self.x += self.vx * dt
        self._collide(level, axis=0)
        self.y += self.vy * dt
        self.on_ground = False
        self._collide(level, axis=1)

    def _collide(self, level, axis):
        c0, c1 = int(self.x // TILE), int((self.x + PLAYER_W - 1e-6) // TILE)
        r0, r1 = int(self.y // TILE), int((self.y + PLAYER_H - 1e-6) // TILE)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if not level.solid(c, r):
                    continue
                if axis == 0:
                    if self.vx > 0:
                        self.x = c * TILE - PLAYER_W
                    elif self.vx < 0:
                        self.x = (c + 1) * TILE
                    self.vx = 0
                else:
                    if self.vy > 0:
                        self.y = r * TILE - PLAYER_H
                        self.on_ground = True
                    elif self.vy < 0:
                        self.y = (r + 1) * TILE
                    self.vy = 0
