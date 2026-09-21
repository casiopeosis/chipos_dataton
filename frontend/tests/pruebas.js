// Pruebas de integración del frontend Habitancia (contrato v1.4 + degradación heredada).
// Se ejecutan en navegador desde tests/index.html y publican el resultado en window.__pruebas.

import { crear, texto, limpiar, reemplazarContenido } from "../js/dom.js";
import { formatoPorcentaje, simboloVeredicto, simboloConfianza } from "../js/formato.js";
import {
  adaptarV14,
  adaptarV12aV14,
  adaptarV11aV14,
  validarContrato,
  obtenerRegistroSegmento,
  obtenerCeldasRama,
  ErrorDatos,
} from "../js/api.js";
import {
  VERSIONES_CONTRATO_ACEPTADAS,
  SEGMENTOS_DEMANDA,
  RAMAS,
  NIVEL,
  rutaDatos,
} from "../js/config.js";
import { ESTADO_POR_DEFECTO, ACCIONES, analizarHash, serializarHash, reducir } from "../js/estado.js";
import { sugerenciaEducacionParaPoblacion } from "../js/filtros.js";

const pruebas = [];
function prueba(nombre, fn) { pruebas.push({ nombre, fn }); }
function afirmar(condicion, mensaje = "afirmación falsa") { if (!condicion) throw new Error(mensaje); }
function afirmarIgual(actual, esperado, mensaje = "no coincide") {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(esperado);
  if (a !== e) throw new Error(`${mensaje}: esperado ${e}, obtuvo ${a}`);
}
function esperarError(fn, codigo) {
  let error = null;
  try { fn(); } catch (e) { error = e; }
  afirmar(error instanceof ErrorDatos, "debe lanzar ErrorDatos");
  afirmarIgual(error.codigo, codigo);
}

function bloqueH(veredicto = "sube", delta = 5, confianza = "media") {
  return { veredicto, delta_pct: delta, tasa_anual_pct: 1.5, ic95: [1, 9], confianza };
}

function registroTemporal(nivelBase = 100) {
  return {
    n_obs: 3,
    motivo_sin_datos: null,
    serie: { t: [2020.2], valor: [nivelBase] },
    nivel_base: nivelBase,
    h: { h1: bloqueH(), h3: bloqueH("sube", 10) },
  };
}

function fixtureV14() {
  const segmentos = Object.fromEntries(SEGMENTOS_DEMANDA.map((s) => [s, registroTemporal(100)]));
  const ramas = Object.fromEntries(RAMAS.map((rama) => [rama, {
    "0900200010025": {
      cve_mun: "002",
      horizontes_disponibles: rama === "verde" ? [] : ["h1", "h3"],
      celdas: rama === "verde"
        ? { cobertura_verde: { nivel_base: 12.5, unidad: "porcentaje" } }
        : { todos: registroTemporal(2) },
    },
  }]));
  return {
    version: "1.4",
    generado: "2026-09-21T00:00:00+00:00",
    fecha_base: "2026-06",
    horizontes: [
      { clave: "h1", anios: 1, fecha: "2027-06" },
      { clave: "h3", anios: 3, fecha: "2029-06" },
      { clave: "h5", anios: 5, fecha: "2031-06" },
    ],
    capas: {
      demanda: { "0900200010025": { cve_mun: "002", segmentos } },
      ramas,
    },
  };
}

function fixtureV12() {
  return {
    version: "1.2",
    generado: "2026-09-21T00:00:00+00:00",
    fecha_base: "2026-06",
    horizontes: [{ clave: "h3", anios: 3, fecha: "2029-06" }],
    capas: {
      demanda: { "0900200010025": { cve_mun: "002", ...registroTemporal(100) } },
      oferta: { "0900200010025": { cve_mun: "002", ...registroTemporal(3) } },
    },
  };
}

function fixtureV11() {
  return {
    version: "1.1",
    generado: "2026-09-21T00:00:00+00:00",
    horizonte: "2027-06",
    capas: {
      demanda: { "0900200010025": { cve_mun: "002", n_obs: 2, ...bloqueH() } },
      oferta: { "0900200010025": { cve_mun: "002", n_obs: 3, ...bloqueH("baja", -3) } },
    },
  };
}

prueba("formato: porcentaje usa signo menos tipográfico y espacio fino", () => {
  afirmarIgual(formatoPorcentaje(-17.9), "−17.9 %");
});
prueba("formato: cubre valores desconocidos sin romper", () => {
  afirmarIgual(simboloVeredicto("desconocido"), "∅");
  afirmarIgual(simboloConfianza("desconocida"), "○");
});
prueba("dom: crear trata HTML recibido como texto literal", () => {
  const el = crear("div", { clase: "segura" }, ["<img src=x onerror=alert(1)>"]);
  afirmar(el.querySelector("img") === null);
  afirmar(el.textContent.startsWith("<img"));
});
prueba("dom: limpiar y reemplazarContenido eliminan nodos anteriores", () => {
  const el = crear("div", {}, [crear("span", {}, ["anterior"])]);
  limpiar(el);
  afirmarIgual(el.childNodes.length, 0);
  reemplazarContenido(el, [texto("nuevo")]);
  afirmarIgual(el.textContent, "nuevo");
});

prueba("config: acepta v1.4 y conserva v1.2/v1.1 como degradación", () => {
  afirmarIgual(VERSIONES_CONTRATO_ACEPTADAS, ["1.4", "1.2", "1.1"]);
});
prueba("validarContrato: acepta v1.4 completo", () => {
  afirmar(validarContrato(fixtureV14()) === true);
});
prueba("validarContrato: rechaza una versión incompatible", () => {
  esperarError(() => validarContrato({ ...fixtureV14(), version: "9.9" }), "version_incompatible");
});
prueba("validarContrato: v1.4 exige las cuatro ramas", () => {
  const json = fixtureV14();
  delete json.capas.ramas.salud;
  esperarError(() => validarContrato(json), "esquema_invalido");
});
prueba("adaptarV14: conserva seis segmentos y cuatro ramas indexadas", () => {
  const adaptado = adaptarV14(fixtureV14(), NIVEL.AGEB);
  const clave = "0900200010025";
  afirmarIgual(Object.keys(adaptado.capas.demanda[clave].segmentos), [...SEGMENTOS_DEMANDA]);
  afirmarIgual(Object.keys(adaptado.capas.ramas), [...RAMAS]);
  afirmar(adaptado.indices.porCvegeo.has(clave));
  afirmar(adaptado.indices.porCveMun.get("002").includes(clave));
});
prueba("adaptarV14: un bloque inválido degrada a sin_datos", () => {
  const json = fixtureV14();
  json.capas.demanda["0900200010025"].segmentos.primaria.h.h1.veredicto = "inventado";
  const adaptado = adaptarV14(json, NIVEL.AGEB);
  afirmarIgual(adaptado.capas.demanda["0900200010025"].segmentos.primaria.h.h1.veredicto, "sin_datos");
});
prueba("obtenerRegistroSegmento: una clave ausente nunca devuelve undefined", () => {
  const adaptado = adaptarV14(fixtureV14(), NIVEL.AGEB);
  afirmarIgual(obtenerRegistroSegmento(adaptado, "0900999999999", "primaria").h.h1.veredicto, "sin_datos");
});
prueba("obtenerCeldasRama: una rama ausente devuelve un objeto vacío", () => {
  const adaptado = adaptarV14(fixtureV14(), NIVEL.AGEB);
  afirmarIgual(obtenerCeldasRama(adaptado, "0900999999999", "salud"), {});
});
prueba("adaptarV12aV14: no inventa salud, comercio ni verde", () => {
  const adaptado = adaptarV12aV14(fixtureV12(), NIVEL.AGEB);
  const clave = "0900200010025";
  afirmar(Object.keys(adaptado.capas.ramas.educacion[clave].celdas).length === 1);
  afirmarIgual(adaptado.capas.ramas.salud[clave].celdas, {});
  afirmarIgual(adaptado.capas.ramas.comercio[clave].celdas, {});
  afirmarIgual(adaptado.capas.ramas.verde[clave].celdas, {});
});
prueba("adaptarV11aV14: conserva el horizonte único y la fecha base heredada", () => {
  const adaptado = adaptarV11aV14(fixtureV11(), NIVEL.AGEB);
  afirmarIgual(adaptado.horizontes, [{ clave: "hU", anios: null, fecha: "2027-06" }]);
  afirmarIgual(adaptado.fecha_base, "2027-06");
  afirmarIgual(adaptado.capas.demanda["0900200010025"].segmentos.todas.h.hU.veredicto, "sube");
});

prueba("mock v1.4 AGEB: incluye 2453 unidades y las cuatro ramas", async () => {
  const json = await (await fetch("../mock/prediccion_ageb.json")).json();
  validarContrato(json);
  afirmarIgual(json.version, "1.4");
  afirmarIgual(Object.keys(json.capas.demanda).length, 2453);
  for (const rama of RAMAS) afirmarIgual(Object.keys(json.capas.ramas[rama]).length, 2453, rama);
});
prueba("mock v1.4: catálogo completo de 44 celdas y un cero publicado", async () => {
  const json = await (await fetch("../mock/prediccion_ageb.json")).json();
  const primera = Object.keys(json.capas.demanda)[0];
  const totalCeldas = RAMAS.reduce((n, rama) => n + Object.keys(json.capas.ramas[rama][primera].celdas).length, 0);
  afirmarIgual(totalCeldas, 44);
  const hayCero = RAMAS.some((rama) => Object.values(json.capas.ramas[rama][primera].celdas)
    .some((celda) => celda.nivel_base === 0));
  afirmar(hayCero, "el fixture debe cubrir oferta cero publicada");
});
prueba("mock v1.4 alcaldía: trae las 16 alcaldías y agregado CDMX", async () => {
  const json = await (await fetch("../mock/prediccion_alcaldia.json")).json();
  validarContrato(json);
  afirmarIgual(Object.keys(json.capas.demanda).length, 16);
  afirmar(json.agregado_cdmx?.demanda?.segmentos?.todas, "falta agregado_cdmx");
});
prueba("mock v1.1 sigue siendo válido para la degradación", async () => {
  const json = await (await fetch("../mock/prediccion_ageb_v11.json")).json();
  const adaptado = adaptarV11aV14(json, NIVEL.AGEB);
  afirmarIgual(adaptado.version, "1.4");
  afirmar(adaptado.indices.porCvegeo.size > 2000);
});
prueba("rutas: sin mock usa datos reales y ?mock=1 usa fixtures", () => {
  afirmarIgual(rutaDatos(NIVEL.AGEB, null), "data/prediccion_ageb.json");
  afirmarIgual(rutaDatos(NIVEL.AGEB, "1"), "mock/prediccion_ageb.json");
});

prueba("estado: hash vacío produce el escenario por omisión", () => {
  afirmarIgual(analizarHash(""), ESTADO_POR_DEFECTO);
});
prueba("estado: serializar y analizar conserva el escenario completo", () => {
  const estado = {
    ...ESTADO_POR_DEFECTO,
    horizonte: "h5",
    poblacion: "primaria",
    pesos: { educacion: 5, salud: 4, comercio: 2, verde: 1 },
    filtros: { ...ESTADO_POR_DEFECTO.filtros, comercio: ["abarrotes"] },
    umbralRiesgo: 0.8,
  };
  afirmarIgual(analizarHash(serializarHash(estado)), estado);
});
prueba("filtros: las sugerencias son explícitas y no se inventan para otras poblaciones", () => {
  afirmarIgual(sugerenciaEducacionParaPoblacion("primaria"), ["primaria"]);
  afirmarIgual(sugerenciaEducacionParaPoblacion("adolescencia"), ["media_superior_tecnica"]);
  afirmarIgual(sugerenciaEducacionParaPoblacion("todas"), null);
});
prueba("reducir: pesos se limitan al rango permitido", () => {
  const cambiado = reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_PESO, rama: "educacion", peso: 5 });
  afirmarIgual(cambiado.pesos.educacion, 5);
  afirmar(reducir(cambiado, { tipo: ACCIONES.CAMBIAR_PESO, rama: "educacion", peso: 9 }) === cambiado);
});

async function ejecutarPruebas() {
  const resultados = [];
  for (const { nombre, fn } of pruebas) {
    try { await fn(); resultados.push({ nombre, ok: true }); }
    catch (error) { resultados.push({ nombre, ok: false, error: error?.message ?? String(error) }); }
  }
  return resultados;
}

async function main() {
  const resultados = await ejecutarPruebas();
  const ok = resultados.filter((r) => r.ok).length;
  const total = resultados.length;
  const lista = crear("ul", { clase: "lista-pruebas" }, resultados.map((r) =>
    crear("li", { clase: r.ok ? "prueba-ok" : "prueba-fallo" }, [
      `${r.ok ? "PASA" : "FALLA"} — ${r.nombre}`,
      r.ok ? null : crear("pre", {}, [r.error]),
    ]),
  ));
  reemplazarContenido(document.getElementById("resultados"), [
    crear("p", { clase: "resumen", id: "resumen-pruebas" }, [`${ok} / ${total} pruebas pasan`]),
    lista,
  ]);
  document.body.dataset.pruebasEstado = ok === total ? "ok" : "fallo";
  document.body.dataset.pruebasResumen = `${ok}/${total}`;
  window.__pruebas = { ok, total, resultados };
  if (ok !== total) console.error("Pruebas fallidas:", resultados.filter((r) => !r.ok));
  console.log(`[pruebas] ${ok}/${total} pasan`);
}

main();
