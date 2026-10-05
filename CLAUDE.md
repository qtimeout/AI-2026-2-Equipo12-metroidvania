# CLAUDE.md

## Fuentes de información

Las fuentes de información del proyecto están en archivos `.pdf` en la raíz del proyecto (por ejemplo, `08-26-1 Guía-Trabajo Final-AI.pdf`). Consultarlos antes de tomar decisiones sobre requisitos o alcance.

## Visión del juego

Metroidvania inspirado en Hollow Knight: máximo 5 niveles, el 5.º es una pelea contra un jefe. Combate con aguijón y vida en máscaras. El arte sale de `Sprites/` (recursos originales de HK; el usuario decidió usarlos también en la versión publicada).

## Estructura y comandos

- Todo el código del juego vive en `app/`, porque pygbag empaqueta la carpeta entera y no debe publicar los PDF, `Sprites/` ni `.claude/`.
- Juego: `cd app && python main.py` · Navegador: `python -m pygbag app` · Benchmark: `cd app && python benchmark.py`.
- Arte: `python tools/build_assets.py` regenera `app/assets/` desde `Sprites/`. Los índices de los fotogramas dependen de `tools/slice_atlas.py` (alfa 100, gap 2, área mínima 400); si se cambian esos parámetros, los índices cambian.
- Niveles: `app/game/level.py`. Validar con `python tools/check_level.py N`: el grafo debe ser fuertemente conexo y cada nodo debe tener 2 celdas de altura libre.
- Las técnicas nuevas se registran en `app/game/agents/__init__.py`. `decide()` debe ser un generador que haga `yield` por cada nodo expandido, para que el scheduler reparta la búsqueda entre frames.
- Enemigos: los tipos están en `ENEMY_TYPES` (`config.py`) y se colocan en el mapa con las letras de `SPAWN_CHARS`; `E` es además el spawn del laboratorio. En partida, cada enemigo es un `Slot` con su propio agente y scheduler. El laboratorio usa un solo Husk saltador para que la comparación sea justa.
- Métricas (`metrics.py`): "T. penal." cuenta cada fallo como `EPISODE_TIMEOUT`. `by_target` guarda los resultados por objetivo para la comparación por pares (solo en el laboratorio).
- `World` (`app/game/world.py`) es lógica pura sin pygame. El render (`render.py`, `background.py`, `hud.py`, `menu.py`, `play.py`) solo lee el estado.
