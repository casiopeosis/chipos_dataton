// frontend/js/formato.js
//
// Formato numérico es-MX (plans/frontend_specs.md §7.1, §14) y símbolos de
// veredicto/confianza (§4.2, §10.4, §14.1). Funciones puras: no tocan el DOM.

export const IDIOMA = "es-MX";

// U+2212 MINUS SIGN: Intl.NumberFormat en es-MX usa el guion ASCII (U+002D)
// para los negativos, no el signo menos tipográfico que pide el spec. Se
// sustituye a mano después de formatear.
const SIGNO_MENOS_TIPOGRAFICO = "−";
const GUION_ASCII = "-";

// U+2009 THIN SPACE: "espacio fino antes de %" (spec §7.1).
const ESPACIO_FINO = " ";

const MARCADOR_SIN_DATOS = "—"; // em dash: placeholder neutro, no es texto de UI (eso vive en textos.js)

function esNumeroFinito(valor) {
  return typeof valor === "number" && Number.isFinite(valor);
}

/**
 * Número es-MX con separador decimal de punto y agrupación de miles,
 * sin signo forzado. Para cifras enteras (p. ej. n_obs) usar `formatoEntero`.
 */
export function formatoNumero(valor, { decimales = 1 } = {}) {
  if (!esNumeroFinito(valor)) return MARCADOR_SIN_DATOS;
  return new Intl.NumberFormat(IDIOMA, {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valor);
}

/** Entero es-MX (n_obs, conteos de la leyenda/tabla). */
export function formatoEntero(valor) {
  if (!esNumeroFinito(valor)) return MARCADOR_SIN_DATOS;
  return new Intl.NumberFormat(IDIOMA, { maximumFractionDigits: 0 }).format(Math.round(valor));
}

/**
 * Porcentaje es-MX con 1 decimal, signo tipográfico y "+" explícito en
 * positivos (spec §7.1): "+12.3 %", "−17.9 %", "0.0 %".
 *
 * @param {number|null|undefined} valor
 * @param {{decimales?: number, signo?: boolean}} [opciones] - `signo:false`
 *   omite el "+"/"−" (para magnitudes ya etiquetadas, p. ej. "por año").
 */
export function formatoPorcentaje(valor, { decimales = 1, signo = true } = {}) {
  if (!esNumeroFinito(valor)) return MARCADOR_SIN_DATOS;
  const nf = new Intl.NumberFormat(IDIOMA, {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
    signDisplay: signo ? "exceptZero" : "never",
  });
  const cifra = nf.format(valor).replaceAll(GUION_ASCII, SIGNO_MENOS_TIPOGRAFICO);
  return `${cifra}${ESPACIO_FINO}%`;
}

/** Formatea un intervalo [lo, hi] como "{lo} y {hi}" (para "Rango probable...", §14.3). */
export function formatoIntervalo(intervalo, opciones = {}) {
  if (!Array.isArray(intervalo) || intervalo.length !== 2) return null;
  const [lo, hi] = intervalo;
  return { lo: formatoPorcentaje(lo, opciones), hi: formatoPorcentaje(hi, opciones) };
}

// --------------------------------------------------------------------
// Símbolos (spec §4.2 veredictos, §10.4/§14 confianza). Nunca depender
// solo del color: todo componente que muestre un veredicto o confianza
// debe usar el símbolo, no solo la clase de color.
// --------------------------------------------------------------------

export const SIMBOLO_VEREDICTO = Object.freeze({
  sube: "▲", // ▲
  se_mantiene: "■", // ■
  baja: "▼", // ▼
  sin_datos: "∅", // ∅
});

export const SIMBOLO_CONFIANZA = Object.freeze({
  alta: "●", // ●
  media: "◐", // ◐
  baja: "○", // ○
});

/** Símbolo de veredicto; cualquier valor fuera del conjunto válido se trata como sin_datos. */
export function simboloVeredicto(veredicto) {
  return SIMBOLO_VEREDICTO[veredicto] ?? SIMBOLO_VEREDICTO.sin_datos;
}

/** Símbolo de confianza; cualquier valor fuera del conjunto válido se trata como confianza baja. */
export function simboloConfianza(confianza) {
  return SIMBOLO_CONFIANZA[confianza] ?? SIMBOLO_CONFIANZA.baja;
}

export const constantesFormato = Object.freeze({
  SIGNO_MENOS_TIPOGRAFICO,
  ESPACIO_FINO,
  MARCADOR_SIN_DATOS,
});
