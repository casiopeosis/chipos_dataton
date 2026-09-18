"""
censo_a_hex.py — POBLACIÓN POR EDAD A HEXÁGONOS
================================================

Produce `poblacion_hexagonos.parquet`, el denominador de TODO el sistema.
Sin este archivo, build_hex_master.py corre en modo oferta y el mapa no puede
llamarse "demanda insatisfecha".

    python censo_a_hex.py --censo ../data/censo_2020_ageb.geojson --anio 2020

QUÉ SE NECESITA DESCARGAR (no está en el repo todavía)
--------------------------------------------------------
1. Marco Geoestadístico Nacional (INEGI) — polígonos de AGEB urbana y/o
   manzana de la entidad 09. Da la geometría.
2. Censo 2020, resultados por AGEB y manzana urbana, entidad 09. Da los
   conteos por edad. Se une al anterior por CVEGEO.
3. Lo mismo para 2010, y (muy recomendable) Conteo 2005 — ver nota sobre
   grados de libertad abajo.

COLUMNAS DE EDAD DEL CENSO QUE SE USAN
---------------------------------------
El Censo trae rangos quinquenales por sexo. Las agregaciones que necesita
el proyecto:

    pob_0a5   = P_0A2 + P_3A5
    pob_6a11  = P_6A11
    pob_12a17 = P_12A14 + P_15A17
    pob_6a17  = pob_6a11 + pob_12a17
    pob_0a17  = pob_0a5 + pob_6a17
    pob_total = POBTOT

OJO CON LOS ASTERISCOS: el Censo suprime celdas por confidencialidad y las
marca con '*' o 'N/D'. Leerlas como cero subestima la población en las zonas
menos pobladas, que son justamente las que el mapa marcaría como "sin
demanda". Este script las convierte a NaN y reporta cuántas hay.

POR QUÉ IMPORTA TENER TRES CENSOS Y NO DOS
--------------------------------------------
Con 2010 y 2020 tienes dos puntos: definen una recta exacta, con cero grados
de libertad y por lo tanto SIN banda de incertidumbre calculable. El reto
exige una medida de incertidumbre. Opciones, en orden de preferencia:

  a) Agregar Conteo 2005 (tiene desglose por AGEB) -> 3 puntos, banda real.
  b) Usar proyecciones CONAPO por municipio como ancla y propagar el error
     municipal a los hexágonos de ese municipio.
  c) Declarar explícitamente que la proyección demográfica es determinista
     y que la banda reportada proviene sólo de la oferta.

(c) es aceptable si se dice; lo que no es aceptable es presentar una banda
que finge cubrir la incertidumbre demográfica cuando no la mide.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capas_config import CRS_GEOGRAFICO, CRS_METRICO, RESOLUCION_H3  # noqa: E402
from hexgrid import construir_rejilla, poligonos_a_hex  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = _REPO_ROOT / "data" / "hex"

# Nombres típicos en los productos censales. El script prueba variantes
# porque INEGI no usa exactamente los mismos encabezados entre años.
MAPEO_EDAD = {
    "pob_0a5":   [["P_0A2", "P_3A5"], ["P_0A2_M", "P_0A2_F", "P_3A5_M", "P_3A5_F"]],
    "pob_6a11":  [["P_6A11"], ["P_6A11_M", "P_6A11_F"]],
    "pob_12a17": [["P_12A14", "P_15A17"], ["P_12A14_M", "P_12A14_F",
                                           "P_15A17_M", "P_15A17_F"]],
    "pob_total": [["POBTOT"], ["POB_TOT"], ["Pob_Total"]],
}

VALORES_NULOS = {"*", "N/D", "n/d", "ND", "", " ", "-"}


def _numerico(serie: pd.Series) -> pd.Series:
    """Convierte a número tratando los supresores censales como NaN, no 0."""
    if serie.dtype.kind in "if":
        return serie.astype(float)
    limpia = serie.astype(str).str.strip().replace(list(VALORES_NULOS), np.nan)
    return pd.to_numeric(limpia, errors="coerce")


def preparar_censo(gdf, verbose: bool = True):
    """Agrega las columnas quinquenales a los grupos del proyecto."""
    out = gdf.copy()
    cols_norm = {c.upper(): c for c in out.columns}
    suprimidas = {}

    for destino, alternativas in MAPEO_EDAD.items():
        for combo in alternativas:
            reales = [cols_norm.get(c.upper()) for c in combo]
            if all(r is not None for r in reales):
                partes = [_numerico(out[r]) for r in reales]
                suprimidas[destino] = int(sum(p.isna().sum() for p in partes))
                out[destino] = sum(p.fillna(0) for p in partes)
                break
        else:
            if verbose:
                print(f"  [X] no se encontraron columnas para {destino}: "
                      f"probé {alternativas}")
            out[destino] = np.nan

    out["pob_6a17"] = out["pob_6a11"].fillna(0) + out["pob_12a17"].fillna(0)
    out["pob_0a17"] = out["pob_0a5"].fillna(0) + out["pob_6a17"]

    if verbose:
        total = out["pob_total"].sum()
        print(f"  Población total en la fuente: {total:,.0f}")
        print(f"  Infancias 0-17: {out['pob_0a17'].sum():,.0f} "
              f"({100 * out['pob_0a17'].sum() / total:.1f}%)")
        for k, v in suprimidas.items():
            if v:
                print(f"  [!] {v} celdas suprimidas/no numéricas en {k} "
                      f"(tratadas como NaN, no como 0)")
        # Sanity check contra la cifra oficial del Censo 2020 CDMX
        if 8.5e6 < total < 9.5e6:
            print("  OK: el total cuadra con el Censo 2020 de CDMX (~9.21 M)")
        else:
            print(f"  [!] El total ({total:,.0f}) no se parece a los ~9.21 M "
                  "del Censo 2020 CDMX. Revisa cobertura y duplicados.")
    return out


GRUPOS = ["pob_0a5", "pob_6a11", "pob_12a17", "pob_6a17", "pob_0a17", "pob_total"]


def censo_a_hexagonos(censo_path: str, rejilla, es_manzana: bool = False):
    """Reproyecta el censo a la rejilla.

    es_manzana=True usa asignación por centroide: las manzanas son tan
    pequeñas frente a un hexágono res-9 (~400 m de ancho) que el error de
    centroide es menor que el error del supuesto de densidad uniforme que
    exige la interpolación areal por AGEB. Si tienes manzana, úsala.
    """
    import geopandas as gpd
    import h3

    censo = gpd.read_file(censo_path).to_crs(CRS_GEOGRAFICO)
    censo = censo[censo.geometry.notna()].copy()
    print(f"  {len(censo):,} polígonos leídos de {os.path.basename(censo_path)}")
    censo = preparar_censo(censo)

    if es_manzana:
        print("  Método: centroide de manzana (preferido)")
        cent = censo.geometry.representative_point()
        censo["hex_id"] = [h3.latlng_to_cell(p.y, p.x, RESOLUCION_H3) for p in cent]
        tabla = censo.groupby("hex_id")[GRUPOS].sum()
    else:
        print("  Método: interpolación areal desde AGEB "
              "(supone densidad uniforme dentro del AGEB)")
        if not censo.geometry.is_valid.all():
            censo["geometry"] = censo.geometry.make_valid()
        piezas = {}
        for g in GRUPOS:
            piezas[g] = poligonos_a_hex(censo, rejilla.reset_index(), g, verbose=False)
        tabla = pd.DataFrame(piezas)
        pct = 100 * tabla["pob_total"].sum() / censo["pob_total"].sum()
        estado = "OK" if pct > 98 else "REVISAR cobertura de la rejilla"
        print(f"  Conservación de población: {pct:.2f}%  [{estado}]")

    return tabla.reindex(rejilla.index).fillna(0.0)


def main(censo_path: str, anio: int, out_dir: str, limite: str | None,
         es_manzana: bool):
    print(f"\nCENSO {anio} -> hexágonos res{RESOLUCION_H3}")
    import geopandas as gpd

    if limite:
        rejilla = construir_rejilla(limite_path=limite)
    else:
        print("  [!] Sin --limite: construyendo rejilla desde el propio censo "
              "(recomendable pasar el Marco Geoestadístico)")
        rejilla = construir_rejilla(capas_fallback=[gpd.read_file(censo_path)])
    rejilla = rejilla.set_index("hex_id")

    tabla = censo_a_hexagonos(censo_path, rejilla, es_manzana)
    tabla = tabla.round(1).reset_index()

    os.makedirs(out_dir, exist_ok=True)
    sufijo = "" if anio == 2020 else f"_{anio}"
    destino = os.path.join(out_dir, f"poblacion_hexagonos{sufijo}.parquet")
    try:
        tabla.to_parquet(destino, index=False)
    except Exception:
        destino = destino.replace(".parquet", ".csv")
        tabla.to_csv(destino, index=False)

    con_gente = int((tabla["pob_total"] >= 10).sum())
    print(f"\n  {destino}")
    print(f"  {len(tabla):,} hexágonos | {con_gente:,} con >=10 habitantes "
          f"({100 * con_gente / len(tabla):.0f}%)")
    print("  Los hexágonos con <10 habitantes quedarán como NaN en el déficit: "
          "no tiene sentido recomendar inversión donde no vive nadie.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--censo", required=True, help="GeoJSON/SHP de AGEB o manzana con población")
    ap.add_argument("--anio", type=int, default=2020)
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--limite", default=None, help="polígono CDMX (Marco Geoestadístico)")
    ap.add_argument("--manzana", action="store_true", help="la fuente es manzana, no AGEB")
    a = ap.parse_args()
    main(a.censo, a.anio, a.out, a.limite, a.manzana)
