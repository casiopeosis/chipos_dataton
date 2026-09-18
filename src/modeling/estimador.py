"""Estimador de déficit de cobertura por alcaldía y dominio, con validación.

Implementa docs/methodology.md completo:
  - §1, §4-7: estimando D_a, modelo de tendencia / Poisson foto única, semáforo.
  - §10: validación y diagnósticos (calibración con origen móvil, sesgo,
    linealidad/escalón, autocorrelación, simulación de control). Los
    resultados de §10 SÍ retroalimentan la producción cuando la regla lo
    exige (kappa infla phi, la regla de linealidad puede restringir la
    ventana de ediciones o activar el escalón, la autocorrelación puede
    inflar la varianza) — no es solo un reporte aparte.
  - §11: análisis de sensibilidad (se reporta; no cambia el semáforo).

Salidas:
  - output/demanda_alcaldias.json: un único JSON con el semáforo final.
  - validacion/{dominio}.json: diagnósticos + sensibilidad por dominio.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

from src.modeling.nucleo import (
    ROOT,
    DATA_PROCESSED,
    NIVEL_IC,
    DELTA_FRACCION,
    Z_975,
    AjusteOLS,
    cargar_alcaldias,
    cargar_poblacion,
    calcular_deficit,
    clasificar_semaforo,
    contar_por_edicion,
    parse_edicion,
)
from src.modeling.diagnostico import diagnosticar_dominio_tendencia
from src.modeling.sensibilidad import analizar_sensibilidad_tendencia, analizar_sensibilidad_cultura

OUTPUT_PATH = ROOT / "output" / "demanda_alcaldias.json"
VALIDACION_DIR = ROOT / "validacion"


def git_commit_actual() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return None


def _metodo_id(decision: dict) -> str:
    base = "tendencia_cq_agrupada@1"
    if decision["metodo_final"] == "ventana_5_recientes":
        base += "+ventana5"
    elif decision["metodo_final"] == "escalon_2022_11":
        base += "+escalon2022_11"
    if decision["kappa"] != 1.0:
        base += "+kappa"
    if decision["factor_rho"] != 1.0:
        base += "+rho_ajustada"
    return base


def construir_alcaldias_tendencia(
    ajustes: dict[str, AjusteOLS],
    phi: float,
    nu: int,
    t_star: float,
    P: dict[str, float],
    cve_list: list[str],
    nombres_alcaldia: dict[str, str],
    factor_rho: float,
) -> tuple[dict, float, float]:
    mu_hat, V, sin_oferta = {}, {}, {}
    for cve in cve_list:
        a = ajustes[cve]
        sin_oferta[cve] = a.ybar <= 0
        if sin_oferta[cve]:
            mu_hat[cve], V[cve] = 0.0, 0.0
        else:
            mu_hat[cve] = a.alpha + a.beta * t_star
            V_base = phi * a.ybar * (1.0 / a.n + (t_star - a.tbar) ** 2 / a.S)
            V[cve] = V_base * factor_rho

    deficit, theta_ref = calcular_deficit(mu_hat, V, P, cve_list)
    delta = DELTA_FRACCION * theta_ref
    t_crit = float(stats.t.ppf(0.975, nu)) if nu > 0 else float("nan")

    alcaldias_out = {}
    for cve in cve_list:
        d = deficit[cve]
        se_oferta = V[cve] ** 0.5
        oferta_ic_inf_raw = mu_hat[cve] - t_crit * se_oferta
        se_D = d["var_D"] ** 0.5
        ic_inf_D, ic_sup_D = d["D"] - t_crit * se_D, d["D"] + t_crit * se_D
        se_theta = d["var_theta"] ** 0.5
        se_F = d["var_F"] ** 0.5

        nivel, certeza = clasificar_semaforo(d["D"], ic_inf_D, ic_sup_D, delta)

        banderas = []
        if sin_oferta[cve]:
            banderas.append("sin_oferta_observada")
        if oferta_ic_inf_raw < 0:
            banderas.append("ic_inf_recortado")

        alcaldias_out[cve] = {
            "nombre": nombres_alcaldia[cve],
            "poblacion_objetivo": P[cve],
            "oferta": {
                "estimacion": mu_hat[cve],
                "ic_inf": max(0.0, oferta_ic_inf_raw),
                "ic_sup": mu_hat[cve] + t_crit * se_oferta,
                "ic_inf_recortado": bool(oferta_ic_inf_raw < 0),
            },
            "cobertura": {
                "estimacion": d["theta"],
                "ic_inf": d["theta"] - t_crit * se_theta,
                "ic_sup": d["theta"] + t_crit * se_theta,
            },
            "estimacion": d["D"],
            "ic_inf": ic_inf_D,
            "ic_sup": ic_sup_D,
            "faltantes": {
                "estimacion": d["F"],
                "ic_inf": d["F"] - t_crit * se_F,
                "ic_sup": d["F"] + t_crit * se_F,
            },
            "nivel": nivel,
            "certeza": certeza,
            "banderas": banderas,
        }

    return alcaldias_out, theta_ref, delta


def procesar_dominio_tendencia(
    nombre_dominio: str,
    grupo_poblacional: str,
    df_nucleo: pd.DataFrame,
    df_todo: pd.DataFrame,
    ediciones: list[str],
    cve_list: list[str],
    poblacion: pd.DataFrame,
    columna_poblacion: str,
    columna_poblacion_alterna: str | None,
    nombres_alcaldia: dict[str, str],
    es_adultos_mayores: bool,
    filtro_mas_edicion_extra: str | None = None,
) -> tuple[dict, dict]:
    P = {cve: float(poblacion[columna_poblacion][cve]) for cve in cve_list}
    t0 = parse_edicion(ediciones[0])
    conteos = contar_por_edicion(df_nucleo, ediciones, cve_list)

    diag = diagnosticar_dominio_tendencia(conteos, ediciones, cve_list, t0, P, es_adultos_mayores=es_adultos_mayores)
    prod = diag.pop("_produccion")

    metodo_id = _metodo_id(diag["decision"])
    alcaldias_out, theta_ref, delta = construir_alcaldias_tendencia(
        prod["ajustes_finales"], prod["phi"], prod["nu"], prod["t_star"], P, cve_list, nombres_alcaldia, prod["factor_rho"]
    )

    dominio_json = {
        "dominio": nombre_dominio,
        "metodo_id": metodo_id,
        "tipo_intervalo": "tendencia_cuasi_poisson",
        "fecha_referencia": ediciones[-1],
        "grupo_poblacional": grupo_poblacional,
        "nivel_ic": NIVEL_IC,
        "unidad": "establecimientos por 100 mil personas del grupo",
        "referencia_cdmx": {"cobertura_100k": theta_ref, "delta": delta},
        "parametros": {
            "phi": prod["phi"],
            "phi_sin_kappa": prod["phi_sin_kappa"],
            "kappa": diag["decision"]["kappa"],
            "factor_rho": prod["factor_rho"],
            "gl": prod["nu"],
            "t_crit": float(stats.t.ppf(0.975, prod["nu"])) if prod["nu"] > 0 else None,
            "ediciones": ediciones,
            "ediciones_usadas_en_produccion": prod["ediciones"],
        },
        "alcaldias": alcaldias_out,
    }

    niveles_principal = {cve: alcaldias_out[cve]["nivel"] for cve in cve_list}
    P_alterna = (
        {cve: float(poblacion[columna_poblacion_alterna][cve]) for cve in cve_list}
        if columna_poblacion_alterna
        else None
    )

    sensibilidad = analizar_sensibilidad_tendencia(
        nombre_variante_dominio=nombre_dominio,
        df_nucleo=df_nucleo,
        df_todo=df_todo,
        ediciones_principal=prod["ediciones"],
        todas_las_ediciones_disponibles=ediciones,
        cve_list=cve_list,
        P_principal=P,
        P_alterna=P_alterna,
        niveles_principal=niveles_principal,
        theta_ref_principal=theta_ref,
        ajustes_principal=prod["ajustes_finales"],
        phi_principal=prod["phi"],
        nu_principal=prod["nu"],
        t_star_principal=prod["t_star"],
        filtro_mas_edicion_extra=filtro_mas_edicion_extra,
    )

    diag["sensibilidad"] = sensibilidad
    return dominio_json, diag


def procesar_cultura(
    df_cultura: pd.DataFrame, cve_list: list[str], poblacion: pd.DataFrame, nombres_alcaldia: dict[str, str]
) -> tuple[dict, dict]:
    P = {cve: float(poblacion["poblacion_total"][cve]) for cve in cve_list}
    conteos = df_cultura.groupby("cve_alc").size()
    mu_hat = {cve: float(conteos.get(cve, 0)) for cve in cve_list}
    V = {cve: mu_hat[cve] for cve in cve_list}

    deficit, theta_ref = calcular_deficit(mu_hat, V, P, cve_list)
    delta = DELTA_FRACCION * theta_ref
    z_crit = Z_975

    alcaldias_out = {}
    for cve in cve_list:
        d = deficit[cve]
        se_oferta = V[cve] ** 0.5
        oferta_ic_inf_raw = mu_hat[cve] - z_crit * se_oferta
        se_D = d["var_D"] ** 0.5
        ic_inf_D, ic_sup_D = d["D"] - z_crit * se_D, d["D"] + z_crit * se_D
        se_theta = d["var_theta"] ** 0.5
        se_F = d["var_F"] ** 0.5
        nivel, certeza = clasificar_semaforo(d["D"], ic_inf_D, ic_sup_D, delta)
        banderas = []
        if mu_hat[cve] == 0:
            banderas.append("sin_oferta_observada")
        if oferta_ic_inf_raw < 0:
            banderas.append("ic_inf_recortado")
        alcaldias_out[cve] = {
            "nombre": nombres_alcaldia[cve],
            "poblacion_objetivo": P[cve],
            "oferta": {
                "estimacion": mu_hat[cve],
                "ic_inf": max(0.0, oferta_ic_inf_raw),
                "ic_sup": mu_hat[cve] + z_crit * se_oferta,
                "ic_inf_recortado": bool(oferta_ic_inf_raw < 0),
            },
            "cobertura": {
                "estimacion": d["theta"],
                "ic_inf": d["theta"] - z_crit * se_theta,
                "ic_sup": d["theta"] + z_crit * se_theta,
            },
            "estimacion": d["D"],
            "ic_inf": ic_inf_D,
            "ic_sup": ic_sup_D,
            "faltantes": {
                "estimacion": d["F"],
                "ic_inf": d["F"] - z_crit * se_F,
                "ic_sup": d["F"] + z_crit * se_F,
            },
            "nivel": nivel,
            "certeza": certeza,
            "banderas": banderas,
        }

    dominio_json = {
        "dominio": "cultura",
        "metodo_id": "poisson_foto_unica@1",
        "tipo_intervalo": "poisson_foto_unica",
        "fecha_referencia": "unica",
        "grupo_poblacional": "total",
        "nivel_ic": NIVEL_IC,
        "unidad": "establecimientos por 100 mil personas del grupo",
        "referencia_cdmx": {"cobertura_100k": theta_ref, "delta": delta},
        "parametros": {"phi": 1.0, "kappa": 1.0, "gl": None, "t_crit": z_crit, "ediciones": ["unica"]},
        "alcaldias": alcaldias_out,
    }

    # 10.5 (sin serie -> sin 10.1-10.4): simulación de control sobre el modelo Poisson.
    sim = simulacion_control_cultura(mu_hat, cve_list, P)

    niveles_principal = {cve: alcaldias_out[cve]["nivel"] for cve in cve_list}
    sensibilidad = analizar_sensibilidad_cultura(df_cultura, cve_list, P, niveles_principal, mu_hat, V, z_crit)

    diag = {"simulacion_control": sim, "sensibilidad": sensibilidad}
    return dominio_json, diag


def simulacion_control_cultura(mu_hat: dict[str, float], cve_list: list[str], P: dict[str, float], n_sim: int = 2000) -> dict:
    """§10.5 adaptada a la foto única: se simula y_sim ~ Poisson(mu_true=y_observado)
    y se verifica sesgo/cobertura de D_a con la fórmula de §5-6."""
    rng = np.random.default_rng(20260918)
    V_cero = {cve: 0.0 for cve in cve_list}
    deficit_true, _ = calcular_deficit(mu_hat, V_cero, P, cve_list)
    D_true = {cve: deficit_true[cve]["D"] for cve in cve_list}

    D_sims = {cve: np.empty(n_sim) for cve in cve_list}
    se_D_sims = {cve: np.empty(n_sim) for cve in cve_list}
    for s in range(n_sim):
        y_sim = {cve: float(rng.poisson(max(mu_hat[cve], 1e-9))) for cve in cve_list}
        V_sim = {cve: y_sim[cve] for cve in cve_list}
        deficit_sim, _ = calcular_deficit(y_sim, V_sim, P, cve_list)
        for cve in cve_list:
            D_sims[cve][s] = deficit_sim[cve]["D"]
            se_D_sims[cve][s] = deficit_sim[cve]["var_D"] ** 0.5

    resultado_por_alcaldia = {}
    sesgo_global, cobertura_global = [], []
    for cve in cve_list:
        d_sim, se_sim = D_sims[cve], se_D_sims[cve]
        sesgo_medio = float(np.mean(d_sim) - D_true[cve])
        cubre = (D_true[cve] >= d_sim - Z_975 * se_sim) & (D_true[cve] <= d_sim + Z_975 * se_sim)
        cobertura = float(np.mean(cubre))
        resultado_por_alcaldia[cve] = dict(sesgo_medio=sesgo_medio, cobertura_ic95=cobertura)
        sesgo_global.append(sesgo_medio)
        cobertura_global.append(cobertura)

    return dict(
        variante="poisson_foto_unica",
        n_sim=n_sim,
        sesgo_medio_global=float(np.mean(sesgo_global)),
        cobertura_min=float(np.min(cobertura_global)),
        cobertura_max=float(np.max(cobertura_global)),
        cobertura_dentro_rango_93_5_96_5=bool(
            0.935 <= float(np.min(cobertura_global)) and float(np.max(cobertura_global)) <= 0.965
        ),
        por_alcaldia=resultado_por_alcaldia,
    )


def main() -> None:
    nombres_alcaldia = cargar_alcaldias()
    cve_list = sorted(nombres_alcaldia)
    poblacion = cargar_poblacion()

    # --- Infancia ---
    infancias = pd.read_csv(DATA_PROCESSED / "infancias.csv", low_memory=False, dtype={"cve_alc": str})
    infancia_nucleo = infancias[infancias["alcance"] == "Principal"]
    ediciones_infancia = sorted(infancia_nucleo["edicion"].unique())
    dominio_infancia, diag_infancia = procesar_dominio_tendencia(
        "infancia",
        "0-17",
        infancia_nucleo,
        infancias,  # df_todo: incluye banderas opcionales, para el análisis de sensibilidad
        ediciones_infancia,
        cve_list,
        poblacion,
        "g0_17",
        None,
        nombres_alcaldia,
        es_adultos_mayores=False,
    )

    # --- Adultos mayores ---
    adultos_mayores = pd.read_csv(DATA_PROCESSED / "adultos_mayores.csv", low_memory=False, dtype={"cve_alc": str})
    residencias = adultos_mayores[
        (adultos_mayores["subcategoria"] == "residencias") & (adultos_mayores["edicion_verificada"] == True)  # noqa: E712
    ]
    residencias_mas_diurno = adultos_mayores[
        (adultos_mayores["subcategoria"].isin(["residencias", "cuidado_diurno"]))
        & (adultos_mayores["edicion_verificada"] == True)  # noqa: E712
    ]
    ediciones_am = sorted(residencias["edicion"].unique())
    dominio_adultos_mayores, diag_am = procesar_dominio_tendencia(
        "adultos_mayores",
        "60+",
        residencias,
        residencias_mas_diurno,
        ediciones_am,
        cve_list,
        poblacion,
        "g60m",
        "g65m",
        nombres_alcaldia,
        es_adultos_mayores=True,
        filtro_mas_edicion_extra="2021-11",
    )

    # --- Cultura ---
    cultura = pd.read_csv(DATA_PROCESSED / "cultura.csv", dtype={"cve_alc": str})
    dominio_cultura, diag_cultura = procesar_cultura(cultura, cve_list, poblacion, nombres_alcaldia)

    salida = {
        "schema_version": 1,
        "generado": datetime.now(timezone.utc).isoformat(),
        "commit": git_commit_actual(),
        "nivel_ic": NIVEL_IC,
        "unidad": "establecimientos por 100 mil personas del grupo",
        "dominios": {
            "infancia": dominio_infancia,
            "adultos_mayores": dominio_adultos_mayores,
            "cultura": dominio_cultura,
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"Escrito {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")

    VALIDACION_DIR.mkdir(parents=True, exist_ok=True)
    for nombre, diag in [("infancia", diag_infancia), ("adultos_mayores", diag_am), ("cultura", diag_cultura)]:
        path = VALIDACION_DIR / f"{nombre}.json"
        payload = {
            "dominio": nombre,
            "generado": datetime.now(timezone.utc).isoformat(),
            "commit": salida["commit"],
            **diag,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"Escrito {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
