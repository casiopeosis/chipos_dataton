// frontend/js/tabla.js
//
// Tabla de predicciones, vista general (plans/frontend_specs.md §7.1-§7.2). 16 filas, una por
// alcaldía, ordenables por cambio/nombre/confianza, con una fila desplegada (acordeón) de 136 px
// animada con FLIP. Reutiliza `resumirVeredictos` (js/veredictos.js, F35) para la barra de
// distribución de AGEB de la fila desplegada, exactamente la misma función que usa el titular, de
// modo que ambos nunca puedan divergir.
//
// Este módulo es autocontenido (plan §9, F40): `montarTabla(contenedor, registros, opciones)` no
// asume ningún id fijo de `index.html`; construye su propio `<table>` dentro del contenedor
// recibido y devuelve un objeto con `actualizar`/`destruir`. No hace `fetch` ni lee `estado.js`
// directamente salvo para despachar acciones (con la posibilidad de inyectar `despachar` para
// pruebas), siguiendo el mismo patrón que `js/titular.js`.

import { texto as t, textos } from "./textos.js";
import { formatoPorcentaje, formatoIntervalo, simboloVeredicto, simboloConfianza } from "./formato.js";
import { crear, reemplazarContenido, limpiar, fijarEstilo } from "./dom.js";
import { resumirVeredictos } from "./veredictos.js";
import { resolverHorizonte } from "./titular.js";
import { despachar as despacharEstado, ACCIONES } from "./estado.js";

// ------------------------------------------------------------------------------------------
// Constantes
// ------------------------------------------------------------------------------------------

/** Alto fijo de la fila desplegada (spec §7.2: "altura fija de 136 px para todas las alcaldías"). */
const ALTO_DETALLE_PX = 136;

/** Escala de la mini-barra divergente de cambio (spec §7.1: "escala ±25 %, con tope"). */
const ESCALA_BARRA_PCT = 25;

const ORDEN = Object.freeze({ CAMBIO: "cambio", NOMBRE: "nombre", CONFIANZA: "confianza" });

const RANGO_CONFIANZA = Object.freeze({ alta: 0, media: 1, baja: 2 });

function duracionMs(nombreVariable, porDefecto) {
  if (typeof window === "undefined" || typeof getComputedStyle !== "function") return porDefecto;
  const valor = getComputedStyle(document.documentElement).getPropertyValue(nombreVariable).trim();
  const ms = Number.parseFloat(valor);
  return Number.isFinite(ms) ? ms : porDefecto;
}

/** Lee un `--ease-*` de tokens.css como cadena `cubic-bezier(...)`, para pasarla a la Web
 * Animations API (que no resuelve variables CSS por sí sola). */
function easingCss(nombreVariable, porDefecto) {
  if (typeof window === "undefined" || typeof getComputedStyle !== "function") return porDefecto;
  const valor = getComputedStyle(document.documentElement).getPropertyValue(nombreVariable).trim();
  return valor || porDefecto;
}

function prefiereMovimientoReducido() {
  return (
    typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

// ------------------------------------------------------------------------------------------
// Normalización de registros de entrada
// ------------------------------------------------------------------------------------------

/**
 * `registros` es la lista de 16 alcaldías ya resueltas al horizonte activo, con el nombre oficial
 * ya adjunto por quien llama (spec: "Supuesto: los nombres... salen de los GeoJSON de
 * referencia"; este módulo no hace ese join). Forma esperada por elemento:
 * `{ cve_mun, nombre, veredicto, delta_pct, tasa_anual_pct, ic95, confianza, n_obs }`.
 */
function normalizarFila(registroOriginal) {
  const r = registroOriginal ?? {};
  return {
    cveMun: typeof r.cve_mun === "string" ? r.cve_mun : String(r.cve_mun ?? ""),
    nombre: typeof r.nombre === "string" && r.nombre !== "" ? r.nombre : t("tooltip.ageb", { cvegeo: r.cve_mun ?? "?" }),
    veredicto: r.veredicto ?? "sin_datos",
    deltaPct: typeof r.delta_pct === "number" ? r.delta_pct : null,
    tasaAnualPct: typeof r.tasa_anual_pct === "number" ? r.tasa_anual_pct : null,
    ic95: Array.isArray(r.ic95) && r.ic95.length === 2 ? r.ic95 : null,
    confianza: r.confianza ?? "baja",
    nObs: typeof r.n_obs === "number" ? r.n_obs : 0,
  };
}

// ------------------------------------------------------------------------------------------
// Orden (spec §7.1: cambio ascendente por defecto, nombre A-Z, confianza alta->baja con
// desempate por cambio)
// ------------------------------------------------------------------------------------------

function compararCambio(a, b) {
  const aVal = a.deltaPct;
  const bVal = b.deltaPct;
  if (aVal === null && bVal === null) return 0;
  if (aVal === null) return 1; // sin dato al final
  if (bVal === null) return -1;
  return aVal - bVal; // ascendente: lo que más baja, arriba
}

function compararNombre(a, b) {
  return a.nombre.localeCompare(b.nombre, "es-MX");
}

function compararConfianza(a, b) {
  const aRango = RANGO_CONFIANZA[a.confianza] ?? 3;
  const bRango = RANGO_CONFIANZA[b.confianza] ?? 3;
  if (aRango !== bRango) return aRango - bRango;
  return compararCambio(a, b); // desempate por cambio (spec §7.1)
}

const COMPARADORES = Object.freeze({
  [ORDEN.CAMBIO]: compararCambio,
  [ORDEN.NOMBRE]: compararNombre,
  [ORDEN.CONFIANZA]: compararConfianza,
});

/** Dirección fija de cada tipo de orden, para `aria-sort` (spec §7.1: sin control de reversa). */
const DIRECCION_ARIA = Object.freeze({
  [ORDEN.CAMBIO]: "ascending",
  [ORDEN.NOMBRE]: "ascending",
  [ORDEN.CONFIANZA]: "descending",
});

function ordenarFilas(filas, orden) {
  const comparador = COMPARADORES[orden] ?? COMPARADORES[ORDEN.CAMBIO];
  return [...filas].sort(comparador);
}

// ------------------------------------------------------------------------------------------
// Mini-barra divergente de cambio (spec §7.1: 28 px, escala ±25 %, tope con marca ▸/◂)
// ------------------------------------------------------------------------------------------

function crearBarraCambio(fila) {
  const contenedor = crear("span", { clase: "tabla__barra", "aria-hidden": "true" });
  if (fila.deltaPct === null) return contenedor;

  const excede = Math.abs(fila.deltaPct) > ESCALA_BARRA_PCT;
  const magnitud = Math.min(Math.abs(fila.deltaPct), ESCALA_BARRA_PCT) / ESCALA_BARRA_PCT; // 0..1
  const sentido = fila.deltaPct < 0 ? "baja" : fila.deltaPct > 0 ? "sube" : "neutro";

  const relleno = crear("span", {
    clase: `tabla__barra-relleno tabla__barra-relleno--${sentido}`,
  });
  contenedor.appendChild(relleno);
  fijarEstilo(relleno, { width: `${magnitud * 14}px` });

  if (excede) {
    const marca = crear(
      "span",
      { clase: `tabla__barra-marca tabla__barra-marca--${sentido}` },
      [sentido === "baja" ? "◂" : "▸"],
    );
    contenedor.appendChild(marca);
  }
  return contenedor;
}

// ------------------------------------------------------------------------------------------
// Distribución de AGEB para la fila desplegada (spec §7.2). El adaptador v1.1→v1.2 nunca trae
// `distribucion_ageb` precalculada (plan §2): se reconstruye a partir del GeoJSON de AGEB
// (membresía por CVE_MUN) y, si están disponibles, los veredictos por AGEB ya resueltos al
// horizonte activo. Ambas piezas son opcionales y este módulo degrada con gracia si faltan
// (esqueleto), tal como pide la tarea F40.
// ------------------------------------------------------------------------------------------

/** Construye (una sola vez, perezoso) un índice `cve_mun -> [cvegeo,...]` del GeoJSON de AGEB. */
function indiceGeojsonPorCveMun(geojsonAgeb) {
  const indice = new Map();
  const features = Array.isArray(geojsonAgeb?.features) ? geojsonAgeb.features : [];
  for (const feature of features) {
    const props = feature?.properties ?? {};
    const cveMun = props.cve_mun;
    const cvegeo = props.cvegeo;
    if (typeof cveMun !== "string" || typeof cvegeo !== "string") continue;
    if (!indice.has(cveMun)) indice.set(cveMun, []);
    indice.get(cveMun).push(cvegeo);
  }
  return indice;
}

/**
 * Devuelve `{ resumen, total }` (resumen = salida de `resumirVeredictos`) para los AGEB de una
 * alcaldía, o `null` si el GeoJSON de AGEB aún no está disponible (degradación a esqueleto,
 * spec §7.2: "Si falta `distribucion_ageb` y el GeoJSON de AGEB aún no llega, la barra se
 * muestra en esqueleto").
 */
function calcularDistribucionAgeb(cveMun, opciones) {
  if (!opciones?.geojsonAgeb) return null;
  const indice = opciones._indiceGeojsonPorCveMun ?? indiceGeojsonPorCveMun(opciones.geojsonAgeb);
  const cvegeos = indice.get(cveMun) ?? [];
  // Sin veredictos por AGEB todavía cargados (opciones.registrosAgebPorCvegeo), cada AGEB cuenta
  // como sin_datos: es honesto (no inventa el sentido del cambio) y sigue dando el total real de
  // AGEB de la alcaldía a partir del GeoJSON.
  const registrosAgeb = cvegeos.map((cvegeo) => {
    const registro = opciones.registrosAgebPorCvegeo?.get?.(cvegeo);
    return registro ?? { veredicto: "sin_datos" };
  });
  return { resumen: resumirVeredictos(registrosAgeb), total: cvegeos.length };
}

function crearBarraDistribucion(cveMun, opciones) {
  const distribucion = calcularDistribucionAgeb(cveMun, opciones);

  if (!distribucion) {
    // Esqueleto (spec §15, patrón `--esqueleto` con pulso; aquí sin animación propia: la clase
    // `tabla__distribucion--esqueleto` la anima css/estados.css o, si aún no existe, queda como
    // bloque sólido discreto sin pretender un dato que no llegó).
    return crear("p", { clase: "tabla__distribucion tabla__distribucion--esqueleto" }, [
      textos.tabla.filaDetalle.distribucionCargando,
    ]);
  }

  const { resumen, total } = distribucion;
  if (total === 0) {
    return crear("p", { clase: "tabla__distribucion" }, [textos.tabla.filaDetalle.distribucionSinAgeb]);
  }

  const segmentos = [
    ["sube", resumen.nSube],
    ["se_mantiene", resumen.nMant],
    ["baja", resumen.nBaja],
    ["sin_datos", resumen.nSin],
  ];

  const barra = crear("span", { clase: "tabla__distribucion-barra", "aria-hidden": "true" });
  for (const [clave, cantidad] of segmentos) {
    if (cantidad <= 0) continue;
    const segmento = crear("span", {
      clase: `tabla__distribucion-segmento tabla__distribucion-segmento--${clave}`,
    });
    barra.appendChild(segmento);
    fijarEstilo(segmento, { flexGrow: cantidad / total });
  }

  const parrafo = crear("p", { clase: "tabla__distribucion" }, [
    barra,
    crear("span", { clase: "tabla__distribucion-texto" }, [
      t("tabla.filaDetalle.distribucion", {
        nBaja: resumen.nBaja,
        nMant: resumen.nMant,
        nSube: resumen.nSube,
        nSin: resumen.nSin,
      }),
    ]),
  ]);
  return parrafo;
}

// ------------------------------------------------------------------------------------------
// Construcción de filas
// ------------------------------------------------------------------------------------------

function crearCeldaAlcaldia(fila, opciones) {
  const boton = crear(
    "button",
    {
      clase: "tabla__nombre",
      type: "button",
      onclick: (evento) => {
        evento.stopPropagation();
        opciones.despachar({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: fila.cveMun });
      },
    },
    [fila.nombre],
  );
  return crear("td", { clase: "tabla__celda tabla__celda--alcaldia" }, [boton]);
}

function crearCeldaVeredicto(fila) {
  return crear(
    "td",
    { clase: `tabla__celda tabla__celda--veredicto color-veredicto--${fila.veredicto}` },
    [`${simboloVeredicto(fila.veredicto)} ${t(`veredicto.palabra.${fila.veredicto}`) ?? textos.veredicto.palabra.sin_datos}`],
  );
}

function crearCeldaCambio(fila) {
  return crear("td", { clase: "tabla__celda tabla__celda--cambio cifras" }, [
    crear("span", { clase: "tabla__cambio-cifra" }, [formatoPorcentaje(fila.deltaPct)]),
    crearBarraCambio(fila),
  ]);
}

function crearCeldaConfianza(fila) {
  const etiqueta = t("confianza.ariaLabel", { nivel: fila.confianza });
  return crear(
    "td",
    { clase: "tabla__celda tabla__celda--confianza", "aria-label": etiqueta, title: etiqueta },
    [simboloConfianza(fila.confianza)],
  );
}

function crearFilaDetalle(fila, opciones, anio) {
  const contenido = [];

  if (fila.deltaPct !== null) {
    contenido.push(
      crear("p", { clase: "tabla__detalle-linea cifras" }, [
        t("tabla.filaDetalle.cambioEsperado", { anio, cambio: formatoPorcentaje(fila.deltaPct) }),
      ]),
    );
  }

  const intervalo = formatoIntervalo(fila.ic95);
  if (intervalo) {
    contenido.push(
      crear("p", { clase: "tabla__detalle-linea cifras" }, [
        t("tabla.filaDetalle.rangoProbable", intervalo),
      ]),
    );
  }

  // "Confianza {palabra}: {explicación}" (§7.2) antecedida por el símbolo (§4.2: nunca solo color).
  contenido.push(
    crear("p", { clase: "tabla__detalle-linea" }, [
      `${simboloConfianza(fila.confianza)} ${textos.tabla.filaDetalle.confianzaLinea(fila.confianza)}`,
    ]),
  );

  const nObsTexto = opciones.capa === "oferta"
    ? textos.tabla.filaDetalle.nObs.oferta(fila.nObs)
    : textos.tabla.filaDetalle.nObs.demanda(fila.nObs);
  contenido.push(crear("p", { clase: "tabla__detalle-linea" }, [nObsTexto]));

  contenido.push(crearBarraDistribucion(fila.cveMun, opciones));

  contenido.push(
    crear(
      "button",
      {
        clase: "tabla__explorar",
        type: "button",
        onclick: (evento) => {
          evento.stopPropagation();
          opciones.despachar({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: fila.cveMun });
        },
      },
      [textos.tabla.filaDetalle.explorar],
    ),
  );

  const detalle = crear("div", { clase: "tabla__detalle" }, contenido);
  const celda = crear("td", { clase: "tabla__celda-detalle", colspan: "4" }, [detalle]);
  const tr = crear("tr", {
    clase: "tabla__fila-detalle",
    id: `tabla-detalle-${fila.cveMun}`,
    hidden: true,
  }, [celda]);
  return tr;
}

// ------------------------------------------------------------------------------------------
// Componente principal
// ------------------------------------------------------------------------------------------

/**
 * Monta la tabla de predicciones dentro de `contenedor` y devuelve `{ raiz, actualizar, destruir }`.
 *
 * @param {HTMLElement} contenedor
 * @param {Array<object>} registrosIniciales - 16 registros de alcaldía (ver `normalizarFila`).
 * @param {object} [opciones]
 * @param {"demanda"|"oferta"} [opciones.capa]
 * @param {{fecha?: string|null, anios?: number|null}} [opciones.horizonte]
 * @param {string|null} [opciones.generadoIso]
 * @param {string} [opciones.orden] - orden inicial ("cambio" por defecto, spec §7.1).
 * @param {(accion: object) => void} [opciones.despachar] - por defecto, `despachar` de estado.js.
 * @param {object|null} [opciones.geojsonAgeb] - FeatureCollection de AGEB (para la fila desplegada).
 * @param {Map<string, {veredicto: string, confianza?: string}>} [opciones.registrosAgebPorCvegeo]
 */
export function montarTabla(contenedor, registrosIniciales, opciones = {}) {
  if (!contenedor) {
    throw new TypeError("montarTabla(contenedor): se requiere un contenedor");
  }

  const config = {
    capa: opciones.capa === "oferta" ? "oferta" : "demanda",
    horizonte: opciones.horizonte ?? { fecha: null, anios: null },
    generadoIso: opciones.generadoIso ?? null,
    despachar: typeof opciones.despachar === "function" ? opciones.despachar : despacharEstado,
    geojsonAgeb: opciones.geojsonAgeb ?? null,
    registrosAgebPorCvegeo: opciones.registrosAgebPorCvegeo ?? null,
  };
  if (config.geojsonAgeb) {
    config._indiceGeojsonPorCveMun = indiceGeojsonPorCveMun(config.geojsonAgeb);
  }

  let filas = (Array.isArray(registrosIniciales) ? registrosIniciales : []).map(normalizarFila);
  let orden = opciones.orden ?? ORDEN.CAMBIO;
  let cveMunExpandida = null;
  let temporizadorIntencion = null;
  let temporizadorRepliegue = null;

  const raiz = crear("div", { clase: "tabla-contenedor" });
  const caption = crear("caption", { clase: "visualmente-oculto" });
  const thead = crear("thead");
  const tbody = crear("tbody");
  const tabla = crear("table", { clase: "tabla" }, [caption, thead, tbody]);
  raiz.appendChild(tabla);
  contenedor.appendChild(raiz);

  function anioActual() {
    return resolverHorizonte(config.horizonte, config.generadoIso).anio;
  }

  function actualizarCaption() {
    reemplazarContenido(caption, [t("tabla.caption", { capa: config.capa, anio: anioActual() })]);
  }

  // ------------------------------------------------------------------------------------------
  // Encabezado: columnas ordenables como <button> con aria-sort en el <th> (spec §7.1).
  // ------------------------------------------------------------------------------------------

  function crearEncabezadoOrdenable(clave, texto) {
    const boton = crear(
      "button",
      {
        clase: "tabla__th-boton",
        type: "button",
        "aria-label": textos.tabla.ordenarPor[clave] ?? texto,
        onclick: () => cambiarOrden(clave),
      },
      [texto],
    );
    return crear("th", {
      scope: "col",
      clase: `tabla__th tabla__th--${clave}`,
      "aria-sort": orden === clave ? DIRECCION_ARIA[clave] : "none",
      dataset: { orden: clave },
    }, [boton]);
  }

  function renderEncabezado() {
    limpiar(thead);
    const anio = anioActual();
    const filaTh = crear("tr", {}, [
      crearEncabezadoOrdenable(ORDEN.NOMBRE, textos.tabla.encabezados.alcaldia),
      crear("th", { scope: "col", clase: "tabla__th tabla__th--veredicto" }, [
        textos.tabla.encabezados.veredicto,
      ]),
      crearEncabezadoOrdenable(ORDEN.CAMBIO, textos.tabla.encabezados.cambio(config.capa, anio)),
      crearEncabezadoOrdenable(ORDEN.CONFIANZA, textos.tabla.encabezados.confianza),
    ]);
    thead.appendChild(filaTh);
  }

  // ------------------------------------------------------------------------------------------
  // Acordeón: hover con intención (100 ms), repliegue (180 ms), foco inmediato con teclado.
  // ------------------------------------------------------------------------------------------

  function limpiarTemporizadores() {
    if (temporizadorIntencion !== null) {
      window.clearTimeout(temporizadorIntencion);
      temporizadorIntencion = null;
    }
    if (temporizadorRepliegue !== null) {
      window.clearTimeout(temporizadorRepliegue);
      temporizadorRepliegue = null;
    }
  }

  function expandir(cveMun) {
    if (cveMunExpandida === cveMun) return;
    const anterior = cveMunExpandida;
    cveMunExpandida = cveMun;
    if (anterior !== null) actualizarFilaExpandida(anterior);
    actualizarFilaExpandida(cveMun);
  }

  function plegar(cveMun) {
    if (cveMunExpandida !== cveMun) return;
    cveMunExpandida = null;
    actualizarFilaExpandida(cveMun);
  }

  function actualizarFilaExpandida(cveMun) {
    const filaTr = tbody.querySelector(`tr.tabla__fila[data-cve-mun="${CSS.escape(cveMun)}"]`);
    const detalleTr = tbody.querySelector(`#tabla-detalle-${CSS.escape(cveMun)}`);
    if (!filaTr || !detalleTr) return;
    const expandida = cveMunExpandida === cveMun;
    filaTr.setAttribute("aria-expanded", String(expandida));
    filaTr.classList.toggle("tabla__fila--expandida", expandida);
    detalleTr.hidden = !expandida;
  }

  function programarExpansion(cveMun) {
    limpiarTemporizadores();
    temporizadorIntencion = window.setTimeout(() => {
      expandir(cveMun);
    }, duracionMs("--d-intencion", 100));
  }

  function programarRepliegue(cveMun) {
    limpiarTemporizadores();
    temporizadorRepliegue = window.setTimeout(() => {
      plegar(cveMun);
    }, duracionMs("--d-repliegue", 180));
  }

  // ------------------------------------------------------------------------------------------
  // Orden + FLIP (spec §7.2: "se mide, se aplica el layout y el tbody se traslada del delta a 0
  // en 200 ms con --ease-salida")
  // ------------------------------------------------------------------------------------------

  function medirPosiciones() {
    const posiciones = new Map();
    for (const tr of tbody.querySelectorAll("tr.tabla__fila")) {
      posiciones.set(tr.dataset.cveMun, tr.getBoundingClientRect().top);
    }
    return posiciones;
  }

  function animarFlip(posicionesAntes) {
    if (prefiereMovimientoReducido()) return;
    const duracion = duracionMs("--d-s", 200);
    const easing = easingCss("--ease-salida", "cubic-bezier(0.22, 1, 0.36, 1)");
    for (const tr of tbody.querySelectorAll("tr.tabla__fila")) {
      const antes = posicionesAntes.get(tr.dataset.cveMun);
      if (antes === undefined) continue;
      const despues = tr.getBoundingClientRect().top;
      const delta = antes - despues;
      if (delta === 0) continue;
      // Web Animations API en vez de `tr.style.transform/transition`: la CSP del proyecto
      // (`style-src 'self'`) bloquea cualquier escritura al atributo `style` desde JS, y WAAPI no
      // pasa por ese atributo. Anima directamente de `translateY(delta)` a `translateY(0)`, sin
      // necesitar el truco de forzar reflow que sí hace falta con transiciones CSS clásicas.
      tr.animate(
        [{ transform: `translateY(${delta}px)` }, { transform: "translateY(0)" }],
        { duration: duracion, easing, fill: "both" },
      );
    }
  }

  function cambiarOrden(nuevoOrden) {
    if (nuevoOrden === orden) return;
    orden = nuevoOrden;
    config.despachar({ tipo: ACCIONES.CAMBIAR_ORDEN, orden });
    renderEncabezado();
    renderCuerpo({ conFlip: true });
  }

  // ------------------------------------------------------------------------------------------
  // Render del cuerpo
  // ------------------------------------------------------------------------------------------

  function crearFila(fila) {
    const tr = crear(
      "tr",
      {
        clase: "tabla__fila",
        tabindex: "0",
        "aria-expanded": String(cveMunExpandida === fila.cveMun),
        "aria-controls": `tabla-detalle-${fila.cveMun}`,
        dataset: { cveMun: fila.cveMun },
        onmouseenter: () => programarExpansion(fila.cveMun),
        onmouseleave: () => programarRepliegue(fila.cveMun),
        onfocus: () => {
          limpiarTemporizadores();
          expandir(fila.cveMun);
        },
        onfocusout: (evento) => {
          const destino = evento.relatedTarget;
          const detalle = tbody.querySelector(`#tabla-detalle-${CSS.escape(fila.cveMun)}`);
          if (destino && (tr.contains(destino) || detalle?.contains(destino))) return;
          programarRepliegue(fila.cveMun);
        },
      },
      [
        crearCeldaAlcaldia(fila, config),
        crearCeldaVeredicto(fila),
        crearCeldaCambio(fila),
        crearCeldaConfianza(fila),
      ],
    );
    return tr;
  }

  function crearFilaDetalleConEventos(fila) {
    const detalleTr = crearFilaDetalle(fila, config, anioActual());
    detalleTr.addEventListener("mouseenter", () => {
      limpiarTemporizadores();
    });
    detalleTr.addEventListener("mouseleave", () => programarRepliegue(fila.cveMun));
    return detalleTr;
  }

  function renderCuerpo({ conFlip = false } = {}) {
    const posicionesAntes = conFlip ? medirPosiciones() : null;
    const filasOrdenadas = ordenarFilas(filas, orden);
    limpiar(tbody);
    for (const fila of filasOrdenadas) {
      tbody.appendChild(crearFila(fila));
      tbody.appendChild(crearFilaDetalleConEventos(fila));
    }
    if (posicionesAntes) animarFlip(posicionesAntes);
  }

  // ------------------------------------------------------------------------------------------
  // API pública
  // ------------------------------------------------------------------------------------------

  function actualizar(nuevosRegistros, nuevasOpciones = {}) {
    if (Array.isArray(nuevosRegistros)) {
      filas = nuevosRegistros.map(normalizarFila);
    }
    if (typeof nuevasOpciones.capa === "string") config.capa = nuevasOpciones.capa;
    if (nuevasOpciones.horizonte) config.horizonte = nuevasOpciones.horizonte;
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "generadoIso")) {
      config.generadoIso = nuevasOpciones.generadoIso;
    }
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "geojsonAgeb")) {
      config.geojsonAgeb = nuevasOpciones.geojsonAgeb;
      config._indiceGeojsonPorCveMun = config.geojsonAgeb
        ? indiceGeojsonPorCveMun(config.geojsonAgeb)
        : null;
    }
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "registrosAgebPorCvegeo")) {
      config.registrosAgebPorCvegeo = nuevasOpciones.registrosAgebPorCvegeo;
    }
    actualizarCaption();
    renderEncabezado();
    renderCuerpo({ conFlip: false });
  }

  /** Establece el orden desde afuera (p. ej. al restaurar `&orden=` del hash). */
  function establecerOrden(nuevoOrden) {
    if (!COMPARADORES[nuevoOrden] || nuevoOrden === orden) return;
    orden = nuevoOrden;
    renderEncabezado();
    renderCuerpo({ conFlip: true });
  }

  /** Sincronización bidireccional con el mapa (spec §7.2): expande/realza la fila de `cveMun`. */
  function establecerActiva(cveMun, { desplazar = true } = {}) {
    limpiarTemporizadores();
    if (cveMun === null) {
      if (cveMunExpandida !== null) plegar(cveMunExpandida);
      return;
    }
    expandir(cveMun);
    if (desplazar) {
      const filaTr = tbody.querySelector(`tr.tabla__fila[data-cve-mun="${CSS.escape(cveMun)}"]`);
      filaTr?.scrollIntoView({
        block: "nearest",
        behavior: prefiereMovimientoReducido() ? "auto" : "smooth",
      });
    }
  }

  function destruir() {
    limpiarTemporizadores();
    raiz.remove();
  }

  actualizarCaption();
  renderEncabezado();
  renderCuerpo({ conFlip: false });

  return { raiz, actualizar, establecerOrden, establecerActiva, destruir };
}

export const ALTO_DETALLE = ALTO_DETALLE_PX;
export { ORDEN as ORDEN_TABLA };
