// frontend/js/ficha.js
//
// Ficha de AGEB (plans/frontend_specs.md §7.4): cifras del registro (veredicto, cambio, rango,
// confianza, observaciones) más la mini-gráfica de js/graficas.js. Con el contrato v1.1 (vía el
// adaptador de `api.js`) `serie`/`nivel_base` siempre llegan `null` y `horizontes` vacío, así que
// `graficas.js` degrada solo a la nota fija; con v1.2 (`main.js#renderAgeb`) llegan los datos
// reales (serie censal/DENUE, `nivel_base` y los 3 horizontes con su `.h`).
//
// Autocontenida (plan §9, F50): `montarFicha(contenedor, cvegeo, registro, opciones)` no asume
// ningún id fijo de `index.html`.

import { texto as t, textos } from "./textos.js";
import { formatoPorcentaje, formatoIntervalo, simboloVeredicto, simboloConfianza } from "./formato.js";
import { crear, reemplazarContenido } from "./dom.js";
import { montarGrafica } from "./graficas.js";
import { resolverHorizonte } from "./titular.js";
import { despachar as despacharEstado, ACCIONES } from "./estado.js";

// `serie`/`nivel_base` NO viven en el registro por horizonte (`registroOriginal` aquí): en el
// contrato viven un nivel arriba, junto a `h` (`capas[capa][clave].serie`/`.nivel_base`, spec
// §17), así que `montarFicha` los recibe aparte en `opciones` (ver docstring más abajo), no desde
// este registro plano.
function normalizarRegistro(registroOriginal) {
  const r = registroOriginal ?? {};
  return {
    veredicto: r.veredicto ?? "sin_datos",
    deltaPct: typeof r.delta_pct === "number" ? r.delta_pct : null,
    tasaAnualPct: typeof r.tasa_anual_pct === "number" ? r.tasa_anual_pct : null,
    ic95: Array.isArray(r.ic95) && r.ic95.length === 2 ? r.ic95 : null,
    confianza: r.confianza ?? "baja",
    nObs: typeof r.n_obs === "number" ? r.n_obs : 0,
    motivoSinDatos: typeof r.motivo_sin_datos === "string" ? r.motivo_sin_datos : undefined,
  };
}

function crearEncabezado(config) {
  const { cvegeo, alcaldiaNombre, tipoAgeb } = config;
  return crear("div", { clase: "ficha__encabezado" }, [
    crear("p", { clase: "ficha__ubicacion" }, [
      t("ficha.ubicacion", { alcaldia: alcaldiaNombre, tipo: textos.ficha.tipoAgeb[tipoAgeb] ?? textos.ficha.tipoAgeb.urbana }),
    ]),
    crear("p", { clase: "ficha__clave cifras" }, [cvegeo]),
  ]);
}

function crearCifras(registro, config) {
  const filas = [];

  filas.push(
    crear("p", { clase: "ficha__linea ficha__linea--principal" }, [
      crear("span", { clase: `ficha__veredicto color-veredicto--${registro.veredicto}` }, [
        `${simboloVeredicto(registro.veredicto)} ${t(`veredicto.palabra.${registro.veredicto}`) ?? textos.veredicto.palabra.sin_datos}`,
      ]),
      crear("span", { clase: "ficha__cambio cifras" }, [formatoPorcentaje(registro.deltaPct)]),
    ]),
  );

  if (registro.veredicto === "sin_datos") {
    const motivo = textos.motivosSinDatos.obtener(registro.motivoSinDatos);
    filas.push(crear("p", { clase: "ficha__linea ficha__linea--motivo" }, [motivo]));
    return crear("div", { clase: "ficha__cifras" }, filas);
  }

  if (registro.tasaAnualPct !== null) {
    filas.push(
      crear("p", { clase: "ficha__linea cifras" }, [
        `${textos.ficha.tasaAnualLabel}: ${textos.ficha.tasaAnualValor(formatoPorcentaje(registro.tasaAnualPct))}`,
      ]),
    );
  }

  const intervalo = formatoIntervalo(registro.ic95);
  if (intervalo) {
    filas.push(
      crear("p", { clase: "ficha__linea cifras" }, [
        `${textos.ficha.rangoLabel}: ${textos.ficha.rangoValor(intervalo)}`,
      ]),
    );
  }

  filas.push(
    crear("p", { clase: "ficha__linea" }, [
      `${textos.ficha.confianzaLabel}: ${textos.ficha.confianzaValor(registro.confianza)}`,
    ]),
  );

  const nObsTexto = config.capa === "oferta"
    ? textos.ficha.nObs.oferta(registro.nObs)
    : textos.ficha.nObs.demanda(registro.nObs);
  filas.push(crear("p", { clase: "ficha__linea" }, [`${textos.ficha.observacionesLabel}: ${nObsTexto}`]));

  return crear("div", { clase: "ficha__cifras" }, filas);
}

/**
 * Monta la ficha de un AGEB dentro de `contenedor`. Devuelve `{ raiz, actualizar, destruir }`.
 *
 * @param {HTMLElement} contenedor
 * @param {string} cvegeo - `CVEGEO` de 13 dígitos.
 * @param {object} registro - registro del AGEB ya resuelto al horizonte activo (ver
 *   `normalizarRegistro`); `sin_datos` cuando el AGEB es rural o no tiene datos suficientes.
 * @param {object} [opciones]
 * @param {"demanda"|"oferta"} [opciones.capa]
 * @param {{fecha?: string|null, anios?: number|null}} [opciones.horizonte]
 * @param {string|null} [opciones.generadoIso]
 * @param {string} [opciones.alcaldiaNombre]
 * @param {"urbana"|"rural"} [opciones.tipoAgeb]
 * @param {string} [opciones.cveMun]
 * @param {{t:number[], valor:number[]}|null} [opciones.serie] - niveles observados (v1.2, spec
 *   §17); `null`/ausente con v1.1 (degrada la gráfica a la nota fija, `graficas.js`).
 * @param {number|null} [opciones.nivelBase] - nivel en `fecha_base` (`nivel_base`, v1.2).
 * @param {Array<{clave:string, anios:number|null, fecha:string|null}>} [opciones.horizontes] -
 *   `datosAdaptados.horizontes` (3 entradas con v1.2, 1 con v1.1).
 * @param {Map<string, object>} [opciones.registrosPorHorizonte] - `entradaCapa.h` completo
 *   (`{h3:{...}, h5:{...}, h7:{...}}`, o `{hU:{...}}` con v1.1), para la banda IC95 por horizonte.
 * @param {string|null} [opciones.fechaBase] - `datosAdaptados.fecha_base` ("YYYY-MM"), el año
 *   base de la gráfica ("línea de hoy"); NUNCA el horizonte activo del slider (ese es un punto
 *   proyectado, no "hoy" — moverlo no debe correr la línea de hoy, plan §7 "bug a corregir").
 */
export function montarFicha(contenedor, cvegeo, registro, opciones = {}) {
  if (!contenedor) {
    throw new TypeError("montarFicha(contenedor): se requiere un contenedor");
  }

  const config = {
    capa: opciones.capa === "oferta" ? "oferta" : "demanda",
    horizonte: opciones.horizonte ?? { fecha: null, anios: null },
    generadoIso: opciones.generadoIso ?? null,
    alcaldiaNombre: typeof opciones.alcaldiaNombre === "string" && opciones.alcaldiaNombre !== ""
      ? opciones.alcaldiaNombre
      : `CVE_MUN ${opciones.cveMun ?? ""}`,
    tipoAgeb: opciones.tipoAgeb === "rural" ? "rural" : "urbana",
    cveMun: opciones.cveMun ?? null,
    serie: opciones.serie ?? null,
    nivelBase: typeof opciones.nivelBase === "number" ? opciones.nivelBase : null,
    horizontes: Array.isArray(opciones.horizontes) ? opciones.horizontes : [],
    registrosPorHorizonte: opciones.registrosPorHorizonte instanceof Map ? opciones.registrosPorHorizonte : new Map(),
    fechaBase: typeof opciones.fechaBase === "string" ? opciones.fechaBase : null,
  };

  const raiz = crear("article", { clase: "ficha-contenedor", "aria-labelledby": "ficha-clave" });
  const botonVolver = crear(
    "button",
    { type: "button", clase: "ficha__volver", onclick: () => despacharEstado({ tipo: ACCIONES.VOLVER }) },
    [textos.ficha.volver ?? "← Volver"],
  );
  const zonaEncabezado = crear("div", { clase: "ficha__zona-encabezado" });
  const zonaCifras = crear("div", { clase: "ficha__zona-cifras" });
  const zonaGrafica = crear("div", { clase: "ficha__zona-grafica" });

  raiz.appendChild(botonVolver);
  raiz.appendChild(zonaEncabezado);
  raiz.appendChild(zonaCifras);
  raiz.appendChild(zonaGrafica);
  contenedor.appendChild(raiz);

  function render(cvegeoActual, registroOriginal) {
    const registroNorm = normalizarRegistro(registroOriginal);
    reemplazarContenido(zonaEncabezado, [crearEncabezado({ ...config, cvegeo: cvegeoActual })]);
    reemplazarContenido(zonaCifras, [crearCifras(registroNorm, config)]);

    // Año base de la gráfica ("línea de hoy", spec §7.4): SIEMPRE `fecha_base` (constante, no
    // cambia al mover el slider de horizonte); con v1.1 (`fechaBase` ausente) se conserva el
    // fallback anterior a partir del horizonte único/`generado`, que en ese camino nunca dibuja
    // proyección de cualquier forma (`horizontes` llega vacío).
    const anio = config.fechaBase !== null
      ? resolverHorizonte({ fecha: config.fechaBase, anios: null }, config.generadoIso).anio
      : resolverHorizonte(config.horizonte, config.generadoIso).anio;
    reemplazarContenido(zonaGrafica, []);
    // AGEB `sin_datos`: la gráfica solo muestra puntos censales si existen (spec §7.4); con v1.1
    // real `serie` siempre está ausente, así que aquí siempre sale la nota de degradación fija.
    montarGrafica(zonaGrafica, {
      capa: config.capa,
      serie: config.serie,
      nivelBase: config.nivelBase,
      anioBase: anio,
      horizontes: config.horizontes,
      horizonteActivoClave: config.horizonte?.clave ?? null,
      registrosPorHorizonte: config.registrosPorHorizonte,
      veredicto: registroNorm.veredicto,
      soloPuntos: registroNorm.veredicto === "sin_datos",
    });
  }

  render(cvegeo, registro);

  function actualizar(nuevoCvegeo, nuevoRegistro, nuevasOpciones = {}) {
    if (typeof nuevasOpciones.capa === "string") config.capa = nuevasOpciones.capa;
    if (nuevasOpciones.horizonte) config.horizonte = nuevasOpciones.horizonte;
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "generadoIso")) {
      config.generadoIso = nuevasOpciones.generadoIso;
    }
    if (nuevasOpciones.alcaldiaNombre) config.alcaldiaNombre = nuevasOpciones.alcaldiaNombre;
    if (nuevasOpciones.tipoAgeb) config.tipoAgeb = nuevasOpciones.tipoAgeb;
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "serie")) config.serie = nuevasOpciones.serie ?? null;
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "nivelBase")) {
      config.nivelBase = typeof nuevasOpciones.nivelBase === "number" ? nuevasOpciones.nivelBase : null;
    }
    if (Array.isArray(nuevasOpciones.horizontes)) config.horizontes = nuevasOpciones.horizontes;
    if (nuevasOpciones.registrosPorHorizonte instanceof Map) {
      config.registrosPorHorizonte = nuevasOpciones.registrosPorHorizonte;
    }
    if (Object.prototype.hasOwnProperty.call(nuevasOpciones, "fechaBase")) {
      config.fechaBase = typeof nuevasOpciones.fechaBase === "string" ? nuevasOpciones.fechaBase : null;
    }
    render(nuevoCvegeo ?? cvegeo, nuevoRegistro ?? registro);
  }

  function destruir() {
    raiz.remove();
  }

  return { raiz, actualizar, destruir };
}
