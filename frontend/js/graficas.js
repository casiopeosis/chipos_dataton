// frontend/js/graficas.js
//
// Mini-gráfica SVG de la ficha de AGEB (plans/frontend_specs.md §7.4). SVG de 416×168 px con eje
// de tiempo real (años decimales): puntos censales, tramos, proyección, banda IC95, horizontes
// ◇/◆ y una regla vertical "hoy". Autocontenida y sin dependencias externas (sin D3: el spec pide
// "a mano, sin D3" para este componente).
//
// `js/dom.js` no ofrece helpers de espacio de nombres SVG (todo lo que crea es HTML), así que este
// módulo trae sus propios helpers locales `crearSvg`/`textoSvg` en vez de ampliar `dom.js` — el
// resto del frontend no necesita SVG salvo el mapa (`js/mapa.js`, D3, fuera de este archivo).
//
// **Degradación (spec §7.4).** Con el contrato v1.1 (el único que produce hoy el backend, ver
// CLAUDE.md y plans/frontend_plan.md §2) `serie` SIEMPRE está ausente: `montarGrafica` siempre
// toma la rama de la nota fija de degradación con datos reales. El resto de esta función (puntos,
// tramos, proyección, banda, horizontes) queda listo y se ejercita únicamente con fixtures de
// `serie` ficticias, para el día en que el backend la entregue (plan §3-1).

import { texto as t, textos } from "./textos.js";
import { formatoEntero } from "./formato.js";

const SVG_NS = "http://www.w3.org/2000/svg";

/** Dimensiones fijas del SVG (spec §7.4: "SVG de 416 × 168 px"). */
const ANCHO = 416;
const ALTO = 168;

/** Márgenes del área de trazo, para dejar espacio a los ejes y etiquetas. */
const PAD_IZQ = 40;
const PAD_DER = 12;
const PAD_SUP = 24;
const PAD_INF = 26;

const RADIO_PUNTO = 4;
const TAMANO_HORIZONTE_INACTIVO = 5;
const TAMANO_HORIZONTE_ACTIVO = 7;

/** Color de línea/relleno por veredicto (tokens de §4.2: -3 para la línea, -1 para la banda). */
const COLOR_LINEA_VEREDICTO = Object.freeze({
  sube: "var(--sube-3)",
  baja: "var(--baja-3)",
  se_mantiene: "var(--mantiene-texto)",
  sin_datos: "var(--tinta-3)",
});

const COLOR_BANDA_VEREDICTO = Object.freeze({
  sube: "var(--sube-1)",
  baja: "var(--baja-1)",
  se_mantiene: "var(--mantiene)",
  sin_datos: "var(--sin-datos)",
});

/** Opacidad de la banda de rango 95 % (spec: "Relleno del color -1 del veredicto al 60 %"). */
const OPACIDAD_BANDA = 0.6;

// ------------------------------------------------------------------------------------------
// Helpers SVG locales (sin innerHTML; equivalentes de `dom.js` para el espacio de nombres SVG)
// ------------------------------------------------------------------------------------------

function crearSvg(etiqueta, atributos = {}, hijos = []) {
  const el = document.createElementNS(SVG_NS, etiqueta);
  for (const [nombre, valor] of Object.entries(atributos ?? {})) {
    if (valor === null || valor === undefined || valor === false) continue;
    if (nombre === "clase") {
      el.setAttribute("class", String(valor));
      continue;
    }
    el.setAttribute(nombre, String(valor));
  }
  const lista = Array.isArray(hijos) ? hijos : [hijos];
  for (const hijo of lista) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    if (typeof hijo === "string" || typeof hijo === "number") {
      el.appendChild(document.createTextNode(String(hijo)));
      continue;
    }
    if (hijo instanceof Node) {
      el.appendChild(hijo);
      continue;
    }
    throw new TypeError("crearSvg(): hijo no soportado; usa texto, número, Node, null/undefined/false");
  }
  return el;
}

/** Texto SVG con las mismas convenciones que `crearSvg` (nunca `innerHTML`/`textContent` con marcado). */
function textoSvg(atributos, contenido) {
  return crearSvg("text", atributos, [contenido]);
}

// ------------------------------------------------------------------------------------------
// Escalas y "ticks" bonitos (sin dependencias externas)
// ------------------------------------------------------------------------------------------

function escalaLineal(dominio, rango) {
  const [d0, d1] = dominio;
  const [r0, r1] = rango;
  const anchoDominio = d1 - d0 === 0 ? 1 : d1 - d0;
  return (valor) => r0 + ((valor - d0) / anchoDominio) * (r1 - r0);
}

/** Redondea `valorAproximado` al siguiente "paso bonito" (1/2/5 × 10^n), para los 3 marcas del eje Y. */
function pasoBonito(valorAproximado) {
  if (!(valorAproximado > 0)) return 1;
  const exponente = Math.floor(Math.log10(valorAproximado));
  const base = 10 ** exponente;
  const fraccion = valorAproximado / base;
  let pasoNormalizado = 10;
  if (fraccion <= 1) pasoNormalizado = 1;
  else if (fraccion <= 2) pasoNormalizado = 2;
  else if (fraccion <= 5) pasoNormalizado = 5;
  return pasoNormalizado * base;
}

// ------------------------------------------------------------------------------------------
// Construcción de la gráfica a partir de una serie (rama que hoy nunca se ejercita con datos
// reales: v1.1 nunca trae `serie`, ver cabecera del módulo).
// ------------------------------------------------------------------------------------------

/**
 * @param {object} datos
 * @param {"demanda"|"oferta"} datos.capa
 * @param {{t: number[], valor: number[]}|null|undefined} datos.serie - años decimales y niveles
 *   observados (censos o levantamientos DENUE), del contrato v1.2 (spec §17).
 * @param {number|null} [datos.nivelBase] - nivel en la fecha base (`nivel_base`, v1.2).
 * @param {number|null} [datos.anioBase] - año de la fecha base ("hoy" en la regla vertical).
 * @param {Array<{clave: string, anios: number|null, fecha: string|null}>} [datos.horizontes]
 * @param {string} [datos.horizonteActivoClave]
 * @param {Map<string, {delta_pct?: number|null, ic95?: [number, number]|null}>} [datos.registrosPorHorizonte]
 * @param {"sube"|"se_mantiene"|"baja"|"sin_datos"} datos.veredicto
 * @param {boolean} [datos.soloPuntos] - AGEB `sin_datos` (spec: "la gráfica muestra solo los
 *   puntos censales si existen").
 * @returns {{svg: SVGSVGElement, figcaption: string}|null} `null` si no hay nada que dibujar
 *   (sin serie, o sin puntos en modo `soloPuntos`).
 */
export function construirGraficaSerie(datos) {
  const {
    capa = "demanda",
    serie,
    nivelBase = null,
    anioBase = null,
    horizontes = [],
    horizonteActivoClave = null,
    registrosPorHorizonte = new Map(),
    veredicto = "sin_datos",
    soloPuntos = false,
  } = datos ?? {};

  const tieneSerie = serie && Array.isArray(serie.t) && Array.isArray(serie.valor)
    && serie.t.length === serie.valor.length && serie.t.length > 0;
  if (!tieneSerie) return null;

  const puntos = serie.t.map((anio, indice) => ({ anio, valor: serie.valor[indice] }));

  // Horizontes con nivel proyectado (solo si hay `nivelBase` y `delta_pct`); en modo `soloPuntos`
  // no se dibuja proyección ni horizontes, aunque los datos vinieran completos (spec §7.4).
  const horizontesResueltos = soloPuntos || nivelBase === null
    ? []
    : horizontes
      .map((h) => {
        const registro = registrosPorHorizonte.get(h.clave);
        const anio = typeof h.fecha === "string" && h.fecha.length >= 4 ? Number(h.fecha.slice(0, 4)) : h.anios;
        if (!Number.isFinite(anio) || !registro || typeof registro.delta_pct !== "number") return null;
        const nivel = nivelBase * (1 + registro.delta_pct / 100);
        const banda = Array.isArray(registro.ic95)
          ? { lo: nivelBase * (1 + registro.ic95[0] / 100), hi: nivelBase * (1 + registro.ic95[1] / 100) }
          : null;
        return { clave: h.clave, anio, nivel, banda, activo: h.clave === horizonteActivoClave };
      })
      .filter((h) => h !== null)
      .sort((a, b) => a.anio - b.anio);

  // -----------------------------------------------------------------------------------------
  // Dominios y escalas
  // -----------------------------------------------------------------------------------------

  const aniosDominio = [...puntos.map((p) => p.anio)];
  if (anioBase !== null && horizontesResueltos.length > 0) aniosDominio.push(anioBase);
  for (const h of horizontesResueltos) aniosDominio.push(h.anio);
  const anioMin = Math.min(...aniosDominio);
  const anioMax = Math.max(...aniosDominio);

  const valoresDominio = [...puntos.map((p) => p.valor)];
  if (!soloPuntos && nivelBase !== null && horizontesResueltos.length > 0) valoresDominio.push(nivelBase);
  for (const h of horizontesResueltos) {
    valoresDominio.push(h.nivel);
    if (h.banda) valoresDominio.push(h.banda.lo, h.banda.hi);
  }
  const valorMaximoObservado = Math.max(0, ...valoresDominio);
  const paso = pasoBonito(valorMaximoObservado / 3 || 1);
  const dominioYMax = paso * 3.3;

  const escalaX = escalaLineal([anioMin, anioMax], [PAD_IZQ, ANCHO - PAD_DER]);
  const escalaY = escalaLineal([0, dominioYMax], [ALTO - PAD_INF, PAD_SUP]);

  // -----------------------------------------------------------------------------------------
  // Elementos
  // -----------------------------------------------------------------------------------------

  const elementos = [];

  // Línea base del eje (spec: "Sin cuadrícula; solo la línea base").
  elementos.push(crearSvg("line", {
    clase: "ficha-grafica__eje-linea",
    x1: PAD_IZQ, y1: ALTO - PAD_INF, x2: ANCHO - PAD_DER, y2: ALTO - PAD_INF,
  }));

  // Eje Y: 3 marcas redondeadas, formato es-MX.
  for (let indice = 1; indice <= 3; indice += 1) {
    const valor = paso * indice;
    const y = escalaY(valor);
    elementos.push(crearSvg("line", {
      clase: "ficha-grafica__eje-marca", x1: PAD_IZQ - 4, y1: y, x2: PAD_IZQ, y2: y,
    }));
    elementos.push(textoSvg(
      { clase: "ficha-grafica__eje-texto", x: PAD_IZQ - 8, y, "text-anchor": "end", "dominant-baseline": "middle" },
      formatoEntero(valor),
    ));
  }

  // Eje X: años de los puntos observados, la fecha base y los horizontes (sin duplicados).
  const aniosEje = [...new Set([...puntos.map((p) => Math.round(p.anio)), ...(anioBase !== null ? [anioBase] : []), ...horizontesResueltos.map((h) => h.anio)])].sort((a, b) => a - b);
  for (const anio of aniosEje) {
    const x = escalaX(anio);
    elementos.push(textoSvg(
      { clase: "ficha-grafica__eje-texto", x, y: ALTO - PAD_INF + 16, "text-anchor": "middle" },
      String(anio),
    ));
  }

  const colorLinea = COLOR_LINEA_VEREDICTO[veredicto] ?? COLOR_LINEA_VEREDICTO.sin_datos;
  const colorBanda = COLOR_BANDA_VEREDICTO[veredicto] ?? COLOR_BANDA_VEREDICTO.sin_datos;

  // Banda del rango 95 % (spec: "polígono... interpolado linealmente entre la fecha base y los
  // tres horizontes"), solo si hay al menos un horizonte con banda.
  const horizontesConBanda = horizontesResueltos.filter((h) => h.banda);
  if (!soloPuntos && horizontesConBanda.length > 0 && nivelBase !== null && anioBase !== null) {
    const xBase = escalaX(anioBase);
    const yBase = escalaY(nivelBase);
    const puntosSuperiores = horizontesConBanda.map((h) => `${escalaX(h.anio)},${escalaY(h.banda.hi)}`);
    const puntosInferiores = [...horizontesConBanda].reverse().map((h) => `${escalaX(h.anio)},${escalaY(h.banda.lo)}`);
    const puntosPoligono = [`${xBase},${yBase}`, ...puntosSuperiores, ...puntosInferiores, `${xBase},${yBase}`].join(" ");
    elementos.push(crearSvg("polygon", {
      clase: "ficha-grafica__banda",
      points: puntosPoligono,
      fill: colorBanda,
      "fill-opacity": OPACIDAD_BANDA,
    }));
  }

  // Tramos: sólido entre observaciones consecutivas.
  if (puntos.length > 1) {
    const puntosOrdenados = [...puntos].sort((a, b) => a.anio - b.anio);
    elementos.push(crearSvg("polyline", {
      clase: "ficha-grafica__tramo-solido",
      points: puntosOrdenados.map((p) => `${escalaX(p.anio)},${escalaY(p.valor)}`).join(" "),
      fill: "none",
    }));
  }

  // Tramo punteado: de la última observación a la fecha base.
  if (!soloPuntos && nivelBase !== null && anioBase !== null) {
    const ultimo = [...puntos].sort((a, b) => a.anio - b.anio).at(-1);
    if (ultimo) {
      elementos.push(crearSvg("line", {
        clase: "ficha-grafica__tramo-punteado",
        x1: escalaX(ultimo.anio), y1: escalaY(ultimo.valor),
        x2: escalaX(anioBase), y2: escalaY(nivelBase),
      }));
    }
  }

  // Proyección: de la fecha base a través de los horizontes.
  if (!soloPuntos && nivelBase !== null && anioBase !== null && horizontesResueltos.length > 0) {
    const puntosProyeccion = [
      `${escalaX(anioBase)},${escalaY(nivelBase)}`,
      ...horizontesResueltos.map((h) => `${escalaX(h.anio)},${escalaY(h.nivel)}`),
    ].join(" ");
    elementos.push(crearSvg("polyline", {
      clase: "ficha-grafica__proyeccion",
      points: puntosProyeccion,
      fill: "none",
      stroke: colorLinea,
    }));
  }

  // Regla vertical "hoy" en la fecha base.
  if (!soloPuntos && anioBase !== null) {
    const xHoy = escalaX(anioBase);
    elementos.push(crearSvg("line", {
      clase: "ficha-grafica__regla-hoy", x1: xHoy, y1: PAD_SUP - 4, x2: xHoy, y2: ALTO - PAD_INF,
    }));
    elementos.push(textoSvg(
      { clase: "ficha-grafica__regla-etiqueta", x: xHoy, y: PAD_SUP - 8, "text-anchor": "middle" },
      t("ficha.reglaHoy", anioBase),
    ));
  }

  // Horizontes: rombos ◇ (inactivos) y ◆ (activo, con etiqueta "{año}: {valor}").
  for (const h of horizontesResueltos) {
    const x = escalaX(h.anio);
    const y = escalaY(h.nivel);
    const tamano = h.activo ? TAMANO_HORIZONTE_ACTIVO : TAMANO_HORIZONTE_INACTIVO;
    elementos.push(crearSvg("rect", {
      clase: `ficha-grafica__horizonte${h.activo ? " ficha-grafica__horizonte--activo" : ""}`,
      x: x - tamano / 2, y: y - tamano / 2, width: tamano, height: tamano,
      transform: `rotate(45 ${x} ${y})`,
      fill: h.activo ? colorLinea : "var(--papel)",
      stroke: colorLinea,
    }));
    if (h.activo) {
      elementos.push(textoSvg(
        { clase: "ficha-grafica__horizonte-etiqueta", x: x + 8, y: y - 8, "text-anchor": "start" },
        t("ficha.etiquetaHorizonte", { anio: h.anio, valor: formatoEntero(h.nivel) }),
      ));
    }
  }

  // Puntos censales (encima de tramos y proyección).
  for (const punto of puntos) {
    elementos.push(crearSvg("circle", {
      clase: "ficha-grafica__punto",
      cx: escalaX(punto.anio), cy: escalaY(punto.valor), r: RADIO_PUNTO,
    }));
  }

  const svg = crearSvg("svg", {
    clase: "ficha-grafica__svg",
    viewBox: `0 0 ${ANCHO} ${ALTO}`,
    width: ANCHO,
    height: ALTO,
    role: "img",
    "aria-hidden": "true", // el contenido accesible equivalente vive en el `<figcaption>`
  }, elementos);

  const figcaption = construirFigcaption({ capa, puntos, nivelBase, anioBase, horizontesResueltos, horizonteActivoClave });

  return { svg, figcaption };
}

/** Texto exacto del `<figcaption>` (spec §7.4: cifras exactas, alternativa textual a la gráfica). */
function construirFigcaption({ puntos, horizontesResueltos, horizonteActivoClave }) {
  const ordenados = [...puntos].sort((a, b) => a.anio - b.anio);
  const primero = ordenados[0];
  const ultimo = ordenados.at(-1) ?? primero;
  const activo = horizontesResueltos.find((h) => h.clave === horizonteActivoClave) ?? horizontesResueltos.at(-1);

  if (!activo) {
    // Sin proyección resoluble (p. ej. modo `soloPuntos`): solo se describen los puntos censales.
    if (primero === ultimo) {
      return t("ficha.figcaption", {
        anioA: Math.round(primero.anio), valorA: formatoEntero(primero.valor),
        anioB: Math.round(primero.anio), valorB: formatoEntero(primero.valor),
        anioH: "", valorH: "", lo: "", hi: "",
      });
    }
    return t("ficha.figcaption", {
      anioA: Math.round(primero.anio), valorA: formatoEntero(primero.valor),
      anioB: Math.round(ultimo.anio), valorB: formatoEntero(ultimo.valor),
      anioH: "", valorH: "", lo: "", hi: "",
    });
  }

  return t("ficha.figcaption", {
    anioA: Math.round(primero.anio),
    valorA: formatoEntero(primero.valor),
    anioB: Math.round(ultimo.anio),
    valorB: formatoEntero(ultimo.valor),
    anioH: activo.anio,
    valorH: formatoEntero(activo.nivel),
    lo: activo.banda ? formatoEntero(activo.banda.lo) : "",
    hi: activo.banda ? formatoEntero(activo.banda.hi) : "",
  });
}

// ------------------------------------------------------------------------------------------
// Montaje: `<figure>` con la gráfica o la nota fija de degradación (spec §7.4)
// ------------------------------------------------------------------------------------------

/**
 * Construye el `<figure>` de la mini-gráfica (o la nota de degradación si no hay `serie`
 * dibujable) y lo agrega a `contenedor`. Devuelve el nodo `<figure>` creado, o `null` cuando no
 * hay nada que mostrar (sin `serie`, capa sin puntos en modo `soloPuntos`, etc. — decidido por
 * `ficha.js`, que es quien sabe si hay que mostrar la nota).
 *
 * @param {HTMLElement} contenedor
 * @param {object} datos - ver `construirGraficaSerie`.
 * @returns {HTMLElement} el `<figure>` (con gráfica) o `<p>` (con la nota de degradación).
 */
export function montarGrafica(contenedor, datos) {
  const resultado = construirGraficaSerie(datos);

  if (!resultado) {
    const nota = document.createElement("p");
    nota.className = "ficha__nota-degradacion";
    nota.appendChild(document.createTextNode(textos.ficha.sinSerie));
    contenedor.appendChild(nota);
    return nota;
  }

  const figcaption = document.createElement("figcaption");
  figcaption.className = "visualmente-oculto";
  figcaption.appendChild(document.createTextNode(resultado.figcaption));

  const figure = document.createElement("figure");
  figure.className = "ficha__grafica";
  figure.appendChild(resultado.svg);
  figure.appendChild(figcaption);

  contenedor.appendChild(figure);
  return figure;
}
