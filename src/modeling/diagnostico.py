"""Validación y diagnósticos — docs/methodology.md §10.

Solo aplica a los dominios con serie histórica (infancia, adultos_mayores).
Cultura (§5, foto única) no tiene con qué calibrar un origen móvil ni medir
autocorrelación; para cultura solo corre la simulación de control (§10.5),
adaptada al modelo Poisson de una sola foto.

Cada función implementa una subsección de §10 y devuelve un dict serializable
a JSON. `diagnosticar_dominio_tendencia` orquesta 10.1-10.5 y traduce el
resultado en la configuración que debe usar el modelo de producción
(kappa, ventana de ediciones, si se activa el escalón, factor de autocorrelación).
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.modeling.nucleo import (
    AjusteOLS,
    ajustar_ols,
    ajustar_ols_general,
    calcular_deficit,
    calcular_phi_pooled,
    parse_edicion,
    prueba_f_agrupada,
    years_since,
)

RNG_SEED = 20260918  # fecha de la corrida original; fija para reproducibilidad
N_SIM = 2000


# ---------------------------------------------------------------------------
# 10.1 Calibración con origen móvil + 10.2 Sesgo (comparten las predicciones)
# ---------------------------------------------------------------------------


def calibracion_origen_movil(
    conteos: dict[str, dict[str, int]],
    ediciones: list[str],
    cve_list: list[str],
    t0,
) -> dict:
    n = len(ediciones)
    errores: list[float] = []
    z_scores: list[float] = []
    dentro_flags: list[bool] = []
    errores_naive: list[float] = []

    for k in range(4, n):
        train_ed = ediciones[:k]
        target_ed = ediciones[k]
        t_train = np.array([years_since(parse_edicion(e), t0) for e in train_ed])
        t_target = years_since(parse_edicion(target_ed), t0)

        ajustes_k: dict[str, AjusteOLS] = {}
        for cve in cve_list:
            y = np.array([conteos[cve][e] for e in train_ed], dtype=float)
            ajustes_k[cve] = ajustar_ols(t_train, y)
        phi_k, nu_k = calcular_phi_pooled(ajustes_k, cve_list)
        t_crit_k = float(stats.t.ppf(0.975, nu_k)) if nu_k > 0 else float("nan")

        for cve in cve_list:
            a = ajustes_k[cve]
            y_real = float(conteos[cve][target_ed])
            y_naive = float(conteos[cve][train_ed[-1]])

            if a.ybar <= 0:
                y_pred, se_pred = 0.0, 0.0
            else:
                y_pred = a.alpha + a.beta * t_target
                V_pred = phi_k * a.ybar * (1.0 + 1.0 / a.n + (t_target - a.tbar) ** 2 / a.S)
                se_pred = V_pred**0.5

            e_err = y_real - y_pred
            errores.append(e_err)
            errores_naive.append(y_real - y_naive)

            if se_pred > 0:
                moe = t_crit_k * se_pred
                dentro_flags.append(bool(abs(e_err) <= moe))
                z_scores.append(e_err / se_pred)
            else:
                dentro_flags.append(bool(abs(e_err) < 1e-9))
                # sin varianza no hay z bien definido; no contamina kappa

    errores_arr = np.array(errores)
    z_arr = np.array(z_scores)
    n_total = len(errores_arr)
    cobertura = float(np.mean(dentro_flags))
    criterio_cumplido = cobertura >= 0.90
    kappa = float(np.mean(z_arr**2)) if (not criterio_cumplido and len(z_arr) > 0) else 1.0

    mae_tendencia = float(np.mean(np.abs(errores_arr)))
    mae_naive = float(np.mean(np.abs(errores_naive)))

    return dict(
        n_predicciones=n_total,
        cobertura_empirica=cobertura,
        criterio_90pct_cumplido=criterio_cumplido,
        kappa=kappa,
        mae_tendencia=mae_tendencia,
        mae_naive_ultimo_valor=mae_naive,
        tendencia_supera_naive=bool(mae_tendencia < mae_naive),
        _errores=errores_arr,  # uso interno para 10.2; se descarta antes de exportar
    )


def prueba_sesgo(errores: np.ndarray) -> dict:
    """§10.2: media de errores firmados de 10.1, con prueba t."""
    n = len(errores)
    media = float(np.mean(errores))
    s = float(np.std(errores, ddof=1))
    if s == 0 or n < 2:
        return dict(media_error=media, t_stat=float("nan"), p_value=float("nan"), significativo_1pct=False, n=n)
    t_stat = media / (s / np.sqrt(n))
    p_value = float(2 * stats.t.sf(abs(t_stat), n - 1))
    return dict(media_error=media, t_stat=float(t_stat), p_value=p_value, significativo_1pct=bool(p_value < 0.01), n=n)


# ---------------------------------------------------------------------------
# 10.3 Linealidad y cambio de generación
# ---------------------------------------------------------------------------


def prueba_curvatura(
    ajustes_lineales: dict[str, AjusteOLS],
    conteos: dict[str, dict[str, int]],
    ediciones: list[str],
    cve_list: list[str],
    t0,
) -> dict:
    t_vals = np.array([years_since(parse_edicion(e), t0) for e in ediciones])
    ajustes_cuad = {}
    for cve in cve_list:
        y = np.array([conteos[cve][e] for e in ediciones], dtype=float)
        ajustes_cuad[cve] = ajustar_ols_general(t_vals, y, [t_vals**2])
    return prueba_f_agrupada(ajustes_lineales, ajustes_cuad, cve_list, q_extra_por_alcaldia=1)


def prueba_escalon(
    ajustes_lineales: dict[str, AjusteOLS],
    conteos: dict[str, dict[str, int]],
    ediciones: list[str],
    cve_list: list[str],
    t0,
    edicion_corte: str = "2022-11",
) -> dict:
    """Solo adultos_mayores: escalón por alcaldía a partir de edicion_corte (cambio Gen A -> Gen B)."""
    t_vals = np.array([years_since(parse_edicion(e), t0) for e in ediciones])
    t_corte = years_since(parse_edicion(edicion_corte), t0)
    indicador = (t_vals >= t_corte).astype(float)
    ajustes_escalon = {}
    for cve in cve_list:
        y = np.array([conteos[cve][e] for e in ediciones], dtype=float)
        ajustes_escalon[cve] = ajustar_ols_general(t_vals, y, [indicador])
    resultado = prueba_f_agrupada(ajustes_lineales, ajustes_escalon, cve_list, q_extra_por_alcaldia=1)
    resultado["ajustes_escalon"] = ajustes_escalon
    resultado["indicador"] = indicador
    return resultado


# ---------------------------------------------------------------------------
# 10.4 Autocorrelación + 10.5 Simulación de control (comparten las simulaciones)
# ---------------------------------------------------------------------------


def autocorrelacion_lag1_pooled(residuales_por_alcaldia: dict[str, np.ndarray]) -> float:
    """Correlación de rezago 1, agrupando pares consecutivos de todas las alcaldías."""
    xs, ys = [], []
    for _, r in residuales_por_alcaldia.items():
        if len(r) < 3:
            continue
        xs.append(r[:-1])
        ys.append(r[1:])
    if not xs:
        return float("nan")
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def simulacion_control(
    ajustes_finales: dict[str, AjusteOLS],
    phi_final: float,
    cve_list: list[str],
    t_vals: np.ndarray,
    t_star: float,
    P: dict[str, float],
    n_sim: int = N_SIM,
    variante: str = "normal",
    seed: int = RNG_SEED,
) -> dict:
    """§10.4 (referencia de autocorrelación bajo independencia) y §10.5
    (sesgo y cobertura de D_a) calculados sobre las MISMAS simulaciones.

    Se simula desde el modelo ajustado (mu_true_a(t) = alpha_a + beta_a*t,
    con la dispersión phi_final estimada), se reestima todo por simulación
    (alpha, beta, phi, V, D_a), y se compara contra el D_a "verdadero"
    calculado con los parámetros de simulación (mu_true, sin ruido).
    """
    rng = np.random.default_rng(seed)
    n = len(t_vals)
    cve_con_datos = [c for c in cve_list if ajustes_finales[c].ybar > 0]

    mu_true_por_alcaldia = {}
    for cve in cve_list:
        a = ajustes_finales[cve]
        mu_true_por_alcaldia[cve] = a.alpha + a.beta * t_vals  # (n,)

    # D_a "verdadero": usa mu_true evaluado en t_star (sin ruido) como oferta real
    mu_true_star = {cve: ajustes_finales[cve].alpha + ajustes_finales[cve].beta * t_star for cve in cve_list}
    V_cero = {cve: 0.0 for cve in cve_list}
    deficit_true, _ = calcular_deficit(mu_true_star, V_cero, P, cve_list)
    D_true = {cve: deficit_true[cve]["D"] for cve in cve_list}

    D_sims = {cve: np.empty(n_sim) for cve in cve_list}
    se_D_sims = {cve: np.empty(n_sim) for cve in cve_list}
    rho_sims = np.empty(n_sim)

    tbar = float(t_vals.mean())
    S = float(np.sum((t_vals - tbar) ** 2))

    for s in range(n_sim):
        mu_hat_sim = {}
        V_sim = {}
        residuales_sim: dict[str, np.ndarray] = {}
        rss_sum, ybar_sum_n = 0.0, 0

        ajustes_sim: dict[str, AjusteOLS] = {}
        for cve in cve_list:
            mu_true = mu_true_por_alcaldia[cve]
            m_a = max(ajustes_finales[cve].ybar, 1e-9)
            if variante == "normal":
                eps = rng.normal(0.0, np.sqrt(phi_final * m_a), size=n)
                y_sim = mu_true + eps
            else:  # poisson escalada: Var = phi * mu, usando un generador de Poisson
                base = rng.poisson(np.clip(mu_true, 0, None)).astype(float)
                y_sim = mu_true + np.sqrt(phi_final) * (base - mu_true)

            aj = ajustar_ols(t_vals, y_sim)
            ajustes_sim[cve] = aj
            if cve in cve_con_datos:
                residuales_sim[cve] = y_sim - (aj.alpha + aj.beta * t_vals)

        phi_sim, nu_sim = calcular_phi_pooled(ajustes_sim, cve_list)
        for cve in cve_list:
            aj = ajustes_sim[cve]
            if aj.ybar > 0:
                mu_hat_sim[cve] = aj.alpha + aj.beta * t_star
                V_sim[cve] = phi_sim * aj.ybar * (1.0 / aj.n + (t_star - aj.tbar) ** 2 / aj.S)
            else:
                mu_hat_sim[cve] = 0.0
                V_sim[cve] = 0.0

        deficit_sim, _ = calcular_deficit(mu_hat_sim, V_sim, P, cve_list)
        for cve in cve_list:
            D_sims[cve][s] = deficit_sim[cve]["D"]
            se_D_sims[cve][s] = deficit_sim[cve]["var_D"] ** 0.5

        rho_sims[s] = autocorrelacion_lag1_pooled(residuales_sim)

    resultado_por_alcaldia = {}
    sesgo_global = []
    cobertura_global = []
    t_crit_sim = float(stats.t.ppf(0.975, max(len(cve_list) * (n - 2), 1)))
    for cve in cve_list:
        d_sim = D_sims[cve]
        se_sim = se_D_sims[cve]
        sesgo_medio = float(np.mean(d_sim) - D_true[cve])
        cubre = (D_true[cve] >= d_sim - t_crit_sim * se_sim) & (D_true[cve] <= d_sim + t_crit_sim * se_sim)
        cobertura = float(np.mean(cubre))
        resultado_por_alcaldia[cve] = dict(sesgo_medio=sesgo_medio, cobertura_ic95=cobertura)
        sesgo_global.append(sesgo_medio)
        cobertura_global.append(cobertura)

    return dict(
        variante=variante,
        n_sim=n_sim,
        sesgo_medio_global=float(np.mean(sesgo_global)),
        cobertura_min=float(np.min(cobertura_global)),
        cobertura_max=float(np.max(cobertura_global)),
        cobertura_dentro_rango_93_5_96_5=bool(
            0.935 <= float(np.min(cobertura_global)) and float(np.max(cobertura_global)) <= 0.965
        ),
        por_alcaldia=resultado_por_alcaldia,
        rho_referencia_media=float(np.mean(rho_sims)),
        rho_referencia_p95=float(np.quantile(rho_sims, 0.95)),
    )


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------


def diagnosticar_dominio_tendencia(
    conteos: dict[str, dict[str, int]],
    ediciones: list[str],
    cve_list: list[str],
    t0,
    P: dict[str, float],
    es_adultos_mayores: bool = False,
) -> dict:
    """Corre §10.1-10.5 sobre el ajuste base (serie completa) y devuelve tanto
    los resultados como la configuración recomendada para el modelo de
    producción (metodo, ediciones a usar, kappa, factor de autocorrelación).
    """
    t_vals = np.array([years_since(parse_edicion(e), t0) for e in ediciones])
    ajustes_base = {cve: ajustar_ols(t_vals, np.array([conteos[cve][e] for e in ediciones], dtype=float)) for cve in cve_list}
    phi_base, nu_base = calcular_phi_pooled(ajustes_base, cve_list)

    # 10.1 + 10.2
    calib = calibracion_origen_movil(conteos, ediciones, cve_list, t0)
    errores = calib.pop("_errores")
    sesgo = prueba_sesgo(errores)

    # 10.3
    curvatura = prueba_curvatura(ajustes_base, conteos, ediciones, cve_list, t0)
    escalon = None
    if es_adultos_mayores:
        escalon = prueba_escalon(ajustes_base, conteos, ediciones, cve_list, t0)

    # Regla de decisión de §10.3
    escalon_activado = bool(escalon and escalon["significativo_1pct"])
    fallback_ventana = bool(curvatura["significativo_1pct"] or sesgo["significativo_1pct"])

    if escalon_activado:
        metodo_final = "escalon_2022_11"
        ediciones_finales = ediciones
        ajustes_finales_dict = escalon["ajustes_escalon"]
        # Modelo de escalón: mu_hat(t*) = alpha + beta*t* + delta (t* siempre es post-corte)
        ajustes_finales = {
            cve: AjusteOLS(
                alpha=float(ajustes_finales_dict[cve]["coef"][0] + ajustes_finales_dict[cve]["coef"][2]),
                beta=float(ajustes_finales_dict[cve]["coef"][1]),
                tbar=ajustes_base[cve].tbar,
                ybar=ajustes_finales_dict[cve]["ybar"],
                S=ajustes_base[cve].S,
                rss=ajustes_finales_dict[cve]["rss"],
                n=ajustes_finales_dict[cve]["n"],
            )
            for cve in cve_list
        }
        phi_finales, nu_finales = calcular_phi_pooled(
            {c: AjusteOLS(0, 0, 0, ajustes_finales[c].ybar, 1, ajustes_finales[c].rss, ajustes_finales[c].n) for c in cve_list},
            cve_list,
            params_por_alcaldia=3,
        )
        t_vals_finales = t_vals
        t_star_final = float(t_vals[-1])
    elif fallback_ventana:
        metodo_final = "ventana_5_recientes"
        ediciones_finales = ediciones[-5:]
        t_vals_finales = np.array([years_since(parse_edicion(e), t0) for e in ediciones_finales])
        ajustes_finales = {
            cve: ajustar_ols(t_vals_finales, np.array([conteos[cve][e] for e in ediciones_finales], dtype=float))
            for cve in cve_list
        }
        phi_finales, nu_finales = calcular_phi_pooled(ajustes_finales, cve_list)
        t_star_final = float(t_vals_finales[-1])
    else:
        metodo_final = "completo"
        ediciones_finales = ediciones
        ajustes_finales = ajustes_base
        phi_finales, nu_finales = phi_base, nu_base
        t_vals_finales = t_vals
        t_star_final = float(t_vals[-1])

    # 10.4 + 10.5: simulación sobre el modelo final ya seleccionado
    sim_normal = simulacion_control(
        ajustes_finales, phi_finales, cve_list, t_vals_finales, t_star_final, P, variante="normal"
    )
    sim_poisson = simulacion_control(
        ajustes_finales, phi_finales, cve_list, t_vals_finales, t_star_final, P, variante="poisson_escalada"
    )

    residuales_finales = {}
    for cve in cve_list:
        a = ajustes_finales[cve]
        if a.ybar <= 0 or a.n <= 2:
            continue
        sigma = (a.rss / (a.n - 2)) ** 0.5
        if sigma <= 0:
            continue
        fitted = a.alpha + a.beta * t_vals_finales
        y_obs = np.array([conteos[cve][e] for e in ediciones_finales], dtype=float)
        residuales_finales[cve] = (y_obs - fitted) / sigma

    rho_hat = autocorrelacion_lag1_pooled(residuales_finales)
    rho_ref_p95 = sim_normal["rho_referencia_p95"]
    autocorrelacion_significativa = bool(not np.isnan(rho_hat) and rho_hat > rho_ref_p95)
    factor_rho = float((1 + rho_hat) / (1 - rho_hat)) if autocorrelacion_significativa and rho_hat < 1 else 1.0

    kappa_final = calib["kappa"]
    phi_produccion = phi_finales * kappa_final

    return {
        "calibracion_origen_movil": calib,
        "sesgo": sesgo,
        "curvatura": {k: v for k, v in curvatura.items()},
        "escalon": ({k: v for k, v in escalon.items() if k not in ("ajustes_escalon", "indicador")} if escalon else None),
        "autocorrelacion": {
            "rho_hat": None if np.isnan(rho_hat) else rho_hat,
            "rho_referencia_p95": rho_ref_p95,
            "significativa": autocorrelacion_significativa,
            "factor_ajuste_varianza": factor_rho,
        },
        "simulacion_control": {"normal": sim_normal, "poisson_escalada": sim_poisson},
        "decision": {
            "metodo_final": metodo_final,
            "escalon_activado": escalon_activado,
            "fallback_ventana_activado": fallback_ventana,
            "ediciones_finales": ediciones_finales,
            "kappa": kappa_final,
            "factor_rho": factor_rho,
        },
        "_produccion": {
            "ajustes_finales": ajustes_finales,
            "phi": phi_produccion,
            "phi_sin_kappa": phi_finales,
            "nu": nu_finales,
            "t_vals": t_vals_finales,
            "t_star": t_star_final,
            "ediciones": ediciones_finales,
            "factor_rho": factor_rho,
        },
    }
