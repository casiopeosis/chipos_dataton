"""Primitivas estadísticas compartidas por el estimador (docs/methodology.md §1-7)
y por la validación/diagnósticos (§10-11).

Todo lo que es "ajustar una recta a una serie" o "pasar de oferta a déficit"
vive aquí, para que estimador.py, diagnostico.py y sensibilidad.py usen
exactamente el mismo código, en vez de reimplementarlo con matices distintos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_REFERENCE = ROOT / "data" / "reference"

NIVEL_IC = 0.95
DELTA_FRACCION = 0.10  # materialidad: 10% de theta_ref (methodology.md §7, D6)
Z_975 = float(stats.norm.ppf(0.975))


def parse_edicion(ed: str) -> date:
    y, m = ed.split("-")
    return date(int(y), int(m), 1)


def years_since(d: date, ref: date) -> float:
    return (d - ref).days / 365.25


def cargar_alcaldias() -> dict[str, str]:
    df = pd.read_csv(DATA_REFERENCE / "alcaldias.csv", dtype={"cve_alc": str})
    return dict(zip(df["cve_alc"], df["nombre_oficial"]))


def cargar_poblacion() -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED / "poblacion_alcaldia.csv", dtype={"cve_alc": str})
    return df.set_index("cve_alc")


@dataclass
class AjusteOLS:
    alpha: float
    beta: float
    tbar: float
    ybar: float
    S: float
    rss: float
    n: int


def ajustar_ols(t: np.ndarray, y: np.ndarray) -> AjusteOLS:
    """OLS simple y_j = alpha + beta*t_j (methodology.md §4.2)."""
    n = len(t)
    tbar = float(t.mean())
    ybar = float(y.mean())
    S = float(np.sum((t - tbar) ** 2))
    beta = float(np.sum((t - tbar) * (y - ybar)) / S)
    alpha = float(ybar - beta * tbar)
    resid = y - (alpha + beta * t)
    rss = float(np.sum(resid**2))
    return AjusteOLS(alpha=alpha, beta=beta, tbar=tbar, ybar=ybar, S=S, rss=rss, n=n)


def ajustar_ols_general(t: np.ndarray, y: np.ndarray, columnas_extra: list[np.ndarray]) -> dict:
    """Regresión lineal con columnas extra (término cuadrático o escalón, §10.3).

    Devuelve coef (alpha, beta, *extra), rss y n. Se usa solo para las pruebas
    de diagnóstico y para el modelo de escalón cuando la prueba lo activa;
    el modelo de producción por defecto sigue siendo ajustar_ols.
    """
    n = len(t)
    X = np.column_stack([np.ones(n), t, *columnas_extra])
    coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ coef
    resid = y - fitted
    rss = float(np.sum(resid**2))
    ybar = float(y.mean())
    return dict(coef=coef, rss=rss, n=n, ybar=ybar)


def calcular_phi_pooled(
    ajustes: dict[str, AjusteOLS], cve_list: list[str], params_por_alcaldia: int = 2
) -> tuple[float, int]:
    """Dispersión cuasi-Poisson agrupada (§4.3), generalizada a k parámetros/alcaldía.

    Las alcaldías con ybar=0 no aportan al numerador (RSS/ybar indefinido),
    pero sí a los grados de libertad, tal como especifica §4.3 literalmente
    (nu = suma sobre TODAS las alcaldias de (n_a - params)).
    """
    num = 0.0
    nu = 0
    for cve in cve_list:
        a = ajustes[cve]
        if a.ybar > 0:
            num += a.rss / a.ybar
        nu += a.n - params_por_alcaldia
    phi = num / nu if nu > 0 else float("nan")
    return phi, nu


def prueba_f_agrupada(
    ajustes_restringido: dict[str, AjusteOLS],
    ajustes_ampliado: dict[str, dict],
    cve_list: list[str],
    q_extra_por_alcaldia: int = 1,
) -> dict:
    """F agrupada tipo cuasi-devianza (§10.3): ¿mejora el ajuste con q parámetros
    extra por alcaldía (cuadrático o escalón)? Se pondera cada RSS por 1/ybar_a,
    igual que en calcular_phi_pooled, para ser consistente con Var ∝ phi*m_a.
    """
    wrss_r = 0.0
    wrss_a = 0.0
    df_full = 0
    for cve in cve_list:
        ar = ajustes_restringido[cve]
        aa = ajustes_ampliado[cve]
        if ar.ybar <= 0:
            continue
        wrss_r += ar.rss / ar.ybar
        wrss_a += aa["rss"] / ar.ybar
        df_full += aa["n"] - (2 + q_extra_por_alcaldia)
    q = q_extra_por_alcaldia * len(cve_list)
    if wrss_a <= 0 or df_full <= 0:
        return dict(f_stat=float("nan"), p_value=float("nan"), df1=q, df2=df_full, significativo_1pct=False)
    f_stat = max(((wrss_r - wrss_a) / q) / (wrss_a / df_full), 0.0)
    p_value = float(stats.f.sf(f_stat, q, df_full))
    return dict(f_stat=f_stat, p_value=p_value, df1=q, df2=df_full, significativo_1pct=bool(p_value < 0.01))


def calcular_deficit(
    mu_hat: dict[str, float],
    V: dict[str, float],
    P: dict[str, float],
    cve_list: list[str],
) -> tuple[dict[str, dict], float]:
    """§6: del nivel de oferta al déficit de cobertura D_a, con su varianza."""
    P_tot = sum(P[c] for c in cve_list)
    mu_tot = sum(mu_hat[c] for c in cve_list)
    theta_ref = 1e5 * mu_tot / P_tot

    resultado = {}
    for a in cve_list:
        theta_a = 1e5 * mu_hat[a] / P[a]
        D_a = theta_ref - theta_a
        F_a = D_a * P[a] / 1e5

        c_aa = 1e5 * (1.0 / P_tot - 1.0 / P[a])
        var_D = c_aa**2 * V[a]
        for b in cve_list:
            if b == a:
                continue
            c_ab = 1e5 / P_tot
            var_D += c_ab**2 * V[b]

        var_theta = 1e10 * V[a] / (P[a] ** 2)
        var_F = (P[a] / 1e5) ** 2 * var_D

        resultado[a] = dict(theta=theta_a, D=D_a, F=F_a, var_D=var_D, var_theta=var_theta, var_F=var_F)

    return resultado, theta_ref


def clasificar_semaforo(D_a: float, ic_inf: float, ic_sup: float, delta: float) -> tuple[str, str]:
    """§7: regla del semáforo, absoluta contra la CDMX."""
    if ic_inf > 0 and D_a >= delta:
        return "alto", "concluyente"
    if ic_sup < 0 and D_a <= -delta:
        return "bajo", "concluyente"
    if ic_inf > -delta and ic_sup < delta:
        return "medio", "concluyente"
    return "medio", "indeterminado"


def contar_por_edicion(df: pd.DataFrame, ediciones: list[str], cve_list: list[str]) -> dict[str, dict[str, int]]:
    """Conteos alcaldía x edición con ceros explícitos (methodology.md §2 regla 3)."""
    conteos_raw = df.groupby(["cve_alc", "edicion"]).size()
    return {cve: {ed: int(conteos_raw.get((cve, ed), 0)) for ed in ediciones} for cve in cve_list}
