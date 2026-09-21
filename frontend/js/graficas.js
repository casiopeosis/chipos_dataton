// frontend/js/graficas.js
//
// Gráficas de Nivel 2 (plans/frontend_specs.md §10.5, plan F86): histórico + proyección de
// población, oferta por rama y cobertura frente a CDMX. Viven dentro del drawer "Entender esta
// zona" (franja.js), nunca en Nivel 1 (spec: "Nivel 1 no debe saturar con gráficas").
//
// Sin librería de gráficas: el bundle vendorizado (`vendor/d3/d3-chipos.esm.js`) trae
// d3-geo/d3-zoom/d3-selection/etc. para el mapa, pero NO d3-scale ni d3-shape (nunca se
// vendorizaron esos módulos, y añadirlos exigiría regenerar el bundle offline, CLAUDE.md "sin CDN
// en tiempo de ejecución"). Una escala lineal y un generador de línea SVG son un puñado de líneas
// (`escalaLineal`/`rutaLinea` abajo): más simple que ampliar el vendor para esto.
//
// Cada función es pura: recibe datos ya calculados (nunca lee `composicion.js`/`estado.js`
// directamente) y devuelve un `SVGSVGElement` listo para insertar. `franja.js` las invoca.

import { select } from "../vendor/d3/d3-chipos.esm.js";
import { textos } from "./textos.js";

const ANCHO = 280;
const ALTO = 110;
const MARGEN = { arriba: 8, derecha: 8, abajo: 18, izquierda: 34 };

/** Escala lineal mínima: `dominio: [min,max]` -> `rango: [min,max]`, sin dependencias. */
function escalaLineal(dominio, rango) {
  const [d0, d1] = dominio;
  const [r0, r1] = rango;
  const denom = d1 - d0;
  return (v) => (denom === 0 ? (r0 + r1) / 2 : r0 + ((v - d0) / denom) * (r1 - r0));
}

/** Ruta SVG `M...L...` de una serie de puntos `{x,y}` ya proyectados a píxeles. */
function rutaLinea(puntos) {
  if (puntos.length === 0) return "";
  return puntos.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
}

/** Color de tendencia por veredicto + magnitud (tokens.css §4.3, "uso restringido a Nivel 2"). */
function colorTendencia(veredicto, tasaAnualPct) {
  const magnitud = Math.abs(tasaAnualPct ?? 0);
  if (veredicto === "sube") return magnitud >= 3.5 ? "var(--sube-3)" : magnitud >= 2 ? "var(--sube-2)" : "var(--sube-1)";
  if (veredicto === "baja") return magnitud >= 3.5 ? "var(--baja-3)" : magnitud >= 2 ? "var(--baja-2)" : "var(--baja-1)";
  return "var(--mantiene)";
}

function crearLienzo(claseExtra) {
  const svg = select(document.createElementNS("http://www.w3.org/2000/svg", "svg"))
    .attr("viewBox", `0 0 ${ANCHO} ${ALTO}`)
    .attr("class", `grafica__lienzo ${claseExtra}`)
    .attr("role", "img");
  return svg;
}

// -------------------------------------------------------------------------------------------
// A/B) Población: histórico (censo) + proyección al horizonte activo, con banda IC95.
// -------------------------------------------------------------------------------------------

/**
 * @param {object} datos
 * @param {Array<{t: number, valor: number}>} datos.historico - puntos observados (censo 2010/2020).
 * @param {{t: number, valor: number}} datos.base - nivel proyectado a `fecha_base`.
 * @param {{t: number, valor: number, ic95: [number, number], veredicto: string, tasaAnualPct: number}} datos.proyeccion
 * @param {{anioA: string, anioB: string, valorA: string, valorB: string, anioH: string, valorH: string, lo: string, hi: string}} datos.figcaptionValores
 * @returns {SVGSVGElement}
 */
export function graficaPoblacion(datos) {
  const puntos = [...datos.historico, datos.base, datos.proyeccion];
  const valores = puntos.flatMap((p) => (p.ic95 ? [p.valor, ...p.ic95] : [p.valor]));
  const escalaX = escalaLineal([puntos[0].t, datos.proyeccion.t], [MARGEN.izquierda, ANCHO - MARGEN.derecha]);
  const escalaY = escalaLineal([0, Math.max(...valores) * 1.1], [ALTO - MARGEN.abajo, MARGEN.arriba]);

  const svg = crearLienzo("grafica__lienzo--poblacion");

  // Banda IC95 de la proyección (solo un punto: se dibuja como línea vertical con extremos).
  if (datos.proyeccion.ic95) {
    const x = escalaX(datos.proyeccion.t);
    svg.append("line")
      .attr("x1", x).attr("x2", x)
      .attr("y1", escalaY(datos.proyeccion.ic95[0]))
      .attr("y2", escalaY(datos.proyeccion.ic95[1]))
      .attr("class", "grafica__banda");
  }

  // Histórico + base: línea sólida --tinta-2. Proyección: línea discontinua con el color de
  // tendencia (§4.3, restringido a Nivel 2).
  const puntosSolidos = [...datos.historico, datos.base].map((p) => ({ x: escalaX(p.t), y: escalaY(p.valor) }));
  svg.append("path").attr("d", rutaLinea(puntosSolidos)).attr("class", "grafica__linea grafica__linea--historico");

  const puntosProyeccion = [datos.base, datos.proyeccion].map((p) => ({ x: escalaX(p.t), y: escalaY(p.valor) }));
  svg.append("path")
    .attr("d", rutaLinea(puntosProyeccion))
    .attr("class", "grafica__linea grafica__linea--proyeccion")
    .attr("stroke", colorTendencia(datos.proyeccion.veredicto, datos.proyeccion.tasaAnualPct));

  for (const p of puntosSolidos) svg.append("circle").attr("cx", p.x).attr("cy", p.y).attr("r", 2.5).attr("class", "grafica__punto");
  const pFinal = puntosProyeccion[1];
  svg.append("circle").attr("cx", pFinal.x).attr("cy", pFinal.y).attr("r", 3)
    .attr("class", "grafica__punto grafica__punto--proyeccion")
    .attr("fill", colorTendencia(datos.proyeccion.veredicto, datos.proyeccion.tasaAnualPct));

  svg.append("line")
    .attr("x1", MARGEN.izquierda).attr("x2", ANCHO - MARGEN.derecha)
    .attr("y1", ALTO - MARGEN.abajo).attr("y2", ALTO - MARGEN.abajo)
    .attr("class", "grafica__eje");

  svg.append("title").text(textos.graficas.poblacion.figcaption(datos.figcaptionValores));
  return svg.node();
}

// -------------------------------------------------------------------------------------------
// Servicios (oferta) por rama: mismo patrón, sin proyección para verde (§10.1: sin componente
// temporal). Si hay más de una celda seleccionada, el histórico combinado no está definido de
// forma única entre levantamientos irregulares -- se muestra solo nivel base + proyección en ese
// caso (degradación explícita, nunca una suma inventada entre series de distintas fechas).
// -------------------------------------------------------------------------------------------

/**
 * @param {object} datos
 * @param {string} datos.rama
 * @param {Array<{t: number, valor: number}>|null} datos.historico - `null` si hay >1 celda activa.
 * @param {{t: number, valor: number}} datos.base
 * @param {{t: number, valor: number, veredicto: string, tasaAnualPct: number}|null} datos.proyeccion - `null` para verde.
 * @returns {SVGSVGElement}
 */
export function graficaServicios(datos) {
  if (!datos.historico && !datos.proyeccion) {
    // Ni histórico combinable ni proyección (verde con una sola foto): solo el nivel base, como
    // barra única -- no hay nada más honesto que dibujar con los datos disponibles.
    const svg = crearLienzo("grafica__lienzo--servicios");
    const escalaY = escalaLineal([0, Math.max(datos.base.valor, 1) * 1.2], [ALTO - MARGEN.abajo, MARGEN.arriba]);
    svg.append("rect")
      .attr("x", ANCHO / 2 - 20).attr("width", 40)
      .attr("y", escalaY(datos.base.valor)).attr("height", ALTO - MARGEN.abajo - escalaY(datos.base.valor))
      .attr("class", "grafica__barra");
    svg.append("line")
      .attr("x1", MARGEN.izquierda).attr("x2", ANCHO - MARGEN.derecha)
      .attr("y1", ALTO - MARGEN.abajo).attr("y2", ALTO - MARGEN.abajo)
      .attr("class", "grafica__eje");
    return svg.node();
  }

  const puntosConocidos = [...(datos.historico ?? []), datos.base, ...(datos.proyeccion ? [datos.proyeccion] : [])];
  const tMin = puntosConocidos[0].t;
  const tMax = puntosConocidos[puntosConocidos.length - 1].t;
  const escalaX = escalaLineal([tMin, tMax], [MARGEN.izquierda, ANCHO - MARGEN.derecha]);
  const escalaY = escalaLineal([0, Math.max(...puntosConocidos.map((p) => p.valor)) * 1.1 || 1], [ALTO - MARGEN.abajo, MARGEN.arriba]);

  const svg = crearLienzo("grafica__lienzo--servicios");

  const puntosSolidos = [...(datos.historico ?? []), datos.base].map((p) => ({ x: escalaX(p.t), y: escalaY(p.valor) }));
  svg.append("path").attr("d", rutaLinea(puntosSolidos)).attr("class", "grafica__linea grafica__linea--historico");
  for (const p of puntosSolidos) svg.append("circle").attr("cx", p.x).attr("cy", p.y).attr("r", 2.5).attr("class", "grafica__punto");

  if (datos.proyeccion) {
    const puntosProyeccion = [datos.base, datos.proyeccion].map((p) => ({ x: escalaX(p.t), y: escalaY(p.valor) }));
    svg.append("path")
      .attr("d", rutaLinea(puntosProyeccion))
      .attr("class", "grafica__linea grafica__linea--proyeccion")
      .attr("stroke", colorTendencia(datos.proyeccion.veredicto, datos.proyeccion.tasaAnualPct));
    const pFinal = puntosProyeccion[1];
    svg.append("circle").attr("cx", pFinal.x).attr("cy", pFinal.y).attr("r", 3)
      .attr("class", "grafica__punto grafica__punto--proyeccion")
      .attr("fill", colorTendencia(datos.proyeccion.veredicto, datos.proyeccion.tasaAnualPct));
  }

  svg.append("line")
    .attr("x1", MARGEN.izquierda).attr("x2", ANCHO - MARGEN.derecha)
    .attr("y1", ALTO - MARGEN.abajo).attr("y2", ALTO - MARGEN.abajo)
    .attr("class", "grafica__eje");

  return svg.node();
}

// -------------------------------------------------------------------------------------------
// C) Cobertura frente a CDMX: una barra para la zona, una línea de referencia para la CDMX.
// -------------------------------------------------------------------------------------------

/**
 * @param {{coberturaZona: number, coberturaCdmx: number, unidad: string}} datos
 * @returns {SVGSVGElement}
 */
export function graficaCobertura(datos) {
  const svg = crearLienzo("grafica__lienzo--cobertura");
  const maximo = Math.max(datos.coberturaZona, datos.coberturaCdmx, 1) * 1.2;
  const escalaY = escalaLineal([0, maximo], [ALTO - MARGEN.abajo, MARGEN.arriba]);

  const xBarra = ANCHO / 2 - 20;
  svg.append("rect")
    .attr("x", xBarra).attr("width", 40)
    .attr("y", escalaY(datos.coberturaZona)).attr("height", ALTO - MARGEN.abajo - escalaY(datos.coberturaZona))
    .attr("class", "grafica__barra");

  const yReferencia = escalaY(datos.coberturaCdmx);
  svg.append("line")
    .attr("x1", MARGEN.izquierda).attr("x2", ANCHO - MARGEN.derecha)
    .attr("y1", yReferencia).attr("y2", yReferencia)
    .attr("class", "grafica__referencia");
  svg.append("text")
    .attr("x", ANCHO - MARGEN.derecha).attr("y", yReferencia - 3)
    .attr("class", "grafica__referencia-texto").attr("text-anchor", "end")
    .text(textos.graficas.cobertura.referenciaCdmx);

  svg.append("line")
    .attr("x1", MARGEN.izquierda).attr("x2", ANCHO - MARGEN.derecha)
    .attr("y1", ALTO - MARGEN.abajo).attr("y2", ALTO - MARGEN.abajo)
    .attr("class", "grafica__eje");

  return svg.node();
}

