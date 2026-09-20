// frontend/js/vista_mapa.js
//
// Selector de vista de mapa (plans/frontend_plan.md F65; plans/frontend_specs.md §9). Reemplaza
// al antiguo control segmentado de "capa" (`capas.js`, retirado -- plans/frontend_plan.md §0
// punto 3): en vez de dos capas del backend (demanda/oferta), ahora son 5 VISTAS de un mismo
// índice ya calculado por `composicion.js` -- la vista general (índice compuesto) o una de las
// 4 ramas individuales. Cambiar de vista nunca recrea la geometría del mapa (`mapa.js` reutiliza
// el mismo `<g class="escenario">`): solo cambia color/leyenda/ranking/título.
//
// Mismo patrón accesible que el control retirado: `role="radiogroup"` con `<input type="radio">`
// estilizados (las flechas cambian la opción, comportamiento nativo de un grupo de radios con el
// mismo `name`, sin reimplementar el manejo de teclado).

import { crear, texto as nodoTexto, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { despachar, suscribir, obtenerEstado, ACCIONES, VISTA_MAPA } from "./estado.js";

/** Orden fijo del selector (spec §9): general primero, luego las 4 ramas en el orden del hash de pesos. */
const ORDEN_VISTAS = Object.freeze([
  VISTA_MAPA.GENERAL,
  VISTA_MAPA.EDUCACION,
  VISTA_MAPA.SALUD,
  VISTA_MAPA.COMERCIO,
  VISTA_MAPA.VERDE,
]);

let contador = 0;

/**
 * Monta el selector de vista de mapa dentro de `contenedor` (se reemplaza su contenido; no se
 * asume ningún `id` fijo de `index.html`).
 *
 * @param {HTMLElement} contenedor
 * @returns {() => void} función para desmontar (cancela la suscripción a `estado.js`).
 */
export function montarVistaMapa(contenedor) {
  contador += 1;
  const nombreGrupo = `vista-mapa-${contador}`;
  const entradas = new Map();

  const grupo = crear("div", {
    clase: "vista-mapa",
    role: "radiogroup",
    "aria-label": textos.vista.controlEtiqueta,
  });

  const vistaActivaInicial = obtenerEstado().vistaMapa;

  for (const claveVista of ORDEN_VISTAS) {
    const id = `${nombreGrupo}-${claveVista}`;

    const entrada = crear("input", {
      type: "radio",
      name: nombreGrupo,
      id,
      value: claveVista,
      clase: "vista-mapa__entrada",
      dataset: { vista: claveVista },
      checked: claveVista === vistaActivaInicial,
      onchange: () => despachar({ tipo: ACCIONES.CAMBIAR_VISTA_MAPA, vistaMapa: claveVista }),
    });

    const etiqueta = crear(
      "label",
      { for: id, clase: "vista-mapa__opcion" },
      [nodoTexto(textos.vista.nombre[claveVista])],
    );

    entradas.set(claveVista, entrada);
    grupo.appendChild(entrada);
    grupo.appendChild(etiqueta);
  }

  reemplazarContenido(contenedor, [grupo]);

  function reflejarVistaActiva(estado) {
    for (const [claveVista, entrada] of entradas) {
      entrada.checked = claveVista === estado.vistaMapa;
    }
  }

  return suscribir(reflejarVistaActiva);
}
