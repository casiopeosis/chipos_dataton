"""Validación retrospectiva y calibración del piso de incertidumbre.

Tarea B9 (nunca entregada hasta ahora) de `plans/backend_plan.md` §6, que
`correccion/rubrica.md` §5-6 exige explícitamente; fórmulas y criterios en
`docs/metodologia.md` §4 (validación) y §2.7/§6.2 (calibración del piso de
incertidumbre). Fase 2/3 de `correccion/action_plan.md`.

Contenido:
- `adelgazar`, `validar_adelgazamiento`: submuestreo binomial **del propio
  Censo 2020** (nunca del futuro) para poner a prueba si la contracción EB
  (`r_tilde`) mejora sobre la tasa directa (`r_hat`) y sobre la tasa de la
  alcaldía (`rho_m`) cuando el dato es más ruidoso.
- `validar_loao`: validación cruzada **espacial** (deja una alcaldía fuera
  al reestimar `tau2`, nunca usa datos futuros de esa alcaldía).
- `backtest_oferta`: el único backtest **temporal** genuino disponible hoy
  (origen 2016-10 + 2019-11, sin ver 2024-11, contra baseline "S constante").
- `comparar_censo_conapo`: comparación de fuentes en el mismo punto del
  tiempo (2010-2020), **no es un backtest** (metodología §4.1 punto 2):
  alimenta `sigma_C`, que `modelos.simular_demanda` ya calcula por su
  cuenta; aquí solo se expone para el reporte.
- `calibrar_piso_incertidumbre`: elige `SIGMA_MIN_DEMANDA`/`SIGMA_MIN_OFERTA`
  con la cobertura empírica de lo anterior, nunca con un ancho de intervalo
  arbitrario (metodología §2.7, corrige el criterio equivocado de la
  versión anterior del plan).
- `metricas`, `ejecutar`, `escribir_reporte`: utilidades de agregación y de
  escritura de `data/outputs/backtest.json` / `docs/backtest.md`.

**Se retira, deliberadamente, cualquier función de "backtest de CONAPO" con
orígenes móviles sobre `data/processed/conapo/pobproy_quinq1.csv`.** Ese
archivo es una sola vintage, reconciliada en bloque contra el Censo 2020
(`tools/build_conapo.py`): tratar sus años 2000/2005/2010/2015 como si
fueran observaciones independientes sería validar una proyección con otra
proyección construida con información futura (metodología §4.1). No existe
ninguna función `backtest_conapo` en este módulo; `test_backtest.py` incluye
un guardarraíl que falla si alguna vez reaparece.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from chipos.config import (
    DELTA,
    RUTA_BACKTEST_JSON,
    RUTA_BACKTEST_MD,
    SEMILLA,
    T_2010,
    T_2020,
)
from chipos.io import CORTES_OFERTA
from chipos.modelos import contraccion_eb, tasa_conapo, tasa_directa

# Percentil 97.5 de la normal estándar (IC95 simétrico, misma convención que
# `modelos.resumir` -- ahí se usa a través de la simulación Monte Carlo; aquí
# los folds del backtest son puntuales, así que el IC95 se aproxima con la
# normal, ya que no hay 4000 réplicas por fold).
_Z_975 = 1.959963984540054

# Rejilla de candidatos de `SIGMA_MIN_TASA` (metodología §2.7 punto 1).
CANDIDATOS_PISO: tuple[float, ...] = (0.000, 0.005, 0.010, 0.015, 0.020)

# Banda de cobertura aceptable, la misma que ya usa LOAO (metodología §2.7 punto 3).
_COBERTURA_MINIMA = 0.90
_COBERTURA_MAXIMA = 0.97

_CLASES_VEREDICTO: tuple[str, ...] = ("sube", "se_mantiene", "baja")


# ---------------------------------------------------------------------------
# Utilidades compartidas
# ---------------------------------------------------------------------------


def _clasificar(r: np.ndarray, delta: float = DELTA) -> np.ndarray:
    """Clasificación determinista de una tasa puntual en 3 clases (banda muerta `delta`).

    No es la regla de veredicto de producción (`modelos.veredicto`, que usa
    probabilidades de una simulación Monte Carlo con `P_DECISION=0.80`): aquí
    solo hay un punto por fold, no una distribución. Se clasifica igual que
    se centra la banda muerta de producción (metodología §7), para que el F1
    macro compare "de qué lado de la banda cae" con el mismo criterio.
    """
    r = np.asarray(r, dtype=float)
    clases = np.full(r.shape, "se_mantiene", dtype=object)
    clases[r > delta] = "sube"
    clases[r < -delta] = "baja"
    return clases


def metricas(
    y_real: np.ndarray,
    y_pred: np.ndarray,
    clases_real: np.ndarray,
    clases_pred: np.ndarray,
    ic: np.ndarray | None = None,
) -> dict:
    """MAE, F1 macro (3 clases) y, si se da `ic`, cobertura empírica del IC95.

    `y_real`/`y_pred` en las unidades que decida quien llama (`backtest.py`
    siempre pasa puntos porcentuales por año, "pp/año", para que los
    resultados sean directamente comparables con `tasa_anual_pct` del
    contrato). `ic`: `(n, 2)` con `[lo, hi]` en las mismas unidades que
    `y_real`; si se omite, la clave `cobertura_ic95` no aparece en el
    resultado (algunos competidores del backtest -- `rho_m`, el baseline
    `r=0` -- no tienen una varianza individual por AGEB, metodología §4.3).
    """
    y_real = np.asarray(y_real, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mae = float(np.mean(np.abs(y_pred - y_real)))
    f1 = float(
        f1_score(
            clases_real,
            clases_pred,
            labels=list(_CLASES_VEREDICTO),
            average="macro",
            zero_division=0,
        )
    )
    resultado: dict = {"mae_pp_anio": mae, "f1_macro": f1, "n": int(len(y_real))}
    if ic is not None:
        ic = np.asarray(ic, dtype=float)
        cobertura = float(np.mean((y_real >= ic[:, 0]) & (y_real <= ic[:, 1])))
        resultado["cobertura_ic95"] = cobertura
    return resultado


def _deviance_poisson(y: np.ndarray, mu: np.ndarray) -> float:
    """Deviance Poisson media (`2*(y*ln(y/mu) - (y-mu))`, límite `y=0` -> `2*mu`)."""
    y = np.asarray(y, dtype=float)
    mu = np.clip(np.asarray(mu, dtype=float), 1e-6, None)
    termino = np.zeros_like(y)
    con_y = y > 0
    termino[con_y] = y[con_y] * np.log(y[con_y] / mu[con_y])
    return float(np.mean(2.0 * (termino - (y - mu))))


# ---------------------------------------------------------------------------
# Adelgazamiento binomial del Censo 2020 (metodología §4.3 punto 2)
# ---------------------------------------------------------------------------


def adelgazar(panel_d: pd.DataFrame, frac: float, rng: np.random.Generator) -> pd.DataFrame:
    """Submuestrea `d_2020` como `Binomial(d_2020, frac)`, reescalado por `1/frac`.

    Solo tiene sentido sobre AGEB con `d_2020` numérico; el resto (rurales,
    suprimidas) se copian tal cual. El redondeo de `d_2020` a entero antes de
    la binomial es necesario porque el censo es un conteo; en teoría siempre
    llega entero, pero se protege contra el caso sintético.

    **El reescalado por `1/frac` es obligatorio, no cosmético.** Sin él,
    adelgazar introduce un sesgo mecánico de `ln(frac)/dt` en la tasa (a
    `frac=0.25`, `dt=9.76`: unos -14 pp/año, mucho mayor que cualquier
    tendencia real) que no tiene nada que ver con la robustez del estimador
    -- es aritmética pura de "el conteo bajó porque lo submuestreé".
    `Binomial(d, frac)/frac` es insesgado para `d` (misma media, más
    varianza): simula "menos información disponible" sin fingir una caída
    poblacional que nunca ocurrió. `validar_adelgazamiento` corrige además
    la varianza de `psi` por el mismo factor `1/frac` (ver su docstring).
    """
    df = panel_d.copy()
    con_dato = df["d_2020"].notna()
    conteos = df.loc[con_dato, "d_2020"].round().astype(int).to_numpy()
    conteos = np.clip(conteos, 0, None)
    df.loc[con_dato, "d_2020"] = rng.binomial(conteos, frac).astype(float) / frac
    return df


def validar_adelgazamiento(
    panel_d: pd.DataFrame,
    rng: np.random.Generator,
    fracs: tuple[float, ...] = (0.25, 0.5),
) -> pd.DataFrame:
    """Folds de adelgazamiento binomial (metodología §4.3 punto 2).

    Para cada `frac`, adelgaza `d_2020` y reestima, sobre los datos
    adelgazados, 4 competidores por AGEB: `r_hat_directo` (tasa directa
    adelgazada), `r_tilde_eb` (contracción EB sobre los datos adelgazados),
    `rho_m` (tasa de la alcaldía, adelgazada, asignada a cada AGEB) y
    `baseline_r0` (tasa cero, "igual que el último corte"). La verdad de
    referencia (`r_real`) es la tasa directa calculada sobre el Censo 2020
    **completo** (nunca adelgazado): es el mismo censo, no el futuro, así
    que no hay fuga -- adelgazar y comparar contra el propio dato completo
    es exactamente "poner a prueba el método con menos información
    disponible", no "predecir años que aún no pasaron".

    Solo entran las AGEB con `motivo_sin_datos` nulo y `d_2010` no nulo (las
    mismas que `modelos.simular_demanda` usa para `r_hat`): sin un segundo
    punto no hay tasa directa "completa" con la que comparar.

    Devuelve un DataFrame a granularidad de fold (una fila por
    `frac` x `cvegeo` x `estimador`), con columnas `frac, cvegeo, cve_mun,
    estimador, r_real, r_estimado, var_estimador` (`var_estimador` es `NaN`
    para `rho_m`/`baseline_r0`, que no tienen una varianza individual por
    AGEB). `r_real`/`r_estimado`/`var_estimador` en unidades de tasa (no
    pp/año): quien agrega a pp/año es `metricas()`/`ejecutar()`.

    **Corrección de varianza por el reescalado de `adelgazar()`.** Si
    `Y ~ Binomial(d, frac)` y `d' = Y/frac` (insesgado para `d`), entonces
    `Var(d') = Var(Y)/frac² ≈ frac·d/frac² = d/frac` (aproximación Poisson de
    la binomial), `1/frac` veces la varianza que tendría un conteo `d`
    genuino. Por el método delta (el mismo que justifica `psi = 1/d` en
    `modelos.tasa_directa`), la contribución de `d_2020` a `psi` es entonces
    `1/(frac·(d'+0.5))`, no `1/(d'+0.5)` -- de ahí la corrección explícita
    más abajo; la contribución de `d_2010` (nunca adelgazado) no cambia.
    """
    dt = T_2020 - T_2010
    elegibles = (
        panel_d.loc[panel_d["motivo_sin_datos"].isna() & panel_d["d_2010"].notna()]
        .reset_index(drop=True)
    )
    if elegibles.empty:
        return pd.DataFrame(
            columns=["frac", "cvegeo", "cve_mun", "estimador", "r_real", "r_estimado", "var_estimador"]
        )

    r_real, _psi_real = tasa_directa(
        elegibles["d_2010"].to_numpy(dtype=float), elegibles["d_2020"].to_numpy(dtype=float), dt
    )

    filas: list[dict] = []
    for frac in fracs:
        thin = adelgazar(elegibles, frac, rng)

        d_2010 = thin["d_2010"].to_numpy(dtype=float)
        d_2020 = thin["d_2020"].to_numpy(dtype=float)
        r_hat_thin = np.log((d_2020 + 0.5) / (d_2010 + 0.5)) / dt
        psi_thin = (1.0 / (frac * (d_2020 + 0.5)) + 1.0 / (d_2010 + 0.5)) / dt**2

        agregado = thin.groupby("cve_mun")[["d_2010", "d_2020"]].sum()
        rho_m_thin = np.log((agregado["d_2020"] + 0.5) / (agregado["d_2010"] + 0.5)) / dt
        rho_m_por_unidad = thin["cve_mun"].map(rho_m_thin).to_numpy(dtype=float)

        r_tilde_thin, var_post_thin, _tau2_thin = contraccion_eb(r_hat_thin, psi_thin, rho_m_por_unidad)

        competidores = {
            "r_hat_directo": (r_hat_thin, psi_thin),
            "r_tilde_eb": (r_tilde_thin, var_post_thin),
            "rho_m": (rho_m_por_unidad, None),
            "baseline_r0": (np.zeros_like(r_hat_thin), None),
        }
        for nombre, (valor, varianza) in competidores.items():
            for i in range(len(thin)):
                filas.append(
                    {
                        "frac": frac,
                        "cvegeo": thin["cvegeo"].iat[i],
                        "cve_mun": thin["cve_mun"].iat[i],
                        "estimador": nombre,
                        "r_real": float(r_real[i]),
                        "r_estimado": float(valor[i]),
                        "var_estimador": float(varianza[i]) if varianza is not None else np.nan,
                    }
                )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Validación cruzada espacial: deja una alcaldía fuera (metodología §4.3 punto 3)
# ---------------------------------------------------------------------------


def validar_loao(panel_d: pd.DataFrame) -> pd.DataFrame:
    """Deja cada alcaldía fuera al reestimar `tau2`; nunca usa datos futuros.

    Para cada alcaldía `m`, `tau2` se reestima con `contraccion_eb` sobre las
    AGEB de **las otras** alcaldías (partición espacial: no hay ninguna
    dependencia temporal que se pueda "filtrar" desde `m` hacia el resto).
    Con ese `tau2` "externo" se recalcula `r_tilde`/`var_post` para las AGEB
    de `m` (usando la `rho_m` de la propia `m`, que solo depende de sus
    propias AGEB) y se mide si el IC95 resultante cubre `r_hat` -- la tasa
    directa observada de esa AGEB, que es el mejor proxy disponible de "la
    tasa real" sin una fuente independiente (misma lógica que valida
    cualquier estimador de contracción en estimación de área pequeña:
    ¿el intervalo del estimador contraído cubre el estimador directo?).

    Alcaldías con menos de 2 AGEB elegibles en el resto de la ciudad (no
    ocurre con los datos reales, defensivo) se omiten: no hay suficiente
    información externa para estimar `tau2`.

    Devuelve una fila por AGEB con columnas `cve_mun, cvegeo, r_real,
    r_estimado, var_estimador, tau2_externo` (unidades de tasa, no pp/año).
    """
    dt = T_2020 - T_2010
    elegibles = (
        panel_d.loc[panel_d["motivo_sin_datos"].isna() & panel_d["d_2010"].notna()]
        .reset_index(drop=True)
    )
    if elegibles.empty:
        return pd.DataFrame(
            columns=["cve_mun", "cvegeo", "r_real", "r_estimado", "var_estimador", "tau2_externo"]
        )

    r_hat, psi = tasa_directa(
        elegibles["d_2010"].to_numpy(dtype=float), elegibles["d_2020"].to_numpy(dtype=float), dt
    )
    cve_mun = elegibles["cve_mun"].to_numpy()

    agregado = elegibles.groupby("cve_mun")[["d_2010", "d_2020"]].sum()
    rho_m_serie = np.log((agregado["d_2020"] + 0.5) / (agregado["d_2010"] + 0.5)) / dt
    rho_m_por_unidad = elegibles["cve_mun"].map(rho_m_serie).to_numpy(dtype=float)

    filas: list[dict] = []
    for m in sorted(set(cve_mun.tolist())):
        idx_fuera = cve_mun != m
        idx_dentro = cve_mun == m
        if idx_fuera.sum() < 2 or not idx_dentro.any():
            continue
        tau2_externo = max(
            0.0,
            float(
                np.mean((r_hat[idx_fuera] - rho_m_por_unidad[idx_fuera]) ** 2) - np.mean(psi[idx_fuera])
            ),
        )
        b = psi[idx_dentro] / (psi[idx_dentro] + tau2_externo)
        r_tilde_m = b * rho_m_por_unidad[idx_dentro] + (1.0 - b) * r_hat[idx_dentro]
        var_post_m = (1.0 - b) * psi[idx_dentro]

        cvegeos_m = elegibles.loc[idx_dentro, "cvegeo"].to_numpy()
        for i in range(len(cvegeos_m)):
            filas.append(
                {
                    "cve_mun": m,
                    "cvegeo": cvegeos_m[i],
                    "r_real": float(r_hat[idx_dentro][i]),
                    "r_estimado": float(r_tilde_m[i]),
                    "var_estimador": float(var_post_m[i]),
                    "tau2_externo": tau2_externo,
                }
            )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Backtest temporal genuino de oferta (metodología §4.2 punto 1)
# ---------------------------------------------------------------------------


def backtest_oferta(panel_o: pd.DataFrame) -> pd.DataFrame:
    """Ajuste con 2016-10 + 2019-11 (sin ver 2024-11) -> predice 2024-11.

    Corrección de continuidad `+0.5`, la misma convención que `tasa_directa`
    (metodología §2.1): necesaria porque `S=0` es frecuente en conteos de
    establecimientos y el ajuste log-lineal con exactamente 2 puntos es la
    solución cerrada del Poisson saturado (`b_hat = ln[(s2+0.5)/(s1+0.5)] /
    (t2-t1)`; con 2 parámetros y 2 observaciones el ajuste Poisson MLE
    reproduce los conteos observados exactamente, así que no hace falta
    Newton-Raphson iterativo aquí -- a diferencia de `modelos.ajustar_oferta`,
    que sí lo necesita porque tiene 3 puntos y 2 parámetros).

    Baseline "S constante" (CLAUDE.md, metodología §4.2): predicción = `S`
    del último corte visto (2019-11), tasa cero.

    Devuelve dos filas por AGEB (`estimador` = `modelo_poisson_2016_2019` o
    `baseline_s_constante`), con `cvegeo, cve_mun, estimador, s_2016, s_2019,
    s_2024_real, s_2024_pred, tasa_estimada, var_estimador, tasa_realizada,
    deviance_poisson` (`tasa_estimada`/`var_estimador` son `NaN` para el
    baseline: su tasa es 0 por construcción, sin varianza).
    """
    t_2016, t_2019, t_2024 = sorted(CORTES_OFERTA.values())
    dt_origen = t_2019 - t_2016
    dt_prediccion = t_2024 - t_2016

    tabla = panel_o.pivot(index="cvegeo", columns="t", values="s")[[t_2016, t_2019, t_2024]]
    cve_mun = panel_o.drop_duplicates("cvegeo").set_index("cvegeo")["cve_mun"].reindex(tabla.index)

    s1 = tabla[t_2016].to_numpy(dtype=float)
    s2 = tabla[t_2019].to_numpy(dtype=float)
    s_real = tabla[t_2024].to_numpy(dtype=float)

    b_hat = np.log((s2 + 0.5) / (s1 + 0.5)) / dt_origen
    var_b = (1.0 / (s2 + 0.5) + 1.0 / (s1 + 0.5)) / dt_origen**2

    pred_modelo = (s1 + 0.5) * np.exp(b_hat * dt_prediccion) - 0.5
    pred_modelo = np.clip(pred_modelo, 0.0, None)
    pred_baseline = s2  # "igual que el último corte visto", tasa 0

    tasa_realizada = np.log((s_real + 0.5) / (s1 + 0.5)) / dt_prediccion

    dev_modelo = _deviance_poisson(s_real, pred_modelo)
    dev_baseline = _deviance_poisson(s_real, pred_baseline)

    n = len(tabla)
    filas = {
        "cvegeo": list(tabla.index) * 2,
        "cve_mun": list(cve_mun.to_numpy()) * 2,
        "estimador": ["modelo_poisson_2016_2019"] * n + ["baseline_s_constante"] * n,
        "s_2016": list(s1) * 2,
        "s_2019": list(s2) * 2,
        "s_2024_real": list(s_real) * 2,
        "s_2024_pred": list(pred_modelo) + list(pred_baseline),
        "tasa_estimada": list(b_hat) + [np.nan] * n,
        "var_estimador": list(var_b) + [np.nan] * n,
        "tasa_realizada": list(tasa_realizada) * 2,
        "deviance_poisson": [dev_modelo] * n + [dev_baseline] * n,
    }
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Comparación de fuentes (NO es un backtest; metodología §4.1 punto 2 / §4.3 punto 4)
# ---------------------------------------------------------------------------


def comparar_censo_conapo(panel_d: pd.DataFrame, conapo: pd.DataFrame) -> pd.DataFrame:
    """Discrepancia censo-CONAPO por alcaldía, 2010-2020 (comparación de fuentes).

    **No predice el futuro; no es un backtest.** Compara, en el mismo punto
    del tiempo, la tasa censal observada (`rho_m` sobre `panel_d`) contra la
    tasa que implica la serie CONAPO entre las mismas dos fechas
    (`modelos.tasa_conapo`). Reutiliza exactamente la misma discrepancia que
    `modelos.simular_demanda` ya calcula internamente como `sigma_C`
    (metodología §2.6): esta función solo la expone para el reporte de
    `docs/backtest.md`, etiquetada explícitamente como lo que es.

    Devuelve una fila por alcaldía: `cve_mun, tasa_censo_pct_anio,
    tasa_conapo_pct_anio, diferencia_pp_anio` (pp/año = `tasa_censo -
    tasa_conapo`, en puntos porcentuales).
    """
    dt = T_2020 - T_2010
    elegibles = panel_d.loc[panel_d["motivo_sin_datos"].isna() & panel_d["d_2010"].notna()]
    agregado = elegibles.groupby("cve_mun")[["d_2010", "d_2020"]].sum()
    tasa_censo = np.log((agregado["d_2020"] + 0.5) / (agregado["d_2010"] + 0.5)) / dt

    tasa_conapo_serie = tasa_conapo(conapo, T_2010, T_2020)

    filas = []
    for m in sorted(tasa_censo.index):
        if m not in tasa_conapo_serie.index:
            continue
        t_censo = float(tasa_censo.loc[m])
        t_conapo = float(tasa_conapo_serie.loc[m])
        filas.append(
            {
                "cve_mun": m,
                "tasa_censo_pct_anio": round(t_censo * 100, 2),
                "tasa_conapo_pct_anio": round(t_conapo * 100, 2),
                "diferencia_pp_anio": round((t_censo - t_conapo) * 100, 2),
            }
        )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Calibración del piso de incertidumbre (metodología §2.7 / §6.1)
# ---------------------------------------------------------------------------


def _elegir_piso(folds: pd.DataFrame, candidatos: tuple[float, ...]) -> dict:
    """Rejilla de `sigma_min` sobre un conjunto de folds `{r_real, r_estimado, var_estimador}`.

    Elige el candidato **más pequeño** cuya cobertura empírica del IC95 cae
    en `[0.90, 0.97]`. Si `0.000` ya sobrecubre (> 0.97), no se añade piso:
    el error de conteo ya basta. Si ninguno alcanza `0.90`, se reporta el de
    mayor cobertura lograda, marcado como "rejilla insuficiente" -- nunca se
    inventa un candidato fuera de la rejilla ni se redondea la cobertura.
    """
    r_real = folds["r_real"].to_numpy(dtype=float)
    r_estimado = folds["r_estimado"].to_numpy(dtype=float)
    var_base = folds["var_estimador"].to_numpy(dtype=float)

    rejilla = []
    for sigma in candidatos:
        var_con_piso = np.maximum(var_base, sigma**2)
        margen = _Z_975 * np.sqrt(var_con_piso)
        cobertura = float(np.mean((r_real >= r_estimado - margen) & (r_real <= r_estimado + margen)))
        rejilla.append({"sigma_min_tasa": sigma, "cobertura": cobertura})

    elegido = next(
        (r for r in rejilla if _COBERTURA_MINIMA <= r["cobertura"] <= _COBERTURA_MAXIMA), None
    )
    rejilla_insuficiente = elegido is None
    if elegido is None:
        elegido = rejilla[0] if rejilla[0]["cobertura"] > _COBERTURA_MAXIMA else max(
            rejilla, key=lambda r: r["cobertura"]
        )

    return {
        "elegido": elegido["sigma_min_tasa"],
        "cobertura_lograda": elegido["cobertura"],
        "rejilla_insuficiente": rejilla_insuficiente,
        "rejilla": rejilla,
    }


def calibrar_piso_incertidumbre(
    resultados_adelgazamiento: pd.DataFrame,
    resultados_loao: pd.DataFrame,
    resultados_oferta: pd.DataFrame,
    candidatos: tuple[float, ...] = CANDIDATOS_PISO,
) -> dict:
    """`SIGMA_MIN_DEMANDA`/`SIGMA_MIN_OFERTA`, calibrados con cobertura empírica.

    Demanda: folds de `r_tilde_eb` del adelgazamiento + los folds de LOAO
    (ambos comparten unidades de tasa y ya traen `var_estimador`). Oferta:
    folds del modelo Poisson 2016->2019 del backtest de oferta. Nunca se
    calibra con un ancho de intervalo objetivo (metodología §2.7): el
    criterio es exclusivamente la cobertura del `[0.90, 0.97]`.
    """
    folds_demanda = pd.concat(
        [
            resultados_adelgazamiento.loc[
                resultados_adelgazamiento["estimador"] == "r_tilde_eb",
                ["r_real", "r_estimado", "var_estimador"],
            ],
            resultados_loao[["r_real", "r_estimado", "var_estimador"]],
        ],
        ignore_index=True,
    )
    folds_oferta = resultados_oferta.loc[
        resultados_oferta["estimador"] == "modelo_poisson_2016_2019",
        ["tasa_realizada", "tasa_estimada", "var_estimador"],
    ].rename(columns={"tasa_realizada": "r_real", "tasa_estimada": "r_estimado"})

    return {
        "candidatos": list(candidatos),
        "demanda": _elegir_piso(folds_demanda, candidatos),
        "oferta": _elegir_piso(folds_oferta, candidatos),
    }


# ---------------------------------------------------------------------------
# Orquestación y reporte
# ---------------------------------------------------------------------------


def _resumen_adelgazamiento(folds: pd.DataFrame) -> list[dict]:
    resumen = []
    for (frac, estimador), grupo in folds.groupby(["frac", "estimador"], sort=True):
        clases_real = _clasificar(grupo["r_real"].to_numpy(dtype=float))
        clases_pred = _clasificar(grupo["r_estimado"].to_numpy(dtype=float))
        ic = None
        if grupo["var_estimador"].notna().all():
            margen = _Z_975 * np.sqrt(grupo["var_estimador"].to_numpy(dtype=float)) * 100
            centro = grupo["r_estimado"].to_numpy(dtype=float) * 100
            ic = np.column_stack([centro - margen, centro + margen])
        m = metricas(
            grupo["r_real"].to_numpy(dtype=float) * 100,
            grupo["r_estimado"].to_numpy(dtype=float) * 100,
            clases_real,
            clases_pred,
            ic,
        )
        resumen.append({"frac": frac, "estimador": estimador, **m})
    return resumen


def _resumen_loao(folds: pd.DataFrame) -> dict:
    if folds.empty:
        return {"mae_pp_anio": None, "f1_macro": None, "cobertura_ic95": None, "n": 0}
    clases_real = _clasificar(folds["r_real"].to_numpy(dtype=float))
    clases_pred = _clasificar(folds["r_estimado"].to_numpy(dtype=float))
    margen = _Z_975 * np.sqrt(folds["var_estimador"].to_numpy(dtype=float)) * 100
    centro = folds["r_estimado"].to_numpy(dtype=float) * 100
    ic = np.column_stack([centro - margen, centro + margen])
    return metricas(
        folds["r_real"].to_numpy(dtype=float) * 100,
        folds["r_estimado"].to_numpy(dtype=float) * 100,
        clases_real,
        clases_pred,
        ic,
    )


def _resumen_oferta(folds: pd.DataFrame) -> list[dict]:
    resumen = []
    for estimador, grupo in folds.groupby("estimador", sort=True):
        clases_real = _clasificar(grupo["tasa_realizada"].to_numpy(dtype=float))
        if grupo["tasa_estimada"].notna().all():
            clases_pred = _clasificar(grupo["tasa_estimada"].to_numpy(dtype=float))
            margen = _Z_975 * np.sqrt(grupo["var_estimador"].to_numpy(dtype=float)) * 100
            centro = grupo["tasa_estimada"].to_numpy(dtype=float) * 100
            ic = np.column_stack([centro - margen, centro + margen])
            tasa_pred = grupo["tasa_estimada"].to_numpy(dtype=float) * 100
        else:
            clases_pred = _clasificar(np.zeros(len(grupo)))
            ic = None
            tasa_pred = np.zeros(len(grupo))
        m = metricas(
            grupo["tasa_realizada"].to_numpy(dtype=float) * 100,
            tasa_pred,
            clases_real,
            clases_pred,
            ic,
        )
        resumen.append(
            {
                "estimador": estimador,
                "deviance_poisson_media": float(grupo["deviance_poisson"].iloc[0]),
                **m,
            }
        )
    return resumen


def _criterio_adopcion(resumen_adelg: list[dict], resumen_loao: dict, resumen_oferta: list[dict]) -> dict:
    """Criterio de adopción sin escapatoria (metodología §4.3, CLAUDE.md).

    Demanda: `r_tilde_eb` debe superar a `baseline_r0` en MAE y F1 macro
    (adelgazamiento, ambas fracciones) y LOAO debe caer en `[0.90, 0.97]`.
    Oferta: el modelo debe superar al baseline "S constante" en MAE y F1
    macro. Si algo no se cumple, se reporta tal cual (`False`), nunca se
    esconde ni se maquilla.
    """
    por_frac = {(r["frac"], r["estimador"]): r for r in resumen_adelg}
    demanda_ok = True
    detalle_demanda = []
    for frac in sorted({k[0] for k in por_frac}):
        eb = por_frac.get((frac, "r_tilde_eb"))
        base = por_frac.get((frac, "baseline_r0"))
        if eb is None or base is None:
            continue
        mae_mejor = eb["mae_pp_anio"] <= base["mae_pp_anio"]
        f1_mejor = eb["f1_macro"] >= base["f1_macro"]
        demanda_ok = demanda_ok and mae_mejor and f1_mejor
        detalle_demanda.append(
            {"frac": frac, "mae_supera_baseline": mae_mejor, "f1_supera_baseline": f1_mejor}
        )

    cobertura_loao = resumen_loao.get("cobertura_ic95")
    loao_ok = cobertura_loao is not None and _COBERTURA_MINIMA <= cobertura_loao <= _COBERTURA_MAXIMA

    por_estimador_oferta = {r["estimador"]: r for r in resumen_oferta}
    modelo_o = por_estimador_oferta.get("modelo_poisson_2016_2019")
    base_o = por_estimador_oferta.get("baseline_s_constante")
    oferta_ok = (
        modelo_o is not None
        and base_o is not None
        and modelo_o["mae_pp_anio"] <= base_o["mae_pp_anio"]
        and modelo_o["f1_macro"] >= base_o["f1_macro"]
    )

    return {
        "demanda_supera_baseline": demanda_ok,
        "demanda_detalle": detalle_demanda,
        "loao_cobertura_en_rango": loao_ok,
        "oferta_supera_baseline": oferta_ok,
        "modelo_se_adopta": bool(demanda_ok and loao_ok and oferta_ok),
    }


def ejecutar(
    panel_d: pd.DataFrame,
    panel_o: pd.DataFrame,
    conapo: pd.DataFrame,
    rng: np.random.Generator | None = None,
) -> dict:
    """Corre las 4 validaciones, calibra el piso y arma el diccionario del reporte.

    `rng`: si se omite, usa `np.random.default_rng(SEMILLA)` (determinismo,
    CLAUDE.md regla 5).
    """
    if rng is None:
        rng = np.random.default_rng(SEMILLA)

    folds_adelg = validar_adelgazamiento(panel_d, rng)
    folds_loao = validar_loao(panel_d)
    folds_oferta = backtest_oferta(panel_o)
    comparacion_fuentes = comparar_censo_conapo(panel_d, conapo)
    calibracion = calibrar_piso_incertidumbre(folds_adelg, folds_loao, folds_oferta)

    resumen_adelg = _resumen_adelgazamiento(folds_adelg)
    resumen_loao = _resumen_loao(folds_loao)
    resumen_oferta = _resumen_oferta(folds_oferta)
    adopcion = _criterio_adopcion(resumen_adelg, resumen_loao, resumen_oferta)

    return {
        "semilla": SEMILLA,
        "metadatos": {
            "marco_geoestadistico": "MG 2020 censal, UPC 889463807469",
        },
        "adelgazamiento": resumen_adelg,
        "loao": resumen_loao,
        "oferta": resumen_oferta,
        "comparacion_censo_conapo": comparacion_fuentes.to_dict("records"),
        "calibracion_piso": calibracion,
        "adopcion": adopcion,
        "limitacion_conapo": (
            "No existe hoy una validación temporal independiente de la tendencia de "
            "demanda a nivel alcaldía; la comparación 2010-2020 alimenta la incertidumbre "
            "del modelo (sigma_C), pero no lo valida contra el futuro."
        ),
    }


def _generado_iso() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat(timespec="seconds")
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _formato_pct(valor: float | None) -> str:
    return "n/d" if valor is None else f"{valor:.2f}"


def _resumen_md(resultados: dict) -> str:
    """Resumen de <= 5 líneas + tabla (metodología §4.3, action_plan.md #13)."""
    adopcion = resultados["adopcion"]
    piso = resultados["calibracion_piso"]
    loao = resultados["loao"]
    lineas = [
        "# Backtest",
        "",
        f"Semilla: `{resultados['semilla']}`. "
        f"Marco geoestadístico: {resultados['metadatos']['marco_geoestadistico']}.",
        "",
        "## Resumen (≤ 5 líneas)",
        "",
        f"1. Demanda (adelgazamiento 25%/50%): "
        f"{'supera' if adopcion['demanda_supera_baseline'] else 'NO supera'} al baseline "
        f"`r=0` en MAE y F1 macro.",
        f"2. Demanda (LOAO): cobertura del IC95 = {_formato_pct(loao.get('cobertura_ic95'))} "
        f"({'dentro' if adopcion['loao_cobertura_en_rango'] else 'FUERA'} de [0.90, 0.97]).",
        f"3. Oferta (origen 2016+2019 -> predice 2024): "
        f"{'supera' if adopcion['oferta_supera_baseline'] else 'NO supera'} al baseline "
        f"'S constante' en MAE y F1 macro.",
        f"4. Piso de incertidumbre calibrado: demanda `sigma_min={piso['demanda']['elegido']}` "
        f"(cobertura {_formato_pct(piso['demanda']['cobertura_lograda'])}); "
        f"oferta `sigma_min={piso['oferta']['elegido']}` "
        f"(cobertura {_formato_pct(piso['oferta']['cobertura_lograda'])}).",
        f"5. **Modelo {'SE ADOPTA' if adopcion['modelo_se_adopta'] else 'NO SE ADOPTA'}** "
        "según el criterio de CLAUDE.md (supera al baseline en las 3 validaciones).",
        "",
        "## Adelgazamiento binomial (Censo 2020, nunca el futuro)",
        "",
        "| frac | estimador | MAE (pp/año) | F1 macro | cobertura IC95 | n |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for fila in resultados["adelgazamiento"]:
        lineas.append(
            f"| {fila['frac']} | {fila['estimador']} | {fila['mae_pp_anio']:.2f} | "
            f"{fila['f1_macro']:.2f} | {_formato_pct(fila.get('cobertura_ic95'))} | {fila['n']} |"
        )

    lineas += [
        "",
        "## LOAO (validación cruzada espacial, deja una alcaldía fuera)",
        "",
        f"MAE: {_formato_pct(loao.get('mae_pp_anio'))} pp/año · "
        f"F1 macro: {_formato_pct(loao.get('f1_macro'))} · "
        f"cobertura IC95: {_formato_pct(loao.get('cobertura_ic95'))} · n={loao.get('n')}",
        "",
        "## Oferta (backtest temporal: origen 2016-10+2019-11 -> predice 2024-11)",
        "",
        "| estimador | MAE log-razón | F1 macro | deviance Poisson | cobertura IC95 | n |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for fila in resultados["oferta"]:
        lineas.append(
            f"| {fila['estimador']} | {fila['mae_pp_anio']:.2f} | {fila['f1_macro']:.2f} | "
            f"{fila['deviance_poisson_media']:.3f} | {_formato_pct(fila.get('cobertura_ic95'))} | "
            f"{fila['n']} |"
        )

    lineas += [
        "",
        "## Comparación censo-CONAPO 2010-2020 (NO es un backtest)",
        "",
        "Compara dos fuentes en el mismo punto del tiempo; alimenta `sigma_C` "
        "(`modelos.simular_demanda`), nunca se usa como validación retrospectiva.",
        "",
        "| alcaldía | tasa censo (%/año) | tasa CONAPO (%/año) | diferencia (pp/año) |",
        "|---|---:|---:|---:|",
    ]
    for fila in resultados["comparacion_censo_conapo"]:
        lineas.append(
            f"| {fila['cve_mun']} | {fila['tasa_censo_pct_anio']} | "
            f"{fila['tasa_conapo_pct_anio']} | {fila['diferencia_pp_anio']} |"
        )

    lineas += [
        "",
        "## Limitación declarada",
        "",
        resultados["limitacion_conapo"],
        "",
    ]
    return "\n".join(lineas) + "\n"


def escribir_reporte(
    resultados: dict,
    destino_json: Path = RUTA_BACKTEST_JSON,
    destino_md: Path = RUTA_BACKTEST_MD,
) -> None:
    """Escribe `data/outputs/backtest.json` y `docs/backtest.md` (determinista salvo `generado`)."""
    salida_json = {"generado": _generado_iso(), **resultados}
    destino_json.parent.mkdir(parents=True, exist_ok=True)
    with destino_json.open("w", encoding="utf-8") as f:
        json.dump(salida_json, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    destino_md.parent.mkdir(parents=True, exist_ok=True)
    destino_md.write_text(_resumen_md(resultados), encoding="utf-8")


def main() -> None:
    """`python -m chipos.backtest`: corre las validaciones y escribe el reporte."""
    from chipos.io import conectar, leer_censo_panel, leer_conapo_0a14, leer_denue_infancias, leer_equivalencia, leer_universo_ageb
    from chipos.panel import construir_panel_demanda, construir_panel_oferta

    print("chipos.backtest: leyendo datos...")
    universo = leer_universo_ageb()
    censo = leer_censo_panel()
    equivalencia = leer_equivalencia()
    conapo = leer_conapo_0a14()
    con = conectar()
    denue = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))

    panel_d = construir_panel_demanda(censo, equivalencia, universo)
    panel_o = construir_panel_oferta(denue, universo)

    print("chipos.backtest: corriendo validaciones (adelgazamiento, LOAO, oferta)...")
    resultados = ejecutar(panel_d, panel_o, conapo)
    escribir_reporte(resultados)
    print(f"chipos.backtest: modelo_se_adopta = {resultados['adopcion']['modelo_se_adopta']}")
    print(f"chipos.backtest: {RUTA_BACKTEST_JSON} y {RUTA_BACKTEST_MD} escritos.")


if __name__ == "__main__":
    main()
