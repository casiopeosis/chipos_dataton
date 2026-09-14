# Inventario de Áreas Verdes de la Ciudad de México

Datos del **Inventario de Áreas Verdes de la Ciudad de México** preparados para su uso en el Datatón.

El objetivo de esta depuración es conservar la información espacial del inventario y añadir una clasificación analítica que permita distinguir entre:

- cobertura verde;
- espacios verdes con posible función recreativa;
- vegetación asociada a equipamiento urbano;
- áreas de protección ecológica;
- registros que requieren revisión manual.

## Fuente

**Inventario de Áreas Verdes de la Ciudad de México**

Portal de Datos Abiertos de la Ciudad de México:

https://datos.cdmx.gob.mx/dataset/inventario-de-areas-verdes-en-la-ciudad-de-mexico

Edición utilizada: **2021**.

Se conservaron como fuentes originales:

- GeoJSON oficial;
- diccionario de datos;
- Shapefile oficial.

Los archivos originales se encuentran en las carpetas `fuente/` y `shapefile/`.

## Archivos

### `inventario_areas_verdes_cdmx_depurado.geojson`

Archivo espacial principal.

Contiene los polígonos originales disponibles en el GeoJSON oficial, además de las variables analíticas generadas durante la depuración.

### `inventario_areas_verdes_cdmx_depurado.csv`

Versión tabular de los registros depurados.

Contiene los mismos atributos analíticos que el GeoJSON, pero no incluye geometría.

### `criterios_areas_verdes.csv`

Tabla de reglas utilizada para clasificar cada combinación de categoría y subcategoría de la fuente.

Permite reproducir y revisar las decisiones de clasificación sin modificar directamente los datos originales.

### `resumen_calidad.json`

Resumen de los principales controles de calidad y estadísticas de la depuración.

### `fuente/`

Contiene los archivos fuente descargados del Portal de Datos Abiertos de la Ciudad de México.

### `shapefile/`

Contiene los componentes del Shapefile oficial utilizados para verificar la información espacial de la fuente.

## Depuración realizada

El inventario contiene **11,739 registros**.

No se eliminaron registros del universo original.

Se generó un identificador único para cada registro con el formato:

`AV000001`, `AV000002`, ...

La fuente publicada no contiene un identificador único utilizable de forma consistente, por lo que `id_area_verde` es un campo generado específicamente para este proyecto.

Los valores vacíos y el valor `"0"` en el campo de nombre se normalizaron como valores nulos.

Las categorías y subcategorías originales se conservaron en:

- `categoria_fuente`
- `subcategoria_fuente`

## Clasificación analítica

La clasificación distingue entre **cobertura verde** y **oferta verde recreativa**.

Estas dos variables no deben interpretarse como equivalentes.

Por ejemplo, un camellón, una azotea verde o vegetación dentro de una institución pueden aportar cobertura vegetal, pero no necesariamente constituyen un espacio recreativo accesible para la población.

Se generaron los siguientes campos:

### `tipo_analitico`

Clasificación derivada de la categoría y subcategoría originales.

Los principales tipos son:

- `oferta_verde_recreativa`
- `cobertura_verde_vial`
- `cobertura_verde_fragmentada`
- `cobertura_verde_no_recreativa`
- `vegetacion_en_equipamiento`
- `proteccion_ecologica`
- `revisar`

### `usar_cobertura_verde`

Indica si el registro puede utilizarse para análisis de cobertura vegetal.

### `usar_oferta_recreativa`

Indica si el registro puede utilizarse como parte de la oferta de espacios verdes recreativos.

No implica que se haya verificado de manera independiente el acceso público al sitio.

### `revision_manual`

Marca registros cuya categoría o subcategoría no permite tomar una decisión analítica suficientemente clara de manera automática.

Existen **595 registros** marcados para revisión manual.

Las reglas completas se encuentran en `criterios_areas_verdes.csv`.

## Geometría

El GeoJSON oficial contiene:

- **10,601 Polygon**
- **1,082 MultiPolygon**
- **56 registros sin geometría**

En total existen **11,683 registros con geometría utilizable**.

Se comparó el GeoJSON con el Shapefile oficial para verificar los 56 registros faltantes.

Los mismos 56 registros aparecen en el Shapefile sin partes ni puntos geométricos utilizables, por lo que no fue posible recuperar su ubicación a partir de los archivos oficiales.

Estos registros se conservaron con:

- `geometry = null`
- `area_m2 = null`
- `area_ha = null`

No se asignó un área igual a cero, ya que la ausencia de geometría representa información desconocida y no una superficie de 0 m².

## Superficie

Para las **11,683 geometrías disponibles** se calcularon:

- `area_m2`: superficie en metros cuadrados;
- `area_ha`: superficie en hectáreas.

Las superficies se calcularon geodésicamente utilizando WGS84.

Resultados generales:

- superficie mínima calculada: **2.26 m²**;
- superficie máxima calculada: **2,478,293.69 m²**;
- suma de superficies registradas: **67,360,004.02 m²**;
- equivalente: **6,736.00 ha**.

La suma de superficies no debe interpretarse automáticamente como la superficie verde única de la Ciudad de México.

Los polígonos pueden presentar superposición espacial, por lo que para calcular cobertura territorial debe realizarse una unión espacial de geometrías antes de sumar superficies y evitar doble conteo.

## Campos del archivo depurado

| Campo | Descripción |
|---|---|
| `id_area_verde` | Identificador único generado para el proyecto |
| `nombre` | Nombre del área cuando está disponible |
| `categoria_fuente` | Categoría original de la fuente |
| `subcategoria_fuente` | Subcategoría original de la fuente |
| `tipo_analitico` | Clasificación analítica generada |
| `usar_cobertura_verde` | Indica si puede utilizarse para análisis de cobertura verde |
| `usar_oferta_recreativa` | Indica si puede utilizarse como oferta verde recreativa |
| `revision_manual` | Indica si el registro requiere revisión |
| `motivo_criterio` | Justificación de la clasificación aplicada |
| `area_m2` | Superficie calculada en metros cuadrados |
| `area_ha` | Superficie calculada en hectáreas |
| `geometry` | Geometría espacial; disponible únicamente en el GeoJSON |

## Uso recomendado

Para estudiar **cobertura vegetal**, utilizar principalmente:

`usar_cobertura_verde = true`

Para estudiar **oferta verde con función recreativa**, utilizar:

`usar_oferta_recreativa = true`

Los registros con:

`revision_manual = true`

deben revisarse antes de incorporarlos definitivamente a análisis que dependan de acceso público o función recreativa.

Para estimar indicadores por AGEB, colonia, alcaldía u otra unidad territorial, se recomienda realizar una intersección espacial entre las geometrías del inventario y los polígonos de la unidad geográfica correspondiente.

## Limitaciones

- 56 registros de la fuente oficial no cuentan con geometría utilizable.
- Una parte importante de los registros no tiene un nombre informativo.
- La clasificación de cobertura y función recreativa es una clasificación analítica desarrollada para este proyecto y no forma parte de la fuente oficial.
- El acceso público real a cada espacio no fue verificado individualmente.
- Los registros marcados con `revision_manual` requieren análisis adicional.
- Las superficies no deben sumarse directamente para estimar cobertura territorial si existen polígonos superpuestos.
- La fuente corresponde a la edición 2021 y no representa necesariamente el estado actual de todas las áreas verdes de la ciudad.
