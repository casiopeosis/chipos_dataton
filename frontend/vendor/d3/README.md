# `vendor/d3/` — bundle de D3 vendorizado

`d3-chipos.esm.js` es un único módulo ES generado **fuera de línea** que empaqueta los
submódulos de D3 que usa el mapa (`plans/frontend_specs.md` §3):

- `d3-geo` (proyección y trayectorias)
- `d3-zoom` (zoom/paneo de la vista de alcaldía)
- `d3-selection`
- `d3-transition`
- `d3-interpolate`
- `d3-ease`
- dependencias transitivas: `d3-array`, `d3-color`, `d3-dispatch`, `d3-drag`, `d3-timer`

No hay paso de build en tiempo de ejecución: `frontend/index.html` y los módulos de
`frontend/js/` importan `d3-chipos.esm.js` directamente (`<script type="module">` /
`import ... from "../vendor/d3/d3-chipos.esm.js"`), sin CDN y sin bundler en el navegador.
Este bundle se genera **una sola vez** y se versiona (se comitea) en el repositorio; solo
hay que regenerarlo si cambia la lista de submódulos necesarios.

## Cómo regenerarlo

Requiere Node.js y npm (no forman parte del runtime del frontend, solo de este paso de
build puntual). Desde esta carpeta (`frontend/vendor/d3/`):

```sh
npm install
node build.mjs
rm -rf node_modules package-lock.json
```

- `npm install` instala temporalmente las versiones exactas de D3 y `esbuild` fijadas en
  `package.json` (devDependencies). `node_modules/` está en el `.gitignore` raíz y nunca se
  comitea.
- `node build.mjs` corre `esbuild` en modo `bundle` + `minify` sobre una entrada virtual que
  re-exporta todo lo público de los 11 paquetes listados arriba (igual que hace el paquete
  `d3` completo, pero limitado a estos), y escribe el resultado en
  `d3-chipos.esm.js` (formato `esm`, `target: es2020`, sin comentarios de licencia).
- El último paso borra `node_modules/` y el lockfile: no quedan artefactos de build sin
  comitear salvo el propio `d3-chipos.esm.js`.

Tras regenerar, verificar:

```sh
gzip -9 -c d3-chipos.esm.js | wc -c   # debe quedar ≤ 40 960 bytes (40 kB gzip, spec §16.1)
grep -o "geoMercator\|geoPath\|zoom\|select\|transition\|interpolateZoom\|easeCubic" d3-chipos.esm.js
```

## Versiones empaquetadas

Fijadas en `package.json` de esta carpeta (npm, snapshot 2026-09-18):

| paquete | versión |
|---|---|
| d3-array | 3.2.4 |
| d3-color | 3.1.0 |
| d3-dispatch | 3.0.1 |
| d3-drag | 3.0.0 |
| d3-ease | 3.0.1 |
| d3-geo | 3.1.1 |
| d3-interpolate | 3.0.1 |
| d3-selection | 3.0.0 |
| d3-timer | 3.0.1 |
| d3-transition | 3.0.1 |
| d3-zoom | 3.0.0 |
| esbuild (solo build) | 0.28.2 |

## Estado actual del bundle comiteado

Generado el 2026-09-18: 116 168 bytes sin comprimir, **39 651 bytes gzip** (`gzip -9`),
por debajo del presupuesto de 40 kB gzip de `plans/frontend_specs.md` §16.1.

No editar `d3-chipos.esm.js` a mano: cualquier cambio se hace en `build.mjs` o en las
versiones de `package.json` y se regenera con el comando de arriba.
