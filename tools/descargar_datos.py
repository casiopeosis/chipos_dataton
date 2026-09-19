"""Descarga fuentes oficiales y extrae a data/processed/ solo lo de la CDMX.

- Originales (zip/csv) → data/interim/descargas/ (ignorado por git), con sha256.
- Extraídos → data/processed/{censo,conapo,marco_geo}/. Nunca sobrescribe: si el
  destino ya existe, lo deja intacto (CLAUDE.md, regla 3).
- Escribe data/interim/descargas/registro.json (URL, fecha, bytes, sha256) que se
  transcribe a docs/data_manifest.md.

Uso: python tools/descargar_datos.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESCARGAS = RAIZ / "data" / "interim" / "descargas"
PROCESADOS = RAIZ / "data" / "processed"

INEGI_MG = "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia"
FUENTES = {
    "resageburb_09_2010_csv.zip": "https://www.inegi.org.mx/contenidos/programas/ccpv/2010/datosabiertos/ageb_y_manzana/resageburb_09_2010_csv.zip",
    "ageb_mza_urbana_09_cpv2020_csv.zip": "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_09_cpv2020_csv.zip",
    # Marco Geoestadístico, Censo de Población y Vivienda 2020 (UPC 889463807469), entidad 09
    "mg2020_09_ciudaddemexico.zip": f"{INEGI_MG}/marcogeo/889463807469/09_ciudaddemexico.zip",
    # Marco Geoestadístico 2010 v5.0, Censo 2010 (UPC 702825292812), solo existe nacional
    "mg2010v5_nacional.zip": f"{INEGI_MG}/marc_geo/702825292812_s.zip",
    # CONAPO, población a mitad de año por municipio y grupo quinquenal 1990-2040 (datos.gob.mx)
    "pobproy_quinq1.csv": "https://www.datos.gob.mx/dataset/f2b9b220-3ef7-4e3a-bde6-87e1dac78c6a/resource/3c3092be-583e-4490-8c23-67ef9a64b198/download/pobproy_quinq1.csv",
}


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(nombre: str, url: str) -> Path:
    destino = DESCARGAS / nombre
    if not destino.exists():
        subprocess.run(
            ["curl", "-sSL", "--retry", "5", "-A", "Mozilla/5.0", "-o", str(destino), url], check=True
        )
    if destino.suffix == ".zip":
        with zipfile.ZipFile(destino) as z:
            if z.testzip() is not None:
                raise RuntimeError(f"{nombre}: zip corrupto")
    return destino


def extraer(zip_ruta: Path, miembros: dict[str, Path]) -> None:
    """Copia miembros del zip a su destino sin sobrescribir."""
    with zipfile.ZipFile(zip_ruta) as z:
        for miembro, destino in miembros.items():
            if destino.exists():
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            with z.open(miembro) as src, open(destino, "wb") as dst:
                shutil.copyfileobj(src, dst)


def extraer_mg2010(zip_nacional: Path) -> None:
    """El marco 2010 v5.0 solo es nacional: se filtra la CDMX (CVEGEO/CVE_ENT = 09) a GeoPackage."""
    import geopandas as gpd

    tmp = DESCARGAS / "mg2010v5"
    capas = {
        "mgau2010v5_0.zip": ("AGEB_urb_2010_5.shp", "ageb_urbana_2010_09.gpkg", lambda g: g["CVEGEO"].str[:2] == "09"),
        "mgm2010v5_0.zip": ("Municipios_2010_5.shp", "municipios_2010_09.gpkg", lambda g: g["CVE_ENT"] == "09"),
    }
    with zipfile.ZipFile(zip_nacional) as z:
        z.extractall(tmp)
    for interno, (shp, salida, filtro) in capas.items():
        destino = PROCESADOS / "marco_geo" / "mg2010v5" / salida
        if destino.exists():
            continue
        with zipfile.ZipFile(tmp / interno) as z:
            z.extractall(tmp)
        g = gpd.read_file(tmp / shp)
        g = g[filtro(g)]
        destino.parent.mkdir(parents=True, exist_ok=True)
        g.to_file(destino, driver="GPKG")  # CRS original (LCC ITRF92), sin reproyectar


def main() -> None:
    DESCARGAS.mkdir(parents=True, exist_ok=True)
    registro = {}
    for nombre, url in FUENTES.items():
        ruta = descargar(nombre, url)
        registro[nombre] = {
            "url": url,
            "fecha": dt.datetime.fromtimestamp(ruta.stat().st_mtime).date().isoformat(),
            "bytes": ruta.stat().st_size,
            "sha256": sha256(ruta),
        }
        print(f"{nombre}: {ruta.stat().st_size / 1e6:.1f} MB")

    censo = PROCESADOS / "censo"
    base10 = "resultados_ageb_urbana_09_cpv2010"
    extraer(DESCARGAS / "resageburb_09_2010_csv.zip", {
        f"{base10}/conjunto_de_datos/resultados_ageb_urbana_09_cpv2010.csv": censo / "inegi_2010" / "resultados_ageb_urbana_09_cpv2010.csv",
        f"{base10}/diccionario_de_datos/fd_resultados_ageb_urbana_cpv2010.csv": censo / "inegi_2010" / "fd_resultados_ageb_urbana_cpv2010.csv",
        f"{base10}/metadatos/metadatos_resultados_ageb_urbana_cpv2010.txt": censo / "inegi_2010" / "metadatos_resultados_ageb_urbana_cpv2010.txt",
    })
    base20 = "ageb_mza_urbana_09_cpv2020"
    extraer(DESCARGAS / "ageb_mza_urbana_09_cpv2020_csv.zip", {
        f"{base20}/conjunto_de_datos/conjunto_de_datos_ageb_urbana_09_cpv2020.csv": censo / "inegi_2020" / "conjunto_de_datos_ageb_urbana_09_cpv2020.csv",
        f"{base20}/diccionario_de_datos/diccionario_datos_ageb_urbana_09_cpv2020.csv": censo / "inegi_2020" / "diccionario_datos_ageb_urbana_09_cpv2020.csv",
        f"{base20}/metadatos/metadatos_ageb_urbana_09_cpv2020.txt": censo / "inegi_2020" / "metadatos_ageb_urbana_09_cpv2020.txt",
    })
    mg20 = PROCESADOS / "marco_geo" / "mg2020"
    miembros = {
        f"conjunto_de_datos/{capa}.{ext}": mg20 / f"{capa}.{ext}"
        for capa in ("09a", "09ar", "09mun")
        for ext in ("shp", "shx", "dbf", "prj", "cpg")
    }
    miembros["metadatos/mg_cpyv2020_09.txt"] = mg20 / "mg_cpyv2020_09.txt"
    extraer(DESCARGAS / "mg2020_09_ciudaddemexico.zip", miembros)
    extraer_mg2010(DESCARGAS / "mg2010v5_nacional.zip")

    conapo = PROCESADOS / "conapo" / "pobproy_quinq1.csv"
    if not conapo.exists():
        conapo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DESCARGAS / "pobproy_quinq1.csv", conapo)

    (DESCARGAS / "registro.json").write_text(json.dumps(registro, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
