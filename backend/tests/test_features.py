"""Tests de `chipos.features` (brecha oferta/demanda, tarea B10).

Fixtures sintéticas locales (el `panel_oferta_sintetico` de `conftest.py` no
trae `s_2024`, que es lo que este módulo necesita); los tests marcados
`@pytest.mark.datos` ejercen el cálculo con datos reales y se saltan si
falta `data/interim/` (ver `conftest.py`).
"""

from __future__ import annotations

import json
import math

import pandas as pd
import pytest

from chipos.features import (
    calcular_brecha_ageb,
    calcular_brecha_alcaldia,
    construir_diagnostico,
    escribir_diagnostico,
)

# ---------------------------------------------------------------------------
# Fixtures sintéticas locales
# ---------------------------------------------------------------------------


@pytest.fixture
def panel_d_sintetico() -> pd.DataFrame:
    """Panel de demanda: 4 AGEB urbanas (2 alcaldías) + 1 rural."""
    return pd.DataFrame(
        {
            "cvegeo": [
                "0900200011991",
                "0900200012005",
                "0900300010112",
                "0900300010128",
                "090150001",
            ],
            "cve_mun": ["002", "002", "003", "003", "015"],
            "ambito": ["urbano", "urbano", "urbano", "urbano", "rural"],
            "relacion": ["misma", "division", "misma", "misma", None],
            "d_2010": [120.0, 45.0, 300.0, 200.0, None],
            "d_2020": [100.0, 50.0, 300.0, 0.0, None],
            "motivo_sin_datos": [None, None, None, None, "rural"],
        }
    )


@pytest.fixture
def panel_o_sintetico() -> pd.DataFrame:
    """Panel de oferta largo (3 cortes) con `s_2024`, solo AGEB urbanas.

    `s` en el último corte (2024.87): 2, 3, 0, 5 para las 4 AGEB urbanas de
    `panel_d_sintetico`, en el mismo orden.
    """
    cvegeos = ["0900200011991", "0900200012005", "0900300010112", "0900300010128"]
    cve_muns = ["002", "002", "003", "003"]
    cortes = [2016.79, 2019.87, 2024.87]
    s_2024_por_ageb = {"0900200011991": 2, "0900200012005": 3, "0900300010112": 0, "0900300010128": 5}
    filas = []
    for cve, mun in zip(cvegeos, cve_muns):
        for t in cortes:
            filas.append(
                {
                    "cvegeo": cve,
                    "cve_mun": mun,
                    "t": t,
                    "s": s_2024_por_ageb[cve] if t == 2024.87 else 1,
                    "s_2024": s_2024_por_ageb[cve],
                }
            )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# calcular_brecha_ageb
# ---------------------------------------------------------------------------


def test_calcular_brecha_ageb_formula(panel_d_sintetico, panel_o_sintetico):
    brecha = calcular_brecha_ageb(panel_d_sintetico, panel_o_sintetico)

    assert set(brecha["cvegeo"]) == {
        "0900200011991",
        "0900200012005",
        "0900300010112",
        "0900300010128",
    }

    por_ageb = brecha.set_index("cvegeo")
    # 0900200011991: s_2024=2, d_2020=100 -> 2/100*1000 = 20.0
    assert math.isclose(por_ageb.loc["0900200011991", "brecha_por_mil"], 20.0)
    # 0900200012005: s_2024=3, d_2020=50 -> 3/50*1000 = 60.0
    assert math.isclose(por_ageb.loc["0900200012005", "brecha_por_mil"], 60.0)
    # 0900300010112: s_2024=0, d_2020=300 -> 0/300*1000 = 0.0 (oferta cero, no nulo)
    assert math.isclose(por_ageb.loc["0900300010112", "brecha_por_mil"], 0.0)


def test_calcular_brecha_ageb_denominador_cero_es_nulo(panel_d_sintetico, panel_o_sintetico):
    """`d_2020 == 0` (AGEB `0900300010128`) no debe producir una razón infinita."""
    brecha = calcular_brecha_ageb(panel_d_sintetico, panel_o_sintetico)
    fila = brecha.set_index("cvegeo").loc["0900300010128"]
    assert pd.isna(fila["brecha_por_mil"])


def test_calcular_brecha_ageb_excluye_rural(panel_d_sintetico, panel_o_sintetico):
    """Las AGEB rurales no están en `panel_o` (construir_panel_oferta ya las
    excluye) y por lo tanto no aparecen en la tabla de brecha."""
    brecha = calcular_brecha_ageb(panel_d_sintetico, panel_o_sintetico)
    assert "090150001" not in set(brecha["cvegeo"])


# ---------------------------------------------------------------------------
# calcular_brecha_alcaldia: suma S y suma D por separado, nunca promedio de razones
# ---------------------------------------------------------------------------


def test_calcular_brecha_alcaldia_suma_antes_de_dividir(panel_d_sintetico, panel_o_sintetico):
    brecha_ageb = calcular_brecha_ageb(panel_d_sintetico, panel_o_sintetico)
    brecha_mun = calcular_brecha_alcaldia(brecha_ageb).set_index("cve_mun")

    # Alcaldía 002: AGEB (s=2,d=100) y (s=3,d=50) -> suma s=5, suma d=150
    # brecha = 5/150*1000 = 33.33..., DISTINTA del promedio de razones
    # (20.0 y 60.0 -> promedio 40.0): verifica que se usa la razón de sumas.
    esperado_002 = (2 + 3) / (100 + 50) * 1000
    promedio_de_razones_002 = (20.0 + 60.0) / 2
    assert not math.isclose(esperado_002, promedio_de_razones_002)
    assert math.isclose(brecha_mun.loc["002", "brecha_por_mil"], esperado_002)
    assert brecha_mun.loc["002", "s_2024"] == 5
    assert math.isclose(brecha_mun.loc["002", "d_2020"], 150.0)

    # Alcaldía 003: AGEB (s=0,d=300) y (s=5,d=0). `d_2020 = 0` es un dato
    # válido (no nulo), así que ambas AGEB aportan a la suma: suma s=5,
    # suma d=300 -> brecha = 5/300*1000, DISTINTA de 0 (que daría promediar
    # las razones 0.0 y "nula/excluida").
    esperado_003 = (0 + 5) / (300 + 0) * 1000
    assert math.isclose(brecha_mun.loc["003", "d_2020"], 300.0)
    assert brecha_mun.loc["003", "s_2024"] == 5
    assert math.isclose(brecha_mun.loc["003", "brecha_por_mil"], esperado_003)


def test_calcular_brecha_alcaldia_consistente_con_sumas_directas(
    panel_d_sintetico, panel_o_sintetico
):
    """La brecha de alcaldía nunca debe calcularse promediando `brecha_por_mil`
    de las AGEB: debe coincidir exactamente con sum(s)/sum(d)*1000 calculado
    directamente sobre el panel crudo (sin pasar por la razón por AGEB)."""
    brecha_ageb = calcular_brecha_ageb(panel_d_sintetico, panel_o_sintetico)
    brecha_mun = calcular_brecha_alcaldia(brecha_ageb).set_index("cve_mun")

    for mun in ["002", "003"]:
        filas = brecha_ageb.loc[brecha_ageb["cve_mun"] == mun]
        suma_s = filas["s_2024"].sum()
        suma_d = filas["d_2020"].dropna().sum()
        esperado = (suma_s / suma_d * 1000) if suma_d > 0 else None
        if esperado is None:
            assert pd.isna(brecha_mun.loc[mun, "brecha_por_mil"])
        else:
            assert math.isclose(brecha_mun.loc[mun, "brecha_por_mil"], esperado)


# ---------------------------------------------------------------------------
# construir_diagnostico / escribir_diagnostico
# ---------------------------------------------------------------------------


def test_construir_diagnostico_estructura(panel_d_sintetico, panel_o_sintetico):
    diagnostico = construir_diagnostico(panel_d_sintetico, panel_o_sintetico)

    assert "generado" in diagnostico
    assert set(diagnostico["brecha"].keys()) >= {"ageb", "alcaldia"}
    assert set(diagnostico["brecha"]["ageb"].keys()) == {
        "0900200011991",
        "0900200012005",
        "0900300010112",
        "0900300010128",
    }
    assert set(diagnostico["brecha"]["alcaldia"].keys()) == {"002", "003"}

    fila = diagnostico["brecha"]["ageb"]["0900200011991"]
    assert fila["cve_mun"] == "002"
    assert fila["s_2024"] == 2
    assert fila["brecha_por_mil"] == 20.0

    fila_nula = diagnostico["brecha"]["ageb"]["0900300010128"]
    assert fila_nula["brecha_por_mil"] is None
    assert fila_nula["d_2020"] == 0.0


def test_escribir_diagnostico_preserva_claves_de_otras_tareas(
    tmp_path, panel_d_sintetico, panel_o_sintetico
):
    """`diagnostico.json` es compartido con B9 (backtest); escribir la brecha
    no debe borrar otras claves de nivel superior ya presentes en el
    archivo."""
    ruta = tmp_path / "diagnostico.json"
    ruta.write_text(
        json.dumps({"backtest": {"mae": 1.23}, "generado": "viejo"}), encoding="utf-8"
    )

    diagnostico = construir_diagnostico(panel_d_sintetico, panel_o_sintetico)
    escribir_diagnostico(diagnostico, ruta=ruta)

    con_disco = json.loads(ruta.read_text(encoding="utf-8"))
    assert con_disco["backtest"] == {"mae": 1.23}
    assert "brecha" in con_disco
    assert con_disco["generado"] != "viejo"


def test_escribir_diagnostico_json_valido(tmp_path, panel_d_sintetico, panel_o_sintetico):
    ruta = tmp_path / "diagnostico.json"
    diagnostico = construir_diagnostico(panel_d_sintetico, panel_o_sintetico)
    escribir_diagnostico(diagnostico, ruta=ruta)

    con_disco = json.loads(ruta.read_text(encoding="utf-8"))
    assert con_disco["brecha"]["alcaldia"]["002"]["brecha_por_mil"] == round(
        (2 + 3) / (100 + 50) * 1000, 2
    )


# ---------------------------------------------------------------------------
# Con datos reales (B10: "diagnostico.json generado con datos reales al final")
# ---------------------------------------------------------------------------


@pytest.mark.datos
def test_diagnostico_con_datos_reales_se_escribe():
    from chipos.config import RUTA_DIAGNOSTICO
    from chipos.features import main

    main()

    assert RUTA_DIAGNOSTICO.exists()
    con_disco = json.loads(RUTA_DIAGNOSTICO.read_text(encoding="utf-8"))
    assert "brecha" in con_disco
    ageb = con_disco["brecha"]["ageb"]
    alcaldia = con_disco["brecha"]["alcaldia"]
    assert len(ageb) > 0
    assert len(alcaldia) == 16
    # Alguna AGEB urbana con oferta y demanda válidas debe tener brecha no nula.
    assert any(v["brecha_por_mil"] is not None for v in ageb.values())
