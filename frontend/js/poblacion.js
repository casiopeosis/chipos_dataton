// frontend/js/poblacion.js
//
// Selector de población objetivo (plans/frontend_specs.md §5.3, plan F31). Mismo patrón accesible
// que `vista_mapa.js`: `role="radiogroup"` con `<input type="radio">` estilizados, un `name` único
// por montaje (soporta varias instancias en la misma página, p. ej. pruebas).

import { crear, texto as nodoTexto, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { SEGMENTOS_DEMANDA } from "./config.js";
import { despachar, suscribir, obtenerEstado, ACCIONES } from "./estado.js";
import { crearAyuda } from "./ayuda.js";

let contador = 0;

/**
 * Monta el selector de población objetivo dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @returns {() => void} función para desmontar (cancela la suscripción a `estado.js`).
 */
export function montarPoblacion(contenedor) {
  contador += 1;
  const nombreGrupo = `poblacion-${contador}`;
  const entradas = new Map();

  const titulo = crear("div", { clase: "poblacion__titulo" }, [
    crear("span", {}, [textos.poblacion.controlEtiqueta]),
    crearAyuda("poblacionObjetivo", textos.poblacion.controlEtiqueta),
  ]);

  const grupo = crear("div", {
    clase: "poblacion",
    role: "radiogroup",
    "aria-label": textos.poblacion.controlEtiqueta,
  });

  const activaInicial = obtenerEstado().poblacion;

  for (const segmento of SEGMENTOS_DEMANDA) {
    const id = `${nombreGrupo}-${segmento}`;

    const entrada = crear("input", {
      type: "radio",
      name: nombreGrupo,
      id,
      value: segmento,
      clase: "poblacion__entrada",
      dataset: { segmento },
      checked: segmento === activaInicial,
      onchange: () => despachar({ tipo: ACCIONES.CAMBIAR_POBLACION, poblacion: segmento }),
    });

    const etiqueta = crear(
      "label",
      { for: id, clase: "poblacion__opcion" },
      [nodoTexto(textos.poblacion.nombre[segmento])],
    );

    entradas.set(segmento, entrada);
    grupo.appendChild(entrada);
    grupo.appendChild(etiqueta);
  }

  // Nota de confianza tope "media" para adolescencia (spec §5.3): no se explica la razón
  // estadística aquí, solo se advierte, visible siempre (no solo cuando el segmento está activo,
  // para que se pueda anticipar antes de elegirlo).
  const nota = crear("p", { clase: "poblacion__nota" }, [textos.poblacion.notaAdolescencia]);

  reemplazarContenido(contenedor, [titulo, grupo, nota]);

  function reflejarActiva(estado) {
    for (const [segmento, entrada] of entradas) {
      entrada.checked = segmento === estado.poblacion;
    }
  }

  return suscribir(reflejarActiva);
}
