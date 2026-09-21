# Solución: color uniforme de AGEB al enfocar una alcaldía

Continúa `correccion/action_plan.md` §8.2 (puntos 41-45, congelamiento del clic en alcaldía) y
responde al defecto nuevo reportado tras ese arreglo: al enfocar una alcaldía, los AGEB se pintaban
con un único color en vez de por quintil.

## 1. Causa raíz

**`data/reference/ageb_cdmx_simplificado.geojson` tiene los 2453 anillos de AGEB devanados en
sentido inverso al que exige `d3-geo`.** No es un problema de datos de demanda/oferta, de
clasificación por percentiles, de CSS ni del orden de capas SVG: es una única inversión de
orientación introducida por el proceso de simplificación de geometría.

### Mecanismo

`d3-geo` recorta cada polígono contra el antimeridiano (necesario para proyecciones como
Mercator). Ese recorte decide qué lado de un anillo es "adentro" según su devanado (regla de la
mano derecha vista desde fuera de la esfera, RFC 7946). Con el devanado invertido, el algoritmo
interpreta cada AGEB como *"todo el planisferio menos ese polígono"* y cierra el `<path>`
añadiendo, además del contorno real (pequeño), un segundo anillo del tamaño del dominio
proyectado — un rectángulo casi-cuadrado de ~346 574 × 346 574 unidades, **idéntico para los 2453
AGEB** porque depende solo de la proyección activa, no de la geometría de cada uno.

Como los AGEB se pintan uno tras otro en el mismo `<g class="agebs">` (orden de documento = orden
de pintado en SVG), ese rectángulo gigante de cada `<path>` tapa a todos los pintados antes; lo que
se ve en pantalla es, en la práctica, el color del **último** AGEB pintado extendido a toda la
escena — de ahí "el mismo color, uniforme". Los AGEB reales (invisibles, del tamaño de una manzana)
seguían ahí, correctamente coloreados, pero ocultos bajo los rectángulos.

### Evidencia (medida, no inferida)

**(a) Datos** — `data/outputs/prediccion_ageb.json` (v1.4), Iztapalapa (`cve_mun="007"`) vs. CDMX:

| | CDMX | Iztapalapa |
|---|---|---|
| AGEB totales | 2453 | 458 |
| con `nivel_base` (demanda) | 2366 | 453 |
| valores distintos de `nivel_base` | 2178 | 447 |
| con celdas en las 4 ramas | — | 458/458 en cada una |

La vista sirve `data/` real (`config.js#rutaDatos`: sin `?mock=`, usa `RUTA_BASE_DATOS="data/"`).
No hay colapso de datos ni AGEB huérfanos.

**(b) Cálculo de color** — reproduje `nivelesPorRama → coberturaProyectada → indiceOportunidad →
indiceCompuesto → clasificadorQuintiles` en Node con los datos reales (`repro.mjs`,
`h3`/`todas`/pesos 3-3-3-3, mismos parámetros que el estado por omisión):

```
Iztapalapa, cortes GLOBALES de CDMX: {1: 91, 2: 91, 3: 90, 4: 91, 5: 90, sin_datos: 5}
Iztapalapa, cortes LOCALES (solo Iztapalapa): {1: 91, 2: 91, 3: 90, 4: 91, 5: 90, sin_datos: 5}
cobertura educacion: 361 valores distintos de 453 (93 en 0)
cobertura salud:     424 valores distintos de 453 (30 en 0)
cobertura comercio:  448 valores distintos de 453 (6 en 0)
cobertura verde:     375 valores distintos de 453 (78 en 0)
```

Los 5 quintiles quedan casi perfectamente repartidos (~90 AGEB cada uno) tanto con cortes
calculados sobre toda la CDMX (el comportamiento real y documentado de `main.js#calcularComposicion`
— "no filtra por alcaldía", intencional) como con cortes recalculados solo sobre Iztapalapa: **no
hay colapso por empates**. La hipótesis de "cortes globales vs. por alcaldía" queda descartada como
causa de este defecto (aunque sí es una decisión de producto documentada, ver §3).

**(c) Render (DOM real, navegador headless del entorno)** — antes de la corrección, al enfocar
Iztapalapa:

```js
// 20 <path class="mapa__ageb"> muestreados
getBBox() → { w: 346574.53125, h: 346574.59375 }   // IDÉNTICO en los 20
```

El atributo `d` de un AGEB (`0900700010638`) traía dos anillos:

```
M391.477,252.455L...ZM268994.187,-154014.449L268994.187,-146940.681L...
   ↑ contorno real, pequeño         ↑ rectángulo gigante, mismas 4 esquinas en TODOS los AGEB
```

Reproduje el mismo resultado en Node con `d3-geo` puro (sin ningún código de `mapa.js` de por
medio), pasándole la geometría cruda del AGEB desde el propio GeoJSON: el rectángulo aparece igual.
Invertir manualmente el orden de los puntos del anillo (sin tocar nada más) lo elimina
(`d.length`: 770 → 186). Confirmé el patrón midiendo la orientación de los tres archivos de
referencia con la fórmula del área con signo (shoelace, lon/lat como x/y):

```
ageb_cdmx_simplificado.geojson:  2453 anillos con área > 0  (0 con área < 0)  ← el que usa el frontend
ageb_cdmx.geojson (sin simplificar): 0 con área > 0 (2453 con área < 0)      ← correcto
alcaldias.geojson:                    0 con área > 0 (16 con área < 0)      ← correcto (por eso el mapa de alcaldías nunca tuvo este defecto)
```

100% de los AGEB del archivo *simplificado* está invertido; el archivo sin simplificar y el de
alcaldías (que sí se renderizan bien) están devanados al revés de él. Esto aísla el origen al paso
de simplificación (herramienta fuera de `frontend/`, no identificada por nombre en este diagnóstico
porque no hay un `tools/build_geo.py` con ese paso documentado en `docs/perfil_datos.md`; ver
riesgos).

**(d) Interacción con los cambios previos ya aplicados** — ninguno de los cambios de
`correccion/action_plan.md` §8.2 causa ni enmascara este defecto:
- La omisión de `pintarAgebs()` cuando `registrosAgeb` está vacío no interviene: el registro sí
  llega (`main.js` pasa `composicion.porClave` ya resuelto antes de que `mapa.js` pinte).
- El orden de capas SVG (`alcaldias-fondo, agebs, confianza-baja, alcaldias`) es correcto para el
  propósito documentado (`.mapa__alcaldia--enfocada { visibility: hidden }` existe justo porque
  `alcaldias` se pinta encima de `agebs`); confirmado en DOM: la alcaldía enfocada tiene
  `visibility: hidden` y su clase de prioridad es irrelevante mientras está oculta.
- La clase `mapa__alcaldia--enfocada` y el atributo `stroke-width` escalado no interactúan con la
  orientación de los anillos: son ortogonales al bug.
- `cve_mun`/`cvegeo` SÍ coinciden entre GeoJSON y contrato (verificado con Python sobre los 2453
  AGEB y sobre los 458 de Iztapalapa: intersección exacta, mismo `cve_mun` en ambas fuentes) — la
  hipótesis de discrepancia de claves queda descartada.

**(e) `leyenda.css` (selector de ID)** — la regla `#contenedor-mapa[data-filtro-tercil=…]` solo se
activa con un filtro de leyenda pulsado (`estado.filtroLeyenda !== null`); confirmé en el árbol de
accesibilidad de la sesión de reproducción que ningún filtro estaba activo al reproducir el
defecto. No contribuye.

## 2. Corrección aplicada

`data/reference/` es de solo lectura (`CLAUDE.md`): la corrección **no** toca ese archivo. Vive en
`frontend/js/mapa.js`, del lado del cliente, aplicada una sola vez a cada `agebGeoJSON` que entra a
`montarMapa`/`actualizarAgeb` (memoizada por referencia con `WeakMap`, no reprocesa en cada
repintado):

- `areaPlanaAnillo(anillo)`: área con signo (shoelace) de un anillo en lon/lat.
- `anilloConOrientacionCorrecta(anillo, esExterior)`: invierte el anillo solo si su signo no es el
  que exige `d3-geo` (exterior: área negativa, igual que `alcaldias.geojson`; interior/hueco: signo
  contrario). Es defensiva e idempotente: si el pipeline de datos corrigiera el archivo de
  referencia algún día, esta función dejaría de tocar nada, no lo rompería.
- `repararOrientacionGeometria`/`repararAgebGeoJSON`: aplican lo anterior a `Polygon`/`MultiPolygon`
  y a toda la colección, sin mutar el objeto original (los AGEB de este dataset no tienen huecos,
  pero la función cubre el caso general).

Verificado en el navegador tras el cambio: los `getBBox()` de los AGEB pasan de ser todos idénticos
(346574×346574) a valores reales de manzana urbana (3-12 unidades, todos distintos); la captura de
Iztapalapa muestra el mosaico esperado de 5 tonos, coincidente con `Alta 147 / Media 157 / Baja
149 / Sin datos 5` de la leyenda.

## 3. Decisión de diseño que SÍ requiere confirmación del equipo (no la cambié)

`main.js#calcularComposicion` calcula los quintiles/terciles de color sobre **toda la CDMX**, nunca
solo sobre la alcaldía enfocada (comentario explícito en el código, línea ~449: "calcularComposicion
no filtra por alcaldía"). Con los datos reales esto no colapsa (§1.b), así que **no encontré
justificación para cambiarlo** y no lo toqué — pero lo señalo porque:
- Afecta la lectura del mapa: dentro de una alcaldía homogénea (todas sus AGEB parecidas entre sí
  pero distintas del resto de la CDMX), los 5 tonos podrían concentrarse en 2-3 quintiles
  visualmente parecidos, no por bug sino porque la comparación es contra toda la ciudad. Es
  coherente con la semántica "prioridad relativa en la CDMX" (spec §4.2) pero es una elección de
  producto, no un hecho técnico neutro.
- Cambiarlo (recortar el universo de comparación a la alcaldía activa) alteraría la invariante
  "resumen=ranking" y el spec §4.2/§6 mencionados en el encargo. **No lo implico ni lo recomiendo
  sin decisión explícita del equipo**: lo dejo documentado para que se decida aparte de esta
  corrección.

## 4. Consolidación de los cambios previos (`action_plan.md` §8.2, puntos 41-45)

Confirmé en el código y con mediciones en el navegador que los 5 puntos siguen aplicados y
correctos; los conservo tal cual:

| Punto | Estado | Evidencia |
|---|---|---|
| 41. Sin `transition: transform` | Conservado | No aparece en `mapa.css`; comentario explicativo en su lugar. |
| 42. Sin `filter` en `--recesivo` | Conservado | `.mapa__alcaldia--recesivo` usa solo `fill`/`stroke`. |
| 43. Un solo grupo animado (`g.escenario`) | Conservado | `aplicarTransform` escribe un único `transform`. |
| 44. `stroke-width` recalculado una vez, no por fotograma | Conservado y verificado | Medido en el navegador tras zoom: `stroke-width` escala correctamente (0.097px a escala alta), sin `vector-effect`. |
| 45. Respeta `prefers-reduced-motion` | Conservado | `duracionEfectiva()` consulta `matchMedia` antes de animar. |

Puntos específicos pedidos:
- **`.mapa__alcaldia--enfocada { visibility: hidden }` es correcto**, no un parche: dado el orden
  de capas del spec §3 (`alcaldias` se pinta después de `agebs`), es la única forma de que la
  alcaldía enfocada no tape sus propios AGEB sin reordenar las 6 capas del spec (que si se
  reordenaran, romperían el contorno recesivo de las vecinas, pintado en `alcaldias-fondo`,
  *debajo* de `agebs` a propósito). Lo conservo.
- **Trazo escalado a zoom alto**: medido en el navegador después de 8 pasos de zoom con rueda,
  `stroke-width` computado = 0.097px — fino, sin engordar ni desaparecer, sin tapar el relleno.
- **Salida limpia (`volverAVistaGeneral`/`Esc`)**: verificado en DOM tras 10 ciclos
  enfocar→Esc→enfocar→Esc en Iztapalapa: `path.mapa__ageb` vuelve a 0, `.mapa__alcaldia--enfocada`
  y `.mapa__alcaldia--recesivo` vuelven a 0 elementos. Sin residuos.

## 5. Interruptores `TEMP-DIAG`

Eliminados los cuatro (el diagnóstico ya identificó y corrigió la causa raíz, no hacen falta como
mecanismo permanente):
- `DIAG`/`?diag=sinanim,sinhover,sinpatron,sinagebs` en `mapa.js` — interruptores y sus 6 usos.
- `DIAG_SIN_PANEL`/`?diag=sinpanel` en `main.js` — interruptor y su rama en `recalcularYPintar`.
- `.mapa__lienzo--sin-patron .mapa__alcaldia--sin-datos` en `mapa.css` — regla sin código que la
  active tras quitar `DIAG`.

## 6. Pruebas de regresión (`frontend/tests/`)

Nuevo `pruebas_mapa.js`/`index_mapa.html` (mismo runner sin framework que `pruebas_composicion.js`),
13 pruebas, todas verdes en el navegador:
- Orientación de anillos: el anillo real de `ageb_cdmx_simplificado.geojson` da área positiva (mal
  devanado); `anilloConOrientacionCorrecta`/`repararOrientacionGeometria`/`repararAgebGeoJSON` lo
  corrigen, son idempotentes, no mutan el objeto original y memoizan por referencia. Cubre
  `Polygon` y `MultiPolygon`.
- `clasificadorQuintiles` con 95% de valores empatados en 0 y con 100% `sin_datos`: no lanza,
  separa `sin_datos` sin mezclarlo con el quintil más bajo.
- `indiceCompuesto` + `clasificadorQuintiles` con una rama completamente empatada: el compuesto no
  colapsa (se reparte en ≥4 de 5 quintiles) mientras otra rama tenga variación real.
- Coherencia `cvegeo`/`cve_mun` entre `ageb_cdmx_simplificado.geojson` y
  `prediccion_ageb.json` reales: cada AGEB del GeoJSON tiene registro en el contrato con el mismo
  `cve_mun`, y viceversa.
- `pintarAgebs` (a través de `montarMapa`/`actualizarAgeb` reales, GeoJSON sintético de 5 AGEB):
  dibuja exactamente 5 `<path>` al enfocar la alcaldía, cada uno con una clase de prioridad
  distinta de las otras cuatro.

## 7. Congelamiento (medido, punto 7 del encargo)

Con el `PerformanceObserver` de `longtask` del navegador, 10 ciclos de
enfocar Iztapalapa → `Esc` → enfocar Iztapalapa (la alcaldía con más AGEB, 458): **2 tareas largas
en 10 ciclos, máximo 71 ms** — muy por debajo de los 100 ms pedidos y del umbral de 200 ms de
`action_plan.md` punto 46. Nodos DOM estables: 458 `path.mapa__ageb` al terminar enfocado, 0 tras
`Esc`, sin acumulación entre ciclos.

## 8. Riesgos frente a `frontend_requisitos.md` / `rubrica.md`

- **No identifiqué la herramienta exacta que generó el devanado invertido** (no hay un paso de
  simplificación de AGEB documentado por nombre en `docs/perfil_datos.md` ni en `Makefile`): la
  corrección del lado del cliente es robusta y suficiente para producción, pero si en algún momento
  se regenera `ageb_cdmx_simplificado.geojson` con la orientación ya correcta, la función
  defensiva simplemente no hará nada (verificado con la prueba de idempotencia) — no hay riesgo de
  doble inversión.
- La decisión de §3 (quintiles globales CDMX vs. por alcaldía) queda sin resolver a propósito: es
  una decisión de producto que toca `frontend_specs.md` §4.2/§6, fuera del alcance de "corregir un
  defecto visual".
- No corrí Lighthouse en esta sesión (fuera del alcance del encargo); los cambios de `mapa.js`
  no tocan atributos `aria-*` ni la tabla/lista alternativa (F40/F45), así que no debería haber
  regresión de accesibilidad, pero no está medido en este pase.

## 9. Cómo verificar manualmente

1. `make serve` (o `python3 -m http.server 8000 --directory frontend`), abrir `http://localhost:8000`.
2. Clic en Iztapalapa (o cualquier alcaldía grande): los AGEB deben verse en un mosaico de 5 tonos,
   no en un bloque de un solo color.
3. Consola del navegador, sin enfocar nada: `document.querySelectorAll('path.mapa__ageb').length`
   → `0` en vista ciudad; tras enfocar, coincide con el número de AGEB de esa alcaldía.
4. `frontend/tests/index_mapa.html` y `frontend/tests/index_composicion.html`: deben mostrar
   "N/N pruebas OK".

## Resumen (5 líneas)

La causa del color uniforme era el devanado invertido de los 2453 anillos de
`ageb_cdmx_simplificado.geojson`, que hacía que `d3-geo` cerrara cada AGEB con un rectángulo
gigante idéntico que tapaba a los demás; se corrigió del lado del cliente (`mapa.js`), sin tocar
`data/`, con una función defensiva e idempotente. Los cinco cambios previos de congelamiento
(§8.2 puntos 41-45) se revisaron, se confirmaron correctos con mediciones nuevas y se conservaron
tal cual; los interruptores `TEMP-DIAG` se retiraron. Se añadieron 13 pruebas de regresión
(orientación de anillos, quintiles ante empates, coherencia `cvegeo`/`cve_mun`, conteo de `pintarAgebs`)
y se midió el congelamiento con `PerformanceObserver` (máx. 71 ms en 10 ciclos). Queda sin resolver,
a propósito, si los quintiles de color deben compararse contra toda la CDMX o solo contra la
alcaldía activa — es una decisión de producto, no un defecto, y afecta la semántica del spec §4.2.
No se corrió Lighthouse ni se identificó la herramienta exacta que introdujo el devanado invertido.
