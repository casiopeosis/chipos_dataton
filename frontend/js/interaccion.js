// frontend/js/interaccion.js
//
// Teclado transversal (plans/frontend_specs.md §10.8, plan F85): Esc retrocede un nivel, con
// prioridad drawer > filtro de leyenda > vista (spec §10.4, §10.8; contrato documentado en la
// cabecera de leyenda.js). El orden de Tab de la app sale del orden natural del DOM (HTML
// semántico, sin `tabindex` positivo en ningún módulo), así que no hace falta gestionarlo aquí.
//
// El cierre de un `<dialog>` abierto (el drawer de metodología) ya lo maneja el propio
// `franja.js` con el evento nativo `cancel` del `<dialog>`; este módulo se aparta explícitamente
// cuando hay uno abierto, para no despachar una segunda acción (limpiar filtro o VOLVER) en el
// mismo toque de Esc que ya usó el drawer (spec §10.8: "Esc retrocede un nivel a la vez").

import { obtenerEstado, despachar, ACCIONES, VISTA } from "./estado.js";
import { limpiarFiltroLeyenda } from "./leyenda.js";

/** Engancha el manejador global de Esc. Devuelve una función para desmontarlo (pruebas). */
export function iniciarInteraccionGlobal() {
  function alPresionarTecla(evento) {
    if (evento.key !== "Escape") return;

    const dialogoAbierto = document.querySelector("dialog[open]");
    if (dialogoAbierto) return; // el propio <dialog> (franja.js) ya está manejando este Esc

    const estado = obtenerEstado();
    if (estado.filtroLeyenda !== null) {
      limpiarFiltroLeyenda();
      return;
    }
    if (estado.vista !== VISTA.CIUDAD) {
      despachar({ tipo: ACCIONES.VOLVER });
    }
  }

  window.addEventListener("keydown", alPresionarTecla);
  return () => window.removeEventListener("keydown", alPresionarTecla);
}
