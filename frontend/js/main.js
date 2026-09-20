// frontend/js/main.js
//
// Arranque y orquestación (plans/frontend_plan.md §9, F100): carga los datos reales/mock, corre
// el motor de composición cliente (composicion.js) y monta los módulos de la UI sobre los
// contenedores que ya deja `index.html`, reaccionando a `estado.js`.
//
// NOTA DE ALCANCE (Fase 7, en progreso): este archivo ya conecta el pipeline completo de datos ->
// composicion.js -> mapa.js/leyenda.js (la parte más difícil de acertar, spec §17). El panel de
// `#vista-principal` (resumen estructurado Nivel 1 + ranking, plans/frontend_plan.md F45/F50) usa
// por ahora un ranking mínimo inline -- placeholder deliberado hasta que `resumen.js`/`ranking.js`
// existan; se reemplaza sin tocar el resto de este archivo (mismo patrón que ya separa
// mapa/leyenda). `prioridades.js`/`filtros.js`/`poblacion.js`/`busqueda.js`/`riesgo.js`/
// `comparar.js`/`ayuda.js`/`franja.js`/`ficha.js`/`graficas.js`/`interaccion.js`/`presentacion.js`
// aún no están conectados aquí -- ver el commit para el detalle exacto.

import { NIVEL, RAMAS, RAMAS_CON_PROYECCION, HORIZONTES_OFERTA, SEGMENTO_POR_OMISION } from "./config.js";
import { cargarPrediccion, ErrorDatos } from "./api.js";
import { crear, limpiar, reemplazarContenido, texto as nodoTexto } from "./dom.js";
import { textos } from "./textos.js";
import { formatoPorcentaje, formatoEntero } from "./formato.js";
import { obtenerEstado, suscribir, despachar, ACCIONES, VISTA, VISTA_MAPA, BUSQUEDA } from "./estado.js";
import { iniciarCabecera, establecerNombreAlcaldia } from "./cabecera.js";
import { montarVistaMapa } from "./vista_mapa.js";
import { montarControlHorizonte } from "./horizonte.js";
import { montarMapa } from "./mapa.js";
import { montarLeyenda } from "./leyenda.js";
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
} from "./composicion.js";

// Rutas planas bajo frontend/data/, que `make frontend-datos` llena con copias de
// data/reference/ y data/outputs/ (data/ es solo lectura, CLAUDE.md).
const RUTA_ALCALDIAS_GEOJSON = "data/alcaldias.geojson";
const RUTA_AGEB_GEOJSON = "data/ageb_cdmx_simplificado.geojson";

// ---------------------------------------------------------------------------------------------
// Referencias a los contenedores que ya deja index.html.
// ---------------------------------------------------------------------------------------------

const elementoHeader = document.querySelector("body > header");
const vistaPrincipal = document.getElementById("vista-principal");
const mapaHost = document.getElementById("mapa-svg-host");
const leyendaHost = document.getElementById("leyenda");
const horizonteHost = document.getElementById("control-horizonte");
const pieEl = document.getElementById("pie");

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

  const porClave = new Map();
  claves.forEach((clave, i) => {
    const oRama = {};
    for (const rama of RAMAS) oRama[rama] = oPorRama[rama][i];
    porClave.set(clave, {
      valor: valores[i],
      quintil: clasificarQuintil(valores[i]),
      tercil: clasificarTercil(valores[i]),
      confianzaBaja: demandaPorClave.get(clave)?.confianzaBaja ?? false,
      oPorRama: oRama,
    });
  });

  return { claves, porClave, horizonteEntrada };
}

// ---------------------------------------------------------------------------------------------
// Ranking mínimo (placeholder de F50, ver nota de cabecera): lista ordenada por prioridad
// descendente, top 20 (acción_plan.md Fase 6 punto 33), sin FLIP ni acordeón todavía.
// ---------------------------------------------------------------------------------------------

const TOP_N_RANKING = 20;

function pintarVistaPrincipal(composicion, datos, nombresAlcaldia, estado) {
  const filas = composicion.claves
    .map((clave) => ({ clave, ...composicion.porClave.get(clave) }))
    .filter((f) => !Number.isNaN(f.valor))
    .sort((a, b) => b.valor - a.valor)
    .slice(0, TOP_N_RANKING);

  const lista = crear(
    "ol",
    { clase: "ranking-min__lista" },
    filas.map((f) => {
      const cveMun = datos.capas.demanda[f.clave]?.cve_mun;
      const nombre = estado.vista === VISTA.CIUDAD ? (nombresAlcaldia.get(cveMun) ?? cveMun) : f.clave;
      return crear("li", { clase: "ranking-min__fila" }, [
        crear("span", { clase: "ranking-min__nombre" }, [String(nombre)]),
        crear("span", { clase: `ranking-min__tercil ranking-min__tercil--${f.tercil}` }, [
          textos.tercil.palabra[f.tercil] ?? "",
        ]),
        crear("span", { clase: "ranking-min__valor cifras" }, [formatoPorcentaje(f.valor * 100, { decimales: 0 })]),
      ]);
    }),
  );

  const resumenTexto = estado.vista === VISTA.CIUDAD
    ? textos.resumen.tituloGeneral({ poblacion: textos.poblacion.nombre[estado.poblacion], h: composicion.horizonteEntrada?.anios ?? "" })
    : textos.resumen.tituloAlcaldia({
        alcaldia: nombresAlcaldia.get(estado.cve_mun) ?? estado.cve_mun,
        poblacion: textos.poblacion.nombre[estado.poblacion],
        h: composicion.horizonteEntrada?.anios ?? "",
      });

  reemplazarContenido(vistaPrincipal, [
    crear("h2", { clase: "ranking-min__titulo" }, [resumenTexto]),
    crear("p", { clase: "ranking-min__nota" }, [textos.ranking.topN(filas.length)]),
    lista,
  ]);
}

// ---------------------------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------------------------

async function iniciar() {
  let cabecera = null;
  if (elementoHeader) cabecera = iniciarCabecera(elementoHeader);

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

    pintarVistaPrincipal(composicion, datosVista, nombresAlcaldia, estado);
  }

  recalcularYPintar(obtenerEstado());
  suscribir(recalcularYPintar);
}

if (typeof document !== "undefined") {
  iniciar();
}
