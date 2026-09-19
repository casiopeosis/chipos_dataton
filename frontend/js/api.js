// frontend/js/api.js
//
// Carga y valida el contrato (v1.1 de un horizonte o v1.2 de varios, CLAUDE.md → "Contrato de
// salida") y lo adapta al esquema interno v1.2 contra el que se escribe toda la UI
// (plans/frontend_plan.md §2, plans/frontend_specs.md §17). Ningún otro módulo debe leer el JSON
// crudo ni tocar `fetch` directamente.
//
// Dos caminos de adaptación, mismo resultado (`{version:"1.2", ..., indices}`):
// - `adaptarV11aV12`: contrato v1.1 real (un solo horizonte `hU`), degrada `serie`,
//   `distribucion_ageb` y `agregado_cdmx` a ausentes (nunca los inventa).
// - `adaptarV12`: contrato v1.2 real (horizontes `h3`/`h5`/`h7`), pasa `serie`,
//   `distribucion_ageb` y `agregado_cdmx` tal cual.
// En ambos caminos, `indices.porCvegeo`/`indices.porCveMun` guardan la entrada COMPLETA de cada
// capa (con su `.h` interno intacto, sin aplanar a un horizonte concreto): quien consume los
// índices (`main.js#registroPlano`, `leyenda.js#registroPlano`, `mapa.js#registroDeHorizonte`)
// decide qué horizonte mostrar con la clave activa de `estado.js`.

import {
  VERSIONES_CONTRATO_ACEPTADAS,
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
 * Valida la forma mínima del contrato, v1.1 (un horizonte, `json.horizonte`) o v1.2 (varios,
 * `json.fecha_base` + `json.horizontes[]`). No valida cada registro (eso lo hace
 * `normalizarRegistro`, que degrada a `sin_datos` en vez de rechazar todo el archivo por una
 * clave corrupta).
 */
export function validarContrato(json) {
  if (!json || typeof json !== "object") {
    throw new ErrorDatos("La respuesta de datos está vacía o mal formada.", {
      codigo: "esquema_invalido",
    });
  }
  if (!VERSIONES_CONTRATO_ACEPTADAS.includes(json.version)) {
    throw new ErrorDatos(`Versión de datos incompatible (${json.version ?? "desconocida"}).`, {
      codigo: "version_incompatible",
    });
  }
  if (json.version === "1.1" && (typeof json.horizonte !== "string" || json.horizonte === "")) {
    throw new ErrorDatos("Los datos no traen horizonte.", { codigo: "esquema_invalido" });
  }
  if (json.version === "1.2") {
    if (typeof json.fecha_base !== "string" || json.fecha_base === "") {
      throw new ErrorDatos("Los datos no traen fecha_base.", { codigo: "esquema_invalido" });
    }
    if (!Array.isArray(json.horizontes) || json.horizontes.length === 0) {
      throw new ErrorDatos("Los datos no traen horizontes.", { codigo: "esquema_invalido" });
    }
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

/**
 * Junta las claves de todas las capas y arma `porCvegeo`/`porCveMun` (nivel AGEB) o `porCveMun`
 * (nivel alcaldía). Cada valor de `porClave` es `{demanda: entradaCapa|null, oferta:
 * entradaCapa|null}`, donde `entradaCapa` es la entrada COMPLETA de `capas[nombreCapa][clave]`
 * (con su `.h` interno intacto, p. ej. `{cve_mun, ..., h:{h3:{...}, h5:{...}, h7:{...}}}` o
 * `{cve_mun, ..., h:{hU:{...}}}` en el camino v1.1) — SIN aplanar a un horizonte concreto. Quien
 * consuma los índices resuelve el horizonte activo (`registroPlano` en `main.js`/`leyenda.js`,
 * `registroDeHorizonte` en `mapa.js`).
 */
function construirIndices(capas, nivel) {
  const claves = new Set();
  for (const nombreCapa of CAPAS) {
    for (const clave of Object.keys(capas[nombreCapa] ?? {})) claves.add(clave);
  }

  const porClave = new Map();
  const porCveMun = new Map();

  for (const clave of claves) {
    const entradaDemanda = capas.demanda?.[clave] ?? null;
    const entradaOferta = capas.oferta?.[clave] ?? null;
    porClave.set(clave, { demanda: entradaDemanda, oferta: entradaOferta });

    if (nivel === NIVEL.AGEB) {
      const cveMun = entradaDemanda?.cve_mun ?? entradaOferta?.cve_mun ?? null;
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

/** Igual que `construirIndices`, para el camino v1.2 (nombre propio por claridad, plan §6). */
function construirIndicesV12(capas, nivel) {
  return construirIndices(capas, nivel);
}

/**
 * Adaptador v1.1 → v1.2 (plan §2). Nunca produce `serie`, `distribucion_ageb`,
 * `agregado_cdmx` ni `capas.brecha`: son degradaciones intencionales que
 * cada componente de UI sabe interpretar (ficha sin gráfica, fila
 * desplegada con el GeoJSON en vez de la barra precalculada, etc.).
 *
 * Cada entrada de capa queda `{cve_mun, h: {hU: registroNormalizado}}` — el mismo shape
 * `{cve_mun, ..., h:{...}}` que produce `adaptarV12` (sin aplanar), para que `construirIndices`
 * y quien consuma los índices (`main.js`/`leyenda.js`/`mapa.js`) no necesiten distinguir de qué
 * camino vinieron los datos.
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
      const registroNorm = normalizarRegistro(registroOriginal);
      registros[clave] = { cve_mun: registroNorm.cve_mun, h: { [CLAVE_HORIZONTE_UNICO]: registroNorm } };
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
 * Adaptador v1.2 → v1.2 "interno" (plan §6): valida y arma la misma envoltura que
 * `adaptarV11aV12` (`{version, generado, nivel, horizontes, capas, indices}`), más los campos
 * propios de v1.2 (`fecha_base`, `distribucion_ageb`, `agregado_cdmx`). A diferencia del camino
 * v1.1, aquí `json.capas` ya trae cada entrada con su `.h` completo (`h3`/`h5`/`h7`, o solo `h3`
 * para oferta): no hace falta envolver nada, solo indexar.
 *
 * @param {object} json - JSON v1.2 crudo (ya validado con `validarContrato`).
 * @param {"ageb"|"alcaldia"} nivel
 */
export function adaptarV12(json, nivel) {
  validarContrato(json);

  return {
    version: "1.2",
    generado: typeof json.generado === "string" ? json.generado : null,
    fecha_base: json.fecha_base,
    nivel,
    horizontes: json.horizontes,
    capas: json.capas,
    distribucion_ageb: json.distribucion_ageb ?? null,
    agregado_cdmx: json.agregado_cdmx ?? null,
    indices: construirIndicesV12(json.capas, nivel),
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

  return json?.version === "1.2" ? adaptarV12(json, nivel) : adaptarV11aV12(json, nivel);
}
