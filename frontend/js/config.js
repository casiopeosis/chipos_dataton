// frontend/js/config.js
//
// Rutas de datos, versión de contrato esperada y constantes técnicas de la
// UI (plans/frontend_plan.md §1, F15). No incluye textos visibles: esos
// viven centralizados en js/textos.js (F30).

/**
 * Versiones del contrato que el frontend sabe leer (CLAUDE.md → "Contrato de salida").
 * "1.4" (`plans/backend_plan.md` §7, `plans/frontend_specs.md` §17.2) es el contrato de trabajo
 * principal: `capas.demanda` por segmento de población objetivo + `capas.ramas.{educacion,salud,
 * comercio,verde}` por celda de filtro, sin `capas.oferta` ni `capas.brecha`. "1.1"/"1.2" (un solo
 * horizonte / horizontes sin segmentos ni ramas) se conservan como cadena de degradación de dos
 * pasos (`plans/frontend_plan.md` §2): el frontend sigue funcionando con capacidades reducidas si
 * el backend algún día solo pudiera entregar una de esas versiones. Cualquier otro valor de
 * `version` se rechaza en `api.js#validarContrato` con `codigo: "version_incompatible"`.
 */
export const VERSIONES_CONTRATO_ACEPTADAS = Object.freeze(["1.4", "1.2", "1.1"]);

export const NIVEL = Object.freeze({
  AGEB: "ageb",
  ALCALDIA: "alcaldia",
});

/** Horizontes que reporta la capa `demanda` (docs/metodologia.md §1.1, contrato v1.4). */
export const ORDEN_HORIZONTES = Object.freeze(["h1", "h3", "h5"]);

/** Horizontes que reportan las ramas con proyección (educación/salud/comercio); verde no tiene
 * ninguno (`plans/frontend_specs.md` §17.3, metodología §10.1). */
export const HORIZONTES_OFERTA = Object.freeze(["h1", "h3"]);

/** Los 6 segmentos de población objetivo (`panel.SEGMENTOS_DEMANDA`, metodología §1.1). `todas`
 * (0–17) es el valor por omisión del selector -- Habitancia ya no tiene como alcance "0-14". */
export const SEGMENTOS_DEMANDA = Object.freeze([
  "todas",
  "primera_infancia",
  "preescolar",
  "primaria",
  "secundaria",
  "adolescencia",
]);
export const SEGMENTO_POR_OMISION = "todas";

/** Las 4 ramas del contrato v1.4, mismo orden fijo que el hash de pesos (`estado.js`) y
 * `composicion.js#RAMAS`. */
export const RAMAS = Object.freeze(["educacion", "salud", "comercio", "verde"]);

/** Ramas con proyección temporal (tienen `h`); verde no (`plans/frontend_specs.md` §17.3). */
export const RAMAS_CON_PROYECCION = Object.freeze(["educacion", "salud", "comercio"]);

export const VEREDICTOS_VALIDOS = Object.freeze(["sube", "se_mantiene", "baja", "sin_datos"]);

export const CONFIANZAS_VALIDAS = Object.freeze(["alta", "media", "baja"]);

/** Clave de horizonte único que usa el adaptador v1.1→v1.4 (plan §2). */
export const CLAVE_HORIZONTE_UNICO = "hU";

/** Clave de celda única que usa el adaptador v1.1/v1.2→v1.4 (plan §2): el contrato heredado solo
 * traía una capa `oferta` sin celdas de filtro, así que se mapea a una sola celda "todos" dentro
 * de la rama `educacion` (la única rama que existía antes) -- salud/comercio/verde quedan
 * `sin_datos` en el camino degradado, nunca inventadas. */
export const CLAVE_CELDA_UNICA = "todos";

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
