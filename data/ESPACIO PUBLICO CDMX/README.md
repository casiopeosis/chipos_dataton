# Espacio público de la Ciudad de México

## Descripción

Este conjunto de datos contiene la localización de espacios públicos de la Ciudad de México, incluyendo áreas verdes, camellones, instalaciones deportivas o recreativas, plazas y parques nacionales, estatales o urbanos.

La fuente original compila información proveniente de:

- CentroGeo (2020);
- cartas topográficas de la Ciudad de México a escala 1:20,000 de INEGI (2008);
- Marco Geoestadístico de INEGI (2019);
- Censo de Población y Vivienda de INEGI (2010);
- Comisión Nacional de Áreas Naturales Protegidas (CONANP).

La descarga original se obtuvo en formato Shapefile.

## Estructura de la fuente original

El shapefile original presenta una estructura poco convencional:

- contiene **1 solo registro**;
- dicho registro contiene **8,499 partes geométricas**;
- el único atributo disponible es `Id`;
- el valor del atributo original es `Id = 1`;
- no existen atributos individuales de nombre, categoría o tipo de espacio público para cada componente geométrico.

El sistema de coordenadas original es:

- **WGS 84 / UTM Zone 14N**
- **EPSG:32614**
- unidades en metros.

## Depuración realizada

Para facilitar el análisis espacial, la geometría multiparte original fue desagregada en componentes poligonales individuales.

Se identificaron:

- **8,499 partes geométricas originales**;
- **8,498 componentes con superficie válida**;
- **1 geometría degenerada con área igual a 0 m²**;
- **0 huecos interiores detectados**.

La parte original **4057** fue excluida por presentar área geométrica igual a cero.

Las 8,498 partes restantes fueron conservadas sin aplicar filtros por tamaño.

Se generó un identificador nuevo para cada componente válido:

- `EP000001`
- `EP000002`
- `EP000003`
- etc.

La columna `parte_original` permite conservar la relación con la posición original de cada parte dentro del shapefile fuente.

## Superficie

Las superficies fueron calculadas usando el sistema de coordenadas original UTM, cuyas unidades son metros.

Resultados:

- superficie mínima: **0.02 m²**;
- superficie máxima: **15,239,366.58 m²**;
- superficie total registrada: **94,994,430.00 m²**;
- equivalente: **9,499.443 ha**.

Distribución de tamaños:

- 7 componentes menores de 1 m²;
- 57 componentes menores de 10 m²;
- 1,222 componentes menores de 100 m²;
- 112 componentes mayores de 100,000 m² (10 ha);
- 9 componentes mayores de 1,000,000 m² (100 ha).

Las geometrías de superficie muy pequeña o muy grande fueron conservadas debido a que la fuente no contiene información suficiente para determinar objetivamente si deben eliminarse.

## Archivos

### Fuente original

`fuente/diccionario_datos.csv`

Diccionario de datos publicado junto con el conjunto original.

### Shapefile original

La carpeta `shapefile/` conserva los archivos originales:

- `espacio_publico_cdmx.shp`
- `espacio_publico_cdmx.dbf`
- `espacio_publico_cdmx.shx`
- `espacio_publico_cdmx.prj`
- `espacio_publico_cdmx.shp.xml`

Estos archivos no fueron modificados.

### Datos depurados

`espacio_publico_cdmx_depurado.csv`

Contiene un registro por componente geométrico válido con los siguientes campos:

- `id_espacio_publico`
- `id_fuente`
- `parte_original`
- `area_m2`
- `area_ha`

`espacio_publico_cdmx_depurado.geojson`

Contiene los mismos 8,498 registros junto con su geometría.

Las geometrías fueron transformadas de **EPSG:32614** a **WGS 84 / EPSG:4326** para su uso en GeoJSON.

### Documentación

`diccionario_campos_depurados.csv`

Describe los campos generados durante la depuración.

`resumen_calidad.json`

Contiene métricas de calidad, estructura original, resultados de depuración y advertencias de uso.

## Consideraciones para el análisis

Este conjunto debe interpretarse principalmente como una capa de **cobertura espacial general de espacio público**.

La fuente original no permite distinguir individualmente si cada componente corresponde a parque, plaza, camellón, instalación deportiva, instalación recreativa, área verde, área natural protegida u otro tipo de espacio público.

Por esta razón, no se asignaron categorías inferidas durante la depuración.

Además, un componente geométrico no debe interpretarse necesariamente como un espacio público independiente. Un mismo espacio real podría estar representado por más de una geometría.

## Uso previsto en el proyecto

La capa puede utilizarse posteriormente para cruces espaciales con AGEB u otras unidades territoriales.

Entre los indicadores posibles se encuentran:

- superficie de espacio público por AGEB;
- porcentaje del territorio cubierto por espacio público;
- metros cuadrados de espacio público por habitante;
- identificación de zonas con baja disponibilidad espacial de espacio público;
- análisis conjunto con áreas verdes, población y otros servicios urbanos.

Debe evitarse sumar directamente esta capa con otros conjuntos como el inventario de áreas verdes sin realizar primero una revisión espacial de superposiciones, ya que ambas fuentes pueden representar algunas superficies comunes.
