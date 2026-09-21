// frontend/tests/pruebas_composicion.js
//
// Pruebas del motor de composición cliente (F16, plans/frontend_specs.md §17.5): oferta cero,
// rama sin dato, invariantes [0,1], independencia de pesos. Mismo runner mínimo sin framework
// que tests/pruebas.js (se ejecutan al cargar tests/index_composicion.html).

import {
  nivelEnHorizonte,
  sumaCeldas,
  tasaAnualImplicita,
  coberturaProyectada,
  rangoPercentilPromediado,
  indiceOportunidad,
  indiceDisponibilidad,
  indiceCompuesto,
  clasificadorTerciles,
  clasificadorQuintiles,
  tercilDeQuintil,
  RAMAS,
} from "../js/composicion.js";
import { FIXTURE_PARIDAD_OPORTUNIDAD } from "./fixtures/paridad_oportunidad.js";

const pruebas = [];
function prueba(nombre, fn) {
  pruebas.push({ nombre, fn });
}
function afirmar(condicion, mensaje) {
  if (!condicion) throw new Error(mensaje ?? "afirmación falsa");
}
function afirmarCercano(actual, esperado, tolerancia, mensaje) {
  afirmar(
    Math.abs(actual - esperado) <= tolerancia,
    `${mensaje ?? "no coincide"}: esperado ${esperado} ± ${tolerancia}, obtuvo ${actual}`,
  );
}

// ------------------------------------------------------------------
// nivelEnHorizonte / sumaCeldas
// ------------------------------------------------------------------

prueba("nivelEnHorizonte: nivel_base nulo (sin_establecimientos) es 0, no NaN", () => {
  const registro = { nivel_base: null, h: { h1: { delta_pct: null } } };
  afirmar(nivelEnHorizonte(registro, "h1") === 0, "debe ser 0");
});

prueba("nivelEnHorizonte: aplica delta_pct sobre nivel_base", () => {
  const registro = { nivel_base: 10, h: { h3: { delta_pct: -20 } } };
  afirmarCercano(nivelEnHorizonte(registro, "h3"), 8, 1e-9);
});

prueba("nivelEnHorizonte: horizonte null (verde) devuelve nivel_base directo", () => {
  const registro = { nivel_base: 5 };
  afirmar(nivelEnHorizonte(registro, null) === 5, "debe ignorar cualquier `h`");
});

prueba("sumaCeldas: suma nivel_base y nivel proyectado de las celdas seleccionadas", () => {
  const celdas = {
    a: { nivel_base: 10, h: { h1: { delta_pct: 10 } } },
    b: { nivel_base: 5, h: { h1: { delta_pct: -10 } } },
    c: { nivel_base: 100, h: { h1: { delta_pct: 50 } } }, // no seleccionada
  };
  const { nivelBase, nivelHorizonte } = sumaCeldas(celdas, ["a", "b"], "h1");
  afirmarCercano(nivelBase, 15, 1e-9);
  afirmarCercano(nivelHorizonte, 11 + 4.5, 1e-6);
});

prueba("sumaCeldas: celda ausente del objeto no rompe (se trata como 0)", () => {
  const celdas = { a: { nivel_base: 10, h: { h1: { delta_pct: 0 } } } };
  const { nivelBase } = sumaCeldas(celdas, ["a", "inexistente"], "h1");
  afirmarCercano(nivelBase, 10, 1e-9);
});

// ------------------------------------------------------------------
// tasaAnualImplicita
// ------------------------------------------------------------------

prueba("tasaAnualImplicita: cero a cero es 0, no NaN ni error", () => {
  afirmar(tasaAnualImplicita(0, 0, 3) === 0, "debe ser 0");
});

prueba("tasaAnualImplicita: crecimiento log-lineal correcto", () => {
  const tasa = tasaAnualImplicita(100, 100 * Math.exp(0.1 * 3), 3);
  afirmarCercano(tasa, 10, 1e-6); // 10 %/año, 3 años.
});

// ------------------------------------------------------------------
// coberturaProyectada — Ŝ=0 con D̂>0 es un valor válido, nunca sin_datos (metodología §10.1)
// ------------------------------------------------------------------

prueba("coberturaProyectada: Ŝ=0 con D̂>0 da 0, no NaN", () => {
  const c = coberturaProyectada(0, 500);
  afirmar(c === 0, `debe ser 0, obtuvo ${c}`);
});

prueba("coberturaProyectada: D̂<=0 da NaN (denominador inválido, nunca se imputa)", () => {
  afirmar(Number.isNaN(coberturaProyectada(10, 0)), "D=0 debe dar NaN");
  afirmar(Number.isNaN(coberturaProyectada(10, -5)), "D<0 debe dar NaN");
});

prueba("coberturaProyectada: fórmula exacta Ŝ/D̂×1000", () => {
  afirmarCercano(coberturaProyectada(3, 1000), 3, 1e-9);
});

// ------------------------------------------------------------------
// rangoPercentilPromediado — empates promediados, NaN se propaga
// ------------------------------------------------------------------

prueba("rangoPercentilPromediado: sin empates, 0 y 1 en los extremos", () => {
  const r = rangoPercentilPromediado([10, 20, 30, 40]);
  afirmarCercano(r[0], 0, 1e-9);
  afirmarCercano(r[3], 1, 1e-9);
  afirmarCercano(r[1], 1 / 3, 1e-9);
});

prueba("rangoPercentilPromediado: empates comparten el rango promedio", () => {
  const r = rangoPercentilPromediado([5, 5, 10]); // rangos 1,2 empatados -> 1.5; 3 -> 3
  afirmarCercano(r[0], (1.5 - 1) / 2, 1e-9);
  afirmarCercano(r[1], (1.5 - 1) / 2, 1e-9);
  afirmarCercano(r[2], 1, 1e-9);
});

prueba("rangoPercentilPromediado: NaN se propaga, no participa del rango de los demás", () => {
  const r = rangoPercentilPromediado([10, NaN, 30]);
  afirmar(Number.isNaN(r[1]), "el NaN de entrada debe seguir NaN");
  afirmarCercano(r[0], 0, 1e-9);
  afirmarCercano(r[2], 1, 1e-9);
});

prueba("rangoPercentilPromediado: un solo valor válido da 0.5", () => {
  const r = rangoPercentilPromediado([NaN, 42, NaN]);
  afirmarCercano(r[1], 0.5, 1e-9);
});

// ------------------------------------------------------------------
// indiceOportunidad — invariantes [0,1], Ŝ=0 nunca sin_datos, ajuste acotado
// ------------------------------------------------------------------

prueba("indiceOportunidad: cobertura 0 (Ŝ=0,D̂>0) produce percentil máximo de oportunidad", () => {
  const coberturas = [0, 10, 20, 30];
  const tasaD = [0, 0, 0, 0];
  const tasaS = [0, 0, 0, 0];
  const o = indiceOportunidad(coberturas, tasaD, tasaS);
  afirmar(o[0] === Math.max(...o), `la cobertura 0 debe dar la mayor oportunidad, obtuvo ${Array.from(o)}`);
  afirmar(!Number.isNaN(o[0]), "nunca debe ser NaN cuando la cobertura es un número válido");
});

prueba("indiceOportunidad: siempre en [0,1] con tasas extremas", () => {
  const coberturas = [0, 5, 50, 500];
  const tasaD = [1000, -1000, 1000, -1000];
  const tasaS = [-1000, 1000, -1000, 1000];
  const o = indiceOportunidad(coberturas, tasaD, tasaS);
  for (const v of o) {
    afirmar(v >= 0 && v <= 1, `O fuera de [0,1]: ${v}`);
  }
});

prueba("indiceOportunidad: NaN en cobertura (D̂ inválido) se propaga a O=NaN", () => {
  const o = indiceOportunidad([10, NaN, 30], [0, 0, 0], [0, 0, 0]);
  afirmar(Number.isNaN(o[1]), "debe ser NaN");
});

prueba("indiceOportunidad: tasaOferta=null (verde) no lanza y no ajusta", () => {
  const coberturas = [0, 10, 20];
  const tasaD = [5, 5, 5];
  const o = indiceOportunidad(coberturas, tasaD, null);
  const rango = rangoPercentilPromediado(coberturas);
  for (let i = 0; i < coberturas.length; i++) {
    afirmarCercano(o[i], 1 - rango[i], 1e-9, "sin tasaOferta, O debe ser solo el término de nivel");
  }
});

// ------------------------------------------------------------------
// Paridad Python↔JS (F-4, correccion/avance_plan.md punto 30.iii): mismos vectores que
// backend/tests/test_features.py::TestParidadIndiceOportunidadPythonJs deben dar el mismo
// resultado en las dos implementaciones de indice_oportunidad/indiceOportunidad.
// ------------------------------------------------------------------

prueba("indiceOportunidad: paridad con features.indice_oportunidad (fixture compartido)", () => {
  const f = FIXTURE_PARIDAD_OPORTUNIDAD;
  const o = indiceOportunidad(f.cobertura, f.tasaDemanda, f.tasaOferta, f.k);
  afirmar(o.length === f.esperado.length, "longitud del resultado no coincide con el fixture");
  for (let i = 0; i < f.esperado.length; i++) {
    if (Number.isNaN(f.esperado[i])) {
      afirmar(Number.isNaN(o[i]), `posición ${i}: se esperaba NaN, se obtuvo ${o[i]}`);
    } else {
      afirmarCercano(o[i], f.esperado[i], 1e-9, `posición ${i} del fixture de paridad`);
    }
  }
});

// ------------------------------------------------------------------
// indiceDisponibilidad — nunca se mezcla con oportunidad, cobertura alta = disponibilidad alta
// ------------------------------------------------------------------

prueba("indiceDisponibilidad: orientación inversa a indiceOportunidad (cobertura alta = F alto)", () => {
  const coberturas = [0, 10, 20, 30];
  const tasaS = [0, 0, 0, 0];
  const confianzas = ["alta", "alta", "alta", "alta"];
  const f = indiceDisponibilidad(coberturas, tasaS, confianzas);
  afirmar(f[3] === Math.max(...f), "la cobertura más alta debe dar la mayor disponibilidad");
});

prueba("indiceDisponibilidad: confianza baja anula el ajuste de estabilidad", () => {
  const coberturas = [10, 20];
  const tasaS = [100, 100]; // tendencia fuerte, saturaría el ajuste con confianza alta
  const fBaja = indiceDisponibilidad(coberturas, tasaS, ["baja", "baja"]);
  const fAlta = indiceDisponibilidad(coberturas, tasaS, ["alta", "alta"]);
  const rango = rangoPercentilPromediado(coberturas);
  afirmarCercano(fBaja[0], rango[0], 1e-9, "confianza baja: ajuste debe ser 0");
  afirmar(fAlta[0] > fBaja[0] - 1e-9, "confianza alta con tendencia positiva no debe ser menor");
});

// ------------------------------------------------------------------
// indiceCompuesto — renormaliza sobre ramas con dato, independencia de pesos sobre O
// ------------------------------------------------------------------

prueba("indiceCompuesto: rama sin_datos se renormaliza, no cuenta como 0", () => {
  const oPorRama = {
    educacion: new Float64Array([0.8]),
    salud: new Float64Array([NaN]), // sin_datos para esta AGEB
    comercio: new Float64Array([0.8]),
    verde: new Float64Array([0.8]),
  };
  const pesos = { educacion: 3, salud: 3, comercio: 3, verde: 3 };
  const ic = indiceCompuesto(oPorRama, pesos);
  afirmarCercano(ic[0], 0.8, 1e-9, "con las 3 ramas restantes iguales, IC debe ser 0.8, no arrastrar la ausente");
});

prueba("indiceCompuesto: todas las ramas sin_datos da NaN (estado 9 del spec §15)", () => {
  const oPorRama = Object.fromEntries(RAMAS.map((r) => [r, new Float64Array([NaN])]));
  const pesos = { educacion: 1, salud: 1, comercio: 1, verde: 1 };
  const ic = indiceCompuesto(oPorRama, pesos);
  afirmar(Number.isNaN(ic[0]), "debe ser NaN");
});

prueba("indiceCompuesto: mover un peso no cambia ningún O_r, solo IC (independencia de pesos)", () => {
  const oPorRama = {
    educacion: new Float64Array([0.2, 0.9]),
    salud: new Float64Array([0.5, 0.5]),
    comercio: new Float64Array([0.3, 0.7]),
    verde: new Float64Array([0.6, 0.1]),
  };
  const snapshot = Object.fromEntries(RAMAS.map((r) => [r, Array.from(oPorRama[r])]));
  indiceCompuesto(oPorRama, { educacion: 5, salud: 1, comercio: 1, verde: 1 });
  indiceCompuesto(oPorRama, { educacion: 1, salud: 5, comercio: 1, verde: 1 });
  for (const r of RAMAS) {
    afirmar(
      JSON.stringify(Array.from(oPorRama[r])) === JSON.stringify(snapshot[r]),
      `indiceCompuesto no debe mutar O_${r}`,
    );
  }
});

prueba("indiceCompuesto: pesos iguales = promedio simple", () => {
  const oPorRama = {
    educacion: new Float64Array([1.0]),
    salud: new Float64Array([0.0]),
    comercio: new Float64Array([0.5]),
    verde: new Float64Array([0.5]),
  };
  const ic = indiceCompuesto(oPorRama, { educacion: 1, salud: 1, comercio: 1, verde: 1 });
  afirmarCercano(ic[0], 0.5, 1e-9);
});

// ------------------------------------------------------------------
// clasificadorTerciles
// ------------------------------------------------------------------

prueba("clasificadorTerciles: terciles correctos sobre 9 valores uniformes", () => {
  const valores = [1, 2, 3, 4, 5, 6, 7, 8, 9];
  const clasificar = clasificadorTerciles(valores);
  afirmar(clasificar(1) === "baja", "el más bajo debe ser baja");
  afirmar(clasificar(9) === "alta", "el más alto debe ser alta");
  afirmar(clasificar(NaN) === "sin_datos", "NaN siempre sin_datos");
});

prueba("clasificadorTerciles: universo vacío nunca lanza, todo sin_datos", () => {
  const clasificar = clasificadorTerciles([]);
  afirmar(clasificar(5) === "sin_datos", "debe ser sin_datos");
});

prueba("clasificadorQuintiles: 10 valores uniformes dan quintiles 1..5 en pares", () => {
  const valores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const clasificar = clasificadorQuintiles(valores);
  afirmar(clasificar(1) === 1, "el más bajo debe ser quintil 1");
  afirmar(clasificar(10) === 5, "el más alto debe ser quintil 5");
});

prueba("tercilDeQuintil: agrupa {1,2}->baja, {3}->media, {4,5}->alta, sin_datos aparte", () => {
  afirmar(tercilDeQuintil(1) === "baja");
  afirmar(tercilDeQuintil(2) === "baja");
  afirmar(tercilDeQuintil(3) === "media");
  afirmar(tercilDeQuintil(4) === "alta");
  afirmar(tercilDeQuintil(5) === "alta");
  afirmar(tercilDeQuintil("sin_datos") === "sin_datos");
});

// ------------------------------------------------------------------
// Rendimiento (spec §16.1): < 80 ms sobre 2453 AGEB
// ------------------------------------------------------------------

prueba("rendimiento: indiceOportunidad + indiceCompuesto sobre 2453 AGEB en < 80 ms", () => {
  const n = 2453;
  const coberturas = new Float64Array(n);
  const tasaD = new Float64Array(n);
  const tasaS = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    coberturas[i] = i % 37 === 0 ? NaN : (i * 977) % 5000;
    tasaD[i] = ((i * 13) % 200) / 10 - 10;
    tasaS[i] = ((i * 29) % 200) / 10 - 10;
  }
  const inicio = performance.now();
  const oPorRama = {};
  for (const rama of RAMAS) {
    oPorRama[rama] = indiceOportunidad(coberturas, tasaD, rama === "verde" ? null : tasaS);
  }
  indiceCompuesto(oPorRama, { educacion: 3, salud: 2, comercio: 4, verde: 1 });
  const duracion = performance.now() - inicio;
  afirmar(duracion < 80, `debe correr en < 80 ms, tomó ${duracion.toFixed(1)} ms`);
});

// ------------------------------------------------------------------
// Runner
// ------------------------------------------------------------------

function ejecutar() {
  const resultados = pruebas.map(({ nombre, fn }) => {
    try {
      fn();
      return { nombre, ok: true };
    } catch (error) {
      return { nombre, ok: false, error: error.message };
    }
  });

  const fallidas = resultados.filter((r) => !r.ok);
  const resumenTexto = `${resultados.length - fallidas.length}/${resultados.length} pruebas OK`;

  const contenedor = document.getElementById("resultados");
  if (contenedor) {
    contenedor.innerHTML = "";
    const resumen = document.createElement("p");
    resumen.className = "resumen";
    resumen.textContent = resumenTexto;
    contenedor.appendChild(resumen);

    const lista = document.createElement("ul");
    lista.className = "lista-pruebas";
    for (const r of resultados) {
      const li = document.createElement("li");
      li.className = r.ok ? "prueba-ok" : "prueba-fallo";
      li.textContent = `${r.ok ? "✓" : "✗"} ${r.nombre}`;
      if (!r.ok) {
        const pre = document.createElement("pre");
        pre.textContent = r.error;
        li.appendChild(pre);
      }
      lista.appendChild(li);
    }
    contenedor.appendChild(lista);
  }

  window.__pruebas = { resumen: resumenTexto, total: resultados.length, fallidas: fallidas.length, resultados };
  // eslint-disable-next-line no-console
  console.log(resumenTexto);
  return resultados;
}

ejecutar();
