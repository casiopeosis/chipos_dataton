// frontend/tests/pruebas_veredictos.js
//
// Pruebas en navegador (mismo patrón sin framework que tests/pruebas.js) de F35:
// - resumirVeredictos (js/veredictos.js), los 6 escenarios de §6.2 y el matiz de confianza baja.
// - calcularTitular (js/titular.js): plantillas §6.3 y §6.5 con los mocks reales de F10, el
//   sufijo de confianza baja y "De mantenerse las tendencias..." a 7 años.
// - Invariante "titular = tabla": el veredicto agregado que arma la frase del titular es
//   exactamente el que produciría una tabla que resuma el mismo conjunto de registros, porque
//   ambos llaman a la misma `resumirVeredictos` con los mismos registros.
//
// Exporta `pruebasVeredictos` (array `{nombre, fn}}`, mismo formato que el runner de
// tests/pruebas.js) para que se pueda enganchar ahí (`pruebas.push(...pruebasVeredictos)`) sin
// tocar ese archivo desde esta tarea. También se puede ejecutar solo, ver tests/index_veredictos.html.

import { resumirVeredictos, UMBRALES_VEREDICTO_GENERAL, ESCENARIO } from "../js/veredictos.js";
import { calcularTitular, resolverHorizonte, montarTitular } from "../js/titular.js";
import { textos } from "../js/textos.js";

export const pruebasVeredictos = [];

function prueba(nombre, fn) {
  pruebasVeredictos.push({ nombre, fn });
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

// ------------------------------------------------------------------
// Fixtures: listas sintéticas de 16 "alcaldías" cubriendo cada escenario de §6.2.
// ------------------------------------------------------------------

function registros(veredictos, confianza = "alta") {
  return veredictos.map((veredicto) => ({ veredicto, confianza }));
}

const FIXTURES_ESCENARIO = {
  // V = 7 < 8: insuficiente, sin importar la mezcla.
  insuficiente: registros(["sube", "baja", "baja", "se_mantiene", "sin_datos", "sin_datos", "sin_datos", "sin_datos", "sin_datos"]),
  // V = 16, n_baja = 10 (>=60%), n_sube = 1 (<=15%): predominio de baja.
  baja: registros(["baja", "baja", "baja", "baja", "baja", "baja", "baja", "baja", "baja", "baja", "sube", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene"]),
  // simétrico: predominio de sube.
  sube: registros(["sube", "sube", "sube", "sube", "sube", "sube", "sube", "sube", "sube", "sube", "baja", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene"]),
  // V = 16, n_sube = 5 (>=25%), n_baja = 5 (>=25%): polarizado (no cumple mayoría 60%/15%).
  polarizado: registros(["sube", "sube", "sube", "sube", "sube", "baja", "baja", "baja", "baja", "baja", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene"]),
  // V = 16, n_mant = 9 (>=50%): mayoría se mantiene.
  mantiene: registros(["se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "sube", "sube", "sube", "baja", "baja", "baja", "sin_datos"]),
  // V = 16, n_sube = 3 (<25%: no polariza), n_baja = 6, n_mant = 7 (<50%: no hay mayoría):
  // ninguna condición anterior se cumple -> mixto.
  mixto: registros(["sube", "sube", "sube", "baja", "baja", "baja", "baja", "baja", "baja", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene", "se_mantiene"]),
};

// ------------------------------------------------------------------
// resumirVeredictos: los 6 escenarios de §6.2
// ------------------------------------------------------------------

prueba("resumirVeredictos: V < 8 -> insuficiente, sin importar el resto", () => {
  const resumen = resumirVeredictos(FIXTURES_ESCENARIO.insuficiente);
  afirmarIgual(resumen.escenario, ESCENARIO.INSUFICIENTE);
  afirmar(resumen.v < UMBRALES_VEREDICTO_GENERAL.V_MINIMO);
});

prueba("resumirVeredictos: predominio de baja (n_baja >= 60% y n_sube <= 15%)", () => {
  const resumen = resumirVeredictos(FIXTURES_ESCENARIO.baja);
  afirmarIgual(resumen.v, 16);
  afirmarIgual(resumen.escenario, ESCENARIO.BAJA);
});

prueba("resumirVeredictos: predominio de sube (simétrico)", () => {
  const resumen = resumirVeredictos(FIXTURES_ESCENARIO.sube);
  afirmarIgual(resumen.escenario, ESCENARIO.SUBE);
});

prueba("resumirVeredictos: polarizado (n_sube y n_baja >= 25%, sin mayoría de ninguno)", () => {
  const resumen = resumirVeredictos(FIXTURES_ESCENARIO.polarizado);
  afirmarIgual(resumen.escenario, ESCENARIO.POLARIZADO);
});

prueba("resumirVeredictos: mayoría se mantiene (n_mant >= 50%)", () => {
  const resumen = resumirVeredictos(FIXTURES_ESCENARIO.mantiene);
  afirmarIgual(resumen.escenario, ESCENARIO.MANTIENE);
});

prueba("resumirVeredictos: mixto cuando ninguna condición anterior se cumple", () => {
  const resumen = resumirVeredictos(FIXTURES_ESCENARIO.mixto);
  afirmarIgual(resumen.escenario, ESCENARIO.MIXTO);
});

prueba("resumirVeredictos: escenarios se evalúan en orden, gana la primera condición", () => {
  // 16 registros, todos "baja": cumple a la vez predominio de baja Y (trivialmente) mantiene=no,
  // pero también podría leerse como polarizado si se evaluara mal el orden. Verifica que gana
  // "baja" (escenario 2), la primera condición aplicable.
  const resumen = resumirVeredictos(registros(Array(16).fill("baja")));
  afirmarIgual(resumen.escenario, ESCENARIO.BAJA);
});

prueba("resumirVeredictos: registros vacíos, nulos o con veredicto inválido cuentan como sin dato", () => {
  const resumen = resumirVeredictos([null, undefined, {}, { veredicto: "no_es_valido" }, { veredicto: "sin_datos" }]);
  afirmarIgual(resumen.v, 0);
  afirmarIgual(resumen.nSin, 5);
  afirmarIgual(resumen.escenario, ESCENARIO.INSUFICIENTE);
});

prueba("resumirVeredictos: lista vacía o no-array no lanza y degrada a insuficiente", () => {
  afirmarIgual(resumirVeredictos([]).escenario, ESCENARIO.INSUFICIENTE);
  afirmarIgual(resumirVeredictos(null).escenario, ESCENARIO.INSUFICIENTE);
  afirmarIgual(resumirVeredictos(undefined).escenario, ESCENARIO.INSUFICIENTE);
});

prueba("resumirVeredictos: matiz de confianza baja dominante (>= 50% de V)", () => {
  const mitadBaja = registros(Array(16).fill("baja"), "alta").map((r, i) => ({
    ...r,
    confianza: i < 8 ? "baja" : "alta",
  }));
  const resumen = resumirVeredictos(mitadBaja);
  afirmar(resumen.confianzaBajaDominante, "8 de 16 (50%) debe activar el matiz de confianza baja");

  const minoriaBaja = registros(Array(16).fill("baja"), "alta").map((r, i) => ({
    ...r,
    confianza: i < 7 ? "baja" : "alta",
  }));
  afirmar(
    !resumirVeredictos(minoriaBaja).confianzaBajaDominante,
    "7 de 16 (<50%) no debe activar el matiz de confianza baja",
  );
});

// ------------------------------------------------------------------
// Invariante "titular = tabla": el escenario del titular coincide con el que produciría una
// tabla que agregue los mismos registros, porque ambos usan `resumirVeredictos`.
// ------------------------------------------------------------------

function resumenComoLoHariaUnaTabla(registrosVista) {
  // Simula lo que haría js/tabla.js (F40) al agregar sus propias filas: exactamente la misma
  // llamada que hace calcularTitular internamente.
  return resumirVeredictos(registrosVista);
}

for (const [nombreFixture, listaRegistros] of Object.entries(FIXTURES_ESCENARIO)) {
  prueba(`invariante titular = tabla: escenario "${nombreFixture}" coincide en ambos`, () => {
    const resumenTitular = calcularTitular({
      capa: "demanda",
      vista: "general",
      registros: listaRegistros,
      horizonte: { fecha: "2027-06", anios: null },
    }).resumen;
    const resumenTabla = resumenComoLoHariaUnaTabla(listaRegistros);
    afirmarIgual(resumenTitular.escenario, resumenTabla.escenario, "el escenario debe ser idéntico");
    afirmarIgual(resumenTitular.nBaja, resumenTabla.nBaja);
    afirmarIgual(resumenTitular.nSube, resumenTabla.nSube);
    afirmarIgual(resumenTitular.nMant, resumenTabla.nMant);
    afirmarIgual(resumenTitular.v, resumenTabla.v);
  });
}

// ------------------------------------------------------------------
// calcularTitular: plantillas §6.3 (vista general) con los mocks de F10
// ------------------------------------------------------------------

async function cargarMock(ruta) {
  const respuesta = await fetch(ruta);
  return respuesta.json();
}

function registrosAlcaldiaMock(json, capa) {
  return Object.values(json.capas[capa]).map((r) => ({ veredicto: r.veredicto, confianza: r.confianza }));
}

prueba("calcularTitular: vista general con el mock de alcaldías produce 'mixto' (fixture real de F10)", async () => {
  const json = await cargarMock("../mock/prediccion_alcaldia.json");
  const regs = registrosAlcaldiaMock(json, "demanda");
  const resultado = calcularTitular({
    capa: "demanda",
    vista: "general",
    registros: regs,
    horizonte: { fecha: json.horizonte, anios: null },
    generadoIso: json.generado,
  });
  afirmarIgual(resultado.resumen.escenario, ESCENARIO.MIXTO, "16 alcaldías del mock: 6 baja/6 mant./3 sube -> mixto");
  afirmar(resultado.frase.startsWith("A "), `debe empezar con "A {h} años,...": ${resultado.frase}`);
  afirmar(resultado.frase.includes("no muestra una dirección común"), resultado.frase);
  afirmar(resultado.frase.trim().endsWith("."), "la frase debe terminar en punto (spec §6.1)");
});

prueba("calcularTitular: capa oferta usa 'establecimientos', nunca la palabra 'demanda'", () => {
  const resultado = calcularTitular({
    capa: "oferta",
    vista: "general",
    registros: FIXTURES_ESCENARIO.baja,
    horizonte: { fecha: "2027-06", anios: null },
  });
  afirmar(resultado.frase.includes("establecimientos"), resultado.frase);
  afirmar(!resultado.frase.includes("demanda"), resultado.frase);
  afirmarIgual(resultado.notaOferta, textos.titular.notaOferta, "la nota de confianza máxima media siempre acompaña a oferta");
});

prueba("calcularTitular: sufijo de confianza baja dominante reemplaza el punto final", () => {
  const registrosConfianzaBaja = FIXTURES_ESCENARIO.baja.map((r) => ({ ...r, confianza: "baja" }));
  const resultado = calcularTitular({
    capa: "demanda",
    vista: "general",
    registros: registrosConfianzaBaja,
    horizonte: { fecha: "2027-06", anios: null },
  });
  afirmar(resultado.frase.endsWith(textos.titular.sufijoConfianzaBaja), resultado.frase);
  afirmar(!resultado.frase.trim().endsWith(". aunque"), "el punto original debe desaparecer, no duplicarse");
});

prueba("calcularTitular: horizonte a 7 años antepone 'De mantenerse las tendencias, a 7 años'", () => {
  const resultado = calcularTitular({
    capa: "demanda",
    vista: "general",
    registros: FIXTURES_ESCENARIO.baja,
    horizonte: { fecha: "2033-06", anios: 7 },
  });
  afirmar(resultado.frase.startsWith(textos.titular.prefijoH7), resultado.frase);
  afirmarIgual(resultado.h, 7);
});

prueba("calcularTitular: sin agregado_cdmx (siempre con v1.1) el subtítulo omite el bloque CDMX", () => {
  const resultado = calcularTitular({
    capa: "demanda",
    vista: "general",
    registros: FIXTURES_ESCENARIO.baja,
    horizonte: { fecha: "2027-06", anios: null },
    agregadoCdmx: null,
  });
  afirmar(!resultado.subtitulo.includes("CDMX"), resultado.subtitulo);
  afirmar(resultado.subtitulo.includes("MEDIADOS DE"), resultado.subtitulo);
});

// ------------------------------------------------------------------
// calcularTitular: plantillas §6.5 (vista de alcaldía)
// ------------------------------------------------------------------

prueba("calcularTitular: vista de alcaldía arma la frase con el nombre y V_a correctos", () => {
  const registrosAgeb = [
    ...Array(9).fill({ veredicto: "baja", confianza: "alta" }),
    ...Array(2).fill({ veredicto: "se_mantiene", confianza: "alta" }),
    { veredicto: "sin_datos" },
  ];
  const resultado = calcularTitular({
    capa: "demanda",
    vista: "alcaldia",
    registros: registrosAgeb,
    horizonte: { fecha: "2027-06", anios: null },
    generadoIso: "2026-09-18T00:00:00+00:00",
    alcaldiaNombre: "Coyoacán",
    nSinDatosAgeb: 1,
  });
  afirmar(resultado.frase.includes("En Coyoacán"), resultado.frase);
  afirmar(resultado.frase.includes("de sus 11 AGEB"), resultado.frase);
  afirmar(resultado.frase.includes("1 AGEB no tienen datos suficientes."), resultado.frase);
});

prueba("calcularTitular: vista de alcaldía sin resumen agregado propio omite el bloque de cambio", () => {
  const resultado = calcularTitular({
    capa: "demanda",
    vista: "alcaldia",
    registros: FIXTURES_ESCENARIO.baja,
    horizonte: { fecha: "2027-06", anios: null },
    alcaldiaNombre: "Gustavo A. Madero",
    resumenAlcaldia: null,
  });
  afirmar(resultado.subtitulo.includes("Gustavo A. Madero"), resultado.subtitulo);
  afirmar(!resultado.subtitulo.includes("ENTRE"), "sin resumenAlcaldia no debe inventar un rango");
});

// ------------------------------------------------------------------
// montarTitular: DOM sin innerHTML, altura reservada, crossfade
// ------------------------------------------------------------------

prueba("montarTitular: crea el header con frase/sub/nota/enlace y actualiza sin innerHTML", () => {
  const contenedor = document.createElement("main");
  const { raiz, actualizar } = montarTitular(contenedor);
  afirmar(raiz.tagName === "HEADER");
  afirmar(raiz.classList.contains("titular"));
  afirmarIgual(raiz.getAttribute("aria-live"), "off", "el titular no es aria-live (lo anuncia la región viva global)");

  actualizar({ frase: "Frase de prueba.", subtitulo: "SUBTÍTULO", notaOferta: null });
  afirmar(contenedor.querySelector(".titular__frase").textContent.includes("Frase de prueba."));
  afirmar(contenedor.querySelector(".titular__nota").hidden === true);

  actualizar({ frase: "Otra frase.", subtitulo: "OTRO SUBTÍTULO", notaOferta: "Nota de oferta." });
  afirmar(contenedor.querySelector(".titular__nota").hidden === false);
  afirmar(contenedor.querySelector(".titular__nota").textContent.includes("Nota de oferta."));
});

prueba("montarTitular: es idempotente (reutiliza #titular si ya existe en el contenedor)", () => {
  const contenedor = document.createElement("main");
  const primero = montarTitular(contenedor);
  const segundo = montarTitular(contenedor);
  afirmar(primero.raiz === segundo.raiz, "una segunda llamada debe reutilizar el mismo header");
  afirmarIgual(contenedor.querySelectorAll("#titular").length, 1);
});

prueba("resolverHorizonte: deriva años redondeados cuando anios es null (contrato v1.1 adaptado)", () => {
  const { anio, h } = resolverHorizonte({ fecha: "2027-06", anios: null }, "2026-09-18T00:00:00+00:00");
  afirmarIgual(anio, 2027);
  afirmar(Number.isInteger(h) && h >= 1, `h debe ser un entero >= 1, obtuvo ${h}`);
});

prueba("resolverHorizonte: usa anios explícito cuando el contrato lo trae (v1.2 real, código listo)", () => {
  const { anio, h } = resolverHorizonte({ fecha: "2033-06", anios: 7 }, "2026-09-18T00:00:00+00:00");
  afirmarIgual(anio, 2033);
  afirmarIgual(h, 7);
});
