# Especificación de diseño del frontend

Documento vinculante para `frontend/` (CLAUDE.md → "Frontend"). Resuelve los marcadores
`[SPEC PENDIENTE]` de `plans/frontend_plan.md`. Lo que requiere datos que el contrato v1.1 no trae
se pide en §17 ("Peticiones al backend"), y la UI se degrada si no llegan (§8.6). Las decisiones que
no son de diseño van marcadas **[DECISIÓN DEL EQUIPO]** (§18).

**Cambios que esta especificación obliga a hacer en `plans/frontend_plan.md`** (actualizarlo antes de F6):
1. El mapa pasa de Leaflet a **SVG propio con d3-geo + d3-zoom vendorizados** (§3). F0 ya no restaura Leaflet.
2. La paleta, la tipografía y el layout del plan quedan reemplazados por §4–§7.
3. El conmutador de capa pasa a la cabecera; el control de horizonte se agrega como componente nuevo (§8).
4. Los datos mock se generan con el esquema v1.2 de §17, y el adaptador de v1.1 va en `api.js`.

---

## 1. Dirección estética

Estilo editorial suizo, como el de un portafolio de referencia (design.byform). Se toma su
estructura y su carácter, no su marca ni sus textos.

- **Tipografía.** Una sola familia neo-grotesca, **Inter** (variable), para todo. El texto grande
  del titular se compone como un párrafo de revista: sangría en la primera línea, guiones y
  espaciado ajustado. Todas las cifras son tabulares.
- **Color.** La página es monocroma: blanco roto, tinta casi negra y un solo gris para las líneas.
  El color aparece **solo** para codificar veredictos. Si algo tiene color, significa algo.
- **Ritmo.** Retícula de 8 px, líneas de 1 px, sin sombras, tarjetas ni iconos decorativos.
  Toda la información es texto, tabla o mapa.
- **Dónde nos apartamos de la referencia:**
  1. El mapa ocupa ≥ 60 % del ancho, no ~45 %. Es el objeto de análisis, no un adorno.
  2. Hay controles visibles (capa y horizonte), porque es una herramienta y no un portafolio.
  3. El texto es más pequeño y compacto, para que quepan las 16 filas sin scroll en 1080 px de alto.

## 2. Producto

- Nombre provisional: **"Infancias CDMX — Pronóstico de demanda"**, abreviado "Infancias CDMX".
  [DECISIÓN DEL EQUIPO: nombre y créditos institucionales, §18-5.]
- Audiencias:
  - **Jurado y autoridades**, en proyección (hay modo presentación, §10.9).
  - **Analistas**, en uso autónomo (orden de tablas, buscador, enlaces compartibles).
- La UI está en español de México. Siempre se dice "alcaldía" y "AGEB" (en mayúsculas).
  Nunca "delegación", "hex", "backtest" ni "shrinkage".

## 3. Stack y decisión de mapa

**Decisión: SVG propio con d3.** Los módulos son d3-geo, d3-zoom, d3-selection, d3-transition,
d3-interpolate y d3-ease, más sus dependencias (d3-array, d3-color, d3-dispatch, d3-drag, d3-timer).
Van como un solo paquete ESM vendorizado en `frontend/vendor/d3/d3-chipos.esm.js`, que se genera una
vez fuera de línea con esbuild y se versiona. `vendor/d3/README.md` explica cómo regenerarlo. No hay
paso de build en tiempo de ejecución.

Por qué d3 y no Leaflet ni MapLibre:
- **Sin teselas no hace falta un motor de teselas.** Leaflet anima el zoom transformando el pane con
  CSS y redibuja los paths al terminar. Eso produce un "salto" al final de `flyToBounds` y hace
  inestables el `transform` del pop y las transiciones de `fill`.
- **Con SVG propio controlamos todo:**
  - el zoom es un `transform` sobre un `<g>` con `d3.interpolateZoom`, un vuelo suave y continuo;
  - los trazos no escalan (`vector-effect: non-scaling-stroke`);
  - el color transiciona por CSS (`transition: fill`);
  - la atenuación son clases CSS;
  - el pop es un `transform` sobre el `<g>` de la alcaldía.
- **MapLibre se descarta** porque exige WebGL y más de 200 kB, y dibujaría de nuevo los polígonos en
  canvas, fuera del DOM accesible.

Detalles del mapa:
- **Proyección.** `d3.geoMercator().fitExtent()` al área del mapa con 32 px de margen. Se recalcula al
  redimensionar, con 150 ms de *debounce*, sin animación.
- **Capas SVG**, de abajo arriba:
  1. `g.alcaldias-fondo`: silueta de las vecinas.
  2. `g.agebs`: polígonos AGEB de la alcaldía en foco.
  3. `g.confianza-baja`: superposición de punteado.
  4. `g.alcaldias`: contornos y relleno en vista general.
  5. `g.realce`: contorno de hover o foco.
  6. `defs`: patrones.
- **Zoom libre.** Desactivado en la vista general, que es un encuadre fijo y editorial. En la vista
  de alcaldía se permiten rueda y pellizco, con `scaleExtent` entre [k_encuadre, 6·k_encuadre], y hay
  un botón "Reencuadrar" (§10.3).
- **Seguridad.** Todo texto con datos se inserta con `textContent` o creando nodos, nunca con
  `innerHTML`. CSP en `<meta>`: `default-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'`.

## 4. Tokens

Todos se definen en `css/tokens.css`, sobre `:root`. No se usan colores literales fuera de ese archivo.

### 4.1 Color base (monocromo)

Contrastes medidos contra `--papel`.

| token | valor | uso | contraste |
|---|---|---|---|
| `--papel` | `#FAFAF8` | fondo de página y del mapa | — |
| `--tinta` | `#111111` | texto principal, contornos activos | 18.1:1 |
| `--tinta-2` | `#555553` | texto secundario, encabezados de tabla | 7.1:1 |
| `--tinta-3` | `#6E6E6B` | notas y metadatos (mínimo permitido para texto) | 4.9:1 |
| `--linea` | `#D9D9D5` | reglas de tabla y divisor de columnas (decorativo) | — |
| `--linea-fuerte` | `#858581` | contornos de polígonos que se deben distinguir | 3.5:1 |
| `--foco` | `#111111` | anillo de foco de 2 px con 2 px de separación | 18.1:1 |
| `--superficie` | `#FFFFFF` | drawer, tooltip, hoja móvil | — |
| `--esqueleto` | `#ECECE8` | bloques de carga | — |

### 4.2 Veredictos

La escala es divergente azul ↔ ocre, legible con deuteranopía, protanopía y tritanopía. No hay rojo
contra verde, y ningún veredicto es "bueno" ni "malo". La intensidad codifica la **magnitud de la
tasa anual** (|tasa_anual_pct|). Así el mismo AGEB conserva su tono al cambiar de horizonte, y el
color solo cambia si cambia el veredicto.

| token | valor | cuándo |
|---|---|---|
| `--sube-1` | `#C6DAEA` | sube, \|tasa\| < 2 %/año |
| `--sube-2` | `#7EA7CB` | sube, 2 – 3.5 |
| `--sube-3` | `#2F6A9E` | sube, ≥ 3.5 (tope) |
| `--baja-1` | `#F1D3B3` | baja, \|tasa\| < 2 %/año |
| `--baja-2` | `#DD9A5E` | baja, 2 – 3.5 |
| `--baja-3` | `#A95616` | baja, ≥ 3.5 (tope) |
| `--mantiene` | `#E3DDD0` | se_mantiene (neutro cálido, un solo tono) |
| `--sin-datos` | `#F2F2EF` con patrón `#hachurado` | sin_datos |
| `--sube-texto` | `#245A88` | símbolo o palabra "Sube" como texto (6.9:1) |
| `--baja-texto` | `#8F4712` | símbolo o palabra "Baja" como texto (6.5:1) |
| `--mantiene-texto` | `#5E5646` | símbolo o palabra "Se mantiene" (7.0:1) |

Reglas de uso:
- **Símbolos.** Nunca se muestra solo el color: ▲ Sube · ▼ Baja · ■ Se mantiene · ∅ Sin datos.
  En la leyenda y en la tabla van en la misma línea que la palabra.
- **Hachurado de `sin_datos`.** Líneas a 45°, 1 px de `#8C8C88`, cada 6 px, sobre `--sin-datos`.
- **Confianza baja** (canal no cromático): superposición de **punteado**. Son puntos de 1.2 px en
  `rgba(17,17,17,.45)` cada 5 px, en retícula ortogonal. Se eligió así porque:
  - conserva el tono del veredicto;
  - puntos contra líneas diagonales no se confunden con el hachurado;
  - no usa opacidad, que queda reservada a la atenuación de foco (y viceversa, §4.3).

  Las confianzas alta y media no tienen marca en el mapa. La tabla y la ficha las distinguen con ● ◐ ○.
- **Contraste de los rellenos.** Los rellenos claros (`-1`) no alcanzan 3:1 contra el papel. Lo
  compensan el contorno `--linea-fuerte` entre polígonos (3.5:1) y la tabla, que es la alternativa
  equivalente (WCAG 1.4.11 se cumple con el contorno y el texto).

### 4.3 Estado recesivo (atenuación por foco)

Canal elegido: **luminosidad y saturación, no opacidad** (el punteado de confianza no la usa).

| token | valor | uso |
|---|---|---|
| `--recesivo-relleno` | `#EEEEEB` | relleno de las alcaldías vecinas en vista de alcaldía |
| `--recesivo-contorno` | `#858581` | contorno de las vecinas (3.5:1: se ven como silueta) |
| `--recesivo-texto` | `#6E6E6B` | etiquetas de las vecinas (4.9:1) |
| `--recesivo-filtro` | `saturate(0) brightness(1.08)` | leyenda de vista general mientras transiciona |

### 4.4 Capa brecha (solo si el backend la entrega)

La brecha no tiene veredicto. Se pinta con una escala secuencial **en tinta**, para no gastar el
color, que está reservado a los veredictos. Son 5 cuantiles: `#EDEDEA` `#C9C9C5` `#9E9E99` `#6B6B67`
`#3A3A37`.

### 4.5 Tipografía

- Familia: **Inter 4.x variable** (licencia OFL), con ejes `wght` 300–700 y `opsz`.
- Archivos: `frontend/vendor/fonts/InterVariable.woff2` e `InterVariable-Italic.woff2`, en subconjunto
  latín + latín extendido (~110 kB).
- Carga: `font-display: swap`, más `preload` del archivo normal.
- Se activan las features `"tnum" 1, "cv11" 1` (cifras tabulares, a de un piso desactivada) en cifras.
- Respaldo: `"Inter", "Helvetica Neue", Arial, system-ui, sans-serif`.

| token | tamaño / interlínea | peso | tracking | uso |
|---|---|---|---|---|
| `--t-titular` | clamp(26px, 2.1vw, 32px) / 1.12 | 420 | −0.012em | titular dinámico |
| `--t-ficha-cifra` | 44px / 1.0 | 380 | −0.02em | cifra principal de la ficha AGEB |
| `--t-h2` | 20px / 1.2 | 500 | −0.005em | nombre de alcaldía o AGEB en la columna |
| `--t-cuerpo` | 14px / 20px | 400 | 0 | celdas, detalle, drawer |
| `--t-subtitulo` | 13px / 18px | 450 | 0 | línea de capa + horizonte bajo el titular |
| `--t-nota` | 12px / 16px | 400 | 0 | notas, fuentes, tooltip secundario |
| `--t-etiqueta` | 11px / 14px | 550 | 0.08em, MAYÚSCULAS | encabezados de tabla, enlaces pequeños, franja lateral |

- Titular: `text-indent: 2.2em`, `hyphens: auto`, `lang="es-MX"` en `<html>`,
  `text-wrap: pretty`, `hanging-punctuation: first`.
- Modo presentación (§10.9): todos los tamaños × 1.25 con `--escala: 1.25`.

### 4.6 Espaciado y retícula

- Escala: `--e-1: 4px` · `--e-2: 8px` · `--e-3: 12px` · `--e-4: 16px` · `--e-5: 24px` · `--e-6: 32px`
  · `--e-7: 48px` · `--e-8: 64px`.
- Columna izquierda con padding de 32 px a los lados y 24 px arriba.
- Divisor vertical de 1 px `--linea`. Franja lateral derecha de 40 px.
- Filas de tabla: 36 px (vista general) y 34 px (lista de AGEB). Encabezado de tabla: 32 px.
- Sin `border-radius`, salvo 2 px en el control segmentado y el pulgar del slider.
- Sin sombras. Única excepción: el tooltip lleva un contorno de 1 px `--tinta` y ninguna sombra.

### 4.7 Movimiento

| token | valor |
|---|---|
| `--d-intencion` | 100ms (retardo de hover con intención) |
| `--d-repliegue` | 180ms (retardo antes de plegar) |
| `--d-xs` | 120ms |
| `--d-s` | 200ms |
| `--d-m` | 300ms |
| `--d-l` | 700ms (vuelo del mapa) |
| `--ease-salida` | cubic-bezier(0.22, 1, 0.36, 1) |
| `--ease-entrada-salida` | cubic-bezier(0.65, 0, 0.35, 1) |
| `--ease-pop` | cubic-bezier(0.34, 1.45, 0.64, 1) (rebote leve) |
| `--ease-lineal` | linear (solo crossfades) |

Con `prefers-reduced-motion: reduce`, todos los `--d-*` pasan a 0 ms, salvo los crossfades, que se
quedan en 120 ms. La tabla de §12 da el sustituto de cada animación.

## 5. Layout de escritorio

### 5.1 Reparto

| ancho de ventana | columna izquierda | mapa | franja |
|---|---|---|---|
| ≥ 1280 px | clamp(480px, 34vw, 560px) | resto (≥ 62 %) | 40 px |
| 1024 – 1279 px | 480 px fijos | resto (≥ 49 %, excepción aceptada) | 40 px |
| < 1024 px | layout móvil y tableta (§11) | | |

**El reparto es el mismo en las tres vistas** (general, alcaldía y AGEB). Cambiar el ancho en la
transición obligaría a proyectar de nuevo y produciría un salto de geometría. El "acercamiento" es
el zoom del mapa, no una reflow de la página.

El mapa gana en vista de alcaldía porque la alcaldía ocupa el 88 % del alto útil. La columna
izquierda no crece: su contenido cambia (§6, §7).

### 5.2 Cabecera

Mide 48 px de alto, con una línea inferior de 1 px `--linea`. De izquierda a derecha:
1. nombre del producto (`--t-etiqueta`, `--tinta`);
2. migas: "CDMX / Coyoacán / AGEB 0900300010123" (`--t-etiqueta`, `--tinta-2`, cada nivel es enlace);
3. al centro-derecha, el control segmentado de capa;
4. a la derecha, "Metodología ↗" y el botón de modo presentación "⤢".

### 5.3 Wireframe 1: vista general (1440 × 900)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┬──┐
│ INFANCIAS CDMX   CDMX                         [ DEMANDA | Oferta ]   METODOLOGÍA ↗   ⤢       │  │
├──────────────────────────────────────────┬───────────────────────────────────────────────────┤ M│
│      A 5 años, la población de 0 a 14    │                                                   │ E│
│ años —la demanda de servicios para in-   │                 ░░▓▓▓                             │ T│
│ fancias— bajaría en 14 de las 16 alcal-  │              ░░▓▓▓▓▓▓▓░                           │ O│
│ días; en ninguna subiría.                │           ▒▒▓▓▓▓▓▓▓▓▓▓▓▓░                         │ D│
│ DEMANDA · MEDIADOS DE 2031 · CDMX −9.8 % │           ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                        │ O│
│ VER METODOLOGÍA ↗                        │            ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒                        │ L│
│                                          │             ▓▓▓▓▓▓▓▓▓▓▓▓▓░                         │ O│
│ ALCALDÍA        VEREDICTO   CAMBIO A 2031  CONF.│        ▓▓▓▓▓▓▓▒▒▒▒░                       │ G│
│ ─────────────────────────────────────────│               ▓▓▓▒▒▒▒▒░                           │ Í│
│ Benito Juárez   ▼ Baja      −21.4 % ▐██  ● │             ▒▒▒▒▒▒▒▒                              │ A│
│ Coyoacán        ▼ Baja      −17.9 % ▐█▌  ● │              ▒▒▒▒▒                                │  │
│ Cuauhtémoc      ▼ Baja      −15.2 % ▐█▌  ◐ │ ┌LEYENDA · DEMANDA · 2031──┐                      │ Y│
│ …                                         │ │▲ Sube 0 ■ Se mantiene 2  │  3 ──── ● ──── 7 años│  │
│ Milpa Alta      ■ Se mant.   −3.1 %  ▌   ○ │ │▼ Baja 14 ∅ Sin datos 0   │  2029   2031   2033  │ L│
│ (16 filas, 36 px; sin scroll a 1080 px)   │ │⁘ Confianza baja          │  El intervalo se      │ Í│
│                                          │ └──────────────────────────┘  amplía con el plazo. │ M│
├──────────────────────────────────────────┴───────────────────────────────────────────────────┤ ↓│
│ Fuentes: INEGI, Censos 2010 y 2020 · CONAPO · DENUE                          Datos: 18 sep 2026 │  │
└──────────────────────────────────────────────────────────────────────────────────────────────┴──┘
```

- **Pie.** 28 px, `--t-nota`, `--tinta-3`. Muestra el `generado` del JSON con formato "18 sep 2026".
- **Leyenda.** Abajo a la izquierda del mapa, a 24 px del borde.
- **Control de horizonte.** Centrado en la base del mapa, a 24 px del borde, 320 px de ancho.

## 6. Titular dinámico

### 6.1 Composición

```html
<header class="titular" aria-live="off">
  <p class="titular__frase">…</p>
  <p class="titular__sub">…</p>
  <a>Ver metodología ↗</a>
</header>
```

- **Altura reservada.** `min-height` = 4 líneas de `--t-titular` en 480 px. Así los cambios no
  desplazan la tabla.
- **Cambio de texto.** Crossfade de 200 ms: la frase saliente va a opacidad 0 en 100 ms y la entrante
  sube de 0 a 1 en 100 ms, las dos lineales. No se anima el alto.
- **Cifras.** Siempre en `tnum`. La frase termina en punto. Máximo 3–4 líneas en 480 px: cada
  plantilla está probada con el nombre de alcaldía más largo ("Gustavo A. Madero").
- **Anuncios a lectores de pantalla.** El titular **no** es `aria-live`; los cambios los anuncia la
  región viva global (§13).

### 6.2 Regla del "veredicto general" (vista general)

- Sea V el número de alcaldías con veredicto distinto de `sin_datos`, y `n_sube`, `n_mant`, `n_baja`
  sus conteos.
- `h` es el horizonte en años y `año` su año calendario.
- Se evalúa en orden; gana la primera condición que se cumple.

| # | escenario | condición | justificación |
|---|---|---|---|
| 1 | datos insuficientes | V < 8 | con menos de la mitad no se puede generalizar |
| 2 | predominio de baja | n_baja ≥ 0.60·V **y** n_sube ≤ 0.15·V | mayoría clara sin contrapeso relevante |
| 3 | predominio de sube | n_sube ≥ 0.60·V **y** n_baja ≤ 0.15·V | simétrico al anterior |
| 4 | polarizado | n_sube ≥ 0.25·V **y** n_baja ≥ 0.25·V | dos bloques opuestos de tamaño comparable |
| 5 | mayoría se mantiene | n_mant ≥ 0.50·V | estabilidad mayoritaria |
| 6 | mixto | ninguna de las anteriores | sin patrón dominante |

- **Matiz por confianza.** Si ≥ 50 % de las V alcaldías tienen confianza `baja`, se añade el
  sufijo de confianza (§6.4).
- **Matiz por horizonte.** Si `h = 7`, la frase empieza con "De mantenerse las tendencias, a 7 años…".
- **Agregado CDMX.** Si `agregado_cdmx` existe, su cambio aparece en el subtítulo, nunca en la frase
  principal: la frase habla de alcaldías y el subtítulo de la ciudad.

### 6.3 Plantillas, vista general

`{h}`, `{año}` y los `{n_*}` son variables. Los números menores que 10 van en palabra ("dos"),
salvo que acompañen a "de las 16".

**Capa DEMANDA.**

| escenario | frase |
|---|---|
| baja | A {h} años, la población de 0 a 14 años —la demanda de servicios para infancias— bajaría en {n_baja} de las 16 alcaldías{; en ninguna subiría \| y subiría en {n_sube}}. |
| sube | A {h} años, la población de 0 a 14 años —la demanda de servicios para infancias— subiría en {n_sube} de las 16 alcaldías{; en ninguna bajaría \| y bajaría en {n_baja}}. |
| polarizado | A {h} años, la demanda de servicios para infancias iría en direcciones opuestas: subiría en {n_sube} alcaldías y bajaría en {n_baja}. |
| mantiene | A {h} años, la demanda de servicios para infancias se mantendría estable en {n_mant} de las 16 alcaldías. |
| mixto | A {h} años, la demanda de servicios para infancias no muestra una dirección común: {n_baja} alcaldías bajarían, {n_mant} se mantendrían y {n_sube} subirían. |
| insuficiente | Aún no hay datos suficientes para pronosticar la demanda de servicios para infancias en la mayoría de las alcaldías. |

**Capa OFERTA.** La palabra es siempre "establecimientos"; nunca "demanda".

| escenario | frase |
|---|---|
| baja | A {h} años, el número de establecimientos para infancias tendería a bajar en {n_baja} de las 16 alcaldías. |
| sube | A {h} años, el número de establecimientos para infancias tendería a subir en {n_sube} de las 16 alcaldías. |
| polarizado | A {h} años, los establecimientos para infancias tenderían a subir en {n_sube} alcaldías y a bajar en {n_baja}. |
| mantiene | A {h} años, el número de establecimientos para infancias se mantendría en {n_mant} de las 16 alcaldías. |
| mixto | A {h} años, los establecimientos para infancias no muestran una tendencia común entre alcaldías. |
| insuficiente | No hay registros suficientes de establecimientos para pronosticar la oferta en la mayoría de las alcaldías. |

**Capa BRECHA** (si existe). No hay veredicto; es una sola plantilla:
"Hay {min} a {max} establecimientos para infancias por cada 1,000 niñas y niños, según la alcaldía;
la cifra más baja está en {alcaldía_min}."

### 6.4 Subtítulo y sufijos

- **Subtítulo.** En mayúsculas diminutas (`--t-etiqueta`). Lleva siempre la capa y el horizonte:
  - `DEMANDA · MEDIADOS DE {año} · CDMX {±x.x %} (ENTRE {lo} Y {hi} %)`
  - sin agregado CDMX: `DEMANDA · MEDIADOS DE {año}`
  - capa oferta: `OFERTA (ESTABLECIMIENTOS DENUE) · MEDIADOS DE {año}`
- **Sufijo por confianza baja dominante.** Reemplaza el punto final: "…, aunque con certeza limitada
  en la mayoría de los casos."
- **Oferta.** Debajo del subtítulo, siempre, en `--t-nota`: "Confianza máxima: media. El
  levantamiento de 2024 registró de una vez cierres ocurridos entre 2020 y 2023."

### 6.5 Plantillas, vista de alcaldía

Se aplican sobre sus AGEB con dato (`V_a`). `{alc}` es el nombre oficial. La primera condición que
se cumple gana, con los mismos umbrales de §6.2.

| escenario | frase (DEMANDA) |
|---|---|
| baja | En {alc}, la población de 0 a 14 años bajaría a {h} años en {n_baja} de sus {V_a} AGEB ({p_baja} %). |
| sube | En {alc}, la población de 0 a 14 años subiría a {h} años en {n_sube} de sus {V_a} AGEB ({p_sube} %). |
| polarizado | En {alc}, la demanda iría en direcciones opuestas: {n_sube} AGEB subirían y {n_baja} bajarían a {h} años. |
| mantiene | En {alc}, la demanda se mantendría estable a {h} años en {n_mant} de sus {V_a} AGEB. |
| mixto | En {alc}, a {h} años, {n_baja} AGEB bajarían, {n_mant} se mantendrían y {n_sube} subirían. |
| insuficiente | En {alc} no hay datos suficientes para pronosticar la mayoría de sus AGEB. |

- **Oferta.** Mismas estructuras, cambiando "la población de 0 a 14 años" o "la demanda" por "el
  número de establecimientos para infancias" y los verbos por "tendería a subir / bajar".
- **AGEB sin datos.** Si `n_sin > 0`, se agrega una segunda oración: "{n_sin} AGEB no tienen datos
  suficientes."
- **Subtítulo.** `DEMANDA · MEDIADOS DE {año} · {ALC} {±x.x %} (ENTRE {lo} Y {hi} %)`.
- **Vista AGEB.** El titular no cambia: se mantiene el de la alcaldía.
- **Invariante.** Toda cifra del titular se calcula con la misma función que llena la tabla
  (`resumirVeredictos(registros)`), así que no pueden divergir. Hay una prueba para ello (§16).

## 7. Tabla de predicciones

### 7.1 Vista general (16 filas)

- Es un `<table>` real. Cada `<tr>` lleva `tabindex="0"`, `aria-expanded` y `aria-controls` hacia su
  fila de detalle. El `<caption>` es visualmente oculto: "Pronóstico por alcaldía, capa demanda, a
  mediados de 2031".
- Encabezados en `--t-etiqueta` y `--tinta-2`. Las columnas ordenables son `<button>` dentro del
  `<th>`, con `aria-sort`.

| columna | ancho (en 480 px) | contenido | alineación |
|---|---|---|---|
| ALCALDÍA | flexible (≥ 150) | nombre oficial | izquierda |
| VEREDICTO | 112 | símbolo coloreado + palabra ("▼ Baja") | izquierda |
| CAMBIO A {AÑO} | 118 | "−17.9 %" + mini-barra divergente de 28 px (escala ±25 %, con tope y marca ▸ si lo excede) | derecha |
| CONF. | 44 | ● alta · ◐ media · ○ baja; `aria-label` "confianza alta" | centro |

- **Orden.** Por defecto, por cambio ascendente (lo que más baja, arriba). También por nombre (A–Z) y
  por confianza (alta → baja, con desempate por cambio). El orden se refleja en el hash con `&orden=`.
- **Filas.** 36 px, regla inferior de 1 px `--linea`. Sin cebreado.
- **Fila activa** (hover, foco o fila del hover del mapa): fondo `#F0F0EC` y regla superior de 1 px
  `--tinta`.
- **Cifras.** Formato es-MX: signo menos tipográfico U+2212, "+" explícito, punto decimal, espacio
  fino antes de "%", 1 decimal.

### 7.2 Fila desplegada (acordeón)

Tiene una **altura fija de 136 px** para todas las alcaldías. Wireframe 5:

```
│ Coyoacán        ▼ Baja      −17.9 % ▐█▌  ● │
│┌───────────────────────────────────────────┐│
││ Cambio esperado a mediados de 2031: −17.9 %││
││ Rango probable (95 %): entre −24.0 % y −11.6 %│
││ ● Confianza alta: el resultado se sostiene aun con supuestos distintos.│
││ Basado en 2 censos (2010 y 2020).          ││
││ AGEB  ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼■■∅   141 bajan · 12 se mantienen · 0 suben · 3 sin datos │
││                                  EXPLORAR ALCALDÍA →                          ││
│└───────────────────────────────────────────┘│
```

**Contenido.**
- La barra apilada mide 100 % × 8 px, sin huecos, en el orden sube · se mantiene · baja · sin datos.
  El texto va al lado.
- Explicaciones de confianza (una línea):
  - **alta**: "el resultado se sostiene aun con supuestos distintos."
  - **media**: "el sentido del cambio es probable, pero su tamaño es incierto."
  - **baja**: "los datos no permiten afirmar el sentido del cambio con seguridad."
- `n_obs`, capa demanda: "Basado en {n} censos (2010 y 2020)."
- `n_obs`, capa oferta: "Basado en {n} levantamientos del DENUE (2016, 2019 y 2024)."
- Si falta `distribucion_ageb` y el GeoJSON de AGEB aún no llega, la barra se muestra en esqueleto.

**Disparo.**
- **Con ratón.** Hover sostenido `--d-intencion` (100 ms), en la fila o en el polígono del mapa. El
  vínculo es bidireccional: la fila realza el polígono y el polígono despliega la fila.
- **Con teclado.** El foco en la fila despliega de inmediato.
- **Pliegue.** Al salir de la fila y de su detalle se espera `--d-repliegue` (180 ms). Si en ese
  lapso el puntero entra en otra fila, se hace el cambio directo.
- **Una sola fila** desplegada a la vez.
- **Hover desde el mapa con la fila fuera de vista.** El contenedor hace `scrollIntoView({block:
  'nearest'})` con desplazamiento suave de 200 ms (instantáneo con movimiento reducido).

**Cómo se evitan los saltos de layout** (decisión):
1. **La altura del detalle es fija (136 px) y el detalle es parte del área de hover de la fila.**
   Al pasar de A a B, si B está debajo de A, B sube exactamente 136 px. El puntero queda entonces
   **dentro del detalle de B**, que pertenece a B. No se dispara otra fila ni hay oscilación.
2. **Ese desplazamiento no es un salto: se anima con FLIP.** Se mide, se aplica el layout y el
   `tbody` se traslada del delta a 0 en 200 ms con `--ease-salida`. Con movimiento reducido, el
   cambio es directo.
3. **Nada fuera de la tabla cambia de alto.** El contenedor tiene alto fijo y scroll propio. El
   titular tiene altura reservada.

### 7.3 Vista de alcaldía (sustituye a la tabla general)

Wireframe 3:

```
┌──────────────────────────────────────────┬──────────────────────────────────────────────────┐
│ ← TODAS LAS ALCALDÍAS                    │      (silueta vecinas, gris recesivo)            │
│      En Coyoacán, la población de 0 a 14 │         ┌──────────────────────┐                 │
│ años bajaría a 5 años en 141 de sus 153  │         │▓▓▒▒▓▓▓░░▓▓▓▓▒▒▓▓▓▓▓▓ │                 │
│ AGEB (92 %). 3 AGEB no tienen datos su-  │         │▓▓▓▓▒▓▓▓▓▓▓▓⁘⁘▓▓▓▓▒▒▓▓│  AGEB coloreados│
│ ficientes.                               │         │▓▓▓▓▓▓▓■■▓▓▓▓▓▓▓▓▓▓▓▓ │                 │
│ DEMANDA · MEDIADOS DE 2031 · COYOACÁN    │         │▓▓▓▓▓▓▓▓▓▓▓▓▓▓///▓▓▓▓ │  /// = sin datos│
│ −17.9 % (ENTRE −24.0 Y −11.6 %)          │         └──────────────────────┘                 │
│                                          │                                                  │
│ COYOACÁN     ▼ Baja  −17.9 %   ● alta    │                                     [Reencuadrar]│
│ ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼■■∅ 141 · 12 · 0 · 3     │  ┌LEYENDA · COYOACÁN · 2031─┐                    │
│ BUSCAR AGEB POR CLAVE [0900300_______]   │  │▲ 0 ■ 12 ▼ 141 ∅ 3 ⁘ 27   │   3 ──── ● ──── 7   │
│ AGEB           VEREDICTO  CAMBIO   CONF. │  └──────────────────────────┘                    │
│ ──────────────────────────────────────── │                                                  │
│ 0900300010123  ▼ Baja     −31.2 %   ◐   │                                                  │
│ … (12 AGEB con mayor cambio absoluto)    │                                                  │
│ VER LOS 156 AGEB ↓                       │                                                  │
└──────────────────────────────────────────┴──────────────────────────────────────────────────┘
```

**Bloque resumen.** Cuatro líneas, sin acordeón. Es el mismo contenido que la fila desplegada de la
alcaldía, compactado.

**Lista de AGEB.**
- Columnas: AGEB (clave completa de 13 caracteres, `tnum`) · VEREDICTO · CAMBIO A {AÑO} · CONF.
- Filas de 34 px.
- **Orden por defecto: |cambio| descendente**, es decir, los AGEB con mayor cambio en cualquier
  sentido. También se puede ordenar por clave y por confianza.
- Primero se muestran 12. El botón "Ver los {N} AGEB ↓" expande la lista completa dentro del mismo
  contenedor con scroll. No se virtualiza: ≤ ~300 filas es aceptable.
- Los `sin_datos` van al final, con "∅ Sin datos" y el motivo en el `title` y en el tooltip.

**Buscador (incluido).**
- Es un `<input type="search">` con etiqueta visible "BUSCAR AGEB POR CLAVE", precargado con el
  prefijo de la alcaldía (`09` + `CVE_MUN`).
- Filtra por subcadena mientras se escribe, con 120 ms de *debounce*.
- Sin resultados: "Ninguna clave coincide con «{texto}»."
- Con Enter y un resultado único, abre la ficha.

**Hover en fila o polígono.** Solo realza. Las filas de AGEB no tienen acordeón; el detalle es la
ficha.

### 7.4 Ficha de AGEB (sustituye a la lista)

Wireframe 4:

```
┌──────────────────────────────────────────┐
│ ← VOLVER A COYOACÁN                      │
│ (titular de la alcaldía, sin cambios)    │
│ AGEB 0900300010123                       │  --t-h2
│ COYOACÁN · URBANA                        │  --t-etiqueta
│ ▼ Baja                     −31.2 %       │  cifra --t-ficha-cifra
│ a mediados de 2031, frente a mediados de 2026            │
│ ──────────────────────────────────────── │
│ TASA ANUAL          −5.1 % por año       │
│ RANGO PROBABLE 95 % entre −40.3 % y −20.8 %│
│ CONFIANZA           ◐ Media — el sentido del cambio es probable, pero su tamaño es incierto.│
│ OBSERVACIONES       2 censos (2010 y 2020)│
│ ──────────────────────────────────────── │
│ NIÑAS Y NIÑOS DE 0 A 14 AÑOS             │
│ 900┤ ●                                    │
│    │    ╲                                 │
│ 600┤      ╲●·········◇━━━━◆······◇        │  ● censos  ◆ horizonte activo
│    │        ░░░░░░░░░░░░░░░░░░░░░░        │  banda = rango 95 %
│ 300┤                                      │
│    └──┬──────┬──────┬──┬───┬───┬───┬──    │
│     2010   2015   2020 2026 2029 2031 2033│
│ Proyección basada en los censos 2010 y 2020 y en las proyecciones de CONAPO.│
└──────────────────────────────────────────┘
```

**Mini-gráfica.** SVG de 416 × 168 px, con eje de tiempo real (años decimales). La hace
`graficas.js`.
- **Puntos censales.** 2010.44 y 2020.20, círculos llenos de 4 px `--tinta`. En oferta son 3
  levantamientos: 2016.79, 2019.87 y 2024.87.
- **Tramos.** Sólido entre las observaciones; punteado desde la última observación hasta la fecha
  base.
- **Proyección.** Línea de 1.5 px en el color del veredicto (`-3`).
- **Horizontes.** Rombos ◇ en los tres; el activo es ◆ de 7 px con etiqueta "2031: 612".
- **Banda.** Polígono del rango 95 % por horizonte, interpolado linealmente entre la fecha base y
  los tres horizontes. Relleno del color `-1` del veredicto al 60 %; es un área decorativa y no
  compite con el punteado de confianza porque la ficha no lo usa.
- **Regla vertical** "hoy" en la fecha base, en `--linea-fuerte`, con la etiqueta "MEDIADOS DE 2026".
- **Ejes.** Eje Y con 3 marcas redondeadas y formato es-MX. Sin cuadrícula; solo la línea base.
- **Alternativa textual.** `<figure>` con `<figcaption>` visualmente oculta: "En 2010 había 912
  niñas y niños de 0 a 14 años; en 2020, 701. La proyección a mediados de 2031 es 612 (rango
  probable entre 545 y 690)."
- **Degradación.** Sin `serie` en los datos, la gráfica se sustituye por la nota "La serie histórica
  de este AGEB no está disponible en este conjunto de datos."

**AGEB `sin_datos`.**
- Muestra "∅ Sin datos" y el motivo en lenguaje claro (§14.4), sin cifras.
- La gráfica muestra solo los puntos censales si existen.

### 7.5 Adaptación por capa

- Todos los encabezados que dependen de la capa nombran la capa:
  - `CAMBIO EN DEMANDA A 2031` / `CAMBIO EN ESTABLECIMIENTOS A 2029`;
  - `NIÑAS Y NIÑOS DE 0 A 14 AÑOS` / `ESTABLECIMIENTOS DENUE (ALCANCE PRINCIPAL)`.
- En la vista general, el `caption` y el subtítulo también nombran la capa.

## 8. Control de horizonte

### 8.1 Ubicación y forma

- Va anclado en la base del área del mapa, centrado, y es visible en las tres vistas.
- Se eligió ese sitio porque actúa sobre lo que se está mirando, que son los colores del mapa.

Wireframe 6 (las tres posiciones):

```
HORIZONTE                                   HORIZONTE                                   HORIZONTE
 ●━━━━━━━━━○━━━━━━━━━○                       ○━━━━━━━━━●━━━━━━━━━○                       ○━━━━━━━━━○━━━━━━━━━●
3 años     5 años     7 años                3 años     5 años     7 años                3 años     5 años     7 años
2029       2031       2033                  2029       2031       2033                  2029       2031       2033
Proyección a corto plazo.                   El rango probable se amplía con el plazo.   A 7 años es una extrapolación de tendencias: úsela como orientación.
```

- **Pista.** 280 px de ancho, 2 px de `--tinta`, con marcas de 8 px en 3, 5 y 7.
- **Pulgar.** Círculo de 16 px `--tinta`. El área táctil es de 44 × 44 px.
- **Etiquetas.** Siempre visibles, en dos líneas: "3 años" (`--t-nota` y `--tinta`) y "2029"
  (`--tinta-3`). La etiqueta activa va en peso 600.
- **Nota.** Debajo, en `--t-nota` `--tinta-2`. Tiene altura reservada de 1 línea y crossfade de
  120 ms.

### 8.2 Implementación

- `<input type="range" id="horizonte" min="3" max="7" step="2" value="5" list="marcas-horizonte">`,
  más un `<datalist>` y un `<label>` visible "HORIZONTE".
- Teclado nativo: flechas, Inicio/Fin y RePág/AvPág.
- `aria-valuetext`: "5 años, a mediados de 2031". Se actualiza con cada `input`.
- Táctil: se puede arrastrar o tocar una etiqueta. Las etiquetas son `<button>` que fijan el valor.

### 8.3 Comportamiento

- **Fuente de verdad.** Los tres horizontes ya vienen en el archivo, así que mover el slider no
  dispara peticiones.
- **Qué cambia:**
  - clases de color de alcaldías y AGEB, con transición de `fill` en 300 ms `--ease-salida`, sin
    recrear paths;
  - punteado de confianza, con opacidad de superposición 0 ↔ 1 en 300 ms;
  - titular (crossfade de 200 ms);
  - tabla (valores y reordenamiento con FLIP de 200 ms);
  - fila desplegada o ficha;
  - leyenda y sus conteos;
  - encabezados "CAMBIO A {AÑO}";
  - hash `&h=`.
- **Durante el arrastre** se actualiza en cada `input`, con un `requestAnimationFrame` como máximo por
  cuadro. El anuncio a la región viva se hace en `change`, no en `input`.

### 8.4 Comunicar la incertidumbre creciente (sin alarmismo)

1. **Nota bajo el slider** (§8.1), que cambia con el horizonte.
2. **Titular.** A 7 años empieza con "De mantenerse las tendencias, …" (§6.2).
3. **Ficha.** La banda se ensancha de forma visible. La línea de confianza puede bajar de nivel;
   cuando eso ocurre por el plazo, se añade: "La confianza es menor a 7 años que a 3."

### 8.5 Capa oferta y capa brecha

- **Recomendación: el slider no aplica a oferta ni a brecha.**
  - Los levantamientos del DENUE no son observaciones independientes. Proyectar oferta a 7 años con
    3 levantamientos no es defendible.
  - Oferta se muestra en un solo horizonte: 3 años, es decir, 2029.
  - [DECISIÓN DEL EQUIPO §18-2]
- **Estado deshabilitado del slider** con oferta o brecha:
  - el control lleva `disabled` y opacidad de etiquetas `--tinta-3`;
  - el pulgar se fija en el horizonte de la capa;
  - texto en lugar de la nota: "La oferta se pronostica solo a 3 años (2029): los levantamientos del
    DENUE no permiten proyectar más lejos."
  - Al volver a demanda, se restaura el último horizonte de demanda.

### 8.6 Degradación con un solo horizonte (contrato v1.1)

- El slider aparece deshabilitado, con el pulgar en la posición más cercana o, si no coincide, sin
  pulgar, y las marcas en `--tinta-3`.
- Nota: "Este conjunto de datos trae un solo horizonte: mediados de {año del campo `horizonte`}."
- Las etiquetas "CAMBIO A {AÑO}" usan ese año. El hash ignora `h`. Todo lo demás funciona igual.

## 9. Capas y semántica

- **Control segmentado** en la cabecera: `[ Demanda | Oferta | Brecha ]`.
  - Es un `role="radiogroup"` con `<input type="radio">` estilizados; las flechas cambian la opción.
  - Brecha **solo aparece** si el archivo trae `capas.brecha`.
  - Demanda es la opción por defecto.
  - Al cambiar de capa: transición de color de 300 ms, sin recrear geometría, y se actualiza el hash
    con `&capa=`.
- **Nombre de la capa visible** en seis lugares: control, subtítulo del titular, encabezado de la
  leyenda, encabezados de tabla, tooltip ("Demanda: ▼ Baja") y ficha.
- **Oferta.**
  - Advertencia fija bajo el subtítulo (§6.4).
  - En la fila desplegada y en la ficha se añade "Confianza máxima de esta capa: media."
- **Brecha.**
  - Leyenda secuencial en tinta con 5 cortes y su unidad: "establecimientos por cada 1,000 niñas y
    niños de 0 a 14 años".
  - No hay veredicto ni slider.
  - La tabla cambia sus columnas a ALCALDÍA · ESTABLECIMIENTOS POR 1,000 · NIÑAS Y NIÑOS · ESTABLECIMIENTOS.
- **`sin_datos`.** Siempre visible, con el hachurado. El tooltip da el motivo (§14.4). Cuenta en la
  leyenda y en el titular.

## 10. Componentes

### 10.1 Mapa: vista general

- 16 polígonos de alcaldía, con relleno por veredicto y contorno de 1 px `--papel` entre vecinas.
- **Contorno exterior de la CDMX:** 1 px `--linea-fuerte`.
- **Etiquetas.** No se dibujan en el mapa en la vista general; el nombre está en la tabla y en el
  tooltip. En vista de alcaldía, las vecinas llevan su nombre en `--t-etiqueta` `--recesivo-texto`
  sobre su centroide, si cabe en su área visible.
- **Hover** (alcaldía o fila):
  - contorno de 2 px `--tinta` en `g.realce`;
  - "elevación leve": copia del contorno desplazada 2 px hacia abajo, en `--tinta` al 15 %, sin
    desenfoque, y la forma se traslada −1 px en Y;
  - la transición dura 120 ms `--ease-salida`.
- **Tooltip.** Mínimo, a 12 px del puntero; se voltea si toca un borde.
  - Contenido: dos líneas, "Coyoacán" (`--t-cuerpo` 500) y "Demanda: ▼ Baja" (`--t-nota`).
  - Aparece con fade de 100 ms. No se muestra con teclado: el foco en la fila ya da la información.
- **Modo sin puntero.** El primer toque se comporta como hover, el segundo como clic (§10.8).

### 10.2 Transición de foco (clic, Enter o segundo toque)

Es un solo gesto de 820 ms. Wireframe 2 (fotograma a ~400 ms):

```
┌──────────────────────────────────────────┬───────────────────────────────────────────────┐
│ (titular: frase general ya en 0 %, frase │   ░░░░ (vecinas pasando a gris recesivo)      │
│  de alcaldía entrando)                   │      ░░░┌──────────────────┐░░░               │
│                                          │      ░░░│ ▓▓▓ Coyoacán ▓▓▓ │░░  ← vuelo en  │
│ (tabla general a 0 %; resumen de         │      ░░░│ ▓▓▓ (escala 1.8×) │░░    curso     │
│  Coyoacán deslizándose +8 px → 0)        │      ░░░└──────────────────┘░░░               │
│                                          │   leyenda: crossfade de conteos                │
└──────────────────────────────────────────┴───────────────────────────────────────────────┘
```

| t (ms) | paso | detalle | easing |
|---|---|---|---|
| 0 – 180 | 1. pop | el `<g>` de la alcaldía escala 1 → 1.035 → 1 alrededor de su centroide (`transform-box: fill-box`) y sube al frente | `--ease-pop` |
| 120 – 820 | 2. vuelo | `d3.zoom().transform` con `interpolateZoom` hasta encuadrar la alcaldía (bbox + 48 px de margen; alto útil ≥ 88 %) | `--ease-entrada-salida` |
| 120 – 420 | 3. recesión | relleno de las vecinas → `--recesivo-relleno`, contorno → `--recesivo-contorno`; la leyenda cambia de conteos | `--ease-salida` |
| 0 – 200 | 5a. salida | la frase del titular va a 0 (100 ms); el contenido de la tabla general va a 0 (120 ms) | lineal |
| 200 – 480 | 5b. entrada | nueva frase (100 ms); el resumen y las filas de AGEB entran con opacidad 0 → 1 y `translateY(8px → 0)` en 200 ms, con escalonado de 12 ms por fila (máx. 10 filas) | `--ease-salida` |
| 520 – 820 | 4. AGEB | los AGEB de la alcaldía entran con `fill-opacity` 0 → 1; el relleno propio de la alcaldía se vuelve transparente y queda solo su contorno de 1.5 px `--tinta` | `--ease-salida` |

**Si el GeoJSON de AGEB aún no llegó:**
- el vuelo y la recesión no esperan;
- la alcaldía conserva su color agregado y muestra un pulso de carga (§15.6);
- cuando llegan los datos, los AGEB entran con fade de 300 ms.

**Prefetch.** La petición del GeoJSON de AGEB se lanza:
- en el primer hover con intención (100 ms) sobre cualquier alcaldía o fila;
- en su defecto, en `requestIdleCallback` 2 s después del primer render.

**Accesibilidad de la atenuación.**
- **Qué se atenúa:** los rellenos de las vecinas. Es decorativo en esta vista: su veredicto se
  consulta volviendo a la general.
- **Qué no se atenúa:** texto, controles, leyenda, slider ni la columna izquierda. Esta se
  **transforma**, no se atenúa.
- **Contrastes que se conservan:**
  - contorno de las vecinas contra el papel: 3.5:1;
  - etiquetas de las vecinas: 4.9:1;
  - contorno de la alcaldía en foco: 18:1.
- **Interactividad de las vecinas.**
  - Con ratón y toque se pueden pulsar: el tooltip dice "Ir a Tlalpan" y el clic ejecuta la
    transición de foco directamente de alcaldía a alcaldía (vuelo de 700 ms, sin volver a la general).
  - Van con `aria-hidden="true"` y fuera del orden de tabulación. **No se usa `inert`**, porque
    bloquearía el clic.
  - El camino por teclado es "← Todas las alcaldías" o Esc.
- **Contenido de la vista general.** Se retira del DOM, no se oculta.

### 10.3 Mapa: vista de alcaldía

- **AGEB de la alcaldía.** Filtro `cve_mun`, relleno por veredicto y magnitud, contornos de 0.5 px
  `--papel`, punteado si la confianza es baja y hachurado si es `sin_datos`.
- **Hover sobre un AGEB.**
  - contorno de 2 px `--tinta`, sin elevación: son pequeños y el desplazamiento confundiría;
  - tooltip "AGEB 0900300010123 · Demanda: ▼ Baja";
  - realce de su fila si está visible.
- **Clic en un AGEB.** Abre la ficha y lo marca con un contorno de 2.5 px `--tinta` permanente. No
  hay vuelo: el AGEB ya es visible.
- **"Reencuadrar".** Botón de texto `--t-etiqueta`, abajo a la derecha del mapa. Solo aparece si el
  usuario hizo zoom o paneo manual.

### 10.4 Leyenda

- **Posición.** Abajo a la izquierda del área del mapa. Fondo `--papel` al 92 % y contorno de 1 px
  `--linea`. Mide 248 px de ancho.
- **Encabezado.** `--t-etiqueta`: "LEYENDA · DEMANDA · 2031" en la general; "LEYENDA · COYOACÁN ·
  2031" en la de alcaldía.
- **Filas.** Muestra de 14 × 10 px con el color o patrón, el símbolo, la palabra y el conteo
  (`tnum`). Los conteos se refieren a lo que se ve: alcaldías en la general, AGEB en la de alcaldía.
- **Intensidad.** Una fila extra con tres muestras por lado: "Más intensidad = cambio anual mayor".
- **Confianza baja.** Muestra de punteado + "Confianza baja ({n})".
- **Filtro y realce (incluido).**
  - Cada fila es un `<button aria-pressed>`.
  - Al pulsarla, las unidades de otras categorías pasan a `--recesivo-relleno`. Se aplica el mismo
    canal que en la recesión y no se toca el punteado.
  - Solo puede haber una categoría activa. Se desactiva al pulsarla de nuevo o con Esc, que tiene
    prioridad sobre retroceder un nivel.
  - La tabla filtra en paralelo sus filas y muestra "Mostrando 14 de 16 · Quitar filtro".
- **Capa brecha.** Rampa de 5 cortes con límites numéricos.

### 10.5 Franja lateral y drawer "Metodología y limitaciones"

- **Franja.** 40 px de ancho, a todo lo alto, con un divisor de 1 px. El texto "METODOLOGÍA Y
  LIMITACIONES ↓" va rotado −90° (`writing-mode: vertical-rl; transform: rotate(180deg)`) en
  `--t-etiqueta`. Toda la franja es un `<button aria-haspopup="dialog">`.
- **Drawer.** Es un `<dialog>` modal que entra desde la derecha, de 560 px de ancho (100 % en móvil).
  - Entra con `translateX(100%) → 0` en 300 ms `--ease-salida` y sale en 200 ms.
  - El fondo lleva una capa `--papel` al 70 %.
  - El foco inicial va al título; Esc cierra; al cerrar, el foco vuelve al disparador.
  - Tiene scroll propio.
- También se abre desde "Metodología ↗" en la cabecera y "Ver metodología ↗" en el titular.
- Hash `#/…?…&info=1`, que se puede enlazar.

Wireframe 7:

```
                                   ┌──────────────────────────────────────────────┐
                                   │ METODOLOGÍA Y LIMITACIONES             CERRAR ✕│
                                   │ ──────────────────────────────────────────── │
                                   │ Qué mide esta herramienta                     │
                                   │ Demanda y oferta                              │
                                   │ De dónde vienen los datos                     │
                                   │ Cómo se decide si algo sube, baja o se mantiene│
                                   │ Por qué a 7 años hay más incertidumbre        │
                                   │ AGEB rurales y sin datos                      │
                                   │ El levantamiento del DENUE de 2024            │
                                   │ Advertencias                                  │
                                   │ (texto corrido §14.6, 14 px / 20 px, 60 ch)   │
                                   └──────────────────────────────────────────────┘
```

### 10.6 Cabecera y migas

- Las migas son un `<nav aria-label="Ruta">` con `<ol>`. El nivel actual lleva `aria-current="page"`.
- Hacer clic en "CDMX" o en la alcaldía retrocede a ese nivel, con la misma transición inversa (§12).

### 10.7 Transición inversa (volver)

- **AGEB → alcaldía.** La ficha hace crossfade con la lista en 200 ms y se quita la marca del AGEB.
  El mapa no se mueve.
- **Alcaldía → general.**
  - vuelo inverso de 700 ms;
  - los AGEB salen con fade en 200 ms (0–200);
  - la alcaldía recupera su relleno y las vecinas su color (300 ms, 150–450);
  - la columna izquierda hace crossfade (0–480, igual que §10.2 paso 5).
  - Al final, el foco vuelve a la fila de la alcaldía, desplegada.

### 10.8 Táctil y teclado

- **Táctil (`pointer: coarse`).**
  - Primer toque en polígono o fila: despliega la fila y realza el polígono. En la fila aparece el
    botón "EXPLORAR ALCALDÍA →".
  - Segundo toque en la misma unidad, o el botón: foco (§10.2).
  - Tocar fuera: pliega.
- **Teclado.**
  - Tab recorre en este orden: cabecera → titular (enlace) → encabezados ordenables → filas →
    control de horizonte → leyenda → franja.
  - Foco en una fila = hover. Enter o Espacio = clic.
  - Esc retrocede **un** nivel: primero cierra el drawer o el filtro de leyenda; luego va de AGEB a
    alcaldía y de alcaldía a la general.

### 10.9 Modo presentación (incluido)

- **Cómo se activa.** Botón "⤢" en la cabecera, tecla `P` o `?presentacion=1`.
- **Qué cambia:**
  - `--escala: 1.25` en todos los tokens tipográficos;
  - `--tinta-3` pasa a `--tinta-2`, para más contraste en proyector;
  - contornos de mapa de +0.5 px;
  - la leyenda muestra la intensidad.
- **Qué se oculta:** buscador, controles de orden, pie y franja lateral. La metodología sigue
  disponible con `M`.
- **Qué se mantiene:** capa, slider y migas, porque son la narración.
- **Pantalla completa.** Opcional con `requestFullscreen` al activarlo, si el navegador lo permite.

## 11. Móvil y tableta (< 1024 px)

Wireframe 8:

```
┌──────────────────────────────┐
│ INFANCIAS CDMX  [Dem.|Ofe.] ⓘ│ 48 px
├──────────────────────────────┤
│                              │
│        MAPA (100 % ancho)    │
│                              │
│  ┌leyenda compacta, 1 línea┐ │  ▲0 ■2 ▼14 ∅0  (toca para expandir)
│  3 ───●─── 7   5 años · 2031 │  slider, siempre sobre la hoja
├══════════ ▬▬▬ ═══════════════┤  asa de la hoja (botón)
│ A 5 años, la población de 0 a│  altura BAJA: 128 px (titular recortado a 2 líneas + asa)
│ 14 años… bajaría en 14 de 16 │
│ ─────────────────────────────│  altura MEDIA: 50 % del viewport (titular + tabla con scroll)
│ ALCALDÍA   VERED.  CAMBIO  C │
│ Benito J.  ▼ Baja  −21.4 % ● │  altura ALTA: 88 % (tabla/ficha completa; el mapa queda como banda de 12 %)
└──────────────────────────────┘
```

**Hoja inferior.**
- Tres alturas: **baja** (128 px), **media** (50 dvh) y **alta** (88 dvh).
- Se mueve arrastrando el asa (con *snap*) o tocando el asa, que es un `<button>` con
  `aria-label="Ajustar panel: altura media"` y cicla baja → media → alta.
- El arrastre no es obligatorio.
- La transición entre alturas dura 300 ms `--ease-salida`.

**Controles.**
- El **slider y la capa siguen accesibles en las tres alturas**:
  - la capa vive en la cabecera;
  - el slider flota sobre el borde superior de la hoja en las alturas baja y media;
  - en la alta, el slider se mueve a la primera fila de la hoja.
- El slider mide 240 px de ancho, con pulgar de 44 px táctiles.

**Comportamiento del mapa.**
- Al enfocar una alcaldía, la hoja pasa a la altura media y el vuelo encuadra la alcaldía en el
  área visible **por encima de la hoja**, usando ese padding inferior.
- En la ficha de AGEB, la hoja pasa a la altura alta.
- En móvil no hay tooltip de mapa: el primer toque despliega la fila en la hoja.

**Tableta** (768–1023 px): mismo esquema, con la hoja limitada a 560 px de ancho y alineada a la
izquierda. El mapa ocupa todo el fondo.

## 12. Mapa de interacciones

| disparador | efecto | duración | easing | con movimiento reducido |
|---|---|---|---|---|
| Hover alcaldía o fila (≥ 100 ms) | realce del polígono + despliegue de la fila + prefetch AGEB | 120 ms realce; 200 ms despliegue | `--ease-salida` | realce y despliegue instantáneos |
| Salida de fila o polígono | pliegue tras 180 ms | 200 ms | `--ease-salida` | instantáneo |
| Cambio de fila desplegada | FLIP del `tbody` | 200 ms | `--ease-salida` | instantáneo |
| Clic / Enter / segundo toque en alcaldía | pop + vuelo + recesión + AGEB + columna (§10.2) | 820 ms total | ver §10.2 | corte directo al encuadre final; columna y AGEB con crossfade de 120 ms; sin pop |
| Clic en vecina (vista alcaldía) | cambio de foco directo | 700 ms vuelo + 300 ms AGEB | `--ease-entrada-salida` | corte + crossfade de 120 ms |
| Hover AGEB | contorno + tooltip + realce de fila | 100 ms | `--ease-salida` | instantáneo |
| Clic / Enter en AGEB | ficha sustituye a la lista; marca en el mapa | 200 ms crossfade | lineal | crossfade de 120 ms |
| Esc / "← Volver" / atrás del navegador | retrocede un nivel (§10.7) | 200 ms (AGEB); 820 ms (alcaldía) | espejo del avance | corte + crossfade de 120 ms |
| Slider de horizonte | recolor de `fill`, punteado, titular, tabla, leyenda | 300 ms color; 200 ms titular; 200 ms FLIP tabla | `--ease-salida` / lineal | color instantáneo; titular con crossfade de 120 ms |
| Cambio de capa | recolor, textos, leyenda, slider (des)habilitado | 300 ms | `--ease-salida` | instantáneo |
| Orden de tabla | reordenamiento FLIP | 200 ms | `--ease-salida` | instantáneo |
| Filtro de leyenda | recesión de otras categorías; filtro de tabla | 200 ms | `--ease-salida` | instantáneo |
| Abrir / cerrar metodología | drawer desde la derecha | 300 ms / 200 ms | `--ease-salida` | crossfade de 120 ms |
| Hoja móvil (asa) | cambio de altura | 300 ms | `--ease-salida` | instantáneo |
| Rueda o pellizco (vista alcaldía) | zoom libre acotado | continuo | nativo d3-zoom | igual (es control directo) |
| "Reencuadrar" | vuelo al encuadre | 500 ms | `--ease-entrada-salida` | corte directo |
| Llegada tardía de AGEB | fade de entrada | 300 ms | `--ease-salida` | instantáneo |
| Datos cargados (primer render) | esqueleto → contenido | 200 ms crossfade | lineal | crossfade de 120 ms |

## 13. Accesibilidad

- **Contraste.** Todo el texto es ≥ 4.5:1 (el mínimo es `--tinta-3`, 4.9:1). Contornos y controles
  son ≥ 3:1. El foco es visible siempre: `outline: 2px solid var(--foco); outline-offset: 2px`, nunca
  eliminado.
- **Estructura:**
  - `<header>`, `<nav>` (migas), `<main>` con dos regiones: `<section aria-labelledby>` para la
    columna y `<section role="region" aria-label="Mapa de la CDMX">` para el mapa;
  - `<aside>` para la leyenda y `<footer>`;
  - un `<h1>` visualmente oculto con el nombre del producto;
  - `<h2>` para el nombre de la vista.
- **Mapa.**
  - El SVG lleva `role="img"` con `aria-labelledby` hacia un resumen oculto, que se genera con las
    plantillas: "Mapa de la CDMX por alcaldía, capa demanda, a mediados de 2031: 14 bajan, 2 se
    mantienen, 0 suben. La tabla contiene el detalle."
  - Los polígonos no son tabulables. **La tabla es la alternativa completa** y todo lo que se hace
    con el mapa se hace desde ella.
- **Región viva.** Un `<div aria-live="polite" class="visualmente-oculto">` global anuncia:
  - "Vista de Coyoacán: 153 AGEB con datos."
  - "Vista general de la CDMX."
  - "Horizonte: 7 años, a mediados de 2033."
  - "Capa: oferta, establecimientos DENUE."
  - "AGEB 0900300010123: baja, −31.2 %."
  - "Filtro: solo Baja."
- **Gestión del foco:**
  - al entrar en una alcaldía, al `<h2>` de la columna (`tabindex="-1"`);
  - al entrar en un AGEB, al `<h2>` de la ficha;
  - al volver a la alcaldía, a la fila del AGEB, o al `<h2>` si la fila no está en el top N visible;
  - al volver a la general, a la fila de la alcaldía;
  - al cerrar el drawer, al disparador.
- **Movimiento reducido.** La tabla de §12 define el sustituto de cada animación. También se respeta
  `prefers-reduced-transparency`: la leyenda pasa a fondo opaco.
- **Idioma.** `lang="es-MX"`. Las claves CVEGEO se leen dígito a dígito en el `aria-label`.
- **Objetivos táctiles.** ≥ 44 × 44 px en `pointer: coarse`. El área de la fila es toda la fila.

## 14. Textos de la UI

### 14.1 Etiquetas fijas

| id | texto |
|---|---|
| producto | Infancias CDMX |
| capa.demanda / oferta / brecha | Demanda · Oferta · Brecha |
| horizonte.label | Horizonte |
| horizonte.opcion | {h} años · {año} |
| volver.general | ← Todas las alcaldías |
| volver.alcaldia | ← Volver a {alcaldía} |
| explorar | Explorar alcaldía → |
| metodologia.enlace | Ver metodología ↗ |
| metodologia.franja | Metodología y limitaciones ↓ |
| ver.todos | Ver los {n} AGEB ↓ |
| buscar | Buscar AGEB por clave |
| reencuadrar | Reencuadrar |
| veredicto.* | Sube · Se mantiene · Baja · Sin datos |
| confianza.* | Alta · Media · Baja |

### 14.2 Tooltips

- Alcaldía: "{nombre}" / "{Capa}: {símbolo} {Veredicto}".
- Vecina en vista de alcaldía: "Ir a {nombre}".
- AGEB: "AGEB {cvegeo}" / "{Capa}: {símbolo} {Veredicto}".
- AGEB sin datos: "AGEB {cvegeo}" / "Sin datos: {motivo}".

### 14.3 Fila desplegada y ficha

Ver §7.2 y §7.4. Frases fijas:
- "Cambio esperado a mediados de {año}: {±x.x %}"
- "Rango probable (95 %): entre {lo} y {hi}"
- "a mediados de {año}, frente a mediados de {año_base}"
- "{±x.x %} por año"

### 14.4 Motivos de `sin_datos`

Llegan del backend en `motivo_sin_datos` (§17).

| código | texto |
|---|---|
| rural | AGEB rural: el censo no publica datos de población infantil por AGEB rural. |
| suprimido_inegi | El INEGI no publica esta cifra para proteger la confidencialidad. |
| poblacion_menor_20 | Hay menos de 20 niñas y niños: la cifra es demasiado pequeña para pronosticar. |
| sin_poligono / sin_censo | Esta clave no tiene correspondencia entre el mapa y el censo. |
| sin_establecimientos | No hay establecimientos registrados en ningún levantamiento. |
| (ausente) | No hay estimación para esta unidad. |

### 14.5 Estados

Ver §15.

### 14.6 Metodología y limitaciones (texto del drawer)

**Qué mide esta herramienta.** Pronostica si la población de 0 a 14 años de cada alcaldía y de cada
AGEB urbana de la Ciudad de México subirá, se mantendrá o bajará a 3, 5 y 7 años. Esa población es
la demanda potencial de servicios para infancias: guarderías, preescolares, primarias, secundarias y
servicios de apoyo.

**Demanda y oferta.** La *demanda* es el número de niñas y niños de 0 a 14 años que viven en cada
zona. La *oferta* es el número de establecimientos dedicados principalmente a la infancia,
registrados en el Directorio Estadístico Nacional de Unidades Económicas (DENUE) del INEGI. Son
cosas distintas y se muestran en capas separadas. Que una baje no implica que la otra deba bajar.

**Por qué de 0 a 14 años.** Todos los establecimientos dedicados principalmente a la infancia
atienden edades dentro de ese rango. Las edades se suman sin ponderaciones.

**De dónde vienen los datos.**
- Censos de Población y Vivienda 2010 y 2020 del INEGI, por AGEB urbana.
- Proyecciones de población por municipio del Consejo Nacional de Población (CONAPO).
- DENUE (INEGI), levantamientos de 2016, 2019 y 2024.
- Marco Geoestadístico 2020 del INEGI.

**Cómo se calcula.** Para cada AGEB se mide cómo cambió su población infantil entre 2010 y 2020. En
las AGEB pequeñas, ese cambio se acerca al de su alcaldía, porque con pocas personas una variación
puede deberse al azar. La tendencia de cada alcaldía se ajusta a las proyecciones de CONAPO. Con
miles de simulaciones se obtiene un rango probable para cada resultado.

**Cómo se decide si algo sube, baja o se mantiene.**
- Un cambio menor a 1 % por año, en cualquier sentido, cuenta como "se mantiene".
- Se dice que algo **sube** o **baja** solo cuando la probabilidad de que el cambio supere ese
  umbral en ese sentido es de al menos 80 %.
- La confianza es **alta** si esa probabilidad es de 95 % o más y el resultado no depende de los
  supuestos. Es **media** si está entre 80 % y 95 %. Es **baja** en los demás casos, y también
  cuando hay muy pocas niñas y niños o un solo dato.

**Por qué a 7 años hay más incertidumbre.** Solo hay dos censos con datos por AGEB. Todo pronóstico
supone que las tendencias de 2010–2020 y las proyecciones de CONAPO siguen vigentes. Cuanto más
lejano el horizonte, más amplio el rango probable. A 7 años, el resultado es una orientación, no una
predicción precisa.

**AGEB rurales y sin datos.** El censo no publica la población infantil por AGEB rural (22 en la
ciudad, en Milpa Alta, Tlalpan y Xochimilco, entre otras), así que se muestran como "Sin datos".
Tampoco se pronostican las AGEB donde el INEGI reserva la cifra o donde viven menos de 20 niñas y
niños. Nunca se inventa un valor.

**El levantamiento del DENUE de 2024.** Entre 2020 y 2023, el DENUE casi no se actualizó en campo.
Cuando el INEGI volvió a recorrer la ciudad en 2024, registró de una sola vez los cierres acumulados
en esos años, sobre todo de preescolares y guarderías privadas. Por eso la oferta se mide entre
levantamientos y su confianza máxima es media.

**Advertencias.**
- Estos pronósticos describen tendencias de población, no necesidades de servicio ni calidad de la
  atención.
- Una alcaldía puede tener AGEB que suben aunque en conjunto baje.
- Las cifras de CONAPO y del censo no coinciden exactamente. Por eso se usa la *tasa* de cambio de
  CONAPO y no su nivel.
- Datos generados el {generado}.

## 15. Estados

Wireframe 9 (columna izquierda en cada estado):

```
CARGA INICIAL               ERROR                              VACÍO (alcaldía)
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒        No pudimos cargar los datos.       En {alcaldía} no hay AGEB con datos
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒             Revise su conexión e intente de    suficientes para pronosticar la
▒▒▒▒▒▒▒▒▒▒                  nuevo. (Detalle: {causa})          {capa}. Motivos: 22 rurales · 3 …
────────────────────        [ REINTENTAR ]                     ← TODAS LAS ALCALDÍAS
▒▒▒▒▒▒▒▒   ▒▒▒▒  ▒▒▒  ▒
▒▒▒▒▒▒▒▒   ▒▒▒▒  ▒▒▒  ▒     (mapa: solo contornos en
(16 barras de 36 px)         --linea-fuerte, sin relleno)
```

| # | estado | diseño | texto |
|---|---|---|---|
| 1 | Carga inicial | Esqueleto: 3 barras de titular + 16 filas `--esqueleto`; mapa con contornos de alcaldía si ya llegó `alcaldias.geojson`, si no un rectángulo `--esqueleto`; `aria-busy="true"`; brillo animado de 1.2 s lineal (sin brillo con movimiento reducido) | Anuncio: "Cargando pronósticos…" |
| 2 | Error de carga | Bloque en la columna; mapa solo con contornos; botón Reintentar que repite solo las peticiones fallidas | "No pudimos cargar los datos. Revise su conexión e intente de nuevo." + causa: "sin conexión" · "el archivo no es válido" · "versión de datos incompatible ({v})" |
| 3 | Capa o alcaldía sin datos | Mapa con hachurado en todas las unidades; tabla sustituida por el mensaje; leyenda con conteos | "En {alcaldía} no hay AGEB con datos suficientes para pronosticar la {capa}." + motivos agregados |
| 4 | AGEB sin datos | Ficha con "∅ Sin datos" y motivo (§14.4); sin cifras; gráfica solo con puntos si existen | ver §14.4 |
| 5 | Datos incompletos | Unidades ausentes del JSON = `sin_datos` "(ausente)"; aviso discreto en el pie una vez por sesión | "Faltan estimaciones para {n} unidades; se muestran como sin datos." |
| 6 | AGEB cargándose tras el clic | La alcaldía conserva su color con un pulso de opacidad de superposición 0.0 → 0.15 → 0.0 cada 1.2 s; la lista de AGEB en esqueleto | "Cargando AGEB de {alcaldía}…" |
| 7 | Horizonte no disponible | §8.5 y §8.6 | textos de §8.5 y §8.6 |

- **Caché.** En memoria: el GeoJSON de AGEB se descarga una sola vez y se indexa en
  `Map<cve_mun, paths[]>`. Los paths proyectados se generan por alcaldía la primera vez y se
  reutilizan.
- **Sin parpadeos.** Cambiar de capa u horizonte solo cambia clases y transiciona `fill`. Nunca se
  vacía un `<g>` para volver a llenarlo.

## 16. Rendimiento y criterios de aceptación

### 16.1 Presupuesto

| recurso | tamaño (gzip) | carga |
|---|---|---|
| HTML + CSS + JS propios | ≤ 45 kB | inmediata |
| d3-chipos.esm.js | ≤ 40 kB | inmediata |
| Inter (1 woff2, latín) | ≤ 110 kB | `preload` |
| alcaldias.geojson | ≤ 60 kB | inmediata |
| prediccion_alcaldia.json | ≤ 15 kB | inmediata |
| prediccion_ageb.json (3 horizontes + series) | ≤ 250 kB | diferida (con el primer hover o en reposo) |
| ageb_cdmx_simplificado.geojson | ~420 kB (1.51 MB sin comprimir) | diferida |

- **Tiempos.** Primer render útil (titular + tabla + mapa coloreado) < 2 s en "Fast 4G" de DevTools
  con caché fría. Interacción (hover → realce) < 50 ms. Transiciones a 60 fps en un portátil de gama
  media, con ≤ 16 ms por cuadro durante el vuelo.
- **TopoJSON.** No se adopta: el GeoJSON simplificado cumple el presupuesto. Se revisaría solo si la
  medición de carga diferida supera 1.5 s en Fast 4G.

### 16.2 Checklist de aceptación

- [ ] Sin peticiones a dominios externos (pestaña Red) y sin errores ni avisos en consola.
- [ ] Lighthouse: accesibilidad ≥ 95 y rendimiento ≥ 90 en escritorio.
- [ ] Las 16 filas caben sin scroll a 1920 × 1080; a 1440 × 900, la tabla tiene scroll propio y la
      página no.
- [ ] Hover con intención de 100 ms; pliegue a 180 ms; una sola fila desplegada; sin oscilación al
      barrer las 16 filas con el ratón de arriba abajo y de abajo arriba.
- [ ] La transición de foco dura 820 ± 50 ms en total, sin salto al final del vuelo (grabación a 60 fps).
- [ ] Con `prefers-reduced-motion`, ninguna animación supera 120 ms y no hay vuelo ni pop.
- [ ] Esc retrocede exactamente un nivel. El botón "atrás" del navegador reproduce la misma
      secuencia. Recargar con cualquier hash restaura vista, capa, horizonte, orden y drawer.
- [ ] El slider funciona con flechas, Inicio/Fin y toque. `aria-valuetext` es correcto. No hay
      peticiones de red al moverlo. El titular y la tabla muestran las mismas cifras (prueba
      automática en `tests/`).
- [ ] Con un archivo v1.1 (un horizonte), el slider está deshabilitado con su nota y todo lo demás
      funciona.
- [ ] La capa se nombra en los seis lugares de §9. Con oferta, la advertencia es visible y el
      subtítulo dice "Oferta".
- [ ] `sin_datos` se distingue sin color (hachurado + ∅ + palabra). La confianza baja se distingue
      sin color (punteado + ○). Ninguno se confunde con la atenuación.
- [ ] Con simulación de deuteranopía, protanopía y tritanopía (DevTools), los tres veredictos siguen
      siendo distinguibles.
- [ ] Todos los flujos de §10 se completan solo con teclado. El foco se gestiona según §13.
- [ ] Móvil de 360 × 740: la hoja tiene 3 alturas, el slider y la capa se alcanzan en cada una, y
      los objetivos táctiles miden ≥ 44 px.
- [ ] Ningún `innerHTML` con datos (`grep -n innerHTML frontend/js` vacío o solo con cadenas
      literales). Sin `!important`. Sin estilos en línea.
- [ ] Los 7 estados de §15 se reproducen con los mocks (`?mock=error`, `?mock=v11`, `?mock=vacio`,
      `?mock=lento`).
- [ ] Todos los textos de la UI coinciden con §14. Nunca aparece "delegación".

## 17. Peticiones al backend

Son peticiones: hoy no son hechos. Están alineadas con la pregunta abierta B2 de `plans/backend_plan.md`.

**P1 · Varios horizontes en un solo archivo (contrato v1.2).**
- Horizontes de 3, 5 y 7 años desde la fecha base.
- `delta_pct` e `ic95` se miden **desde la fecha base**, no desde el censo 2020, para que "cambio a
  2031" signifique lo que dice (§18-1).
- `tasa_anual_pct` es la tasa anual proyectada en el último año antes del horizonte.

**P2 · Agregado de toda la CDMX** en `prediccion_alcaldia.json`, bajo `agregado_cdmx`, para el
subtítulo del titular.

**P3 · Serie para la mini-gráfica.** Por AGEB y por alcaldía, los niveles observados (`serie`) y el
nivel en la fecha base. Así, el cliente calcula los niveles de cada horizonte como
`nivel_base·(1+delta/100)` y la banda con `ic95`.

**P4 · Motivo de `sin_datos`** (`motivo_sin_datos`, códigos de §14.4) y la **distribución de AGEB
por veredicto** en cada alcaldía y horizonte (`distribucion_ageb`). Así la fila desplegada no espera
al archivo de AGEB.

**P5 · Brecha** (opcional), como capa sin veredicto.

Esquema mínimo v1.2. Es compatible hacia atrás en espíritu: los campos por horizonte son los de la
v1.1.

```json
{"version":"1.2","generado":"2026-09-18T12:00:00-06:00","fecha_base":"2026-06",
 "horizontes":[{"clave":"h3","anios":3,"fecha":"2029-06"},
               {"clave":"h5","anios":5,"fecha":"2031-06"},
               {"clave":"h7","anios":7,"fecha":"2033-06"}],
 "capas":{
  "demanda":{"<CVEGEO>":{"cve_mun":"003","n_obs":2,"motivo_sin_datos":null,
     "serie":{"t":[2010.44,2020.20],"valor":[912,701]},"nivel_base":655,
     "h":{"h3":{"veredicto":"baja","delta_pct":-6.1,"tasa_anual_pct":-2.1,"ic95":[-9.8,-2.4],"confianza":"alta"},
          "h5":{…},"h7":{…}}}},
  "oferta":{"<CVEGEO>":{"cve_mun":"003","n_obs":3,"motivo_sin_datos":null,
     "serie":{"t":[2016.79,2019.87,2024.87],"valor":[6,6,4]},"nivel_base":4,
     "horizontes_disponibles":["h3"],
     "h":{"h3":{"veredicto":"se_mantiene","delta_pct":-3.0,"tasa_anual_pct":-1.0,"ic95":[-20.0,15.0],"confianza":"baja"}}}},
  "brecha":{"<CVEGEO>":{"cve_mun":"003","valor":6.1,"unidad":"establecimientos por 1,000 de 0 a 14 años",
     "t_oferta":2024.87,"t_demanda":2020.20}}}}
```

`prediccion_alcaldia.json` usa el mismo esquema por `CVE_MUN`, más:

```json
"distribucion_ageb":{"h3":{"sube":0,"se_mantiene":12,"baja":141,"sin_datos":3},"h5":{…},"h7":{…}}
```

en cada alcaldía de demanda y oferta, más:

```json
"agregado_cdmx":{"demanda":{…mismo registro con "h"…},"oferta":{…}}
```

en la raíz.

Reglas para el cliente:
- Un registro `sin_datos` lleva `h.hX.veredicto = "sin_datos"`, `confianza` y `n_obs`, con cifras
  en `null`.
- **Adaptador en `api.js`.** La v1.1 se convierte a v1.2 con un solo horizonte (clave `hU`,
  `anios = null`, fecha = `horizonte`), sin `serie`, `distribucion_ageb` ni `agregado_cdmx`. Con eso
  se activan las degradaciones de §7.4, §8.6 y §7.2.

## 18. Decisiones abiertas

1. **[RESUELTO] Fecha base y referencia del cambio.** `fecha_base = 2026-06` (2026.5), horizontes
   en `2029-06`/`2031-06`/`2033-06` (3/5/7 años), `delta_pct`/`ic95` medidos desde `fecha_base`
   (no desde el censo 2020). `docs/metodologia.md` y `CLAUDE.md` ya reflejan esto; contrato
   `version 1.2` implementado en `backend/src/chipos/exportar.py`.
2. **[RESUELTO] Horizonte de la oferta.** Solo 3 años (`h3`, `horizontes_disponibles: ["h3"]`),
   confianza tope `media` como antes. El slider queda deshabilitado cuando la capa activa es
   oferta (o brecha, que no tiene horizonte).
3. **[DECISIÓN DEL EQUIPO] Capa brecha.** ¿Se publica como tercera capa, secuencial y sin veredicto,
   con la unidad "establecimientos por 1,000 niñas y niños"? ¿O queda solo en la metodología?
4. **[DECISIÓN DEL EQUIPO] Umbrales del veredicto general** (§6.2: 60 % / 15 % / 25 % / 50 %,
   V ≥ 8). Con los datos esperados (casi todo "baja"), el escenario dominante será "predominio de
   baja". Hay que confirmar que los umbrales sirven al relato.
5. **[DECISIÓN DEL EQUIPO] Nombre del producto y créditos institucionales**: logotipos, instituciones
   participantes y licencia de datos en el pie. Si hay logotipos, van en el pie, en monocromo y a
   ≤ 20 px de alto, para no romper la sobriedad.
