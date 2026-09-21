# Plan de acción — `rubrica.md`, `detalles_a_tratar.md` y `frontend_requisitos.md`

Fecha: 2026-09-20 (revisión sobre la de 2026-09-19) · Rama: `jaladas2` · Estado auditado: 122
pruebas de backend en verde, `make pipeline` reproducible, frontend funcional sin errores de
consola.

El **modelo de demanda por AGEB se conserva** (tasa log-lineal + contracción EB + control CONAPO):
sigue siendo la pieza mejor pensada del proyecto. Lo que sí cambia de raíz en esta revisión es el
**producto de frontend**: `correccion/frontend_requisitos.md` define **Habitancia**, que sustituye
al visor de dos capas (demanda/oferta) por un explorador de cuatro ramas ponderables con filtros,
dos tipos de búsqueda y comparación entre alcaldías. Esta revisión también corrige tres defectos de
diseño que el propio plan anterior tenía (piso de incertidumbre elegido a ojo, backtest de CONAPO
con fuga de futuro, índice de oportunidad sin fórmula exacta) — ver Fases 2, 3 y 6. Cada punto trae:
archivos, criterio de aceptación y verificación.

Contrato de salida: los cambios de las fases 1, 4, 5 y 6 **rompen el contrato** y lo llevan de v1.2
a **v1.4** directamente (no se publica una v1.3 intermedia: los tres cambios de fondo — horizontes,
segmentos, ramas — comparten el mismo trabajo sobre `exportar.py`). El adaptador v1.1 del frontend
(`frontend/js/api.js`) se conserva como camino de degradación.

---

## 0. Hallazgos verificados en esta auditoría (contexto)

Lo que la revisión afirmaba, confirmado contra el repo:

| # | Hallazgo | Evidencia |
|---|---|---|
| 0.1 | `backtest.py` no existe | `config.py:44-45` declara `RUTA_BACKTEST_JSON` y `RUTA_BACKTEST_MD`; no hay módulo ni `tests/test_backtest.py`; `exportar.main()` lo dice en su propio docstring |
| 0.2 | Documentación borrada, no solo desactualizada | el commit `1550ba5` **eliminó** `docs/metodologia.md`, `plans/backend_plan.md` y `plans/frontend_plan.md` (736 líneas). Todo el código las cita como fuente de verdad |
| 0.3 | Horizontes 3/5/7 | `config.py:78`, `exportar.py:54-56` |
| 0.4 | Veredictos poco discriminantes | AGEB h3: `baja` 2181, `se_mantiene` 180, `sube` 6, `sin_datos` 86 (de 2453) |
| 0.5 | IC degenerados en oferta | `agregado_cdmx.oferta.h3.ic95 = [-6.9, -6.9]`; ancho 0.0 |
| 0.6 | Brecha mezcla años | `features.py` divide `s_2024` entre `d_2020`; es histórica, no proyectada |
| 0.7 | Fuentes descargadas sin usar | `areas_verdes/`, `espacios_publicos/`, `comercios/`, `salud/`, `enut/` solo aparecen en `tools/profile_data.py`; el backend no las lee |
| 0.8 | **El mapa cuelga el navegador** | Reproducido: un clic en Cuauhtémoc generó **58 tareas largas por 12 301 ms** de hilo principal bloqueado (peor tarea 1 128 ms). Causa aislada en Fase 8.1 |
| 0.9 | El plan anterior también tenía defectos de diseño | Piso de incertidumbre con criterio de aceptación "ancho ≥ 0.2" (arbitrario, no calibrado); backtest de CONAPO con orígenes móviles sobre una sola vintage reconciliada (fuga de futuro); índice de oportunidad descrito en prosa, sin fórmula, pesos ni tratamiento de oferta cero. Corregidos en Fases 2, 3 y 6 |
| 0.10 | `correccion/frontend_requisitos.md` redefine el producto | Habitancia: cuatro ramas (educación, salud, comercio, verde) con pesos y filtros del usuario, dos tipos de búsqueda, comparación entre alcaldías, población objetivo 0–17. El visor de dos capas queda superado, no solo "por mejorar" |

Dos cosas **buenas** que conviene no tocar: la separación demanda/oferta y la regla de veredicto
con banda muerta. La crítica de fondo de la revisión (§7-8) no pide otro algoritmo, pide
**cerrar la validación, la incertidumbre y la combinación oferta-demanda**. Este plan sigue ese orden.

---

## FASE 0 — Recuperar la documentación borrada *(bloqueante, ~30 min)*

Sin esto, ninguna otra fase es revisable: `modelos.py`, `config.py` y `exportar.py` citan §§ de
archivos que ya no existen, y los jueces pueden abrir el repo.

1. **Restaurar los tres archivos desde git** y volver a commitearlos:
   ```bash
   git checkout 1550ba5^ -- docs/metodologia.md plans/backend_plan.md plans/frontend_plan.md
   ```
2. **Marcar en `docs/metodologia.md` §4 lo que aún no está implementado.** Hoy §4 describe cuatro
   validaciones (adelgazamiento binomial, leave-one-alcaldía-out, backtest CONAPO, comparación con
   baseline) como si existieran. Hasta terminar la fase 2, cada una lleva el prefijo `PENDIENTE`.
3. **Actualizar `docs/estado_datos.md`**: el bloque "Pendiente para el modelado" dice que falta
   implementar `backend/src/chipos/`, que ya existe. Dejar solo lo realmente pendiente.
4. **Verificación:** `grep -rn "metodologia.md\|backend_plan.md" backend/src` no debe apuntar a
   archivos inexistentes.

> Criterio de aceptación: todo `.md` citado por el código existe en el árbol de trabajo.

---

## FASE 1 — Horizontes 1 / 3 / 5 años *(bloqueante de rúbrica, ~2 h)*

`rubrica.md` §5: *"Proyectar un horizonte de uno, tres o cinco años"*. Sea que se lea como "elige
uno" o como "los tres", **h1 / h3 / h5 cumple ambas lecturas**; 3/5/7 no cumple ninguna.

5. `backend/src/chipos/config.py`: `HORIZONTES = {"h1": T_BASE+1, "h3": T_BASE+3, "h5": T_BASE+5}`,
   `T_HOR = HORIZONTES["h5"]` (ancla CONAPO a 2031.5, no 2033.5 — dentro del rango publicado y
   coincidente con el punto de control final que pide la revisión). `HORIZONTES_OFERTA` pasa a
   `("h1", "h3")`: con tres cortes DENUE y el quiebre de 2024, tres años sigue siendo el techo
   defendible, pero un año sí es reportable.
6. `backend/src/chipos/exportar.py:52-56`: `ORDEN_HORIZONTES = ("h1","h3","h5")`,
   `FECHAS_HORIZONTE = {"h1":"2027-06","h3":"2029-06","h5":"2031-06"}`,
   `ANIOS_HORIZONTE = {"h1":1,"h3":3,"h5":5}`. `VERSION_CONTRATO` se deja en `"1.2"` hasta que las
   Fases 4-6 completen el salto a **`"1.4"`** en un solo cambio (no se publica una `"1.3"`
   intermedia solo por los horizontes — ver cabecera de este documento).
7. `frontend/js/config.js`: los 3 horizontes ya son compatibles con el adaptador existente; no hace
   falta tocar `VERSIONES_CONTRATO_ACEPTADAS` todavía (se añade `"1.4"` al cierre de la Fase 6).
   **No hay que tocar `horizonte.js`**: el slider ya se construye desde el array `horizontes` del
   JSON y ordena por `anios` (`ordenarHorizontes`). Sí hay que revisar `frontend/js/textos.js`
   §"Por qué a 7 años hay más incertidumbre" → reescribir como "a 5 años".
8. `frontend/mock/generar_mock.py`: regenerar los fixtures con tres horizontes (1/3/5); conservar
   `prediccion_ageb_v11.json` y el inválido tal cual. Se vuelven a regenerar en v1.4 al cierre de la
   Fase 6 — evitar dos pasadas de datos de fixture si se puede secuenciar Fase 1 justo antes de 4-6.
9. Actualizar `CLAUDE.md` ("Contrato de salida", ejemplo JSON y prosa de horizontes) y
   `docs/metodologia.md` §2/§7.
10. **Verificación:** `make pipeline && make validar && make test`; abrir el frontend y comprobar
    que el slider tiene 3 paradas etiquetadas 2027 / 2029 / 2031.

> Nota honesta para la presentación: el veredicto y la confianza **no cambian entre horizontes**
> (dependen de la tasa anual, no del horizonte); solo cambian `delta_pct` e `ic95`. Es una
> propiedad del modelo log-lineal, no un bug — conviene decirlo en el drawer de metodología antes
> de que un juez lo note.

---

## FASE 2 — Validación retrospectiva real, sin fuga de futuro *(bloqueante de rúbrica, ~1 día)*

`rubrica.md` §5 y §6 la exigen ("validación retrospectiva", "requisitos técnicos mínimos"), y §7
la pone primero en la evaluación. Es el hueco más grave. El diseño está en `plans/backend_plan.md`
§6 (tarea B9) — solo falta implementarlo.

> **Corrección sobre la versión anterior de este plan.** El punto 11 original proponía
> `backtest_conapo(conapo, origenes=(2000,2005,2010,2015), horizontes=(1,3,5))` "sobre la serie
> municipal CONAPO 1990-2040". **Es inválido y se retira.** `data/processed/conapo/pobproy_quinq1.csv`
> es **una sola vintage**, reconciliada en bloque contra el Censo 2020
> (`tools/build_conapo.py`: "conciliada con las proyecciones estatales 2020-2070, base Censo 2020").
> El valor que ese archivo asigna a 2005 o a 2015 ya fue ajustado con información de 2020: usarlo
> como si fuera una serie de orígenes independientes es exactamente el error de validar una
> proyección con otra proyección construida con información futura, presentada como si fuera la
> realidad observada. Detalle completo, la reclasificación de la comparación censo-CONAPO (ya no es
> un backtest, es una comparación de fuentes) y la vía honesta para resolverlo de verdad (una
> vintage CONAPO publicada antes del Censo 2020): `docs/metodologia.md` §4.1.

11. **Crear `backend/src/chipos/backtest.py`** con las validaciones que sí son válidas con los datos
    disponibles (`plans/backend_plan.md` §6):
    - `backtest_oferta(panel_o)` — **el único backtest temporal genuino disponible hoy**: origen
      2019-11 (ajuste sobre 2016-10 + 2019-11, sin ver 2024-11) → predecir 2024-11, contra baseline
      "S constante".
    - `validacion_adelgazamiento(panel_d)` — adelgazamiento binomial **del propio Censo 2020**
      (nunca de proyecciones futuras): comprueba que la contracción EB supera a `r̂` directo y a
      `ρ_m` en MAE y cobertura del IC95.
    - `leave_one_alcaldia_out(panel_d, conapo)` — reajustar `τ²` excluyendo una alcaldía a la vez
      (partición espacial, no temporal: no tiene el problema de fuga de futuro).
    - `comparar_censo_conapo(censo, conapo)` — la comparación 2010–2020 se conserva, pero se
      reclasifica: no predice el futuro, compara dos fuentes en el mismo punto en el tiempo;
      alimenta `σ_C`, se reporta etiquetada como tal, nunca como "backtest".
11b. **Declarar la limitación en vez de maquillarla**: `docs/backtest.md` incluye, literal, *"No
    existe hoy una validación temporal independiente de la tendencia de demanda a nivel alcaldía; la
    comparación 2010–2020 alimenta la incertidumbre del modelo, pero no lo valida contra el
    futuro."* Opcional, no bloqueante: si se localiza y descarga una edición CONAPO **anterior** al
    Censo 2020 (p. ej. "Proyecciones 2016–2050, base Censo 2010"), su predicción de 2020 se puede
    comparar contra el Censo 2020 real sin ninguna fuga — ver Fase 7 (fuentes).
12. **Baseline obligatorio en todas**: `r = 0` ("igual que el último corte") o `S` constante en
    oferta. Reportar MAE de la tasa, cobertura empírica del IC95 y F1 macro de las 3 clases de
    veredicto. Si el modelo **no** supera al baseline, `CLAUDE.md` obliga a no adoptarlo: en ese caso
    el hallazgo se reporta y se discute, no se esconde.
13. **Escribir salidas reales**: `data/outputs/backtest.json` y `docs/backtest.md` (resumen de ≤ 5
    líneas + tabla + la limitación de 11b). Ambas rutas ya están declaradas en `config.py:44-45`.
14. **Enganchar al pipeline**: `exportar.main()` llama a `backtest` entre `panel` y `exportar`
    (el docstring ya reserva el lugar). Añadir target `backtest` al `Makefile`.
15. **Tests**: `backend/tests/test_backtest.py` — sin fuga de futuro (el origen nunca ve datos
    posteriores), determinismo con `SEMILLA`, baseline calculado sobre el mismo universo, **y un
    test que falla explícitamente si `backtest_conapo` con orígenes móviles reaparece** (guardarraíl
    contra reintroducir el error).
16. **Superficie en el frontend**: una sección nueva en el Nivel 2 de Habitancia (§"¿Qué tan
    confiable es la estimación?", Fase 7) con "qué tan bien acertó el modelo en el pasado" — dos o
    tres cifras, en lenguaje llano, sin fórmulas (`correccion/frontend_requisitos.md`, "no mostrar
    metodología estadística avanzada"). La rúbrica valora que se **comunique**, no solo que exista.
17. **Verificación:** `docs/backtest.md` existe, tiene cifras modelo-vs-baseline y la limitación
    declarada, y `make pipeline` reejecutado dos veces produce el mismo `backtest.json` byte a byte.

---

## FASE 3 — Incertidumbre calibrada con el backtest, no un ancho mínimo *(alta prioridad, ~medio día, depende de Fase 2)*

Hallazgo 0.5: `ic95 = [-6.9, -6.9]` en la oferta agregada de la CDMX es un intervalo de ancho cero.
El modelo propaga el error de conteo, no la incertidumbre estructural del DENUE.

> **Corrección sobre la versión anterior de este plan.** El punto 19 original proponía un "piso
> mínimo de incertidumbre" y el punto 21 un criterio de aceptación "ningún `ic95` con ancho < 0.2".
> **Ambos están mal planteados**: eligen un ancho de intervalo a ojo, sin relación con qué tan bien
> calibrado está el modelo. Un intervalo ancho no es automáticamente un intervalo *correcto*, y uno
> angosto no es automáticamente uno *incorrecto*. Corregido: el piso se calibra con la **cobertura
> empírica** del backtest de la Fase 2, no con un ancho objetivo. Por eso esta fase ahora depende de
> la Fase 2 (antes iban en paralelo).

18. **Sobredispersión en cada rama proyectable** (`modelos.py#ajustar_oferta`, generalizado en la
    Fase 5 a salud/comercio): estimar un factor quasi-Poisson `φ_m = χ²(Pearson)/gl`, **agrupado por
    alcaldía** (con 1 grado de libertad por AGEB, `φ` individual es puro ruido), `φ_m ≥ 1`, aplicado
    por AGEB. Esto sí sale de los datos de ajuste — es la parte que no cambia.
19. **Piso mínimo de incertidumbre, calibrado, no elegido a ojo** (`SIGMA_MIN_TASA` en `config.py`,
    posiblemente distinto para demanda y para oferta). Procedimiento (`backtest.py`, función
    `calibrar_piso_incertidumbre`, `docs/metodologia.md` §2.7 y §6.1):
    1. Rejilla de candidatos, p. ej. `{0.000, 0.005, 0.010, 0.015, 0.020}` %/año.
    2. Para cada candidato, recalcular el IC95 simulado **sobre los folds del backtest de la Fase
       2** (adelgazamiento, LOAO, oferta 2019→2024) y medir la cobertura empírica.
    3. Elegir el candidato **más pequeño** con cobertura dentro de `[0.90, 0.97]` (la misma banda ya
       usada para LOAO).
    4. Si `0.000` ya sobrecubre (> 0.97), **no se añade piso**: se documenta que el error de conteo
       ya es suficiente. Si ningún candidato llega a `0.90`, se amplía la rejilla.
    El resultado (piso elegido + cobertura lograda) va a `docs/backtest.md`, sin redondear "para que
    se vea bien".
20. **Dos escenarios para la caída DENUE 2024** en vez de una hipótesis única
    (`detalles_a_tratar.md` §4 y §9.8). `CLAUDE.md` ya la trata como "cierres reales acumulados"; la
    revisión pide presentarla como hipótesis:
    - **A (actual):** cierres reales acumulados 2020-2023, registrados de golpe.
    - **B:** parte de la caída es depuración del padrón → tasa de oferta atenuada.
    Exportar ambos en `diagnostico.json` y mencionarlo en el drawer. No hace falta duplicar el
    contrato: basta con el rango entre escenarios como sensibilidad reportada.
21. **Verificación:** cobertura empírica del IC95 en el backtest dentro de `[0.90, 0.97]` (reemplaza
    al criterio de ancho mínimo); test en `test_modelos.py`/`test_backtest.py` que lo garantice.

---

## FASE 4 — Población objetivo: segmentos de edad, ampliados a 0–17 *(alta prioridad, ~1 día)*

Hallazgos C y D, más el requisito de `correccion/frontend_requisitos.md` §5: el selector de
"población objetivo" debe incluir **0–17 y 15–17**, no solo 0–14. Es más barato de lo que parece:
**los datos ya están desagregados en disco**, incluida la banda 15–17.

- `data/interim/censo_ageb_panel.parquet` ya trae `p_0a2, p_3a5, p_6a11, p_12a14` **y `p_15a17`**
  por AGEB y año (verificado en disco: la columna existe).
- `data/interim/conapo_mun_quinq.parquet` ya trae grupos quinquenales por alcaldía (incluido 15–19,
  que no coincide exactamente con 15–17 — ver limitación abajo).
- El DENUE de infancias ya trae `Subcategoría` + `Código SCIAN`.

22. **Renombrar el concepto en toda la UI y la documentación**: "demanda" → **"población objetivo"**
    de cara al usuario, con "demanda potencial" reservado para el icono "?" y la documentación
    técnica (`correccion/frontend_requisitos.md`: nunca usar jerga estadística en la interfaz
    principal). Archivos: `frontend/js/textos.js`, `docs/metodologia.md`, `CLAUDE.md`.
23. **Segmentar por servicio y por edad**, con el mapeo SCIAN ya presente en los datos
    (edición 2024-11, `Alcance = Principal`), ampliado a seis segmentos
    (`correccion/frontend_requisitos.md` §5):

    | Población objetivo | SCIAN (`Principal`) | Establecimientos | Columna censal |
    |---|---|---:|---|
    | Todas las infancias y adolescencias · 0–17 | todos los anteriores | 7 309 | `p_0a2+…+p_15a17` |
    | Primera infancia · 0–2 | 624411, 624412 | 592 | `p_0a2` |
    | Preescolar · 3–5 | 611111, 611112 | 2 262 | `p_3a5` |
    | Primaria · 6–11 | 611121, 611122 | 2 289 | `p_6a11` |
    | Secundaria · 12–14 | 611131, 611132, 611141, 611142 | 895 | `p_12a14` |
    | Adolescencia · 15–17 | solo `Complementario` (media superior, recreación juvenil) | — | `p_15a17` |

    El segmento 15–17 tiene oferta menos confiable (casi toda `Complementario`, no `Principal`):
    se publica con **tope de confianza `media` obligatorio**, nunca se excluye — el requisito
    funcional pide que esté disponible, no que sea perfecto.
24. **Implementación**: `panel.py` construye un panel por segmento (misma forma, columna
    `segmento`); `modelos.py` **no cambia** — se le pasa cada segmento por separado. `exportar.py`
    emite la capa `demanda` con una entrada por segmento
    (`todas, primera_infancia, preescolar, primaria, secundaria, adolescencia`). El segmento `todas`
    (0–17) es el valor por omisión del selector, no `total` (0–14): el alcance del producto ya no es
    "infancias 0–14", es Habitancia.
25. **Cuidado documentado**: CONAPO es quinquenal (00-04, 05-09, 10-14, 15-19) y no coincide con
    ninguna de las seis bandas exactamente (15–19 ≠ 15–17). El ancla municipal se aplica sobre 0–14
    (como hoy) y todos los segmentos heredan el mismo factor de control; registrar esa aproximación
    en `docs/metodologia.md` §1.2, no ocultarla.
26. **Frontend**: el selector "¿A quién quieres analizar?" (`correccion/frontend_requisitos.md` §5),
    con icono "?" explicando la diferencia entre población objetivo y demanda observada. Módulo
    nuevo `frontend/js/poblacion.js` + acción en `estado.js`; el mapa solo recolorea, no recarga.
27. **Verificación**: suma de los cinco segmentos con dato = segmento `todas` por AGEB (test en
    `test_panel.py`); el selector cambia el mapa sin peticiones de red.

---

## FASE 5 — Cuatro ramas de oferta/disponibilidad *(alta prioridad, ~1.5 días, depende de Fase 4)*

Esta fase **reemplaza** a lo que antes era una sola capa "oferta" y absorbe la antigua Fase 7
("tercera fuente"): `correccion/frontend_requisitos.md` §2 exige que Habitancia combine **cuatro
ramas** — educación y cultura, salud, comercio, áreas verdes y espacio público —, no una. Las
fuentes para las tres ramas que faltan **ya están descargadas y sin usar** (hallazgo 0.7):
`data/processed/salud/`, `data/processed/comercios/`, `data/processed/areas_verdes/`,
`data/processed/espacios_publicos/`. Esto también resuelve, de paso, el pedido de
`rubrica.md` §3 de integrar Datos Abiertos de la CDMX junto a INEGI (no solo fuentes federales).

35. **Generalizar el modelo de oferta a educación, salud y comercio** (`modelos.py#ajustar_oferta`
    y `simular_oferta` no cambian de forma, se reutilizan por rama): DENUE salud tiene los mismos 3
    cortes que infancias (mismas ediciones); DENUE comercios tiene 11 ediciones, mismo criterio de
    "1 corte por periodo" que ya se aplicó a infancias (§6 de la metodología). Ambas ramas heredan
    la sobredispersión y el piso calibrado de la Fase 3.
36. **Áreas verdes y espacio público: sin proyección, nunca inventada.** Un solo corte (inventario
    estático) no identifica tendencia — igual que un solo censo no la identificaría. Se publica
    disponibilidad **actual** (conteo/superficie por AGEB, join espacial WGS84), sin horizontes,
    exactamente como pide `correccion/frontend_requisitos.md` §16: *"Si una rama solo tiene
    información actual, mostrar su situación actual y NO inventar una línea futura"*.
37. **Celdas de filtro, no una sola serie agregada por rama.** `correccion/frontend_requisitos.md`
    §10 exige filtros (nivel/tipo × sector) dentro de cada rama, aplicados en tiempo real. El
    backend no decide el filtro: publica la serie **por celda** (segmento SCIAN × sector) y el
    cliente suma los conteos/varianzas proyectados de las celdas seleccionadas (nunca suma tasas —
    no son lineales en el conteo). Tabla de celdas por rama, tamaño de contrato y fórmula exacta:
    `docs/metodologia.md` §10.6, `plans/backend_plan.md` tarea B22.
38. **Documentar "momentos históricos comparables" por rama** (hallazgo B, antes Fase 7 punto 42):
    - Oferta educación/salud/comercio, por AGEB: **3 momentos** cada una (mismo criterio de
      1-corte-por-periodo).
    - Demanda, por alcaldía: **serie CONAPO 1990-2040**, decenas de momentos (nunca usada como
      backtest de origen móvil — Fase 2).
    - Demanda, por AGEB: **2 momentos censales**, límite de INEGI.
    - Verde: **1 momento**, sin tendencia, declarado como tal.
    Ponerlo en `docs/metodologia.md` §1.3 y en el Nivel 2 de Habitancia.
39. **Contrato v1.4**: `capas.oferta` se retira; la sustituyen `capas.ramas.{educacion, salud,
    comercio, verde}`, cada una con `celdas: {clave_celda: {...}}` por AGEB. Actualizar
    `validar_contrato()`, `plans/frontend_specs.md` §17.
40. **Verificación**: Σ celdas de una rama = total sin filtrar, por AGEB y horizonte (test en
    `test_exportar.py`); verde nunca publica `h`, solo `nivel_base`.

---

## FASE 6 — Índice de oportunidad: fórmula exacta, tratamiento de oferta cero, sensibilidad *(alta prioridad, ~1 día, depende de Fase 5)*

Hallazgos F y G, y el núcleo de `rubrica.md` §2: *"la aplicación debe decirte dónde hay
oportunidades de expansión y cómo rankearlas"*. El caso de prueba de la rúbrica ("zonas donde la
demanda aumentará en tres años, evitando áreas con oferta ya saturada") y el de
`correccion/frontend_requisitos.md` §24 (educación + salud combinadas con pesos) exigen una fórmula
**exacta**, no una idea general — la versión anterior de este plan decía "índice normalizado y
explicable en una línea" sin fijar la fórmula. Corregido aquí: variables, pesos, tratamiento de
oferta cero y sensibilidad, todos definidos (fórmula completa y razonada en
`docs/metodologia.md` §10, resumen operativo abajo).

28. **Cobertura proyectada por rama** en `features.py`, por AGEB, horizonte y segmento, sobre las
    **mismas** réplicas Monte Carlo (no sobre las medianas — así el intervalo sale gratis):
    `cobertura_{i,h,r}^s = Ŝ_{i,h,r}^s / D̂_{i,h,seg}^s × 1000`.
29. **Tratamiento de oferta cero, explícito y obligatorio.** `Ŝ=0` con `D̂>0` es un valor **válido**
    (la señal de mayor oportunidad posible), nunca `sin_datos`; solo `D̂` inválido produce
    `sin_datos`. Esto se resuelve solo con el paso 30 (rango percentil con empates), no con una
    excepción de código aparte.
30. **Índice de oportunidad por rama, fórmula exacta:**
    - Paso 1 — nivel: `N_{i,h,r} = 1 − rango_percentil(cobertura_{i,h,r})`, rango fraccionario con
      empates promediados (las AGEB con `cobertura=0` comparten el rango más bajo → `N=1`).
    - Paso 2 — tendencia, acotada: `ajuste = clip((tasa_D − tasa_S) / K, −0.15, +0.15)`, `K=5`
      pp/año por omisión (constante interna, no expuesta al usuario).
    - Paso 3: `O_{i,h,r} = clip(N_{i,h,r} + ajuste, 0, 1)`.
    - **Sensibilidad obligatoria**: recalcular con `K∈{3,5,8}`, marcar en `diagnostico.json` las
      AGEB cuyo orden cambia sustancialmente entre extremos.
31. **Índice compuesto, calculado en el cliente, no en el backend** (§Fase 7): combina las cuatro
    ramas con los pesos que el usuario mueve en tiempo real,
    `IC_{i,h} = Σ w_r·O_{i,h,r} / Σ w_r` sobre ramas con dato, renormalizado si alguna rama es
    `sin_datos` para esa AGEB. El backend solo publica `O_{i,h,r}` por celda de filtro; nunca
    calcula el compuesto (`correccion/frontend_requisitos.md` §9: "los pesos NO alteran los datos").
32. **Filtro de nivel de riesgo** (`rubrica.md` §2: *"nivel de riesgo aceptable"*): exponer `p_dec`
    y la confianza de la demanda como umbral ajustable; el ranking solo lista unidades que lo
    superan. Resuelve el hallazgo G: deja de importar que casi todo sea `baja`, porque el orden lo
    da `O_{i,h,r}`/`IC_{i,h}`, no el signo del veredicto.
33. **Segundo índice, separado**: *Disponibilidad proyectada de servicios para infancias*
    (`correccion/frontend_requisitos.md` §7, "Disponibilidad para familias"). **Nunca mezclarlo**
    con el de oportunidad — una zona buena para abrir servicios es justo una con baja cobertura.
34. **`capas.brecha` se retira del contrato** (ya no tiene sentido con cuatro ramas filtrables); lo
    sustituye el cálculo client-side de §30-31. `diagnostico.json` conserva un resumen agregado
    fuera del contrato.
34b. **Verificación:** el caso de prueba de `rubrica.md` §8 y el de
    `correccion/frontend_requisitos.md` §24 se responden en vivo en menos de 30 segundos de
    interacción; `indice_oportunidad` nunca convierte `Ŝ=0` en `sin_datos` (test dedicado).

---

## FASE 7 — Frontend Habitancia: rediseño funcional completo *(alta prioridad, ~3-4 días, depende de Fases 4-6)*

`correccion/frontend_requisitos.md` (25 secciones, documento vinculante y autocontenido) redefine
el frontend de raíz: ya no es un visor de dos capas con un titular autogenerado, es **Habitancia**
— un producto de exploración con cuatro ramas ponderables, filtros, dos tipos de búsqueda,
comparación entre alcaldías y una arquitectura de información en dos niveles (respuesta rápida /
entender el resultado). El detalle completo, sección por sección, vive en
`plans/frontend_specs.md` (reescrito para esta fase) y `plans/frontend_plan.md` (tareas F-series
reescritas); aquí solo el resumen ejecutivo y los puntos que exigen coordinación con el backend.

48. **Arquitectura de información en dos niveles** (`correccion/frontend_requisitos.md` §1, §13,
    §25): Nivel 1 = resumen estructurado (zona, población, horizonte, oportunidad relativa,
    confianza, ramas con mayor incidencia) — **nunca una frase autogenerada**; Nivel 2 = "Entiende
    esta zona" (cómo cambió, qué podría pasar, qué explica el resultado, qué ramas pesan más).
    Ningún componente nuevo genera texto interpretativo dinámico: todo son etiquetas, valores y
    gráficas predefinidas con icono "?" (`correccion/frontend_requisitos.md` §1, §18, §20).
49. **Selector de tipo de búsqueda** (§7-8 de requisitos): "Oportunidad de expansión" (el
    `O_{i,h,r}`/`IC_{i,h}` de la Fase 6) vs. "Disponibilidad para familias" (el índice de la Fase 6
    punto 33). Cambia qué extremo del ranking se muestra primero, nunca los datos.
50. **Prioridades (pesos) y filtros, con la diferencia clarísima entre los tres** (§9-10, §21 de
    requisitos): los pesos (1-5 círculos por rama) solo reordenan; los filtros (nivel/tipo × sector
    dentro de cada rama) cambian qué se cuenta como oferta de esa rama (Fase 5, celdas). Ninguno de
    los dos toca la predicción original. Botones "Restablecer prioridades"/"Restablecer filtros".
51. **Mapa multi-vista sobre el mismo SVG de AGEB** (§11, §11A de requisitos): un selector "¿Qué
    quieres ver en el mapa?" (Vista general = índice compuesto; o una de las cuatro ramas
    individuales) que solo cambia color/leyenda/ranking/título, **nunca** recrea la geometría ni
    abre un mapa nuevo. Reutiliza el `<g>` de AGEB que ya existe (`mapa.js`); se construye **después**
    de la Fase 8 (el cuelgue), sobre el mapa ya corregido.
52. **Ranking por AGEB** (§11): la unidad mínima coloreada y rankeada es siempre la AGEB
    (`correccion/frontend_requisitos.md` es explícito: "las alcaldías NO son la unidad mínima que
    se colorea"); la alcaldía sigue siendo el nivel de navegación/zoom/búsqueda, no de cómputo.
    La UI llama "zona" a la AGEB frente al usuario no técnico, con "?" explicando la equivalencia.
53. **Comparar dos alcaldías** (§19): mismos indicadores lado a lado, conservando población/
    horizonte/búsqueda/pesos/filtros activos; **sin declarar un ganador** ni frase automática.
54. **Población objetivo ampliada a 0–17** (Fase 4) integrada en el flujo de configuración (§3, §5).
55. **Motor de composición cliente** (referenciado desde `docs/metodologia.md` §10.3 y
    `plans/backend_plan.md`, especificado en `plans/frontend_specs.md` §17): módulo nuevo
    `frontend/js/composicion.js` que, dado el contrato v1.4 (celdas por rama) más pesos y filtros
    activos, calcula `Ŝ_{i,h,r}(filtro)`, `cobertura`, `O_{i,h,r}` e `IC_{i,h}` para las 2 453 AGEB
    en el navegador, sin red, actualizando mapa y ranking en el mismo ciclo de eventos
    (`correccion/frontend_requisitos.md` §22: "no recargar la página").
56. **Iconos "?" como sistema de ayuda** (§20): cada concepto listado en requisitos §20 tiene su
    ayuda de 3 partes (qué es / por qué importa / cómo interpretarlo), centralizada en
    `frontend/js/textos.js` junto con el resto de copy — reutiliza casi literal el texto que
    `correccion/frontend_requisitos.md` ya da.
57. **Verificación:** el caso de uso de jueces de `correccion/frontend_requisitos.md` §24 (primaria
    pública + hospitales/clínicas + comercio de primera necesidad + áreas verdes recreativas,
    3 años, educación y salud en alta prioridad) se completa sin recargar la página y sin abrir
    DevTools; los 26 puntos de `correccion/frontend_requisitos.md` §26 quedan verificables uno por
    uno.

---

## FASE 8 — Frontend: el cuelgue del mapa *(bloqueante de demo, ~2 h)*

`detalles_a_tratar.md` cierra con esto en mayúsculas, y es lo que un juez verá primero. Se corrige
**antes** de construir el mapa multi-vista de la Fase 7 sobre el mismo archivo (`mapa.js`), para no
heredar el defecto al nuevo código.

### 8.1 Diagnóstico medido (no es el número de polígonos)

La geometría **no** es el problema: `frontend/data/ageb_cdmx_simplificado.geojson` son 1.5 MB,
2 453 features y **55 711 vértices en total** (máximo 7 568 por alcaldía, ~23 vértices por AGEB).
Eso lo dibuja cualquier navegador.

Medido en el navegador, con `PerformanceObserver` sobre tareas largas, clic real en Cuauhtémoc
(153 AGEB, escala de enfoque 7.16×):

| Escenario | Tareas largas | Hilo principal bloqueado |
|---|---:|---:|
| Estado actual (primer clic, en frío) | 58 | **12 301 ms** |
| Estado actual (pareado, mismo ciclo) | 6 | 8 790 ms |
| Sin `filter` en las vecinas | 6 | 5 729 ms |
| Sin `vector-effect: non-scaling-stroke` | 2 | 2 290 ms |
| **Sin `transition: transform` en los grupos** | **1** | **412 ms** |

Media de tres repeticiones pareadas: **947 ms (actual) → 29 ms (con el parche)**.

**Causa raíz.** `frontend/css/mapa.css:179-182` declara:

```css
.alcaldias-fondo, .agebs, .confianza-baja, .alcaldias {
  transition: transform var(--d-xs) var(--ease-salida);
}
```

y `frontend/js/mapa.js#aplicarTransform` (línea 391) anima **ese mismo `transform`** como atributo
SVG con una transición de D3 a ~60 fps durante 820 ms. Cada escritura de atributo **arranca una
transición CSS nueva de 120 ms** sobre un grupo que contiene cientos de `<path>` con
`non-scaling-stroke` y 15 rutas con `filter`. Las transiciones se encabalgan y el rasterizado se
multiplica hasta bloquear el hilo principal — y, en una máquina más lenta o una ventana más grande,
matar la pestaña.

### 8.2 Correcciones, en orden de impacto

41. **Eliminar `transition: transform`** de `.alcaldias-fondo, .agebs, .confianza-baja, .alcaldias`
    en `frontend/css/mapa.css`. La animación ya la hace D3; la regla CSS es redundante y dañina.
    *Efecto medido: 8 790 ms → 412 ms.*
42. **Quitar `filter: var(--recesivo-filtro)`** de `.mapa__alcaldia--recesivo` (`mapa.css:155-159`).
    `saturate(0) brightness(1.08)` obliga a rasterizar una superficie fuera de pantalla por cada una
    de las 15 vecinas, **a la escala del zoom**. El mismo efecto visual se consigue con el color ya
    definido en `--recesivo-relleno` / `--recesivo-contorno`, sin filtro. *Efecto medido:
    12 301 ms → 8 951 ms adicionales.*
43. **Animar un solo grupo envolvente.** Hoy `aplicarTransform` escribe el atributo en 4 grupos por
    fotograma. Envolverlos en un único `<g class="escenario">` y animar solo ese: una escritura por
    fotograma en vez de cuatro. Este grupo envolvente es también el punto de anclaje del mapa
    multi-vista de la Fase 7 (una sola capa de AGEB, varios colores posibles).
44. **Revisar `vector-effect: non-scaling-stroke`** (~2 290 ms de coste medido). Es necesario para
    que el trazo no engorde con el zoom, pero se puede sustituir por `stroke-width` recalculado una
    sola vez **al terminar** la animación, en vez de por fotograma.
45. **Respetar `prefers-reduced-motion`**: con la media query activa, `--d-xs` ya es `0ms`, pero
    `DURACION_ENFOQUE_MS` (820 ms, `mapa.js:39`) está en JS y **no** la respeta. Leerla de
    `matchMedia("(prefers-reduced-motion: reduce)")` y saltar la animación.
46. **Verificación obligatoria**: reejecutar la medición de tareas largas después del parche, en las
    16 alcaldías, con el objetivo de **ninguna tarea > 200 ms**. Incluir el script de medición en
    `frontend/tests/` para que sea reproducible ante los jueces.

> Si tras 41-45 alguna alcaldía siguiera pesada (no se espera), el siguiente escalón es
> `<canvas>` en vez de SVG para la capa de AGEB. **No empezar por ahí**: el problema medido es CSS,
> no volumen de datos, y migrar a canvas costaría la accesibilidad por teclado que ya funciona.

---

## FASE 9 — Mensaje, documentación y demo *(media, ~medio día)*

Esta fase se **encoge** respecto a la versión anterior de este plan: adoptar Habitancia
(`correccion/frontend_requisitos.md`) ya resuelve el problema de mensaje — su línea de misión y sus
26 secciones de copy están escritas y son defendibles, no hay que redactarlas de nuevo.

47. **La promesa ya está resuelta por Habitancia**: *"ayudar a una persona no técnica a explorar la
    Ciudad de México y detectar zonas donde, de acuerdo con la evolución de la población infantil y
    la disponibilidad de servicios, podría existir una mayor oportunidad relativa de ampliar o
    fortalecer infraestructura para infancias"* (`correccion/frontend_requisitos.md`, línea de
    misión) — no promete "dónde conviene vivir", nunca declara certeza donde solo hay tendencia.
58. **Sesgos y límites** (`rubrica.md` §8): visibles en el bloque "¿Qué explica este resultado?"
    (§18 de requisitos) y en el Nivel 2, no escondidos en un solo párrafo: (a) ausencia de datos ≠
    ausencia de demanda (§8 de la rúbrica, ya en el flujo de `sin_datos`), (b) un establecimiento no
    mide capacidad, calidad ni matrícula — texto ya dado en requisitos §16 ("no representa
    capacidad, calidad, matrícula ni número de lugares disponibles"), (c) las proyecciones son
    condicionales (§6 de requisitos, icono "?" de horizonte).
59. **Reconciliar `CLAUDE.md`** con el estado final: contrato v1.4, horizontes 1/3/5, cuatro ramas,
    `backtest.py` existente con la limitación de CONAPO declarada, archivos de `plans/` y
    `docs/metodologia.md` al día, nombre del producto (Habitancia) reflejado donde CLAUDE.md
    describa la UI.
60. **Guion de demo de 3-4 minutos**, ensayado con el caso de jueces de requisitos §24: pantalla
    inicial → seleccionar alcaldía → definir población (6–11) → horizonte (3 años) → tipo de
    búsqueda (oportunidad) → pesos (educación y salud altos) → filtros (primaria pública, hospitales
    y clínicas) → mapa y ranking se actualizan → abrir una zona → Nivel 1 → "Entender esta zona" →
    gráficas → comparar dos alcaldías. Todo sin recargar la página, sin errores de consola, sin el
    cuelgue de la Fase 8. Los jueces verifican en vivo (`rubrica.md` §7).

---

## Orden de ejecución y dependencias

```
FASE 0 (docs)  ──┐
FASE 1 (h1/h3/h5)├─> FASE 2 (backtest) ──> FASE 3 (incertidumbre) ──┐
FASE 8 (crash) ──┘                                                   │
                    FASE 4 (segmentos 0–17) ──> FASE 5 (4 ramas) ──> FASE 6 (oportunidad) ─┐
                                                                                              ├─> FASE 7 (Habitancia) ──> FASE 9 (mensaje/demo)
                                        FASE 3 (incertidumbre) ─────────────────────────────┘
```

- **Fases 0, 1 y 8 son independientes entre sí** y se pueden paralelizar (documentación, backend de
  configuración, CSS/JS del mapa: archivos disjuntos). **La fase 8 es la de mayor retorno por hora
  invertida**: dos líneas de CSS eliminan un cuelgue de 12 segundos que hoy haría fracasar la
  verificación en vivo — y hacerla antes de la Fase 7 evita reconstruir el mapa multi-vista sobre
  código roto.
- **La fase 2 es la única que la rúbrica exige explícitamente y que hoy no existe**; si hubiera que
  recortar alcance, se recorta la Fase 7 (o su parte de comparación/filtros finos), no la 2.
- **La fase 3 ahora depende de la 2** (el piso se calibra con el backtest): ya no van en paralelo.
- **La fase 7 es la más grande y la que más cambia el producto**; depende de que 4, 5 y 6 entreguen
  el contrato v1.4 completo (segmentos, ramas, índice de oportunidad) antes de que el frontend
  pueda construir el motor de composición cliente sobre datos reales — puede empezarse antes con
  mocks (`frontend/mock/generar_mock.py` actualizado a v1.4), pero no cerrarse sin el backend real.
- Las fases 4, 5 y 6 comparten el salto de contrato a v1.4: conviene tocar `exportar.py`,
  `validar_contrato()` y `frontend/js/api.js` una sola vez, al final de la 6, no tres veces.

## Definición de terminado (ampliada sobre la de `CLAUDE.md`)

- [ ] Todo `.md` citado por el código existe en el árbol.
- [ ] `docs/backtest.md` con cifras reales de modelo vs baseline, y la limitación de CONAPO
      declarada explícitamente (no se usa `pobproy_quinq1.csv` como si fuera el futuro observado).
- [ ] Horizontes h1/h3/h5; contrato v1.4 validado por `make validar`.
- [ ] Cobertura empírica del IC95 en el backtest dentro de `[0.90, 0.97]` (piso calibrado, no un
      ancho mínimo elegido a ojo).
- [ ] Cuatro ramas (educación, salud, comercio, verde) con celdas de filtro; verde sin proyección.
- [ ] Índice de oportunidad con fórmula exacta implementada; `Ŝ=0` nunca se convierte en `sin_datos`.
- [ ] Ranking de oportunidad consultable y filtrable por nivel de riesgo.
- [ ] Selector de población objetivo 0–17 (incl. 15–17) funcionando en tiempo real.
- [ ] Pesos y filtros de las cuatro ramas actualizan mapa/ranking sin recargar la página.
- [ ] Comparación entre dos alcaldías funcional, sin declarar un ganador.
- [ ] Ninguna tarea larga > 200 ms al enfocar cualquiera de las 16 alcaldías (medido, no estimado).
- [ ] `make test` verde; `make pipeline` determinista en dos ejecuciones.
- [ ] Sin CDN, sin errores de consola, Lighthouse accesibilidad ≥ 90.
