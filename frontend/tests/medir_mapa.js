// frontend/tests/medir_mapa.js
//
// Script reproducible de medición del cuelgue del mapa (F-6 de correccion/avance_plan.md,
// punto 46). Carga la app real en un <iframe> (mismo servidor, ?mock=1 para no depender de
// data/outputs/ regenerado), recorre las 16 alcaldías haciendo clic en su polígono
// (`path.mapa__alcaldia[data-cve-mun]`, el mismo evento que dispara un usuario real -- no una
// llamada directa a `despachar`, para medir la ruta completa incluida la animación "pop" +
// `flyToBounds`), y usa `PerformanceObserver` sobre entradas `longtask` para registrar cuántas
// tareas largas (>50 ms, definición estándar de `longtask`) produce cada enfoque, cuál es la más
// larga y el total. Objetivo del plan: ninguna tarea > 200 ms.
//
// Uso: abrir frontend/tests/medir_mapa.html desde un servidor (`make serve`), nunca por
// `file://` (el iframe necesita el mismo origen que sirve `index.html` y `data/`).

const RUTA_APP = "../index.html?mock=1";
const UMBRAL_ROJO_MS = 200;
const ESPERA_TRAS_CLIC_MS = 900; // cubre la animación (300 ms entrada + reflow) con margen.
const ESPERA_ENTRE_ALCALDIAS_MS = 250;

async function cargarIframe() {
  const iframe = document.createElement("iframe");
  iframe.src = RUTA_APP;
  iframe.style.width = "1024px";
  iframe.style.height = "768px";
  iframe.style.border = "1px solid #ccc";
  document.getElementById("contenedor-iframe").appendChild(iframe);
  await new Promise((resolve) => {
    iframe.addEventListener("load", resolve, { once: true });
  });
  // Deja que el bundle de módulos (main.js, mapa.js, fetch de datos) termine de montar el mapa.
  await new Promise((resolve) => setTimeout(resolve, 1500));
  return iframe;
}

function instalarObservadorLongtask(ventana) {
  const entradas = [];
  const observador = new ventana.PerformanceObserver((lista) => {
    entradas.push(...lista.getEntries());
  });
  observador.observe({ entryTypes: ["longtask"] });
  return { observador, entradas };
}

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function volverAVistaGeneral(ventanaIframe) {
  const boton = ventanaIframe.document.querySelector('[data-accion="volver"], .ficha__volver, .breadcrumbs__raiz');
  if (boton) {
    boton.dispatchEvent(new ventanaIframe.MouseEvent("click", { bubbles: true }));
    return;
  }
  // Sin botón identificable (p.ej. ya en vista general): Esc, que estado.js también maneja.
  ventanaIframe.document.dispatchEvent(new ventanaIframe.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
}

async function medirAlcaldia(ventanaIframe, cveMun, entradasLongtask) {
  const path = ventanaIframe.document.querySelector(`path.mapa__alcaldia[data-cve-mun="${cveMun}"]`);
  if (!path) {
    return { cveMun, error: "polígono no encontrado en el DOM (data-cve-mun ausente)" };
  }

  const marcaInicio = entradasLongtask.length;
  const t0 = ventanaIframe.performance.now();
  path.dispatchEvent(new ventanaIframe.MouseEvent("click", { bubbles: true, cancelable: true }));
  await esperar(ESPERA_TRAS_CLIC_MS);
  const t1 = ventanaIframe.performance.now();

  const nuevas = entradasLongtask.slice(marcaInicio);
  const duraciones = nuevas.map((e) => e.duration);
  const maxima = duraciones.length ? Math.max(...duraciones) : 0;
  const total = duraciones.reduce((a, b) => a + b, 0);

  await volverAVistaGeneral(ventanaIframe);
  await esperar(ESPERA_ENTRE_ALCALDIAS_MS);

  return {
    cveMun,
    ventanaMedidaMs: Math.round(t1 - t0),
    numeroTareasLargas: nuevas.length,
    maximaMs: Math.round(maxima * 10) / 10,
    totalMs: Math.round(total * 10) / 10,
  };
}

function obtenerAlcaldias(ventanaIframe) {
  const paths = [...ventanaIframe.document.querySelectorAll("path.mapa__alcaldia[data-cve-mun]")];
  const claves = [...new Set(paths.map((p) => p.getAttribute("data-cve-mun")))].sort();
  return claves;
}

function pintarTabla(resultados) {
  const contenedor = document.getElementById("resultados");
  contenedor.innerHTML = "";

  const resumen = document.createElement("p");
  const conError = resultados.filter((r) => r.error);
  const enRojo = resultados.filter((r) => !r.error && r.maximaMs > UMBRAL_ROJO_MS);
  resumen.textContent =
    `${resultados.length} alcaldías medidas · ${enRojo.length} con alguna tarea > ${UMBRAL_ROJO_MS} ms` +
    (conError.length ? ` · ${conError.length} sin medir (error)` : "");
  resumen.className = enRojo.length || conError.length ? "resumen resumen--mal" : "resumen resumen--bien";
  contenedor.appendChild(resumen);

  const tabla = document.createElement("table");
  tabla.innerHTML = `
    <thead>
      <tr>
        <th>cve_mun</th>
        <th>tareas largas</th>
        <th>máxima (ms)</th>
        <th>total (ms)</th>
        <th>ventana medida (ms)</th>
      </tr>
    </thead>`;
  const cuerpo = document.createElement("tbody");
  for (const r of resultados) {
    const fila = document.createElement("tr");
    if (r.error) {
      fila.innerHTML = `<td>${r.cveMun}</td><td colspan="4" class="fila--error">${r.error}</td>`;
    } else {
      const mal = r.maximaMs > UMBRAL_ROJO_MS;
      if (mal) fila.className = "fila--mal";
      fila.innerHTML = `
        <td>${r.cveMun}</td>
        <td>${r.numeroTareasLargas}</td>
        <td>${r.maximaMs}</td>
        <td>${r.totalMs}</td>
        <td>${r.ventanaMedidaMs}</td>`;
    }
    cuerpo.appendChild(fila);
  }
  tabla.appendChild(cuerpo);
  contenedor.appendChild(tabla);

  window.__medicionMapa = { resultados, umbralRojoMs: UMBRAL_ROJO_MS };
}

async function ejecutar() {
  document.getElementById("estado").textContent = "Cargando la app en un iframe…";
  const iframe = await cargarIframe();
  const ventanaIframe = iframe.contentWindow;

  const { entradas } = instalarObservadorLongtask(ventanaIframe);
  const claves = obtenerAlcaldias(ventanaIframe);

  if (claves.length === 0) {
    document.getElementById("estado").textContent =
      "No se encontraron polígonos de alcaldía (¿el mapa cargó? revisa la consola del iframe).";
    return;
  }

  document.getElementById("estado").textContent = `Midiendo ${claves.length} alcaldías…`;
  const resultados = [];
  for (const cveMun of claves) {
    resultados.push(await medirAlcaldia(ventanaIframe, cveMun, entradas));
  }

  document.getElementById("estado").textContent = `Listo (${claves.length} alcaldías).`;
  pintarTabla(resultados);
}

ejecutar();
