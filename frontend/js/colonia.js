// frontend/js/colonia.js
//
// Buscador de colonia por nombre. Mismo mecanismo que `alcaldia.js` (§5.2): debounce 120 ms,
// mensaje sin resultados, Enter con resultado único navega. A diferencia de la alcaldía (una
// región con veredicto propio), una colonia no tiene datos ni color: seleccionarla solo navega a
// la alcaldía que la contiene y resalta su contorno completo en el mapa (`mapa.js#resaltarColonia`)
// -- nunca abre la ficha de un AGEB en particular, porque una colonia casi siempre cruza varios.
//
// AGEB y colonia no anidan limpiamente (`docs/perfil_datos.md` → "Colonias"): una colonia puede
// caer en más de una alcaldía si el AGEB con mayor traslape de sus distintos AGEB no coincide en
// `cve_mun`. Se navega a la alcaldía MÁS FRECUENTE entre los AGEB de esa colonia (moda), no
// necesariamente la única.

import { crear, texto as nodoTexto, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { despachar, ACCIONES } from "./estado.js";

const DEBOUNCE_BUSCADOR_MS = 120;

/**
 * @typedef {{cveut: string, colonia: string, cveMun: string|null, alcaldiaNombre: string}} EntradaColonia
 */

/**
 * Monta el buscador de colonia por nombre dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @param {EntradaColonia[]} entradasColonia
 * @param {{despachar?: (accion: object) => void, resaltar?: (cveut: string) => void}} [opciones]
 */
export function montarColonia(contenedor, entradasColonia, opciones = {}) {
  const despacharAccion = typeof opciones.despachar === "function" ? opciones.despachar : despachar;
  const resaltar = typeof opciones.resaltar === "function" ? opciones.resaltar : () => {};

  let consulta = "";
  let temporizador = null;

  const idCampo = "colonia-buscador";
  const idResultados = "colonia-buscador-resultados";

  const etiqueta = crear("label", { for: idCampo, clase: "alcaldia-buscador__etiqueta" }, [
    textos.buscadorColonia.etiqueta,
  ]);

  const listaResultados = crear("ul", { id: idResultados, clase: "alcaldia-buscador__resultados" });

  function coincidencias() {
    const texto = consulta.trim().toLowerCase();
    if (texto === "") return [];
    return entradasColonia.filter((e) => e.colonia.toLowerCase().includes(texto)).slice(0, 20);
  }

  function seleccionar(entrada) {
    if (entrada.cveMun) despacharAccion({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: entrada.cveMun });
    resaltar(entrada.cveut);
    consulta = "";
    campo.value = "";
    renderResultados();
  }

  function renderResultados() {
    const filas = coincidencias();
    if (consulta.trim() === "") {
      reemplazarContenido(listaResultados, []);
      return;
    }
    if (filas.length === 0) {
      reemplazarContenido(listaResultados, [
        crear("li", { clase: "alcaldia-buscador__sin-resultados" }, [
          textos.buscadorColonia.sinResultados({ texto: consulta.trim() }),
        ]),
      ]);
      return;
    }
    reemplazarContenido(
      listaResultados,
      filas.map((entrada) =>
        crear("li", {}, [
          crear(
            "button",
            { type: "button", clase: "alcaldia-buscador__opcion", onclick: () => seleccionar(entrada) },
            [textos.buscadorColonia.opcion({ colonia: entrada.colonia, alcaldia: entrada.alcaldiaNombre })],
          ),
        ])),
    );
  }

  function irSiResultadoUnico() {
    const filas = coincidencias();
    if (filas.length === 1) seleccionar(filas[0]);
  }

  const campo = crear("input", {
    id: idCampo,
    type: "search",
    clase: "alcaldia-buscador__campo",
    autocomplete: "off",
    "aria-describedby": idResultados,
    oninput: (evento) => {
      const valorActual = evento.target.value;
      if (temporizador !== null) window.clearTimeout(temporizador);
      temporizador = window.setTimeout(() => {
        consulta = valorActual;
        renderResultados();
      }, DEBOUNCE_BUSCADOR_MS);
    },
    onkeydown: (evento) => {
      if (evento.key === "Enter") {
        evento.preventDefault();
        if (temporizador !== null) {
          window.clearTimeout(temporizador);
          temporizador = null;
        }
        consulta = evento.target.value;
        renderResultados();
        irSiResultadoUnico();
      }
    },
  });

  reemplazarContenido(contenedor, [
    crear("div", { clase: "alcaldia-buscador" }, [etiqueta, campo, listaResultados]),
  ]);
}
