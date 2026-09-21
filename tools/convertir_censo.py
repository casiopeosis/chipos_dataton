"""Convierte data/processed/censo/AGEB_2010_2020.xlsx a parquet en data/interim/.

Salida: data/interim/censo_xlsx_ageb_2010.parquet y censo_xlsx_ageb_2020.parquet (solo para contraste con
el censo oficial; el xlsx 2010 está truncado y queda superseded por tools/build_censo.py) con
`cvegeo` (13 caracteres = '09' + CVE_MUN + CVE_LOC + CVE_AGEB), `cve_mun`, `anio`
y los conteos por grupo de edad como enteros. Las celdas suprimidas por INEGI
(confidencialidad, en blanco en el xlsx) quedan como NULL: no se imputan.

Uso: python tools/convertir_censo.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "data" / "processed" / "censo" / "AGEB_2010_2020.xlsx"
DESTINO = RAIZ / "data" / "interim"

COLUMNAS = {
    "Municipio (clave)": "cve_mun",
    "Municipio": "municipio",
    "Localidad (clave)": "cve_loc",
    "Localidad": "localidad",
    "AGEB": "cve_ageb",
    "Población total": "pob_total",
    "0-2 años": "p_0a2",
    "3-5 años": "p_3a5",
    "6-11 años": "p_6a11",
    "12-14 años": "p_12a14",
    "15-17 años": "p_15a17",
    "18-24 años": "p_18a24",
    "18+ años": "p_18ymas",
}
CONTEOS = [v for v in COLUMNAS.values() if v.startswith("p")]


def convertir(hoja: str, anio: int) -> pd.DataFrame:
    df = pd.read_excel(ORIGEN, sheet_name=hoja, dtype=str).rename(columns=COLUMNAS)
    faltan = set(COLUMNAS.values()) - set(df.columns)
    if faltan:
        raise ValueError(f"{hoja}: faltan columnas {sorted(faltan)}")
    for col in CONTEOS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["cvegeo"] = "09" + df["cve_mun"] + df["cve_loc"] + df["cve_ageb"]
    if df["cvegeo"].str.len().ne(13).any() or df["cvegeo"].duplicated().any():
        raise ValueError(f"{hoja}: clave CVEGEO inválida o duplicada")
    df["anio"] = anio
    return df[["cvegeo", "anio", *COLUMNAS.values()]]


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for hoja, anio in (("AGEB 2010", 2010), ("AGEB 2020", 2020)):
        df = convertir(hoja, anio)
        salida = DESTINO / f"censo_xlsx_ageb_{anio}.parquet"
        df.to_parquet(salida, index=False)
        print(f"{salida.relative_to(RAIZ)}: {len(df)} AGEB")


if __name__ == "__main__":
    main()
