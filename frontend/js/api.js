// frontend/js/api.js
//
// Carga y valida el contrato (v1.4 directo, con v1.1/v1.2 como cadena de degradación,
// CLAUDE.md → "Contrato de salida", plans/frontend_plan.md §2) y lo adapta al esquema interno
// común contra el que se escribe toda la UI. Ningún otro módulo debe leer el JSON crudo ni tocar
// `fetch` directamente.
//
// Tres caminos de adaptación, mismo resultado (`{version, generado, fecha_base, nivel, horizontes,
// capas, indices, distribucion_ageb?, agregado_cdmx?}`, forma v1.4 siempre):
// - `adaptarV14`: contrato real, pasa `capas.demanda`/`capas.ramas` tal cual y construye índices.
// - `adaptarV12aV14`: contrato v1.2 (demanda/oferta de dos capas, sin segmentos ni celdas) →
//   segmento único `todas`, celda única `educacion.todos`; salud/comercio/verde `sin_datos`.
// - `adaptarV11aV14`: contrato v1.1 (un solo horizonte) → igual que v1.2 más horizonte único `hU`.
// En los tres, `indices.porCvegeo`/`indices.porCveMun` guardan la entrada COMPLETA de cada unidad
// (`{cve_mun, segmentos, ramas}`, con su `.h` interno intacto): `composicion.js` decide qué
// segmento/celda/horizonte usar según el estado activo (`estado.js`), nunca este módulo.

import {
  VERSIONES_CONTRATO_ACEPTADAS,
  VEREDICTOS_VALIDOS,
  CONFIANZAS_VALIDAS,
  NIVEL,
  RAMAS,
  RAMAS_CON_PROYECCION,
  HORIZONTES_OFERTA,
  SEGMENTOS_DEMANDA,
  SEGMENTO_POR_OMISION,
  CLAVE_HORIZONTE_UNICO,
  CLAVE_CELDA_UNICA,
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
 * Valida la forma mínima del contrato: v1.1 (`json.horizonte`), v1.2 (`json.fecha_base` +
 * `json.horizontes[]`, capas `demanda`/`oferta`) o v1.4 (igual que v1.2, capas `demanda`/`ramas`).
 * No valida cada registro (eso lo hace `normalizarRegistroH`, que degrada a `sin_datos` en vez de
 * rechazar todo el archivo por una clave corrupta).
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
  if (json.version !== "1.1") {
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
 * Registro `h` degradado a `sin_datos`. Se usa tanto para horizontes ausentes del JSON como para
 * registros con forma inválida: CLAUDE.md prohíbe inventar un veredicto, así que ante cualquier
 * duda el resultado es "sin_datos", nunca un valor construido a partir de datos incompletos.
 */
function bloqueHSinDatos() {
  return { veredicto: "sin_datos", delta_pct: null, tasa_anual_pct: null, ic95: null, confianza: "baja" };
}

function normalizarBloqueH(bloque) {
  if (!bloque || typeof bloque !== "object") return bloqueHSinDatos();
  if (!VEREDICTOS_VALIDOS.includes(bloque.veredicto)) return bloqueHSinDatos();
  if (bloque.veredicto === "sin_datos") return bloqueHSinDatos();
  const confianza = CONFIANZAS_VALIDAS.includes(bloque.confianza) ? bloque.confianza : "baja";
  return {
    veredicto: bloque.veredicto,
    delta_pct: typeof bloque.delta_pct === "number" ? bloque.delta_pct : null,
    tasa_anual_pct: typeof bloque.tasa_anual_pct === "number" ? bloque.tasa_anual_pct : null,
    ic95: Array.isArray(bloque.ic95) && bloque.ic95.length === 2 ? bloque.ic95 : null,
    confianza,
  };
}

/** Registro de una celda/segmento (demanda u oferta), normalizado. `horizontesEsperados`: lista de
 * claves de horizonte que el registro debe traer (`[]` para verde, sin `h`). */
function normalizarRegistroCapa(registroOriginal, horizontesEsperados) {
  const cveMun = typeof registroOriginal?.cve_mun === "string" ? registroOriginal.cve_mun : null;
  const nObs = typeof registroOriginal?.n_obs === "number" ? registroOriginal.n_obs : 0;
  const motivoSinDatos =
    typeof registroOriginal?.motivo_sin_datos === "string" ? registroOriginal.motivo_sin_datos : null;
  const nivelBase = typeof registroOriginal?.nivel_base === "number" ? registroOriginal.nivel_base : null;
  const serie =
    registroOriginal?.serie && Array.isArray(registroOriginal.serie.t) ? registroOriginal.serie : { t: [], valor: [] };

  const base = { cve_mun: cveMun, n_obs: nObs, motivo_sin_datos: motivoSinDatos, nivel_base: nivelBase, serie };
  if (horizontesEsperados.length === 0) {
    // Rama sin proyección (verde): sin `h`, con `area_m2` por celda si el original lo trae.
    return { ...base, area_m2: typeof registroOriginal?.area_m2 === "number" ? registroOriginal.area_m2 : null };
  }
  const h = {};
  for (const clave of horizontesEsperados) {
    h[clave] = normalizarBloqueH(registroOriginal?.h?.[clave]);
  }
  return { ...base, h };
}

/**
 * Junta las claves de `capas.demanda` y de todas las ramas, y arma `porCvegeo`/`porCveMun` (nivel
 * AGEB) o `porCveMun` (nivel alcaldía). Cada valor es `{cve_mun, segmentos, ramas}`:
 * `segmentos[segmento]` y `ramas[rama].celdas[celda]` son la entrada COMPLETA de esa unidad (con
 * su `.h` interno intacto, sin aplanar a un horizonte concreto) -- quien consuma los índices
 * (`composicion.js`) resuelve el horizonte/segmento/filtro activo.
 */
function construirIndices(capas, nivel) {
  const claves = new Set(Object.keys(capas.demanda ?? {}));
  for (const rama of RAMAS) {
    for (const clave of Object.keys(capas.ramas?.[rama] ?? {})) claves.add(clave);
  }

  const porClave = new Map();
  const porCveMun = new Map();

  for (const clave of claves) {
    const entradaDemanda = capas.demanda?.[clave] ?? null;
    const cveMun = entradaDemanda?.cve_mun ?? capas.ramas?.educacion?.[clave]?.cve_mun ?? null;
    const ramas = {};
    for (const rama of RAMAS) {
      const entradaRama = capas.ramas?.[rama]?.[clave];
      ramas[rama] = {
        cve_mun: entradaRama?.cve_mun ?? cveMun,
        horizontes_disponibles: Array.isArray(entradaRama?.horizontes_disponibles)
          ? entradaRama.horizontes_disponibles
          : [],
        celdas: entradaRama?.celdas ?? {},
      };
    }
    porClave.set(clave, { cve_mun: cveMun, segmentos: entradaDemanda?.segmentos ?? {}, ramas });

    if (nivel === NIVEL.AGEB && cveMun) {
      if (!porCveMun.has(cveMun)) porCveMun.set(cveMun, []);
      porCveMun.get(cveMun).push(clave);
    }
  }

  if (nivel === NIVEL.AGEB) return { porCvegeo: porClave, porCveMun };
  // Nivel alcaldía: la propia clave del registro ya es el cve_mun.
  return { porCveMun: porClave };
}

/**
 * Adaptador del contrato v1.4 real: pasa `capas.demanda`/`capas.ramas` normalizadas (cada registro
 * de segmento/celda con sus horizontes válidos, sin inventar ninguno) y construye los índices.
 *
 * @param {object} json - JSON v1.4 crudo (ya validado con `validarContrato`).
 * @param {"ageb"|"alcaldia"} nivel
 */
export function adaptarV14(json, nivel) {
  validarContrato(json);
  const horizontesRaiz = json.horizontes.map((h) => h.clave);

  const demanda = {};
  for (const [clave, registro] of Object.entries(json.capas.demanda ?? {})) {
    const segmentos = {};
    for (const segmento of SEGMENTOS_DEMANDA) {
      segmentos[segmento] = normalizarRegistroCapa(registro?.segmentos?.[segmento], horizontesRaiz);
    }
    demanda[clave] = {
      cve_mun: registro.cve_mun,
      segmentos,
      distribucion_ageb: registro.distribucion_ageb ?? null,
    };
  }

  const ramas = {};
  for (const rama of RAMAS) {
    const horizontesRama = RAMAS_CON_PROYECCION.includes(rama) ? [...HORIZONTES_OFERTA] : [];
    const capaRama = {};
    for (const [clave, registro] of Object.entries(json.capas.ramas?.[rama] ?? {})) {
      const celdasOriginales = registro?.celdas ?? {};
      const celdas = {};
      for (const claveCelda of Object.keys(celdasOriginales)) {
        celdas[claveCelda] = normalizarRegistroCapa(celdasOriginales[claveCelda], horizontesRama);
      }
      capaRama[clave] = {
        cve_mun: registro.cve_mun,
        horizontes_disponibles: Array.isArray(registro?.horizontes_disponibles)
          ? registro.horizontes_disponibles
          : horizontesRama,
        celdas,
      };
    }
    ramas[rama] = capaRama;
  }

  const capas = { demanda, ramas };
  return {
    version: "1.4",
    generado: typeof json.generado === "string" ? json.generado : null,
    fecha_base: json.fecha_base,
    nivel,
    horizontes: json.horizontes,
    capas,
    distribucion_ageb: null, // vive dentro de cada registro de demanda en v1.4 (alcaldía).
    agregado_cdmx: json.agregado_cdmx ?? null,
    indices: construirIndices(capas, nivel),
  };
}

/**
 * Construye un documento v1.4-mínimo a partir de un contrato v1.2 (demanda/oferta de dos capas,
 * sin segmentos ni celdas de filtro, plan §2): degradación explícita, nunca inventa datos que el
 * contrato de origen no tiene.
 * - `capas.demanda[clave].segmentos.todas` = el único registro de demanda que traía v1.2; los
 *   demás 5 segmentos quedan `sin_datos` (motivo `"contrato_v1.2"`, no un código de §14.4 real:
 *   `textos.js` lo traduce a un mensaje de degradación, no de ausencia de dato).
 * - `capas.ramas.educacion[clave].celdas.todos` = el único registro de oferta que traía v1.2;
 *   salud/comercio/verde quedan enteramente `sin_datos` (la v1.2 no tenía esas ramas).
 *
 * @param {object} json - JSON v1.2 crudo (ya validado con `validarContrato`).
 * @param {"ageb"|"alcaldia"} nivel
 */
export function adaptarV12aV14(json, nivel) {
  validarContrato(json);
  const horizontesRaiz = json.horizontes.map((h) => h.clave);
  const horizontesOferta = (json.capas.oferta ? Object.values(json.capas.oferta)[0]?.horizontes_disponibles : null) ?? [
    "h1",
    "h3",
  ];

  const demandaOriginal = json.capas.demanda ?? {};
  const ofertaOriginal = json.capas.oferta ?? {};
  const claves = new Set([...Object.keys(demandaOriginal), ...Object.keys(ofertaOriginal)]);

  const demanda = {};
  const ramas = { educacion: {}, salud: {}, comercio: {}, verde: {} };
  for (const clave of claves) {
    const registroD = demandaOriginal[clave];
    const cveMun = registroD?.cve_mun ?? ofertaOriginal[clave]?.cve_mun ?? null;
    const segmentos = {};
    for (const segmento of SEGMENTOS_DEMANDA) {
      segmentos[segmento] =
        segmento === SEGMENTO_POR_OMISION
          ? normalizarRegistroCapa(registroD, horizontesRaiz)
          : { cve_mun: cveMun, n_obs: 0, motivo_sin_datos: "contrato_v1.2", nivel_base: null, serie: { t: [], valor: [] }, h: Object.fromEntries(horizontesRaiz.map((h) => [h, bloqueHSinDatos()])) };
    }
    demanda[clave] = { cve_mun: cveMun, segmentos, distribucion_ageb: null };

    const registroO = ofertaOriginal[clave];
    ramas.educacion[clave] = {
      cve_mun: cveMun,
      horizontes_disponibles: horizontesOferta,
      celdas: { [CLAVE_CELDA_UNICA]: normalizarRegistroCapa(registroO, horizontesOferta) },
    };
    for (const rama of ["salud", "comercio"]) {
      ramas[rama][clave] = { cve_mun: cveMun, horizontes_disponibles: horizontesOferta, celdas: {} };
    }
    ramas.verde[clave] = { cve_mun: cveMun, horizontes_disponibles: [], celdas: {} };
  }

  const capas = { demanda, ramas };
  return {
    version: "1.4",
    generado: typeof json.generado === "string" ? json.generado : null,
    fecha_base: json.fecha_base,
    nivel,
    horizontes: json.horizontes,
    capas,
    distribucion_ageb: null,
    agregado_cdmx: json.agregado_cdmx ?? null,
    indices: construirIndices(capas, nivel),
  };
}

/**
 * Contrato v1.1 (un solo horizonte `hU`) → forma v1.4-mínima, encadenando primero a un v1.2
 * sintético de un horizonte (plan §2: "v1.1 → v1.2 → v1.4-mínimo") y reutilizando `adaptarV12aV14`.
 *
 * @param {object} json - JSON v1.1 crudo (ya validado con `validarContrato`).
 * @param {"ageb"|"alcaldia"} nivel
 */
export function adaptarV11aV14(json, nivel) {
  validarContrato(json);
  const v12Sintetico = {
    version: "1.2",
    generado: json.generado,
    fecha_base: null,
    horizontes: [{ clave: CLAVE_HORIZONTE_UNICO, anios: null, fecha: json.horizonte }],
    capas: {
      demanda: Object.fromEntries(
        Object.entries(json.capas.demanda ?? {}).map(([clave, registro]) => [
          clave,
          { cve_mun: registro.cve_mun, n_obs: registro.n_obs, motivo_sin_datos: null, serie: null, nivel_base: null, h: { [CLAVE_HORIZONTE_UNICO]: normalizarBloqueH(registro) } },
        ]),
      ),
      oferta: Object.fromEntries(
        Object.entries(json.capas.oferta ?? {}).map(([clave, registro]) => [
          clave,
          { cve_mun: registro.cve_mun, n_obs: registro.n_obs, motivo_sin_datos: null, serie: null, nivel_base: null, horizontes_disponibles: [CLAVE_HORIZONTE_UNICO], h: { [CLAVE_HORIZONTE_UNICO]: normalizarBloqueH(registro) } },
        ]),
      ),
    },
  };
  return adaptarV12aV14(v12Sintetico, nivel);
}

/**
 * Devuelve el registro adaptado de un segmento (demanda) o celda (rama) para una clave dada,
 * aunque la clave esté ausente del JSON: en ese caso, `sin_datos` (nunca `undefined`).
 */
export function obtenerRegistroSegmento(datosAdaptados, clave, segmento) {
  return (
    datosAdaptados?.capas?.demanda?.[clave]?.segmentos?.[segmento] ??
    normalizarRegistroCapa(null, datosAdaptados?.horizontes?.map((h) => h.clave) ?? [])
  );
}

export function obtenerCeldasRama(datosAdaptados, clave, rama) {
  return datosAdaptados?.capas?.ramas?.[rama]?.[clave]?.celdas ?? {};
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

  if (json?.version === "1.4") return adaptarV14(json, nivel);
  if (json?.version === "1.2") return adaptarV12aV14(json, nivel);
  return adaptarV11aV14(json, nivel);
}
