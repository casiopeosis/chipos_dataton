# Inventario de `data/` — estado actual

Generado a partir de `README.md` y `resumen_calidad.json` / `reporte_calidad_*.json` de cada carpeta (nunca de los CSV/GeoJSON/XLSX crudos, salvo consultas puntuales de estructura de JSON). No se movió ni modificó ningún archivo de `data/` para producir este documento.

Fecha de corte: 2026-09-17. Rama: `reorganizacion`.

**Nota sobre la versión anterior de este archivo:** ya existía un `docs/current-state.md` sin comitear en el árbol de trabajo. Afirmaba que `INFANCIAS_*`, `AREAS_CULTURALES_CDMX`, `PILARES CDMX`, `ESTUDIO EDADES CENSO 2020`, `enut`, `ESPACIO PUBLICO CDMX` y `COMERCIOS_2025_05` **no existían** en `data/`, y que la rama se llamaba `reorg`. Ninguna de esas dos cosas es cierta hoy: las seis carpetas existen y la rama activa es `reorganizacion`. Ese documento describía un estado distinto al actual (probablemente de antes de que se subieran esos datos) y se reemplaza por completo con lo que sigue, verificado directamente contra el filesystem en esta sesión.

## 0. Qué hay realmente en `data/`

50 carpetas + 3 archivos sueltos en la raíz de `data/`:

- **11** `COMERCIOS_YYYY_MM` (2016_10 → 2026_05, un corte por año, mensual solo en el primer y últimos dos)
- **11** `INFANCIAS_YYYY_MM` (mismo calendario)
- **11** `SALUD_CDMX_YYYY_MM` (mismo calendario)
- **10** carpetas `MAYO|NOVIEMBRE|OCTUBRE YYYY CDMX` (deporte + adultos mayores): `OCTUBRE 2016`, `NOVIEMBRE 2017/2018/2020/2021`, `NOVIEMBRE 2022/2023/2024`, `MAYO 2025/2026`
- `AREAS_CULTURALES_CDMX`, `AREAS VERDES CDMX`, `ESPACIO PUBLICO CDMX`, `ESTUDIO EDADES CENSO 2020`, `PILARES CDMX`, `enut` (6 carpetas de contexto/dominio no-DENUE-genérico)
- Sueltos en `data/`: `data.csv` (vacío), `semaforo_v0.json`, `semaforo_v1.json`

Todas las carpetas `COMERCIOS_*`, `MAYO/NOVIEMBRE/OCTUBRE * CDMX` (2022+), `AREAS VERDES CDMX`, `AREAS_CULTURALES_CDMX`, `ESPACIO PUBLICO CDMX`, `PILARES CDMX` y `ESTUDIO EDADES CENSO 2020` tienen `README.md`. **`INFANCIAS_*` (salvo `2016_10`), `SALUD_CDMX_*` (ninguna), `MAYO/NOVIEMBRE/OCTUBRE * CDMX` de 2016-2021, y `enut` no tienen `README.md`.**

## 1. Vista rápida

| Carpeta / archivo | Dominio | README | Reporte de calidad | Nº ediciones | Notas |
|---|---|---|---|---|---|
| `COMERCIOS_2016_10`…`2026_05` (11) | Comercio de primera necesidad (abarrotes, súper, carnicerías, farmacias como complemento) | Sí | `resumen_calidad.json` | 11, serie completa | §2 |
| `INFANCIAS_2016_10`…`2026_05` (11) | Infancia (guarderías, escuelas, apoyo social/residencias) | Solo `2016_10` | `reporte_calidad_infancias_*.json` | 11, serie completa | §3 |
| `SALUD_CDMX_2016_10`…`2026_05` (11) | Salud (farmacias, consultorios, residencias) | **No, ninguna** | `reporte_calidad_salud_*.json` (falta en `2019_11`) | 11, serie completa | §4 |
| `NOVIEMBRE 2022/2023/2024 CDMX`, `MAYO 2025/2026 CDMX` (5) | Deporte + adultos mayores, esquema nuevo (Gen B) | Sí | `resumen_calidad.json` | 5 | §5 |
| `OCTUBRE 2016`, `NOVIEMBRE 2017/2018/2020/2021 CDMX` (5) | Deporte + adultos mayores, esquema previo (Gen A) | **No, ninguna** | `reporte_calidad_denue_*.json` (falta en `2021`) | 4 completas + 1 rota | §6 |
| `AREAS_CULTURALES_CDMX` | Cultura (teatros, centros culturales, cines — SIC) | Sí | `resumen_calidad.json` | 1 (foto SIC actual) | §7 |
| `AREAS VERDES CDMX` | Contexto urbano (áreas verdes, Datos Abiertos ed. 2021) | Sí | `resumen_calidad.json` | 1 | §8 |
| `ESPACIO PUBLICO CDMX` | Contexto urbano (espacio público genérico, sin categorías) | Sí | `resumen_calidad.json` | 1 | §9 |
| `PILARES CDMX` | Infraestructura comunitaria pública | Sí | `resumen_calidad.json` | 1 | §10 |
| `ESTUDIO EDADES CENSO 2020` | Denominador poblacional por edad/sexo, Censo 2020 | Sí | No (es un XLSX de estudio, no un pipeline de depuración) | 1 (año 2020) | §11 |
| `enut` | Uso del tiempo (posible insumo de cuidado) | **No** | **No** | 1 CSV suelto (`enut_2024_cdmx_uso_tiempo.csv`) | §12 |
| `data/data.csv` | — | — | — | — | **Vacío, 0 líneas.** Sin carpeta ni README propios |
| `data/semaforo_v0.json` / `semaforo_v1.json` | Output previo del semáforo | — | — | — | §13 |

## 2. `COMERCIOS_YYYY_MM` — serie completa, comercio de primera necesidad

11 carpetas, una por edición DENUE, de 10/2016 a 05/2026 (10/2016, 11/2017, 11/2018, 11/2019, 11/2020, 11/2021, 11/2022, 11/2023, 11/2024, 05/2025, 05/2026). Es la **única familia con cobertura ininterrumpida de las 11 ediciones**, incluyendo 11/2019 y 11/2021 que faltan o están rotas en la familia deporte/adultos-mayores (§6).

- README idéntico en estructura entre las 11 carpetas ("DENUE Comercios CDMX MM/YYYY depurado"): filtra abarrotes, supermercados, minisúpers, carnicerías, pollerías, pescaderías, frutas y verduras, semillas y granos, lácteos y embutidos, otros alimentos; conserva farmacias como oferta complementaria; identifica tiendas IMSS por SCIAN + nombre.
- Archivos por carpeta: `*_depurado.csv/.geojson/.xlsx`, `criterios_scian.csv`, `diccionario_campos_depurados.csv`, `diccionario_shapefile.csv` (campo extra que **no** tiene la familia Gen B de §5/§6), `resumen_calidad.json`, `fuente/`, `shapefile/`.
- Registros originales vs. conservados por edición (de `resumen_calidad.json` → `fuente.edicion` / `resultados`):

  | Edición | Originales | Conservados | % |
  |---|---:|---:|---:|
  | 10/2016 | 464,583 | 86,534 | 18.6% |
  | 11/2017 | 467,279 | 86,831 | 18.6% |
  | 11/2018 | 471,957 | 86,997 | 18.4% |
  | 11/2019 | 466,301 | 85,710 | 18.4% |
  | 11/2020 | 474,328 | 85,309 | 18.0% |
  | 11/2021 | 474,333 | 85,283 | 18.0% |
  | 11/2022 | 474,323 | 85,348 | 18.0% |
  | 11/2023 | 475,331 | 85,366 | 18.0% |
  | 11/2024 | 458,228 | 86,405 | 18.9% |
  | 05/2025 | 460,762 | 88,116 | 19.1% |
  | 05/2026 | 462,732 | 88,738 | 19.2% |

- No corresponde al dominio "infancia/adultos mayores/cultura" de `CLAUDE.md` §2 — es un cuarto dominio (comercio/abasto) no listado ahí. Puede servir de contexto de oferta comercial, pero no es un insumo directo de ninguno de los tres focos declarados.

## 3. `INFANCIAS_YYYY_MM` — serie completa, sin README (salvo 2016_10)

11 carpetas, 2016_10 → 2026_05. Estructura distinta a `COMERCIOS_*`/Gen B: no hay `resumen_calidad.json` sino `reporte_calidad_infancias_YYYY_MM.json`; no hay `diccionario_campos*.csv` sino `catalogo_scian_infancias_YYYY_MM.csv`; no hay `.geojson`/`.xlsx`/`shapefile/`, solo `denue_infancias_cdmx_YYYY_MM.csv` + `registros_rechazados_*.csv` + `registros_revision_manual_*.csv`.

- **Solo `INFANCIAS_2016_10` tiene `README.md`**; las otras 10 no.
- El reporte de calidad (revisado en detalle para `2025_05`) incluye `fuente.sha256` del zip DENUE de entrada y flags de configuración (`incluir_media_superior`, `incluir_formacion_complementaria`, `incluir_clubes_y_recreacion`, `incluir_apoyo_social_y_residencias`, `solo_primera_infancia`) con códigos SCIAN principales de guarderías/educación (611111-611182, 624411-624412) más extensiones opcionales.
- **Confirmado por hash**: `INFANCIAS_2025_05` usa el mismo zip de origen (`sha256 ab4f31e5…`, 460,762 registros declarados) que `SALUD_CDMX_2025_05` y las cuentas de `COMERCIOS_2025_05`/`MAYO 2025 CDMX` — ver §14. Es un recorte temático más sobre la misma descarga DENUE del periodo, no una fuente aparte.
- **Esta familia responde directamente al dominio "Infancia" de `CLAUDE.md` §2** — pero la carpeta ahí referida como `INFANCIAS_*` ya existe y con datos completos; falta documentarla con README en 10 de 11 ediciones.

## 4. `SALUD_CDMX_YYYY_MM` — serie completa, sin README en ninguna

11 carpetas, mismo calendario que §2/§3. **Ninguna tiene `README.md`.** Mismo patrón de archivos que `INFANCIAS_*`: `catalogo_scian_salud_YYYY_MM.csv`, `denue_salud_cdmx_YYYY_MM.csv`, `registros_rechazados_*.csv`, `registros_revision_manual_*.csv`, `reporte_calidad_salud_*.json`.

- **Falta el reporte de calidad en `SALUD_CDMX_2019_11`** (los demás archivos de esa carpeta sí están completos).
- El campo `fuente.edicion` del JSON coincide de forma confiable con el nombre de carpeta (ej. `SALUD_CDMX_2025_05` → `"2025-05"`), a diferencia del bug de metadatos de la familia Gen A (§6).
- No es uno de los tres dominios de demanda listados en `CLAUDE.md` §2 (adultos mayores / infancia / cultura), pero sí aparece mencionado ahí como fuente derivada de los snapshots DENUE genéricos.

## 5. Familia "Gen B": deporte + adultos mayores, esquema con README (2022+)

`NOVIEMBRE 2022 CDMX`, `NOVIEMBRE 2023 CDMX`, `NOVIEMBRE 2024 CDMX`, `MAYO 2025 CDMX`, `MAYO 2026 CDMX`.

- README idéntico en estructura ("DENUE CDMX MM/YYYY depurado para el Datatón 2026"): conserva únicamente clubes deportivos/gimnasios (SCIAN 713941-4), escuelas de deporte (611621-2), asilos/residencias para adultos mayores (623311-2) y centros de cuidado diurno (624121-2, marcados para revisión por mezclar poblaciones).
- Archivos: `*_depurado.csv/.geojson/.xlsx`, `criterios_scian.csv`, `diccionario_campos_depurados.csv` (sin `diccionario_shapefile.csv`, a diferencia de §2), `resumen_calidad.json`, `fuente/`, `shapefile/`.
- Cobertura conservada por edición: ~3,100–3,250 registros de ~458k–475k originales (0.66%–0.70%).
- **Esta familia ES el dato "adultos mayores" (+ deporte) que `CLAUDE.md` §2 busca bajo `NOVIEMBRE * CDMX/denue_servicios_adultos_mayores_*`** — el filtro deporte+adultos-mayores ya viene aplicado desde README, no hace falta reprocesar `denue_enfoque_*`.

## 6. Familia "Gen A": deporte + adultos mayores, esquema previo, sin README

`OCTUBRE 2016 CDMX`, `NOVIEMBRE 2017/2018/2020/2021 CDMX`.

- **Ninguna tiene `README.md`.** Documentación solo vía `reporte_calidad_denue_YYYY.json` (falta también en `NOVIEMBRE 2021`).
- Archivos por carpeta (completas): `denue_enfoque_cdmx_YYYY.geojson`, `denue_enfoque_gimnasios_adultos_mayores_cdmx_YYYY.csv`, `denue_oferta_deportiva_cdmx_YYYY.csv`, `denue_servicios_adultos_mayores_cdmx_YYYY.csv`, `registros_rechazados_denue_YYYY.csv` — mismo dominio que Gen B, pero repartido en 3-4 CSV temáticos en vez de un único `*_depurado.csv`, y sin `.xlsx`/`shapefile/`/`diccionario_campos_depurados.csv`.
- **Bug de metadatos confirmado** (leído directamente de los 4 JSON en esta sesión): los campos `fuente.anio_datos`, `fuente.mes_corte`, `fuente.edicion` y `fuente.nota_temporal` de `2016.json`, `2017.json`, `2018.json` y `2020.json` dicen **los cuatro** `anio_datos: 2020, mes_corte: 11, edicion: "2020-11"` y "fotografía del DENUE a noviembre de 2021" — es una plantilla no actualizada al generar cada reporte, **no confiar en esos campos**.
  - Lo que sí es correcto y distinto por carpeta: `fuente.archivo` (`denue_09_1016.zip`, `_1117`, `_1118`, `_1120` — MM+AA correctos), `fuente.sha256_archivo_entrada` (los 4 hashes son distintos) y `resultados.registros_maestros` (2,513 / 2,526 / 2,535 / 2,582 — todos distintos). Son 4 ediciones DENUE genuinamente diferentes, no el mismo zip copiado 4 veces.
- Falta el corte **noviembre 2019** en esta familia (no hay carpeta); sí existe para ese periodo en `SALUD_CDMX_2019_11`, `INFANCIAS_2019_11` y `COMERCIOS_2019_11`.

### 6.1 `NOVIEMBRE 2021 CDMX` — carpeta incompleta

Solo 3 archivos: `denue_enfoque_gimnasios_adultos_mayores_cdmx_2021.csv`, `denue_oferta_deportiva_cdmx_2021.csv`, y **`denue_servicios_adultos_mayores_cdmx_2021 (2).csv`** — el sufijo `" (2)"` es el patrón típico de una descarga duplicada (navegador/Finder). Le faltan, respecto a sus hermanas: `denue_enfoque_cdmx_2021.geojson`, `registros_rechazados_denue_2021.csv` y `reporte_calidad_denue_2021.json`. No se puede verificar su calidad ni confirmar contra qué zip fuente se generó.

## 7. `AREAS_CULTURALES_CDMX`

- Fuente: Sistema de Información Cultural (SIC), Secretaría de Cultura. Solo incluye TEATRO, CENTRO_CULTURAL, CINE (no museos, galerías, bibliotecas, auditorios, librerías ni escuelas artísticas).
- 868 registros totales (157 teatros, 584 centros culturales, 127 cines). Clasificación de gestión: 577 público, 228 privado, 4 mixto, 59 no determinado.
- Marca cruce con PILARES (`es_pilares=SI`, `dataset_relacionado=PILARES`, 287 identificados) para evitar doble conteo si se combina con `PILARES CDMX` (§10).
- Es una fotografía del directorio SIC actual, no una serie histórica.
- **Es el dato "Cultura" que `CLAUDE.md` §2 espera en `AREAS_CULTURALES_CDMX/`** — ya existe y está completo, con README y resumen de calidad.

## 8. `AREAS VERDES CDMX`

- Inventario de Áreas Verdes CDMX (Datos Abiertos CDMX, edición 2021). 11,739 registros, 0 eliminados del universo original; 595 marcados para revisión manual.
- Clasificación analítica en 7 tipos (`oferta_verde_recreativa`, `cobertura_verde_vial`, `cobertura_verde_fragmentada`, `cobertura_verde_no_recreativa`, `vegetacion_en_equipamiento`, `proteccion_ecologica`, `revisar`); distingue explícitamente cobertura vegetal de oferta recreativa (no son equivalentes).
- 56 registros sin geometría utilizable (ni en el GeoJSON ni en el shapefile oficial); 11,683 con geometría. Superficie total ~6,736 ha (con posible superposición de polígonos — no sumar directamente para "cobertura territorial").
- Insumo de contexto de oferta urbana, no un dominio de demanda per se.

## 9. `ESPACIO PUBLICO CDMX`

- Fuente compuesta (CentroGeo 2020, cartas INEGI 1:20,000 2008, Marco Geoestadístico INEGI 2019, Censo 2010, CONANP). Shapefile original **atípico**: 1 solo registro con 8,499 partes geométricas multiparte y un único atributo (`Id=1`) — sin nombre, categoría ni tipo por componente.
- Depuración: desagregó las partes en 8,498 componentes válidos (1 excluido por área=0). CRS original EPSG:32614 (UTM 14N), reproyectado a EPSG:4326 para el GeoJSON.
- **No se asignaron categorías inferidas** — no distingue parque/plaza/camellón/instalación deportiva. Es una capa de cobertura espacial genérica, pensada para cruces por AGEB (superficie de espacio público, m²/habitante), no un catálogo tipado.
- README advierte explícitamente de posible superposición con `AREAS VERDES CDMX` — no sumar ambas capas sin revisión espacial previa.

## 10. `PILARES CDMX`

- 300 registros (198 en operación, 11 recibidos por SECTEI, 23 obra concluida sin recibir, 68 en obra). Sin IDs duplicados, sin nombres/alcaldías vacíos. 296 de 300 con coordenadas (los 4 sin coordenadas están "en obra"); no se imputaron coordenadas faltantes.
- Depurado agrega `operativo` (1 si `estatus_fuente="01. EN OPERACIÓN"`) y `tiene_coordenadas`.
- Único dataset de infraestructura comunitaria pública fuera de DENUE. Relevante como insumo cruzado del dominio "Adultos mayores" (`CLAUDE.md` §2 lista `PILARES CDMX/` ahí), aunque el README no restringe PILARES a un grupo etario específico — habría que confirmar con el equipo si PILARES debe tratarse como insumo transversal o específico de adultos mayores.

## 11. `ESTUDIO EDADES CENSO 2020`

- Único archivo de datos: `datos/ESTUDIO_POBLACION_TODAS_LAS_EDADES_CDMX_2020.xlsx` (bases, fórmulas, comparación de 16 alcaldías, método, diccionario). Sin `resumen_calidad.json` (no es un pipeline de depuración DENUE, es un estudio poblacional).
- Población con edad especificada: 9,200,318 (Censo 2020), desagregada en infancias 0-17 (22.2%), adultos jóvenes 18-29 (18.8%), adultos de edad media 30-59 (42.8%), adultos mayores 60+ (16.2%), con indicador complementario 65+ (11.1%, **no sumar a 60+**, ya está contenido).
- **Nivel territorial: solo alcaldía (576 registros) y alcaldía+localidad (3,276 registros). No contiene observaciones de población por AGEB** — la hoja `Diccionario` describe un campo `ageb` pero sin datos poblacionales asociados. Esto es directamente relevante para `CLAUDE.md` §3: el denominador poblacional por AGEB que necesitaría el semáforo con drill-down **no existe todavía en ningún dataset de `data/`**; haría falta una tabla censal adicional a nivel AGEB.
- README incluye metodología completa de reparto del grupo quinquenal 15-19 entre infancias/jóvenes, receta de unión con DENUE por alcaldía, e índice de prioridad territorial opcional — es el candidato natural para servir de denominador del estimador, con la limitación de AGEB señalada arriba.

## 12. `enut`

- Un solo archivo: `enut_2024_cdmx_uso_tiempo.csv`. **Sin `README.md` ni ningún reporte de calidad.** No se pudo determinar estructura/schema sin abrir el CSV, lo cual va contra la regla de `CLAUDE.md` §6.1 de no cargar CSV crudos — pendiente de generar diccionario/resumen antes de usarlo en modelado.

## 13. Archivos sueltos en la raíz de `data/`

- **`data/data.csv` está vacío (0 líneas).** Sin carpeta, README ni JSON de calidad propios. Candidato a archivo huérfano — confirmar con el equipo si se puede eliminar o si falta poblarlo.
- **`data/semaforo_v0.json`** (48 KB): claves de nivel superior `generado, ediciones, categorias, contorno_referencia, zonas`. `categorias` = `["Gimnasios y espacios deportivos", "Servicios para personas adultas mayores"]` — es decir, **solo cubre el dominio adultos mayores/deporte, a nivel alcaldía** (cada `zona` trae `alcaldia`, `poblacion_2020`, `serie_historica`, `oferta_percapita_100k`, `tendencia_pendiente_anual`, `proyeccion`, `validacion_retrospectiva`, `semaforo`).
- **`data/semaforo_v1.json`** (95 KB): mismas claves que v0 más `horizontes`, y cada `zona` añade `tendencia_resid_se`, `tendencia_t_crit`, `tendencia_dof`, `loo_cv` (validación cruzada leave-one-out), `subcategorias`, `factores_determinantes`. **v1 sí incorpora insumos compatibles con intervalos de confianza** (error estándar de residuales, t crítico, grados de libertad, LOO-CV) — es la iteración más cercana a lo que pide `CLAUDE.md` §4 ("estimador insesgado con intervalo de confianza"), aunque sigue sin AGEB ni cobertura de infancia/cultura.

## 14. Respuesta directa: ¿`COMERCIOS_2025_05`, `MAYO 2025 CDMX` y carpetas similares son el mismo corte?

**No son duplicados.** Son recortes temáticos distintos sobre la **misma descarga cruda de DENUE por periodo**, cada uno con su propio filtro SCIAN. Evidencia verificada en esta sesión:

- Para el periodo 05/2025: `COMERCIOS_2025_05` conserva 88,116 de **460,762** registros originales (filtro: comercio de primera necesidad); `MAYO 2025 CDMX` conserva 3,194 de esos mismos **460,762** originales (filtro: deporte + adultos mayores); `INFANCIAS_2025_05` y `SALUD_CDMX_2025_05` reportan **exactamente el mismo total de 460,762 registros declarados** y, más fuerte aún, **el mismo `sha256` del zip de entrada** (`ab4f31e5...`) entre sí. Los cuatro parten del mismo zip INEGI `denue_09_0525_shp.zip`.
- Mismo patrón para 05/2026: `COMERCIOS_2026_05` (88,738 de 462,732) y `MAYO 2026 CDMX` (3,252 de 462,732) comparten el total de 462,732 originales.
- Mismo patrón por edición para 11/2022, 11/2023, 11/2024 (`COMERCIOS_*` vs. `NOVIEMBRE * CDMX`): mismo `fuente.edicion` (ej. "DENUE 11/2022"), mismo nombre de zip salvo el sufijo `(1)` de descarga duplicada.
- **Conclusión operativa:** no hay que deduplicar ni descartar ninguna de estas carpetas. `COMERCIOS_*` (comercio/abasto), `MAYO/NOVIEMBRE/OCTUBRE * CDMX` (deporte + adultos mayores), `INFANCIAS_*` (infancia) y `SALUD_CDMX_*` (salud) son **cuatro vistas temáticas independientes de la misma serie histórica DENUE** — exactamente el patrón que `CLAUDE.md` §2 anticipa ("snapshots DENUE genéricos... fuente de la que salen `INFANCIAS_*`, `SALUD_CDMX_*` y los de adultos mayores"), ya resuelto y no ambiguo.
- **Donde sí hay una discontinuidad real y sin resolver** es dentro de la propia familia deporte/adultos mayores: Gen A (§6, sin README, esquema de 3-4 CSV sueltos, 2016-2021) vs. Gen B (§5, con README, un único `*_depurado.csv`, 2022+). Mismo dominio, dos generaciones de pipeline con estructura de salida distinta, sin carpeta puente que documente la transición 2020→2022 ni el hueco de 2019. Esto sí conviene confirmar con el equipo antes de unificar bajo `data/raw/`/`data/processed/` (`CLAUDE.md` §7).

## 15. Preguntas abiertas para el equipo

1. `INFANCIAS_*` (10 de 11 ediciones), `SALUD_CDMX_*` (11 de 11) y Gen A de deporte/adultos mayores (5 de 5) no tienen `README.md`. ¿Se genera README uniforme para las tres familias antes de modelar, o basta con los `reporte_calidad_*.json`?
2. ¿Se puede reconstruir/completar `NOVIEMBRE 2021 CDMX` (falta geojson, rechazados y reporte de calidad; el CSV de adultos mayores tiene sufijo `" (2)"` de descarga duplicada)?
3. ¿Por qué no existe el corte noviembre 2019 en la familia deporte/adultos mayores (Gen A/B), si sí existe para ese periodo en `SALUD_CDMX_2019_11`, `INFANCIAS_2019_11` y `COMERCIOS_2019_11`?
4. La transición de esquema Gen A → Gen B (2020→2022, sin README hasta 2022) — ¿fue deliberada? Si sí, ¿hay que regenerar las 5 carpetas Gen A al formato nuevo antes de modelar la serie histórica completa?
5. `data/data.csv` (vacío) — ¿se puede borrar o falta poblarlo?
6. `semaforo_v0.json`/`semaforo_v1.json` solo cubren deporte/adultos mayores a nivel alcaldía. ¿v1 es la base a extender con infancia, cultura y AGEB, o se descartan ambos y se parte de cero?
7. `ESTUDIO EDADES CENSO 2020` no tiene población por AGEB — ¿existe en algún lado (INEGI, equipo) una tabla censal con población por edad a nivel AGEB, o hay que resolver el drill-down del semáforo con otro denominador (ej. reparto proporcional por área desde alcaldía)?
8. `enut/enut_2024_cdmx_uso_tiempo.csv` no tiene README ni reporte de calidad — ¿alguien ya conoce su schema, o hace falta generarlo antes de usarlo como insumo de cuidado?
9. `PILARES CDMX` no distingue grupo etario objetivo en su README — ¿se trata como insumo transversal (infraestructura comunitaria general) o específico del dominio adultos mayores como sugiere `CLAUDE.md` §2?

---
*Este documento no modifica ni mueve ningún archivo de `data/`. Generado a partir de `README.md`, `resumen_calidad.json`/`reporte_calidad_*.json` de cada carpeta, y estructura de alto nivel (claves JSON) de `semaforo_v0.json`/`semaforo_v1.json`. No se abrió ningún CSV/GeoJSON/XLSX de datos completo.*
