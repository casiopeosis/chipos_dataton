// frontend/js/ficha.js
//
// Ficha de AGEB (plans/frontend_specs.md §7.4): cifras del registro (veredicto, cambio, rango,
// confianza, observaciones) más la mini-gráfica de js/graficas.js (o su nota de degradación fija,
// porque el contrato v1.1 — el único que produce hoy el backend — nunca trae `serie`).
//
// Autocontenida (plan §9, F50): `montarFicha(contenedor, cvegeo, registro, opciones)` no asume
// ningún id fijo de `index.html`.

import { texto as t, textos } from "./textos.js";
import { formatoPorcentaje, formatoIntervalo, simboloVeredicto, simboloConfianza } from "./formato.js";
import { crear, reemplazarContenido } from "./dom.js";
import { montarGrafica } from "./graficas.js";
import { resolverHorizonte } from "./titular.js";
import { despachar as despacharEstado, ACCIONES } from "./estado.js";

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
    serie: r.serie ?? null,
    nivelBase: typeof r.nivel_base === "number" ? r.nivel_base : null,
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

    const anio = resolverHorizonte(config.horizonte, config.generadoIso).anio;
    reemplazarContenido(zonaGrafica, []);
    // AGEB `sin_datos`: la gráfica solo muestra puntos censales si existen (spec §7.4); con v1.1
    // real `serie` siempre está ausente, así que aquí siempre sale la nota de degradación fija.
    montarGrafica(zonaGrafica, {
      capa: config.capa,
      serie: registroNorm.serie,
      nivelBase: registroNorm.nivelBase,
      anioBase: anio,
      horizontes: [],
      horizonteActivoClave: config.horizonte?.clave ?? null,
      registrosPorHorizonte: new Map(),
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
    render(nuevoCvegeo ?? cvegeo, nuevoRegistro ?? registro);
  }

  function destruir() {
    raiz.remove();
  }

  return { raiz, actualizar, destruir };
}
