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
import { adaptarV11aV12, adaptarV12, validarContrato, obtenerRegistro, ErrorDatos } from "../js/api.js";
import { VERSIONES_CONTRATO_ACEPTADAS, CLAVE_HORIZONTE_UNICO, NIVEL } from "../js/config.js";
import {
  VISTA,
  ESTADO_POR_DEFECTO,
  ACCIONES,
  analizarHash,
  serializarHash,
  reducir,
  despachar,
  suscribir,
  obtenerEstado,
} from "../js/estado.js";
import { capasDesdeAdaptado, montarControlCapas } from "../js/capas.js";
import { textos } from "../js/textos.js";
import {
  ordenarHorizontes,
  indiceHorizonteActivo,
  textoValorHorizonte,
  montarControlHorizonte,
} from "../js/horizonte.js";

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
  afirmarIgual(VERSIONES_CONTRATO_ACEPTADAS, ["1.1", "1.2"]);
});

prueba("validarContrato: acepta v1.2 con fecha_base y horizontes[]", () => {
  const json = {
    version: "1.2",
    generado: "2026-09-18T00:00:00+00:00",
    fecha_base: "2026-06",
    horizontes: [{ clave: "h3", anios: 3, fecha: "2029-06" }],
    capas: { demanda: {}, oferta: {} },
  };
  afirmar(validarContrato(json) === true);
});

prueba("validarContrato: v1.2 sin fecha_base o sin horizontes[] es esquema_invalido", () => {
  const base = {
    version: "1.2",
    capas: { demanda: {}, oferta: {} },
  };
  for (const invalido of [
    { ...base, horizontes: [{ clave: "h3", anios: 3, fecha: "2029-06" }] }, // sin fecha_base
    { ...base, fecha_base: "2026-06", horizontes: [] }, // horizontes vacío
  ]) {
    let lanzo = false;
    try {
      validarContrato(invalido);
    } catch (error) {
      lanzo = error instanceof ErrorDatos && error.codigo === "esquema_invalido";
    }
    afirmar(lanzo, `debe rechazar ${JSON.stringify(invalido)}`);
  }
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
  // Cada valor conserva su `.h` completo (sin aplanar): el aplanado a un horizonte concreto lo
  // hace quien consume los índices (main.js/leyenda.js/mapa.js), no api.js (plan §6).
  afirmar(adaptado.indices.porCvegeo.get("0900200010025").demanda.h[CLAVE_HORIZONTE_UNICO].veredicto === "sube");
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
  afirmarIgual(adaptado.indices.porCveMun.get("002").demanda.h[CLAVE_HORIZONTE_UNICO].veredicto, "sube");
});

// ------------------------------------------------------------------
// api.js — integración contra los mocks reales de F10 (regresión)
// ------------------------------------------------------------------

prueba("integración: prediccion_ageb_v11.json (mock v1.1 real) valida y adapta sin degradar sus veredictos", async () => {
  const respuesta = await fetch("../mock/prediccion_ageb_v11.json");
  const json = await respuesta.json();
  afirmarIgual(json.version, "1.1");
  const adaptado = adaptarV11aV12(json, NIVEL.AGEB);
  afirmar(Object.keys(adaptado.capas.demanda).length === Object.keys(json.capas.demanda).length);
  afirmar(adaptado.capas.brecha === undefined);
  const veredictos = new Set(Object.values(adaptado.capas.demanda).map((r) => r.h.hU.veredicto));
  afirmar(veredictos.has("sube") && veredictos.has("baja") && veredictos.has("se_mantiene") && veredictos.has("sin_datos"));
});

prueba("integración: prediccion_ageb.json (mock v1.2 base) valida y adapta con 3 horizontes", async () => {
  const respuesta = await fetch("../mock/prediccion_ageb.json");
  const json = await respuesta.json();
  afirmarIgual(json.version, "1.2");
  afirmar(typeof json.fecha_base === "string" && json.fecha_base !== "");
  const adaptado = adaptarV12(json, NIVEL.AGEB);
  afirmarIgual(adaptado.horizontes.map((h) => h.clave), ["h3", "h5", "h7"]);
  const primeraClave = Object.keys(adaptado.capas.demanda)[0];
  const registro = adaptado.capas.demanda[primeraClave];
  afirmar(registro.h.h3 !== undefined && registro.h.h5 !== undefined && registro.h.h7 !== undefined);
});

prueba("integración: prediccion_ageb_v11_invalido.json falla la validación por versión", async () => {
  const respuesta = await fetch("../mock/prediccion_ageb_v11_invalido.json");
  const json = await respuesta.json();
  afirmar(
    !VERSIONES_CONTRATO_ACEPTADAS.includes(json.version),
    "el fixture debe traer una versión no aceptada",
  );
  let lanzo = false;
  try {
    validarContrato(json);
  } catch (error) {
    lanzo = error instanceof ErrorDatos && error.codigo === "version_incompatible";
  }
  afirmar(lanzo, "validarContrato debe rechazar el archivo de versión inválida");
});

// ------------------------------------------------------------------
// estado.js — almacén observable + hash de URL (F20)
// ------------------------------------------------------------------

const HASH_EJEMPLO_SPEC =
  "#/alcaldia/007/ageb/0900700011234?capa=oferta&h=hU&orden=cambio&info=1&filtro=baja";

prueba("analizarHash: hash vacío/ausente degrada al estado por defecto (vista ciudad, capa demanda)", () => {
  for (const entrada of [undefined, null, "", "#", "#/"]) {
    const estado = analizarHash(entrada);
    afirmarIgual(estado, ESTADO_POR_DEFECTO, `entrada ${JSON.stringify(entrada)} debe degradar al default`);
  }
});

prueba("analizarHash: parsea el ejemplo del spec (alcaldía + AGEB + todos los parámetros)", () => {
  const estado = analizarHash(HASH_EJEMPLO_SPEC);
  afirmarIgual(estado, {
    vista: VISTA.AGEB,
    cve_mun: "007",
    cvegeo: "0900700011234",
    capa: "oferta",
    horizonte: "hU",
    orden: "cambio",
    drawerAbierto: true,
    filtroLeyenda: "baja",
  });
});

prueba("analizarHash: funciona igual sin el '#' inicial (recarga directa con cualquier hash)", () => {
  const conAlmohadilla = analizarHash(HASH_EJEMPLO_SPEC);
  const sinAlmohadilla = analizarHash(HASH_EJEMPLO_SPEC.slice(1));
  afirmarIgual(sinAlmohadilla, conAlmohadilla);
});

prueba("analizarHash: solo alcaldía (sin AGEB) y sin parámetros opcionales", () => {
  const estado = analizarHash("#/alcaldia/014");
  afirmarIgual(estado.vista, VISTA.ALCALDIA);
  afirmarIgual(estado.cve_mun, "014");
  afirmarIgual(estado.cvegeo, null);
  afirmarIgual(estado.capa, "demanda", "sin ?capa= debe quedar la capa por defecto");
  afirmarIgual(estado.drawerAbierto, false);
  afirmarIgual(estado.filtroLeyenda, null);
});

prueba("analizarHash: cve_mun inválido (no son 3 dígitos) degrada la vista a ciudad, sin lanzar", () => {
  for (const rutaInvalida of ["#/alcaldia/abc", "#/alcaldia/7", "#/alcaldia/00700"]) {
    const estado = analizarHash(rutaInvalida);
    afirmarIgual(estado.vista, VISTA.CIUDAD, `${rutaInvalida} debe degradar a vista ciudad`);
    afirmarIgual(estado.cve_mun, null);
  }
});

prueba("analizarHash: cvegeo inválido se ignora y la vista se queda en alcaldía, sin lanzar", () => {
  const estado = analizarHash("#/alcaldia/007/ageb/no-es-una-clave");
  afirmarIgual(estado.vista, VISTA.ALCALDIA, "una clave de AGEB corrupta no debe tronar el parseo");
  afirmarIgual(estado.cve_mun, "007");
  afirmarIgual(estado.cvegeo, null);
});

prueba("analizarHash: capa y filtro fuera del conjunto válido degradan a sus valores por defecto", () => {
  const estado = analizarHash("#/?capa=brecha&filtro=excelente&h=&orden=");
  afirmarIgual(estado.capa, "demanda");
  afirmarIgual(estado.filtroLeyenda, null);
  afirmarIgual(estado.horizonte, ESTADO_POR_DEFECTO.horizonte);
  afirmarIgual(estado.orden, ESTADO_POR_DEFECTO.orden);
});

prueba("analizarHash: query mal formada (basura tras '?') no lanza y degrada con gracia", () => {
  let estado;
  let lanzo = false;
  try {
    estado = analizarHash("#/alcaldia/007?%%%no-es-query-valida%%%");
  } catch {
    lanzo = true;
  }
  afirmar(!lanzo, "analizarHash nunca debe lanzar, incluso con una query corrupta");
  afirmar(estado.vista === VISTA.ALCALDIA, "la ruta válida debe respetarse aunque la query sea basura");
});

prueba("serializarHash: produce exactamente el formato del spec (orden capa, h, orden, info, filtro)", () => {
  const hash = serializarHash({
    vista: VISTA.AGEB,
    cve_mun: "007",
    cvegeo: "0900700011234",
    capa: "oferta",
    horizonte: "hU",
    orden: "cambio",
    drawerAbierto: true,
    filtroLeyenda: "baja",
  });
  afirmarIgual(hash, HASH_EJEMPLO_SPEC);
});

prueba("serializarHash: omite 'info' y 'filtro' cuando no están activos", () => {
  const hash = serializarHash(ESTADO_POR_DEFECTO);
  afirmar(!hash.includes("info="), "no debe incluir info= con el drawer cerrado");
  afirmar(!hash.includes("filtro="), "no debe incluir filtro= sin filtro activo");
  afirmar(hash.includes("capa=demanda"));
  afirmar(hash.includes("h=hU"));
  afirmar(hash.includes("orden=cambio"));
});

prueba("analizarHash(serializarHash(estado)) es la identidad para varios estados válidos", () => {
  const estados = [
    ESTADO_POR_DEFECTO,
    analizarHash(HASH_EJEMPLO_SPEC),
    { ...ESTADO_POR_DEFECTO, vista: VISTA.ALCALDIA, cve_mun: "014" },
    { ...ESTADO_POR_DEFECTO, capa: "oferta", filtroLeyenda: "sube" },
  ];
  for (const estado of estados) {
    afirmarIgual(analizarHash(serializarHash(estado)), estado, `ida y vuelta rota para ${JSON.stringify(estado)}`);
  }
});

prueba("reducir: acción sin 'tipo' o desconocida no cambia el estado (misma referencia)", () => {
  afirmar(reducir(ESTADO_POR_DEFECTO, undefined) === ESTADO_POR_DEFECTO);
  afirmar(reducir(ESTADO_POR_DEFECTO, {}) === ESTADO_POR_DEFECTO);
  afirmar(reducir(ESTADO_POR_DEFECTO, { tipo: "no_existe" }) === ESTADO_POR_DEFECTO);
});

prueba("reducir: ir_a_alcaldia / ir_a_ageb / volver navegan los tres niveles", () => {
  let estado = ESTADO_POR_DEFECTO;
  estado = reducir(estado, { tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: "007" });
  afirmarIgual(estado.vista, VISTA.ALCALDIA);
  afirmarIgual(estado.cve_mun, "007");

  estado = reducir(estado, { tipo: ACCIONES.IR_A_AGEB, cvegeo: "0900700011234" });
  afirmarIgual(estado.vista, VISTA.AGEB);
  afirmarIgual(estado.cve_mun, "007", "ir_a_ageb hereda el cve_mun del estado si no se pasa uno");
  afirmarIgual(estado.cvegeo, "0900700011234");

  estado = reducir(estado, { tipo: ACCIONES.VOLVER });
  afirmarIgual(estado.vista, VISTA.ALCALDIA, "volver desde AGEB va a alcaldía");
  afirmarIgual(estado.cvegeo, null);

  estado = reducir(estado, { tipo: ACCIONES.VOLVER });
  afirmarIgual(estado.vista, VISTA.CIUDAD, "volver desde alcaldía va a ciudad");
  afirmarIgual(estado.cve_mun, null);

  afirmar(reducir(estado, { tipo: ACCIONES.VOLVER }) === estado, "volver en ciudad no hace nada");
});

prueba("reducir: ir_a_alcaldia/ir_a_ageb con datos inválidos no cambia el estado", () => {
  afirmar(reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: "x" }) === ESTADO_POR_DEFECTO);
  afirmar(reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.IR_A_AGEB, cvegeo: "corta" }) === ESTADO_POR_DEFECTO);
});

prueba("reducir: cambiar_capa/horizonte/orden validan forma y rechazan valores fuera del conjunto", () => {
  afirmarIgual(reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_CAPA, capa: "oferta" }).capa, "oferta");
  afirmar(reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_CAPA, capa: "brecha" }) === ESTADO_POR_DEFECTO);
  afirmarIgual(
    reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_HORIZONTE, horizonte: "h7" }).horizonte,
    "h7",
  );
  afirmar(reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_HORIZONTE, horizonte: "" }) === ESTADO_POR_DEFECTO);
  afirmarIgual(reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_ORDEN, orden: "nombre" }).orden, "nombre");
});

prueba("reducir: abrir_drawer/cerrar_drawer/alternar_drawer", () => {
  const abierto = reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.ABRIR_DRAWER });
  afirmarIgual(abierto.drawerAbierto, true);
  afirmar(reducir(abierto, { tipo: ACCIONES.ABRIR_DRAWER }) === abierto, "abrir ya abierto no crea estado nuevo");
  const cerrado = reducir(abierto, { tipo: ACCIONES.CERRAR_DRAWER });
  afirmarIgual(cerrado.drawerAbierto, false);
  afirmarIgual(reducir(cerrado, { tipo: ACCIONES.ALTERNAR_DRAWER }).drawerAbierto, true);
});

prueba("reducir: cambiar_filtro alterna (pulsar el mismo filtro lo desactiva) y valida veredictos", () => {
  const conFiltro = reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_FILTRO, filtro: "baja" });
  afirmarIgual(conFiltro.filtroLeyenda, "baja");
  const sinFiltro = reducir(conFiltro, { tipo: ACCIONES.CAMBIAR_FILTRO, filtro: "baja" });
  afirmarIgual(sinFiltro.filtroLeyenda, null, "pulsar el mismo filtro activo lo quita");
  afirmar(
    reducir(ESTADO_POR_DEFECTO, { tipo: ACCIONES.CAMBIAR_FILTRO, filtro: "no_es_veredicto" }) === ESTADO_POR_DEFECTO,
  );
});

prueba("despachar/suscribir: el almacén no depende de variables globales (todo vive en el módulo)", () => {
  afirmar(typeof window.estado === "undefined", "estado.js no debe filtrar su estado a window");
  afirmar(typeof window.despachar === "undefined" && typeof window.suscribir === "undefined");
});

prueba("despachar/suscribir: notifica a los suscriptores con el estado actualizado", () => {
  const recibidos = [];
  const cancelar = suscribir((estado) => recibidos.push(estado));
  try {
    despachar({ tipo: ACCIONES.CAMBIAR_CAPA, capa: "oferta" });
    afirmar(recibidos.length === 1, "debe notificar exactamente una vez por cambio de estado real");
    afirmarIgual(recibidos[0].capa, "oferta");
    afirmarIgual(obtenerEstado().capa, "oferta");

    despachar({ tipo: "accion_inexistente" });
    afirmarIgual(recibidos.length, 1, "una acción que no cambia el estado no debe notificar");
  } finally {
    cancelar();
    despachar({ tipo: ACCIONES.CAMBIAR_CAPA, capa: "demanda" }); // deja el almacén como lo encontró
  }
});

prueba("despachar/suscribir: cancelar la suscripción detiene los avisos futuros", () => {
  let veces = 0;
  const cancelar = suscribir(() => (veces += 1));
  despachar({ tipo: ACCIONES.CAMBIAR_ORDEN, orden: "nombre" });
  cancelar();
  despachar({ tipo: ACCIONES.CAMBIAR_ORDEN, orden: "confianza" });
  afirmarIgual(veces, 1);
  despachar({ tipo: ACCIONES.CAMBIAR_ORDEN, orden: "cambio" }); // deja el almacén como lo encontró
});

prueba("despachar: entrar/salir de una alcaldía usa pushState; cambios internos usan replaceState", () => {
  if (typeof window === "undefined" || !window.history) return; // entorno sin DOM real: no aplica
  const largoInicial = window.history.length;

  despachar({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: "009" });
  afirmar(window.location.hash.startsWith("#/alcaldia/009"), "el hash debe reflejar la alcaldía");
  afirmar(window.history.length > largoInicial, "entrar a una alcaldía debe apilar una entrada de historial");

  const largoTrasAlcaldia = window.history.length;
  despachar({ tipo: ACCIONES.CAMBIAR_ORDEN, orden: "nombre" });
  afirmar(window.location.hash.includes("orden=nombre"));
  afirmarIgual(window.history.length, largoTrasAlcaldia, "cambiar el orden no debe apilar historial (replaceState)");

  despachar({ tipo: ACCIONES.VOLVER }); // limpieza: deja el almacén en ciudad de nuevo
  afirmarIgual(obtenerEstado().vista, VISTA.CIUDAD);
});

prueba("despachar: recargar con el hash del spec restaura el estado completo (vía analizarHash)", () => {
  // El almacén inicializa `estadoActual` leyendo `window.location.hash` con la misma función
  // `analizarHash` que aquí se prueba de forma pura: una recarga con cualquier hash válido pasa
  // por la misma ruta de código y produce el mismo resultado.
  const estadoQueTendriaTrasRecargar = analizarHash(HASH_EJEMPLO_SPEC);
  afirmarIgual(estadoQueTendriaTrasRecargar, {
    vista: VISTA.AGEB,
    cve_mun: "007",
    cvegeo: "0900700011234",
    capa: "oferta",
    horizonte: "hU",
    orden: "cambio",
    drawerAbierto: true,
    filtroLeyenda: "baja",
  });
});

// ------------------------------------------------------------------
// capas.js — control segmentado de capas (F60, spec §9)
// ------------------------------------------------------------------

prueba("capasDesdeAdaptado: con el contrato v1.1 real (adaptado), 'oferta' queda fuera del orden visual (Fase 10)", () => {
  // ORDEN_CAPAS de capas.js pasó a ["demanda","brecha"] (Fase 10): "oferta" sigue existiendo en
  // `adaptado.capas` (el adaptador nunca deja de producirla, CAPAS de config.js no cambia), pero
  // capasDesdeAdaptado ya no la incluye en el orden que consume el control visual.
  const adaptado = adaptarV11aV12(fixtureV11(), NIVEL.AGEB);
  afirmar(Object.keys(adaptado.capas).includes("oferta"), "el adaptador sigue produciendo 'oferta'");
  afirmarIgual(capasDesdeAdaptado(adaptado), ["demanda"]);
});

prueba("capasDesdeAdaptado: si el resultado adaptado trajera capas.brecha, se incluye en el orden fijo (oferta no)", () => {
  // Fixture del objeto YA ADAPTADO (no pasa por adaptarV11aV12, que nunca produce brecha, plan §2):
  // demuestra que el control no tiene "demanda" cableada de forma rígida más allá de ORDEN_CAPAS,
  // sino que lee las claves de `capas` de lo que reciba y las cruza con ORDEN_CAPAS.
  const fixtureConBrecha = {
    version: "1.2",
    nivel: "ageb",
    horizontes: [{ clave: "hU", anios: null, fecha: "2027-06" }],
    capas: {
      demanda: {},
      oferta: {},
      brecha: { "0900200010025": { h: { hU: { valor: 3.2 } } } },
    },
  };
  afirmarIgual(capasDesdeAdaptado(fixtureConBrecha), ["demanda", "brecha"]);
});

prueba("capasDesdeAdaptado: solo demanda presente (fixture parcial)", () => {
  afirmarIgual(capasDesdeAdaptado({ capas: { demanda: {} } }), ["demanda"]);
  afirmarIgual(capasDesdeAdaptado(null), []);
  afirmarIgual(capasDesdeAdaptado(undefined), []);
});

// Fase 10 (plan): ORDEN_CAPAS de capas.js pasó de ["demanda","oferta","brecha"] a
// ["demanda","brecha"] — "oferta" ya no aparece en el control visual (sigue siendo válida por
// hash, ver estado.js). Estas pruebas usan "brecha" en vez de "oferta" para seguir ejercitando el
// mecanismo genérico (el control muestra lo que le llega en `capasDisponibles`, filtrado por
// ORDEN_CAPAS) sin depender de una capa que el propio control oculta a propósito.

prueba("montarControlCapas: role=radiogroup con un role=radio (input radio) por capa disponible", () => {
  const contenedor = crear("div");
  montarControlCapas(contenedor, ["demanda", "brecha"]);
  const grupo = contenedor.querySelector('[role="radiogroup"]');
  afirmar(grupo !== null, "debe crear un contenedor role=radiogroup");
  const opciones = contenedor.querySelectorAll('input[type="radio"]');
  afirmarIgual(opciones.length, 2, "una opción por capa disponible");
  afirmarIgual(Array.from(opciones).map((o) => o.dataset.capa), ["demanda", "brecha"]);
});

prueba("montarControlCapas: 'oferta' nunca aparece en el control, aunque esté disponible (Fase 10)", () => {
  const contenedor = crear("div");
  montarControlCapas(contenedor, ["demanda", "oferta", "brecha"]);
  const opciones = contenedor.querySelectorAll('input[type="radio"]');
  afirmarIgual(opciones.length, 2, "brecha se muestra, oferta no");
  const claves = Array.from(opciones).map((o) => o.dataset.capa);
  afirmar(!claves.includes("oferta"), "oferta no debe tener radio en el control");
  const etiquetas = Array.from(contenedor.querySelectorAll(".capas__opcion")).map((e) => e.textContent);
  afirmar(etiquetas.includes(textos.capa.nombre.brecha), "el texto de la opción debe salir de textos.js");
});

prueba("montarControlCapas: todas las opciones comparten el mismo name (navegación nativa por flechas)", () => {
  const contenedor = crear("div");
  montarControlCapas(contenedor, ["demanda", "brecha"]);
  const opciones = Array.from(contenedor.querySelectorAll('input[type="radio"]'));
  const nombres = new Set(opciones.map((o) => o.name));
  afirmarIgual(nombres.size, 1, "un solo 'name' por grupo: así el navegador mueve la selección con las flechas");
});

// "brecha" no es una capa válida para estado.js (CAPAS de config.js = ["demanda","oferta"], sin
// tocar por la Fase 10): el control ya la muestra (spec §9, "aparece si el archivo la trae"),
// pero CAMBIAR_CAPA con capa="brecha" no cambia el estado (esCapaValida la rechaza) — brecha es,
// por ahora, solo lectura hasta que el contrato/estado.js le den un veredicto real. El round-trip
// completo de dispatch/reflejo solo se puede demostrar hoy con "demanda" (la única capa a la vez
// válida en CAPAS y visible en ORDEN_CAPAS); el caso "oferta" (válida en CAPAS pero oculta del
// control desde la Fase 10) se cubre por hash directo en las pruebas de estado.js.

prueba("montarControlCapas: activar la opción 'brecha' despacha CAMBIAR_CAPA, pero estado.js la rechaza (no es una capa válida)", () => {
  const capaOriginal = obtenerEstado().capa;
  try {
    despachar({ tipo: ACCIONES.CAMBIAR_CAPA, capa: "demanda" });
    const contenedor = crear("div");
    montarControlCapas(contenedor, ["demanda", "brecha"]);
    const opcionBrecha = contenedor.querySelector('input[data-capa="brecha"]');
    opcionBrecha.checked = true;
    opcionBrecha.dispatchEvent(new Event("change", { bubbles: true }));
    afirmarIgual(obtenerEstado().capa, "demanda", "esCapaValida debe rechazar 'brecha' y dejar el estado sin cambios");
  } finally {
    despachar({ tipo: ACCIONES.CAMBIAR_CAPA, capa: capaOriginal }); // deja el almacén como lo encontró
  }
});

prueba("montarControlCapas: la opción 'demanda' refleja el estado activo (única capa seleccionable hoy en el control)", () => {
  const capaOriginal = obtenerEstado().capa;
  try {
    despachar({ tipo: ACCIONES.CAMBIAR_CAPA, capa: "demanda" });
    const contenedor = crear("div");
    montarControlCapas(contenedor, ["demanda", "brecha"]);
    const opcionDemanda = contenedor.querySelector('input[data-capa="demanda"]');
    afirmarIgual(opcionDemanda.checked, true);
  } finally {
    despachar({ tipo: ACCIONES.CAMBIAR_CAPA, capa: capaOriginal });
  }
});

prueba("montarControlCapas: nombre de capa consistente con textos.js (fuente única, spec §9)", () => {
  afirmarIgual(textos.capa.nombre.demanda, "Demanda");
  afirmarIgual(textos.capa.nombre.oferta, "Oferta");
  afirmarIgual(textos.capa.nombre.brecha, "Brecha");
});

// ------------------------------------------------------------------
// horizonte.js — control de horizonte (F55, spec §8)
// ------------------------------------------------------------------

const HORIZONTE_UNICO = [{ clave: "hU", anios: null, fecha: "2027-06" }];
const TRES_HORIZONTES = [
  { clave: "h3", anios: 3, fecha: "2029-06" },
  { clave: "h5", anios: 5, fecha: "2031-06" },
  { clave: "h7", anios: 7, fecha: "2033-06" },
];

prueba("ordenarHorizontes: ordena por 'anios' ascendente sin mutar la lista original", () => {
  const desordenada = [TRES_HORIZONTES[2], TRES_HORIZONTES[0], TRES_HORIZONTES[1]];
  const ordenada = ordenarHorizontes(desordenada);
  afirmarIgual(ordenada.map((h) => h.clave), ["h3", "h5", "h7"]);
  afirmarIgual(desordenada.map((h) => h.clave), ["h7", "h3", "h5"], "no debe mutar la lista de entrada");
});

prueba("indiceHorizonteActivo: encuentra el índice de la clave activa, o 0 si no existe", () => {
  const ordenada = ordenarHorizontes(TRES_HORIZONTES);
  afirmarIgual(indiceHorizonteActivo(ordenada, "h5"), 1);
  afirmarIgual(indiceHorizonteActivo(ordenada, "no-existe"), 0);
});

prueba("textoValorHorizonte: '5 años, a mediados de 2031' para una entrada con años", () => {
  const texto5 = textoValorHorizonte({ clave: "h5", anios: 5, fecha: "2031-06" });
  afirmar(texto5.includes("5 años"), `debe mencionar '5 años', obtuvo: ${texto5}`);
  afirmar(texto5.includes("2031"), `debe mencionar el año, obtuvo: ${texto5}`);
});

prueba("textoValorHorizonte: sin 'anios' (horizonte único v1.1) usa la nota de degradación", () => {
  const texto = textoValorHorizonte(HORIZONTE_UNICO[0]);
  afirmar(texto.includes("2027"), `debe mencionar el año del campo horizonte, obtuvo: ${texto}`);
  afirmar(texto.includes("un solo horizonte"), `debe describir la degradación, obtuvo: ${texto}`);
});

prueba("montarControlHorizonte: con un solo horizonte (hU) el control queda disabled con la nota de §8.6", () => {
  const contenedor = crear("div");
  montarControlHorizonte(contenedor, HORIZONTE_UNICO);
  const input = contenedor.querySelector("input[type=range]");
  afirmar(input.disabled === true, "el slider debe quedar disabled con un solo horizonte");
  const nota = contenedor.querySelector(".control-horizonte__nota");
  afirmar(nota.textContent.includes("2027"), `la nota debe mencionar el año, obtuvo: ${nota.textContent}`);
  afirmar(nota.textContent.includes("un solo horizonte"), "la nota debe ser la de §8.6");
  afirmar(
    contenedor.classList.contains("control-horizonte--deshabilitado"),
    "el contenedor debe llevar la clase de deshabilitado",
  );
});

prueba("montarControlHorizonte: con 3 horizontes el slider se habilita y aria-valuetext cambia en cada input", () => {
  const contenedor = crear("div");
  montarControlHorizonte(contenedor, TRES_HORIZONTES, { claveActiva: "h3" });
  const input = contenedor.querySelector("input[type=range]");
  afirmar(input.disabled === false, "con 3 horizontes el slider no debe quedar disabled");
  afirmarIgual(input.min, "0");
  afirmarIgual(input.max, "2");
  afirmarIgual(input.value, "0");
  afirmar(input.getAttribute("aria-valuetext").includes("2029"), "aria-valuetext inicial debe ser h3 (2029)");

  input.value = "2";
  input.dispatchEvent(new Event("input", { bubbles: true }));
  afirmar(
    input.getAttribute("aria-valuetext").includes("2033"),
    `aria-valuetext debe actualizarse en cada input, obtuvo: ${input.getAttribute("aria-valuetext")}`,
  );

  const marcaActiva = contenedor.querySelector(".control-horizonte__marca--activa .control-horizonte__marca-anio");
  afirmar(marcaActiva.textContent === "2033", "la marca activa debe reflejar el índice seleccionado");
});

prueba("montarControlHorizonte: mover el control despacha CAMBIAR_HORIZONTE y nunca llama a fetch", async () => {
  const fetchOriginal = window.fetch;
  let seLlamoFetch = false;
  window.fetch = (...args) => {
    seLlamoFetch = true;
    return fetchOriginal(...args);
  };
  const horizonteOriginal = obtenerEstado().horizonte;
  try {
    const contenedor = crear("div");
    montarControlHorizonte(contenedor, TRES_HORIZONTES, { claveActiva: "h3" });
    const input = contenedor.querySelector("input[type=range]");
    input.value = "1";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    afirmarIgual(obtenerEstado().horizonte, "h5", "change debe despachar CAMBIAR_HORIZONTE con la clave del índice");
    afirmar(!seLlamoFetch, "mover el slider nunca debe disparar una petición de red");
  } finally {
    window.fetch = fetchOriginal;
    despachar({ tipo: ACCIONES.CAMBIAR_HORIZONTE, horizonte: horizonteOriginal }); // deja el almacén como lo encontró
  }
});

prueba("montarControlHorizonte: el botón de una etiqueta fija el valor del slider (táctil, §8.2)", () => {
  const contenedor = crear("div");
  montarControlHorizonte(contenedor, TRES_HORIZONTES, { claveActiva: "h3" });
  const botones = contenedor.querySelectorAll(".control-horizonte__marca");
  afirmarIgual(botones.length, 3);
  botones[2].dispatchEvent(new MouseEvent("click", { bubbles: true }));
  const input = contenedor.querySelector("input[type=range]");
  afirmarIgual(input.value, "2", "pulsar la tercera etiqueta debe fijar el slider en su índice");
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
