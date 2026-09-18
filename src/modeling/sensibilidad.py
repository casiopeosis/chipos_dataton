"""Análisis de sensibilidad — docs/methodology.md §11.

Se reporta cuántas alcaldías cambian de color frente al resultado principal
bajo cada variante. No cambia el semáforo principal (eso ya lo decidió
diagnostico.py vía la regla de §10.3); esto es un reporte aparte.

"Variante de inclusión" (cuidado diurno, edición 2021-11, banderas opcionales
de infancia, sin PILARES) son las que activan la nota de robustez si mueven
a más de 3 alcaldías (§11, última línea). Las variantes de umbral/estadística
(delta, Bonferroni, fecha de referencia) se reportan pero no activan la nota.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.modeling.nucleo import (
    ajustar_ols,
    calcular_deficit,
    calcular_phi_pooled,
    clasificar_semaforo,
    contar_por_edicion,
    parse_edicion,
    years_since,
    DELTA_FRACCION,
)

VARIANTES_INCLUSION = {
    "adultos_mayores": ["mas_cuidado_diurno", "denominador_65mas", "mas_edicion_2021_11"],
    "infancia": ["mas_banderas_opcionales"],
    "cultura": ["sin_pilares"],
}


def _niveles_desde_ajustes(ajustes, phi, nu, t_star, P, cve_list, delta_fraccion=DELTA_FRACCION, t_crit_override=None):
    mu_hat = {}
    V = {}
    for cve in cve_list:
        a = ajustes[cve]
        if a.ybar <= 0:
            mu_hat[cve], V[cve] = 0.0, 0.0
        else:
            mu_hat[cve] = a.alpha + a.beta * t_star
            V[cve] = phi * a.ybar * (1.0 / a.n + (t_star - a.tbar) ** 2 / a.S)
    deficit, theta_ref = calcular_deficit(mu_hat, V, P, cve_list)
    delta = delta_fraccion * theta_ref
    t_crit = t_crit_override if t_crit_override is not None else float(stats.t.ppf(0.975, nu))
    niveles = {}
    for cve in cve_list:
        d = deficit[cve]
        se = d["var_D"] ** 0.5
        ic_inf, ic_sup = d["D"] - t_crit * se, d["D"] + t_crit * se
        nivel, _ = clasificar_semaforo(d["D"], ic_inf, ic_sup, delta)
        niveles[cve] = nivel
    return niveles, theta_ref


def refit_variante_tendencia(df_subset, ediciones, cve_list, P):
    """Reajusta desde cero (mismo método base, sin kappa/rho de diagnóstico) para
    una variante que cambia los datos de entrada (qué se cuenta o qué ediciones)."""
    conteos = contar_por_edicion(df_subset, ediciones, cve_list)
    t0 = parse_edicion(ediciones[0])
    t_vals = np.array([years_since(parse_edicion(e), t0) for e in ediciones])
    t_star = float(t_vals[-1])
    ajustes = {cve: ajustar_ols(t_vals, np.array([conteos[cve][e] for e in ediciones], dtype=float)) for cve in cve_list}
    phi, nu = calcular_phi_pooled(ajustes, cve_list)
    return _niveles_desde_ajustes(ajustes, phi, nu, t_star, P, cve_list)


def comparar(niveles_principal: dict[str, str], niveles_variante: dict[str, str]) -> dict:
    cambios = [cve for cve in niveles_principal if niveles_principal[cve] != niveles_variante[cve]]
    return dict(n_cambios=len(cambios), alcaldias_cambian=sorted(cambios))


def analizar_sensibilidad_tendencia(
    *,
    nombre_variante_dominio: str,
    df_nucleo: "pd.DataFrame",
    df_todo: "pd.DataFrame",
    ediciones_principal: list[str],
    todas_las_ediciones_disponibles: list[str],
    cve_list: list[str],
    P_principal: dict[str, float],
    P_alterna: dict[str, float] | None,
    niveles_principal: dict[str, str],
    theta_ref_principal: float,
    ajustes_principal,
    phi_principal: float,
    nu_principal: int,
    t_star_principal: float,
    filtro_mas_edicion_extra: str | None = None,
) -> dict:
    resultados = {}

    # --- delta 5% y 20% (mismo ajuste, solo cambia el umbral) ---
    for etiqueta, frac in [("delta_5pct", 0.05), ("delta_20pct", 0.20)]:
        niveles, _ = _niveles_desde_ajustes(
            ajustes_principal, phi_principal, nu_principal, t_star_principal, P_principal, cve_list, delta_fraccion=frac
        )
        resultados[etiqueta] = comparar(niveles_principal, niveles)

    # --- multiplicidad: Bonferroni 1 - 0.05/16 ---
    alpha_bonf = 0.05 / len(cve_list)
    t_crit_bonf = float(stats.t.ppf(1 - alpha_bonf / 2, nu_principal))
    niveles_bonf, _ = _niveles_desde_ajustes(
        ajustes_principal, phi_principal, nu_principal, t_star_principal, P_principal, cve_list, t_crit_override=t_crit_bonf
    )
    resultados["bonferroni"] = comparar(niveles_principal, niveles_bonf)

    # --- fecha de referencia: último conteo crudo en vez del nowcast ---
    mu_hat_crudo, V_crudo = {}, {}
    ultima_edicion = ediciones_principal[-1]
    conteos_ultima = contar_por_edicion(df_nucleo, [ultima_edicion], cve_list)
    for cve in cve_list:
        a = ajustes_principal[cve]
        y_crudo = float(conteos_ultima[cve][ultima_edicion])
        mu_hat_crudo[cve] = y_crudo
        V_crudo[cve] = phi_principal * a.ybar if a.ybar > 0 else 0.0
    deficit_crudo, theta_ref_crudo = calcular_deficit(mu_hat_crudo, V_crudo, P_principal, cve_list)
    delta_crudo = DELTA_FRACCION * theta_ref_crudo
    t_crit = float(stats.t.ppf(0.975, nu_principal))
    niveles_crudo = {}
    for cve in cve_list:
        d = deficit_crudo[cve]
        se = d["var_D"] ** 0.5
        nivel, _ = clasificar_semaforo(d["D"], d["D"] - t_crit * se, d["D"] + t_crit * se, delta_crudo)
        niveles_crudo[cve] = nivel
    resultados["fecha_referencia_cruda"] = comparar(niveles_principal, niveles_crudo)

    # --- variantes de inclusión, específicas por dominio ---
    if nombre_variante_dominio == "adultos_mayores":
        # + cuidado diurno 624121-624122
        niveles, _ = refit_variante_tendencia(df_todo, ediciones_principal, cve_list, P_principal)
        resultados["mas_cuidado_diurno"] = comparar(niveles_principal, niveles)

        # denominador 65+
        niveles, _ = _niveles_desde_ajustes(
            ajustes_principal, phi_principal, nu_principal, t_star_principal, P_alterna, cve_list
        )
        resultados["denominador_65mas"] = comparar(niveles_principal, niveles)

        # + edición 2021-11 no verificada
        if filtro_mas_edicion_extra and filtro_mas_edicion_extra not in ediciones_principal:
            ediciones_con_extra = sorted(ediciones_principal + [filtro_mas_edicion_extra])
            niveles, _ = refit_variante_tendencia(df_nucleo, ediciones_con_extra, cve_list, P_principal)
            resultados["mas_edicion_2021_11"] = comparar(niveles_principal, niveles)

    elif nombre_variante_dominio == "infancia":
        niveles, _ = refit_variante_tendencia(df_todo, ediciones_principal, cve_list, P_principal)
        resultados["mas_banderas_opcionales"] = comparar(niveles_principal, niveles)

    variantes_inclusion = VARIANTES_INCLUSION.get(nombre_variante_dominio, [])
    max_cambios_inclusion = max(
        (resultados[v]["n_cambios"] for v in variantes_inclusion if v in resultados), default=0
    )
    resultados["_nota_robustez"] = max_cambios_inclusion > 3

    return resultados


def analizar_sensibilidad_cultura(
    df_cultura, cve_list, P_total, niveles_principal, ajustes_mu_hat, ajustes_V, nu_desconocido_z
) -> dict:
    resultados = {}
    for etiqueta, frac in [("delta_5pct", 0.05), ("delta_20pct", 0.20)]:
        deficit, theta_ref = calcular_deficit(ajustes_mu_hat, ajustes_V, P_total, cve_list)
        delta = frac * theta_ref
        niveles = {}
        for cve in cve_list:
            d = deficit[cve]
            se = d["var_D"] ** 0.5
            nivel, _ = clasificar_semaforo(d["D"], d["D"] - nu_desconocido_z * se, d["D"] + nu_desconocido_z * se, delta)
            niveles[cve] = nivel
        resultados[etiqueta] = comparar(niveles_principal, niveles)

    alpha_bonf = 0.05 / len(cve_list)
    z_bonf = float(stats.norm.ppf(1 - alpha_bonf / 2))
    deficit, theta_ref = calcular_deficit(ajustes_mu_hat, ajustes_V, P_total, cve_list)
    delta = DELTA_FRACCION * theta_ref
    niveles_bonf = {}
    for cve in cve_list:
        d = deficit[cve]
        se = d["var_D"] ** 0.5
        nivel, _ = clasificar_semaforo(d["D"], d["D"] - z_bonf * se, d["D"] + z_bonf * se, delta)
        niveles_bonf[cve] = nivel
    resultados["bonferroni"] = comparar(niveles_principal, niveles_bonf)

    # sin es_pilares = SI
    df_sin_pilares = df_cultura[df_cultura["es_pilares"] != "SI"]
    conteos = df_sin_pilares.groupby("cve_alc").size()
    mu_hat_sp = {cve: float(conteos.get(cve, 0)) for cve in cve_list}
    V_sp = {cve: mu_hat_sp[cve] for cve in cve_list}
    deficit_sp, theta_ref_sp = calcular_deficit(mu_hat_sp, V_sp, P_total, cve_list)
    delta_sp = DELTA_FRACCION * theta_ref_sp
    niveles_sp = {}
    for cve in cve_list:
        d = deficit_sp[cve]
        se = d["var_D"] ** 0.5
        nivel, _ = clasificar_semaforo(d["D"], d["D"] - nu_desconocido_z * se, d["D"] + nu_desconocido_z * se, delta_sp)
        niveles_sp[cve] = nivel
    resultados["sin_pilares"] = comparar(niveles_principal, niveles_sp)

    variantes_inclusion = VARIANTES_INCLUSION["cultura"]
    max_cambios_inclusion = max((resultados[v]["n_cambios"] for v in variantes_inclusion if v in resultados), default=0)
    resultados["_nota_robustez"] = max_cambios_inclusion > 3

    return resultados
