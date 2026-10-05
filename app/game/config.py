"""Parámetros globales. Juego (main.py) y benchmark (benchmark.py) leen los mismos valores."""

SCREEN_W, SCREEN_H = 1280, 720
TILE = 48
FPS = 60
DT = 1.0 / FPS            # paso fijo de la simulación (independiente del framerate real)

# Física del jugador (px, s)
GRAVITY = 2600.0
PLAYER_SPEED = 300.0
PLAYER_JUMP_VEL = 930.0   # ~3.4 celdas de altura
PLAYER_MAX_FALL = 1100.0
PLAYER_W, PLAYER_H = 26, 56

# Combate (modo juego)
PLAYER_MAX_HP = 5                 # máscaras
PLAYER_INVULN = 1.3               # s de invulnerabilidad tras recibir daño
PLAYER_KNOCKBACK = (420.0, 420.0)
ATTACK_TIME = 0.32                # duración total del golpe de aguijón
ATTACK_ACTIVE = (0.04, 0.16)      # ventana en la que el golpe hace daño
ATTACK_RANGE = (78, 56)           # ancho, alto de la zona de impacto frente al jugador
SOUL_PER_HIT = 11
SOUL_HEAL_COST = 33
ENEMY_STUN = 0.35                 # s que el enemigo queda aturdido al recibir un golpe
ENEMY_RECOVER = 0.9               # s que el enemigo espera tras golpear al jugador
ENEMY_RESPAWN = 2.5               # s hasta reaparecer tras morir

# Movilidad del enemigo sobre el grafo de navegación (en celdas)
ENEMY_SPEED = 6.0         # celdas recorridas por segundo
JUMP_UP = 3               # altura máxima de salto
JUMP_ACROSS = 3           # alcance horizontal máximo del salto
ENEMY_W, ENEMY_H = 36, 64

# Tipos de enemigo (letra en el mapa -> stats). Todos usan el mismo grafo y el mismo actuador;
# el laboratorio IA usa SOLO el tipo "saltador" para que la comparación entre técnicas sea justa.
ENEMY_TYPES = {
    "saltador": {"name": "Husk saltador", "anim": "husk", "speed": ENEMY_SPEED, "hp": 3},
    "errante": {"name": "Husk errante", "anim": "whusk", "speed": 4.5, "hp": 2},
    "cornudo": {"name": "Husk cornudo", "anim": "horn", "speed": 5.0, "hp": 4},
}
SPAWN_CHARS = {"E": "saltador", "S": "saltador", "W": "errante", "H": "cornudo"}   # "E" = spawn del laboratorio

# IA
AI_BUDGET = 200           # nodos que el agente puede expandir por frame antes de ceder el control
EPISODE_TIMEOUT = 20.0    # segundos simulados; si no alcanza al objetivo, el episodio cuenta como fallo
MIN_TARGET_DIST = 12      # distancia Manhattan mínima entre el spawn del enemigo y el objetivo (modo auto)
SEED = 2026
