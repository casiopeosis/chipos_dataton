"""Capa de lectura (plan `backend_plan.md` §3).

Reglas duras que este módulo respeta:
- Una conexión DuckDB en memoria por ejecución (`conectar()`), reutilizable
  por quien orqueste el pipeline (`exportar.main()`).
- Proyección de columnas explícita: nunca `SELECT *` ni `pd.read_parquet`
  sin `columns=`.
- DENUE se lee con `read_csv(..., all_varchar=true)` y casteo explícito
  (tipos inestables entre ediciones, ver CLAUDE.md / problema M3).
- `data/processed/` y `data/reference/` son de solo lectura: este módulo
  nunca escribe ahí.
- Si falta un derivado de `data/interim/`, se lanza un error claro pidiendo
  `make datos` (nunca se regenera desde aquí).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import duckdb
import pandas as pd
import pyogrio

from chipos.config import (
    DIR_PROCESSED,
    RUTA_AGEB_GEOJSON,
    RUTA_CENSO_PANEL,
    RUTA_CONAPO_MUN_0A14,
    RUTA_EQUIVALENCIA_AGEB,
)

# ---------------------------------------------------------------------------
# Cortes de oferta (plan §3): edición DENUE -> fecha de levantamiento (años
# decimales). Solo estos 3 cortes se usan como observaciones de oferta
# (problema "Importante" del plan §1: los 11 cortes no son independientes).
# ---------------------------------------------------------------------------
CORTES_OFERTA: dict[str, float] = {
    "2016-10": 2016.79,
    "2019-11": 2019.87,
    "2024-11": 2024.87,
}

# Las 11 ediciones disponibles en `data/processed/infancias/` y `salud/`,
# para diagnóstico (p. ej. verificación de códigos SCIAN, B4).
EDICIONES_TODAS: tuple[str, ...] = (
    "2016-10",
    "2017-11",
    "2018-11",
    "2019-11",
    "2020-11",
    "2021-11",
    "2022-11",
    "2023-11",
    "2024-11",
    "2025-05",
    "2026-05",
)

_DIR_INFANCIAS = DIR_PROCESSED / "infancias"

# Columnas leídas del CSV crudo (plan §3) y su nombre normalizado a
# snake_case. El orden importa: fija el orden del SELECT.
_COLUMNAS_DENUE: dict[str, str] = {
    "ID": "id",
    "Clave geográfica AGEB": "cvegeo",
    "Alcance": "alcance",
    "Sector": "sector",
    "Código SCIAN": "scian",
    "Subcategoría": "subcategoria",
    "Edición DENUE": "edicion",
}


def _ruta_denue_infancias(edicion: str) -> Path:
    """Ruta del CSV de infancias para una edición (p. ej. `"2016-10"`)."""
    return _DIR_INFANCIAS / f"denue_infancias_cdmx_{edicion.replace('-', '_')}.csv"


def _requiere_archivo(ruta: Path, *, sugerencia: str = "make datos") -> None:
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta}. Ejecuta `{sugerencia}` antes de usar `chipos.io`."
        )


def conectar() -> duckdb.DuckDBPyConnection:
    """Abre una conexión DuckDB en memoria (una por ejecución del pipeline)."""
    return duckdb.connect(database=":memory:")


def leer_denue_infancias(
    con: duckdb.DuckDBPyConnection, ediciones: Iterable[str]
) -> pd.DataFrame:
    """Lee y concatena ediciones de DENUE infancias.

    Columnas de salida: `id, cvegeo, cve_mun, alcance, sector, scian,
    subcategoria, edicion, t`. `t` es la fecha de levantamiento
    (`CORTES_OFERTA[edicion]`) o `NaN` si la edición no es un corte de
    oferta (uso diagnóstico, p. ej. con `EDICIONES_TODAS`).

    Tipos: `id` -> BIGINT, `scian` -> INTEGER (el resto queda `VARCHAR`,
    leído con `all_varchar=true` porque los tipos son inestables entre
    ediciones, ver CLAUDE.md problema M3).
    """
    tipos_cast = {"id": "BIGINT", "scian": "INTEGER"}
    columnas_sql = ", ".join(
        f'CAST("{crudo}" AS {tipos_cast[normal]}) AS {normal}'
        if normal in tipos_cast
        else f'"{crudo}" AS {normal}'
        for crudo, normal in _COLUMNAS_DENUE.items()
    )

    marcos: list[pd.DataFrame] = []
    for edicion in ediciones:
        ruta = _ruta_denue_infancias(edicion)
        _requiere_archivo(
            ruta,
            sugerencia="verifica data/processed/infancias/ (solo lectura)",
        )
        consulta = f"""
            SELECT {columnas_sql}
            FROM read_csv('{ruta.as_posix()}', all_varchar=true, header=true)
        """
        marco = con.sql(consulta).df()

        duplicados = marco["id"][marco["id"].duplicated()]
        if not duplicados.empty:
            raise ValueError(
                f"IDs duplicados en la edición {edicion} de DENUE infancias: "
                f"{sorted(duplicados.unique().tolist())[:10]} "
                "(se esperaba `id` único por edición; no se deduplica en silencio)."
            )

        marco["edicion"] = edicion
        marco["cve_mun"] = marco["cvegeo"].str.slice(2, 5)
        marco["t"] = CORTES_OFERTA.get(edicion, float("nan"))
        marcos.append(marco)

    columnas_salida = [
        "id",
        "cvegeo",
        "cve_mun",
        "alcance",
        "sector",
        "scian",
        "subcategoria",
        "edicion",
        "t",
    ]
    if not marcos:
        return pd.DataFrame(columns=columnas_salida)
    return pd.concat(marcos, ignore_index=True)[columnas_salida]


def leer_censo_panel() -> pd.DataFrame:
    """Lee `data/interim/censo_ageb_panel.parquet` (ya limpio, ver `tools/build_censo.py`).

    Columnas: `cvegeo, anio, t, cve_mun, pob_0a14, p_0a2, p_3a5, p_6a11,
    p_12a14, p_15a17` (las cinco últimas, Fase 4: segmentos de población
    objetivo, `panel.COLUMNAS_SEGMENTO`; ya están en el parquet, no son una
    fuente nueva).
    """
    _requiere_archivo(RUTA_CENSO_PANEL)
    marco = pd.read_parquet(
        RUTA_CENSO_PANEL,
        columns=[
            "cvegeo",
            "anio",
            "t",
            "cve_mun",
            "pob_0a14",
            "p_0a2",
            "p_3a5",
            "p_6a11",
            "p_12a14",
            "p_15a17",
        ],
    )
    # `t` llega como DECIMAL de Parquet (objetos `Decimal`); se castea a
    # float64 para aritmética de tiempo real en años decimales (plan §5).
    marco["t"] = marco["t"].astype("float64")
    return marco


def leer_conapo_0a14() -> pd.DataFrame:
    """Lee `data/interim/conapo_mun_0a14.parquet`.

    Columnas: `cve_mun, anio, pob_0a14`.
    """
    _requiere_archivo(RUTA_CONAPO_MUN_0A14)
    return pd.read_parquet(
        RUTA_CONAPO_MUN_0A14, columns=["cve_mun", "anio", "pob_0a14"]
    )


def leer_equivalencia() -> pd.DataFrame:
    """Lee `data/interim/equivalencia_ageb_2010_2020.parquet`.

    Columnas: `cvegeo, cvegeo_2010, frac_de_2020, frac_de_2010,
    hijas_de_2010, relacion`.
    """
    _requiere_archivo(RUTA_EQUIVALENCIA_AGEB)
    return pd.read_parquet(
        RUTA_EQUIVALENCIA_AGEB,
        columns=[
            "cvegeo",
            "cvegeo_2010",
            "frac_de_2020",
            "frac_de_2010",
            "hijas_de_2010",
            "relacion",
        ],
    )


def leer_universo_ageb() -> pd.DataFrame:
    """Universo de las 2,453 AGEB de `data/reference/ageb_cdmx.geojson`.

    Solo propiedades (`cvegeo, cve_mun, ambito`), nunca geometría (economía
    de tokens/memoria, CLAUDE.md).
    """
    _requiere_archivo(
        RUTA_AGEB_GEOJSON, sugerencia="tools/build_geo.py (data/reference/ es de solo lectura)"
    )
    return pyogrio.read_dataframe(
        RUTA_AGEB_GEOJSON,
        read_geometry=False,
        columns=["cvegeo", "cve_mun", "ambito"],
    )
