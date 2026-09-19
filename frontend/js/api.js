// frontend/js/api.js
//
// Carga y valida el contrato v1.1 (CLAUDE.md → "Contrato de salida") y lo
// adapta al esquema v1.2 contra el que se escribe toda la UI
// (plans/frontend_plan.md §2). Ningún otro módulo debe leer el JSON v1.1
// crudo ni tocar `fetch` directamente.

import {
  VERSION_CONTRATO_ESPERADA,
  VEREDICTOS_VALIDOS,
  CONFIANZAS_VALIDAS,
  CAPAS,
  CLAVE_HORIZONTE_UNICO,
  NIVEL,
  VALORES_MOCK,
  DEMORA_MOCK_LENTO_MS,
  leerParametroMock,
  rutaDatos,
} from "./config.js";

/** Error de carga/validación de datos. `codigo` distingue el estado a mostrar (spec §15). */
export class ErrorDatos extends Error {
  constructor(mensaje, { codigo = "desconocido", causa = null } = {}) {
    super(mensaje);
    this.name = "ErrorDatos";
    this.codigo = codigo;
    this.causa = causa;
  }
}

function esperar(ms) {
  return new Promise((resolver) => setTimeout(resolver, ms));
}

/**
 * Valida la forma mínima del contrato v1.1. No valida cada registro (eso lo
 * hace `normalizarRegistro`, que degrada a `sin_datos` en vez de rechazar
 * todo el archivo por una clave corrupta).
 */
export function validarContrato(json) {
  if (!json || typeof json !== "object") {
    throw new ErrorDatos("La respuesta de datos está vacía o mal formada.", {
      codigo: "esquema_invalido",
    });
  }
  if (json.version !== VERSION_CONTRATO_ESPERADA) {
    throw new ErrorDatos(`Versión de datos incompatible (${json.version ?? "desconocida"}).`, {
      codigo: "version_incompatible",
    });
  }
  if (typeof json.horizonte !== "string" || json.horizonte === "") {
    throw new ErrorDatos("Los datos no traen horizonte.", { codigo: "esquema_invalido" });
  }
  if (!json.capas || typeof json.capas !== "object") {
    throw new ErrorDatos("Los datos no traen capas.", { codigo: "esquema_invalido" });
  }
  return true;
}

/**
 * Registro degradado a `sin_datos`. Se usa tanto para claves ausentes del
 * JSON como para registros con forma inválida: CLAUDE.md prohíbe inventar
 * un veredicto, así que ante cualquier duda el resultado es "sin_datos",
 * nunca un valor construido a partir de datos incompletos.
 */
function registroSinDatos(original) {
  return {
    veredicto: "sin_datos",
    delta_pct: null,
    tasa_anual_pct: null,
    ic95: null,
    confianza: CONFIANZAS_VALIDAS.includes(original?.confianza) ? original.confianza : "baja",
    n_obs: typeof original?.n_obs === "number" ? original.n_obs : 0,
    cve_mun: typeof original?.cve_mun === "string" ? original.cve_mun : null,
    motivo_sin_datos: typeof original?.motivo_sin_datos === "string" ? original.motivo_sin_datos : undefined,
  };
}

function normalizarRegistro(registroOriginal) {
  if (!registroOriginal || typeof registroOriginal !== "object") {
    return registroSinDatos(registroOriginal);
  }
  if (!VEREDICTOS_VALIDOS.includes(registroOriginal.veredicto)) {
    return registroSinDatos(registroOriginal);
  }
  if (registroOriginal.veredicto === "sin_datos") {
    return registroSinDatos(registroOriginal);
  }
  const confianza = CONFIANZAS_VALIDAS.includes(registroOriginal.confianza)
    ? registroOriginal.confianza
    : "baja";
  return {
    veredicto: registroOriginal.veredicto,
    delta_pct: typeof registroOriginal.delta_pct === "number" ? registroOriginal.delta_pct : null,
    tasa_anual_pct:
      typeof registroOriginal.tasa_anual_pct === "number" ? registroOriginal.tasa_anual_pct : null,
    ic95: Array.isArray(registroOriginal.ic95) && registroOriginal.ic95.length === 2
      ? registroOriginal.ic95
      : null,
    confianza,
    n_obs: typeof registroOriginal.n_obs === "number" ? registroOriginal.n_obs : 0,
    cve_mun: typeof registroOriginal.cve_mun === "string" ? registroOriginal.cve_mun : null,
    motivo_sin_datos: undefined,
  };
}

function construirIndices(capas, nivel) {
  const claves = new Set();
  for (const nombreCapa of CAPAS) {
    for (const clave of Object.keys(capas[nombreCapa] ?? {})) claves.add(clave);
  }

  const porClave = new Map();
  const porCveMun = new Map();

  for (const clave of claves) {
    const registroDemanda = capas.demanda?.[clave]?.h?.[CLAVE_HORIZONTE_UNICO] ?? null;
    const registroOferta = capas.oferta?.[clave]?.h?.[CLAVE_HORIZONTE_UNICO] ?? null;
    porClave.set(clave, { demanda: registroDemanda, oferta: registroOferta });

    if (nivel === NIVEL.AGEB) {
      const cveMun = registroDemanda?.cve_mun ?? registroOferta?.cve_mun ?? null;
      if (cveMun) {
        if (!porCveMun.has(cveMun)) porCveMun.set(cveMun, []);
        porCveMun.get(cveMun).push(clave);
      }
    }
  }

  if (nivel === NIVEL.AGEB) {
    return { porCvegeo: porClave, porCveMun };
  }
  // nivel alcaldía: la propia clave del registro ya es el cve_mun.
  return { porCveMun: porClave };
}

/**
 * Adaptador v1.1 → v1.2 (plan §2). Nunca produce `serie`, `distribucion_ageb`,
 * `agregado_cdmx` ni `capas.brecha`: son degradaciones intencionales que
 * cada componente de UI sabe interpretar (ficha sin gráfica, fila
 * desplegada con el GeoJSON en vez de la barra precalculada, etc.).
 *
 * @param {object} json - JSON v1.1 crudo (ya validado con `validarContrato`).
 * @param {"ageb"|"alcaldia"} nivel
 */
export function adaptarV11aV12(json, nivel) {
  validarContrato(json);

  const horizontes = [{ clave: CLAVE_HORIZONTE_UNICO, anios: null, fecha: json.horizonte }];

  const capas = {};
  for (const nombreCapa of CAPAS) {
    const capaOriginal = json.capas[nombreCapa] ?? {};
    const registros = {};
    for (const [clave, registroOriginal] of Object.entries(capaOriginal)) {
      registros[clave] = { h: { [CLAVE_HORIZONTE_UNICO]: normalizarRegistro(registroOriginal) } };
    }
    capas[nombreCapa] = registros;
  }

  return {
    version: "1.2",
    generado: typeof json.generado === "string" ? json.generado : null,
    nivel,
    horizontes,
    capas,
    indices: construirIndices(capas, nivel),
  };
}

/**
 * Devuelve el registro adaptado de una capa para una clave dada, aunque la
 * clave esté ausente del JSON: en ese caso, `sin_datos` (nunca `undefined`).
 */
export function obtenerRegistro(datosAdaptados, clave, nombreCapa) {
  const entrada = datosAdaptados?.capas?.[nombreCapa]?.[clave];
  if (!entrada) {
    return { h: { [CLAVE_HORIZONTE_UNICO]: registroSinDatos() } };
  }
  return entrada;
}

/**
 * Carga y adapta la predicción de un nivel ("ageb" | "alcaldia"), aplicando
 * el parámetro `?mock=` (plan §6).
 *
 * @param {"ageb"|"alcaldia"} nivel
 * @param {{mock?: string|null, fetch?: typeof fetch, ubicacion?: Location, demoraMs?: number}} [opciones]
 */
export async function cargarPrediccion(nivel, opciones = {}) {
  const mock = opciones.mock !== undefined ? opciones.mock : leerParametroMock(opciones.ubicacion);
  const obtenerFetch = opciones.fetch ?? (typeof fetch !== "undefined" ? fetch.bind(globalThis) : null);

  if (mock === VALORES_MOCK.ERROR) {
    throw new ErrorDatos("No pudimos cargar los datos.", { codigo: "red" });
  }
  if (mock === VALORES_MOCK.LENTO) {
    await esperar(opciones.demoraMs ?? DEMORA_MOCK_LENTO_MS);
  }
  if (!obtenerFetch) {
    throw new ErrorDatos("No hay una función fetch disponible en este entorno.", { codigo: "sin_fetch" });
  }

  const ruta = rutaDatos(nivel, mock);

  let respuesta;
  try {
    respuesta = await obtenerFetch(ruta);
  } catch (causa) {
    throw new ErrorDatos("No pudimos cargar los datos.", { codigo: "red", causa });
  }
  if (!respuesta.ok) {
    throw new ErrorDatos(`No pudimos cargar los datos (HTTP ${respuesta.status}).`, { codigo: "red" });
  }

  let json;
  try {
    json = await respuesta.json();
  } catch (causa) {
    throw new ErrorDatos("Los datos recibidos no son JSON válido.", { codigo: "esquema_invalido", causa });
  }

  return adaptarV11aV12(json, nivel);
}
