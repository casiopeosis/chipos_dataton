# DENUE Comercios CDMX 11/2020 depurado

## Qué contiene

Esta carpeta contiene una selección temática del DENUE 11/2020
para analizar acceso territorial a productos de primera necesidad
en la Ciudad de México.

Se conservaron 85,309 de 474,328
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

En esta edición se identificaron 2 tiendas IMSS.

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
complejo (`nom_CenCom`) está vacío o registrado como `SIN NOMBRE`.

En esta edición se identificaron 17 registros
para revisión manual.

Estos registros se conservan en el conjunto de datos; la bandera no
indica que el establecimiento sea incorrecto, sino que existe
información incompleta sobre el complejo comercial reportado.


## Diferencia de esquema: CLEE

La edición DENUE 11/2020 utilizada no contiene el campo `clee`.
Por esta razón, el campo no se generó artificialmente y no se
realizó una evaluación de duplicados mediante CLEE.

La validación de duplicados disponible para esta edición se realiza
mediante el identificador original `id`.


## Calidad de los datos

- 0 IDs duplicados.
- No evaluable: el campo CLEE no existe en esta edición.
- 0 registros sin coordenadas.
- 0 registros sin clave AGEB completa.
- 2 tiendas IMSS detectadas.
- 17 registros para revisión manual.

## Formatos

- CSV: conserva todos los campos originales disponibles en DENUE
  y los campos derivados.
- GeoJSON: versión ligera con campos relevantes para análisis espacial.
- Shapefile: versión ligera con identificación, SCIAN, municipio, AGEB,
  contexto comercial y campos analíticos. La geometría contiene las
  coordenadas, por lo que latitud/longitud no se duplican en el DBF.
- XLSX: versión de análisis con hojas `datos`, `revision_manual`
  y `resumen`.

## Uso recomendado

Para análisis territorial, utilizar `cve_geo_ageb` cuando esté
completa o realizar una unión espacial de los puntos con
los polígonos AGEB.

No interpretar `fecha_alta` como fecha exacta de apertura.
