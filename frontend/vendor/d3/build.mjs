#!/usr/bin/env node
// Genera frontend/vendor/d3/d3-chipos.esm.js: un único bundle ESM con los
// submódulos de D3 que necesita el mapa (plans/frontend_specs.md §3):
// d3-geo, d3-zoom, d3-selection, d3-transition, d3-interpolate, d3-ease,
// más sus dependencias (d3-array, d3-color, d3-dispatch, d3-drag, d3-timer).
//
// Este script se ejecuta una sola vez, fuera de línea, para producir el
// bundle versionado que se comitea en el repositorio. El frontend en sí
// no tiene ningún paso de build: `frontend/index.html` importa
// `d3-chipos.esm.js` directamente como módulo ES.
//
// Comando exacto para regenerarlo: ver README.md de esta carpeta.

import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const aqui = dirname(fileURLToPath(import.meta.url));

// Entrada virtual: re-exporta todo lo público de cada submódulo, igual que
// hace el paquete "d3" completo, pero limitado a los módulos que se listan
// arriba. `resolveDir` apunta a esta carpeta para que esbuild resuelva los
// paquetes de node_modules instalados aquí (ver README.md).
const entrada = `
export * from "d3-array";
export * from "d3-color";
export * from "d3-dispatch";
export * from "d3-timer";
export * from "d3-ease";
export * from "d3-interpolate";
export * from "d3-selection";
export * from "d3-transition";
export * from "d3-drag";
export * from "d3-zoom";
export * from "d3-geo";
`;

const resultado = await build({
  stdin: {
    contents: entrada,
    resolveDir: aqui,
    loader: "js",
    sourcefile: "d3-chipos-entrada-virtual.js",
  },
  outfile: `${aqui}/d3-chipos.esm.js`,
  bundle: true,
  format: "esm",
  platform: "browser",
  target: ["es2020"],
  minify: true,
  legalComments: "none",
  metafile: true,
  banner: {
    js:
      "// d3-chipos.esm.js — bundle ESM vendorizado de D3 para chipos_dataton.\n" +
      "// Incluye: d3-geo, d3-zoom, d3-selection, d3-transition, d3-interpolate,\n" +
      "// d3-ease, d3-array, d3-color, d3-dispatch, d3-drag, d3-timer.\n" +
      "// Generado offline con esbuild (frontend/vendor/d3/build.mjs).\n" +
      "// No editar a mano: regenerar con el comando de frontend/vendor/d3/README.md.",
  },
});

if (resultado.metafile) {
  const bytes = Buffer.byteLength(
    (await import("node:fs")).readFileSync(`${aqui}/d3-chipos.esm.js`),
  );
  console.log(`Bundle generado: d3-chipos.esm.js (${bytes} bytes sin gzip)`);
}
