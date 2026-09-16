# Espacios dedicados a infancias en la Ciudad de México

Esta carpeta contiene una selección de establecimientos del **Directorio Estadístico Nacional de Unidades Económicas (DENUE)** relacionados con primera infancia, niñez y adolescencia en la Ciudad de México.

La base incluye escuelas, guarderías, estancias infantiles, espacios de educación especial, clubes deportivos, actividades culturales o recreativas y algunos servicios de apoyo social. Los datos corresponden a la edición de **octubre de 2016** y utilizan la versión **SCIAN 2013**.

## Objetivo

El objetivo es identificar y ubicar establecimientos que puedan formar parte de la infraestructura disponible para infancias en la Ciudad de México. La base puede utilizarse para:

- contar establecimientos por alcaldía, localidad o AGEB;
- identificar espacios dirigidos a primera infancia, niñez o adolescencia;
- separar actividades principales de actividades complementarias;
- localizar establecimientos mediante latitud y longitud;
- comparar la oferta registrada en distintas ediciones del DENUE, tomando en cuenta los cambios de cobertura y clasificación.

## Fuente y periodo

| Elemento | Valor |
|---|---|
| Fuente | INEGI, DENUE |
| Archivo original | `denue_09_1016_shp.zip` |
| Entidad | Ciudad de México, clave 09 |
| Año de los datos | **2016** |
| Mes de corte | Octubre, mes 10 |
| Edición | `2016-10` |
| Versión SCIAN declarada | 2013 |
| Registros originales del DENUE | 464,583 |
| Establecimientos seleccionados | **11,589** |

Cita sugerida: **INEGI, Directorio Estadístico Nacional de Unidades Económicas (DENUE), Ciudad de México, edición octubre de 2016.**

## Archivos incluidos

Los nombres recibidos son identificadores automáticos. En la siguiente tabla se explica qué contiene cada archivo y se propone un nombre más claro para trabajar en GitHub.

| Archivo recibido | Contenido | Registros | Nombre sugerido |
|---|---|---:|---|
| `cc76a270-e35e-4090-bc00-c355525fca72.csv` | Base principal de establecimientos seleccionados | 11,589 | `denue_infancias_cdmx_2016_10.csv` |
| `1ddb03ba-8f98-4c5a-8df5-41b0c59ab0cc.csv` | Subconjunto de la base principal que requiere revisión manual | 2,652 | `revision_manual_infancias_2016_10.csv` |
| `0d14a5c5-acdb-46e8-b176-4cc6e646238b.csv` | Catálogo resumen de reglas, códigos SCIAN y cantidades | 59 | `catalogo_scian_infancias_2016_10.csv` |
| `95086d63-69d3-4404-9fd3-4b65970264c3.csv` | Copia exactamente igual al catálogo anterior | 59 | No es necesario conservar ambas copias |
| `ef907304-4a60-4346-b640-d1b7372dfa9f.json` | Reporte de calidad, configuración, conteos y advertencias | — | `reporte_calidad_infancias_2016_10.json` |

Los dos archivos de catálogo son idénticos: tienen el mismo contenido y el mismo hash SHA-256. Para evitar confusiones, se recomienda conservar solo uno.

El reporte JSON menciona también un archivo de registros rechazados, pero ese archivo no se encuentra entre los documentos recibidos.

## Resumen de la base principal

| Indicador | Registros |
|---|---:|
| Alcance principal | 8,886 |
| Alcance complementario | 2,703 |
| Dedicación directa por código SCIAN | 9,514 |
| Actividad mixta por código SCIAN | 1,687 |
| Selección probable por palabras clave | 388 |
| Registros que requieren revisión manual | 2,652 |
| Registros con enfoque de primera infancia | 4,253 |
| Sector privado identificado | 5,848 |
| Sector no especificado | 5,741 |

La base contiene las 16 alcaldías de la Ciudad de México, 23 subcategorías y 46 códigos SCIAN diferentes.

Algunas de las principales subcategorías son:

- preescolar: 3,088 establecimientos;
- primaria: 2,597;
- guardería o estancia infantil: 1,146;
- secundaria general o técnica: 971;
- escuela con varios niveles educativos: 875;
- club o actividad deportiva: 821;
- educación especial: 209;
- recreación o cultura infantil: 296;
- apoyo social o residencia: 278.

## Cómo se seleccionaron los establecimientos

La selección combina códigos SCIAN y palabras encontradas en el nombre del establecimiento o en su razón social.

### 1. Dedicación directa por código

Incluye actividades cuyo código SCIAN se relaciona directamente con infancias, como preescolares, primarias, secundarias, educación especial, guarderías y estancias infantiles.

### 2. Actividad mixta por código

Incluye actividades que pueden atender a menores de edad y también a personas adultas. Por ejemplo, escuelas de arte, idiomas, deporte y algunos clubes.

### 3. Selección probable por palabras

Incluye establecimientos de clases SCIAN amplias únicamente cuando su nombre contiene términos como `INFANTIL`, `JUVENIL`, `GUARDERÍA`, `CENDI`, `MATERNAL`, `LUDOTECA`, `PREESCOLAR` o `CASA HOGAR`.

Estos casos deben verificarse manualmente porque una palabra en el nombre no garantiza que el establecimiento atienda exclusivamente a menores de edad.

### 4. Reducción de falsos positivos

Se descartaron expresiones que podían producir coincidencias incorrectas, como `NIÑOS HÉROES`, `DIVINO NIÑO`, `NIÑO JESÚS`, `SANTO NIÑO` y `NIÑO DOCTOR`.

## Campos principales

La base principal tiene 52 columnas. Las más importantes se agrupan de la siguiente manera:

| Grupo | Columnas | Descripción |
|---|---|---|
| Identificación | `Registro origen`, `ID`, `CLEE`, `Establecimiento`, `Razón social` | Identificadores y nombre de la unidad económica |
| Clasificación | `Código SCIAN`, `Actividad SCIAN`, `Subcategoría`, `Población objetivo estimada` | Actividad económica y clasificación utilizada en el proyecto |
| Criterio de inclusión | `Alcance`, `Dedicación a infancias`, `Regla de inclusión`, `Palabras clave detectadas` | Explica por qué se incluyó el registro |
| Indicadores | Columnas que comienzan con `Es...` y `Enfoque primera infancia` | Variables binarias: `1` significa que cumple el criterio y `0` que no lo cumple |
| Revisión | `Revisión manual`, `Motivo de revisión` | Indica si el registro necesita verificación humana |
| Ubicación | `Alcaldía`, `Localidad`, `Asentamiento`, `Código postal`, `Vialidad`, `Número exterior` | Dirección del establecimiento |
| Geografía | `Clave geográfica AGEB`, `AGEB`, `Manzana`, `Latitud`, `Longitud` | Ubicación territorial y coordenadas |
| Temporalidad | `Fecha de alta DENUE`, `Año de alta DENUE`, `Año de datos`, `Mes de corte`, `Edición DENUE` | Fechas y edición de la fuente |
| Procedencia | `Versión SCIAN declarada`, `Archivo fuente` | Versión del catálogo y archivo original |

### Datos de AGEB

Esta base **sí contiene la ubicación AGEB de los establecimientos**. Los 11,589 registros tienen valor en `Clave geográfica AGEB`, `AGEB` y `Manzana`. Se identificaron 2,083 claves geográficas AGEB completas diferentes.

Es importante no confundir esta información con datos demográficos. La clave AGEB indica dónde está ubicado cada establecimiento, pero esta base no contiene la población que vive en cada AGEB. Para calcular cobertura o establecimientos por habitante se necesita unirla con una base del Censo mediante una clave geográfica compatible.

## Uso básico en Python

Se recomienda leer todas las columnas como texto para conservar ceros a la izquierda en códigos postales, claves AGEB, manzanas y códigos SCIAN.

```python
import pandas as pd

archivo = "denue_infancias_cdmx_2016_10.csv"

df = pd.read_csv(
    archivo,
    encoding="utf-8-sig",
    dtype=str
)

print(df.shape)
print(df.columns.tolist())
```

### Filtrar los registros de alcance principal

```python
principal = df[df["Alcance"] == "Principal"].copy()
```

### Filtrar primera infancia

```python
primera_infancia = df[df["Enfoque primera infancia"] == "1"].copy()
```

### Obtener los casos que no requieren revisión manual

```python
base_para_analisis = df[
    (df["Alcance"] == "Principal") &
    (df["Revisión manual"] == "NO")
].copy()
```

### Contar establecimientos por alcaldía

```python
por_alcaldia = (
    df.groupby("Alcaldía")
      .size()
      .reset_index(name="establecimientos")
      .sort_values("establecimientos", ascending=False)
)

print(por_alcaldia)
```

### Contar establecimientos por AGEB

```python
por_ageb = (
    df.groupby(["Alcaldía", "Clave geográfica AGEB"])
      .size()
      .reset_index(name="establecimientos")
)
```

## Problema de codificación detectado

Los CSV están guardados como UTF-8, pero varios textos ya contienen caracteres mal interpretados, por ejemplo `CoyoacÃ¡n` en lugar de `Coyoacán`. Esto ocurrió antes de guardar los archivos y no se corrige únicamente cambiando el parámetro `encoding`.

La siguiente función repara únicamente los valores que presentan señales comunes de este problema:

```python
def reparar_texto(valor):
    if not isinstance(valor, str):
        return valor

    if "Ã" not in valor and "Â" not in valor:
        return valor

    try:
        return valor.encode("latin1").decode("utf-8")
    except UnicodeError:
        return valor


columnas_texto = df.columns

for columna in columnas_texto:
    df[columna] = df[columna].map(reparar_texto)
```

Antes de reemplazar los archivos originales, conviene revisar una muestra de los textos corregidos.

## Recomendaciones para combinar varios años

Para trabajar con ediciones de 2016 a 2026:

1. Conservar un CSV separado por edición.
2. Mantener las columnas `Año de datos`, `Mes de corte`, `Edición DENUE` y `Archivo fuente`.
3. Homologar nombres de columnas y tipos de datos antes de unir los archivos.
4. No eliminar establecimientos repetidos entre años: su repetición sirve para estudiar su permanencia en el directorio.
5. Eliminar duplicados únicamente dentro de una misma edición y después de revisar `ID`, `CLEE`, nombre, dirección y coordenadas.
6. Revisar cambios de versión SCIAN y cambios territoriales de las AGEB.
7. No interpretar la diferencia de registros entre dos años como crecimiento automático de la oferta. Parte del cambio puede deberse a actualizaciones del DENUE, reclasificaciones o modificaciones en las reglas de selección.

## Limitaciones

- DENUE registra establecimientos, no matrícula, capacidad, calidad ni demanda atendida.
- La fecha de alta en DENUE no confirma la fecha de apertura del establecimiento.
- La ausencia de un registro en una edición posterior no demuestra por sí sola que el establecimiento cerró.
- La educación media superior puede incluir personas de 18 años o más.
- Las escuelas de arte, idiomas, deporte y los clubes suelen atender edades mixtas.
- Los registros incluidos únicamente por palabras clave necesitan revisión manual.
- El campo `CLEE` está vacío en todos los registros de esta edición.
- El sector público o privado se infirió a partir del texto de la actividad SCIAN. En esta edición hay 5,741 registros con sector no especificado y ningún registro etiquetado directamente como público. Esto no significa que no existan establecimientos públicos.
- Aunque todos los registros tienen clave AGEB y coordenadas válidas, varias unidades pueden compartir ubicación.
- La base no debe mezclarse con servicios pediátricos de salud ni con comercios de productos infantiles, porque esos temas pertenecen a categorías distintas del proyecto.

## Revisión manual

El archivo `1ddb03ba-8f98-4c5a-8df5-41b0c59ab0cc.csv` contiene exactamente los 2,652 registros de la base principal cuyo campo `Revisión manual` tiene el valor `SI`.

La revisión debe confirmar, cuando sea posible:

- que el establecimiento atiende realmente a menores de edad;
- el grupo de edad atendido;
- si el servicio es público, privado o social;
- si la actividad sigue vigente;
- si la clasificación y la subcategoría son correctas.

## Integridad de los archivos

- La base principal no tiene filas completamente duplicadas.
- Los 11,589 valores de `ID` son únicos dentro de esta edición.
- El subconjunto de revisión manual está contenido completamente en la base principal.
- La suma de la columna `Registros` del catálogo es igual a 11,589, por lo que coincide con la base principal.
- No faltan claves geográficas AGEB, latitudes ni longitudes en los registros seleccionados.

