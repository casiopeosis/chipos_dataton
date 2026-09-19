"""Verificación de la geometría AGEB ya adquirida (plan `backend_plan.md` §2.1).

`data/reference/ageb_cdmx.geojson` y `ageb_cdmx_simplificado.geojson` son de
solo lectura (CLAUDE.md regla 3): este módulo únicamente los lee y aserta
sobre ellos, nunca los reescribe ni regenera.

Las propiedades se leen con `pyogrio.read_dataframe(..., read_geometry=False)`
y el bbox con `pyogrio.read_info(..., force_total_bounds=True)`: ninguna de
las dos rutas carga las geometrías completas (economía de tokens/memoria,
CLAUDE.md "Economía de tokens").
"""

from __future__ import annotations

import pandas as pd
import pyogrio
import pytest

from chipos.config import RUTA_AGEB_GEOJSON, RUTA_AGEB_GEOJSON_SIMPLIFICADO

N_FEATURES_ESPERADO = 2_453
N_URBANO_ESPERADO = 2_431
N_RURAL_ESPERADO = 22
CVE_MUN_VALIDOS = {f"{i:03d}" for i in range(2, 18)}  # 002..017
BBOX_CDMX = (-99.37, 19.04, -98.94, 19.60)  # (minx, miny, maxx, maxy)


def _requiere_geojson(ruta) -> None:
    if not ruta.exists():
        pytest.skip(f"falta {ruta} (solo lectura; no se regenera desde los tests)")


@pytest.fixture(scope="module")
def propiedades_completo() -> pd.DataFrame:
    _requiere_geojson(RUTA_AGEB_GEOJSON)
    return pyogrio.read_dataframe(RUTA_AGEB_GEOJSON, read_geometry=False)


@pytest.fixture(scope="module")
def propiedades_simplificado() -> pd.DataFrame:
    _requiere_geojson(RUTA_AGEB_GEOJSON_SIMPLIFICADO)
    return pyogrio.read_dataframe(
        RUTA_AGEB_GEOJSON_SIMPLIFICADO, read_geometry=False
    )


class TestGeojsonCompleto:
    def test_numero_de_features(self, propiedades_completo: pd.DataFrame) -> None:
        assert len(propiedades_completo) == N_FEATURES_ESPERADO

    def test_cvegeo_unico(self, propiedades_completo: pd.DataFrame) -> None:
        assert propiedades_completo["cvegeo"].is_unique

    def test_conteo_urbano_rural(self, propiedades_completo: pd.DataFrame) -> None:
        longitudes = propiedades_completo["cvegeo"].str.len()
        urbano = propiedades_completo["ambito"] == "urbano"
        rural = propiedades_completo["ambito"] == "rural"

        assert (longitudes == 13).sum() == N_URBANO_ESPERADO
        assert (longitudes == 9).sum() == N_RURAL_ESPERADO
        assert urbano.sum() == N_URBANO_ESPERADO
        assert rural.sum() == N_RURAL_ESPERADO

        # Correspondencia exacta: 13 caracteres <=> urbano, 9 <=> rural.
        assert (longitudes[urbano] == 13).all()
        assert (longitudes[rural] == 9).all()

    def test_cve_mun_valido(self, propiedades_completo: pd.DataFrame) -> None:
        assert set(propiedades_completo["cve_mun"].unique()) <= CVE_MUN_VALIDOS

    def test_bbox_dentro_de_cdmx(self) -> None:
        _requiere_geojson(RUTA_AGEB_GEOJSON)
        info = pyogrio.read_info(RUTA_AGEB_GEOJSON, force_total_bounds=True)
        minx, miny, maxx, maxy = info["total_bounds"]

        assert BBOX_CDMX[0] <= minx
        assert BBOX_CDMX[1] <= miny
        assert maxx <= BBOX_CDMX[2]
        assert maxy <= BBOX_CDMX[3]


class TestGeojsonSimplificado:
    def test_mismas_claves_que_el_completo(
        self,
        propiedades_completo: pd.DataFrame,
        propiedades_simplificado: pd.DataFrame,
    ) -> None:
        claves_completo = set(propiedades_completo["cvegeo"])
        claves_simplificado = set(propiedades_simplificado["cvegeo"])
        assert claves_completo == claves_simplificado
