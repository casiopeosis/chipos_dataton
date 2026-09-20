# CLAUDE.md — chipos_dataton

Proyecto: **predicción de demanda de servicios para infancias en la Ciudad de México, por AGEB y por alcaldía**.
Salida: un veredicto conclusivo por unidad territorial (**sube / se_mantiene / baja**) con magnitud, intervalo y confianza, visualizado en un frontend web profesional.

## Reglas duras
1. **Prohibido Streamlit, Dash, Gradio, Panel, Shiny** o cualquier framework que genere la UI desde Python.
2. **Frontend = HTML + CSS + JS vanilla (ES modules)**. Sin React/Vue/Angular, sin paso de build obligatorio. Librerías de mapas/gráficas (Leaflet o MapLibre, D3) permitidas solo **vendorizadas en `frontend/vendor/`**, sin CDN en tiempo de ejecución.
3. El **contenido** de `data/processed/` y `data/reference/` es inmutable (nunca editar ni sobrescribir archivos). Se **autoriza reorganizar** (mover/renombrar con `git mv` en subcarpetas coherentes), registrando cada movimiento en `docs/data_manifest.md` (ruta anterior → nueva, motivo) y actualizando las rutas en `tools/` y `backend/`. Derivados van a `data/interim/` o `data/outputs/`. Se autoriza crear `requirements.txt`, `Makefile` y `.venv` (ignorado por git); toda dependencia instalada se registra en `requirements.txt`.
4. **Nunca leer archivos de datos completos** (ver "Economía de tokens").
5. Todo es **reproducible**: semillas fijas, pipeline determinista, `make pipeline` regenera `data/outputs/`.
6. No inventar datos, columnas, claves ni rutas: verificarlas en `docs/perfil_datos.md`. No imputar sin documentarlo.

## Idioma y estilo
- Código, comentarios, commits y docs en **español**. Identificadores en `snake_case` sin acentos.
- "alcaldía" en código y UI (sinónimo histórico: delegación). "AGEB" en mayúsculas.
- Python 3.11+ (`duckdb`, `pandas`, `geopandas`, `statsmodels`, `scikit-learn`, `pytest`). Dependencia nueva = justificación en el plan y en `requirements.txt`.

## Estructura del repo
```
chipos_dataton/
├── CLAUDE.md · Makefile · requirements.txt
├── plans/      backend_plan.md · frontend_plan.md · frontend_specs.md (lo entrega el equipo)
├── docs/       perfil_datos.md · problemas_datos.md · metodologia.md
├── tools/      profile_data.py
├── data/
│   ├── processed/   SOLO LECTURA: areas_verdes, comercios, espacios_publicos, infancias, salud, enut_2024_cdmx_uso_tiempo.csv
│   ├── reference/   SOLO LECTURA: alcaldias.{csv,geojson}, dominios_scian.csv, ageb_cdmx.geojson, ageb_cdmx_simplificado.geojson
│   ├── interim/     panel AGEB-año, features (git-ignorado si pesa)
│   └── outputs/     prediccion_ageb.json · prediccion_alcaldia.json (regenerables, no editar a mano)
├── backend/
│   ├── src/chipos/  io.py · panel.py · features.py · modelos.py · backtest.py · exportar.py
│   └── tests/
└── frontend/        index.html · css/ · js/ (main, mapa, estado, api, graficas) · vendor/ · data/ (copia/enlace a outputs)
```

## Datos (resumen)
- DENUE `infancias/`, `salud/` (CSV) y `comercios/` (GeoJSON): 11 cortes, 2016-10 a 2026-05, **intervalos irregulares**. Son fotografías, no flujos: un cambio puede ser cobertura del levantamiento o reclasificación SCIAN (`dominios_scian.csv`), no cambio real. Verificar antes de comparar años.
- `areas_verdes/`, `espacios_publicos/`: cortes únicos (features estáticas). ENUT 2024: encuesta, probable resolución superior a AGEB.
- **Brecha conocida:** no hay geometría AGEB. Fuente: INEGI Marco Geoestadístico, entidad `09`, reproyectar a EPSG:4326 y guardar en `data/reference/ageb_cdmx.geojson`. Clave `CVEGEO` = `CVE_ENT`(2)+`CVE_MUN`(3)+`CVE_LOC`(4)+`CVE_AGEB`(4); alcaldía = `CVE_MUN` `002`–`017`. La versión del marco debe coincidir con la clave AGEB de los DENUE; registrarla en el perfil.
- AGEB rurales (Milpa Alta, Tlalpan, Xochimilco): incluir o excluir con decisión documentada.
- Joins geográficos siempre en WGS84.

## Enfoque de modelado
- Unidad base **AGEB**; alcaldía = agregación por `CVE_MUN`.
- Distinguir **oferta** (establecimientos DENUE) de **demanda** (población objetivo × necesidad). Nunca presentar una como la otra sin etiquetarlo. La variable objetivo exacta se fija en `plans/backend_plan.md`.
- Pocas observaciones por AGEB (≤ 11): modelos parsimoniosos, contracción hacia la alcaldía (jerárquico / empirical Bayes) para conteos bajos; modelar sobre tiempo real (años decimales), no sobre índice.
- Veredicto por **regla explícita con banda muerta** (umbral de `se_mantiene`) definida y documentada en un solo lugar (`modelos.py` + `docs/metodologia.md`).
- Validar con **backtest temporal de origen móvil** (sin k-fold aleatorio, sin fuga del futuro) y comparar contra baseline ingenuo ("igual que el último corte"). Si no lo supera, no se adopta.
- Datos insuficientes → `sin_datos`, nunca un veredicto inventado.

## Decisiones vigentes (confirmadas por el equipo)
- **Demanda** = población infantil por AGEB, del Censo 2010 y 2020 (INEGI RESAGEBURB oficial en `data/processed/censo/inegi_{2010,2020}/`; el xlsx del equipo queda superseded, ver `docs/data_manifest.md`), proyectada con tendencia y contracción hacia la alcaldía, ajustada a proyecciones CONAPO por municipio. **Oferta** = establecimientos DENUE con `Alcance = Principal`. Capas separadas; el veredicto principal es de **demanda**; la oferta y la brecha (demanda/oferta) son capas complementarias.
- Rango de edad: **0–14 años** (confirmado: todos los establecimientos `Principal` atienden esas edades). **Suma simple, sin ponderaciones** (ENUT no se usa para ponderar: solo tiene resolución CDMX; queda como contexto narrativo).
- DENUE: las 11 ediciones **no son independientes** (levantamientos nuevos en 2019-11 y 2024-11). Usar **un corte por periodo**; nunca tratar los 11 como observaciones. Agrupar siempre por `CVE_MUN` (nombres de alcaldía mal codificados en 2016–2018). La caída de 2024-11 (−11.2 %; privado −22.8 %, preescolar privado −38.7 %; público +1.2 %; solo reaparece el 3 % de las bajas) se trata como **cierres reales acumulados entre 2020 y 2023 y registrados de golpe al volver a campo en 2024**: usar las fechas de levantamiento como eje temporal, no atribuirla a un solo año, y aplicar **tope de confianza `media`** a la capa de oferta.
- Banda de `se_mantiene`: umbral base ±1 %/año sobre la tasa proyectada; `sube`/`baja` solo si la probabilidad de estar fuera de la banda en ese sentido es **≥ 0.80**; se reporta sensibilidad a ±0.5 y ±2 %/año. Horizonte: fecha base mediados de 2026 (2026.5), horizontes de reporte a 3, 5 y 7 años (2029-06/2031-06/2033-06).
- AGEB **rurales** → `sin_datos`. Filtrar puntos fuera de CDMX (p. ej. 85 de salud) por clave/bbox, aunque vengan marcados como válidos. No usar `CLEE` para rastrear establecimientos antes de 2020 (vacía).

## Contrato de salida (versionado; cambiarlo exige actualizar el frontend)
`data/outputs/prediccion_ageb.json` (`version` 1.2, generado por `backend/src/chipos/exportar.py`;
shape completo y decisiones de diseño en `plans/frontend_specs.md` §17-18): `fecha_base` = fecha de
referencia del cambio (mediados de 2026); `horizontes` = 3 puntos de reporte (3/5/7 años desde
`fecha_base`); cada registro de AGEB/alcaldía trae `serie` (niveles observados), `nivel_base`
(proyectado a `fecha_base`) y un objeto `h` con un resultado por horizonte disponible. La capa
`oferta` solo reporta `h3` (`horizontes_disponibles: ["h3"]`), sin calibración más allá de 3 años
(ver `docs/metodologia.md` §6). `delta_pct`/`ic95` se miden desde `fecha_base`, no desde el censo
2020; el veredicto y la confianza no varían entre horizontes (dependen de la tasa anual, no del
horizonte de reporte) — solo `delta_pct`/`ic95` cambian.
```json
{"version":"1.2","generado":"ISO-8601","fecha_base":"2026-06",
 "horizontes":[{"clave":"h3","anios":3,"fecha":"2029-06"},
               {"clave":"h5","anios":5,"fecha":"2031-06"},
               {"clave":"h7","anios":7,"fecha":"2033-06"}],
 "capas":{
  "demanda":{"<CVEGEO>":{"cve_mun":"002","n_obs":2,"motivo_sin_datos":null,
     "serie":{"t":[2010.44,2020.20],"valor":[512.0,388.0]},"nivel_base":306.2,
     "h":{"h3":{"veredicto":"baja","delta_pct":-10.7,"tasa_anual_pct":-3.8,"ic95":[-15.3,-7.3],"confianza":"alta"},
          "h5":{"veredicto":"baja","delta_pct":-17.1,"tasa_anual_pct":-3.8,"ic95":[-24.2,-11.8],"confianza":"alta"},
          "h7":{"veredicto":"baja","delta_pct":-23.1,"tasa_anual_pct":-3.8,"ic95":[-32.2,-16.1],"confianza":"alta"}}}},
  "oferta":{"<CVEGEO>":{"cve_mun":"002","n_obs":3,"motivo_sin_datos":null,
     "serie":{"t":[2016.79,2019.87,2024.87],"valor":[7,5,5]},"nivel_base":4.8,
     "horizontes_disponibles":["h3"],
     "h":{"h3":{"veredicto":"baja","delta_pct":-6.3,"tasa_anual_pct":-2.2,"ic95":[-6.3,-6.3],"confianza":"media"}}}},
  "brecha":{"<CVEGEO>":{"cve_mun":"002","valor":6.1,"unidad":"establecimientos por 1,000 de 0 a 14 años",
     "t_oferta":2024.87,"t_demanda":2020.20}}}}
```
`prediccion_alcaldia.json`: mismo esquema por `CVE_MUN`, más `distribucion_ageb` (conteo de
veredictos por horizonte) en cada alcaldía y `agregado_cdmx` (mismo registro a nivel ciudad) en la
raíz. Veredictos: `sube | se_mantiene | baja | sin_datos`. Confianza: `alta | media | baja`. Nunca
un veredicto sin `confianza` ni `n_obs`. El frontend conserva un adaptador para leer contrato v1.1
(un solo horizonte) como camino de degradación (`frontend/js/api.js`).

## Frontend
Calidad de producción; detalle vinculante en `plans/frontend_specs.md`. Mínimos:
- Mapa de alcaldías → clic → animación "pop" + `flyToBounds` → solo los AGEB de esa alcaldía, coloreados por veredicto; tooltip + panel lateral; `Esc`/botón para volver.
- **Un solo GeoJSON de AGEB** (simplificado; TopoJSON si pesa) unido por `CVEGEO` en cliente, filtrado por `CVE_MUN`. No crear archivos por alcaldía salvo que el único supere ~5 MB tras simplificar.
- Paleta con significado fijo y apta para daltonismo (`sube`/`baja` divergente, `se_mantiene` neutro, `sin_datos` gris con patrón/etiqueta); leyenda siempre visible; no depender solo del color.
- HTML semántico, teclado, `aria-*`, contraste WCAG AA, respetar `prefers-reduced-motion`. Responsive. CSS con variables y sin `!important`. JS modular sin globales; sin `innerHTML` con datos sin sanear.
- Estados de carga, error y vacío diseñados. UI en español (México).

## Economía de tokens al leer datos
- Empezar por `docs/perfil_datos.md`; no releer lo ya resumido.
- Usar `tools/profile_data.py` (salida acotada por archivo: filas, columnas, dtypes, % nulos, cardinalidad, min/max, 2 filas de ejemplo).
- CSV: `head -n 3`, `wc -l`, `duckdb -c "DESCRIBE SELECT * FROM 'f.csv'"`. GeoJSON: `jq -c '.features[0].properties'`, `jq '.features|length'`; jamás imprimir geometrías.
- Las 11 tablas de cada familia comparten esquema: perfilar una a fondo y las demás solo por diferencias.
- Imprimir agregados, no filas; máximo ~40 líneas por salida. Los hallazgos van a archivos `.md`, no a la conversación.


## Definición de terminado
- Backend: tests verdes; backtest reportado (métrica del modelo vs baseline, 5 líneas); salidas validadas contra el contrato; `docs/metodologia.md` al día.
- Frontend: cumple `frontend_specs.md`; sin CDN ni errores en consola; Lighthouse accesibilidad ≥ 90.
- Ningún archivo de `data/processed/` ni `data/reference/` modificado.