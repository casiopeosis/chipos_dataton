# DENUE Comercios CDMX 10/2016 depurado

## Qué contiene

Esta carpeta contiene una selección temática del DENUE 10/2016
para analizar acceso territorial a productos de primera necesidad
en la Ciudad de México.

Se conservaron 86,534 de 464,583
registros originales.

De los registros conservados:

- 80,101 corresponden a establecimientos de primera necesidad.
- 6,433 corresponden a oferta complementaria.

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
complejo (`nom_CenCom`) está vacío o registrado como `SIN NOMBRE`.

En esta edición se identificaron 53 registros
para revisión manual.

Distribución:

- 46 en `CENTRAL DE ABASTO`.
- 7 en `TIANGUIS, BAZAR O PULGA`.

Todos cumplen la regla de revisión porque `nom_CenCom` está vacío
o registrado como `SIN NOMBRE`.

Estos registros se conservan en el conjunto de datos. La bandera no
indica que el establecimiento sea incorrecto, sino que existe
información incompleta sobre el complejo comercial reportado.

## Diferencias de esquema

La edición DENUE 10/2016 utilizada no contiene el campo `CLEE`.

Por esta razón, `CLEE` no se generó artificialmente y no fue posible
evaluar duplicados mediante esta clave.

La validación de duplicados disponible para esta edición se realizó
mediante el campo original `id`.

## Codificación de caracteres

La fuente 10/2016 fue probada directamente antes de la depuración.

La lectura correcta del DBF se realiza utilizando UTF-8.

La lectura como `latin1` produce caracteres incorrectos en textos
acentuados, por ejemplo `misceláneas`, `lácteos` o `minisúper`.

Por ello, esta edición se procesó explícitamente con UTF-8.

## Claves geográficas

Se comprobó que los campos:

- `cve_ent`
- `cve_mun`
- `cve_loc`
- `ageb`

ya están almacenados como texto y conservan sus ceros a la izquierda
en la fuente utilizada.

El campo derivado `cve_geo_ageb` se construye concatenando:

`cve_ent + cve_mun + cve_loc + ageb`

sin modificar las claves originales.

Las claves geográficas deben tratarse como texto al analizarlas para
evitar que programas como Excel o pandas oculten ceros a la izquierda.

## Calidad de los datos

- 0 IDs duplicados.
- No evaluable: el campo CLEE no existe en esta edición.
- 0 registros sin coordenadas.
- 0 registros sin clave AGEB completa.
- 1 tienda IMSS detectada.
- 53 registros para revisión manual.

## Formatos

- CSV: conserva todos los campos originales disponibles en DENUE
  y los campos derivados del proyecto.
- GeoJSON: versión ligera con campos relevantes para análisis espacial.
- Shapefile: versión ligera con identificación, SCIAN, municipio,
  AGEB, contexto comercial y campos analíticos.
- XLSX: versión de análisis con hojas `datos`, `revision_manual`
  y `resumen`.

## Uso recomendado

Para análisis territorial, utilizar `cve_geo_ageb` cuando esté
completa o realizar una unión espacial de los puntos con
los polígonos AGEB.

No interpretar `fecha_alta` como fecha exacta de apertura.
