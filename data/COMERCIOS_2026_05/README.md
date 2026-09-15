# DENUE Comercios CDMX 05/2026 depurado

## Qué contiene

Esta carpeta contiene una selección temática del DENUE 05/2026
para analizar acceso territorial a productos de primera necesidad
en la Ciudad de México.

Se conservaron 88,738 de 462,732
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

## Infraestructura comercial

Se conserva la información original de DENUE sobre:

- mercados públicos
- centrales de abasto
- centros y plazas comerciales
- tianguis, bazares o pulgas

Estos campos describen el complejo donde está ubicado el
establecimiento y no deben interpretarse automáticamente como
un inventario único de instalaciones.

## Formatos

- CSV: conserva todos los campos originales DENUE y los campos derivados.
- GeoJSON: versión ligera con campos relevantes para análisis espacial.
- Shapefile: versión ligera con identificación, SCIAN, municipio, AGEB,
  contexto comercial y campos analíticos. La geometría contiene las
  coordenadas, por lo que latitud/longitud no se duplican en el DBF.
- XLSX: versión de análisis con hojas `datos`, `revision_manual` y `resumen`.

## Uso recomendado

Para análisis territorial, utilizar `cve_geo_ageb` cuando esté
completa o realizar una unión espacial de los puntos con
los polígonos AGEB.

No interpretar `fecha_alta` como fecha exacta de apertura.
