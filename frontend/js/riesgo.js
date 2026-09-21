// frontend/js/riesgo.js
//
// Filtro de nivel de riesgo aceptable (plans/frontend_specs.md §10.12, plan F35). Control aparte,
// no una rama: umbral sobre la CONFIANZA de la demanda del segmento activo. El contrato solo
// publica confianza discreta (alta/media/baja, nunca un `p_dec` continuo, docs/metodologia.md
// §10.4), así que el umbral vive en los mismos 3 escalones -- un `<input type="range">` continuo
// insinuaría una precisión que los datos no tienen. `estado.umbralRiesgo` seguye siendo un número
// en [0,1] (0 = baja, 0.5 = media, 1 = alta), mismo mapeo que `FACTOR_CONFIANZA` de
// `composicion.js` (no importado aquí para no crear una dependencia circular de UI -> motor con
// un solo número; `main.js`, que ya conecta ambos, es quien filtra el ranking con este umbral).

import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { despachar, suscribir, obtenerEstado, ACCIONES } from "./estado.js";
import { crearAyuda } from "./ayuda.js";

/** Mismos 3 escalones que `FACTOR_CONFIANZA` (composicion.js): baja=0, media=0.5, alta=1. */
const ESCALONES = Object.freeze([
  { valor: 0, nivel: "baja" },
  { valor: 0.5, nivel: "media" },
  { valor: 1, nivel: "alta" },
]);

function indiceDeUmbral(umbral) {
  if (umbral === null) return 0; // "sin filtrar" == acepta cualquier confianza == equivalente al escalón más bajo.
  let mejor = 0;
  let mejorDist = Infinity;
  ESCALONES.forEach((e, i) => {
    const dist = Math.abs(e.valor - umbral);
    if (dist < mejorDist) {
      mejorDist = dist;
      mejor = i;
    }
  });
  return mejor;
}

/**
 * Monta el filtro de nivel de riesgo dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @returns {() => void} función para desmontar (cancela la suscripción a `estado.js`).
 */
export function montarRiesgo(contenedor) {
  const raiz = crear("div", { clase: "riesgo" });
  const etiqueta = crear("label", { for: "riesgo-umbral", clase: "riesgo__etiqueta" }, [textos.riesgo.etiqueta]);

  const estadoInicial = obtenerEstado();

  const control = crear("input", {
    type: "range",
    id: "riesgo-umbral",
    clase: "riesgo__control",
    min: "0",
    max: String(ESCALONES.length - 1),
    step: "1",
    value: String(indiceDeUmbral(estadoInicial.umbralRiesgo)),
    oninput: (evento) => {
      const indice = Number(evento.target.value);
      const umbral = ESCALONES[indice]?.valor ?? 0;
      // El escalón más bajo (0) equivale a "sin filtrar" (spec: acepta cualquier confianza).
      despachar({ tipo: ACCIONES.CAMBIAR_UMBRAL_RIESGO, umbral: umbral === 0 ? null : umbral });
    },
  });

  const valorTexto = crear("span", { clase: "riesgo__valor" });

  raiz.appendChild(etiqueta);
  raiz.appendChild(crearAyuda("riesgo", textos.riesgo.etiqueta));
  raiz.appendChild(control);
  raiz.appendChild(valorTexto);
  raiz.appendChild(crear("p", { clase: "riesgo__ayuda" }, [textos.riesgo.ayuda]));

  reemplazarContenido(contenedor, [raiz]);

  function reflejarUmbral(estado) {
    const indice = indiceDeUmbral(estado.umbralRiesgo);
    control.value = String(indice);
    reemplazarContenido(valorTexto, [textos.confianza.palabra[ESCALONES[indice].nivel] ?? ""]);
  }

  reflejarUmbral(estadoInicial);
  return suscribir(reflejarUmbral);
}

/** Umbral numérico ↔ `FACTOR_CONFIANZA` de `composicion.js` (documentado en la cabecera del módulo). */
export const FACTOR_CONFIANZA_RIESGO = Object.freeze({ alta: 1, media: 0.5, baja: 0 });
