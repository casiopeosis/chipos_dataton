// frontend/js/leyenda.js
//
// Leyenda con conteos, filtro y realce (plans/frontend_plan.md F80; plans/frontend_specs.md
// §10.4, §4.2). Habitancia colorea el mapa por QUINTIL de un índice continuo (oportunidad o
// disponibilidad relativa, según `estado.busqueda`), pero la leyenda agrupa en **3 categorías
// legibles** ("Mayor/intermedia/Menor oportunidad relativa", o "...disponibilidad..." en la otra
// búsqueda) -- nunca cinco, spec §10.4/§4.2. Autocontenido para el filtro/realce (se suscribe a
// `estado.js`), pero YA NO calcula el índice: recibe la lista de registros `{valor, quintil,
// tercil, confianzaBaja}` ya resuelta por `composicion.js` a través de `main.js` (mismo principio
// que `mapa.js`: un solo lugar calcula, todos los demás consumen).
//
// Coordinación con el mapa, SIN tocar `js/mapa.js`/`css/mapa.css`:
// -------------------------------------------------------------------------------------------
// Igual que la versión anterior: este módulo solo pone/quita `data-filtro-tercil="<tercil>"` en
// `#contenedor-mapa`; `leyenda.css` trae las reglas que, con ese atributo puesto, recolorean
// `.mapa__alcaldia--prioridad-N`/`.mapa__ageb--prioridad-N` a `--recesivo-relleno` cuando su
// quintil no pertenece al tercil filtrado (1-2→baja, 3→media, 4-5→alta, spec §4.2).
//
// Contrato para interaccion.js (manejador global de teclado):
// -------------------------------------------------------------------------------------------
// "Esc tiene prioridad sobre retroceder de nivel" (spec §10.4, §10.8): antes de despachar
// `ACCIONES.VOLVER`, el manejador de Esc debe comprobar `obtenerEstado().filtroLeyenda`. Si no es
// `null`, Esc debe limitarse a limpiar el filtro (`limpiarFiltroLeyenda()`) y NO retroceder de
// nivel en el mismo toque de Esc.

import { crear, reemplazarContenido, limpiar } from "./dom.js";
import { textos } from "./textos.js";
import { formatoEntero } from "./formato.js";
import { ACCIONES, despachar, suscribir, obtenerEstado, VISTA } from "./estado.js";

/** Orden fijo de las 3 categorías legibles (spec §4.2/§10.4), más sin_datos. */
export const ORDEN_TERCILES = Object.freeze(["alta", "media", "baja", "sin_datos"]);

/** Id del elemento común mapa+leyenda que index.html ya define (ver comentario de cabecera). */
const ID_CONTENEDOR_MAPA = "contenedor-mapa";

// ---------------------------------------------------------------------------------------------
// Funciones puras (probadas en frontend/tests/pruebas_leyenda.js)
// ---------------------------------------------------------------------------------------------

/**
 * Cuenta registros `{tercil, confianzaBaja}` por tercil (spec §10.4). `confianzaBaja` (entre los
 * registros CON dato, es decir, excluyendo `sin_datos`) es la confianza de la DEMANDA que
 * alimenta el índice -- la confianza de una estimación inexistente no aporta nada.
 *
 * @param {Array<{tercil?: string, confianzaBaja?: boolean}|null>} registros
 * @returns {{alta:number, media:number, baja:number, sin_datos:number, total:number, confianzaBaja:number}}
 */
export function contarPorTercil(registros) {
  const lista = Array.isArray(registros) ? registros : [];
  const conteo = { alta: 0, media: 0, baja: 0, sin_datos: 0, total: lista.length, confianzaBaja: 0 };

  for (const registro of lista) {
    const tercil = ORDEN_TERCILES.includes(registro?.tercil) ? registro.tercil : "sin_datos";
    conteo[tercil] += 1;
    if (tercil !== "sin_datos" && registro?.confianzaBaja === true) conteo.confianzaBaja += 1;
  }

  return conteo;
}

/** Despacha la limpieza del filtro. Ver el contrato para interaccion.js en el comentario de cabecera. */
export function limpiarFiltroLeyenda() {
  despachar({ tipo: ACCIONES.CAMBIAR_FILTRO, filtro: null });
}

// ---------------------------------------------------------------------------------------------
// Construcción de nodos (sin innerHTML, dom.js)
// ---------------------------------------------------------------------------------------------

function construirFilaTercil({ tercil, cantidad, activo, onAlternar }) {
  return crear(
    "button",
    {
      type: "button",
      clase: `leyenda__fila leyenda__fila--${tercil.replace("_", "-")}`,
      "aria-pressed": activo ? "true" : "false",
      dataset: { tercil },
      onclick: onAlternar,
    },
    [
      crear("span", { clase: `leyenda__muestra leyenda__muestra--${tercil.replace("_", "-")}`, "aria-hidden": "true" }),
      crear("span", { clase: "leyenda__palabra" }, [textos.tercil.palabra[tercil]]),
      crear("span", { clase: "leyenda__conteo cifras" }, [formatoEntero(cantidad)]),
    ],
  );
}

function construirFilaConfianzaBaja(n) {
  if (n <= 0) return null;
  return crear("p", { clase: "leyenda__confianza-baja" }, [
    crear("span", { clase: "leyenda__muestra leyenda__muestra--confianza-baja", "aria-hidden": "true" }),
    textos.leyenda.confianzaBaja(n),
  ]);
}

function construirFilaFiltroActivo(filtro, conteo) {
  if (!filtro) return crear("p", { clase: "leyenda__filtro-activo", hidden: true });

  const n = conteo[filtro] ?? 0;
  const boton = crear(
    "button",
    { type: "button", clase: "leyenda__quitar-filtro", onclick: () => limpiarFiltroLeyenda() },
    [textos.leyenda.filtroActivo({ n, total: conteo.total })],
  );
  return crear("p", { clase: "leyenda__filtro-activo", "aria-live": "polite" }, [boton]);
}

function nombreDeAlcaldia(fuente, cveMun) {
  if (!fuente || !cveMun) return "";
  if (fuente instanceof Map) return fuente.get(cveMun) ?? "";
  return fuente[cveMun] ?? "";
}

// ---------------------------------------------------------------------------------------------
// Montaje
// ---------------------------------------------------------------------------------------------

/**
 * Monta la leyenda dentro de `contenedor`. Autocontenida para filtro/realce (se suscribe a
 * `estado.js`: vista, filtro), pero los REGISTROS los entrega `main.js` vía `actualizar()` cada
 * vez que `composicion.js` recalcula (cambio de vista de mapa, población, horizonte, búsqueda,
 * pesos o filtros).
 *
 * @param {Element} contenedor
 * @param {object} [opcionesIniciales]
 * @param {Array<{tercil?: string, confianzaBaja?: boolean}>} [opcionesIniciales.registros] -
 *   las unidades visibles (alcaldías en vista ciudad, AGEB de la alcaldía activa en vista
 *   alcaldía/AGEB), ya resueltas por `composicion.js`.
 * @param {Map<string,string>|Record<string,string>|null} [opcionesIniciales.nombresAlcaldia]
 * @param {string} [opcionesIniciales.anio] - año del horizonte activo, para el encabezado.
 * @returns {{actualizar(parcial: object): void, destruir(): void}}
 */
export function montarLeyenda(contenedor, opcionesIniciales = {}) {
  if (!(contenedor instanceof Element)) {
    throw new TypeError("montarLeyenda: contenedor debe ser un elemento del DOM");
  }

  let datos = {
    registros: opcionesIniciales.registros ?? [],
    nombresAlcaldia: opcionesIniciales.nombresAlcaldia ?? null,
    anio: opcionesIniciales.anio ?? "",
  };

  contenedor.classList.add("leyenda");

  function elementoRealceMapa() {
    return document.getElementById(ID_CONTENEDOR_MAPA) ?? contenedor.closest(".contenedor-mapa") ?? null;
  }

  function reflejarFiltroEnMapa(filtro) {
    const el = elementoRealceMapa();
    if (!el) return; // supuesto documentado arriba: sin ese contenedor no hay realce cruzado.
    if (filtro) el.setAttribute("data-filtro-tercil", filtro);
    else el.removeAttribute("data-filtro-tercil");
  }

  function renderizar() {
    const estado = obtenerEstado();
    const enAlcaldia = estado.vista !== VISTA.CIUDAD;
    const conteo = contarPorTercil(datos.registros);

    const nombreVista = textos.vista.nombre[estado.vistaMapa] ?? textos.vista.nombre.general;
    const encabezadoTexto = enAlcaldia
      ? textos.leyenda.encabezadoAlcaldia({
          alcaldia: nombreDeAlcaldia(datos.nombresAlcaldia, estado.cve_mun),
          vista: nombreVista,
          anio: datos.anio ?? "",
        })
      : textos.leyenda.encabezadoGeneral({ vista: nombreVista, anio: datos.anio ?? "" });

    const encabezado = crear("p", { clase: "leyenda__encabezado" }, [encabezadoTexto]);

    const filas = ["alta", "media", "baja", "sin_datos"].map((tercil) =>
      construirFilaTercil({
        tercil,
        cantidad: conteo[tercil],
        activo: estado.filtroLeyenda === tercil,
        onAlternar: () => despachar({ tipo: ACCIONES.CAMBIAR_FILTRO, filtro: tercil }),
      }),
    );
    const listaFilas = crear(
      "ul",
      { clase: "leyenda__filas" },
      filas.map((fila) => crear("li", {}, [fila])),
    );

    const hijos = [encabezado, listaFilas];
    const filaConfianza = construirFilaConfianzaBaja(conteo.confianzaBaja);
    if (filaConfianza) hijos.push(filaConfianza);
    hijos.push(construirFilaFiltroActivo(estado.filtroLeyenda, conteo));

    reemplazarContenido(contenedor, hijos);
    reflejarFiltroEnMapa(estado.filtroLeyenda);
  }

  renderizar();
  const cancelarSuscripcion = suscribir(renderizar);

  return {
    /** Reemplaza los registros/metadatos (p. ej. cuando `composicion.js` recalcula) y repinta. */
    actualizar(parcial) {
      datos = { ...datos, ...(parcial ?? {}) };
      renderizar();
    },
    /** Cancela la suscripción a `estado.js`, limpia el realce cruzado y vacía el contenedor. */
    destruir() {
      cancelarSuscripcion();
      reflejarFiltroEnMapa(null);
      limpiar(contenedor);
      contenedor.classList.remove("leyenda");
    },
  };
}
