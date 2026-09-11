"""
Motor de análisis — Semáforo de Inversión Social v1

Mejoras respecto a algo.py (v0):
  - Intervalo de predicción con distribución t de Student (apropiado para n=5).
  - Horizontes de proyección: 3, 5 y 7 años.
  - Validación retrospectiva leave-one-out (LOO-CV).
  - Análisis por subcategoría y sector (público/privado).
  - Cacheo compatible con Streamlit (@st.cache_data).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

# ---------------------------------------------------------------------------
# Rutas y constantes
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

EDITIONS = [
    ("NOVIEMBRE 2022 CDMX", "denue_cdmx_11_2022_depurado.csv"),
    ("NOVIEMBRE 2023 CDMX", "denue_cdmx_11_2023_depurado.csv"),
    ("NOVIEMBRE 2024 CDMX", "denue_cdmx_11_2024_depurado.csv"),
    ("MAYO 2025 CDMX", "denue_cdmx_05_2025_depurado.csv"),
    ("MAYO 2026 CDMX", "denue_cdmx_05_2026_depurado.csv"),
]

EDITION_YEARS: dict[str, float] = {
    "2022-11": 0.0,
    "2023-11": 1.0,
    "2024-11": 2.0,
    "2025-05": 2.5,
    "2026-05": 3.5,
}

POBLACION_2020_ALCALDIA: dict[str, int] = {
    "Iztapalapa": 1835486,
    "Gustavo A. Madero": 1173351,
    "Álvaro Obregón": 759137,
    "Coyoacán": 614447,
    "Tlalpan": 699928,
    "Cuauhtémoc": 545884,
    "Azcapotzalco": 432205,
    "Iztacalco": 404695,
    "Benito Juárez": 434153,
    "Miguel Hidalgo": 414470,
    "Venustiano Carranza": 442798,
    "Xochimilco": 442178,
    "Tláhuac": 392313,
    "Cuajimalpa de Morelos": 217686,
    "La Magdalena Contreras": 247622,
    "Milpa Alta": 152685,
}

CATEGORIES = [
    "Gimnasios y espacios deportivos",
    "Servicios para personas adultas mayores",
]

HORIZONS_YEARS = [3, 5, 7]

# Columnas que se cargan del CSV para minimizar uso de memoria.
_CSV_COLS = [
    "edicion_denue",
    "anio_denue",
    "mes_denue",
    "categoria_proyecto",
    "subcategoria_proyecto",
    "sector_gestion",
    "alcance_analitico",
    "municipio",
    "latitud",
    "longitud",
    "revision_manual",
    "cve_geo_ageb",
]


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def load_all_editions() -> pd.DataFrame:
    """Carga las 5 ediciones históricas de DENUE depuradas."""
    frames: list[pd.DataFrame] = []
    for folder, fname in EDITIONS:
        path = DATA_DIR / folder / fname
        df = pd.read_csv(path, usecols=_CSV_COLS)
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    full["years_elapsed"] = full["edicion_denue"].map(EDITION_YEARS)
    return full


# ---------------------------------------------------------------------------
# Regresión OLS con intervalo de predicción t de Student
# ---------------------------------------------------------------------------

def ols_fit(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """Regresión lineal simple con intervalo de predicción basado en
    la distribución t de Student — correcto para n pequeño.

    Devuelve dict con pendiente, intercepto, R², residual SE, y función
    ``predict(x0) -> (y_hat, banda_inferior, banda_superior)``.
    """
    n = len(x)
    x_mean = float(x.mean())
    y_mean = float(y.mean())
    sxx = float(np.sum((x - x_mean) ** 2))

    if sxx == 0 or n < 3:
        slope, intercept = 0.0, y_mean
        resid_se = 0.0
    else:
        slope = float(np.sum((x - x_mean) * (y - y_mean)) / sxx)
        intercept = y_mean - slope * x_mean
        y_hat = intercept + slope * x
        dof = n - 2
        resid_se = float(np.sqrt(np.sum((y - y_hat) ** 2) / dof))

    y_hat_full = intercept + slope * x
    ss_res = float(np.sum((y - y_hat_full) ** 2))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Grados de libertad para la distribución t
    dof = max(n - 2, 1)
    t_crit = float(t_dist.ppf(0.975, df=dof))  # bilateral 95 %

    def predict(x0: float) -> tuple[float, float, float]:
        """Devuelve (y_hat, lower_95, upper_95)."""
        y0 = intercept + slope * x0
        if sxx == 0 or n < 3:
            se_pred = resid_se
        else:
            se_pred = resid_se * np.sqrt(1 + 1 / n + (x0 - x_mean) ** 2 / sxx)
        margin = t_crit * se_pred
        lower = max(y0 - margin, 0.0)
        upper = y0 + margin
        return max(y0, 0.0), lower, upper

    return {
        "slope_per_year": round(slope, 4),
        "intercept": round(intercept, 4),
        "r2": round(r2, 4),
        "resid_se": round(resid_se, 4),
        "t_crit": round(t_crit, 4),
        "dof": dof,
        "n": n,
        "predict": predict,
    }


# ---------------------------------------------------------------------------
# Validación retrospectiva
# ---------------------------------------------------------------------------

def retro_validation(series: dict[str, int]) -> list[dict]:
    """Entrena con las 3 primeras ediciones (2022-2024) y evalúa en
    2025-05 y 2026-05."""
    train_eds = ["2022-11", "2023-11", "2024-11"]
    test_eds = ["2025-05", "2026-05"]
    x_train = np.array([EDITION_YEARS[e] for e in train_eds])
    y_train = np.array([series[e] for e in train_eds], dtype=float)
    fit = ols_fit(x_train, y_train)

    results = []
    for ed in test_eds:
        y_pred, lo, hi = fit["predict"](EDITION_YEARS[ed])
        y_real = series[ed]
        err_abs = abs(y_pred - y_real)
        err_pct = (err_abs / y_real * 100) if y_real > 0 else (0.0 if y_pred == 0 else None)
        within = bool(lo <= y_real <= hi)
        results.append({
            "edicion": ed,
            "predicho": round(y_pred, 1),
            "observado": y_real,
            "lower_95": round(lo, 1),
            "upper_95": round(hi, 1),
            "error_abs": round(err_abs, 1),
            "error_pct": round(err_pct, 1) if err_pct is not None else None,
            "dentro_IC": within,
        })
    return results


def loo_cv(series: dict[str, int]) -> dict:
    """Leave-one-out cross-validation: entrena con n-1 puntos,
    predice el restante. Devuelve MAE y MAPE."""
    eds = list(EDITION_YEARS.keys())
    errors_abs = []
    errors_pct = []
    for leave_out in eds:
        train_eds = [e for e in eds if e != leave_out]
        x_train = np.array([EDITION_YEARS[e] for e in train_eds])
        y_train = np.array([series[e] for e in train_eds], dtype=float)
        fit = ols_fit(x_train, y_train)
        y_pred, _, _ = fit["predict"](EDITION_YEARS[leave_out])
        y_real = series[leave_out]
        errors_abs.append(abs(y_pred - y_real))
        if y_real > 0:
            errors_pct.append(abs(y_pred - y_real) / y_real * 100)
    return {
        "loo_mae": round(float(np.mean(errors_abs)), 2) if errors_abs else None,
        "loo_mape": round(float(np.mean(errors_pct)), 2) if errors_pct else None,
    }


# ---------------------------------------------------------------------------
# Clasificación semáforo
# ---------------------------------------------------------------------------

def classify_semaforo(
    percapita_percentile: float,
    slope: float,
    slope_percentile: float,
) -> str:
    """Semáforo basado en nivel de oferta per cápita (terciles) y tendencia.

    - **Rojo — Zonas saturadas**: alta oferta actual, crecimiento estancado.
    - **Verde — Zonas de oportunidad**: baja oferta, posible crecimiento.
    - **Amarillo — Zonas en transición**: situación intermedia.
    """
    oferta_alta = percapita_percentile >= 0.66
    oferta_baja = percapita_percentile <= 0.33
    crece = slope_percentile >= 0.66 or slope > 0
    estable_o_baja = slope_percentile <= 0.33 or slope <= 0

    if oferta_alta and estable_o_baja:
        return "rojo"
    if oferta_baja:
        return "verde"
    return "amarillo"


# ---------------------------------------------------------------------------
# Centroides y contorno
# ---------------------------------------------------------------------------

def compute_centroids(raw: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Centroide (promedio lat/lon) por alcaldía usando la edición más reciente."""
    last = raw[raw.edicion_denue == "2026-05"]
    out: dict[str, dict[str, float]] = {}
    for municipio, sub in last.groupby("municipio"):
        out[str(municipio)] = {
            "lat": round(float(sub["latitud"].mean()), 5),
            "lon": round(float(sub["longitud"].mean()), 5),
        }
    return out


def compute_outline(raw: pd.DataFrame) -> list[list[float]]:
    """Envolvente convexa aproximada de la zona cubierta por los datos."""
    from scipy.spatial import ConvexHull

    pts = raw[["longitud", "latitud"]].dropna().to_numpy()
    hull = ConvexHull(pts)
    ring = pts[hull.vertices]
    return [[round(float(lon), 5), round(float(lat), 5)] for lon, lat in ring]


# ---------------------------------------------------------------------------
# Percentil
# ---------------------------------------------------------------------------

def _percentile_rank(value: float, sorted_vals: list[float]) -> float:
    import bisect

    if not sorted_vals:
        return 0.5
    i = bisect.bisect_left(sorted_vals, value)
    return i / max(len(sorted_vals) - 1, 1)


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def build_dataset(
    horizons: list[int] | None = None,
) -> dict[str, Any]:
    """Construye el dataset completo de semáforo con proyecciones insesgadas.

    Parameters
    ----------
    horizons : list[int] | None
        Horizontes de proyección en años. Default: [3, 5, 7].
    """
    if horizons is None:
        horizons = HORIZONS_YEARS

    raw = load_all_editions()
    centroids = compute_centroids(raw)
    outline = compute_outline(raw)

    agg = (
        raw.groupby(["municipio", "categoria_proyecto", "edicion_denue", "years_elapsed"])
        .size()
        .reset_index(name="conteo")
        .sort_values(["municipio", "categoria_proyecto", "years_elapsed"])
    )

    # También agregar por subcategoría para fichas detalladas
    agg_sub = (
        raw.groupby([
            "municipio", "categoria_proyecto", "subcategoria_proyecto",
            "sector_gestion", "edicion_denue", "years_elapsed",
        ])
        .size()
        .reset_index(name="conteo")
    )

    alcaldias = sorted(POBLACION_2020_ALCALDIA.keys())
    last_edition = "2026-05"
    last_years = EDITION_YEARS[last_edition]

    zones: list[dict] = []
    raw_metrics: list[tuple] = []
    fits_cache: dict = {}

    for municipio in alcaldias:
        poblacion = POBLACION_2020_ALCALDIA[municipio]
        for categoria in CATEGORIES:
            sub = agg[(agg.municipio == municipio) & (agg.categoria_proyecto == categoria)]
            series: dict[str, int] = {row.edicion_denue: int(row.conteo) for row in sub.itertuples()}
            for ed in EDITION_YEARS:
                series.setdefault(ed, 0)

            x = np.array([EDITION_YEARS[ed] for ed in EDITION_YEARS])
            y = np.array([series[ed] for ed in EDITION_YEARS], dtype=float)

            fit_full = ols_fit(x, y)
            conteo_actual = series[last_edition]
            percapita = conteo_actual / poblacion * 100_000

            fits_cache[(municipio, categoria)] = (fit_full, series, percapita, poblacion)
            raw_metrics.append((municipio, categoria, percapita, fit_full["slope_per_year"]))

    # Calcular distribuciones para terciles
    percapita_vals: dict[str, list[float]] = {}
    slope_vals: dict[str, list[float]] = {}
    for categoria in CATEGORIES:
        percapita_vals[categoria] = sorted(v[2] for v in raw_metrics if v[1] == categoria)
        slope_vals[categoria] = sorted(v[3] for v in raw_metrics if v[1] == categoria)

    for municipio in alcaldias:
        for categoria in CATEGORIES:
            fit_full, series, percapita, poblacion = fits_cache[(municipio, categoria)]

            # --- Validación retrospectiva ---
            validation = retro_validation(series)
            loo = loo_cv(series)

            # --- Proyecciones ---
            proyecciones: dict[str, dict] = {}
            for h in horizons:
                y_pred, lo, hi = fit_full["predict"](last_years + h)
                proyecciones[str(h)] = {
                    "estimado": round(y_pred, 1),
                    "lower_95": round(lo, 1),
                    "upper_95": round(hi, 1),
                    "banda_95": round(hi - y_pred, 1),
                }

            # --- Semáforo ---
            pc_rank = _percentile_rank(percapita, percapita_vals[categoria])
            sl_rank = _percentile_rank(fit_full["slope_per_year"], slope_vals[categoria])
            semaforo = classify_semaforo(pc_rank, fit_full["slope_per_year"], sl_rank)

            # --- Desglose por subcategoría ---
            sub_detail = agg_sub[
                (agg_sub.municipio == municipio)
                & (agg_sub.categoria_proyecto == categoria)
                & (agg_sub.edicion_denue == last_edition)
            ]
            subcategorias = []
            for _, row in sub_detail.iterrows():
                subcategorias.append({
                    "subcategoria": row["subcategoria_proyecto"],
                    "sector": row["sector_gestion"],
                    "conteo": int(row["conteo"]),
                })

            # --- Factores determinantes ---
            factores = _explain_semaforo(
                semaforo, percapita, pc_rank,
                fit_full["slope_per_year"], sl_rank,
                fit_full["r2"], poblacion, categoria,
            )

            zones.append({
                "alcaldia": municipio,
                "categoria": categoria,
                "poblacion_2020": poblacion,
                "centroide": centroids.get(municipio, {"lat": 19.4326, "lon": -99.1332}),
                "serie_historica": [
                    {"edicion": ed, "conteo": series[ed]} for ed in EDITION_YEARS
                ],
                "oferta_percapita_100k": round(percapita, 2),
                "oferta_percapita_percentil": round(pc_rank, 2),
                "tendencia_pendiente_anual": fit_full["slope_per_year"],
                "tendencia_percentil": round(sl_rank, 2),
                "tendencia_r2": fit_full["r2"],
                "tendencia_resid_se": fit_full["resid_se"],
                "tendencia_t_crit": fit_full["t_crit"],
                "tendencia_dof": fit_full["dof"],
                "proyeccion": proyecciones,
                "validacion_retrospectiva": validation,
                "loo_cv": loo,
                "semaforo": semaforo,
                "subcategorias": subcategorias,
                "factores_determinantes": factores,
            })

    return {
        "generado": "v1 — oferta DENUE con proyecciones insesgadas (t de Student)",
        "ediciones": list(EDITION_YEARS.keys()),
        "categorias": CATEGORIES,
        "horizontes": horizons,
        "contorno_referencia": outline,
        "zonas": zones,
    }


def _explain_semaforo(
    semaforo: str,
    percapita: float,
    pc_rank: float,
    slope: float,
    sl_rank: float,
    r2: float,
    poblacion: int,
    categoria: str,
) -> list[str]:
    """Genera una lista de factores que explican la clasificación del semáforo."""
    factores: list[str] = []

    # Nivel de oferta
    if pc_rank >= 0.66:
        factores.append(
            f"Oferta alta: {percapita:.1f} establecimientos por 100k hab "
            f"(percentil {pc_rank:.0%} dentro de la categoría «{categoria}»)."
        )
    elif pc_rank <= 0.33:
        factores.append(
            f"Oferta baja: {percapita:.1f} establecimientos por 100k hab "
            f"(percentil {pc_rank:.0%} dentro de la categoría «{categoria}»)."
        )
    else:
        factores.append(
            f"Oferta intermedia: {percapita:.1f} establecimientos por 100k hab "
            f"(percentil {pc_rank:.0%})."
        )

    # Tendencia
    if slope > 0:
        factores.append(
            f"Tendencia creciente: +{slope:.2f} establecimientos/año "
            f"(percentil de crecimiento: {sl_rank:.0%})."
        )
    elif slope < 0:
        factores.append(
            f"Tendencia decreciente: {slope:.2f} establecimientos/año "
            f"(la oferta se está reduciendo)."
        )
    else:
        factores.append("Tendencia estable: sin cambio neto en la oferta.")

    # Calidad del ajuste
    if r2 < 0.5:
        factores.append(
            f"Precaución: el ajuste lineal explica poco de la variación (R²={r2:.2f}); "
            f"las proyecciones tienen alta incertidumbre."
        )

    # Clasificación
    labels = {
        "rojo": "Zona saturada — alta oferta con crecimiento estancado.",
        "amarillo": "Zona en transición — oferta y crecimiento intermedios.",
        "verde": "Zona de oportunidad — baja oferta relativa, posible inversión beneficiosa.",
    }
    factores.append(f"Clasificación: {labels.get(semaforo, semaforo)}")

    return factores


# ---------------------------------------------------------------------------
# Utilidades para Streamlit
# ---------------------------------------------------------------------------

def get_zones_dataframe(dataset: dict) -> pd.DataFrame:
    """Convierte las zonas del dataset a un DataFrame plano para visualización."""
    rows = []
    for z in dataset["zonas"]:
        row = {
            "Alcaldía": z["alcaldia"],
            "Categoría": z["categoria"],
            "Población 2020": z["poblacion_2020"],
            "Lat": z["centroide"]["lat"],
            "Lon": z["centroide"]["lon"],
            "Oferta per cápita (100k)": z["oferta_percapita_100k"],
            "Percentil oferta": z["oferta_percapita_percentil"],
            "Pendiente anual": z["tendencia_pendiente_anual"],
            "R²": z["tendencia_r2"],
            "Semáforo": z["semaforo"],
            "LOO MAE": z["loo_cv"]["loo_mae"],
            "LOO MAPE (%)": z["loo_cv"]["loo_mape"],
        }
        # Conteo actual (última edición)
        row["Conteo actual"] = z["serie_historica"][-1]["conteo"]
        # Proyecciones
        for h, proj in z["proyeccion"].items():
            row[f"Proy. {h}a (est.)"] = proj["estimado"]
            row[f"Proy. {h}a (±95%)"] = proj["banda_95"]
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI: generar JSON
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    dataset = build_dataset()
    # Remover funciones predict antes de serializar
    for z in dataset["zonas"]:
        pass  # predict ya no se guarda en zones
    out_path = DATA_DIR / "semaforo_v1.json"
    out_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK -> {out_path} ({len(dataset['zonas'])} filas alcaldía × categoría)")
