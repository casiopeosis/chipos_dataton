// frontend/js/movil.js
//
// Hoja inferior de 3 alturas para móvil/tableta (plans/frontend_specs.md §11, plan F91). El spec
// permite "asa arrastrable O `<button>` cíclico" -- se implementa el botón cíclico: mismo
// resultado (tres alturas fijas), sin el riesgo de una implementación de arrastre táctil a medio
// probar. Solo activo bajo 1024px (mismo punto de corte que `layout.css`); por encima, no hace
// nada (el escritorio no tiene hoja).
//
// El reordenamiento de contenido de §11 ("configuración → prioridades → filtros → resumen →
// ranking") ya lo da el orden real del DOM que arma `main.js` (`panel-configuracion` antes de
// `vista-principal`): este módulo no reordena nada, solo controla la altura de `.panel-datos`
// como hoja fija sobre el mapa.

import { crear } from "./dom.js";

const PUNTO_CORTE_MOVIL = "(max-width: 1023px)";
const ALTURAS = Object.freeze(["baja", "media", "alta"]);

/**
 * Activa la hoja inferior sobre `.panel-datos` cuando el viewport está bajo 1024px. Añade un
 * botón cíclico de altura al principio del panel.
 *
 * @param {HTMLElement} panelDatos - el `.panel-datos` que ya arma `main.js`.
 * @returns {() => void} función para desmontar (quita el listener de `matchMedia`).
 */
export function montarMovil(panelDatos) {
  if (!panelDatos) return () => {};

  let indiceAltura = 0; // "baja" al entrar, spec §11.
  const mql = typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(PUNTO_CORTE_MOVIL)
    : null;

  const asa = crear(
    "button",
    {
      type: "button",
      clase: "movil__asa",
      "aria-label": "Cambiar altura del panel",
      onclick: () => {
        indiceAltura = (indiceAltura + 1) % ALTURAS.length;
        aplicarAltura();
      },
    },
    [crear("span", { clase: "movil__asa-barra", "aria-hidden": "true" })],
  );

  function aplicarAltura() {
    for (const altura of ALTURAS) panelDatos.classList.remove(`movil--${altura}`);
    panelDatos.classList.add(`movil--${ALTURAS[indiceAltura]}`);
  }

  function aplicarModo(coincide) {
    if (coincide) {
      panelDatos.classList.add("movil");
      if (panelDatos.firstChild !== asa) panelDatos.insertBefore(asa, panelDatos.firstChild);
      aplicarAltura();
    } else {
      panelDatos.classList.remove("movil", ...ALTURAS.map((a) => `movil--${a}`));
      asa.remove();
    }
  }

  aplicarModo(mql ? mql.matches : false);
  const escuchar = (evento) => aplicarModo(evento.matches);
  mql?.addEventListener?.("change", escuchar);

  return () => mql?.removeEventListener?.("change", escuchar);
}
