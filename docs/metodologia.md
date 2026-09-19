# Metodología

Veredicto `sube | se_mantiene | baja | sin_datos` por AGEB y alcaldía, fecha base **2026-06**
(2026.5); horizontes de reporte **2029-06** (3 años), **2031-06** (5 años) y **2033-06** (7 años),
contrato `version 1.2` con capas `demanda` (principal) y `oferta`. Decisiones vigentes en
CLAUDE.md; hechos en `docs/perfil_datos.md` y `docs/problemas_datos.md`. Revisión 2026-09-19
(censo oficial completo, CONAPO municipal y marcos 2010/2020 ya disponibles; horizontes 3/5/7 años
y contrato v1.2 adoptados por el equipo, ver `plans/frontend_specs.md` §17-18).

## 1. Variables y fuentes

**Demanda (capa principal).** `D_it = P_0A2 + P_3A5 + P_6A11 + P_12A14` (0–14, suma simple), AGEB
urbana *i*, censo *t* ∈ {2010.44, 2020.20} (fechas de referencia 12-jun-2010 y 15-mar-2020;
Δt = 9.76). Fuente: INEGI RESAGEBURB 2010 y 2020 (`data/interim/censo_ageb_panel.parquet`).
Rango 0–14 porque todo DENUE infancias `Principal` atiende 0–14; 15–17 solo en `Complementario`.

**Control externo.** CONAPO, población a mitad de año por municipio y grupo quinquenal 1990–2040
(`conapo_mun_0a14.parquet`, 0–14 = 00_04 + 05_09 + 10_14).

**Oferta (capa complementaria).** DENUE infancias `Alcance = Principal`; un corte por periodo, el
primero tras cada levantamiento: 2016-10, 2019-11, 2024-11 (§6). `n_obs = 3`.

**Brecha (contexto, sin veredicto).** `S / D × 1000` con `D` 2020 y `S` 2024-11.

## 2. Método principal de demanda: tasa log-lineal + contracción EB + control CONAPO

1. **Tasa directa** por AGEB: `r̂_i = ln[(D_i,2020 + 0.5)/(D_i,2010 + 0.5)] / 9.76`, con varianza
   Poisson `ψ_i = [1/(D_i,2020 + 0.5) + 1/(D_i,2010 + 0.5)] / 9.76²`.
2. **Contracción (Fay-Herriot)** hacia la alcaldía: `r_i ~ N(ρ_m, τ²)`; `ρ_m` = tasa censal de la
   alcaldía (Σ AGEB), `τ²` por momentos; `r̃_i = B_i ρ_m + (1 − B_i) r̂_i`, `B_i = ψ_i/(ψ_i + τ²)`.
3. **Tasa futura**: la alcaldía toma la tasa CONAPO y la AGEB conserva parte de su desviación:
   `r_i,fut = ρ_m,CONAPO + λ (r̃_i − ρ_m)`, con `ρ_m,CONAPO = ln(C_m,2033.5 / C_m,2020.5)/13.0`
   (CONAPO publica población a mitad de año; el control se ancla al horizonte de reporte **más
   lejano**, `2033.5` = mediados de 2033 = fecha base + 7 años, ver §7).
4. **Proyección** `D̂_i(t) = D_i,2020 · exp(r_i,fut (t − 2020.20))`.
5. **Control por tasa, no por nivel:** reescalar por alcaldía para que
   `Σ_i D̂_i,2033.5 / Σ_i D_i,2020 = C_m,2033.5 / C_m,2020.20`. Se usa la **razón** de CONAPO, no
   su nivel, porque CONAPO incluye población rural y está conciliada (+5.9 % en 0–14 frente al
   censo urbano en 2020; problemas N1). `C_m,2020.20` se interpola log-linealmente entre las cifras
   2019 (2019.5) y 2020 (2020.5). El control se aplica **una sola vez**, contra el horizonte más
   lejano (`h7`, 2033.5): los horizontes `h3`/`h5` (2029-06, 2031-06) se leen sobre la **misma**
   trayectoria de tasa `r_i,fut` ya controlada, sin volver a controlar contra CONAPO en cada
   horizonte por separado. No es una pérdida de precisión: con dos censos no se identifica
   curvatura de la tendencia (§3), así que no hay información para justificar tres controles
   independientes; controlar una sola vez, al horizonte más lejano, es la opción más conservadora.
6. **Simulación** (semilla fija, 4,000 réplicas): `r_i ~ N(r̃_i, (1 − B_i)ψ_i)`, `λ ~ U(0.25, 1)`,
   choque de alcaldía compartido `N(0, σ_C²)` con `σ_C` = discrepancia censo-CONAPO 2010–20 de esa
   alcaldía (§4.3) → `IC95`, `P(sube)`, `P(baja)` e IC de alcaldía.

Salidas, una vez fijada `r_i,fut` (§2.3-2.5): `tasa_anual_pct` = `r_i,fut` proyectada × 100 — **es
la misma en los tres horizontes de reporte** (`h3`, `h5`, `h7`): depende solo de la tasa, no del
horizonte al que se mira. `delta_pct` = cambio acumulado desde la **fecha base** (2026.5, no desde
el censo 2020) hasta cada horizonte de reporte (2029-06, 2031-06 o 2033-06); por eso `delta_pct`
crece en magnitud de `h3` a `h7` aunque la tasa no cambie (`modelos.resumir()`). **El veredicto usa
la tasa `r_i,fut`**, así que tampoco cambia entre horizontes (§7). Baseline ingenuo: `r = 0` (igual
que el censo 2020).

## 3. (a) Qué se identifica con dos censos

| se identifica | no se identifica |
|---|---|
| Tasa media 2010–2020 por AGEB (`r̂_i`) y su ruido Poisson (`ψ_i`) | Curvatura o aceleración de la tendencia local |
| Dispersión real entre AGEB de una alcaldía (`τ`) | Si la desviación local de 2010–20 **persiste** (`λ`) |
| Tendencia futura por alcaldía (CONAPO, externo) | Choques posteriores a 2020 a escala AGEB |

Hechos (censo completo, 2,268 AGEB "misma unidad" con ≥ 20 niños en ambos censos): mediana de `r̂`
−1.97 %/año (p10 −3.78, p90 +0.31); DE 2.09 %/año; `τ` intra-alcaldía 1.89 %/año; error Poisson
mediano 0.58 %/año (AGEB mediana: 583 niños). La incertidumbre dominante es **estructural** (`λ`);
IC solo Poisson serían ~3.5 veces más estrechos que la dispersión real. `λ` no es estimable con dos
puntos: previa `U(0.25, 1)` y veredicto reportado con `λ` = 0.25, 0.6 y 1; si cambia entre extremos,
la confianza baja un nivel.

## 4. (b) Validación que sustituye al backtest temporal de demanda

Con dos censos no hay tercer punto que predecir (todo origen móvil tendría fuga): excepción
explícita a la regla de backtest, que sí se aplica a la oferta (§6). Sustitutos (semilla fija):
1. **Adelgazamiento binomial:** submuestrear conteos al 25 % y 50 %, estimar `r̃` y medir el error
   contra `r̂` completo; debe superar a `r̂` directo y a `ρ_m` (MAE y cobertura del IC95).
2. **Validación cruzada dejando una alcaldía fuera** para `τ²` y el IC (cobertura 0.90–0.97).
3. **Censo vs CONAPO 2010–2020 por alcaldía:** la reconstrucción CONAPO 1990–2019 permite comparar
   tendencias. Diferencias: ≤ 0.6 pp/año en 13 alcaldías; 014 −0.28 vs −2.14, 015 −1.72 vs −2.50,
   016 −0.33 vs −1.10 (alcaldías centrales: el censo urbano cae menos que CONAPO).
   Esa discrepancia alimenta `σ_C` (§2.6) y se reporta en el panel.
4. **Backtest de alcaldía con CONAPO:** origen móvil sobre la serie municipal 1990–2020 (orígenes
   2000, 2005, 2010, 2015; horizontes 5 y 7 años) para calibrar la banda sin tocar el test final.
Adopción: 1 y 2 superan al baseline `r = 0` en MAE de la tasa y F1 macro de 3 clases.

## 5. (c) Geografía AGEB 2010 → 2020 (datos completos)

- Claves: 2,430 en ambos censos, 3 solo en 2020, 2 solo en 2010 (`censo_ageb_panel.parquet`).
- Traslape de áreas MG 2010 v5.0 vs MG 2020 (`equivalencia_ageb_2010_2020.parquet`), por AGEB
  urbana 2020: **misma** 2,331 (≥ 95 % de área compartida en ambos sentidos); **fusión/expansión** 62
  (la 2020 cubre ≥ 95 % de la 2010 pero es mayor: bordes urbanos que crecieron); **cambio de
  límites** 37; **división** 1. Las 100 no-"misma" suman 60,820 niños (3.7 % del total 2020).
- Tratamiento: "misma" → tasa directa; división → tasa de la madre 2010 aplicada a la hija;
  fusión/expansión y cambio de límites → tasa directa con la misma clave, pero confianza máxima
  **media** (el denominador 2010 cubre otra superficie); sin contraparte → `r̃_i = ρ_m`,
  `n_obs = 1`, confianza **baja**.

## 6. Oferta

Tasa Poisson log-lineal sobre las fechas de levantamiento (2016.79, 2019.87, 2024.87) + EB hacia la
alcaldía, sin control externo. La caída 2023→2024 son **cierres reales acumulados 2020–2023
registrados de golpe**: al usar fechas de levantamiento se reparte en 5 años. Tope de confianza
**media** en toda la capa. Backtest de origen móvil: origen 2019-11 (ajuste 2016-10/2019-11) →
predecir 2024-11; baseline `S` constante. `sin_datos` si `S = 0` en los tres cortes.

**Horizonte de reporte de la oferta: solo 3 años (`h3`, 2029-06).** A diferencia de la demanda, la
oferta no se controla contra ninguna serie externa y su único ancla temporal es el propio
levantamiento DENUE (§1); no hay calibración ni justificación para reportar `delta_pct`/`ic95` más
allá de 3 años desde la fecha base — `h5`/`h7` simplemente no se calculan ni se publican para esta
capa (`config.HORIZONTES_OFERTA = ("h3",)`, contrato v1.2 §17: `horizontes_disponibles: ["h3"]`).

## 7. (d) Regla de decisión y sensibilidad de la banda

Regla única (`modelos.py`) sobre la distribución simulada de la tasa proyectada:
- `sube` si `P(tasa > +δ) ≥ 0.80`; `baja` si `P(tasa < −δ) ≥ 0.80`; `se_mantiene` si
  `P(|tasa| ≤ δ) ≥ 0.50`; si no, `se_mantiene` con confianza **baja**.
- Confianza: **alta** si la probabilidad decisiva ≥ 0.95 y el veredicto no cambia con `λ`;
  **media** si ≥ 0.80; **baja** en el resto, y siempre con `n_obs = 1` o `D_2020 < 100` (141 AGEB).

**`tasa_anual_pct` y `delta_pct` (contrato v1.2, `modelos.resumir()`).** `tasa_anual_pct` es la
tasa `r_i,fut` proyectada × 100: depende solo de la simulación de la tasa, no del horizonte de
reporte, así que **es idéntica en `h3`, `h5` y `h7`** — al igual que el veredicto y la confianza,
que se calculan sobre esa misma tasa (`P(tasa > +δ)`, etc., §7). Lo único que varía entre
horizontes es `delta_pct`/`ic95`: se miden desde la **fecha base** (`T_BASE = 2026.5`, no desde el
censo 2020) hasta cada horizonte (`100·(e^(r·(t_horizonte − 2026.5)) − 1)`), por lo que su
magnitud crece de `h3` a `h7` aunque la tasa no cambie. Esto es deliberado: separa "¿hacia dónde
va la tendencia?" (una sola respuesta, la tasa) de "¿cuánto se acumula a 3, 5 o 7 años?" (tres
respuestas, el `delta_pct`).

Sensibilidad con tasas **históricas** directas 2010–2020 (2,268 AGEB), % por clase:

| δ (%/año) | baja | se_mantiene | sube |
|---|---|---|---|
| 0.5 | 82.0 | 9.1 | 8.9 |
| **1.0** | **73.9** | **19.1** | **6.9** |
| 2.0 | 49.3 | 46.3 | 4.4 |

Con CONAPO las tasas 2020–2027 de alcaldía son más negativas (−1.45 a −4.19 %/año, problemas N2):
el reparto proyectado tendrá aún más `baja`. **Umbral final: δ = 1 %/año y probabilidad ≥ 0.80**
(≈ 0.5 τ; ±7 % acumulado a 2027.5, ~40 niños en la AGEB mediana, 1–2 grupos escolares). Se
publican las tres bandas en el panel de metodología.

## 8. Datos insuficientes y agregación

- `sin_datos` (demanda): AGEB rural (22 en `09ar`, CVEGEO de 9 caracteres); 0–14 suprimido por
  INEGI (41 AGEB en 2020); `D_2020 < 20` (23); AGEB urbana 2020 sin polígono (2) o sin censo. Nunca se imputa.
- Alcaldía: `D_m = Σ_{i∈m} D_i` sobre AGEB urbanas con dato; `Δ%` desde sumas, no promedios; IC de
  la simulación conjunta; cobertura vs CONAPO reportada. Tests: suma AGEB = alcaldía, sin `CVEGEO`
  duplicados, veredictos en el conjunto válido.

## 9. Métodos descartados (una línea)

Theil-Sen/Mann-Kendall: 2–3 puntos efectivos. · Poisson/BN independiente: sin contracción e IC
~3.5× estrechos. · GLMM con pendiente aleatoria: equivalente al EB e inestable con 2 tiempos. ·
Hamilton-Perry: requiere quinquenios por AGEB. · Covariables espaciales estáticas como modelo
principal: no identifican cambio; solo como media previa del EB si mejoran §4.
