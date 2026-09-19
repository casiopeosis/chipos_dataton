// frontend/js/estado.js
//
// Almacén observable de la sesión (plans/frontend_plan.md §1, F20): "estado.js es la única
// fuente de verdad de la sesión (vista, cve_mun, cvegeo, capa, horizonte activo, orden de tabla,
// drawer abierto, filtro de leyenda). Los módulos se suscriben (suscribir(fn)) y emiten acciones
// (despachar({tipo, ...})); sin variables globales."
//
// Este módulo NO dibuja nada ni gestiona la región viva de anuncios (spec §13): eso lo hacen
// otros módulos (F95) suscritos a este almacén. Tampoco decide qué es válido para `orden` más
// allá de su forma (eso lo define tabla.js/alcaldia.js); solo valida lo que puede validar sin
// conocer esos módulos: vista, cve_mun, cvegeo, capa y filtro (veredictos del contrato).
//
// Formato del hash (spec §1, §16.2): "#/alcaldia/007/ageb/0900700011234?capa=oferta&h=hU&
// orden=cambio&info=1&filtro=baja". Se parsea al cargar el módulo (incluida una recarga directa
// con cualquier hash) y se actualiza el hash cuando cambia el estado, con `history.replaceState`
// para cambios dentro de la sesión y `history.pushState` solo al entrar/salir de una alcaldía (o
// de un AGEB), que es lo que tiene sentido como "atrás" del navegador (§10.7, §10.8, checklist
// §16.2: "el botón atrás del navegador reproduce la misma secuencia").

import { CAPAS, VEREDICTOS_VALIDOS, CLAVE_HORIZONTE_UNICO } from "./config.js";

// ---------------------------------------------------------------------------------------------
// Vistas y estado por defecto
// ---------------------------------------------------------------------------------------------

export const VISTA = Object.freeze({
  CIUDAD: "ciudad",
  ALCALDIA: "alcaldia",
  AGEB: "ageb",
});

/** Orden por defecto de la tabla de vista general (spec §7.1: "por cambio ascendente"). */
const ORDEN_POR_DEFECTO = "cambio";

/** Estado con el que arranca la sesión si no hay hash, o si el hash es inválido/incompleto. */
export const ESTADO_POR_DEFECTO = Object.freeze({
  vista: VISTA.CIUDAD,
  cve_mun: null,
  cvegeo: null,
  capa: "demanda",
  horizonte: CLAVE_HORIZONTE_UNICO,
  orden: ORDEN_POR_DEFECTO,
  drawerAbierto: false,
  filtroLeyenda: null,
});

/** Tipos de acción reconocidos por `despachar` (evita cadenas mágicas sueltas en otros módulos). */
export const ACCIONES = Object.freeze({
  IR_A_CIUDAD: "ir_a_ciudad",
  IR_A_ALCALDIA: "ir_a_alcaldia",
  IR_A_AGEB: "ir_a_ageb",
  VOLVER: "volver",
  CAMBIAR_CAPA: "cambiar_capa",
  CAMBIAR_HORIZONTE: "cambiar_horizonte",
  CAMBIAR_ORDEN: "cambiar_orden",
  ABRIR_DRAWER: "abrir_drawer",
  CERRAR_DRAWER: "cerrar_drawer",
  ALTERNAR_DRAWER: "alternar_drawer",
  CAMBIAR_FILTRO: "cambiar_filtro",
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

/** Hoy solo existe la clave "hU" (adaptador v1.1→v1.2), pero el resto del código admite h3/h5/h7. */
function esHorizonteValido(valor) {
  return typeof valor === "string" && /^h[0-9A-Za-z]+$/.test(valor);
}

/** Forma de columna de orden: token corto en minúsculas; el significado lo definen tabla/alcaldia.js. */
function esOrdenValido(valor) {
  return typeof valor === "string" && valor.length > 0 && valor.length <= 40 && /^[a-z0-9_-]+$/.test(valor);
}

function esCapaValida(valor) {
  return CAPAS.includes(valor);
}

function esFiltroValido(valor) {
  // El filtro de leyenda solo tiene sentido sobre veredictos, no sobre "sin_datos" (§10.4: filtra
  // categorías con conteo); aun así se admite cualquier veredicto válido del contrato.
  return VEREDICTOS_VALIDOS.includes(valor);
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

  const estado = { ...ESTADO_POR_DEFECTO };

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

  const capa = parametros.get("capa");
  if (esCapaValida(capa)) estado.capa = capa;

  const horizonte = parametros.get("h");
  if (esHorizonteValido(horizonte)) estado.horizonte = horizonte;

  const orden = parametros.get("orden");
  if (esOrdenValido(orden)) estado.orden = orden;

  estado.drawerAbierto = parametros.get("info") === "1";

  const filtro = parametros.get("filtro");
  if (esFiltroValido(filtro)) estado.filtroLeyenda = filtro;

  return estado;
}

/**
 * Serializa un estado completo al formato de hash del spec. Siempre incluye `capa`, `h` y
 * `orden` (para que el enlace sea autodescriptivo y compartible, spec §1 "analistas... enlaces
 * compartibles"); `info` y `filtro` solo aparecen cuando están activos.
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
  parametros.set("capa", estado.capa);
  parametros.set("h", estado.horizonte);
  parametros.set("orden", estado.orden);
  if (estado.drawerAbierto) parametros.set("info", "1");
  if (estado.filtroLeyenda) parametros.set("filtro", estado.filtroLeyenda);

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
      // Un nivel a la vez (spec §10.7-§10.8: Esc y "atrás" retroceden AGEB→alcaldía→general).
      if (estado.vista === VISTA.AGEB) return { ...estado, vista: VISTA.ALCALDIA, cvegeo: null };
      if (estado.vista === VISTA.ALCALDIA) return { ...estado, vista: VISTA.CIUDAD, cve_mun: null };
      return estado;
    }

    case ACCIONES.CAMBIAR_CAPA: {
      if (!esCapaValida(accion.capa)) return estado;
      return { ...estado, capa: accion.capa };
    }

    case ACCIONES.CAMBIAR_HORIZONTE: {
      if (!esHorizonteValido(accion.horizonte)) return estado;
      return { ...estado, horizonte: accion.horizonte };
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
  // que debe poder deshacerse con el botón "atrás" del navegador. Todo lo demás (capa,
  // horizonte, orden, drawer, filtro) es replaceState para no inflar el historial.
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
