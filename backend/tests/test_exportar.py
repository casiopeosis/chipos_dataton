"""Tests de `chipos.exportar` (contrato v1.4: 6 segmentos de demanda, 4 ramas de oferta).

Usa fixtures sintéticas pequeñas (no lee `data/` real, salvo el marcador
`@pytest.mark.datos` de `test_pipeline_datos_reales`, que se salta si falta
`data/interim/`). El universo sintético (5 AGEB) se comparte entre los 6
segmentos de demanda y las celdas de cada rama (misma capa reutilizada bajo
cada segmento/celda): lo que se prueba aquí es el *ensamblado* anidado del
contrato (`construir_capa_demanda_v14`, `construir_capa_rama_v14`,
`construir_capa_verde`, `validar_contrato`), no que cada segmento/celda
produzca cifras distintas (eso ya lo cubren `test_panel.py`/`test_features.py`).
"""

from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd
import pytest

from chipos.config import HORIZONTES, HORIZONTES_OFERTA, SEMILLA, T_2020
from chipos.modelos import agregar_alcaldia, ajustar_oferta, resumir, simular_demanda, simular_oferta
from chipos.panel import CELDAS_COMERCIO, CELDAS_EDUCACION, CELDAS_SALUD, CELDAS_VERDE, SEGMENTOS_DEMANDA
from chipos.exportar import (
    RAMAS,
    RAMAS_CON_PROYECCION,
    ErrorContrato,
    ORDEN_HORIZONTES,
    _CELDAS_POR_RAMA,
    _simulacion_cdmx,
    construir_agregado_cdmx,
    construir_capa,
    construir_capa_demanda_v14,
    construir_capa_rama_v14,
    construir_capa_verde,
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
# Universo sintético (5 AGEB: 4 urbanas con dato, 1 rural)
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


def _contexto_verde(claves: pd.DataFrame, clave_col: str = "cvegeo") -> pd.DataFrame:
    """`io.leer_contexto_cdmx()` sintético: una fila por clave con las 3 celdas de
    `CELDAS_VERDE` (conteo entero, área en m2)."""
    columnas = [c for par in CELDAS_VERDE.values() for c in par]
    datos = {clave_col: claves[clave_col].tolist(), "cve_mun": claves["cve_mun"].tolist()}
    for i, col in enumerate(columnas):
        # conteo si termina en cantidad par de columnas de área, área si no: basta con
        # valores > 0 estables y deterministas para no depender de orden de dict.
        es_area = col.startswith("area_")
        datos[col] = [(10.0 + i) if es_area else (i + 1) for _ in range(len(claves))]
    return pd.DataFrame(datos).rename(columns={clave_col: "cvegeo"})


@pytest.fixture
def pipeline(universo, panel_d, panel_o, conapo):
    """Corre el ensamblado completo del contrato v1.4 sobre el universo sintético,
    reutilizando la misma capa de demanda/celda bajo cada uno de los 6 segmentos /
    N celdas por rama (ver docstring del módulo)."""
    from chipos.io import CORTES_OFERTA

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

    nivel_base_d = nivel_en(sim_d, T_2020)
    nivel_base_o = nivel_en(sim_o, max(CORTES_OFERTA.values()))
    nivel_base_d_mun = nivel_en(sim_d_mun, T_2020)
    nivel_base_o_mun = nivel_en(sim_o_mun, max(CORTES_OFERTA.values()))

    # --- Demanda: misma capa bajo los 6 segmentos ---
    capa_demanda_una = construir_capa(
        res_d, universo, serie_demanda_por_clave(panel_d), nivel_base_d,
        list(ORDEN_HORIZONTES), motivos_d,
    )
    capa_demanda = construir_capa_demanda_v14({seg: capa_demanda_una for seg in SEGMENTOS_DEMANDA})

    munes_validas = ["002", "003"] + [f"{i:03d}" for i in range(4, 18)]
    munes = pd.DataFrame({"cvegeo": munes_validas, "cve_mun": munes_validas})
    capa_demanda_mun_una = construir_capa(
        res_d_mun, munes, serie_demanda_alcaldia_por_clave(panel_d), nivel_base_d_mun,
        list(ORDEN_HORIZONTES), {m: None for m in munes_validas},
    )
    capa_demanda_mun = construir_capa_demanda_v14(
        {seg: capa_demanda_mun_una for seg in SEGMENTOS_DEMANDA}
    )
    distribucion_demanda = construir_distribucion_ageb(capa_demanda_una, list(ORDEN_HORIZONTES))

    # --- Ramas con proyección: misma capa bajo cada celda real de la rama ---
    capa_oferta_una = construir_capa(
        res_o, universo, serie_oferta_por_clave(panel_o), nivel_base_o,
        list(HORIZONTES_OFERTA), motivos_o, incluir_horizontes_disponibles=True,
    )
    capa_oferta_mun_una = construir_capa(
        res_o_mun, munes, serie_oferta_alcaldia_por_clave(panel_o), nivel_base_o_mun,
        list(HORIZONTES_OFERTA), {m: None for m in munes_validas}, incluir_horizontes_disponibles=True,
    )

    capas_ramas_ageb: dict[str, dict] = {}
    capas_ramas_mun: dict[str, dict] = {}
    for rama in RAMAS_CON_PROYECCION:
        celdas_rama = _CELDAS_POR_RAMA[rama]
        capas_ramas_ageb[rama] = construir_capa_rama_v14(
            {c: capa_oferta_una for c in celdas_rama}, list(HORIZONTES_OFERTA)
        )
        capas_ramas_mun[rama] = construir_capa_rama_v14(
            {c: capa_oferta_mun_una for c in celdas_rama}, list(HORIZONTES_OFERTA)
        )

    # --- Verde: sin proyección ---
    munes_urbanas = munes.assign(ambito="urbano")
    capas_ramas_ageb["verde"] = construir_capa_verde(_contexto_verde(universo), universo, CELDAS_VERDE)
    capas_ramas_mun["verde"] = construir_capa_verde(
        _contexto_verde(munes, clave_col="cvegeo"), munes_urbanas, CELDAS_VERDE
    )

    generado = "2026-09-19T00:00:00+00:00"
    salida_ageb = construir_salida_ageb(capa_demanda, capas_ramas_ageb, generado)

    # --- Agregado CDMX ---
    resumen_cdmx_d = resumir(_simulacion_cdmx(sim_d), HORIZONTES)
    resumen_cdmx_o = resumir(_simulacion_cdmx(sim_o), horizontes_oferta)
    resumenes_demanda_cdmx = {seg: resumen_cdmx_d for seg in SEGMENTOS_DEMANDA}
    resumenes_ramas_cdmx = {
        rama: {c: resumen_cdmx_o for c in _CELDAS_POR_RAMA[rama]} for rama in RAMAS_CON_PROYECCION
    }
    capa_verde_cdmx = {
        "horizontes_disponibles": [],
        "celdas": {
            celda: {"nivel_base": 5, "area_m2": 50.0, "motivo_sin_datos": None}
            for celda in CELDAS_VERDE
        },
    }
    agregado_cdmx = construir_agregado_cdmx(resumenes_demanda_cdmx, resumenes_ramas_cdmx, capa_verde_cdmx)

    salida_alcaldia = construir_salida_alcaldia(
        capa_demanda_mun, capas_ramas_mun, distribucion_demanda, agregado_cdmx, generado,
    )
    return salida_ageb, salida_alcaldia


# ---------------------------------------------------------------------------
# construir_capa_demanda_v14 / construir_capa_rama_v14 / construir_capa_verde
# ---------------------------------------------------------------------------


class TestConstruirCapa:
    def test_todas_las_claves_del_universo_aparecen(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        claves = {
            "0900200011991", "0900200012005", "0900300010112", "0900300010128", "090150001",
        }
        assert set(salida_ageb["capas"]["demanda"].keys()) == claves
        for rama in RAMAS:
            assert set(salida_ageb["capas"]["ramas"][rama].keys()) == claves

    def test_demanda_trae_los_6_segmentos(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        for registro in salida_ageb["capas"]["demanda"].values():
            assert set(registro["segmentos"].keys()) == set(SEGMENTOS_DEMANDA)

    def test_ramas_con_proyeccion_traen_sus_celdas_reales(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        for registro in salida_ageb["capas"]["ramas"]["educacion"].values():
            assert set(registro["celdas"].keys()) == set(CELDAS_EDUCACION)
        for registro in salida_ageb["capas"]["ramas"]["salud"].values():
            assert set(registro["celdas"].keys()) == set(CELDAS_SALUD)
        for registro in salida_ageb["capas"]["ramas"]["comercio"].values():
            assert set(registro["celdas"].keys()) == set(CELDAS_COMERCIO)

    def test_rural_es_sin_datos_en_demanda_y_ramas(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        rural_d = salida_ageb["capas"]["demanda"]["090150001"]["segmentos"]["todas"]
        assert rural_d["motivo_sin_datos"] == "rural"
        assert rural_d["n_obs"] == 0
        for h in ORDEN_HORIZONTES:
            assert rural_d["h"][h]["veredicto"] == "sin_datos"
            assert rural_d["h"][h]["delta_pct"] is None

        rural_o = salida_ageb["capas"]["ramas"]["educacion"]["090150001"]["celdas"]["guarderia"]
        assert rural_o["h"]["h3"]["veredicto"] == "sin_datos"

        rural_verde = salida_ageb["capas"]["ramas"]["verde"]["090150001"]["celdas"]["cobertura_verde"]
        assert rural_verde["motivo_sin_datos"] == "rural"
        assert rural_verde["nivel_base"] is None

    def test_sin_establecimientos_en_ramas(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        registro = salida_ageb["capas"]["ramas"]["educacion"]["0900300010112"]["celdas"]["guarderia"]
        assert registro["motivo_sin_datos"] == "sin_establecimientos"
        assert registro["n_obs"] == 3
        assert registro["h"]["h3"]["veredicto"] == "sin_datos"

    def test_ramas_con_proyeccion_solo_traen_h1_y_h3(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        for rama in RAMAS_CON_PROYECCION:
            for registro in salida_ageb["capas"]["ramas"][rama].values():
                assert registro["horizontes_disponibles"] == ["h1", "h3"]
                for celda in registro["celdas"].values():
                    assert list(celda["h"].keys()) == ["h1", "h3"]

    def test_demanda_no_trae_horizontes_disponibles(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        for registro in salida_ageb["capas"]["demanda"].values():
            for sub in registro["segmentos"].values():
                assert "horizontes_disponibles" not in sub

    def test_verde_sin_h_ni_serie_y_horizontes_vacios(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        for registro in salida_ageb["capas"]["ramas"]["verde"].values():
            assert registro["horizontes_disponibles"] == []
            assert set(registro["celdas"].keys()) == set(CELDAS_VERDE)
            for celda in registro["celdas"].values():
                assert "h" not in celda and "serie" not in celda
                assert "nivel_base" in celda and "motivo_sin_datos" in celda

    def test_verde_nivel_base_urbano_no_nulo(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        registro = salida_ageb["capas"]["ramas"]["verde"]["0900200011991"]["celdas"]["cobertura_verde"]
        assert registro["motivo_sin_datos"] is None
        assert registro["nivel_base"] is not None


# ---------------------------------------------------------------------------
# construir_agregado_cdmx
# ---------------------------------------------------------------------------


class TestConstruirAgregadoCdmx:
    def test_estructura(self, pipeline) -> None:
        _, salida_alcaldia = pipeline
        agregado = salida_alcaldia["agregado_cdmx"]
        assert set(agregado["demanda"]["segmentos"].keys()) == set(SEGMENTOS_DEMANDA)
        assert set(agregado["ramas"].keys()) == set(RAMAS)
        assert set(agregado["ramas"]["educacion"]["celdas"].keys()) == set(CELDAS_EDUCACION)
        assert "h" not in agregado["ramas"]["verde"]


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
        esperadas = {f"{i:03d}" for i in range(2, 18)}
        assert set(salida_alcaldia["capas"]["demanda"].keys()) == esperadas
        for rama in RAMAS:
            assert set(salida_alcaldia["capas"]["ramas"][rama].keys()) == esperadas

    def test_version_incorrecta(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        malo["version"] = "1.2"
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_horizontes_incompletos(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        for registro in malo["capas"]["demanda"].values():
            del registro["segmentos"]["todas"]["h"]["h5"]
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
            c for c, r in malo["capas"]["demanda"].items()
            if r["segmentos"]["todas"]["h"]["h3"]["delta_pct"] is not None
        )
        malo["capas"]["demanda"][clave]["segmentos"]["todas"]["h"]["h3"]["ic95"] = [100.0, 200.0]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_alcaldia_faltante(self, pipeline) -> None:
        _, salida_alcaldia = pipeline
        malo = copy.deepcopy(salida_alcaldia)
        del malo["capas"]["demanda"]["002"]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "alcaldia")

    def test_rama_confianza_alta_es_invalido(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        clave = next(iter(malo["capas"]["ramas"]["educacion"]))
        malo["capas"]["ramas"]["educacion"][clave]["celdas"]["guarderia"]["h"]["h3"]["confianza"] = "alta"
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_segmento_faltante_es_invalido(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        clave = next(iter(malo["capas"]["demanda"]))
        del malo["capas"]["demanda"][clave]["segmentos"]["adolescencia"]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_celda_faltante_es_invalido(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        clave = next(iter(malo["capas"]["ramas"]["educacion"]))
        del malo["capas"]["ramas"]["educacion"][clave]["celdas"]["guarderia"]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_verde_con_h_es_invalido(self, pipeline) -> None:
        salida_ageb, _ = pipeline
        malo = copy.deepcopy(salida_ageb)
        clave = next(iter(malo["capas"]["ramas"]["verde"]))
        malo["capas"]["ramas"]["verde"][clave]["celdas"]["cobertura_verde"]["h"] = {}
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "ageb")

    def test_falta_agregado_cdmx_en_alcaldia(self, pipeline) -> None:
        _, salida_alcaldia = pipeline
        malo = copy.deepcopy(salida_alcaldia)
        del malo["agregado_cdmx"]
        with pytest.raises(ErrorContrato):
            validar_contrato(malo, "alcaldia")


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
        registro = malo["capas"]["demanda"]["002"]["segmentos"]["todas"]
        registro["nivel_base"] = registro["nivel_base"] * 100 + 100000
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
            capa_demanda_una = construir_capa(
                res_d, universo, serie_demanda_por_clave(panel_d), nivel_en(sim_d, T_2020),
                list(ORDEN_HORIZONTES), motivos_demanda_por_clave(panel_d),
            )
            capa_demanda = construir_capa_demanda_v14({seg: capa_demanda_una for seg in SEGMENTOS_DEMANDA})
            return construir_salida_ageb(capa_demanda, {}, "2026-01-01T00:00:00+00:00")

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
