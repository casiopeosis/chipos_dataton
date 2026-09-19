// frontend/js/dom.js
//
// Helpers de creación de nodos DOM. Ningún módulo del frontend debe usar
// `innerHTML`/`outerHTML`/`insertAdjacentHTML` con datos: todo texto entra
// siempre por `document.createTextNode` / `Node.textContent`, nunca por un
// parser de HTML. Ver CLAUDE.md → "Frontend" y plans/frontend_plan.md → F15.

const ATRIBUTOS_BOOLEANOS = new Set([
  "disabled",
  "checked",
  "selected",
  "hidden",
  "required",
  "readonly",
  "multiple",
  "open",
  "autofocus",
]);

/**
 * Crea un elemento DOM sin recurrir jamás a innerHTML.
 *
 * @param {string} etiqueta - nombre de la etiqueta HTML (p. ej. "div", "button").
 * @param {Object} [atributos] - pares atributo→valor. Casos especiales:
 *   - `clase` (o `className`): asigna `el.className`.
 *   - `dataset`: objeto que se copia a `el.dataset`.
 *   - claves que empiezan con "on" y valor función: se agregan como listener
 *     de evento (`onclick` → `click`), nunca como atributo `on*` inline.
 *   - claves en ATRIBUTOS_BOOLEANOS: solo se agrega el atributo si el valor
 *     es estrictamente `true` (se agrega vacío, como exige HTML).
 *   - `null`/`undefined`/`false`: se omite el atributo.
 *   - cualquier otro valor se convierte a texto con `String()` y se asigna
 *     con `setAttribute` (nunca se interpreta como HTML).
 * @param {(string|number|Node|null|undefined|false)[]|string|number|Node} [hijos]
 *   - texto (string/number): se agrega como nodo de texto (`createTextNode`).
 *   - `Node`: se agrega tal cual (`appendChild`).
 *   - `null`/`undefined`/`false`: se ignora (permite condicionales inline).
 *   - cualquier otro tipo lanza `TypeError` (no hay forma "silenciosa" de
 *     colar HTML sin sanear).
 * @returns {HTMLElement}
 */
export function crear(etiqueta, atributos = {}, hijos = []) {
  const el = document.createElement(etiqueta);
  asignarAtributos(el, atributos);
  agregarHijos(el, hijos);
  return el;
}

function asignarAtributos(el, atributos) {
  for (const [nombre, valor] of Object.entries(atributos ?? {})) {
    if (valor === null || valor === undefined || valor === false) continue;

    if (nombre === "clase" || nombre === "className") {
      el.className = String(valor);
      continue;
    }

    if (nombre === "dataset" && valor && typeof valor === "object") {
      for (const [claveDato, valorDato] of Object.entries(valor)) {
        if (valorDato === null || valorDato === undefined) continue;
        el.dataset[claveDato] = String(valorDato);
      }
      continue;
    }

    if (nombre.startsWith("on") && nombre.length > 2 && typeof valor === "function") {
      el.addEventListener(nombre.slice(2).toLowerCase(), valor);
      continue;
    }

    if (ATRIBUTOS_BOOLEANOS.has(nombre)) {
      if (valor === true) el.setAttribute(nombre, "");
      continue;
    }

    el.setAttribute(nombre, String(valor));
  }
}

function agregarHijos(el, hijos) {
  const lista = Array.isArray(hijos) ? hijos : [hijos];
  for (const hijo of lista) {
    el.appendChild(nodoDeHijo(hijo));
  }
}

function nodoDeHijo(hijo) {
  if (hijo === null || hijo === undefined || hijo === false) {
    // nodo de texto vacío: mantiene la posición sin agregar nada visible,
    // evita ramificar la firma de crear() con "hijos que a veces no cuentan".
    return document.createTextNode("");
  }
  if (typeof hijo === "string" || typeof hijo === "number") {
    return document.createTextNode(String(hijo));
  }
  if (hijo instanceof Node) {
    return hijo;
  }
  throw new TypeError(
    "crear(): hijo no soportado; usa texto, número, Node, null/undefined/false",
  );
}

/** Nodo de texto plano. Azúcar sobre `document.createTextNode`. */
export function texto(contenido) {
  return document.createTextNode(contenido === null || contenido === undefined ? "" : String(contenido));
}

/** Vacía un elemento sin usar innerHTML = "". */
export function limpiar(el) {
  while (el.firstChild) {
    el.removeChild(el.firstChild);
  }
}

/** Reemplaza el contenido de un elemento por los hijos dados (misma regla que `crear`). */
export function reemplazarContenido(el, hijos) {
  limpiar(el);
  agregarHijos(el, hijos);
}

/** Texto solo para lectores de pantalla (usar junto con `.visualmente-oculto` en CSS). */
export function textoOculto(contenido) {
  return crear("span", { clase: "visualmente-oculto" }, [contenido]);
}
