// frontend/tests/pruebas.js
//
// Pruebas en navegador de las utilidades puras de F15 (sin framework).
// Se ejecutan al cargar tests/index.html y pintan su resultado en el DOM;
// además exponen `window.__pruebas` con el resumen para verificación
// automatizada (p. ej. Playwright) sin tener que leer el DOM renderizado.

import { crear, texto, limpiar, reemplazarContenido } from "../js/dom.js";
import {
  formatoPorcentaje,
  formatoEntero,
  formatoNumero,
  simboloVeredicto,
  simboloConfianza,
  SIMBOLO_VEREDICTO,
  SIMBOLO_CONFIANZA,
} from "../js/formato.js";
import { adaptarV11aV12, validarContrato, obtenerRegistro, ErrorDatos } from "../js/api.js";
import { VERSION_CONTRATO_ESPERADA, CLAVE_HORIZONTE_UNICO, NIVEL } from "../js/config.js";

// ------------------------------------------------------------------
// Runner mínimo
// ------------------------------------------------------------------

const pruebas = [];

function prueba(nombre, fn) {
  pruebas.push({ nombre, fn });
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
// formato.js — cifras es-MX
// ------------------------------------------------------------------

prueba("formatoPorcentaje: negativo usa signo menos tipográfico U+2212", () => {
  const resultado = formatoPorcentaje(-17.9);
  afirmar(resultado.startsWith("−"), `debe empezar con U+2212, obtuvo: ${JSON.stringify(resultado)}`);
  afirmar(!resultado.includes("-"), "no debe contener el guion ASCII");
});

prueba("formatoPorcentaje: positivo lleva '+' explícito", () => {
  const resultado = formatoPorcentaje(11.1);
  afirmar(resultado.startsWith("+"), `debe empezar con '+', obtuvo: ${JSON.stringify(resultado)}`);
});

prueba("formatoPorcentaje: espacio fino U+2009 antes de '%'", () => {
  const resultado = formatoPorcentaje(11.1);
  afirmar(resultado.includes(" %"), `debe contener espacio fino + %, obtuvo: ${JSON.stringify(resultado)}`);
  afirmar(!resultado.includes(" %"), "no debe usar espacio ASCII antes de %");
});

prueba("formatoPorcentaje: siempre 1 decimal, incluso con más precisión de entrada", () => {
  afirmarIgual(formatoPorcentaje(3.14159), "+3.1 %");
  afirmarIgual(formatoPorcentaje(-24.0), "−24.0 %");
});

prueba("formatoPorcentaje: cero sin signo", () => {
  afirmarIgual(formatoPorcentaje(0), "0.0 %");
});

prueba("formatoPorcentaje: valores no numéricos no truenan y devuelven un marcador", () => {
  afirmar(typeof formatoPorcentaje(null) === "string");
  afirmar(typeof formatoPorcentaje(undefined) === "string");
  afirmar(typeof formatoPorcentaje(Number.NaN) === "string");
});

prueba("formatoEntero: sin decimales, es-MX", () => {
  afirmarIgual(formatoEntero(11), "11");
  afirmarIgual(formatoEntero(4), "4");
});

prueba("formatoNumero: punto decimal (no coma) en es-MX", () => {
  const resultado = formatoNumero(12.3);
  afirmar(resultado.includes("."), `debe usar punto decimal, obtuvo: ${JSON.stringify(resultado)}`);
  afirmar(!resultado.includes(","), "no debe usar coma decimal");
});

prueba("símbolos de veredicto: los 4 valores del contrato", () => {
  afirmarIgual(simboloVeredicto("sube"), "▲");
  afirmarIgual(simboloVeredicto("se_mantiene"), "■");
  afirmarIgual(simboloVeredicto("baja"), "▼");
  afirmarIgual(simboloVeredicto("sin_datos"), "∅");
  afirmarIgual(Object.keys(SIMBOLO_VEREDICTO).length, 4, "no debe haber símbolos de veredicto extra");
});

prueba("símbolos de veredicto: valor desconocido se trata como sin_datos", () => {
  afirmarIgual(simboloVeredicto("valor_invalido"), SIMBOLO_VEREDICTO.sin_datos);
});

prueba("símbolos de confianza: las 3 confianzas del contrato", () => {
  afirmarIgual(simboloConfianza("alta"), "●");
  afirmarIgual(simboloConfianza("media"), "◐");
  afirmarIgual(simboloConfianza("baja"), "○");
  afirmarIgual(Object.keys(SIMBOLO_CONFIANZA).length, 3, "no debe haber símbolos de confianza extra");
});

prueba("símbolos de confianza: valor desconocido se trata como confianza baja", () => {
  afirmarIgual(simboloConfianza("valor_invalido"), SIMBOLO_CONFIANZA.baja);
});

// ------------------------------------------------------------------
// dom.js — sin innerHTML
// ------------------------------------------------------------------

prueba("dom.js: el código fuente nunca ASIGNA/LLAMA innerHTML/outerHTML/insertAdjacentHTML", async () => {
  // Se buscan usos reales (asignación o llamada), no menciones en comentarios/documentación,
  // para no producir un falso positivo con la propia advertencia del módulo.
  const respuesta = await fetch("../js/dom.js");
  const fuente = await respuesta.text();
  afirmar(!/\.innerHTML\s*(=|\+=)/.test(fuente), "dom.js no debe asignar a .innerHTML");
  afirmar(!/\.outerHTML\s*(=|\+=)/.test(fuente), "dom.js no debe asignar a .outerHTML");
  afirmar(!/\.insertAdjacentHTML\s*\(/.test(fuente), "dom.js no debe llamar a .insertAdjacentHTML(");
});

prueba("crear(): arma etiqueta, clase y texto correctamente", () => {
  const el = crear("div", { clase: "tarjeta" }, ["hola"]);
  afirmar(el.tagName === "DIV");
  afirmar(el.className === "tarjeta");
  afirmar(el.textContent === "hola");
  afirmar(el.children.length === 0, "el texto debe ser un nodo de texto, no un elemento hijo");
});

prueba("crear(): texto con marcado se trata como texto literal, nunca se parsea como HTML", () => {
  const cargaMaliciosa = "<img src=x onerror=\"window.__pruebaXSS = true\">";
  const el = crear("div", {}, [cargaMaliciosa]);
  afirmar(el.textContent === cargaMaliciosa, "el texto debe conservarse literal");
  afirmar(el.querySelector("img") === null, "no debe crearse ningún elemento a partir del texto");
  afirmar(window.__pruebaXSS === undefined, "el marcado nunca debe ejecutarse");
});

prueba("crear(): atributos booleanos solo se agregan cuando son true", () => {
  const deshabilitado = crear("button", { disabled: true }, "x");
  const habilitado = crear("button", { disabled: false }, "x");
  afirmar(deshabilitado.hasAttribute("disabled") === true);
  afirmar(habilitado.hasAttribute("disabled") === false);
});

prueba("crear(): listeners on* se agregan como addEventListener, no como atributo", () => {
  let clics = 0;
  const boton = crear("button", { onclick: () => (clics += 1) }, "clic");
  afirmar(boton.getAttribute("onclick") === null, "no debe quedar un atributo onclick inline");
  boton.dispatchEvent(new MouseEvent("click"));
  afirmar(clics === 1, "el listener debe ejecutarse");
});

prueba("crear(): hijos Node se anidan tal cual", () => {
  const hijo = crear("span", {}, "adentro");
  const padre = crear("div", {}, [hijo]);
  afirmar(padre.children.length === 1);
  afirmar(padre.firstElementChild === hijo);
});

prueba("crear(): tipos no soportados truenan en vez de colarse silenciosamente", () => {
  let lanzo = false;
  try {
    crear("div", {}, [{ objeto: true }]);
  } catch (error) {
    lanzo = error instanceof TypeError;
  }
  afirmar(lanzo, "debe lanzar TypeError con un hijo no soportado");
});

prueba("limpiar() y reemplazarContenido() no dejan nodos viejos", () => {
  const contenedor = crear("ul", {}, [crear("li", {}, "1"), crear("li", {}, "2")]);
  limpiar(contenedor);
  afirmar(contenedor.childNodes.length === 0);
  reemplazarContenido(contenedor, [crear("li", {}, "solo")]);
  afirmar(contenedor.children.length === 1);
  afirmar(contenedor.textContent === "solo");
});

prueba("texto(): produce un nodo de texto real", () => {
  const nodo = texto("hola");
  afirmar(nodo.nodeType === Node.TEXT_NODE);
  afirmar(nodo.textContent === "hola");
});

// ------------------------------------------------------------------
// api.js — validación y adaptador v1.1 → v1.2
// ------------------------------------------------------------------

function fixtureV11() {
  return {
    version: "1.1",
    generado: "2026-09-18T00:00:00+00:00",
    horizonte: "2027-06",
    capas: {
      demanda: {
        "0900200010025": {
          cve_mun: "002",
          veredicto: "sube",
          delta_pct: 12.4,
          tasa_anual_pct: 1.8,
          ic95: [3.1, 21.7],
          confianza: "alta",
          n_obs: 2,
        },
        "0900200010026": {
          cve_mun: "002",
          veredicto: "se_mantiene",
          delta_pct: 0.4,
          tasa_anual_pct: 0.1,
          ic95: [-3.0, 3.8],
          confianza: "media",
          n_obs: 2,
        },
        "0900200010027": {
          cve_mun: "002",
          veredicto: "baja",
          delta_pct: -17.9,
          tasa_anual_pct: -3.1,
          ic95: [-24.0, -11.6],
          confianza: "baja",
          n_obs: 2,
        },
        "0900200010028": {
          cve_mun: "003",
          veredicto: "sin_datos",
          delta_pct: null,
          tasa_anual_pct: null,
          ic95: null,
          confianza: "baja",
          n_obs: 1,
          motivo_sin_datos: "rural",
        },
        // registro con forma inválida: veredicto fuera del conjunto válido.
        "0900300010099": {
          cve_mun: "003",
          veredicto: "valor_invalido",
          delta_pct: 5,
          confianza: "alta",
          n_obs: 3,
        },
        // registro con confianza fuera del conjunto válido.
        "0900300010100": {
          cve_mun: "003",
          veredicto: "sube",
          delta_pct: 5,
          tasa_anual_pct: 1.5,
          ic95: [1, 9],
          confianza: "extrema",
          n_obs: 3,
        },
      },
      oferta: {
        "0900200010025": { veredicto: "baja", delta_pct: -4.0, confianza: "media", n_obs: 3 },
      },
      // si el backend algún día manda brecha, el adaptador debe ignorarla igual (plan §2).
      brecha: {
        "0900200010025": { veredicto: "sube", delta_pct: 1, confianza: "baja", n_obs: 1 },
      },
    },
  };
}

prueba("validarContrato: rechaza versión distinta de 1.1", () => {
  let lanzo = false;
  try {
    validarContrato({ ...fixtureV11(), version: "1.9" });
  } catch (error) {
    lanzo = error instanceof ErrorDatos && error.codigo === "version_incompatible";
  }
  afirmar(lanzo, "debe lanzar ErrorDatos con codigo version_incompatible");
});

prueba("validarContrato: acepta la versión esperada", () => {
  afirmar(validarContrato(fixtureV11()) === true);
  afirmar(VERSION_CONTRATO_ESPERADA === "1.1");
});

prueba("adaptarV11aV12: horizontes = [{clave:'hU', anios:null, fecha:horizonte}]", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  afirmarIgual(adaptado.horizontes, [{ clave: "hU", anios: null, fecha: "2027-06" }]);
});

prueba("adaptarV11aV12: anida cada registro bajo registro.h.hU sin cambiar sus campos", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  const registro = adaptado.capas.demanda["0900200010025"].h[CLAVE_HORIZONTE_UNICO];
  afirmarIgual(registro.veredicto, "sube");
  afirmarIgual(registro.delta_pct, 12.4);
  afirmarIgual(registro.tasa_anual_pct, 1.8);
  afirmarIgual(registro.ic95, [3.1, 21.7]);
  afirmarIgual(registro.confianza, "alta");
  afirmarIgual(registro.n_obs, 2);
});

prueba("adaptarV11aV12: cubre los 4 veredictos del contrato", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  const h = (clave) => adaptado.capas.demanda[clave].h[CLAVE_HORIZONTE_UNICO];
  afirmarIgual(h("0900200010025").veredicto, "sube");
  afirmarIgual(h("0900200010026").veredicto, "se_mantiene");
  afirmarIgual(h("0900200010027").veredicto, "baja");
  afirmarIgual(h("0900200010028").veredicto, "sin_datos");
});

prueba("adaptarV11aV12: cubre las 3 confianzas del contrato", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  const h = (clave) => adaptado.capas.demanda[clave].h[CLAVE_HORIZONTE_UNICO];
  afirmarIgual(h("0900200010025").confianza, "alta");
  afirmarIgual(h("0900200010026").confianza, "media");
  afirmarIgual(h("0900200010027").confianza, "baja");
});

prueba("adaptarV11aV12: registro con veredicto inválido se degrada a sin_datos, nunca se inventa", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  const registro = adaptado.capas.demanda["0900300010099"].h[CLAVE_HORIZONTE_UNICO];
  afirmarIgual(registro.veredicto, "sin_datos");
  afirmarIgual(registro.delta_pct, null);
});

prueba("adaptarV11aV12: registro con confianza inválida cae a 'baja' sin perder el veredicto", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  const registro = adaptado.capas.demanda["0900300010100"].h[CLAVE_HORIZONTE_UNICO];
  afirmarIgual(registro.veredicto, "sube");
  afirmarIgual(registro.confianza, "baja");
});

prueba("adaptarV11aV12: clave ausente del JSON se resuelve como sin_datos vía obtenerRegistro", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  afirmar(adaptado.capas.demanda["0900999999999"] === undefined, "la clave no debe existir en el objeto crudo");
  const entrada = obtenerRegistro(adaptado, "0900999999999", "demanda");
  afirmarIgual(entrada.h[CLAVE_HORIZONTE_UNICO].veredicto, "sin_datos");
  afirmarIgual(entrada.h[CLAVE_HORIZONTE_UNICO].n_obs, 0);
});

prueba("adaptarV11aV12: NUNCA produce serie, distribucion_ageb, agregado_cdmx ni capas.brecha", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  afirmar(adaptado.serie === undefined, "no debe existir 'serie' en la raíz");
  afirmar(adaptado.distribucion_ageb === undefined, "no debe existir 'distribucion_ageb'");
  afirmar(adaptado.agregado_cdmx === undefined, "no debe existir 'agregado_cdmx'");
  afirmar(adaptado.capas.brecha === undefined, "no debe existir 'capas.brecha' aunque el JSON v1.1 la traiga");
  afirmarIgual(Object.keys(adaptado.capas).sort(), ["demanda", "oferta"]);

  const bruto = JSON.stringify(adaptado);
  afirmar(!bruto.includes('"serie"'), "el JSON serializado no debe mencionar 'serie'");
  afirmar(!bruto.includes('"distribucion_ageb"'), "el JSON serializado no debe mencionar 'distribucion_ageb'");
  afirmar(!bruto.includes('"agregado_cdmx"'), "el JSON serializado no debe mencionar 'agregado_cdmx'");
  afirmar(!bruto.includes('"brecha"'), "el JSON serializado no debe mencionar 'brecha'");

  for (const registro of Object.values(adaptado.capas.demanda)) {
    afirmar(registro.serie === undefined, "ningún registro de demanda debe traer 'serie'");
  }
  for (const registro of Object.values(adaptado.capas.oferta)) {
    afirmar(registro.serie === undefined, "ningún registro de oferta debe traer 'serie'");
  }
});

prueba("adaptarV11aV12: construye índices Map<cvegeo,...> y Map<cve_mun,...> para nivel AGEB", () => {
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  afirmar(adaptado.indices.porCvegeo instanceof Map);
  afirmar(adaptado.indices.porCveMun instanceof Map);
  afirmar(adaptado.indices.porCvegeo.get("0900200010025").demanda.veredicto === "sube");
  afirmar(adaptado.indices.porCveMun.get("002").includes("0900200010025"));
  afirmar(adaptado.indices.porCveMun.get("003").includes("0900200010028"));
});

prueba("adaptarV11aV12: nivel alcaldía indexa por cve_mun", () => {
  const fixtureAlcaldia = {
    version: "1.1",
    generado: "2026-09-18T00:00:00+00:00",
    horizonte: "2027-06",
    capas: {
      demanda: {
        "002": { veredicto: "sube", delta_pct: 5.2, tasa_anual_pct: 1.6, ic95: [-2.7, 9.9], confianza: "baja", n_obs: 2 },
      },
      oferta: {
        "002": { veredicto: "baja", delta_pct: -4.0, confianza: "media", n_obs: 3 },
      },
    },
  };
  const adaptado = adaptarV11aV12(fixtureAlcaldia, NIVEL.ALCALDIA);
  afirmar(adaptado.indices.porCveMun instanceof Map);
  afirmar(adaptado.indices.porCvegeo === undefined, "el nivel alcaldía no debe tener índice por cvegeo");
  afirmarIgual(adaptado.indices.porCveMun.get("002").demanda.veredicto, "sube");
});

// ------------------------------------------------------------------
// api.js — integración contra los mocks reales de F10 (regresión)
// ------------------------------------------------------------------

prueba("integración: prediccion_ageb.json (mock real) valida y adapta sin degradar sus veredictos", async () => {
  const respuesta = await fetch("../mock/prediccion_ageb.json");
  const json = await respuesta.json();
  afirmarIgual(json.version, "1.1");
  const adaptado = adaptarV11aV12(json, NIVEL.AGEB);
  afirmar(Object.keys(adaptado.capas.demanda).length === Object.keys(json.capas.demanda).length);
  afirmar(adaptado.capas.brecha === undefined);
  const veredictos = new Set(Object.values(adaptado.capas.demanda).map((r) => r.h.hU.veredicto));
  afirmar(veredictos.has("sube") && veredictos.has("baja") && veredictos.has("se_mantiene") && veredictos.has("sin_datos"));
});

prueba("integración: prediccion_ageb_v11_invalido.json falla la validación por versión", async () => {
  const respuesta = await fetch("../mock/prediccion_ageb_v11_invalido.json");
  const json = await respuesta.json();
  afirmar(json.version !== VERSION_CONTRATO_ESPERADA, "el fixture debe traer una versión distinta de 1.1");
  let lanzo = false;
  try {
    validarContrato(json);
  } catch (error) {
    lanzo = error instanceof ErrorDatos && error.codigo === "version_incompatible";
  }
  afirmar(lanzo, "validarContrato debe rechazar el archivo de versión inválida");
});

// ------------------------------------------------------------------
// Ejecución + render de resultados (dogfooding de dom.js)
// ------------------------------------------------------------------

async function ejecutarPruebas() {
  const resultados = [];
  for (const { nombre, fn } of pruebas) {
    try {
      // eslint-disable-next-line no-await-in-loop
      await fn();
      resultados.push({ nombre, ok: true });
    } catch (error) {
      resultados.push({ nombre, ok: false, error: error && error.message ? error.message : String(error) });
    }
  }
  return resultados;
}

function pintarResultados(contenedor, resultados) {
  const ok = resultados.filter((r) => r.ok).length;
  const total = resultados.length;

  const lista = crear(
    "ul",
    { clase: "lista-pruebas" },
    resultados.map((r) =>
      crear("li", { clase: r.ok ? "prueba-ok" : "prueba-fallo" }, [
        `${r.ok ? "PASA" : "FALLA"} — ${r.nombre}`,
        r.ok ? null : crear("pre", {}, [r.error]),
      ]),
    ),
  );

  const resumen = crear("p", { clase: "resumen", id: "resumen-pruebas" }, [`${ok} / ${total} pruebas pasan`]);

  reemplazarContenido(contenedor, [resumen, lista]);

  document.body.dataset.pruebasEstado = ok === total ? "ok" : "fallo";
  document.body.dataset.pruebasResumen = `${ok}/${total}`;

  // Resumen accesible para inspección automatizada (Playwright, consola).
  window.__pruebas = { ok, total, resultados };
  if (ok !== total) {
    // eslint-disable-next-line no-console
    console.error("Pruebas fallidas:", resultados.filter((r) => !r.ok));
  }
  // eslint-disable-next-line no-console
  console.log(`[pruebas] ${ok}/${total} pasan`);
}

async function main() {
  const contenedor = document.getElementById("resultados");
  const resultados = await ejecutarPruebas();
  pintarResultados(contenedor, resultados);
}

main();
