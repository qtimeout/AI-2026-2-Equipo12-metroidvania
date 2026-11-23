# Paso Olvidado — Equipo 12

## Problema y quién lo sufre
En los Metroidvania 2D los enemigos persiguen con reglas simples y se atascan en paredes y plataformas, lo que vuelve el juego predecible. Lo sufren los desarrolladores indie, que necesitan enemigos que naveguen el mapa (caminar, caer, saltar) sin congelar el juego. En nuestro Metroidvania inspirado en *Hollow Knight* (4 niveles; el 4.º es el jefe Hornet) medimos qué agente lleva a los enemigos hasta el jugador antes y a qué costo, y qué estrategia de ataque le sirve más al jefe.

## Modo base
**Aleatorio:** el enemigo elige al azar una arista del grafo de navegación (cada nodo es una celda pisable y cada arista un movimiento: caminar, caer o saltar, con costo en celdas). El jefe, en el modo base, elige su ataque al azar.

## Técnicas comparadas
- **Parte 1 (bloque 1):** Reflejo (regla «acércate en línea recta»), **BFS** (ruta con menos saltos) y **A\*** (ruta con menos celdas, heurística Manhattan). Para el jefe: Reflejo (reglas por distancia) y **agente de utilidad** (P(acierto) / duración).
- **Parte 2 (bloque 2):** **KNN, árbol de decisión y MLP** imitan a A\* a partir de 78 322 demostraciones, sin buscar en el grafo. Una **regresión logística** aprende la P(acierto) de cada ataque del jefe.

## Resultados
Laboratorio dentro del juego (`TAB`) y en consola (`python app/benchmark.py`): mismos objetivos sembrados para cada técnica, y un fallo cuenta 20 s. El detalle (comparación por pares, validación y generalización) está en [docs/RESULTADOS.md](docs/RESULTADOS.md).

| Técnica (enemigos) | Alcanza al jugador | Tiempo penalizado | ms/decisión | Corridas |
|--------------------|--------------------|-------------------|-------------|----------|
| Aleatorio (base) | 2–5 % | 19.6–19.8 s | 0.002 | 900 |
| Reflejo | 37–79 % | 10.4–14.9 s | 0.003 | 900 |
| BFS | 86–100 % | 7.0–11.9 s | 0.08 | 900 |
| **A\*** | **100 %** | **5.4–9.8 s** | 0.16 | 900 |
| KNN (índice por cubetas) | 97–98 % | 6.0–10.5 s | 1.7 | 900 |
| **Árbol** | **98–99 %** | **5.6–9.8 s** | **0.02** | 900 |
| MLP | 67–84 % | 7.7–13.0 s | 0.5 | 900 |

*Rangos de los niveles 1 a 3; 3 semillas × 100 objetivos por nivel.* El árbol **iguala a A\* y decide 8 veces más rápido**. El MLP acierta el 97 % de las jugadas sueltas, pero en el juego encadena errores. El KNN compara contra sus 62 657 demostraciones: por fuerza bruta tardaba 116 ms por decisión y casi nunca llegaba (0–7 %); con un **índice por cubetas con poda** da el mismo resultado exacto 73 veces más rápido. En un mapa que no vieron, los modelos caen de 0.99 a 0.70–0.81 de exactitud, mientras que la búsqueda funciona en cualquier mapa.

| Estrategia del jefe | Acierto % | Aciertos/min | Corridas |
|---------------------|-----------|--------------|----------|
| Aleatorio (base) | 63.6 ± 1.4 | 20.3 | 150 × 60 s |
| Reflejo | 53.3 ± 2.0 | 16.2 | 150 × 60 s |
| Utilidad (a mano) | 64.3 ± 1.2 | 22.8 | 150 × 60 s |
| **Utilidad + regresión logística** | **72.5 ± 0.5** | **26.5** | 150 × 60 s |

## Cómo ejecutarlo
- **En línea:** https://qtimeout.itch.io/metroidvania-equipo-12 · **Código:** https://github.com/qtimeout/AI-2026-2-Equipo12-metroidvania
- **Local:** `pip install -r requirements.txt` y luego `python app/main.py`. En navegador: `python -m pygbag app`.
- **Controles:** flechas para moverse, Espacio para saltar, X para atacar y C para curarse. `1..7` asigna la técnica de los enemigos, `0` activa el modo mixto, `G` muestra el grafo, `M` la tabla y `TAB` el laboratorio (`F` cambia la velocidad). **Parámetros en vivo:** `+`/`−` presupuesto por frame, `H` peso de la heurística de A\* y `N` vecinos del KNN (efectos medidos en [docs/RESULTADOS.md](docs/RESULTADOS.md)).
- **Reproducir:** `python app/benchmark.py --level N --seeds 2026 2027 2028`. Reentrenar: `tools/make_dataset.py`, `tools/train_models.py 1 2 3` y `tools/train_boss.py`.
