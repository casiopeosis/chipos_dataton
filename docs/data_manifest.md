# Manifiesto de datos

Registro de fuentes y movimientos en `data/` (CLAUDE.md, regla 3). Ningún archivo existente cambió
de contenido. Los archivos nuevos se añaden; los reemplazados se marcan **superseded**.
Reproducir: `make descargas` (fuentes → `data/processed/`) y `make datos` (derivados).

## Estructura vigente

```
data/processed/
├── areas_verdes/        inventario_areas_verdes_cdmx_depurado.{csv,geojson}
├── censo/               AGEB_2010_2020.xlsx (hoja 2010 superseded)
│   ├── inegi_2010/      resultados_ageb_urbana_09_cpv2010.csv + diccionario + metadatos
│   └── inegi_2020/      conjunto_de_datos_ageb_urbana_09_cpv2020.csv + diccionario + metadatos
├── comercios/           denue_comercios_cdmx_AAAA_MM_depurado.geojson (11)
├── conapo/              pobproy_quinq1.csv (CONAPO municipal 1990–2040, todo el país)
├── enut/                enut_2024_cdmx_uso_tiempo.csv
├── espacios_publicos/   espacio_publico_cdmx_depurado.geojson
├── infancias/           denue_infancias_cdmx_AAAA_MM.csv (11)
├── marco_geo/
│   ├── mg2020/          09a (AGEB urbanas), 09ar (AGEB rurales), 09mun (.shp/.shx/.dbf/.prj/.cpg) + metadatos
│   └── mg2010v5/        ageb_urbana_2010_09.gpkg, municipios_2010_09.gpkg (filtrados a entidad 09)
└── salud/               denue_salud_cdmx_AAAA_MM.csv (11)
data/reference/          alcaldias.{csv,geojson}, dominios_scian.csv,
                         ageb_cdmx.geojson (5.08 MB), ageb_cdmx_simplificado.geojson (1.51 MB)
data/interim/            derivados regenerables, ignorado por git (ver abajo)
```

## Fuentes descargadas (2026-09-18, `tools/descargar_datos.py`)

Originales en `data/interim/descargas/` (git-ignorado; `unzip -t` sin errores en los cuatro zip).

| archivo original | URL | fecha | bytes | sha256 |
|---|---|---|---|---|
| `resageburb_09_2010_csv.zip` | https://www.inegi.org.mx/contenidos/programas/ccpv/2010/datosabiertos/ageb_y_manzana/resageburb_09_2010_csv.zip | 2026-09-18 | 9,754,441 | `34c38e8c527fbc2668e733d21f37b10e1db19c3d9d4443baa0ca17fd6138983a` |
| `ageb_mza_urbana_09_cpv2020_csv.zip` | https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_09_cpv2020_csv.zip | 2026-09-18 | 12,990,807 | `1f5f123b8e9a50991d1847271b5a2bf321e813e924e5bcf958cab612311c765a` |
| `mg2020_09_ciudaddemexico.zip` | https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/09_ciudaddemexico.zip | 2026-09-18 | 83,207,305 | `685b912f5458138a70726cff41aff828473e14264c43289d3b21f86a9df00320` |
| `mg2010v5_nacional.zip` | https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marc_geo/702825292812_s.zip | 2026-09-18 | 100,391,544 | `298d13d6ba8017785006fb0aff9b5a020d7d80f4bfc5fff0afcaeacb6746b4ca` |
| `pobproy_quinq1.csv` | https://www.datos.gob.mx/dataset/f2b9b220-3ef7-4e3a-bde6-87e1dac78c6a/resource/3c3092be-583e-4490-8c23-67ef9a64b198/download/pobproy_quinq1.csv | 2026-09-18 | 36,658,654 | `1a8f07be08de082a0c33404f0fbce9d9292845a8c8290153a6ad2e1889bab31a` |

Productos: MG 2020 = *Marco Geoestadístico, Censo de Población y Vivienda 2020* (UPC 889463807469);
MG 2010 = *Marco Geoestadístico 2010 versión 5.0, Censo 2010* (UPC 702825292812; solo se publica
nacional; no incluye capa de AGEB rurales). CONAPO = *Población a mitad de año por municipio y
grupos quinquenales de edad (1990-2040)*, conjunto "Proyecciones de población" de datos.gob.mx
(recurso modificado 2025-05-11), conciliado con las proyecciones estatales 2020–2070 (base Censo 2020).
`conapo.segob.gob.mx` no respondió desde esta red (timeout); se usó el espejo oficial datos.gob.mx.

## Archivos añadidos a data/processed y data/reference (sha256, primeros 16)

| archivo | sha256 | origen |
|---|---|---|
| `censo/inegi_2010/resultados_ageb_urbana_09_cpv2010.csv` | `d98aadf655cd28aa` | copia byte a byte del zip 2010 |
| `censo/inegi_2020/conjunto_de_datos_ageb_urbana_09_cpv2020.csv` | `f009565b17a855c6` | copia byte a byte del zip 2020 |
| `conapo/pobproy_quinq1.csv` | `1a8f07be08de082a` | descarga directa, sin cambios |
| `marco_geo/mg2020/09a.shp` · `09ar.shp` · `09mun.shp` (+ sidecars) | `890ac3e36221ba3a` · `01393689005021a5` · `d5459db2bffa28df` | copia byte a byte del zip MG 2020 |
| `marco_geo/mg2010v5/ageb_urbana_2010_09.gpkg` | `2883467358b9adc0` | filtro `CVEGEO` que empieza con 09 de `AGEB_urb_2010_5.shp`; CRS original |
| `marco_geo/mg2010v5/municipios_2010_09.gpkg` | `18f8b0727df998d6` | filtro `CVE_ENT = 09` de `Municipios_2010_5.shp` |
| `reference/ageb_cdmx.geojson` | `ffa74ecffe3b6750` | `tools/build_geo.py` (09a + 09ar, EPSG:4326, make_valid) |
| `reference/ageb_cdmx_simplificado.geojson` | `8a83338552ea2469` | mapshaper 0.6, 25 % de vértices, keep-shapes, 5 decimales |

## Superseded

| archivo | parte | reemplazo | motivo |
|---|---|---|---|
| `censo/AGEB_2010_2020.xlsx` | hoja `AGEB 2010` | `censo/inegi_2010/resultados_ageb_urbana_09_cpv2010.csv` | truncada: 1,965 de 2,432 AGEB, faltan 015–017 y 32 AGEB de 014 |
| `censo/AGEB_2010_2020.xlsx` | hoja `AGEB 2020` | `censo/inegi_2020/conjunto_de_datos_ageb_urbana_09_cpv2020.csv` | idéntica al oficial en 0–14 por alcaldía (0.00 %); se prefiere la fuente primaria |

El xlsx se conserva sin cambios; `tools/convertir_censo.py` lo sigue leyendo solo para contraste.

## Movimientos

| fecha | ruta anterior | ruta nueva | cómo | motivo |
|---|---|---|---|---|
| 2026-09-18 | `data/processed/enut_2024_cdmx_uso_tiempo.csv` | `data/processed/enut/enut_2024_cdmx_uso_tiempo.csv` | `git mv` | una carpeta por fuente |
| 2026-09-18 | `data/processed/espacio_publico_cdmx_depurado.geojson` | `data/processed/espacios_publicos/espacio_publico_cdmx_depurado.geojson` | `mv` | restituye la ruta rastreada por git |
| 2026-09-18 | `data/processed/AGEB_2010_2020.xlsx` | `data/processed/censo/AGEB_2010_2020.xlsx` | `mv` | archivo no rastreado; carpeta de la fuente censal |

## Derivados (data/interim/, no versionados; `make datos`)

| archivo | script |
|---|---|
| `censo_ageb_{2010,2020}.parquet`, `censo_ageb_panel.parquet` | `tools/build_censo.py` |
| `censo_xlsx_ageb_{2010,2020}.parquet` (contraste) | `tools/convertir_censo.py` |
| `conapo_mun_quinq.parquet`, `conapo_mun_0a14.parquet` | `tools/build_conapo.py` |
| `equivalencia_ageb_2010_2020.parquet` | `tools/build_geo.py` |
