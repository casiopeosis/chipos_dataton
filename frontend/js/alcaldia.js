// frontend/js/alcaldia.js
//
// Buscador de alcaldía por nombre (plans/frontend_specs.md §5.2, plan F55). Siempre visible,
// complementa a la selección en el mapa (mapa.js): "Selecciona una alcaldía en el mapa o búscala
// por nombre." Mismo mecanismo que el buscador de AGEB de `ranking.js` (§7.3): `debounce` 120 ms,
// mensaje sin resultados, Enter con resultado único navega.
//
// NOTA: este módulo sustituye por completo al `alcaldia.js` anterior (que era la tabla de AGEB de
// una alcaldía con su propio buscador de clave, contrato v1.1/v1.2). Esa responsabilidad ya la
// cubre `ranking.js` (vista de alcaldía, F50) con el mismo `composicion.js` que el resumen; el
// buscador de AGEB por clave vive ahora dentro de `ranking.js` -- este archivo es solo la
// selección de alcaldía por nombre (§5.2), una pieza que antes no existía.

import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { despachar, ACCIONES } from "./estado.js";

const DEBOUNCE_BUSCADOR_MS = 120;

/**
 * Monta el buscador de alcaldía por nombre dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @param {Map<string, string>} nombresAlcaldia - `cve_mun -> nombre`.
 * @param {{despachar?: (accion: object) => void}} [opciones]
 */
export function montarAlcaldia(contenedor, nombresAlcaldia, opciones = {}) {
  const despacharAccion = typeof opciones.despachar === "function" ? opciones.despachar : despachar;
  const entradas = [...nombresAlcaldia.entries()]; // [[cve_mun, nombre], ...]

  let consulta = "";
  let temporizador = null;

  const idCampo = "alcaldia-buscador";
  const idResultados = "alcaldia-buscador-resultados";

  const etiqueta = crear("label", { for: idCampo, clase: "alcaldia-buscador__etiqueta" }, [
    textos.buscadorAlcaldia.etiqueta,
  ]);

  const listaResultados = crear("ul", { id: idResultados, clase: "alcaldia-buscador__resultados" });

  function coincidencias() {
    const texto = consulta.trim().toLowerCase();
    if (texto === "") return [];
    return entradas.filter(([, nombre]) => nombre.toLowerCase().includes(texto));
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
          textos.buscadorAlcaldia.sinResultados({ texto: consulta.trim() }),
        ]),
      ]);
      return;
    }
    reemplazarContenido(
      listaResultados,
      filas.map(([cveMun, nombre]) =>
        crear("li", {}, [
          crear(
            "button",
            {
              type: "button",
              clase: "alcaldia-buscador__opcion",
              onclick: () => {
                despacharAccion({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: cveMun });
                consulta = "";
                campo.value = "";
                renderResultados();
              },
            },
            [nombre],
          ),
        ])),
    );
  }

  function irSiResultadoUnico() {
    const filas = coincidencias();
    if (filas.length === 1) {
      despacharAccion({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: filas[0][0] });
      consulta = "";
      campo.value = "";
      renderResultados();
    }
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
