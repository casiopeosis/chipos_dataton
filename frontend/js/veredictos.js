// frontend/js/veredictos.js
//
// resumirVeredictos(registros) — regla del "veredicto general" (plans/frontend_specs.md §6.2,
// reutilizada tal cual en §6.5 para la vista de alcaldía). Función pura, sin DOM ni textos: solo
// cuenta y decide el escenario. `js/titular.js` y `js/tabla.js` (F40) comparten esta misma
// función para que titular y tabla nunca diverjan (invariante probada en
// frontend/tests/pruebas_veredictos.js).
//
// `registros` es cualquier lista de objetos con `.veredicto` (uno de VEREDICTOS_VALIDOS) y,
// opcionalmente, `.confianza`. Ya deben venir resueltos al horizonte activo (p. ej.
// `registro.h[horizonteActivo]`, ver adaptador de api.js): este módulo no sabe nada de
// horizontes ni de la forma v1.1/v1.2 del contrato.

import { VEREDICTOS_VALIDOS } from "./config.js";

/** Umbrales del spec §6.2 (decisión vigente del equipo, plan §3-4: no se parametrizan). */
export const UMBRALES_VEREDICTO_GENERAL = Object.freeze({
  V_MINIMO: 8, // escenario 1: menos de la mitad de 16 no permite generalizar
  MAYORIA: 0.6, // escenarios 2 y 3: predominio de baja/sube
  CONTRAPESO: 0.15, // tope del veredicto opuesto para que el predominio cuente como "claro"
  POLARIZADO: 0.25, // escenario 4: dos bloques opuestos de tamaño comparable
  MAYORIA_MANTIENE: 0.5, // escenario 5: estabilidad mayoritaria
  CONFIANZA_BAJA_DOMINANTE: 0.5, // matiz §6.2: sufijo de confianza baja
});

const ESCENARIO = Object.freeze({
  INSUFICIENTE: "insuficiente",
  BAJA: "baja",
  SUBE: "sube",
  POLARIZADO: "polarizado",
  MANTIENE: "mantiene",
  MIXTO: "mixto",
});

export { ESCENARIO };

function esVeredictoValido(veredicto) {
  return VEREDICTOS_VALIDOS.includes(veredicto) && veredicto !== "sin_datos";
}

/**
 * Decide el escenario agregado de un conjunto de registros, con los umbrales de §6.2.
 * Nunca lanza: una lista vacía, `null`/`undefined` o registros sin forma válida degradan a
 * `nSin` (cuentan como sin dato) y, si `V < 8`, al escenario `insuficiente` — nunca a un
 * veredicto inventado (CLAUDE.md).
 *
 * @param {Array<{veredicto?: string, confianza?: string}>} registros
 * @returns {{
 *   v: number, total: number,
 *   nSube: number, nBaja: number, nMant: number, nSin: number,
 *   pSube: number, pBaja: number, pMant: number,
 *   confianzaBajaDominante: boolean,
 *   escenario: "insuficiente"|"baja"|"sube"|"polarizado"|"mantiene"|"mixto",
 * }}
 */
export function resumirVeredictos(registros) {
  const lista = Array.isArray(registros) ? registros : [];

  let nSube = 0;
  let nBaja = 0;
  let nMant = 0;
  let nSin = 0;
  let nConfianzaBaja = 0;

  for (const registro of lista) {
    const veredicto = registro?.veredicto;
    if (!esVeredictoValido(veredicto)) {
      nSin += 1;
      continue;
    }
    if (veredicto === "sube") nSube += 1;
    else if (veredicto === "baja") nBaja += 1;
    else if (veredicto === "se_mantiene") nMant += 1;

    if (registro?.confianza === "baja") nConfianzaBaja += 1;
  }

  const v = nSube + nBaja + nMant;
  const u = UMBRALES_VEREDICTO_GENERAL;

  let escenario;
  if (v < u.V_MINIMO) {
    escenario = ESCENARIO.INSUFICIENTE;
  } else if (nBaja >= u.MAYORIA * v && nSube <= u.CONTRAPESO * v) {
    escenario = ESCENARIO.BAJA;
  } else if (nSube >= u.MAYORIA * v && nBaja <= u.CONTRAPESO * v) {
    escenario = ESCENARIO.SUBE;
  } else if (nSube >= u.POLARIZADO * v && nBaja >= u.POLARIZADO * v) {
    escenario = ESCENARIO.POLARIZADO;
  } else if (nMant >= u.MAYORIA_MANTIENE * v) {
    escenario = ESCENARIO.MANTIENE;
  } else {
    escenario = ESCENARIO.MIXTO;
  }

  const confianzaBajaDominante = v > 0 && nConfianzaBaja >= u.CONFIANZA_BAJA_DOMINANTE * v;

  const porcentaje = (n) => (v > 0 ? Math.round((n / v) * 100) : 0);

  return Object.freeze({
    v,
    total: lista.length,
    nSube,
    nBaja,
    nMant,
    nSin,
    pSube: porcentaje(nSube),
    pBaja: porcentaje(nBaja),
    pMant: porcentaje(nMant),
    confianzaBajaDominante,
    escenario,
  });
}
