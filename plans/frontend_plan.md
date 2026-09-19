# Plan de frontend

Objetivo: visor web de producción, HTML + CSS + JS vanilla (ES modules), sin build en tiempo de
ejecución y sin CDN, que cumpla `plans/frontend_specs.md` (documento **vinculante**, CLAUDE.md
→ "Frontend"). Interfaz con el backend: `data/outputs/prediccion_ageb.json` y
`prediccion_alcaldia.json` (contrato **v1.1**, un solo horizonte `"2027-06"`, sin `serie`, sin
`distribucion_ageb`, sin `agregado_cdmx`, sin `capas.brecha`) y `data/reference/ageb_cdmx_simplificado.geojson`
+ `alcaldias.geojson`. Mientras el backend no exista se desarrolla contra mocks con el mismo
contrato v1.1. Este plan sustituye por completo al anterior (Leaflet, sin desglose de componentes);
`frontend_specs.md` es la fuente de verdad para cualquier detalle no repetido aquí.

## 0. Qué cambia respecto al plan anterior

1. **Mapa:** Leaflet queda descartado. El mapa es SVG propio con **D3 vendorizado**
   (`frontend/vendor/d3/d3-chipos.esm.js`), como exige `frontend_specs.md` §3. No se restaura
   ningún vendor de Leaflet.
2. Paleta, tipografía, layout y componentes quedan reemplazados por los §4–§14 del spec; este plan
   ya no tiene `[SPEC PENDIENTE]`: todo lo que antes era una pregunta abierta al equipo de diseño
   está resuelto en el spec o en la §3 de este plan.
3. El conmutador de capa vive en la cabecera; el control de horizonte es un componente nuevo (§8
   del spec). Ambos se construyen contra el esquema **v1.2** que produce el adaptador de `api.js`
   (§2), no contra el v1.1 crudo.
4. Los mocks se generan en v1.1 (es lo único que el backend produce hoy) y pasan siempre por el
   adaptador antes de llegar a cualquier componente de UI.

## 1. Arquitectura

```
frontend/
  index.html                    HTML semántico: header, nav (migas), main (columna + mapa),
                                 aside (leyenda + franja), footer, <dialog> de metodología
  css/
    tokens.css                  §4: color, tipografía, espaciado, movimiento (única fuente de valores)
    base.css                    reset mínimo, tipografía, foco visible, .visualmente-oculto, dialog
    layout.css                  grid de escritorio (§5.1) y breakpoints ≥1024px
    cabecera.css                cabecera 48px, migas, control segmentado (contenedor)
    titular.css                 titular dinámico, crossfade, altura reservada
    tabla.css                   tabla de predicciones, acordeón, FLIP
    alcaldia.css                vista de alcaldía: resumen, lista de AGEB, buscador
    ficha.css                   ficha de AGEB, mini-gráfica
    horizonte.css                control de horizonte (slider)
    capas.css                   control segmentado de capas
    mapa.css                    SVG del mapa, patrones, clases de veredicto/confianza/recesivo
    leyenda.css                 leyenda + filtro
    franja.css                  franja lateral + drawer de metodología
    movil.css                   hoja inferior de 3 alturas, breakpoints <1024px
    presentacion.css            modo presentación (--escala, ocultamientos)
    estados.css                 esqueleto, error, vacío, pulso de carga
  js/
    main.js                     arranque, orquesta módulos, maneja errores globales, estados (§15)
    config.js                   rutas de datos, versión de contrato esperada, constantes de UI
    api.js                      fetch + validación + adaptador v1.1 → v1.2 (§2) + índices por clave
    estado.js                   almacén observable (sin globales) + sincronía con el hash + región viva
    dom.js                      helpers seguros: crear(tag, attrs, hijos), textContent, sin innerHTML
    formato.js                  números es-MX (Intl), signo menos U+2212, símbolos de veredicto/confianza
    textos.js                   §14: todas las cadenas de la UI, centralizadas, con interpolación
    veredictos.js               resumirVeredictos(registros) (§6.2, §6.5) — usado por titular y tabla
    titular.js                  plantillas §6.3/§6.5, subtítulo y sufijos (§6.4)
    cabecera.js                 migas (§10.6), botón metodología, botón modo presentación
    tabla.js                    tabla vista general + acordeón FLIP (§7.1–7.2)
    alcaldia.js                 vista de alcaldía: resumen, lista de AGEB, buscador (§7.3)
    ficha.js                    ficha de AGEB (§7.4), texto y estados sin_datos
    graficas.js                 mini-gráfica SVG de la ficha (§7.4), a mano, sin D3
    horizonte.js                control de horizonte (§8)
    capas.js                    control segmentado de capas (§9)
    mapa.js                     D3: proyección, capas SVG, vista general, foco, vista de alcaldía,
                                 transición inversa (§10.1–10.3, §10.7)
    leyenda.js                  leyenda + filtro/realce (§10.4)
    franja.js                   franja lateral + drawer de metodología (§10.5)
    interaccion.js              táctil/teclado transversal (§10.8): orden de Tab, Esc, doble toque
    presentacion.js             modo presentación (§10.9)
    movil.js                    hoja inferior de 3 alturas (§11)
  vendor/
    d3/d3-chipos.esm.js         bundle ESM único (geo, zoom, selection, transition, interpolate,
                                 ease + dependencias), generado offline con esbuild, versionado
    d3/README.md                comando exacto para regenerar el bundle
    fonts/InterVariable.woff2, InterVariable-Italic.woff2   Inter 4.x variable, subconjunto latín
  data/                         copia de outputs + geojson (generada por `make frontend-datos`)
  mock/
    generar_mock.py             genera mocks deterministas v1.1 desde las claves reales del GeoJSON
    prediccion_ageb.json · prediccion_alcaldia.json
    prediccion_ageb_v11_invalido.json  (para ?mock=v11: versión/esquema incompatible)
  tests/
    index.html · pruebas.js     pruebas en navegador de funciones puras (adaptador, formato,
                                 resumirVeredictos, invariante titular=tabla)
```

- Ningún vendor de Leaflet se restaura; `grep -ri leaflet frontend/` debe quedar vacío en todo momento.
- Módulos con interfaz explícita; `estado.js` es la única fuente de verdad de la sesión (vista,
  `cve_mun`, `cvegeo`, capa, horizonte activo, orden de tabla, drawer abierto, filtro de leyenda).
  Los módulos se suscriben (`suscribir(fn)`) y emiten acciones (`despachar({tipo, ...})`); sin
  variables globales.
- Hash de URL: `#/alcaldia/007/ageb/0900700011234?capa=oferta&h=hU&orden=cambio&info=1&filtro=baja`.
  Recargar con cualquier hash restaura vista, capa, horizonte, orden, drawer y filtro (checklist §16.2).
- CSP en `<meta>` exactamente como pide el spec §3: `default-src 'self'; style-src 'self'; img-src
  'self' data:; font-src 'self'`. Todo texto con datos vía `textContent` o creación de nodos
  (`dom.js`), nunca `innerHTML` con datos.

## 2. Contrato de datos: adaptador v1.1 → v1.2 (`api.js`)

El backend produce y seguirá produciendo **solo v1.1** (CLAUDE.md, `plans/backend_plan.md`). Las
peticiones de §17 del spec (P1–P5, contrato v1.2 con varios horizontes, `serie`, `distribucion_ageb`,
`agregado_cdmx`, `brecha`) **no se implementan en este plan**: son peticiones al backend, no tareas
del frontend. En su lugar, **todos los componentes de UI se escriben contra el esquema v1.2** y
consumen exclusivamente el resultado de un adaptador en `api.js`, tal como indica el propio spec al
cierre de su §17.

Adaptador `adaptarV11aV12(json, nivel)`:
- `horizontes`: `[{clave: "hU", anios: null, fecha: json.horizonte}]` (una sola entrada).
- Cada registro de capa v1.1 (`{veredicto, delta_pct, tasa_anual_pct, ic95, confianza, n_obs,
  cve_mun}`) se anida sin cambios bajo `registro.h.hU`.
- `serie`, `nivel_base`, `motivo_sin_datos` (si no viene) → `null`/ausentes; esto activa a propósito
  las degradaciones descritas en el spec: §7.4 (ficha sin gráfica, con la nota fija), §7.2 (fila
  desplegada usa el GeoJSON de AGEB en vez de `distribucion_ageb` precalculada), §14.4 (motivo
  "(ausente)" si no hay código).
- `distribucion_ageb` y `agregado_cdmx` quedan ausentes: el subtítulo del titular omite el bloque
  "CDMX ±x %" (§6.4) y la barra de la fila desplegada espera al GeoJSON de AGEB si aún no llegó.
- `capas.brecha` nunca aparece en v1.1, así que el adaptador simplemente no la crea. El spec ya
  dice en su §9 que "Brecha solo aparece si el archivo trae `capas.brecha`"; con eso basta, **no
  se agrega ningún flag adicional** para forzar su ausencia.
- Regla general: **ningún componente de UI (tabla, ficha, titular, slider, leyenda, mapa) lee el
  JSON v1.1 crudo.** Todos leen `registro.h[horizonteActivo]` y la lista `horizontes`, sea que
  `horizonteActivo` valga `"hU"` hoy o `"h3"/"h5"/"h7"` el día que el backend entregue v1.2 real.
  Ese día solo cambia `api.js` (dejar de adaptar, o adaptar un contrato distinto): ningún otro
  módulo se toca.

Pruebas del adaptador (F15): fixtures v1.1 con los 4 veredictos, las 3 confianzas, claves ausentes
del JSON, y verificación de que el objeto adaptado nunca contiene `serie`, `distribucion_ageb`,
`agregado_cdmx` ni `capas.brecha`.

## 3. Decisiones fijas (antes "abiertas" en el spec §18; ya resueltas por el equipo)

No se vuelven a plantear como preguntas; el código se escribe directamente así:

1. **Fecha base y horizontes (§18-1).** No se fuerza 2026/2029/2031/2033. El cliente usa el
   `horizonte` real que trae el archivo, vía el adaptador (`hU`, `fecha = horizonte`). Las
   plantillas de §6 y las etiquetas "CAMBIO A {AÑO}" toman `{año}` de ese campo. El código de F35
   (titular), F40 (tabla), F50 (ficha) y F55 (slider) queda listo para el día en que `horizontes`
   traiga 3 entradas, sin necesitar cambios adicionales.
2. **Horizonte de la oferta (§18-2).** No aplica hoy: v1.1 solo trae un horizonte para demanda y
   para oferta por igual. El slider (F55) implementa la lógica de "un solo horizonte disponible
   para esta capa" de forma genérica (lee `horizontes_disponibles` si existe en el registro), pero
   no hay nada que activar mientras el backend no mande más de un horizonte.
3. **Capa brecha (§18-3).** No se muestra el conmutador "Brecha" porque el archivo v1.1 nunca trae
   `capas.brecha`. Se implementa tal cual dice el spec (§9: "Brecha solo aparece si el archivo trae
   `capas.brecha`"), sin flag aparte para forzar su ausencia: el comportamiento correcto es la
   consecuencia natural de que el adaptador nunca crea esa capa.
4. **Umbrales del §6.2 (§18-4).** Se usan los propuestos en el spec tal cual: 60 % / 15 % / 25 % /
   50 %, `V ≥ 8`. No se parametrizan ni se exponen como configuración.
5. **Nombre y créditos (§18-5).** Nombre: "Infancias CDMX" (spec §2). Sin logotipos por ahora. Pie
   con "Fuentes: INEGI, CONAPO, DENUE" tal como muestra el wireframe del spec §5.3 (el drawer de
   metodología detalla censos 2010/2020, CONAPO y DENUE por separado, §14.6).

## 4. Sistema visual

Los tokens de color, tipografía, espaciado y movimiento del spec §4 se implementan literalmente en
`css/tokens.css`: no se reinterpretan valores. Puntos de atención para la implementación:
- Inter 4.x variable se vendoriza en `vendor/fonts/` (subconjunto latín + latín extendido, ~110 kB),
  con `font-display: swap` y `preload` del archivo normal (spec §4.5). Nunca se referencia Google
  Fonts ni ningún CDN de tipografía.
- La paleta de veredictos (§4.2) es la única fuente de color con significado; en el resto de la UI
  no se usan colores literales fuera de `tokens.css` (checklist de CLAUDE.md: "sin colores
  literales").
- El canal de atenuación por foco (§4.3) usa luminosidad/saturación, nunca opacidad (reservada al
  punteado de confianza baja, §4.2); esto se verifica explícitamente en F65/F70/F75.
- Modo presentación (§4.5, §10.9): `--escala: 1.25` en tokens tipográficos, implementado como
  variable CSS conmutable por clase en `<html>`, no duplicando reglas.

## 5. Mapa de componentes a archivos y secciones del spec

| componente | archivos principales | sección del spec |
|---|---|---|
| Titular dinámico | `js/veredictos.js`, `js/titular.js`, `css/titular.css` | §6 |
| Tabla vista general + acordeón | `js/tabla.js`, `css/tabla.css` | §7.1–7.2 |
| Vista de alcaldía (resumen, lista, buscador) | `js/alcaldia.js`, `css/alcaldia.css` | §7.3 |
| Ficha de AGEB + mini-gráfica | `js/ficha.js`, `js/graficas.js`, `css/ficha.css` | §7.4 |
| Control de horizonte | `js/horizonte.js`, `css/horizonte.css` | §8 |
| Control de capas | `js/capas.js`, `css/capas.css` | §9 |
| Mapa D3 (las 4 sub-vistas/transiciones) | `js/mapa.js`, `css/mapa.css` | §10.1–10.3, §10.7 |
| Leyenda | `js/leyenda.js`, `css/leyenda.css` | §10.4 |
| Franja + drawer metodología | `js/franja.js`, `css/franja.css` | §10.5, §14.6 |
| Cabecera y migas | `js/cabecera.js`, `css/cabecera.css` | §5.2, §10.6 |
| Táctil/teclado/presentación | `js/interaccion.js`, `js/presentacion.js`, `css/presentacion.css` | §10.8–10.9 |
| Layout móvil (hoja inferior) | `js/movil.js`, `css/movil.css` | §11 |
| Accesibilidad transversal | `index.html`, `css/base.css`, `js/estado.js` (región viva) | §13 |
| Textos centralizados | `js/textos.js` | §14 |
| Estados y orquestación | `js/main.js`, `css/estados.css` | §15 |

## 6. Mocks y estados (§15)

`mock/generar_mock.py` (solo biblioteca estándar, semilla fija) lee las propiedades de
`data/reference/ageb_cdmx_simplificado.geojson` (sin imprimir geometrías) y escribe JSON v1.1
deterministas cubriendo: los 4 veredictos, las 3 confianzas, AGEB rurales `sin_datos`, campos
`null`, claves ausentes del JSON, IC asimétricos, oferta con tope `media`, y una alcaldía casi toda
`sin_datos` (para el estado vacío, wireframe 9 de §15).

`api.js` interpreta el parámetro `?mock=`:
- `?mock=1` (o ausente en `frontend/mock/`): datos base descritos arriba.
- `?mock=error`: simula fallo de red (fetch rechazado) → estado 2 de §15 ("No pudimos cargar los
  datos", botón "Reintentar" que repite solo las peticiones fallidas).
- `?mock=v11`: sirve `prediccion_ageb_v11_invalido.json`, con `version` incompatible o esquema
  roto → estado de error "versión de datos incompatible ({v})".
- `?mock=vacio`: sirve una alcaldía con el 100 % de sus AGEB `sin_datos` → estado 3 de §15.
- `?mock=lento`: retrasa artificialmente la respuesta (p. ej. 3–5 s) → estados 1 y 6 de §15
  (esqueleto de carga inicial, pulso de "Cargando AGEB de {alcaldía}…").

Los 7 estados de §15 (carga inicial, error, capa/alcaldía sin datos, AGEB sin datos, datos
incompletos, AGEB cargándose, horizonte no disponible) deben ser reproducibles solo con estos
parámetros de URL, sin tocar DevTools.

## 7. Accesibilidad y rendimiento

- Accesibilidad (§13) se implementa de forma transversal (F95) pero cada componente ya nace con su
  parte: `role`, `aria-*`, gestión de foco y contraste se verifican dentro de la propia tarea que
  crea el componente; F95 es la pasada de integración y auditoría final, no el único lugar donde se
  piensa en accesibilidad.
- Presupuesto de rendimiento y checklist de aceptación (§16) **no son una tarea aparte**: son el
  criterio de "acepta cuando" de la tarea de QA final (F110). Se miden con la pestaña Red (gzip) y
  Lighthouse, no se estiman.
- `prefers-reduced-motion` y `prefers-reduced-transparency` se respetan centralizadamente vía
  media queries en `tokens.css`/`base.css` (los `--d-*` a 0 ms salvo crossfades a 120 ms; leyenda a
  fondo opaco), y cada componente que anima consulta esas variables, nunca duraciones fijas propias.

## 8. Riesgos y supuestos

- Supuesto: los nombres de alcaldía y AGEB salen de los GeoJSON de referencia (`nombre`); el
  contrato de predicciones no los trae.
- Supuesto: el servidor sirve `frontend/` como raíz (`make serve`); rutas relativas en todo.
- Riesgo: el bundle `d3-chipos.esm.js` debe medir ≤ 40 kB gzip (§16.1); si al empaquetar con esbuild
  los módulos elegidos superan ese tamaño, hay que revisar el `tree-shaking` antes de aceptar F0.
- Riesgo: foco en elementos SVG no es uniforme entre navegadores (Safari); por diseño del spec, la
  tabla y la lista de AGEB son la alternativa completa por teclado, así que ningún flujo depende
  de que un `<path>` sea tabulable.
- Riesgo: casi todo AGEB saldrá `baja` (decisión N2 del backend); la intensidad por tasa anual
  (§4.2) y el orden por defecto de la tabla (lo que más baja arriba) dan variación legible aunque
  el mapa sea mayormente de un solo lado de la escala.
- Riesgo: el GeoJSON de AGEB (~420 kB gzip) puede tardar en Fast 4G; se mitiga con el prefetch de
  §10.2 (primer hover con intención o `requestIdleCallback` a los 2 s) y no se adopta TopoJSON salvo
  que la medición real de F110 supere 1.5 s (spec §16.1).
- No hay riesgo de build obligatorio: esbuild se invoca una sola vez y offline para generar el
  vendor de D3 (documentado en `vendor/d3/README.md`); el proyecto en sí no tiene paso de build.

## 9. Tareas

| id | objetivo | archivos | acepta cuando | tam. | depende | paralelo con |
|---|---|---|---|---|---|---|
| F0 | Andamiaje del proyecto + vendorizar D3 (esbuild, offline) | `index.html`, `vendor/d3/d3-chipos.esm.js`, `vendor/d3/README.md`, `vendor/d3/build.mjs`, `Makefile` (target `vendor-d3`) | `make serve` sirve `index.html` vacío sin errores de consola; `grep -ri leaflet frontend/` vacío; pestaña Red sin peticiones a dominios externos; el bundle expone los módulos de §3 y pesa ≤ 40 kB gzip | M | — | — |
| F5 | Tokens CSS y tipografía vendorizada | `css/tokens.css`, `vendor/fonts/InterVariable*.woff2`, `index.html` (preload) | todos los tokens de §4.1–§4.7 en `:root`; contraste `--tinta-3` ≥ 4.5:1 medido; Inter carga sin CDN; `tnum`/`cv11` activos en cifras | S | F0 | F10, F15, F30 |
| F10 | Mocks del contrato v1.1 | `mock/generar_mock.py`, `mock/prediccion_ageb.json`, `mock/prediccion_alcaldia.json`, `mock/prediccion_ageb_v11_invalido.json` | JSON deterministas y válidos v1.1 con los 4 veredictos, 3 confianzas, rurales, nulls, claves ausentes, IC asimétricos, alcaldía casi toda `sin_datos`, archivo de versión inválida separado | M | F0 | F5, F15, F30 |
| F15 | Utilidades puras + adaptador v1.1→v1.2 | `js/dom.js`, `js/formato.js`, `js/config.js`, `js/api.js`, `tests/index.html`, `tests/pruebas.js` | pruebas verdes: formato es-MX (menos U+2212, espacio fino, 1 decimal), `dom.js` sin `innerHTML`, adaptador produce `horizontes=[{clave:'hU',anios:null,fecha:horizonte}]` sin `serie`/`distribucion_ageb`/`agregado_cdmx`/`brecha` | M | F0 | F5, F10, F30 |
| F20 | Estado observable + hash de URL | `js/estado.js` | hash con vista/`cve_mun`/`cvegeo`/capa/horizonte/orden/drawer/filtro se parsea y serializa; recargar restaura todo; `despachar`/`suscribir` sin globales | M | F15 | F30 |
| F25 | Layout de escritorio, cabecera y migas | `index.html`, `css/layout.css`, `css/cabecera.css`, `js/cabecera.js` | reparto de §5.1 correcto a 1280/1024/900 px; cabecera de 48 px con los 4 bloques; migas `<nav aria-label="Ruta">` con `aria-current`, cada nivel navega | M | F5, F20 | F30 |
| F30 | Textos de la UI centralizados | `js/textos.js` | cadenas de §14.1–§14.4 y §14.6 en un solo módulo con interpolación; sin cadenas de UI repetidas hardcodeadas en otros archivos; `grep -rn "delegación" frontend/` vacío | S | F0 | F5, F10, F15, F20, F25 |
| F35 | Titular dinámico | `js/veredictos.js` (`resumirVeredictos`, umbrales §6.2), `js/titular.js`, `css/titular.css` | prueba de invariante titular = tabla; las plantillas de §6.3 y §6.5 producen la frase esperada con los mocks, incl. sufijo de confianza baja y "De mantenerse las tendencias…" a 7 años (código listo aunque hoy solo hay `hU`); crossfade de 200 ms | M | F15, F20, F30 | — |
| F40 | Tabla de predicciones (vista general) + acordeón FLIP | `js/tabla.js`, `css/tabla.css` | 16 filas ordenables (cambio/nombre/confianza) con `aria-sort`; fila desplegada de 136 px con contenido §7.2; FLIP de 200 ms sin salto; hover 100 ms / repliegue 180 ms sin oscilación en barrido manual; usa el mismo `resumirVeredictos` que F35 | L | F35, F20 | F65 |
| F45 | Vista de alcaldía: resumen, lista de AGEB, buscador | `js/alcaldia.js`, `css/alcaldia.css` | resumen de 4 líneas sin acordeón; lista con orden por defecto \|cambio\| descendente, 12 filas + "Ver los {n} AGEB ↓"; buscador con debounce 120 ms, precarga de prefijo, mensaje sin resultados, Enter con resultado único abre ficha | L | F40, F20 | — |
| F50 | Ficha de AGEB + mini-gráfica SVG | `js/ficha.js`, `js/graficas.js`, `css/ficha.css` | SVG 416×168 con puntos censales, tramos, proyección, banda IC95, horizontes ◇/◆, `<figcaption>` oculta con cifras exactas; sin `serie` (siempre, con v1.1) muestra la nota de degradación fija; AGEB `sin_datos` solo muestra puntos si existen | L | F45, F15 | — |
| F55 | Control de horizonte | `js/horizonte.js`, `css/horizonte.css` | `<input type="range">` + `<datalist>`, `aria-valuetext` actualizado en cada `input`, anuncio en `change`; con un solo horizonte (`hU`) queda `disabled` con la nota de §8.6; el código admite min/max dinámico (probado con un fixture de 3 horizontes en `tests/`, aunque hoy no se active); sin peticiones de red al mover | M | F20, F15 | F60 |
| F60 | Control segmentado de capas | `js/capas.js`, `css/capas.css` | `role="radiogroup"` navegable con flechas; "Brecha" no aparece porque el mock v1.1 nunca trae `capas.brecha` (se confirma también con un fixture que si la trajera, aparecería); cambia `&capa=` en el hash; el nombre de la capa es visible en los 6 lugares de §9 | M | F20, F30 | F55 |
| F65 | Mapa D3: vista general | `js/mapa.js`, `css/mapa.css` | `geoMercator().fitExtent()` con recálculo *debounced* a 150 ms; las 6 capas SVG de §3; 16 alcaldías coloreadas, contorno exterior, hover con elevación 120 ms, tooltip a 12 px del puntero; zoom desactivado en esta vista; sin `innerHTML` | L | F0, F5, F20 | F40 |
| F70 | Mapa D3: transición de foco, vista de alcaldía y transición inversa | `js/mapa.js` (continuación), `css/mapa.css` | gesto de 820 ms de §10.2 con los tiempos exactos de la tabla; `scaleExtent [k,6k]` con rueda/pellizco en vista de alcaldía; botón "Reencuadrar" solo tras paneo manual; transición inversa de §10.7 devuelve el foco a la fila; prefetch en hover 100 ms o `requestIdleCallback` a los 2 s; con `prefers-reduced-motion`, corte directo + crossfade de 120 ms | L | F65 (mismo archivo, en serie), F45, F50 | — |
| F75 | Leyenda con filtro y realce | `js/leyenda.js`, `css/leyenda.css` | conteos correctos según la vista (alcaldías o AGEB); cada fila es `<button aria-pressed>`; filtra la tabla en paralelo ("Mostrando 14 de 16 · Quitar filtro"); Esc tiene prioridad sobre retroceder de nivel; rampa de brecha de 5 cortes implementada aunque no visible hoy | M | F65 | F80 |
| F80 | Franja lateral y drawer de metodología | `js/franja.js`, `css/franja.css`, `index.html` (`<dialog>`) | `<dialog>` modal desde la derecha (560 px / 100 % móvil), foco inicial en el título, Esc cierra y devuelve el foco al disparador; hash `#/…&info=1` enlazable; las 8 secciones del texto de §14.6 presentes íntegras | M | F30, F25 | F65, F70, F75 |
| F85 | Táctil, teclado y modo presentación | `js/interaccion.js`, `js/presentacion.js`, `css/presentacion.css` | primer/segundo toque en `pointer: coarse` según §10.8; orden de Tab de §10.8; Esc retrocede un nivel con prioridad drawer > filtro de leyenda > vista; modo presentación (tecla `P`, botón "⤢" o `?presentacion=1`) aplica `--escala:1.25`, oculta buscador/orden/pie/franja y mantiene capa/slider/migas | M | F70, F40, F55, F60 | — |
| F90 | Layout móvil: hoja inferior de 3 alturas | `css/movil.css`, `js/movil.js` | hoja con 3 alturas (128 px / 50 dvh / 88 dvh) por asa arrastrable o botón cíclico con `aria-label`; slider y capa alcanzables en las 3 alturas; al enfocar una alcaldía la hoja sube a media y el vuelo encuadra por encima; la ficha sube la hoja a alta; tableta 768–1023 px con hoja de 560 px alineada a la izquierda | L | F25, F55, F60, F70 | — |
| F95 | Accesibilidad completa | `index.html`, `css/base.css`, `js/estado.js` (región viva) + ajustes en F40/F45/F50/F65/F70/F75/F80/F85/F90 | estructura semántica de §13 completa; región viva global con los 6 anuncios de ejemplo del spec; gestión de foco de §13 en las 5 transiciones; `prefers-reduced-motion` y `prefers-reduced-transparency` respetados; Lighthouse accesibilidad ≥ 95 | L | F40, F45, F50, F65, F70, F75, F80, F85, F90 | — |
| F100 | Estados de carga/error/vacío/incompleto + orquestación | `js/main.js`, `css/estados.css` | los 7 estados de §15 reproducibles con `?mock=error`/`?mock=v11`/`?mock=vacio`/`?mock=lento`; caché en memoria `Map<cve_mun, paths[]>`; ningún `<g>` se vacía para redibujar; aviso de datos incompletos una sola vez por sesión | M | F15, F20, F35, F40, F65, F10 | — |
| F105 | Enlace con datos reales | `Makefile` (target `frontend-datos`) | con `data/outputs/` del backend, la app carga sin `?mock=1`, pasando igual por el adaptador de F15; no se editan objetivos existentes del Makefile | S | F100 | — |
| F110 | QA final: rendimiento y checklist de aceptación | — (correcciones puntuales en los módulos existentes) | checklist completo de §16.2 (24 ítems) verde, incl. presupuesto de §16.1 medido con la pestaña Red (gzip); Lighthouse accesibilidad ≥ 95 y rendimiento ≥ 90; sin CDN; sin `innerHTML` con datos; sin `!important`; sin estilos en línea | M | F95, F100, F105, F90 | — |

Paralelizables (archivos disjuntos): {F5, F10, F15, F30}; {F20, F30}; {F55, F60}; {F40, F65};
{F65/F70 con F80}; {F75, F80}. F65 y F70 comparten `mapa.js`: en serie. F95 y F110 son pasadas
transversales y dependen de casi todo lo anterior por diseño (auditoría de integración, no
desarrollo de un componente nuevo).

## 10. Verificación

`make serve` y abrir `http://localhost:8000/?mock=1`; repetir con `?mock=error`, `?mock=v11`,
`?mock=vacio` y `?mock=lento` para los 7 estados de §15. Recorrer el flujo completo (vista general
→ alcaldía → AGEB → volver) con ratón y solo teclado; emular `prefers-reduced-motion` y
`prefers-reduced-transparency`, y los tres tipos de daltonismo en DevTools; probar en 360 px, 768 px
y 1440 px. Pestaña Red: sin peticiones a dominios externos, presupuesto de §16.1 respetado.
`tests/index.html` verde (incluye la prueba de invariante titular = tabla y las pruebas del
adaptador v1.1→v1.2). Lighthouse accesibilidad ≥ 95 y rendimiento ≥ 90. Con datos reales, tras
`make pipeline && make frontend-datos`, la app carga sin `?mock=1` y muestra el mismo comportamiento
(slider deshabilitado con la nota de §8.6, sin "Brecha" en el conmutador, ficha con la nota de
degradación en vez de gráfica).
