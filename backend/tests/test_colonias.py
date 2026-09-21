"""Verificación del lookup AGEB → colonia ya generado (`tools/build_colonias.py`).

`data/interim/ageb_colonia.parquet`, `data/reference/colonias_cdmx*.geojson` y
`data/outputs/colonias_ageb.json` son derivados regenerables (no se recalculan aquí, solo se
verifica que el último cálculo sea razonable, igual que `test_geo.py` con la geometría AGEB).
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from chipos.config import RUTA_AGEB_COLONIA, RUTA_COLONIAS_AGEB_JSON, RUTA_COLONIAS_GEOJSON_SIMPLIFICADO

N_AGEB_ESPERADO = 2_453
COBERTURA_MINIMA_SIN_MATCH = 20  # AGEB sin colonia asociada (rurales/borde de cobertura del IECM)


def _requiere(ruta) -> None:
    if not ruta.exists():
        pytest.skip(f"falta {ruta} (correr `python tools/build_colonias.py`)")


def test_lookup_cubre_todos_los_ageb():
    _requiere(RUTA_AGEB_COLONIA)
    df = pd.read_parquet(RUTA_AGEB_COLONIA)
    assert len(df) == N_AGEB_ESPERADO
    assert df["cvegeo"].is_unique


def test_tasa_de_match_razonable():
    _requiere(RUTA_AGEB_COLONIA)
    df = pd.read_parquet(RUTA_AGEB_COLONIA)
    sin_match = df["cveut"].isna().sum()
    # La delimitación de colonias (IECM) no cubre el 100% del territorio (suelo de conservación);
    # un puñado de AGEB rurales/de borde puede quedar sin colonia asociada, nunca la mayoría.
    assert sin_match <= COBERTURA_MINIMA_SIN_MATCH, f"{sin_match} AGEB sin colonia (revisar el join)"


def test_cobertura_del_match_es_mayoritaria():
    _requiere(RUTA_AGEB_COLONIA)
    df = pd.read_parquet(RUTA_AGEB_COLONIA)
    con_match = df.dropna(subset=["cveut"])
    # La colonia elegida (mayor área de intersección) debe cubrir, en promedio, la mayor parte
    # del AGEB; si cayera por debajo de 50% en promedio, el criterio de "mayor área" no estaría
    # discriminando bien entre colonias traslapadas.
    assert con_match["cobertura_pct"].mean() > 50


def test_json_para_frontend_es_consistente_con_el_parquet():
    _requiere(RUTA_COLONIAS_AGEB_JSON)
    _requiere(RUTA_AGEB_COLONIA)
    lookup = json.loads(RUTA_COLONIAS_AGEB_JSON.read_text(encoding="utf-8"))
    df = pd.read_parquet(RUTA_AGEB_COLONIA)
    assert len(lookup) == len(df)
    con_match = df.dropna(subset=["cveut"]).iloc[0]
    entrada = lookup[con_match["cvegeo"]]
    assert entrada["cveut"] == con_match["cveut"]
    assert entrada["colonia"] == con_match["colonia"]


def test_colonias_geojson_simplificado_existe_y_es_liviano():
    _requiere(RUTA_COLONIAS_GEOJSON_SIMPLIFICADO)
    tam_mb = RUTA_COLONIAS_GEOJSON_SIMPLIFICADO.stat().st_size / 1e6
    assert tam_mb < 5, f"colonias_cdmx_simplificado.geojson pesa {tam_mb:.1f} MB (límite frontend CLAUDE.md ~5MB)"
