// frontend/js/config.js
//
// Rutas de datos, versión de contrato esperada y constantes técnicas de la
// UI (plans/frontend_plan.md §1, F15). No incluye textos visibles: esos
// viven centralizados en js/textos.js (F30).

/** Versión del contrato v1.1 que produce el backend (CLAUDE.md → "Contrato de salida"). */
export const VERSION_CONTRATO_ESPERADA = "1.1";

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

const ARCHIVO_AGEB_VERSION_INVALIDA = "prediccion_ageb_v11_invalido.json";

/** Valores reconocidos del parámetro `?mock=` (plan §6). */
export const VALORES_MOCK = Object.freeze({
  BASE: "1",
  ERROR: "error",
  VERSION_INVALIDA: "v11",
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
  const archivo =
    usaMock && mock === VALORES_MOCK.VERSION_INVALIDA && nivel === NIVEL.AGEB
      ? ARCHIVO_AGEB_VERSION_INVALIDA
      : ARCHIVO_POR_NIVEL[nivel];
  return `${base}${archivo}`;
}
