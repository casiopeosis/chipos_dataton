// frontend/js/alcaldia.js
//
// Vista de alcaldía (plans/frontend_specs.md §7.3): resumen de 4 líneas sin acordeón, lista de
// AGEB (orden por defecto |cambio| descendente, 12 filas + "Ver los {n} AGEB ↓") y buscador por
// clave con debounce de 120 ms. Sustituye a la tabla de vista general (js/tabla.js) cuando la
// sesión entra a una alcaldía (estado.js, vista "alcaldia").
//
// Reutiliza `resumirVeredictos` (js/veredictos.js) para la barra de distribución del resumen —
// la misma función que usan `js/titular.js` y `js/tabla.js` — y las plantillas de texto de
// `textos.tabla.filaDetalle` para no duplicar redacciones ya escritas para la fila desplegada de
// la tabla general (§7.2 y §7.3 describen el mismo contenido, "compactado").
//
// Autocontenido (plan §9, F45): `montarAlcaldia(contenedor, cveMun, registrosAgeb, opciones)` no
// asume ningún id fijo de `index.html`; construye su propio contenido dentro del contenedor
// recibido y devuelve `{ raiz, actualizar, establecerActiva, destruir }`.

import { texto as t, textos } from "./textos.js";
import { formatoPorcentaje, formatoIntervalo, simboloVeredicto, simboloConfianza } from "./formato.js";
import { crear, reemplazarContenido, limpiar, fijarEstilo } from "./dom.js";
import { resumirVeredictos } from "./veredictos.js";
import { resolverHorizonte } from "./titular.js";
import { despachar as despacharEstado, ACCIONES } from "./estado.js";

// ------------------------------------------------------------------------------------------
// Constantes (spec §7.3)
// ------------------------------------------------------------------------------------------

/** Filas visibles antes de "Ver los {n} AGEB ↓" (spec: "Primero se muestran 12"). */
const FILAS_VISIBLES_POR_DEFECTO = 12;

/** Debounce del buscador (spec: "Filtra por subcadena mientras se escribe, con 120 ms de debounce"). */
const DEBOUNCE_BUSCADOR_MS = 120;

const ORDEN = Object.freeze({ CAMBIO: "cambio", CLAVE: "clave", CONFIANZA: "confianza" });

const RANGO_CONFIANZA = Object.freeze({ alta: 0, media: 1, baja: 2 });

/** Dirección fija de cada orden, para `aria-sort` (mismo patrón que tabla.js). */
const DIRECCION_ARIA = Object.freeze({
  [ORDEN.CAMBIO]: "descending",
  [ORDEN.CLAVE]: "ascending",
  [ORDEN.CONFIANZA]: "descending",
});

// ------------------------------------------------------------------------------------------
// Normalización de registros de entrada
// ------------------------------------------------------------------------------------------

/**
 * `registrosAgeb` es la lista de AGEB de una alcaldía ya resuelta al horizonte activo. Forma
 * esperada por elemento: `{ cvegeo, veredicto, delta_pct, tasa_anual_pct, ic95, confianza,
 * n_obs, motivo_sin_datos }`.
 */
function normalizarFilaAgeb(registroOriginal) {
  const r = registroOriginal ?? {};
  return {
    cvegeo: typeof r.cvegeo === "string" ? r.cvegeo : String(r.cvegeo ?? ""),
    veredicto: r.veredicto ?? "sin_datos",
    deltaPct: typeof r.delta_pct === "number" ? r.delta_pct : null,
    tasaAnualPct: typeof r.tasa_anual_pct === "number" ? r.tasa_anual_pct : null,
    ic95: Array.isArray(r.ic95) && r.ic95.length === 2 ? r.ic95 : null,
    confianza: r.confianza ?? "baja",
    nObs: typeof r.n_obs === "number" ? r.n_obs : 0,
    motivoSinDatos: typeof r.motivo_sin_datos === "string" ? r.motivo_sin_datos : undefined,
  };
}

// ------------------------------------------------------------------------------------------
// Orden (spec §7.3: "Orden por defecto: |cambio| descendente"; también por clave y confianza)
// ------------------------------------------------------------------------------------------

function compararCambioAbsDesc(a, b) {
  const aVal = a.deltaPct === null ? null : Math.abs(a.deltaPct);
  const bVal = b.deltaPct === null ? null : Math.abs(b.deltaPct);
  if (aVal === null && bVal === null) return 0;
  if (aVal === null) return 1; // sin dato al final
  if (bVal === null) return -1;
  return bVal - aVal; // descendente: mayor cambio absoluto primero
}

function compararClave(a, b) {
  return a.cvegeo.localeCompare(b.cvegeo, "es-MX");
}

function compararConfianzaDesc(a, b) {
  const aRango = RANGO_CONFIANZA[a.confianza] ?? 3;
  const bRango = RANGO_CONFIANZA[b.confianza] ?? 3;
  if (aRango !== bRango) return aRango - bRango; // alta (0) primero
  return compararCambioAbsDesc(a, b); // desempate por |cambio|
}

const COMPARADORES = Object.freeze({
  [ORDEN.CAMBIO]: compararCambioAbsDesc,
  [ORDEN.CLAVE]: compararClave,
  [ORDEN.CONFIANZA]: compararConfianzaDesc,
});

function ordenarFilas(filas, orden) {
  const comparador = COMPARADORES[orden] ?? COMPARADORES[ORDEN.CAMBIO];
  return [...filas].sort(comparador);
}

// ------------------------------------------------------------------------------------------
// Resumen de 4 líneas, sin acordeón (spec §7.3: "mismo contenido que la fila desplegada de la
// alcaldía, compactado"): veredicto+cambio+confianza · rango probable · n_obs · distribución.
// ------------------------------------------------------------------------------------------

function crearBarraDistribucion(registrosAgeb) {
  const resumen = resumirVeredictos(registrosAgeb);
  const total = registrosAgeb.length;

  if (total === 0) {
    return crear("p", { clase: "alcaldia__resumen-linea" }, [textos.alcaldia.sinAgeb]);
  }

  const segmentos = [
    ["sube", resumen.nSube],
    ["se_mantiene", resumen.nMant],
    ["baja", resumen.nBaja],
    ["sin_datos", resumen.nSin],
  ];

  const barra = crear("span", { clase: "alcaldia__distribucion-barra", "aria-hidden": "true" });
  for (const [clave, cantidad] of segmentos) {
    if (cantidad <= 0) continue;
    const segmento = crear("span", {
      clase: `alcaldia__distribucion-segmento alcaldia__distribucion-segmento--${clave}`,
    });
    barra.appendChild(segmento);
    fijarEstilo(segmento, { flexGrow: cantidad / total });
  }

  return crear("p", { clase: "alcaldia__resumen-linea alcaldia__distribucion" }, [
    barra,
    crear("span", { clase: "alcaldia__distribucion-texto" }, [
      t("tabla.filaDetalle.distribucion", {
        nBaja: resumen.nBaja,
        nMant: resumen.nMant,
        nSube: resumen.nSube,
        nSin: resumen.nSin,
      }),
    ]),
  ]);
}

function crearResumen(config) {
  const { registroAlcaldia, registrosAgeb, alcaldiaNombre, capa } = config;
  const veredicto = registroAlcaldia?.veredicto ?? "sin_datos";
  const confianzaNivel = registroAlcaldia?.confianza ?? "baja";
  const nObs = typeof registroAlcaldia?.n_obs === "number" ? registroAlcaldia.n_obs : 0;

  // Línea 1: nombre + veredicto + cambio + confianza (wireframe 3, "COYOACÁN ▼ Baja −17.9 % ● alta").
  const linea1 = crear("p", { clase: "alcaldia__resumen-linea alcaldia__resumen-linea--principal" }, [
    crear("span", { clase: "alcaldia__resumen-nombre" }, [alcaldiaNombre]),
    crear("span", { clase: `alcaldia__resumen-veredicto color-veredicto--${veredicto}` }, [
      `${simboloVeredicto(veredicto)} ${t(`veredicto.palabra.${veredicto}`) ?? textos.veredicto.palabra.sin_datos}`,
    ]),
    crear("span", { clase: "alcaldia__resumen-cambio cifras" }, [
      formatoPorcentaje(typeof registroAlcaldia?.delta_pct === "number" ? registroAlcaldia.delta_pct : null),
    ]),
    crear("span", { clase: "alcaldia__resumen-confianza" }, [
      `${simboloConfianza(confianzaNivel)} ${t(`confianza.palabra.${confianzaNivel}`)}`,
    ]),
  ]);

  const lineas = [linea1];

  // Línea 2: rango probable (95 %), si hay ic95.
  const intervalo = formatoIntervalo(registroAlcaldia?.ic95 ?? null);
  if (intervalo) {
    lineas.push(
      crear("p", { clase: "alcaldia__resumen-linea cifras" }, [
        t("tabla.filaDetalle.rangoProbable", intervalo),
      ]),
    );
  }

  // Línea 3: n_obs, según capa (§7.2/§7.3).
  const nObsTexto = capa === "oferta"
    ? textos.tabla.filaDetalle.nObs.oferta(nObs)
    : textos.tabla.filaDetalle.nObs.demanda(nObs);
  lineas.push(crear("p", { clase: "alcaldia__resumen-linea" }, [nObsTexto]));

  // Línea 4: distribución de sus AGEB (barra apilada + texto).
  lineas.push(crearBarraDistribucion(registrosAgeb));

  return crear("div", { clase: "alcaldia__resumen" }, lineas);
}

// ------------------------------------------------------------------------------------------
// Lista de AGEB (tabla real, sin acordeón: el detalle es la ficha, spec §7.3/§7.4)
// ------------------------------------------------------------------------------------------

function crearCeldaVeredicto(fila) {
  return crear(
    "td",
    { clase: `alcaldia__celda alcaldia__celda--veredicto color-veredicto--${fila.veredicto}` },
    [`${simboloVeredicto(fila.veredicto)} ${t(`veredicto.palabra.${fila.veredicto}`) ?? textos.veredicto.palabra.sin_datos}`],
  );
}

function crearFila(fila, cveMun, despachar) {
  const sinDatos = fila.veredicto === "sin_datos";
  const motivo = sinDatos ? textos.motivosSinDatos.obtener(fila.motivoSinDatos) : null;

  const activar = () => {
    despachar({ tipo: ACCIONES.IR_A_AGEB, cve_mun: cveMun, cvegeo: fila.cvegeo });
  };

  const tr = crear(
    "tr",
    {
      clase: `alcaldia__fila${sinDatos ? " alcaldia__fila--sin-datos" : ""}`,
      tabindex: "0",
      dataset: { cvegeo: fila.cvegeo },
      title: motivo ?? undefined,
      onclick: activar,
      onkeydown: (evento) => {
        if (evento.key === "Enter" || evento.key === " ") {
          evento.preventDefault();
          activar();
        }
      },
    },
    [
      crear("td", { clase: "alcaldia__celda alcaldia__celda--clave cifras" }, [fila.cvegeo]),
      crearCeldaVeredicto(fila),
      crear("td", { clase: "alcaldia__celda alcaldia__celda--cambio cifras" }, [
        formatoPorcentaje(fila.deltaPct),
      ]),
      crear(
        "td",
        {
          clase: "alcaldia__celda alcaldia__celda--confianza",
          "aria-label": t("confianza.ariaLabel", { nivel: fila.confianza }),
          title: motivo ?? t("confianza.ariaLabel", { nivel: fila.confianza }),
        },
        [simboloConfianza(fila.confianza)],
      ),
    ],
  );
  return tr;
}

// ------------------------------------------------------------------------------------------
// Componente principal
// ------------------------------------------------------------------------------------------

/**
 * Monta la vista de alcaldía dentro de `contenedor` y devuelve `{ raiz, actualizar,
 * establecerActiva, destruir }`.
 *
 * @param {HTMLElement} contenedor
 * @param {string} cveMun - `CVE_MUN` de 3 dígitos de la alcaldía activa.
 * @param {Array<object>} registrosAgeb - AGEB de la alcaldía (ver `normalizarFilaAgeb`).
 * @param {object} [opciones]
 * @param {"demanda"|"oferta"} [opciones.capa]
 * @param {{fecha?: string|null, anios?: number|null}} [opciones.horizonte]
 * @param {string|null} [opciones.generadoIso]
 * @param {string} [opciones.alcaldiaNombre] - nombre oficial (sale del GeoJSON de referencia,
 *   spec: "Supuesto: los nombres de alcaldía... salen de los GeoJSON de referencia").
 * @param {object|null} [opciones.registroAlcaldia] - el propio registro agregado de la alcaldía
 *   (capa activa), para el resumen de 4 líneas.
 * @param {string} [opciones.orden] - orden inicial de la lista ("cambio" por defecto, spec §7.3).
 * @param {(accion: object) => void} [opciones.despachar] - por defecto, `despachar` de estado.js.
 */
export function montarAlcaldia(contenedor, cveMun, registrosAgeb, opciones = {}) {
  if (!contenedor) {
    throw new TypeError("montarAlcaldia(contenedor): se requiere un contenedor");
  }

  const config = {
    capa: opciones.capa === "oferta" ? "oferta" : "demanda",
    horizonte: opciones.horizonte ?? { fecha: null, anios: null },
    generadoIso: opciones.generadoIso ?? null,
    // Igual que cabecera.js: si el nombre oficial aún no llegó del GeoJSON de referencia,
    // degrada mostrando la clave en vez de inventar un nombre.
    alcaldiaNombre: typeof opciones.alcaldiaNombre === "string" && opciones.alcaldiaNombre !== ""
      ? opciones.alcaldiaNombre
      : `CVE_MUN ${cveMun}`,
    registroAlcaldia: opciones.registroAlcaldia ?? null,
    despachar: typeof opciones.despachar === "function" ? opciones.despachar : despacharEstado,
  };

  let filasBase = (Array.isArray(registrosAgeb) ? registrosAgeb : []).map(normalizarFilaAgeb);
  let orden = opciones.orden ?? ORDEN.CAMBIO;
  let expandido = false;
  let consulta = `09${cveMun}`; // precarga de prefijo (spec §7.3: "09" + CVE_MUN)
  let temporizadorBuscador = null;

  const raiz = crear("div", { clase: "alcaldia-contenedor" });
  const zonaResumen = crear("div", { clase: "alcaldia__resumen-zona" });
  const zonaBuscador = crear("div", { clase: "alcaldia__buscador-zona" });
  const listaContenedor = crear("div", { clase: "alcaldia__lista-contenedor" });
  const caption = crear("caption", { clase: "visualmente-oculto" });
  const thead = crear("thead");
  const tbody = crear("tbody");
  const tabla = crear("table", { clase: "alcaldia__tabla" }, [caption, thead, tbody]);
  listaContenedor.appendChild(tabla);
  const zonaExpandir = crear("div", { clase: "alcaldia__expandir-zona" });

  raiz.appendChild(zonaResumen);
  raiz.appendChild(zonaBuscador);
  raiz.appendChild(listaContenedor);
  raiz.appendChild(zonaExpandir);
  contenedor.appendChild(raiz);

  function anioActual() {
    return resolverHorizonte(config.horizonte, config.generadoIso).anio;
  }

  // ------------------------------------------------------------------------------------------
  // Resumen
  // ------------------------------------------------------------------------------------------

  function renderResumen() {
    reemplazarContenido(zonaResumen, [
      crearResumen({
        registroAlcaldia: config.registroAlcaldia,
        registrosAgeb: filasBase,
        alcaldiaNombre: config.alcaldiaNombre,
        capa: config.capa,
      }),
    ]);
  }

  // ------------------------------------------------------------------------------------------
  // Encabezado de la lista (columnas ordenables, spec §7.3)
  // ------------------------------------------------------------------------------------------

  function crearEncabezadoOrdenable(clave, texto) {
    const boton = crear(
      "button",
      {
        clase: "alcaldia__th-boton",
        type: "button",
        "aria-label": textos.alcaldia.ordenarPor[clave] ?? texto,
        onclick: () => cambiarOrden(clave),
      },
      [texto],
    );
    return crear("th", {
      scope: "col",
      clase: `alcaldia__th alcaldia__th--${clave}`,
      "aria-sort": orden === clave ? DIRECCION_ARIA[clave] : "none",
      dataset: { orden: clave },
    }, [boton]);
  }

  function renderEncabezado() {
    limpiar(thead);
    const anio = anioActual();
    const filaTh = crear("tr", {}, [
      crearEncabezadoOrdenable(ORDEN.CLAVE, textos.tabla.encabezados.ageb),
      crear("th", { scope: "col", clase: "alcaldia__th alcaldia__th--veredicto" }, [
        textos.tabla.encabezados.veredicto,
      ]),
      crearEncabezadoOrdenable(ORDEN.CAMBIO, textos.tabla.encabezados.cambio(config.capa, anio)),
      crearEncabezadoOrdenable(ORDEN.CONFIANZA, textos.tabla.encabezados.confianza),
    ]);
    thead.appendChild(filaTh);
  }

  function actualizarCaption() {
    reemplazarContenido(caption, [
      t("alcaldia.caption", { alcaldia: config.alcaldiaNombre, capa: config.capa, anio: anioActual() }),
    ]);
  }

  function cambiarOrden(nuevoOrden) {
    if (nuevoOrden === orden) return;
    orden = nuevoOrden;
    renderEncabezado();
    renderLista();
  }

  // ------------------------------------------------------------------------------------------
  // Filtro del buscador (spec §7.3: subcadena, sin distinguir may/min, sobre la clave del AGEB)
  // ------------------------------------------------------------------------------------------

  function filasFiltradas() {
    const filasOrdenadas = ordenarFilas(filasBase, orden);
    const consultaNormalizada = consulta.trim().toLowerCase();
    if (consultaNormalizada === "") return filasOrdenadas;
    return filasOrdenadas.filter((fila) => fila.cvegeo.toLowerCase().includes(consultaNormalizada));
  }

  // ------------------------------------------------------------------------------------------
  // Lista (12 filas + "Ver los {n} AGEB ↓", spec §7.3)
  // ------------------------------------------------------------------------------------------

  function renderLista() {
    const filtradas = filasFiltradas();
    limpiar(tbody);
    listaContenedor.classList.toggle("alcaldia__lista-contenedor--expandida", expandido);

    if (filtradas.length === 0) {
      const mensaje = filasBase.length === 0
        ? textos.alcaldia.sinAgeb
        : t("alcaldia.buscador.sinResultados", { texto: consulta });
      const filaVacia = crear("tr", { clase: "alcaldia__fila-vacia" }, [
        crear("td", { colspan: "4", clase: "alcaldia__celda alcaldia__celda--vacia" }, [mensaje]),
      ]);
      tbody.appendChild(filaVacia);
      reemplazarContenido(zonaExpandir, []);
      return;
    }

    const mostrar = expandido ? filtradas : filtradas.slice(0, FILAS_VISIBLES_POR_DEFECTO);
    for (const fila of mostrar) {
      tbody.appendChild(crearFila(fila, cveMun, config.despachar));
    }

    if (!expandido && filtradas.length > FILAS_VISIBLES_POR_DEFECTO) {
      const boton = crear(
        "button",
        {
          clase: "alcaldia__expandir",
          type: "button",
          onclick: () => {
            expandido = true;
            renderLista();
          },
        },
        [t("alcaldia.verTodos", { n: filtradas.length })],
      );
      reemplazarContenido(zonaExpandir, [boton]);
    } else {
      reemplazarContenido(zonaExpandir, []);
    }
  }

  // ------------------------------------------------------------------------------------------
  // Buscador: `<input type="search">`, debounce 120 ms, Enter con resultado único abre la ficha.
  // ------------------------------------------------------------------------------------------

  function irAFichaSiResultadoUnico(valorActual) {
    const consultaNormalizada = valorActual.trim().toLowerCase();
    const coincidencias = ordenarFilas(filasBase, orden).filter((fila) =>
      fila.cvegeo.toLowerCase().includes(consultaNormalizada));
    if (coincidencias.length === 1) {
      config.despachar({ tipo: ACCIONES.IR_A_AGEB, cve_mun: cveMun, cvegeo: coincidencias[0].cvegeo });
    }
  }

  function renderBuscador() {
    const idCampo = "alcaldia-buscador";
    const etiqueta = crear("label", { for: idCampo, clase: "alcaldia__buscador-etiqueta" }, [
      textos.alcaldia.buscador.etiqueta,
    ]);
    const campo = crear("input", {
      id: idCampo,
      type: "search",
      clase: "alcaldia__buscador-campo",
      value: consulta,
      autocomplete: "off",
      "aria-describedby": "alcaldia-buscador-resultado",
      oninput: (evento) => {
        const valorActual = evento.target.value;
        if (temporizadorBuscador !== null) window.clearTimeout(temporizadorBuscador);
        temporizadorBuscador = window.setTimeout(() => {
          consulta = valorActual;
          expandido = false;
          renderLista();
        }, DEBOUNCE_BUSCADOR_MS);
      },
      onkeydown: (evento) => {
        if (evento.key === "Enter") {
          evento.preventDefault();
          if (temporizadorBuscador !== null) {
            window.clearTimeout(temporizadorBuscador);
            temporizadorBuscador = null;
          }
          consulta = evento.target.value;
          expandido = false;
          renderLista();
          irAFichaSiResultadoUnico(evento.target.value);
        }
      },
    });
    reemplazarContenido(zonaBuscador, [etiqueta, campo]);
  }

  // ------------------------------------------------------------------------------------------
  // API pública
  // ------------------------------------------------------------------------------------------

  function actualizar(nuevosRegistrosAgeb, nuevasOpciones = {}) {
    if (Array.isArray(nuevosRegistrosAgeb)) {
      filasBase = nuevosRegistrosAgeb.map(normalizarFilaAgeb);
    }
    if (typeof nuevasOpciones.capa === "string") config.capa = nuevasOpciones.capa;
    if (nuevasOpciones.horizonte) config.horizonte = nuevasOpciones.horizonte;
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "generadoIso")) {
      config.generadoIso = nuevasOpciones.generadoIso;
    }
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "alcaldiaNombre") && nuevasOpciones.alcaldiaNombre) {
      config.alcaldiaNombre = nuevasOpciones.alcaldiaNombre;
    }
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "registroAlcaldia")) {
      config.registroAlcaldia = nuevasOpciones.registroAlcaldia;
    }
    renderResumen();
    actualizarCaption();
    renderEncabezado();
    renderLista();
  }

  /** Realza (sin abrir la ficha) la fila de `cvegeo`, para la sincronía con el mapa (§7.3). */
  function establecerActiva(cvegeo, { desplazar = true } = {}) {
    for (const tr of tbody.querySelectorAll("tr.alcaldia__fila")) {
      tr.classList.toggle("alcaldia__fila--activa", tr.dataset.cvegeo === cvegeo);
    }
    if (cvegeo && desplazar) {
      const filaTr = tbody.querySelector(`tr.alcaldia__fila[data-cvegeo="${CSS.escape(cvegeo)}"]`);
      filaTr?.scrollIntoView({ block: "nearest" });
    }
  }

  function destruir() {
    if (temporizadorBuscador !== null) window.clearTimeout(temporizadorBuscador);
    raiz.remove();
  }

  renderResumen();
  actualizarCaption();
  renderEncabezado();
  renderBuscador();
  renderLista();

  return { raiz, actualizar, establecerActiva, destruir };
}

export const FILAS_VISIBLES = FILAS_VISIBLES_POR_DEFECTO;
export { ORDEN as ORDEN_ALCALDIA };
