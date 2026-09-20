# Plan de acción — alineación con `rubrica.md` y `detalles_a_tratar.md`

Fecha: 2026-09-19 · Rama: `jaladas2` · Estado auditado: 122 pruebas de backend en verde,
`make pipeline` reproducible, frontend funcional sin errores de consola.

Este documento **no es un plan de arquitectura nueva**: el modelo de demanda se conserva. Es la
lista de correcciones necesarias para que el repositorio cumpla la rúbrica y para cerrar los
hallazgos de `correccion/detalles_a_tratar.md`. Cada punto trae: archivos, criterio de aceptación
y verificación.

Contrato de salida: los cambios de las fases 1, 4 y 5 **rompen el contrato v1.2** y obligan a
subir a **v1.3**; el adaptador v1.1 del frontend (`frontend/js/api.js`) se conserva como está.

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
| 0.8 | **El mapa cuelga el navegador** | Reproducido: un clic en Cuauhtémoc generó **58 tareas largas por 12 301 ms** de hilo principal bloqueado (peor tarea 1 128 ms). Causa aislada abajo (§6.1) |

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
6. `backend/src/chipos/exportar.py:52-56`: `VERSION_CONTRATO = "1.3"`,
   `ORDEN_HORIZONTES = ("h1","h3","h5")`, `FECHAS_HORIZONTE = {"h1":"2027-06","h3":"2029-06","h5":"2031-06"}`,
   `ANIOS_HORIZONTE = {"h1":1,"h3":3,"h5":5}`.
7. `frontend/js/config.js`: añadir `"1.3"` a `VERSIONES_CONTRATO_ACEPTADAS`. **No hay que tocar
   `horizonte.js`**: el slider ya se construye desde el array `horizontes` del JSON y ordena por
   `anios` (`ordenarHorizontes`). Sí hay que revisar `frontend/js/textos.js` §"Por qué a 7 años hay
   más incertidumbre" → reescribir como "a 5 años".
8. `frontend/mock/generar_mock.py`: regenerar los fixtures v1.3 con tres horizontes; conservar
   `prediccion_ageb_v11.json` y el inválido tal cual.
9. Actualizar `CLAUDE.md` ("Contrato de salida", ejemplo JSON y prosa de horizontes) y
   `docs/metodologia.md` §2/§7.
10. **Verificación:** `make pipeline && make validar && make test`; abrir el frontend y comprobar
    que el slider tiene 3 paradas etiquetadas 2027 / 2029 / 2031.

> Nota honesta para la presentación: el veredicto y la confianza **no cambian entre horizontes**
> (dependen de la tasa anual, no del horizonte); solo cambian `delta_pct` e `ic95`. Es una
> propiedad del modelo log-lineal, no un bug — conviene decirlo en el drawer de metodología antes
> de que un juez lo note.

---

## FASE 2 — Validación retrospectiva real *(bloqueante de rúbrica, ~1 día)*

`rubrica.md` §5 y §6 la exigen ("validación retrospectiva", "requisitos técnicos mínimos"), y §7
la pone primero en la evaluación. Es el hueco más grave. El diseño ya está escrito en
`plans/backend_plan.md` §6 (tarea B9) — solo falta implementarlo.

11. **Crear `backend/src/chipos/backtest.py`** con las cuatro validaciones del plan §6:
    - `backtest_oferta(panel_o)` — **el backtest temporal genuino**: origen 2019-11 (ajuste sobre
      2016-10 + 2019-11) → predecir 2024-11, contra baseline "S constante". Origen móvil, sin fuga
      de futuro.
    - `backtest_conapo(conapo, origenes=(2000,2005,2010,2015), horizontes=(1,3,5))` — origen móvil
      sobre la serie municipal CONAPO 1990-2040 (`data/interim/conapo_mun_0a14.parquet`, 816 filas,
      1990-2040). Esta es la validación temporal de la **capa de demanda a nivel alcaldía**, y la
      única posible con más de dos momentos.
    - `validacion_adelgazamiento(panel_d)` — adelgazamiento binomial de `D_2020`: comprueba que la
      contracción EB supera a `r̂` directo y a `ρ_m` en MAE y cobertura del IC95.
    - `leave_one_alcaldia_out(panel_d, conapo)` — reajustar `τ²` excluyendo una alcaldía a la vez.
12. **Baseline obligatorio en todas**: `r = 0` ("igual que el último corte"). Reportar MAE de la
    tasa, cobertura empírica del IC95 y F1 macro de las 3 clases de veredicto. Si el modelo **no**
    supera al baseline, `CLAUDE.md` obliga a no adoptarlo: en ese caso el hallazgo se reporta y se
    discute, no se esconde.
13. **Escribir salidas reales**: `data/outputs/backtest.json` y `docs/backtest.md` (resumen de ≤ 5
    líneas + tabla). Ambas rutas ya están declaradas en `config.py:44-45`.
14. **Enganchar al pipeline**: `exportar.main()` llama a `backtest` entre `panel` y `exportar`
    (el docstring ya reserva el lugar). Añadir target `backtest` al `Makefile`.
15. **Tests**: `backend/tests/test_backtest.py` — sin fuga de futuro (el origen nunca ve datos
    posteriores), determinismo con `SEMILLA`, y que el baseline se calcula sobre el mismo universo.
16. **Superficie en el frontend**: una sección nueva en el drawer de metodología
    (`frontend/js/textos.js`, `franja.js`) con "qué tan bien acertó el modelo en el pasado" —
    dos o tres cifras, en lenguaje llano. La rúbrica valora que se **comunique**, no solo que exista.
17. **Verificación:** `docs/backtest.md` existe, tiene cifras modelo-vs-baseline, y `make pipeline`
    reejecutado dos veces produce el mismo `backtest.json` byte a byte.

---

## FASE 3 — Incertidumbre honesta *(alta prioridad, ~medio día)*

Hallazgo 0.5: `ic95 = [-6.9, -6.9]` en la oferta agregada de la CDMX es un intervalo de ancho cero.
El modelo propaga el error de conteo, no la incertidumbre estructural del DENUE.

18. **Sobredispersión en la oferta** (`modelos.py#ajustar_oferta`): estimar un factor
    quasi-Poisson `φ = χ²(Pearson)/gl` sobre los tres cortes y escalar `var_b` por `φ`. Con 3
    puntos y 2 parámetros hay 1 grado de libertad — `φ` es ruidoso por AGEB, así que estimarlo
    **agrupado por alcaldía** y aplicarlo por AGEB.
19. **Piso mínimo de incertidumbre** en ambas capas: una constante nueva en `config.py`
    (p. ej. `SIGMA_MIN_TASA`) que impide que `var_post` baje de un valor documentado. Justificación
    explícita en `docs/metodologia.md`: cambios de levantamiento, depuración de registros y
    reclasificación SCIAN no están en el error de conteo.
20. **Dos escenarios para la caída DENUE 2024** en vez de una hipótesis única
    (`detalles_a_tratar.md` §4 y §9.8). `CLAUDE.md` ya la trata como "cierres reales acumulados"; la
    revisión pide presentarla como hipótesis:
    - **A (actual):** cierres reales acumulados 2020-2023, registrados de golpe.
    - **B:** parte de la caída es depuración del padrón → tasa de oferta atenuada.
    Exportar ambos en `diagnostico.json` y mencionarlo en el drawer. No hace falta duplicar el
    contrato: basta con el rango entre escenarios como sensibilidad reportada.
21. **Verificación:** ningún registro de `prediccion_*.json` con `ic95[1] - ic95[0] < 0.2`; test en
    `test_exportar.py` que lo garantice.

---

## FASE 4 — Demanda potencial por grupo de edad y tipo de servicio *(alta prioridad, ~1 día)*

Hallazgos C y D. Es más barato de lo que parece: **los datos ya están desagregados en disco.**

- `data/interim/censo_ageb_panel.parquet` ya trae `p_0a2, p_3a5, p_6a11, p_12a14` por AGEB y año.
- `data/interim/conapo_mun_quinq.parquet` ya trae grupos quinquenales por alcaldía.
- El DENUE de infancias ya trae `Subcategoría` + `Código SCIAN`.

22. **Renombrar el concepto en toda la UI y la documentación**: "demanda" → **"demanda potencial"**.
    Archivos: `frontend/js/textos.js`, `docs/metodologia.md`, `CLAUDE.md`. Es un cambio de etiqueta,
    pero es exactamente lo que `rubrica.md` §8 pide reconocer ("la ausencia de datos no equivale a
    ausencia de demanda"; una asociación no es causalidad).
23. **Segmentar por servicio** con el mapeo SCIAN ya presente en los datos (edición 2024-11,
    `Alcance = Principal`):

    | Servicio | SCIAN | Establecimientos | Población objetivo |
    |---|---|---:|---|
    | Guardería o estancia infantil | 624411, 624412 | 592 | 0–2 |
    | Preescolar | 611111, 611112 | 2 262 | 3–5 |
    | Primaria | 611121, 611122 | 2 289 | 6–11 |
    | Secundaria (general y técnica) | 611131, 611132, 611141, 611142 | 895 | 12–14 |
    | Varios niveles / educación especial | 611171, 611172, 611181, 611182 | 1 271 | 0–14 (sin segmentar) |

24. **Implementación**: `panel.py` construye un panel por segmento (misma forma, columna `segmento`);
    `modelos.py` **no cambia** — se le pasa cada segmento por separado. `exportar.py` emite la capa
    `demanda` con un nivel extra `segmentos: {0a2, 3a5, 6a11, 12a14, total}`, y `oferta` igual.
    Mantener `total` como valor por defecto: el mapa por omisión no cambia.
25. **Cuidado documentado**: CONAPO es quinquenal (00-04, 05-09, 10-14) y no parte en 0-2/3-5/6-11/12-14.
    El ancla municipal se aplica sobre 0-14 (como hoy) y los segmentos heredan el factor de control;
    registrar esa aproximación en `docs/metodologia.md`, no ocultarla.
26. **Frontend**: un selector de **población objetivo** (`rubrica.md` §2 lo lista como entrada
    esperada) junto al control de capas. Módulo nuevo `frontend/js/segmento.js` + acción en
    `estado.js`; el mapa solo recolorea, no recarga.
27. **Verificación**: suma de segmentos = total por AGEB (test en `test_panel.py`); el selector
    cambia el mapa sin peticiones de red.

---

## FASE 5 — Brecha futura, índice de oportunidad y ranking *(alta prioridad, ~1 día)*

Hallazgos F y G, y el núcleo de `rubrica.md` §2: *"la aplicación debe decirte dónde hay
oportunidades de expansión y cómo rankearlas"*. Hoy el proyecto proyecta dos capas y las deja
separadas; el ejemplo de caso de la rúbrica ("zonas donde la demanda aumentará en tres años,
evitando áreas con oferta ya saturada") no se puede responder con la salida actual.

28. **Cobertura proyectada** en `features.py`, por AGEB y horizonte, sobre las **mismas** réplicas
    Monte Carlo (no sobre las medianas — así el intervalo del índice sale gratis):
    `cobertura_{i,h} = Ŝ_{i,h} / D̂_{i,h} × 1000`.
29. **Índice de oportunidad** `O_{i,h}`, normalizado y explicable en una línea: prioridad alta donde
    la cobertura proyectada queda **por debajo de la mediana de la CDMX** y la demanda potencial cae
    más lento que la oferta. Publicar percentil, no solo el valor crudo.
30. **Filtro de riesgo** (`rubrica.md` §2: *"nivel de riesgo aceptable"*): exponer `p_dec` y la
    confianza como umbral ajustable en la UI; el ranking solo lista unidades que superan el umbral
    elegido. Esto también **resuelve el hallazgo G**: deja de importar que casi todo sea `baja`,
    porque el orden lo da la brecha relativa, no el signo.
31. **Segundo índice, separado**: *Disponibilidad proyectada de servicios para infancias* (vista
    "familias"). **No mezclarlo** con el de oportunidad — una zona buena para abrir servicios es
    justo una con baja cobertura. Dos vistas, dos leyendas, dos textos.
32. **Contrato v1.3**: capa `brecha` pasa de un escalar histórico a
    `{h1,h3,h5} → {cobertura, ic95, percentil, indice_oportunidad}`, con `t_oferta`/`t_demanda`
    conservados como metadato del punto de partida. Actualizar `validar_contrato()` y
    `plans/frontend_specs.md` §17-18.
33. **Frontend**: tabla de ranking ordenable (reutiliza `frontend/js/tabla.js`, ya ordenable) con
    las 20 AGEB de mayor oportunidad de la alcaldía enfocada, y el top de la ciudad en la vista
    general. Al clic, `flyTo` + ficha.
34. **Verificación**: el caso de prueba de `rubrica.md` §8 se puede responder en vivo en menos de
    30 segundos de interacción; ensayarlo antes de la demo.

---

## FASE 6 — Frontend: el cuelgue del mapa *(bloqueante de demo, ~2 h)*

`detalles_a_tratar.md` cierra con esto en mayúsculas, y es lo que un juez verá primero.

### 6.1 Diagnóstico medido (no es el número de polígonos)

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

### 6.2 Correcciones, en orden de impacto

35. **Eliminar `transition: transform`** de `.alcaldias-fondo, .agebs, .confianza-baja, .alcaldias`
    en `frontend/css/mapa.css`. La animación ya la hace D3; la regla CSS es redundante y dañina.
    *Efecto medido: 8 790 ms → 412 ms.*
36. **Quitar `filter: var(--recesivo-filtro)`** de `.mapa__alcaldia--recesivo` (`mapa.css:155-159`).
    `saturate(0) brightness(1.08)` obliga a rasterizar una superficie fuera de pantalla por cada una
    de las 15 vecinas, **a la escala del zoom**. El mismo efecto visual se consigue con el color ya
    definido en `--recesivo-relleno` / `--recesivo-contorno`, sin filtro. *Efecto medido:
    12 301 ms → 8 951 ms adicionales.*
37. **Animar un solo grupo envolvente.** Hoy `aplicarTransform` escribe el atributo en 4 grupos por
    fotograma. Envolverlos en un único `<g class="escenario">` y animar solo ese: una escritura por
    fotograma en vez de cuatro.
38. **Revisar `vector-effect: non-scaling-stroke`** (~2 290 ms de coste medido). Es necesario para
    que el trazo no engorde con el zoom, pero se puede sustituir por `stroke-width` recalculado una
    sola vez **al terminar** la animación, en vez de por fotograma.
39. **Respetar `prefers-reduced-motion`**: con la media query activa, `--d-xs` ya es `0ms`, pero
    `DURACION_ENFOQUE_MS` (820 ms, `mapa.js:39`) está en JS y **no** la respeta. Leerla de
    `matchMedia("(prefers-reduced-motion: reduce)")` y saltar la animación.
40. **Verificación obligatoria**: reejecutar la medición de tareas largas después del parche, en las
    16 alcaldías, con el objetivo de **ninguna tarea > 200 ms**. Incluir el script de medición en
    `frontend/tests/` para que sea reproducible ante los jueces.

> Si tras 35-39 alguna alcaldía siguiera pesada (no se espera), el siguiente escalón es
> `<canvas>` en vez de SVG para la capa de AGEB. **No empezar por ahí**: el problema medido es CSS,
> no volumen de datos, y migrar a canvas costaría la accesibilidad por teclado que ya funciona.

---

## FASE 7 — Tercera fuente y "momentos históricos comparables" *(media, ~medio día)*

41. **`rubrica.md` §3 exige ≥ 3 fuentes con INEGI obligatorio** — ya se cumple (Censo 2010 + 2020,
    DENUE, Marco Geoestadístico, CONAPO), pero **todas son federales**. La rúbrica sugiere
    explícitamente Datos Abiertos de la CDMX, y el repo **ya tiene descargados y sin usar**
    `data/processed/areas_verdes/` y `data/processed/espacios_publicos/`. Integrarlos como **capa de
    contexto por AGEB** (conteo y superficie de equipamiento comunitario) es barato y sube
    directamente la nota de "integración y armonización de datos".
42. **Hallazgo B — tres momentos históricos.** A nivel AGEB la demanda solo tiene 2 censos; eso es
    una limitación real de los datos, no del equipo. La respuesta defendible, que hay que **escribir
    y decir en voz alta**:
    - Oferta, por AGEB: **3 momentos** (2016-10, 2019-11, 2024-11).
    - Demanda, por alcaldía: **serie CONAPO 1990-2040**, decenas de momentos, y es la que alimenta
      el backtest de la fase 2.
    - Demanda, por AGEB: **2 momentos censales**; es el límite de INEGI, y por eso existe la
      contracción hacia la alcaldía.
    Ponerlo en `docs/metodologia.md` §3 y en el drawer de metodología.
43. *(Opcional, alto costo)* Un tercer momento censal por AGEB existiría con el Censo 2000, pero la
    equivalencia geográfica 2000→2020 es mucho peor que la 2010→2020 ya calculada. **No recomendado
    antes de la entrega**; la Encuesta Intercensal 2015 no sirve: no se publica por AGEB.

---

## FASE 8 — Mensaje, documentación y demo *(media, ~medio día)*

44. **Cambiar la promesa.** No decir "muestra en qué alcaldías conviene vivir": los datos no lo
    sostienen. Promesa defendible, la de la revisión:
    > *Identifica las zonas de la CDMX donde podría existir mayor presión, déficit u oportunidad de
    > expansión de servicios para infancias durante los próximos años.*
    Nota: el titular que hoy genera `frontend/js/titular.js` **ya está bien redactado** ("la
    población de 0 a 14 años —la demanda de servicios para infancias— bajaría en 15 de las 16
    alcaldías"). El problema está en el *pitch*, no en la UI.
45. **Sesgos y límites** (`rubrica.md` §8): una sección explícita, en lenguaje llano, sobre que (a)
    ausencia de datos ≠ ausencia de demanda, (b) un establecimiento no mide capacidad, calidad ni
    matrícula (hallazgo E), (c) las proyecciones son condicionales. Parte ya está en el drawer;
    falta el punto (b).
46. **Reconciliar `CLAUDE.md`** con el estado final: contrato v1.3, horizontes 1/3/5, `backtest.py`
    existente, archivos de `plans/` restaurados.
47. **Guion de demo de 3 minutos**, ensayado, que recorra: mapa general → clic en alcaldía (ya sin
    cuelgue) → cambiar horizonte → cambiar población objetivo → ranking de oportunidad → drawer con
    backtest y limitaciones. Los jueces verifican en vivo (`rubrica.md` §7).

---

## Orden de ejecución y dependencias

```
FASE 0 (docs)  ──┐
FASE 1 (h1/h3/h5)├─> FASE 2 (backtest) ──> FASE 3 (incertidumbre) ─┐
FASE 6 (crash) ──┘                                                  ├─> FASE 8 (mensaje/demo)
                    FASE 4 (segmentos) ──> FASE 5 (oportunidad) ────┘
                    FASE 7 (fuentes CDMX) ──────────────────────────┘
```

- **Fases 0, 1 y 6 son independientes entre sí y se pueden paralelizar** (documentación, backend
  de configuración, CSS/JS del mapa: archivos disjuntos).
- **La fase 6 es la de mayor retorno por hora invertida**: dos líneas de CSS eliminan un cuelgue de
  12 segundos que hoy haría fracasar la verificación en vivo.
- **La fase 2 es la única que la rúbrica exige explícitamente y que hoy no existe**; si hubiera que
  recortar alcance, se recorta la 4, no la 2.
- Las fases 4 y 5 comparten el salto de contrato a v1.3: conviene hacerlas en el mismo bloque para
  tocar `exportar.py`, `validar_contrato()` y `frontend/js/api.js` una sola vez.

## Definición de terminado (ampliada sobre la de `CLAUDE.md`)

- [ ] Todo `.md` citado por el código existe en el árbol.
- [ ] `docs/backtest.md` con cifras reales de modelo vs baseline; `data/outputs/backtest.json` existe.
- [ ] Horizontes h1/h3/h5; contrato v1.3 validado por `make validar`.
- [ ] Ningún `ic95` de ancho < 0.2.
- [ ] Ranking de oportunidad consultable y filtrable por nivel de riesgo.
- [ ] Ninguna tarea larga > 200 ms al enfocar cualquiera de las 16 alcaldías (medido, no estimado).
- [ ] `make test` verde; `make pipeline` determinista en dos ejecuciones.
- [ ] Sin CDN, sin errores de consola, Lighthouse accesibilidad ≥ 90.
