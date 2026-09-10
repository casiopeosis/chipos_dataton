# DENUE CDMX 05/2026 depurado para el Datatón 2026

## Qué contiene

- `denue_cdmx_05_2026_depurado.csv`: todos los campos originales más clasificación y controles de calidad, en UTF-8.
- `denue_cdmx_05_2026_depurado.geojson`: puntos listos para mapas web.
- `shapefile/denue_cdmx_05_2026_depurado.*`: capa SHP filtrada, con los campos originales y ocho campos derivados.
- `denue_cdmx_05_2026_depurado.xlsx`: vista de revisión, resumen y tabla analítica.
- `criterios_scian.csv`: códigos conservados, conteos y justificación.
- `diccionario_campos_depurados.csv`: campos derivados y referencia a los campos originales.
- `resumen_calidad.json`: controles reproducibles.
- `fuente/`: metadatos y diccionario originales de INEGI.

## Fecha y cobertura

El archivo corresponde a la edición **DENUE 05/2026**, para la entidad **09, Ciudad de México**. Los metadatos internos indican modificación el **20 de mayo de 2026**. El nombre externo del ZIP no incluye el año; por eso se tomó la edición declarada por INEGI dentro del archivo.

## Regla de depuración

Se conservaron 3,252 de 462,732 registros (0.703%). Se eliminaron 459,480 registros cuyas actividades no miden la oferta elegida por el equipo.

Se incluyeron:

1. Clubes deportivos y centros de acondicionamiento físico (SCIAN 713941, 713942, 713943 y 713944), citados en `Dataton.pdf`.
2. Escuelas de deporte (611621 y 611622), como oferta deportiva complementaria.
3. Asilos y residencias para personas mayores (623311 y 623312).
4. Centros de cuidado diurno para ancianos o personas con discapacidad (624121 y 624122). Estos registros quedan marcados para revisión porque el código mezcla dos poblaciones.

No se incluyeron parques de diversiones, apuestas, venta o fabricación de artículos deportivos, promotores de espectáculos, oficinas administrativas de bienestar social ni servicios comunitarios genéricos. Tampoco se intentó obtener áreas verdes, parques públicos o PILARES desde DENUE: la propuesta los asigna a Datos Abiertos CDMX, INAPAM y OpenStreetMap.

## Controles de calidad

- IDs duplicados: 0.
- CLEE duplicadas: 0.
- Registros sin coordenadas: 0.
- Registros sin clave AGEB completa: 0.
- Registros con bandera de revisión: 128.
- Registros que comparten nombre normalizado, actividad y coordenadas: 2. Se conservaron porque un mismo inmueble puede contener unidades económicas distintas y cada registro debe revisarse con `id` y `clee` antes de descartarlo.

## Uso recomendado

Para el mapa, use `cve_geo_ageb` cuando esté completa o haga una unión espacial de las coordenadas con los polígonos AGEB del Marco Geoestadístico. No interprete `fecha_alta` como fecha exacta de apertura: es la fecha de incorporación al DENUE. Para comparar aperturas y cierres se necesitan, como exige el reto, al menos otras dos ediciones históricas procesadas con la misma lista de códigos y una regla explícita de emparejamiento por `clee`.
