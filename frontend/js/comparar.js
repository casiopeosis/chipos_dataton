// frontend/js/comparar.js
//
// Comparar alcaldías (plans/frontend_specs.md §10.13, plan F88). El usuario elige alcaldía A/B;
// la comparación conserva exactamente el escenario activo (población, horizonte, búsqueda, pesos,
// filtros) -- nunca lo reinicia. Indicadores lado a lado con los mismos terciles de §6.2. Nunca
// declara una ganadora ni genera una frase automática.
//
// Autocontenido (plan §9): recibe ya calculados los indicadores de cada alcaldía (misma fuente
// que `resumen.js`/`ranking.js`, `composicion.js` vía `agregarResumen` de `main.js`) y solo pinta
// + despacha `ACCIONES.COMPARAR`/`DEJAR_DE_COMPARAR`.

import { crear, reemplazarContenido, limpiar } from "./dom.js";
import { textos } from "./textos.js";
import { RAMAS } from "./composicion.js";
import { despachar as despacharEstado, ACCIONES } from "./estado.js";

/**
 * Monta el selector + panel de comparación dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @param {Map<string, string>} nombresAlcaldia - `cve_mun -> nombre`.
 * @param {{despachar?: (accion: object) => void}} [opciones]
 * @returns {{actualizar: (datos: object|null) => void, destruir: () => void}}
 */
export function montarComparar(contenedor, nombresAlcaldia, opciones = {}) {
  const despachar = typeof opciones.despachar === "function" ? opciones.despachar : despacharEstado;
  const entradasOrdenadas = [...nombresAlcaldia.entries()].sort((a, b) => a[1].localeCompare(b[1], "es-MX"));

  const raiz = crear("section", { clase: "comparar", "aria-labelledby": "comparar-titulo" });
  raiz.appendChild(crear("h3", { id: "comparar-titulo", clase: "comparar__titulo" }, [textos.comparar.titulo]));

  function crearSelector(idSufijo, etiquetaTexto, valorInicial) {
    const id = `comparar-${idSufijo}`;
    const select = crear(
      "select",
      { id, clase: "comparar__select" },
      [
        crear("option", { value: "" }, ["—"]),
        ...entradasOrdenadas.map(([cveMun, nombre]) =>
          crear("option", { value: cveMun, selected: cveMun === valorInicial }, [nombre])),
      ],
    );
    const etiqueta = crear("label", { for: id, clase: "comparar__etiqueta" }, [etiquetaTexto]);
    return { campo: crear("div", { clase: "comparar__campo" }, [etiqueta, select]), select };
  }

  const estadoActual = { a: null, b: null };
  const selectorA = crearSelector("a", textos.comparar.seleccionA, null);
  const selectorB = crearSelector("b", textos.comparar.seleccionB, null);

  function intentarDespachar() {
    const a = selectorA.select.value;
    const b = selectorB.select.value;
    if (a && b && a !== b) despachar({ tipo: ACCIONES.COMPARAR, cve_mun_a: a, cve_mun_b: b });
  }
  selectorA.select.addEventListener("change", intentarDespachar);
  selectorB.select.addEventListener("change", intentarDespachar);

  const botonQuitar = crear(
    "button",
    { type: "button", clase: "comparar__quitar", onclick: () => despachar({ tipo: ACCIONES.DEJAR_DE_COMPARAR }) },
    [textos.comparar.quitar],
  );

  const controles = crear("div", { clase: "comparar__controles" }, [selectorA.campo, selectorB.campo, botonQuitar]);
  const tablaHost = crear("div", { clase: "comparar__tabla-host" });

  raiz.appendChild(controles);
  raiz.appendChild(crear("p", { clase: "comparar__nota" }, [textos.comparar.nota]));
  raiz.appendChild(tablaHost);
  contenedor.appendChild(raiz);

  /** Fila `{etiqueta, tercilA, tercilB}` -> `<tr>` (tabla real, spec: "indicadores lado a lado"). */
  function crearFilaTabla(etiqueta, tercilA, tercilB) {
    return crear("tr", {}, [
      crear("th", { scope: "row", clase: "comparar__fila-etiqueta" }, [etiqueta]),
      crear("td", { clase: `comparar__celda comparar__celda--${tercilA}` }, [
        `${textos.tercil.simbolo[tercilA] ?? textos.tercil.simbolo.sin_datos} ${textos.tercil.palabra[tercilA] ?? textos.tercil.palabra.sin_datos}`,
      ]),
      crear("td", { clase: `comparar__celda comparar__celda--${tercilB}` }, [
        `${textos.tercil.simbolo[tercilB] ?? textos.tercil.simbolo.sin_datos} ${textos.tercil.palabra[tercilB] ?? textos.tercil.palabra.sin_datos}`,
      ]),
    ]);
  }

  /**
   * @param {{
   *   nombreA: string, nombreB: string,
   *   ramasA: Record<string, string>, ramasB: Record<string, string>,
   *   oportunidadA: string, oportunidadB: string,
   *   confianzaA: string, confianzaB: string,
   * } | null} datos - `null` cuando `estado.comparando` es `null` (sin selección activa).
   */
  function actualizar(datos) {
    if (!datos) {
      limpiar(tablaHost);
      return;
    }
    selectorA.select.value = datos.cveMunA ?? "";
    selectorB.select.value = datos.cveMunB ?? "";

    const filas = [
      ...RAMAS.map((rama) => crearFilaTabla(textos.rama.nombre[rama] ?? rama, datos.ramasA[rama], datos.ramasB[rama])),
      crearFilaTabla(textos.resumen.campo.oportunidad, datos.oportunidadA, datos.oportunidadB),
      crearFilaTabla(textos.resumen.campo.confianza, datos.confianzaA, datos.confianzaB),
    ];

    const encabezado = crear("tr", {}, [
      crear("th", { scope: "col" }, []),
      crear("th", { scope: "col" }, [datos.nombreA]),
      crear("th", { scope: "col" }, [datos.nombreB]),
    ]);

    reemplazarContenido(tablaHost, [
      crear("table", { clase: "comparar__tabla" }, [
        crear("caption", { clase: "visualmente-oculto" }, [`${textos.comparar.titulo}: ${datos.nombreA} / ${datos.nombreB}`]),
        crear("thead", {}, [encabezado]),
        crear("tbody", {}, filas),
      ]),
    ]);
  }

  function destruir() {
    raiz.remove();
  }

  return { actualizar, destruir };
}
