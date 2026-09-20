"""Tests de `chipos.exportar` (B11: contrato v1.2, horizontes h1/h3/h5).

Usa fixtures sintéticas pequeñas (no lee `data/` real, salvo el marcador
`@pytest.mark.datos` de `test_pipeline_datos_reales`, que se salta si falta
`data/interim/`). Cubre: construcción de una capa completa (con las 2,453
claves "universo" -- aquí un universo sintético pequeño -- incluyendo
`sin_datos`), `validar_contrato` (casos válidos e inválidos),
`verificar_suma_ageb_alcaldia`, y determinismo byte a byte del JSON.
"""

from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd
import pytest

from chipos.config import HORIZONTES, HORIZONTES_OFERTA, SEMILLA
from chipos.modelos import agregar_alcaldia, ajustar_oferta, resumir, simular_demanda, simular_oferta
from chipos.exportar import (
    ErrorContrato,
    ORDEN_HORIZONTES,
    _simulacion_cdmx,
    construir_agregado_cdmx,
    construir_capa,
    construir_capa_brecha_ageb,
    construir_capa_brecha_alcaldia,
    construir_distribucion_ageb,
    construir_salida_ageb,
    construir_salida_alcaldia,
    escribir_json,
    motivos_demanda_por_clave,
    motivos_oferta_por_clave,
    nivel_en,
    serie_demanda_alcaldia_por_clave,
    serie_demanda_por_clave,
    serie_oferta_alcaldia_por_clave,
    serie_oferta_por_clave,
    validar_contrato,
    verificar_suma_ageb_alcaldia,
)


# ---------------------------------------------------------------------------
# Universo sintético (6 AGEB: 4 urbanas con dato, 1 sin_contraparte, 1 rural)
# ---------------------------------------------------------------------------


@pytest.fixture
def universo() -> pd.DataFrame:
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
        }
    )


@pytest.fixture
def panel_d(universo: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cvegeo": universo["cvegeo"],
            "cve_mun": universo["cve_mun"],
            "ambito": universo["ambito"],
            "relacion": ["misma", "division", "misma", "sin_contraparte", None],
            "d_2010": [120.0, 45.0, 300.0, np.nan, np.nan],
            "d_2020": [110.0, 60.0, 280.0, 15.0, np.nan],
            "motivo_sin_datos": [None, None, None, None, "rural"],
        }
    )


@pytest.fixture
def panel_o(universo: pd.DataFrame) -> pd.DataFrame:
    from chipos.io import CORTES_OFERTA

    cortes = sorted(CORTES_OFERTA.values())
    conteos = {
        "0900200011991": [8, 6, 5],
        "0900200012005": [2, 3, 4],
        "0900300010112": [0, 0, 0],  # sin_establecimientos
        "0900300010128": [12, 10, 9],
    }
    filas = [
        {"cvegeo": cve, "cve_mun": cve[2:5], "t": t, "s": s, "s_2024": conteos[cve][-1]}
        for cve in conteos
        for t, s in zip(cortes, conteos[cve])
    ]
    return pd.DataFrame(filas)


@pytest.fixture
def conapo() -> pd.DataFrame:
    filas = []
    for mun, base, tasa in [("002", 9000.0, -0.015), ("003", 15000.0, -0.02), ("015", 3000.0, -0.01)]:
        for anio in range(2009, 2035):
            pob = base * np.exp(tasa * (anio - 2009))
            filas.append({"cve_mun": mun, "anio": anio, "pob_0a14": pob})
    return pd.DataFrame(filas)


@pytest.fixture
def pipeline(universo, panel_d, panel_o, conapo):
    """Corre el pipeline completo de `exportar` sobre el universo sintético."""
    rng = np.random.default_rng(SEMILLA)
    sim_d = simular_demanda(panel_d, conapo, rng, n_sim=200)
    sim_o = simular_oferta(ajustar_oferta(panel_o), rng, n_sim=200)
    sim_d_mun = agregar_alcaldia(sim_d)
    sim_o_mun = agregar_alcaldia(sim_o)

    horizontes_oferta = {h: HORIZONTES[h] for h in HORIZONTES_OFERTA}
    res_d = resumir(sim_d, HORIZONTES)
    res_o = resumir(sim_o, horizontes_oferta)
    res_d_mun = resumir(sim_d_mun, HORIZONTES)
    res_o_mun = resumir(sim_o_mun, horizontes_oferta)

    motivos_d = motivos_demanda_por_clave(panel_d)
    ajuste = ajustar_oferta(panel_o)
    motivos_o = motivos_oferta_por_clave(universo, ajuste)

    from chipos.io import CORTES_OFERTA

    nivel_base_d = nivel_en(sim_d, 2020.20)
    nivel_base_o = nivel_en(sim_o, max(CORTES_OFERTA.values()))
    nivel_base_d_mun = nivel_en(sim_d_mun, 2020.20)
    nivel_base_o_mun = nivel_en(sim_o_mun, max(CORTES_OFERTA.values()))

    capa_demanda = construir_capa(
        res_d, universo, serie_demanda_por_clave(panel_d), nivel_base_d,
        list(ORDEN_HORIZONTES), motivos_d,
    )
    capa_oferta = construir_capa(
        res_o, universo, serie_oferta_por_clave(panel_o), nivel_base_o,
        list(HORIZONTES_OFERTA), motivos_o, incluir_horizontes_disponibles=True,
    )

    from chipos.features import calcular_brecha_ageb, calcular_brecha_alcaldia

    brecha_ageb = calcular_brecha_ageb(panel_d, panel_o)
    brecha_alcaldia = calcular_brecha_alcaldia(brecha_ageb)
    capa_brecha_ageb = construir_capa_brecha_ageb(brecha_ageb)
    capa_brecha_alcaldia = construir_capa_brecha_alcaldia(brecha_alcaldia)

    generado = "2026-09-19T00:00:00+00:00"
    salida_ageb = construir_salida_ageb(capa_demanda, capa_oferta, capa_brecha_ageb, generado)

    munes_validas = ["002", "003"] + [f"{i:03d}" for i in range(4, 18)]
    munes = pd.DataFrame({"cvegeo": munes_validas, "cve_mun": munes_validas})
    capa_demanda_mun = construir_capa(
        res_d_mun, munes, serie_demanda_alcaldia_por_clave(panel_d), nivel_base_d_mun,
        list(ORDEN_HORIZONTES), {m: None for m in munes_validas},
    )
    capa_oferta_mun = construir_capa(
        res_o_mun, munes, serie_oferta_alcaldia_por_clave(panel_o), nivel_base_o_mun,
        list(HORIZONTES_OFERTA), {m: None for m in munes_validas}, incluir_horizontes_disponibles=True,
    )
    distribucion_demanda = construir_distribucion_ageb(capa_demanda, list(ORDEN_HORIZONTES))
    distribucion_oferta = construir_distribucion_ageb(capa_oferta, list(HORIZONTES_OFERTA))

    resumen_cdmx_d = resumir(_simulacion_cdmx(sim_d), HORIZONTES)
    resumen_cdmx_o = resumir(_simulacion_cdmx(sim_o), horizontes_oferta)
    agregado_cdmx = construir_agregado_cdmx(resumen_cdmx_d, resumen_cdmx_o)

    salida_alcaldia = construir_salida_alcaldia(
        capa_demanda_mun, capa_oferta_mun, capa_brecha_alcaldia,
        distribucion_demanda, distribucion_oferta, agregado_cdmx, generado,
    )
    return salida_ageb, salida_alcaldia


# ---------------------------------------------------------------------------
# construir_capa: todas las claves del universo aparecen, con sin_datos
# ---------------------------------------------------------------------------


class TestConstruirCapa:
    def test_todas_las_claves_del_universo_aparecen(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        assert set(salida_ageb["capas"]["demanda"].keys()) == {
            "0900200011991", "0900200012005", "0900300010112", "0900300010128", "090150001",
        }
        assert set(salida_ageb["capas"]["oferta"].keys()) == set(
            salida_ageb["capas"]["demanda"].keys()
        )

    def test_rural_es_sin_datos_en_ambas_capas(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        rural_d = salida_ageb["capas"]["demanda"]["090150001"]
        rural_o = salida_ageb["capas"]["oferta"]["090150001"]
        assert rural_d["motivo_sin_datos"] == "rural"
        assert rural_d["n_obs"] == 0
        for h in ORDEN_HORIZONTES:
            assert rural_d["h"][h]["veredicto"] == "sin_datos"
            assert rural_d["h"][h]["delta_pct"] is None
        assert rural_o["h"]["h3"]["veredicto"] == "sin_datos"

    def test_sin_establecimientos_en_oferta(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        registro = salida_ageb["capas"]["oferta"]["0900300010112"]
        assert registro["motivo_sin_datos"] == "sin_establecimientos"
        assert registro["n_obs"] == 3
        assert registro["h"]["h3"]["veredicto"] == "sin_datos"

    def test_oferta_solo_trae_h1_y_h3(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        for registro in salida_ageb["capas"]["oferta"].values():
            assert list(registro["h"].keys()) == ["h1", "h3"]
            assert registro["horizontes_disponibles"] == ["h1", "h3"]

    def test_demanda_no_trae_horizontes_disponibles(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        for registro in salida_ageb["capas"]["demanda"].values():
            assert "horizontes_disponibles" not in registro


# ---------------------------------------------------------------------------
# validar_contrato
# ---------------------------------------------------------------------------


class TestValidarContrato:
    def test_documento_ageb_valido(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        validar_contrato(salida_ageb, "ageb")  # no lanza

    def test_documento_alcaldia_valido(self, pipeline) -> None:
        _, salida_alcaldia = pipeline
        validar_contrato(salida_alcaldia, "alcaldia")  # no lanza

    def test_alcaldia_tiene_16_claves(self, pipeline) -> None:
        _, salida_alcaldia = pipeline
        assert set(salida_alcaldia["capas"]["demanda"].keys()) == {
            f"{i:03d}" for i in range(2, 18)
        }
        assert set(salida_alcaldia["capas"]["oferta"].keys()) == {
            f"{i:03d}" for i in range(2, 18)
        }

    def test_version_incorrecta(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        malo["version"] = "1.1"
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_horizontes_incompletos(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        for registro in malo["capas"]["demanda"].values():
            del registro["h"]["h5"]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_horizontes_desordenados(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        malo["horizontes"] = list(reversed(malo["horizontes"]))
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_ic95_inconsistente(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        clave = next(
            c for c, r in malo["capas"]["demanda"].items() if r["h"]["h3"]["delta_pct"] is not None
        )
        malo["capas"]["demanda"][clave]["h"]["h3"]["ic95"] = [100.0, 200.0]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_alcaldia_faltante(self, pipeline) -> None:
        _, salida_alcaldia = pipeline
        malo = copy.deepcopy(salida_alcaldia)
        del malo["capas"]["demanda"]["002"]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "alcaldia")

    def test_oferta_alta_es_invalido(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        clave = next(iter(malo["capas"]["oferta"]))
        malo["capas"]["oferta"][clave]["h"]["h3"]["confianza"] = "alta"
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")


# ---------------------------------------------------------------------------
# verificar_suma_ageb_alcaldia
# ---------------------------------------------------------------------------


class TestVerificarSumaAgebAlcaldia:
    def test_suma_correcta_no_lanza(self, pipeline) -> None:
        salida_ageb, salida_alcaldia = pipeline
        verificar_suma_ageb_alcaldia(salida_ageb, salida_alcaldia)

    def test_suma_incorrecta_lanza(self, pipeline) -> None:
        salida_ageb, salida_alcaldia = pipeline
        malo = copy.deepcopy(salida_alcaldia)
        malo["capas"]["demanda"]["002"]["nivel_base"] = (
            malo["capas"]["demanda"]["002"]["nivel_base"] * 100 + 100000
        )
        with pytest.raises(ErrorContrato):
            verificar_suma_ageb_alcaldia(salida_ageb, malo)


# ---------------------------------------------------------------------------
# Determinismo byte a byte
# ---------------------------------------------------------------------------


class TestDeterminismo:
    def test_misma_semilla_mismo_json(self, universo, panel_d, panel_o, conapo, tmp_path) -> None:
        def _construir():
            rng = np.random.default_rng(SEMILLA)
            sim_d = simular_demanda(panel_d, conapo, rng, n_sim=100)
            res_d = resumir(sim_d, HORIZONTES)
            capa_demanda = construir_capa(
                res_d, universo, serie_demanda_por_clave(panel_d), nivel_en(sim_d, 2020.20),
                list(ORDEN_HORIZONTES), motivos_demanda_por_clave(panel_d),
            )
            return construir_salida_ageb(capa_demanda, {}, {}, "2026-01-01T00:00:00+00:00")

        salida1 = _construir()
        salida2 = _construir()

        ruta1 = tmp_path / "a.json"
        ruta2 = tmp_path / "b.json"
        escribir_json(salida1, ruta1)
        escribir_json(salida2, ruta2)
        assert ruta1.read_bytes() == ruta2.read_bytes()

    def test_json_es_valido_y_ordenado(self, pipeline, tmp_path) -> None:
        salida_ageb, _ = pipeline
        ruta = tmp_path / "prediccion_ageb.json"
        escribir_json(salida_ageb, ruta)
        texto = ruta.read_text(encoding="utf-8")
        assert json.loads(texto) == salida_ageb
        assert ": " not in texto and ", " not in texto  # separators compactos


# ---------------------------------------------------------------------------
# Pipeline completo sobre datos reales (opcional, se salta sin `make datos`)
# ---------------------------------------------------------------------------


@pytest.mark.datos
def test_pipeline_datos_reales_no_lanza() -> None:
    """Humo: `chipos.exportar.main()` corre sobre datos reales sin lanzar
    `ErrorContrato` (no revisa cifras, solo que el contrato se cumpla)."""
    from chipos.exportar import main

    main()
