# Plan de frontend

Objetivo: visor web de producción, HTML + CSS + JS vanilla (ES modules), sin build y sin CDN, que
muestre el veredicto de demanda (y la oferta como capa complementaria) por alcaldía y AGEB. Interfaz
única con el backend: `data/outputs/prediccion_ageb.json`, `prediccion_alcaldia.json` (contrato
`version 1.1`, ver CLAUDE.md) y `data/reference/ageb_cdmx_simplificado.geojson` (+ `alcaldias.geojson`).
Mientras el backend no exista se desarrolla contra datos mock con el mismo contrato.

## 1. Arquitectura

```
frontend/
  index.html                  HTML semántico: header, main (mapa + aside panel), footer (fuentes)
  css/
    tokens.css                variables: color, tipografía, espacio, radios, sombras, duración de movimiento
    base.css                  reset mínimo, tipografía, foco visible, utilidades (.visualmente-oculto)
    layout.css                grid principal, responsive (sidebar ↔ hoja inferior)
    mapa.css                  estilos Leaflet sobrescritos, pop, patrones sin_datos
    panel.css · leyenda.css · estados.css
  js/
    main.js                   arranque: carga, cablea módulos, maneja errores globales
    config.js                 rutas de datos, versión de contrato esperada, constantes de UI
    api.js                    fetch + validación ligera del contrato + índices por clave
    estado.js                 almacén observable (sin globales) + sincronía con el hash de la URL
    mapa.js                   Leaflet: capa alcaldías, capa AGEB, pop, flyToBounds, foco
    panel.js                  panel de detalle (alcaldía / AGEB) y lista navegable de AGEB
    leyenda.js                leyenda persistente + conmutador de capa (demanda/oferta)
    graficas.js               SVG a mano: barra de intervalo IC95, barras de reparto por veredicto
    formato.js                números es-MX (Intl), etiquetas de veredicto/confianza, íconos
    dom.js                    helpers seguros: crear(tag, attrs, hijos), textContent, sin innerHTML
  vendor/leaflet/             Leaflet 1.9.4 (leaflet.js, leaflet.css, LICENSE) restaurado de git
  data/                       copia de outputs + geojson (generada por `make frontend-datos`)
  mock/
    generar_mock.py           genera mocks deterministas desde las claves reales del GeoJSON
    prediccion_ageb.json · prediccion_alcaldia.json
  tests/index.html · tests/pruebas.js   pruebas en navegador de funciones puras
```
- Sin D3: las dos gráficas (intervalo y reparto) son SVG simples; evita 90 KB y un vendor más.
  [SPEC PENDIENTE: si la spec pide series temporales o gráficas complejas, vendorizar D3 (módulos
  d3-scale/d3-shape) en `vendor/d3/`.]
- Módulos con interfaz explícita; `estado.js` es la única fuente de verdad:
  `{vista: 'ciudad'|'alcaldia', cve_mun, cvegeo, capa: 'demanda'|'oferta', carga: 'cargando'|'listo'|'error'}`.
  Los módulos se suscriben (`suscribir(fn)`) y emiten acciones (`despachar({tipo, ...})`).
- Hash de URL `#/alcaldia/007/ageb/0900700011234?capa=oferta` → enlaces compartibles y botón "atrás".
- CSP en `<meta>`: `default-src 'self'; img-src 'self' data:; style-src 'self'`; sin estilos en línea
  (Leaflet: estilos de path vía `className`, no `style` inline donde sea posible).

## 2. Carga de datos (`api.js`)
1. Arranque: en paralelo `prediccion_alcaldia.json`, `alcaldias.geojson` (pequeños) → pintar vista ciudad.
2. Justo después (sin bloquear): `prediccion_ageb.json` y `ageb.geojson` (1.51 MB, gzip ~0.4 MB en el
   servidor). Se indexan: `Map<cve_mun, Feature[]>` y `Map<cvegeo, registro>`.
3. Si el usuario hace clic antes de que termine, el panel muestra estado de carga de la alcaldía y la
   animación espera la promesa.
4. Validación ligera: `version === '1.1'` (si no, error "versión de datos incompatible"), veredictos y
   confianza en conjuntos válidos (valores desconocidos → tratados como `sin_datos` y avisados en consola
   una sola vez), clave faltante en JSON → `sin_datos` con etiqueta "sin estimación".
5. Origen: `?mock=1` → `mock/`; por defecto `data/`.

Firmas:
```
cargarResumen() -> Promise<{alcaldias: FeatureCollection, pred: ContratoAlcaldia}>
cargarDetalle() -> Promise<{agebPorMun: Map, predAgeb: Map}>
validarContrato(json, nivel) -> {ok: boolean, errores: string[]}
registroDe(capa, clave) -> Registro   // normaliza faltantes a sin_datos
```

## 3. Flujo de interacción
1. **Vista ciudad:** 16 alcaldías coloreadas por veredicto de la capa activa; tooltip (nombre, veredicto,
   Δ %, confianza); lista accesible de alcaldías en el panel (botones, orden alfabético o por Δ).
2. **Selección** (clic, Enter/Espacio en la lista o en el polígono):
   a. *Pop*: el polígono escala a 1.04 y vuelve (transform en el `<path>` con `transform-box: fill-box`,
      ~180 ms) y sube de nivel (`bringToFront`); las demás alcaldías se atenúan.
   b. `map.flyToBounds(bounds, {padding, duration: 0.8})`.
   c. Al terminar (`moveend`): se construye (o reutiliza de caché) `L.geoJSON` solo con los AGEB de ese
      `cve_mun`, coloreados por veredicto; el borde de la alcaldía queda como contexto.
   d. Panel: resumen de alcaldía + gráfica de reparto + lista de AGEB (buscable por clave).
3. **AGEB:** hover/foco → tooltip; clic/Enter → panel de detalle (veredicto, Δ %, tasa anual, IC95
   gráfico, confianza, n_obs, bloque separado "Oferta (establecimientos DENUE)" con nota de la caída
   2024 y tope de confianza).
4. **Volver:** `Esc`, botón "← Todas las alcaldías" o atrás del navegador → quita capa AGEB,
   `flyToBounds` a la CDMX, restaura foco al botón de la alcaldía de origen.
5. `prefers-reduced-motion`: sin pop, `fitBounds` sin animación, sin transiciones de opacidad.

Accesibilidad del mapa: polígonos con `tabindex="0"`, `role="button"`, `aria-label` ("Iztapalapa: baja,
−14.2 %, confianza alta"); región del mapa `role="region"` con `aria-label`; anuncios en
`aria-live="polite"` al cambiar de vista. La lista del panel es la ruta de teclado principal.

## 4. Rendimiento del GeoJSON AGEB
- Un solo archivo simplificado (1.51 MB < 5 MB) → **no** se parte por alcaldía; TopoJSON no necesario
  (opcional si la medición en 4G lenta supera 3 s de carga del detalle; requeriría vendorizar
  `topojson-client`). [SPEC PENDIENTE: presupuesto de peso/tiempo.]
- Carga diferida tras el primer pintado; `requestIdleCallback` para indexar.
- Filtrado por `cve_mun` en cliente; capa por alcaldía cacheada (máx. ~300 paths en Iztapalapa: SVG
  es suficiente y conserva foco por teclado; no usar canvas).
- `smoothFactor` de Leaflet 1.0; estilos por clase CSS (cambio de capa = cambio de clase, sin recrear).

## 5. Sistema visual
- **Paleta** (tokens en `tokens.css`, significado fijo, verificada para deuteranopía/protanopía):
  `--color-sube` azul (#2166ac), `--color-baja` naranja oscuro (#b35806), `--color-se-mantiene`
  neutro (#d8d2c4), `--color-sin-datos` gris (#bdbdbd) **con patrón de rayas** (SVG `<pattern>`).
  Confianza = luminosidad del mismo tono (alta 100 %, media 70 %, baja 45 % + contorno punteado).
  No depender del color: glifos ▲ (sube) ▼ (baja) ● (se mantiene) ∅ (sin datos) en tooltip, panel,
  lista y leyenda. [SPEC PENDIENTE: colores institucionales.]
- Contraste: texto ≥ 4.5:1; elementos gráficos y bordes ≥ 3:1 contra el fondo del mapa (sin teselas
  base externas; fondo liso `--color-fondo-mapa`, porque las teselas serían CDN en tiempo de ejecución).
- **Tipografía:** pila del sistema (`system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`),
  números tabulares (`font-variant-numeric: tabular-nums`). [SPEC PENDIENTE: fuente de marca
  vendorizada en `vendor/fonts/`.]
- **Leyenda** siempre visible (esquina del mapa en escritorio, barra fija en móvil): 4 veredictos con
  glifo + color + patrón, escala de confianza, capa activa, texto "Horizonte: junio 2027".
- **Responsive:** ≥ 1024 px mapa + panel lateral 380 px; 640–1023 px panel colapsable; < 640 px panel
  como hoja inferior arrastrable por botón (no por gesto obligatorio), leyenda compacta.
- CSS sin `!important` (sobrescrituras de Leaflet con especificidad `.mapa .leaflet-…`); unidades rem.
- Tema oscuro: [SPEC PENDIENTE]; tokens preparados para `prefers-color-scheme`.

## 6. Estados
- **Carga:** esqueleto del panel + indicador en el mapa con `aria-busy="true"`.
- **Error:** mensaje en español con causa (red, versión incompatible, JSON inválido) y botón "Reintentar".
- **Vacío:** alcaldía con todos los AGEB `sin_datos` → mensaje explicativo (rurales / suprimidos por INEGI).
- **Sin JS:** `<noscript>` con texto y enlace a los JSON.

## 7. Datos mock
`frontend/mock/generar_mock.py` (solo biblioteca estándar, semilla fija): lee las propiedades de
`data/reference/ageb_cdmx_simplificado.geojson` (sin geometrías en consola) y escribe los dos JSON del
contrato 1.1 cubriendo: los 4 veredictos, las 3 confianzas, rurales `sin_datos`, campos `null`,
algunas claves **ausentes** del JSON, IC asimétricos, oferta con tope `media`, una alcaldía casi
toda `sin_datos` (para el estado vacío) y un archivo `prediccion_ageb_v9.json` con versión inválida
(estado de error). Los mocks se versionan (pequeños).

## 8. Riesgos y supuestos
- Supuesto: los nombres de alcaldía salen de `alcaldias.geojson` (`nombre`); el contrato no los trae.
- Supuesto: el servidor sirve `frontend/` como raíz (`make serve`); rutas relativas en todo.
- Riesgo: casi todo AGEB saldrá `baja` (N2 del backend) → mapa monocromo; mitigación: la intensidad por
  confianza y Δ % en tooltip/lista dan variación legible. [SPEC PENDIENTE: ¿colorear por Δ % continuo?]
- Riesgo: `transform` en paths SVG de Leaflet se reinicia al hacer zoom → aplicar el pop antes del
  `flyToBounds` y retirarlo en `animationend`.
- Riesgo: foco en paths SVG no funciona igual en Safari → la lista del panel es el camino garantizado.
- Riesgo: sin mapa base (teselas externas prohibidas) falta contexto urbano → contornos de alcaldía
  y etiquetas propias; [SPEC PENDIENTE: teselas vendorizadas/rasters locales].

## 9. Marcadores de spec
Puntos que `plans/frontend_specs.md` puede cambiar: paleta/colores de marca (§5), tipografía (§5),
gráficas adicionales y D3 (§1), presupuesto de rendimiento y TopoJSON (§4), mapa base (§8), tema oscuro
(§5), textos/copys y créditos institucionales (§1 footer), si la brecha oferta/demanda se muestra (§3).

## 10. Tareas

| id | objetivo | archivos | acepta cuando | tam. | depende | paralelo con |
|---|---|---|---|---|---|---|
| F0 | Andamiaje + restaurar Leaflet 1.9.4 | `frontend/index.html`, `vendor/leaflet/*` (desde `git show 928e456~1:src/app/vendor/leaflet/…`) | `make serve` muestra la página vacía sin errores de consola; sin peticiones externas | S | — | — |
| F1 | Tokens y base CSS | `css/tokens.css`, `css/base.css`, `css/layout.css` | contraste de tokens verificado AA; grid responsive a 360/768/1280 px | S | F0 | F2, F3 |
| F2 | Mocks del contrato | `mock/generar_mock.py`, `mock/*.json` | JSON válidos v1.1 con todos los casos de §7; deterministas | M | F0 | F1, F3 |
| F3 | Utilidades puras | `js/dom.js`, `js/formato.js`, `js/config.js`, `tests/*` | pruebas en `tests/index.html` verdes (formato es-MX, etiquetas, saneo) | S | F0 | F1, F2 |
| F4 | Datos y estado | `js/api.js`, `js/estado.js` | carga en dos fases; validación rechaza v9; hash ↔ estado | M | F2, F3 | F5 |
| F5 | Leyenda y conmutador de capa | `js/leyenda.js`, `css/leyenda.css` | leyenda visible en todas las vistas y tamaños; conmutador operable con teclado | S | F1, F3 | F4 |
| F6 | Mapa: vista ciudad | `js/mapa.js`, `css/mapa.css` | 16 alcaldías coloreadas por capa; tooltip; foco por teclado | M | F4, F5 | F8 |
| F7 | Mapa: selección, pop, flyToBounds, AGEB, volver | `js/mapa.js`, `css/mapa.css` | flujo §3 completo; `Esc` y atrás funcionan; reduced-motion sin animación | L | F6 (mismo archivo) | F8 |
| F8 | Panel y gráficas | `js/panel.js`, `js/graficas.js`, `css/panel.css` | detalle alcaldía/AGEB con IC95 y reparto; oferta etiquetada aparte | M | F4 | F6, F7 |
| F9 | Estados carga/error/vacío + orquestación | `js/main.js`, `css/estados.css` | los tres estados reproducibles con mocks; reintentar funciona | S | F4, F6, F8 | — |
| F10 | Pasada de accesibilidad y responsive | `index.html`, `css/*` (ajustes) | teclado completo; `aria-live`; Lighthouse accesibilidad ≥ 90 | M | F7, F9 | — |
| F11 | Enlace con datos reales | `Makefile` (objetivo `frontend-datos` que copia 2 JSON + 2 GeoJSON a `frontend/data/`) | con `data/outputs/` del backend la app carga sin `?mock=1` | S | F9 (y outputs del backend, si existen) | F10 |
| F12 | QA final | — (correcciones puntuales) | sin errores en consola; sin CDN (pestaña red); cumple `frontend_specs.md` | M | F10, F11 | — |

Paralelizables (archivos disjuntos): {F1, F2, F3}; {F4, F5}; {F6/F7 con F8}; {F10, F11}. F6 y F7
comparten `mapa.js`: en serie. F11 es la única tarea que toca un archivo compartido (`Makefile`):
un objetivo nuevo, sin editar los existentes.

## 11. Verificación
`make serve` y abrir `http://localhost:8000/?mock=1`; recorrer flujo §3 con ratón y solo teclado;
emular reduced-motion y 360 px en DevTools; pestaña Red sin dominios externos; Lighthouse ≥ 90;
`tests/index.html` verde; con datos reales tras `make pipeline && make frontend-datos`.

## Preguntas abiertas
1. ¿Se muestra la **brecha** oferta/demanda en el frontend (no está en el contrato 1.1) o solo demanda y oferta?
2. ¿El mapa se colorea por **veredicto** (categórico, como dice CLAUDE.md) o también se ofrece Δ % continuo, dado que casi todo saldrá `baja`?
3. ¿Dónde se publicará (servidor estático propio, GitHub Pages en subruta, USB/offline)? Afecta rutas y compresión.
4. ¿Hay identidad visual obligatoria (logos, colores, tipografía institucional) antes de `frontend_specs.md`?
5. ¿La capa **oferta** va como conmutador del mapa o solo como bloque en el panel de detalle?
