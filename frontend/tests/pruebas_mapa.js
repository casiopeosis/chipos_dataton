// frontend/tests/pruebas_mapa.js
//
// Regresión del defecto "AGEB con color uniforme al enfocar una alcaldía"
// (correccion/solucion_agebs.md): `data/reference/ageb_cdmx_simplificado.geojson` trae los
// anillos devanados al revés de lo que exige `d3-geo`, así que cada `<path>` de AGEB terminaba
// con un segundo anillo gigantesco (el recorte de antimeridiano interpretando el polígono como
// "todo el planisferio menos el AGEB"), que tapaba a los demás AGEB pintados antes. Mismo runner
// mínimo sin framework que tests/pruebas_composicion.js.

import { areaPlanaAnillo, anilloConOrientacionCorrecta, repararOrientacionGeometria, repararAgebGeoJSON, montarMapa } from "../js/mapa.js";
import { clasificadorQuintiles, indiceCompuesto } from "../js/composicion.js";
import { ACCIONES, despachar, VISTA } from "../js/estado.js";

const pruebas = [];
function prueba(nombre, fn) {
  pruebas.push({ nombre, fn });
}
function afirmar(condicion, mensaje) {
  if (!condicion) throw new Error(mensaje ?? "afirmación falsa");
}

// Anillo real de un AGEB de Iztapalapa (data/reference/ageb_cdmx_simplificado.geojson,
// CVEGEO 0900700010638), devanado tal cual viene en el archivo: área plana positiva.
const ANILLO_AGEB_MAL_DEVANADO = [
  [-99.00773, 19.37688],
  [-99.01016, 19.37832],
  [-99.01176, 19.37917],
  [-99.0134, 19.37486],
  [-99.01311, 19.3745],
  [-99.0151, 19.37262],
  [-99.01225, 19.37049],
  [-99.01111, 19.36957],
  [-99.01015, 19.3717],
  [-99.00938, 19.37328],
  [-99.00863, 19.37511],
  [-99.00803, 19.3765],
  [-99.00773, 19.37688],
];

// ------------------------------------------------------------------
// areaPlanaAnillo / anilloConOrientacionCorrecta
// ------------------------------------------------------------------

prueba("areaPlanaAnillo: el anillo de ageb_cdmx_simplificado.geojson da área positiva (mal devanado para d3-geo)", () => {
  afirmar(areaPlanaAnillo(ANILLO_AGEB_MAL_DEVANADO) > 0, "el archivo de referencia sigue devanado igual: revisar si ya se corrigió en el pipeline");
});

prueba("anilloConOrientacionCorrecta: invierte un anillo exterior con área positiva", () => {
  const corregido = anilloConOrientacionCorrecta(ANILLO_AGEB_MAL_DEVANADO, true);
  afirmar(areaPlanaAnillo(corregido) < 0, "el anillo exterior corregido debe tener área negativa");
});

prueba("anilloConOrientacionCorrecta: no toca un anillo que ya viene bien devanado (idempotente)", () => {
  const yaCorrecto = ANILLO_AGEB_MAL_DEVANADO.slice().reverse(); // área negativa
  const resultado = anilloConOrientacionCorrecta(yaCorrecto, true);
  afirmar(resultado === yaCorrecto, "no debe reconstruir el arreglo si ya está bien devanado");
});

// ------------------------------------------------------------------
// repararOrientacionGeometria / repararAgebGeoJSON
// ------------------------------------------------------------------

prueba("repararOrientacionGeometria: Polygon con anillo exterior mal devanado queda con área negativa", () => {
  const geometria = { type: "Polygon", coordinates: [ANILLO_AGEB_MAL_DEVANADO] };
  const reparada = repararOrientacionGeometria(geometria);
  afirmar(areaPlanaAnillo(reparada.coordinates[0]) < 0, "anillo exterior corregido");
});

prueba("repararOrientacionGeometria: MultiPolygon corrige cada anillo exterior de cada polígono", () => {
  const geometria = {
    type: "MultiPolygon",
    coordinates: [[ANILLO_AGEB_MAL_DEVANADO], [ANILLO_AGEB_MAL_DEVANADO.slice().reverse()]],
  };
  const reparada = repararOrientacionGeometria(geometria);
  afirmar(areaPlanaAnillo(reparada.coordinates[0][0]) < 0, "primer polígono corregido");
  afirmar(areaPlanaAnillo(reparada.coordinates[1][0]) < 0, "segundo polígono ya venía bien, se conserva");
});

prueba("repararAgebGeoJSON: corrige la colección completa y no muta el objeto original", () => {
  const coleccion = {
    type: "FeatureCollection",
    features: [
      { type: "Feature", properties: { cvegeo: "A" }, geometry: { type: "Polygon", coordinates: [ANILLO_AGEB_MAL_DEVANADO] } },
    ],
  };
  const reparada = repararAgebGeoJSON(coleccion);
  afirmar(areaPlanaAnillo(reparada.features[0].geometry.coordinates[0]) < 0, "la copia reparada queda bien devanada");
  afirmar(areaPlanaAnillo(coleccion.features[0].geometry.coordinates[0]) > 0, "el objeto original (el que carga api.js/fetch) no se muta");
});

prueba("repararAgebGeoJSON: memoiza por referencia (mismo objeto de entrada -> mismo resultado)", () => {
  const coleccion = { type: "FeatureCollection", features: [] };
  afirmar(repararAgebGeoJSON(coleccion) === repararAgebGeoJSON(coleccion), "debe devolver el mismo objeto reparado sin reprocesar");
});

// ------------------------------------------------------------------
// clasificadorQuintiles: empates masivos (correccion/solucion_agebs.md §evidencia) -- el color
// uniforme reportado NO viene de un colapso de percentiles (medido con datos reales: 5 quintiles
// bien repartidos en Iztapalapa), pero la clasificación sigue debiendo degradar con gracia ante
// empates extremos, sin lanzar y sin mezclar sin_datos con el corte más bajo.
// ------------------------------------------------------------------

prueba("clasificadorQuintiles: con 95% de valores empatados en 0, no lanza y separa sin_datos", () => {
  const valores = new Array(100).fill(0);
  valores[0] = NaN;
  valores[50] = 0.9; // único valor distinto
  const clasificar = clasificadorQuintiles(valores);
  afirmar(clasificar(NaN) === "sin_datos", "NaN siempre sin_datos");
  afirmar(clasificar(0.9) >= 1 && clasificar(0.9) <= 5, "el valor distinto cae en algún quintil válido");
  // Con 99 empates en 0 los 4 primeros cortes de percentil valen 0: todo 0 cae en el quintil 1.
  afirmar(clasificar(0) === 1, "el bloque de empates cae en el quintil más bajo, no se reparte");
});

prueba("clasificadorQuintiles: todos los valores son sin_datos (NaN) -> clasificador degrada sin lanzar", () => {
  const clasificar = clasificadorQuintiles(new Array(10).fill(NaN));
  afirmar(clasificar(NaN) === "sin_datos", "sin ningún valor válido, todo es sin_datos");
});

prueba("indiceCompuesto + clasificadorQuintiles: distribución real medida (Iztapalapa) no colapsa (correccion/solucion_agebs.md)", () => {
  // Reproduce a escala pequeña la forma de coberturaProyectada/indiceOportunidad con ceros
  // masivos en una rama (frecuente: `sin_establecimientos`) para confirmar que el compuesto no
  // colapsa aunque UNA rama esté empatada en 0 para casi todas las unidades.
  const n = 50;
  const oEducacion = new Float64Array(n).fill(0.1); // rama empatada
  const oSalud = new Float64Array(n);
  for (let i = 0; i < n; i++) oSalud[i] = i / n; // rama con variación real
  const oComercio = new Float64Array(n).fill(0.5);
  const oVerde = new Float64Array(n).fill(0.5);
  const ic = indiceCompuesto(
    { educacion: oEducacion, salud: oSalud, comercio: oComercio, verde: oVerde },
    { educacion: 3, salud: 3, comercio: 3, verde: 3 },
  );
  const clasificar = clasificadorQuintiles(ic);
  const conteo = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  for (const v of ic) conteo[clasificar(v)]++;
  const quintilesUsados = Object.values(conteo).filter((c) => c > 0).length;
  afirmar(quintilesUsados >= 4, `debe repartirse en al menos 4 de los 5 quintiles, usó ${quintilesUsados}`);
});

// ------------------------------------------------------------------
// Coherencia cvegeo/cve_mun entre el GeoJSON de AGEB y los datos (correccion/frontend_requisitos.md):
// si algún día dejaran de coincidir, `pintarAgebs` filtraría por `cve_mun` un conjunto vacío o
// `claseFeatureAgeb` no encontraría el registro por `cvegeo` -- ambos casos silenciosos (AGEB
// "sin_datos", no un error), así que la única forma de detectarlo es esta comprobación explícita.
// ------------------------------------------------------------------

async function cargarJSON(ruta) {
  const respuesta = await fetch(ruta);
  if (!respuesta.ok) throw new Error(`No se pudo cargar ${ruta}: HTTP ${respuesta.status}`);
  return respuesta.json();
}

prueba("cvegeo/cve_mun: cada AGEB del GeoJSON tiene una clave (y el mismo cve_mun) en el contrato", async () => {
  const [geo, datos] = await Promise.all([
    cargarJSON("../data/ageb_cdmx_simplificado.geojson"),
    cargarJSON("../data/prediccion_ageb.json"),
  ]);
  const demanda = datos.capas.demanda;
  const faltantes = [];
  const cveMunDistinto = [];
  for (const feature of geo.features) {
    const { cvegeo, cve_mun: cveMunGeo } = feature.properties;
    const registro = demanda[cvegeo];
    if (!registro) {
      faltantes.push(cvegeo);
      continue;
    }
    if (registro.cve_mun !== cveMunGeo) cveMunDistinto.push(cvegeo);
  }
  afirmar(faltantes.length === 0, `${faltantes.length} AGEB del GeoJSON sin registro en el contrato: ${faltantes.slice(0, 5).join(", ")}`);
  afirmar(cveMunDistinto.length === 0, `${cveMunDistinto.length} AGEB con cve_mun distinto entre GeoJSON y contrato: ${cveMunDistinto.slice(0, 5).join(", ")}`);
});

prueba("cvegeo/cve_mun: cada clave del contrato tiene geometría en el GeoJSON", async () => {
  const [geo, datos] = await Promise.all([
    cargarJSON("../data/ageb_cdmx_simplificado.geojson"),
    cargarJSON("../data/prediccion_ageb.json"),
  ]);
  const clavesGeo = new Set(geo.features.map((f) => f.properties.cvegeo));
  const faltantes = Object.keys(datos.capas.demanda).filter((clave) => !clavesGeo.has(clave));
  afirmar(faltantes.length === 0, `${faltantes.length} claves del contrato sin geometría: ${faltantes.slice(0, 5).join(", ")}`);
});

// ------------------------------------------------------------------
// pintarAgebs (a través de montarMapa/actualizarAgeb): al enfocar una alcaldía dibuja exactamente
// los AGEB de esa alcaldía, cada uno con SU PROPIA clase de prioridad -- no todos iguales (el
// síntoma reportado). Usa un GeoJSON/registro sintéticos, pequeños y deterministas.
// ------------------------------------------------------------------

prueba("pintarAgebs: dibuja un <path> por AGEB de la alcaldía enfocada, con clases de prioridad distintas", async () => {
  const alcaldiasGeoJSON = {
    type: "FeatureCollection",
    features: [
      { type: "Feature", properties: { cve_alc: "001" }, geometry: { type: "Polygon", coordinates: [[[-99.2, 19.3], [-99.1, 19.3], [-99.1, 19.4], [-99.2, 19.4], [-99.2, 19.3]]] } },
    ],
  };
  // Anillos pequeños, ya bien devanados (área plana negativa), para aislar `pintarAgebs` de la
  // corrección de orientación (probada aparte arriba).
  const cuadro = (cx, cy, r) => [[cx - r, cy + r], [cx - r, cy - r], [cx + r, cy - r], [cx + r, cy + r], [cx - r, cy + r]];
  const agebGeoJSON = {
    type: "FeatureCollection",
    features: [1, 2, 3, 4, 5].map((i) => ({
      type: "Feature",
      properties: { cvegeo: `AGEB-${i}`, cve_mun: "001", ambito: "urbano" },
      geometry: { type: "Polygon", coordinates: [cuadro(-99.15 + i * 0.01, 19.35, 0.003)] },
    })),
  };
  const registrosAgeb = new Map([1, 2, 3, 4, 5].map((i) => [`AGEB-${i}`, { valor: i / 5, quintil: i, tercil: "alta", confianzaBaja: false }]));

  const contenedor = document.createElement("div");
  contenedor.style.width = "400px";
  contenedor.style.height = "300px";
  document.body.appendChild(contenedor);
  try {
    const mapa = montarMapa(contenedor, alcaldiasGeoJSON, new Map(), { agebGeoJSON, registrosAgebPorCvegeo: registrosAgeb });
    despachar({ tipo: ACCIONES.IR_A_ALCALDIA, cve_mun: "001" });
    mapa.actualizarAgeb(agebGeoJSON, registrosAgeb);

    const paths = [...contenedor.querySelectorAll("path.mapa__ageb")];
    afirmar(paths.length === 5, `debe dibujar 5 AGEB, dibujó ${paths.length}`);
    const clasesPrioridad = new Set(
      paths.map((p) => [...p.classList].find((c) => c.startsWith("mapa__alcaldia--prioridad-") || c === "mapa__alcaldia--sin-datos")),
    );
    afirmar(clasesPrioridad.size === 5, `los 5 AGEB deben tener clases de prioridad distintas, hubo ${clasesPrioridad.size} distintas`);

    despachar({ tipo: ACCIONES.VOLVER });
    mapa.destruir();
  } finally {
    despachar({ tipo: ACCIONES.IR_A_CIUDAD });
    contenedor.remove();
  }
});

// ------------------------------------------------------------------
// Runner (mismo patrón que tests/pruebas_composicion.js)
// ------------------------------------------------------------------

async function ejecutar() {
  const resultados = [];
  for (const { nombre, fn } of pruebas) {
    try {
      // eslint-disable-next-line no-await-in-loop
      await fn();
      resultados.push({ nombre, ok: true });
    } catch (error) {
      resultados.push({ nombre, ok: false, error: error.message });
    }
  }

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
