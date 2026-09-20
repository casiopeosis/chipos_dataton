// frontend/js/resumen.js
//
// Resumen estructurado Nivel 1 (plans/frontend_specs.md §6, plan F45). Sustituye por completo al
// "titular dinámico" de la versión anterior: lista de campos etiquetados (`<dl>`), nunca una frase
// autogenerada (`correccion/frontend_requisitos.md` §1, §13).
//
// Este módulo es autocontenido (plan §9): `montarResumen(contenedor)` no lee `estado.js` ni hace
// `fetch`; recibe ya calculados los campos de §6.1/§6.3/§6.4 (misma fuente que `ranking.js`, el
// motor de `composicion.js` orquestado en `main.js`) y solo pinta. Despacha
// `ACCIONES.ABRIR_DRAWER` al pulsar "Entender esta zona" -- hasta que exista un Nivel 2 propio por
// zona (F86/F60, aún no construidos), reutiliza el único drawer disponible (metodología).

import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { despachar as despacharEstado, ACCIONES } from "./estado.js";

const DURACION_CROSSFADE_MS = 120;

function prefiereMovimientoReducido() {
  return (
    typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Una fila `<dt>/<dd>` del `<dl>` de campos (spec §6.1: "nunca texto libre"). */
function crearFila(etiqueta, valorNodo) {
  return [
    crear("dt", { clase: "resumen__etiqueta" }, [etiqueta]),
    crear("dd", { clase: "resumen__valor" }, [valorNodo]),
  ];
}

function crearValorTercil(tercil) {
  return crear("span", { clase: `resumen__tercil resumen__tercil--${tercil}` }, [
    `${textos.tercil.simbolo[tercil] ?? textos.tercil.simbolo.sin_datos} ${textos.tercil.palabra[tercil] ?? textos.tercil.palabra.sin_datos}`,
  ]);
}

function crearValorConfianza(confianza) {
  return crear("span", { clase: "resumen__confianza" }, [
    `${textos.confianza.simbolo[confianza] ?? "○"} ${textos.confianza.palabra[confianza] ?? textos.confianza.palabra.baja}`,
  ]);
}

/** Lista de ramas con mayor incidencia (spec §6.1: "1-2 ramas con mayor w_r·O_{i,h,r}"). */
function crearValorRamasIncidencia(ramas) {
  if (!Array.isArray(ramas) || ramas.length === 0) {
    return crear("span", { clase: "resumen__sin-ramas" }, [textos.resumen.sinRamas]);
  }
  return crear("span", {}, [ramas.map((r) => textos.rama.nombre[r] ?? r).join(" / ")]);
}

/** §6.4: "{rama}: disponibilidad relativa {tercil}" (o "oportunidad", según la búsqueda activa), una línea por rama. */
function crearMotivos(motivos, etiquetaNivel) {
  const lista = crear(
    "ul",
    { clase: "resumen__motivos" },
    motivos.map((m) => crear("li", { clase: "resumen__motivo" }, [
      `${textos.rama.nombre[m.rama] ?? m.rama}: ${etiquetaNivel.toLowerCase()} ${textos.tercil.palabra[m.tercil]?.toLowerCase() ?? textos.tercil.palabra.sin_datos.toLowerCase()}`,
    ])),
  );
  return lista;
}

/**
 * Monta el resumen estructurado Nivel 1 dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @param {{despachar?: (accion: object) => void}} [opciones]
 * @returns {{actualizar: (datos: object) => void, destruir: () => void}}
 */
export function montarResumen(contenedor, opciones = {}) {
  if (!contenedor) throw new TypeError("montarResumen(contenedor): se requiere un contenedor");

  const despachar = typeof opciones.despachar === "function" ? opciones.despachar : despacharEstado;

  const raiz = crear("section", { clase: "resumen-nivel1", "aria-labelledby": "resumen-titulo" });
  const titulo = crear("h2", { id: "resumen-titulo", clase: "resumen__titulo" });
  const dl = crear("dl", { clase: "resumen__campos" });
  const motivosSeccion = crear("section", { clase: "resumen__motivos-seccion" }, [
    crear("h3", { clase: "resumen__motivos-titulo" }, []),
  ]);
  const botonEntender = crear(
    "button",
    {
      type: "button",
      clase: "resumen__entender",
      onclick: () => despachar({ tipo: ACCIONES.ABRIR_DRAWER }),
    },
    [textos.navegacion.entenderZona],
  );

  raiz.appendChild(titulo);
  raiz.appendChild(dl);
  raiz.appendChild(motivosSeccion);
  raiz.appendChild(botonEntender);
  contenedor.appendChild(raiz);

  /**
   * @param {{
   *   titulo: string,
   *   zona: string,
   *   poblacion: string,
   *   horizonte: string,
   *   busqueda: string,
   *   etiquetaNivel: string,
   *   tercil: "alta"|"media"|"baja"|"sin_datos",
   *   confianza: "alta"|"media"|"baja",
   *   ramasIncidencia: string[],
   *   motivos: Array<{rama: string, tercil: string}>,
   * }} datos
   */
  function actualizar(datos) {
    const crossfade = !prefiereMovimientoReducido();

    reemplazarContenido(titulo, [datos.titulo]);

    reemplazarContenido(dl, [
      ...crearFila(textos.resumen.campo.poblacionObjetivo, datos.poblacion),
      ...crearFila(textos.resumen.campo.horizonte, datos.horizonte),
      ...crearFila(datos.etiquetaNivel, crearValorTercil(datos.tercil)),
      ...crearFila(textos.resumen.campo.confianza, crearValorConfianza(datos.confianza)),
      ...crearFila(textos.resumen.campo.ramasIncidencia, crearValorRamasIncidencia(datos.ramasIncidencia)),
    ]);

    reemplazarContenido(motivosSeccion, [
      crear("h3", { clase: "resumen__motivos-titulo" }, [textos.explicacion.titulo]),
      crearMotivos(datos.motivos ?? [], datos.etiquetaNivel),
    ]);

    if (crossfade) {
      dl.animate([{ opacity: 0.4 }, { opacity: 1 }], { duration: DURACION_CROSSFADE_MS });
    }
  }

  function destruir() {
    raiz.remove();
  }

  return { raiz, actualizar, destruir };
}
