# Servicios de salud en la Ciudad de México

Este conjunto de datos contiene establecimientos del **Directorio Estadístico Nacional de Unidades Económicas (DENUE)** relacionados con servicios de salud en la Ciudad de México.

La selección incluye hospitales, clínicas, consultorios, atención psicológica o de salud mental, laboratorios, ambulancias, farmacias, asilos, residencias y otros servicios de cuidado. Los datos corresponden a **octubre de 2016** y utilizan la versión **SCIAN 2013**.

## Objetivo

El objetivo es identificar y ubicar establecimientos que forman parte de la infraestructura de salud de la Ciudad de México. La base puede utilizarse para:

- contar establecimientos de salud por alcaldía, localidad o AGEB;
- separar servicios principales de servicios complementarios;
- identificar hospitales, clínicas, consultorios, farmacias y servicios de salud mental;
- distinguir registros que necesitan revisión manual;
- localizar establecimientos mediante coordenadas geográficas;
- comparar distintas ediciones del DENUE, siempre que se mantengan reglas de selección compatibles.

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
| Establecimientos de salud seleccionados | **27,003** |

Cita sugerida: **INEGI, Directorio Estadístico Nacional de Unidades Económicas (DENUE), Ciudad de México, edición octubre de 2016.**

## Contenido del archivo ZIP

| Archivo | Contenido | Registros |
|---|---|---:|
| `denue_salud_cdmx_2016_10.csv` | Base principal de establecimientos de salud seleccionados | 27,003 |
| `registros_revision_manual_salud_2016_10.csv` | Subconjunto de la base principal que requiere revisión humana | 3,520 |
| `registros_rechazados_salud_2016_10.csv` | Estructura destinada a registros rechazados; en esta edición solo contiene encabezados | 0 |
| `catalogo_scian_salud_2016_10.csv` | Resumen de los códigos SCIAN, subcategorías, reglas y cantidades | 48 |
| `reporte_calidad_salud_2016_10.json` | Metadatos, configuración, resultados, conteos y advertencias | — |

El ZIP también contiene una carpeta `__MACOSX` y archivos cuyo nombre comienza con `._`. Son metadatos creados por macOS y no forman parte de la base. Se pueden ignorar al subir el proyecto a GitHub.

## Resumen de la base principal

| Indicador | Registros |
|---|---:|
| Alcance principal | 18,662 |
| Alcance complementario | 8,341 |
| Hospitales | 476 |
| Sanatorios identificados por nombre | 84 |
| Clínicas y consultorios | 17,262 |
| Salud mental o psicológica | 2,440 |
| Farmacias | 6,433 |
| Residencias y servicios de cuidado | 233 |
| Registros con revisión manual | 3,520 |

La base contiene:

- las 16 alcaldías de la Ciudad de México;
- 29 subcategorías de salud;
- 48 códigos SCIAN diferentes;
- 2,165 claves geográficas AGEB completas diferentes;
- 27,003 identificadores `ID` únicos.

Los indicadores de hospitales, sanatorios, clínicas, salud mental, farmacias y residencias **no son categorías totalmente excluyentes**. Hay 851 registros que cumplen más de uno de esos indicadores. Por esta razón, no deben sumarse sus cantidades para obtener el total general.

## Alcance de los registros

### Alcance principal

Incluye establecimientos clasificados en los prefijos SCIAN:

- `621`: servicios médicos, consultorios, laboratorios, atención ambulatoria y servicios auxiliares;
- `622`: hospitales.

### Alcance complementario

Incluye establecimientos que apoyan o complementan la atención de salud:

- farmacias con y sin minisúper;
- residencias y asilos;
- centros de cuidado diurno;
- agrupaciones de autoayuda;
- algunos servicios sociales incluidos por palabras clave.

La columna `Alcance` permite separar ambos grupos. Para un análisis centrado únicamente en atención médica y hospitalaria puede utilizarse el valor `Principal`.

## Reglas de selección

La base se construyó con los siguientes criterios:

1. Los códigos cuyo prefijo es `621` o `622` se incluyeron como servicios principales de salud.
2. Los códigos `464111` y `464112` se incluyeron como farmacias.
3. Determinados códigos de los grupos `623` y `624` se incluyeron como residencias, asilos, cuidados o asistencia relacionada.
4. Algunas actividades sociales amplias solo se incluyeron cuando el nombre contenía palabras vinculadas con salud.
5. La identificación de salud mental utilizó términos como `PSICOLOG`, `PSIQUIATR`, `SALUD MENTAL`, `TERAP`, `REHABILIT`, `ADICC`, `SUICID`, `NEURO` y `VIOLENCIA`.

Los términos de búsqueda de salud mental son amplios. Por ejemplo, `TERAP`, `REHABILIT` y `NEURO` pueden aparecer en servicios que no son exclusivamente psicológicos. Estos registros deben interpretarse con cuidado.

## Principales subcategorías

| Subcategoría | Registros |
|---|---:|
| Consultorio dental | 6,895 |
| Farmacia sin minisúper | 5,612 |
| Consultorio de medicina especializada | 3,668 |
| Consultorio de medicina general | 3,591 |
| Grupo de autoayuda para adicciones | 1,664 |
| Otro consultorio para el cuidado de la salud | 1,300 |
| Laboratorio médico y de diagnóstico | 871 |
| Farmacia con minisúper | 821 |
| Psicología | 676 |
| Hospital general | 340 |
| Audiología y terapias | 282 |
| Clínica de consultorios médicos | 278 |
| Nutrición y dietética | 269 |

El catálogo completo se encuentra en `catalogo_scian_salud_2016_10.csv`.

## Campos principales

La base principal tiene 44 columnas. Las más importantes son:

| Grupo | Columnas | Descripción |
|---|---|---|
| Identificación | `Registro origen`, `ID`, `CLEE`, `Establecimiento`, `Razón social` | Identificadores y nombre de la unidad económica |
| Clasificación | `Código SCIAN`, `Actividad SCIAN`, `Categoría del proyecto`, `Subcategoría` | Actividad económica y clasificación utilizada |
| Selección | `Sector`, `Alcance`, `Regla de inclusión`, `Palabras clave detectadas` | Explica cómo se incluyó el establecimiento |
| Indicadores | Columnas que comienzan con `Es...` | Variables binarias: `1` significa que cumple el criterio y `0` que no lo cumple |
| Revisión | `Revisión manual`, `Motivo de revisión` | Señala los casos que necesitan verificación humana |
| Tamaño | `Personal ocupado`, `Tipo de unidad económica` | Rango de trabajadores y tipo de unidad |
| Dirección | `Alcaldía`, `Localidad`, `Asentamiento`, `Código postal`, `Vialidad`, `Número exterior` | Ubicación administrativa y domicilio |
| Geografía | `Clave geográfica AGEB`, `AGEB`, `Manzana`, `Latitud`, `Longitud` | Ubicación territorial y coordenadas |
| Temporalidad | `Fecha de alta DENUE`, `Año de alta DENUE`, `Año de datos`, `Mes de corte`, `Edición DENUE` | Fecha de incorporación y periodo de la fuente |
| Procedencia | `Versión SCIAN declarada`, `Archivo fuente` | Versión del catálogo y archivo de origen |

## Datos de AGEB

Esta base **sí contiene el AGEB donde se localiza cada establecimiento**. Los 27,003 registros tienen valores en `Clave geográfica AGEB`, `AGEB`, `Manzana`, `Latitud` y `Longitud`.

La clave AGEB indica la ubicación del establecimiento, pero la base no contiene la población residente en esa zona. Para calcular establecimientos por habitante, cobertura territorial o demanda potencial es necesario unirla con datos del Censo mediante una clave geográfica compatible.

Los códigos geográficos deben conservarse como texto para no perder ceros a la izquierda.

## Cómo extraer el ZIP

En macOS o Linux:

```bash
unzip SALUD_CDMX_2016_10.zip
cd SALUD_CDMX_2016_10
```

## Uso básico en Python

Se recomienda leer todas las columnas como texto para conservar correctamente los códigos SCIAN, postales, AGEB y manzana.

```python
import pandas as pd

archivo = "denue_salud_cdmx_2016_10.csv"

df = pd.read_csv(
    archivo,
    encoding="utf-8-sig",
    dtype=str
)

print(df.shape)
print(df.columns.tolist())
```

### Trabajar solo con el alcance principal

```python
salud_principal = df[df["Alcance"] == "Principal"].copy()
```

### Excluir los casos pendientes de revisión manual

```python
base_para_analisis = df[
    (df["Alcance"] == "Principal") &
    (df["Revisión manual"] == "NO")
].copy()
```

### Filtrar una categoría

```python
hospitales = df[df["Es hospital"] == "1"].copy()
clinicas_consultorios = df[df["Es clínica o consultorio"] == "1"].copy()
salud_mental = df[df["Es salud mental o psicológica"] == "1"].copy()
farmacias = df[df["Es farmacia"] == "1"].copy()
residencias = df[df["Es residencia o cuidado"] == "1"].copy()
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

## Problema en la clasificación del sector

La columna `Sector` contiene:

| Valor | Registros |
|---|---:|
| Privado | 18,031 |
| No especificado | 8,972 |
| Público | 0 |

Este resultado **no significa que no existan establecimientos públicos**. Se encontraron 741 registros cuya descripción de `Actividad SCIAN` dice expresamente `sector público`, pero fueron guardados como `No especificado` en la columna `Sector`.

Para crear una clasificación auxiliar basada únicamente en el texto explícito de la actividad puede utilizarse:

```python
actividad = df["Actividad SCIAN"].fillna("")

df["Sector SCIAN explícito"] = "No especificado"

df.loc[
    actividad.str.contains("sector privado", case=False, na=False),
    "Sector SCIAN explícito"
] = "Privado"

df.loc[
    actividad.str.contains("sector pÃºblico|sector público", case=False, na=False),
    "Sector SCIAN explícito"
] = "Público"
```

Esta corrección solo identifica los casos en que la descripción SCIAN menciona el sector de forma explícita. No permite clasificar automáticamente todos los registros restantes.

## Problemas de codificación de texto

Los CSV están guardados como UTF-8, pero muchos valores contienen caracteres mal interpretados, por ejemplo `pÃºblico` en lugar de `público`. También existen textos con el carácter de sustitución `�`, lo que indica que parte de la información original pudo perderse durante una conversión anterior.

La siguiente función puede reparar los casos reversibles. Los textos que ya contienen `�` deben revisarse contra la fuente original.

```python
def reparar_texto(valor):
    if not isinstance(valor, str):
        return valor

    if "�" in valor:
        return valor

    if "Ã" not in valor and "Â" not in valor:
        return valor

    try:
        return valor.encode("latin1").decode("utf-8")
    except UnicodeError:
        return valor


for columna in df.columns:
    df[columna] = df[columna].map(reparar_texto)
```

Antes de reemplazar el archivo original se recomienda revisar una muestra de los resultados.

## Revisión manual

El archivo `registros_revision_manual_salud_2016_10.csv` contiene exactamente los 3,520 registros cuyo campo `Revisión manual` tiene el valor `SI`.

| Motivo de revisión | Registros |
|---|---:|
| Posible duplicado por mismo nombre y coordenadas | 3,058 |
| Código postal faltante o inválido | 243 |
| SCIAN mezcla atención a personas mayores y discapacidad | 109 |
| Posible duplicado y código postal faltante o inválido | 99 |
| Inclusión por palabra clave; confirmar servicio de salud | 10 |
| Inclusión por palabra clave y código postal inválido | 1 |

Los posibles duplicados tienen identificadores `ID` distintos. No deben eliminarse automáticamente sin comprobar el nombre, razón social, dirección, actividad y coordenadas.

## Calidad e integridad

- La base principal no contiene filas completamente duplicadas.
- Los 27,003 valores de `ID` son únicos dentro de esta edición.
- El archivo de revisión manual es un subconjunto completo de la base principal.
- El catálogo suma 27,003 registros, por lo que coincide con la base principal.
- No faltan claves geográficas AGEB, manzanas, latitudes ni longitudes.
- Los 27,003 registros tienen el indicador de coordenadas válidas.
- Hay 343 códigos postales marcados como inválidos; 224 de ellos están vacíos.
- El campo `CLEE` está vacío en todos los registros.
- El campo `Año de alta DENUE` está vacío en todos los registros, aunque `Fecha de alta DENUE` sí contiene información.
- El archivo de registros rechazados no contiene observaciones.

Si se necesita el año de alta como una columna independiente, puede extraerse del final de `Fecha de alta DENUE`:

```python
df["Año de alta calculado"] = (
    df["Fecha de alta DENUE"]
      .str.extract(r"(\d{4})$", expand=False)
)
```

## Recomendaciones para comparar varios años

Para analizar las ediciones de 2016 a 2026:

1. Conservar un archivo separado por edición.
2. Mantener `Año de datos`, `Mes de corte`, `Edición DENUE`, `Versión SCIAN declarada` y `Archivo fuente`.
3. Aplicar reglas equivalentes de inclusión y exclusión en todos los años.
4. Revisar los cambios entre versiones SCIAN antes de comparar categorías.
5. No eliminar registros repetidos entre años: pueden representar establecimientos que permanecen activos en el directorio.
6. No depender únicamente de `ID` para seguir un establecimiento a través del tiempo. En esta edición `CLEE` está vacío; puede ser necesario comparar nombre, dirección y coordenadas.
7. Revisar cambios en los límites o claves AGEB antes de unir datos territoriales.
8. Separar el alcance principal del complementario para evitar que las farmacias dominen los resultados de atención médica.

La diferencia en el número de establecimientos entre dos ediciones no debe llamarse automáticamente crecimiento o cierre. También puede deberse a actualizaciones del directorio, cambios de cobertura, reclasificaciones SCIAN o modificaciones en las reglas de limpieza.

## Limitaciones

- DENUE registra establecimientos, no pacientes, camas, capacidad, calidad ni demanda atendida.
- Un establecimiento no equivale a una unidad de servicio comparable: un consultorio pequeño y un hospital aparecen como un registro cada uno.
- La fecha de alta en DENUE indica incorporación al directorio, no apertura confirmada.
- La ausencia de un establecimiento en otra edición no demuestra por sí sola que haya cerrado.
- `Sanatorio` no tiene una clase SCIAN exclusiva y se detectó mediante el nombre; puede coincidir con clínicas u hospitales.
- Los códigos `624121` y `624122` mezclan atención a personas mayores y discapacidad.
- Los códigos sociales condicionados por palabras clave requieren revisión manual.
- La clasificación de salud mental usa términos amplios y puede incluir servicios no exclusivamente psicológicos.
- La clasificación público/privado debe corregirse o validarse antes de presentar resultados por sector.
- La base contiene la ubicación AGEB de los establecimientos, pero no población, cobertura efectiva ni accesibilidad.

