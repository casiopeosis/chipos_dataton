"""
build_hex_master.py — ORQUESTADOR
==================================

Corre UNA VEZ (offline) y produce los dos archivos que consume el frontend:

    data/hex_master.parquet     una fila por hexágono, una columna por capa
    data/layers_metadata.json   descripción de las capas para armar los sliders

Después de esto, el frontend NO necesita geopandas, ni h3, ni recalcular nada:
sólo hace la suma ponderada. Esa separación es lo que permite que los sliders
respondan instantáneo.

    python build_hex_master.py --data ../data --out ../data

DEPENDENCIA BLOQUEANTE
----------------------
Las columnas de población por grupo de edad (pob_0a5, pob_6a11, ...) vienen
del Censo por AGEB/manzana, que todavía no está en data/. Mientras no exista,
el script corre en MODO OFERTA: calcula accesibilidad real de todas las capas
pero NO puede calcular déficit per cápita. Ver README_PIPELINE.md, bloqueo #1.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from capas_config import (  # noqa: E402
    CAPAS, METODO_NORMALIZACION, RESOLUCION_H3, exportar_metadata,
)
from hexgrid import (  # noqa: E402
    a_deficit, accesibilidad, construir_rejilla, normalizar,
    poligonos_a_hex, puntos_a_hex,
)

warnings.filterwarnings("ignore", category=UserWarning)

RE_EDICION = re.compile(r"(\d{4})[_-](\d{2})")

# Este archivo vive en <repo>/src/pipeline/build_hex_master.py — subir dos
# niveles da la raíz del repo, sin importar desde dónde se ejecute el script.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = _REPO_ROOT / "data"
DEFAULT_OUT_DIR = _REPO_ROOT / "data" / "hex"


# ---------------------------------------------------------------------------
# Carga y filtrado genérico
# ---------------------------------------------------------------------------
def _leer(path: str):
    """Lee CSV o GeoJSON indistintamente. Los CSV del repo vienen con BOM."""
    if path.endswith((".geojson", ".gpkg", ".shp")):
        import geopandas as gpd
        return gpd.read_file(path)
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def _aplicar_filtro(df, filtro: dict):
    """Filtro declarativo desde capas_config.

    Soporta `_flags_or`: lista de columnas booleanas 0/1 de las que basta
    que UNA esté prendida. Es el mecanismo que aprovecha las banderas que
    las bases depuradas ya traen ('Es preescolar', 'Es primaria', ...), en
    vez de re-filtrar por código SCIAN a mano.
    """
    if not filtro:
        return df
    mask = pd.Series(True, index=df.index)
    for clave, valor in filtro.items():
        if clave == "_flags_or":
            presentes = [c for c in valor if c in df.columns]
            faltantes = [c for c in valor if c not in df.columns]
            if faltantes:
                print(f"    [!] columnas ausentes, ignoradas: {faltantes}")
            if not presentes:
                return df.iloc[0:0]
            flags = df[presentes].apply(pd.to_numeric, errors="coerce").fillna(0)
            mask &= flags.sum(axis=1) > 0
        elif clave in df.columns:
            if isinstance(valor, (list, tuple, set)):
                mask &= df[clave].isin(list(valor))
            else:
                mask &= df[clave] == valor
        else:
            print(f"    [!] columna de filtro ausente: {clave}")
            return df.iloc[0:0]
    return df[mask]


def _col_coords(df):
    """Encuentra las columnas de coordenadas sin importar el nombre exacto.
    Asume que `df` ya viene filtrado a geometrías/coordenadas válidas (ver
    construir_capa) para que el índice coincida con el de `_peso_fila`."""
    for la, lo in [("Latitud", "Longitud"), ("latitud", "longitud"),
                   ("lat", "lon"), ("LATITUD", "LONGITUD")]:
        if la in df.columns and lo in df.columns:
            return df[la], df[lo]
    if hasattr(df, "geometry"):
        return df.geometry.y, df.geometry.x
    raise KeyError("No se encontraron columnas de coordenadas")


def _col_id(df):
    """Encuentra la columna de ID persistente de DENUE (para detectar
    aperturas/cierres entre ediciones). Sin esto, churn no se puede calcular."""
    for c in ("ID", "Id", "id"):
        if c in df.columns:
            return df[c]
    return None


def _peso_personal_ocupado(serie: pd.Series) -> pd.Series:
    """'11 a 30 personas' -> 20.5 | '251 y más personas' -> 251*1.2 (abierto).

    Se extraen los números con regex en vez de parsear el texto exacto para
    ser inmune al mojibake que traen estos CSV ('251 y mÃ¡s personas' sigue
    dando los dígitos '251' sin problema).
    """
    def parse(s):
        if pd.isna(s):
            return np.nan
        nums = [int(x) for x in re.findall(r"\d+", str(s))]
        if len(nums) >= 2:
            return (nums[0] + nums[1]) / 2
        if len(nums) == 1:
            return nums[0] * 1.2   # rango abierto ("X y más")
        return np.nan
    return serie.map(parse)


def _peso_fila(df: pd.DataFrame, capa) -> pd.Series:
    """Combina tamaño (personal ocupado) × sector × alcance en un solo peso
    por registro. Si una columna no existe en esta edición en particular,
    ese factor se ignora (peso 1.0) y se avisa una vez.

    El resultado NO está en una escala "absoluta" con significado propio —
    lo que importa es el orden relativo entre hexágonos, porque el paso
    posterior de normalización por percentil vuelve a poner todo en 0-1.
    """
    peso = pd.Series(1.0, index=df.index)

    if capa.col_personal_ocupado:
        if capa.col_personal_ocupado in df.columns:
            tam = _peso_personal_ocupado(df[capa.col_personal_ocupado])
            peso = peso * tam.fillna(tam.median() if tam.notna().any() else 1.0)
        else:
            print(f"    [!] falta columna '{capa.col_personal_ocupado}' "
                  f"(tamaño); se omite ese factor en esta edición")

    if capa.col_sector and capa.factor_sector:
        if capa.col_sector in df.columns:
            f = df[capa.col_sector].map(capa.factor_sector).fillna(
                min(capa.factor_sector.values())  # valor no listado -> el más conservador
            )
            peso = peso * f
        else:
            print(f"    [!] falta columna '{capa.col_sector}' (sector); "
                  f"se omite ese factor en esta edición")

    if capa.col_alcance and capa.factor_alcance:
        if capa.col_alcance in df.columns:
            f = df[capa.col_alcance].map(capa.factor_alcance).fillna(
                min(capa.factor_alcance.values())
            )
            peso = peso * f
        else:
            print(f"    [!] falta columna '{capa.col_alcance}' (alcance); "
                  f"se omite ese factor en esta edición")

    return peso


def _ediciones_disponibles(data_dir: str, patron: str) -> dict[str, str]:
    """Mapea '2020-11' -> ruta del archivo, para todas las ediciones."""
    salida = {}
    for p in sorted(glob.glob(os.path.join(data_dir, "**", patron), recursive=True)):
        m = RE_EDICION.search(os.path.basename(p))
        if m:
            salida[f"{m.group(1)}-{m.group(2)}"] = p
    return salida


# ---------------------------------------------------------------------------
# Construcción de una capa
# ---------------------------------------------------------------------------
def construir_capa(capa, data_dir: str, rejilla, hex_ids, edicion: str | None = None):
    """Devuelve (oferta_local, acceso) para una capa en una edición dada."""
    if capa.temporal:
        eds = _ediciones_disponibles(data_dir, capa.patron_temporal)
        if not eds:
            print(f"    [X] ninguna edición encontrada para {capa.patron_temporal}")
            return None, None
        if edicion is None:
            edicion = max(eds)          # por defecto, la edición más reciente
        if edicion not in eds:
            return None, None
        path = eds[edicion]
        print(f"    edición {edicion}")
    else:
        path = os.path.join(data_dir, capa.archivo)
        if not os.path.exists(path):
            encontrados = glob.glob(os.path.join(data_dir, "**",
                                                 os.path.basename(capa.archivo)),
                                    recursive=True)
            if not encontrados:
                print(f"    [X] archivo no encontrado: {capa.archivo}")
                return None, None
            path = encontrados[0]

    df = _leer(path)
    df = _aplicar_filtro(df, capa.filtro)
    if len(df) == 0:
        print("    [X] 0 registros tras el filtro")
        return None, None

    if capa.tipo == "poligono":
        local = poligonos_a_hex(df, rejilla.reset_index(), capa.columna_valor)
    else:
        if hasattr(df, "geometry"):
            df = df[df.geometry.notna()].copy()
        lat, lon = _col_coords(df)
        peso = _peso_fila(df, capa)
        local = puntos_a_hex(lat, lon, RESOLUCION_H3, peso=peso)

    local = local.reindex(hex_ids).fillna(0.0)
    acc = accesibilidad(local, hex_ids, capa.radio_m, RESOLUCION_H3)
    print(f"    {len(df):>7,} registros | {int((local > 0).sum()):>5,} hex con oferta "
          f"-> {int((acc > 0).sum()):>5,} hex con acceso (r={capa.radio_m}m)")
    return local, acc


# ---------------------------------------------------------------------------
# Población
# ---------------------------------------------------------------------------
def cargar_poblacion(data_dir: str, hex_ids) -> pd.DataFrame | None:
    """Carga poblacion_hexagonos.parquet si ya existe (lo produce
    censo_a_hex.py, por defecto en data/hex/). Si no existe, devuelve None
    y el pipeline corre en modo oferta."""
    for nombre in ("poblacion_hexagonos.parquet", "poblacion_hexagonos.csv"):
        encontrados = glob.glob(os.path.join(data_dir, "**", nombre), recursive=True)
        candidatos = [os.path.join(data_dir, nombre)] + encontrados
        for p in candidatos:
            if os.path.exists(p):
                pob = (pd.read_parquet(p) if p.endswith(".parquet")
                       else pd.read_csv(p))
                pob = pob.set_index("hex_id").reindex(hex_ids).fillna(0.0)
                print(f"  Población cargada: {p} "
                      f"({pob.get('pob_total', pd.Series()).sum():,.0f} habitantes)")
                return pob
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(data_dir: str, out_dir: str, limite: str | None):
    import geopandas as gpd

    print("=" * 68)
    print("CONSTRUCCIÓN DE hex_master".center(68))
    print("=" * 68)

    # 1. rejilla
    print("\n[1/4] Rejilla H3")
    if limite:
        rejilla = construir_rejilla(limite_path=limite)
    else:
        base = []
        for nombre in ("inventario_areas_verdes_cdmx_depurado.geojson",
                       "espacio_publico_cdmx_depurado.geojson"):
            encontrados = glob.glob(os.path.join(data_dir, "**", nombre),
                                    recursive=True)
            if encontrados:
                base.append(gpd.read_file(encontrados[0]))
        if not base:
            raise SystemExit("No hay con qué construir la rejilla. Pasa --limite.")
        rejilla = construir_rejilla(capas_fallback=base)
    rejilla = rejilla.set_index("hex_id")
    hex_ids = rejilla.index

    # 2. población
    print("\n[2/4] Población por hexágono")
    pob = cargar_poblacion(data_dir, hex_ids)
    modo_oferta = pob is None
    if modo_oferta:
        print("  [!] Sin datos de población. MODO OFERTA: se calcula "
              "accesibilidad pero NO déficit per cápita.")
        print("      Falta correr censo_a_hex.py (ver README_PIPELINE.md).")

    # 3. capas
    print("\n[3/4] Capas")
    master = pd.DataFrame(index=hex_ids)
    master["lat"] = rejilla["lat"]
    master["lon"] = rejilla["lon"]
    if pob is not None:
        for c in pob.columns:
            master[c] = pob[c]

    for capa in CAPAS:
        print(f"\n  > {capa.label} ({capa.id})")
        local, acc = construir_capa(capa, data_dir, rejilla, hex_ids)
        if acc is None:
            continue
        master[capa.col_acceso()] = acc.round(3)
        if modo_oferta:
            # proxy sin población: déficit = inverso del acceso normalizado.
            # NO es demanda insatisfecha; sólo sirve para maquetar el frontend.
            master[capa.col_deficit()] = (1 - normalizar(acc, METODO_NORMALIZACION)).round(4)
        else:
            master[capa.col_deficit()] = a_deficit(
                acc, master[capa.denominador], METODO_NORMALIZACION
            ).round(4)

    # 4. salida
    print("\n[4/4] Escritura")
    os.makedirs(out_dir, exist_ok=True)
    salida = master.reset_index()
    ruta_parquet = os.path.join(out_dir, "hex_master.parquet")
    try:
        salida.to_parquet(ruta_parquet, index=False)
        print(f"  {ruta_parquet}  ({len(salida):,} hex x {salida.shape[1]} cols)")
    except Exception as e:
        print(f"  [!] parquet falló ({e}); escribiendo CSV")
        ruta_parquet = os.path.join(out_dir, "hex_master.csv")
        salida.to_csv(ruta_parquet, index=False)

    meta = exportar_metadata(os.path.join(out_dir, "layers_metadata.json"))
    meta_extra = {
        "modo": "oferta_sin_poblacion" if modo_oferta else "deficit_percapita",
        "n_hexagonos": int(len(salida)),
        "advertencia": (
            "Corrido en MODO OFERTA: los valores de déficit NO consideran "
            "población. No presentar como demanda insatisfecha."
            if modo_oferta else ""
        ),
    }
    import json
    with open(os.path.join(out_dir, "layers_metadata.json"), "w", encoding="utf-8") as fh:
        json.dump({**meta, **meta_extra}, fh, ensure_ascii=False, indent=2)
    print(f"  {os.path.join(out_dir, 'layers_metadata.json')}")
    print("\nListo.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA_DIR),
                    help="carpeta con las bases depuradas (default: <repo>/data)")
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR),
                    help="carpeta de salida (default: <repo>/data/hex)")
    ap.add_argument("--limite", default=None,
                    help="polígono oficial de CDMX (Marco Geoestadístico)")
    a = ap.parse_args()
    main(a.data, a.out, a.limite)
