// frontend/js/main.js
//
// Arranque y orquestación (plans/frontend_plan.md §9, F100): carga los datos reales/mock, monta
// todos los módulos de la UI sobre los contenedores que ya deja `index.html`, y reacciona a
// `estado.js` para intercambiar el contenido de `#vista-principal` (titular+tabla / titular+
// vista de alcaldía / ficha de AGEB) según `estado.vista`. Los demás módulos (mapa, leyenda,
// control de capas, control de horizonte, cabecera, franja) son autocontenidos y se suscriben
// a `estado.js` por su cuenta; aquí solo se montan una vez con los datos ya cargados.

import { NIVEL } from "./config.js";
import { cargarPrediccion, ErrorDatos } from "./api.js";
import { crear, limpiar, reemplazarContenido } from "./dom.js";
import { textos, texto as t } from "./textos.js";
import { obtenerEstado, suscribir, despachar, ACCIONES, VISTA } from "./estado.js";
import { iniciarCabecera, establecerNombreAlcaldia } from "./cabecera.js";
import { montarFranja } from "./franja.js";
import { montarTitular, calcularTitular } from "./titular.js";
import { montarTabla } from "./tabla.js";
import { montarAlcaldia } from "./alcaldia.js";
import { montarFicha } from "./ficha.js";
import { montarControlCapas, capasDesdeAdaptado } from "./capas.js";
import { montarControlHorizonte } from "./horizonte.js";
import { montarMapa } from "./mapa.js";
import { montarLeyenda } from "./leyenda.js";
import { iniciarPresentacion } from "./presentacion.js";
import { iniciarInteraccionGlobal } from "./interaccion.js";

// Igual que config.js#rutaDatos: rutas planas bajo frontend/data/, que `make frontend-datos`
// (F105) llena con copias de data/reference/ y data/outputs/ (data/ es solo lectura, CLAUDE.md).
const RUTA_ALCALDIAS_GEOJSON = "data/alcaldias.geojson";
const RUTA_AGEB_GEOJSON = "data/ageb_cdmx_simplificado.geojson";

// ---------------------------------------------------------------------------------------------
// Referencias a los contenedores que ya deja index.html (F25/F80).
// ---------------------------------------------------------------------------------------------

const elementoHeader = document.querySelector("body > header");
const vistaPrincipal = document.getElementById("vista-principal");
const mapaHost = document.getElementById("mapa-svg-host");
const leyendaHost = document.getElementById("leyenda");
const horizonteHost = document.getElementById("control-horizonte");
const pieEl = document.getElementById("pie");
const franjaEl = document.getElementById("franja-metodologia");
const dialogoEl = document.getElementById("drawer-metodologia");

// ---------------------------------------------------------------------------------------------
// Helpers de datos: de los índices Map de api.js a los objetos "planos" que esperan tabla.js,
// alcaldia.js y ficha.js (cada uno documenta su forma esperada en su propio módulo).
// ---------------------------------------------------------------------------------------------

function registroPlano(entrada, capa, claveHorizonte) {
  return entrada?.[capa]?.h?.[claveHorizonte] ?? null;
}

const REGISTRO_SIN_DATOS = Object.freeze({
  veredicto: "sin_datos",
  delta_pct: null,
  tasa_anual_pct: null,
  ic95: null,
  confianza: "baja",
  n_obs: 0,
});

function listaAlcaldiasParaTabla(datosAlcaldia, capa, nombresAlcaldia, claveHorizonte) {
  const lista = [];
  for (const [cveMun, entrada] of datosAlcaldia.indices.porCveMun) {
    const reg = registroPlano(entrada, capa, claveHorizonte) ?? REGISTRO_SIN_DATOS;
    lista.push({ ...reg, cve_mun: cveMun, nombre: nombresAlcaldia.get(cveMun) ?? cveMun });
  }
  return lista;
}

function mapaCapaAgebPorCvegeo(datosAgeb, capa, claveHorizonte) {
  const mapa = new Map();
  for (const [cvegeo, entrada] of datosAgeb.indices.porCvegeo) {
    mapa.set(cvegeo, registroPlano(entrada, capa, claveHorizonte) ?? REGISTRO_SIN_DATOS);
  }
  return mapa;
}

function listaAgebDeAlcaldia(datosAgeb, cveMun, capa, claveHorizonte) {
  const claves = datosAgeb.indices.porCveMun.get(cveMun) ?? [];
  return claves.map((cvegeo) => {
    const entrada = datosAgeb.indices.porCvegeo.get(cvegeo);
    const reg = registroPlano(entrada, capa, claveHorizonte) ?? REGISTRO_SIN_DATOS;
    return { ...reg, cvegeo };
  });
}

// ---------------------------------------------------------------------------------------------
// Estados de carga/error (spec §15). Los 4 escenarios accesibles vía `?mock=error|v11|vacio|lento`
// se cubren con este único bloque: `cargarPrediccion` ya lanza `ErrorDatos` con el código
// adecuado y ya aplica la demora de `?mock=lento` (js/api.js).
// ---------------------------------------------------------------------------------------------

function pintarCargando() {
  reemplazarContenido(vistaPrincipal, [
    crear("p", { clase: "estado-carga", role: "status" }, [textos.titular.cargandoPronosticos]),
  ]);
}

function pintarError(error, reintentar) {
  const mensaje = error instanceof ErrorDatos ? error.message : textos.estados.error.mensaje;
  const boton = crear("button", { type: "button", clase: "estado-error__boton", onclick: reintentar }, [
    textos.estados.reintentar,
  ]);
  reemplazarContenido(vistaPrincipal, [
    crear("div", { clase: "estado-error", role: "alert" }, [
      crear("p", {}, [mensaje]),
      boton,
    ]),
  ]);
}

// ---------------------------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------------------------

async function iniciar() {
  if (elementoHeader) iniciarCabecera(elementoHeader);
  if (franjaEl && dialogoEl) montarFranja(franjaEl, dialogoEl);
  iniciarPresentacion(document.getElementById("boton-presentacion"));
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

  montarInterfaz({ alcaldiasGeoJSON, agebGeoJSON, datosAlcaldia, datosAgeb, nombresAlcaldia });
}

function montarInterfaz({ alcaldiasGeoJSON, agebGeoJSON, datosAlcaldia, datosAgeb, nombresAlcaldia }) {
  const horizonteInicial = datosAlcaldia.horizontes[0] ?? { clave: "hU", anios: null, fecha: null };

  // El horizonte por defecto de estado.js (`CLAVE_HORIZONTE_UNICO`, "hU") es un valor de
  // arranque para cuando aún no se sabe qué archivo se va a cargar. En cuanto los datos llegan,
  // si esa clave no existe entre los horizontes reales del archivo (p. ej. contrato v1.2 con
  // h3/h5/h7), se reconcilia el estado con el primer horizonte real ANTES de montar mapa.js/
  // leyenda.js/horizonte.js, que leen `obtenerEstado().horizonte` directamente (a diferencia de
  // `horizonteActivo()` más abajo, que ya degrada con gracia solo para tabla/alcaldía/ficha).
  if (!datosAlcaldia.horizontes.some((h) => h.clave === obtenerEstado().horizonte)) {
    despachar({ tipo: ACCIONES.CAMBIAR_HORIZONTE, horizonte: horizonteInicial.clave });
  }

  if (mapaHost) {
    montarMapa(mapaHost, alcaldiasGeoJSON, datosAlcaldia.indices.porCveMun, {
      agebGeoJSON,
      registrosAgebPorCvegeo: datosAgeb.indices.porCvegeo,
    });
  }

  if (leyendaHost) {
    montarLeyenda(leyendaHost, { datosAlcaldia, datosAgeb, nombresAlcaldia });
  }

  if (horizonteHost) {
    montarControlHorizonte(horizonteHost, datosAlcaldia.horizontes, {
      claveActiva: obtenerEstado().horizonte,
    });
  }

  const controlCapasHost = document.getElementById("control-capas");
  if (controlCapasHost) {
    montarControlCapas(controlCapasHost, capasDesdeAdaptado(datosAlcaldia));
    controlCapasHost.dataset.montado = "capas-real";
  }

  if (pieEl) {
    reemplazarContenido(pieEl, [
      crear("p", {}, [textos.pie.fuentes]),
      crear("p", {}, [textos.pie.datosGenerados(datosAlcaldia.generado ?? "—")]),
    ]);
  }

  // -----------------------------------------------------------------------------------------
  // #vista-principal: titular+tabla (ciudad) / titular+vista de alcaldía / ficha de AGEB, según
  // `estado.vista`. Se remonta solo cuando cambia el tipo de vista o la alcaldía/AGEB activos;
  // en cambios de capa/horizonte solo se llama `actualizar()` sobre lo ya montado.
  // -----------------------------------------------------------------------------------------

  let montado = null; // { tipo: "ciudad"|"alcaldia"|"ageb", claveActiva, destruir, ...refs }

  function horizonteActivo(estado) {
    return datosAlcaldia.horizontes.find((h) => h.clave === estado.horizonte) ?? horizonteInicial;
  }

  function renderCiudad(estado) {
    const capa = estado.capa;
    const horizonte = horizonteActivo(estado);
    const claveHorizonte = horizonte.clave;
    const registros = listaAlcaldiasParaTabla(datosAlcaldia, capa, nombresAlcaldia, claveHorizonte);

    if (montado?.tipo !== "ciudad") {
      montado?.destruir?.();
      limpiar(vistaPrincipal);
      const tituloHost = crear("div");
      const tablaHost = crear("div");
      vistaPrincipal.appendChild(tituloHost);
      vistaPrincipal.appendChild(tablaHost);
      const titular = montarTitular(tituloHost);
      const tabla = montarTabla(tablaHost, registros, {
        capa,
        horizonte,
        generadoIso: datosAlcaldia.generado,
        geojsonAgeb: agebGeoJSON,
        registrosAgebPorCvegeo: mapaCapaAgebPorCvegeo(datosAgeb, capa, claveHorizonte),
      });
      montado = { tipo: "ciudad", titular, tabla, destruir: () => tabla.destruir() };
    } else {
      montado.tabla.actualizar(registros, {
        capa,
        horizonte,
        generadoIso: datosAlcaldia.generado,
        registrosAgebPorCvegeo: mapaCapaAgebPorCvegeo(datosAgeb, capa, claveHorizonte),
      });
    }
    montado.titular.actualizar(
      calcularTitular({ capa, vista: "general", registros, horizonte, generadoIso: datosAlcaldia.generado }),
    );
  }

  function renderAlcaldia(estado) {
    const capa = estado.capa;
    const cveMun = estado.cve_mun;
    const horizonte = horizonteActivo(estado);
    const claveHorizonte = horizonte.clave;
    const registrosAgeb = listaAgebDeAlcaldia(datosAgeb, cveMun, capa, claveHorizonte);
    const registroAlcaldia = registroPlano(datosAlcaldia.indices.porCveMun.get(cveMun), capa, claveHorizonte);
    const alcaldiaNombre = nombresAlcaldia.get(cveMun) ?? cveMun;

    if (montado?.tipo !== "alcaldia" || montado.claveActiva !== cveMun) {
      montado?.destruir?.();
      limpiar(vistaPrincipal);
      const tituloHost = crear("div");
      const alcaldiaHostEl = crear("div");
      vistaPrincipal.appendChild(tituloHost);
      vistaPrincipal.appendChild(alcaldiaHostEl);
      const titular = montarTitular(tituloHost);
      const vistaAlcaldia = montarAlcaldia(alcaldiaHostEl, cveMun, registrosAgeb, {
        capa,
        horizonte,
        generadoIso: datosAlcaldia.generado,
        alcaldiaNombre,
        registroAlcaldia,
      });
      montado = { tipo: "alcaldia", claveActiva: cveMun, titular, vistaAlcaldia, destruir: () => vistaAlcaldia.destruir() };
    } else {
      montado.vistaAlcaldia.actualizar(registrosAgeb, {
        capa,
        horizonte,
        generadoIso: datosAlcaldia.generado,
        alcaldiaNombre,
        registroAlcaldia,
      });
    }
    const nSinDatosAgeb = registrosAgeb.filter((r) => r.veredicto === "sin_datos").length;
    montado.titular.actualizar(
      calcularTitular({
        capa,
        vista: "alcaldia",
        registros: registrosAgeb,
        horizonte,
        generadoIso: datosAlcaldia.generado,
        alcaldiaNombre,
        resumenAlcaldia: registroAlcaldia,
        nSinDatosAgeb,
      }),
    );
  }

  function renderAgeb(estado) {
    const capa = estado.capa;
    const cvegeo = estado.cvegeo;
    const horizonte = horizonteActivo(estado);
    const claveHorizonte = horizonte.clave;
    const entrada = datosAgeb.indices.porCvegeo.get(cvegeo);
    const entradaCapa = entrada?.[capa] ?? null;
    const registro = registroPlano(entrada, capa, claveHorizonte) ?? REGISTRO_SIN_DATOS;
    const cveMun = estado.cve_mun ?? entradaCapa?.cve_mun ?? registro.cve_mun;
    const alcaldiaNombre = nombresAlcaldia.get(cveMun) ?? cveMun;
    const feature = (agebGeoJSON.features ?? []).find((f) => f.properties.cvegeo === cvegeo);
    const tipoAgeb = feature?.properties.ambito === "rural" ? "rural" : "urbana";
    // Datos reales para la mini-gráfica (js/graficas.js, ya genérico): con el contrato v1.1
    // (`entradaCapa.serie` siempre ausente) esto degrada solo con `horizontes:[]`, igual que
    // antes; con v1.2 la ficha recibe la serie censal/DENUE y los 3 horizontes con su `.h`.
    const opcionesGrafica = {
      serie: entradaCapa?.serie ?? null,
      nivelBase: typeof entradaCapa?.nivel_base === "number" ? entradaCapa.nivel_base : null,
      horizontes: datosAgeb.horizontes ?? [],
      registrosPorHorizonte: new Map(Object.entries(entradaCapa?.h ?? {})),
      fechaBase: datosAgeb.fecha_base ?? null,
    };

    if (montado?.tipo !== "ageb" || montado.claveActiva !== cvegeo) {
      montado?.destruir?.();
      limpiar(vistaPrincipal);
      const fichaHost = crear("div");
      vistaPrincipal.appendChild(fichaHost);
      const ficha = montarFicha(fichaHost, cvegeo, registro, {
        capa,
        horizonte,
        generadoIso: datosAlcaldia.generado,
        alcaldiaNombre,
        tipoAgeb,
        cveMun,
        ...opcionesGrafica,
      });
      montado = { tipo: "ageb", claveActiva: cvegeo, ficha, destruir: () => ficha.destruir() };
    } else {
      montado.ficha.actualizar(cvegeo, registro, {
        capa,
        horizonte,
        generadoIso: datosAlcaldia.generado,
        alcaldiaNombre,
        tipoAgeb,
        ...opcionesGrafica,
      });
    }
  }

  function render(estado) {
    if (estado.vista === VISTA.ALCALDIA) renderAlcaldia(estado);
    else if (estado.vista === VISTA.AGEB) renderAgeb(estado);
    else renderCiudad(estado);
  }

  render(obtenerEstado());
  suscribir(render);
}

if (typeof document !== "undefined") {
  iniciar();
}
