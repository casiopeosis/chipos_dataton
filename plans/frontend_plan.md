# Plan de frontend — Habitancia

Objetivo: visor web de producción, HTML + CSS + JS vanilla (ES modules), sin build en tiempo de
ejecución y sin CDN, que implemente `correccion/frontend_requisitos.md` sobre
`plans/frontend_specs.md` (documento **vinculante**, CLAUDE.md → "Frontend"). Interfaz con el
backend: `data/outputs/prediccion_ageb.json` y `prediccion_alcaldia.json` (contrato **v1.4**:
capas `demanda` por segmento de población objetivo + `capas.ramas.{educacion,salud,comercio,verde}`
por celda de filtro, sin `capas.oferta` ni `capas.brecha`; `plans/backend_plan.md` §7) y
`data/reference/ageb_cdmx_simplificado.geojson` + `alcaldias.geojson`. Mientras el backend no
publique v1.4 completo, se desarrolla contra mocks con ese mismo contrato
(`frontend/mock/generar_mock.py`, reescrito, §6).

## 0. Qué cambia respecto al plan anterior

> **Revisión 2026-09-20 — reescritura completa.** El plan anterior desarrollaba un visor de dos
> capas (demanda/oferta) contra un adaptador v1.1→v1.2, con un titular de frase autogenerada. Ese
> producto queda **retirado**: `correccion/frontend_requisitos.md` redefine el frontend como
> **Habitancia**. Lo que sigue igual: el mapa SVG con D3 vendorizado, el sistema de tokens, la
> mecánica de acordeón FLIP, la franja lateral + drawer, la accesibilidad transversal y el
> Makefile/mocks-por-parámetro-de-URL. Lo que cambia de raíz:

1. **Contrato de destino: v1.4 directo, sin capa intermedia v1.2/v1.1 como objetivo.** El adaptador
   v1.1→v1.2 de la versión anterior **se conserva como camino de degradación adicional** (si algún
   día el backend solo pudiera producir v1.1/v1.2), pero deja de ser el contrato de trabajo
   principal: todos los componentes se escriben contra v1.4 (`plans/frontend_specs.md` §17).
2. **Titular de frase autogenerada → resumen estructurado (Nivel 1).** Se elimina por completo
   `veredictos.js#resumirVeredictos` como generador de frases; sus umbrales de clasificación (§6.2
   de la versión anterior del spec) quedan retirados. Lo sustituye un componente de campos
   etiquetados, sin texto interpretativo dinámico (`correccion/frontend_requisitos.md` §1, §13).
3. **Control segmentado de "capa" → selector de "vista de mapa" (una vista general + 4 ramas)**,
   sobre el mismo `<g>` de AGEB (`plans/frontend_specs.md` §9).
4. **Cuatro componentes sin precedente**: población objetivo, prioridades (pesos), filtros por
   rama, comparar alcaldías — todos nuevos, todos client-side y en tiempo real
   (`plans/frontend_specs.md` §10.10-§10.13).
5. **Motor de composición cliente**, módulo nuevo (`js/composicion.js`): calcula cobertura, índice
   de oportunidad e índice compuesto para las 2 453 AGEB en el navegador, sobre las celdas de
   filtro que publica el backend (`plans/frontend_specs.md` §17.4). Es el módulo más grande y más
   importante de esta revisión: sin él, pesos y filtros no pueden ser "en tiempo real".
6. **Corrección de rendimiento del mapa aplicada de origen** (`correccion/action_plan.md` Fase 8):
   el plan anterior no la tenía porque el cuelgue se descubrió después. Esta revisión la incorpora
   como parte de la tarea F65/F70 (§9), no como un parche posterior — construir el mapa multi-vista
   sobre el mapa ya corregido evita heredar el defecto.

## 1. Arquitectura

```
frontend/
  index.html                    HTML semántico: header, nav (migas), main (columna de
                                 configuración/resultado + mapa), aside (leyenda + franja),
                                 footer, <dialog> "Entender esta zona / Metodología"
  css/
    tokens.css                  §4 del spec: color (incl. escala de prioridad §4.2 y de
                                 tendencia heredada §4.3), tipografía, espaciado, movimiento
    base.css                    reset mínimo, tipografía, foco visible, .visualmente-oculto, dialog
    layout.css                  grid de escritorio (§5) y breakpoints ≥1024px
    cabecera.css                cabecera 48px, migas, selector de vista de mapa (contenedor)
    configuracion.css           población objetivo, horizonte, tipo de búsqueda (§5 del spec)
    prioridades.css             círculos de peso por rama (§10.10)
    filtros.css                 panel de filtros por 4 ramas (§10.11)
    resumen.css                 resumen estructurado Nivel 1 (§6 del spec; reemplaza titular.css)
    ranking.css                 tabla de ranking, acordeón, FLIP (§7 del spec; reemplaza tabla.css)
    alcaldia.css                vista de alcaldía: resumen, lista de zonas, buscador
    ficha.css                   ficha de zona, mini-gráficas (dos, §10.5)
    comparar.css                panel de comparación entre dos alcaldías (§10.13)
    horizonte.css                control de horizonte (slider), paradas 1/3/5
    vista-mapa.css               selector de vista de mapa (vista general + 4 ramas, §9)
    mapa.css                    SVG del mapa, patrones, clases de prioridad/confianza/recesivo
                                 — SIN `transition: transform` en los grupos animados por D3
                                 (correccion/action_plan.md §8.2 punto 41) ni `filter` en
                                 `.mapa__alcaldia--recesivo` (punto 42)
    leyenda.css                 leyenda + filtro (terciles de oportunidad/disponibilidad)
    franja.css                  franja lateral + drawer "Entender esta zona / Metodología"
    ayuda.css                   icono "?" y su popover (§10.14)
    movil.css                   hoja inferior de 3 alturas, breakpoints <1024px
    presentacion.css            modo presentación (--escala, ocultamientos)
    estados.css                 esqueleto, error, vacío, pulso de carga
  js/
    main.js                     arranque, orquesta módulos, maneja errores globales, estados
    config.js                   rutas de datos, versión de contrato esperada (v1.4, con v1.1/
                                 v1.2 como degradación), constantes de UI
    api.js                      fetch + validación del contrato v1.4 + índices por clave;
                                 conserva `adaptarV11aV12` y su cadena hacia v1.4 como
                                 degradación (§2)
    composicion.js              MOTOR DE COMPOSICIÓN CLIENTE (spec §17.4): suma de celdas por
                                 filtro, cobertura, índice de oportunidad por rama, índice
                                 compuesto, índice de disponibilidad — puro, sin DOM, testeable
    estado.js                   almacén observable (sin globales) + sincronía con el hash:
                                 vista de mapa, cve_mun, cvegeo, población objetivo, horizonte,
                                 tipo de búsqueda, pesos (4), filtros (por rama), umbral de
                                 riesgo, orden de ranking, drawer abierto, comparación activa
    dom.js                      helpers seguros: crear(tag, attrs, hijos), textContent, sin innerHTML
    formato.js                  números es-MX (Intl), signo menos U+2212, símbolos y terciles
    textos.js                   TODAS las cadenas de la UI, citando la sección de
                                 frontend_specs.md que las define; incluye los textos "?"
                                 (§10.14) copiados literalmente de frontend_requisitos.md
    poblacion.js                selector de población objetivo (§5.3)
    horizonte.js                control de horizonte (§8), paradas 1/3/5, deshabilitado por rama
    busqueda.js                 selector "oportunidad de expansión / disponibilidad" (§5.5)
    prioridades.js              círculos de peso por rama (§10.10)
    filtros.js                  panel de filtros por rama (§10.11)
    riesgo.js                   filtro de nivel de riesgo (§10.12)
    resumen.js                  resumen estructurado Nivel 1 (§6 del spec)
    ranking.js                  ranking por AGEB + acordeón FLIP (§7 del spec)
    alcaldia.js                 vista de alcaldía: resumen, lista de zonas, buscador
    ficha.js                    ficha de zona (§7.4 del spec), entrada a Nivel 2
    graficas.js                 dos mini-gráficas SVG de Nivel 2 (población, servicios) + cobertura
    explicacion.js               bloque "¿Qué explica este resultado?" (§10.7, círculos no editables)
    comparar.js                  panel de comparación entre dos alcaldías (§10.13)
    ayuda.js                     icono "?" y su popover (§10.14)
    vista_mapa.js                selector de vista de mapa (§9)
    mapa.js                     D3: proyección, capas SVG, vista general, foco, vista de
                                 alcaldía, transición inversa — un solo <g> de escenario
                                 animado (correccion/action_plan.md §8.2 punto 43)
    leyenda.js                  leyenda + filtro/realce, terciles (§10.4)
    franja.js                   franja lateral + drawer "Entender esta zona / Metodología" (§10.6)
    interaccion.js              táctil/teclado transversal (§10.15): orden de Tab, Esc, doble toque
    presentacion.js             modo presentación (§10.15)
    movil.js                    hoja inferior de 3 alturas (§11 del spec)
  vendor/
    d3/d3-chipos.esm.js         bundle ESM único, sin cambios respecto a la versión anterior
    d3/README.md
    fonts/InterVariable.woff2, InterVariable-Italic.woff2
  data/                         copia de outputs + geojson (generada por `make frontend-datos`)
  mock/
    generar_mock.py             genera mocks deterministas v1.4 (contrato con ramas y celdas)
                                 desde las claves reales del GeoJSON; conserva la generación de
                                 fixtures v1.1/v1.2 para probar la degradación del adaptador
    prediccion_ageb.json · prediccion_alcaldia.json      (v1.4, fixture principal)
    prediccion_ageb_v11.json · prediccion_alcaldia_v11.json   (v1.1 real, degradación)
    prediccion_ageb_v11_invalido.json                    (versión/esquema incompatible)
  tests/
    index.html · pruebas.js     pruebas en navegador de funciones puras (formato, adaptador,
                                 invariante resumen=ranking)
    pruebas_composicion.js      pruebas del motor de composición (spec §17.5): oferta cero,
                                 rama sin dato, invariantes [0,1], independencia de pesos
```

- Ningún vendor de Leaflet se restaura; `grep -ri leaflet frontend/` debe quedar vacío en todo
  momento (regla heredada, sin cambios).
- Módulos con interfaz explícita; `estado.js` es la única fuente de verdad de la sesión. Se amplía
  su forma respecto a la versión anterior: además de vista/`cve_mun`/`cvegeo`/orden/drawer/filtro
  de leyenda, ahora guarda `poblacion`, `horizonte`, `busqueda` (oportunidad/disponibilidad),
  `pesos: {educacion, salud, comercio, verde}` (1-5 cada uno), `filtros: {educacion: {...},
  salud: {...}, comercio: {...}, verde: {...}}`, `umbralRiesgo`, `comparando: [cve_mun, cve_mun] |
  null`, `vistaMapa`. Los módulos se suscriben (`suscribir(fn)`) y emiten acciones
  (`despachar({tipo, ...})`); sin variables globales.
- Hash de URL, ampliado:
  `#/alcaldia/007/ageb/0900700011234?vista=salud&h=h3&pob=primaria&busqueda=oportunidad&pesos=4.5.3.2&filtros=...&orden=oportunidad&info=1&comparar=007.010`.
  Recargar con cualquier hash restaura el escenario completo (checklist de aceptación §16.2 del
  spec). Los pesos se codifican como cuatro dígitos en orden fijo
  (educación.salud.comercio.verde) para no alargar la URL.
- CSP en `<meta>` exactamente como pide el spec §3: `default-src 'self'; style-src 'self'; img-src
  'self' data:; font-src 'self'`. Todo texto con datos vía `textContent` o creación de nodos
  (`dom.js`), nunca `innerHTML` con datos — regla que ahora también cubre las cadenas de
  `explicacion.js` y `comparar.js`, que son las que más fácil sería tentar a construir con
  interpolación de HTML.

## 2. Contrato de datos: v1.4 directo + adaptador heredado como degradación

`api.js` valida el contrato v1.4 (`plans/frontend_specs.md` §17.2) como camino principal. El
adaptador `adaptarV11aV12` de la versión anterior de este plan **no se borra**: se conserva como
una cadena de degradación de dos pasos (`v1.1 → v1.2 → v1.4-mínimo`), documentada pero no
prioritaria — si el backend algún día solo pudiera entregar v1.1/v1.2 (por ejemplo, durante una
migración parcial), el frontend seguiría funcionando con capacidades reducidas: una sola rama
visible ("educación", mapeada desde la antigua `capas.oferta`), sin filtros por celda (todas las
celdas colapsadas en una sola), sin segmentos de población (`total` como único segmento). Este
camino se prueba con `?mock=v11`, igual que antes.

**Regla general, ampliada:** ningún componente de UI (ranking, ficha, resumen, mapa, comparar) lee
el JSON v1.4 crudo ni ejecuta las fórmulas del motor de composición por su cuenta. Todos consumen
la salida de `composicion.js`, que a su vez lee `registro.celdas[filtro seleccionado]` /
`registro.segmentos[población seleccionada]` a través de `api.js`. El día que el contrato cambie de
forma (una v1.5 hipotética), solo se tocan `api.js` y `composicion.js`.

Pruebas del contrato y del adaptador heredado (F15): fixtures v1.4 con los tres terciles de
oportunidad, las tres confianzas, celdas ausentes, claves ausentes del JSON, `Ŝ=0` con `D̂>0`, una
rama completa `sin_datos`, y verificación de que `adaptarV11aV12` sigue produciendo una forma
consumible por `composicion.js` sin que ningún componente de nivel superior necesite saberlo.

## 3. Decisiones fijas

No se vuelven a plantear como preguntas; el código se escribe directamente así:

1. **Fecha base y horizontes.** `fecha_base = 2026-06`, horizontes `h1/h3/h5` = 2027/2029/2031.
   `delta_pct`/`ic95` desde `fecha_base`. Las ramas educación/salud/comercio solo traen `h1`/`h3`;
   verde no trae horizontes — el slider se comunica en consecuencia (`horizonte.js`,
   `plans/frontend_specs.md` §8).
2. **Escala de color del mapa.** Sequencial de prioridad (§4.2 del spec) para el índice compuesto y
   cada rama; la escala divergente de tendencia (§4.3) queda reservada a la gráfica de población de
   Nivel 2 — nunca colorea el mapa ni el ranking.
3. **Capa `brecha`.** No existe como capa del backend en v1.4; el equivalente lo calcula
   `composicion.js` (cobertura + índice de oportunidad), así que no hay conmutador "Brecha" que
   mostrar ni ocultar — es una vista, no una capa aparte.
4. **Constante `K` del ajuste de tendencia** (spec §10.2 de metodología, `K=5` pp/año). No se
   expone como configuración de UI; vive en `composicion.js` como constante documentada, igual que
   el backend la documenta en `config.py`.
5. **Terciles del resumen Nivel 1** (spec §6.2): percentil 33/66 sobre `O`/`IC`, entre unidades del
   mismo nivel territorial. No se parametrizan.
6. **Nombre y créditos.** Nombre: "Habitancia" (spec §2). Sin logotipos por ahora. Pie con
   "Fuentes: INEGI, CONAPO, DENUE, Datos Abiertos CDMX" (añade Datos Abiertos CDMX respecto a la
   versión anterior, por las ramas de comercio/verde).
7. **Top N del ranking en vista general.** 20 zonas por omisión (`correccion/action_plan.md` Fase
   6 punto 33), con "Ver más" para ampliar.

## 4. Sistema visual

Los tokens del spec §4 se implementan literalmente en `css/tokens.css`: no se reinterpretan
valores. Puntos de atención, sobre lo ya establecido en la versión anterior de este plan:
- La escala de prioridad (§4.2 del spec) y la escala de tendencia heredada (§4.3) **coexisten en el
  mismo archivo de tokens**, pero nunca en el mismo componente: `mapa.js` y `ranking.js` solo usan
  clases derivadas de `--prioridad-*`; `graficas.js` (gráfica A de Nivel 2) es el único consumidor
  de `--sube-*`/`--baja-*`/`--mantiene`. Un test de `grep` en CI (o al menos documentado como
  verificación manual) confirma que `mapa.css`/`ranking.css` no referencian tokens de tendencia.
- Los círculos de prioridad (interactivos, `--peso-relleno`/`--peso-vacio`) y los círculos de
  explicación (no editables, `--tinta-2`) usan **marcado HTML distinto** (`role="slider"` vs.
  `role="img"` con `aria-readonly`), no solo una clase CSS distinta — la distinción tiene que
  sobrevivir a un lector de pantalla, no solo a la vista (`plans/frontend_specs.md` §10.7,
  §10.10).
- Inter 4.x variable vendorizada, sin cambios respecto a la versión anterior.

## 5. Mapa de componentes a archivos y secciones del spec

| componente | archivos principales | sección del spec |
|---|---|---|
| Pantalla inicial | `js/main.js`, `css/layout.css` | §5.1 |
| Selección de alcaldía (buscador) | `js/alcaldia.js` | §5.2 |
| Población objetivo | `js/poblacion.js`, `css/configuracion.css` | §5.3, §10.15 |
| Horizonte | `js/horizonte.js`, `css/horizonte.css` | §8 |
| Tipo de búsqueda | `js/busqueda.js`, `css/configuracion.css` | §5.5 |
| Resumen estructurado Nivel 1 | `js/resumen.js`, `css/resumen.css` | §6 |
| Ranking por AGEB + acordeón | `js/ranking.js`, `css/ranking.css` | §7 |
| Vista de alcaldía (resumen, lista, buscador) | `js/alcaldia.js`, `css/alcaldia.css` | §7.3 |
| Ficha de zona | `js/ficha.js`, `css/ficha.css` | §7.4 |
| Selector de vista de mapa | `js/vista_mapa.js`, `css/vista-mapa.css` | §9 |
| Mapa D3 (vista general, foco, alcaldía, inversa) | `js/mapa.js`, `css/mapa.css` | §3, §10.1-10.3, §10.9 |
| Leyenda | `js/leyenda.js`, `css/leyenda.css` | §10.4 |
| Gráficas de Nivel 2 (población, servicios, cobertura) | `js/graficas.js`, `css/ficha.css` | §10.5 |
| Franja + drawer "Entender esta zona / Metodología" | `js/franja.js`, `css/franja.css` | §10.6, §14.6-14.7 |
| Explicación por rama (círculos no editables) | `js/explicacion.js` | §10.7 |
| Cabecera y migas | `js/main.js`, `css/cabecera.css` | §10.8 |
| Prioridades (pesos) | `js/prioridades.js`, `css/prioridades.css` | §10.10 |
| Filtros por rama | `js/filtros.js`, `css/filtros.css` | §10.11 |
| Filtro de nivel de riesgo | `js/riesgo.js` | §10.12 |
| Comparar alcaldías | `js/comparar.js`, `css/comparar.css` | §10.13 |
| Iconos "?" | `js/ayuda.js`, `css/ayuda.css` | §10.14 |
| Táctil/teclado/presentación | `js/interaccion.js`, `js/presentacion.js`, `css/presentacion.css` | §10.15 |
| Layout móvil (hoja inferior) | `js/movil.js`, `css/movil.css` | §11 |
| Accesibilidad transversal | `index.html`, `css/base.css`, `js/estado.js` (región viva) | §13 |
| Textos centralizados | `js/textos.js` | §14 |
| Estados y orquestación | `js/main.js`, `css/estados.css` | §15 |
| **Motor de composición cliente** | `js/composicion.js` | §17.4 |

## 6. Mocks y estados

`mock/generar_mock.py` (solo biblioteca estándar, semilla fija) lee las propiedades de
`data/reference/ageb_cdmx_simplificado.geojson` (sin imprimir geometrías) y escribe JSON **v1.4**
deterministas cubriendo: los tres terciles de oportunidad/disponibilidad en las cuatro ramas, las
tres confianzas, AGEB rurales `sin_datos`, celdas de filtro ausentes, `Ŝ=0` con `D̂>0` en varias
AGEB (para probar que el motor de composición no las marca `sin_datos`), una rama completa
`sin_datos` en algunas AGEB (para probar la renormalización de pesos), el segmento 15–17 con
confianza tope `media`, y una alcaldía casi toda `sin_datos` (estado vacío). Conserva además la
generación de fixtures v1.1/v1.2 (`prediccion_ageb_v11.json`, etc.) para probar la cadena de
degradación de §2.

`api.js` interpreta el parámetro `?mock=`, mismo mecanismo que la versión anterior:
- `?mock=1` (o ausente en `frontend/mock/`): datos base v1.4 descritos arriba.
- `?mock=error`: simula fallo de red → estado 2 de §15 del spec.
- `?mock=v11`: sirve el fixture v1.1 real → prueba la cadena de degradación completa (§2).
- `?mock=version_invalida`: sirve el archivo deliberadamente inválido.
- `?mock=vacio`: alcaldía con el 100 % de sus AGEB `sin_datos` → estado 3.
- `?mock=lento`: retrasa artificialmente la respuesta → estados 1 y 6.

Los 9 estados de §15 del spec (7 heredados + 2 nuevos de rama-sin-dato) deben ser reproducibles
solo con estos parámetros de URL, sin tocar DevTools.

## 7. Accesibilidad y rendimiento

- Accesibilidad (§13 del spec) transversal, con cada componente naciendo con su parte (`role`,
  `aria-*`, foco, contraste) verificada en la propia tarea que lo crea; una pasada de integración
  final (F95 renombrada) audita el conjunto, con énfasis especial en los componentes nuevos:
  círculos de prioridad/explicación (`role="slider"`/`role="img"`, nunca solo color), panel de
  filtros (agrupación con `fieldset`/`legend` por rama) y comparar (tabla accesible, no solo
  columnas visuales).
- Presupuesto de rendimiento y checklist (§16 del spec) son el criterio de aceptación de la tarea
  de QA final (F110), igual que antes, **más el presupuesto nuevo del motor de composición**
  (§16.1 del spec: < 80 ms por recálculo completo) — medido con `performance.now()` alrededor de
  `composicion.js#recalcular`, no estimado.
- `prefers-reduced-motion`/`prefers-reduced-transparency` centralizados en `tokens.css`/`base.css`,
  sin cambios de mecanismo.

## 8. Riesgos y supuestos

- **Riesgo principal, nuevo en esta revisión: el tamaño del contrato v1.4 — resuelto (Fase 6).**
  Publicar celdas de filtro por rama (§17.3 del spec) multiplica el tamaño de
  `prediccion_ageb.json` frente a la versión de dos capas. Medido con datos reales: 21.4 MB sin
  comprimir / ~1.02 MB gzip, muy por encima del presupuesto original de 600 kB. La mitigación que
  proponía esta sección (fusionar 1-2 celdas marginales) se descartó tras medir su ahorro real
  (~4 %, insuficiente — gzip ya comprime la estructura repetida entre celdas). Decisión del equipo:
  mantener la granularidad completa de celdas y el archivo único, y subir el presupuesto documentado
  a ≤ 1.1 MB gzip (`plans/frontend_specs.md` §16.1). Sigue con carga diferida, así que no afecta el
  render inicial ni el presupuesto estático.
- **Riesgo: el motor de composición se ejecuta en cada movimiento de un slider de peso.** Si el
  usuario arrastra rápido, se debe *debounce*ar el recálculo pesado (percentiles, paso 3 de §17.4
  del spec) a un máximo de una vez por `requestAnimationFrame`, igual que ya hacía el slider de
  horizonte en la versión anterior — mismo patrón, aplicado a un cálculo más caro.
- **Riesgo heredado: casi todo AGEB puede salir con oportunidad "Alta" si los pesos favorecen una
  rama con oferta muy baja en toda la ciudad.** Ya no es indeseable como lo era con el veredicto de
  dos clases (`correccion/detalles_a_tratar.md` hallazgo G): el ranking sigue diferenciando por
  percentil aunque el tercil textual se concentre, porque el ranking ordena por el valor continuo,
  no por el tercil. Se documenta como comportamiento esperado, no como bug.
- Supuesto: los nombres de alcaldía y AGEB salen de los GeoJSON de referencia; el contrato de
  predicciones no los trae — sin cambios respecto a la versión anterior.
- Supuesto: el servidor sirve `frontend/` como raíz (`make serve`); rutas relativas en todo.
- Riesgo heredado: el bundle `d3-chipos.esm.js` debe medir ≤ 40 kB gzip; sin cambios respecto a la
  versión anterior (no se añaden módulos de d3 nuevos para Habitancia).
- Riesgo heredado, ya resuelto de origen en esta revisión: el cuelgue del mapa
  (`correccion/action_plan.md` Fase 8) se corrige **antes** de construir el selector de vista de
  mapa (F65/F70 en §9), no después — evita reconstruir sobre código roto.
- No hay riesgo de build obligatorio: esbuild se invoca una sola vez y offline para el vendor de
  D3; el proyecto en sí no tiene paso de build.

## 9. Tareas

| id | objetivo | archivos | acepta cuando | tam. | depende | paralelo con |
|---|---|---|---|---|---|---|
| F0 | Andamiaje del proyecto + vendorizar D3 (heredado, sin cambios) | `index.html`, `vendor/d3/*`, `Makefile` | `make serve` sirve `index.html` vacío sin errores; `grep -ri leaflet frontend/` vacío; bundle ≤ 40 kB gzip | M | — | — |
| F5 | Tokens CSS y tipografía vendorizada (extendido: escala de prioridad §4.2, tokens de pesos §4.5) | `css/tokens.css`, `vendor/fonts/*`, `index.html` | tokens de §4.1-§4.7 del spec en `:root`; contraste `--tinta-3` ≥ 4.5:1; escala de prioridad y de tendencia coexisten sin mezclarse | S | F0 | F10, F15, F30 |
| **F8** | **Corrección de rendimiento del mapa** (`correccion/action_plan.md` Fase 8, movida al principio de esta revisión) | `css/mapa.css`, `js/mapa.js` | ninguna tarea larga > 200 ms al enfocar cualquiera de las 16 alcaldías (medido); sin `transition: transform` en grupos animados por D3; sin `filter` en `.mapa__alcaldia--recesivo` | M | F0 | F5 |
| F10 | Mocks del contrato v1.4 (+ v1.1/v1.2 heredados) | `mock/generar_mock.py`, `mock/prediccion_*.json` | JSON deterministas v1.4 con terciles, confianzas, `Ŝ=0`, rama `sin_datos`, segmento 15-17; fixtures v1.1/v1.2 conservados | L | F0 | F5, F15, F30 |
| F15 | Utilidades puras + validación v1.4 + adaptador heredado | `js/dom.js`, `js/formato.js`, `js/config.js`, `js/api.js`, `tests/pruebas.js` | pruebas verdes: formato es-MX, `dom.js` sin `innerHTML`, `api.js` valida v1.4 y encadena `adaptarV11aV12` sin que los componentes lo noten | M | F0 | F5, F10, F30 |
| **F16** | **Motor de composición cliente** | `js/composicion.js`, `tests/pruebas_composicion.js` | implementa §17.4 del spec literal; `Ŝ=0,D̂>0` da percentil máximo nunca `sin_datos`; rama `sin_datos` renormaliza pesos; `O`/`IC` ∈ [0,1] siempre; < 80 ms sobre 2453 AGEB (medido) | L | F15 | F20 |
| F20 | Estado observable + hash de URL (ampliado: población, horizonte, búsqueda, pesos, filtros, riesgo, comparar) | `js/estado.js` | hash con los 11 campos de §1 se parsea y serializa; recargar restaura el escenario completo; `despachar`/`suscribir` sin globales | L | F16 | F30 |
| F25 | Layout de escritorio, cabecera y migas | `index.html`, `css/layout.css`, `css/cabecera.css`, `js/main.js` (cabecera) | reparto correcto a 1280/1024/900 px; cabecera con selector de vista de mapa; migas navegables | M | F5, F20 | F30 |
| F30 | Textos de la UI centralizados (incl. copy literal de `frontend_requisitos.md` y ayudas "?") | `js/textos.js` | cadenas de §14 del spec en un solo módulo; ayudas "?" con las 3 partes (qué es/por qué importa/cómo interpretarlo); `grep -rn "delegación" frontend/` vacío; sin frases interpretativas generadas dinámicamente en ningún otro módulo | M | F0 | F5, F10, F15, F20, F25 |
| F31 | Población objetivo, horizonte, tipo de búsqueda | `js/poblacion.js`, `js/horizonte.js`, `js/busqueda.js`, `css/configuracion.css`, `css/horizonte.css` | selector de 6 poblaciones con sugerencia automática de nivel educativo (no forzada); slider 1/3/5 con degradación por rama (§8 del spec); búsqueda oportunidad/disponibilidad sin red al cambiar | L | F20, F30 | F35 |
| F35 | Prioridades (pesos) + filtro de riesgo | `js/prioridades.js`, `js/riesgo.js`, `css/prioridades.css` | círculos `role="slider"` 1-5 por rama; "Restablecer prioridades"; umbral de riesgo filtra sin red; solo afecta índice compuesto y ranking, nunca los datos originales | M | F16, F20, F30 | F31 |
| F40 | Filtros por rama | `js/filtros.js`, `css/filtros.css` | 4 sub-paneles (§10.11 del spec) con las opciones exactas de `frontend_requisitos.md` §10; "Restablecer filtros"; resumen breve del escenario activo siempre visible; actualiza mapa/ranking/ficha/gráficas sin red | XL | F16, F20, F30, F31 | — |
| F45 | Resumen estructurado Nivel 1 | `js/resumen.js`, `css/resumen.css` | campos de §6.1 del spec, sin frase autogenerada; terciles de §6.2 correctos; invariante resumen=ranking (misma fuente, `composicion.js`) | M | F16, F20, F30 | F50 |
| F50 | Ranking por AGEB + acordeón FLIP | `js/ranking.js`, `css/ranking.css` | columnas de §7.1 del spec; FLIP de 200 ms sin salto; orden por defecto oportunidad/disponibilidad descendente; usa el mismo resultado de `composicion.js` que F45 | L | F45, F20 | F80 |
| F55 | Vista de alcaldía: resumen, lista de zonas, buscador | `js/alcaldia.js`, `css/alcaldia.css` | resumen Nivel 1 de alcaldía (§6.3); lista ordenada por \|oportunidad\| descendente, 12 filas + "Ver los {n}"; buscador con debounce 120 ms | L | F50, F20 | — |
| F60 | Ficha de zona (Nivel 1) | `js/ficha.js`, `css/ficha.css` | Nivel 1 sin gráficas (§7.4 del spec); botón "Entender esta zona"; AGEB `sin_datos` con motivo | M | F55, F45 | F65 |
| F65 | Selector de vista de mapa | `js/vista_mapa.js`, `css/vista-mapa.css` | `role="radiogroup"` con 5 opciones; cambia solo color/leyenda/ranking/título/ficha, nunca recrea geometría; peso no altera color en vista individual de rama (§9 del spec, verificado con test manual) | M | F16, F20, F30 | F60 |
| F70 | Mapa D3: vista general (sobre la corrección de F8) | `js/mapa.js`, `css/mapa.css` | `geoMercator().fitExtent()` con debounce 150 ms; 6 capas SVG; hover con elevación 120 ms; coloreado por vista activa (§9); sin `innerHTML` | L | F8, F5, F20, F65 | F50 |
| F75 | Mapa D3: transición de foco, vista de alcaldía y transición inversa | `js/mapa.js` (continuación) | gesto de 820 ms con un solo `<g class="escenario">` animado (F8); `scaleExtent [k,6k]`; botón "Reencuadrar"; transición inversa devuelve foco al ranking; prefetch en hover 100 ms | L | F70 (mismo archivo, en serie), F55, F60 | — |
| F80 | Leyenda con terciles, filtro y realce | `js/leyenda.js`, `css/leyenda.css` | 3 categorías legibles (§4.2 del spec) con conteos correctos; `<button aria-pressed>`; filtra el ranking en paralelo | M | F70 | F85 |
| F85 | Franja lateral y drawer "Entender esta zona / Metodología" | `js/franja.js`, `css/franja.css`, `index.html` (`<dialog>`) | `<dialog>` modal desde la derecha; foco inicial en título; Esc cierra y devuelve foco; hash enlazable; contenido A-D de §10.6 del spec presente | M | F30, F25 | F70, F75, F80 |
| F86 | Gráficas de Nivel 2 (población, servicios, cobertura) | `js/graficas.js` | 3 bloques de §10.5 del spec: población con histórico/proyección/banda (escala de tendencia); servicios respetando filtros activos, sin línea futura para verde; cobertura con referencia CDMX | L | F16, F85, F60 | F87 |
| F87 | Explicación por rama (círculos no editables) | `js/explicacion.js`, `css/franja.css` (o propio) | círculos `role="img" aria-readonly` distintos de los de prioridad; icono "?" por rama; nunca frase automática | M | F16, F85 | F86 |
| F88 | Comparar alcaldías | `js/comparar.js`, `css/comparar.css` | conserva escenario activo; indicadores lado a lado de §10.13 del spec; nunca declara un ganador ni genera frase automática | L | F16, F20, F45 | — |
| F89 | Iconos "?" (sistema de ayuda) | `js/ayuda.js`, `css/ayuda.css` | popover con las 3 partes fijas, anclado al icono, dentro de la misma vista; cubre los 9 conceptos de `frontend_requisitos.md` §20 | M | F30 | F31, F35, F40 |
| F90 | Táctil, teclado y modo presentación | `js/interaccion.js`, `js/presentacion.js`, `css/presentacion.css` | orden de Tab ampliado (§10.15 del spec); Esc con prioridad drawer > filtro de leyenda > vista; modo presentación oculta buscador/orden/pie/franja | M | F75, F50, F31, F65 | — |
| F91 | Layout móvil: hoja inferior de 3 alturas | `css/movil.css`, `js/movil.js` | 3 alturas con el contenido reordenado de §11 del spec; horizonte y vista de mapa alcanzables en las 3 | L | F25, F31, F65, F75 | — |
| F95 | Accesibilidad completa | `index.html`, `css/base.css`, `js/estado.js` (región viva) + ajustes en F35/F40/F45/F50/F70/F75/F80/F85/F86/F87/F88/F90/F91 | estructura semántica §13; región viva con los 7 anuncios ampliados; gestión de foco en todas las transiciones; Lighthouse accesibilidad ≥ 95 | XL | todo lo anterior | — |
| F100 | Estados de carga/error/vacío/incompleto + orquestación | `js/main.js`, `css/estados.css` | los 9 estados de §15 del spec reproducibles con `?mock=*`; caché en memoria; ningún `<g>` se vacía para redibujar | M | F16, F20, F45, F50, F70, F10 | — |
| F105 | Enlace con datos reales | `Makefile` (target `frontend-datos`) | con `data/outputs/` del backend en v1.4, la app carga sin `?mock=1` | S | F100 | — |
| F110 | QA final: rendimiento y checklist de aceptación | — (correcciones puntuales) | checklist completo de §16.2 del spec verde, incl. presupuesto de composición < 80 ms; Lighthouse accesibilidad ≥ 95, rendimiento ≥ 90; caso de uso de jueces (`frontend_requisitos.md` §24) completo sin recargar | L | F95, F100, F105, F91 | — |

Paralelizables (archivos disjuntos): {F5, F10, F15, F30}; {F8, F5}; {F31, F35}; {F45, F50 tras F16};
{F86, F87}; {F70, F50 tras F65}. F70 y F75 comparten `mapa.js`: en serie. F95 y F110 son pasadas
transversales, dependen de casi todo lo anterior por diseño. **F16 (motor de composición) es el
nodo crítico**: bloquea F20, F35, F40, F45, F65, F86, F87, F88, F100 — conviene entregarlo temprano
y con pruebas sólidas (F16 incluye `tests/pruebas_composicion.js` desde el primer commit, no al
final).

## 10. Verificación

`make serve` y abrir `http://localhost:8000/?mock=1`; repetir con `?mock=error`, `?mock=v11`,
`?mock=version_invalida`, `?mock=vacio` y `?mock=lento` para los 9 estados de §15 del spec. Recorrer
el flujo completo de `correccion/frontend_requisitos.md` §3 (pantalla inicial → alcaldía → población
→ horizonte → búsqueda → pesos → filtros → mapa/ranking → zona → Nivel 1 → Nivel 2 → comparar) con
ratón y solo teclado; emular `prefers-reduced-motion`/`prefers-reduced-transparency` y los tres
tipos de daltonismo en DevTools; probar en 360 px, 768 px y 1440 px. Pestaña Red: sin peticiones
externas, presupuesto de §16.1 del spec respetado (incl. el ampliado de v1.4). `tests/index.html` y
`tests/pruebas_composicion.js` verdes. Lighthouse accesibilidad ≥ 95, rendimiento ≥ 90. Con datos
reales, tras `make pipeline && make frontend-datos`, la app carga sin `?mock=1` y reproduce el caso
de uso de jueces de `correccion/frontend_requisitos.md` §24 de principio a fin.
