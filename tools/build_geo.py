"""Geometría AGEB de la CDMX para joins y frontend, y equivalencia AGEB 2010 ↔ 2020.

Entradas (data/processed/marco_geo/):
- mg2020/09a.shp (AGEB urbanas 2020), mg2020/09ar.shp (AGEB rurales 2020) — Marco
  Geoestadístico, Censo 2020 (UPC 889463807469), CRS MEXICO_ITRF_2008_LCC.
- mg2010v5/ageb_urbana_2010_09.gpkg — Marco Geoestadístico 2010 v5.0 (UPC 702825292812).

Salidas:
- data/reference/ageb_cdmx.geojson: EPSG:4326, geometrías válidas, propiedades `cvegeo`,
  `cve_mun`, `ambito` (urbano|rural). Urbanas: CVEGEO de 13 caracteres. Rurales: INEGI no les
  asigna localidad → CVEGEO de 9 caracteres (ENT+MUN+AGEB), tal cual lo publica el marco.
- data/reference/ageb_cdmx_simplificado.geojson: para el frontend (< 5 MB, 5 decimales,
  topología compartida). mapshaper vía npx; si no está disponible, shapely.coverage_simplify.
- data/interim/equivalencia_ageb_2010_2020.parquet: por AGEB urbana 2020, la AGEB 2010 con
  mayor traslape y las fracciones de área compartidas (ver docs/metodologia.md §5).

Nunca sobrescribe un archivo existente en data/reference/ (CLAUDE.md, regla 3): si existe,
lo compara y avisa si difiere.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

RAIZ = Path(__file__).resolve().parents[1]
MG = RAIZ / "data" / "processed" / "marco_geo"
REFERENCIA = RAIZ / "data" / "reference"
INTERIM = RAIZ / "data" / "interim"
CRS_METRICO = "EPSG:6372"  # México ITRF2008 LCC (el del marco 2020), para áreas
BBOX_CDMX = (-99.37, 19.04, -98.94, 19.60)
SIMPLIFICACION = "25%"  # porcentaje de vértices que conserva mapshaper


def cargar_2020() -> gpd.GeoDataFrame:
    urb = gpd.read_file(MG / "mg2020" / "09a.shp")[["CVEGEO", "CVE_MUN", "geometry"]].assign(ambito="urbano")
    rur = gpd.read_file(MG / "mg2020" / "09ar.shp")[["CVEGEO", "CVE_MUN", "geometry"]].assign(ambito="rural")
    g = pd.concat([urb, rur], ignore_index=True).rename(columns={"CVEGEO": "cvegeo", "CVE_MUN": "cve_mun"})
    g = gpd.GeoDataFrame(g, geometry="geometry", crs=urb.crs)
    g["geometry"] = shapely.make_valid(g.geometry.values)
    if g["cvegeo"].duplicated().any():
        raise ValueError("CVEGEO duplicado en el marco 2020")
    return g


def escribir_nuevo(g: gpd.GeoDataFrame, destino: Path) -> None:
    """Escribe a un temporal y solo lo mueve si el destino no existe."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_ruta = Path(tmp) / destino.name
        g.to_file(tmp_ruta, driver="GeoJSON", COORDINATE_PRECISION=6)
        instalar(tmp_ruta, destino)


def instalar(origen: Path, destino: Path) -> None:
    if destino.exists():
        iguales = hashlib.sha256(origen.read_bytes()).digest() == hashlib.sha256(destino.read_bytes()).digest()
        print(f"{destino.name}: ya existe, no se sobrescribe ({'idéntico' if iguales else 'DIFIERE: revisar'})")
        return
    shutil.copyfile(origen, destino)
    print(f"{destino.relative_to(RAIZ)}: {destino.stat().st_size / 1e6:.2f} MB")


def simplificar(completo: Path, destino: Path, g4326: gpd.GeoDataFrame) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        salida = Path(tmp) / destino.name
        cmd = [
            "npx", "-y", "mapshaper@0.6", str(completo),
            "-simplify", SIMPLIFICACION, "keep-shapes",
            "-o", "format=geojson", "precision=0.00001", str(salida),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=600)
            metodo = f"mapshaper {SIMPLIFICACION} keep-shapes"
        except (subprocess.SubprocessError, FileNotFoundError):
            # respaldo: simplificación de cobertura (preserva bordes compartidos), ~5 m en grados
            gs = g4326.copy()
            gs["geometry"] = shapely.coverage_simplify(gs.geometry.values, tolerance=0.00005)
            gs.to_file(salida, driver="GeoJSON", COORDINATE_PRECISION=5)
            metodo = "shapely.coverage_simplify 0.00005°"
        print(f"simplificación: {metodo}")
        instalar(salida, destino)


def equivalencia(g2020: gpd.GeoDataFrame) -> pd.DataFrame:
    a20 = g2020[g2020["ambito"] == "urbano"][["cvegeo", "geometry"]].to_crs(CRS_METRICO)
    a10 = gpd.read_file(MG / "mg2010v5" / "ageb_urbana_2010_09.gpkg")[["CVEGEO", "geometry"]]
    a10 = a10.rename(columns={"CVEGEO": "cvegeo_2010"}).to_crs(CRS_METRICO)
    a10["geometry"] = shapely.make_valid(a10.geometry.values)
    a20["area_2020"] = a20.area
    a10["area_2010"] = a10.area
    inter = gpd.overlay(a20, a10, how="intersection", keep_geom_type=True)
    inter["area_inter"] = inter.area
    inter["frac_de_2020"] = inter["area_inter"] / inter["area_2020"]
    inter["frac_de_2010"] = inter["area_inter"] / inter["area_2010"]
    mejor = inter.sort_values("area_inter", ascending=False).drop_duplicates("cvegeo")
    eq = a20[["cvegeo"]].merge(mejor[["cvegeo", "cvegeo_2010", "frac_de_2020", "frac_de_2010"]], on="cvegeo", how="left")
    # hijas 2020 por AGEB 2010 (para distinguir división de cambio de límites)
    hijas = inter[inter["frac_de_2020"] >= 0.5].groupby("cvegeo_2010")["cvegeo"].nunique()
    eq["hijas_de_2010"] = eq["cvegeo_2010"].map(hijas)

    def clase(r) -> str:
        if pd.isna(r.cvegeo_2010):
            return "sin_contraparte"
        if r.frac_de_2020 >= 0.95 and r.frac_de_2010 >= 0.95:
            return "misma" if r.cvegeo == r.cvegeo_2010 else "misma_otra_clave"
        if r.frac_de_2020 >= 0.95 and r.hijas_de_2010 > 1:
            return "division"
        if r.frac_de_2010 >= 0.95:
            return "fusion_o_expansion"
        return "cambio_limites"

    eq["relacion"] = eq.apply(clase, axis=1)
    return eq


def main() -> None:
    g = cargar_2020()
    g4326 = g.to_crs("EPSG:4326")
    xmin, ymin, xmax, ymax = g4326.total_bounds
    if not (xmin >= BBOX_CDMX[0] and ymin >= BBOX_CDMX[1] and xmax <= BBOX_CDMX[2] and ymax <= BBOX_CDMX[3]):
        raise ValueError(f"bbox fuera de la CDMX: {g4326.total_bounds}")
    if not g4326.is_valid.all():
        raise ValueError("geometrías inválidas tras make_valid")
    completo = REFERENCIA / "ageb_cdmx.geojson"
    escribir_nuevo(g4326, completo)
    simplificar(completo, REFERENCIA / "ageb_cdmx_simplificado.geojson", g4326)
    eq = equivalencia(g)
    INTERIM.mkdir(parents=True, exist_ok=True)
    eq.to_parquet(INTERIM / "equivalencia_ageb_2010_2020.parquet", index=False)
    print("equivalencia 2010↔2020:", eq["relacion"].value_counts().to_dict())


if __name__ == "__main__":
    main()
