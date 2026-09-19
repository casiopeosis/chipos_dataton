// frontend/js/cabecera.js
//
// Cabecera de 48 px (spec §5.2) y migas de navegación (spec §10.6, §13). Tarea F25
// (plans/frontend_plan.md). Se suscribe a estado.js y vuelve a pintar las migas y el
// resaltado del nivel activo cada vez que cambia la vista/`cve_mun`/`cvegeo`.
//
// Fuera de alcance de F25 (quedan como placeholders en el DOM, sin lógica, para que las
// tareas que sí les corresponden los sustituyan o los monten encima):
//   - El control segmentado de capas real (F60, js/capas.js): aquí solo se muestra un
//     indicador de solo lectura con la capa activa, dentro de `#control-capas`.
//   - El drawer de metodología (F80, js/franja.js + <dialog> en index.html): el botón
//     "Metodología ↗" existe con `id="boton-metodologia"` pero sin manejador propio.
//   - El modo presentación (F85, js/presentacion.js): el botón "⤢" existe con
//     `id="boton-presentacion"` pero sin manejador propio.
//
// Nombres de alcaldía: el contrato de predicciones (CLAUDE.md) no trae `nombre`, solo
// `cve_mun`/`CVEGEO`. Los nombres oficiales salen del GeoJSON de referencia
// (`data/reference/alcaldias.geojson`), que carga otro módulo (mapa.js/alcaldia.js, F65/F45).
// Para no acoplar esta tarea a esa carga, `cabecera.js` expone `establecerNombreAlcaldia`
// para que, cuando ese nombre esté disponible, quien lo tenga lo registre aquí; mientras
// tanto la miga de alcaldía degrada con gracia mostrando la clave (`CVE_MUN {cve_mun}`).

import { suscribir, obtenerEstado, despachar, ACCIONES, VISTA, serializarHash } from "./estado.js";
import { crear, reemplazarContenido, limpiar } from "./dom.js";
import { textos, digitosSeparados } from "./textos.js";
import { CAPAS } from "./config.js";

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

/**
 * Indicador de solo lectura de la capa activa. F100/main.js monta el control real de F60
 * (`capas.js#montarControlCapas`) sobre este mismo `#control-capas` en cuanto los datos cargan, y
 * marca el contenedor con `dataset.montado = "capas-real"`; a partir de ahí este render de
 * respaldo se desactiva para no pisar el `role="radiogroup"` de capas.js en cada cambio de estado.
 */
function pintarControlCapas(contenedor, estado) {
  if (contenedor.dataset.montado === "capas-real") return;
  const botones = CAPAS.map((clave) =>
    crear(
      "span",
      {
        clase: `cabecera__capa${estado.capa === clave ? " cabecera__capa--activa" : ""}`,
        "aria-hidden": estado.capa === clave ? null : "true",
      },
      [textos.capa.nombre[clave]],
    ),
  );
  reemplazarContenido(contenedor, botones);
}

let elementoMigas = null;

/**
 * Monta la cabecera dentro de `elementoHeader` (el `<header>` de index.html) y la deja
 * suscrita a estado.js. Devuelve una función para desmontar la suscripción (uso en pruebas).
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

  const controlCapas = crear("div", {
    id: "control-capas",
    clase: "cabecera__capas",
    role: "group",
    "aria-label": "Capa activa",
  });

  const botonMetodologia = crear(
    "button",
    { type: "button", id: "boton-metodologia", clase: "cabecera__boton" },
    [textos.metodologia.enlaceCabecera],
  );

  const botonPresentacion = crear(
    "button",
    {
      type: "button",
      id: "boton-presentacion",
      clase: "cabecera__boton cabecera__boton--icono",
      "aria-label": textos.presentacion.boton,
    },
    [textos.presentacion.simbolo],
  );

  const fila = crear("div", { clase: "cabecera__fila" }, [
    crear("span", { clase: "cabecera__producto" }, [textos.producto.nombre]),
    nav,
    controlCapas,
    crear("div", { clase: "cabecera__acciones" }, [botonMetodologia, botonPresentacion]),
  ]);

  elementoHeader.appendChild(h1);
  elementoHeader.appendChild(fila);

  const pintar = (estado) => {
    pintarMigas(nav, estado);
    pintarControlCapas(controlCapas, estado);
  };
  pintar(obtenerEstado());

  return suscribir(pintar);
}

// Autoarranque: hasta que exista js/main.js (F100, "arranque, orquesta módulos"), este módulo
// es su propio punto de entrada cuando index.html lo carga con <script type="module">. F100
// solo necesita cambiar ese `src` a "js/main.js" e importar/llamar `iniciarCabecera` desde ahí;
// nada de este bloque estorba esa migración (`iniciarCabecera` es idempotente: limpia y vuelve
// a montar el `<header>` cada vez que se invoca).
if (typeof document !== "undefined") {
  const elementoHeader = document.querySelector("body > header");
  if (elementoHeader) iniciarCabecera(elementoHeader);
}
