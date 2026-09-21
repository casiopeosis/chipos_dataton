// frontend/js/filtros.js
//
// Filtros por rama (plans/frontend_specs.md §10.11, plan F40). Un sub-panel por rama; nunca añade
// complejidad matemática nueva -- solo decide qué celdas de filtro (§17.3, `panel.CELDAS_*` en el
// backend) se suman en `composicion.js` (`estado.filtros[rama]`, `[]` = todas). Las claves de
// nivel/tipo y de sector que ofrece esta UI son exactamente las de `textos.filtros[rama].nivel` /
// `textos.filtros.sector` (ya centralizadas ahí, espejo de `panel.py`): este módulo no inventa
// ninguna clave nueva, solo las combina en celdas `{nivel}__{sector}` para educación/salud
// (backend `panel.CELDAS_EDUCACION`/`CELDAS_SALUD`) o las usa tal cual para comercio/verde (sin
// sector, backend `panel.CELDAS_COMERCIO`/`CELDAS_VERDE`).
//
import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { RAMAS } from "./composicion.js";
import { despachar, suscribir, obtenerEstado, ACCIONES } from "./estado.js";
import { crearAyuda } from "./ayuda.js";

const SECTORES = Object.freeze(["todos", "publico", "privado"]);
/** Ramas con cruce de sector (§10.11.1/§10.11.2); comercio/verde no lo tienen. */
const RAMAS_CON_SECTOR = Object.freeze(["educacion", "salud"]);

/** Preset de "primera necesidad" para comercio (§10.11.3): las 4 celdas salvo farmacias. */
const COMERCIO_PRIMERA_NECESIDAD = Object.freeze([
  "supermercados_minisupers",
  "abarrotes",
  "frutas_verduras",
  "carnes_otros_alimentos",
]);

const SUGERENCIAS_EDUCACION = Object.freeze({
  primaria: Object.freeze(["primaria"]),
  adolescencia: Object.freeze(["media_superior_tecnica"]),
});

export function sugerenciaEducacionParaPoblacion(poblacion) {
  const sugerencia = SUGERENCIAS_EDUCACION[poblacion];
  return sugerencia ? [...sugerencia] : null;
}

function nivelesDeRama(rama) {
  return Object.keys(textos.filtros[rama].nivel);
}

/**
 * Deriva `estado.filtros[rama]` (lista de claves de celda) a partir de los niveles/tipos y el
 * sector elegidos en la UI. `niveles` vacío = todos los niveles; `sector==="todos"` = los 3
 * sectores. Si el resultado equivale a "sin filtro" (todo seleccionado), devuelve `[]` -- nunca
 * una lista que enumere expresamente TODAS las celdas (serían idénticas para `composicion.js`,
 * pero `[]` es más corto en el hash y más claro como "sin filtro" para `estado.js`).
 */
function celdasDeSeleccion(rama, nivelesSeleccionados, sector) {
  const todosLosNiveles = nivelesDeRama(rama);
  const niveles = nivelesSeleccionados.size === 0 ? todosLosNiveles : [...nivelesSeleccionados];

  if (!RAMAS_CON_SECTOR.includes(rama)) {
    return niveles.length === todosLosNiveles.length ? [] : niveles;
  }

  const sectoresClave = sector === "todos" ? ["publico", "privado", "no_especificado"] : [sector];
  if (niveles.length === todosLosNiveles.length && sector === "todos") return [];
  const celdas = [];
  for (const nivel of niveles) {
    for (const s of sectoresClave) celdas.push(`${nivel}__${s}`);
  }
  return celdas;
}

/** Deriva de vuelta {niveles, sector} desde `estado.filtros[rama]`, para reflejar el hash/URL en
 * los controles (p. ej. tras restaurar un enlace compartido). Aproximación honesta: si las celdas
 * no calzan con un patrón "niveles × sector" limpio (p. ej. vinieron de otra fuente), se muestran
 * como estaban -- los checkboxes reflejan cada celda presente, sin forzar un sector común. */
function seleccionDeCeldas(rama, celdas) {
  const todosLosNiveles = nivelesDeRama(rama);
  if (celdas.length === 0) return { niveles: new Set(), sector: "todos" };

  if (!RAMAS_CON_SECTOR.includes(rama)) {
    return { niveles: new Set(celdas), sector: "todos" };
  }

  const niveles = new Set();
  const sectoresVistos = new Set();
  for (const celda of celdas) {
    const [nivel, sectorCrudo] = celda.split("__");
    niveles.add(nivel);
    sectoresVistos.add(sectorCrudo === "no_especificado" ? "todos" : sectorCrudo);
  }
  const sector = sectoresVistos.size === 1 ? [...sectoresVistos][0] : "todos";
  return { niveles: niveles.size === todosLosNiveles.length ? new Set() : niveles, sector };
}

function crearSubpanel(rama, estadoInicial, onInteraccionUsuario) {
  const config = textos.filtros[rama];
  const { niveles: nivelesIniciales, sector: sectorInicial } = seleccionDeCeldas(rama, estadoInicial.filtros[rama]);
  let niveles = nivelesIniciales;
  let sector = sectorInicial;

  const casillas = new Map();
  const radiosSector = new Map();

  function emitir() {
    despachar({ tipo: ACCIONES.CAMBIAR_FILTRO_RAMA, rama, celdas: celdasDeSeleccion(rama, niveles, sector) });
  }

  const listaCasillas = crear("div", { clase: "filtros__opciones" });
  for (const [claveNivel, etiqueta] of Object.entries(config.nivel)) {
    const id = `filtros-${rama}-${claveNivel}`;
    const casilla = crear("input", {
      type: "checkbox",
      id,
      clase: "filtros__casilla",
      checked: niveles.size === 0 || niveles.has(claveNivel),
      onchange: (evento) => {
        onInteraccionUsuario(rama);
        // `niveles` vacío representa "todas" implícitamente (todas las casillas nacen marcadas
        // sin que ningún nivel esté explícito, spec §5.6: "sin filtros activos"). Antes de tocar
        // una sola casilla hay que materializar ese "todas" en el conjunto explícito completo, o
        // desmarcar una perdería a las demás (que seguirían "vacías" = "todas").
        if (niveles.size === 0) niveles = new Set(nivelesDeRama(rama));
        if (evento.target.checked) niveles.add(claveNivel);
        else niveles.delete(claveNivel);
        // Vuelve a quedar "todas" marcadas: limpia el conjunto para que se guarde como `[]` en
        // estado.js, no como una lista redundante que enumera cada nivel.
        if (niveles.size === nivelesDeRama(rama).length) niveles = new Set();
        emitir();
      },
    });
    casillas.set(claveNivel, casilla);
    listaCasillas.appendChild(
      crear("div", { clase: "filtros__item" }, [casilla, crear("label", { for: id }, [etiqueta])]),
    );
  }

  let presetPrimeraNecesidad = null;
  if (rama === "comercio") {
    presetPrimeraNecesidad = crear(
      "button",
      {
        type: "button",
        clase: "filtros__preset",
        onclick: () => {
          onInteraccionUsuario(rama);
          niveles = new Set(COMERCIO_PRIMERA_NECESIDAD);
          for (const [clave, casilla] of casillas) casilla.checked = niveles.has(clave);
          emitir();
        },
      },
      [textos.filtros.comercio.primeraNecesidad],
    );
  }

  let filaSector = null;
  if (RAMAS_CON_SECTOR.includes(rama)) {
    const grupoSector = crear("div", { clase: "filtros__sector", role: "radiogroup", "aria-label": textos.filtros.sectorEtiqueta });
    for (const claveSector of SECTORES) {
      const idSector = `filtros-${rama}-sector-${claveSector}`;
      const radio = crear("input", {
        type: "radio",
        name: `filtros-${rama}-sector`,
        id: idSector,
        clase: "filtros__radio",
        checked: claveSector === sector,
        onchange: () => {
          onInteraccionUsuario(rama);
          sector = claveSector;
          emitir();
        },
      });
      radiosSector.set(claveSector, radio);
      grupoSector.appendChild(radio);
      grupoSector.appendChild(crear("label", { for: idSector }, [textos.filtros.sector[claveSector]]));
    }
    filaSector = grupoSector;
  }

  const raiz = crear("details", { clase: "filtros__subpanel" }, [
    crear("summary", { clase: "filtros__pregunta" }, [config.pregunta]),
    listaCasillas,
    presetPrimeraNecesidad,
    filaSector,
    crear("p", { clase: "filtros__ayuda" }, [config.ayuda]),
  ]);

  function reflejar(estado) {
    const derivado = seleccionDeCeldas(rama, estado.filtros[rama]);
    niveles = derivado.niveles;
    sector = derivado.sector;
    for (const [clave, casilla] of casillas) casilla.checked = niveles.size === 0 || niveles.has(clave);
    for (const [clave, radio] of radiosSector) radio.checked = clave === sector;
  }

  function aplicarSugerencia(nivelesSugeridos) {
    niveles = new Set(nivelesSugeridos);
    sector = "todos";
    for (const [clave, casilla] of casillas) casilla.checked = niveles.has(clave);
    for (const [clave, radio] of radiosSector) radio.checked = clave === sector;
    emitir();
  }

  return { rama, raiz, reflejar, aplicarSugerencia };
}

/**
 * Monta el panel de filtros por rama dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @returns {() => void} función para desmontar (cancela la suscripción a `estado.js`).
 */
export function montarFiltros(contenedor) {
  const estadoInicial = obtenerEstado();
  const raiz = crear("section", { clase: "filtros", "aria-label": "Filtros por rama" });
  let educacionTocada = estadoInicial.filtros.educacion.length > 0;
  let poblacionAnterior = null;
  const marcarInteraccion = (rama) => {
    if (rama === "educacion") educacionTocada = true;
  };
  const subpaneles = RAMAS.map((rama) => crearSubpanel(rama, estadoInicial, marcarInteraccion));
  for (const { raiz: nodoSubpanel } of subpaneles) raiz.appendChild(nodoSubpanel);

  raiz.prepend(crear("div", { clase: "filtros__cabecera" }, [
    crear("span", { clase: "filtros__titulo" }, ["Filtros"]),
    crearAyuda("filtros", "Filtros por rama"),
  ]));

  const botonRestablecer = crear(
    "button",
    {
      type: "button",
      clase: "filtros__restablecer",
      onclick: () => {
        educacionTocada = true;
        despachar({ tipo: ACCIONES.RESTABLECER_FILTROS });
      },
    },
    [textos.filtros.restablecer],
  );
  raiz.appendChild(botonRestablecer);
  raiz.appendChild(crear("p", { clase: "filtros__ayuda-general" }, [textos.filtros.ayuda]));

  reemplazarContenido(contenedor, [raiz]);

  function reflejarTodo(estado) {
    const cambioPoblacion = estado.poblacion !== poblacionAnterior;
    poblacionAnterior = estado.poblacion;
    if (cambioPoblacion && !educacionTocada) {
      const sugerencia = sugerenciaEducacionParaPoblacion(estado.poblacion);
      if (sugerencia) {
        subpaneles.find((subpanel) => subpanel.rama === "educacion")?.aplicarSugerencia(sugerencia);
        return;
      }
    }
    for (const subpanel of subpaneles) subpanel.reflejar(estado);
  }

  reflejarTodo(estadoInicial);
  return suscribir(reflejarTodo);
}
