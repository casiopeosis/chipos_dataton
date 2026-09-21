"""Asociación AGEB → colonia de la CDMX, para el frontend (búsqueda/filtro/ficha) y el
resaltado del contorno completo de una colonia en el mapa.

Entrada: `data/processed/colonias/colonias_iecm_2022.geojson` (delimitación de colonias del
Instituto Electoral de la Ciudad de México, 2022; descargada por `tools/descargar_datos.py` de
un espejo en GitHub porque `datos.cdmx.gob.mx` no respondió desde esta red — ver
`docs/data_manifest.md`). Propiedades de origen: `colonia`, `alcaldia`, `cveut`, `pobl`.

AGEB (INEGI) y colonia (autoridad municipal/IECM) son dos delimitaciones independientes que no
anidan: sus bordes no coinciden. La asociación se calcula por MAYOR ÁREA DE INTERSECCIÓN (no por
centroide, que falla cuando el centroide cae justo sobre un borde o en un hueco entre polígonos
de colonia que se traslapan) entre cada AGEB y las colonias con las que se cruza.

Salidas:
- `data/reference/colonias_cdmx.geojson`: EPSG:4326, propiedades `cveut`, `colonia`, `alcaldia`
  (deduplicado por `cveut`, quedándose con el polígono de mayor área si hay repetidos).
- `data/reference/colonias_cdmx_simplificado.geojson`: para el frontend, mismo criterio de
  simplificación que `ageb_cdmx_simplificado.geojson` (mapshaper vía npx; respaldo sin red:
  shapely.coverage_simplify).
- `data/interim/ageb_colonia.parquet`: por `cvegeo`, la colonia (`cveut`) con mayor traslape,
  `cobertura_pct` (fracción del área del AGEB que cae en esa colonia) y `n_colonias_interseccion`.
- `data/outputs/colonias_ageb.json`: mismo lookup en JSON, `{cvegeo: {cveut, colonia, cobertura_pct}}`,
  para que el frontend lo copie a `frontend/data/` (fuera del contrato versionado de
  `prediccion_*.json`, igual que `diagnostico.json`).

Nunca sobrescribe un archivo existente en `data/reference/` (CLAUDE.md, regla 3): si existe, lo
compara y avisa si difiere, igual que `tools/build_geo.py`.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

RAIZ = Path(__file__).resolve().parents[1]
REFERENCIA = RAIZ / "data" / "reference"
INTERIM = RAIZ / "data" / "interim"
OUTPUTS = RAIZ / "data" / "outputs"

RUTA_COLONIAS_RAW = RAIZ / "data" / "processed" / "colonias" / "colonias_iecm_2022.geojson"
RUTA_AGEB_GEOJSON = REFERENCIA / "ageb_cdmx.geojson"

CRS_METRICO = "EPSG:6372"  # México ITRF2008 LCC, para áreas (igual que build_geo.py)


def instalar(origen: Path, destino: Path) -> None:
    if destino.exists():
        iguales = hashlib.sha256(origen.read_bytes()).digest() == hashlib.sha256(destino.read_bytes()).digest()
        print(f"{destino.name}: ya existe, no se sobrescribe ({'idéntico' if iguales else 'DIFIERE: revisar'})")
        return
    shutil.copyfile(origen, destino)
    print(f"{destino.relative_to(RAIZ)}: {destino.stat().st_size / 1e6:.2f} MB")


def cargar_colonias() -> gpd.GeoDataFrame:
    g = gpd.read_file(RUTA_COLONIAS_RAW)[["colonia", "alcaldia", "cveut", "geometry"]]
    g["geometry"] = shapely.make_valid(g.geometry.values)
    # Deduplicar por cveut (la fuente trae algunas colonias repetidas/traslapadas): se queda con
    # el polígono de mayor área de cada cveut.
    g = g.set_crs("EPSG:4326") if g.crs is None else g.to_crs("EPSG:4326")
    g["_area"] = g.to_crs(CRS_METRICO).area
    g = g.sort_values("_area", ascending=False).drop_duplicates("cveut").drop(columns="_area")
    return g.reset_index(drop=True)


def unir_ageb_colonia(ageb: gpd.GeoDataFrame, colonias: gpd.GeoDataFrame) -> pd.DataFrame:
    """Por cada AGEB, la colonia con mayor área de intersección (no el centroide: ver docstring)."""
    a = ageb[["cvegeo", "geometry"]].to_crs(CRS_METRICO)
    a["area_ageb"] = a.area
    c = colonias[["cveut", "colonia", "geometry"]].to_crs(CRS_METRICO)

    inter = gpd.overlay(a, c, how="intersection", keep_geom_type=False)
    inter["area_inter"] = inter.area
    inter = inter[inter["area_inter"] > 0]

    conteo = inter.groupby("cvegeo")["cveut"].nunique().rename("n_colonias_interseccion")
    mejor = inter.sort_values("area_inter", ascending=False).drop_duplicates("cvegeo")
    mejor = mejor.merge(conteo, on="cvegeo", how="left")
    mejor["cobertura_pct"] = (mejor["area_inter"] / mejor["area_ageb"] * 100).round(1)

    resultado = a[["cvegeo"]].merge(
        mejor[["cvegeo", "cveut", "colonia", "cobertura_pct", "n_colonias_interseccion"]],
        on="cvegeo",
        how="left",
    )
    resultado["n_colonias_interseccion"] = resultado["n_colonias_interseccion"].fillna(0).astype(int)
    return resultado


def escribir_geojson(g: gpd.GeoDataFrame, destino: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_ruta = Path(tmp) / destino.name
        g.to_file(tmp_ruta, driver="GeoJSON", COORDINATE_PRECISION=6)
        instalar(tmp_ruta, destino)


def simplificar(destino: Path, g4326: gpd.GeoDataFrame) -> None:
    # A diferencia de `ageb_cdmx.geojson` (partición sin traslapes), las colonias del IECM SÍ se
    # traslapan entre sí (ver docstring del módulo): `mapshaper -simplify keep-shapes` está
    # pensado para topología compartida y aquí falla en reparar miles de intersecciones y parte
    # la salida en varios archivos. Se simplifica cada polígono de forma independiente
    # (`shapely.simplify`, preservando topología propia): estos contornos solo se usan para
    # dibujar el resaltado de una colonia en el mapa, no para un join espacial nuevo.
    with tempfile.TemporaryDirectory() as tmp:
        salida = Path(tmp) / destino.name
        gs = g4326.copy()
        gs["geometry"] = shapely.simplify(gs.geometry.values, tolerance=0.00005, preserve_topology=True)
        gs.to_file(salida, driver="GeoJSON", COORDINATE_PRECISION=5)
        print("simplificación: shapely.simplify 0.00005° (preserve_topology)")
        instalar(salida, destino)


def main() -> None:
    if not RUTA_COLONIAS_RAW.exists():
        raise SystemExit(f"falta {RUTA_COLONIAS_RAW}: correr antes `python tools/descargar_datos.py`")
    if not RUTA_AGEB_GEOJSON.exists():
        raise SystemExit(f"falta {RUTA_AGEB_GEOJSON}: correr antes `python tools/build_geo.py`")

    colonias = cargar_colonias()
    ageb = gpd.read_file(RUTA_AGEB_GEOJSON)[["cvegeo", "geometry"]]

    INTERIM.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    escribir_geojson(colonias, REFERENCIA / "colonias_cdmx.geojson")
    simplificar(REFERENCIA / "colonias_cdmx_simplificado.geojson", colonias)

    lookup = unir_ageb_colonia(ageb, colonias)
    lookup.to_parquet(INTERIM / "ageb_colonia.parquet", index=False)
    print(f"data/interim/ageb_colonia.parquet: {len(lookup)} AGEB")

    sin_colonia = lookup["cveut"].isna().sum()
    print(f"AGEB sin colonia asociada (sin intersección): {sin_colonia} / {len(lookup)}")

    salida_json = {
        fila.cvegeo: (
            None
            if pd.isna(fila.cveut)
            else {"cveut": fila.cveut, "colonia": fila.colonia, "cobertura_pct": fila.cobertura_pct}
        )
        for fila in lookup.itertuples()
    }
    (OUTPUTS / "colonias_ageb.json").write_text(
        json.dumps(salida_json, ensure_ascii=False, indent=None, separators=(",", ":")), encoding="utf-8"
    )
    print(f"data/outputs/colonias_ageb.json: {(OUTPUTS / 'colonias_ageb.json').stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
