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
_DIR_SALUD = DIR_PROCESSED / "salud"
_DIR_COMERCIOS = DIR_PROCESSED / "comercios"
_DIR_AREAS_VERDES = DIR_PROCESSED / "areas_verdes"
_DIR_ESPACIOS_PUBLICOS = DIR_PROCESSED / "espacios_publicos"

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

# Salud (Fase 5, rama "salud"): mismo esquema base que infancias, más 4
# columnas booleanas que ya clasifican el establecimiento -- más directo y
# confiable que reclasificar por SCIAN (51 códigos distintos en salud) y
# coincide 1:1 con las celdas de filtro de
# `correccion/frontend_requisitos.md` §10.2 (clínicas/hospitales/salud
# mental/farmacias).
_COLUMNAS_DENUE_SALUD: dict[str, str] = {
    **_COLUMNAS_DENUE,
    "Es hospital": "es_hospital",
    "Es clínica o consultorio": "es_clinica",
    "Es salud mental o psicológica": "es_salud_mental",
    "Es farmacia": "es_farmacia",
}


def _ruta_denue_infancias(edicion: str) -> Path:
    """Ruta del CSV de infancias para una edición (p. ej. `"2016-10"`)."""
    return _DIR_INFANCIAS / f"denue_infancias_cdmx_{edicion.replace('-', '_')}.csv"


def _ruta_denue_salud(edicion: str) -> Path:
    return _DIR_SALUD / f"denue_salud_cdmx_{edicion.replace('-', '_')}.csv"


def _ruta_denue_comercios(edicion: str) -> Path:
    return _DIR_COMERCIOS / f"denue_comercios_cdmx_{edicion.replace('-', '_')}_depurado.geojson"


def _leer_denue_csv(
    con: duckdb.DuckDBPyConnection,
    ediciones: Iterable[str],
    ruta_por_edicion,
    columnas: dict[str, str],
    tipos_cast: dict[str, str],
    nombre_familia: str,
) -> pd.DataFrame:
    """Lector genérico de una familia DENUE en CSV (infancias/salud comparten esquema).

    `ruta_por_edicion`: función `edicion -> Path`. `columnas`: crudo ->
    snake_case (plan §3). Valida `id` único por edición (nunca deduplica en
    silencio) y añade `cve_mun` (de `cvegeo`) y `t` (fecha de levantamiento,
    `CORTES_OFERTA.get(edicion)`, `NaN` si la edición no es uno de los 3
    cortes de oferta).
    """
    columnas_sql = ", ".join(
        f'CAST("{crudo}" AS {tipos_cast[normal]}) AS {normal}'
        if normal in tipos_cast
        else f'"{crudo}" AS {normal}'
        for crudo, normal in columnas.items()
    )
    marcos: list[pd.DataFrame] = []
    for edicion in ediciones:
        ruta = ruta_por_edicion(edicion)
        _requiere_archivo(
            ruta, sugerencia=f"verifica data/processed/{nombre_familia}/ (solo lectura)"
        )
        consulta = f"""
            SELECT {columnas_sql}
            FROM read_csv('{ruta.as_posix()}', all_varchar=true, header=true)
        """
        marco = con.sql(consulta).df()

        duplicados = marco["id"][marco["id"].duplicated()]
        if not duplicados.empty:
            raise ValueError(
                f"IDs duplicados en la edición {edicion} de DENUE {nombre_familia}: "
                f"{sorted(duplicados.unique().tolist())[:10]} "
                "(se esperaba 'id' único por edición; no se deduplica en silencio)."
            )

        marco["edicion"] = edicion
        marco["cve_mun"] = marco["cvegeo"].str.slice(2, 5)
        marco["t"] = CORTES_OFERTA.get(edicion, float("nan"))
        marcos.append(marco)

    # `cve_mun` se inserta justo después de `cvegeo` (no al final): agrupa las dos claves
    # geográficas, igual que el orden original de `leer_denue_infancias` antes de la Fase 5.
    nombres = list(columnas.values())
    idx_cvegeo = nombres.index("cvegeo")
    columnas_salida = nombres[: idx_cvegeo + 1] + ["cve_mun"] + nombres[idx_cvegeo + 1 :] + ["t"]
    if not marcos:
        return pd.DataFrame(columns=columnas_salida)
    return pd.concat(marcos, ignore_index=True)[columnas_salida]


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

    Columnas de salida: `id, cvegeo, alcance, sector, scian, subcategoria,
    edicion, cve_mun, t`. `t` es la fecha de levantamiento
    (`CORTES_OFERTA[edicion]`) o `NaN` si la edición no es un corte de
    oferta (uso diagnóstico, p. ej. con `EDICIONES_TODAS`).

    Tipos: `id` -> BIGINT, `scian` -> INTEGER (el resto queda `VARCHAR`,
    leído con `all_varchar=true` porque los tipos son inestables entre
    ediciones, ver CLAUDE.md problema M3).
    """
    return _leer_denue_csv(
        con,
        ediciones,
        _ruta_denue_infancias,
        _COLUMNAS_DENUE,
        {"id": "BIGINT", "scian": "INTEGER"},
        "infancias",
    )


def leer_denue_salud(con: duckdb.DuckDBPyConnection, ediciones: Iterable[str]) -> pd.DataFrame:
    """Lee y concatena ediciones de DENUE salud (Fase 5, rama "salud").

    Mismo esquema base que `leer_denue_infancias`, más 4 columnas booleanas
    (0/1) que ya clasifican el establecimiento: `es_hospital, es_clinica,
    es_salud_mental, es_farmacia` (ver `_COLUMNAS_DENUE_SALUD`).
    """
    tipos_cast = {
        "id": "BIGINT",
        "scian": "INTEGER",
        "es_hospital": "INTEGER",
        "es_clinica": "INTEGER",
        "es_salud_mental": "INTEGER",
        "es_farmacia": "INTEGER",
    }
    return _leer_denue_csv(
        con, ediciones, _ruta_denue_salud, _COLUMNAS_DENUE_SALUD, tipos_cast, "salud"
    )


# Comercios (Fase 5, rama "comercio"): GeoJSON, no CSV -- columnas ya en
# snake_case en el archivo depurado. `cve_geo_ageb` ya es la clave AGEB (13
# caracteres): no hace falta join espacial, a diferencia de verde (§ más abajo).
_COLUMNAS_COMERCIOS: dict[str, str] = {
    "id": "id",
    "cve_geo_ageb": "cvegeo",
    "alcance_analitico": "alcance",
    "categoria_proyecto": "categoria",
    "subcategoria_proyecto": "subcategoria",
    "es_primera_necesidad": "es_primera_necesidad",
}


def leer_denue_comercios(ediciones: Iterable[str]) -> pd.DataFrame:
    """Lee y concatena ediciones de DENUE comercios (GeoJSON, sin geometría -- Fase 5).

    Columnas de salida: `id, cvegeo, alcance, categoria, subcategoria,
    es_primera_necesidad, edicion, cve_mun, t`. `subcategoria` alimenta las
    celdas de filtro de `correccion/frontend_requisitos.md` §10.3
    (abarrotes, frutas y verduras, minisúper/supermercado, farmacias, otros
    alimentos). A diferencia de infancias/salud, aquí NO se filtra por
    `alcance = 'Principal'`: en comercios esa columna separa "las 3
    categorías más grandes" de "el resto", no relevancia (`categoria` /
    `es_primera_necesidad` ya acotan el universo a comercio de primera
    necesidad, metodología §1).
    """
    marcos: list[pd.DataFrame] = []
    for edicion in ediciones:
        ruta = _ruta_denue_comercios(edicion)
        _requiere_archivo(ruta, sugerencia="verifica data/processed/comercios/ (solo lectura)")
        marco = pyogrio.read_dataframe(
            ruta, read_geometry=False, columns=list(_COLUMNAS_COMERCIOS)
        ).rename(columns=_COLUMNAS_COMERCIOS)
        marco["id"] = marco["id"].astype("int64")

        duplicados = marco["id"][marco["id"].duplicated()]
        if not duplicados.empty:
            raise ValueError(
                f"IDs duplicados en la edición {edicion} de DENUE comercios: "
                f"{sorted(duplicados.unique().tolist())[:10]} "
                "(se esperaba 'id' único por edición; no se deduplica en silencio)."
            )

        marco["edicion"] = edicion
        marco["cve_mun"] = marco["cvegeo"].str.slice(2, 5)
        marco["t"] = CORTES_OFERTA.get(edicion, float("nan"))
        marcos.append(marco)

    columnas_salida = [
        "id",
        "cvegeo",
        "alcance",
        "categoria",
        "subcategoria",
        "es_primera_necesidad",
        "edicion",
        "cve_mun",
        "t",
    ]
    if not marcos:
        return pd.DataFrame(columns=columnas_salida)
    return pd.concat(marcos, ignore_index=True)[columnas_salida]


def leer_contexto_cdmx() -> pd.DataFrame:
    """Áreas verdes y espacio público por AGEB (Fase 5, rama "verde"; metodología §1.4/§10.1).

    Join espacial en WGS84 (`gpd.sjoin`, `predicate="within"`) del punto
    representativo (`representative_point()`, siempre dentro del polígono a
    diferencia del centroide en formas cóncavas) de cada área/espacio contra
    los polígonos de AGEB (`data/reference/ageb_cdmx.geojson`). Un solo
    corte (inventario estático, sin `t`): metodología §10.1, "si una rama
    solo tiene información actual, mostrar su situación actual y NO
    inventar una línea futura".

    Devuelve una fila por AGEB urbana con conteo y superficie (m²) por
    categoría de filtro (`correccion/frontend_requisitos.md` §10.4):
    `cvegeo, cve_mun, n_cobertura_verde, area_cobertura_verde_m2,
    n_areas_recreativas, area_areas_recreativas_m2, n_espacios_publicos,
    area_espacios_publicos_m2`. AGEB sin ninguna área/espacio: ceros
    explícitos (nunca ausencia de fila -- coherente con `construir_panel_oferta`).
    Un punto representativo fuera de toda AGEB (borde de la ciudad, ver
    `sjoin how="left"`) queda excluido de los agregados (no genera una fila
    "cvegeo=NaN"): `_agregar` agrupa por `cvegeo` antes del merge, así que
    esas filas sin AGEB simplemente no contribuyen a ningún grupo.
    """
    import geopandas as gpd

    ruta_verdes = _DIR_AREAS_VERDES / "inventario_areas_verdes_cdmx_depurado.geojson"
    ruta_publicos = _DIR_ESPACIOS_PUBLICOS / "espacio_publico_cdmx_depurado.geojson"
    _requiere_archivo(ruta_verdes, sugerencia="verifica data/processed/areas_verdes/ (solo lectura)")
    _requiere_archivo(
        ruta_publicos, sugerencia="verifica data/processed/espacios_publicos/ (solo lectura)"
    )
    _requiere_archivo(RUTA_AGEB_GEOJSON, sugerencia="tools/build_geo.py")

    ageb = gpd.read_file(RUTA_AGEB_GEOJSON, columns=["cvegeo", "cve_mun"]).to_crs(epsg=4326)

    def _puntos_dentro_de_ageb(ruta: Path, columnas: list[str]) -> pd.DataFrame:
        capa = gpd.read_file(ruta, columns=columnas).to_crs(epsg=4326)
        capa = capa.loc[capa.geometry.notna() & capa.geometry.is_valid].copy()
        capa["geometry"] = capa.geometry.representative_point()
        unido = gpd.sjoin(capa, ageb, how="left", predicate="within")
        return pd.DataFrame(unido.drop(columns=["geometry", "index_right"]))

    verdes = _puntos_dentro_de_ageb(
        ruta_verdes, ["id_area_verde", "usar_cobertura_verde", "usar_oferta_recreativa", "area_m2"]
    )
    publicos = _puntos_dentro_de_ageb(ruta_publicos, ["id_espacio_publico", "area_m2"])

    cobertura = verdes.loc[verdes["usar_cobertura_verde"]]
    recreativas = verdes.loc[verdes["usar_oferta_recreativa"]]

    universo = ageb[["cvegeo", "cve_mun"]].copy()

    def _agregar(tabla: pd.DataFrame, prefijo: str) -> pd.DataFrame:
        agregado = (
            tabla.groupby("cvegeo")
            .agg(**{f"n_{prefijo}": ("area_m2", "size"), f"area_{prefijo}_m2": ("area_m2", "sum")})
            .reset_index()
        )
        return agregado

    resultado = universo
    for tabla, prefijo in (
        (cobertura, "cobertura_verde"),
        (recreativas, "areas_recreativas"),
        (publicos, "espacios_publicos"),
    ):
        resultado = resultado.merge(_agregar(tabla, prefijo), on="cvegeo", how="left")

    columnas_conteo = ["n_cobertura_verde", "n_areas_recreativas", "n_espacios_publicos"]
    columnas_area = [
        "area_cobertura_verde_m2",
        "area_areas_recreativas_m2",
        "area_espacios_publicos_m2",
    ]
    for col in columnas_conteo:
        resultado[col] = resultado[col].fillna(0).astype(int)
    for col in columnas_area:
        resultado[col] = resultado[col].fillna(0.0).round(1)

    return resultado.sort_values("cvegeo").reset_index(drop=True)


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
