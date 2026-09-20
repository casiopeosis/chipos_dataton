# Plan de backend y algoritmos

Objetivo: `make pipeline` regenera `data/outputs/prediccion_ageb.json` y `prediccion_alcaldia.json`
(contrato **`version 1.4`** de CLAUDE.md) aplicando exactamente `docs/metodologia.md`. Este plan no
depende del frontend; la única interfaz es el contrato de salida, más
`data/reference/ageb_cdmx*.geojson`. La contraparte de este plan es
`plans/frontend_specs.md` §17 ("motor de composición cliente"), que consume el contrato v1.4 para
calcular el índice compuesto de Habitancia en tiempo real sin volver a llamar al backend.

Convenciones: paquete `backend/src/chipos/`, Python 3.11+, sin dependencias nuevas (todo está en
`requirements.txt`). Semilla global `SEMILLA = 20260918`. Tiempo en años decimales.

**Revisión 2026-09-20.** Sobre la revisión 2026-09-19b (que ya reflejaba lo implementado: B0–B8,
B10–B12 entregadas, 122 pruebas en verde), esta revisión corrige tres defectos de diseño que el
equipo señaló en el propio plan anterior, y añade el producto **Habitancia**
(`correccion/frontend_requisitos.md`, cuatro ramas con pesos y filtros del usuario). Marcas de
estado:

- **✅** implementado y cubierto por `make test`.
- **🔄 fase N** acordado y pendiente; N es la fase de `correccion/action_plan.md` que lo entrega.

Los seis cambios de fondo respecto de la versión anterior de este plan:

| # | Cambio | Motivo | Rompe contrato |
|---|---|---|---|
| 1 | Horizontes **1 / 3 / 5** años (`T_HOR = 2031.5`), no 3/5/7 ni 2027.5 | `correccion/rubrica.md` §5 exige "uno, tres o cinco años" | sí → v1.4 (versión final del contrato, ver #4 y #6) |
| 2 | `backtest.py` **se implementa** (B9, la única tarea nunca entregada) | `correccion/rubrica.md` §5-6 lo exige; hoy no existe | no |
| 3 | Sobredispersión + piso de incertidumbre **calibrado con el backtest**, no un ancho mínimo elegido a ojo | corrige un defecto del propio plan anterior (§6, §8bis); IC degenerados (`ic95 = [-6.9,-6.9]`) | no |
| 4 | Segmentos por edad/servicio (0–17 incl. 15–17) + índice de oportunidad con fórmula exacta | `correccion/rubrica.md` §2 ("rankear oportunidades"); `correccion/frontend_requisitos.md` §5 | sí → v1.4 |
| 5 | **Se retira** el backtest de origen móvil sobre CONAPO (usaba una proyección como si fuera el futuro observado) | corrige una fuga de futuro del propio plan anterior (§6) | no |
| 6 | Generalización a **cuatro ramas** (educación, salud, comercio, verde) con filtros por celda | `correccion/frontend_requisitos.md` §2, §9-11 | sí → v1.4 |

## 1. Problemas de datos que afectan la implementación

| sev. | problema (ref.) | efecto en la implementación | mitigación |
|---|---|---|---|
| — | **Bloqueantes: ninguno abierto.** Censo 2010/2020, CONAPO y geometría AGEB resueltos (C1, C4, C5). | — | Tarea B1 solo re-verifica. ✅ |
| Importante | DENUE con 2 re-levantamientos; 11 cortes no independientes (C2) | Tratar 11 cortes como serie = pseudo-réplica | Solo 3 cortes de oferta: 2016-10, 2019-11, 2024-11 (fechas 2016.79, 2019.87, 2024.87) ✅ |
| Importante | Caída infancias 2024-11 −11.2 %, concentrada en privado (C3) | Sesgo de tasa si se fecha en 2024 | Eje = fechas de levantamiento ✅; tope `media` ✅; **dos escenarios A/B**, no una certeza ✅ |
| Importante | CONAPO > censo urbano en nivel (+5.9 %, hasta +29.7 % en 009) (N1) | Control por nivel inflaría AGEB | Control por **razón** 2031.5/2020.20, nunca por nivel ✅ |
| Importante | CONAPO proyecta caídas fuertes (−1.45 a −4.19 %/año) (N2) | Casi todo AGEB sale `baja` (2 181 de 2 453 en `h3`) | Resultado sustantivo; se reporta reparto y sensibilidad δ ∈ {0.5, 1, 2} ✅. El producto decisorio deja de ser el veredicto y pasa a ser el ranking de oportunidad (§8bis) ✅ |
| Importante | `λ` no identificable con 2 censos (metodología §3) | IC dominados por supuesto | Previa `U(0.25, 1)`; veredicto con λ ∈ {0.25, 0.6, 1}; si cambia, confianza −1 nivel ✅ |
| Importante | 100 AGEB con geometría 2010→2020 no idéntica (N5) | Denominador 2010 de otra superficie | Reglas de `relacion` (§4.2); confianza máx. `media` ✅ |
| **Importante** | **IC de oferta degenerados** (`agregado_cdmx.oferta.h3.ic95 = [-6.9, -6.9]`) | El modelo se publica más seguro de lo que está | Quasi-Poisson `φ_m` por alcaldía + piso `SIGMA_MIN_TASA` **calibrado con la cobertura empírica del backtest** (§6, metodología §2.7), no con un ancho mínimo elegido a ojo ✅ |
| **Importante** | **El backtest de CONAPO original usaba una proyección como "futuro real"** | Circular: `pobproy_quinq1.csv` es una sola vintage reconciliada contra el Censo 2020, así que ningún año de ese archivo representa "lo que se sabía entonces" | Se retira el backtest de origen móvil sobre ese archivo; se documenta la limitación; vía honesta si se consigue una vintage CONAPO anterior a 2020 (metodología §4.1, tarea B23, opcional) ✅ |
| **Importante** | **Solo 2 momentos censales por AGEB** | La rúbrica pide ≥ 3 momentos comparables | No se inventa un tercero: se documenta por capa (metodología §1.3) y el backtest se corre sobre oferta por AGEB (3 momentos, único backtest temporal genuino disponible hoy) ✅ |
| **Menor** | **CONAPO es quinquenal (00_04/05_09/10_14)** y no parte en 0–2/3–5/6–11/12–14 | Los segmentos no tienen ancla municipal propia | Los segmentos heredan el factor de control `k_m^s` de 0–14; aproximación declarada en metodología §1.2 y en `diagnostico.json` ✅ |
| Menor | Mojibake en nombres de alcaldía 2016–2018 (A1) | Grupos duplicados | Agrupar siempre por `CVE_MUN` de la clave AGEB ✅ |
| Menor | Tipos inestables (`Mes de corte`, `Año de alta DENUE`) (M3) | Errores de unión entre años | `read_csv(all_varchar=true)` y casteo explícito ✅ |
| Menor | Puntos fuera de CDMX con `Coordenadas válidas = 1` (M2) | Asignación errónea | Territorio por clave AGEB, no por coordenadas; filtro de clave (13 car., `09`, MUN 002–017) ✅ |
| Menor | Cambio SCIAN 2013→2018 (M1) | Altas/bajas artificiales por código | B4 verifica códigos `Principal` ausentes en algún corte ✅; los mismos códigos alimentan los segmentos (§4.4) ✅ |
| Menor | Claves sin polígono: 2 censales, 5 DENUE rurales (N3) | Filas huérfanas | `sin_datos`; contadas en el reporte de cobertura ✅ |
| Menor | 0–14 suprimido por INEGI (41 AGEB 2020), `D_2020 < 20` (23) | — | `sin_datos`, nunca imputar ✅ |

## 2. Geometría AGEB (ya adquirida; solo verificación) ✅

Estado: `tools/build_geo.py` ya produjo `data/reference/ageb_cdmx.geojson` (MG 2020 censal, 09a + 09ar,
EPSG:4326, `make_valid`) y `ageb_cdmx_simplificado.geojson` (mapshaper 25 %, 5 decimales, 1.51 MB).
No se re-descarga. Pasos del plan:
1. Test de verificación (`backend/tests/test_geo.py`): 2,453 features; `cvegeo` único; 2,431 con 13
   caracteres y `ambito = urbano`, 22 con 9 caracteres y `ambito = rural`; `cve_mun` ∈ 002–017; bbox
   dentro de [−99.37, 19.04, −98.94, 19.60]; mismo conjunto de claves en completo y simplificado. ✅
2. Versión del marco: afirmar join censo 2020 → polígono ≥ 99.9 % y claves DENUE `Principal` 2026-05 →
   polígono ≥ 99.7 % (valores de `perfil_datos.md`); registrar "MG 2020 censal, UPC 889463807469" en
   el bloque `metadatos` del reporte de backtest. ✅
3. Ningún archivo de `data/reference/` se reescribe; si hiciera falta TopoJSON lo genera el frontend
   en su propia carpeta. ✅

> **Nota de rendimiento (no es tarea de backend).** El cuelgue del navegador al enfocar una alcaldía
> **no** proviene de esta geometría: son 55 711 vértices en total, ~23 por AGEB. La causa está en
> `frontend/css/mapa.css` (ver `correccion/action_plan.md` §6.1). No simplificar más el GeoJSON:
> sería perder detalle sin ganar nada.

## 3. Capa de lectura `io.py` (DuckDB) ✅

- Una conexión DuckDB en memoria por ejecución; consultas con proyección de columnas (nunca `SELECT *`). ✅
- DENUE infancias: `read_csv(ruta, all_varchar=true, header=true)`; columnas: `ID`, `Clave geográfica AGEB`,
  `Alcance`, `Sector`, `Código SCIAN`, `Subcategoría`, `Edición DENUE`. Casteo: `ID`→BIGINT,
  `Código SCIAN`→INTEGER. Normaliza nombres a `snake_case` (`id, cvegeo, alcance, sector, scian,
  subcategoria, edicion`). ✅ — `scian` y `subcategoria` ya se leen; la fase 4 solo los **usa**.
- Mapa de ediciones → archivo y fecha de levantamiento en una constante `CORTES_OFERTA`
  (`{"2016-10": 2016.79, "2019-11": 2019.87, "2024-11": 2024.87}`); `EDICIONES_TODAS` para diagnóstico. ✅
- Censo: lee `data/interim/censo_ageb_panel.parquet` (ya limpio por `tools/build_censo.py`). ✅
  Trae `p_0a2, p_3a5, p_6a11, p_12a14` además de `pob_0a14`: los segmentos (§4.4) no requieren datos nuevos.
- CONAPO: `data/interim/conapo_mun_0a14.parquet`. ✅ · `leer_conapo_quinq()`/`conapo_mun_quinq.parquet`
  (diagnóstico quinquenal por segmento) — **descoped**: el criterio real de Fase 4
  (`correccion/action_plan.md` #25) solo pedía documentar la aproximación de CONAPO quinquenal en
  `docs/metodologia.md` §1.2, no una función de lectura nueva; se documentó sin implementar el
  diagnóstico adicional.
- Equivalencia: `data/interim/equivalencia_ageb_2010_2020.parquet`. ✅
- Geometría: solo propiedades (`cvegeo, cve_mun, ambito`) vía `pyogrio.read_dataframe(..., read_geometry=False)`. ✅
- Contexto CDMX: `areas_verdes/` y `espacios_publicos/` por join espacial WGS84 → conteo y superficie
  por AGEB, categorías de la rama "verde" (metodología §1.4/§10.1). ✅ — deja de ser "solo
  descriptivo": alimenta directamente `capas.ramas.verde` del contrato (Fase 5/6), no solo un
  diagnóstico de fondo como preveía esta sección originalmente.
- Si falta un parquet de `data/interim/`, error claro: "ejecuta `make datos`". ✅

Firmas:
```
conectar() -> duckdb.DuckDBPyConnection                                   # ✅
leer_denue_infancias(con, ediciones: Iterable[str]) -> pd.DataFrame       # ✅ id, cvegeo, cve_mun, alcance, sector, scian, subcategoria, edicion, t
leer_censo_panel() -> pd.DataFrame                                        # ✅ cvegeo, anio, t, cve_mun, p_0a2, p_3a5, p_6a11, p_12a14, pob_0a14, ...
leer_conapo_0a14() -> pd.DataFrame                                        # ✅ cve_mun, anio, pob_0a14
leer_conapo_quinq() -> pd.DataFrame                                       # descoped, ver nota arriba
leer_equivalencia() -> pd.DataFrame                                       # ✅
leer_universo_ageb() -> pd.DataFrame                                      # ✅ cvegeo, cve_mun, ambito (2,453 filas)
leer_contexto_cdmx() -> pd.DataFrame                                      # ✅ cvegeo, cve_mun, n_cobertura_verde,
    # area_cobertura_verde_m2, n_areas_recreativas, area_areas_recreativas_m2, n_espacios_publicos,
    # area_espacios_publicos_m2 (nombres reales de columna, distintos de los propuestos aquí en la
    # versión anterior del plan)
```

## 4. Panel AGEB × corte (`panel.py`)

### 4.1 Demanda ✅
- Unidad: AGEB urbana del MG 2020 (universo = `leer_universo_ageb()`).
- `D_it = pob_0a14` (ya = P_0A2+P_3A5+P_6A11+P_12A14), `t ∈ {2010.44, 2020.20}`.
- Columnas de salida: `cvegeo, cve_mun, ambito, relacion, d_2010, d_2020, motivo_sin_datos`.
- `motivo_sin_datos` ∈ {`rural`, `suprimido_inegi`, `d2020_menor_20`, `sin_poligono`, `sin_censo`, null}.
  Las 2 claves censales sin polígono se registran en el reporte de cobertura, no en el JSON.

### 4.2 Tratamiento geográfico 2010→2020 (según `relacion`) ✅
| relacion | d_2010 usado | n_obs | tope de confianza |
|---|---|---|---|
| misma | el de la misma clave | 2 | — |
| division | el de la madre 2010 **sin reescalar** por `frac_de_2010` (pregunta B3, resuelta: la hija hereda la **tasa**) | 2 | media |
| fusion_o_expansion, cambio_limites | el de la misma clave | 2 | media |
| sin contraparte | — (`r̃ = ρ_m`) | 1 | baja |

Conteos reales: `misma` 2 331, `fusion_o_expansion` 62, `cambio_limites` 37, `division` 1.

### 4.3 Oferta ✅
- `S_it` = nº de `ID` distintos con `alcance = 'Principal'` por `cvegeo` y corte (3 cortes).
- Filtros: clave de 13 caracteres, prefijo `09`, `cve_mun` 002–017, presente en el universo urbano.
  Claves rurales/sin polígono → contadas en cobertura, `sin_datos`.
- Duplicados: aserción de `ID` único por edición (B2 lo confirma hoy); si falla, error, no deduplicar en silencio.
- SCIAN: calcular códigos `Principal` presentes en los 3 cortes; los que no, se reportan (código,
  filas por corte) y se excluyen **solo** si su ausencia es de catálogo (aparece/desaparece en toda
  la CDMX en una edición). Decisión y conteos → `docs/metodologia.md` §6.
- Completar el panel con ceros explícitos para AGEB urbanas sin establecimientos en un corte.
- Salida: `cvegeo, cve_mun, t, s` (formato largo) + `s_2024` para brecha.

### 4.4 Segmentos de servicio y población objetivo ✅ — entregado distinto de esta sección (ver nota)

**Esta sección quedó superseded por el diseño real (B16 + B22, metodología §1.1 y §10.6): describe
un único `segmento` mezclando demanda y oferta (SCIAN → columna censal) que nunca se implementó
así.** Lo que se entregó separa las dos capas, cada una con su propio nombre de tarea:
- **Demanda (B16, `panel.SEGMENTOS_DEMANDA`)**: 6 segmentos por banda de edad censal —
  `todas` (0–17, por omisión), `primera_infancia` (`p_0a2`), `preescolar` (`p_3a5`), `primaria`
  (`p_6a11`), `secundaria` (`p_12a14`), `adolescencia` (`p_15a17`). Invariante real: Σ de los 5
  segmentos con dato = `todas`, exacto (`test_panel_demanda_suma_de_segmentos_igual_a_todas`).
- **Oferta (B22, `panel.CELDAS_EDUCACION`)**: 8 celdas por SCIAN dentro de la rama educación
  (`guarderia, preescolar, primaria, secundaria, educacion_especial, varios_niveles,
  media_superior_tecnica, recreacion_cultura`) — más las celdas de las ramas salud (4) y comercio
  (5), que no existían en esta sección del plan. Las celdas de oferta no se combinan con `pob_0a14`
  aquí: cada rama tiene su propio ajuste Poisson+EB, independiente del segmento de demanda activo.

Firmas:
```
construir_panel_demanda(censo, equivalencia, universo, segmento="todas") -> pd.DataFrame   # ✅
construir_panel_oferta(denue, universo, cortes=CORTES_OFERTA) -> pd.DataFrame  # ✅ sin `segmento`:
    # la generalización por celda de la rama educación (y las nuevas salud/comercio) es una función
    # aparte, `construir_panel_oferta_celda(denue, universo, filtro_celda, cortes=CORTES_OFERTA)` (B22)
reporte_cobertura(panel_d, panel_o, universo) -> dict   # ✅ conteos por motivo, para el log y el backtest
```

## 5. Algoritmo de estimación (`modelos.py`)

Constantes (único lugar: `config.py`, reflejadas en `docs/metodologia.md` §7):
`T_2010=2010.44`, `T_2020=2020.20`, `T_BASE=2026.5`, `DELTA=0.01`, `P_DECISION=0.80`,
`P_ALTA=0.95`, `P_MANTIENE=0.50`, `N_SIM=4000`, `LAMBDA_PREVIA=(0.25, 1.0)`,
`LAMBDAS_SENS=(0.25, 0.6, 1.0)`, `DELTAS_SENS=(0.005, 0.01, 0.02)`, `D_MIN_CONF=100`. ✅

Entregado ✅ (Fase 1):
```
HORIZONTES        = {"h1": T_BASE + 1, "h3": T_BASE + 3, "h5": T_BASE + 5}   # 2027.5 / 2029.5 / 2031.5
T_HOR             = HORIZONTES["h5"]        # 2031.5 — ancla única del control CONAPO
HORIZONTES_OFERTA = ("h1", "h3")            # la oferta no reporta h5 (metodología §6.3)
```
Entregado ✅ (Fase 3), con nombres reales distintos a los propuestos aquí: `SIGMA_MIN_DEMANDA` y
`SIGMA_MIN_OFERTA` (piso separado por capa, no un único `SIGMA_MIN_TASA` — cada capa se calibró con
su propio backtest) y `PHI_MINIMO = 1.0` (el factor quasi-Poisson nunca reduce la varianza).

### 5.1 Demanda
1. Tasa directa `r̂_i = ln[(D_i,20+0.5)/(D_i,10+0.5)]/Δt`, `Δt = 9.76`;
   `ψ_i = [1/(D_i,20+0.5) + 1/(D_i,10+0.5)]/Δt²`. ✅
2. `ρ_m` = misma fórmula con sumas de la alcaldía. ✅
3. `τ²` por momentos, agrupado en toda la CDMX: `τ² = max(0, mean((r̂_i − ρ_m)²) − mean(ψ_i))`
   (se reporta también por alcaldía como diagnóstico). ✅
4. `B_i = ψ_i/(ψ_i+τ²)`; `r̃_i = B_i ρ_m + (1−B_i) r̂_i`; var. posterior `(1−B_i)ψ_i`,
   **acotada por abajo en `SIGMA_MIN_DEMANDA²`** ✅
5. `ρ_m,CONAPO = ln(C_m,2031.5 / C_m,2020.5)/11.0` (cifras de mitad de año). ✅
6. `C_m,2020.20` = interpolación log-lineal entre 2019 (2019.5) y 2020 (2020.5). ✅
7. Por réplica s = 1..4000: `r_i^s ~ N(r̃_i, var_post_i)`, `λ^s ~ U(0.25,1)`,
   `ε_m^s ~ N(0, σ_C,m²)` con `σ_C,m = |ρ_m,censo 2010–20 − ρ_m,CONAPO 2010–20|`;
   `r_i,fut^s = ρ_m,CONAPO + λ^s (r_i^s − ρ_m)`. ✅
8. Control por razón: `k_m^s = [C_m,2031.5/C_m,2020.20] · Σ_i D_i,20 / Σ_i D_i,20·exp(r_i,fut^s·(T_HOR−T_2020))`
   y `r_i,fut^s ← r_i,fut^s + ln(k_m^s)/(T_HOR−T_2020)` (mantiene la forma log-lineal). ✅
   `ε_m^s` se aplica **después** del control, sobre la razón de CONAPO, para que el choque compartido
   sobreviva al reescalado. ✅
   Un solo control, contra el horizonte más lejano; `h1`/`h3` se leen sobre la misma trayectoria
   (metodología §2.5). ✅ `T_HOR` = 2031.5 (Fase 1, antes 2033.5).
9. Salidas **por horizonte** `h ∈ HORIZONTES` (`resumir()` devuelve un `DataFrame` por clave):
   `tasa_anual_pct = 100·mediana(r_i,fut^s)` — idéntica en los 3 horizontes (pregunta B5 resuelta:
   tasa logarítmica ×100, coherente con la banda δ);
   `delta_pct = mediana(100·(exp(r·(t_h − T_BASE)) − 1))`; `ic95` = percentiles 2.5/97.5 de esa
   misma cantidad; `p_sube = P(r > +δ)`, `p_baja = P(r < −δ)`, `p_mantiene = P(|r| ≤ δ)`. ✅
   Ojo: `delta_pct`/`ic95` se miden desde `T_BASE`, **no** desde `T_2020`.

### 5.2 Oferta
- Por AGEB: Poisson log-lineal `log E[S_it] = a_i + b_i (t − 2019.87)` sobre 3 cortes, ajuste por
  Newton-Raphson vectorizado (sin bucle `statsmodels` por AGEB; `statsmodels` solo en el test de
  paridad). `var(b_i)` = inversa de la información de Fisher. ✅
- **Sobredispersión** ✅: `φ_m = χ²(Pearson)/gl` estimado **agrupado por alcaldía** (1 gl por
  AGEB es puro ruido), `φ_m ← max(φ_m, PHI_MINIMO)`, y `var(b_i) ← φ_m · var(b_i)` antes del EB.
- EB: igual que 5.1 pasos 3–4 hacia `b_m` (pendiente Poisson de la suma de la alcaldía). Sin control externo. ✅
- Simulación `b_i^s ~ N(b̃_i, var_post)`, con el piso `SIGMA_MIN_OFERTA` ✅;
  `delta_pct` desde `T_BASE` a `h1` y `h3`. ✅
- `sin_datos` si `S = 0` en los 3 cortes o AGEB rural. Confianza con tope `media`. `n_obs = 3`. ✅
- **Escenarios de la caída 2024-11** ✅: A (cierres reales, principal, es el que se publica)
  y B (depuración parcial del padrón, sensibilidad). Ambos a `diagnostico.json`; el contrato no se
  duplica (metodología §6.1).

### 5.3 Regla de veredicto (única función, compartida por ambas capas) ✅
```
veredicto(p_sube, p_baja, p_mantiene):
    si p_sube ≥ 0.80: 'sube', p_dec = p_sube
    si p_baja ≥ 0.80: 'baja', p_dec = p_baja
    si no: 'se_mantiene', p_dec = p_mantiene
confianza: 'alta' si p_dec ≥ 0.95 y estable en λ ∈ {0.25,0.6,1}; 'media' si p_dec ≥ 0.80; si no 'baja'
    bajar un nivel si el veredicto cambia con λ
    'baja' forzada si n_obs = 1 o D_2020 < 100
    aplicar topes (relacion no 'misma' → media; capa oferta → media)
```
Nota de implementación: la rama "si `p_mantiene ≥ 0.50` … si no, `se_mantiene` con confianza forzada
`baja`" del plan original no necesita código propio — como `P_MANTIENE (0.50) < P_DECISION (0.80)`,
`confianza()` ya devuelve `baja` en ese caso con sus umbrales estándar.

El veredicto y la confianza **no dependen del horizonte de reporte**: se calculan sobre la tasa, que
es una sola por unidad y réplica. Salen idénticos en `h1`, `h3` y `h5` por diseño, y así se explica
en el frontend (metodología §7).

Sensibilidad: recalcular veredictos con δ ∈ {0.5, 1, 2} %/año y λ fijo ∈ {0.25, 0.6, 1};
se guarda en `data/outputs/diagnostico.json` (fuera del contrato). ✅

### 5.4 Agregación a alcaldía ✅
- Por réplica: `D̂_m^s = Σ_{i∈m} D̂_i^s` sobre AGEB con dato; tasa de alcaldía = log-razón anualizada;
  mismo `veredicto()`. `n_obs = 2` (demanda) y `3` (oferta). Δ% desde sumas, nunca promedio de %.
- Agregado CDMX: misma estructura, una sola unidad (`_simulacion_cdmx`).
- Cobertura vs CONAPO por alcaldía (Σ D_2020 urbano / C_m,2020.20) en `diagnostico.json`.
- Milpa Alta (009, 82.8 % de cobertura urbana): se publica igual, etiquetada "solo urbano", sin tope
  de confianza (pregunta B4 resuelta; metodología §8). El etiquetado es tarea de frontend.

Firmas (estado real del módulo):
```
tasa_directa(d0, d1, dt) -> tuple[np.ndarray, np.ndarray]                        # ✅ r_hat, psi
contraccion_eb(r_hat, psi, rho_m_por_ageb) -> tuple[np.ndarray, np.ndarray, float]  # ✅ r_tilde, var_post, tau2
tasa_conapo(conapo, t0, t1) -> pd.Series                                          # ✅ por cve_mun
simular_demanda(panel_d, conapo, rng, n_sim=N_SIM, lam=None) -> Simulacion        # ✅
ajustar_oferta(panel_o) -> pd.DataFrame                                           # ✅ a_hat, b_hat, var_b por AGEB
simular_oferta(ajuste, rng, n_sim=N_SIM) -> Simulacion                            # ✅
veredicto(p_sube, p_baja, p_mantiene) -> tuple[str, float]                        # ✅
confianza(p_dec, estable_lambda, n_obs, d2020, tope) -> str                       # ✅
resumir(sim, horizontes: dict[str, float], delta=DELTA) -> dict[str, pd.DataFrame]  # ✅ una tabla por horizonte
agregar_alcaldia(sim) -> Simulacion                                               # ✅
```
`Simulacion` (dataclass congelada, compartida por ambas capas y ambos niveles):
`clave, cve_mun, n_obs, base, d2020_conf, tope, r_fut (n, n_sim), r_fut_lambdas, horizonte_control`.

## 6. Validación y backtesting (`backtest.py`) ✅

> **Esta es la única tarea del plan original que nunca se entregó (B9), y la que
> `correccion/rubrica.md` §5-6 exige explícitamente.** `config.py:44-45` ya declara
> `RUTA_BACKTEST_JSON` y `RUTA_BACKTEST_MD`, y el docstring de `exportar.main()` ya reserva el lugar
> en el pipeline. Hasta que existan los dos archivos de salida, ni `docs/metodologia.md` §4 ni la
> presentación pueden afirmar que la validación está hecha.

> **Corrección respecto a la versión anterior de este plan: se retira `backtest_conapo`.** El plan
> anterior proponía "origen móvil sobre la serie municipal CONAPO 1990–2020 (orígenes 2000, 2005,
> 2010, 2015)". Es inválido: `pobproy_quinq1.csv` es **una sola vintage**, reconciliada en bloque
> contra el Censo 2020 (`tools/build_conapo.py`); ningún año de ese archivo, ni 2005 ni 2015,
> representa "lo que se sabía en ese año" — todos fueron ajustados con información de 2020. Usarlo
> como si fuera una serie de orígenes independientes es exactamente el error que
> `correccion/detalles_a_tratar.md` señala: **validar una proyección con otra proyección construida
> con información futura, presentada como si fuera la realidad observada.** Detalle completo y la
> vía honesta para resolverlo (conseguir una vintage CONAPO anterior a 2020): metodología §4.1.

**Backtest temporal genuino** (origen móvil, sin fuga de futuro) — el único disponible hoy:
1. **Oferta por AGEB:** ajuste con 2016.79 y 2019.87 (sin ver 2024.87) → predecir 2024.87; baseline
   `S` constante. MAE de log-razón, deviance Poisson y F1 macro. Nota obligatoria: el objetivo 2024
   contiene la caída C3 (difícil para ambos).

**Sustitutos para la demanda por AGEB** (dos censos, todo origen móvil tendría fuga; semilla fija):

2. **Adelgazamiento binomial** al 25 % y 50 % **del propio Censo 2020** (nunca del futuro): estimar
   `r̂` y `r̃` sobre conteos adelgazados y comparar contra `r̂` completo. Métricas: MAE de la tasa
   (pp/año), cobertura IC95, F1 macro de 3 clases. Competidores: `r̃` (EB), `r̂` directo, `ρ_m`,
   baseline `r = 0`.
3. **Dejar una alcaldía fuera** para `τ²`: cobertura del IC95 en la alcaldía excluida ∈ [0.90, 0.97].
   Válida porque es una partición espacial, no temporal.
4. **Censo vs CONAPO 2010–2020** por alcaldía: tabla de discrepancias (alimenta `σ_C`). **No es un
   backtest** (no predice el futuro): es una comparación de dos fuentes en el mismo punto en el
   tiempo; se reporta etiquetada como tal, nunca como validación retrospectiva (metodología §4.1).

**Criterio de adopción:** la demanda EB se adopta si en (2) y (3) supera a `r = 0` en MAE **y** F1
macro y la cobertura está en rango; la oferta, si (1) supera a `S` constante. Si alguno no lo supera,
CLAUDE.md obliga a no adoptarlo: se publica el hallazgo (ver pregunta abierta B1).

**Limitación declarada, no maquillada:** no existe hoy una validación temporal independiente de la
tendencia de demanda a nivel alcaldía. Esta frase va literal en `docs/backtest.md` (metodología
§4.1, punto 4).

### 6.1 Calibración del piso de incertidumbre (depende de lo anterior)

`SIGMA_MIN_TASA` (config.py, metodología §2.7) **no se elige para que los intervalos midan más de
un ancho arbitrario** — ese fue un defecto de la versión anterior de este plan, corregido aquí. Se
calibra con la cobertura empírica de (1), (2) y (3):

```
calibrar_piso_incertidumbre(resultados_adelgazamiento, resultados_loao, resultados_oferta,
                             candidatos=(0.000, 0.005, 0.010, 0.015, 0.020)) -> dict
    # para cada candidato: recalcula var_post con el piso añadido, mide cobertura empírica del
    # IC95 sobre los folds de (2), (3) y (1); devuelve el candidato más pequeño con cobertura en
    # [0.90, 0.97] para demanda y para oferta por separado (pueden diferir: SIGMA_MIN_DEMANDA,
    # SIGMA_MIN_OFERTA), y la cobertura lograda para cada uno.
```

Si ningún candidato de la rejilla alcanza 0.90, se amplía la rejilla (nunca se fuerza el resultado);
si el candidato `0.000` ya sobrecubre (> 0.97), no se añade piso y se documenta que el error de
conteo ya basta. El resultado (piso elegido, cobertura lograda) se escribe en `docs/backtest.md` sin
redondear para que "se vea bien". Esto reemplaza el criterio de aceptación anterior
("`ic95[1] − ic95[0] ≥ 0.2`" — un ancho mínimo no dice nada sobre si el intervalo está bien
calibrado) por el criterio correcto: cobertura empírica dentro de rango.

Salida: `data/outputs/backtest.json` (métricas + calibración del piso + bloque `metadatos` con la
versión del marco, §2.2) y `docs/backtest.md` (≤ 5 líneas de resumen + tabla + la limitación de
CONAPO). El frontend expone 2–3 cifras en el drawer.

Firmas:
```
adelgazar(panel_d, frac, rng) -> pd.DataFrame
validar_adelgazamiento(panel_d, fracs=(0.25, 0.5), rng) -> pd.DataFrame
validar_loao(panel_d) -> pd.DataFrame
backtest_oferta(panel_o) -> pd.DataFrame
calibrar_piso_incertidumbre(res_adelg, res_loao, res_oferta, candidatos=...) -> dict  # §6.1
metricas(y_real, y_pred, clases_real, clases_pred, ic=None) -> dict   # mae, f1_macro, cobertura
escribir_reporte(resultados, destino_json, destino_md) -> None
```

Tests (`tests/test_backtest.py`): **sin fuga de futuro** (el origen nunca ve datos posteriores),
determinismo con `SEMILLA`, baseline calculado sobre el mismo universo que el modelo, y
`calibrar_piso_incertidumbre` nunca elige un candidato por fuera de la rejilla ni redondea la
cobertura lograda.

## 7. Exportación (`exportar.py`, punto de entrada de `make pipeline`)

- `main()`: io → panel → modelos → **backtest** (incluye calibración del piso, §6.1) → features →
  exportar; log en español con conteos. ✅
- Contrato `version` **1.4** ✅ (Fase 6 de `correccion/action_plan.md`; ver también fases 1/4/5, que
  entregaron horizontes, segmentos y ramas por separado antes del salto de contrato único). `fecha_base
  = "2026-06"`; `horizontes = [{h1, 1, "2027-06"}, {h3, 3, "2029-06"}, {h5, 5, "2031-06"}]`.
- Esquema por unidad de la capa `demanda`: `cve_mun, n_obs, motivo_sin_datos, serie, nivel_base,
  h{...}`, **una entrada por segmento de población objetivo** (metodología §1.1:
  `todas, primera_infancia, preescolar, primaria, secundaria, adolescencia`); cada `h` con
  `veredicto, delta_pct, tasa_anual_pct, ic95[2], confianza`. ✅
- **Las cuatro ramas reemplazan a la capa `oferta`** (metodología §1, tabla de ramas):
  `capas.ramas.{educacion, salud, comercio, verde}`. Educación, salud y comercio comparten forma
  (proyección Poisson, `horizontes_disponibles: ["h1","h3"]`, tope de confianza `media`); verde no
  tiene componente temporal (`horizontes_disponibles: []`, solo `nivel_base`).
  **Cada rama se publica por celda de filtro**, no ya agregada (metodología §10.6): un objeto
  `celdas: {clave_celda: {...mismos campos que hoy tenía "oferta"...}}` por AGEB, donde
  `clave_celda` combina nivel/tipo × sector (tabla exacta de celdas por rama: §11 más abajo, tarea
  B22). El cliente suma las celdas que el usuario seleccionó (metodología §10.6): el backend nunca
  decide qué filtro está activo.
- `sin_datos`: campos numéricos `null`, `confianza: "baja"`, `n_obs` real (0, 1 o 2) — nunca se omite. ✅
- **Todas** las 2,453 claves del universo aparecen en `capas.demanda` (rurales como `sin_datos`); en
  cada rama igual. Redondeo a 1 decimal. `generado` = ISO-8601 con zona. ✅
- `prediccion_alcaldia.json`: mismo esquema por `CVE_MUN`, más `distribucion_ageb` por horizonte y
  `agregado_cdmx` en la raíz. ✅
- **`capas.brecha` se retira del contrato.** La sustituye el cálculo client-side de §10.1-10.3 de
  metodología (cobertura + índice de oportunidad por rama), porque depende de pesos y filtros que
  solo existen en el cliente; publicar una "brecha" fija en el backend ya no tiene sentido con
  cuatro ramas filtrables. `diagnostico.json` conserva un resumen agregado por CDMX/alcaldía como
  contexto de depuración, fuera del contrato. ✅
- JSON determinista: claves ordenadas, `ensure_ascii=False`, `separators` compactos; misma semilla →
  mismo archivo byte a byte salvo `generado`. ✅

Validaciones antes de escribir (fallan el pipeline):
- `version == "1.4"`; veredicto ∈ {sube, se_mantiene, baja, sin_datos}; confianza ∈ {alta, media, baja}. ✅
- Todo registro tiene `confianza` y `n_obs`; `ic95[0] ≤ delta_pct ≤ ic95[1]` cuando no es null. ✅
- **Cobertura del IC95 dentro de `[0.90, 0.97]` en el backtest** (§6.1; sustituye al invariante de
  ancho mínimo `ic95[1]−ic95[0] ≥ 0.2` de la versión anterior de este plan, que era un criterio
  equivocado — ver metodología §6.2). ✅
- `cvegeo` único, 13 o 9 caracteres, `cve_mun` coherente con `cvegeo[2:5]`. ✅
- Alcaldía: 16 claves 002–017; Σ nivel AGEB = nivel alcaldía por horizonte (`verificar_suma_ageb_alcaldia`). ✅
- Ramas educación/salud/comercio: ningún `confianza == "alta"`. Verde: sin `h`, solo `nivel_base`. ✅
- Horizontes declarados en la raíz = horizontes presentes en cada registro (o subconjunto declarado
  en `horizontes_disponibles`). ✅
- **Σ `Ŝ_celda` de una rama en una AGEB coherente con el total sin filtrar — no implementado,
  desviación del plan.** El contrato v1.4 (Fase 6) nunca publica un "total sin filtrar" por rama:
  cada celda es su propio ajuste Poisson+EB independiente (no una partición de un total ya
  simulado), así que no hay una cifra de referencia contra la que comparar la suma sin volver a
  correr el modelo sobre el panel sin filtrar de cada rama (costo ≈ duplicar el paso más caro del
  pipeline). Pendiente de decisión del equipo: publicar igual un total de referencia por rama
  (nuevo costo de cómputo) o retirar este invariante del plan.

Firmas (estado real del módulo; nombres reales del código, no los propuestos en la versión anterior
de este plan — `construir_capa_rama` se entregó como `construir_capa_demanda_v14`/
`construir_capa_rama_v14`/`construir_capa_verde`, tres funciones en vez de una sola, porque demanda
[segmentos] y ramas con proyección [celdas] anidan distinto y verde no pasa por `modelos.resumir`):
```
construir_capa(res, universo, series, nivel_base, horizontes, motivos, incluir_horizontes_disponibles=False) -> dict  # ✅
construir_capa_demanda_v14(capas_por_segmento) -> dict                   # ✅
construir_capa_rama_v14(capas_por_celda, horizontes_disponibles) -> dict # ✅
construir_capa_verde(contexto, universo, celdas) -> dict                 # ✅
construir_distribucion_ageb(capa, horizontes) -> dict                    # ✅
construir_agregado_cdmx(res_d_por_segmento, res_ramas_por_celda, capa_verde_cdmx) -> dict  # ✅
construir_salida_ageb(...) -> dict · construir_salida_alcaldia(...) -> dict   # ✅
validar_contrato(salida, nivel: Literal['ageb','alcaldia']) -> None       # ✅ lanza ErrorContrato
verificar_suma_ageb_alcaldia(ageb, alcaldia) -> None                      # ✅
escribir_json(salida, ruta) -> None · main() -> None                      # ✅
```

## 8. Módulos, tests y Makefile

```
backend/src/chipos/
  __init__.py
  config.py      rutas, constantes del modelo, SEMILLA (único lugar de parámetros)   ✅
  io.py · panel.py · features.py · modelos.py · exportar.py                          ✅
  backtest.py                                                                        ✅
backend/tests/
  conftest.py            fixtures sintéticas pequeñas (no leen data/ salvo marca @datos)  ✅
  test_geo.py test_io.py test_panel.py test_modelos.py test_exportar.py test_features.py  ✅
  test_backtest.py                                                                   ✅
```

### 8bis. `features.py`: de la brecha histórica al índice de oportunidad por rama

**Hoy ✅:** brecha `S_2024 / D_2020 × 1000` por AGEB y alcaldía → contrato y `diagnostico.json`.
Mezcla dos momentos distintos, es histórica y no responde la pregunta de la rúbrica. Se retira del
contrato (§7).

**Entregado ✅ (Fase 6)** (fórmula exacta y completa en metodología §10; aquí solo las firmas y el
orden de cómputo — **no** se reescribe la fórmula en dos lugares):

```
cobertura_proyectada(sim_d_seg, sim_rama, horizontes) -> pd.DataFrame   # §10.1: Ŝ/D̂×1000 por réplica,
    # no sobre medianas; Ŝ=0 con D̂>0 es un valor válido (nunca sin_datos); sin_datos solo si D̂
    # inválido o el conteo base de la rama nunca superó S_MIN_CONF
indice_oportunidad(cobertura, tasa_d, tasa_s, k_normalizacion=5.0) -> pd.DataFrame  # §10.2: paso 1
    # rango percentil (empates promediados) + paso 2 ajuste de tendencia acotado ±0.15 + paso 3 clip
sensibilidad_indice_oportunidad(cobertura, tasa_d, tasa_s, ks=(3.0, 5.0, 8.0)) -> dict  # §10.2,
    # a diagnostico.json; marca AGEB cuyo orden relativo cambia sustancialmente entre K=3 y K=8
indice_disponibilidad(cobertura, confianza, tasa_s) -> pd.DataFrame     # §10.5, vista separada,
    # nunca se combina con indice_oportunidad en el mismo campo del contrato
```

**Lo que el backend NO calcula: el índice compuesto.** `IC_{i,h}` (metodología §10.3) combina las
cuatro ramas con los pesos que el usuario mueve en tiempo real — es responsabilidad del **motor de
composición del frontend** (`plans/frontend_specs.md` §17), no de `features.py`. El backend solo
garantiza que `O_{i,h,r}` (por rama, por celda de filtro agregada) esté disponible para que el
cliente lo combine sin volver a llamar al pipeline. El **nivel de riesgo** tampoco es un cálculo del
backend: se publican `p_dec` y `confianza` por unidad de demanda y el frontend filtra.

Covariables estáticas de contexto (áreas verdes, espacios públicos) alimentan directamente la rama
"verde" (metodología §1, tabla de ramas) — dejan de ser solo descriptivas de fondo y pasan a tener
su propio `cobertura_proyectada`/`indice_oportunidad` (sin componente temporal, §10.1). 🔄 fase 7/9

Tests clave:
- `test_modelos` ✅: EB con τ²→∞ ⇒ `r̃ = r̂`; ψ→∞ ⇒ `r̃ = ρ_m`; control por razón reproduce
  `C_T_HOR/C_2020.20` por alcaldía (1e-9); regla de veredicto en bordes (0.7999/0.80/0.95);
  topes de confianza; determinismo con semilla; Newton-Raphson = `statsmodels` GLM Poisson (1e-6).
  Incluye: `var_post ≥ SIGMA_MIN_TASA²`; `φ_m ≥ 1`.
- `test_panel` ✅: sin `cvegeo` duplicados; ceros explícitos; filtro de claves; motivo de `sin_datos`;
  Σ segmentos (incl. 15–17) = total 0–17 por AGEB.
- `test_exportar` ✅: esquema válido; 2,453 claves; suma AGEB = alcaldía; ningún `alta` en ramas
  proyectables; `version == "1.4"`, 3 horizontes. Pendiente (no implementado, ver §7): Σ celdas de
  filtro = total sin filtrar, por rama y AGEB.
- `test_backtest` ✅: sin fuga de futuro; determinismo; baseline sobre el mismo universo;
  ninguna métrica usa `pobproy_quinq1.csv` como si fuera observación independiente (test explícito
  que falla si `backtest_conapo` reaparece).
- `test_features` ✅: brecha histórica (superseded) + `indice_oportunidad` con
  `Ŝ=0, D̂>0` produce el percentil máximo (no `sin_datos`); `D̂=0` produce `sin_datos`; sensibilidad
  con `K∈{3,5,8}` no cambia el signo del ajuste (`|ajuste| ≤ 0.15` siempre).
- Marca `@pytest.mark.datos` para tests sobre datos reales (se saltan si falta `data/interim/`). ✅

Makefile: `pipeline`, `test`, `validar`, `datos`, `perfil`, `serve`, `frontend-datos`, `vendor-d3`
ya existen ✅, incluido el target `backtest` (`python -m chipos.backtest`, solo reporte).
`data/outputs/` está versionado (salidas pequeñas) ✅.

## 9. Tareas

### 9.1 Entregadas

| id | objetivo | archivos | estado |
|---|---|---|---|
| B0 | Andamiaje del paquete y constantes | `__init__.py`, `config.py`, `tests/conftest.py` | ✅ |
| B1 | Verificar geometría y versión del marco | `tests/test_geo.py` | ✅ |
| B2 | Capa de lectura | `io.py`, `tests/test_io.py` | ✅ |
| B3 | Panel de demanda + reglas 2010→2020 | `panel.py`, `tests/test_panel.py` | ✅ |
| B4 | Panel de oferta + verificación SCIAN | `panel.py`, `tests/test_panel.py` | ✅ |
| B5 | Regla de veredicto y confianza | `modelos.py`, `tests/test_modelos.py` | ✅ |
| B6 | Modelo de demanda (EB + CONAPO + simulación) | `modelos.py`, `tests/test_modelos.py` | ✅ |
| B7a | Modelo de oferta | `modelos.py`, `tests/test_modelos.py` | ✅ |
| B8 | Agregación a alcaldía | `modelos.py` | ✅ |
| B10 | Brecha (features mínimas) | `features.py` | ✅ (histórica; la sustituye B17, retirada del contrato en Fase 6) |
| B11 | Exportación + validación de contrato | `exportar.py`, `tests/test_exportar.py` | ✅ |
| B12 | Makefile y docs | `Makefile`, `docs/` | ✅ |
| B13 | Horizontes 1/3/5 (infraestructura) | `config.py`, `exportar.py`, `frontend/js/config.js`, `frontend/mock/generar_mock.py` | ✅ |
| B9 | Validación y backtest (sin CONAPO circular) | `backtest.py`, `tests/test_backtest.py`, `docs/backtest.md`, `Makefile` | ✅ |
| B14 | Piso de incertidumbre calibrado + sobredispersión | `config.py`, `backtest.py`, `modelos.py`, `tests/test_modelos.py` | ✅ |
| B15 | Escenarios A/B de la caída DENUE 2024 | `modelos.py`, `features.py`, `diagnostico.json` | ✅ |
| B16 | Segmentos de población objetivo (6 segmentos Habitancia) | `io.py`, `panel.py`, `exportar.py`, `tests/test_panel.py` | ✅ |
| B21 | Contexto CDMX (áreas verdes, espacios públicos) → datos crudos de la rama verde | `io.py`, `tools/` | ✅ |
| B22 | Generalizar oferta a 4 ramas + celdas de filtro | `io.py`, `panel.py`, `modelos.py`, `exportar.py`, `tests/test_panel.py`, `tests/test_modelos.py` | ✅ |
| B17 | Cobertura proyectada e índice de oportunidad (fórmula exacta) | `features.py`, `exportar.py`, `tests/test_features.py` | ✅ |
| B18 | Índice de disponibilidad (vista familias) | `features.py`, `exportar.py` | ✅ |

### 9.2 Pendientes

Todas las tareas de modelado (B9, B13–B18, B21, B22) están entregadas (tabla 9.1); solo queda
reconciliación de documentación y el backtest opcional de CONAPO.

| id | objetivo | archivos | acepta cuando | tam. | fase | depende | paralelo con |
|---|---|---|---|---|---|---|---|
| B20 | Reconciliar docs y CLAUDE.md | `CLAUDE.md`, `docs/metodologia.md`, `docs/estado_datos.md` | ninguna marca 🔄 sin entregar; contrato v1.4 descrito en un solo lugar; sin restos de `capas.oferta`/`capas.brecha` en la documentación | S | 9 | B9, B14, B17, B22 | — |

**Opcional, no bloqueante (mencionada en §6, metodología §4.1):**

| id | objetivo | archivos | acepta cuando | tam. | fase | depende |
|---|---|---|---|---|---|---|
| B23 | Backtest genuino de CONAPO con una vintage anterior a 2020 | `tools/descargar_datos.py` (fuente nueva), `backtest.py` | se localiza y descarga una edición CONAPO publicada antes del Censo 2020 (p. ej. "2016–2050, base Censo 2010"); su predicción de 2020 se compara contra el Censo 2020 real; si no se consigue a tiempo, se documenta como intento fallido, no se omite en silencio | M | 2/7 | B9 |

**Paralelizables realmente** (archivos disjuntos o sin dependencia de datos): {B13, B21}, {B16, B21},
{B15, ...tras B14}. B9 → B14 → B15 → B22 → B17 → B18 es la cadena crítica: cada uno consume el
resultado del anterior (backtest → piso calibrado → escenarios de oferta → generalización a ramas
→ índice de oportunidad). B13, B16 y B22 comparten el salto a v1.4: conviene un solo bloque final de
trabajo sobre `exportar.py`, `validar_contrato()` y `frontend/js/api.js` una vez que B22 esté listo,
en vez de tocar el contrato tres veces.
Commits: uno por tarea (`feat:`/`test:`/`docs:`).

## 10. Verificación

`make datos && make pipeline && make backtest && make test && make validar`;
`git status data/processed data/reference` vacío; `docs/backtest.md` con modelo vs baseline y la
limitación de CONAPO declarada (§6, metodología §4.1); reejecutar `make pipeline` → mismo JSON byte
a byte (salvo `generado`).

Criterios añadidos por `correccion/action_plan.md`:
- Ningún `.md` citado por el código apunta a un archivo inexistente.
- Cobertura empírica del IC95 en el backtest dentro de `[0.90, 0.97]` (sustituye al criterio de ancho
  mínimo de la versión anterior de este plan).
- Ningún backtest usa `pobproy_quinq1.csv` como si sus años fueran observaciones independientes.
- `indice_oportunidad` nunca convierte `Ŝ=0` (con `D̂>0`) en `sin_datos`.
- El caso de prueba de `correccion/rubrica.md` §8 ("zonas donde la demanda aumentará en tres años,
  evitando áreas con oferta ya saturada") se responde con la salida del pipeline, sin cálculos a
  mano; el caso de `correccion/frontend_requisitos.md` §24 (educación + salud, primaria pública +
  hospitales/clínicas, horizonte 3 años) se responde combinando dos ramas del contrato v1.4.

## Preguntas abiertas

**Resueltas desde la versión anterior:**
- ~~B2 · Campos extra~~ → el contrato subió a 1.2, luego a 1.4; `brecha` se retira (§7) y la
  sustituye el cálculo client-side de cobertura/oportunidad; sensibilidad (δ, λ, K) y probabilidades
  por unidad quedan en `diagnostico.json`, fuera del contrato.
- ~~B3 · AGEB con `division`~~ → la hija hereda la **tasa** de la madre; `D_2010` no se reescala por
  `frac_de_2010` (§4.2). Afecta solo a 1 AGEB.
- ~~B4 · Milpa Alta (009)~~ → se publica igual, etiquetada "solo urbano", sin tope de confianza (§5.4).
- ~~B5 · `tasa_anual_pct`~~ → tasa logarítmica ×100, coherente con la banda δ de metodología §7.
- ~~B6 · Ancla de los segmentos~~ → los segmentos heredan el factor de control `k_m^s` de 0–14
  (CONAPO no publica 0–2/3–5/6–11/12–14 ni 15–17 exacto); documentado en metodología §1.2.
  Aproximación declarada, no una identidad.

**Resueltas (2026-09-20, con cifras reales del backtest):**
- ~~B1 · Ramas sin ventaja sobre el baseline~~ → el modelo de oferta (educación) NO supera a "S
  constante" en MAE (5.45 vs 3.61 en log-razón), aunque sí en F1 macro (0.67 vs 0.20)
  (`docs/metodologia.md` §4). **Decisión del equipo: se mantiene** el tratamiento Poisson+EB
  actual para educación/salud/comercio (Fase 5), con la limitación documentada explícitamente en
  el drawer de metodología (Fase 7) en vez de omitir la rama o quitarle el veredicto. No cambia el
  diseño de B17/B22.

**Abiertas:**
2. **B7 · Umbral del índice de oportunidad.** El percentil de `indice_oportunidad` (metodología
   §10.2) ¿se calcula sobre todas las AGEB con dato, o solo sobre las urbanas del mismo segmento y
   rama? Afecta el ranking, no el modelo. Recomendación: solo sobre las urbanas del mismo
   segmento/rama/horizonte — comparar contra AGEB rurales `sin_datos` no aporta información.
3. **B8 · `K` de la tendencia comparativa.** Metodología §10.2 fija `K=5` pp/año por omisión, sin
   exponerlo al usuario. ¿Se ajusta ese valor una vez que exista el backtest de oferta (B9), o se
   deja fijo? Recomendación: recalibrar `K` como el `p90` de `|Δ_{i,r}|` observado en el backtest de
   oferta, una vez disponible — mismo espíritu que la calibración del piso (§6.1), pero no bloquea
   la primera entrega (`K=5` es un valor razonable de partida, documentado como tal).
4. **B9 · Vintage CONAPO anterior a 2020 (B23).** ¿Existe y es descargable una edición pre-2020?
   `docs/data_manifest.md` no la registra hoy. Si no se localiza dentro del tiempo disponible antes
   de la entrega, la limitación de metodología §4.1 punto 4 queda como está: declarada, no fingida.
