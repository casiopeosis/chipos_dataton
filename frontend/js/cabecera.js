// frontend/js/cabecera.js
//
// Cabecera de 48 px (spec §5.2) y migas de navegación (spec §10.6, §13). Tarea F25
// (plans/frontend_plan.md). Se suscribe a estado.js y vuelve a pintar las migas y el
// resaltado del nivel activo cada vez que cambia la vista/`cve_mun`/`cvegeo`.
//
// El selector de vista de mapa (§9) vive aquí como contenedor (`#control-vista-mapa`), pero lo
// MONTA `vista_mapa.js#montarVistaMapa` (F65) -- este módulo no reimplementa ese control, solo le
// da un lugar en el layout (`main.js` decide el orden de montaje).
//
// El botón "Metodología ↗" de la cabecera se eliminó (un solo disparador del drawer de
// metodología: la franja lateral derecha, `js/franja.js` → `#franja-metodologia`).
//
// Nombres de alcaldía: el contrato de predicciones (CLAUDE.md) no trae `nombre`, solo
// `cve_mun`/`CVEGEO`. Los nombres oficiales salen del GeoJSON de referencia
// (`data/reference/alcaldias.geojson`), que carga otro módulo (mapa.js/alcaldia.js). Para no
// acoplar esta tarea a esa carga, `cabecera.js` expone `establecerNombreAlcaldia` para que,
// cuando ese nombre esté disponible, quien lo tenga lo registre aquí; mientras tanto la miga de
// alcaldía degrada con gracia mostrando la clave (`CVE_MUN {cve_mun}`).

import { suscribir, obtenerEstado, despachar, ACCIONES, VISTA, serializarHash } from "./estado.js";
import { crear, reemplazarContenido, limpiar } from "./dom.js";
import { textos, digitosSeparados } from "./textos.js";

/** cve_mun (string de 3 dígitos) -> nombre oficial de la alcaldía, si ya se conoce. */
const nombresAlcaldia = new Map();

/**
 * Registra el nombre oficial de una alcaldía para que las migas dejen de mostrar su clave.
 * Pensado para que lo llame mapa.js/alcaldia.js en cuanto carguen el GeoJSON de referencia.
 * Vuelve a pintar las migas de inmediato si la alcaldía registrada es la que está activa.
 *
 * @param {string} cveMun
 * @param {string} nombre
 */
export function establecerNombreAlcaldia(cveMun, nombre) {
  if (typeof cveMun !== "string" || typeof nombre !== "string" || nombre === "") return;
  nombresAlcaldia.set(cveMun, nombre);
  if (elementoMigas && obtenerEstado().cve_mun === cveMun) {
    pintarMigas(elementoMigas, obtenerEstado());
  }
}

function nombreDeAlcaldia(cveMun) {
  return nombresAlcaldia.get(cveMun) ?? `CVE_MUN ${cveMun}`;
}

/**
 * Enlace de miga: `<a>` con el hash de destino real (para que "abrir en pestaña nueva"
 * funcione) que en el clic normal despacha `accion` en vez de dejar que el navegador navegue,
 * así la sesión sigue pasando por `estado.js` (pushState/replaceState consistentes).
 */
function enlaceMiga(hashDestino, accion, textoVisible, { actual = false } = {}) {
  if (actual) {
    return crear(
      "span",
      { "aria-current": "page", clase: "cabecera__miga cabecera__miga--actual" },
      [textoVisible],
    );
  }
  return crear(
    "a",
    {
      href: hashDestino,
      clase: "cabecera__miga",
      onclick: (evento) => {
        evento.preventDefault();
        despachar(accion);
      },
    },
    [textoVisible],
  );
}

function pintarMigas(nav, estado) {
  const items = [];

  const hashCiudad = serializarHash({ ...estado, vista: VISTA.CIUDAD, cve_mun: null, cvegeo: null });
  items.push(
    crear("li", {}, [
      enlaceMiga(
        hashCiudad,
        { tipo: ACCIONES.IR_A_CIUDAD },
        textos.navegacion.raiz,
        { actual: estado.vista === VISTA.CIUDAD },
      ),
    ]),
  );

  if (estado.vista === VISTA.ALCALDIA || estado.vista === VISTA.AGEB) {
    const nombre = nombreDeAlcaldia(estado.cve_mun);
    const hashAlcaldia = serializarHash({ ...estado, vista: VISTA.ALCALDIA, cvegeo: null });
    items.push(
      crear("li", {}, [
        enlaceMiga(
          hashAlcaldia,
          { tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: estado.cve_mun },
          nombre,
          { actual: estado.vista === VISTA.ALCALDIA },
        ),
      ]),
    );
  }

  if (estado.vista === VISTA.AGEB) {
    items.push(
      crear("li", {}, [
        crear(
          "span",
          {
            "aria-current": "page",
            "aria-label": `AGEB ${digitosSeparados(estado.cvegeo)}`,
            clase: "cabecera__miga cabecera__miga--actual",
          },
          [`AGEB ${estado.cvegeo}`],
        ),
      ]),
    );
  }

  reemplazarContenido(nav.querySelector("ol"), items);
}

let elementoMigas = null;

/**
 * Monta la cabecera dentro de `elementoHeader` (el `<header>` de index.html) y la deja
 * suscrita a estado.js. Devuelve `{elemento, contenedorVistaMapa, botonPresentacion, destruir}`:
 * `main.js` monta `vista_mapa.js#montarVistaMapa(contenedorVistaMapa)` y conecta
 * `botonPresentacion` a `presentacion.js`, ninguno de los dos aquí (esta tarea solo da el layout).
 *
 * @param {HTMLElement} elementoHeader
 */
export function iniciarCabecera(elementoHeader) {
  limpiar(elementoHeader);
  elementoHeader.classList.add("cabecera");

  const h1 = crear("h1", { clase: "visualmente-oculto" }, [textos.producto.nombreLargo]);

  const nav = crear("nav", { "aria-label": textos.navegacion.rutaAriaLabel, clase: "cabecera__migas" }, [
    crear("ol", { clase: "cabecera__migas-lista" }, []),
  ]);
  elementoMigas = nav;

  const contenedorVistaMapa = crear("div", { id: "control-vista-mapa", clase: "cabecera__vista-mapa" });

  const botonPresentacion = crear(
    "button",
    {
      type: "button",
      id: "boton-presentacion",
      clase: "cabecera__boton cabecera__boton--icono",
      "aria-label": textos.presentacion.boton,
      "aria-pressed": "false",
    },
    [textos.presentacion.simbolo],
  );

  const fila = crear("div", { clase: "cabecera__fila" }, [
    crear("span", { clase: "cabecera__producto" }, [textos.producto.nombre]),
    nav,
    contenedorVistaMapa,
    crear("div", { clase: "cabecera__acciones" }, [botonPresentacion]),
  ]);

  elementoHeader.appendChild(h1);
  elementoHeader.appendChild(fila);

  pintarMigas(nav, obtenerEstado());
  const cancelarSuscripcion = suscribir((estado) => pintarMigas(nav, estado));

  return {
    elemento: elementoHeader,
    contenedorVistaMapa,
    botonPresentacion,
    destruir: cancelarSuscripcion,
  };
}
