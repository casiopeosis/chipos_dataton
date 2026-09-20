"""Tests de `chipos.panel` (plan `backend_plan.md` §4, tareas B3 y B4).

Los tests sintéticos ejercen cada rama de `relacion` / `motivo_sin_datos` y
los filtros de clave de la capa de oferta sin tocar `data/`. Los tests
marcados `@pytest.mark.datos` verifican los conteos de aceptación contra el
perfil (`docs/perfil_datos.md`) y se saltan si falta `data/interim/`.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from chipos.io import CORTES_OFERTA, leer_censo_panel, leer_denue_infancias, leer_equivalencia, leer_universo_ageb
from chipos.panel import (
    COLUMNAS_SEGMENTO,
    SEGMENTOS_DEMANDA,
    construir_panel_demanda,
    construir_panel_oferta,
    reporte_cobertura,
)


# ---------------------------------------------------------------------------
# Fixtures sintéticas locales (control fino de cada rama de `relacion` /
# `motivo_sin_datos`, distintas de las fixtures genéricas de conftest.py).
# ---------------------------------------------------------------------------


@pytest.fixture
def universo_demanda() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cvegeo": [
                "0900200011991",  # misma, con dato
                "0900200012005",  # division, D_2020 < 20
                "0900300010112",  # fusion_o_expansion, suprimido en 2020
                "0900300010128",  # sin_contraparte (sin fila en equivalencia)
                "0900300010999",  # urbana, sin ninguna fila censal 2020
                "090150001",  # rural
            ],
            "cve_mun": ["002", "002", "003", "003", "003", "015"],
            "ambito": ["urbano", "urbano", "urbano", "urbano", "urbano", "rural"],
        }
    )


@pytest.fixture
def equivalencia_demanda() -> pd.DataFrame:
    # `0900300010999` (sin censo) y `090150001` (rural) quedan fuera a propósito.
    return pd.DataFrame(
        {
            "cvegeo": ["0900200011991", "0900200012005", "0900300010112"],
            "cvegeo_2010": ["0900200011991", "0900200019999", "0900300019999"],
            "frac_de_2020": [1.0, 0.99, 0.9],
            "frac_de_2010": [1.0, 0.85, 1.0],
            "hijas_de_2010": [1.0, 2.0, 1.0],
            "relacion": ["misma", "division", "fusion_o_expansion"],
        }
    )


@pytest.fixture
def censo_demanda() -> pd.DataFrame:
    """Cada fila trae las bandas censales (Fase 4) en vez de `pob_0a14` directo; las 4
    bandas 0-14 (`p_0a2, p_3a5, p_6a11, p_12a14`) suman exactamente el total que antes
    tenía `pob_0a14` en cada caso, para que los tests que usan `segmento="total_0a14"`
    (alias de 0-14, ver `panel.COLUMNAS_SEGMENTO`) conserven sus valores esperados."""
    filas = [
        # 2010: la madre de la división (0900200019999) tiene 200 niños;
        # su hija (0900200012005) NO debe reescalarlos por frac_de_2010.
        # (cvegeo, anio, p_0a2, p_3a5, p_6a11, p_12a14, p_15a17)  -> total 0-14 en el comentario
        ("0900200011991", 2010, 30, 30, 30, 30, 12),  # 120
        ("0900200019999", 2010, 50, 50, 50, 50, 20),  # 200
        ("0900300019999", 2010, 10, 15, 15, 10, 5),  # 50
        # 2020
        ("0900200011991", 2020, 25, 25, 30, 30, 11),  # 110
        ("0900200012005", 2020, 3, 4, 4, 4, 2),  # 15, < 20 -> d2020_menor_20
        ("0900300010112", 2020, None, None, None, None, None),  # suprimido INEGI
        ("0900300010128", 2020, 20, 20, 20, 20, 8),  # 80, sin_contraparte, con dato válido
        # `0900300010999` no aparece en 2020 -> sin_censo
    ]
    marco = pd.DataFrame(
        filas, columns=["cvegeo", "anio", "p_0a2", "p_3a5", "p_6a11", "p_12a14", "p_15a17"]
    )
    for col in ["p_0a2", "p_3a5", "p_6a11", "p_12a14", "p_15a17"]:
        marco[col] = marco[col].astype("float64")
    return marco


@pytest.fixture
def denue_oferta() -> pd.DataFrame:
    t_2016, t_2019, t_2024 = CORTES_OFERTA["2016-10"], CORTES_OFERTA["2019-11"], CORTES_OFERTA["2024-11"]
    filas = [
        # AGEB 0900200011991: 2 Principal en 2016, 1 en 2019, 0 en 2024
        (1, "0900200011991", "002", "Principal", 611111, "2016-10", t_2016),
        (2, "0900200011991", "002", "Principal", 611111, "2016-10", t_2016),
        (3, "0900200011991", "002", "Principal", 611111, "2019-11", t_2019),
        (4, "0900200011991", "002", "Complementario", 624411, "2019-11", t_2019),  # excluido: no Principal
        # AGEB 0900200012005: 1 Principal en 2024
        (5, "0900200012005", "002", "Principal", 611122, "2024-11", t_2024),
        # AGEB 0900300010112: sin ningún Principal en los 3 cortes (queda en 0)
        # Ruido a filtrar:
        (6, "090150001", "015", "Principal", 611111, "2016-10", t_2016),  # rural: cvegeo de 9 car.
        (7, "0801500011991", "015", "Principal", 611111, "2016-10", t_2016),  # prefijo != 09
        (8, "0900100011991", "001", "Principal", 611111, "2016-10", t_2016),  # cve_mun fuera de 002-017
        (9, "0900900019999", "009", "Principal", 611111, "2016-10", t_2016),  # no está en el universo urbano
        (10, "0900200011991", "002", "Principal", 611111, "2017-11", float("nan")),  # edición fuera de los 3 cortes
    ]
    marco = pd.DataFrame(
        filas, columns=["id", "cvegeo", "cve_mun", "alcance", "scian", "edicion", "t"]
    )
    marco["subcategoria"] = "guarderia"
    marco["sector"] = "Privado"
    return marco


# ---------------------------------------------------------------------------
# B3: construir_panel_demanda
# ---------------------------------------------------------------------------


def test_panel_demanda_una_fila_por_ageb_del_universo(universo_demanda, equivalencia_demanda, censo_demanda):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    assert len(panel) == len(universo_demanda)
    assert not panel["cvegeo"].duplicated().any()
    assert list(panel.columns) == [
        "cvegeo",
        "cve_mun",
        "ambito",
        "relacion",
        "segmento",
        "d_2010",
        "d_2020",
        "motivo_sin_datos",
    ]
    assert (panel["segmento"] == "total_0a14").all()


def test_panel_demanda_rural_sin_datos(universo_demanda, equivalencia_demanda, censo_demanda):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    fila = panel.set_index("cvegeo").loc["090150001"]
    assert fila["motivo_sin_datos"] == "rural"
    assert pd.isna(fila["relacion"])
    assert pd.isna(fila["d_2010"]) and pd.isna(fila["d_2020"])


def test_panel_demanda_misma_usa_su_propia_clave(universo_demanda, equivalencia_demanda, censo_demanda):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    fila = panel.set_index("cvegeo").loc["0900200011991"]
    assert fila["relacion"] == "misma"
    assert fila["d_2010"] == 120
    assert fila["d_2020"] == 110
    assert pd.isna(fila["motivo_sin_datos"]) or fila["motivo_sin_datos"] is None


def test_panel_demanda_division_hereda_d2010_completo_de_la_madre(
    universo_demanda, equivalencia_demanda, censo_demanda
):
    """`división`: la hija usa el `D_2010` completo de la madre (200), sin
    reescalarlo por `frac_de_2010` (0.85) -- decisión de `docs/metodologia.md`
    §5 ("hereda la tasa de la madre, no reparte por frac_de_2010")."""
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    fila = panel.set_index("cvegeo").loc["0900200012005"]
    assert fila["relacion"] == "division"
    assert fila["d_2010"] == 200  # NO 200 * 0.85 = 170
    assert fila["motivo_sin_datos"] == "d2020_menor_20"


def test_panel_demanda_fusion_o_expansion_suprimido(universo_demanda, equivalencia_demanda, censo_demanda):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    fila = panel.set_index("cvegeo").loc["0900300010112"]
    assert fila["relacion"] == "fusion_o_expansion"
    assert fila["d_2010"] == 50
    assert pd.isna(fila["d_2020"])
    assert fila["motivo_sin_datos"] == "suprimido_inegi"


def test_panel_demanda_sin_contraparte(universo_demanda, equivalencia_demanda, censo_demanda):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    fila = panel.set_index("cvegeo").loc["0900300010128"]
    assert fila["relacion"] == "sin_contraparte"
    assert pd.isna(fila["d_2010"])
    assert fila["d_2020"] == 80
    assert fila["motivo_sin_datos"] is None or pd.isna(fila["motivo_sin_datos"])


def test_panel_demanda_sin_censo(universo_demanda, equivalencia_demanda, censo_demanda):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    fila = panel.set_index("cvegeo").loc["0900300010999"]
    assert fila["motivo_sin_datos"] == "sin_censo"
    assert pd.isna(fila["d_2020"])


# ---------------------------------------------------------------------------
# Fase 4: segmentos de población objetivo (metodología §1.1, action_plan.md #22-27)
# ---------------------------------------------------------------------------


def test_segmento_todas_es_la_suma_de_las_cinco_bandas(
    universo_demanda, equivalencia_demanda, censo_demanda
):
    panel_todas = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="todas"
    )
    fila = panel_todas.set_index("cvegeo").loc["0900200011991"]
    # 2010: 30+30+30+30+12 = 132; 2020: 25+25+30+30+11 = 121.
    assert fila["d_2010"] == 132
    assert fila["d_2020"] == 121
    assert fila["segmento"] == "todas"


def test_segmento_adolescencia_usa_solo_p_15a17(
    universo_demanda, equivalencia_demanda, censo_demanda
):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="adolescencia"
    )
    fila = panel.set_index("cvegeo").loc["0900200011991"]
    assert fila["d_2010"] == 12
    assert fila["d_2020"] == 11


def test_segmento_preescolar_usa_solo_p_3a5(universo_demanda, equivalencia_demanda, censo_demanda):
    panel = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="preescolar"
    )
    fila = panel.set_index("cvegeo").loc["0900200011991"]
    assert fila["d_2010"] == 30
    assert fila["d_2020"] == 25


def test_segmento_todas_queda_nulo_si_falta_una_sola_banda(universo_demanda, equivalencia_demanda):
    """`min_count=len(columnas)`: si UNA banda de las 5 de `todas` está suprimida, el
    segmento completo queda `NaN` -- nunca se trata la banda faltante como cero."""
    equivalencia = pd.DataFrame(
        {
            "cvegeo": ["0900200011991"],
            "cvegeo_2010": ["0900200011991"],
            "frac_de_2020": [1.0],
            "frac_de_2010": [1.0],
            "hijas_de_2010": [1.0],
            "relacion": ["misma"],
        }
    )
    censo = pd.DataFrame(
        {
            "cvegeo": ["0900200011991", "0900200011991"],
            "anio": [2010, 2020],
            "p_0a2": [30.0, 25.0],
            "p_3a5": [30.0, 25.0],
            "p_6a11": [30.0, 30.0],
            "p_12a14": [30.0, 30.0],
            "p_15a17": [12.0, None],  # suprimida solo en 2020
        }
    )
    universo = universo_demanda.loc[universo_demanda["cvegeo"] == "0900200011991"]

    panel_todas = construir_panel_demanda(censo, equivalencia, universo, segmento="todas")
    fila_todas = panel_todas.set_index("cvegeo").loc["0900200011991"]
    assert pd.isna(fila_todas["d_2020"])  # falta p_15a17 en 2020 -> "todas" queda sin dato

    # Pero "primaria" (solo p_6a11), que sí tiene dato completo, no se ve afectada.
    panel_primaria = construir_panel_demanda(censo, equivalencia, universo, segmento="primaria")
    fila_primaria = panel_primaria.set_index("cvegeo").loc["0900200011991"]
    assert fila_primaria["d_2020"] == 30.0


def test_segmento_desconocido_lanza_valueerror(universo_demanda, equivalencia_demanda, censo_demanda):
    with pytest.raises(ValueError):
        construir_panel_demanda(
            censo_demanda, equivalencia_demanda, universo_demanda, segmento="no_existe"
        )


def test_segmentos_demanda_no_incluye_el_alias_transitorio():
    """`total_0a14` es un alias de compatibilidad (Fase 4->6, ver panel.py), no uno de los
    6 segmentos reales de Habitancia que expondrá el contrato v1.4."""
    assert "total_0a14" not in SEGMENTOS_DEMANDA
    assert set(SEGMENTOS_DEMANDA) == {
        "todas",
        "primera_infancia",
        "preescolar",
        "primaria",
        "secundaria",
        "adolescencia",
    }
    assert "total_0a14" in COLUMNAS_SEGMENTO


@pytest.mark.datos
def test_panel_demanda_conteos_de_aceptacion_perfil():
    censo = leer_censo_panel()
    equivalencia = leer_equivalencia()
    universo = leer_universo_ageb()

    # segmento="total_0a14": las cifras de docs/perfil_datos.md son sobre 0-14 (pob_0a14).
    panel = construir_panel_demanda(censo, equivalencia, universo, segmento="total_0a14")

    assert len(panel) == 2453
    assert not panel["cvegeo"].duplicated().any()

    conteos = panel["motivo_sin_datos"].value_counts(dropna=True)
    assert conteos.get("rural", 0) == 22
    assert conteos.get("suprimido_inegi", 0) == 41
    assert conteos.get("d2020_menor_20", 0) == 23


@pytest.mark.datos
def test_panel_demanda_suma_de_segmentos_igual_a_todas():
    """Fase 4, criterio de aceptación de `correccion/action_plan.md` #27: la suma de los
    cinco segmentos con dato debe ser igual al segmento `todas` (0-17), por AGEB."""
    censo = leer_censo_panel()
    equivalencia = leer_equivalencia()
    universo = leer_universo_ageb()

    panel_todas = construir_panel_demanda(censo, equivalencia, universo, segmento="todas")
    paneles_segmento = {
        seg: construir_panel_demanda(censo, equivalencia, universo, segmento=seg)
        for seg in SEGMENTOS_DEMANDA
        if seg != "todas"
    }

    base = panel_todas.set_index("cvegeo")[["d_2010", "d_2020"]]
    suma_d2010 = sum(p.set_index("cvegeo")["d_2010"] for p in paneles_segmento.values())
    suma_d2020 = sum(p.set_index("cvegeo")["d_2020"] for p in paneles_segmento.values())

    # Solo donde TODOS los segmentos (incluido "todas") tienen dato: min_count exige que
    # las 5 bandas estén presentes para que "todas" tenga dato, así que si "todas" no es
    # NaN, los 5 segmentos individuales tampoco lo son -- la comparación es exacta ahí.
    comparables = base["d_2010"].notna()
    assert (suma_d2010.reindex(base.index)[comparables] == base.loc[comparables, "d_2010"]).all()
    comparables_2020 = base["d_2020"].notna()
    assert (suma_d2020.reindex(base.index)[comparables_2020] == base.loc[comparables_2020, "d_2020"]).all()


# ---------------------------------------------------------------------------
# B4: construir_panel_oferta
# ---------------------------------------------------------------------------


def test_panel_oferta_malla_completa_con_ceros_explicitos(universo_demanda, denue_oferta):
    universo_urbano = universo_demanda[universo_demanda["ambito"] == "urbano"]
    panel = construir_panel_oferta(denue_oferta, universo_demanda)

    assert set(panel.columns) == {"cvegeo", "cve_mun", "t", "s", "s_2024"}
    assert len(panel) == len(universo_urbano) * len(CORTES_OFERTA)
    assert not panel.duplicated(["cvegeo", "t"]).any()
    # AGEB sin ningún establecimiento Principal: ceros explícitos, no ausencia.
    fila = panel[(panel["cvegeo"] == "0900300010112")]
    assert (fila["s"] == 0).all()


def test_panel_oferta_filtra_ruido_de_clave(universo_demanda, denue_oferta):
    panel = construir_panel_oferta(denue_oferta, universo_demanda)
    t_2016 = CORTES_OFERTA["2016-10"]
    fila = panel[(panel["cvegeo"] == "0900200011991") & (panel["t"] == t_2016)].iloc[0]
    # 2 Principal reales en ese AGEB/corte; el resto del "ruido" (rural,
    # prefijo, cve_mun fuera de rango, fuera de universo) no se cuenta.
    assert fila["s"] == 2


def test_panel_oferta_s_2024_se_repite_por_ageb(universo_demanda, denue_oferta):
    panel = construir_panel_oferta(denue_oferta, universo_demanda)
    t_2024 = CORTES_OFERTA["2024-11"]
    grupo = panel[panel["cvegeo"] == "0900200012005"]
    valor_2024 = grupo.loc[grupo["t"] == t_2024, "s"].iloc[0]
    assert (grupo["s_2024"] == valor_2024).all()
    assert valor_2024 == 1


@pytest.mark.datos
def test_panel_oferta_totales_principal_por_corte_igual_a_duckdb_directo():
    con = duckdb.connect()
    denue = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))
    universo = leer_universo_ageb()

    panel = construir_panel_oferta(denue, universo)
    totales_panel = panel.groupby("t")["s"].sum().to_dict()

    claves_urbanas = set(universo.loc[universo["ambito"] == "urbano", "cvegeo"])
    directo = (
        denue[
            (denue["alcance"] == "Principal")
            & (denue["cvegeo"].str.len() == 13)
            & (denue["cvegeo"].str.slice(0, 2) == "09")
            & denue["cve_mun"].between("002", "017")
            & denue["cvegeo"].isin(claves_urbanas)
            & denue["t"].isin(CORTES_OFERTA.values())
        ]
        .groupby("t")["id"]
        .nunique()
        .to_dict()
    )

    assert totales_panel.keys() == directo.keys()
    for t, esperado in directo.items():
        assert totales_panel[t] == esperado


@pytest.mark.datos
def test_panel_oferta_sin_cvegeo_duplicado_por_corte():
    con = duckdb.connect()
    denue = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))
    universo = leer_universo_ageb()
    panel = construir_panel_oferta(denue, universo)
    assert not panel.duplicated(["cvegeo", "t"]).any()


# ---------------------------------------------------------------------------
# reporte_cobertura
# ---------------------------------------------------------------------------


def test_reporte_cobertura_forma(universo_demanda, equivalencia_demanda, censo_demanda, denue_oferta):
    panel_d = construir_panel_demanda(
        censo_demanda, equivalencia_demanda, universo_demanda, segmento="total_0a14"
    )
    panel_o = construir_panel_oferta(denue_oferta, universo_demanda)

    reporte = reporte_cobertura(panel_d, panel_o, universo_demanda)

    assert reporte["universo_total"] == len(universo_demanda)
    assert reporte["universo_rural"] == 1
    assert reporte["demanda_motivo_sin_datos"]["rural"] == 1
    assert reporte["demanda_motivo_sin_datos"]["suprimido_inegi"] == 1
    assert reporte["demanda_motivo_sin_datos"]["d2020_menor_20"] == 1
    assert reporte["demanda_motivo_sin_datos"]["sin_censo"] == 1
    # 0900300010128: sin_contraparte, con dato válido -> cuenta como "con dato".
    assert reporte["demanda_n_con_dato"] == 2
    assert reporte["oferta_total_principal_por_corte"][CORTES_OFERTA["2016-10"]] == 2
    # AGEB urbanas sin ningún Principal en los 3 cortes: 0900300010112,
    # 0900300010128 y 0900300010999 (esta última ni siquiera aparece en
    # `denue_oferta`).
    assert reporte["oferta_ageb_sin_establecimientos_en_ningun_corte"] == 3
