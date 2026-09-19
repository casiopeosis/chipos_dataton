// frontend/js/capas.js
//
// Control segmentado de capas (plans/frontend_plan.md §5, F60; plans/frontend_specs.md §9).
//
// "Control segmentado" en la cabecera: `[ Demanda | Oferta | Brecha ]`, un `role="radiogroup"`
// con `<input type="radio">` estilizados; las flechas cambian la opción (comportamiento nativo de
// un grupo de radios con el mismo `name`, sin reimplementar el manejo de teclado). "Brecha" solo
// aparece si el archivo trae `capas.brecha`; hoy el adaptador v1.1→v1.2 nunca la produce
// (`js/api.js`, `js/config.js` → `CAPAS = ["demanda", "oferta"]`), pero este módulo no asume eso:
// lee las capas disponibles del propio resultado adaptado (`capasDesdeAdaptado`) en vez de
// hardcodear un conjunto fijo, así que el día que el backend mande `capas.brecha` el control la
// muestra sin cambios aquí.
//
// Demanda es la opción por defecto (spec §9, `estado.js` → `ESTADO_POR_DEFECTO.capa = "demanda"`).
// Al activar una opción se despacha `ACCIONES.CAMBIAR_CAPA`, que actualiza `&capa=` en el hash
// (estado.js, no se toca aquí: solo se despacha la acción).
//
// El nombre de cada capa sale siempre de `textos.js` (`textos.capa.nombre`), la fuente única que
// exige el spec §9 para que el nombre sea consistente en los seis lugares donde aparece (control,
// subtítulo del titular, encabezado de la leyenda, encabezados de tabla, tooltip y ficha).

import { crear, texto as nodoTexto, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { despachar, suscribir, obtenerEstado, ACCIONES } from "./estado.js";

/**
 * Orden fijo del control segmentado (spec §9: "[ Demanda | Oferta | Brecha ]"). No se deriva del
 * orden de claves del JSON (que no está garantizado): se usa para ordenar lo que sí esté presente.
 */
const ORDEN_CAPAS = Object.freeze(["demanda", "oferta", "brecha"]);

let contador = 0;

/**
 * Deriva la lista de capas disponibles a partir del resultado ya adaptado (v1.2) de `api.js`, en
 * vez de asumir un conjunto fijo. Con el contrato v1.1 de hoy siempre da `["demanda", "oferta"]`
 * (CAPAS de `config.js`); si algún día `datosAdaptados.capas` trae `brecha`, aparece aquí también,
 * en la posición que le toca en `ORDEN_CAPAS`.
 *
 * @param {{capas?: Record<string, unknown>}|null|undefined} datosAdaptados
 * @returns {string[]}
 */
export function capasDesdeAdaptado(datosAdaptados) {
  const presentes = new Set(Object.keys(datosAdaptados?.capas ?? {}));
  return ORDEN_CAPAS.filter((nombreCapa) => presentes.has(nombreCapa));
}

/**
 * Monta el control segmentado de capas dentro de `contenedor` (se reemplaza su contenido; no se
 * asume ningún `id` fijo de `index.html`, que todavía no define la cabecera).
 *
 * @param {HTMLElement} contenedor
 * @param {string[]} capasDisponibles - normalmente el resultado de `capasDesdeAdaptado`.
 * @returns {() => void} función para desmontar (cancela la suscripción a `estado.js`).
 */
export function montarControlCapas(contenedor, capasDisponibles) {
  const capas = ORDEN_CAPAS.filter((nombreCapa) => (capasDisponibles ?? []).includes(nombreCapa));

  if (capas.length === 0) {
    reemplazarContenido(contenedor, []);
    return () => {};
  }

  contador += 1;
  const nombreGrupo = `capas-${contador}`;
  const entradas = new Map();

  const grupo = crear("div", {
    clase: "capas",
    role: "radiogroup",
    "aria-label": textos.capa.controlEtiqueta,
  });

  const estadoInicial = obtenerEstado();
  // La capa activa del estado puede no estar entre las disponibles (p. ej. hash con `capa=oferta`
  // pero un archivo que hoy solo trae demanda); en ese caso no se marca ninguna opción, nunca se
  // inventa una activa que no exista.
  const capaActivaInicial = capas.includes(estadoInicial.capa) ? estadoInicial.capa : null;

  for (const nombreCapa of capas) {
    const id = `${nombreGrupo}-${nombreCapa}`;

    const entrada = crear("input", {
      type: "radio",
      name: nombreGrupo,
      id,
      value: nombreCapa,
      clase: "capas__entrada",
      dataset: { capa: nombreCapa },
      checked: nombreCapa === capaActivaInicial,
      onchange: () => despachar({ tipo: ACCIONES.CAMBIAR_CAPA, capa: nombreCapa }),
    });

    const etiqueta = crear(
      "label",
      { for: id, clase: "capas__opcion" },
      [nodoTexto(textos.capa.nombre[nombreCapa])],
    );

    entradas.set(nombreCapa, entrada);
    grupo.appendChild(entrada);
    grupo.appendChild(etiqueta);
  }

  reemplazarContenido(contenedor, [grupo]);

  function reflejarCapaActiva(estado) {
    for (const [nombreCapa, entrada] of entradas) {
      entrada.checked = nombreCapa === estado.capa;
    }
  }

  return suscribir(reflejarCapaActiva);
}
