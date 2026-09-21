// frontend/js/titular.js
//
// Titular dinámico (plans/frontend_specs.md §6). Combina `resumirVeredictos` (js/veredictos.js,
// §6.2/§6.5) con las plantillas de `js/textos.js` (§6.3-§6.5) para producir la frase, el
// subtítulo y la nota de oferta, y monta/actualiza el `<header class="titular">` con crossfade
// (§6.1) sin `innerHTML` (js/dom.js).
//
// Este módulo es autocontenido: no asume que `index.html` ya trae un contenedor con un id
// concreto. `montarTitular(contenedor)` construye el `<header>` dentro del contenedor recibido
// (idempotente: si ya existe `#titular` dentro, lo reutiliza) y devuelve un objeto con
// `actualizar(datos)`. El orquestador (main.js, F100) es quien decide cuándo llamarlo y con qué
// datos — este módulo no lee `estado.js` ni hace `fetch`.

import { texto as t, textos } from "./textos.js";
import { formatoPorcentaje, formatoNumero } from "./formato.js";
import { crear, reemplazarContenido, texto as nodoTexto } from "./dom.js";
import { resumirVeredictos } from "./veredictos.js";

const MESES_POR_ANIO = 12;

/**
 * Deriva `{ anio, h }` de un horizonte del contrato v1.2 (plan §2: hoy siempre `hU`, con
 * `anios: null` y `fecha` = el horizonte real del archivo, p. ej. "2027-06"). Si el backend
 * llega a entregar `anios` explícito (v1.2 real, 3/5/7), se usa tal cual: el resto del módulo
 * no cambia (plan §3-1).
 *
 * @param {{fecha?: string|null, anios?: number|null}} horizonte
 * @param {string|null} [generadoIso] - `json.generado`, para derivar `h` cuando `anios` es null.
 */
export function resolverHorizonte(horizonte, generadoIso) {
  const fecha = horizonte?.fecha ?? null;
  const anio = typeof fecha === "string" && fecha.length >= 4 ? Number(fecha.slice(0, 4)) : null;

  if (typeof horizonte?.anios === "number" && Number.isFinite(horizonte.anios)) {
    return { anio, h: horizonte.anios };
  }
  if (!anio || !generadoIso) {
    return { anio, h: null };
  }

  const fechaGenerado = new Date(generadoIso);
  if (Number.isNaN(fechaGenerado.getTime())) {
    return { anio, h: null };
  }
  const mesHorizonte = fecha.length >= 7 ? Number(fecha.slice(5, 7)) : MESES_POR_ANIO / 2;
  const mesesTotales =
    (anio - fechaGenerado.getFullYear()) * MESES_POR_ANIO
    + (mesHorizonte - (fechaGenerado.getMonth() + 1));
  const h = Math.max(1, Math.round(mesesTotales / MESES_POR_ANIO));
  return { anio, h };
}

/** Reemplaza el "A {h} años" inicial por el prefijo de §6.2 cuando h = 7. */
function aplicarPrefijoH7(frase, h) {
  if (h !== 7) return frase;
  return frase.replace(/^A 7 años/, textos.titular.prefijoH7);
}

/** Sustituye el punto final por el sufijo de confianza baja dominante (§6.2/§6.4). */
function aplicarSufijoConfianzaBaja(frase, activo) {
  if (!activo) return frase;
  if (!/\.\s*$/.test(frase)) return `${frase}${textos.titular.sufijoConfianzaBaja}`;
  return frase.replace(/\.\s*$/, textos.titular.sufijoConfianzaBaja);
}

function fraseGeneral(capa, resumen, h, anio) {
  const variables = {
    h,
    anio,
    nBaja: resumen.nBaja,
    nSube: resumen.nSube,
    nMant: resumen.nMant,
  };
  let frase = t(`titular.${capa}.general.${resumen.escenario}`, variables);
  frase = aplicarPrefijoH7(frase, h);
  frase = aplicarSufijoConfianzaBaja(frase, resumen.confianzaBajaDominante);
  return frase;
}

function fraseAlcaldia(capa, resumen, h, alcaldiaNombre, nSinDatosAgeb) {
  const variables = {
    h,
    alc: alcaldiaNombre,
    vA: resumen.v,
    nBaja: resumen.nBaja,
    nSube: resumen.nSube,
    nMant: resumen.nMant,
    pBaja: resumen.pBaja,
    pSube: resumen.pSube,
  };
  let frase = t(`titular.${capa}.alcaldia.${resumen.escenario}`, variables);
  frase = aplicarPrefijoH7(frase, h);
  frase = aplicarSufijoConfianzaBaja(frase, resumen.confianzaBajaDominante);
  if (typeof nSinDatosAgeb === "number" && nSinDatosAgeb > 0) {
    // `sinDatosExtra` recibe el número directamente (no un objeto de variables), así que se
    // invoca tal cual en vez de con el atajo `texto()`.
    const extra = textos.titular.demanda.alcaldia.sinDatosExtra(nSinDatosAgeb);
    frase = `${frase} ${extra}`;
  }
  return frase;
}

/**
 * Plantilla fija de la capa brecha (§6.3): sin veredicto, no usa `resumirVeredictos`. `min`/`max`
 * son establecimientos por cada 1,000 niñas y niños (una razón, no un porcentaje de cambio), así
 * que se formatean con `formatoNumero`, no `formatoPorcentaje`.
 */
function fraseBrecha({ min, max, alcaldiaMin }) {
  return t("titular.brecha", {
    min: formatoNumero(min),
    max: formatoNumero(max),
    alcaldiaMin,
  });
}

function subtituloGeneral(capa, anio, agregadoCdmx) {
  if (capa === "oferta") {
    return t("titular.subtitulo.oferta", { anio });
  }
  const nombreCapa = textos.capa.nombre[capa] ?? textos.capa.nombre.demanda;
  if (agregadoCdmx && typeof agregadoCdmx.delta_pct === "number" && Array.isArray(agregadoCdmx.ic95)) {
    const [lo, hi] = agregadoCdmx.ic95;
    return t("titular.subtitulo.conAgregado", {
      capa: nombreCapa,
      anio,
      cambio: formatoPorcentaje(agregadoCdmx.delta_pct),
      lo: formatoPorcentaje(lo, { signo: false }),
      hi: formatoPorcentaje(hi, { signo: false }),
    });
  }
  return t("titular.subtitulo.sinAgregado", { capa: nombreCapa, anio });
}

function subtituloAlcaldia(anio, alcaldiaNombre, resumenAlcaldia) {
  if (
    resumenAlcaldia
    && typeof resumenAlcaldia.delta_pct === "number"
    && Array.isArray(resumenAlcaldia.ic95)
  ) {
    const [lo, hi] = resumenAlcaldia.ic95;
    return t("titular.subtitulo.alcaldia", {
      anio,
      alcaldia: alcaldiaNombre,
      cambio: formatoPorcentaje(resumenAlcaldia.delta_pct),
      lo: formatoPorcentaje(lo, { signo: false }),
      hi: formatoPorcentaje(hi, { signo: false }),
    });
  }
  return t("titular.subtitulo.alcaldiaSinAgregado", { anio, alcaldia: alcaldiaNombre });
}

/**
 * Calcula el texto del titular (frase, subtítulo y nota de oferta) para la vista general o la
 * vista de alcaldía. Función pura: no toca el DOM. El mismo `resumen` que produce se puede
 * reutilizar para pintar la tabla (F40), de modo que titular y tabla nunca diverjan (§6.5
 * "Invariante").
 *
 * @param {object} opciones
 * @param {"demanda"|"oferta"} opciones.capa
 * @param {"general"|"alcaldia"} opciones.vista
 * @param {Array<{veredicto?: string, confianza?: string}>} opciones.registros - registros ya
 *   resueltos al horizonte activo (`registro.h[horizonteActivo]`), alcaldías (vista general) o
 *   AGEB de una alcaldía (vista alcaldía).
 * @param {{fecha?: string|null, anios?: number|null}} opciones.horizonte
 * @param {string|null} [opciones.generadoIso]
 * @param {{delta_pct?: number, ic95?: [number, number]}|null} [opciones.agregadoCdmx] - vista
 *   general: `agregado_cdmx`, ausente con v1.1 (plan §2) — el subtítulo lo omite.
 * @param {string} [opciones.alcaldiaNombre] - requerido si `vista === "alcaldia"`.
 * @param {{delta_pct?: number, ic95?: [number, number]}|null} [opciones.resumenAlcaldia] - el
 *   propio registro (demanda) de la alcaldía activa, para el subtítulo (§6.5).
 * @param {number} [opciones.nSinDatosAgeb] - AGEB con `sin_datos` en la alcaldía (§6.5).
 * @param {{min: number, max: number, alcaldiaMin: string}} [opciones.brecha] - solo si
 *   `capa === "brecha"` (nunca ocurre con v1.1, código listo para cuando exista `capas.brecha`).
 */
export function calcularTitular(opciones) {
  const {
    capa,
    vista,
    registros,
    horizonte,
    generadoIso = null,
    agregadoCdmx = null,
    alcaldiaNombre = null,
    resumenAlcaldia = null,
    nSinDatosAgeb = 0,
    brecha = null,
  } = opciones ?? {};

  const { anio, h } = resolverHorizonte(horizonte, generadoIso);

  if (capa === "brecha") {
    return {
      frase: brecha ? fraseBrecha(brecha) : "",
      subtitulo: t("capa.nombre.brecha") ?? "",
      notaOferta: null,
      resumen: null,
      anio,
      h,
    };
  }

  const resumen = resumirVeredictos(registros);

  const frase =
    vista === "alcaldia"
      ? fraseAlcaldia(capa, resumen, h, alcaldiaNombre, nSinDatosAgeb)
      : fraseGeneral(capa, resumen, h, anio);

  const subtitulo =
    vista === "alcaldia"
      ? subtituloAlcaldia(anio, alcaldiaNombre, resumenAlcaldia)
      : subtituloGeneral(capa, anio, agregadoCdmx);

  const notaOferta = capa === "oferta" ? textos.titular.notaOferta : null;

  return { frase, subtitulo, notaOferta, resumen, anio, h };
}

// --------------------------------------------------------------------------------------------
// Montaje en el DOM (§6.1) con crossfade de 200 ms (§6.1, --d-crossfade en tokens.css)
// --------------------------------------------------------------------------------------------

const DURACION_CROSSFADE_MS_POR_DEFECTO = 200;

function duracionCrossfadeMs() {
  if (typeof window === "undefined" || typeof getComputedStyle !== "function") {
    return DURACION_CROSSFADE_MS_POR_DEFECTO;
  }
  const valor = getComputedStyle(document.documentElement).getPropertyValue("--d-crossfade").trim();
  const ms = Number.parseFloat(valor);
  return Number.isFinite(ms) ? ms : DURACION_CROSSFADE_MS_POR_DEFECTO;
}

/**
 * Reemplaza el texto de `linea` con un crossfade de dos capas superpuestas (saliente/entrante,
 * §6.1: "la frase saliente va a opacidad 0 en 100 ms y la entrante sube de 0 a 1 en 100 ms, las
 * dos lineales"). El alto no se anima: `css/titular.css` reserva la altura del contenedor.
 */
function crossfadeLinea(linea, textoNuevo) {
  const actual = linea.dataset.textoActual ?? "";
  if (actual === textoNuevo) return;

  const saliente = crear("span", { clase: "titular__capa titular__capa--saliente" }, [
    nodoTexto(actual),
  ]);
  const entrante = crear("span", { clase: "titular__capa titular__capa--entrante" }, [
    nodoTexto(textoNuevo),
  ]);
  reemplazarContenido(linea, [saliente, entrante]);
  linea.dataset.textoActual = textoNuevo;

  // Reinicia la animación en cada cambio: se activa en el siguiente frame para que el
  // navegador registre el estado inicial antes de aplicar las clases que animan.
  requestAnimationFrame(() => {
    saliente.classList.add("titular__capa--activa");
    entrante.classList.add("titular__capa--activa");
  });

  window.setTimeout(() => {
    reemplazarContenido(linea, [nodoTexto(textoNuevo)]);
  }, duracionCrossfadeMs());
}

/**
 * Crea (o reutiliza) el `<header class="titular">` dentro de `contenedor` y devuelve
 * `{ raiz, actualizar }`. `actualizar(datos)` recibe el resultado de `calcularTitular` (o un
 * objeto con `frase`/`subtitulo`/`notaOferta`) y actualiza el DOM con crossfade, sin `innerHTML`.
 *
 * @param {HTMLElement} contenedor
 */
export function montarTitular(contenedor) {
  if (!contenedor) {
    throw new TypeError("montarTitular(contenedor): se requiere un contenedor");
  }

  let raiz = contenedor.querySelector("#titular");
  if (!raiz) {
    raiz = crear("header", { id: "titular", clase: "titular", "aria-live": "off" });
    contenedor.appendChild(raiz);
  }

  const frase = crear("p", { clase: "titular__frase" });
  const sub = crear("p", { clase: "titular__sub" });
  const nota = crear("p", { clase: "titular__nota", hidden: true });
  const enlace = crear("a", { clase: "titular__metodologia", href: "#" }, [
    t("metodologia.enlaceTitular"),
  ]);

  reemplazarContenido(raiz, [frase, sub, nota, enlace]);

  function actualizar(datos) {
    crossfadeLinea(frase, datos?.frase ?? "");
    crossfadeLinea(sub, datos?.subtitulo ?? "");
    if (datos?.notaOferta) {
      nota.hidden = false;
      crossfadeLinea(nota, datos.notaOferta);
    } else {
      nota.hidden = true;
    }
  }

  return { raiz, frase, sub, nota, enlace, actualizar };
}
