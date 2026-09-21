// frontend/tests/pruebas_leyenda.js
//
// Pruebas en navegador (mismo patrón sin framework que tests/pruebas_veredictos.js) de F75:
// - contarPorVeredicto y seleccionarRegistrosVisibles (funciones puras de js/leyenda.js).
// - construirFilasBrecha ejercitada con un fixture ficticio de 5 cortes (CLAUDE.md/plan §2: la
//   capa brecha nunca llega con el contrato v1.1, así que esta es la única forma de probarla hoy).
// - montarLeyenda: conteos correctos en vista ciudad y en vista de alcaldía, cada fila es un
//   <button aria-pressed>, y el mensaje "Mostrando N de M · ..." al activar un filtro.
//
// Exporta `pruebasLeyenda` (array `{nombre, fn}`), mismo formato que tests/pruebas_veredictos.js.
// Se puede fusionar en tests/pruebas.js más adelante sin tocarlo desde esta tarea.

import {
  montarLeyenda,
  contarPorVeredicto,
  seleccionarRegistrosVisibles,
  construirFilasBrecha,
  ORDEN_VEREDICTOS,
} from "../js/leyenda.js";
import { despachar, ACCIONES, obtenerEstado, VISTA } from "../js/estado.js";

export const pruebasLeyenda = [];

function prueba(nombre, fn) {
  pruebasLeyenda.push({ nombre, fn });
}

function afirmar(condicion, mensaje) {
  if (!condicion) throw new Error(mensaje ?? "afirmación falsa");
}

function afirmarIgual(actual, esperado, mensaje) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(esperado);
  if (a !== e) {
    throw new Error(`${mensaje ?? "no coincide"}: esperado ${e}, obtuvo ${a}`);
  }
}

/** Vuelve `estado.js` a su estado inicial (vista ciudad, sin filtro) al terminar una prueba. */
function reiniciarEstado() {
  despachar({ tipo: ACCIONES.CAMBIAR_FILTRO, filtro: null });
  despachar({ tipo: ACCIONES.IR_A_CIUDAD });
}

// ------------------------------------------------------------------
// Fixtures: índices "alcaldía" y "ageb" con la misma forma que produce
// api.js#adaptarV11aV12 (registro.h[horizonteActivo], indices.porCveMun/porCvegeo).
// ------------------------------------------------------------------

function registroConH(veredicto, confianza, tasaAnualPct) {
  return { h: { hU: { veredicto, confianza, tasa_anual_pct: tasaAnualPct } } };
}

const DATOS_ALCALDIA_FIXTURE = {
  generado: "2026-01-01T00:00:00Z",
  horizontes: [{ clave: "hU", anios: null, fecha: "2027-06" }],
  indices: {
    porCveMun: new Map([
      ["002", { demanda: registroConH("sube", "alta", 1.2), oferta: null }],
      ["003", { demanda: registroConH("sube", "media", 2.5), oferta: null }],
      ["004", { demanda: registroConH("baja", "baja", 4.1), oferta: null }],
      ["005", { demanda: registroConH("baja", "alta", 0.5), oferta: null }],
      ["006", { demanda: registroConH("se_mantiene", "alta", 0.2), oferta: null }],
      ["007", { demanda: registroConH("sin_datos", "baja", null), oferta: null }],
    ]),
  },
};

const DATOS_AGEB_FIXTURE = {
  generado: "2026-01-01T00:00:00Z",
  horizontes: [{ clave: "hU", anios: null, fecha: "2027-06" }],
  indices: {
    porCveMun: new Map([
      ["007", ["0900700010001", "0900700010002", "0900700010003", "0900700010004"]],
    ]),
    porCvegeo: new Map([
      ["0900700010001", { demanda: registroConH("baja", "media", 2.5), oferta: null }],
      ["0900700010002", { demanda: registroConH("sube", "alta", 1.0), oferta: null }],
      ["0900700010003", { demanda: registroConH("sin_datos", "baja", null), oferta: null }],
      ["0900700010004", { demanda: registroConH("baja", "baja", 3.8), oferta: null }],
    ]),
  },
};

const NOMBRES_ALCALDIA_FIXTURE = new Map([["007", "Coyoacán"]]);

const BRECHA_FIXTURE = { min: 0, max: 20, cortes: [4, 8, 12, 16], unidad: "establecimientos por 1,000" };

// ------------------------------------------------------------------
// contarPorVeredicto
// ------------------------------------------------------------------

prueba("contarPorVeredicto: cuenta los 4 veredictos y degrada valores inválidos a sin_datos", () => {
  const registros = [
    { veredicto: "sube", confianza: "alta" },
    { veredicto: "baja", confianza: "baja" },
    { veredicto: "baja", confianza: "media" },
    { veredicto: "se_mantiene", confianza: "alta" },
    null,
    { veredicto: "algo-invalido", confianza: "alta" },
  ];
  const conteo = contarPorVeredicto(registros);
  afirmarIgual(conteo, { sube: 1, se_mantiene: 1, baja: 2, sin_datos: 2, total: 6, confianzaBaja: 1 });
});

prueba("contarPorVeredicto: la confianza baja de registros sin_datos no cuenta", () => {
  const registros = [{ veredicto: "sin_datos", confianza: "baja" }];
  const conteo = contarPorVeredicto(registros);
  afirmarIgual(conteo.confianzaBaja, 0);
  afirmarIgual(conteo.sin_datos, 1);
});

prueba("contarPorVeredicto: lista vacía o no-array no lanza", () => {
  afirmarIgual(contarPorVeredicto([]).total, 0);
  afirmarIgual(contarPorVeredicto(null).total, 0);
  afirmarIgual(contarPorVeredicto(undefined).total, 0);
});

// ------------------------------------------------------------------
// seleccionarRegistrosVisibles
// ------------------------------------------------------------------

prueba("seleccionarRegistrosVisibles: vista ciudad cuenta sobre alcaldías (demanda)", () => {
  const registros = seleccionarRegistrosVisibles({
    enAlcaldia: false,
    cveMun: null,
    capaActiva: "demanda",
    horizonteActivo: "hU",
    datosAlcaldia: DATOS_ALCALDIA_FIXTURE,
    datosAgeb: null,
  });
  afirmarIgual(registros.length, 6);
  const conteo = contarPorVeredicto(registros);
  afirmarIgual(conteo, { sube: 2, se_mantiene: 1, baja: 2, sin_datos: 1, total: 6, confianzaBaja: 1 });
});

prueba("seleccionarRegistrosVisibles: vista alcaldía cuenta sobre las AGEB de esa alcaldía", () => {
  const registros = seleccionarRegistrosVisibles({
    enAlcaldia: true,
    cveMun: "007",
    capaActiva: "demanda",
    horizonteActivo: "hU",
    datosAlcaldia: null,
    datosAgeb: DATOS_AGEB_FIXTURE,
  });
  afirmarIgual(registros.length, 4);
  const conteo = contarPorVeredicto(registros);
  afirmarIgual(conteo, { sube: 1, se_mantiene: 0, baja: 2, sin_datos: 1, total: 4, confianzaBaja: 1 });
});

prueba("seleccionarRegistrosVisibles: sin índices disponibles, degrada a lista vacía (nunca lanza)", () => {
  afirmarIgual(seleccionarRegistrosVisibles({ enAlcaldia: false, datosAlcaldia: null }).length, 0);
  afirmarIgual(
    seleccionarRegistrosVisibles({ enAlcaldia: true, cveMun: "007", datosAgeb: null }).length,
    0,
  );
});

// ------------------------------------------------------------------
// construirFilasBrecha: rampa de 5 cortes (nunca visible hoy con v1.1, solo por fixture).
// ------------------------------------------------------------------

prueba("construirFilasBrecha: 5 filas con límites numéricos correctos", () => {
  const filas = construirFilasBrecha(BRECHA_FIXTURE);
  afirmarIgual(filas.length, 5);
  afirmarIgual(filas[0], { color: "brecha-1", desde: 0, hasta: 4 });
  afirmarIgual(filas[1], { color: "brecha-2", desde: 4, hasta: 8 });
  afirmarIgual(filas[2], { color: "brecha-3", desde: 8, hasta: 12 });
  afirmarIgual(filas[3], { color: "brecha-4", desde: 12, hasta: 16 });
  afirmarIgual(filas[4], { color: "brecha-5", desde: 16, hasta: 20 });
});

prueba("construirFilasBrecha: forma inválida degrada a lista vacía", () => {
  afirmarIgual(construirFilasBrecha(null), []);
  afirmarIgual(construirFilasBrecha({ min: 0, max: 10, cortes: [1, 2] }), []);
  afirmarIgual(construirFilasBrecha({ min: 0, cortes: [1, 2, 3, 4] }), []);
});

// ------------------------------------------------------------------
// montarLeyenda: DOM real, sin innerHTML.
// ------------------------------------------------------------------

prueba("montarLeyenda: 4 filas <button aria-pressed>, en el orden de ORDEN_VEREDICTOS", () => {
  reiniciarEstado();
  const contenedor = document.createElement("aside");
  const instancia = montarLeyenda(contenedor, {
    datosAlcaldia: DATOS_ALCALDIA_FIXTURE,
    datosAgeb: DATOS_AGEB_FIXTURE,
    nombresAlcaldia: NOMBRES_ALCALDIA_FIXTURE,
  });
  try {
    const botones = Array.from(contenedor.querySelectorAll("button.leyenda__fila"));
    afirmarIgual(botones.length, 4);
    afirmarIgual(botones.map((b) => b.dataset.veredicto), ORDEN_VEREDICTOS);
    for (const boton of botones) {
      afirmar(boton.hasAttribute("aria-pressed"), "cada fila debe traer aria-pressed");
      afirmarIgual(boton.getAttribute("aria-pressed"), "false");
    }
  } finally {
    instancia.destruir();
    reiniciarEstado();
  }
});

prueba("montarLeyenda: conteos correctos en vista ciudad (alcaldías)", () => {
  reiniciarEstado();
  const contenedor = document.createElement("aside");
  const instancia = montarLeyenda(contenedor, {
    datosAlcaldia: DATOS_ALCALDIA_FIXTURE,
    datosAgeb: DATOS_AGEB_FIXTURE,
    nombresAlcaldia: NOMBRES_ALCALDIA_FIXTURE,
  });
  try {
    const conteoPorVeredicto = {};
    for (const boton of contenedor.querySelectorAll("button.leyenda__fila")) {
      conteoPorVeredicto[boton.dataset.veredicto] = boton.querySelector(".leyenda__conteo").textContent;
    }
    afirmarIgual(conteoPorVeredicto, { sube: "2", se_mantiene: "1", baja: "2", sin_datos: "1" });
  } finally {
    instancia.destruir();
    reiniciarEstado();
  }
});

prueba("montarLeyenda: al entrar a una alcaldía, los conteos cambian a sus AGEB", () => {
  reiniciarEstado();
  const contenedor = document.createElement("aside");
  const instancia = montarLeyenda(contenedor, {
    datosAlcaldia: DATOS_ALCALDIA_FIXTURE,
    datosAgeb: DATOS_AGEB_FIXTURE,
    nombresAlcaldia: NOMBRES_ALCALDIA_FIXTURE,
  });
  try {
    despachar({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: "007" });
    afirmarIgual(obtenerEstado().vista, VISTA.ALCALDIA);

    const conteoPorVeredicto = {};
    for (const boton of contenedor.querySelectorAll("button.leyenda__fila")) {
      conteoPorVeredicto[boton.dataset.veredicto] = boton.querySelector(".leyenda__conteo").textContent;
    }
    afirmarIgual(conteoPorVeredicto, { sube: "1", se_mantiene: "0", baja: "2", sin_datos: "1" });

    const encabezado = contenedor.querySelector(".leyenda__encabezado").textContent;
    afirmar(encabezado.includes("Coyoacán"), `el encabezado debe nombrar la alcaldía activa: "${encabezado}"`);
  } finally {
    instancia.destruir();
    reiniciarEstado();
  }
});

prueba("montarLeyenda: pulsar una fila despacha el filtro y marca aria-pressed", () => {
  reiniciarEstado();
  const contenedor = document.createElement("aside");
  const instancia = montarLeyenda(contenedor, {
    datosAlcaldia: DATOS_ALCALDIA_FIXTURE,
    datosAgeb: DATOS_AGEB_FIXTURE,
  });
  try {
    contenedor.querySelector('button.leyenda__fila[data-veredicto="baja"]').click();
    afirmarIgual(obtenerEstado().filtroLeyenda, "baja");

    const botonBaja = contenedor.querySelector('button.leyenda__fila[data-veredicto="baja"]');
    afirmarIgual(botonBaja.getAttribute("aria-pressed"), "true");

    const mensaje = contenedor.querySelector(".leyenda__filtro-activo");
    afirmar(!mensaje.hidden, "el mensaje de filtro activo debe mostrarse");
    afirmar(
      mensaje.textContent.includes("Mostrando 2 de 6"),
      `mensaje inesperado: "${mensaje.textContent}"`,
    );

    // Pulsarla de nuevo la desactiva (estado.js, spec §10.4).
    botonBaja.click();
    afirmarIgual(obtenerEstado().filtroLeyenda, null);
    afirmar(contenedor.querySelector(".leyenda__filtro-activo").hidden, "el mensaje debe ocultarse sin filtro");
  } finally {
    instancia.destruir();
    reiniciarEstado();
  }
});

prueba('montarLeyenda: "Quitar filtro" limpia el filtro', () => {
  reiniciarEstado();
  const contenedor = document.createElement("aside");
  const instancia = montarLeyenda(contenedor, { datosAlcaldia: DATOS_ALCALDIA_FIXTURE, datosAgeb: DATOS_AGEB_FIXTURE });
  try {
    despachar({ tipo: ACCIONES.CAMBIAR_FILTRO, filtro: "sube" });
    contenedor.querySelector(".leyenda__quitar-filtro").click();
    afirmarIgual(obtenerEstado().filtroLeyenda, null);
  } finally {
    instancia.destruir();
    reiniciarEstado();
  }
});

prueba("montarLeyenda: la capa brecha no aparece con datosAlcaldia/datosAgeb del contrato v1.1", () => {
  reiniciarEstado();
  const contenedor = document.createElement("aside");
  const instancia = montarLeyenda(contenedor, {
    datosAlcaldia: DATOS_ALCALDIA_FIXTURE,
    datosAgeb: DATOS_AGEB_FIXTURE,
    brecha: BRECHA_FIXTURE,
  });
  try {
    // estado.js nunca deja capa="brecha" (config.js → CAPAS = ["demanda","oferta"]): la fila de
    // brecha no debe estar en el DOM aunque se le haya pasado un fixture de brecha.
    afirmar(!contenedor.querySelector(".leyenda__brecha"), "la fila de brecha no debe aparecer con v1.1");
  } finally {
    instancia.destruir();
    reiniciarEstado();
  }
});

prueba("montarLeyenda: destruir() quita el realce cruzado del mapa", () => {
  reiniciarEstado();
  const contenedorMapa = document.createElement("section");
  contenedorMapa.id = "contenedor-mapa";
  document.body.appendChild(contenedorMapa);
  const contenedorLeyenda = document.createElement("aside");
  contenedorMapa.appendChild(contenedorLeyenda);

  const instancia = montarLeyenda(contenedorLeyenda, {
    datosAlcaldia: DATOS_ALCALDIA_FIXTURE,
    datosAgeb: DATOS_AGEB_FIXTURE,
  });
  try {
    contenedorLeyenda.querySelector('button.leyenda__fila[data-veredicto="sube"]').click();
    afirmarIgual(contenedorMapa.getAttribute("data-filtro-veredicto"), "sube");
    instancia.destruir();
    afirmar(!contenedorMapa.hasAttribute("data-filtro-veredicto"), "destruir() debe limpiar el atributo");
  } finally {
    reiniciarEstado();
    contenedorMapa.remove();
  }
});

prueba("montarLeyenda: actualizar() repinta con datos nuevos", () => {
  reiniciarEstado();
  const contenedor = document.createElement("aside");
  const instancia = montarLeyenda(contenedor, { datosAlcaldia: null, datosAgeb: null });
  try {
    let conteoInicial = contenedor.querySelector('button.leyenda__fila[data-veredicto="sube"] .leyenda__conteo').textContent;
    afirmarIgual(conteoInicial, "0");

    instancia.actualizar({ datosAlcaldia: DATOS_ALCALDIA_FIXTURE });
    const conteoTrasActualizar = contenedor.querySelector('button.leyenda__fila[data-veredicto="sube"] .leyenda__conteo').textContent;
    afirmarIgual(conteoTrasActualizar, "2");
  } finally {
    instancia.destruir();
    reiniciarEstado();
  }
});
