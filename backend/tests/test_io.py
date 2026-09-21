"""Tests de la capa de lectura `chipos.io` (plan `backend_plan.md` §3, tarea B2).

Los tests marcados `@pytest.mark.datos` leen `data/processed/` y
`data/interim/` reales (solo lectura); se saltan automáticamente si falta
`data/interim/` (ver `conftest.py`). El resto usa archivos temporales para
verificar el manejo de errores sin depender de datos reales.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from chipos import io


# ---------------------------------------------------------------------------
# Constantes del módulo
# ---------------------------------------------------------------------------


def test_cortes_oferta_tiene_los_3_cortes_documentados() -> None:
    assert io.CORTES_OFERTA == {
        "2016-10": 2016.79,
        "2019-11": 2019.87,
        "2024-11": 2024.87,
    }


def test_ediciones_todas_incluye_los_cortes_de_oferta() -> None:
    assert set(io.CORTES_OFERTA) <= set(io.EDICIONES_TODAS)
    assert len(io.EDICIONES_TODAS) == 11


# ---------------------------------------------------------------------------
# conectar()
# ---------------------------------------------------------------------------


def test_conectar_devuelve_conexion_duckdb_en_memoria() -> None:
    con = io.conectar()
    try:
        assert isinstance(con, duckdb.DuckDBPyConnection)
        assert con.sql("SELECT 1 AS uno").df()["uno"].iloc[0] == 1
    finally:
        con.close()


# ---------------------------------------------------------------------------
# leer_denue_infancias: con datos reales
# ---------------------------------------------------------------------------


@pytest.mark.datos
class TestLeerDenueInfanciasDatosReales:
    @staticmethod
    @pytest.fixture(scope="class")
    def con():
        con = io.conectar()
        yield con
        con.close()

    @staticmethod
    @pytest.fixture(scope="class")
    def df_3_cortes(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        return io.leer_denue_infancias(con, io.CORTES_OFERTA.keys())

    def test_columnas_exactas(self, df_3_cortes: pd.DataFrame) -> None:
        assert list(df_3_cortes.columns) == [
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

    def test_tipos_correctos(self, df_3_cortes: pd.DataFrame) -> None:
        assert pd.api.types.is_integer_dtype(df_3_cortes["id"])
        assert pd.api.types.is_integer_dtype(df_3_cortes["scian"])
        assert pd.api.types.is_float_dtype(df_3_cortes["t"])
        for col in ("cvegeo", "cve_mun", "alcance", "sector", "subcategoria", "edicion"):
            assert df_3_cortes[col].dtype == object or pd.api.types.is_string_dtype(
                df_3_cortes[col]
            )

    def test_lee_los_3_cortes(self, df_3_cortes: pd.DataFrame) -> None:
        assert set(df_3_cortes["edicion"].unique()) == set(io.CORTES_OFERTA)

    def test_t_coincide_con_cortes_oferta(self, df_3_cortes: pd.DataFrame) -> None:
        esperado = df_3_cortes["edicion"].map(io.CORTES_OFERTA)
        assert (df_3_cortes["t"] == esperado).all()

    def test_cve_mun_derivado_de_cvegeo(self, df_3_cortes: pd.DataFrame) -> None:
        esperado = df_3_cortes["cvegeo"].str.slice(2, 5)
        assert (df_3_cortes["cve_mun"] == esperado).all()

    def test_alcance_en_valores_esperados(self, df_3_cortes: pd.DataFrame) -> None:
        assert set(df_3_cortes["alcance"].unique()) <= {"Principal", "Complementario"}

    def test_id_unico_por_edicion(self, df_3_cortes: pd.DataFrame) -> None:
        for edicion, grupo in df_3_cortes.groupby("edicion"):
            assert grupo["id"].is_unique, f"IDs duplicados en la edición {edicion}"

    def test_conteo_de_filas_por_corte(
        self, con: duckdb.DuckDBPyConnection, df_3_cortes: pd.DataFrame
    ) -> None:
        # Conteo directo con DuckDB sobre el CSV crudo, como aserción
        # independiente de `leer_denue_infancias` (plan §8, criterio de B4
        # se apoya en este mismo patrón).
        conteos = df_3_cortes.groupby("edicion").size().to_dict()
        assert conteos == {"2016-10": 11589, "2019-11": 11221, "2024-11": 10197}

    def test_ediciones_todas_se_pueden_leer(
        self, con: duckdb.DuckDBPyConnection
    ) -> None:
        df = io.leer_denue_infancias(con, io.EDICIONES_TODAS)
        assert set(df["edicion"].unique()) == set(io.EDICIONES_TODAS)
        # Las ediciones fuera de CORTES_OFERTA no tienen fecha de oferta.
        sin_corte = df[~df["edicion"].isin(io.CORTES_OFERTA)]
        assert sin_corte["t"].isna().all()

    def test_lista_vacia_de_ediciones(self, con: duckdb.DuckDBPyConnection) -> None:
        df = io.leer_denue_infancias(con, [])
        assert df.empty
        assert list(df.columns) == [
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


# ---------------------------------------------------------------------------
# Fase 5: leer_denue_salud, leer_denue_comercios, leer_contexto_cdmx
# ---------------------------------------------------------------------------


@pytest.mark.datos
class TestLeerDenueSaludDatosReales:
    @staticmethod
    @pytest.fixture(scope="class")
    def con():
        con = io.conectar()
        yield con
        con.close()

    @staticmethod
    @pytest.fixture(scope="class")
    def df_3_cortes(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        return io.leer_denue_salud(con, io.CORTES_OFERTA.keys())

    def test_columnas_exactas(self, df_3_cortes: pd.DataFrame) -> None:
        assert list(df_3_cortes.columns) == [
            "id",
            "cvegeo",
            "cve_mun",
            "alcance",
            "sector",
            "scian",
            "subcategoria",
            "edicion",
            "es_hospital",
            "es_clinica",
            "es_salud_mental",
            "es_farmacia",
            "t",
        ]

    def test_booleanos_son_0_o_1(self, df_3_cortes: pd.DataFrame) -> None:
        for col in ("es_hospital", "es_clinica", "es_salud_mental", "es_farmacia"):
            assert set(df_3_cortes[col].unique()) <= {0, 1}
            assert df_3_cortes[col].sum() > 0  # cada bandera aparece de verdad en los datos

    def test_id_unico_por_edicion(self, df_3_cortes: pd.DataFrame) -> None:
        for edicion, grupo in df_3_cortes.groupby("edicion"):
            assert grupo["id"].is_unique, f"IDs duplicados en la edición {edicion}"

    def test_lee_los_3_cortes(self, df_3_cortes: pd.DataFrame) -> None:
        assert set(df_3_cortes["edicion"].unique()) == set(io.CORTES_OFERTA)


@pytest.mark.datos
class TestLeerDenueComerciosDatosReales:
    @staticmethod
    @pytest.fixture(scope="class")
    def df_3_cortes() -> pd.DataFrame:
        return io.leer_denue_comercios(io.CORTES_OFERTA.keys())

    def test_columnas_exactas(self, df_3_cortes: pd.DataFrame) -> None:
        assert list(df_3_cortes.columns) == [
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

    def test_cvegeo_de_13_caracteres(self, df_3_cortes: pd.DataFrame) -> None:
        assert (df_3_cortes["cvegeo"].str.len() == 13).all()

    def test_id_unico_por_edicion(self, df_3_cortes: pd.DataFrame) -> None:
        for edicion, grupo in df_3_cortes.groupby("edicion"):
            assert grupo["id"].is_unique, f"IDs duplicados en la edición {edicion}"

    def test_es_primera_necesidad_si_o_no(self, df_3_cortes: pd.DataFrame) -> None:
        assert set(df_3_cortes["es_primera_necesidad"].unique()) <= {"SI", "NO"}


@pytest.mark.datos
def test_leer_contexto_cdmx_una_fila_por_ageb() -> None:
    df = io.leer_contexto_cdmx()
    universo = io.leer_universo_ageb()
    assert len(df) == len(universo)
    assert not df["cvegeo"].duplicated().any()
    for col in ("n_cobertura_verde", "n_areas_recreativas", "n_espacios_publicos"):
        assert (df[col] >= 0).all()
        assert df[col].sum() > 0  # hay áreas/espacios de verdad, no todo ceros
    for col in ("area_cobertura_verde_m2", "area_areas_recreativas_m2", "area_espacios_publicos_m2"):
        assert (df[col] >= 0).all()


def test_leer_denue_infancias_lanza_id_duplicado_con_csv_sintetico(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aserción de `id` único por edición: falla en vez de deduplicar en silencio."""
    dir_infancias = tmp_path / "infancias"
    dir_infancias.mkdir()
    contenido = (
        "ID,Clave geográfica AGEB,Alcance,Sector,Código SCIAN,Subcategoría,Edición DENUE\n"
        "1,0900200011991,Principal,Público,853,guarderia,2016-10\n"
        "1,0900200012005,Principal,Público,853,guarderia,2016-10\n"
    )
    (dir_infancias / "denue_infancias_cdmx_2016_10.csv").write_text(
        contenido, encoding="utf-8"
    )
    monkeypatch.setattr(io, "_DIR_INFANCIAS", dir_infancias)

    con = io.conectar()
    try:
        with pytest.raises(ValueError, match="duplicad"):
            io.leer_denue_infancias(con, ["2016-10"])
    finally:
        con.close()


def test_leer_denue_infancias_lanza_error_claro_si_falta_el_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(io, "_DIR_INFANCIAS", tmp_path / "no_existe")
    con = io.conectar()
    try:
        with pytest.raises(FileNotFoundError, match="denue_infancias_cdmx_2016_10.csv"):
            io.leer_denue_infancias(con, ["2016-10"])
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Loaders de `data/interim/`: error claro si falta el parquet
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nombre_ruta, funcion",
    [
        ("RUTA_CENSO_PANEL", io.leer_censo_panel),
        ("RUTA_CONAPO_MUN_0A14", io.leer_conapo_0a14),
        ("RUTA_EQUIVALENCIA_AGEB", io.leer_equivalencia),
    ],
)
def test_loaders_de_interim_lanzan_error_claro_si_falta_el_parquet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    nombre_ruta: str,
    funcion,
) -> None:
    ruta_falsa = tmp_path / "no_existe.parquet"
    monkeypatch.setattr(io, nombre_ruta, ruta_falsa)
    with pytest.raises(FileNotFoundError, match="make datos"):
        funcion()


def test_leer_universo_ageb_lanza_error_claro_si_falta_el_geojson(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(io, "RUTA_AGEB_GEOJSON", tmp_path / "no_existe.geojson")
    with pytest.raises(FileNotFoundError):
        io.leer_universo_ageb()


# ---------------------------------------------------------------------------
# Loaders de `data/interim/`: datos reales
# ---------------------------------------------------------------------------


@pytest.mark.datos
class TestLoadersDatosReales:
    def test_leer_censo_panel_columnas_y_tipos(self) -> None:
        df = io.leer_censo_panel()
        assert list(df.columns) == [
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
        ]
        assert set(df["anio"].unique()) == {2010, 2020}
        assert pd.api.types.is_float_dtype(df["t"])
        assert not df.empty
        # pob_0a14 (0-14) debe ser exactamente la suma de las 4 bandas 0-14 (Fase 4,
        # metodología §1.1); p_15a17 es una banda adicional, fuera de pob_0a14.
        con_dato = df[["pob_0a14", "p_0a2", "p_3a5", "p_6a11", "p_12a14"]].dropna()
        suma = con_dato[["p_0a2", "p_3a5", "p_6a11", "p_12a14"]].sum(axis=1)
        assert (con_dato["pob_0a14"] == suma).all()

    def test_leer_conapo_0a14_columnas(self) -> None:
        df = io.leer_conapo_0a14()
        assert list(df.columns) == ["cve_mun", "anio", "pob_0a14"]
        assert set(df["cve_mun"].str.len().unique()) == {3}
        assert not df.empty

    def test_leer_equivalencia_columnas_y_relaciones(self) -> None:
        df = io.leer_equivalencia()
        assert list(df.columns) == [
            "cvegeo",
            "cvegeo_2010",
            "frac_de_2020",
            "frac_de_2010",
            "hijas_de_2010",
            "relacion",
        ]
        assert set(df["relacion"].unique()) <= {
            "misma",
            "division",
            "fusion_o_expansion",
            "cambio_limites",
        }

    def test_leer_universo_ageb_2453_filas(self) -> None:
        df = io.leer_universo_ageb()
        assert list(df.columns) == ["cvegeo", "cve_mun", "ambito"]
        assert len(df) == 2_453
        assert df["cvegeo"].is_unique
        assert set(df["ambito"].unique()) == {"urbano", "rural"}
