// frontend/js/ficha.js
//
// Ficha de zona (AGEB), Nivel 1 + entrada a Nivel 2 (plans/frontend_specs.md §7.4, plan F60).
// Reutiliza el contenido de Nivel 1 (§6.1, sin frase) montando internamente `resumen.js` --
// mismo campo, mismos terciles, invariante resumen=ranking (§7.1) también aquí, en vez de
// reimplementar el `<dl>`. Este módulo solo añade lo específico de una ficha de AGEB: la línea de
// ubicación (alcaldía · clave AGEB) y el motivo de `sin_datos` cuando corresponde (§14.4).
//
// Sin gráficas aquí (spec: "Nivel 1 no debe saturar con gráficas") -- esas viven en Nivel 2
// (§10.5, `graficas.js`, aún no conectado), detrás del botón "Entender esta zona" que ya trae
// `resumen.js` (abre el drawer, ver su propia nota de alcance).

import { crear, reemplazarContenido } from "./dom.js";
import { textos } from "./textos.js";
import { montarResumen } from "./resumen.js";

/**
 * Monta la ficha de zona dentro de `contenedor`.
 *
 * @param {HTMLElement} contenedor
 * @returns {{actualizar: (datos: object) => void, destruir: () => void}}
 */
export function montarFicha(contenedor) {
  if (!contenedor) throw new TypeError("montarFicha(contenedor): se requiere un contenedor");

  const raiz = crear("div", { clase: "ficha" });
  const ubicacionEl = crear("p", { clase: "ficha__ubicacion" });
  const motivoEl = crear("p", { clase: "ficha__motivo" });
  const resumenHost = crear("div", { clase: "ficha__resumen" });

  raiz.appendChild(ubicacionEl);
  raiz.appendChild(motivoEl);
  raiz.appendChild(resumenHost);
  contenedor.appendChild(raiz);

  const resumenInstancia = montarResumen(resumenHost);

  /**
   * @param {{
   *   cvegeo: string,
   *   alcaldiaNombre: string,
   *   motivoSinDatosCodigo: string|null,
   *   resumen: Parameters<ReturnType<typeof montarResumen>["actualizar"]>[0],
   * }} datos
   */
  function actualizar(datos) {
    reemplazarContenido(ubicacionEl, [
      textos.ficha.ubicacion({ alcaldia: datos.alcaldiaNombre, cvegeo: datos.cvegeo }),
    ]);
    reemplazarContenido(
      motivoEl,
      datos.motivoSinDatosCodigo
        ? [textos.tooltip.agebSinDatos(textos.motivosSinDatos.obtener(datos.motivoSinDatosCodigo))]
        : [],
    );
    resumenInstancia.actualizar(datos.resumen);
  }

  function destruir() {
    resumenInstancia.destruir();
    raiz.remove();
  }

  return { raiz, actualizar, destruir };
}
