// frontend/js/explicacion.js
//
// "¿Qué explica este resultado?" -- bloque de explicación por rama (plans/frontend_specs.md
// §10.7, plan F87), dentro de Nivel 2 (drawer "Entender esta zona"). Círculos NO editables,
// deliberadamente distintos de los de `prioridades.js` (§10.10): `--tinta-2`, sin borde
// interactivo, `aria-readonly`. Representan la intensidad de la señal de cada rama en el
// resultado de esa zona, después de filtros y pesos -- nunca una frase automática.
//
// ALCANCE: el spec pide un icono "?" POR RAMA con una frase de ejemplo dinámica ("Educación y
// cultura: la disponibilidad... es relativamente baja frente a otras zonas comparables"). Eso no
// es una ayuda de 3 partes fija como las de `ayuda.js` (que documentan un concepto, no el
// resultado concreto de una zona) -- generar esa frase por zona sería la clase de "texto
// interpretativo autogenerado" que CLAUDE.md/el spec prohíben en otros lados (§6, §6.4). Se omite
// aquí por esa razón, documentado en vez de fingido: los círculos + el valor/peso/contribución de
// abajo ya son la explicación estructurada, sin frase.

import { crear } from "./dom.js";
import { textos } from "./textos.js";

const CIRCULOS = 5;

function crearCirculosLectura(valor0a1, etiquetaAria) {
  const llenos = Number.isNaN(valor0a1) ? 0 : Math.max(0, Math.min(CIRCULOS, Math.round(valor0a1 * CIRCULOS)));
  const contenedor = crear("span", {
    clase: "explicacion__circulos",
    role: "img",
    "aria-readonly": "true",
    "aria-label": etiquetaAria,
  });
  for (let i = 1; i <= CIRCULOS; i++) {
    contenedor.appendChild(
      crear("span", { clase: `explicacion__circulo ${i <= llenos ? "explicacion__circulo--lleno" : ""}`, "aria-hidden": "true" }),
    );
  }
  return contenedor;
}

/**
 * Construye el bloque de explicación por rama.
 *
 * @param {Array<{rama: string, valor: number, peso: number, contribucionPct: number|null}>} filas
 *   `valor` ∈ [0,1] (`O_{i,r}`/`F_{i,r}`, NaN si sin_datos); `peso` 1-5; `contribucionPct` es la
 *   participación de esa rama en el índice compuesto ya calculado, o `null` si sin dato.
 * @returns {HTMLElement}
 */
export function crearExplicacion(filas) {
  const raiz = crear("section", { clase: "explicacion", "aria-labelledby": "explicacion-titulo" });
  raiz.appendChild(
    crear("h3", { id: "explicacion-titulo", clase: "explicacion__titulo" }, [textos.explicacion.titulo]),
  );

  for (const fila of filas) {
    const nombreRama = textos.rama.nombre[fila.rama] ?? fila.rama;
    const etiquetaAria = textos.explicacion.circuloAriaLabel({
      rama: nombreRama,
      valor: Number.isNaN(fila.valor) ? 0 : Math.round(fila.valor * CIRCULOS),
    });

    const partesDetalle = [textos.explicacion.peso(fila.peso)];
    if (fila.contribucionPct !== null) partesDetalle.push(textos.explicacion.contribucion(fila.contribucionPct.toFixed(0)));

    raiz.appendChild(
      crear("div", { clase: "explicacion__fila" }, [
        crear("span", { clase: "explicacion__nombre" }, [nombreRama]),
        crearCirculosLectura(fila.valor, etiquetaAria),
      ]),
    );
    raiz.appendChild(crear("p", { clase: "explicacion__detalle" }, [partesDetalle.join(" · ")]));
  }

  raiz.appendChild(crear("p", { clase: "explicacion__ayuda" }, [textos.explicacion.ayuda]));
  return raiz;
}
