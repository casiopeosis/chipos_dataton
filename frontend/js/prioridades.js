// frontend/js/prioridades.js
//
// Prioridades (pesos) por rama (plans/frontend_specs.md §10.10, plan F35). Componente nuevo: no
// hay `<input type="range">` nativo que dé "cinco círculos clicables + flechas" a la vez, así que
// cada rama es un `role="slider"` propio (aria-valuemin=1, aria-valuemax=5) hecho de 5 círculos:
// clic/toque en un círculo fija el peso hasta ese punto, flechas izquierda/derecha (o abajo/arriba)
// con foco en el grupo cambian el valor en 1, todo sin recargar datos (§17.4: solo reordena
// cliente).

import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { RAMAS } from "./composicion.js";
import { despachar, suscribir, obtenerEstado, ACCIONES } from "./estado.js";

const PESO_MINIMO = 1;
const PESO_MAXIMO = 5;

function crearCirculos(rama, pesoActual, onCambiar) {
  const circulos = [];
  const contenedorCirculos = crear("div", { clase: "prioridades__circulos" });

  for (let valor = PESO_MINIMO; valor <= PESO_MAXIMO; valor++) {
    const circulo = crear("span", {
      clase: `prioridades__circulo ${valor <= pesoActual ? "prioridades__circulo--lleno" : ""}`,
      "aria-hidden": "true",
      onclick: () => onCambiar(valor),
    });
    circulos.push(circulo);
    contenedorCirculos.appendChild(circulo);
  }

  const slider = crear(
    "div",
    {
      clase: "prioridades__slider",
      role: "slider",
      tabindex: "0",
      "aria-label": textos.prioridades.circuloAriaLabel({ rama: textos.rama.nombre[rama] ?? rama, peso: pesoActual }),
      "aria-valuemin": String(PESO_MINIMO),
      "aria-valuemax": String(PESO_MAXIMO),
      "aria-valuenow": String(pesoActual),
      onkeydown: (evento) => {
        let siguiente = null;
        if (evento.key === "ArrowRight" || evento.key === "ArrowUp") siguiente = Math.min(PESO_MAXIMO, pesoActual + 1);
        else if (evento.key === "ArrowLeft" || evento.key === "ArrowDown") siguiente = Math.max(PESO_MINIMO, pesoActual - 1);
        else if (evento.key === "Home") siguiente = PESO_MINIMO;
        else if (evento.key === "End") siguiente = PESO_MAXIMO;
        if (siguiente !== null) {
          evento.preventDefault();
          onCambiar(siguiente);
        }
      },
    },
    [contenedorCirculos],
  );

  return { slider, circulos };
}

/**
 * Monta el panel de prioridades por rama dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @returns {() => void} función para desmontar (cancela la suscripción a `estado.js`).
 */
export function montarPrioridades(contenedor) {
  const raiz = crear("section", { clase: "prioridades", "aria-labelledby": "prioridades-titulo" });
  const titulo = crear("h3", { id: "prioridades-titulo", clase: "prioridades__titulo" }, [textos.prioridades.titulo]);
  raiz.appendChild(titulo);

  const estadoInicial = obtenerEstado();
  /** @type {Map<string, {slider: HTMLElement, circulos: HTMLElement[]}>} */
  const controles = new Map();

  for (const rama of RAMAS) {
    const fila = crear("div", { clase: "prioridades__fila" }, [
      crear("span", { clase: "prioridades__nombre" }, [textos.rama.nombre[rama] ?? rama]),
    ]);
    const { slider, circulos } = crearCirculos(rama, estadoInicial.pesos[rama], (valor) => {
      despachar({ tipo: ACCIONES.CAMBIAR_PESO, rama, peso: valor });
    });
    fila.appendChild(slider);
    controles.set(rama, { slider, circulos });
    raiz.appendChild(fila);
  }

  const botonRestablecer = crear(
    "button",
    { type: "button", clase: "prioridades__restablecer", onclick: () => despachar({ tipo: ACCIONES.RESTABLECER_PESOS }) },
    [textos.prioridades.restablecer],
  );
  raiz.appendChild(botonRestablecer);
  raiz.appendChild(crear("p", { clase: "prioridades__ayuda" }, [textos.prioridades.ayuda]));

  reemplazarContenido(contenedor, [raiz]);

  function reflejarPesos(estado) {
    for (const rama of RAMAS) {
      const peso = estado.pesos[rama];
      const { slider, circulos } = controles.get(rama);
      slider.setAttribute("aria-valuenow", String(peso));
      slider.setAttribute("aria-label", textos.prioridades.circuloAriaLabel({ rama: textos.rama.nombre[rama] ?? rama, peso }));
      circulos.forEach((circulo, indice) => {
        const lleno = indice + 1 <= peso;
        circulo.classList.toggle("prioridades__circulo--lleno", lleno);
      });
    }
  }

  return suscribir(reflejarPesos);
}
