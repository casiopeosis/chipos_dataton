# Estudio de población de todas las edades — Ciudad de México, 2020

Este paquete contiene el estudio corregido de la estructura de la población por edad y sexo en la Ciudad de México. Incluye **infancias, adultos jóvenes, adultos de edad media y adultos mayores**. Está preparado para apoyar el proyecto y combinarse, con las precauciones descritas aquí, con bases del DENUE de infancias, salud, gimnasios, recreación y servicios para personas mayores.

## Contenido de la carpeta

```text
paquete_estudio_todas_edades_cdmx_2020/
├── README.md
└── datos/
    └── ESTUDIO_POBLACION_TODAS_LAS_EDADES_CDMX_2020.xlsx
```

El Excel conserva las bases utilizadas, las fórmulas, el resumen general, la comparación de las 16 alcaldías, las gráficas, el método y el diccionario disponible.

## Año, cobertura y unidad de análisis

| Elemento | Descripción |
|---|---|
| Año de referencia | **2020** |
| Entidad | Ciudad de México |
| Fuente identificada para el proyecto | Censo 2020 |
| Nivel principal del análisis | Alcaldía |
| Nivel complementario | Localidad |
| Desagregación original | Sexo y grupos quinquenales de edad |
| Población con edad especificada | **9,200,318 personas** |
| Alcaldías | 16 |

El año 2020 procede de la identificación de los archivos y de la información proporcionada para el proyecto. Las bases originales incluidas en el libro no contienen una columna independiente de año; esta condición queda registrada también en la hoja `Método`.

## Grupos de edad utilizados

Los siguientes rangos son **definiciones operativas del proyecto**. Cubren toda la población sin traslapes ni huecos.

| Etapa de vida | Rango operativo |
|---|---:|
| Infancias | 0 a 17 años |
| Adultos jóvenes | 18 a 29 años |
| Adultos de edad media | 30 a 59 años |
| Adultos mayores | 60 años y más |

También se incluye `65+` como indicador complementario para proyectos o instituciones que definan a la población mayor a partir de los 65 años. No debe sumarse a `60+`, porque ya está contenida en ese grupo.

## Resultados generales de 2020

| Etapa de vida | Población estimada | Hombres | Mujeres | Porcentaje del total |
|---|---:|---:|---:|---:|
| Infancias, 0–17 | 2,043,006.4 | 1,036,962.4 | 1,006,044.0 | 22.21% |
| Adultos jóvenes, 18–29 | 1,727,049.6 | 863,573.6 | 863,476.0 | 18.77% |
| Adultos de edad media, 30–59 | 3,938,643.0 | 1,861,196.0 | 2,077,447.0 | 42.81% |
| Adultos mayores, 60+ | 1,491,619.0 | 638,412.0 | 853,207.0 | 16.21% |
| **Total** | **9,200,318.0** | **4,400,144.0** | **4,800,174.0** | **100.00%** |

Indicadores complementarios:

- Población adulta de 18 años y más: **7,157,311.6 personas**, equivalente a **77.79%**.
- Población de 65 años y más: **1,022,105 personas**, equivalente a **11.11%**.
- El grupo más grande es el de adultos de edad media, con **42.81%** de la población.

Los decimales de los grupos 0–17 y 18–29 se deben al prorrateo del grupo original 15–19. No representan fracciones reales de una persona. Para presentar resultados pueden redondearse, pero es preferible conservar los decimales durante los cálculos.

## Hallazgos territoriales

- **Iztapalapa** concentra el mayor volumen de población en las cuatro etapas de vida. En adultos mayores registra aproximadamente 262,064 personas de 60 años y más.
- **Milpa Alta** tiene las proporciones más altas de población de 0–17 años, con 29.1%, y de 18–29 años, con 20.8%.
- **Benito Juárez** tiene la mayor proporción de población de 30–59 años, con 49.4%.
- **Coyoacán** tiene la mayor proporción de población de 60 años y más, con 20.6%; le sigue Benito Juárez, con 20.1%.
- Después de Iztapalapa, los mayores volúmenes de población de 60+ se encuentran en Gustavo A. Madero y Coyoacán.

Una proporción alta y un volumen alto responden preguntas distintas. Para planear servicios conviene revisar ambos: el porcentaje describe la composición de la alcaldía y el volumen aproxima el número potencial de personas usuarias.

## Qué contiene cada hoja del Excel

| Hoja | Contenido |
|---|---|
| `Resumen 2020` | Resultados de las cuatro etapas, población adulta, 60+, distribución por sexo, gráfica y tabla quinquenal detallada |
| `Por alcaldía` | Comparación de las 16 alcaldías para 0–17, 18–29, 30–59, 60+ y 65+, con porcentajes y controles |
| `Base alcaldía` | 576 registros: 16 alcaldías × 2 sexos × 18 grupos de edad |
| `Base localidad` | 3,276 registros por alcaldía, localidad, sexo y grupo de edad |
| `Método` | Fuente, definiciones operativas, fórmulas, supuestos y limitaciones |
| `Diccionario` | Descripción de variables de una fuente AGEB; no contiene observaciones poblacionales por AGEB |

La columna `Control` de la hoja `Por alcaldía` debe ser cero. Esto confirma que los cuatro grupos suman exactamente la población total de cada alcaldía.

## Cómo se calcularon los grupos

La fuente organiza las edades en intervalos de cinco años. Solo el límite entre 17 y 18 años cae dentro de un grupo quinquenal. Se supone una distribución uniforme dentro de 15–19.

```text
Infancias 0–17 = 0–4 + 5–9 + 10–14 + 3/5 de 15–19

Adultos jóvenes 18–29 = 2/5 de 15–19 + 20–24 + 25–29

Adultos de edad media 30–59 = 30–34 + 35–39 + 40–44
                                  + 45–49 + 50–54 + 55–59

Adultos mayores 60+ = 60–64 + 65–69 + 70–74 + 75–79
                        + 80–84 + 85+

Indicador 65+ = 65–69 + 70–74 + 75–79 + 80–84 + 85+
```

### Tabla de ponderaciones demográficas

| Grupo original | 0–17 | 18–29 | 30–59 | 60+ |
|---|---:|---:|---:|---:|
| 0–4, 5–9 y 10–14 | 1.00 | 0.00 | 0.00 | 0.00 |
| 15–19 | 0.60 | 0.40 | 0.00 | 0.00 |
| 20–24 y 25–29 | 0.00 | 1.00 | 0.00 | 0.00 |
| 30–34 a 55–59 | 0.00 | 0.00 | 1.00 | 0.00 |
| 60–64 a 85+ | 0.00 | 0.00 | 0.00 | 1.00 |

Estas ponderaciones reparten edades; no significan que un grupo tenga mayor importancia social.

## Alcance geográfico real: no hay observaciones por AGEB

El archivo **no contiene filas de población por AGEB**.

- La base principal permite trabajar por alcaldía.
- La base complementaria permite trabajar por alcaldía y localidad.
- La hoja `Diccionario` describe un campo llamado `ageb`, pero no contiene observaciones territoriales con población para cada clave.

Las bases DENUE sí pueden incluir la AGEB de cada establecimiento. No deben unirse por AGEB con este Excel, porque aquí falta el denominador poblacional correspondiente. Para trabajar a ese nivel se necesita una tabla censal adicional con la clave completa de AGEB y la población por edad.

## Diferencia entre las bases de población

| Base | Registros | Suma de población |
|---|---:|---:|
| Por alcaldía | 576 | 9,200,318 |
| Por localidad | 3,276 | 9,163,177 |
| Diferencia | — | 37,141 |

La base por localidad tiene 37,141 personas menos que la base por alcaldía, una diferencia aproximada de 0.40%. Por ello:

- `Base alcaldía` debe usarse para resultados oficiales del paquete a nivel ciudad y alcaldía;
- `Base localidad` puede emplearse para exploración, documentando la diferencia;
- no deben mezclarse los totales de las dos bases dentro del mismo indicador.

## Cómo combinar el estudio con otras bases del proyecto

Con los archivos actuales, la unión más segura es por **alcaldía**. Primero debe agregarse cada base DENUE a una fila por alcaldía y categoría; después se une con la población. No se debe anexar la población directamente a cada establecimiento, porque se repetiría miles de veces.

| Base o tema | Población objetivo recomendada |
|---|---|
| Guarderías, preescolares y espacios generales para infancias | 0–17, o un subgrupo más específico si se calcula desde la base quinquenal |
| Salud general, hospitales y clínicas sin edad objetivo | Población total |
| Servicios pediátricos o psicológicos para menores | 0–17, después de verificar que el establecimiento atienda a menores |
| Servicios para jóvenes | 18–29 |
| Gimnasios y recreación para personas adultas jóvenes | 18–29 |
| Gimnasios, recreación o bienestar para población adulta amplia | 18+ o 30–59, según el alcance declarado |
| Servicios para personas mayores | 60+ como indicador principal; 65+ como análisis de sensibilidad |
| Espacios públicos o servicios sin segmentación etaria | Población total |

La elección del denominador debe responder al público real del servicio. Por ejemplo, no es correcto dividir todos los hospitales entre la población infantil ni todos los gimnasios entre 60+ si los registros no están dirigidos específicamente a esos grupos.

### Flujo recomendado

1. Limpiar y clasificar los establecimientos DENUE.
2. Homologar los nombres o claves de alcaldía.
3. Contar o ponderar los establecimientos por alcaldía y categoría.
4. Leer la hoja `Por alcaldía` de este Excel.
5. Unir una fila de oferta con una fila de población por alcaldía.
6. Calcular tasas usando el grupo de edad apropiado.
7. Conservar por separado el conteo real, la oferta ponderada y cualquier índice de prioridad.

### Ejemplo de unión en Python

```python
import re
import unicodedata
import pandas as pd


def clave_texto(valor):
    valor = "" if valor is None else str(valor)
    valor = unicodedata.normalize("NFKD", valor)
    valor = valor.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", valor.strip().upper())


# Una fila por establecimiento DENUE.
denue = pd.read_csv("denue_limpio.csv", encoding="utf-8-sig", dtype=str)
denue["alcaldia_clave"] = denue["Alcaldía"].map(clave_texto)

# Agregar antes de unir con población.
oferta = (
    denue.groupby("alcaldia_clave")
         .size()
         .reset_index(name="establecimientos")
)

poblacion = pd.read_excel(
    "datos/ESTUDIO_POBLACION_TODAS_LAS_EDADES_CDMX_2020.xlsx",
    sheet_name="Por alcaldía",
    header=4,
)

poblacion = poblacion[
    poblacion["Alcaldía"].notna()
    & (poblacion["Alcaldía"] != "CDMX (suma)")
].copy()
poblacion["alcaldia_clave"] = poblacion["Alcaldía"].map(clave_texto)

analisis = poblacion.merge(
    oferta,
    on="alcaldia_clave",
    how="left",
    validate="one_to_one",
)
analisis["establecimientos"] = analisis["establecimientos"].fillna(0)

# Ejemplo: servicios para personas mayores por cada 10,000 personas de 60+.
analisis["servicios_por_10mil_60mas"] = (
    analisis["establecimientos"] / analisis["60+"] * 10_000
)
```

## Indicadores de cobertura sugeridos

```text
Cobertura para infancias = establecimientos para infancias / población 0–17 × 10,000

Cobertura para adultos jóvenes = servicios dirigidos a jóvenes / población 18–29 × 10,000

Cobertura para edad media = servicios dirigidos a ese grupo / población 30–59 × 10,000

Cobertura para personas mayores = servicios dirigidos a mayores / población 60+ × 10,000

Cobertura general = establecimientos generales / población total × 10,000
```

Estas tasas miden establecimientos registrados en relación con la población. No miden camas, personal, matrícula, aforo, horarios, calidad, accesibilidad ni capacidad efectiva.

## Ponderación opcional de establecimientos DENUE

El resultado principal debe conservar el conteo real de establecimientos. Cuando el proyecto necesite distinguir la fuerza de la relación temática, puede añadirse una oferta ponderada.

| Tipo de relación | Peso propuesto |
|---|---:|
| Directa o principal por código de actividad | 1.00 |
| Mixta o complementaria | 0.50 |
| Incluida únicamente por palabra clave | 0.25 |
| Rechazada | 0.00 |

Para registros pendientes de revisión manual puede aplicarse un factor adicional:

| Estado de revisión | Factor propuesto |
|---|---:|
| Confirmado o sin revisión pendiente | 1.00 |
| Revisión pendiente | 0.50 |

```text
Peso final = peso de relación × factor de revisión

Oferta ponderada de una alcaldía = suma de los pesos finales
```

Ejemplos:

- relación directa confirmada: `1.00 × 1.00 = 1.00`;
- relación complementaria confirmada: `0.50 × 1.00 = 0.50`;
- palabra clave con revisión pendiente: `0.25 × 0.50 = 0.125`.

Estos pesos son una **propuesta metodológica del proyecto**; no proceden del DENUE ni del Censo. Deben presentarse junto al conteo real y someterse a revisión y análisis de sensibilidad.

## Índice opcional de prioridad territorial

Si se necesita ordenar alcaldías para explorar brechas, puede combinarse el tamaño de la población objetivo con un déficit relativo de cobertura.

```text
Demanda normalizada = rango percentil de la población objetivo
Déficit normalizado = 1 - rango percentil de la cobertura

Prioridad = 100 × (0.60 × demanda normalizada + 0.40 × déficit normalizado)
```

La población objetivo cambia según el servicio: 0–17 para infancias, 18–29 para servicios juveniles, 30–59 para algunos servicios de edad media, 60+ para mayores o población total para servicios generales.

La ponderación 60/40 es solo un escenario inicial. Deben compararse al menos estos escenarios:

| Escenario | Demanda | Déficit de cobertura |
|---|---:|---:|
| Equilibrado | 50% | 50% |
| Inicial | 60% | 40% |
| Prioridad demográfica | 70% | 30% |

Si el orden de las alcaldías cambia mucho, el índice es sensible a los pesos y esa incertidumbre debe reportarse.

## Uso con DENUE 2016–2026

Este paquete contiene población de un solo año: 2020. Al combinarlo con distintas ediciones DENUE existen dos opciones:

1. **Denominador fijo de 2020.** Sirve para comparar cambios en establecimientos manteniendo constante la población de referencia. La tasa debe nombrarse, por ejemplo, `establecimientos por 10,000 personas usando población 2020`.
2. **Denominador del mismo año.** Es preferible para medir cobertura anual, pero requiere datos poblacionales comparables para cada año y grupo de edad.

Una tasa con establecimientos de 2016 y población de 2020 no debe presentarse como si ambos datos correspondieran al mismo momento.

## Sobre el crecimiento de la población

Con estos archivos se puede calcular la **composición porcentual por edades en 2020**, pero no el crecimiento temporal. Para medir crecimiento se necesita como mínimo otro año comparable con la misma geografía y los mismos grupos.

```text
Crecimiento porcentual = (población final - población inicial)
                         / población inicial × 100
```

La diferencia entre dos grupos de edad en 2020 no es crecimiento. Por ejemplo, que 30–59 sea mayor que 18–29 describe la estructura de población del año 2020; no muestra cómo cambió una misma población a lo largo del tiempo.

## Recomendaciones y limitaciones

- Usar `Base alcaldía` como fuente principal para resultados de ciudad y alcaldía.
- Mantener códigos geográficos como texto para conservar ceros a la izquierda.
- Agregar el DENUE antes de unirlo con población.
- No unir por AGEB hasta obtener una base censal con observaciones por AGEB.
- No sumar `60+` y `65+`; el segundo está contenido en el primero.
- Documentar siempre el año del numerador y del denominador.
- Conservar conteos reales además de tasas e indicadores ponderados.
- Validar manualmente registros DENUE incluidos por palabras clave.
- El prorrateo de 15–19 supone una distribución uniforme por edad y es una aproximación.
- Un establecimiento DENUE no representa una cantidad fija de capacidad o personas atendidas.
- Los cambios del DENUE entre años pueden reflejar aperturas, cierres, actualizaciones, reclasificaciones o cambios de cobertura del directorio.
- Las definiciones 0–17, 18–29, 30–59 y 60+ son operativas para este proyecto y deben ajustarse si una institución adopta otros límites.

