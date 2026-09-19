// frontend/js/config.js
//
// Rutas de datos, versión de contrato esperada y constantes técnicas de la
// UI (plans/frontend_plan.md §1, F15). No incluye textos visibles: esos
// viven centralizados en js/textos.js (F30).

/**
 * Versiones del contrato que el frontend sabe leer (CLAUDE.md → "Contrato de salida").
 * "1.1" = un solo horizonte (el que producía el backend hasta ahora, sigue vivo como modo de
 * degradación probado con `?mock=v11`). "1.2" = varios horizontes (`h3`/`h5`/`h7`) más `fecha_base`,
 * `serie`, `distribucion_ageb` y `agregado_cdmx` (`plans/frontend_specs.md` §17); pasa a ser el
 * fixture principal de desarrollo (`?mock=1`/sin parámetro). Cualquier otro valor de `version` se
 * rechaza en `api.js#validarContrato` con `codigo: "version_incompatible"`.
 */
export const VERSIONES_CONTRATO_ACEPTADAS = Object.freeze(["1.1", "1.2"]);

export const NIVEL = Object.freeze({
  AGEB: "ageb",
  ALCALDIA: "alcaldia",
});

/** Nombres de capa del contrato v1.1 (nunca incluye "brecha": ver plan §2). */
export const CAPAS = Object.freeze(["demanda", "oferta"]);

export const VEREDICTOS_VALIDOS = Object.freeze(["sube", "se_mantiene", "baja", "sin_datos"]);

export const CONFIANZAS_VALIDAS = Object.freeze(["alta", "media", "baja"]);

/** Clave de horizonte único que usa el adaptador v1.1→v1.2 (plan §2). */
export const CLAVE_HORIZONTE_UNICO = "hU";

const RUTA_BASE_MOCK = "mock/";
const RUTA_BASE_DATOS = "data/";

const ARCHIVO_POR_NIVEL = Object.freeze({
  [NIVEL.AGEB]: "prediccion_ageb.json",
  [NIVEL.ALCALDIA]: "prediccion_alcaldia.json",
});

/** Archivo `1.9` deliberadamente inválido, para el estado de error "versión incompatible". */
const ARCHIVO_AGEB_VERSION_INVALIDA = "prediccion_ageb_v11_invalido.json";

/** v1.1 real (un solo horizonte), para probar la degradación del slider (`?mock=v11`). */
const ARCHIVO_POR_NIVEL_V11 = Object.freeze({
  [NIVEL.AGEB]: "prediccion_ageb_v11.json",
  [NIVEL.ALCALDIA]: "prediccion_alcaldia_v11.json",
});

/**
 * Valores reconocidos del parámetro `?mock=` (plan §6). `V11` y `VERSION_INVALIDA` solían
 * compartir el nombre de query string `"v11"`: ahora `V11` sirve un contrato v1.1 REAL y válido
 * (para probar el slider deshabilitado) y `VERSION_INVALIDA` sirve el archivo `1.9` deliberadamente
 * inválido (para probar el estado de error "versión incompatible"), bajo `?mock=version_invalida`.
 */
export const VALORES_MOCK = Object.freeze({
  BASE: "1",
  ERROR: "error",
  V11: "v11",
  VERSION_INVALIDA: "version_invalida",
  VACIO: "vacio",
  LENTO: "lento",
});

/** Demora artificial de `?mock=lento` (plan §6: "3-5 s"). */
export const DEMORA_MOCK_LENTO_MS = 3500;

/** Lee `?mock=` de la URL actual (o de la ubicación dada, para pruebas). */
export function leerParametroMock(ubicacion) {
  const loc = ubicacion ?? (typeof window !== "undefined" ? window.location : undefined);
  if (!loc || typeof loc.search !== "string") return null;
  return new URLSearchParams(loc.search).get("mock");
}

/**
 * Ruta relativa (desde `frontend/`) al archivo de datos correspondiente.
 * Sin `mock` (o `mock` vacío/null) se sirven los datos reales de `data/`
 * (F105); con cualquier valor de `?mock=` se sirven los mocks de `mock/`.
 */
export function rutaDatos(nivel, mock) {
  if (!Object.prototype.hasOwnProperty.call(ARCHIVO_POR_NIVEL, nivel)) {
    throw new RangeError(`nivel desconocido: ${String(nivel)}`);
  }
  const usaMock = mock !== null && mock !== undefined && mock !== "";
  const base = usaMock ? RUTA_BASE_MOCK : RUTA_BASE_DATOS;

  if (usaMock && mock === VALORES_MOCK.VERSION_INVALIDA && nivel === NIVEL.AGEB) {
    return `${base}${ARCHIVO_AGEB_VERSION_INVALIDA}`;
  }
  if (usaMock && mock === VALORES_MOCK.V11) {
    return `${base}${ARCHIVO_POR_NIVEL_V11[nivel]}`;
  }
  return `${base}${ARCHIVO_POR_NIVEL[nivel]}`;
}
