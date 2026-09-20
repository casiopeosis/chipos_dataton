// frontend/js/busqueda.js
//
// Selector de tipo de búsqueda: "oportunidad de expansión" / "disponibilidad para familias"
// (plans/frontend_specs.md §5.5, plan F31). Mismo patrón que `vista_mapa.js`/`poblacion.js`.
// Cambiar de búsqueda no pide datos (spec §5.5): ambos índices ya están calculados por
// `composicion.js` en cada recálculo, así que el cambio es una reordenación/recoloreado
// instantáneo vía `estado.js`, sin `fetch`.

import { crear, texto as nodoTexto, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { despachar, suscribir, obtenerEstado, ACCIONES, BUSQUEDA } from "./estado.js";
import { crearAyuda } from "./ayuda.js";

/** Orden fijo del selector (spec §5.5: oportunidad primero, valor inicial del escenario §5.6). */
const ORDEN_BUSQUEDA = Object.freeze([BUSQUEDA.OPORTUNIDAD, BUSQUEDA.DISPONIBILIDAD]);

let contador = 0;

/**
 * Monta el selector de tipo de búsqueda dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @returns {() => void} función para desmontar (cancela la suscripción a `estado.js`).
 */
export function montarBusqueda(contenedor) {
  contador += 1;
  const nombreGrupo = `busqueda-${contador}`;
  const entradas = new Map();

  const grupo = crear("div", {
    clase: "busqueda",
    role: "radiogroup",
    "aria-label": textos.busqueda.controlEtiqueta,
  });

  const activaInicial = obtenerEstado().busqueda;

  for (const clave of ORDEN_BUSQUEDA) {
    const id = `${nombreGrupo}-${clave}`;

    const entrada = crear("input", {
      type: "radio",
      name: nombreGrupo,
      id,
      value: clave,
      clase: "busqueda__entrada",
      dataset: { busqueda: clave },
      checked: clave === activaInicial,
      onchange: () => despachar({ tipo: ACCIONES.CAMBIAR_BUSQUEDA, busqueda: clave }),
    });

    const etiqueta = crear(
      "label",
      { for: id, clase: "busqueda__opcion" },
      [nodoTexto(textos.busqueda.nombre[clave])],
    );

    const ayuda = crear("p", { clase: "busqueda__ayuda" }, [textos.busqueda.ayuda[clave]]);
    const iconoAyuda = crearAyuda(clave, textos.busqueda.nombre[clave]);

    entradas.set(clave, entrada);
    grupo.appendChild(
      crear("div", { clase: "busqueda__item" }, [entrada, etiqueta, iconoAyuda, ayuda]),
    );
  }

  reemplazarContenido(contenedor, [grupo]);

  function reflejarActiva(estado) {
    for (const [clave, entrada] of entradas) {
      entrada.checked = clave === estado.busqueda;
    }
  }

  return suscribir(reflejarActiva);
}
