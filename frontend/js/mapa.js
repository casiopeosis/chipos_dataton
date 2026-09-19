// frontend/js/mapa.js
//
// Mapa D3 (plans/frontend_plan.md → F65/F70; plans/frontend_specs.md §3, §10.1–§10.3, §10.7).
// Este archivo cubre F65: SOLO la vista general (16 alcaldías). F70 continúa este mismo
// archivo, EN SERIE, para añadir: el gesto de foco de 820 ms (§10.2), la vista de alcaldía con
// AGEB y zoom acotado (§10.3) y la transición inversa (§10.7). Por eso:
//   - las 6 capas SVG de §3 se crean todas desde ahora, en el orden exacto del spec, aunque
//     `g.alcaldias-fondo`, `g.agebs` y `g.confianza-baja` queden vacías hasta F70;
//   - la proyección, el generador de rutas y los grupos se devuelven en `_interno` para que F70
//     no tenga que volver a montar el SVG ni re-consultar el DOM;
//   - no se importa `zoom` del vendor de D3: esta vista es de encuadre fijo (spec §3 "Zoom
//     libre... Desactivado en la vista general"); F70 es quien lo añade para la vista de alcaldía.
//
// Seguridad (CLAUDE.md, spec §3): nada de `innerHTML`; todo nodo con datos se crea con
// `dom.js`/D3 (`.attr`, `.text` sobre nodos ya creados, nunca un parser de HTML).

import { geoMercator, geoPath, select, zoom, zoomIdentity } from "../vendor/d3/d3-chipos.esm.js";
import { crear, limpiar, fijarEstilo } from "./dom.js";
import { texto as cadena, textos } from "./textos.js";
import { ACCIONES, despachar, suscribir, obtenerEstado, VISTA } from "./estado.js";

// ---------------------------------------------------------------------------------------------
// Constantes de dibujo. Los valores de movimiento (duración/easing del hover) NO viven aquí:
// se expresan en `mapa.css` con `var(--d-xs)`/`var(--ease-salida)` (tokens.css), tal como pide
// la tarea F65. Los siguientes SÍ son literales a propósito porque el spec los fija como medidas
// de diseño exactas, no como parte de la escala de movimiento ni de espaciado:
// -  32  px de margen de la proyección (spec §3: "fitExtent()... con 32 px de margen").
// - 150  ms de debounce de resize (spec §3: "se recalcula al redimensionar, con 150 ms de
//   debounce, sin animación").
// -  12  px de desplazamiento del tooltip respecto al puntero (spec §10.1).
const MARGEN_PROYECCION_PX = 32;
const DEBOUNCE_RESIZE_MS = 150;
const DESPLAZAMIENTO_TOOLTIP_PX = 12;

// --- F70: transición de foco/inversa y zoom de la vista de alcaldía (spec §10.2-§10.3, §10.7). ---
// 820 ms es el valor exacto que fija el spec para el gesto de foco (y su inverso); no forma parte
// de la escala `--d-*` de tokens.css porque es una medida de diseño puntual de esta transición,
// igual que el resto de literales de este archivo (ver comentario de cabecera).
const DURACION_ENFOQUE_MS = 820;
// `scaleExtent [k, 6k]` (spec §10.3): k = 1 porque el zoom del usuario se aplica ENCIMA de la
// transformación de encuadre de la alcaldía (que ya hizo su propio "zoom" al reproyectar), así
// que 1 es "tal como quedó encuadrada" y 6 es el límite superior pedido por el spec.
const ZOOM_ESCALA_MINIMA = 1;
const ZOOM_ESCALA_MAXIMA = 6;

// Umbrales de intensidad de la paleta de veredictos (spec §4.2: "la intensidad codifica la
// magnitud de la tasa anual"). Los mismos cortes que la leyenda (2 %/año y 3.5 %/año, tope).
function nivelIntensidad(tasaAnualPct) {
  const magnitud = Math.abs(typeof tasaAnualPct === "number" ? tasaAnualPct : 0);
  if (magnitud >= 3.5) return 3;
  if (magnitud >= 2) return 2;
  return 1;
}

/**
 * Clase CSS de relleno para un registro adaptado de una capa (`{veredicto, tasa_anual_pct, ...}`
 * o `null`). Nunca decide colores aquí: solo nombra la clase; `mapa.css` es la única fuente de
 * los valores de color (spec §4: "no se usan colores literales fuera de tokens.css").
 */
function claseVeredicto(registro) {
  const veredicto = registro?.veredicto ?? "sin_datos";
  if (veredicto === "sube") return `mapa__alcaldia--sube-${nivelIntensidad(registro.tasa_anual_pct)}`;
  if (veredicto === "baja") return `mapa__alcaldia--baja-${nivelIntensidad(registro.tasa_anual_pct)}`;
  if (veredicto === "se_mantiene") return "mapa__alcaldia--mantiene";
  return "mapa__alcaldia--sin-datos";
}

function obtenerRegistroCveMun(registrosPorCveMun, cveMun) {
  if (registrosPorCveMun instanceof Map) return registrosPorCveMun.get(cveMun) ?? null;
  if (registrosPorCveMun && typeof registrosPorCveMun === "object") {
    return registrosPorCveMun[cveMun] ?? null;
  }
  return null;
}

// ---------------------------------------------------------------------------------------------
// Contorno exterior de la CDMX (spec §10.1). No hay geometría de unión de polígonos entre los
// módulos vendorizados (§3 no incluye d3-geo-voronoi ni topojson), así que se calcula por conteo
// de aristas: toda arista que solo aparece una vez entre las 16 alcaldías es exterior; la que se
// repite (compartida entre dos vecinas) es interior y se descarta. El resultado es un conjunto de
// segmentos sueltos (no un anillo cerrado), suficiente para un trazo: se dibujan como comandos
// "M...L..." independientes en un único <path>.
// ---------------------------------------------------------------------------------------------

function anillosDeGeometria(geometria) {
  if (!geometria) return [];
  if (geometria.type === "Polygon") return geometria.coordinates;
  if (geometria.type === "MultiPolygon") return geometria.coordinates.flat(1);
  return [];
}

function calcularSegmentosExteriores(coleccion) {
  const conteoPorArista = new Map();
  const puntosPorArista = new Map();
  const clavePunto = (punto) => `${punto[0].toFixed(6)},${punto[1].toFixed(6)}`;

  for (const feature of coleccion?.features ?? []) {
    for (const anillo of anillosDeGeometria(feature.geometry)) {
      for (let i = 0; i < anillo.length - 1; i += 1) {
        const a = anillo[i];
        const b = anillo[i + 1];
        const claveA = clavePunto(a);
        const claveB = clavePunto(b);
        const clave = claveA < claveB ? `${claveA}|${claveB}` : `${claveB}|${claveA}`;
        conteoPorArista.set(clave, (conteoPorArista.get(clave) ?? 0) + 1);
        if (!puntosPorArista.has(clave)) puntosPorArista.set(clave, [a, b]);
      }
    }
  }

  const segmentos = [];
  for (const [clave, veces] of conteoPorArista) {
    if (veces === 1) segmentos.push(puntosPorArista.get(clave));
  }
  return segmentos;
}

function trazarSegmentosProyectados(segmentos, proyeccion) {
  let d = "";
  for (const [a, b] of segmentos) {
    const pa = proyeccion(a);
    const pb = proyeccion(b);
    if (!pa || !pb) continue;
    d += `M${pa[0]},${pa[1]}L${pb[0]},${pb[1]}`;
  }
  return d;
}

// ---------------------------------------------------------------------------------------------
// Montaje
// ---------------------------------------------------------------------------------------------

/**
 * Monta el mapa D3 de vista general (16 alcaldías) dentro de `contenedor`.
 *
 * No asume ningún `id` fijo de `index.html`: el layout (F25) puede construirse en paralelo, así
 * que quien llame a `montarMapa` decide qué elemento le pertenece al mapa.
 *
 * @param {Element} contenedor - elemento donde se monta el `<svg>` y el tooltip. Se limpia con
 *   `dom.js#limpiar` (nunca `innerHTML`) antes de montar.
 * @param {GeoJSON.FeatureCollection} alcaldiasGeoJSON - `data/reference/alcaldias.geojson`
 *   (propiedades `cve_alc`, `nombre`; ver `docs/perfil_datos.md`).
 * @param {Map<string, {demanda: object|null, oferta: object|null}>|Object} registrosPorCveMun -
 *   registros adaptados por alcaldía, indexados por `cve_alc`/`cve_mun` de 3 dígitos. Coincide
 *   exactamente con `datosAdaptados.indices.porCveMun` que produce `api.js#adaptarV11aV12` para
 *   el nivel "alcaldia": cada entrada es `{demanda: registroFlat|null, oferta: registroFlat|null}`
 *   y cada `registroFlat` trae `{veredicto, delta_pct, tasa_anual_pct, ic95, confianza, n_obs}`.
 * @param {object} [opciones]
 * @param {GeoJSON.FeatureCollection|null} [opciones.agebGeoJSON] -
 *   `data/reference/ageb_cdmx_simplificado.geojson` (propiedades `cvegeo`, `cve_mun`, `ambito`);
 *   puede llegar después con `actualizarAgeb` (carga diferida/prefetch, spec §10.2).
 * @param {Map<string, {demanda: object|null, oferta: object|null}>|Object} [opciones.registrosAgebPorCvegeo]
 *   mismo formato que `registrosPorCveMun` pero indexado por `CVEGEO` (13 dígitos).
 * @returns {{
 *   actualizarRegistros(nuevo: Map|Object): void,
 *   actualizarAgeb(agebGeoJSON: GeoJSON.FeatureCollection, registrosAgebPorCvegeo: Map|Object): void,
 *   destruir(): void,
 *   _interno: object,
 * }}
 */
export function montarMapa(contenedor, alcaldiasGeoJSON, registrosPorCveMun, opciones = {}) {
  if (!(contenedor instanceof Element)) {
    throw new TypeError("montarMapa: contenedor debe ser un elemento del DOM");
  }

  let registros = registrosPorCveMun;
  let capaActiva = obtenerEstado().capa;
  let agebGeoJSON = opciones.agebGeoJSON ?? null;
  let registrosAgeb = opciones.registrosAgebPorCvegeo ?? new Map();
  let cveMunEnfocado = null;
  let transformEnfoque = { escala: 1, tx: 0, ty: 0 };
  let comportamientoZoom = null;
  let botonReencuadrar = null;
  let tooltipAgebFeature = null;

  limpiar(contenedor);
  contenedor.classList.add("mapa");

  const segmentosExteriores = calcularSegmentosExteriores(alcaldiasGeoJSON);
  const proyeccion = geoMercator();
  const generadorRuta = geoPath(proyeccion);

  // El SVG es decorativo de cara a lectores de pantalla: la tabla (F40) y la lista de AGEB
  // (F45) son la alternativa completa por teclado (plan §8, riesgo "foco en <path> no uniforme
  // entre navegadores"), así que el mapa se oculta del árbol de accesibilidad.
  const svg = select(contenedor)
    .append("svg")
    .attr("class", "mapa__lienzo")
    .attr("aria-hidden", "true")
    .attr("focusable", "false");

  // --- defs: patrón de hachurado de "sin_datos" (spec §4.2: "líneas a 45°, 1 px, cada 6 px"). ---
  const defs = svg.append("defs");
  const patron = defs
    .append("pattern")
    .attr("id", "mapa-patron-sin-datos")
    .attr("width", 6)
    .attr("height", 6)
    .attr("patternUnits", "userSpaceOnUse")
    .attr("patternTransform", "rotate(45)");
  patron.append("rect").attr("class", "mapa__hachura-fondo").attr("width", 6).attr("height", 6);
  patron.append("line").attr("class", "mapa__hachura-linea").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 6);

  // --- Capas SVG, de abajo arriba, en el orden exacto de la spec §3. ---
  const gFondo = svg.append("g").attr("class", "alcaldias-fondo"); // F70: silueta de vecinas
  const gAgebs = svg.append("g").attr("class", "agebs"); // F70: polígonos AGEB en foco
  const gConfianzaBaja = svg.append("g").attr("class", "confianza-baja"); // F70: punteado sobre AGEB
  const gAlcaldias = svg.append("g").attr("class", "alcaldias"); // esta tarea: 16 alcaldías
  const gRealce = svg.append("g").attr("class", "realce"); // hover/foco

  let rutaContornoExterior = null;
  let featureConHover = null;
  let sombraHover = null;
  let contornoHover = null;
  let tooltipEl = null;

  function medidasContenedor() {
    const rect = contenedor.getBoundingClientRect();
    return {
      ancho: rect.width > 0 ? rect.width : 800,
      alto: rect.height > 0 ? rect.height : 600,
    };
  }

  function claseFeature(feature, capa) {
    const registro = obtenerRegistroCveMun(registros, feature.properties.cve_alc);
    return claseVeredicto(registro?.[capa] ?? null);
  }

  function actualizarClases(capa) {
    gAlcaldias
      .selectAll("path.mapa__alcaldia")
      .attr("class", (feature) => `mapa__alcaldia ${claseFeature(feature, capa)}`)
      .classed("mapa__alcaldia--recesivo", (feature) => cveMunEnfocado !== null && feature.properties.cve_alc !== cveMunEnfocado);
    gAgebs
      .selectAll("path.mapa__ageb")
      .attr("class", (feature) => `mapa__ageb ${claseFeatureAgeb(feature, capa)}`);
  }

  function crearTooltip() {
    tooltipEl = crear("div", { clase: "mapa__tooltip" }, []);
    contenedor.appendChild(tooltipEl);
  }

  function posicionarTooltip(evento) {
    if (!tooltipEl) return;
    const rectContenedor = contenedor.getBoundingClientRect();
    const rectTooltip = tooltipEl.getBoundingClientRect();
    let x = evento.clientX - rectContenedor.left + DESPLAZAMIENTO_TOOLTIP_PX;
    let y = evento.clientY - rectContenedor.top + DESPLAZAMIENTO_TOOLTIP_PX;
    // "se voltea si toca un borde" (spec §10.1).
    if (x + rectTooltip.width > rectContenedor.width) {
      x = evento.clientX - rectContenedor.left - DESPLAZAMIENTO_TOOLTIP_PX - rectTooltip.width;
    }
    if (y + rectTooltip.height > rectContenedor.height) {
      y = evento.clientY - rectContenedor.top - DESPLAZAMIENTO_TOOLTIP_PX - rectTooltip.height;
    }
    // `fijarEstilo` (Web Animations API) en vez de `tooltipEl.style.left/top`: la CSP del
    // proyecto (`style-src 'self'`) bloquea cualquier escritura al atributo `style` desde JS.
    fijarEstilo(tooltipEl, { left: `${x}px`, top: `${y}px` });
  }

  function mostrarTooltip(evento, feature) {
    if (!tooltipEl) crearTooltip();
    const registro = obtenerRegistroCveMun(registros, feature.properties.cve_alc);
    const veredicto = registro?.[capaActiva]?.veredicto ?? "sin_datos";
    limpiar(tooltipEl);
    tooltipEl.appendChild(crear("p", { clase: "mapa__tooltip-nombre" }, [feature.properties.nombre]));
    tooltipEl.appendChild(
      crear("p", { clase: "mapa__tooltip-veredicto" }, [
        cadena("tooltip.capaVeredicto", {
          capa: textos.capa.nombre[capaActiva] ?? textos.capa.nombre.demanda,
          simbolo: textos.veredicto.simbolo[veredicto],
          veredicto: textos.veredicto.palabra[veredicto],
        }),
      ]),
    );
    tooltipEl.classList.add("mapa__tooltip--visible");
    posicionarTooltip(evento);
  }

  function ocultarTooltip() {
    tooltipEl?.classList.remove("mapa__tooltip--visible");
  }

  // --- Hover: contorno de 2px + "elevación" (spec §10.1: copia del contorno 2px hacia abajo al
  // 15% de --tinta, sin desenfoque; el polígono real sube -1px en Y). Duración/easing SIEMPRE
  // por CSS con var(--d-xs)/var(--ease-salida) (mapa.css), nunca un valor propio en JS. ---
  function mostrarRealce(feature) {
    const d = generadorRuta(feature);
    if (!sombraHover) sombraHover = gRealce.append("path").attr("class", "mapa__realce-elevacion");
    if (!contornoHover) contornoHover = gRealce.append("path").attr("class", "mapa__realce-contorno");
    sombraHover.attr("d", d);
    contornoHover.attr("d", d);
    featureConHover = feature;
    gAlcaldias
      .select(`path.mapa__alcaldia[data-cve-mun="${feature.properties.cve_alc}"]`)
      .classed("mapa__alcaldia--elevada", true);
  }

  function ocultarRealce() {
    sombraHover?.remove();
    contornoHover?.remove();
    sombraHover = null;
    contornoHover = null;
    if (featureConHover) {
      gAlcaldias
        .select(`path.mapa__alcaldia[data-cve-mun="${featureConHover.properties.cve_alc}"]`)
        .classed("mapa__alcaldia--elevada", false);
    }
    featureConHover = null;
  }

  function actualizarRealceTrasReproyeccion() {
    if (!featureConHover) return;
    const d = generadorRuta(featureConHover);
    sombraHover?.attr("d", d);
    contornoHover?.attr("d", d);
  }

  function alManejarClic(feature) {
    despachar({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: feature.properties.cve_alc });
  }

  function pintarAlcaldias() {
    gAlcaldias
      .selectAll("path.mapa__alcaldia")
      .data(alcaldiasGeoJSON.features, (feature) => feature.properties.cve_alc)
      .join("path")
      .attr("class", (feature) => `mapa__alcaldia ${claseFeature(feature, capaActiva)}`)
      .attr("data-cve-mun", (feature) => feature.properties.cve_alc)
      .on("mouseenter", (evento, feature) => {
        mostrarRealce(feature);
        mostrarTooltip(evento, feature);
      })
      .on("mousemove", (evento) => posicionarTooltip(evento))
      .on("mouseleave", () => {
        ocultarRealce();
        ocultarTooltip();
      })
      .on("click", (_evento, feature) => alManejarClic(feature));

    rutaContornoExterior = gAlcaldias.append("path").attr("class", "mapa__contorno-exterior").attr("aria-hidden", "true");
  }

  function actualizarGeometria() {
    gAlcaldias.selectAll("path.mapa__alcaldia").attr("d", generadorRuta);
    rutaContornoExterior?.attr("d", trazarSegmentosProyectados(segmentosExteriores, proyeccion));
    actualizarRealceTrasReproyeccion();
  }

  function recalcularProyeccion() {
    const { ancho, alto } = medidasContenedor();
    svg.attr("viewBox", `0 0 ${ancho} ${alto}`).attr("width", ancho).attr("height", alto);
    proyeccion.fitExtent(
      [
        [MARGEN_PROYECCION_PX, MARGEN_PROYECCION_PX],
        [ancho - MARGEN_PROYECCION_PX, alto - MARGEN_PROYECCION_PX],
      ],
      alcaldiasGeoJSON,
    );
    actualizarGeometria();
  }

  // -----------------------------------------------------------------------------------------
  // F70: foco en una alcaldía (AGEB coloreados, vecinas "recesivas"), zoom acotado y transición
  // inversa (spec §10.2-§10.3, §10.7). No se vuelve a llamar `proyeccion.fitExtent()`: se calcula
  // el encuadre de la alcaldía en el espacio YA proyectado (`generadorRuta.bounds`) y se anima
  // como una transformación SVG de grupo — evita recalcular el `d` de cada `<path>` en cada
  // fotograma y hace que el zoom del usuario (d3-zoom) se componga con el mismo mecanismo.
  // -----------------------------------------------------------------------------------------

  function gruposEscenario() {
    return [gFondo, gAlcaldias, gAgebs, gConfianzaBaja];
  }

  function aplicarTransform(t, { animar = false, duracion = DURACION_ENFOQUE_MS } = {}) {
    const cadenaTransform = `translate(${t.tx},${t.ty}) scale(${t.escala})`;
    for (const g of gruposEscenario()) {
      if (animar) g.transition().duration(duracion).attr("transform", cadenaTransform);
      else g.attr("transform", cadenaTransform);
    }
  }

  function claseFeatureAgeb(feature, capa) {
    const registro = obtenerRegistroCveMun(registrosAgeb, feature.properties.cvegeo);
    return claseVeredicto(registro?.[capa] ?? null);
  }

  function crearTooltipAgeb(evento, feature) {
    if (!tooltipEl) crearTooltip();
    const registro = obtenerRegistroCveMun(registrosAgeb, feature.properties.cvegeo);
    const veredicto = registro?.[capaActiva]?.veredicto ?? "sin_datos";
    limpiar(tooltipEl);
    tooltipEl.appendChild(crear("p", { clase: "mapa__tooltip-nombre cifras" }, [feature.properties.cvegeo]));
    tooltipEl.appendChild(
      crear("p", { clase: "mapa__tooltip-veredicto" }, [
        cadena("tooltip.capaVeredicto", {
          capa: textos.capa.nombre[capaActiva] ?? textos.capa.nombre.demanda,
          simbolo: textos.veredicto.simbolo[veredicto],
          veredicto: textos.veredicto.palabra[veredicto],
        }),
      ]),
    );
    tooltipEl.classList.add("mapa__tooltip--visible");
    posicionarTooltip(evento);
  }

  function pintarAgebs() {
    const features = agebGeoJSON?.features?.filter((f) => f.properties.cve_mun === cveMunEnfocado) ?? [];
    gAgebs
      .selectAll("path.mapa__ageb")
      .data(features, (feature) => feature.properties.cvegeo)
      .join("path")
      .attr("class", (feature) => `mapa__ageb ${claseFeatureAgeb(feature, capaActiva)}`)
      .attr("data-cvegeo", (feature) => feature.properties.cvegeo)
      .attr("d", generadorRuta)
      .on("mouseenter", (evento, feature) => {
        tooltipAgebFeature = feature;
        crearTooltipAgeb(evento, feature);
      })
      .on("mousemove", (evento) => posicionarTooltip(evento))
      .on("mouseleave", () => {
        tooltipAgebFeature = null;
        ocultarTooltip();
      })
      .on("click", (_evento, feature) => {
        despachar({ tipo: ACCIONES.IR_A_AGEB, cve_mun: cveMunEnfocado, cvegeo: feature.properties.cvegeo });
      });

    gConfianzaBaja
      .selectAll("path.mapa__ageb-confianza-baja")
      .data(
        features.filter((f) => {
          const r = obtenerRegistroCveMun(registrosAgeb, f.properties.cvegeo);
          return (r?.[capaActiva]?.confianza ?? null) === "baja";
        }),
        (feature) => feature.properties.cvegeo,
      )
      .join("path")
      .attr("class", "mapa__ageb-confianza-baja")
      .attr("aria-hidden", "true")
      .attr("d", generadorRuta);
  }

  function limpiarAgebs() {
    gAgebs.selectAll("path.mapa__ageb").remove();
    gConfianzaBaja.selectAll("path.mapa__ageb-confianza-baja").remove();
  }

  function crearBotonReencuadrar() {
    botonReencuadrar = crear(
      "button",
      {
        type: "button",
        clase: "mapa__reencuadrar",
        onclick: () => reencuadrar(),
      },
      [textos.navegacion.reencuadrar],
    );
    contenedor.appendChild(botonReencuadrar);
  }

  function mostrarBotonReencuadrar(visible) {
    if (!botonReencuadrar) crearBotonReencuadrar();
    botonReencuadrar.classList.toggle("mapa__reencuadrar--visible", visible);
  }

  function activarZoomUsuario() {
    if (comportamientoZoom) return;
    comportamientoZoom = zoom()
      .scaleExtent([ZOOM_ESCALA_MINIMA, ZOOM_ESCALA_MAXIMA])
      .on("zoom", (evento) => {
        const t = evento.transform;
        aplicarTransform({
          escala: transformEnfoque.escala * t.k,
          tx: transformEnfoque.tx + t.x,
          ty: transformEnfoque.ty + t.y,
        });
        // Solo gestos con `sourceEvent` (rueda/pellizco/arrastre real) cuentan como paneo manual;
        // el reencuadre programático (`zoom.transform`) no debe volver a mostrar el botón.
        if (evento.sourceEvent) mostrarBotonReencuadrar(true);
      });
    svg.call(comportamientoZoom);
  }

  function desactivarZoomUsuario() {
    if (!comportamientoZoom) return;
    svg.on(".zoom", null);
    comportamientoZoom = null;
    mostrarBotonReencuadrar(false);
  }

  function reencuadrar() {
    if (!comportamientoZoom) return;
    svg.transition().duration(DURACION_ENFOQUE_MS / 2).call(comportamientoZoom.transform, zoomIdentity);
    mostrarBotonReencuadrar(false);
  }

  function calcularTransformEnfoque(feature) {
    const [[x0, y0], [x1, y1]] = generadorRuta.bounds(feature);
    const { ancho, alto } = medidasContenedor();
    const anchoBbox = Math.max(x1 - x0, 1);
    const altoBbox = Math.max(y1 - y0, 1);
    const escala = Math.min(
      (ancho - MARGEN_PROYECCION_PX * 2) / anchoBbox,
      (alto - MARGEN_PROYECCION_PX * 2) / altoBbox,
    );
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    return { escala, tx: ancho / 2 - escala * cx, ty: alto / 2 - escala * cy };
  }

  /** Transición de foco (spec §10.2): recesivo en las vecinas, AGEB de la alcaldía, zoom acotado. */
  function enfocarAlcaldia(cveMun) {
    const feature = alcaldiasGeoJSON.features.find((f) => f.properties.cve_alc === cveMun);
    if (!feature) return;
    cveMunEnfocado = cveMun;
    transformEnfoque = calcularTransformEnfoque(feature);

    gAlcaldias
      .selectAll("path.mapa__alcaldia")
      .classed("mapa__alcaldia--recesivo", (f) => f.properties.cve_alc !== cveMun);
    ocultarRealce();
    ocultarTooltip();

    pintarAgebs();
    aplicarTransform(transformEnfoque, { animar: true });
    activarZoomUsuario();
  }

  /** Transición inversa (spec §10.7): vuelve a la vista general, sin dejar zoom/AGEB residuales. */
  function volverAVistaGeneral() {
    cveMunEnfocado = null;
    desactivarZoomUsuario();
    gAlcaldias.selectAll("path.mapa__alcaldia").classed("mapa__alcaldia--recesivo", false);
    aplicarTransform({ escala: 1, tx: 0, ty: 0 }, { animar: true });
    // La animación de salida de los AGEB es la misma duración que el foco; se quitan del DOM al
    // terminar para no competir con el siguiente `enfocarAlcaldia` si el usuario navega rápido.
    window.setTimeout(() => {
      if (cveMunEnfocado === null) limpiarAgebs();
    }, DURACION_ENFOQUE_MS);
  }

  function sincronizarVista(estado) {
    const enfocando = estado.vista === VISTA.ALCALDIA || estado.vista === VISTA.AGEB;
    if (enfocando && estado.cve_mun !== cveMunEnfocado) {
      enfocarAlcaldia(estado.cve_mun);
    } else if (!enfocando && cveMunEnfocado !== null) {
      volverAVistaGeneral();
    }
  }

  pintarAlcaldias();
  recalcularProyeccion();
  sincronizarVista(obtenerEstado());

  // --- Recálculo debounced a 150 ms en resize (spec §3), sin animación. ---
  let temporizadorResize = null;
  function programarRecalculo() {
    if (temporizadorResize !== null) clearTimeout(temporizadorResize);
    temporizadorResize = setTimeout(() => {
      temporizadorResize = null;
      recalcularProyeccion();
    }, DEBOUNCE_RESIZE_MS);
  }

  let observadorResize = null;
  if (typeof ResizeObserver !== "undefined") {
    observadorResize = new ResizeObserver(() => programarRecalculo());
    observadorResize.observe(contenedor);
  } else if (typeof window !== "undefined") {
    window.addEventListener("resize", programarRecalculo);
  }

  // --- Cambio de capa (§9): solo recolorea (transición de `fill` por CSS), nunca recrea la
  // geometría de los <path>. No hay conmutador de capas todavía (F60), pero el mapa ya queda
  // listo para reaccionar en cuanto exista. ---
  const cancelarSuscripcion = suscribir((estado) => {
    if (estado.capa !== capaActiva) {
      capaActiva = estado.capa;
      actualizarClases(capaActiva);
    }
    sincronizarVista(estado);
  });

  return {
    /** Reemplaza los registros por alcaldía (p. ej. al cambiar de horizonte cuando exista) y recolorea. */
    actualizarRegistros(nuevosRegistros) {
      registros = nuevosRegistros;
      actualizarClases(capaActiva);
    },
    /** Entrega (o reemplaza) el GeoJSON de AGEB y sus registros; recolorea si hay una alcaldía enfocada. */
    actualizarAgeb(nuevoAgebGeoJSON, nuevosRegistrosAgeb) {
      agebGeoJSON = nuevoAgebGeoJSON ?? agebGeoJSON;
      if (nuevosRegistrosAgeb) registrosAgeb = nuevosRegistrosAgeb;
      if (cveMunEnfocado !== null) pintarAgebs();
    },
    /** Libera observadores/listeners/suscripciones y vacía el contenedor. */
    destruir() {
      if (temporizadorResize !== null) clearTimeout(temporizadorResize);
      observadorResize?.disconnect();
      if (typeof window !== "undefined") window.removeEventListener("resize", programarRecalculo);
      desactivarZoomUsuario();
      cancelarSuscripcion();
      tooltipEl?.remove();
      botonReencuadrar?.remove();
      limpiar(contenedor);
      contenedor.classList.remove("mapa");
    },
    _interno: {
      svg,
      defs,
      proyeccion,
      generadorRuta,
      gFondo,
      gAgebs,
      gConfianzaBaja,
      gAlcaldias,
      gRealce,
      segmentosExteriores,
      recalcularProyeccion,
    },
  };
}
