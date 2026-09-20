# Especificación de diseño del frontend — Habitancia

Documento vinculante para `frontend/` (CLAUDE.md → "Frontend"). Implementa
`correccion/frontend_requisitos.md` (documento funcional autocontenido, NIVEL 1 y NIVEL 2 de
información) sobre el contrato de datos **v1.4** de `plans/backend_plan.md` /
`docs/metodologia.md`. Lo que requiere datos que el contrato no trae se pide en §17 ("Contrato de
datos y motor de composición cliente"), y la UI se degrada si no llegan (§15). Las decisiones que
no son de diseño van marcadas **[DECISIÓN DEL EQUIPO]** (§18).

> **Revisión 2026-09-20 — reescritura completa.** La versión anterior de este documento describía
> un visor de dos capas (demanda/oferta) con un titular de frase autogenerada. Esa versión queda
> **retirada**: `correccion/frontend_requisitos.md` redefine el producto como **Habitancia**, un
> explorador de **cuatro ramas** ponderables por el usuario (educación y cultura, salud, comercio,
> áreas verdes y espacio público), con filtros, dos tipos de búsqueda, comparación entre alcaldías
> y una arquitectura de información en dos niveles. Se conservan casi intactos: el stack (§3), los
> tokens de color/tipografía/espaciado/movimiento (§4), la mecánica del mapa D3 (§10.1–10.3, con la
> corrección de rendimiento de `correccion/action_plan.md` Fase 8 ya aplicada), el patrón de franja
> lateral + drawer (§10.6), la accesibilidad transversal (§13) y los estados de carga/error (§15).
> Se retira por completo: la generación de frases interpretativas dinámicas (antiguo §6) —
> `correccion/frontend_requisitos.md` lo prohíbe explícitamente ("No se deben generar narrativas
> automáticas en lenguaje natural para explicar el resultado") — y la capa `brecha` como capa
> separada del backend (la sustituye el índice de oportunidad calculado en el cliente, §17).

**Cambios que esta especificación obliga a hacer en `plans/frontend_plan.md`** (ver también
`correccion/action_plan.md` Fase 7):
1. El titular de frase autogenerada desaparece; lo sustituye el **resumen estructurado** de
   Nivel 1 (§6), sin texto interpretativo generado dinámicamente.
2. La tabla de predicciones por alcaldía se convierte en un **ranking por AGEB** (§7), con la
   alcaldía como nivel de navegación, no de cómputo (`correccion/frontend_requisitos.md` §11).
3. El control segmentado de capas se convierte en el selector de **vista del mapa** (§9): vista
   general (índice compuesto) + cuatro vistas de rama.
4. Se añaden cuatro componentes nuevos sin precedente en la versión anterior: **población
   objetivo** (§5.4), **prioridades/pesos** (§10.10), **filtros por rama** (§10.11) y **comparar
   alcaldías** (§10.13).
5. El backend deja de publicar `capas.oferta`/`capas.brecha`; publica `capas.demanda` (por
   segmento) y `capas.ramas.{educacion,salud,comercio,verde}` (por celda de filtro) — contrato v1.4
   (§17). El cálculo del índice de oportunidad y del índice compuesto se mueve **al cliente**
   (motor de composición, §17.4), porque depende de pesos y filtros que solo existen ahí.

---

## 1. Dirección estética

Estilo editorial suizo, como el de un portafolio de referencia (design.byform). Se toma su
estructura y su carácter, no su marca ni sus textos. Habitancia no adopta un estilo "de app": sigue
siendo un documento que se explora, no un dashboard con tarjetas.

- **Tipografía.** Una sola familia neo-grotesca, **Inter** (variable), para todo. Todas las cifras
  son tabulares.
- **Color.** La página es monocroma: blanco roto, tinta casi negra y un solo gris para las líneas.
  El color aparece **solo** para codificar significado: la escala de oportunidad/disponibilidad
  relativa en el mapa y el ranking (§4.2), y —en contextos puntuales de Nivel 2 (la gráfica de
  población objetivo, §10.5)— la escala de tendencia (sube/se mantiene/baja) heredada de la versión
  anterior de este documento, que sigue siendo válida ahí porque describe una cantidad distinta (una
  tendencia demográfica, no una prioridad relativa). Nunca se mezclan las dos escalas en el mismo
  elemento visual.
- **Ritmo.** Retícula de 8 px, líneas de 1 px, sin sombras, tarjetas ni iconos decorativos más allá
  del icono "?" (§10.14), que es funcional, no decorativo. Toda la información es texto, tabla,
  mapa o gráfica.
- **Dónde nos apartamos de la referencia:**
  1. El mapa ocupa ≥ 55 % del ancho en la vista general (baja un poco frente a la versión anterior:
     ahora comparte la columna izquierda con configuración, prioridades y filtros).
  2. Hay controles visibles y numerosos (población, horizonte, búsqueda, pesos, filtros, vista de
     mapa), porque Habitancia es una herramienta de exploración, no un portafolio de una sola
     lectura. Se organizan en un flujo progresivo (§2.3) para no saturar de golpe.
  3. El texto es compacto y las secciones son plegables por defecto salvo la primera vez, para que
     la pantalla inicial no abrume a una persona que nunca ha usado la herramienta.

## 2. Producto

### 2.1 Qué es Habitancia

**Habitancia** ("habitar" + "infancia") ayuda a una persona no técnica a explorar la Ciudad de
México y detectar zonas donde, de acuerdo con la evolución de la población infantil y la
disponibilidad de servicios, podría existir una mayor oportunidad relativa de ampliar o fortalecer
infraestructura para infancias. Pregunta que responde, textual
(`correccion/frontend_requisitos.md` §2):

> "¿En qué zonas de la Ciudad de México podría existir una mayor oportunidad de ampliar o
> fortalecer servicios para infancias durante los próximos años?"

Combina cuatro **ramas**: educación y cultura para infancias, áreas verdes y espacio público,
salud, comercio y acceso a productos de primera necesidad. El usuario decide cuáles considerar,
cuánto pesa cada una y qué filtros específicos aplicar dentro de cada una. **Los pesos y filtros no
cambian las predicciones originales**: cambian cómo Habitancia ordena y presenta los resultados
(`correccion/frontend_requisitos.md` §2, §21).

- Nombre del producto: **Habitancia**. Sin logotipos por ahora.
  [DECISIÓN DEL EQUIPO: créditos institucionales, §18-4.]
- Audiencias:
  - **Jurado y autoridades**, en proyección (hay modo presentación, §10.9).
  - **Personas no técnicas**, en uso autónomo — es la audiencia primaria de este documento; todo
    lenguaje técnico queda detrás de un icono "?" (§10.14).
  - **Analistas**, en uso autónomo avanzado (comparar, ordenar, filtrar con precisión).
- La UI está en español de México. La AGEB es la unidad geográfica base del mapeo y del cálculo;
  frente al usuario no técnico se presenta como **"zona"**, con un icono "?" que explica la
  equivalencia (`correccion/frontend_requisitos.md` §4, §11). La alcaldía es el nivel de
  orientación, búsqueda, navegación y agregación — **nunca la unidad mínima que se colorea**.
  Nunca "delegación", "hex", "backtest", "shrinkage" ni fórmulas frente al usuario.

### 2.2 Los dos niveles de información

`correccion/frontend_requisitos.md` §1 los define; son la columna vertebral de todo este documento.

**Nivel 1 — Respuesta rápida.** La información mínima para comprender el resultado sin
conocimientos técnicos: dónde está la zona, qué población se analiza, a qué horizonte, qué tipo de
servicio, qué tan alta es la oportunidad relativa, qué tan confiable es el resultado. Es un
**resumen estructurado** (§6), nunca una frase autogenerada. No satura con gráficas ni tablas.

**Nivel 2 — Entender el resultado.** Se abre solo si el usuario lo pide ("Entender esta zona", §10.6
renombrado). Explica cómo ha cambiado la zona, cómo podría cambiar, qué ocurre con la población
objetivo y con los servicios disponibles, cómo influyen las cuatro ramas, qué filtros y pesos están
activos, qué tan incierta es la estimación, y cómo se compara con otra alcaldía.

Ningún componente de ningún nivel genera texto interpretativo dinámico. La interpretación se
construye con etiquetas, valores, gráficas y ayudas "?" predefinidas (§10.14).

### 2.3 Flujo del usuario

`correccion/frontend_requisitos.md` §3, tal cual, es la secuencia de navegación de Habitancia:

1. Pantalla inicial: el usuario entiende qué hace Habitancia (§5.1).
2. Selecciona una alcaldía en el mapa o la busca por nombre (§5.2, §9).
3. Define la población objetivo (§5.3, §10.15).
4. Define el horizonte (§8).
5. Define el tipo de búsqueda: oportunidad de expansión o disponibilidad para familias (§5.5).
6. Define cuánto le importa cada una de las cuatro ramas — prioridades/pesos (§10.10).
7. Si quiere, abre "Filtros" para indicar qué tipos de servicios incluir por rama (§10.11).
8. El mapa y el ranking se actualizan, en el navegador, sin recargar (§17.4).
9. Selecciona una alcaldía o una zona (AGEB).
10. Consulta primero el resumen breve de Nivel 1 (§6).
11. Si quiere profundizar, abre "Entender esta zona" → Nivel 2 (§10.6).
12. Consulta gráficas y el detalle de las cuatro ramas (§10.5).
13. Puede comparar dos alcaldías (§10.13).

No se muestra toda la información de golpe: cada paso revela solo lo que corresponde a esa
pregunta (`correccion/frontend_requisitos.md` §23, §25 — reproducidas en §5 y §10 de este
documento).

## 3. Stack y decisión de mapa

**Decisión: SVG propio con d3**, sin cambios respecto a la versión anterior de esta especificación.
Los módulos son d3-geo, d3-zoom, d3-selection, d3-transition, d3-interpolate y d3-ease, más sus
dependencias (d3-array, d3-color, d3-dispatch, d3-drag, d3-timer). Van como un solo paquete ESM
vendorizado en `frontend/vendor/d3/d3-chipos.esm.js`, generado una vez fuera de línea con esbuild y
versionado. `vendor/d3/README.md` explica cómo regenerarlo. No hay paso de build en tiempo de
ejecución.

Por qué d3 y no Leaflet ni MapLibre: igual razonamiento que antes (control total del zoom vía
`transform`, trazos sin escalar, color por transición CSS, sin motor de teselas ni WebGL
innecesarios). No cambia con Habitancia.

**Novedad respecto a la versión anterior: un solo mapa de AGEB, varias "lecturas".** El selector de
vista (§9) no crea SVGs distintos por rama: reutiliza exactamente el mismo `<g>` de polígonos AGEB
(`g.agebs`) y solo cambia la **clase de color** de cada `<path>` según qué vista está activa. Esto
es una consecuencia directa de `correccion/frontend_requisitos.md` §11A ("conservar EL MISMO MAPA
DE AGEB y actualizar únicamente: el color de las zonas, la leyenda, el ranking...").

Detalles del mapa (sin cambios respecto a la versión anterior, salvo la corrección de rendimiento
de `correccion/action_plan.md` Fase 8, ya incorporada aquí):
- **Proyección.** `d3.geoMercator().fitExtent()` al área del mapa con 32 px de margen. Se recalcula
  al redimensionar, con 150 ms de *debounce*, sin animación.
- **Capas SVG**, de abajo arriba: `g.alcaldias-fondo` (siluetas de las vecinas) · `g.agebs`
  (polígonos AGEB de la alcaldía en foco, coloreados por la vista activa) · `g.confianza-baja`
  (punteado) · `g.alcaldias` (contornos y relleno en vista general, coloreados por el índice
  compuesto o la rama activa) · `g.realce` (contorno de hover o foco) · `defs` (patrones).
- **Transform de foco: un solo grupo envolvente, no cuatro.** Corrección de
  `correccion/action_plan.md` §8.2 punto 43: `aplicarTransform` anima un único `<g class="escenario">`
  que envuelve a los cuatro grupos anteriores, en vez de escribir el atributo `transform` cuatro
  veces por fotograma. **Nunca** se declara `transition: transform` en CSS sobre ese grupo ni sus
  hijos — la animación la hace únicamente D3 (`d3.transition`); esa regla CSS redundante era la
  causa raíz del cuelgue medido en `correccion/action_plan.md` §8.1 (12.3 s de hilo bloqueado, hoy
  412 ms tras el parche).
- **Zoom libre.** Desactivado en la vista general, encuadre fijo y editorial. En vista de alcaldía,
  rueda y pellizco con `scaleExtent [k_encuadre, 6·k_encuadre]`, con botón "Reencuadrar" (§10.3).
- **Seguridad.** Todo texto con datos vía `textContent` o creación de nodos, nunca `innerHTML`. CSP
  en `<meta>`: `default-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'`.

## 4. Tokens

Todos se definen en `css/tokens.css`, sobre `:root`. No se usan colores literales fuera de ese
archivo.

### 4.1 Color base (monocromo)

Sin cambios respecto a la versión anterior.

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

### 4.2 Escala de prioridad: oportunidad / disponibilidad relativa (color primario del mapa)

**Reemplaza a la paleta divergente de veredictos como color dominante del mapa y del ranking.** Es
una escala **secuencial de un solo matiz** (ocre cálido), porque `O_{i,h,r}`/`IC_{i,h}`
(`docs/metodologia.md` §10) no es una comparación "sube vs. baja": es un **percentil de prioridad**
entre 0 y 1, y el mismo tono se lee igual sea que la vista activa sea "oportunidad de expansión" o
"disponibilidad para familias" (solo cambia qué extremo aparece primero en el ranking, §5.5).

| token | valor | cuándo |
|---|---|---|
| `--prioridad-1` | `#F2E9DC` | percentil 0–20 (menor prioridad relativa) |
| `--prioridad-2` | `#E3CBA0` | percentil 20–40 |
| `--prioridad-3` | `#CBA363` | percentil 40–60 |
| `--prioridad-4` | `#A97A2E` | percentil 60–80 |
| `--prioridad-5` | `#7A5416` | percentil 80–100 (mayor prioridad relativa, tope) |
| `--sin-datos` | `#F2F2EF` con patrón `#hachurado` | `sin_datos` (rama o AGEB completa) |

Reglas de uso (`correccion/frontend_requisitos.md` §9, "leyenda con categorías comprensibles"):
- **Leyenda en tres categorías legibles, no cinco.** El mapa se pinta con los 5 tonos (más
  granularidad visual), pero la leyenda agrupa en **"Mayor oportunidad relativa" / "Oportunidad
  intermedia" / "Menor oportunidad relativa"** (copy exacto de requisitos §9) — o, en la vista de
  disponibilidad, "Mayor disponibilidad relativa" / "Disponibilidad intermedia" / "Menor
  disponibilidad relativa". Nunca se muestra solo el color: cada categoría lleva su etiqueta de
  texto en la leyenda y en el tooltip.
- **Hachurado de `sin_datos`.** Líneas a 45°, 1 px de `#8C8C88`, cada 6 px, sobre `--sin-datos`.
  Igual que antes: cuenta en la leyenda, nunca se confunde con un valor bajo de prioridad.
- **Confianza baja** (canal no cromático, igual que antes): superposición de **punteado**, puntos de
  1.2 px en `rgba(17,17,17,.45)` cada 5 px, retícula ortogonal. No usa opacidad (reservada a la
  atenuación de foco, §4.4).

### 4.3 Escala de tendencia (heredada, uso restringido a Nivel 2)

Se conserva la paleta divergente azul↔ocre de la versión anterior, pero su uso queda **restringido**
a los lugares donde de verdad se describe una tendencia demográfica de dos sentidos (sube/baja), no
una prioridad: la gráfica de población objetivo de Nivel 2 (§10.5) y, si el usuario lo pide en el
detalle de una rama, el indicador de tendencia de esa rama. **Nunca** colorea el mapa ni el ranking
en su color principal — eso es tarea de §4.2.

| token | valor | cuándo |
|---|---|---|
| `--sube-1` / `--sube-2` / `--sube-3` | `#C6DAEA` / `#7EA7CB` / `#2F6A9E` | tendencia al alza, intensidad por magnitud |
| `--baja-1` / `--baja-2` / `--baja-3` | `#F1D3B3` / `#DD9A5E` / `#A95616` | tendencia a la baja |
| `--mantiene` | `#E3DDD0` | estable |
| `--sube-texto` / `--baja-texto` / `--mantiene-texto` | `#245A88` / `#8F4712` / `#5E5646` | símbolo o palabra como texto (≥ 6.5:1) |

Símbolos, igual que antes: ▲ Sube · ▼ Baja · ■ Se mantiene · ∅ Sin datos — usados solo junto a la
palabra, nunca solo el color.

### 4.4 Estado recesivo (atenuación por foco)

Sin cambios: luminosidad y saturación, no opacidad.

| token | valor | uso |
|---|---|---|
| `--recesivo-relleno` | `#EEEEEB` | relleno de las alcaldías vecinas en vista de alcaldía |
| `--recesivo-contorno` | `#858581` | contorno de las vecinas (3.5:1) |
| `--recesivo-texto` | `#6E6E6B` | etiquetas de las vecinas (4.9:1) |
| `--recesivo-filtro` | *(retirado, ver nota)* | — |

> **Corrección de rendimiento (`correccion/action_plan.md` §8.2 punto 42).** La versión anterior
> definía `--recesivo-filtro: saturate(0) brightness(1.08)` y lo aplicaba con `filter` CSS a cada
> alcaldía recesiva. Medido: ese `filter` por sí solo costaba ~9 s de hilo bloqueado en el peor
> caso (rasteriza cada vecina fuera de pantalla, a la escala del zoom). Se retira: el mismo efecto
> visual ya lo dan `--recesivo-relleno`/`--recesivo-contorno` sin filtro.

### 4.5 Prioridades y pesos (componente nuevo)

| token | valor | uso |
|---|---|---|
| `--peso-relleno` | `--tinta` | círculo de prioridad activo (1–5) |
| `--peso-vacio` | `--linea` | círculo de prioridad inactivo |
| `--peso-foco` | `--foco` | anillo de foco sobre el control de círculos |

### 4.6 Tipografía

Sin cambios de fondo respecto a la versión anterior; se añade un tamaño para las etiquetas de rama.

- Familia: **Inter 4.x variable** (licencia OFL), ejes `wght` 300–700 y `opsz`.
- Archivos: `frontend/vendor/fonts/InterVariable.woff2` e `InterVariable-Italic.woff2`, subconjunto
  latín + latín extendido (~110 kB). Carga `font-display: swap` + `preload` del archivo normal.
- Features `"tnum" 1, "cv11" 1` en cifras. Respaldo: `"Inter", "Helvetica Neue", Arial, system-ui,
  sans-serif`.

| token | tamaño / interlínea | peso | tracking | uso |
|---|---|---|---|---|
| `--t-mision` | clamp(24px, 2vw, 30px) / 1.15 | 420 | −0.01em | pantalla inicial, "¿Dónde podrían hacer falta más servicios…?" |
| `--t-ficha-cifra` | 40px / 1.0 | 380 | −0.02em | oportunidad relativa u otra cifra principal de la ficha |
| `--t-h2` | 20px / 1.2 | 500 | −0.005em | nombre de alcaldía o zona en la columna |
| `--t-cuerpo` | 14px / 20px | 400 | 0 | celdas, detalle, drawer |
| `--t-subtitulo` | 13px / 18px | 450 | 0 | línea de escenario activo bajo la configuración |
| `--t-nota` | 12px / 16px | 400 | 0 | notas, fuentes, tooltip secundario, ayudas "?" |
| `--t-etiqueta` | 11px / 14px | 550 | 0.08em, MAYÚSCULAS | encabezados, ramas, franja lateral |

- `hyphens: auto`, `lang="es-MX"` en `<html>`, `text-wrap: pretty`.
- Modo presentación (§10.9): todos los tamaños × 1.25 con `--escala: 1.25`.

### 4.7 Espaciado, retícula y movimiento

Sin cambios respecto a la versión anterior.

- Escala: `--e-1: 4px` … `--e-8: 64px`. Columna izquierda con padding de 32 px / 24 px.
- Filas de ranking: 36 px. Encabezado: 32 px. Sin `border-radius` salvo 2 px en controles
  segmentados, el pulgar del slider y los círculos de prioridad.
- Movimiento: `--d-intencion` 100ms · `--d-repliegue` 180ms · `--d-xs` 120ms · `--d-s` 200ms ·
  `--d-m` 300ms · `--d-l` 700ms (vuelo del mapa) · `--ease-salida`
  `cubic-bezier(0.22,1,0.36,1)` · `--ease-entrada-salida` `cubic-bezier(0.65,0,0.35,1)` ·
  `--ease-pop` `cubic-bezier(0.34,1.45,0.64,1)` · `--ease-lineal` `linear`.
  Con `prefers-reduced-motion: reduce`, todos los `--d-*` a 0 ms salvo crossfades (120 ms).

## 5. Pantalla inicial y flujo de configuración

### 5.1 Pantalla inicial

`correccion/frontend_requisitos.md` §4, texto exacto:

- Texto principal (`--t-mision`): **"¿Dónde podrían hacer falta más servicios para las
  infancias?"**
- Texto secundario (`--t-cuerpo`, `--tinta-2`): **"Habitancia analiza cómo podría cambiar la
  población infantil y cómo se distribuyen distintos servicios en la Ciudad de México para
  identificar zonas que conviene explorar con mayor detalle."**
- Mapa general de la CDMX (polígonos de alcaldía, límites visibles), coloreado con el índice
  compuesto por omisión (pesos iguales, población "todas", horizonte 3 años, búsqueda "oportunidad
  de expansión" — valores iniciales, §5.6).
- Icono "?" junto al mapa: **"Cada zona corresponde a una AGEB, una división geográfica utilizada
  por INEGI para organizar información estadística."**

### 5.2 Selección de alcaldía

- **En el mapa.** Cada alcaldía es seleccionable; hover muestra su nombre; clic abre su vista
  (§10.2); hay una forma clara de volver ("← Todas las alcaldías", §10.7).
- **Buscador**, siempre visible: **"Selecciona una alcaldía en el mapa o búscala por nombre."** El
  usuario escribe, selecciona de una lista o va directamente. Mismo mecanismo que el buscador de
  AGEB de la versión anterior (§7.3), aplicado a alcaldías: `debounce` 120 ms, mensaje sin
  resultados, Enter con resultado único navega.

### 5.3 Población objetivo

Selector **"¿A quién quieres analizar?"** (`correccion/frontend_requisitos.md` §5), seis opciones:

| opción | icono sencillo | columna censal (`docs/metodologia.md` §1.1) |
|---|---|---|
| Todas las infancias y adolescencias · 0–17 años | — | `p_0a2+p_3a5+p_6a11+p_12a14+p_15a17` |
| Primera infancia · 0–2 años | — | `p_0a2` |
| Preescolar · 3–5 años | — | `p_3a5` |
| Primaria · 6–11 años | — | `p_6a11` |
| Secundaria · 12–14 años | — | `p_12a14` |
| Adolescencia · 15–17 años | — | `p_15a17` |

Icono "?": **"La población objetivo indica qué grupo de niñas y niños quieres analizar. Cambiarla
modifica la población que se compara con los servicios disponibles."** El segmento 15–17 tiene
confianza tope `media` (oferta educativa parcial, `docs/metodologia.md` §1.1); no se explica la
razón estadística aquí, solo se ve reflejado en el indicador de confianza cuando ese segmento está
activo.

### 5.4 Horizonte

Ver §8 (componente compartido con la versión anterior, valores actualizados a 1/3/5 años).

### 5.5 Tipo de búsqueda

Pregunta **"¿Qué quieres encontrar?"** (`correccion/frontend_requisitos.md` §7), dos opciones,
`role="radiogroup"`:

- **Oportunidad de expansión** — *"Ordena primero las zonas donde, de acuerdo con los criterios
  seleccionados, podría existir mayor espacio para ampliar o fortalecer servicios."* Usa
  `O_{i,h,r}`/`IC_{i,h}` (`docs/metodologia.md` §10.2-10.3).
- **Disponibilidad para familias** — *"Ordena primero las zonas donde existe una mayor
  disponibilidad relativa de los servicios seleccionados."* Usa `F_{i,h,r}`
  (`docs/metodologia.md` §10.5).

Icono "?": **"Una zona con poca oferta puede representar una oportunidad de expansión, pero al
mismo tiempo tener baja disponibilidad actual para las familias. Por eso ambas búsquedas responden
preguntas diferentes."**

Cambiar el tipo de búsqueda **no vuelve a pedir datos**: ambos índices se derivan de los mismos
ingredientes (§17.4), así que el cambio es una reordenación instantánea del ranking y un
recoloreado del mapa (mismo mecanismo del cambio de vista, §9).

### 5.6 Valores iniciales del escenario

Al entrar a Habitancia, antes de cualquier interacción: población **"Todas · 0–17"**, horizonte
**3 años**, búsqueda **"Oportunidad de expansión"**, las cuatro ramas con **peso igual** (3/5 cada
una), sin filtros activos (todas las subcategorías incluidas). Es un escenario válido y completo,
no un estado vacío: el mapa y el ranking ya muestran resultados desde el primer render.

## 6. Nivel 1 — Resumen estructurado

**Sustituye por completo al "titular dinámico" de la versión anterior de este documento.** No hay
frase autogenerada: es una lista de campos etiquetados
(`correccion/frontend_requisitos.md` §1, §13).

### 6.1 Composición (vista general / CDMX)

```html
<section class="resumen-nivel1" aria-labelledby="resumen-titulo">
  <h2 id="resumen-titulo">…</h2>
  <dl class="resumen-nivel1__campos"><!-- pares etiqueta/valor, nunca texto libre --></dl>
</section>
```

Campos, en este orden, con su ayuda "?" cuando corresponda (§10.14):

| etiqueta | valor | fuente |
|---|---|---|
| Zona / Alcaldía | nombre; en AGEB, clave amigable "Zona en {alcaldía}" | `properties.nombre` / `cvegeo` |
| Población analizada | rango de edad elegido (§5.3) | estado |
| Horizonte | "{h} años · {año}" | estado |
| Búsqueda | "Oportunidad de expansión" / "Disponibilidad para familias" | estado |
| Oportunidad relativa (o Disponibilidad relativa) | Alta / Media / Baja — de `O_{i,h,r}`/`IC_{i,h}` en terciles, `docs/metodologia.md` §10.3 | motor de composición |
| Confianza | Alta / Media / Baja | capa demanda del segmento activo |
| Ramas con mayor incidencia | lista de 1–2 ramas con mayor `w_r·O_{i,h,r}` | motor de composición |

**No hay altura reservada por "frase": cada campo es un renglón fijo**, así que no hace falta el
mecanismo de crossfade con altura reservada de la versión anterior — el `<dl>` cambia de valores,
no de estructura, entre un escenario y otro. Los cambios de valor sí llevan un crossfade breve
(120 ms) para no parpadear.

### 6.2 Terciles de oportunidad/disponibilidad relativa (Alta/Media/Baja)

Sobre `O_{i,h,r}`/`IC_{i,h}` ∈ [0,1] (percentil ya calculado, `docs/metodologia.md` §10.2-10.3),
entre las unidades con dato del mismo nivel territorial (AGEB entre AGEB, alcaldía entre
alcaldías): `Alta` ≥ percentil 66, `Media` entre 33 y 66, `Baja` < percentil 33. Mismos umbrales
para "confianza", tomados directamente de `confianza` en el contrato (§17.2), sin recalcular.

### 6.3 Vista de alcaldía

`correccion/frontend_requisitos.md` §12, ejemplo textual:

```
Ciudad de México > Álvaro Obregón

Álvaro Obregón
Población: 6–11 años
Horizonte: 3 años
Búsqueda: Oportunidad de expansión
Oportunidad relativa: Alta
Confianza: Media–alta
Ramas con mayor incidencia: Educación y cultura / Salud
```

Mismos campos que §6.1, agregados a nivel alcaldía (media ponderada de sus AGEB con dato, mismo
motor de composición). Aparece primero, antes que cualquier gráfica o tabla.

### 6.4 Motivos principales del resultado

`correccion/frontend_requisitos.md` §13: en vez de una frase autogenerada, indicadores
estructurados, uno por rama:

```
Educación y cultura: disponibilidad relativa baja
Salud: disponibilidad relativa media
Áreas verdes y espacio público: disponibilidad relativa media
Comercio: disponibilidad relativa alta
```

Cada línea es `{rama}: disponibilidad relativa {tercil}` (mismos terciles de §6.2, aplicados a
`O_{i,h,r}` de esa rama sola). Botón **"Entender esta zona"** al final, abre Nivel 2 (§10.6).

## 7. Ranking por AGEB

**Sustituye a la tabla de predicciones por alcaldía de la versión anterior.** La unidad mínima que
se rankea es siempre la AGEB (`correccion/frontend_requisitos.md` §11: "las alcaldías NO son la
unidad mínima que se colorea"); la alcaldía es el filtro de navegación.

### 7.1 Vista general (ranking de toda la CDMX)

- `<table>` real, `<caption>` visualmente oculto: "Ranking de zonas por {búsqueda activa}, {n}
  ramas consideradas, a {h} años". Columnas ordenables como `<button>` con `aria-sort` dentro del
  `<th>`.
- Muestra el **top N** (20 por omisión, `correccion/action_plan.md` Fase 6 punto 33), con "Ver más"
  para ampliar dentro del mismo contenedor con scroll — mismo patrón sin virtualizar que la versión
  anterior (≤ ~300 filas es aceptable).

| columna | contenido | alineación |
|---|---|---|
| ZONA | "{alcaldía}" (la clave AGEB **no** es el dato principal, requisitos §11) | izquierda |
| OPORTUNIDAD (o DISPONIBILIDAD) | símbolo de intensidad + palabra ("●●●● Alta") | izquierda |
| RAMA PRINCIPAL | nombre de la rama con mayor incidencia | izquierda |
| CONFIANZA | ● alta · ◐ media · ○ baja | centro |

- **Orden por defecto:** oportunidad/disponibilidad relativa descendente (lo más prioritario
  arriba). También por alcaldía (A–Z) y por confianza.
- **Filtro de nivel de riesgo** (`correccion/frontend_requisitos.md` §2, "nivel de riesgo
  aceptable"): un control aparte, no una columna — umbral sobre la confianza/`p_dec` de la demanda
  del segmento activo; el ranking solo lista unidades que lo superan. Ver §10.12.
- Filas de 36 px, misma mecánica de fila activa/hover que la versión anterior.

### 7.2 Fila desplegada (acordeón) — mismo mecanismo FLIP que la versión anterior

Altura fija (136 px), mismo disparo por hover con intención (100 ms) / foco por teclado / pliegue
diferido (180 ms) / una sola fila a la vez / FLIP de 200 ms al reordenar, **sin cambios
mecánicos** respecto a §7.2 de la versión anterior de esta especificación. Cambia el **contenido**:

```
│ Zona en Coyoacán            ●●●● Alta   Educación y cultura      ● │
│┌─────────────────────────────────────────────────────────────────┐│
││ Oportunidad relativa: alta (percentil 84 entre las zonas de CDMX) ││
││ Ramas: Educación ●●●●● · Salud ●●● · Verde ●● · Comercio ●        ││
││ ● Confianza alta: el resultado se sostiene aun con supuestos distintos.││
││                                          ENTENDER ESTA ZONA →     ││
│└─────────────────────────────────────────────────────────────────┘│
```

Explicaciones de confianza: mismo texto de la versión anterior (§14.3), reutilizado tal cual —
sigue siendo la explicación correcta de qué significa cada nivel.

### 7.3 Vista de alcaldía (ranking de sus AGEB)

Mismo patrón que la versión anterior §7.3 (resumen de 4 líneas sin acordeón → ahora es el resumen
Nivel 1 de §6.3; lista de AGEB con orden por defecto |oportunidad| descendente; 12 filas + "Ver los
{n} AGEB ↓"; buscador de AGEB por clave, precargado con el prefijo de la alcaldía). Columnas:
ZONA (clave AGEB, `tnum`) · OPORTUNIDAD/DISPONIBILIDAD · RAMA PRINCIPAL · CONFIANZA.

### 7.4 Ficha de zona (AGEB) — Nivel 1 + entrada a Nivel 2

Reutiliza la estructura de "ficha de AGEB" de la versión anterior (§7.4), con el contenido de Nivel
1 (§6.1, sin frase) como cabecera y el botón "Entender esta zona" (no "Explorar alcaldía") como
salida hacia Nivel 2 (§10.6). La mini-gráfica SVG que antes vivía aquí se mueve a Nivel 2 (§10.5):
Nivel 1 no debe saturar con gráficas (`correccion/frontend_requisitos.md` §1).

## 8. Control de horizonte

Mismo componente que la versión anterior, con las paradas actualizadas a **1, 3 y 5 años**
(`docs/metodologia.md` §7, `correccion/action_plan.md` Fase 1):

```
HORIZONTE                                   HORIZONTE                                   HORIZONTE
 ●━━━━━━━━━○━━━━━━━━━○                       ○━━━━━━━━━●━━━━━━━━━○                       ○━━━━━━━━━○━━━━━━━━━●
1 año      3 años     5 años                1 año      3 años     5 años                1 año      3 años     5 años
2027       2029       2031                  2027       2029       2031                  2027       2029       2031
```

- `<input type="range" min="1" max="5" step="…">` con `<datalist>` en las tres paradas (el paso no
  es uniforme: 1→3→5; se implementa con `<datalist>` + valores discretos, no con `step` lineal).
- `aria-valuetext`: "3 años, a mediados de 2029". Táctil: arrastre o toque en la etiqueta.
- **Qué cambia al mover el slider:** color de AGEB/alcaldías (la vista activa, §9), punteado de
  confianza, resumen Nivel 1 (§6), ranking (reordenamiento FLIP), ficha/Nivel 2, leyenda y sus
  conteos, hash `&h=`. **Nunca dispara peticiones de red**: los horizontes ya vienen en el archivo.
- **Ramas sin horizonte 5 años.** Educación, salud y comercio solo reportan `h1`/`h3`
  (`docs/metodologia.md` §6.3): si el horizonte activo es 5 años y la vista de mapa es una de esas
  ramas, el slider muestra su pulgar detenido en `h3` con la nota **"Esta rama se proyecta solo
  hasta 3 años; el resultado que ves es a 3 años."** La vista general (índice compuesto) sigue
  igual de disponible a 5 años porque se renormaliza sobre las ramas con dato a ese horizonte
  (`docs/metodologia.md` §10.3).
- **Verde, sin proyección.** Si la vista de mapa activa es "Áreas verdes y espacio público", el
  slider completo queda deshabilitado con la nota **"Esta rama no tiene proyección: se muestra su
  disponibilidad actual."** (`correccion/frontend_requisitos.md` §16).
- Icono "?": **"Las proyecciones son estimaciones. Mientras más lejano es el horizonte, mayor puede
  ser la incertidumbre."**

## 9. Vista general y vistas por rama (selector de mapa)

**Sustituye al control segmentado de "capas" de la versión anterior.**
`correccion/frontend_requisitos.md` §11A, textual: selector **"¿Qué quieres ver en el mapa?"**, con
cinco opciones — Vista general · Educación y cultura · Áreas verdes y espacio público · Salud ·
Comercio.

- Es un `role="radiogroup"` con `<input type="radio">` estilizados (mismo patrón técnico que el
  control segmentado anterior); las flechas cambian la opción.
- **Se conserva EL MISMO mapa de AGEB**; cambiar de vista solo actualiza: color de las zonas,
  leyenda, ranking, título de la vista y la información que aparece al seleccionar una zona
  (`correccion/frontend_requisitos.md` §11A). Nunca se abren mapas separados por rama.
- **Vista general.** Usa el índice compuesto `IC_{i,h}` (`docs/metodologia.md` §10.3), que sí
  combina las cuatro ramas con los pesos elegidos (§10.10). Pregunta que responde: *"Considerando
  todo lo que seleccioné, ¿qué zonas aparecen con mayor oportunidad relativa?"* Es la opción por
  omisión.
- **Vista de una rama.** Muestra solo `O_{i,h,r}` de esa rama, respetando sus filtros activos
  (§10.11). Pregunta que responde, por rama: *"¿Cómo se distribuye la disponibilidad u
  oportunidad relacionada con {filtro activo}?"* (educación) / *"¿En qué zonas existe mayor o menor
  disponibilidad relativa de {filtro activo}?"* (salud) / *"¿Dónde existe mayor o menor
  disponibilidad relativa de {filtro activo}?"* (comercio) / *"¿Cómo se distribuyen los espacios
  verdes o públicos seleccionados?"* (verde).
- **Pesos vs. vistas de rama — distinción obligatoria** (`correccion/frontend_requisitos.md`
  "Relación entre pesos y vistas por rama"): el peso de una rama **solo** influye en la Vista
  general (a través de `IC_{i,h}`). En la vista individual de esa rama, el peso **no altera el
  color**: la vista de "Salud" muestra la disponibilidad de salud sea cual sea su peso. Los filtros
  sí modifican la vista individual, porque determinan qué datos de esa rama se están mirando.
- **Cambio automático de leyenda y titular de vista.** Cada cambio de vista actualiza: (1) el
  título fijo de la vista, (2) la leyenda (§10.4, agrupada por rama activa), (3) el ranking (§7),
  (4) los indicadores visibles, (5) la ficha de la zona seleccionada. Nunca genera una narrativa
  automática — solo cambian etiquetas ya escritas.
- Nombre de la vista visible en seis lugares: selector, resumen Nivel 1, encabezado de leyenda,
  encabezados de ranking, tooltip del mapa y ficha — mismo principio de "seis lugares" que la
  versión anterior aplicaba a la capa.

## 10. Componentes

### 10.1 Mapa: vista general

Sin cambios mecánicos respecto a la versión anterior (§10.1 de esa versión): 16 polígonos de
alcaldía con contorno de 1 px `--papel` entre vecinas, contorno exterior de la CDMX en
`--linea-fuerte`, hover con contorno de 2 px + elevación leve (120 ms), tooltip mínimo a 12 px del
puntero. **Cambia el contenido del tooltip**: "Coyoacán" / "{Vista activa}: ●●●● Alta" en vez de
"Demanda: ▼ Baja".

### 10.2 Transición de foco (clic, Enter o segundo toque)

**Mismo gesto de 820 ms, mismos cinco pasos (pop, vuelo, recesión, entrada de AGEB, crossfade de
columna) de la versión anterior (§10.2), con la corrección de rendimiento ya incorporada en §3 y
§4.4** (un solo grupo envolvente animado, sin `filter` en las vecinas recesivas). Lo único que
cambia es el contenido de la columna que entra: Nivel 1 (§6.3) + ranking de AGEB (§7.3) en vez del
resumen de 4 líneas + tabla de la versión anterior. El prefetch del GeoJSON de AGEB en hover con
intención (100 ms) o `requestIdleCallback` a los 2 s se mantiene igual.

### 10.3 Mapa: vista de alcaldía

Sin cambios mecánicos respecto a la versión anterior (§10.3): AGEB de la alcaldía coloreados por la
vista activa, hover con contorno de 2 px + tooltip, clic abre la ficha con marca permanente, botón
"Reencuadrar" tras zoom/paneo manual.

### 10.4 Leyenda

- Posición y contorno igual que la versión anterior. **Contenido nuevo**: agrupa en las tres
  categorías de §4.2 ("Mayor oportunidad relativa" / "Oportunidad intermedia" / "Menor oportunidad
  relativa", o su variante de disponibilidad), con el conteo de zonas en cada una y la muestra de
  color correspondiente. Fila de confianza baja (punteado) igual que antes.
- **Filtro y realce.** Mismo mecanismo `aria-pressed` por categoría que la versión anterior: pulsar
  una categoría atenúa las demás (mismo canal de §4.4) y filtra el ranking en paralelo
  ("Mostrando {n} de {total} · Quitar filtro").
- **Encabezado.** "LEYENDA · {VISTA ACTIVA} · {AÑO}".

### 10.5 Nivel 2: gráficas de la zona

Vive dentro del drawer "Entender esta zona" (§10.6), no en Nivel 1. Reutiliza la mecánica de mini-
gráfica SVG de la versión anterior (§7.4: puntos observados, tramo sólido/punteado, proyección,
banda de incertidumbre, horizontes ◇/◆, `<figcaption>` oculta con cifras exactas), pero ahora son
**dos gráficas separadas**, tal como pide `correccion/frontend_requisitos.md` §15-17:

**A. "¿Cómo ha cambiado la población objetivo?"** (§15 de requisitos)
- Histórico (censos 2010/2020) + proyección + rango de incertidumbre, con controles de horizonte
  (1/3/5 años, mismo componente de §8, sincronizado con el horizonte global).
- Icono "?": **"La parte histórica muestra los datos observados. La parte proyectada muestra cómo
  podría continuar la tendencia. El rango alrededor de la proyección representa la
  incertidumbre."**
- Usa la escala de tendencia (§4.3), no la de prioridad: aquí sí es correcto pintar la línea
  proyectada en el color sube/baja, porque describe una tendencia de dos sentidos.

**B. "¿Cómo han cambiado los servicios disponibles?"** (§16 de requisitos)
- Depende de los **filtros activos**: si el filtro es "Primaria · Público", la gráfica muestra la
  evolución de establecimientos de primaria pública en esa zona (suma de las celdas seleccionadas,
  §17.4). Si es "Hospitales", muestra hospitales.
- Icono "?": **"Esta gráfica muestra establecimientos registrados. No representa capacidad,
  calidad, matrícula ni número de lugares disponibles."**
- **Solo se proyectan ramas con serie temporal** (educación, salud, comercio, §6.3 de metodología).
  Áreas verdes y espacio público muestran su situación actual, **sin línea futura inventada**
  (`correccion/frontend_requisitos.md` §16, regla explícita).

**C. Cobertura** (§17 de requisitos), tercer bloque, después de población y servicios:
- Pregunta: **"¿Cómo se relaciona la cantidad de servicios con la población?"**
- Muestra cobertura actual, cobertura proyectada cuando exista (no para verde), y una referencia de
  CDMX o comparación con otras zonas (percentil, §6.2 de este documento).
- Icono "?": **"La cobertura relaciona los servicios disponibles con el tamaño de la población
  objetivo para poder comparar zonas de tamaños distintos."**

### 10.6 Franja lateral y drawer — ahora "Entender esta zona"

Misma mecánica que la versión anterior (§10.5 de esa versión: franja de 40 px con texto rotado,
`<dialog>` modal de 560 px desde la derecha, foco inicial en el título, Esc cierra y devuelve el
foco, hash enlazable `#/…?…&nivel2=1`). **Cambia el contenido y el disparador**:
- Se abre desde el botón "Entender esta zona" (§6.4, §7.2) cuando hay una zona seleccionada, y
  desde "Metodología ↗" en la cabecera cuando no la hay (mismo drawer, dos entradas — igual que
  antes con "Metodología").
- Contenido, en orden (`correccion/frontend_requisitos.md` §14): A) ¿Cómo ha cambiado? (§10.5-A) ·
  B) ¿Qué podría pasar? (proyección de la misma gráfica) · C) ¿Qué explica el resultado? (§10.5-C +
  bloque de explicación por rama, §10.7) · D) ¿Qué ramas pesan más bajo mis criterios? (mismo
  bloque, con los pesos activos visibles).
- Cuando se abre sin zona seleccionada, muestra el texto de metodología y limitaciones (§14.7,
  heredado casi intacto de la versión anterior) más el resumen del backtest (§14.8, nuevo).

### 10.7 "¿Qué explica este resultado?" (bloque de explicación por rama)

`correccion/frontend_requisitos.md` §18, dentro de Nivel 2:

```
Educación y cultura        ● ● ● ● ○
Salud                      ● ● ● ○ ○
Áreas verdes y espacio público ● ● ○ ○ ○
Comercio                   ● ● ● ● ○
```

**Círculos no editables** (distintos de los de prioridad, §10.10 — la distinción es obligatoria y
se marca visualmente: estos van en `--tinta-2`, sin borde interactivo, y llevan `aria-readonly`).
Representan la intensidad de la señal de cada rama en el resultado de esa zona, después de aplicar
filtros y pesos. Icono "?" por rama, ejemplo: **"Educación y cultura: la disponibilidad de los
servicios educativos seleccionados es relativamente baja frente a otras zonas comparables."**
Debajo de los círculos, sin frase automática: valor/nivel de la rama, peso asignado, contribución al
resultado general (si ya está calculada), icono "?".

### 10.8 Cabecera y migas

Igual que la versión anterior (§10.6): migas `<nav aria-label="Ruta">`, nivel actual con
`aria-current="page"`, clic en un nivel retrocede con la transición inversa (§10.9). Cambia el
nombre del producto en la cabecera a "Habitancia" y el conmutador de capa se sustituye por el
selector de vista (§9).

### 10.9 Transición inversa (volver)

Sin cambios mecánicos respecto a la versión anterior (§10.7): AGEB→alcaldía con crossfade de 200 ms
sin mover el mapa; alcaldía→general con vuelo inverso de 700 ms + salida de AGEB (200 ms) +
recuperación de color de vecinas (300 ms) + crossfade de columna (0–480 ms, igual escalonado que la
entrada). El foco vuelve a la fila del ranking, desplegada.

### 10.10 Prioridades (pesos) — componente nuevo

`correccion/frontend_requisitos.md` §9. Sección **"¿Qué es más importante para ti?"**, con las
cuatro ramas y un control de cinco círculos cada una:

```
Educación y cultura
● ● ● ● ○

Áreas verdes y espacio público
● ● ● ○ ○

Salud
● ● ● ● ●

Comercio
● ● ● ○ ○
```

- Círculos **interactivos**: 5 = prioridad muy alta, 1 = prioridad baja. Clic/toque en un círculo
  fija el peso hasta ese punto; también responde a flechas con foco en el grupo (patrón
  `role="slider"` con `aria-valuemin=1 aria-valuemax=5`, un `role="slider"` por rama).
- **No alteran los datos ni las predicciones.** Solo modifican, en el cliente: el índice compuesto
  (§9, vista general), la oportunidad/disponibilidad relativa resultante y el orden del ranking.
- Icono "?": **"Los pesos indican qué tan importante es cada rama para tu búsqueda. Habitancia
  utiliza esa preferencia para ordenar las zonas, pero no cambia los datos originales."**
- Botón **"Restablecer prioridades"** → todas a 3/5 (escenario inicial, §5.6).
- Cambiar un peso actualiza mapa (vista general), ranking y resumen Nivel 1 **en el mismo ciclo de
  eventos**, sin red (§17.4).

### 10.11 Filtros por rama — componente nuevo

`correccion/frontend_requisitos.md` §10. Pestaña/apartado **"Filtros"**, un sub-panel por rama.
Nunca añade complejidad matemática nueva: solo decide qué celdas de filtro (§17.3) se suman.

**10.11.1 Educación y cultura.** Pregunta: *"¿Qué servicios de educación y cultura quieres
considerar?"* — NIVEL/TIPO: Guarderías y estancias infantiles · Preescolar · Primaria · Secundaria
· Media superior o técnica · Educación especial · Recreación o cultura infantil. SECTOR: Todos ·
Público · Privado. **Sugerencia automática, no forzada**: si la población objetivo (§5.3) es
6–11, sugiere "Primaria"; si es 15–17, sugiere "Media superior o técnica" cuando los datos lo
permitan — el usuario puede modificarlo. Icono "?": *"Estos filtros indican qué tipos de servicios
educativos o culturales quieres incluir en el análisis de esta rama."*

**10.11.2 Salud.** Pregunta: *"¿Qué instalaciones de salud quieres considerar?"* — TIPO: Clínicas o
consultorios · Hospitales · Salud mental o psicológica · Farmacias. SECTOR: Todos · Público ·
Privado. Icono "?": *"Habitancia utiliza únicamente los tipos de instalaciones que selecciones
para calcular la disponibilidad de servicios de salud."*

**10.11.3 Comercio.** Pregunta: *"¿Qué comercios quieres considerar?"* — TIPO: Comercios de primera
necesidad · Supermercados y minisúpers · Abarrotes · Frutas y verduras · Carnes y otros alimentos ·
Farmacias (si se decide incluirlas también aquí). Selección de "Todos" o varios tipos. Icono "?":
*"Este filtro permite decidir qué tipos de comercios cotidianos deben considerarse al analizar la
disponibilidad de productos de primera necesidad."*

**10.11.4 Áreas verdes y espacio público.** Pregunta: *"¿Qué tipo de espacio quieres
considerar?"* — Áreas verdes recreativas · Cobertura verde · Espacio público. Icono "?": *"No toda
superficie verde funciona como espacio recreativo. Este filtro permite diferenciar entre cobertura
verde general y espacios que pueden tener una función de convivencia o recreación."*

**10.11.5 Comportamiento común.** Todos los filtros actualizan, sin red: mapa (§9), ranking (§7),
ficha (§6, §10.5), explicación por rama (§10.7) y las gráficas que correspondan. Botón
**"Restablecer filtros"**. Siempre hay un resumen breve del escenario activo, visible cerca del
selector de vista: **"6–11 años · Primaria · 3 años"**, o, con filtros más específicos, **"Primaria
pública · hospitales y clínicas · comercio de primera necesidad · áreas verdes recreativas"**.

### 10.12 Filtro de nivel de riesgo

Control aparte, no una rama: umbral sobre `p_dec`/confianza de la demanda del segmento activo
(`docs/metodologia.md` §10.4). Vive junto al ranking (§7.1), no en "Filtros" (que son por rama).
Mover el umbral filtra el ranking sin red.

### 10.13 Comparar alcaldías — componente nuevo

`correccion/frontend_requisitos.md` §19. Pestaña o función **"Comparar"**:

```
Educación y cultura      Alcaldía A: Media    Alcaldía B: Media
Salud                    Alcaldía A: Baja     Alcaldía B: Alta
Verde y espacio público  Alcaldía A: Alta     Alcaldía B: Media
Comercio                 Alcaldía A: Media    Alcaldía B: Media
Oportunidad relativa     Alcaldía A: Alta     Alcaldía B: Media
Confianza                Alcaldía A: Alta     Alcaldía B: Media
```

- El usuario elige Alcaldía A vs. Alcaldía B. La comparación **conserva exactamente** el escenario
  activo (población, horizonte, búsqueda, pesos, filtros) — no reinicia nada.
- Indicadores equivalentes lado a lado, mismos terciles de §6.2. **Nunca declara un ganador ni
  genera una frase automática.**
- Cambiar cualquier control del escenario recalcula la comparación en el mismo ciclo de eventos.

### 10.14 Iconos "?" como sistema de ayuda

`correccion/frontend_requisitos.md` §20. Cada ayuda responde tres preguntas fijas: qué es / por qué
importa / cómo interpretarlo. Se abren dentro de la misma vista (popover anclado al icono, no
navegación a otra pantalla). Conceptos con ayuda obligatoria (lista completa de requisitos §20,
textos ya dados en las secciones correspondientes de este documento): oportunidad relativa (§2.1),
demanda potencial/oferta (§14.6, heredado), cobertura (§10.5-C), confianza (§14.3, heredado),
incertidumbre (§8), pesos (§10.10), población objetivo (§5.3), histórico/proyección (§10.5-A), cada
una de las cuatro ramas cuando haga falta (§10.11).

### 10.15 Táctil, teclado y modo presentación

Sin cambios mecánicos respecto a la versión anterior (§10.8-10.9): primer/segundo toque en
`pointer: coarse`, orden de Tab (cabecera → configuración → prioridades → filtros → resumen →
ranking → control de horizonte → leyenda → franja), Esc retrocede un nivel (drawer > filtro de
leyenda > vista), modo presentación con `--escala:1.25` oculta buscador/orden/pie/franja y conserva
vista de mapa/slider/migas. Se añade al orden de Tab, entre "configuración" y "prioridades", el
selector de tipo de búsqueda (§5.5); y entre "prioridades" y "filtros", los propios filtros por
rama (§10.11) cuando el panel está expandido.

## 11. Móvil y tableta (< 1024 px)

Mismo patrón de hoja inferior de tres alturas de la versión anterior (§11: baja 128 px, media 50
dvh, alta 88 dvh, asa arrastrable o `<button>` cíclico, transición de 300 ms). **Contenido de la
hoja reordenado** para seguir el flujo de §2.3: en altura baja, resumen Nivel 1 compacto + asa; en
media, resumen + ranking con scroll; en alta, panel completo (configuración → prioridades → filtros
→ resumen → ranking), con el mapa como banda del 12 % superior. El control de horizonte y el
selector de vista siguen accesibles en las tres alturas (horizonte flotando sobre el borde superior
de la hoja en baja/media, primera fila en alta). Tableta (768–1023 px): mismo esquema, hoja de
560 px alineada a la izquierda.

## 12. Mapa de interacciones

Tabla heredada de la versión anterior (§12), con las filas nuevas de Habitancia añadidas:

| disparador | efecto | duración | easing | con movimiento reducido |
|---|---|---|---|---|
| Hover alcaldía/zona o fila (≥ 100 ms) | realce + despliegue de fila + prefetch AGEB | 120 ms / 200 ms | `--ease-salida` | instantáneo |
| Salida de fila o polígono | pliegue tras 180 ms | 200 ms | `--ease-salida` | instantáneo |
| Cambio de fila desplegada | FLIP del `tbody` | 200 ms | `--ease-salida` | instantáneo |
| Clic/Enter/segundo toque en alcaldía | pop + vuelo + recesión + AGEB + columna (§10.2) | 820 ms | ver §10.2 | corte + crossfade 120 ms |
| Clic en vecina (vista alcaldía) | foco directo | 700 ms + 300 ms | `--ease-entrada-salida` | corte + crossfade 120 ms |
| Hover AGEB | contorno + tooltip + realce de fila | 100 ms | `--ease-salida` | instantáneo |
| Clic/Enter en AGEB | ficha sustituye a la lista; marca en el mapa | 200 ms crossfade | lineal | crossfade 120 ms |
| Esc / "← Volver" / atrás del navegador | retrocede un nivel (§10.9) | 200/820 ms | espejo del avance | corte + crossfade 120 ms |
| Slider de horizonte | recolor, punteado, resumen, ranking, leyenda | 300/200 ms | `--ease-salida`/lineal | color instantáneo |
| **Cambio de vista de mapa (§9)** | recolor, textos, leyenda, slider (des)habilitado por rama | 300 ms | `--ease-salida` | instantáneo |
| **Cambio de tipo de búsqueda (§5.5)** | reordena ranking, recolor de mapa | 300 ms | `--ease-salida` | instantáneo |
| **Mover un peso (§10.10)** | recalcula índice compuesto, ranking, mapa (vista general) | 300 ms | `--ease-salida` | instantáneo |
| **Cambiar un filtro (§10.11)** | recalcula esa rama, índice compuesto si aplica, mapa, ranking, gráficas | 300 ms | `--ease-salida` | instantáneo |
| **Abrir/cerrar "Comparar" (§10.13)** | panel de comparación entra/sale | 300/200 ms | `--ease-salida` | crossfade 120 ms |
| Orden de ranking | reordenamiento FLIP | 200 ms | `--ease-salida` | instantáneo |
| Filtro de leyenda | recesión de otras categorías; filtro de ranking | 200 ms | `--ease-salida` | instantáneo |
| Abrir/cerrar "Entender esta zona" | drawer desde la derecha | 300/200 ms | `--ease-salida` | crossfade 120 ms |
| Hoja móvil (asa) | cambio de altura | 300 ms | `--ease-salida` | instantáneo |
| Rueda o pellizco (vista alcaldía) | zoom libre acotado | continuo | nativo d3-zoom | igual |
| "Reencuadrar" | vuelo al encuadre | 500 ms | `--ease-entrada-salida` | corte directo |
| Datos cargados (primer render) | esqueleto → contenido | 200 ms crossfade | lineal | crossfade 120 ms |

## 13. Accesibilidad

Hereda íntegro el marco de la versión anterior (§13): contraste ≥ 4.5:1 en texto, ≥ 3:1 en
contornos/controles, foco visible siempre (`outline: 2px solid var(--foco); outline-offset: 2px`);
estructura semántica con `<header>`, `<nav>` (migas), `<main>` con secciones etiquetadas, `<aside>`
para leyenda y pie, `<h1>` oculto con "Habitancia"; el mapa lleva `role="img"` con resumen textual
generado por plantilla (no libre) y **la tabla/ranking es la alternativa completa**: todo lo que se
hace con el mapa se puede hacer desde el ranking. Objetivos táctiles ≥ 44×44 px.

**Región viva global**, anuncios ampliados con los nuevos controles:
- "Vista de Coyoacán: 153 zonas con datos."
- "Horizonte: 3 años, a mediados de 2029."
- "Vista: salud, disponibilidad relativa."
- "Zona 0900300010123: oportunidad relativa alta."
- "Peso de Educación y cultura: 4 de 5."
- "Filtro de Salud actualizado: hospitales y clínicas, sector público."
- "Comparando Coyoacán y Álvaro Obregón."

**Gestión del foco**, ampliada: al abrir "Filtros" o "Prioridades", el foco va al primer control
del panel; al cerrarlos, vuelve al botón que los abrió; el resto (entrar/salir de alcaldía/AGEB,
abrir/cerrar drawer) es igual a la versión anterior.

Los círculos de prioridad (§10.10) y de explicación (§10.7) llevan `role="slider"`/`role="img"`
respectivamente, nunca solo `<div>` con color: cada uno tiene un `aria-label` con el valor
numérico ("Educación y cultura: prioridad 4 de 5" / "Educación y cultura: señal 4 de 5").

## 14. Textos de la UI

Los textos funcionales (preguntas, ayudas "?", ejemplos) están dados **literalmente** en
`correccion/frontend_requisitos.md` y se citan tal cual en las secciones de este documento donde
aplican (§5, §8, §9, §10.5, §10.7, §10.10-§10.13); no se repiten aquí para no mantener dos copias
que puedan divergir — `frontend/js/textos.js` los centraliza citando la sección de este documento
en su comentario. Lo que sigue es lo que **no** está en requisitos.md porque es mecánico o
heredado.

### 14.1 Etiquetas fijas (nuevas o cambiadas respecto a la versión anterior)

| id | texto |
|---|---|
| producto | Habitancia |
| vista.general / educacion / salud / comercio / verde | Vista general · Educación y cultura · Salud · Comercio · Áreas verdes y espacio público |
| busqueda.oportunidad / disponibilidad | Oportunidad de expansión · Disponibilidad para familias |
| horizonte.opcion | {h} año(s) · {año} |
| volver.general | ← Todas las alcaldías |
| entender.zona | Entender esta zona → |
| restablecer.prioridades / restablecer.filtros | Restablecer prioridades · Restablecer filtros |
| comparar | Comparar |
| metodologia.franja | Metodología y limitaciones ↓ |
| ver.todos | Ver los {n} AGEB ↓ |
| buscar.alcaldia / buscar.ageb | Selecciona una alcaldía en el mapa o búscala por nombre · Buscar zona por clave |
| oportunidad.* | Alta · Media · Baja |
| confianza.* | Alta · Media · Baja |

### 14.2 Tooltips

- Alcaldía/zona: "{nombre}" / "{Vista activa}: {símbolo} {tercil}".
- Vecina en vista de alcaldía: "Ir a {nombre}".
- Zona sin datos: "{nombre o clave}" / "Sin datos: {motivo}" (§14.4, heredado).

### 14.3 Explicaciones de confianza (heredadas sin cambio)

- **alta**: "el resultado se sostiene aun con supuestos distintos."
- **media**: "el sentido del cambio es probable, pero su tamaño es incierto."
- **baja**: "los datos no permiten afirmar el sentido del cambio con seguridad."

### 14.4 Motivos de `sin_datos` (heredados, con una fila nueva)

| código | texto |
|---|---|
| rural | AGEB rural: el censo no publica datos de población infantil por AGEB rural. |
| suprimido_inegi | El INEGI no publica esta cifra para proteger la confidencialidad. |
| poblacion_menor_20 | Hay menos de 20 niñas y niños: la cifra es demasiado pequeña para pronosticar. |
| sin_poligono / sin_censo | Esta clave no tiene correspondencia entre el mapa y el censo. |
| sin_establecimientos | No hay establecimientos registrados en ningún levantamiento, para esta rama y estos filtros. |
| rama_sin_dato | Esta rama no tiene información suficiente en esta zona. |
| (ausente) | No hay estimación para esta unidad. |

### 14.5 Estados

Ver §15.

### 14.6 Metodología: qué mide esta herramienta (reemplaza y amplía a la versión anterior)

**Qué mide Habitancia.** Identifica zonas de la Ciudad de México donde, de acuerdo con la
evolución de la población infantil y adolescente y la disponibilidad de servicios en cuatro ramas
(educación y cultura, salud, comercio, áreas verdes y espacio público), podría existir una mayor
oportunidad relativa de ampliar o fortalecer infraestructura para infancias.

**Población objetivo y oferta.** La *población objetivo* es el número de niñas, niños o
adolescentes del rango de edad elegido que viven en cada zona. La *oferta* de cada rama es el
número de establecimientos o espacios de ese tipo registrados en fuentes oficiales. Son cosas
distintas: que la población baje no implica que la oferta deba bajar, y viceversa.

**Oportunidad relativa, no una certeza.** Indica qué tan prioritaria aparece una zona frente a
otras, bajo los criterios que elegiste — no que sea obligatorio abrir un negocio ahí, ni que exista
una necesidad de mercado comprobada, ni que el modelo esté recomendando una inversión.

**De dónde vienen los datos.**
- Censos de Población y Vivienda 2010 y 2020 del INEGI, por AGEB urbana.
- Proyecciones de población por municipio del Consejo Nacional de Población (CONAPO).
- DENUE (INEGI): educación, salud y comercio, varios levantamientos entre 2016 y 2026.
- Áreas verdes y espacio público: Datos Abiertos de la Ciudad de México.
- Marco Geoestadístico 2020 del INEGI.

**Cómo se decide si una zona tiene mayor oportunidad relativa.** Para cada rama se compara la
oferta proyectada con la población objetivo proyectada, y se ordena esa relación entre todas las
zonas de la CDMX: las zonas con menor cobertura relativa quedan arriba del ranking. Los pesos que
elegiste combinan las cuatro ramas en un solo orden; los filtros deciden qué establecimientos
cuentan en cada rama. Ninguno de los dos cambia los datos originales.

**Qué tan bien acertó el modelo en el pasado.** *(placeholder hasta que exista `backtest.json`,
`correccion/action_plan.md` Fase 2)* Se probó el método comparando lo que habría predicho en el
pasado contra lo que realmente ocurrió después, y contra la opción de "suponer que nada cambia".
{cifras exactas aquí una vez que existan}.

**AGEB rurales y sin datos.** El censo no publica la población infantil por AGEB rural, así que se
muestran como "Sin datos". Nunca se inventa un valor donde falta información — y la ausencia de
datos nunca significa ausencia de necesidad.

**El levantamiento del DENUE de 2024.** Entre 2020 y 2023 el DENUE casi no se actualizó en campo;
al volver en 2024 registró de golpe varios cierres acumulados en esos años, sobre todo en
preescolares y guarderías privadas. Por eso la rama de educación tiene su confianza máxima limitada.
Se trata como una hipótesis razonable, no como un hecho comprobado.

**Advertencias.**
- Las proyecciones son estimaciones condicionadas a los datos y escenarios usados, no certezas.
- Una asociación histórica no implica causalidad.
- La ausencia de datos no equivale a ausencia de necesidad.
- Un establecimiento registrado no mide su capacidad, calidad ni matrícula.
- Datos generados el {generado}.

### 14.7 Advertencia de sesgos (nueva, `rubrica.md` §8)

Sección propia dentro del drawer, visible sin tener que buscarla: **"Habitancia describe tendencias
y disponibilidad relativa, no recomienda dónde vivir ni garantiza éxito comercial. Reconocemos
sesgos posibles: los datos disponibles no cubren igual todas las zonas, y usar esta herramienta para
decidir dónde invertir o vivir sin considerar otros factores (seguridad, vivienda, movilidad,
precios) podría reforzar exclusión existente en vez de reducirla."**

## 15. Estados

Hereda la tabla de 7 estados de la versión anterior (§15: carga inicial, error, capa/alcaldía sin
datos, AGEB sin datos, datos incompletos, AGEB cargándose, horizonte no disponible), con textos
adaptados al vocabulario de Habitancia (zona/rama/oportunidad en vez de AGEB/capa/veredicto) y dos
estados nuevos:

| # | estado | diseño | texto |
|---|---|---|---|
| 8 | Rama sin dato en la vista general | esa rama se excluye del índice compuesto para esa zona, renormalizando pesos (`docs/metodologia.md` §10.3); no se oculta la zona | indicador en la ficha: "Esta rama no tiene datos suficientes en esta zona; el resultado usa las demás." |
| 9 | Todas las ramas sin dato | la zona completa es `sin_datos` en la vista general | "En esta zona no hay información suficiente en ninguna de las cuatro ramas." |

## 16. Rendimiento y criterios de aceptación

### 16.1 Presupuesto

Igual que la versión anterior en la parte estática (HTML+CSS+JS propios ≤ 45 kB gzip, d3 vendor
≤ 40 kB, Inter ≤ 110 kB, `alcaldias.geojson` ≤ 60 kB, `ageb_cdmx_simplificado.geojson` ~420 kB
gzip, diferido). **Nuevo**: `prediccion_ageb.json` con capas por rama y celda de filtro pesa más
que la versión de dos capas — presupuesto ampliado a **≤ 600 kB gzip**, diferido igual que el
GeoJSON de AGEB (primer hover con intención o reposo). El **motor de composición cliente** (§17.4)
debe recalcular oportunidad/disponibilidad e índice compuesto para las 2 453 AGEB en **< 80 ms** al
mover un peso o un filtro (medido con `performance.now()`), para que el recoloreado del mapa se
sienta instantáneo.

### 16.2 Checklist de aceptación (añade a la lista heredada de la versión anterior)

- [ ] Sin peticiones a dominios externos; sin errores ni avisos en consola; Lighthouse
      accesibilidad ≥ 95, rendimiento ≥ 90.
- [ ] Ninguna tarea larga > 200 ms al enfocar cualquiera de las 16 alcaldías (medido con
      `PerformanceObserver`, no estimado — `correccion/action_plan.md` §8.2 punto 46).
- [ ] Mover un peso o un filtro recolorea el mapa y reordena el ranking en < 80 ms, sin red.
- [ ] El caso de uso de jueces (`correccion/frontend_requisitos.md` §24) se completa sin recargar
      la página: población 6–11, horizonte 3 años, oportunidad de expansión, educación y salud en
      alta prioridad, filtros de primaria pública + hospitales/clínicas + comercio de primera
      necesidad + áreas verdes recreativas → mapa y ranking se actualizan → abrir zona → Nivel 1 →
      "Entender esta zona" → gráficas → comparar dos alcaldías.
- [ ] Ningún componente genera una frase interpretativa dinámica en tiempo de ejecución (auditoría
      manual de `frontend/js/*.js`: toda cadena visible sale de `textos.js` o es un valor/cifra).
- [ ] Los 26 puntos de `correccion/frontend_requisitos.md` §26 ("resultado funcional esperado")
      son verificables uno por uno con el frontend real.
- [ ] `sin_datos` se distingue sin color (hachurado + etiqueta). La confianza baja se distingue sin
      color (punteado). Con simulación de deuteranopía/protanopía/tritanopía, los tres terciles de
      §4.2 y la escala de tendencia de §4.3 siguen siendo distinguibles.
- [ ] Todos los flujos se completan solo con teclado; el foco se gestiona según §13.
- [ ] Ningún `innerHTML` con datos; sin `!important`; sin estilos en línea.

## 17. Contrato de datos y motor de composición cliente

Este contrato ya no es una "petición al backend a futuro": es el diseño acordado del contrato
**v1.4**, especificado en `docs/metodologia.md` §10 y `plans/backend_plan.md` (tareas B16, B22,
B17). Se documenta aquí la mitad que le toca al frontend: cómo se consume y qué calcula el
**motor de composición cliente** (`frontend/js/composicion.js`, tarea F-nueva en
`plans/frontend_plan.md`).

### 17.1 Por qué el cálculo final se mueve al cliente

`correccion/frontend_requisitos.md` §9, §21: los pesos y los filtros **no alteran los datos
originales**, y el frontend debe **actualizarse en tiempo real** al moverlos. Un índice compuesto
que dependiera de pesos elegidos por el usuario no puede vivir precalculado en el backend —
tendría que recalcularse en el servidor en cada movimiento del control, lo que rompe "sin recargar
la página" (`correccion/frontend_requisitos.md` §22). Por eso el backend publica los
**ingredientes** por rama y por celda de filtro, y el cliente los combina.

### 17.2 Forma del contrato v1.4 (resumen; detalle exacto en `plans/backend_plan.md` §7)

```json
{"version":"1.4","generado":"ISO-8601","fecha_base":"2026-06",
 "horizontes":[{"clave":"h1","anios":1,"fecha":"2027-06"},
               {"clave":"h3","anios":3,"fecha":"2029-06"},
               {"clave":"h5","anios":5,"fecha":"2031-06"}],
 "capas":{
  "demanda":{"<CVEGEO>":{"cve_mun":"003","segmentos":{
     "todas":{"n_obs":2,"motivo_sin_datos":null,"serie":{...},"nivel_base":912,
              "h":{"h1":{...},"h3":{...},"h5":{...}}},
     "primera_infancia":{...}, "preescolar":{...}, "primaria":{...},
     "secundaria":{...}, "adolescencia":{...}}}},
  "ramas":{
   "educacion":{"<CVEGEO>":{"cve_mun":"003","celdas":{
      "primaria__publico":{"n_obs":3,"serie":{...},"nivel_base":4,
        "horizontes_disponibles":["h1","h3"],
        "h":{"h1":{...},"h3":{...}}},
      "primaria__privado":{...}, "preescolar__publico":{...}, "...":{...}}}},
   "salud":{"<CVEGEO>":{"celdas":{"hospital__publico":{...}, "...":{...}}}},
   "comercio":{"<CVEGEO>":{"celdas":{"primera_necesidad":{...}, "...":{...}}}},
   "verde":{"<CVEGEO>":{"celdas":{"areas_verdes_recreativas":{"nivel_base":1200,
      "unidad":"m2"}, "cobertura_verde":{...}, "espacio_publico":{...}}}}
  }}}
```

- `prediccion_alcaldia.json` usa el mismo esquema por `CVE_MUN`, más `distribucion_ageb` (ahora por
  tercil de oportunidad, no por veredicto) y `agregado_cdmx` en la raíz.
- Un registro `sin_datos`: `h.hX = null` por horizonte inaplicable, `motivo_sin_datos` con código de
  §14.4, `confianza: "baja"`, `n_obs` real — nunca se omite (regla heredada del contrato v1.1/v1.2).
- **`capas.oferta` y `capas.brecha` ya no existen** en v1.4. `capas.demanda` reemplaza a la única
  entrada `total` por seis entradas de segmento (§5.3); `capas.ramas` reemplaza a `capas.oferta`.

### 17.3 Celdas de filtro por rama

Detalle exacto de qué SCIAN/subcategoría compone cada `clave_celda`: `docs/metodologia.md` §10.6 y
`plans/backend_plan.md` tarea B22. Resumen operativo para el frontend — el nombre de cada celda
combina `{nivel_o_tipo}__{sector}` (sin sector para comercio y verde):

| rama | celdas (nivel/tipo) | sector | horizontes |
|---|---|---|---|
| Educación | guarderia, preescolar, primaria, secundaria, media_superior, educacion_especial, recreacion_cultural | publico, privado | h1, h3 |
| Salud | clinica_consultorio, hospital, salud_mental, farmacia | publico, privado | h1, h3 |
| Comercio | primera_necesidad, supermercado, abarrotes, frutas_verduras, carnes_alimentos, farmacia | — | h1, h3 |
| Verde | areas_verdes_recreativas, cobertura_verde, espacio_publico | — | sin horizonte, solo `nivel_base` |

Los filtros de §10.11 se traducen a un conjunto de claves de celda; "Todos" en un filtro selecciona
todas las celdas de esa fila.

### 17.4 Motor de composición cliente (`frontend/js/composicion.js`)

Implementa exactamente las fórmulas de `docs/metodologia.md` §10, sin reinterpretarlas — este
documento no las repite para no mantener dos copias:

1. **Suma de celdas seleccionadas** (metodología §10.6): `Ŝ_{i,h,r}(filtro) = Σ Ŝ_{i,h,c}`,
   `var(Ŝ) = Σ var(Ŝ_c)` (independencia aproximada, documentada).
2. **Cobertura** (metodología §10.1): `cobertura_{i,h,r} = Ŝ_{i,h,r}(filtro) / D̂_{i,h,seg} × 1000`.
   `Ŝ=0` con `D̂>0` es un valor válido, nunca se convierte en `sin_datos` en el cliente tampoco.
3. **Índice de oportunidad por rama** (metodología §10.2): percentil inverso (rango fraccionario,
   empates promediados) + ajuste de tendencia acotado ±0.15 con `K=5` — calculado sobre las 2 453
   AGEB del universo activo (mismo segmento/horizonte/vista territorial), en el cliente, cada vez
   que cambian filtro u horizonte.
4. **Índice compuesto** (metodología §10.3): `IC_{i,h} = Σ w_r·O_{i,h,r} / Σ w_r` sobre ramas con
   dato, recalculado cada vez que se mueve un peso — **sin volver a tocar §3**, porque los `O_{i,h,r}`
   ya están calculados.
5. **Índice de disponibilidad** (metodología §10.5): mismo motor, orientación inversa —
   `F_{i,h,r} = rango_percentil(cobertura) + ajuste_estabilidad`, sin mezclarse nunca con `O_{i,h,r}`.

**Rendimiento** (ver §16.1): pasos 1-2 son sumas y divisiones sobre arreglos tipados
(`Float64Array`), paso 3 es un `sort`+rango por universo activo (≤ 2 453 elementos), paso 4 es una
combinación lineal — todo cabe en el presupuesto de 80 ms en cualquier portátil de gama media.

### 17.5 Pruebas del motor de composición

`frontend/tests/pruebas_composicion.js`: fixtures con `Ŝ=0`/`D̂>0` (debe dar percentil máximo, nunca
`sin_datos`); fixtures con una rama `sin_datos` (el índice compuesto debe renormalizar sobre las
demás, no tratar la ausente como 0); invariante de que `O` e `IC` nunca salen de `[0,1]`; invariante
de que mover un peso no cambia ningún `O_{i,h,r}` (solo `IC_{i,h}`).

## 18. Decisiones abiertas

1. **[RESUELTO] Horizontes.** 1/3/5 años desde `fecha_base = 2026-06`; `delta_pct`/`ic95` medidos
   desde `fecha_base`. Contrato `version 1.4`.
2. **[RESUELTO] Ramas sin proyección a 5 años.** Educación, salud y comercio reportan `h1`/`h3`
   solamente; verde no reporta horizontes. El slider se comunica en consecuencia (§8).
3. **[DECISIÓN DEL EQUIPO] Constante `K` del ajuste de tendencia** (metodología §10.2, `K=5`
   pp/año por omisión, no expuesta al usuario). ¿Se recalibra con el backtest de oferta una vez
   disponible (`plans/backend_plan.md` pregunta B8), o se deja fija para esta entrega?
4. **[DECISIÓN DEL EQUIPO] Nombre del producto y créditos institucionales**: logotipos,
   instituciones participantes y licencia de datos en el pie. Si hay logotipos, en monocromo y
   ≤ 20 px de alto.
5. **[DECISIÓN DEL EQUIPO] Denominador de la rama comercio.** `correccion/frontend_requisitos.md`
   §17 dice literal "la cobertura relaciona los servicios disponibles con el tamaño de la población
   objetivo" para todas las ramas, incluido comercio — aunque el comercio de primera necesidad sirve
   a toda la población, no solo a la infantil. ¿Se sigue el texto literal (denominador = población
   objetivo elegida, consistente entre ramas) o se usa población total para comercio? Recomendación:
   seguir el texto literal — es lo que dice el documento vinculante, y mantiene una sola fórmula de
   cobertura para las cuatro ramas, más fácil de explicar con un solo icono "?".
6. **[DECISIÓN DEL EQUIPO] Top N del ranking en vista general.** ¿20 zonas por omisión (heredado de
   `correccion/action_plan.md`) o un número distinto? No lo fija `frontend_requisitos.md`.
