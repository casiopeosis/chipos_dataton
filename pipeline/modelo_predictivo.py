"""
modelo_predictivo.py — PROYECCIÓN Y VALIDACIÓN RETROSPECTIVA
=============================================================

Cubre los cinco requisitos temporales del reto:

  [x] al menos tres momentos históricos comparables  -> ediciones DENUE
  [x] medida explícita de tendencia                  -> pendiente OLS anual
  [x] horizonte de 1, 3 o 5 años                     -> HORIZONTES
  [x] aumento / estabilidad / disminución            -> signo y significancia
  [x] medida de incertidumbre                        -> intervalo de predicción t
  [x] validación retrospectiva                       -> backtest hold-out

POR QUÉ SE MODELA LA ACCESIBILIDAD Y NO EL CONTEO CRUDO
--------------------------------------------------------
La serie de conteo dentro de un hexágono res-9 es casi toda ceros con saltos
de 0 a 1 (hay ~1,800 escuelas de arte en 10,000 hexágonos). Una regresión
sobre eso no estima una tendencia, estima ruido.

La serie de ACCESIBILIDAD (ya suavizada por el decaimiento k-ring de
hexgrid.py) es continua y estable: si abre una guardería a 600 m, la
accesibilidad de tu hexágono sube un poco, que es justo el comportamiento
que queremos capturar. Por eso el panel se arma sobre acceso_*, no sobre
conteos.

LA DEMANDA SE PROYECTA APARTE
------------------------------
déficit proyectado = f(oferta proyectada, población proyectada)

La oferta se proyecta con las ediciones DENUE (5-10 puntos, buena serie).
La población se proyecta con los censos (2 o 3 puntos, serie pobre). Se
mantienen separadas porque su calidad es MUY distinta y hay que reportarlo
así en la ficha de explicabilidad, no promediar la incertidumbre de ambas
en un solo número que oculte que la parte demográfica es la débil.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from capas_config import (  # noqa: E402
    CAPAS_TEMPORALES, HORIZONTES, METODO_NORMALIZACION, RESOLUCION_H3,
    PERFILES_RIESGO,
)
from hexgrid import a_deficit, accesibilidad, normalizar, puntos_a_hex  # noqa: E402

MIN_PUNTOS = 3          # requisito del reto
CONFIANZA = 0.95

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = _REPO_ROOT / "data"
DEFAULT_OUT_DIR = _REPO_ROOT / "data" / "hex"
DEFAULT_HEX_MASTER = DEFAULT_OUT_DIR / "hex_master.parquet"


# ---------------------------------------------------------------------------
# Regresión vectorizada sobre 10,000 hexágonos a la vez
# ---------------------------------------------------------------------------
def ols_panel(X: np.ndarray, Y: np.ndarray):
    """Ajusta y = a + b·x independientemente para cada fila de Y.

    X: (T,)   años transcurridos de cada edición
    Y: (N, T) una fila por hexágono

    Hacerlo vectorizado y no con un for sobre 10,000 hexágonos es la
    diferencia entre 0.2 s y varios minutos, y el dashboard tiene que
    reconstruirse durante la demo si los jueces piden algo.

    Devuelve dict con pendiente, intercepto, r2, se_residual y gl.
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    n = X.size
    xm = X.mean()
    sxx = ((X - xm) ** 2).sum()

    ym = Y.mean(axis=1)
    sxy = ((X - xm) * (Y - ym[:, None])).sum(axis=1)
    b = sxy / sxx
    a = ym - b * xm

    Yhat = a[:, None] + b[:, None] * X[None, :]
    resid = Y - Yhat
    ss_res = (resid ** 2).sum(axis=1)
    ss_tot = ((Y - ym[:, None]) ** 2).sum(axis=1)

    gl = max(n - 2, 1)
    se_resid = np.sqrt(ss_res / gl)

    with np.errstate(divide="ignore", invalid="ignore"):
        r2 = np.where(ss_tot > 0, 1 - ss_res / ss_tot, 0.0)

    return {
        "pendiente": b, "intercepto": a, "r2": r2,
        "se_resid": se_resid, "gl": gl, "xm": xm, "sxx": sxx, "n": n,
    }


def predecir(fit: dict, x0: float, confianza: float = CONFIANZA):
    """Predicción puntual + semiancho del intervalo de PREDICCIÓN.

    Se usa el intervalo de predicción (no el de confianza de la media) y la
    t de Student, no z=1.96. Con 5 ediciones DENUE los grados de libertad
    son 3 y t≈3.18 contra z=1.96: usar z subestimaría la banda en ~60%.
    Comunicar mal la incertidumbre es exactamente lo que el reto penaliza.
    """
    from scipy.stats import t as t_dist

    y0 = fit["intercepto"] + fit["pendiente"] * x0
    se = fit["se_resid"] * np.sqrt(
        1 + 1 / fit["n"] + (x0 - fit["xm"]) ** 2 / fit["sxx"]
    )
    t_crit = float(t_dist.ppf(0.5 + confianza / 2, df=fit["gl"]))
    return np.maximum(y0, 0.0), t_crit * se


def clasificar_direccion(fit: dict, umbral_t: float = 2.0) -> np.ndarray:
    """aumento / estable / disminución, según significancia de la pendiente.

    Una pendiente distinta de cero no basta: si el error estándar es grande,
    esa pendiente es ruido. Sólo se declara dirección cuando |t| supera el
    umbral; si no, 'estable'. Esto evita pintar de rojo media ciudad por
    variaciones que no son distinguibles de cero.
    """
    se_b = fit["se_resid"] / np.sqrt(fit["sxx"])
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = np.where(se_b > 0, fit["pendiente"] / se_b, 0.0)
    out = np.full(len(t_stat), "estable", dtype=object)
    out[t_stat > umbral_t] = "aumento"
    out[t_stat < -umbral_t] = "disminucion"
    return out


# ---------------------------------------------------------------------------
# Panel temporal
# ---------------------------------------------------------------------------
def anios_transcurridos(ediciones: list[str]) -> np.ndarray:
    """'2016-10' -> años desde la primera edición.

    No asume espaciado uniforme: entre nov-2024 y may-2025 hay 6 meses, no
    12. Tratar las ediciones como equiespaciadas sesga la pendiente.
    """
    base = None
    out = []
    for e in sorted(ediciones):
        y, m = int(e[:4]), int(e[5:7])
        t = y + (m - 1) / 12
        base = t if base is None else base
        out.append(t - base)
    return np.array(out)


def construir_panel(capa, data_dir: str, hex_ids) -> pd.DataFrame | None:
    """Panel (hexágono x edición) de accesibilidad para una capa temporal."""
    from build_hex_master import _ediciones_disponibles, construir_capa

    eds = _ediciones_disponibles(data_dir, capa.patron_temporal)
    if len(eds) < MIN_PUNTOS:
        print(f"    [X] sólo {len(eds)} edición(es); el reto exige >= {MIN_PUNTOS}")
        return None

    cols = {}
    for ed in sorted(eds):
        _, acc = construir_capa(capa, data_dir, None, hex_ids, edicion=ed)
        if acc is not None:
            cols[ed] = acc
    if len(cols) < MIN_PUNTOS:
        return None
    return pd.DataFrame(cols, index=hex_ids)


# ---------------------------------------------------------------------------
# Validación retrospectiva
# ---------------------------------------------------------------------------
def backtest(panel: pd.DataFrame, n_holdout: int = 2) -> dict:
    """Entrena con las primeras ediciones y predice las últimas.

    Es el análogo directo de lo que pide el reto ("predecir 2020 usando
    2010-2015"). Reporta MAPE, MAE y cobertura del intervalo.

    La COBERTURA es la métrica que más importa y la que casi nadie reporta:
    si el intervalo es de 95%, debería contener el valor observado ~95% de
    las veces. Si la cobertura sale en 60%, el modelo está vendiendo una
    confianza que no tiene, y eso es peor que un MAPE alto.
    """
    eds = list(panel.columns)
    if len(eds) - n_holdout < MIN_PUNTOS - 1:
        n_holdout = max(1, len(eds) - (MIN_PUNTOS - 1))

    train, test = eds[:-n_holdout], eds[-n_holdout:]
    x_all = anios_transcurridos(eds)
    x_train = x_all[: len(train)]

    fit = ols_panel(x_train, panel[train].to_numpy())

    resultados = []
    for i, ed in enumerate(test):
        x0 = x_all[len(train) + i]
        y_pred, banda = predecir(fit, x0)
        y_real = panel[ed].to_numpy()

        err = np.abs(y_pred - y_real)
        mask = y_real > 0            # MAPE indefinido en ceros
        mape = float(np.mean(err[mask] / y_real[mask]) * 100) if mask.any() else None
        dentro = float(np.mean(np.abs(y_pred - y_real) <= banda) * 100)

        resultados.append({
            "edicion": ed,
            "entrenado_con": train,
            "mae": round(float(np.mean(err)), 3),
            "mape_pct": round(mape, 2) if mape is not None else None,
            "cobertura_ic95_pct": round(dentro, 1),
            "n_hexagonos": int(len(y_real)),
        })
    return {"holdout": resultados}


# ---------------------------------------------------------------------------
# Proyección de población (parte débil, se reporta como tal)
# ---------------------------------------------------------------------------
def proyectar_poblacion(pob_por_censo: dict[int, pd.Series],
                        anio_base: int, horizonte: int) -> tuple[pd.Series, pd.Series | None]:
    """pob_por_censo: {2010: serie, 2020: serie, ...} por hexágono.

    Con DOS censos: recta determinista, sin banda de incertidumbre posible
    (dos puntos definen una recta con 0 grados de libertad). Se devuelve
    banda = None y el dashboard DEBE declararlo.

    Con TRES o más (agregando Conteo 2005): banda t real.
    """
    anios = sorted(pob_por_censo)
    if len(anios) < 2:
        raise ValueError("Se requieren al menos dos censos")

    X = np.array(anios, dtype=float)
    Y = np.column_stack([pob_por_censo[a].to_numpy() for a in anios])
    idx = pob_por_censo[anios[0]].index
    objetivo = anio_base + horizonte

    if len(anios) == 2:
        tasa = (Y[:, 1] - Y[:, 0]) / (X[1] - X[0])
        pred = Y[:, 1] + tasa * (objetivo - X[1])
        return pd.Series(np.maximum(pred, 0), index=idx), None

    fit = ols_panel(X, Y)
    pred, banda = predecir(fit, objetivo)
    return pd.Series(pred, index=idx), pd.Series(banda, index=idx)


# ---------------------------------------------------------------------------
# Aperturas y cierres (churn) entre las dos ediciones más recientes
# ---------------------------------------------------------------------------
def calcular_churn(capa, data_dir: str, hex_ids, resolucion: int = RESOLUCION_H3):
    """Detecta aperturas y cierres comparando IDs de DENUE entre las dos
    ediciones más recientes disponibles.

    Por qué esto es una señal distinta a la pendiente OLS: la regresión
    promedia la tendencia sobre TODO el periodo (ej. 8 años), así que un
    cierre masivo reciente se diluye entre datos viejos. El churn de la
    última transición es la señal más "actual" que hay — es lo que el
    README original pedía explícitamente ("aperturas y cierres de
    establecimientos") y que la regresión sola no captura bien.

    Requiere que la base tenga una columna de ID persistente entre
    ediciones (DENUE la trae como 'ID' o 'id'). Si dos ediciones reusan
    IDs para negocios distintos, esto sobreestima el churn — es una
    limitación conocida de DENUE, no de este código, y se declara así en
    el reporte.
    """
    from build_hex_master import (
        _aplicar_filtro, _col_coords, _col_id, _ediciones_disponibles, _leer,
    )

    eds = _ediciones_disponibles(data_dir, capa.patron_temporal)
    if len(eds) < 2:
        return None

    ed_prev, ed_last = sorted(eds)[-2], sorted(eds)[-1]
    df_prev = _aplicar_filtro(_leer(eds[ed_prev]), capa.filtro)
    df_last = _aplicar_filtro(_leer(eds[ed_last]), capa.filtro)

    id_prev, id_last = _col_id(df_prev), _col_id(df_last)
    if id_prev is None or id_last is None:
        print(f"    [!] sin columna de ID persistente; no se puede calcular "
              f"churn para {capa.id}")
        return None

    ids_prev = set(id_prev.dropna().astype(str))
    ids_last = set(id_last.dropna().astype(str))
    ids_abiertos = ids_last - ids_prev
    ids_cerrados = ids_prev - ids_last

    m_open = id_last.astype(str).isin(ids_abiertos)
    m_close = id_prev.astype(str).isin(ids_cerrados)

    df_open = df_last[m_open]
    if hasattr(df_open, "geometry"):
        df_open = df_open[df_open.geometry.notna()]
    df_close = df_prev[m_close]
    if hasattr(df_close, "geometry"):
        df_close = df_close[df_close.geometry.notna()]

    lat_o, lon_o = _col_coords(df_open)
    lat_c, lon_c = _col_coords(df_close)

    aper = puntos_a_hex(lat_o, lon_o, resolucion).reindex(hex_ids).fillna(0)
    cier = puntos_a_hex(lat_c, lon_c, resolucion).reindex(hex_ids).fillna(0)

    print(f"    churn {ed_prev} -> {ed_last}: "
          f"{len(ids_abiertos)} aperturas, {len(ids_cerrados)} cierres "
          f"({len(ids_prev)} -> {len(ids_last)} unidades totales)")

    return pd.DataFrame({
        f"aperturas_recientes_{capa.id}": aper,
        f"cierres_recientes_{capa.id}": cier,
        f"churn_neto_{capa.id}": aper - cier,
    }, index=hex_ids), ed_prev, ed_last



def ejecutar(data_dir: str, hex_master_path: str, out_dir: str):
    import json

    hm = (pd.read_parquet(hex_master_path) if hex_master_path.endswith(".parquet")
          else pd.read_csv(hex_master_path))
    hm = hm.set_index("hex_id")
    hex_ids = hm.index

    tiene_pob = "pob_total" in hm.columns
    if not tiene_pob:
        print("[!] hex_master sin columnas de población: se proyecta OFERTA, "
              "no demanda insatisfecha.\n")

    reporte = {"capas": {}, "horizontes": HORIZONTES,
               "resolucion_h3": RESOLUCION_H3, "confianza": CONFIANZA}

    for capa in CAPAS_TEMPORALES:
        print(f"\n> {capa.label} ({capa.id})")
        panel = construir_panel(capa, data_dir, hex_ids)
        if panel is None:
            reporte["capas"][capa.id] = {"estado": "sin_serie_suficiente"}
            continue

        X = anios_transcurridos(list(panel.columns))
        fit = ols_panel(X, panel.to_numpy())
        direccion = clasificar_direccion(fit)

        hm[f"tendencia_{capa.id}"] = fit["pendiente"].round(4)
        hm[f"r2_{capa.id}"] = np.round(fit["r2"], 3)
        hm[f"direccion_{capa.id}"] = direccion

        x_ultimo = X[-1]
        for h in HORIZONTES:
            pred, banda = predecir(fit, x_ultimo + h)
            acc_proy = pd.Series(pred, index=hex_ids)

            if tiene_pob:
                # TODO: sustituir por población PROYECTADA a h años
                # (proyectar_poblacion) cuando existan los censos por hex.
                den = hm[capa.denominador]
                deficit = a_deficit(acc_proy, den, METODO_NORMALIZACION)
            else:
                deficit = 1 - normalizar(acc_proy, METODO_NORMALIZACION)

            hm[f"deficit_{capa.id}_h{h}"] = deficit.round(4)
            # incertidumbre normalizada 0-1: alimenta los perfiles de riesgo
            hm[f"incert_{capa.id}_h{h}"] = normalizar(
                pd.Series(banda, index=hex_ids)
            ).round(4)

        bt = backtest(panel)
        reporte["capas"][capa.id] = {
            "estado": "ok",
            "ediciones": list(panel.columns),
            "anios_cubiertos": round(float(X[-1]), 2),
            "r2_mediano": round(float(np.median(fit["r2"])), 3),
            "direccion": pd.Series(direccion).value_counts().to_dict(),
            "validacion_retrospectiva": bt["holdout"],
        }
        for r in bt["holdout"]:
            print(f"    backtest {r['edicion']}: MAPE={r['mape_pct']}% "
                  f"cobertura IC95={r['cobertura_ic95_pct']}%")

        churn = calcular_churn(capa, data_dir, hex_ids)
        if churn is not None:
            tabla_churn, ed_prev, ed_last = churn
            for col in tabla_churn.columns:
                hm[col] = tabla_churn[col]
            reporte["capas"][capa.id]["churn"] = {
                "transicion": f"{ed_prev} -> {ed_last}",
                "aperturas": int(tabla_churn[f"aperturas_recientes_{capa.id}"].sum()),
                "cierres": int(tabla_churn[f"cierres_recientes_{capa.id}"].sum()),
            }

    os.makedirs(out_dir, exist_ok=True)
    sal = os.path.join(out_dir, "hex_master.parquet")
    try:
        hm.reset_index().to_parquet(sal, index=False)
    except Exception:
        sal = os.path.join(out_dir, "hex_master.csv")
        hm.reset_index().to_csv(sal, index=False)

    rep = os.path.join(out_dir, "reporte_validacion.json")
    with open(rep, "w", encoding="utf-8") as fh:
        json.dump(reporte, fh, ensure_ascii=False, indent=2, default=str)

    print(f"\n{sal}\n{rep}")
    return reporte


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA_DIR))
    ap.add_argument("--hex-master", default=str(DEFAULT_HEX_MASTER))
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    a = ap.parse_args()
    ejecutar(a.data, a.hex_master, a.out)
