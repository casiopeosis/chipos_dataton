// frontend/js/franja.js
//
// Franja lateral (40 px) y drawer modal "Metodología y limitaciones"
// (plans/frontend_specs.md §10.5, §14.6; plans/frontend_plan.md F80).
//
// Responsabilidades:
// - Pintar el botón de la franja (`aria-haspopup="dialog"`, texto rotado -90°) dentro del
//   contenedor que deja index.html (`#franja-metodologia`).
// - Pintar, una sola vez, el contenido íntegro del drawer (§14.6, ya centralizado en
//   textos.js) dentro del `<dialog>` que deja index.html (`#drawer-metodologia`).
// - Abrir/cerrar el `<dialog>` como reacción a `estado.js` (`drawerAbierto`), nunca al revés:
//   todo cierre manual (Esc, clic fuera, botón "Cerrar ✕") despacha `ACCIONES.CERRAR_DRAWER`
//   y es la notificación de estado.js la que de verdad anima y cierra el `<dialog>`. Así el
//   hash `#/…&info=1` (que ya deja `drawerAbierto=true` desde el arranque, vía
//   `estado.js`/`analizarHash`) abre el drawer sin que este módulo tenga que leer el hash.
// - Foco inicial en el título al abrir; al cerrar, el foco vuelve al elemento que tenía el
//   foco justo antes de abrir (normalmente el botón de la franja: es el único disparador del
//   drawer — el botón "Metodología ↗" de la cabecera se eliminó, ver js/cabecera.js).

import { suscribir, obtenerEstado, despachar, ACCIONES } from "./estado.js";
import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";

const ID_TITULO_DRAWER = "drawer-metodologia-titulo";

/** Margen de seguridad si `transitionend` no llega a disparar (p. ej. duración 0 con movimiento reducido, no soportado igual en todos los motores). */
const RESERVA_CIERRE_MS = 260;

/**
 * Arma el contenido íntegro del drawer (§14.6: las secciones de `textos.metodologia.secciones`)
 * dentro de `dialogo`, una sola vez. Devuelve el `<h2>` del título, para poder enfocarlo.
 *
 * @param {HTMLDialogElement} dialogo
 * @param {string|null} generado - fecha ya formateada (p. ej. "18 sep 2026"); si aún no se
 *   conoce (los datos reales no han cargado), se usa un guion largo, nunca una cifra inventada.
 */
function pintarContenidoDrawer(dialogo, generado) {
  const titulo = crear(
    "h2",
    { id: ID_TITULO_DRAWER, tabindex: "-1", clase: "franja__titulo" },
    [textos.metodologia.tituloDrawer],
  );

  const botonCerrar = crear(
    "button",
    {
      type: "button",
      clase: "franja__cerrar",
      onclick: () => despachar({ tipo: ACCIONES.CERRAR_DRAWER }),
    },
    [textos.metodologia.cerrar, " ", crear("span", { "aria-hidden": "true" }, ["✕"])],
  );

  const cabeceraDrawer = crear("div", { clase: "franja__cabecera-drawer" }, [titulo, botonCerrar]);

  const generadoTexto = typeof generado === "string" && generado !== "" ? generado : "—";
  const secciones = textos.metodologia.secciones(generadoTexto).map((seccion) => {
    const hijos = [crear("h3", { clase: "franja__seccion-titulo" }, [seccion.titulo])];
    if (Array.isArray(seccion.parrafos)) {
      for (const parrafo of seccion.parrafos) {
        hijos.push(crear("p", { clase: "franja__parrafo" }, [parrafo]));
      }
    }
    if (Array.isArray(seccion.lista)) {
      hijos.push(
        crear(
          "ul",
          { clase: "franja__lista" },
          seccion.lista.map((item) => crear("li", {}, [item])),
        ),
      );
    }
    return crear("section", { clase: "franja__seccion" }, hijos);
  });

  reemplazarContenido(dialogo, [
    cabeceraDrawer,
    crear("div", { clase: "franja__cuerpo" }, secciones),
  ]);

  return titulo;
}

/**
 * Arma el contenido del drawer para "Entender esta zona" (§10.5-§10.7, Nivel 2): gráficas de
 * población/servicios/cobertura ya renderizadas por `main.js` (vía `graficas.js`/`explicacion.js`,
 * este módulo no conoce `composicion.js`) más el bloque de explicación por rama. Mismo patrón que
 * `pintarContenidoDrawer`: devuelve el `<h2>` para enfocarlo al abrir.
 *
 * @param {HTMLDialogElement} dialogo
 * @param {ReturnType<typeof import("./main.js").construirDatosZona>} datosZona
 */
function pintarContenidoZona(dialogo, datosZona) {
  const titulo = crear("h2", { id: ID_TITULO_DRAWER, tabindex: "-1", clase: "franja__titulo" }, [datosZona.titulo]);

  const botonCerrar = crear(
    "button",
    { type: "button", clase: "franja__cerrar", onclick: () => despachar({ tipo: ACCIONES.CERRAR_DRAWER }) },
    [textos.metodologia.cerrar, " ", crear("span", { "aria-hidden": "true" }, ["✕"])],
  );
  const cabeceraDrawer = crear("div", { clase: "franja__cabecera-drawer" }, [titulo, botonCerrar]);

  const seccionPoblacion = crear("section", { clase: "franja__seccion" }, [
    crear("h3", { clase: "franja__seccion-titulo" }, [textos.graficas.poblacion.titulo]),
    datosZona.poblacionGrafica ?? crear("p", { clase: "franja__parrafo" }, [textos.graficas.sinDatos]),
  ]);

  const seccionServicios = crear(
    "section",
    { clase: "franja__seccion" },
    datosZona.serviciosPorRama.map((s) =>
      crear("div", { clase: "grafica__bloque" }, [
        crear("p", { clase: "grafica__etiqueta" }, [s.etiqueta]),
        s.grafica,
      ])),
  );

  const seccionCobertura = crear("section", { clase: "franja__seccion" }, [
    crear("h3", { clase: "franja__seccion-titulo" }, [textos.graficas.cobertura.titulo]),
    ...datosZona.coberturaPorRama.map((c) =>
      crear("div", { clase: "grafica__bloque" }, [
        crear("p", { clase: "grafica__etiqueta" }, [c.etiqueta]),
        c.grafica,
      ])),
  ]);

  reemplazarContenido(dialogo, [
    cabeceraDrawer,
    crear("div", { clase: "franja__cuerpo" }, [
      seccionPoblacion,
      seccionServicios,
      seccionCobertura,
      datosZona.explicacionNodo,
    ]),
  ]);

  return titulo;
}

/** Pinta el botón de la franja lateral (spec §10.5: "toda la franja es un `<button>`"). */
function pintarBotonFranja(contenedor, idDialogo) {
  const boton = crear(
    "button",
    {
      type: "button",
      clase: "franja__boton",
      "aria-haspopup": "dialog",
      "aria-controls": idDialogo,
      "aria-expanded": obtenerEstado().drawerAbierto ? "true" : "false",
    },
    [textos.metodologia.franja],
  );
  reemplazarContenido(contenedor, [boton]);
  return boton;
}

/**
 * Abre el `<dialog>` con la animación de entrada (300 ms, `--ease-salida`, spec §10.5) y mueve
 * el foco a su título. No hace nada si ya estaba abierto (llamada idempotente).
 */
function abrirDialogo(dialogo, tituloEl) {
  if (dialogo.open) return;
  dialogo.classList.add("franja__drawer--entrando");
  dialogo.showModal();
  // Doble rAF: deja que el navegador pinte el estado inicial (fuera de pantalla) antes de
  // aplicar la clase que dispara la transición a la posición final.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => dialogo.classList.add("franja__drawer--visible"));
  });
  tituloEl.focus();
}

/**
 * Cierra el `<dialog>` con la animación de salida (200 ms, spec §10.5) y devuelve el foco al
 * disparador. No hace nada si ya estaba cerrado.
 */
function cerrarDialogo(dialogo, disparador) {
  if (!dialogo.open) return;

  let yaCerrado = false;
  const finalizar = () => {
    if (yaCerrado) return;
    yaCerrado = true;
    dialogo.removeEventListener("transitionend", finalizar);
    dialogo.close();
    dialogo.classList.remove("franja__drawer--entrando");
    if (disparador && typeof disparador.focus === "function" && document.contains(disparador)) {
      disparador.focus();
    }
  };

  dialogo.addEventListener("transitionend", finalizar);
  setTimeout(finalizar, RESERVA_CIERRE_MS);

  // Quitar "entrando" primero deja la duración de salida (200 ms, --d-s) en vez de la de
  // entrada (300 ms, --d-m); ver franja.css.
  dialogo.classList.remove("franja__drawer--entrando");
  dialogo.classList.remove("franja__drawer--visible");
}

/**
 * Monta la franja lateral y el drawer, que sirve dos contenidos distintos según haya o no una
 * zona (AGEB) activa (§10.6: "mismo drawer, dos entradas"): metodología (sin zona) o "Entender
 * esta zona" (Nivel 2: gráficas + explicación por rama, vía `actualizarZona`). Es el único
 * disparador del drawer (el botón "Metodología ↗" que antes vivía en la cabecera se eliminó, ver
 * `js/cabecera.js`).
 *
 * @param {HTMLElement} elementoFranja - contenedor de la franja (`#franja-metodologia`).
 * @param {HTMLDialogElement} elementoDialogo - `<dialog>` de metodología (`#drawer-metodologia`).
 * @param {{generado?: string|null}} [opciones]
 * @returns {{cancelarSuscripcion: () => void, actualizarZona: (datosZona: object|null) => void}}
 */
export function montarFranja(elementoFranja, elementoDialogo, opciones = {}) {
  if (!elementoDialogo.id) elementoDialogo.id = "drawer-metodologia";
  elementoDialogo.classList.add("franja__drawer");
  elementoDialogo.setAttribute("aria-labelledby", ID_TITULO_DRAWER);

  let tituloEl = pintarContenidoDrawer(elementoDialogo, opciones.generado ?? null);
  const botonFranja = pintarBotonFranja(elementoFranja, elementoDialogo.id);

  let zonaActual = null;
  /** Llamado por `main.js` en cada recálculo: `datosZona` (de `construirDatosZona`) o `null`. */
  function actualizarZona(datosZona) {
    zonaActual = datosZona;
  }

  let disparadorActivo = botonFranja;

  botonFranja.addEventListener("click", () => {
    disparadorActivo = botonFranja;
    despachar({ tipo: ACCIONES.ALTERNAR_DRAWER });
  });

  // Clic fuera del contenido (en el propio `<dialog>`, que es donde cae el clic sobre el
  // `::backdrop` en los motores actuales) cierra el drawer.
  elementoDialogo.addEventListener("click", (evento) => {
    if (evento.target === elementoDialogo) {
      despachar({ tipo: ACCIONES.CERRAR_DRAWER });
    }
  });

  // Esc: se intercepta el cierre nativo (`cancel`) para que el cierre pase siempre por
  // estado.js y se anime igual que cualquier otro cierre (spec §10.5, checklist "Esc cierra el
  // drawer y devuelve el foco al disparador").
  elementoDialogo.addEventListener("cancel", (evento) => {
    evento.preventDefault();
    despachar({ tipo: ACCIONES.CERRAR_DRAWER });
  });

  let abiertoAnterior = false;

  const reaccionar = (estado) => {
    const abierto = estado.drawerAbierto;
    botonFranja.setAttribute("aria-expanded", abierto ? "true" : "false");

    if (abierto && !abiertoAnterior) {
      // Repinta el contenido justo antes de abrir, con la zona activa en ese momento (§10.6): el
      // drawer no se mantiene "vivo" mientras está cerrado, así que no hace falta reaccionar a
      // cada cambio de zona, solo al abrir.
      tituloEl = zonaActual
        ? pintarContenidoZona(elementoDialogo, zonaActual)
        : pintarContenidoDrawer(elementoDialogo, opciones.generado ?? null);

      // Si el disparador no viene de un clic propio (p. ej. carga inicial con `&info=1` en el
      // hash), se usa lo que tenga el foco en ese momento o, en su defecto, el botón de la
      // franja, como disparador al que volver al cerrar.
      const activo = document.activeElement;
      if (activo instanceof HTMLElement && activo !== document.body) {
        disparadorActivo = activo;
      }
      abrirDialogo(elementoDialogo, tituloEl);
    } else if (!abierto && abiertoAnterior) {
      cerrarDialogo(elementoDialogo, disparadorActivo);
    }
    abiertoAnterior = abierto;
  };

  const cancelarSuscripcion = suscribir(reaccionar);
  reaccionar(obtenerEstado());

  return { cancelarSuscripcion, actualizarZona };
}
