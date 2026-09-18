# Plan — Consolidación de datos a nivel alcaldía → JSON estático

## Contexto

El semáforo necesita, por alcaldía (16) y dominio, una serie histórica de oferta + un denominador poblacional, servidos como JSON estático a un frontend HTML/JS sin backend. Hoy los datos están en 50 carpetas con 4 esquemas distintos (Gen A, Gen B/Comercios, Infancias/Salud, Cultura/PILARES), claves de alcaldía heterogéneas y el bug de metadatos de Gen A (CLAUDE.md §1.1). El código existente (`src/engine.py`, `src/algo.py`) solo lee Gen B 2022+ y trae la población hardcodeada.

`docs/implementation-plan.md` no existe (ni en el árbol ni en git); por decisión del usuario se diseña sin él. Decisiones confirmadas: geometría de las alcaldías del Marco Geoestadístico INEGI 2020; se consolidan las 4 familias DENUE + cultura + PILARES, el frontend expone solo los 3 focos.

**Fuera de alcance (a propósito):** el estimador y los intervalos de confianza (CLAUDE.md §4: primero `docs/methodology.md`). Este pipeline entrega los insumos y fija el contrato del JSON del semáforo; no calcula la estimación. Nada de AGEB: ni columnas, ni tablas, ni ganchos.

## Hallazgos verificados en esta sesión (condicionan el diseño)

1. **El bug de Gen A también está en las filas y en `archivos_generados`**: `OCTUBRE 2016 CDMX/denue_servicios_adultos_mayores_cdmx_2016.csv` trae `anio_datos=2020, mes_corte=11, edicion_denue=2020-11` en cada fila, y `reporte_calidad_denue_2018.json → archivos_generados` lista archivos `_2020`. La regla se amplía: en Gen A se ignoran **todos** los campos de fecha, sea en el JSON o en el CSV.
2. **Nombres de alcaldía con mojibake en Gen A** (`Benito JuÃ¡rez`); se une por `clave_alcaldia`, nunca por nombre.
3. **Cambio de SCIAN entre Gen A y Gen B**: Gen A (deporte) solo tiene 713941-4; Gen B además tiene 611621-2 (escuelas de deporte). La serie 2016→2026 solo es comparable en el conjunto SCIAN común.
4. Claves de alcaldía por familia: Gen A `clave_alcaldia` ("002"), Gen B/Comercios `cve_mun` ("003"), Cultura `municipio_id` (int sin ceros), Infancias/Salud solo el nombre en `Alcaldía`, PILARES el nombre en mayúsculas sin acentos.
5. Infancias: `configuracion` idéntica en las 11 ediciones (`incluir_apoyo_social_y_residencias=True`, `solo_primera_infancia=False`); `fuente.edicion` es confiable. `INFANCIAS_2026_05` tiene zip `denue_09_shp.zip`, sin MMAA.
6. Gen A: `denue_enfoque_gimnasios_adultos_mayores_cdmx_YYYY.csv` es la unión (2018: 2,270 + 267 − 2 = 2,535 = `registros_maestros`).
7. `.venv` tiene pandas 3, numpy, scipy, shapely y jsonschema; **no tiene** openpyxl (el censo es .xlsx), geopandas ni pytest.

## Arquitectura

```
data/ (sin mover nada, CLAUDE.md §6.4)
  reference/            NUEVO, versionado
    alcaldias.csv       cve_alc, cvegeo, nombre oficial, variantes normalizadas
    alcaldias.geojson   16 polígonos INEGI MG 2020, simplificados, EPSG:4326
    dominios_scian.csv  scian → dominio, subcategoría, en_serie_armonizada
  processed/            NUEVO, tablas intermedias (CSV)
src/etl/
  fuentes.py            registro carpeta → familia (única pieza que conoce las rutas)
  catalogo.py           normalizar_alcaldia(valor, tipo) → cve_alc; falla si no cae en las 16
  ediciones.py          resolver_edicion(carpeta, familia) → "YYYY-MM" + procedencia
  lectores/{gen_a,gen_b,tematicos,cultura,pilares}.py
  poblacion.py          censo 2020 → población por alcaldía y grupo
  agregar.py            conteos alcaldía × edición × dominio × subcategoría
  exportar.py           JSON compacto + manifest
  validar.py            chequeos cruzados (ver Verificación)
  schemas/*.schema.json contrato de cada JSON de salida
  run.py                CLI: python -m src.etl.run
src/app/data/           salida estática que consume el frontend
```

### 1. Resolución de edición (`ediciones.py`), regla de §1.1

| Familia | Fuente de verdad | Chequeo cruzado |
|---|---|---|
| Gen A (2016/17/18/20) | `fuente.archivo` → regex `denue_09_(\d{2})(\d{2})` → MM/AA | nombre de la carpeta y sufijo del archivo; se guarda `sha256_archivo_entrada`. **Nunca** `anio_datos`/`mes_corte`/`edicion`/`nota_temporal`/`archivos_generados` ni las columnas de fila equivalentes. |
| Gen A 2021 (sin JSON) | nombre de la carpeta + sufijo del archivo | `edicion_verificada=false` |
| Infancias / Salud | `fuente.edicion` | carpeta + MMAA del zip cuando exista; Salud 2019 (sin JSON) → carpeta, `edicion_verificada=false` |
| Gen B / Comercios | `fuente.edicion` ("DENUE 05/2025") | carpeta |

Si la edición resuelta no coincide con el chequeo cruzado, el proceso aborta. Salida: `data/processed/linaje_ediciones.csv` (carpeta, familia, edición, zip, sha256, procedencia, verificada).

### 2. Lectores → esquema largo común (un registro por establecimiento)

Columnas: `familia, edicion, cve_alc, clee, scian, dominio, subcategoria, sector, alcance, revision_manual, flags_dominio…`. Se leen solo las columnas necesarias (`usecols`); `ageb`, `cve_geo_ageb`, `manzana`, `localidad`, dirección, teléfono, etc. no se leen.

- **Gen A**: solo el archivo de unión, deduplicado por `clee`; dominio/subcategoría asignados por SCIAN vía `dominios_scian.csv` (no por los textos de `categoria_enfoque`).
- **Gen B**: `*_depurado.csv`; se conserva `alcance_analitico` (Principal/Complementario: los centros de cuidado diurno 624121-2 son complementarios).
- **Infancias / Salud**: se conservan como columnas `Dedicación a infancias`, `Población objetivo estimada` y los flags `Es …`, para que la metodología decida qué contar sin volver a leer los crudos.
- **Cultura**: snapshot único; `tipo_cultural` como subcategoría; `es_pilares` se conserva para evitar el doble conteo.
- **PILARES**: métrica de contexto propia (`operativo`), sin sumarla a ningún dominio (pregunta 9 de current-state sigue abierta).
- `enut`, `AREAS VERDES`, `ESPACIO PUBLICO`: fuera de esta iteración (enut no tiene diccionario; las otras dos requieren un cruce espacial con los polígonos → siguiente iteración con shapely).

### 3. Población (`poblacion.py`)

Lee `Por alcaldía` / `Base alcaldía` del xlsx del censo (openpyxl pasa a ser dependencia del ETL, no del frontend). Grupos 0-17, 18-29, 30-59, 60+ y 65+ (65+ contenido en 60+, nunca se suma), aplicando el reparto 15-19 descrito en el README. Reemplaza el `POBLACION_2020_ALCALDIA` hardcodeado de `src/engine.py`, que se usa solo como chequeo en las pruebas.

### 4. Agregación (`agregar.py`) → `data/processed/`

- `oferta_alcaldia.csv`: edición × cve_alc × dominio × subcategoría × {n_total, n_principal, n_revision_manual, n_publico, n_privado}, más `en_serie_armonizada`.
- `poblacion_alcaldia.csv`: cve_alc × grupo.
- Se rellenan con 0 explícito las combinaciones alcaldía × edición sin establecimientos (para no confundirlas con dato faltante); las ediciones inexistentes (deporte/adultos mayores 2019-11) quedan **ausentes** y listadas en `manifest.huecos`.

### 5. Salida para el frontend (`src/app/data/`)

JSON minificado, claves estables, un archivo por dominio para que el navegador descargue solo el que se selecciona:

- `manifest.json`: `schema_version`, `generado`, commit de git, ediciones, dominios (`id`, etiqueta, grupo poblacional asociado: adultos_mayores→60+, infancia→0-17, cultura→total), huecos, hash por archivo (para invalidar caché).
- `alcaldias.geojson`: 16 polígonos, propiedades `cve_alc` y `nombre`; presupuesto ≤150 KB.
- `poblacion.json`: `{cve_alc: {total, g0_17, g18_29, g30_59, g60m, g65m}}`.
- `oferta/{dominio}.json`: `{ediciones:[…], alcaldias:{cve_alc:{serie:[…], serie_armonizada:[…], subcategorias:{…}, tasa_100k_ultima}}, calidad:{edicion:{verificada, n_revision_manual}}}`.
- `semaforo/{dominio}.schema.json`: **solo el contrato** (`estimacion`, `ic_inf`, `ic_sup`, `nivel_ic`, `nivel` ∈ {alto, medio, bajo}, `metodo_id`). Lo llena la etapa de modelado cuando exista `docs/methodology.md`.

### Qué pasa con el código existente

`src/engine.py` y `src/algo.py` no se tocan (su lógica de t de Student/LOO-CV servirá de referencia para el modelado). El archivado de `semaforo_v0/v1.json` en `docs/legacy/` queda como un paso aparte, fuera de este plan.

## Orden de implementación

1. `data/reference/alcaldias.csv` + `catalogo.py` + pruebas (las 5 formas de clave/nombre → 16 claves).
2. `ediciones.py` + pruebas de la regla de Gen A (fixture: JSON con `edicion: "2020-11"` y `archivo: denue_09_1016.zip` → `2016-10`).
3. `dominios_scian.csv` + lectores, uno por familia.
4. `poblacion.py` (instalar openpyxl y pytest en `.venv`; agregar `requirements-etl.txt`).
5. `agregar.py`, `exportar.py`, schemas, `run.py`.
6. Descargar el MG 2020 de INEGI (capa mun, entidad 09), simplificarlo con shapely y guardar `alcaldias.geojson` (acción de red; se confirma antes de ejecutarla).
7. Documentar el pipeline y la regla ampliada de Gen A en `docs/etl.md`.

## Verificación

`python -m src.etl.run && python -m pytest tests/etl` debe comprobar:

- **Reconciliación con los reportes de calidad**: los conteos por edición cuadran con `resultados` de cada JSON (Gen A 2018 = 2,535 tras deduplicar; Comercios 2025-05 = 88,116; Gen B 2025-05 = 3,194; Infancias/Salud = sus totales conservados).
- **Linaje**: las 4 familias de un mismo periodo comparten edición y, donde existe, `sha256`.
- **Gen A**: ninguna edición resuelta es `2020-11` salvo `NOVIEMBRE 2020 CDMX`, y las 4 ediciones son distintas.
- **Territorio**: el `cve_alc` de todas las filas está en las 16 claves; ninguna salida tiene columnas o llaves que coincidan con `/ageb|manzana|localidad/i` (prueba explícita).
- **Población**: suma 9,200,318; `Control` = 0; coincide con `POBLACION_2020_ALCALDIA` de `src/engine.py`.
- **Salida**: cada JSON valida contra su schema (jsonschema); presupuesto de tamaño (dominio ≤100 KB, geojson ≤150 KB).
- **Humo del frontend**: `python -m http.server -d src/app` y hacer `fetch` a `manifest.json` → `oferta/infancia.json` desde la consola del navegador, sin backend.
