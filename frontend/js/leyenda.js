// frontend/js/leyenda.js
//
// Leyenda con conteos, filtro y realce (plans/frontend_plan.md §5, F75; plans/frontend_specs.md
// §10.4). Autocontenido: se suscribe a `estado.js` para saber la vista activa (ciudad → cuenta
// alcaldías; alcaldía → cuenta AGEB de la alcaldía activa), la capa y el horizonte activos, y el
// filtro vigente (`filtroLeyenda`). Nunca lee el JSON v1.1 crudo: recibe los índices ya adaptados
// por `api.js#adaptarV11aV12` (mismo formato que `mapa.js` espera de `datosAdaptados.indices`).
//
// Coordinación con el mapa (F65/F70), SIN tocar `js/mapa.js`/`css/mapa.css`:
// -------------------------------------------------------------------------------------------
// El spec §10.4 pide que, al activar un filtro, "las unidades de otras categorías pasan a
// `--recesivo-relleno`" en el propio mapa. `mapa.js` (F65) todavía no expone ningún gancho para
// esto (no hay `_interno.aplicarFiltro` ni similar) y F70, que continúa ese mismo archivo, es
// quien decide cómo se pintan las AGEB en foco; por eso este módulo NO importa ni llama nada de
// `mapa.js`. En su lugar acopla el realce por **CSS puro**, aprovechando que:
//   - `index.html` ya define `<section id="contenedor-mapa">` como antepasado común del SVG del
//     mapa y de `<aside id="leyenda">` (ver comentario de F65 en `mapa.js`);
//   - `mapa.js` ya pinta cada alcaldía con una clase `mapa__alcaldia--sube-N` / `--baja-N` /
//     `--mantiene` / `--sin-datos` (ver `claseVeredicto` en `mapa.js`).
// Este módulo solo pone/quita `data-filtro-veredicto="<veredicto>"` en `#contenedor-mapa`;
// `leyenda.css` trae las reglas que, con ese atributo puesto, recolorean `.mapa__alcaldia` (hoy)
// y, especulativamente, `.mapa__ageb` (para cuando F70 pinte AGEB con una convención de clase
// análoga `mapa__ageb--<veredicto>[-N]`; si F70 usa otra convención, esas reglas quedan inertes
// y hay que ajustarlas ahí, no aquí). Si `#contenedor-mapa` no existe (p. ej. en las pruebas de
// este módulo, que montan la leyenda en un contenedor suelto), el filtro se sigue aplicando en
// `estado.js` con normalidad; solo no hay realce visual cruzado.
//
// Contrato para F85 (interaccion.js, manejador global de teclado, no implementado aquí):
// -------------------------------------------------------------------------------------------
// "Esc tiene prioridad sobre retroceder de nivel" (spec §10.4, §10.8): antes de despachar
// `ACCIONES.VOLVER`, el manejador de Esc de F85 debe comprobar `obtenerEstado().filtroLeyenda`
// (de `estado.js`, no de este módulo). Si no es `null`, Esc debe limitarse a limpiar el filtro
// (se puede usar `limpiarFiltroLeyenda()`, exportada más abajo, o despachar
// `{tipo: ACCIONES.CAMBIAR_FILTRO, filtro: null}` directamente) y NO retroceder de nivel en el
// mismo toque de Esc.

import { crear, reemplazarContenido, limpiar } from "./dom.js";
import { textos } from "./textos.js";
import { formatoEntero } from "./formato.js";
import { ACCIONES, despachar, suscribir, obtenerEstado, VISTA } from "./estado.js";
import { CLAVE_HORIZONTE_UNICO, VEREDICTOS_VALIDOS } from "./config.js";
import { resolverHorizonte } from "./titular.js";

/** Orden fijo de las 4 filas de veredicto (spec §4.2/§10.4). */
export const ORDEN_VEREDICTOS = Object.freeze(["sube", "se_mantiene", "baja", "sin_datos"]);

/** Id del elemento común mapa+leyenda que index.html ya define (ver comentario de arriba). */
const ID_CONTENEDOR_MAPA = "contenedor-mapa";

// ---------------------------------------------------------------------------------------------
// Funciones puras (probadas en frontend/tests/pruebas_leyenda.js)
// ---------------------------------------------------------------------------------------------

/**
 * Registro plano `{veredicto, confianza, tasa_anual_pct, ...}` de una capa, resuelto al
 * horizonte activo, o `null` si no hay entrada. `entrada` es `{demanda, oferta}`, como produce
 * `api.js#construirIndices`: cada valor conserva su `.h` completo (`{h3:{...}, h5:{...}, ...}`,
 * o `{hU:{...}}` en el camino v1.1) sin aplanar a un horizonte concreto; el aplanado se hace aquí
 * con la clave de horizonte activa (mismo criterio que `main.js#registroPlano`).
 */
function registroPlano(entrada, capaActiva, horizonteActivo) {
  return entrada?.[capaActiva]?.h?.[horizonteActivo] ?? null;
}

/**
 * Lista de registros planos visibles según la vista activa: las alcaldías (vista ciudad) o las
 * AGEB de la alcaldía activa (vista alcaldía/AGEB). Nunca lanza: índices ausentes degradan a
 * lista vacía (conteos en cero, nunca un veredicto inventado).
 *
 * @param {object} opciones
 * @param {boolean} opciones.enAlcaldia - `estado.vista !== VISTA.CIUDAD`.
 * @param {string|null} opciones.cveMun
 * @param {string} opciones.capaActiva
 * @param {string} opciones.horizonteActivo
 * @param {{indices?: {porCveMun?: Map}}|null} opciones.datosAlcaldia - adaptado v1.2, nivel "alcaldia".
 * @param {{indices?: {porCveMun?: Map, porCvegeo?: Map}}|null} opciones.datosAgeb - adaptado v1.2, nivel "ageb".
 * @returns {Array<object|null>}
 */
export function seleccionarRegistrosVisibles(opciones) {
  const {
    enAlcaldia,
    cveMun,
    capaActiva,
    horizonteActivo,
    datosAlcaldia,
    datosAgeb,
  } = opciones ?? {};

  if (!enAlcaldia) {
    const indice = datosAlcaldia?.indices?.porCveMun;
    if (!(indice instanceof Map)) return [];
    return Array.from(indice.values(), (entrada) => registroPlano(entrada, capaActiva, horizonteActivo));
  }

  const clavesPorAlcaldia = datosAgeb?.indices?.porCveMun;
  const porCvegeo = datosAgeb?.indices?.porCvegeo;
  if (!(clavesPorAlcaldia instanceof Map) || !(porCvegeo instanceof Map) || !cveMun) return [];
  const claves = clavesPorAlcaldia.get(cveMun) ?? [];
  return claves.map((cvegeo) => registroPlano(porCvegeo.get(cvegeo), capaActiva, horizonteActivo));
}

/**
 * Cuenta registros planos por veredicto, más `confianzaBaja` (confianza "baja" entre los
 * registros CON veredicto, es decir, excluyendo `sin_datos`: la confianza de una estimación
 * inexistente no aporta nada a "cuánto confiar en el cambio"). Cualquier registro `null` o con
 * `veredicto` fuera del conjunto válido cuenta como `sin_datos` (CLAUDE.md: nunca inventar).
 *
 * @param {Array<object|null>} registrosPlanos
 * @returns {{sube:number, se_mantiene:number, baja:number, sin_datos:number, total:number, confianzaBaja:number}}
 */
export function contarPorVeredicto(registrosPlanos) {
  const lista = Array.isArray(registrosPlanos) ? registrosPlanos : [];
  const conteo = { sube: 0, se_mantiene: 0, baja: 0, sin_datos: 0, total: lista.length, confianzaBaja: 0 };

  for (const registro of lista) {
    const veredicto = VEREDICTOS_VALIDOS.includes(registro?.veredicto) ? registro.veredicto : "sin_datos";
    conteo[veredicto] += 1;
    if (veredicto !== "sin_datos" && registro?.confianza === "baja") conteo.confianzaBaja += 1;
  }

  return conteo;
}

/**
 * Filas de la rampa de brecha de 5 cortes (spec §4.4/§10.4: "escala secuencial en tinta, 5
 * cuantiles" / "rampa de 5 cortes con límites numéricos"). Nunca ocurre con el contrato v1.1
 * (CLAUDE.md, plan §2: `capas.brecha` nunca aparece), así que esta función solo se ejercita hoy
 * con un fixture ficticio (frontend/tests/pruebas_leyenda.js); queda lista para cuando el backend
 * entregue `capas.brecha`.
 *
 * @param {{min:number, max:number, cortes:[number,number,number,number], unidad?:string}|null} brecha
 *   `cortes` son los 3 límites internos que separan 5 cuantiles junto con `min`/`max`... en
 *   realidad son 4 límites internos (5 cuantiles = 4 fronteras entre ellos), de `min` a `max`.
 * @returns {Array<{color:string, desde:number, hasta:number}>} 5 filas, o `[]` si `brecha` no
 *   trae la forma esperada.
 */
export function construirFilasBrecha(brecha) {
  if (!brecha || !Array.isArray(brecha.cortes) || brecha.cortes.length !== 4) return [];
  if (typeof brecha.min !== "number" || typeof brecha.max !== "number") return [];

  const limites = [brecha.min, ...brecha.cortes, brecha.max];
  const filas = [];
  for (let i = 0; i < limites.length - 1; i += 1) {
    filas.push({ color: `brecha-${i + 1}`, desde: limites[i], hasta: limites[i + 1] });
  }
  return filas;
}

/** Despacha la limpieza del filtro. Ver el contrato para F85 en el comentario de cabecera. */
export function limpiarFiltroLeyenda() {
  despachar({ tipo: ACCIONES.CAMBIAR_FILTRO, filtro: null });
}

// ---------------------------------------------------------------------------------------------
// Construcción de nodos (sin innerHTML, dom.js)
// ---------------------------------------------------------------------------------------------

function claseSwatch(veredicto) {
  if (veredicto === "sube") return "sube";
  if (veredicto === "baja") return "baja";
  if (veredicto === "se_mantiene") return "mantiene";
  return "sin-datos";
}

function construirFilaVeredicto({ veredicto, cantidad, activo, onAlternar }) {
  return crear(
    "button",
    {
      type: "button",
      clase: `leyenda__fila leyenda__fila--${veredicto.replace("_", "-")}`,
      // dom.js#crear omite el atributo por completo cuando el valor es `false` (lo trata como
      // "no lo pongas"), pero `aria-pressed` debe estar SIEMPRE presente con "true"/"false"
      // explícito (WAI-ARIA); por eso se pasa como cadena, no como booleano.
      "aria-pressed": activo ? "true" : "false",
      dataset: { veredicto },
      onclick: onAlternar,
    },
    [
      crear("span", { clase: `leyenda__muestra leyenda__muestra--${claseSwatch(veredicto)}`, "aria-hidden": "true" }),
      crear("span", { clase: "leyenda__simbolo", "aria-hidden": "true" }, [textos.veredicto.simbolo[veredicto]]),
      crear("span", { clase: "leyenda__palabra" }, [textos.veredicto.palabra[veredicto]]),
      crear("span", { clase: "leyenda__conteo cifras" }, [formatoEntero(cantidad)]),
    ],
  );
}

function construirFilaIntensidad() {
  const niveles = ["baja-1", "baja-2", "baja-3", "sube-1", "sube-2", "sube-3"];
  return crear("p", { clase: "leyenda__intensidad" }, [
    crear(
      "span",
      { clase: "leyenda__muestras-intensidad", "aria-hidden": "true" },
      niveles.map((nivel) => crear("span", { clase: `leyenda__muestra leyenda__muestra--${nivel}` })),
    ),
    textos.leyenda.intensidad,
  ]);
}

function construirFilaConfianzaBaja(n) {
  return crear("p", { clase: "leyenda__confianza-baja" }, [
    crear("span", { clase: "leyenda__muestra leyenda__muestra--confianza-baja", "aria-hidden": "true" }),
    textos.leyenda.confianzaBaja(n),
  ]);
}

function construirFilaBrecha(brecha) {
  const filas = construirFilasBrecha(brecha);
  if (filas.length === 0) return null;

  const lista = crear(
    "ul",
    { clase: "leyenda__brecha-lista" },
    filas.map((fila) =>
      crear("li", { clase: "leyenda__brecha-corte" }, [
        crear("span", { clase: `leyenda__muestra leyenda__muestra--${fila.color}`, "aria-hidden": "true" }),
        crear("span", { clase: "leyenda__brecha-rango cifras" }, [
          `${formatoEntero(fila.desde)}–${formatoEntero(fila.hasta)}`,
        ]),
      ]),
    ),
  );

  return crear("div", { clase: "leyenda__brecha" }, [
    crear("p", { clase: "leyenda__brecha-titulo" }, [textos.capa.unidadBrecha]),
    lista,
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

/**
 * Horizonte `{clave, anios, fecha}` activo dentro de `datosAdaptados.horizontes`, o el primero si
 * no se encuentra la clave (hoy siempre hay exactamente uno, "hU"; plan §2/§3-1).
 */
function horizonteActivoDe(datosAdaptados, horizonteActivo) {
  const lista = datosAdaptados?.horizontes;
  if (!Array.isArray(lista) || lista.length === 0) return null;
  return lista.find((h) => h.clave === horizonteActivo) ?? lista[0];
}

// ---------------------------------------------------------------------------------------------
// Montaje
// ---------------------------------------------------------------------------------------------

/**
 * Monta la leyenda dentro de `contenedor`. Autocontenida: internamente se suscribe a
 * `estado.js` (vista, capa, horizonte, filtro) y recalcula/repinta en cada cambio.
 *
 * @param {Element} contenedor
 * @param {object} [opcionesIniciales]
 * @param {object|null} [opcionesIniciales.datosAlcaldia] - adaptado v1.2 de nivel "alcaldia"
 *   (`api.js#adaptarV11aV12(json, "alcaldia")`), o `null` mientras no ha cargado.
 * @param {object|null} [opcionesIniciales.datosAgeb] - adaptado v1.2 de nivel "ageb", o `null`.
 * @param {Map<string,string>|Record<string,string>|null} [opcionesIniciales.nombresAlcaldia] -
 *   nombre de alcaldía por `cve_mun`, para el encabezado en vista de alcaldía.
 * @param {{min:number,max:number,cortes:number[],unidad?:string}|null} [opcionesIniciales.brecha] -
 *   ver `construirFilasBrecha`; nunca llega con v1.1, solo se ejercita en pruebas.
 * @returns {{actualizar(parcial: object): void, destruir(): void}}
 */
export function montarLeyenda(contenedor, opcionesIniciales = {}) {
  if (!(contenedor instanceof Element)) {
    throw new TypeError("montarLeyenda: contenedor debe ser un elemento del DOM");
  }

  let datos = {
    datosAlcaldia: opcionesIniciales.datosAlcaldia ?? null,
    datosAgeb: opcionesIniciales.datosAgeb ?? null,
    nombresAlcaldia: opcionesIniciales.nombresAlcaldia ?? null,
    brecha: opcionesIniciales.brecha ?? null,
  };

  contenedor.classList.add("leyenda");

  function elementoRealceMapa() {
    return document.getElementById(ID_CONTENEDOR_MAPA) ?? contenedor.closest(".contenedor-mapa") ?? null;
  }

  function reflejarFiltroEnMapa(filtro) {
    const el = elementoRealceMapa();
    if (!el) return; // supuesto documentado arriba: sin ese contenedor no hay realce cruzado.
    if (filtro) el.setAttribute("data-filtro-veredicto", filtro);
    else el.removeAttribute("data-filtro-veredicto");
  }

  function renderizar() {
    const estado = obtenerEstado();
    const enAlcaldia = estado.vista !== VISTA.CIUDAD;
    const capaActiva = estado.capa;
    const horizonteActivo = estado.horizonte ?? CLAVE_HORIZONTE_UNICO;

    const registrosVisibles = seleccionarRegistrosVisibles({
      enAlcaldia,
      cveMun: estado.cve_mun,
      capaActiva,
      horizonteActivo,
      datosAlcaldia: datos.datosAlcaldia,
      datosAgeb: datos.datosAgeb,
    });
    const conteo = contarPorVeredicto(registrosVisibles);

    const fuenteHorizontes = enAlcaldia ? datos.datosAgeb : datos.datosAlcaldia;
    const horizonte = horizonteActivoDe(fuenteHorizontes, horizonteActivo);
    const { anio } = resolverHorizonte(horizonte ?? {}, fuenteHorizontes?.generado ?? null);

    const nombreCapa = textos.capa.nombre[capaActiva] ?? textos.capa.nombre.demanda;
    const encabezadoTexto = enAlcaldia
      ? textos.leyenda.encabezadoAlcaldia({
          alcaldia: nombreDeAlcaldia(datos.nombresAlcaldia, estado.cve_mun),
          anio: anio ?? "",
        })
      : textos.leyenda.encabezadoGeneral({ capa: nombreCapa, anio: anio ?? "" });

    const encabezado = crear("p", { clase: "leyenda__encabezado" }, [encabezadoTexto]);

    const filas = ORDEN_VEREDICTOS.map((veredicto) =>
      construirFilaVeredicto({
        veredicto,
        cantidad: conteo[veredicto],
        activo: estado.filtroLeyenda === veredicto,
        onAlternar: () => despachar({ tipo: ACCIONES.CAMBIAR_FILTRO, filtro: veredicto }),
      }),
    );
    const listaFilas = crear(
      "ul",
      { clase: "leyenda__filas" },
      filas.map((fila) => crear("li", {}, [fila])),
    );

    const hijos = [
      encabezado,
      listaFilas,
      construirFilaIntensidad(),
      construirFilaConfianzaBaja(conteo.confianzaBaja),
    ];

    // Capa brecha (spec §9: "solo aparece si el archivo trae capas.brecha"). Con v1.1 `capaActiva`
    // nunca vale "brecha" (config.js → CAPAS = ["demanda", "oferta"]), así que en producción de
    // hoy esta fila jamás se agrega; el código queda listo para cuando exista.
    const filaBrecha = capaActiva === "brecha" ? construirFilaBrecha(datos.brecha) : null;
    if (filaBrecha) hijos.push(filaBrecha);

    hijos.push(construirFilaFiltroActivo(estado.filtroLeyenda, conteo));

    reemplazarContenido(contenedor, hijos);
    reflejarFiltroEnMapa(estado.filtroLeyenda);
  }

  renderizar();
  const cancelarSuscripcion = suscribir(renderizar);

  return {
    /** Reemplaza los datos (p. ej. cuando `api.js` termina de cargar/recargar) y repinta. */
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
