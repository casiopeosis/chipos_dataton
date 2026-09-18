"""Lector de la familia `comercios` / DENUE genérico (Gen B / Comercios, CLAUDE.md §2).

Carpetas `data/COMERCIOS_YYYY_MM/` (11 ediciones, 2016-10 .. 2026-05). Cada una
trae `<nombre>_depurado.csv` ya filtrado a comercio de primera necesidad, más
`resumen_calidad.json` (linaje de edición) y `diccionario_campos_depurados.csv`.

Esta familia NO es uno de los 3 dominios del semáforo (CLAUDE.md §2) — es dato
transversal de contexto de oferta comercial. Se escribe con `dominio="comercio_abasto"`
fijo.

Solo alcaldía (CLAUDE.md §3): no se leen `ageb`, `cve_geo_ageb`, `manzana`,
`localidad`. La alcaldía se resuelve desde `cve_mun` (código INEGI de 3 dígitos)
vía `etl.catalogo.normalizar_alcaldia(valor, tipo="clave")`.

Mapeo de columnas reales (verificado con `head -1` sobre 2016 y 2025, y
`diccionario_campos_depurados.csv`) al esquema largo común:

    clee                    -> clee (ausente en 2016-2020; pd.NA)
    codigo_act              -> scian
    categoria_proyecto      -> sector       ("Primera necesidad" / "Complementario")
    subcategoria_proyecto   -> subcategoria (ej. "Abarrotes, ultramarinos y misceláneas")
    alcance_analitico       -> alcance      ("Principal" / "Complementario")
    revision_manual         -> revision_manual (bool; SI/NO -> True/False)
    cve_mun                 -> cve_alc (normalizado)

No existe una columna equivalente a "sector_gestion" (u otro nombre) en esta
familia; si algún día se agrega, debe mapearse explícitamente aquí en vez de
inventarse un valor.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pandas as pd

_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR.parent.parent))  # para `python archivo.py` directo

from etl.catalogo import CLAVES_VALIDAS, normalizar_alcaldia  # noqa: E402
from etl.ediciones import resolver_edicion_confiable  # noqa: E402

FAMILIA = "comercios"
DOMINIO_FIJO = "comercio_abasto"

_COLUMNAS_ORIGEN = [
    "clee",
    "codigo_act",
    "cve_mun",
    "categoria_proyecto",
    "subcategoria_proyecto",
    "alcance_analitico",
    "revision_manual",
]

_COLUMNAS_SALIDA = [
    "familia",
    "edicion",
    "edicion_verificada",
    "cve_alc",
    "clee",
    "scian",
    "dominio",
    "subcategoria",
    "sector",
    "alcance",
    "revision_manual",
]


def _mapear_revision_manual(serie: pd.Series) -> pd.Series:
    mapa = {"SI": True, "SÍ": True, "NO": False}
    return serie.map(lambda v: mapa.get(str(v).strip().upper()) if pd.notna(v) else pd.NA)


def _leer_una_carpeta(carpeta: Path) -> pd.DataFrame:
    nombre_carpeta = carpeta.name
    resumen = json.loads((carpeta / "resumen_calidad.json").read_text(encoding="utf-8"))
    fuente = resumen.get("fuente", {})

    edicion = resolver_edicion_confiable(fuente, nombre_carpeta)
    if not edicion.verificada:
        warnings.warn(
            f"[comercios] {nombre_carpeta}: edición no verificada ({edicion.edicion}, "
            f"procedencia={edicion.procedencia})"
        )

    csvs = list(carpeta.glob("*_depurado.csv"))
    if len(csvs) != 1:
        raise ValueError(f"[comercios] {nombre_carpeta}: se esperaba exactamente 1 *_depurado.csv, hay {len(csvs)}")
    ruta_csv = csvs[0]

    # Los nombres de columna originales de DENUE (a diferencia de las columnas
    # derivadas como categoria_proyecto) varían en mayúsculas/minúsculas entre
    # ediciones (ej. COMERCIOS_2019_11 trae CODIGO_ACT/CVE_MUN en mayúsculas,
    # el resto en minúsculas). Se matchea sin distinguir mayúsculas.
    header = pd.read_csv(ruta_csv, nrows=0).columns.tolist()
    header_lower_a_real = {c.lower(): c for c in header}
    columnas_faltantes = [c for c in _COLUMNAS_ORIGEN if c not in header_lower_a_real]
    columnas_presentes_reales = [header_lower_a_real[c] for c in _COLUMNAS_ORIGEN if c in header_lower_a_real]
    if columnas_faltantes:
        warnings.warn(
            f"[comercios] {nombre_carpeta}: columnas esperadas ausentes en el CSV: {columnas_faltantes} "
            f"(se rellenan con NA)"
        )

    dtype_map = {header_lower_a_real["clee"]: "string"} if "clee" in header_lower_a_real else None
    df = pd.read_csv(ruta_csv, usecols=columnas_presentes_reales, dtype=dtype_map)
    df = df.rename(columns={real: canon for canon, real in header_lower_a_real.items() if real in df.columns})

    for col in columnas_faltantes:
        df[col] = pd.NA

    # Alcaldía: cve_mun (clave INEGI 3 dígitos) -> cve_alc; nunca ageb/manzana.
    filas_totales = len(df)
    cve_alc = []
    n_no_reconocidas = 0
    for valor in df["cve_mun"]:
        try:
            cve_alc.append(normalizar_alcaldia(valor, tipo="clave"))
        except ValueError:
            cve_alc.append(pd.NA)
            n_no_reconocidas += 1
    if n_no_reconocidas:
        warnings.warn(
            f"[comercios] {nombre_carpeta}: {n_no_reconocidas}/{filas_totales} filas con cve_mun "
            f"fuera de las 16 alcaldías válidas (se conservan con cve_alc=NA, no se descartan silenciosamente)"
        )

    salida = pd.DataFrame(
        {
            "familia": FAMILIA,
            "edicion": edicion.edicion,
            "edicion_verificada": edicion.verificada,
            "cve_alc": cve_alc,
            "clee": df["clee"] if "clee" in df.columns else pd.NA,
            "scian": df["codigo_act"],
            "dominio": DOMINIO_FIJO,
            "subcategoria": df["subcategoria_proyecto"],
            "sector": df["categoria_proyecto"],
            "alcance": df["alcance_analitico"],
            "revision_manual": _mapear_revision_manual(df["revision_manual"]),
        }
    )

    # Chequeo cruzado contra resumen_calidad.json -> depuracion.registros_conservados
    conservados = resumen.get("depuracion", {}).get("registros_conservados")
    if conservados is not None and abs(len(salida) - conservados) > 0:
        warnings.warn(
            f"[comercios] {nombre_carpeta}: filas leídas ({len(salida)}) != "
            f"depuracion.registros_conservados ({conservados})"
        )

    return salida[_COLUMNAS_SALIDA]


def leer_todas(data_dir: Path) -> pd.DataFrame:
    """Recorre las 11 carpetas `COMERCIOS_*` bajo `data_dir` y devuelve el
    esquema largo común. No lanza si una carpeta individual falla de forma
    "blanda" (warnings); sí propaga ValueError de linaje/edición (regla dura,
    CLAUDE.md §1.1 / docs/architecture-plan.md).
    """
    data_dir = Path(data_dir)
    carpetas = sorted(p for p in data_dir.glob("COMERCIOS_*") if p.is_dir())
    if not carpetas:
        raise ValueError(f"[comercios] no se encontraron carpetas COMERCIOS_* en {data_dir}")

    marcos = [_leer_una_carpeta(carpeta) for carpeta in carpetas]
    resultado = pd.concat(marcos, ignore_index=True)

    ediciones_distintas = resultado["edicion"].nunique()
    if ediciones_distintas != len(carpetas):
        warnings.warn(
            f"[comercios] se esperaban {len(carpetas)} ediciones distintas, se obtuvieron {ediciones_distintas}"
        )

    claves_invalidas = resultado.loc[~resultado["cve_alc"].isin(CLAVES_VALIDAS) & resultado["cve_alc"].notna()]
    if not claves_invalidas.empty:
        warnings.warn(f"[comercios] {len(claves_invalidas)} filas con cve_alc fuera del catálogo tras normalizar")

    return resultado


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent.parent.parent
    df = leer_todas(raiz / "data")
    salida = raiz / "data" / "processed" / "comercios.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False)
    print(f"Escrito {len(df)} filas en {salida}")
