// frontend/js/presentacion.js
//
// Modo presentación (plans/frontend_specs.md §10.9, plan F85): tecla "P", el botón "⤢" que ya
// deja `cabecera.js` (F25, `#boton-presentacion`, sin manejador propio) o `?presentacion=1` en la
// URL activan `--escala: 1.25` (tokens.css → `html.modo-presentacion`) y ocultan el buscador, el
// pie y la franja de metodología (css/presentacion.css), sin tocar capa/horizonte/migas.

const CLASE_PRESENTACION = "modo-presentacion";

function activo() {
  return document.documentElement.classList.contains(CLASE_PRESENTACION);
}

function aplicar(nuevoEstado, boton) {
  document.documentElement.classList.toggle(CLASE_PRESENTACION, nuevoEstado);
  boton?.setAttribute("aria-pressed", String(nuevoEstado));
}

/**
 * Engancha el botón "⤢" de la cabecera y la tecla "P" al modo presentación; lee `?presentacion=1`
 * de la URL actual para el estado inicial.
 *
 * @param {HTMLElement|null} boton - `document.getElementById("boton-presentacion")`.
 * @returns {{activo: () => boolean, alternar: (forzar?: boolean) => void}}
 */
export function iniciarPresentacion(boton) {
  const parametros = new URLSearchParams(window.location.search);
  aplicar(parametros.get("presentacion") === "1", boton);

  function alternar(forzar) {
    aplicar(typeof forzar === "boolean" ? forzar : !activo(), boton);
  }

  boton?.addEventListener("click", () => alternar());

  window.addEventListener("keydown", (evento) => {
    if (evento.key !== "p" && evento.key !== "P") return;
    if (evento.metaKey || evento.ctrlKey || evento.altKey) return;
    const objetivo = evento.target;
    const enCampoDeTexto =
      objetivo instanceof HTMLElement &&
      (objetivo.tagName === "INPUT" || objetivo.tagName === "TEXTAREA" || objetivo.isContentEditable);
    if (enCampoDeTexto) return; // no interceptar "p" mientras se escribe en el buscador de AGEB
    alternar();
  });

  return { activo, alternar };
}
