# Avance de `correccion/action_plan.md` — auditoría de la rama `jaladas4`

Fecha de la auditoría: 2026-09-20 · Rama auditada: `jaladas4` (2 commits sobre `jaladas3`:
`6de8226` "Distingue capas ausentes de oferta cero", `84969db` "Agrega ayuda contextual al panel
de riesgo") · Árbol de trabajo limpio.

**Método.** Se verificó cada punto numerado del `action_plan.md` contra el repositorio: código en
`backend/src/chipos/`, `frontend/js/`, documentación en `docs/`/`plans/`, salidas reales en
`data/outputs/`, y la aplicación corriendo (`make serve`, medición de tareas largas con
`PerformanceObserver` en el navegador). No se aceptó ninguna afirmación de la documentación sin
comprobarla contra el artefacto que describe.

## Resumen ejecutivo

| Fase | Estado | Puntos abiertos |
|---|---|---|
| 0 — Documentación recuperada | ✅ completa | — |
| 1 — Horizontes h1/h3/h5 | ✅ completa | — |
| 2 — Backtest sin fuga de futuro | ⚠️ implementada, con un defecto de redacción y un resultado negativo sin resolver | 12, 16 |
| 3 — Incertidumbre calibrada | ⚠️ implementada, **criterio de aceptación no alcanzado** | 21 |
| 4 — Segmentos 0–17 | ✅ completa | — |
| 5 — Cuatro ramas | ✅ completa | — |
| 6 — Índice de oportunidad | ⚠️ fórmula implementada y usada, pero sin cablear en el pipeline | 28, 30 |
| 7 — Frontend Habitancia | ✅ prácticamente completa | 55 (paridad de fórmula), peso del payload |
| 8 — Cuelgue del mapa | ✅ corregido y verificado | 46 (script reproducible) |
| 9 — Mensaje, docs y demo | ❌ sin hacer | 59, 60 |

**Estado global:** 122+ pruebas de backend en verde (`make test`: 59 pruebas listadas, exit 0),
`make validar` pasa contra el contrato **v1.4**, la app carga y opera **sin un solo error de
consola**, y el cuelgue del mapa está resuelto (12 301 ms → **56 ms** de tarea larga, medido).
Lo que queda es poco, pero incluye **dos cosas que un juez puede ver**: `CLAUDE.md` describe un
contrato v1.2 que ya no existe, y el backtest declara que **el modelo no se adopta** con un texto
autogenerado contradictorio.

---

## Lo que está implementado y verificado

### FASE 0 — Documentación *(completa)*
- `docs/metodologia.md`, `plans/backend_plan.md`, `plans/frontend_plan.md` existen y están
  reescritos para esta revisión (no solo restaurados).
- `docs/estado_datos.md` ya no afirma que falte `backend/src/chipos/`.
- **Verificado:** todas las rutas `docs/*.md` y `plans/*.md` citadas desde `backend/src/chipos/*.py`
  y `frontend/js/*.js` existen en el árbol (0 faltantes).
- La convención ✅ / 🔄 de `metodologia.md` §0 y `backend_plan.md` §0 sustituye al prefijo
  `PENDIENTE` que pedía el punto 2; es equivalente y más legible.

### FASE 1 — Horizontes 1 / 3 / 5 *(completa)*
- `config.py:71` `HORIZONTES = {"h1": T_BASE+1, "h3": T_BASE+3, "h5": T_BASE+5}`;
  `T_HOR = HORIZONTES["h5"]` (2031.5); `HORIZONTES_OFERTA = ("h1","h3")`.
- `exportar.py:69-71` `ORDEN_HORIZONTES`/`FECHAS_HORIZONTE`/`ANIOS_HORIZONTE` con 2027-06 /
  2029-06 / 2031-06.
- **Verificado en la app:** el slider de horizonte muestra tres paradas `1 año(s) 2027`,
  `3 año(s) 2029`, `5 año(s) 2031`.
- Sin rastros de "7 años" en `frontend/js/textos.js`.

### FASE 2 — Backtest *(implementada)*
- `backend/src/chipos/backtest.py` existe con las cuatro validaciones del punto 11:
  `validar_adelgazamiento`, `validar_loao`, `backtest_oferta`, `comparar_censo_conapo`.
- No existe ninguna función `backtest_conapo` con orígenes móviles; el módulo lo declara
  explícitamente y `test_backtest.py` incluye el guardarraíl pedido (punto 15).
- `data/outputs/backtest.json` y `docs/backtest.md` se generan con cifras reales.
- Enganchado al pipeline: `exportar.main()` corre `io → panel → backtest → modelos → features →
  exportar`, y existe el target `make backtest`.
- `docs/metodologia.md` §4.1 conserva la explicación de por qué el backtest CONAPO original era
  inválido (punto 11b).

### FASE 3 — Sobredispersión e incertidumbre *(implementada)*
- `modelos.calcular_phi_por_alcaldia`: quasi-Poisson `φ_m = χ²(Pearson)/gl` agrupado por alcaldía,
  `φ_m ≥ PHI_MINIMO`, aplicado por AGEB dentro de `simular_oferta` (punto 18 ✅).
- `backtest.calibrar_piso_incertidumbre` + `_elegir_piso`: rejilla de candidatos, cobertura
  empírica sobre los folds, elección del más pequeño dentro de `[0.90, 0.97]` (punto 19 ✅ como
  procedimiento).
- Escenarios A/B de la caída DENUE 2024 en `features.construir_escenarios_oferta`, exportados en
  `data/outputs/diagnostico.json` bajo `oferta_escenarios_denue_2024` (punto 20 ✅).

### FASE 4 — Segmentos 0–17 *(completa)*
- `panel.SEGMENTOS_DEMANDA` con los seis segmentos; `construir_panel_demanda(segmento=...)`.
- `exportar.construir_capa_demanda_v14` emite `capas.demanda[cvegeo].segmentos.<seg>`;
  `validar_contrato` exige exactamente los seis.
- **Verificado en la app:** el selector "¿Qué población objetivo quieres explorar?" ofrece
  `0 a 17 (todas)` (por omisión), `Primera infancia 0-2`, `Preescolar 3-5`, `Primaria 6-11`,
  `Secundaria 12-14`, `Adolescencia 15-17`, con la nota de confianza `media` para 15–17.
- La UI dice "población objetivo", no "demanda" (punto 22 ✅).

### FASE 5 — Cuatro ramas *(completa)*
- `panel.construir_panel_oferta_celda` + `filtro_celda_educacion/salud/comercio`: series por celda,
  no una sola agregada (punto 37 ✅).
- `exportar.construir_capa_rama_v14` y `construir_capa_verde`; `capas.oferta` retirada,
  `capas.ramas.{educacion,salud,comercio,verde}` en su lugar; verde sin `h`
  (`horizontes_disponibles: []`) (puntos 36, 39 ✅).
- `docs/metodologia.md` §1.3 documenta los momentos históricos comparables por rama (punto 38 ✅).
- **Verificado:** `make validar` acepta `data/outputs/*.json` contra el contrato **v1.4**, y
  `verificar_suma_ageb_alcaldia` pasa.

### FASE 6 — Índice de oportunidad *(fórmula completa)*
- `features.indice_oportunidad` implementa los tres pasos exactos (rango percentil promediado →
  `clip((tasa_D − tasa_S)/K, ±0.15)` → `clip(N + ajuste, 0, 1)`), con `K_OPORTUNIDAD_DEFECTO = 5.0`
  y `K_SENSIBILIDAD = (3.0, 5.0, 8.0)`.
- `Ŝ=0` con `D̂>0` produce cobertura 0 y oportunidad máxima, **nunca `sin_datos`**; solo `D̂`
  inválido propaga `NaN`. Hay pruebas dedicadas en `test_features.py` y en
  `frontend/tests/pruebas_composicion.js` (punto 29 ✅, punto 34b parcial).
- `features.indice_disponibilidad` es un índice separado, orientado al revés (punto 33 ✅).
- `frontend/js/riesgo.js`: filtro de nivel de riesgo en tres escalones sobre la confianza de la
  demanda (punto 32 ✅; honesto sobre por qué no es un `p_dec` continuo).
- `capas.brecha` retirada del contrato; el resumen agregado sobrevive en `diagnostico.json`
  (punto 34 ✅).

### FASE 7 — Frontend Habitancia *(prácticamente completa)*
Existen y están cableados en `main.js`: `poblacion.js`, `busqueda.js`, `prioridades.js`,
`filtros.js`, `riesgo.js`, `vista_mapa.js`, `ranking.js`, `resumen.js`, `explicacion.js`,
`ficha.js`, `graficas.js`, `comparar.js`, `alcaldia.js`, `movil.js`, `ayuda.js`, `composicion.js`.

**Verificado en vivo** (`http://localhost:8000`):
- Dos niveles de información: resumen estructurado + "Entender esta zona →" (punto 48).
- Selector "Oportunidad de expansión" / "Disponibilidad para familias" (punto 49).
- Pesos por rama en 5 círculos + "Restablecer prioridades"; filtros por rama en pestañas
  (Vista general / Educación y cultura / Salud / Comercio / Áreas verdes) (puntos 50, 51).
- Ranking por AGEB con columnas Zona / Oportunidad relativa / Rama principal / Confianza; la
  alcaldía es solo navegación (punto 52).
- `comparar.js` conserva el escenario activo y no declara ganadora (punto 53).
- Iconos "?" como sistema de ayuda centralizado en `textos.js` (punto 56).
- `composicion.js` es el motor de composición cliente completo (punto 55), con **29/29 pruebas OK**
  en `frontend/tests/index_composicion.html`, incluida una de rendimiento < 80 ms.
- **Cero errores de consola** tras carga, clic en alcaldía y navegación.

### FASE 8 — Cuelgue del mapa *(corregido y medido)*
- Punto 41 ✅: `transition: transform` eliminada (`mapa.css:187` documenta la retirada).
- Punto 42 ✅: sin `filter` en `.mapa__alcaldia--recesivo`; `--recesivo-filtro` retirado de
  `tokens.css`.
- Punto 43 ✅: existe el `<g class="escenario">` envolvente (`mapa.js:232`); `aplicarTransform`
  escribe un solo atributo por fotograma.
- Punto 44 ✅: `vector-effect: non-scaling-stroke` retirado de las capas del escenario; el trazo se
  recalcula en `mapa.js#ajustarTrazoEscena` (solo queda en `.mapa__realce-contorno`, que es un
  único path de hover, no una capa masiva).
- Punto 45 ✅: `mapa.js:60` lee `matchMedia("(prefers-reduced-motion: reduce)")` y salta la
  animación.
- **Medición propia de esta auditoría** (clic en Cuauhtémoc, 153 AGEB, `PerformanceObserver` sobre
  `longtask`): **1 tarea larga de 56 ms** (antes: 58 tareas, 12 301 ms). Se confirmó además que las
  AGEB siguen pintándose y siendo interactivas tras el enfoque (33 de 81 puntos muestreados en el
  área del mapa devuelven `path.mapa__ageb`).

---

## Lo que FALTA

Ordenado por impacto. Cada punto trae archivo, qué hacer y cómo verificarlo.

### F-1 · `CLAUDE.md` quedó en el contrato v1.2 — *(punto 59, bloqueante de coherencia)*
`CLAUDE.md` sigue describiendo `version 1.2`, horizontes **3/5/7**, `capas.oferta`, `capas.brecha`
y "infancias 0–14", con un bloque JSON de ejemplo que ya no corresponde a nada de lo que el
pipeline emite. Es el primer archivo que abre cualquiera que llegue al repo, y contradice al
código en el punto más visible.

- **Archivos:** `CLAUDE.md` (secciones "Decisiones vigentes", "Contrato de salida" incl. el JSON de
  ejemplo, "Frontend").
- **Qué hacer:** contrato v1.4; horizontes h1/h3/h5 (2027-06 / 2029-06 / 2031-06);
  `capas.demanda[cvegeo].segmentos.<seg>` con los seis segmentos; `capas.ramas.{educacion, salud,
  comercio, verde}` con `celdas`; `capas.brecha` retirada; `HORIZONTES_OFERTA = ("h1","h3")`;
  población objetivo 0–17; nombre del producto (Habitancia) donde se describa la UI; mencionar
  `backtest.py` y la limitación CONAPO. Tomar el JSON de ejemplo de una entrada real de
  `data/outputs/prediccion_ageb.json`, recortada.
- **Verificación:** `grep -n "1\.2\|h7\|capas.oferta\|capas.brecha\|0–14" CLAUDE.md` no devuelve
  nada que describa el contrato vigente. Cierra también la tarea B20 de `plans/backend_plan.md`.

### F-2 · El resumen del backtest se contradice a sí mismo — *(punto 12)*
`backend/src/chipos/backtest.py` línea ~728 genera:

> `5. **Modelo NO SE ADOPTA** según el criterio de CLAUDE.md (supera al baseline en las 3 validaciones).`

El paréntesis está **hardcodeado** y solo tiene sentido en el caso positivo. Hoy `docs/backtest.md`
publica esa frase, que dice una cosa y la contraria en la misma línea, justo en el archivo que la
rúbrica valora más.

- **Qué hacer:** que el paréntesis se derive de `adopcion` (qué validación falló y por qué), no de
  una cadena fija. Caso actual real: la demanda sí supera al baseline (adelgazamiento), pero
  **la oferta NO** (`modelo_poisson_2016_2019` peor que `baseline_s_constante` en MAE y F1) y
  **LOAO cubre 1.00**, fuera de `[0.90, 0.97]`.
- **Qué hacer además (lo de fondo):** `CLAUDE.md` obliga a no adoptar un modelo que no supere al
  baseline. Hoy la capa de oferta se publica igual. El plan (punto 12) dice que en ese caso el
  hallazgo se **reporta y se discute**, no se esconde. Falta esa discusión explícita: una sección
  en `docs/backtest.md` que diga qué se hace con la oferta (p. ej. publicarla con tope de confianza
  y etiqueta visible, o degradarla a "nivel actual sin proyección" como la rama verde), y por qué.
- **Verificación:** `docs/backtest.md` no contiene ninguna frase internamente contradictoria; la
  decisión sobre la oferta está escrita y es la que el código ejecuta.

### F-3 · La cobertura del IC95 no cae en `[0.90, 0.97]` — *(punto 21, criterio de aceptación NO alcanzado)*
Cifras reales de `docs/backtest.md`: LOAO cobertura **1.00**; adelgazamiento 0.98–1.00; piso
calibrado `sigma_min = 0.0` tanto en demanda (cobertura 0.99) como en oferta (1.00).

El procedimiento del punto 19 está bien implementado, pero es **estructuralmente incapaz** de
cerrar este hueco: un piso de incertidumbre solo puede **ensanchar** el intervalo, y aquí el
problema es que ya **sobrecubre**. El paso 19.4 previó ese caso ("si 0.000 ya sobrecubre, no se
añade piso: se documenta"), pero la *Definición de terminado* del plan sigue exigiendo
`[0.90, 0.97]`, y hoy no se cumple.

- **Qué hacer (decisión, no código a ciegas):** elegir una de dos y documentarla:
  (a) aceptar la sobrecobertura como conservadora, marcar el criterio de la DoD como
  explícitamente relajado en `docs/backtest.md` con la razón (el IC es conservador, no
  anticonservador: falla del lado seguro); o
  (b) añadir al calibrador la capacidad de **estrechar** (un factor multiplicativo sobre `σ` en
  `[0.5, 1.0]`, elegido por la misma rejilla y la misma banda de cobertura).
  La opción (a) es defendible y barata; la (b) es más trabajo y arriesga empeorar la calibración
  real. **Recomendación: (a)**, escrita, no callada.
- **Verificación:** existe una prueba en `test_backtest.py` que afirma la banda que efectivamente
  se decidió (no una que pase por casualidad), y `docs/backtest.md` lo explica en una línea.

### F-4 · Fase 6 no está cableada al pipeline — *(puntos 28 y 30)*
`features.cobertura_proyectada`, `indice_oportunidad`, `sensibilidad_indice_oportunidad` e
`indice_disponibilidad` están implementadas y con pruebas unitarias, pero **nadie las llama fuera
de los tests**: `construir_diagnostico` solo arma `brecha` + `oferta_escenarios_denue_2024`, y
`exportar.py` no las importa. Consecuencias concretas:

1. **Punto 30 (sensibilidad `K ∈ {3,5,8}`) no se publica.** `diagnostico.json` no tiene la clave;
   las AGEB cuyo orden cambia entre extremos nunca se marcan. Era obligatorio ("sensibilidad
   obligatoria").
2. **Punto 28 no se cumple como está escrito.** El plan pedía la cobertura proyectada "sobre las
   mismas réplicas Monte Carlo (no sobre las medianas — así el intervalo sale gratis)". El índice
   se calcula hoy **solo** en `frontend/js/composicion.js`, a partir de `nivel_base` + `delta_pct`
   (es decir, de las medianas). El intervalo de la cobertura se pierde. La decisión es defendible
   —los filtros del usuario cambian `Ŝ`, así que el índice **tiene** que recalcularse en cliente—
   pero no está documentada como desviación, y el intervalo que el plan daba por gratis no existe.
3. **Riesgo de divergencia de fórmula.** La misma fórmula vive dos veces: `features.py` (Python) y
   `composicion.js` (JS). Nada garantiza que no se separen.

- **Qué hacer:** (i) añadir a `construir_diagnostico` el bloque de sensibilidad `K` sobre el
  universo real de AGEB y escribirlo en `diagnostico.json`; (ii) escribir en
  `docs/metodologia.md` §10.1-§10.3 la desviación del punto 28 (cliente sobre niveles, no sobre
  réplicas) con su razón; (iii) una prueba de **paridad** que alimente los mismos vectores a
  `features.indice_oportunidad` y a `composicion.indiceOportunidad` y exija el mismo resultado
  (basta con exportar un fixture JSON desde Python y consumirlo en
  `frontend/tests/pruebas_composicion.js`).
- **Verificación:** `diagnostico.json` trae la sensibilidad; la prueba de paridad falla si se toca
  una fórmula sin tocar la otra.

### F-5 · Los mocks siguen en el contrato v1.2 — *(punto 8)*
`frontend/mock/prediccion_ageb.json` y `prediccion_alcaldia.json` declaran `version: "1.2"` (con
horizontes 1/3/5, o sea a medias). El punto 8 pedía regenerarlos a v1.4 al cerrar la Fase 6.
`generar_mock.py` no se actualizó. Los fixtures v1.1 y el inválido deben conservarse tal cual
(son el camino de degradación y el caso de error).

- **Verificación:** `frontend/mock/prediccion_*.json` (los no `_v11`) declaran `1.4` y pasan
  `validar_contrato`; `frontend/tests/index.html` sigue en verde.

### F-6 · Falta el script reproducible de medición del mapa — *(punto 46)*
El cuelgue está corregido y medido en esta auditoría (56 ms en Cuauhtémoc), pero el plan pedía
**incluir el script de medición en `frontend/tests/`** y barrer **las 16 alcaldías** con el
objetivo de ninguna tarea > 200 ms. No existe ningún archivo con `PerformanceObserver` en el repo.

- **Qué hacer:** `frontend/tests/medir_mapa.html` + `medir_mapa.js` que recorra las 16 alcaldías,
  registre `longtask` por enfoque e imprima una tabla con máximo y total por alcaldía, marcando en
  rojo cualquier tarea > 200 ms.
- **Verificación:** abrir la página produce una tabla de 16 filas, todas en verde.

### F-7 · El backtest no aflora en el frontend con cifras — *(punto 16)*
`frontend/js/textos.js` tiene un bloque "Qué tan bien acertó el modelo en el pasado", pero es
**prosa sin una sola cifra**, vive en el drawer de metodología (no en el Nivel 2 de la zona), y
—más grave— afirma que "la demanda superó esa comparación; la oferta acierta mejor la dirección
del cambio que su magnitud exacta", que es una manera suave de no decir que **la oferta no supera
al baseline**. El plan pedía "dos o tres cifras, en lenguaje llano" en el Nivel 2.

- **Qué hacer:** dos o tres cifras reales leídas de `backtest.json` (o fijadas y citadas), en el
  Nivel 2 de "Entender esta zona", y una frase que no maquille el resultado de la oferta.
  Coordinar con F-2: lo que se decida ahí es lo que debe decir esta tarjeta.
- **Verificación:** la sección "¿Qué tan confiable es la estimación?" muestra cifras, y lo que dice
  coincide con `docs/backtest.md`.

### F-8 · Guion de demo — *(punto 60)*
No existe ningún archivo de guion en `docs/` ni `plans/`. El plan pide un guion de 3-4 minutos
ensayado con el caso de jueces de `frontend_requisitos.md` §24 (primaria pública + hospitales y
clínicas + comercio de primera necesidad + áreas verdes recreativas, 3 años, educación y salud en
alta prioridad).

- **Qué hacer:** `docs/guion_demo.md` con la secuencia exacta de clics y lo que se dice en cada
  paso, incluyendo dónde se enseña la limitación del backtest y el "ausencia de datos ≠ ausencia de
  demanda".
- **Verificación:** el guion se ejecuta de principio a fin sin recargar la página y sin errores de
  consola.

---

## Verificaciones pendientes (no son código faltante, son comprobaciones no hechas)

- **Determinismo de `make pipeline`.** No se reejecutó en esta auditoría (es caro). La DoD exige
  dos corridas byte a byte idénticas de `backtest.json` y de los dos `prediccion_*.json`.
- **Lighthouse accesibilidad ≥ 90.** No se midió.
- **Peso del payload.** `frontend/data/prediccion_ageb.json` pesa **44 MB** (`data/outputs/` igual).
  El contrato v1.4 (6 segmentos × 3 horizontes × N celdas por rama × 2 453 AGEB) lo justifica, pero
  es una descarga de 44 MB antes de que el mapa pinte nada. No es un punto del `action_plan.md`, y
  por eso no se cuenta como faltante — pero es el riesgo de demo más grande que queda vivo, y en una
  red de auditorio puede costar la presentación. Medirlo antes de decidir si hay que hacer algo.

---

## Instrucción para la siguiente iteración

El backend está esencialmente terminado y el frontend también. Lo que falta son **ocho tareas
acotadas (F-1 … F-8)**, ninguna de arquitectura. El orden recomendado es:

1. **F-1** (`CLAUDE.md`) — media hora, cierra la incoherencia más visible.
2. **F-2** y **F-3** juntas — son la misma conversación (qué decimos sobre un modelo cuya capa de
   oferta no supera al baseline y cuyo IC sobrecubre). F-3 requiere **elegir** entre (a) y (b);
   la recomendación es (a).
3. **F-4** — cablear la sensibilidad `K` y añadir la prueba de paridad Python↔JS.
4. **F-5**, **F-6**, **F-7**, **F-8** — independientes entre sí, paralelizables.

**Regla de trabajo para quien implemente:** después de cada tarea, `make test` y, si tocó salidas,
`make validar`. No abrir una tarea nueva con la anterior en rojo. No tocar `data/processed/` ni
`data/reference/`. No reabrir decisiones de modelado ya cerradas: F-1 … F-8 son escritura,
cableado y pruebas, no rediseño.
