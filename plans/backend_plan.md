# Plan de backend y algoritmos

Objetivo: `make pipeline` regenera `data/outputs/prediccion_ageb.json` y `prediccion_alcaldia.json`
(contrato `version 1.1` de CLAUDE.md) aplicando exactamente `docs/metodologia.md`. Este plan no
depende del frontend; la única interfaz es el contrato de salida y `data/reference/ageb_cdmx*.geojson`.

Convenciones: paquete `backend/src/chipos/`, Python 3.11+, sin dependencias nuevas (todo está en
`requirements.txt`). Semilla global `SEMILLA = 20260918`. Tiempo en años decimales.

## 1. Problemas de datos que afectan la implementación

| sev. | problema (ref.) | efecto en la implementación | mitigación |
|---|---|---|---|
| — | **Bloqueantes: ninguno abierto.** Censo 2010/2020, CONAPO y geometría AGEB resueltos (C1, C4, C5). | — | Tarea B1 solo re-verifica. |
| Importante | DENUE con 2 re-levantamientos; 11 cortes no independientes (C2) | Tratar 11 cortes como serie = pseudo-réplica | Solo 3 cortes de oferta: 2016-10, 2019-11, 2024-11 (fechas 2016.79, 2019.87, 2024.87) |
| Importante | Caída infancias 2024-11 −11.2 %, concentrada en privado (C3) | Sesgo de tasa si se fecha en 2024 | Eje = fechas de levantamiento; tope de confianza `media` en oferta; nota en metadatos |
| Importante | CONAPO > censo urbano en nivel (+5.9 %, hasta +29.7 % en 009) (N1) | Control por nivel inflaría AGEB | Control por **razón** 2027.5/2020.20, nunca por nivel |
| Importante | CONAPO proyecta caídas fuertes (−1.45 a −4.19 %/año) (N2) | Casi todo AGEB saldrá `baja` | Resultado sustantivo; se reporta reparto y sensibilidad δ ∈ {0.5, 1, 2} |
| Importante | `λ` (persistencia de la desviación local) no identificable con 2 censos (metodología §3) | IC dominados por supuesto | Previa `U(0.25, 1)`; veredicto con λ ∈ {0.25, 0.6, 1}; si cambia, confianza −1 nivel |
| Importante | 100 AGEB con geometría 2010→2020 no idéntica (N5) | Denominador 2010 de otra superficie | Reglas de `relacion` (§4.2); confianza máx. `media` |
| Menor | Mojibake en nombres de alcaldía 2016–2018 (A1) | Grupos duplicados | Agrupar siempre por `CVE_MUN` de la clave AGEB |
| Menor | Tipos inestables (`Mes de corte`, `Año de alta DENUE`) (M3) | Errores de unión entre años | `read_csv(all_varchar=true)` y casteo explícito |
| Menor | Puntos fuera de CDMX con `Coordenadas válidas = 1` (M2) | Asignación errónea | Territorio por clave AGEB, no por coordenadas; filtro de clave (13 car., `09`, MUN 002–017) |
| Menor | Cambio SCIAN 2013→2018 (M1); sin tabla de armonización para infancias | Altas/bajas artificiales por código | Tarea B4 verifica qué códigos `Principal` no están en los 3 cortes; si alguno, se excluye y se documenta |
| Menor | Claves sin polígono: 2 censales, 5 DENUE rurales (N3) | Filas huérfanas | `sin_datos`; contadas en el reporte de cobertura |
| Menor | 0–14 suprimido por INEGI (41 AGEB 2020), `D_2020 < 20` (23) | — | `sin_datos`, nunca imputar |

## 2. Geometría AGEB (ya adquirida; solo verificación)

Estado: `tools/build_geo.py` ya produjo `data/reference/ageb_cdmx.geojson` (MG 2020 censal, 09a + 09ar,
EPSG:4326, `make_valid`) y `ageb_cdmx_simplificado.geojson` (mapshaper 25 %, 5 decimales, 1.51 MB).
No se re-descarga. Pasos del plan:
1. Test de verificación (`backend/tests/test_geo.py`): 2,453 features; `cvegeo` único; 2,431 con 13
   caracteres y `ambito = urbano`, 22 con 9 caracteres y `ambito = rural`; `cve_mun` ∈ 002–017; bbox
   dentro de [−99.37, 19.04, −98.94, 19.60]; mismo conjunto de claves en completo y simplificado.
2. Versión del marco: afirmar join censo 2020 → polígono ≥ 99.9 % y claves DENUE `Principal` 2026-05 →
   polígono ≥ 99.7 % (valores de `perfil_datos.md`); registrar "MG 2020 censal, UPC 889463807469" en
   el bloque `metadatos` del reporte de backtest.
3. Ningún archivo de `data/reference/` se reescribe; si hiciera falta TopoJSON lo genera el frontend
   en su propia carpeta.

## 3. Capa de lectura `io.py` (DuckDB)

- Una conexión DuckDB en memoria por ejecución; consultas con proyección de columnas (nunca `SELECT *`).
- DENUE infancias: `read_csv(ruta, all_varchar=true, header=true)`; columnas: `ID`, `Clave geográfica AGEB`,
  `Alcance`, `Sector`, `Código SCIAN`, `Subcategoría`, `Edición DENUE`. Casteo: `ID`→BIGINT,
  `Código SCIAN`→INTEGER. Normaliza nombres a `snake_case` (`id, cvegeo, alcance, sector, scian,
  subcategoria, edicion`).
- Mapa de ediciones → archivo y fecha de levantamiento en una constante `CORTES_OFERTA`
  (`{"2016-10": 2016.79, "2019-11": 2019.87, "2024-11": 2024.87}`); `EDICIONES_TODAS` para diagnóstico.
- Censo: lee `data/interim/censo_ageb_panel.parquet` (ya limpio por `tools/build_censo.py`).
- CONAPO: `data/interim/conapo_mun_0a14.parquet`.
- Equivalencia: `data/interim/equivalencia_ageb_2010_2020.parquet`.
- Geometría: solo propiedades (`cvegeo, cve_mun, ambito`) vía `pyogrio.read_dataframe(..., read_geometry=False)`.
- Si falta un parquet de `data/interim/`, error claro: "ejecuta `make datos`".

Firmas:
```
conectar() -> duckdb.DuckDBPyConnection
leer_denue_infancias(con, ediciones: Iterable[str]) -> pd.DataFrame      # id, cvegeo, cve_mun, alcance, sector, scian, edicion, t
leer_censo_panel() -> pd.DataFrame                                        # cvegeo, anio, t, cve_mun, pob_0a14, ...
leer_conapo_0a14() -> pd.DataFrame                                        # cve_mun, anio, pob_0a14
leer_equivalencia() -> pd.DataFrame
leer_universo_ageb() -> pd.DataFrame                                      # cvegeo, cve_mun, ambito (2,453 filas)
```

## 4. Panel AGEB × corte (`panel.py`)

### 4.1 Demanda
- Unidad: AGEB urbana del MG 2020 (universo = `leer_universo_ageb()`).
- `D_it = pob_0a14` (ya = P_0A2+P_3A5+P_6A11+P_12A14), `t ∈ {2010.44, 2020.20}`.
- Columnas de salida: `cvegeo, cve_mun, ambito, relacion, d_2010, d_2020, motivo_sin_datos`.
- `motivo_sin_datos` ∈ {`rural`, `suprimido_inegi`, `d2020_menor_20`, `sin_poligono`, `sin_censo`, null}.
  Las 2 claves censales sin polígono se registran en el reporte de cobertura, no en el JSON.

### 4.2 Tratamiento geográfico 2010→2020 (según `relacion`)
| relacion | d_2010 usado | n_obs | tope de confianza |
|---|---|---|---|
| misma | el de la misma clave | 2 | — |
| division | el de la madre 2010 **reescalado por `frac_de_2010`** — ver Pregunta B3 | 2 | media |
| fusion_o_expansion, cambio_limites | el de la misma clave | 2 | media |
| sin contraparte | — (`r̃ = ρ_m`) | 1 | baja |

### 4.3 Oferta
- `S_it` = nº de `ID` distintos con `alcance = 'Principal'` por `cvegeo` y corte (3 cortes).
- Filtros: clave de 13 caracteres, prefijo `09`, `cve_mun` 002–017, presente en el universo urbano.
  Claves rurales/sin polígono → contadas en cobertura, `sin_datos`.
- Duplicados: aserción de `ID` único por edición (B2 lo confirma hoy); si falla, error, no deduplicar en silencio.
- SCIAN: calcular códigos `Principal` presentes en los 3 cortes; los que no, se reportan (código,
  filas por corte) y se excluyen **solo** si su ausencia es de catálogo (aparece/desaparece en toda
  la CDMX en una edición). Decisión y conteos → `docs/metodologia.md` §6.
- Completar el panel con ceros explícitos para AGEB urbanas sin establecimientos en un corte.
- Salida: `cvegeo, cve_mun, t, s` (formato largo) + `s_2024` para brecha.

Firmas:
```
construir_panel_demanda(censo, equivalencia, universo) -> pd.DataFrame
construir_panel_oferta(denue, universo, cortes=CORTES_OFERTA) -> pd.DataFrame
reporte_cobertura(panel_d, panel_o, universo) -> dict   # conteos por motivo, para el log y el backtest
```

## 5. Algoritmo de estimación (`modelos.py`)

Constantes (único lugar, reflejadas en `docs/metodologia.md` §7): `T_2010=2010.44`, `T_2020=2020.20`,
`T_HOR=2027.5`, `DELTA=0.01`, `P_DECISION=0.80`, `P_ALTA=0.95`, `P_MANTIENE=0.50`, `N_SIM=4000`,
`LAMBDA_PREVIA=(0.25, 1.0)`, `LAMBDAS_SENS=(0.25, 0.6, 1.0)`, `DELTAS_SENS=(0.005, 0.01, 0.02)`,
`D_MIN_CONF=100`.

### 5.1 Demanda
1. Tasa directa `r̂_i = ln[(D_i,20+0.5)/(D_i,10+0.5)]/Δt`, `Δt = 9.76`;
   `ψ_i = [1/(D_i,20+0.5) + 1/(D_i,10+0.5)]/Δt²`.
2. `ρ_m` = misma fórmula con sumas de la alcaldía.
3. `τ²` por momentos, agrupado en toda la CDMX: `τ² = max(0, mean((r̂_i − ρ_m)²) − mean(ψ_i))`
   (se reporta también por alcaldía como diagnóstico).
4. `B_i = ψ_i/(ψ_i+τ²)`; `r̃_i = B_i ρ_m + (1−B_i) r̂_i`; var. posterior `(1−B_i)ψ_i`.
5. `ρ_m,CONAPO = ln(C_m,2027 / C_m,2020)/7` (cifras de mitad de año).
6. `C_m,2020.20` = interpolación log-lineal entre 2019 (2019.5) y 2020 (2020.5).
7. Por réplica s = 1..4000: `r_i^s ~ N(r̃_i, (1−B_i)ψ_i)`, `λ^s ~ U(0.25,1)`,
   `ε_m^s ~ N(0, σ_C,m²)` con `σ_C,m = |ρ_m,censo 2010–20 − ρ_m,CONAPO 2010–20|`;
   `r_i,fut^s = ρ_m,CONAPO + ε_m^s + λ^s (r_i^s − ρ_m)`.
8. Control por razón: `k_m^s = [C_m,2027.5/C_m,2020.20] · Σ_i D_i,20 / Σ_i D_i,20·exp(r_i,fut^s·(T_HOR−T_2020))`
   y `r_i,fut^s ← r_i,fut^s + ln(k_m^s)/(T_HOR−T_2020)` (mantiene la forma log-lineal).
   `ε_m^s` se aplica **después** del control, sobre la razón de CONAPO, para que el choque compartido
   sobreviva al reescalado.
9. Salidas por AGEB: `tasa_anual_pct = 100·mediana(r_i,fut^s)`; `delta_pct = 100·(mediana(exp(r·(T_HOR−T_2020))) − 1)`;
   `ic95` = percentiles 2.5/97.5 de `delta_pct^s`; `p_sube = P(r > +δ)`, `p_baja = P(r < −δ)`,
   `p_mantiene = P(|r| ≤ δ)`.

### 5.2 Oferta
- Por AGEB: Poisson log-lineal `log E[S_it] = a_i + b_i (t − 2019.87)` sobre 3 cortes, ajuste por
  Newton-Raphson vectorizado (sin bucle `statsmodels` por AGEB; `statsmodels` solo en el test de
  paridad). `var(b_i)` = inversa de la información de Fisher.
- EB: igual que 5.1 pasos 3–4 hacia `b_m` (pendiente Poisson de la suma de la alcaldía). Sin control externo.
- Simulación `b_i^s ~ N(b̃_i, var_post)`; `delta_pct` = cambio 2024.87 → 2027.5; mismas probabilidades.
- `sin_datos` si `S = 0` en los 3 cortes o AGEB rural. Confianza con tope `media`. `n_obs = 3`.

### 5.3 Regla de veredicto (única función, compartida por ambas capas)
```
veredicto(p_sube, p_baja, p_mantiene):
    si p_sube ≥ 0.80: 'sube', p_dec = p_sube
    si p_baja ≥ 0.80: 'baja', p_dec = p_baja
    si p_mantiene ≥ 0.50: 'se_mantiene', p_dec = p_mantiene
    si no: 'se_mantiene', confianza forzada 'baja'
confianza: 'alta' si p_dec ≥ 0.95 y estable en λ ∈ {0.25,0.6,1}; 'media' si p_dec ≥ 0.80; si no 'baja'
    bajar un nivel si el veredicto cambia con λ
    'baja' forzada si n_obs = 1 o D_2020 < 100
    aplicar topes (relacion no 'misma' → media; capa oferta → media)
```
Sensibilidad: recalcular veredictos con δ ∈ {0.5, 1, 2} %/año y λ fijo ∈ {0.25, 0.6, 1};
se guarda en `data/outputs/diagnostico.json` (fuera del contrato; ver Pregunta B2).

### 5.4 Agregación a alcaldía
- Por réplica: `D̂_m^s = Σ_{i∈m} D̂_i^s` sobre AGEB con dato; tasa de alcaldía = log-razón anualizada;
  mismo `veredicto()`. `n_obs = 2` (demanda) y `3` (oferta). Δ% desde sumas, nunca promedio de %.
- Cobertura vs CONAPO por alcaldía (Σ D_2020 urbano / C_m,2020.20) en `diagnostico.json`.

Firmas:
```
tasa_directa(d0, d1, dt) -> tuple[np.ndarray, np.ndarray]           # r_hat, psi
contraccion_eb(r_hat, psi, rho_m_por_ageb) -> tuple[np.ndarray, np.ndarray, float]  # r_tilde, var_post, tau2
tasa_conapo(conapo, t0, t1) -> pd.Series                              # por cve_mun
simular_demanda(panel_d, conapo, rng, n_sim=N_SIM, lam=None) -> SimDemanda  # arrays (n_ageb, n_sim) + índices
ajustar_oferta(panel_o) -> pd.DataFrame                               # b_hat, var_b por AGEB
simular_oferta(ajuste, rng, n_sim=N_SIM) -> SimOferta
veredicto(p_sube, p_baja, p_mantiene) -> tuple[str, float]
confianza(p_dec, estable_lambda, n_obs, d2020, tope) -> str
resumir(sim, delta=DELTA) -> pd.DataFrame                             # una fila por unidad, campos del contrato + probabilidades
agregar_alcaldia(sim) -> SimDemanda | SimOferta
```

## 6. Validación y backtesting (`backtest.py`)

Demanda (sustitutos del origen móvil, metodología §4; semilla fija):
1. **Adelgazamiento binomial** al 25 % y 50 %: estimar `r̂` y `r̃` sobre conteos adelgazados y comparar
   contra `r̂` completo. Métricas: MAE de la tasa (pp/año), cobertura IC95, F1 macro de 3 clases.
   Competidores: `r̃` (EB), `r̂` directo, `ρ_m`, baseline `r = 0`.
2. **Dejar una alcaldía fuera** para `τ²`: cobertura del IC95 en la alcaldía excluida ∈ [0.90, 0.97].
3. **Censo vs CONAPO 2010–2020** por alcaldía: tabla de discrepancias (alimenta `σ_C`).
4. **Origen móvil CONAPO municipal** (orígenes 2000, 2005, 2010, 2015; horizontes 5 y 7): tendencia
   log-lineal de 10 años vs `r = 0`; F1 de la banda δ=1 %.
Oferta: ajuste con 2016.79 y 2019.87 → predecir 2024.87; baseline `S` constante. MAE de log-razón,
deviance Poisson y F1 macro. Nota obligatoria: el objetivo 2024 contiene la caída C3 (difícil para ambos).

Criterio de adopción: demanda EB se adopta si en (1) y (2) supera a `r = 0` en MAE **y** F1 macro y
la cobertura está en rango. Oferta: si no supera al baseline, ver Pregunta B1 (no se decide aquí).
Salida: `data/outputs/backtest.json` (métricas) y `docs/backtest.md` (≤ 5 líneas de resumen + tabla).

Firmas:
```
adelgazar(panel_d, frac, rng) -> pd.DataFrame
validar_adelgazamiento(panel_d, fracs=(0.25, 0.5), rng) -> pd.DataFrame
validar_loao(panel_d) -> pd.DataFrame
backtest_conapo(conapo, origenes=(2000,2005,2010,2015), horizontes=(5,7)) -> pd.DataFrame
backtest_oferta(panel_o) -> pd.DataFrame
metricas(y_real, y_pred, clases_real, clases_pred, ic=None) -> dict   # mae, f1_macro, cobertura
escribir_reporte(resultados, destino_json, destino_md) -> None
```

## 7. Exportación (`exportar.py`, punto de entrada de `make pipeline`)

- `main()`: io → panel → modelos → backtest → exportar; log en español con conteos.
- Esquema por unidad (demanda): `cve_mun, veredicto, delta_pct, tasa_anual_pct, ic95[2], confianza, n_obs`.
  Oferta: `veredicto, delta_pct, confianza, n_obs` (+ `tasa_anual_pct`, `ic95` como en el ejemplo si
  se aprueba; el contrato solo exige los del ejemplo).
- `sin_datos`: campos numéricos `null`, `confianza: "baja"`, `n_obs` real (0, 1 o 2) — nunca se omite.
- **Todas** las 2,453 claves del universo aparecen en `capas.demanda` (rurales como `sin_datos`); en
  `capas.oferta` igual. Redondeo a 1 decimal. `generado` = ISO-8601 con zona; `horizonte: "2027-06"`.
- JSON determinista: claves ordenadas, `ensure_ascii=False`, `separators` compactos; misma semilla →
  mismo archivo byte a byte salvo `generado` (se toma de `SOURCE_DATE_EPOCH` si existe).

Validaciones antes de escribir (fallan el pipeline):
- `version == "1.1"`; veredicto ∈ {sube, se_mantiene, baja, sin_datos}; confianza ∈ {alta, media, baja}.
- Todo registro tiene `confianza` y `n_obs`; `ic95[0] ≤ delta_pct ≤ ic95[1]` cuando no es null.
- `cvegeo` único, 13 o 9 caracteres, `cve_mun` coherente con `cvegeo[2:5]`.
- Alcaldía: 16 claves 002–017; Σ D̂ AGEB = D̂ alcaldía (sobre tabla intermedia
  `data/interim/proyeccion_ageb.parquet`, tolerancia 1e-6 relativa).
- Oferta: ningún `confianza == "alta"`.

Firmas:
```
construir_salida_ageb(res_d, res_o, universo) -> dict
construir_salida_alcaldia(res_d_m, res_o_m) -> dict
validar_contrato(salida: dict, nivel: Literal['ageb','alcaldia']) -> None   # lanza ErrorContrato
escribir_json(salida, ruta) -> None
main() -> None
```

## 8. Módulos, tests y Makefile

```
backend/src/chipos/
  __init__.py
  config.py      rutas, constantes del modelo, SEMILLA (único lugar de parámetros)
  io.py · panel.py · features.py · modelos.py · backtest.py · exportar.py
backend/tests/
  conftest.py            fixtures sintéticas pequeñas (no leen data/ salvo marca @datos)
  test_geo.py test_io.py test_panel.py test_modelos.py test_backtest.py test_exportar.py
```
`features.py` (alcance mínimo): brecha `S_2024 / D_2020 × 1000` por AGEB y alcaldía → `diagnostico.json`;
covariables estáticas (áreas verdes, espacios públicos por join espacial WGS84) **solo** si se usan
como media previa del EB y mejoran §6.1 — por defecto no se implementan (metodología §9).

Tests clave:
- `test_modelos`: EB con τ²→∞ ⇒ `r̃ = r̂`; ψ→∞ ⇒ `r̃ = ρ_m`; control por razón reproduce
  `C_2027.5/C_2020.20` por alcaldía (1e-9); regla de veredicto en bordes (0.7999/0.80/0.95);
  topes de confianza; determinismo con semilla; Newton-Raphson = `statsmodels` GLM Poisson (1e-6).
- `test_panel`: sin `cvegeo` duplicados; ceros explícitos; filtro de claves; motivo de `sin_datos`.
- `test_exportar`: esquema válido; 2,453 claves; suma AGEB = alcaldía; ningún `alta` en oferta.
- Marca `@pytest.mark.datos` para tests sobre datos reales (se saltan si falta `data/interim/`).

Makefile (modificar, no reescribir): `pipeline` ya invoca `chipos.exportar`; añadir `backtest`
(`python -m chipos.backtest`, solo reporte) y `validar` (valida los JSON existentes contra contrato).
`make test` ya existe. Añadir `data/outputs/` al flujo sin git-ignorarlo (salidas pequeñas, versionables).

## 9. Tareas

| id | objetivo | archivos | acepta cuando | tam. | depende | paralelo con |
|---|---|---|---|---|---|---|
| B0 | Andamiaje del paquete y constantes | `backend/src/chipos/__init__.py`, `config.py`, `backend/tests/conftest.py` | `make test` corre (0 tests, verde); constantes de §5 en `config.py` | S | — | — |
| B1 | Verificar geometría y versión del marco | `backend/tests/test_geo.py` | aserciones §2 verdes con datos reales | S | B0 | B2 |
| B2 | Capa de lectura | `io.py`, `tests/test_io.py` | lee 3 cortes con tipos correctos; columnas exactas; error claro sin `make datos` | M | B0 | B1 |
| B3 | Panel de demanda + reglas 2010→2020 | `panel.py` (funciones demanda), `tests/test_panel.py` | 2,453 filas; conteos por `motivo_sin_datos` = perfil (22 rurales, 41 suprimidos, 23 <20) | M | B2 | B4* |
| B4 | Panel de oferta + verificación SCIAN | `panel.py` (funciones oferta), `tests/test_panel.py` | totales Principal por corte = conteo DuckDB directo; reporte de códigos no comunes | M | B3 (mismo archivo) | — |
| B5 | Regla de veredicto y confianza | `modelos.py` (`veredicto`, `confianza`), `tests/test_modelos.py` | tests de bordes verdes | S | B0 | B2–B4 |
| B6 | Modelo de demanda (EB + CONAPO + simulación) | `modelos.py`, `tests/test_modelos.py` | tests §8 verdes; τ agrupado ≈ 1.89 %/año ± 0.1 | L | B3, B5 | B7a |
| B7a | Modelo de oferta | `modelos.py`, `tests/test_modelos.py` | paridad con statsmodels; tope `media` | M | B4, B5, B6 (mismo archivo) | — |
| B8 | Agregación a alcaldía | `modelos.py` | suma AGEB = alcaldía; 16 alcaldías | S | B6, B7a | B10 |
| B9 | Validación y backtest | `backtest.py`, `tests/test_backtest.py`, `docs/backtest.md` | 4 validaciones de demanda + backtest de oferta; reporte ≤ 5 líneas | L | B6, B7a | B10 |
| B10 | Brecha (features mínimas) | `features.py` | brecha por AGEB/alcaldía en `diagnostico.json` | S | B4, B3 | B8, B9 |
| B11 | Exportación + validación de contrato | `exportar.py`, `tests/test_exportar.py` | `make pipeline` genera ambos JSON válidos, deterministas | M | B8, B9, B10 | — |
| B12 | Makefile y docs | `Makefile`, `docs/metodologia.md`, `docs/data_manifest.md` (derivados) | `make pipeline && make test` limpio desde cero; metodología refleja constantes y decisión SCIAN | S | B11 | — |

\* B3 y B4 tocan `panel.py`: en serie. Paralelizables realmente (archivos disjuntos): {B1, B2}, {B5 con
B2–B4}, {B9, B10}. Commits: uno por tarea (`feat:`/`test:`/`docs:`).

## 10. Verificación
`make datos && make pipeline && make test && make validar`; `git status data/processed data/reference`
vacío; `docs/backtest.md` con modelo vs baseline; reejecutar `make pipeline` → mismo JSON.

## Preguntas abiertas
1. **B1 · Oferta sin ventaja sobre el baseline:** si el backtest 2019→2024 no supera a "S constante",
   ¿se publica la capa oferta como `se_mantiene`/baseline, se publica solo descriptiva (cambio
   observado 2019.87→2024.87, sin veredicto) o se omite?
2. **B2 · Campos extra:** ¿se sube el contrato a `1.2` para incluir `brecha`, sensibilidad (δ, λ) y
   probabilidades por unidad, o quedan en `diagnostico.json` fuera del contrato?
3. **B3 · AGEB con `division`:** ¿la hija hereda la **tasa** de la madre (metodología §5, literal) o
   se reparte el `D_2010` de la madre por `frac_de_2010`? (dan lo mismo en tasa; difieren en `ψ`).
4. **B4 · Milpa Alta (009):** las AGEB urbanas cubren 82.8 % de su población. ¿El veredicto de alcaldía
   se publica igual (etiquetado "solo urbano") o con confianza tope `media`?
5. **B5 · `tasa_anual_pct`:** ¿se reporta como tasa logarítmica ×100 (coherente con la banda de
   metodología) o como `100·(e^r − 1)` (más intuitiva)? Diferencia < 0.1 pp en el rango observado.
