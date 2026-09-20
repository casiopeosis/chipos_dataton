// frontend/js/main.js
//
// Arranque y orquestación (plans/frontend_plan.md §9, F100): carga los datos reales/mock, corre
// el motor de composición cliente (composicion.js) y monta los módulos de la UI sobre los
// contenedores que ya deja `index.html`, reaccionando a `estado.js`.
//
// NOTA DE ALCANCE (Fase 7, en progreso): este archivo ya conecta el pipeline completo de datos ->
// composicion.js -> mapa.js/leyenda.js (la parte más difícil de acertar, spec §17), la cabecera,
// la franja/drawer de metodología, el modo presentación, el manejador global de Esc, el resumen
// Nivel 1 + ranking (F45/F50) y el flujo de configuración del escenario (población, búsqueda,
// prioridades, riesgo -- F31/F35). `filtros.js`/`comparar.js`/`ayuda.js`/`ficha.js`/`alcaldia.js`/
// `graficas.js` aún no están conectados aquí.

import { NIVEL, RAMAS, RAMAS_CON_PROYECCION, HORIZONTES_OFERTA, SEGMENTO_POR_OMISION } from "./config.js";
import { cargarPrediccion, ErrorDatos } from "./api.js";
import { crear, limpiar, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { obtenerEstado, suscribir, VISTA, VISTA_MAPA, BUSQUEDA } from "./estado.js";
import { iniciarCabecera, establecerNombreAlcaldia } from "./cabecera.js";
import { montarVistaMapa } from "./vista_mapa.js";
import { montarControlHorizonte } from "./horizonte.js";
import { montarMapa } from "./mapa.js";
import { montarLeyenda } from "./leyenda.js";
import { montarFranja } from "./franja.js";
import { iniciarPresentacion } from "./presentacion.js";
import { iniciarInteraccionGlobal } from "./interaccion.js";
import {
  sumaCeldas,
  tasaAnualImplicita,
  coberturaProyectada,
  indiceOportunidad,
  indiceDisponibilidad,
  indiceCompuesto,
  clasificadorQuintiles,
  clasificadorTerciles,
  tercilDeQuintil,
  rangoPercentilPromediado,
} from "./composicion.js";
import { montarResumen } from "./resumen.js";
import { montarRanking } from "./ranking.js";
import { montarPoblacion } from "./poblacion.js";
import { montarBusqueda } from "./busqueda.js";
import { montarPrioridades } from "./prioridades.js";
import { montarRiesgo, FACTOR_CONFIANZA_RIESGO } from "./riesgo.js";

// Rutas planas bajo frontend/data/, que `make frontend-datos` llena con copias de
// data/reference/ y data/outputs/ (data/ es solo lectura, CLAUDE.md).
const RUTA_ALCALDIAS_GEOJSON = "data/alcaldias.geojson";
const RUTA_AGEB_GEOJSON = "data/ageb_cdmx_simplificado.geojson";

// ---------------------------------------------------------------------------------------------
// Referencias a los contenedores que ya deja index.html.
// ---------------------------------------------------------------------------------------------

const elementoHeader = document.querySelector("body > header");
const panelConfiguracion = document.getElementById("panel-configuracion");
const vistaPrincipal = document.getElementById("vista-principal");
const mapaHost = document.getElementById("mapa-svg-host");
const leyendaHost = document.getElementById("leyenda");
const horizonteHost = document.getElementById("control-horizonte");
const pieEl = document.getElementById("pie");
const franjaEl = document.getElementById("franja-metodologia");
const dialogoEl = document.getElementById("drawer-metodologia");

// ---------------------------------------------------------------------------------------------
// Estados de carga/error (spec §15).
// ---------------------------------------------------------------------------------------------

function pintarCargando() {
  reemplazarContenido(vistaPrincipal, [
    crear("p", { clase: "estado-carga", role: "status" }, [textos.accesibilidad.cargandoPronosticos]),
  ]);
}

function pintarError(error, reintentar) {
  const mensaje = error instanceof ErrorDatos ? error.message : textos.estados.error.mensaje;
  const boton = crear("button", { type: "button", clase: "estado-error__boton", onclick: reintentar }, [
    textos.estados.reintentar,
  ]);
  reemplazarContenido(vistaPrincipal, [
    crear("div", { clase: "estado-error", role: "alert" }, [crear("p", {}, [mensaje]), boton]),
  ]);
}

// ---------------------------------------------------------------------------------------------
// Motor de composición: de los datos adaptados (v1.4) + estado activo a {valor, quintil, tercil,
// confianzaBaja} por clave. Es el único lugar de todo el frontend que llama a composicion.js
// (plans/frontend_plan.md §2: "el día que cambie el contrato, solo se tocan api.js y
// composicion.js" -- y aquí, el único orquestador que los conecta).
// ---------------------------------------------------------------------------------------------

/** Celdas seleccionadas de una rama según el filtro activo (`[]` = todas las celdas reales). */
function celdasSeleccionadas(rama, filtroRama, celdasDisponiblesPorClave) {
  if (Array.isArray(filtroRama) && filtroRama.length > 0) return filtroRama;
  // "Todas": las celdas reales que existan en el propio registro (evita asumir un catálogo fijo
  // aquí, cuando panel.py es la fuente real de qué celdas hay por rama).
  return Object.keys(celdasDisponiblesPorClave ?? {});
}

/**
 * Calcula, para cada clave del índice de demanda (`datos.capas.demanda`), el nivel/tasa
 * combinados de UNA rama bajo el filtro activo, en el horizonte activo (o el nivel estático si es
 * verde). Devuelve `Map<clave, {nivelBase, nivelHorizonte, tasaAnual}>`.
 */
function nivelesPorRama(datos, rama, filtroRama, horizonteActivo, horizonteAnios) {
  const capaRama = datos.capas.ramas[rama] ?? {};
  const esVerde = rama === "verde";
  const resultado = new Map();
  for (const [clave, registro] of Object.entries(capaRama)) {
    const celdas = celdasSeleccionadas(rama, filtroRama, registro.celdas);
    const { nivelBase, nivelHorizonte } = sumaCeldas(registro.celdas ?? {}, celdas, esVerde ? null : horizonteActivo);
    const tasaAnual = esVerde ? null : tasaAnualImplicita(nivelBase, nivelHorizonte, horizonteAnios);
    resultado.set(clave, { nivelBase, nivelHorizonte: esVerde ? nivelBase : nivelHorizonte, tasaAnual });
  }
  return resultado;
}

/**
 * Ejecuta el motor de composición completo sobre `datos` (adaptado v1.4, un nivel territorial) y
 * el estado activo: cobertura + índice de oportunidad/disponibilidad por rama, índice compuesto,
 * y el resultado final por clave (según `busqueda` y `vistaMapa`) con quintil/tercil de color.
 *
 * @returns {{claves: string[], porClave: Map<string, {valor:number, quintil:number|"sin_datos", tercil:string, confianzaBaja:boolean, oPorRama: Record<string, number>}>}}
 */
function calcularComposicion(datos, estado) {
  const claves = Object.keys(datos.capas.demanda);
  const horizonteEntrada = datos.horizontes.find((h) => h.clave === estado.horizonte) ?? datos.horizontes[0];
  const horizonteOferta = HORIZONTES_OFERTA.includes(estado.horizonte) ? estado.horizonte : HORIZONTES_OFERTA[HORIZONTES_OFERTA.length - 1];
  const horizonteOfertaEntrada = datos.horizontes.find((h) => h.clave === horizonteOferta) ?? horizonteEntrada;

  // --- Demanda: nivel/tasa del segmento activo, por clave. ---
  const demandaPorClave = new Map();
  for (const [clave, registro] of Object.entries(datos.capas.demanda)) {
    const seg = registro.segmentos?.[estado.poblacion] ?? registro.segmentos?.[SEGMENTO_POR_OMISION];
    const bloqueH = seg?.h?.[estado.horizonte];
    const nivelBase = seg?.nivel_base ?? null;
    const nivelHorizonte = nivelBase !== null && bloqueH?.delta_pct != null ? nivelBase * (1 + bloqueH.delta_pct / 100) : nivelBase;
    demandaPorClave.set(clave, {
      nivelBase,
      nivelHorizonte,
      tasaAnual: bloqueH?.tasa_anual_pct ?? null,
      confianza: bloqueH?.confianza ?? "baja",
      confianzaBaja: bloqueH?.confianza === "baja",
    });
  }
  const nD = claves.length;
  const nivelDemandaH = new Float64Array(nD);
  const tasaD = new Float64Array(nD);
  claves.forEach((clave, i) => {
    const d = demandaPorClave.get(clave);
    nivelDemandaH[i] = d?.nivelHorizonte ?? NaN;
    tasaD[i] = d?.tasaAnual ?? 0;
  });

  // --- Oferta: cobertura + O/F por rama, bajo el filtro activo. ---
  const oPorRama = {};
  const fPorRama = {};
  for (const rama of RAMAS) {
    const esVerde = rama === "verde";
    const horizonteRama = esVerde ? null : horizonteOferta;
    const anios = esVerde ? null : horizonteOfertaEntrada.anios;
    const niveles = nivelesPorRama(datos, rama, estado.filtros[rama], horizonteRama, anios);

    const nivelOferta = new Float64Array(nD);
    const tasaS = esVerde ? null : new Float64Array(nD);
    claves.forEach((clave, i) => {
      const n = niveles.get(clave);
      nivelOferta[i] = n?.nivelHorizonte ?? 0;
      if (tasaS) tasaS[i] = n?.tasaAnual ?? 0;
    });

    const coberturas = new Float64Array(nD);
    for (let i = 0; i < nD; i++) coberturas[i] = coberturaProyectada(nivelOferta[i], nivelDemandaH[i]);

    oPorRama[rama] = indiceOportunidad(coberturas, tasaD, tasaS);
    fPorRama[rama] = indiceDisponibilidad(coberturas, tasaS, claves.map((clave) => demandaPorClave.get(clave)?.confianza ?? "baja"));
  }

  const ic = indiceCompuesto(oPorRama, estado.pesos);
  const idisp = indiceCompuesto(fPorRama, estado.pesos);

  // --- Resultado final por clave: según vistaMapa (general = compuesto, o una rama) y búsqueda. ---
  const valores = new Float64Array(nD);
  claves.forEach((_, i) => {
    const fuente = estado.busqueda === BUSQUEDA.DISPONIBILIDAD ? idisp : ic;
    const fuenteRama = estado.busqueda === BUSQUEDA.DISPONIBILIDAD ? fPorRama : oPorRama;
    valores[i] = estado.vistaMapa === VISTA_MAPA.GENERAL ? fuente[i] : fuenteRama[estado.vistaMapa][i];
  });

  const clasificarQuintil = clasificadorQuintiles(valores);
  const clasificarTercil = clasificadorTerciles(valores);
  const percentiles = rangoPercentilPromediado(valores);
  // Terciles POR RAMA (§6.4: "mismos terciles de §6.2, aplicados a O_{i,h,r} de esa rama sola"):
  // un clasificador por rama, sobre la distribución completa de esa rama entre las unidades del
  // mismo nivel territorial -- nunca entre las 4 ramas de una sola unidad.
  const clasificarTercilPorRama = {};
  for (const rama of RAMAS) clasificarTercilPorRama[rama] = clasificadorTerciles(oPorRama[rama]);

  const porClave = new Map();
  claves.forEach((clave, i) => {
    const oRama = {};
    const tercilPorRama = {};
    for (const rama of RAMAS) {
      oRama[rama] = oPorRama[rama][i];
      tercilPorRama[rama] = clasificarTercilPorRama[rama](oPorRama[rama][i]);
    }
    const demanda = demandaPorClave.get(clave);
    porClave.set(clave, {
      valor: valores[i],
      quintil: clasificarQuintil(valores[i]),
      tercil: clasificarTercil(valores[i]),
      percentil: percentiles[i],
      confianza: demanda?.confianza ?? "baja",
      confianzaBaja: demanda?.confianzaBaja ?? false,
      // Peso poblacional (nivel de demanda proyectado, segmento activo) para agregados ponderados
      // de §6.3/§6.1 (resumen.js): NaN (AGEB sin_datos) pesa 0, nunca se descarta de la suma.
      pesoPoblacion: Number.isNaN(nivelDemandaH[i]) ? 0 : nivelDemandaH[i],
      oPorRama: oRama,
      tercilPorRama,
    });
  });

  return { claves, porClave, horizonteEntrada };
}

// ---------------------------------------------------------------------------------------------
// Agregación ponderada por población (spec §6.3: "media ponderada de sus AGEB con dato, mismo
// motor de composición"), reutilizada tanto para el resumen de alcaldía como para el de CDMX
// (§6.1, vista general): ninguna réplica de fórmulas de cobertura/oportunidad, solo combina
// resultados YA calculados por `calcularComposicion` con el mismo peso poblacional que usa el
// backend para agregar AGEB en alcaldía (`modelos.agregar_alcaldia`).
// ---------------------------------------------------------------------------------------------

function promedioPonderado(items) {
  let sumaValor = 0;
  let sumaPeso = 0;
  for (const { valor, peso } of items) {
    if (Number.isNaN(valor)) continue;
    const w = Math.max(peso, 0);
    sumaValor += valor * w;
    sumaPeso += w;
  }
  return sumaPeso > 0 ? sumaValor / sumaPeso : NaN;
}

/** Moda ponderada (categoría con mayor peso poblacional acumulado); si todos los pesos son 0, moda simple. */
function modaPonderada(items) {
  const totalPeso = items.reduce((s, { peso }) => s + Math.max(peso, 0), 0);
  const acumulado = new Map();
  for (const { valor, peso } of items) {
    if (valor === null || valor === undefined || valor === "sin_datos") continue;
    const w = totalPeso > 0 ? Math.max(peso, 0) : 1;
    acumulado.set(valor, (acumulado.get(valor) ?? 0) + w);
  }
  let mejor = "sin_datos";
  let mejorPeso = -1;
  for (const [valor, peso] of acumulado) {
    if (peso > mejorPeso) {
      mejor = valor;
      mejorPeso = peso;
    }
  }
  return mejor;
}

/**
 * Resumen agregado (§6.1 CDMX / §6.3 alcaldía) sobre un subconjunto de claves de `composicion`.
 * @returns {{tercil: string, confianza: string, ramasIncidencia: string[], motivos: Array<{rama:string, tercil:string}>}}
 */
function agregarResumen(composicion, claves, pesos) {
  const registros = claves.map((c) => composicion.porClave.get(c)).filter(Boolean);
  const tercil = modaPonderada(registros.map((r) => ({ valor: r.tercil, peso: r.pesoPoblacion })));
  const confianza = modaPonderada(registros.map((r) => ({ valor: r.confianza, peso: r.pesoPoblacion })));

  const promedioPorRama = {};
  for (const rama of RAMAS) {
    promedioPorRama[rama] = promedioPonderado(
      registros.map((r) => ({ valor: r.oPorRama[rama], peso: r.pesoPoblacion })),
    );
  }
  const ramasIncidencia = RAMAS
    .filter((r) => !Number.isNaN(promedioPorRama[r]))
    .sort((a, b) => pesos[b] * promedioPorRama[b] - pesos[a] * promedioPorRama[a])
    .slice(0, 2);
  const motivos = RAMAS
    .filter((r) => !Number.isNaN(promedioPorRama[r]))
    .map((r) => ({
      rama: r,
      tercil: modaPonderada(registros.map((reg) => ({ valor: reg.tercilPorRama[r], peso: reg.pesoPoblacion }))),
    }));

  return { tercil, confianza, ramasIncidencia, motivos };
}

/** Rama con mayor incidencia de una sola fila (ranking.js, columna RAMA PRINCIPAL): mayor `w_r·O_{i,r}`. */
function ramaPrincipalDeFila(oPorRama, pesos) {
  let mejor = null;
  let mejorValor = -Infinity;
  for (const rama of RAMAS) {
    const o = oPorRama[rama];
    if (Number.isNaN(o)) continue;
    const puntaje = pesos[rama] * o;
    if (puntaje > mejorValor) {
      mejorValor = puntaje;
      mejor = rama;
    }
  }
  return mejor;
}

// ---------------------------------------------------------------------------------------------
// Vista principal (F45/F50): resumen estructurado Nivel 1 + ranking, ambos alimentados por la
// misma `composicion` (spec §7.1: "invariante resumen=ranking, misma fuente"). Vista de ficha de
// AGEB (§7.4/F60) aún no existe: en `VISTA.AGEB` se sigue mostrando el resumen/ranking de la
// alcaldía contenedora, degradación explícita hasta que `ficha.js` exista.
// ---------------------------------------------------------------------------------------------

function pintarVistaPrincipal(instancias, composicion, datos, nombresAlcaldia, estado) {
  const enAlcaldia = estado.vista !== VISTA.CIUDAD;
  const clavesAgregado = enAlcaldia
    ? composicion.claves.filter((c) => datos.capas.demanda[c]?.cve_mun === estado.cve_mun)
    : composicion.claves;

  const agregado = agregarResumen(composicion, clavesAgregado, estado.pesos);
  const etiquetaNivel = estado.busqueda === BUSQUEDA.DISPONIBILIDAD
    ? textos.resumen.campo.disponibilidad
    : textos.resumen.campo.oportunidad;
  const poblacionTexto = textos.poblacion.nombre[estado.poblacion];
  const anios = composicion.horizonteEntrada?.anios ?? "";

  instancias.resumen.actualizar({
    titulo: enAlcaldia
      ? textos.resumen.tituloAlcaldia({ alcaldia: nombresAlcaldia.get(estado.cve_mun) ?? estado.cve_mun, poblacion: poblacionTexto, h: anios })
      : textos.resumen.tituloGeneral({ poblacion: poblacionTexto, h: anios }),
    poblacion: poblacionTexto,
    horizonte: textos.horizonte.etiquetaAnios(anios),
    etiquetaNivel,
    tercil: agregado.tercil,
    confianza: agregado.confianza,
    ramasIncidencia: agregado.ramasIncidencia,
    motivos: agregado.motivos,
  });

  // Filtro de nivel de riesgo (§10.12): solo el ranking, nunca el mapa ni el resumen -- "un
  // control aparte... vive junto al ranking". `umbralRiesgo === null` = sin filtrar.
  const clavesFiltradasRiesgo = estado.umbralRiesgo === null
    ? clavesAgregado
    : clavesAgregado.filter((c) => {
        const confianza = composicion.porClave.get(c)?.confianza ?? "baja";
        return (FACTOR_CONFIANZA_RIESGO[confianza] ?? 0) >= estado.umbralRiesgo;
      });

  const filasRanking = clavesFiltradasRiesgo.map((clave) => {
    const registro = composicion.porClave.get(clave);
    const cveMun = datos.capas.demanda[clave]?.cve_mun ?? null;
    return {
      clave,
      nombreZona: enAlcaldia ? clave : (nombresAlcaldia.get(cveMun) ?? cveMun ?? clave),
      nombreAlcaldia: nombresAlcaldia.get(cveMun) ?? cveMun ?? "",
      valor: registro.valor,
      tercil: registro.tercil,
      confianza: registro.confianza,
      ramaPrincipal: ramaPrincipalDeFila(registro.oPorRama, estado.pesos),
      percentil: registro.percentil,
      oPorRama: registro.oPorRama,
    };
  });

  instancias.ranking.actualizar(filasRanking, {
    enAlcaldia,
    cveMun: estado.cve_mun,
    busqueda: estado.busqueda,
  });
}

// ---------------------------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------------------------

async function iniciar() {
  let cabecera = null;
  if (elementoHeader) cabecera = iniciarCabecera(elementoHeader);
  if (cabecera) iniciarPresentacion(cabecera.botonPresentacion);
  iniciarInteraccionGlobal();

  pintarCargando();

  let alcaldiasGeoJSON;
  let agebGeoJSON;
  let datosAlcaldia;
  let datosAgeb;
  try {
    [alcaldiasGeoJSON, agebGeoJSON, datosAlcaldia, datosAgeb] = await Promise.all([
      fetch(RUTA_ALCALDIAS_GEOJSON).then((r) => {
        if (!r.ok) throw new ErrorDatos("No pudimos cargar la geometría de alcaldías.", { codigo: "red" });
        return r.json();
      }),
      fetch(RUTA_AGEB_GEOJSON).then((r) => {
        if (!r.ok) throw new ErrorDatos("No pudimos cargar la geometría de AGEB.", { codigo: "red" });
        return r.json();
      }),
      cargarPrediccion(NIVEL.ALCALDIA),
      cargarPrediccion(NIVEL.AGEB),
    ]);
  } catch (error) {
    pintarError(error, iniciar);
    return;
  }

  const nombresAlcaldia = new Map(
    (alcaldiasGeoJSON.features ?? []).map((f) => [f.properties.cve_alc, f.properties.nombre]),
  );
  for (const [cveMun, nombre] of nombresAlcaldia) establecerNombreAlcaldia(cveMun, nombre);

  if (cabecera) montarVistaMapa(cabecera.contenedorVistaMapa);

  montarInterfaz({ cabecera, alcaldiasGeoJSON, agebGeoJSON, datosAlcaldia, datosAgeb, nombresAlcaldia });
}

function montarInterfaz({ alcaldiasGeoJSON, agebGeoJSON, datosAlcaldia, datosAgeb, nombresAlcaldia }) {
  let instanciaMapa = null;
  let instanciaLeyenda = null;

  if (mapaHost) {
    instanciaMapa = montarMapa(mapaHost, alcaldiasGeoJSON, new Map(), { agebGeoJSON, registrosAgebPorCvegeo: new Map() });
  }
  if (leyendaHost) {
    instanciaLeyenda = montarLeyenda(leyendaHost, { registros: [], nombresAlcaldia });
  }

  limpiar(vistaPrincipal);
  const resumenHost = crear("div", { clase: "vista-principal__resumen" });
  const rankingHost = crear("div", { clase: "vista-principal__ranking" });
  vistaPrincipal.appendChild(resumenHost);
  vistaPrincipal.appendChild(rankingHost);
  const instanciasVistaPrincipal = {
    resumen: montarResumen(resumenHost),
    ranking: montarRanking(rankingHost, []),
  };

  if (panelConfiguracion) {
    limpiar(panelConfiguracion);
    const poblacionHost = crear("div", { clase: "panel-configuracion__poblacion" });
    const busquedaHost = crear("div", { clase: "panel-configuracion__busqueda" });
    const prioridadesHost = crear("div", { clase: "panel-configuracion__prioridades" });
    const riesgoHost = crear("div", { clase: "panel-configuracion__riesgo" });
    panelConfiguracion.appendChild(poblacionHost);
    panelConfiguracion.appendChild(busquedaHost);
    panelConfiguracion.appendChild(prioridadesHost);
    panelConfiguracion.appendChild(riesgoHost);
    montarPoblacion(poblacionHost);
    montarBusqueda(busquedaHost);
    montarPrioridades(prioridadesHost);
    montarRiesgo(riesgoHost);
  }

  const controlHorizonte = horizonteHost
    ? montarControlHorizonte(horizonteHost, datosAlcaldia.horizontes, { claveActiva: obtenerEstado().horizonte })
    : null;

  if (pieEl) {
    reemplazarContenido(pieEl, [
      crear("p", {}, [textos.pie.fuentes]),
      crear("p", {}, [textos.pie.datosGenerados(datosAlcaldia.generado ?? "—")]),
      crear("p", { clase: "pie__advertencia" }, [textos.pie.advertenciaSesgos]),
    ]);
  }

  if (franjaEl && dialogoEl) montarFranja(franjaEl, dialogoEl, { generado: datosAlcaldia.generado ?? null });

  function recalcularYPintar(estado) {
    const enAlcaldia = estado.vista !== VISTA.CIUDAD;
    const datosVista = enAlcaldia ? datosAgeb : datosAlcaldia;
    const composicion = calcularComposicion(datosVista, estado);

    if (enAlcaldia) {
      const clavesAlcaldia = composicion.claves.filter((c) => datosAgeb.capas.demanda[c]?.cve_mun === estado.cve_mun);
      const registrosMapa = new Map(clavesAlcaldia.map((c) => [c, composicion.porClave.get(c)]));
      instanciaMapa?.actualizarAgeb(agebGeoJSON, registrosMapa);
      instanciaLeyenda?.actualizar({
        registros: clavesAlcaldia.map((c) => composicion.porClave.get(c)),
        anio: composicion.horizonteEntrada?.fecha?.slice(0, 4) ?? "",
      });
    } else {
      const registrosMapa = new Map(composicion.claves.map((c) => [c, composicion.porClave.get(c)]));
      instanciaMapa?.actualizarRegistros(registrosMapa);
      instanciaLeyenda?.actualizar({
        registros: composicion.claves.map((c) => composicion.porClave.get(c)),
        anio: composicion.horizonteEntrada?.fecha?.slice(0, 4) ?? "",
      });
    }

    pintarVistaPrincipal(instanciasVistaPrincipal, composicion, datosVista, nombresAlcaldia, estado);
  }

  recalcularYPintar(obtenerEstado());
  suscribir(recalcularYPintar);
}

if (typeof document !== "undefined") {
  iniciar();
}
