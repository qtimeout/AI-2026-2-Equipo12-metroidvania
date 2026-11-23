# Resultados detallados — Paso Olvidado (Equipo 12)

Tablas completas, comparación por pares, validación de los modelos y análisis. El resumen está en el [README](../README.md).

## Resultados — Parte 1 (búsqueda, nivel 1)
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

## Resultados — Parte 2 (aprendizaje automático)
**Datos.** `tools/make_dataset.py N` graba la decisión de A\* en cada par (nodo del enemigo, nodo del jugador) del nivel N: 15 500 demostraciones del nivel 1, 20 592 del nivel 2 y 42 230 del nivel 3, con 16 características y 10 clases de movimiento muy desbalanceadas. `tools/train_models.py` separa 80 % para entrenamiento y 20 % para prueba (estratificado, semilla 2026) y elige hiperparámetros con **validación cruzada de 5 particiones** optimizando el F1 macro. **El juego predice en Python puro** (`app/game/ml/models.py`), porque en el navegador no hay scikit-learn.

**1) Validación offline** (modelos del juego, entrenados con los niveles 1, 2 y 3; 62 657 muestras de entrenamiento y 15 665 de prueba):

| Modelo | Hiperparámetros (CV) | Exactitud CV | F1 macro CV | Exactitud prueba | F1 macro prueba |
|--------|----------------------|--------------|-------------|------------------|-----------------|
| KNN | k = 1 | 0.985 ± 0.001 | 0.964 ± 0.016 | 0.989 | 0.973 |
| Árbol | sin límite de profundidad | 0.988 ± 0.001 | 0.963 ± 0.016 | 0.991 | 0.973 |
| MLP | capas (64, 32), ReLU | 0.971 ± 0.003 | 0.908 ± 0.019 | 0.969 | 0.913 |

Línea base: predecir siempre la clase más frecuente da 0.447 de exactitud.

**2) Generalización a un mapa no visto.** Con modelos entrenados con el nivel 1 y evaluados en el 2, la exactitud cae de 0.99 a 0.70 y el árbol pasa del 99 % al **42 %** de alcance en el juego (por debajo del Reflejo, 48 %). Con modelos entrenados con los niveles 1 y 2 y evaluados en el 3, la exactitud es de 0.78 a 0.81 y el F1 macro de 0.46 a 0.51. **La búsqueda generaliza a cualquier mapa porque razona sobre el grafo; los modelos memorizan los mapas que vieron.**

**3) En el juego, con los modelos finales** (`--seeds 2026 2027 2028`; 3 semillas × 100 objetivos por nivel; alcanza % / tiempo penalizado en s):

| Técnica | Nivel 1 | Nivel 2 | Nivel 3 |
|---------|---------|---------|---------|
| Aleatorio (base) | 5 % / 19.57 | 4 % / 19.73 | 2 % / 19.83 |
| Reflejo | 37 % / 14.87 | 52 % / 13.05 | 79 % / 10.40 |
| BFS | 86 % / 11.91 | 100 % / 6.99 | 100 % / 7.76 |
| **A\*** | **100 % / 9.80** | **100 % / 5.42** | **100 % / 6.07** |
| KNN (índice) | 97 % / 10.46 | 98 % / 6.00 | 98 % / 6.80 |
| **Árbol** | 99 % / 9.83 | 99 % / 5.57 | 98 % / 6.32 |
| MLP | 67 % / 13.01 | 84 % / 7.74 | 76 % / 9.29 |

**Análisis.**
- **El árbol es el mejor imitador:** prácticamente iguala a A\* en los tres niveles (a menos de 0.3 s) y decide unas 8 veces más rápido (≈0.02 contra ≈0.16 ms), porque no busca en el grafo.
- **Exactitud alta no basta.** El MLP acierta el 97 % de las jugadas sueltas, pero en el juego los errores se encadenan: una jugada mala lo lleva a un estado que el experto nunca visitó y empieza a oscilar.
- **El KNN por fuerza bruta no escala; el indexado sí.** Con 62 657 demostraciones, compararlas todas en Python puro cuesta 116 ms por decisión: con el presupuesto calibrado (1 unidad ≈ 1 nodo de A\* ≈ 2 comparaciones), el enemigo se quedaba decenas de frames pensando en cada nodo y alcanzaba solo el 0–7 %. Lo resolvimos con un **índice por cubetas con poda**, sin cambiar el modelo: las demostraciones se agrupan por posición del enemigo y movimientos disponibles (475 cubetas). Se recorren de menor a mayor cota inferior de distancia y se descartan las que no pueden contener un vecino más cercano. En 300 estados de prueba **predice exactamente lo mismo que la búsqueda completa**, comparando 157 puntos en promedio en vez de 62 657 (1.6 ms contra 116 ms; 73 veces más rápido). Cobramos también el cálculo de las cotas contra el presupuesto, para no darle ventaja sobre A\*. Ahora alcanza el 97–98 %.
- **Información:** los modelos solo perciben información local; A\* conoce el grafo completo.

## Resultados — Jefe final (Hornet)
**Problema.** En cada pausa entre ataques, Hornet elige **qué ataque usar** —lanza (aguja horizontal), embestida (carga por el suelo) o salto (cae sobre el jugador)— para acertarle. **Métrica:** % de ataques que aciertan y aciertos por minuto, contra un **jugador robot sembrado** (`PlayerBot`) cuya trayectoria es idéntica para todas las estrategias; cada ronda dura 60 s simulados.

| Estrategia | Tipo | Cómo decide |
|---|---|---|
| Aleatorio (base) | modo base | ataque al azar |
| Reflejo | agente reflejo (B1) | si el jugador está arriba, salto; si está cerca, embestida; si está lejos, lanza |
| Utilidad (a mano) | agente basado en utilidad (B1) | utilidad = P(acierto) / duración; P sale de un modelo geométrico escrito a mano que predice dónde estará el jugador |
| Utilidad (aprendida) | utilidad + regresión logística (B2) | misma utilidad, pero P(acierto \| ataque, situación) la estima una regresión logística con términos de grado 2 |

**Regresión logística** (`tools/train_boss.py`): 1 896 ataques registrados con el jefe aleatorio y la semilla 7 (distinta de las de evaluación), validación cruzada de 5 particiones:

| Ataque | Acierto real | Exactitud CV | AUC CV | Brier (base) |
|---|---|---|---|---|
| Lanza | 0.69 | 0.836 | 0.826 | 0.127 (0.213) |
| Embestida | 0.63 | 0.723 | 0.755 | 0.184 (0.233) |
| Salto | 0.54 | 0.540 | 0.569 | 0.245 (0.249) |

**En la arena** (`python app/benchmark.py --level 4 --rounds 30 --seeds 2026 2027 2028 2029 2030`; 5 semillas × 30 rondas de 60 s):

| Estrategia | Acierto % | Aciertos/min | Corridas |
|---|---|---|---|
| Aleatorio (base) | 63.6 ± 1.4 | 20.3 ± 0.4 | 150 |
| Reflejo | 53.3 ± 2.0 | 16.2 ± 0.7 | 150 |
| Utilidad (a mano) | 64.3 ± 1.2 | 22.8 ± 0.4 | 150 |
| **Utilidad (aprendida)** | **72.5 ± 0.5** | **26.5 ± 0.2** | 150 |

**Análisis.**
- **La utilidad aprendida gana en las 5 semillas:** acierta 9 puntos más que el azar y saca un 31 % más de aciertos por minuto.
- **Un agente de utilidad vale lo que vale su modelo del mundo.** El modelo escrito a mano estaba mal calibrado: en una primera versión predecía 100 % de acierto para embestidas que acertaban el 34 %, y la utilidad a mano quedó *por debajo* del azar. Aprender P(acierto) con datos corrigió eso.
- **El Reflejo es el peor.** Sus reglas («si está lejos, lanza») ignoran que el jugador se mueve.
- **Límite:** el modelo del salto apenas supera al azar (AUC 0.57), así que la versión aprendida casi nunca salta. Con más características, como la altura del salto del jugador, podría mejorar.


## Parámetros en vivo (para «cambie este parámetro y prediga»)
En la partida y en el laboratorio: `+`/`−` presupuesto de cálculo por frame, `H` peso de la heurística de A\* y `N` vecinos del KNN. Cada cambio reinicia la tabla, así que cada tabla mide **una sola** configuración. En consola se reproduce con `python app/benchmark.py --peso-h W --k K --budget B`. Nivel 1, semilla 2026, 50 objetivos:

| Parámetro | Valor | Resultado | Por qué |
|---|---|---|---|
| Peso de la heurística de A\* | 0 (costo uniforme) | 100 %, 9.16 s, **55.4 nodos** | Sin heurística, explora en todas direcciones como Dijkstra: sigue siendo óptimo, pero expande más. |
| | **1 (A\* clásico)** | 100 %, 9.16 s, **36.0 nodos** | Heurística admisible: óptimo y con menos nodos. |
| | 2 | 100 %, 9.62 s, 24.5 nodos | Sobreestima: expande menos, pero elige rutas peores. |
| | 5 | **88 %**, 11.11 s, 15.1 nodos | Casi voraz: rápido para decidir, pero falla objetivos. |
| k del KNN | **1** | 96 % de alcance | Copia la jugada del estado más parecido. |
| | 3 | 78 % | Votan estados con otro objetivo y diluyen la jugada correcta. |
| | 5 | 74 % | Peor aún. |
| Presupuesto por frame | 200 → 5 | A\* 100 % → 77 %, BFS 88 % → 74 % | El enemigo espera más frames en cada nodo mientras piensa. |
