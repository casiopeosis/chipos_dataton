// frontend/tests/ejecutar_pruebas_leyenda.js
//
// Runner mínimo (mismo patrón que tests/ejecutar_pruebas_veredictos.js) para
// tests/index_leyenda.html. Deliberadamente separado de tests/pruebas.js (varias tareas en
// progreso en paralelo, ver plan §9): cuando ese archivo esté libre, el orquestador puede hacer
// `pruebas.push(...pruebasLeyenda)` para fusionar ambos runners en uno solo.

import { crear, reemplazarContenido } from "../js/dom.js";
import { pruebasLeyenda } from "./pruebas_leyenda.js";

async function ejecutarPruebas() {
  const resultados = [];
  for (const { nombre, fn } of pruebasLeyenda) {
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

  window.__pruebasLeyenda = { ok, total, resultados };
  if (ok !== total) {
    // eslint-disable-next-line no-console
    console.error("Pruebas fallidas:", resultados.filter((r) => !r.ok));
  }
  // eslint-disable-next-line no-console
  console.log(`[pruebas_leyenda] ${ok}/${total} pasan`);
}

async function main() {
  const contenedor = document.getElementById("resultados");
  const resultados = await ejecutarPruebas();
  pintarResultados(contenedor, resultados);
}

main();
