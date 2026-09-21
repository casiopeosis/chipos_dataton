// frontend/js/estado.js
//
// Almacén observable de la sesión (plans/frontend_plan.md §1, F20): "estado.js es la única
// fuente de verdad de la sesión". Los módulos se suscriben (suscribir(fn)) y emiten acciones
// (despachar({tipo, ...})); sin variables globales.
//
// Este módulo NO dibuja nada ni gestiona la región viva de anuncios (spec §13): eso lo hacen
// otros módulos (F95) suscritos a este almacén. Tampoco decide qué celdas existen por rama más
// allá de la forma de `filtros` (eso lo define filtros.js/config.js); solo valida lo que puede
// validar sin conocer esos módulos: vista, cve_mun, cvegeo, vistaMapa, población, horizonte,
// búsqueda, pesos, umbral de riesgo y comparar.
//
// Formato del hash (plans/frontend_plan.md §1; el selector de "¿qué buscar?" -oportunidad/
// disponibilidad- se retiró del frontend: ya no hay `busqueda=` en el hash, la sesión siempre
// busca oportunidad, `ESTADO_POR_DEFECTO.busqueda` es una constante que ningún flujo cambia):
// "#/alcaldia/007/ageb/0900700011234?vista=salud&h=h3&pob=primaria&
// pesos=4.5.3.2&filtros=educacion:guarderia__publico,preescolar__publico|salud:...&riesgo=0.8&
// orden=oportunidad&info=1&comparar=007.010". Se parsea al cargar el módulo (incluida una recarga
// directa con cualquier hash) y se actualiza el hash cuando cambia el estado, con
// `history.replaceState` para cambios dentro de la sesión y `history.pushState` solo al
// entrar/salir de una alcaldía (o de un AGEB), que es lo que tiene sentido como "atrás" del
// navegador.

import { RAMAS, SEGMENTOS_DEMANDA, SEGMENTO_POR_OMISION, ORDEN_HORIZONTES } from "./config.js";

// ---------------------------------------------------------------------------------------------
// Vistas y estado por defecto
// ---------------------------------------------------------------------------------------------

export const VISTA = Object.freeze({
  CIUDAD: "ciudad",
  ALCALDIA: "alcaldia",
  AGEB: "ageb",
});

/** Vista de mapa: la general (índice compuesto) o una de las 4 ramas individuales (spec §9). */
export const VISTA_MAPA = Object.freeze({
  GENERAL: "general",
  EDUCACION: "educacion",
  SALUD: "salud",
  COMERCIO: "comercio",
  VERDE: "verde",
});

/** Tipo de búsqueda (spec §5.5): qué extremo del ranking se muestra primero. */
export const BUSQUEDA = Object.freeze({
  OPORTUNIDAD: "oportunidad",
  DISPONIBILIDAD: "disponibilidad",
});

/** Orden por defecto del ranking de la vista general (spec §7.1). */
const ORDEN_POR_DEFECTO = "oportunidad";

const PESO_MINIMO = 1;
const PESO_MAXIMO = 5;
const PESO_POR_DEFECTO = 3;

function pesosPorDefecto() {
  return { educacion: PESO_POR_DEFECTO, salud: PESO_POR_DEFECTO, comercio: PESO_POR_DEFECTO, verde: PESO_POR_DEFECTO };
}

/** `[]` = "Todos" (sin filtro, todas las celdas de esa rama cuentan) -- nunca `null`/`undefined`,
 * para que `composicion.js` pueda iterar directamente. */
function filtrosPorDefecto() {
  return { educacion: [], salud: [], comercio: [], verde: [] };
}

/** Estado con el que arranca la sesión si no hay hash, o si el hash es inválido/incompleto. */
export const ESTADO_POR_DEFECTO = Object.freeze({
  vista: VISTA.CIUDAD,
  cve_mun: null,
  cvegeo: null,
  vistaMapa: VISTA_MAPA.GENERAL,
  poblacion: SEGMENTO_POR_OMISION,
  horizonte: "h3",
  busqueda: BUSQUEDA.OPORTUNIDAD,
  pesos: Object.freeze(pesosPorDefecto()),
  filtros: Object.freeze(filtrosPorDefecto()),
  umbralRiesgo: null, // sin filtrar por nivel de riesgo (spec §10.12).
  orden: ORDEN_POR_DEFECTO,
  drawerAbierto: false,
  filtroLeyenda: null, // tercil activo del realce de leyenda: "alta"|"media"|"baja"|"sin_datos".
  comparando: null, // [cve_mun, cve_mun] | null (spec §10.13).
});

/** Tipos de acción reconocidos por `despachar` (evita cadenas mágicas sueltas en otros módulos). */
export const ACCIONES = Object.freeze({
  IR_A_CIUDAD: "ir_a_ciudad",
  IR_A_ALCALDIA: "ir_a_alcaldia",
  IR_A_AGEB: "ir_a_ageb",
  VOLVER: "volver",
  CAMBIAR_VISTA_MAPA: "cambiar_vista_mapa",
  CAMBIAR_POBLACION: "cambiar_poblacion",
  CAMBIAR_HORIZONTE: "cambiar_horizonte",
  CAMBIAR_PESO: "cambiar_peso",
  RESTABLECER_PESOS: "restablecer_pesos",
  CAMBIAR_FILTRO_RAMA: "cambiar_filtro_rama",
  RESTABLECER_FILTROS: "restablecer_filtros",
  CAMBIAR_UMBRAL_RIESGO: "cambiar_umbral_riesgo",
  CAMBIAR_ORDEN: "cambiar_orden",
  ABRIR_DRAWER: "abrir_drawer",
  CERRAR_DRAWER: "cerrar_drawer",
  ALTERNAR_DRAWER: "alternar_drawer",
  CAMBIAR_FILTRO: "cambiar_filtro",
  COMPARAR: "comparar",
  DEJAR_DE_COMPARAR: "dejar_de_comparar",
});

// ---------------------------------------------------------------------------------------------
// Validación de forma (sin lanzar nunca: cualquier valor fuera de rango se ignora o degrada)
// ---------------------------------------------------------------------------------------------

/** `CVE_MUN`: 3 dígitos (CLAUDE.md: alcaldía = CVE_MUN "002"-"017"; se admite el patrón general). */
function esCveMunValida(valor) {
  return typeof valor === "string" && /^\d{3}$/.test(valor);
}

/** `CVEGEO`: 13 dígitos (CVE_ENT 2 + CVE_MUN 3 + CVE_LOC 4 + CVE_AGEB 4, CLAUDE.md). */
function esCvegeoValida(valor) {
  return typeof valor === "string" && /^\d{13}$/.test(valor);
}

function esHorizonteValido(valor) {
  return typeof valor === "string" && /^h[0-9A-Za-z]+$/.test(valor);
}

/** Forma de columna de orden: token corto en minúsculas; el significado lo define ranking.js/alcaldia.js. */
function esOrdenValido(valor) {
  return typeof valor === "string" && valor.length > 0 && valor.length <= 40 && /^[a-z0-9_-]+$/.test(valor);
}

function esVistaMapaValida(valor) {
  return Object.values(VISTA_MAPA).includes(valor);
}

function esPoblacionValida(valor) {
  return SEGMENTOS_DEMANDA.includes(valor);
}

function esPesoValido(valor) {
  return Number.isInteger(valor) && valor >= PESO_MINIMO && valor <= PESO_MAXIMO;
}

function esUmbralRiesgoValido(valor) {
  return typeof valor === "number" && Number.isFinite(valor) && valor >= 0 && valor <= 1;
}

const TERCILES_VALIDOS = Object.freeze(["alta", "media", "baja", "sin_datos"]);
function esFiltroValido(valor) {
  return TERCILES_VALIDOS.includes(valor);
}

/** Lista de claves de celda: cadenas no vacías, sin duplicados exigidos (se deduplican al leer). */
function esListaCeldasValida(valor) {
  return Array.isArray(valor) && valor.every((c) => typeof c === "string" && c.length > 0);
}

// ---------------------------------------------------------------------------------------------
// Funciones puras: parseo y serialización del hash, y el reductor. Se exportan para que
// `tests/pruebas.js` las pruebe sin tocar `window.location` real.
// ---------------------------------------------------------------------------------------------

/**
 * Parsea un hash de URL (con o sin "#" inicial) a un estado completo. Nunca lanza: cualquier
 * segmento o parámetro ausente, corrupto o fuera del conjunto válido degrada esa sola pieza a su
 * valor por defecto (criterio de aceptación F20: "hash inválido o incompleto degrada con gracia").
 *
 * @param {string|null|undefined} hashCrudo
 * @returns {typeof ESTADO_POR_DEFECTO}
 */
export function analizarHash(hashCrudo) {
  const cadena = typeof hashCrudo === "string" ? hashCrudo : "";
  const sinAlmohadilla = cadena.startsWith("#") ? cadena.slice(1) : cadena;
  const indiceInterrogacion = sinAlmohadilla.indexOf("?");
  const rutaCruda = indiceInterrogacion === -1 ? sinAlmohadilla : sinAlmohadilla.slice(0, indiceInterrogacion);
  const queryCruda = indiceInterrogacion === -1 ? "" : sinAlmohadilla.slice(indiceInterrogacion + 1);
  const segmentos = rutaCruda.split("/").filter((segmento) => segmento !== "");

  const estado = { ...ESTADO_POR_DEFECTO, pesos: pesosPorDefecto(), filtros: filtrosPorDefecto() };

  if (segmentos[0] === "alcaldia" && esCveMunValida(segmentos[1])) {
    estado.vista = VISTA.ALCALDIA;
    estado.cve_mun = segmentos[1];
    if (segmentos[2] === "ageb" && esCvegeoValida(segmentos[3])) {
      estado.vista = VISTA.AGEB;
      estado.cvegeo = segmentos[3];
    }
  }

  let parametros;
  try {
    parametros = new URLSearchParams(queryCruda);
  } catch {
    parametros = new URLSearchParams();
  }

  const vistaMapa = parametros.get("vista");
  if (esVistaMapaValida(vistaMapa)) estado.vistaMapa = vistaMapa;

  const poblacion = parametros.get("pob");
  if (esPoblacionValida(poblacion)) estado.poblacion = poblacion;

  const horizonte = parametros.get("h");
  if (esHorizonteValido(horizonte)) estado.horizonte = horizonte;

  const pesosCrudo = parametros.get("pesos");
  if (typeof pesosCrudo === "string") {
    const partes = pesosCrudo.split(".").map((p) => Number(p));
    if (partes.length === RAMAS.length && partes.every(esPesoValido)) {
      RAMAS.forEach((rama, indice) => {
        estado.pesos[rama] = partes[indice];
      });
    }
  }

  const filtrosCrudo = parametros.get("filtros");
  if (typeof filtrosCrudo === "string" && filtrosCrudo.length > 0) {
    for (const bloque of filtrosCrudo.split("|")) {
      const separador = bloque.indexOf(":");
      if (separador === -1) continue;
      const rama = bloque.slice(0, separador);
      if (!RAMAS.includes(rama)) continue;
      const celdas = bloque
        .slice(separador + 1)
        .split(",")
        .filter((c) => c.length > 0);
      if (esListaCeldasValida(celdas)) estado.filtros[rama] = celdas;
    }
  }

  const riesgo = parametros.get("riesgo");
  if (riesgo !== null) {
    const numero = Number(riesgo);
    if (esUmbralRiesgoValido(numero)) estado.umbralRiesgo = numero;
  }

  const orden = parametros.get("orden");
  if (esOrdenValido(orden)) estado.orden = orden;

  estado.drawerAbierto = parametros.get("info") === "1";

  const filtro = parametros.get("filtro");
  if (esFiltroValido(filtro)) estado.filtroLeyenda = filtro;

  const comparar = parametros.get("comparar");
  if (typeof comparar === "string") {
    const [a, b] = comparar.split(".");
    if (esCveMunValida(a) && esCveMunValida(b) && a !== b) estado.comparando = [a, b];
  }

  return estado;
}

/**
 * Serializa un estado completo al formato de hash del spec. Siempre incluye `vista`, `h`, `pob`,
 * `busqueda`, `pesos` y `orden` (para que el enlace sea autodescriptivo y compartible); `filtros`,
 * `riesgo`, `info`, `filtro` y `comparar` solo aparecen cuando están activos (distintos de su
 * valor por omisión).
 *
 * @param {typeof ESTADO_POR_DEFECTO} estado
 * @returns {string} incluye el "#" inicial.
 */
export function serializarHash(estado) {
  let ruta = "/";
  if (estado.vista === VISTA.ALCALDIA || estado.vista === VISTA.AGEB) {
    ruta = `/alcaldia/${estado.cve_mun}`;
    if (estado.vista === VISTA.AGEB) {
      ruta += `/ageb/${estado.cvegeo}`;
    }
  }

  const parametros = new URLSearchParams();
  parametros.set("vista", estado.vistaMapa);
  parametros.set("h", estado.horizonte);
  parametros.set("pob", estado.poblacion);
  parametros.set("pesos", RAMAS.map((r) => estado.pesos[r]).join("."));

  const bloquesFiltros = RAMAS.filter((r) => estado.filtros[r]?.length > 0).map(
    (r) => `${r}:${estado.filtros[r].join(",")}`,
  );
  if (bloquesFiltros.length > 0) parametros.set("filtros", bloquesFiltros.join("|"));

  if (estado.umbralRiesgo !== null) parametros.set("riesgo", String(estado.umbralRiesgo));
  parametros.set("orden", estado.orden);
  if (estado.drawerAbierto) parametros.set("info", "1");
  if (estado.filtroLeyenda) parametros.set("filtro", estado.filtroLeyenda);
  if (estado.comparando) parametros.set("comparar", estado.comparando.join("."));

  return `#${ruta}?${parametros.toString()}`;
}

/** Reductor puro: `(estado, accion) -> estado`. Nunca lanza; una acción inválida no cambia nada. */
export function reducir(estado, accion) {
  if (!accion || typeof accion.tipo !== "string") return estado;

  switch (accion.tipo) {
    case ACCIONES.IR_A_CIUDAD:
      return { ...estado, vista: VISTA.CIUDAD, cve_mun: null, cvegeo: null };

    case ACCIONES.IR_A_ALCALDIA: {
      if (!esCveMunValida(accion.cve_mun)) return estado;
      return { ...estado, vista: VISTA.ALCALDIA, cve_mun: accion.cve_mun, cvegeo: null };
    }

    case ACCIONES.IR_A_AGEB: {
      const cveMun = accion.cve_mun ?? estado.cve_mun;
      if (!esCveMunValida(cveMun) || !esCvegeoValida(accion.cvegeo)) return estado;
      return { ...estado, vista: VISTA.AGEB, cve_mun: cveMun, cvegeo: accion.cvegeo };
    }

    case ACCIONES.VOLVER: {
      // Un nivel a la vez: Esc y "atrás" retroceden AGEB→alcaldía→general.
      if (estado.vista === VISTA.AGEB) return { ...estado, vista: VISTA.ALCALDIA, cvegeo: null };
      if (estado.vista === VISTA.ALCALDIA) return { ...estado, vista: VISTA.CIUDAD, cve_mun: null };
      return estado;
    }

    case ACCIONES.CAMBIAR_VISTA_MAPA: {
      if (!esVistaMapaValida(accion.vistaMapa)) return estado;
      return { ...estado, vistaMapa: accion.vistaMapa };
    }

    case ACCIONES.CAMBIAR_POBLACION: {
      if (!esPoblacionValida(accion.poblacion)) return estado;
      return { ...estado, poblacion: accion.poblacion };
    }

    case ACCIONES.CAMBIAR_HORIZONTE: {
      if (!esHorizonteValido(accion.horizonte)) return estado;
      return { ...estado, horizonte: accion.horizonte };
    }

    case ACCIONES.CAMBIAR_PESO: {
      if (!RAMAS.includes(accion.rama) || !esPesoValido(accion.peso)) return estado;
      return { ...estado, pesos: { ...estado.pesos, [accion.rama]: accion.peso } };
    }

    case ACCIONES.RESTABLECER_PESOS:
      return { ...estado, pesos: pesosPorDefecto() };

    case ACCIONES.CAMBIAR_FILTRO_RAMA: {
      if (!RAMAS.includes(accion.rama) || !esListaCeldasValida(accion.celdas)) return estado;
      return { ...estado, filtros: { ...estado.filtros, [accion.rama]: accion.celdas } };
    }

    case ACCIONES.RESTABLECER_FILTROS:
      return { ...estado, filtros: filtrosPorDefecto() };

    case ACCIONES.CAMBIAR_UMBRAL_RIESGO: {
      if (accion.umbral === null) return estado.umbralRiesgo === null ? estado : { ...estado, umbralRiesgo: null };
      if (!esUmbralRiesgoValido(accion.umbral)) return estado;
      return { ...estado, umbralRiesgo: accion.umbral };
    }

    case ACCIONES.CAMBIAR_ORDEN: {
      if (!esOrdenValido(accion.orden)) return estado;
      return { ...estado, orden: accion.orden };
    }

    case ACCIONES.ABRIR_DRAWER:
      return estado.drawerAbierto ? estado : { ...estado, drawerAbierto: true };

    case ACCIONES.CERRAR_DRAWER:
      return estado.drawerAbierto ? { ...estado, drawerAbierto: false } : estado;

    case ACCIONES.ALTERNAR_DRAWER:
      return { ...estado, drawerAbierto: !estado.drawerAbierto };

    case ACCIONES.CAMBIAR_FILTRO: {
      const filtro = accion.filtro;
      if (filtro === null || filtro === undefined) {
        return estado.filtroLeyenda === null ? estado : { ...estado, filtroLeyenda: null };
      }
      if (!esFiltroValido(filtro)) return estado;
      // Pulsar la misma categoría activa la desactiva (spec §10.4).
      return { ...estado, filtroLeyenda: estado.filtroLeyenda === filtro ? null : filtro };
    }

    case ACCIONES.COMPARAR: {
      if (!esCveMunValida(accion.cve_mun_a) || !esCveMunValida(accion.cve_mun_b)) return estado;
      if (accion.cve_mun_a === accion.cve_mun_b) return estado;
      return { ...estado, comparando: [accion.cve_mun_a, accion.cve_mun_b] };
    }

    case ACCIONES.DEJAR_DE_COMPARAR:
      return estado.comparando === null ? estado : { ...estado, comparando: null };

    default:
      return estado;
  }
}

// ---------------------------------------------------------------------------------------------
// Almacén (singleton del módulo: estado y suscriptores viven en el cierre, nunca en `window`
// ni en ninguna variable de ámbito global).
// ---------------------------------------------------------------------------------------------

function ubicacionActual() {
  return typeof window !== "undefined" ? window.location : null;
}

function historialActual() {
  return typeof window !== "undefined" ? window.history : null;
}

let estadoActual = analizarHash(ubicacionActual()?.hash ?? "");
const suscriptores = new Set();

function notificar() {
  for (const fn of suscriptores) fn(estadoActual);
}

/** Refleja el estado en el hash de la URL, con la estrategia de historial del spec §1/§16.2. */
function sincronizarHistorial(estadoAnterior, estadoNuevo) {
  const historia = historialActual();
  const ubicacion = ubicacionActual();
  if (!historia || !ubicacion) return;

  const hashNuevo = serializarHash(estadoNuevo);
  const hashActual = ubicacion.hash && ubicacion.hash !== "" ? ubicacion.hash : "#/";
  if (hashNuevo === hashActual) return;

  const url = `${ubicacion.pathname}${ubicacion.search}${hashNuevo}`;
  // pushState solo al entrar/salir de una alcaldía o de un AGEB (cambia `vista`): es lo único
  // que debe poder deshacerse con el botón "atrás" del navegador. Todo lo demás es replaceState
  // para no inflar el historial.
  if (estadoAnterior.vista !== estadoNuevo.vista) {
    historia.pushState(estadoNuevo, "", url);
  } else {
    historia.replaceState(estadoNuevo, "", url);
  }
}

/**
 * Emite una acción `{tipo, ...datos}` contra el almacén. Sin retorno: quien necesite el estado
 * resultante se suscribe con `suscribir`, o lo lee con `obtenerEstado`.
 */
export function despachar(accion) {
  const estadoAnterior = estadoActual;
  const estadoNuevo = reducir(estadoAnterior, accion);
  if (estadoNuevo === estadoAnterior) return;
  estadoActual = estadoNuevo;
  sincronizarHistorial(estadoAnterior, estadoNuevo);
  notificar();
}

/**
 * Suscribe `fn(estado)` a todo cambio de estado. Devuelve una función para cancelar la
 * suscripción (equivalente al patrón `unsubscribe` habitual, sin depender de nada global).
 */
export function suscribir(fn) {
  if (typeof fn !== "function") throw new TypeError("suscribir(fn): fn debe ser una función");
  suscriptores.add(fn);
  return () => suscriptores.delete(fn);
}

/** Lectura puntual del estado actual (p. ej. al montar un componente, antes de la primera notificación). */
export function obtenerEstado() {
  return estadoActual;
}

// Navegación por el historial del navegador (atrás/adelante): re-sincroniza el estado desde el
// hash resultante, sin volver a empujar historial (el navegador ya lo movió).
if (typeof window !== "undefined") {
  window.addEventListener("popstate", () => {
    const estadoAnterior = estadoActual;
    const estadoDesdeHash = analizarHash(window.location.hash);
    if (JSON.stringify(estadoDesdeHash) === JSON.stringify(estadoAnterior)) return;
    estadoActual = estadoDesdeHash;
    notificar();
  });
}
