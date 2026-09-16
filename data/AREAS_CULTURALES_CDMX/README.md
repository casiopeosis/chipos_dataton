# Áreas culturales de la Ciudad de México

## Fuente principal

Sistema de Información Cultural (SIC),
Secretaría de Cultura.

## Alcance

Se integran exclusivamente:

- TEATRO
- CENTRO_CULTURAL
- CINE

No se incluyen museos, galerías, bibliotecas, auditorios,
librerías, escuelas artísticas ni otros equipamientos culturales.

## Registros

Total integrado: 868

- Teatros: 157
- Centros culturales: 584
- Cines: 127

## Tipo de gestión

La clasificación se derivó a partir de la adscripción reportada
por el SIC.

Resultados:

- PUBLICO: 577
- PRIVADO: 228
- MIXTO: 4
- NO_DETERMINADO: 59

La adscripción original se conserva íntegramente en
`adscripcion_original`.

Algunas adscripciones del SIC contenían diferencias únicamente
por espacios iniciales o finales. Para fines de clasificación,
estas variantes se normalizaron mediante eliminación de espacios
externos, sin modificar el valor original almacenado en cada
registro.

## PILARES

Los PILARES que aparecen en el directorio SIC de centros culturales
se conservan.

Se marcan mediante:

- `es_pilares = SI`
- `dataset_relacionado = PILARES`

Esto permite evitar doble conteo cuando se combine esta capa con
el dataset específico de PILARES.

PILARES identificados: 287

## Coordenadas

Los registros utilizan las coordenadas proporcionadas por el SIC.

GeoJSON:

- geometría: Point
- orden de coordenadas: [longitud, latitud]

## Calidad

- IDs culturales duplicados: 0
- Registros sin nombre: 0
- Registros sin latitud: 0
- Registros sin longitud: 0
- Registros sin correspondencia de clasificación: 0
- Registros para revisión manual: 59

## Archivos

- `areas_culturales_cdmx_depurado.csv`
- `areas_culturales_cdmx_depurado.geojson`
- `areas_culturales_cdmx_depurado.xlsx`
- `clasificacion_adscripciones.csv`
- `diccionario_campos.csv`
- `resumen_calidad.json`
- `fuente/`

## Consideraciones

Los registros no se deduplican entre categorías culturales.

Un mismo inmueble puede ser registrado por el SIC como teatro,
centro cultural o cine de acuerdo con las funciones que desempeña.

La base representa una fotografía del directorio SIC descargado,
no una serie histórica anual.

Las fechas de fundación y modificación son atributos del registro
y no deben interpretarse como snapshots históricos del directorio.
