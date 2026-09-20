// frontend/js/ayuda.js
//
// Sistema de ayuda "?" (plans/frontend_specs.md §10.14, plan F89). Cada ayuda responde tres
// preguntas fijas (qué es / por qué importa / cómo interpretarlo, ya centralizadas en
// `textos.ayuda`) dentro de un popover anclado al icono -- nunca navega a otra pantalla. Sin
// posicionamiento calculado en JS (la CSP del proyecto es `style-src 'self'`, `dom.js`): el
// panel se ancla con CSS puro (`position: absolute` dentro de un contenedor `position: relative`),
// nunca con una coordenada escrita desde JS.

import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";

let contador = 0;

/**
 * Crea el nodo `<span class="ayuda">` (botón "?" + popover) para un concepto de `textos.ayuda`.
 * Insértalo junto a la etiqueta del control correspondiente.
 *
 * @param {string} claveConcepto - clave en `textos.ayuda` (p. ej. "oportunidad", "prioridades").
 * @param {string} etiquetaConcepto - nombre legible para el `aria-label` del botón (p. ej.
 *   "Oportunidad relativa"). `textos.ayuda.abrir` ya arma "Ayuda: {concepto}".
 * @returns {HTMLElement}
 */
export function crearAyuda(claveConcepto, etiquetaConcepto) {
  const contenido = textos.ayuda[claveConcepto];
  if (!contenido) {
    throw new TypeError(`crearAyuda(): "${claveConcepto}" no existe en textos.ayuda`);
  }

  contador += 1;
  const idPanel = `ayuda-panel-${claveConcepto}-${contador}`;
  let abierto = false;

  const panel = crear(
    "div",
    { id: idPanel, clase: "ayuda__panel", role: "dialog", "aria-label": etiquetaConcepto, hidden: true },
    [
      crear("p", { clase: "ayuda__parrafo" }, [contenido.queEs]),
      crear("p", { clase: "ayuda__parrafo" }, [contenido.porQueImporta]),
      crear("p", { clase: "ayuda__parrafo" }, [contenido.comoInterpretar]),
    ],
  );

  function cerrar() {
    if (!abierto) return;
    abierto = false;
    panel.hidden = true;
    boton.setAttribute("aria-expanded", "false");
  }

  function alternar() {
    abierto = !abierto;
    panel.hidden = !abierto;
    boton.setAttribute("aria-expanded", String(abierto));
  }

  const boton = crear(
    "button",
    {
      type: "button",
      clase: "ayuda__boton",
      "aria-label": textos.ayuda.abrir(etiquetaConcepto),
      "aria-expanded": "false",
      "aria-controls": idPanel,
      onclick: (evento) => {
        evento.stopPropagation();
        alternar();
      },
    },
    ["?"],
  );

  const envoltura = crear("span", { clase: "ayuda" }, [boton, panel]);

  // Clic fuera y Esc cierran (patrón estándar de popover, spec §10.14: "se abren dentro de la
  // misma vista", nunca deben quedar abiertos estorbando el resto de la interacción).
  document.addEventListener("click", (evento) => {
    if (abierto && !envoltura.contains(evento.target)) cerrar();
  });
  envoltura.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && abierto) {
      evento.preventDefault();
      cerrar();
      boton.focus();
    }
  });

  return envoltura;
}

/** Azúcar: crea la ayuda y la inserta al final de `contenedor` (reemplaza lo que hubiera). */
export function montarAyuda(contenedor, claveConcepto, etiquetaConcepto) {
  reemplazarContenido(contenedor, [crearAyuda(claveConcepto, etiquetaConcepto)]);
}
