// frontend/js/ranking.js
//
// Ranking por AGEB/alcaldía (plans/frontend_specs.md §7, plan F50). Sustituye a la tabla de
// predicciones por alcaldía de la versión anterior; reutiliza su mismo mecanismo FLIP
// (`tabla.js`: hover con intención de 100 ms, repliegue de 180 ms, una fila desplegada a la vez,
// reordenar con `tr.animate(...)` de 200 ms) porque sigue siendo la mecánica correcta -- solo
// cambian columnas y contenido (§7.1-§7.3), nunca la geometría del gesto.
//
// Autocontenido (plan §9): `montarRanking(contenedor, opciones)` no lee `estado.js` salvo para
// despachar (inyectable, igual que `tabla.js`); recibe ya calculadas las filas por `main.js`
// (misma fuente de `composicion.js` que `resumen.js`, spec §7.1: "invariante resumen=ranking").

import { texto as t, textos } from "./textos.js";
import { formatoPorcentaje } from "./formato.js";
import { crear, reemplazarContenido, limpiar } from "./dom.js";
import { despachar as despacharEstado, ACCIONES } from "./estado.js";

const ALTO_DETALLE_PX = 136;
const TOP_N_DEFECTO = 20;
/** Debounce del buscador de AGEB (§7.3: "buscador de AGEB por clave... debounce 120 ms"). */
const DEBOUNCE_BUSCADOR_MS = 120;

const ORDEN = Object.freeze({ VALOR: "valor", ALCALDIA: "alcaldia", CONFIANZA: "confianza" });
const RANGO_CONFIANZA = Object.freeze({ alta: 0, media: 1, baja: 2 });

function duracionMs(nombreVariable, porDefecto) {
  if (typeof window === "undefined" || typeof getComputedStyle !== "function") return porDefecto;
  const valor = getComputedStyle(document.documentElement).getPropertyValue(nombreVariable).trim();
  const ms = Number.parseFloat(valor);
  return Number.isFinite(ms) ? ms : porDefecto;
}

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
// Normalización de filas de entrada.
// ------------------------------------------------------------------------------------------

/**
 * `filas` viene ya resuelta por `main.js` a partir de `composicion.js`. Forma esperada por
 * elemento: `{ clave, nombreZona, nombreAlcaldia, valor, tercil, confianza, ramaPrincipal,
 * percentil }`. `clave` es el `cvegeo`/`cve_mun` (identificador estable de fila); `valor` es el
 * índice de oportunidad/disponibilidad compuesto (o de rama, según vista de mapa) ∈ [0,1] o `NaN`.
 */
function normalizarFila(registroOriginal) {
  const r = registroOriginal ?? {};
  return {
    clave: String(r.clave ?? ""),
    nombreZona: typeof r.nombreZona === "string" && r.nombreZona !== "" ? r.nombreZona : t("tooltip.ageb", { cvegeo: r.clave ?? "?" }),
    nombreAlcaldia: typeof r.nombreAlcaldia === "string" ? r.nombreAlcaldia : "",
    valor: typeof r.valor === "number" ? r.valor : NaN,
    tercil: r.tercil ?? "sin_datos",
    confianza: r.confianza ?? "baja",
    ramaPrincipal: r.ramaPrincipal ?? null,
    percentil: typeof r.percentil === "number" ? r.percentil : NaN,
    oPorRama: r.oPorRama ?? {},
  };
}

// ------------------------------------------------------------------------------------------
// Orden (spec §7.1: oportunidad/disponibilidad descendente por defecto, alcaldía A-Z, confianza).
// ------------------------------------------------------------------------------------------

function compararValor(a, b) {
  if (Number.isNaN(a.valor) && Number.isNaN(b.valor)) return 0;
  if (Number.isNaN(a.valor)) return 1; // sin dato al final
  if (Number.isNaN(b.valor)) return -1;
  return b.valor - a.valor; // descendente: lo más prioritario arriba
}

function compararAlcaldia(a, b) {
  return (a.nombreAlcaldia || a.nombreZona).localeCompare(b.nombreAlcaldia || b.nombreZona, "es-MX");
}

function compararConfianza(a, b) {
  const aRango = RANGO_CONFIANZA[a.confianza] ?? 3;
  const bRango = RANGO_CONFIANZA[b.confianza] ?? 3;
  if (aRango !== bRango) return aRango - bRango;
  return compararValor(a, b);
}

const COMPARADORES = Object.freeze({
  [ORDEN.VALOR]: compararValor,
  [ORDEN.ALCALDIA]: compararAlcaldia,
  [ORDEN.CONFIANZA]: compararConfianza,
});

const DIRECCION_ARIA = Object.freeze({
  [ORDEN.VALOR]: "descending",
  [ORDEN.ALCALDIA]: "ascending",
  [ORDEN.CONFIANZA]: "descending",
});

function ordenarFilas(filas, orden) {
  const comparador = COMPARADORES[orden] ?? COMPARADORES[ORDEN.VALOR];
  return [...filas].sort(comparador);
}

// ------------------------------------------------------------------------------------------
// Celdas
// ------------------------------------------------------------------------------------------

function crearCeldaZona(fila, opciones) {
  const boton = crear(
    "button",
    {
      clase: "ranking__nombre",
      type: "button",
      onclick: (evento) => {
        evento.stopPropagation();
        if (opciones.enAlcaldia) {
          opciones.despachar({ tipo: ACCIONES.IR_A_AGEB, cve_mun: opciones.cveMun ?? null, cvegeo: fila.clave });
        } else {
          opciones.despachar({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: fila.clave });
        }
      },
    },
    [fila.nombreZona],
  );
  return crear("td", { clase: "ranking__celda ranking__celda--zona" }, [boton]);
}

function crearCeldaValor(fila, etiquetaNivel) {
  return crear(
    "td",
    { clase: `ranking__celda ranking__celda--valor ranking__celda--tercil-${fila.tercil}`, "aria-label": `${etiquetaNivel}: ${textos.tercil.palabra[fila.tercil] ?? textos.tercil.palabra.sin_datos}` },
    [`${textos.tercil.simbolo[fila.tercil] ?? textos.tercil.simbolo.sin_datos} ${textos.tercil.palabra[fila.tercil] ?? textos.tercil.palabra.sin_datos}`],
  );
}

function crearCeldaRamaPrincipal(fila) {
  const nombre = fila.ramaPrincipal ? (textos.rama.nombre[fila.ramaPrincipal] ?? fila.ramaPrincipal) : "—";
  return crear("td", { clase: "ranking__celda ranking__celda--rama" }, [nombre]);
}

function crearCeldaConfianza(fila) {
  const etiqueta = t("confianza.ariaLabel", { nivel: fila.confianza });
  return crear(
    "td",
    { clase: "ranking__celda ranking__celda--confianza", "aria-label": etiqueta, title: etiqueta },
    [textos.confianza.simbolo[fila.confianza] ?? "○"],
  );
}

/** Círculos de intensidad (0-5 llenos) para "Ramas: Educación ●●●●● · Salud ●●●…" (§7.2). */
function circulosDeValor(valor) {
  if (typeof valor !== "number" || Number.isNaN(valor)) return "—";
  const llenos = Math.max(0, Math.min(5, Math.round(valor * 5)));
  return "●".repeat(llenos) + "○".repeat(5 - llenos);
}

function crearFilaDetalle(fila, opciones, RAMAS) {
  const contenido = [];

  const percentilTexto = Number.isFinite(fila.percentil)
    ? t("ranking.detalle.percentil", { percentil: Math.round(fila.percentil * 100) })
    : null;
  contenido.push(
    crear("p", { clase: "ranking__detalle-linea" }, [
      `${opciones.etiquetaNivel}: ${(textos.tercil.palabra[fila.tercil] ?? textos.tercil.palabra.sin_datos).toLowerCase()}${percentilTexto ? ` (${percentilTexto})` : ""}`,
    ]),
  );

  contenido.push(
    crear("p", { clase: "ranking__detalle-linea" }, [
      `${textos.ranking.detalle.ramas}: `,
      RAMAS.map((r) => `${textos.rama.nombre[r] ?? r} ${circulosDeValor(fila.oPorRama?.[r])}`).join(" · "),
    ]),
  );

  contenido.push(
    crear("p", { clase: "ranking__detalle-linea" }, [
      `${textos.confianza.simbolo[fila.confianza] ?? "○"} ${textos.confianza.palabra[fila.confianza] ?? ""}: ${textos.confianza.explicacion[fila.confianza] ?? ""}`,
    ]),
  );

  contenido.push(
    crear(
      "button",
      {
        clase: "ranking__entender",
        type: "button",
        onclick: (evento) => {
          evento.stopPropagation();
          opciones.despachar({ tipo: ACCIONES.ABRIR_DRAWER });
        },
      },
      [textos.navegacion.entenderZona],
    ),
  );

  const detalle = crear("div", { clase: "ranking__detalle" }, contenido);
  const celda = crear("td", { clase: "ranking__celda-detalle", colspan: "4" }, [detalle]);
  return crear("tr", {
    clase: "ranking__fila-detalle",
    id: `ranking-detalle-${fila.clave}`,
    hidden: true,
  }, [celda]);
}

// ------------------------------------------------------------------------------------------
// Componente principal
// ------------------------------------------------------------------------------------------

/**
 * Monta el ranking dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @param {Array<object>} filasIniciales - ver `normalizarFila`.
 * @param {object} [opciones]
 * @param {boolean} [opciones.enAlcaldia] - `true` en vista de alcaldía (filas = AGEB de esa alcaldía).
 * @param {string|null} [opciones.cveMun] - alcaldía activa, para navegar de AGEB a AGEB (`IR_A_AGEB`).
 * @param {"oportunidad"|"disponibilidad"} [opciones.busqueda]
 * @param {number} [opciones.topN]
 * @param {(accion: object) => void} [opciones.despachar]
 * @param {readonly string[]} [opciones.ramas] - claves de rama en orden fijo (mismo orden que `composicion.RAMAS`).
 */
export function montarRanking(contenedor, filasIniciales, opciones = {}) {
  if (!contenedor) throw new TypeError("montarRanking(contenedor): se requiere un contenedor");

  const config = {
    enAlcaldia: opciones.enAlcaldia === true,
    cveMun: opciones.cveMun ?? null,
    busqueda: opciones.busqueda === "disponibilidad" ? "disponibilidad" : "oportunidad",
    despachar: typeof opciones.despachar === "function" ? opciones.despachar : despacharEstado,
    ramas: Array.isArray(opciones.ramas) ? opciones.ramas : ["educacion", "salud", "comercio", "verde"],
  };

  let filas = (Array.isArray(filasIniciales) ? filasIniciales : []).map(normalizarFila);
  let orden = ORDEN.VALOR;
  let claveExpandida = null;
  let topN = opciones.topN ?? TOP_N_DEFECTO;
  let temporizadorIntencion = null;
  let temporizadorRepliegue = null;
  let consultaBuscador = "";
  let temporizadorBuscador = null;

  const raiz = crear("div", { clase: "ranking-contenedor" });
  const buscadorRaiz = crear("div", { clase: "ranking__buscador" });
  const sinResultadosRaiz = crear("p", { clase: "ranking__sin-resultados" });
  const caption = crear("caption", { clase: "visualmente-oculto" });
  const thead = crear("thead");
  const tbody = crear("tbody");
  const tabla = crear("table", { clase: "ranking" }, [caption, thead, tbody]);
  const pieRaiz = crear("div", { clase: "ranking__pie" });
  raiz.appendChild(buscadorRaiz);
  raiz.appendChild(sinResultadosRaiz);
  raiz.appendChild(tabla);
  raiz.appendChild(pieRaiz);
  contenedor.appendChild(raiz);

  // ------------------------------------------------------------------------------------------
  // Buscador de AGEB por clave (§7.3): solo en vista de alcaldía, filtra sin red, debounce 120 ms.
  // ------------------------------------------------------------------------------------------

  function filasVisiblesPorBusqueda(filasOrdenadas) {
    if (!config.enAlcaldia || consultaBuscador.trim() === "") return filasOrdenadas;
    const consulta = consultaBuscador.trim().toLowerCase();
    return filasOrdenadas.filter((f) => f.clave.toLowerCase().includes(consulta));
  }

  function renderBuscador() {
    if (!config.enAlcaldia) {
      reemplazarContenido(buscadorRaiz, []);
      return;
    }
    const idCampo = "ranking-buscador-ageb";
    const etiqueta = crear("label", { for: idCampo, clase: "ranking__buscador-etiqueta" }, [
      textos.ranking.buscador.etiqueta,
    ]);
    const campo = crear("input", {
      id: idCampo,
      type: "search",
      clase: "ranking__buscador-campo",
      value: consultaBuscador,
      autocomplete: "off",
      oninput: (evento) => {
        const valorActual = evento.target.value;
        if (temporizadorBuscador !== null) window.clearTimeout(temporizadorBuscador);
        temporizadorBuscador = window.setTimeout(() => {
          consultaBuscador = valorActual;
          renderCuerpo({ conFlip: false });
        }, DEBOUNCE_BUSCADOR_MS);
      },
    });
    reemplazarContenido(buscadorRaiz, [etiqueta, campo]);
  }

  function etiquetaNivel() {
    return config.busqueda === "disponibilidad" ? textos.resumen.campo.disponibilidad : textos.resumen.campo.oportunidad;
  }

  function actualizarCaption(totalFiltrado) {
    const nombreBusqueda = textos.busqueda.nombre[config.busqueda];
    reemplazarContenido(caption, [
      `Ranking de zonas por ${nombreBusqueda}, ${config.ramas.length} ramas consideradas, ${totalFiltrado} filas.`,
    ]);
  }

  // ------------------------------------------------------------------------------------------
  // Encabezado
  // ------------------------------------------------------------------------------------------

  function crearEncabezadoOrdenable(clave, texto) {
    const boton = crear(
      "button",
      {
        clase: "ranking__th-boton",
        type: "button",
        "aria-label": clave === ORDEN.VALOR
          ? (config.busqueda === "disponibilidad" ? textos.ranking.ordenarPor.disponibilidad : textos.ranking.ordenarPor.oportunidad)
          : (textos.ranking.ordenarPor[clave] ?? texto),
        onclick: () => cambiarOrden(clave),
      },
      [texto],
    );
    return crear("th", {
      scope: "col",
      clase: `ranking__th ranking__th--${clave}`,
      "aria-sort": orden === clave ? DIRECCION_ARIA[clave] : "none",
      dataset: { orden: clave },
    }, [boton]);
  }

  function renderEncabezado() {
    limpiar(thead);
    const filaTh = crear("tr", {}, [
      crear("th", { scope: "col", clase: "ranking__th ranking__th--zona" }, [
        config.enAlcaldia ? textos.ranking.columnas.zona : textos.ranking.columnas.alcaldia,
      ]),
      crearEncabezadoOrdenable(ORDEN.VALOR, etiquetaNivel()),
      crear("th", { scope: "col", clase: "ranking__th ranking__th--rama" }, [textos.ranking.columnas.ramaPrincipal]),
      crearEncabezadoOrdenable(ORDEN.CONFIANZA, textos.ranking.columnas.confianza),
    ]);
    thead.appendChild(filaTh);
  }

  // ------------------------------------------------------------------------------------------
  // Acordeón (mismo mecanismo que tabla.js §7.2: intención 100 ms, repliegue 180 ms).
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

  function expandir(clave) {
    if (claveExpandida === clave) return;
    const anterior = claveExpandida;
    claveExpandida = clave;
    if (anterior !== null) actualizarFilaExpandida(anterior);
    actualizarFilaExpandida(clave);
  }

  function plegar(clave) {
    if (claveExpandida !== clave) return;
    claveExpandida = null;
    actualizarFilaExpandida(clave);
  }

  function actualizarFilaExpandida(clave) {
    const filaTr = tbody.querySelector(`tr.ranking__fila[data-clave="${CSS.escape(clave)}"]`);
    const detalleTr = tbody.querySelector(`#ranking-detalle-${CSS.escape(clave)}`);
    if (!filaTr || !detalleTr) return;
    const expandida = claveExpandida === clave;
    filaTr.setAttribute("aria-expanded", String(expandida));
    filaTr.classList.toggle("ranking__fila--expandida", expandida);
    detalleTr.hidden = !expandida;
  }

  function programarExpansion(clave) {
    limpiarTemporizadores();
    temporizadorIntencion = window.setTimeout(() => expandir(clave), duracionMs("--d-intencion", 100));
  }

  function programarRepliegue(clave) {
    limpiarTemporizadores();
    temporizadorRepliegue = window.setTimeout(() => plegar(clave), duracionMs("--d-repliegue", 180));
  }

  // ------------------------------------------------------------------------------------------
  // Orden + FLIP
  // ------------------------------------------------------------------------------------------

  function medirPosiciones() {
    const posiciones = new Map();
    for (const tr of tbody.querySelectorAll("tr.ranking__fila")) {
      posiciones.set(tr.dataset.clave, tr.getBoundingClientRect().top);
    }
    return posiciones;
  }

  function animarFlip(posicionesAntes) {
    if (prefiereMovimientoReducido()) return;
    const duracion = duracionMs("--d-s", 200);
    const easing = easingCss("--ease-salida", "cubic-bezier(0.22, 1, 0.36, 1)");
    for (const tr of tbody.querySelectorAll("tr.ranking__fila")) {
      const antes = posicionesAntes.get(tr.dataset.clave);
      if (antes === undefined) continue;
      const despues = tr.getBoundingClientRect().top;
      const delta = antes - despues;
      if (delta === 0) continue;
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
  // Cuerpo
  // ------------------------------------------------------------------------------------------

  function crearFila(fila) {
    const tr = crear(
      "tr",
      {
        clase: "ranking__fila",
        tabindex: "0",
        "aria-expanded": String(claveExpandida === fila.clave),
        "aria-controls": `ranking-detalle-${fila.clave}`,
        dataset: { clave: fila.clave },
        onmouseenter: () => programarExpansion(fila.clave),
        onmouseleave: () => programarRepliegue(fila.clave),
        onfocus: () => {
          limpiarTemporizadores();
          expandir(fila.clave);
        },
        onfocusout: (evento) => {
          const destino = evento.relatedTarget;
          const detalle = tbody.querySelector(`#ranking-detalle-${CSS.escape(fila.clave)}`);
          if (destino && (tr.contains(destino) || detalle?.contains(destino))) return;
          programarRepliegue(fila.clave);
        },
      },
      [
        crearCeldaZona(fila, config),
        crearCeldaValor(fila, etiquetaNivel()),
        crearCeldaRamaPrincipal(fila),
        crearCeldaConfianza(fila),
      ],
    );
    return tr;
  }

  function crearFilaDetalleConEventos(fila) {
    const detalleTr = crearFilaDetalle(fila, { ...config, etiquetaNivel: etiquetaNivel() }, config.ramas);
    detalleTr.addEventListener("mouseenter", () => limpiarTemporizadores());
    detalleTr.addEventListener("mouseleave", () => programarRepliegue(fila.clave));
    return detalleTr;
  }

  function renderPie(totalOrdenado) {
    limpiar(pieRaiz);
    if (totalOrdenado <= topN) return;
    const boton = crear(
      "button",
      {
        clase: "ranking__ver-mas",
        type: "button",
        onclick: () => {
          topN = totalOrdenado;
          renderCuerpo({ conFlip: false });
        },
      },
      [config.enAlcaldia ? textos.ranking.verTodos({ n: totalOrdenado }) : textos.ranking.verMas(totalOrdenado - topN)],
    );
    pieRaiz.appendChild(boton);
  }

  function renderCuerpo({ conFlip = false } = {}) {
    const posicionesAntes = conFlip ? medirPosiciones() : null;
    const filasOrdenadas = filasVisiblesPorBusqueda(ordenarFilas(filas, orden));
    const visibles = filasOrdenadas.slice(0, topN);
    limpiar(tbody);
    for (const fila of visibles) {
      tbody.appendChild(crearFila(fila));
      tbody.appendChild(crearFilaDetalleConEventos(fila));
    }
    actualizarCaption(visibles.length);
    renderPie(filasOrdenadas.length);
    reemplazarContenido(
      sinResultadosRaiz,
      config.enAlcaldia && consultaBuscador.trim() !== "" && filasOrdenadas.length === 0
        ? [textos.ranking.buscador.sinResultados({ texto: consultaBuscador.trim() })]
        : [],
    );
    if (posicionesAntes) animarFlip(posicionesAntes);
  }

  // ------------------------------------------------------------------------------------------
  // API pública
  // ------------------------------------------------------------------------------------------

  function actualizar(nuevasFilas, nuevasOpciones = {}) {
    if (Array.isArray(nuevasFilas)) filas = nuevasFilas.map(normalizarFila);
    const cambioDeUniverso = typeof nuevasOpciones.enAlcaldia === "boolean" && nuevasOpciones.enAlcaldia !== config.enAlcaldia;
    if (typeof nuevasOpciones.enAlcaldia === "boolean") config.enAlcaldia = nuevasOpciones.enAlcaldia;
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "cveMun")) {
      if (nuevasOpciones.cveMun !== config.cveMun) consultaBuscador = "";
      config.cveMun = nuevasOpciones.cveMun;
    }
    if (typeof nuevasOpciones.busqueda === "string") config.busqueda = nuevasOpciones.busqueda;
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "topN") && typeof nuevasOpciones.topN === "number") {
      topN = nuevasOpciones.topN;
    } else if (Array.isArray(nuevasFilas)) {
      // Cambió el universo de filas (p. ej. entrar/salir de alcaldía): vuelve al top N por omisión,
      // en vez de conservar un "Ver más" que ya no corresponde al nuevo conjunto.
      topN = opciones.topN ?? TOP_N_DEFECTO;
    }
    if (cambioDeUniverso) renderBuscador();
    renderEncabezado();
    renderCuerpo({ conFlip: false });
  }

  function destruir() {
    limpiarTemporizadores();
    raiz.remove();
  }

  renderBuscador();
  renderEncabezado();
  renderCuerpo({ conFlip: false });

  return { raiz, actualizar, destruir };
}

export const ALTO_DETALLE = ALTO_DETALLE_PX;
export { ORDEN as ORDEN_RANKING };
