Proyecto de análisis de datos para el Datatón: identificación de zonas de oportunidad para inversión en infraestructura social en la Ciudad de México.

## Objetivo

Cruzar la evolución demográfica de la CDMX (envejecimiento de la población, llegada de familias jóvenes) con la oferta actual de espacios públicos y equipamiento comunitario, para detectar **islas de carencia**: zonas con alta densidad poblacional y baja oferta de servicios, y proyectar su evolución a futuro.

## Categorías de análisis

- Áreas verdes y equipamiento comunitario
- Servicios para personas adultas mayores
- Gimnasios y espacios deportivos

## Enfoque metodológico

La demanda insatisfecha se estima combinando densidad de espacios públicos actuales con tendencias demográficas y cambios de uso de suelo, apoyándose en aperturas y cierres de establecimientos reportados por el DENUE.

### Requisitos técnicos del reto

| Requisito | Enfoque adoptado |
|---|---|
| Fuentes de datos (mínimo 3, INEGI obligatorio) | INEGI (DENUE, Censos), Datos Abiertos CDMX, OpenStreetMap |
| Requisito temporal | Mínimo 3 momentos censales/históricos comparables (INEGI/DENUE) para calcular tendencia de crecimiento o saturación |
| Horizonte y proyección | Proyección a 3 o 5 años de la demanda insatisfecha |
| Medida de incertidumbre | Intervalo de confianza o nivel de riesgo por zona (por ejemplo, alta demanda proyectada con alta incertidumbre por cambios normativos de uso de suelo) |
| Validación retrospectiva | Entrenamiento con datos históricos (ej. predecir 2020 usando 2010–2015) para validar el acierto del modelo |

## Plataforma (dashboard)

Dashboard interactivo orientado a tomadores de decisión no técnicos (funcionarios públicos, inversionistas de impacto social).

### A. Panel de control y filtros

- Horizonte de proyección: 1, 3 o 5 años
- Población objetivo: infancia, adultos mayores o comunidad general
- Tipo de infraestructura: áreas verdes, centros comunitarios o espacios deportivos
- Nivel de riesgo/inversión aceptable: conservador (zonas estables) o de alto impacto (zonas en rápida densificación)

### B. Visualización geoespacial — Semáforo de Inversión Social

Mapa interactivo de la CDMX desagregado por AGEB o alcaldía, con clasificación de zonas:

- **Rojo — Zonas saturadas**: alta oferta actual, crecimiento poblacional estancado
- **Verde — Zonas de oportunidad**: alta demanda / baja oferta; colonias que reciben nuevos habitantes o envejecen sin parques ni centros comunitarios cercanos
- **Amarillo — Zonas en transición**: crecimiento comercial o inmobiliario con déficit anticipado de espacios públicos

### C. Ficha detallada por zona (explicabilidad)

Al seleccionar una colonia o AGEB, se despliega:

- Gráfica de tendencia histórica y proyectada de población y oferta
- Factores determinantes de la predicción (ej. incremento de adultos mayores combinado con baja disponibilidad de unidades deportivas)
- Métrica de incertidumbre de la proyección

## Flujo de datos

| Paso | Fuente / tarea | Resultado |
|---|---|---|
| 1 | Censo 2010 + 2020 | Población, grupos etarios, densidad y crecimiento por AGEB |
| 2 | DENUE histórico | Evolución de gimnasios, clubes y centros de acondicionamiento |
| 3 | Espacio público CDMX | Parques, instalaciones recreativas y equipamiento público |
| 4 | Inventario de Áreas Verdes | Superficie verde y m² por habitante |
| 5 | PILARES | Infraestructura comunitaria |
| 6 | AGEB como llave geográfica | Asignación de cada punto/polígono a un AGEB y tabla maestra |

## Fuentes de datos

### Demográficas y temporales

**Censo de Población y Vivienda 2020 (AGEB y manzana) — INEGI — Prioridad alta**
Base principal para describir la demanda actual a escala fina.
Variables: población total, grupos de edad, sexo, vivienda, hogares, escolaridad, discapacidad, otros indicadores sociodemográficos.
Uso: cálculo de densidad poblacional, proporción de adultos mayores y proporción de población infantil por AGEB.

**Censo de Población y Vivienda 2010 (AGEB y manzana) — INEGI — Prioridad alta**
Punto histórico comparable para medir cambios demográficos de largo plazo.
Variables: población total y composición demográfica por AGEB/manzana; indicadores de vivienda.
Uso: comparación 2010 vs. 2020 para crecimiento, envejecimiento y validación retrospectiva.
Nota: verificar comparabilidad geográfica entre años; no asumir equivalencia directa entre productos censales de distintos periodos.

**DENUE histórico — INEGI — Prioridad alta**
Directorio georreferenciado de establecimientos; permite observar la evolución de la oferta en distintos años.
Variables: nombre, actividad económica, código SCIAN, dirección, latitud, longitud, tamaño del establecimiento.
Uso: conteo de gimnasios, centros de acondicionamiento y clubes deportivos por AGEB; comparación entre ediciones históricas.
Nota: filtrar por códigos SCIAN relevantes para deporte, entre otros 713941, 713942, 713943 y 713944.

**Variable temporal recomendada:** demografía 2010 → 2020; oferta con varias ediciones de DENUE. Esto permite una serie temporal defendible sin forzar equivalencias falsas entre productos estadísticos distintos.

### Infraestructura, áreas verdes y comunidad

**Espacio público de la Ciudad de México — Datos Abiertos CDMX — Prioridad alta**
Capa geográfica de espacios públicos, intersectable con polígonos de AGEB.
Variables: áreas verdes, camellones, instalaciones deportivas y recreativas, plazas y parques.
Uso: conteo de espacios por AGEB y cálculo de superficie de espacio público disponible por habitante.

**Inventario de Áreas Verdes de la Ciudad de México — Datos Abiertos CDMX — Prioridad alta**
Inventario cartográfico especializado que permite medir superficie disponible.
Variables: polígonos, ubicación, geometría y superficie (formatos SHP y GeoJSON).
Uso: cálculo de m² de área verde por habitante y déficit relativo entre zonas comparables.

**Ubicación y estatus de PILARES — Datos Abiertos CDMX — Prioridad alta**
Representa la infraestructura comunitaria pública.
Variables: ubicación y estatus de los puntos PILARES.
Uso: conteo por AGEB o cálculo de distancia al PILARES más cercano.

**Instalaciones deportivas — Datos Abiertos CDMX — Prioridad media-alta**
Directorio georreferenciado de instalaciones deportivas públicas, como fuente complementaria.
Variables: nombre, domicilio y ubicación geográfica.
Uso: cruce con DENUE y OSM para consolidar la capa de oferta deportiva.
Nota: no usar como única fuente de oferta deportiva; su cobertura es limitada.

### Adultos mayores, accesibilidad y transformación urbana

**Directorio de Clubes INAPAM para personas adultas mayores — INAPAM / Gobierno de México — Prioridad media-alta**
Complementa la categoría de servicios para población de 60 años y más.
Variables: directorio de clubes, ubicación/dirección y servicios ofrecidos.
Uso: geocodificación de direcciones y construcción de indicadores como clubes por 1,000 adultos mayores o distancia al club más cercano.

**Promedio de distancias a espacios públicos por colonia — Datos Abiertos CDMX — Prioridad media**
Indicador procesado de accesibilidad.
Variables: distancia promedio a áreas verdes, camellones, instalaciones deportivas/recreativas, plazas y parques.
Uso: dimensión de accesibilidad dentro del índice de carencia, como variable complementaria cuando no sea viable calcular rutas o buffers propios.

**Uso de suelo de la Ciudad de México — SEDUVI / Datos Abiertos CDMX — Prioridad media**
Información sobre densidad, usos y características urbanísticas.
Variables: alcaldía, colonia, superficie, clave/tipo de uso, densidad, niveles, altura, área libre y coordenadas.
Uso: variables explicativas de crecimiento urbano y detección de zonas con presión inmobiliaria o cambios de uso de suelo.

**OpenStreetMap / Overpass API — OpenStreetMap — Prioridad alta**
Fuente abierta complementaria para parques, canchas, centros deportivos, gimnasios, áreas peatonales y centros comunitarios no cubiertos por otras bases.
Variables: objetos etiquetados, por ejemplo `leisure=park`, `leisure=pitch`, `leisure=sports_centre`, `leisure=fitness_centre`, `leisure=playground`, `amenity=community_centre`.
Uso: complemento de huecos de cobertura y enriquecimiento geométrico. Para descargas masivas de México, usar Geofabrik.
Nota: fuente colaborativa; requiere control de calidad y detección de duplicados.

## Índice de enlaces

- INEGI — Censo 2020
- INEGI — Censo 2010
- INEGI — Descarga DENUE
- CDMX — Espacio público
- CDMX — Inventario de Áreas Verdes
- CDMX — PILARES
- CDMX — Instalaciones deportivas
- INAPAM — Clubes para adultos mayores
- CDMX — Distancias a espacios públicos
- CDMX — Uso de suelo
- OpenStreetMap — Overpass API
- Geofabrik — México
