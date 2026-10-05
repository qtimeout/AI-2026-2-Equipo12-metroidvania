# MetroidvaniaPython — Paso Olvidado — Equipo 12

## Problema y quién lo sufre
En los Metroidvania 2D los enemigos suelen perseguir con reglas simples y se atascan en paredes, techos y plataformas, lo que vuelve el juego predecible. Los diseñadores de juegos indie necesitan enemigos que naveguen el mapa (caminar, caer, saltar) sin bloquear el juego. En nuestro Metroidvania inspirado en *Hollow Knight* (5 niveles; el 5.º es una pelea contra un jefe) medimos qué agente lleva a los Husks hasta el jugador más rápido y a qué costo computacional.

**Enemigos del nivel 1:** 2 Husks saltadores (3 de vida, 6 celdas/s), 1 Husk errante (2 de vida, 4.5 celdas/s) y 1 Husk cornudo (4 de vida, 5 celdas/s). Todos navegan con el mismo grafo. En el menú, **«Enemigos»** asigna una técnica a todos los enemigos o **«Aleatorio (mixto)»**, que da a cada enemigo una técnica al azar (p. ej. errante → BFS, cornudo → A\*). Cada enemigo lleva una etiqueta con su técnica.

## Modo base
`Aleatorio`: en cada nodo, el Husk elige al azar una arista del grafo de navegación (caminar, caer o saltar).

## Técnicas comparadas
- **Parte 1 (bloque 1):** `Reflejo` (agente reflejo: toma la arista que más lo acerca al jugador en distancia Manhattan) → `BFS` (agente basado en objetivos: ruta con menos aristas) → `A*` (agente basado en objetivos: ruta de menor costo en celdas, con heurística Manhattan). BFS y A* replanifican la ruta completa en cada nodo y ejecutan su primera arista.
- **Parte 2 (bloque 2):** por definir (p. ej., KNN / DT / MLP imitando al mejor agente de búsqueda).

El estado es la celda pisable `(c, r)`: el nivel 1 tiene 125 nodos y 780 aristas, y el grafo es fuertemente conexo. Las acciones son `walk`, `fall` y `jump` (hasta 3×3 celdas). El costo es el número de celdas recorridas, por eso la distancia Manhattan nunca sobreestima.

## Resultados
Laboratorio IA (`python app/benchmark.py --rounds 100`): un solo Husk saltador, semilla 2026, mismos 100 objetivos para cada técnica, presupuesto de 200 nodos/frame y límite de 20 s por corrida. El laboratorio usa un único tipo de enemigo para que la velocidad y la vida no favorezcan a ninguna técnica.

| Técnica | Métrica: alcanza al objetivo | T. alcance (solo éxitos) | **T. penalizado (fallo = 20 s)** | Pasos | Nodos/decisión | ms/decisión | Corridas |
|---------|------------------------------|--------------------------|----------------------------------|-------|----------------|-------------|----------|
| Aleatorio (base) | 7 % | 9.67 s | 19.28 s | 14.9 | 1.0 | 0.001 | 100 |
| Reflejo | 40 % | 6.40 s | 14.56 s | 6.3 | 1.0 | 0.003 | 100 |
| BFS | 88 % | 10.12 s | 11.30 s | 9.5 | 57.3 | 0.060 | 100 |
| **A\*** | **100 %** | 9.28 s | **9.28 s** | 24.9 | 36.1 | 0.154 | 100 |

**Comparación por pares** (% de los mismos 100 objetivos en que la fila llega estrictamente antes que la columna; un fallo cuenta como 20 s):

| Fila gana a columna | Aleatorio | Reflejo | BFS | A\* |
|---------------------|-----------|---------|-----|-----|
| Aleatorio (base) | — | 0 % | 0 % | 0 % |
| Reflejo | 40 % | — | 14 % | 0 % |
| BFS | 88 % | 70 % | — | 0 % |
| **A\*** | 100 % | 100 % | 100 % | — |

**Análisis.**
- **Sin sesgo, el orden es claro: A\* < BFS < Reflejo < Aleatorio** en tiempo penalizado (9.28 / 11.30 / 14.56 / 19.28 s). La columna "T. alcance" engañaba: el Reflejo parecía el más rápido (6.40 s) porque solo promedia el 40 % de objetivos fáciles que resuelve.
- **A\* gana a BFS en los 100 objetivos, sin un solo empate**, con 0.55 a 4.12 s de ventaja. BFS minimiza el número de aristas y prefiere un salto largo a tres pasos cortos, pero cada salto recorre más celdas. A\* minimiza las celdas: es óptimo (verificado contra Dijkstra en 500 pares) y expande un 37 % menos nodos (36.1 contra 57.3) gracias a la heurística Manhattan.
- **Costo:** A\* tarda más por decisión (0.154 contra 0.060 ms) porque la cola de prioridad cuesta más que la FIFO, y toma más decisiones porque prefiere aristas cortas.
- **Dónde pierde el ganador:** con el presupuesto reducido a 5 nodos/frame (`--budget 5`), A\* baja al 77 % y BFS al 74 %. El enemigo espera varios frames en cada nodo mientras piensa, y A\*, al dar más pasos, paga esa espera más veces.
- La tabla de la partida con humano (tecla `M`) suma los episodios de cada técnica con varios enemigos de distinto tipo. Sirve para la demostración, no para concluir: la comparación válida es la del laboratorio.

## Cómo ejecutarlo
- **Enlace público:** _pendiente (itch.io con pygbag)_.
- **Repositorio:** https://github.com/qtimeout/AI-2026-2-Equipo12-metroidvania
- **Local, escritorio:** `pip install -r requirements.txt` y luego `python app/main.py`.
- **Local, navegador:** `python -m pygbag app` y abrir `http://localhost:8000`.
- **Benchmark en consola:** `python app/benchmark.py --rounds 100 --seed 2026 --budget 200`.
- **Regenerar el arte** (requiere `Sprites/`, que no se versiona): `python tools/build_assets.py`. Para validar un nivel: `python tools/check_level.py 1`.
- **Controles:** flechas/A-D para moverse, Espacio/Z para saltar, X para atacar y C para curarse (gasta alma). Las teclas `1..4` asignan una técnica a todos los enemigos y `0` activa el modo mixto, `M` muestra u oculta la tabla, `G` el grafo, `TAB` alterna entre partida y laboratorio (`F` cambia la velocidad) y `ESC` vuelve al menú.
