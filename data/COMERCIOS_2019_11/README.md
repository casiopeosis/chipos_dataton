# DENUE Comercios CDMX 11/2019 depurado

## Qué contiene

Esta carpeta contiene una selección temática del DENUE 11/2019
para analizar acceso territorial a productos de primera necesidad
en la Ciudad de México.

Se conservaron 85,710 de 466,301
registros originales.

## Criterio principal

Se incluyeron establecimientos de:

- abarrotes
- supermercados
- minisúpers
- carnicerías
- pollerías
- pescaderías
- frutas y verduras
- semillas y granos
- lácteos y embutidos
- otros alimentos

Las farmacias se conservan como oferta complementaria.

## Tiendas IMSS

Se identifican mediante combinación de actividad SCIAN
de supermercado/minisúper y referencias explícitas a Tienda IMSS
en nombre o razón social.

En esta edición se identificó 1 tienda IMSS.

## Infraestructura comercial

Se conserva la información original de DENUE sobre:

- mercados públicos
- centrales de abasto
- centros y plazas comerciales
- tianguis, bazares o pulgas

Estos campos describen el complejo donde está ubicado el
establecimiento y no deben interpretarse automáticamente como
un inventario único de instalaciones.

## Revisión manual

Se marcan para revisión manual los establecimientos que DENUE reporta
dentro de infraestructura comercial relevante, pero cuyo nombre de
complejo (`NOM_CENCOM`) está vacío o registrado como `SIN NOMBRE`.

En esta edición se identificaron 9 registros
para revisión manual.

Estos registros se conservan en el conjunto de datos. La bandera de
revisión no indica que el establecimiento sea incorrecto, sino que
existe información incompleta sobre el complejo comercial reportado.

## Diferencias de esquema y normalización

La edición DENUE 11/2019 presenta algunas diferencias respecto de
ediciones posteriores utilizadas en este proyecto:

- Los nombres de los campos originales se encuentran en mayúsculas
  (`ID`, `NOM_ESTAB`, `CODIGO_ACT`, etc.).
- La fuente contiene un campo adicional `OID`.
- La fuente utilizada no contiene el campo `CLEE`.

Por esta razón, `CLEE` no se generó artificialmente y no fue posible
evaluar duplicados mediante esta clave.

La validación de duplicados disponible para esta edición se realizó
mediante el campo original `ID`.

### Normalización de claves geográficas

En esta edición algunas claves geográficas pueden ser interpretadas
como valores numéricos y perder ceros a la izquierda.

Para construir el campo derivado `cve_geo_ageb` se normalizaron las
claves geográficas a sus longitudes esperadas:

- `CVE_ENT`: 2 caracteres.
- `CVE_MUN`: 3 caracteres.
- `CVE_LOC`: 4 caracteres.
- `AGEB`: 4 caracteres.

Posteriormente se concatenaron como:

`CVE_ENT + CVE_MUN + CVE_LOC + AGEB`

Por ejemplo:

`09 + 012 + 0001 + 1890 = 0901200011890`

Esta normalización se aplica al campo derivado `cve_geo_ageb`.
Los campos originales del DENUE se conservan sin modificación en el CSV.

En las versiones ligeras para análisis espacial, la clave AGEB se
representa con cuatro caracteres para conservar los ceros a la izquierda.

Las claves geográficas deben tratarse como texto y no como valores
numéricos, ya que programas como Excel o pandas pueden ocultar los
ceros a la izquierda al inferir automáticamente el tipo de dato.

## Calidad de los datos

- 0 IDs duplicados.
- No evaluable: el campo CLEE no existe en esta edición.
- 0 registros sin coordenadas.
- 0 registros sin clave AGEB completa.
- 1 tienda IMSS detectada.
- 9 registros para revisión manual.

## Formatos

- CSV: conserva todos los campos originales disponibles en DENUE,
  incluido `OID`, además de los campos derivados del proyecto.
- GeoJSON: versión ligera con campos relevantes para análisis espacial.
- Shapefile: versión ligera con identificación, SCIAN, municipio,
  AGEB, contexto comercial y campos analíticos.
- XLSX: versión de análisis con hojas `datos`, `revision_manual`
  y `resumen`.

## Uso recomendado

Para análisis territorial, utilizar `cve_geo_ageb` cuando esté
completa o realizar una unión espacial de los puntos con
los polígonos AGEB.

No interpretar `FECHA_ALTA` como fecha exacta de apertura.
