"use strict";

/* ---------------------------------------------------------------------
 * Semáforo de demanda — CDMX
 *
 * Consume dos fuentes estáticas (nada de backend en vivo):
 *   /data/reference/alcaldias.geojson   — 16 polígonos, {cve_alc, nombre}
 *   /output/demanda_alcaldias.json      — estimaciones + IC por dominio
 *
 * Rutas absolutas: se asume que el servidor estático corre desde la raíz
 * del repo (p.ej. `python -m http.server` en chipos_dataton/, abriendo
 * http://localhost:8000/src/app/index.html).
 * ------------------------------------------------------------------- */

const GEOJSON_URL = "/data/reference/alcaldias.geojson";
const DATA_URL = "/output/demanda_alcaldias.json";

const COLORS = {
  alto: "#d1543a",
  medio: "#e3a94f",
  bajo: "#3a9c7c",
  neutral: "#e4e1da",
  ink: "#1c2530",
  strokeIdle: "#b9b3a7",
};

const DOMAIN_META = {
  infancia: {
    label: "Infancia",
    grupo: "0 a 17 años",
    servicio: "guarderías y escuelas de educación inicial y preescolar",
    resumen: "Guarderías y escuelas para la primera infancia frente a la población de 0 a 17 años.",
  },
  adultos_mayores: {
    label: "Adultos mayores",
    grupo: "60 años y más",
    servicio: "asilos y residencias para personas adultas mayores",
    resumen: "Asilos y residencias para personas adultas mayores frente a la población de 60 años y más.",
  },
  cultura: {
    label: "Cultura",
    grupo: "población total",
    servicio: "espacios culturales — teatros, centros culturales y cines",
    resumen: "Teatros, centros culturales y cines frente a la población total de cada alcaldía.",
  },
};

const NIVEL_LABEL = {
  alto: "Demanda alta",
  medio: "En línea con el promedio",
  bajo: "Cobertura por encima del promedio",
};

const state = {
  domain: "infancia",
  data: null, // parsed demanda_alcaldias.json
  geo: null, // parsed geojson
  map: null,
  layer: null, // L.geoJSON layer
  layersByCve: new Map(),
  selectedCve: null,
  ready: false,
};

const fmt1 = (n) => (n === null || n === undefined ? "—" : n.toLocaleString("es-MX", { maximumFractionDigits: 1, minimumFractionDigits: 1 }));
const fmt0 = (n) => (n === null || n === undefined ? "—" : Math.round(n).toLocaleString("es-MX"));
const signed = (n) => (n > 0 ? "+" : "") + fmt1(n);
const establecimientos = (n) => `${fmt0(n)} ${Math.round(Math.abs(n)) === 1 ? "establecimiento" : "establecimientos"}`;

function domainData(domainId) {
  return state.data.dominios[domainId];
}

function alcData(domainId, cve) {
  return domainData(domainId).alcaldias[cve];
}

/* ---------------------------- carga ---------------------------- */

async function loadAll() {
  const [geo, data] = await Promise.all([
    fetch(GEOJSON_URL).then((r) => {
      if (!r.ok) throw new Error(`No se pudo cargar ${GEOJSON_URL} (${r.status})`);
      return r.json();
    }),
    fetch(DATA_URL).then((r) => {
      if (!r.ok) throw new Error(`No se pudo cargar ${DATA_URL} (${r.status})`);
      return r.json();
    }),
  ]);
  state.geo = geo;
  state.data = data;
}

/* ---------------------------- mapa ---------------------------- */

function styleFor(cve) {
  const rec = alcData(state.domain, cve);
  if (!rec) return { color: COLORS.strokeIdle, weight: 1, fillColor: COLORS.neutral, fillOpacity: 0.7 };

  const nivel = rec.nivel;
  const indeterminado = rec.certeza === "indeterminado";
  const fillColor = COLORS[nivel] || COLORS.neutral;

  return {
    color: COLORS.strokeIdle,
    weight: 1,
    fillColor,
    fillOpacity: indeterminado ? 0.55 : 0.85,
    dashArray: indeterminado ? "4 3" : null,
  };
}

function selectedStyle(cve) {
  const base = styleFor(cve);
  return Object.assign({}, base, { color: COLORS.ink, weight: 2.6 });
}

function hoverStyle(cve) {
  const base = styleFor(cve);
  return Object.assign({}, base, { color: COLORS.ink, weight: 1.6 });
}

function initMap() {
  const map = L.map("map", {
    zoomControl: true,
    scrollWheelZoom: false,
    attributionControl: false,
    minZoom: 9,
    maxZoom: 13,
  });
  state.map = map;

  const layer = L.geoJSON(state.geo, {
    style: (feature) => styleFor(feature.properties.cve_alc),
    onEachFeature: (feature, lyr) => {
      const cve = feature.properties.cve_alc;
      const nombre = feature.properties.nombre;
      state.layersByCve.set(cve, lyr);

      lyr.bindTooltip(buildTooltip(cve, nombre), { sticky: true, direction: "top", opacity: 1 });

      lyr.on("mouseover", () => {
        if (state.selectedCve !== cve) lyr.setStyle(hoverStyle(cve));
        lyr.bringToFront();
      });
      lyr.on("mouseout", () => {
        if (state.selectedCve !== cve) lyr.setStyle(styleFor(cve));
      });
      lyr.on("click", () => selectAlcaldia(cve));
    },
  }).addTo(map);

  state.layer = layer;
  map.fitBounds(layer.getBounds(), { padding: [22, 22] });
  map.setMaxBounds(layer.getBounds().pad(0.35));

  const throttledLine = rafThrottle(updateLeaderLine);
  map.on("move zoom resize", throttledLine);
  window.addEventListener("resize", throttledLine);
}

function buildTooltip(cve, nombre) {
  const rec = alcData(state.domain, cve);
  if (!rec) return nombre;
  const meta = DOMAIN_META[state.domain];
  return `<strong>${nombre}</strong><br>${NIVEL_LABEL[rec.nivel]}${rec.certeza === "indeterminado" ? " (no concluyente)" : ""}<br>${signed(rec.estimacion)} por 100k · ${meta.label.toLowerCase()}`;
}

function restyleAll() {
  state.layersByCve.forEach((lyr, cve) => {
    lyr.setStyle(cve === state.selectedCve ? selectedStyle(cve) : styleFor(cve));
    lyr.setTooltipContent(buildTooltip(cve, lyr.feature.properties.nombre));
  });
}

/* ---------------------------- selección / panel ---------------------------- */

function selectAlcaldia(cve) {
  if (state.selectedCve && state.layersByCve.has(state.selectedCve)) {
    state.layersByCve.get(state.selectedCve).setStyle(styleFor(state.selectedCve));
  }
  state.selectedCve = cve;
  const lyr = state.layersByCve.get(cve);
  if (lyr) {
    lyr.setStyle(selectedStyle(cve));
    lyr.bringToFront();
  }
  document.getElementById("alc-select").value = cve;
  renderPanel(cve);
  updateLeaderLine();
}

function clearSelection() {
  if (state.selectedCve && state.layersByCve.has(state.selectedCve)) {
    state.layersByCve.get(state.selectedCve).setStyle(styleFor(state.selectedCve));
  }
  state.selectedCve = null;
  document.getElementById("alc-select").value = "";
  document.getElementById("panel-empty").classList.remove("is-hidden");
  document.getElementById("panel-content").classList.remove("is-visible");
  updateLeaderLine();
}

function frase(rec, meta) {
  const ref = domainData(state.domain).referencia_cdmx;
  const delta = ref.delta;

  if (rec.banderas && rec.banderas.includes("sin_oferta_observada")) {
    return `No se registraron establecimientos de ${meta.servicio} en las ediciones observadas. Frente al promedio de la CDMX, eso implica una brecha estimada de <b>${establecimientos(Math.abs(rec.faltantes.estimacion))}</b> para igualar la cobertura de la ciudad.`;
  }

  if (rec.nivel === "alto") {
    return `La cobertura de ${meta.servicio} está <b>${fmt1(Math.abs(rec.estimacion))} establecimientos por 100 mil habitantes por debajo</b> del promedio de la CDMX — una diferencia estadísticamente distinguible de cero. Igualar la cobertura de la ciudad requeriría del orden de <b>${establecimientos(Math.abs(rec.faltantes.estimacion))}</b> adicionales.`;
  }
  if (rec.nivel === "bajo") {
    return `La cobertura de ${meta.servicio} está <b>${fmt1(Math.abs(rec.estimacion))} establecimientos por 100 mil habitantes por encima</b> del promedio de la CDMX, con evidencia suficiente para distinguirlo. Equivale a un superávit del orden de <b>${establecimientos(Math.abs(rec.faltantes.estimacion))}</b> respecto a la cobertura de referencia.`;
  }
  if (rec.certeza === "concluyente") {
    return `La cobertura de ${meta.servicio} está <b>en línea con el promedio de la CDMX</b> (diferencia estimada de ${signed(rec.estimacion)} por 100 mil habitantes, dentro del margen de ±${fmt1(delta)} que se considera equivalente).`;
  }
  return `Con los datos disponibles <b>no hay evidencia suficiente</b> para determinar si la cobertura de ${meta.servicio} está por encima o por debajo del promedio de la CDMX (intervalo de confianza: ${signed(rec.ic_inf)} a ${signed(rec.ic_sup)} por 100 mil habitantes).`;
}

function renderPanel(cve) {
  const rec = alcData(state.domain, cve);
  const nombre = state.geo.features.find((f) => f.properties.cve_alc === cve).properties.nombre;
  const meta = DOMAIN_META[state.domain];

  document.getElementById("panel-empty").classList.add("is-hidden");
  const content = document.getElementById("panel-content");
  content.classList.add("is-visible");

  const kicker = document.getElementById("panel-kicker");
  kicker.textContent = NIVEL_LABEL[rec.nivel] + (rec.certeza === "indeterminado" ? " · no concluyente" : "");
  kicker.className = "panel-kicker k-" + rec.nivel;

  document.getElementById("panel-title").textContent = nombre;
  document.getElementById("panel-text").innerHTML = frase(rec, meta);
  document.getElementById("ci-chart").innerHTML = ciChartSvg(rec, domainData(state.domain).referencia_cdmx.delta);
  document.getElementById("ci-caption").textContent =
    `Déficit/superávit estimado frente a la CDMX: ${signed(rec.estimacion)} (IC 95%: ${signed(rec.ic_inf)} a ${signed(rec.ic_sup)}, establecimientos por 100 mil habitantes). La banda sombreada marca el margen de ±10% que se considera equivalente al promedio de la ciudad.`;

  const badges = document.getElementById("panel-badges");
  badges.innerHTML = "";
  const badgeTexts = [];
  if (rec.oferta.ic_inf_recortado) badgeTexts.push("límite inferior de oferta recortado a 0");
  if (rec.banderas && rec.banderas.includes("sin_oferta_observada")) badgeTexts.push("sin oferta observada");
  badgeTexts.forEach((t) => {
    const span = document.createElement("span");
    span.className = "badge";
    span.textContent = t;
    badges.appendChild(span);
  });
}

/* ------------------------ mini gráfico de IC (SVG) ------------------------ */

function ciChartSvg(rec, delta) {
  const W = 320, H = 92, PAD = 14;
  const span = Math.max(Math.abs(rec.ic_inf), Math.abs(rec.ic_sup), delta) * 1.25 || 1;
  const x = (v) => PAD + ((v + span) / (2 * span)) * (W - 2 * PAD);
  const color = COLORS[rec.nivel] || COLORS.neutral;

  const zeroX = x(0);
  const deltaLeftX = x(-delta);
  const deltaRightX = x(delta);
  const yMid = 46;

  return `
  <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
    <rect x="${deltaLeftX.toFixed(1)}" y="14" width="${(deltaRightX - deltaLeftX).toFixed(1)}" height="${H - 28}" fill="${COLORS.medio}" opacity="0.14"/>
    <line x1="${zeroX.toFixed(1)}" y1="12" x2="${zeroX.toFixed(1)}" y2="${H - 12}" stroke="${COLORS.strokeIdle}" stroke-width="1"/>
    <line x1="${PAD}" y1="${yMid}" x2="${W - PAD}" y2="${yMid}" stroke="${COLORS.strokeIdle}" stroke-width="1" opacity="0.5"/>
    <line x1="${x(rec.ic_inf).toFixed(1)}" y1="${yMid}" x2="${x(rec.ic_sup).toFixed(1)}" y2="${yMid}" stroke="${color}" stroke-width="3" stroke-linecap="round"/>
    <circle cx="${x(rec.estimacion).toFixed(1)}" cy="${yMid}" r="5.5" fill="${color}"/>
    <text x="${zeroX.toFixed(1)}" y="${H - 2}" font-size="9.5" fill="${COLORS.ink}" text-anchor="middle" opacity="0.6">promedio CDMX</text>
    <text x="${PAD}" y="10" font-size="9.5" fill="${COLORS.ink}" text-anchor="start" opacity="0.6">superávit −</text>
    <text x="${W - PAD}" y="10" font-size="9.5" fill="${COLORS.ink}" text-anchor="end" opacity="0.6">déficit +</text>
  </svg>`;
}

/* ---------------------------- línea guía ---------------------------- */

function updateLeaderLine() {
  const svg = document.getElementById("leader-line");
  const stage = document.querySelector(".stage");
  if (window.innerWidth <= 980 || !state.selectedCve) {
    svg.innerHTML = "";
    return;
  }
  const lyr = state.layersByCve.get(state.selectedCve);
  const mapWrap = document.querySelector(".map-wrap");
  const panel = document.getElementById("panel");
  if (!lyr || !mapWrap || !panel) return;

  const stageRect = stage.getBoundingClientRect();
  const mapRect = mapWrap.getBoundingClientRect();
  const panelRect = panel.getBoundingClientRect();

  const centroid = lyr.getBounds().getCenter();
  const pt = state.map.latLngToContainerPoint(centroid);

  const x1 = mapRect.left - stageRect.left + pt.x;
  const y1 = mapRect.top - stageRect.top + pt.y;
  const x2 = panelRect.left - stageRect.left;
  const y2 = panelRect.top - stageRect.top + 56;

  const midX = (x1 + x2) / 2;

  svg.innerHTML = `<path class="is-visible" d="M ${x1.toFixed(1)} ${y1.toFixed(1)} C ${midX.toFixed(1)} ${y1.toFixed(1)}, ${midX.toFixed(1)} ${y2.toFixed(1)}, ${x2.toFixed(1)} ${y2.toFixed(1)}" />`;
}

function rafThrottle(fn) {
  let scheduled = false;
  return (...args) => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      fn(...args);
    });
  };
}

/* ---------------------------- dominio (tabs) ---------------------------- */

function setDomain(domainId) {
  state.domain = domainId;
  const meta = DOMAIN_META[domainId];

  document.getElementById("domain-title").textContent = meta.label;
  document.getElementById("domain-desc").textContent = meta.resumen;

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.setAttribute("aria-selected", String(btn.dataset.domain === domainId));
  });

  const ref = domainData(domainId).referencia_cdmx;
  document.getElementById("legend-note").textContent =
    `Referencia CDMX: ${fmt1(ref.cobertura_100k)} por 100 mil habitantes del grupo. Zona "en línea" = ±${fmt1(ref.delta)} (10%).`;

  restyleAll();

  if (state.selectedCve) {
    renderPanel(state.selectedCve);
  }
}

/* ---------------------------- selector móvil ---------------------------- */

function populateSelect() {
  const select = document.getElementById("alc-select");
  const names = state.geo.features
    .map((f) => ({ cve: f.properties.cve_alc, nombre: f.properties.nombre }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  names.forEach(({ cve, nombre }) => {
    const opt = document.createElement("option");
    opt.value = cve;
    opt.textContent = nombre;
    select.appendChild(opt);
  });
  select.addEventListener("change", () => {
    if (select.value) selectAlcaldia(select.value);
    else clearSelection();
  });
}

/* ---------------------------- arranque ---------------------------- */

async function main() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => setDomain(btn.dataset.domain));
  });
  document.getElementById("panel-close").addEventListener("click", clearSelection);

  try {
    await loadAll();
  } catch (err) {
    document.getElementById("loading").innerHTML = `<p style="color:${COLORS.alto}">${err.message}</p>`;
    return;
  }

  populateSelect();
  initMap();
  setDomain(state.domain);

  document.getElementById("loading").classList.add("is-done");
  state.ready = true;
}

main();
