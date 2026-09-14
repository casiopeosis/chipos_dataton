# PILARES CDMX

## Descripción

Este conjunto contiene la ubicación y el estatus de los Puntos de Innovación, Libertad, Arte, Educación y Saberes (PILARES) de la Ciudad de México.

La base se utiliza en el proyecto como una capa de infraestructura comunitaria pública.

## Fuente original

El archivo original se conserva en:

`fuente/pilares_cdmx.csv`

La fuente contiene los siguientes campos:

- `CLAVE_ID`
- `NOMBRE_PILARES*`
- `ESTATUS`
- `REGION`
- `ALCALDIA`
- `LATITUD`
- `LONGITUD`

## Estructura general

La fuente contiene **300 registros**.

Distribución por estatus:

- **198** en operación;
- **11** recibidos por SECTEI;
- **23** con obra concluida sin recibir;
- **68** en obra.

No se detectaron IDs duplicados.

Tampoco se encontraron nombres ni alcaldías vacías.

## Coordenadas

De los 300 registros:

- **296** cuentan con latitud y longitud;
- **4** no cuentan con coordenadas;
- **0** coordenadas presentes quedaron fuera del rango aproximado esperado para la Ciudad de México.

Los cuatro registros sin coordenadas corresponden a PILARES con estatus `04. EN OBRA`.

No se imputaron ni geocodificaron coordenadas faltantes.

## Depuración realizada

Se generó una versión depurada:

`pilares_cdmx_depurado.csv`

No se eliminó ningún registro.

Los nombres de columnas fueron normalizados y se agregaron dos indicadores analíticos:

- `operativo`
- `tiene_coordenadas`

### Criterio de `operativo`

El campo `operativo` vale:

- `1` cuando `estatus_fuente = "01. EN OPERACIÓN"`
- `0` para cualquier otro estatus

Esto permite distinguir infraestructura actualmente disponible de infraestructura recibida, concluida o en proceso.

### Criterio de `tiene_coordenadas`

El campo `tiene_coordenadas` vale:

- `1` cuando el registro cuenta con latitud y longitud;
- `0` cuando falta alguna de las coordenadas.

## Campos de la versión depurada

La versión depurada contiene:

- `clave_id`
- `nombre_pilares`
- `estatus_fuente`
- `region`
- `alcaldia`
- `latitud`
- `longitud`
- `operativo`
- `tiene_coordenadas`

El significado de cada campo está documentado en:

`diccionario_campos_depurados.csv`

## Calidad de los datos

El archivo:

`resumen_calidad.json`

documenta:

- número total de registros;
- distribución por estatus;
- duplicados;
- campos vacíos;
- disponibilidad de coordenadas;
- criterios de depuración;
- advertencias de uso.

## Consideraciones para el análisis

Para análisis de cobertura actual se recomienda utilizar principalmente registros con:

`operativo = 1`

y, cuando se requiera análisis espacial:

`tiene_coordenadas = 1`

Los registros con estatus distinto de operación se conservan porque pueden ser útiles para estudiar infraestructura próxima a incorporarse a la oferta pública.

Sin embargo, no deben interpretarse como servicios actualmente disponibles.

## Uso previsto en el proyecto

La capa puede utilizarse posteriormente para cruces espaciales con AGEB u otras unidades territoriales.

Entre los indicadores posibles se encuentran:

- número de PILARES operativos por AGEB;
- PILARES por habitante;
- distancia al PILARES operativo más cercano;
- identificación de zonas con baja cobertura de infraestructura comunitaria;
- comparación entre oferta actual e infraestructura en construcción o concluida;
- combinación con variables demográficas, áreas verdes, espacio público y otros servicios urbanos.

## Archivos

La estructura principal del conjunto es:

PILARES CDMX/
├── README.md
├── diccionario_campos_depurados.csv
├── pilares_cdmx_depurado.csv
├── resumen_calidad.json
└── fuente/
    └── pilares_cdmx.csv
