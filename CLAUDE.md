# CLAUDE.md

## Fuentes de información

Las fuentes de información del proyecto están en archivos `.pdf` en la raíz del proyecto (por ejemplo, `08-26-1 Guía-Trabajo Final-AI.pdf`). Consultarlos antes de tomar decisiones sobre requisitos o alcance.

## Visión del juego

Metroidvania inspirado en Hollow Knight: 4 niveles; el 4.º es la pelea contra el jefe (Hornet). Combate con aguijón y vida en máscaras. El arte sale de `Sprites/` (recursos originales de HK; el usuario decidió usarlos también en la versión publicada).

## Estructura y comandos

- Todo el código del juego vive en `app/`, porque pygbag empaqueta la carpeta entera y no debe publicar los PDF, `Sprites/` ni `.claude/`.
- Juego: `python app/main.py` · Navegador: `python -m pygbag app` · Benchmark: `python app/benchmark.py` (`--seeds 2026 2027 ...` para varias semillas).
- Arte: `python tools/build_assets.py` regenera `app/assets/` desde `Sprites/`. Los índices de los fotogramas dependen de `tools/slice_atlas.py` (alfa 100, gap 2, área mínima 400); si se cambian esos parámetros, los índices cambian.
- Niveles: `app/game/level.py`. `LEVELS[n]` guarda el nombre del área, el tema visual y el mapa; `X` es la salida al nivel siguiente (la partida conserva vida y alma) y tras el último nivel se muestra `EndScene`. Validar con `python tools/check_level.py N`: el grafo debe ser fuertemente conexo y cada nodo debe tener 2 celdas de altura libre. Nivel 1 = Paso Olvidado (tema `kingspass`), nivel 2 = Cruces Olvidados (`crossroads`, con faroles), nivel 3 = Sendero Verde (`greenpath`, 9 enemigos con Musgosos `M`/`V`), nivel 4 = Guarida de Hornet (`jefe: True`, paleta `arena`, spawn `B`). La arena del jefe debe ser plana: Hornet mide 2+ baldosas.
- Jefe (`app/game/boss.py`): `BossWorld` imita la interfaz de `World`. La IA elige QUÉ ataque usar (lanza, embestida o salto) con 4 estrategias: Aleatorio (base), Reflejo, Utilidad (a mano) y Utilidad (aprendida, regresión logística de `tools/train_boss.py` → `app/models/boss_logreg.json`). El laboratorio del jefe usa un `PlayerBot` sembrado, idéntico para todas las estrategias. Si se cambia la arena o los ataques, hay que reentrenar con `python tools/train_boss.py`.
- Temas: `THEMES` en `tools/build_assets.py` define las piezas de cada zona (floor/rock/bg/deco/exit/lamp) y `PALETTES` en `background.py`, su paleta. Para un nivel nuevo: agregar el tema, regenerar assets y añadir la entrada en `LEVELS`.
- Las técnicas nuevas se registran en `app/game/agents/__init__.py`. `decide()` debe ser un generador que haga `yield` por cada nodo expandido, para que el scheduler reparta la búsqueda entre frames.
- Enemigos: los tipos están en `ENEMY_TYPES` (`config.py`) y se colocan en el mapa con las letras de `SPAWN_CHARS`; `E` es además el spawn del laboratorio. En partida, cada enemigo es un `Slot` con su propio agente y scheduler. El laboratorio usa un solo Husk saltador para que la comparación sea justa.
- Métricas (`metrics.py`): "T. penal." cuenta cada fallo como `EPISODE_TIMEOUT`. `by_target` guarda los resultados por objetivo para la comparación por pares (solo en el laboratorio).
- Bloque 2 (aprendizaje): `python tools/make_dataset.py 1` graba las demostraciones de A* en `data/`. Luego `python tools/train_models.py 1` entrena KNN, Árbol y MLP con scikit-learn (validación cruzada de 5 particiones) y los exporta a `app/models/*.json`. El juego predice en Python puro (`app/game/ml/models.py`), porque pygbag no tiene scikit-learn ni numpy. Si se cambia el nivel o `features.py`, hay que regenerar el dataset y reentrenar. Los modelos del juego se entrenan con todos los niveles con Husks (`train_models.py 1 2 3`); `--eval N` mide la transferencia a un nivel no visto.
- El KNN usa un índice por cubetas con poda (`KEY_DIMS` en `ml/models.py`; resultado idéntico a la fuerza bruta, verificable con `KNNModel(d, brute=True)`). Reparte su cálculo con `yield PAUSE` cada `KNN_CHUNK` puntos o cotas, calibrado para que 1 unidad de `AI_BUDGET` cueste lo mismo que expandir un nodo. El scheduler no cuenta las pausas como nodos expandidos.
- Parámetros en vivo: `World.set_param` (presupuesto, peso_h, k) reinicia las métricas. Teclas `+`/`-`, `H` y `N` en `play.py`; los valores persisten en `app.params`. En consola: `benchmark.py --peso-h --k --budget`.
- HUD (`hud.py`): paneles plegables en `Hud.panels` (tabla compacta/completa/oculta, pares, validación, parámetros), con teclas M/P/V/O o clic en la barra (`draw_toolbar`/`click`). En el modo mixto, `World._mix_assignment` reparte como baraja las técnicas y también los tipos de enemigo (`ENEMY_TYPES`), con una semilla distinta por nivel.
- `World` (`app/game/world.py`) es lógica pura sin pygame. El render (`render.py`, `background.py`, `hud.py`, `menu.py`, `play.py`) solo lee el estado.
