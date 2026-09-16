# Estudio de población por edad en la Ciudad de México, 2020

Esta carpeta contiene un estudio de la estructura de la población por edad y sexo en la Ciudad de México. El archivo está preparado para apoyar el análisis de demanda potencial del proyecto y para combinarse, con ciertas precauciones, con bases del DENUE sobre infancias, salud, gimnasios, recreación y servicios para personas mayores.

## Contenido de la carpeta

```text
estudio_edades_cdmx_2020/
├── README.md
└── datos/
    └── ESTUDIO_POR_EDAD_CDMX_2020.xlsx
```

El Excel conserva las bases utilizadas, las fórmulas de cálculo, las tablas por alcaldía y localidad, las gráficas y las notas metodológicas.

## Periodo y cobertura

| Elemento | Descripción |
|---|---|
| Año de referencia | **2020** |
| Entidad | Ciudad de México |
| Nivel principal | Alcaldía |
| Nivel complementario | Localidad |
| Desagregación | Sexo y grupos quinquenales de edad |
| Población con edad especificada | 9,200,318 personas |
| Alcaldías | 16 |

El periodo 2020 se tomó de la identificación proporcionada para el proyecto. Las bases originales incluidas en el libro no tienen una columna de año, por lo que el README y la hoja `Método` conservan esta aclaración.

## Qué contiene cada hoja

| Hoja | Contenido |
|---|---|
| `Resumen 2020` | Resultados generales, distribución por edad, estimaciones para 0-5, 6-11 y 12-17 años y una gráfica |
| `Por alcaldía` | Comparación de las 16 alcaldías y estimación de población de 0 a 17 años |
| `Base alcaldía` | 576 registros: 16 alcaldías × 2 sexos × 18 grupos de edad |
| `Base localidad` | 3,276 registros por alcaldía, localidad, sexo y grupo de edad |
| `Método` | Fuentes, criterios, limitaciones y conciliación de las bases |
| `Diccionario` | Descripción de variables de una fuente AGEB; no contiene observaciones de población por AGEB |

## Resultados principales

| Grupo del proyecto | Población estimada | Porcentaje de la población |
|---|---:|---:|
| Primera infancia, 0 a 5 años | 592,685.4 | 6.44% |
| Niñez escolar, 6 a 11 años | 694,710.4 | 7.55% |
| Adolescencia, 12 a 17 años | 755,610.6 | 8.21% |
| Total estimado, 0 a 17 años | **2,043,006.4** | **22.21%** |

Las cantidades tienen decimales porque son estimaciones por prorrateo. No representan fracciones reales de personas. Para presentaciones pueden redondearse a personas enteras, pero conviene conservar los decimales durante los cálculos.

Resultados territoriales destacados:

- Iztapalapa concentra el mayor volumen estimado de población de 0 a 17 años: aproximadamente 452,751 personas.
- Milpa Alta tiene la mayor proporción estimada de población de 0 a 17 años: 29.1% de su población con edad especificada.

## Ponderaciones que ya utiliza el Excel

La fuente presenta grupos de cinco años: 0-4, 5-9, 10-14, 15-19 y así sucesivamente. El proyecto necesita los grupos 0-5, 6-11 y 12-17. Para aproximarlos, el Excel supone que la población está distribuida uniformemente dentro de cada rango quinquenal.

### Primera infancia: 0 a 5 años

```text
Población 0-5 = población 0-4 + 1/5 de la población 5-9
```

Se toma el 100% del grupo 0-4 y el 20% del grupo 5-9, que corresponde al año de edad 5.

### Niñez escolar: 6 a 11 años

```text
Población 6-11 = 4/5 de la población 5-9 + 2/5 de la población 10-14
```

Se toma el 80% del grupo 5-9, correspondiente a las edades 6, 7, 8 y 9, y el 40% del grupo 10-14, correspondiente a las edades 10 y 11.

### Adolescencia: 12 a 17 años

```text
Población 12-17 = 3/5 de la población 10-14 + 3/5 de la población 15-19
```

Se toma el 60% del grupo 10-14, correspondiente a las edades 12, 13 y 14, y el 60% del grupo 15-19, correspondiente a las edades 15, 16 y 17.

### Tabla de ponderaciones demográficas

| Rango original | Peso en 0-5 | Peso en 6-11 | Peso en 12-17 | Parte no utilizada en 0-17 |
|---|---:|---:|---:|---:|
| 0-4 | 1.00 | 0.00 | 0.00 | 0.00 |
| 5-9 | 0.20 | 0.80 | 0.00 | 0.00 |
| 10-14 | 0.00 | 0.40 | 0.60 | 0.00 |
| 15-19 | 0.00 | 0.00 | 0.60 | 0.40 |

Estas ponderaciones sirven para **repartir edades**, no para indicar que un grupo sea más importante que otro.

## Supuesto y limitación del prorrateo

El método supone que dentro de cada grupo quinquenal hay aproximadamente la misma cantidad de personas por cada edad. Por ejemplo, se considera que cada edad del grupo 5-9 representa una quinta parte del total.

Este supuesto permite obtener una aproximación cuando no existen datos por edad simple, pero no sustituye un conteo censal exacto. Si posteriormente se consigue población por edad individual, deben reemplazarse estas estimaciones.

## Nivel geográfico real

Este archivo **no contiene observaciones de población por AGEB**.

- La base principal permite trabajar por alcaldía.
- La base complementaria permite trabajar por alcaldía y localidad.
- La hoja `Diccionario` menciona una variable llamada `ageb`, pero solo describe el campo; no contiene filas territoriales con población.

Las bases DENUE de salud e infancias sí contienen la ubicación AGEB de cada establecimiento. No deben unirse directamente por AGEB con este Excel porque aquí falta la población correspondiente a esa clave.

Para un análisis real por AGEB se necesita otra base del Censo 2020 que incluya, como mínimo, la clave completa de AGEB y la población objetivo.

## Diferencia entre las dos bases de población

| Base | Registros | Suma de población |
|---|---:|---:|
| Por alcaldía | 576 | 9,200,318 |
| Por localidad | 3,276 | 9,163,177 |
| Diferencia | — | 37,141 |

La base por localidad registra 37,141 personas menos, una diferencia de aproximadamente 0.40% frente al agregado por alcaldía. Por esta razón:

- la base por alcaldía debe utilizarse como fuente principal para indicadores de toda la ciudad y por alcaldía;
- la base por localidad puede utilizarse para exploración territorial, dejando registrada la diferencia;
- no se deben mezclar totales de ambas bases dentro del mismo indicador.

## Cómo combinarla con las demás bases de datos

Las bases deben combinarse después de definir una unidad geográfica común. Con los archivos actuales, la opción más segura es la **alcaldía**.

| Base | Unidad que cuenta | Año | Geografía disponible | Unión recomendada con este Excel |
|---|---|---:|---|---|
| Población por edad | Personas | 2020 | Alcaldía y localidad | Base de demanda |
| DENUE infancias | Establecimientos | Según edición | Alcaldía, localidad y AGEB | Agregar primero por alcaldía y después unir |
| DENUE salud | Establecimientos | Según edición | Alcaldía, localidad y AGEB | Agregar primero por alcaldía y después unir |
| DENUE gimnasios o recreación | Establecimientos | Según edición | Alcaldía, localidad y AGEB | Agregar primero por alcaldía y después unir |
| DENUE servicios para personas mayores | Establecimientos | Según edición | Alcaldía, localidad y AGEB | Agregar primero por alcaldía y después unir |

### Paso 1. Elegir la población objetivo

| Tipo de servicio | Denominador recomendado |
|---|---|
| Guarderías, estancias y preescolares | Población estimada de 0 a 5 años |
| Primarias y servicios para niñez escolar | Población estimada de 6 a 11 años |
| Secundarias y servicios juveniles | Población estimada de 12 a 17 años |
| Espacios generales para infancias | Población estimada de 0 a 17 años |
| Salud general | Población total |
| Salud infantil o psicológica para menores | Población de 0 a 17 años, únicamente después de confirmar que el servicio atiende a menores |
| Servicios para personas mayores | Población de 60 años o más, o de 65 años o más, según la definición del proyecto |
| Gimnasios o recreación sin edad definida | Población total o el grupo objetivo expresamente definido |

El DENUE de salud no indica de forma general la edad de los pacientes. No es correcto dividir todos los hospitales o consultorios entre la población infantil sin verificar primero que el servicio esté dirigido a ese grupo.

### Paso 2. Normalizar nombres de alcaldía

Antes de unir las bases se deben corregir problemas de codificación y homologar mayúsculas, acentos y espacios. Por ejemplo, `Álvaro Obregón`, `ALVARO OBREGON` y una versión con acentos dañados deben convertirse en una misma clave.

```python
import re
import unicodedata


def clave_texto(valor):
    valor = "" if valor is None else str(valor)
    valor = unicodedata.normalize("NFKD", valor)
    valor = valor.encode("ascii", "ignore").decode("ascii")
    valor = re.sub(r"\s+", " ", valor.strip().upper())
    return valor
```

La normalización no puede recuperar caracteres que ya aparecen como `�`. Esos casos deben corregirse con un catálogo de las 16 alcaldías antes de hacer la unión.

### Paso 3. Agregar el DENUE antes de unirlo

Una alcaldía puede tener miles de establecimientos. Si se une la población directamente con cada registro DENUE, la población se repetirá muchas veces. Primero se deben contar o ponderar los establecimientos por alcaldía y categoría.

```python
import pandas as pd

denue = pd.read_csv(
    "denue_infancias_cdmx_2016_10.csv",
    encoding="utf-8-sig",
    dtype=str
)

denue["alcaldia_clave"] = denue["Alcaldía"].map(clave_texto)

oferta = (
    denue.groupby("alcaldia_clave")
         .size()
         .reset_index(name="establecimientos")
)
```

### Paso 4. Leer la tabla de población por alcaldía

```python
poblacion = pd.read_excel(
    "datos/ESTUDIO_POR_EDAD_CDMX_2020.xlsx",
    sheet_name="Por alcaldía",
    header=4
)

poblacion = poblacion[
    poblacion["Alcaldía"].notna() &
    (poblacion["Alcaldía"] != "CDMX (suma)")
].copy()

poblacion["alcaldia_clave"] = poblacion["Alcaldía"].map(clave_texto)
```

### Paso 5. Unir una fila de población con una fila de oferta por alcaldía

```python
analisis = poblacion.merge(
    oferta,
    on="alcaldia_clave",
    how="left",
    validate="one_to_one"
)

analisis["establecimientos"] = (
    analisis["establecimientos"].fillna(0)
)
```

El parámetro `validate="one_to_one"` ayuda a detectar si alguna base quedó con alcaldías duplicadas después de la agregación.

## Indicadores de cobertura

Una forma clara de comparar alcaldías es calcular establecimientos por cada 10,000 personas del grupo objetivo.

### Cobertura para infancias

```text
Cobertura infantil = establecimientos para infancias / población de 0-17 × 10,000
```

### Cobertura general de salud

```text
Cobertura de salud = establecimientos principales de salud / población total × 10,000
```

### Cobertura para personas mayores

```text
Cobertura para personas mayores = servicios dirigidos a personas mayores / población de 60+ × 10,000
```

Una tasa de establecimientos no mide camas, capacidad, personal, calidad, horarios ni accesibilidad. Debe interpretarse como disponibilidad registrada, no como cobertura efectiva.

## Ponderación opcional de los establecimientos DENUE

Las bases DENUE contienen registros con diferente nivel de relación y certeza. Los conteos sin ponderar deben conservarse como resultado principal. Si el proyecto requiere un indicador complementario, puede utilizarse la siguiente propuesta inicial.

### Peso de relevancia propuesto

| Tipo de registro | Ejemplo en Infancias | Ejemplo en Salud | Peso propuesto |
|---|---|---|---:|
| Relación directa o alcance principal | `Directa por código` | `Principal` | 1.00 |
| Relación mixta o complementaria | `Mixta por código` | `Complementario` | 0.50 |
| Inclusión únicamente por palabra clave | `Probable por palabras` | Regla condicionada por palabra | 0.25 |
| Registro rechazado | Rechazado | Rechazado | 0.00 |

### Factor por revisión pendiente

| Revisión manual | Factor propuesto |
|---|---:|
| `NO` | 1.00 |
| `SI` | 0.50 |

El peso final sería:

```text
Peso final del establecimiento = peso de relevancia × factor de revisión
```

Ejemplos:

- registro directo sin revisión: `1.00 × 1.00 = 1.00`;
- registro complementario sin revisión: `0.50 × 1.00 = 0.50`;
- registro probable con revisión pendiente: `0.25 × 0.50 = 0.125`.

La oferta ponderada se obtiene sumando los pesos finales dentro de cada alcaldía y categoría.

Estas ponderaciones son una **propuesta metodológica**, no forman parte del DENUE ni del Censo y no representan capacidad de atención. Siempre deben presentarse junto con el conteo real de establecimientos y probarse con otros valores.

## Índice opcional de prioridad territorial

Si se necesita ordenar alcaldías para detectar posibles brechas, puede construirse un índice que combine demanda y baja cobertura.

```text
Demanda normalizada = rango percentil de la población objetivo
Déficit normalizado = 1 - rango percentil de la cobertura

Prioridad = 100 × (0.60 × demanda normalizada + 0.40 × déficit normalizado)
```

Interpretación:

- 60% corresponde al tamaño de la población objetivo;
- 40% corresponde a la falta relativa de establecimientos;
- una puntuación mayor indica una combinación de mayor demanda y menor cobertura relativa.

La ponderación 60/40 es una propuesta inicial. Deben compararse, como mínimo, tres escenarios:

| Escenario | Demanda | Déficit de cobertura |
|---|---:|---:|
| Equilibrado | 50% | 50% |
| Recomendado inicial | 60% | 40% |
| Prioridad demográfica | 70% | 30% |

Si el orden de las alcaldías cambia demasiado entre escenarios, el resultado es sensible a la ponderación y debe reportarse esa incertidumbre. La calidad de los datos debe mostrarse como indicador separado, no ocultarse dentro del puntaje.

## Uso de 2020 con ediciones DENUE de otros años

El Excel contiene un solo año de población. Si se combina con DENUE 2016, 2017 o 2026, existen dos opciones:

1. **Denominador fijo de 2020.** Permite comparar cómo cambia el número de establecimientos usando la misma población de referencia. El indicador debe llamarse, por ejemplo, `establecimientos por 10,000 habitantes usando población 2020`.
2. **Denominador del mismo año.** Es la opción preferible para medir cobertura anual, pero requiere una estimación o fuente poblacional comparable para cada año.

No debe presentarse una tasa calculada con establecimientos de 2016 y población de 2020 como si ambos datos correspondieran al mismo momento.

## Crecimiento poblacional

Este archivo por sí solo no permite calcular crecimiento de población porque contiene únicamente 2020.

Para medir crecimiento se necesita la misma variable, grupo de edad y geografía en otro año:

```text
Crecimiento porcentual = (población final - población inicial) / población inicial × 100
```

Para estudiar tendencia con mayor estabilidad conviene utilizar al menos tres momentos comparables. También deben revisarse los cambios territoriales y metodológicos entre censos.

La diferencia entre grupos de edad observados en 2020 no es crecimiento temporal. Por ejemplo, que el grupo 0-4 sea menor que el grupo 15-19 describe la estructura de edades de 2020, no el cambio de una misma población a través del tiempo.

## Recomendaciones de uso

- Utilizar `Base alcaldía` como fuente principal de población.
- Conservar `Base localidad` como apoyo exploratorio y documentar su diferencia de 37,141 personas.
- No unir por AGEB hasta conseguir observaciones censales por AGEB.
- Mantener los códigos geográficos como texto para conservar ceros a la izquierda.
- Corregir la codificación de caracteres de las bases DENUE antes de homologar nombres.
- Agregar el DENUE a la geografía elegida antes de unirlo con población.
- Reportar conteos reales y tasas, no únicamente puntajes ponderados.
- Mantener separadas las ponderaciones de edad, las ponderaciones de relevancia del DENUE y las ponderaciones de un índice territorial.
- Documentar el año de cada numerador y denominador.
- Validar manualmente las categorías amplias y los registros incluidos por palabras clave.

## Limitaciones

- El año 2020 no aparece como columna en las bases originales; proviene de la identificación del proyecto.
- Los grupos 0-5, 6-11 y 12-17 son estimaciones, no conteos exactos por edad simple.
- La base por localidad no concilia completamente con la base por alcaldía.
- El archivo no contiene observaciones poblacionales por AGEB.
- Un establecimiento DENUE no equivale a una capacidad determinada de servicio.
- DENUE no contiene matrícula, pacientes, camas, aforo, calidad ni demanda atendida.
- Los cambios de registros DENUE entre años pueden reflejar aperturas, cierres, actualizaciones, reclasificaciones o cambios de cobertura.
- Las ponderaciones propuestas deben someterse a análisis de sensibilidad y aprobación metodológica antes de usarse en resultados finales.

