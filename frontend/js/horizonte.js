// frontend/js/horizonte.js
//
// Control de horizonte temporal (plans/frontend_specs.md §8, plan F55).
// Autocontenido: `montarControlHorizonte(contenedor, horizontesDisponibles)` construye el
// `<input type="range">` + `<datalist>` dentro del `contenedor` que le pasa quien lo invoca
// (F100/main.js); este módulo nunca asume un `id` concreto de `index.html`.
//
// Con el contrato v1.1 real, `horizontesDisponibles` siempre trae una sola entrada (`hU`, ver
// `js/config.js` → `CLAVE_HORIZONTE_UNICO` y el adaptador de `js/api.js`): en ese caso el control
// queda `disabled` con la nota fija de §8.6. La lógica de min/max es genérica (no hay ningún
// atajo hardcodeado a "un solo horizonte"): con 2 o más entradas el slider se habilita solo,
// como probarán los fixtures de `tests/pruebas.js` con 3 horizontes.
//
// Fuente de verdad: mover el control nunca dispara peticiones de red (§8.3); solo despacha
// `ACCIONES.CAMBIAR_HORIZONTE` contra `js/estado.js`. La región viva global (§13) la conecta F95;
// aquí solo se deja `aria-valuetext` actualizado en cada `input` y, en `change`, un
// `CustomEvent("horizonteanunciado", {detail:{texto}})` despachado sobre el propio contenedor
// como enganche para quien conecte esa región viva.

import { crear, limpiar } from "./dom.js";
import { texto as t, textos } from "./textos.js";
import { ACCIONES, despachar } from "./estado.js";

let contadorInstancias = 0;

/** "2027-06" → "2027". Nunca lanza: entradas corruptas devuelven cadena vacía. */
function extraerAnio(fecha) {
  if (typeof fecha !== "string") return "";
  const coincidencia = fecha.match(/^(\d{4})/);
  return coincidencia ? coincidencia[1] : "";
}

/**
 * Normaliza y ordena la lista de horizontes por `anios` ascendente. Las entradas con
 * `anios: null` (el caso real hoy, `hU`) se consideran únicas y se colocan solas: si hay más de
 * una entrada en la lista, `anios: null` nunca debería coexistir con otras (contrato v1.1/v1.2),
 * pero por si acaso se ordenan al final sin romper nada.
 */
export function ordenarHorizontes(horizontesDisponibles) {
  const lista = Array.isArray(horizontesDisponibles) ? horizontesDisponibles.slice() : [];
  return lista.slice().sort((a, b) => {
    const aAnios = typeof a.anios === "number" ? a.anios : Number.POSITIVE_INFINITY;
    const bAnios = typeof b.anios === "number" ? b.anios : Number.POSITIVE_INFINITY;
    return aAnios - bAnios;
  });
}

/** Índice dentro de `lista` (ya ordenada) cuya `clave` coincide con `claveActiva`, o `0`. */
export function indiceHorizonteActivo(listaOrdenada, claveActiva) {
  const indice = listaOrdenada.findIndex((h) => h.clave === claveActiva);
  return indice === -1 ? 0 : indice;
}

/** Texto de `aria-valuetext`/anuncio para una entrada de horizonte (§8.2: "5 años, a mediados de 2031"). */
export function textoValorHorizonte(entrada) {
  const anio = extraerAnio(entrada.fecha);
  if (typeof entrada.anios === "number") {
    return t("horizonte.ariaValuetext", { h: entrada.anios, anio });
  }
  // Sin `anios` (horizonte único del contrato v1.1): no hay una cifra de años que anunciar como
  // tal, así que se reutiliza la nota de degradación como valor accesible del control.
  return textos.horizonte.deshabilitadoUnico(anio);
}

function crearDatalist(idDatalist, listaOrdenada) {
  return crear(
    "datalist",
    { id: idDatalist },
    listaOrdenada.map((entrada, indice) =>
      crear("option", {
        value: String(indice),
        label: typeof entrada.anios === "number" ? textos.horizonte.etiquetaAnios(entrada.anios) : "",
      }),
    ),
  );
}

function crearBotonEtiqueta(entrada, indice, onSeleccionar) {
  const anio = extraerAnio(entrada.fecha);
  const lineaAnios =
    typeof entrada.anios === "number" ? textos.horizonte.etiquetaAnios(entrada.anios) : "";
  return crear(
    "button",
    {
      type: "button",
      clase: "control-horizonte__marca",
      dataset: { indice: String(indice) },
      onclick: () => onSeleccionar(indice),
    },
    [
      crear("span", { clase: "control-horizonte__marca-anios" }, [lineaAnios]),
      crear("span", { clase: "control-horizonte__marca-anio cifras" }, [anio]),
    ],
  );
}

/**
 * Monta el control de horizonte dentro de `contenedor` (se limpia antes de montar, así que puede
 * reutilizarse el mismo contenedor si el conjunto de horizontes cambia).
 *
 * @param {HTMLElement} contenedor - nodo ya existente en el DOM; este módulo no asume su `id`.
 * @param {{clave:string, anios:number|null, fecha:string}[]} horizontesDisponibles - `estado.js`
 *   guarda solo la `clave` activa (`estado.horizonte`); esta lista es la que produce el
 *   adaptador de `js/api.js` (`adaptado.horizontes`).
 * @param {{claveActiva?: string}} [opciones] - `claveActiva` por defecto es la primera entrada.
 * @returns {{elemento: HTMLElement, destruir: () => void, actualizar: (horizontesDisponibles: any[], opciones?: any) => void}}
 */
export function montarControlHorizonte(contenedor, horizontesDisponibles, opciones = {}) {
  if (!(contenedor instanceof HTMLElement)) {
    throw new TypeError("montarControlHorizonte(contenedor, ...): contenedor debe ser un HTMLElement");
  }

  contadorInstancias += 1;
  const idInstancia = `control-horizonte-${contadorInstancias}`;
  const idEtiqueta = `${idInstancia}-etiqueta`;
  const idInput = `${idInstancia}-input`;
  const idDatalist = `${idInstancia}-marcas`;
  const idNota = `${idInstancia}-nota`;

  let listaOrdenada = ordenarHorizontes(horizontesDisponibles);

  function anunciarCambio(entrada) {
    contenedor.dispatchEvent(
      new CustomEvent("horizonteanunciado", {
        bubbles: true,
        detail: { texto: t("accesibilidad.anuncioHorizonte", { h: entrada.anios, anio: extraerAnio(entrada.fecha) }) },
      }),
    );
  }

  function aplicarValor(input, nota, marcas, indice, { anunciar } = {}) {
    const entrada = listaOrdenada[indice] ?? listaOrdenada[0];
    if (!entrada) return;
    input.setAttribute("aria-valuetext", textoValorHorizonte(entrada));
    limpiar(nota);
    const textoNota =
      listaOrdenada.length <= 1
        ? textos.horizonte.deshabilitadoUnico(extraerAnio(entrada.fecha))
        : textos.horizonte.nota[entrada.anios] ?? "";
    nota.appendChild(document.createTextNode(textoNota));

    for (const marca of marcas) {
      const esActiva = Number(marca.dataset.indice) === indice;
      marca.classList.toggle("control-horizonte__marca--activa", esActiva);
      marca.setAttribute("aria-current", esActiva ? "true" : "false");
    }

    if (anunciar) anunciarCambio(entrada);
  }

  function construir() {
    limpiar(contenedor);
    contenedor.classList.add("control-horizonte");

    const deshabilitado = listaOrdenada.length <= 1;
    const claveActiva = opciones.claveActiva ?? listaOrdenada[0]?.clave;
    const indiceInicial = indiceHorizonteActivo(listaOrdenada, claveActiva);
    const maximo = Math.max(listaOrdenada.length - 1, 0);

    const etiqueta = crear("span", { id: idEtiqueta, clase: "control-horizonte__etiqueta" }, [
      textos.horizonte.etiqueta,
    ]);

    const input = crear("input", {
      type: "range",
      id: idInput,
      clase: "control-horizonte__input cifras",
      min: "0",
      max: String(maximo),
      step: "1",
      value: String(indiceInicial),
      list: idDatalist,
      "aria-labelledby": idEtiqueta,
      "aria-describedby": idNota,
      disabled: deshabilitado,
    });

    const datalist = crearDatalist(idDatalist, listaOrdenada);

    const marcasEnvoltura = crear("div", { clase: "control-horizonte__marcas" });
    const marcas = listaOrdenada.map((entrada, indice) =>
      crearBotonEtiqueta(entrada, indice, (indiceSeleccionado) => {
        if (deshabilitado) return;
        input.value = String(indiceSeleccionado);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }),
    );
    for (const marca of marcas) {
      marca.disabled = deshabilitado;
      marcasEnvoltura.appendChild(marca);
    }

    const nota = crear("p", { id: idNota, clase: "control-horizonte__nota" });

    aplicarValor(input, nota, marcas, indiceInicial, { anunciar: false });

    input.addEventListener("input", () => {
      // §8.2: aria-valuetext (y la marca activa) deben reflejar el valor en cada evento input,
      // sin diferirlo a un frame posterior (un lector de pantalla o una prueba puede leerlo de
      // inmediato); el coste de aplicarValor es mínimo (un atributo + una clase por marca), así
      // que no hace falta throttling con requestAnimationFrame.
      const indice = Number(input.value);
      aplicarValor(input, nota, marcas, indice, { anunciar: false });
    });

    input.addEventListener("change", () => {
      const indice = Number(input.value);
      const entrada = listaOrdenada[indice];
      if (!entrada) return;
      aplicarValor(input, nota, marcas, indice, { anunciar: true });
      // §8.3: mover el control nunca dispara peticiones; solo actualiza el almacén de sesión.
      despachar({ tipo: ACCIONES.CAMBIAR_HORIZONTE, horizonte: entrada.clave });
    });

    const pistaEnvoltura = crear("div", { clase: "control-horizonte__pista" }, [input, datalist]);

    contenedor.appendChild(etiqueta);
    contenedor.appendChild(pistaEnvoltura);
    contenedor.appendChild(marcasEnvoltura);
    contenedor.appendChild(nota);

    contenedor.classList.toggle("control-horizonte--deshabilitado", deshabilitado);
  }

  construir();

  return {
    elemento: contenedor,
    /** Reconstruye el control con un nuevo conjunto de horizontes (p. ej. al cambiar de capa). */
    actualizar(nuevosHorizontesDisponibles, nuevasOpciones = {}) {
      listaOrdenada = ordenarHorizontes(nuevosHorizontesDisponibles);
      opciones = { ...opciones, ...nuevasOpciones };
      construir();
    },
    /** Limpia el contenedor (para cuando quien orquesta desmonta la vista). */
    destruir() {
      limpiar(contenedor);
      contenedor.classList.remove("control-horizonte", "control-horizonte--deshabilitado");
    },
  };
}
