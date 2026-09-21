"""Tests de `chipos.features` (brecha oferta/demanda, tarea B10).

Fixtures sintéticas locales (el `panel_oferta_sintetico` de `conftest.py` no
trae `s_2024`, que es lo que este módulo necesita); los tests marcados
`@pytest.mark.datos` ejercen el cálculo con datos reales y se saltan si
falta `data/interim/` (ver `conftest.py`).
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from chipos.features import (
    K_OPORTUNIDAD_DEFECTO,
    calcular_brecha_ageb,
    calcular_brecha_alcaldia,
    calcular_escenario_b_oferta,
    cobertura_proyectada,
    construir_diagnostico,
    construir_escenarios_oferta,
    construir_sensibilidad_oportunidad,
    escribir_diagnostico,
    indice_disponibilidad,
    indice_oportunidad,
    nivel_proyectado_por_replica,
    nivel_rama_por_celda,
    sensibilidad_indice_oportunidad,
    _rango_percentil_promediado,
)
from chipos.modelos import Simulacion

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
    assert "oferta_escenarios_denue_2024" in diagnostico
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
# calcular_escenario_b_oferta / construir_escenarios_oferta (Fase 3, metodología §6.1)
# ---------------------------------------------------------------------------


@pytest.fixture
def panel_o_con_caida_2024() -> pd.DataFrame:
    """3 AGEB con una caída marcada en 2024-11 (simula el patrón real: estable o al
    alza 2016->2019, caída fuerte en 2024)."""
    cortes = [2016.79, 2019.87, 2024.87]
    conteos = {
        "0900200010001": [4, 4, 1],  # estable 2016-2019, cae fuerte en 2024
        "0900200010002": [2, 3, 0],  # al alza 2016-2019, cae a 0 en 2024
        "0900300010001": [5, 4, 4],  # baja 2016-2019, estable después (menos dramático)
    }
    filas = []
    for cve, valores in conteos.items():
        for t, s in zip(cortes, valores):
            filas.append({"cvegeo": cve, "cve_mun": cve[2:5], "t": t, "s": s})
    return pd.DataFrame(filas)


def test_calcular_escenario_b_ignora_el_corte_2024(panel_o_con_caida_2024):
    tasa_b = calcular_escenario_b_oferta(panel_o_con_caida_2024)
    # AGEB estable 2016->2019 (4 -> 4): tasa_b debe ser ~0, sin importar la caída de 2024.
    assert tasa_b.loc["0900200010001"] == pytest.approx(0.0, abs=1e-9)
    # AGEB al alza 2016->2019 (2 -> 3): tasa_b > 0, aunque el conteo 2024 caiga a 0.
    assert tasa_b.loc["0900200010002"] > 0


def test_escenario_a_difiere_de_b_cuando_hay_caida_2024(panel_o_con_caida_2024):
    diagnostico = construir_escenarios_oferta(panel_o_con_caida_2024)
    ageb = diagnostico["ageb"]
    assert set(ageb.keys()) == {"0900200010001", "0900200010002", "0900300010001"}
    # La AGEB estable 2016-2019 pero con caída fuerte en 2024 debe mostrar el mayor rango
    # A-B (el escenario A sí ve la caída; B la ignora por completo).
    rango_estable = ageb["0900200010001"]["rango_pp_anio"]
    assert rango_estable > 0
    for clave in ageb:
        assert ageb[clave]["rango_pp_anio"] == pytest.approx(
            abs(ageb[clave]["tasa_a_pct_anio"] - ageb[clave]["tasa_b_pct_anio"]), abs=0.01
        )


def test_construir_escenarios_oferta_nunca_cambia_el_veredicto_publicado(
    panel_o_con_caida_2024,
):
    """El bloque de escenarios es puramente diagnóstico: no debe traer 'veredicto' ni
    tocar el contrato -- CLAUDE.md / metodología §6.1 ("no se duplica el contrato")."""
    diagnostico = construir_escenarios_oferta(panel_o_con_caida_2024)
    for registro in diagnostico["ageb"].values():
        assert "veredicto" not in registro
    assert "descripcion" in diagnostico


# ---------------------------------------------------------------------------
# Fase 6: índice de oportunidad e índice de disponibilidad (metodología §10)
# ---------------------------------------------------------------------------


def _sim(clave: list[str], base: list[float], r_fut: np.ndarray) -> Simulacion:
    n = len(clave)
    return Simulacion(
        clave=np.array(clave),
        cve_mun=np.array(["002"] * n),
        n_obs=np.full(n, 3),
        base=np.array(base, dtype=float),
        d2020_conf=None,
        tope=np.full(n, "media", dtype=object),
        r_fut=r_fut,
        r_fut_lambdas={},
        horizonte_control=1.0,
    )


class TestRangoPercentilPromediado:
    def test_orden_simple_sin_empates(self) -> None:
        rango = _rango_percentil_promediado(np.array([30.0, 10.0, 20.0]))
        # 10 -> rango 0 (más bajo); 30 -> rango 1 (más alto); 20 -> 0.5 (medio)
        np.testing.assert_allclose(rango, [1.0, 0.0, 0.5])

    def test_empates_se_promedian(self) -> None:
        rango = _rango_percentil_promediado(np.array([5.0, 5.0, 10.0]))
        # dos valores empatados en el mínimo comparten el rango promedio (0+1)/2=0.5 -> 0.25
        np.testing.assert_allclose(rango, [0.25, 0.25, 1.0])

    def test_nan_se_propaga_y_se_excluye_del_ranking(self) -> None:
        rango = _rango_percentil_promediado(np.array([10.0, np.nan, 20.0]))
        assert np.isnan(rango[1])
        np.testing.assert_allclose(rango[[0, 2]], [0.0, 1.0])

    def test_un_solo_valor_valido_da_0_5(self) -> None:
        rango = _rango_percentil_promediado(np.array([10.0, np.nan, np.nan]))
        assert rango[0] == 0.5

    def test_todos_nan(self) -> None:
        rango = _rango_percentil_promediado(np.array([np.nan, np.nan]))
        assert np.isnan(rango).all()


class TestNivelProyectadoYRama:
    def test_nivel_proyectado_por_replica_formula(self) -> None:
        r_fut = np.array([[0.0, np.log(2.0)]])  # tasa 0 y tasa ln(2) para la única AGEB
        sim = _sim(["A"], [100.0], r_fut)
        nivel = nivel_proyectado_por_replica(sim, t0=2020.0, t_horizonte=2021.0)
        # replica 0: 100*exp(0*1)=100; replica 1: 100*exp(ln(2)*1)=200
        np.testing.assert_allclose(nivel, [[100.0, 200.0]])

    def test_nivel_rama_por_celda_suma_y_alinea_por_ageb(self) -> None:
        # Celda 1: solo AGEB A y B. Celda 2: solo AGEB B y C (A falta -> aporta 0 a la celda 2).
        celda1 = _sim(["A", "B"], [10.0, 20.0], np.zeros((2, 3)))
        celda2 = _sim(["B", "C"], [5.0, 8.0], np.zeros((2, 3)))
        universo = pd.Index(["A", "B", "C"], name="cvegeo")

        nivel = nivel_rama_por_celda({"c1": celda1, "c2": celda2}, t0=2020.0, t_horizonte=2020.0, claves_universo=universo)

        # t_horizonte == t0 -> exp(0)=1, nivel = base tal cual.
        np.testing.assert_allclose(nivel[0], [10.0, 10.0, 10.0])  # A: solo celda1 (10), celda2 no la tiene -> 0
        np.testing.assert_allclose(nivel[1], [25.0, 25.0, 25.0])  # B: 20 (celda1) + 5 (celda2) = 25
        np.testing.assert_allclose(nivel[2], [8.0, 8.0, 8.0])  # C: solo celda2 (8)


class TestCoberturaProyectada:
    def test_oferta_cero_con_demanda_valida_es_cero_no_nan(self) -> None:
        cobertura = cobertura_proyectada(np.array([0.0]), np.array([100.0]))
        assert cobertura[0] == 0.0
        assert not np.isnan(cobertura[0])

    def test_demanda_invalida_es_nan(self) -> None:
        cobertura = cobertura_proyectada(np.array([5.0, 5.0]), np.array([0.0, -1.0]))
        assert np.isnan(cobertura).all()

    def test_formula_por_mil(self) -> None:
        cobertura = cobertura_proyectada(np.array([2.0]), np.array([1000.0]))
        assert cobertura[0] == pytest.approx(2.0)  # 2/1000*1000 = 2


class TestIndiceOportunidad:
    def test_cobertura_cero_da_oportunidad_maxima(self) -> None:
        """Metodología §10.2: las AGEB con cobertura=0 comparten el rango más bajo -> N=1,
        máxima oportunidad -- sin tratar Ŝ=0 como caso especial."""
        cobertura = np.array([0.0, 5.0, 10.0])
        tasa_d = np.zeros(3)
        tasa_s = np.zeros(3)
        o = indice_oportunidad(cobertura, tasa_d, tasa_s)
        assert o[0] == pytest.approx(1.0)  # N=1, ajuste=0 (tasas iguales)
        assert o[0] > o[1] > o[2]

    def test_ajuste_de_tendencia_se_acota_a_0_15(self) -> None:
        cobertura = np.array([5.0, 5.0])
        tasa_d = np.array([100.0, -100.0])  # brecha enorme, positiva y negativa
        tasa_s = np.zeros(2)
        o = indice_oportunidad(cobertura, tasa_d, tasa_s, k_normalizacion=K_OPORTUNIDAD_DEFECTO)
        # con cobertura empatada, N=0.5 para ambas; el ajuste satura en +-0.15.
        assert o[0] == pytest.approx(0.5 + 0.15)
        assert o[1] == pytest.approx(0.5 - 0.15)

    def test_resultado_siempre_en_0_1(self) -> None:
        rng = np.random.default_rng(1)
        cobertura = rng.uniform(0, 50, 200)
        tasa_d = rng.uniform(-10, 10, 200)
        tasa_s = rng.uniform(-10, 10, 200)
        o = indice_oportunidad(cobertura, tasa_d, tasa_s)
        assert np.all((o >= 0.0) & (o <= 1.0))

    def test_cobertura_nan_produce_oportunidad_nan(self) -> None:
        cobertura = np.array([np.nan, 5.0])
        o = indice_oportunidad(cobertura, np.zeros(2), np.zeros(2))
        assert np.isnan(o[0])
        assert not np.isnan(o[1])


class TestSensibilidadIndiceOportunidad:
    def test_estructura_del_resultado(self) -> None:
        rng = np.random.default_rng(2)
        n = 50
        cobertura = rng.uniform(0, 50, n)
        tasa_d = rng.uniform(-5, 5, n)
        tasa_s = rng.uniform(-5, 5, n)
        claves = pd.Index([f"AGEB{i}" for i in range(n)])
        resultado = sensibilidad_indice_oportunidad(cobertura, tasa_d, tasa_s, claves)
        assert resultado["k_candidatos"] == [3.0, 5.0, 8.0]
        assert isinstance(resultado["claves_con_cambio_sustancial"], list)
        assert resultado["n_con_cambio"] == len(resultado["claves_con_cambio_sustancial"])

    def test_sin_dispersion_de_tendencia_no_hay_cambios(self) -> None:
        """Si tasa_d == tasa_s en todos lados, el ajuste es 0 para cualquier K -> ningún
        cambio de orden entre K=3 y K=8."""
        n = 30
        cobertura = np.linspace(0, 100, n)
        tasa_d = np.zeros(n)
        tasa_s = np.zeros(n)
        claves = pd.Index([f"AGEB{i}" for i in range(n)])
        resultado = sensibilidad_indice_oportunidad(cobertura, tasa_d, tasa_s, claves)
        assert resultado["n_con_cambio"] == 0


class TestParidadIndiceOportunidadPythonJs:
    """Fixture compartido con `frontend/tests/fixtures/paridad_oportunidad.js`, consumido por
    `frontend/tests/pruebas_composicion.js` (F-4, `correccion/avance_plan.md` punto 30.iii).

    Los vectores de entrada y `esperado` de abajo deben ser LITERALMENTE iguales a los del
    fixture JS. Si alguien cambia `features.indice_oportunidad` o
    `composicion.indiceOportunidad` sin actualizar el otro lado, una de las dos pruebas falla:
    ese es el propósito. Casos: cobertura 0 (máxima oportunidad), cobertura alta, tasas
    iguales (ajuste 0), `NaN` propagado, y ajuste saturado (`clip` a ±0.15) en ambos sentidos.
    """

    def test_mismos_vectores_que_el_fixture_js(self) -> None:
        cobertura = np.array([0.0, 1000.0, 500.0, np.nan, 250.0, 4000.0, 0.0])
        tasa_d = np.array([-3.0, -3.0, 2.0, -3.0, 0.0, -5.0, 1.0])
        tasa_s = np.array([-1.0, -1.0, 2.0, -1.0, 5.0, -6.0, -4.0])
        k = 5.0
        esperado = [0.75, 0.05, 0.4, None, 0.45, 0.15, 1.0]

        o = indice_oportunidad(cobertura, tasa_d, tasa_s, k)

        assert len(o) == len(esperado)
        for valor, esp in zip(o, esperado):
            if esp is None:
                assert np.isnan(valor)
            else:
                assert valor == pytest.approx(esp, abs=1e-9)


class TestIndiceDisponibilidad:
    def test_cobertura_alta_da_disponibilidad_alta(self) -> None:
        """A diferencia de indice_oportunidad, NO se invierte el rango: cobertura alta =
        disponibilidad alta."""
        cobertura = np.array([0.0, 5.0, 10.0])
        confianza = np.array(["baja", "baja", "baja"])
        f = indice_disponibilidad(cobertura, np.zeros(3), confianza)
        assert f[0] < f[1] < f[2]

    def test_confianza_baja_no_premia_tendencia_positiva(self) -> None:
        cobertura = np.array([5.0, 5.0])
        tasa_s = np.array([100.0, 100.0])
        f_baja = indice_disponibilidad(cobertura, tasa_s, np.array(["baja", "baja"]))
        f_alta = indice_disponibilidad(cobertura, tasa_s, np.array(["alta", "alta"]))
        assert f_baja[0] == pytest.approx(0.5)  # sin premio: factor_confianza=0
        assert f_alta[0] == pytest.approx(0.5 + 0.15)  # premio máximo

    def test_resultado_siempre_en_0_1(self) -> None:
        rng = np.random.default_rng(3)
        n = 100
        cobertura = rng.uniform(0, 50, n)
        tasa_s = rng.uniform(-20, 20, n)
        confianza = rng.choice(["alta", "media", "baja"], n)
        f = indice_disponibilidad(cobertura, tasa_s, confianza)
        assert np.all((f >= 0.0) & (f <= 1.0))


class TestConstruirSensibilidadOportunidad:
    """`exportar.py` llama esto sobre el contrato v1.4 ya construido (F-4, punto 30): antes
    nadie llamaba `sensibilidad_indice_oportunidad` fuera de los tests, y `diagnostico.json`
    nunca traía la sensibilidad obligatoria a `K`."""

    def _capa_demanda_todas(self) -> dict:
        return {
            "0900200010010": {"nivel_base": 100.0, "h": {"h3": {"delta_pct": -10.0, "tasa_anual_pct": -3.5}}},
            "0900200010020": {"nivel_base": 50.0, "h": {"h3": {"delta_pct": 5.0, "tasa_anual_pct": 1.6}}},
            "0900200010030": {"nivel_base": 0.0, "h": {"h3": {"delta_pct": None, "tasa_anual_pct": None}}},
        }

    def _capa_rama(self, niveles: dict[str, float]) -> dict:
        return {
            cve: {"celdas": {"celda_a": {"nivel_base": nb, "h": {"h3": {"delta_pct": -5.0}}}}}
            for cve, nb in niveles.items()
        }

    def test_estructura_por_rama(self) -> None:
        capa_demanda_todas = self._capa_demanda_todas()
        capas_ramas = {
            "educacion": self._capa_rama({"0900200010010": 3.0, "0900200010020": 1.0, "0900200010030": 0.0}),
            "salud": self._capa_rama({"0900200010010": 0.0, "0900200010020": 2.0, "0900200010030": 0.0}),
        }
        resultado = construir_sensibilidad_oportunidad(capa_demanda_todas, capas_ramas)
        assert set(resultado.keys()) == {"educacion", "salud"}
        for bloque in resultado.values():
            assert bloque["k_candidatos"] == [3.0, 5.0, 8.0]
            assert isinstance(bloque["claves_con_cambio_sustancial"], list)

    def test_ageb_con_demanda_invalida_no_se_evalua(self) -> None:
        """`0900200010030` no tiene `delta_pct` (demanda inválida) -> `D̂` inválido -> `sin_datos`
        -> se excluye de `n_evaluado` (cobertura NaN, metodología §10.1)."""
        capa_demanda_todas = self._capa_demanda_todas()
        capas_ramas = {"educacion": self._capa_rama({"0900200010010": 3.0, "0900200010020": 1.0, "0900200010030": 5.0})}
        resultado = construir_sensibilidad_oportunidad(capa_demanda_todas, capas_ramas)
        assert resultado["educacion"]["n_evaluado"] == 2


@pytest.mark.datos
class TestIndiceOportunidadConDatosReales:
    def test_educacion_primaria_de_punta_a_punta(self) -> None:
        """Extremo a extremo con datos reales: simula demanda (segmento 'primaria') y oferta
        (celda 'primaria' de educación), calcula cobertura e índice de oportunidad, y verifica
        que ninguna AGEB con oferta cero y demanda válida quede sin_datos."""
        from chipos.config import HORIZONTES, SEMILLA, T_2020
        from chipos.io import (
            CORTES_OFERTA,
            conectar,
            leer_censo_panel,
            leer_conapo_0a14,
            leer_denue_infancias,
            leer_equivalencia,
            leer_universo_ageb,
        )
        from chipos.modelos import ajustar_oferta, simular_demanda, simular_oferta
        from chipos.panel import construir_panel_demanda, construir_panel_oferta_celda, filtro_celda_educacion

        universo = leer_universo_ageb()
        censo = leer_censo_panel()
        equivalencia = leer_equivalencia()
        conapo = leer_conapo_0a14()
        con = conectar()
        infancias = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))

        panel_d = construir_panel_demanda(censo, equivalencia, universo, segmento="primaria")
        # "primaria" ya no es una sola celda (Fase 5 rework: cruce por sector) -- se suman las 3
        # celdas de sector para reproducir el nivel/tipo "primaria" completo, sin filtrar sector.
        filtro_primaria = sum(
            (filtro_celda_educacion(infancias, f"primaria__{s}") for s in ("publico", "privado", "no_especificado")),
            start=pd.Series(False, index=infancias.index),
        )
        panel_o_celda = construir_panel_oferta_celda(infancias, universo, filtro_primaria)

        rng = np.random.default_rng(SEMILLA)
        sim_d = simular_demanda(panel_d, conapo, rng)
        sim_o = simular_oferta(ajustar_oferta(panel_o_celda), rng)

        claves = pd.Index(sorted(set(sim_d.clave) | set(sim_o.clave)), name="cvegeo")
        t_h3 = HORIZONTES["h3"]

        nivel_d = nivel_rama_por_celda({"todas": sim_d}, T_2020, t_h3, claves)
        nivel_o = nivel_rama_por_celda({"primaria": sim_o}, max(CORTES_OFERTA.values()), t_h3, claves)

        mediana_d = np.median(nivel_d, axis=1)
        mediana_o = np.median(nivel_o, axis=1)
        cobertura = cobertura_proyectada(mediana_o, mediana_d)

        # Al menos una AGEB con demanda válida y oferta cero debe existir y dar cobertura 0 (no NaN).
        con_demanda = mediana_d > 0
        assert np.any((mediana_o == 0) & con_demanda)
        idx_cero = np.where((mediana_o == 0) & con_demanda)[0][0]
        assert cobertura[idx_cero] == 0.0
        assert not np.isnan(cobertura[idx_cero])


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

    escenarios = con_disco["oferta_escenarios_denue_2024"]["ageb"]
    assert len(escenarios) > 0
    # el rango A-B debe ser positivo para al menos algunas AGEB (la caída 2024 es real).
    assert any(v["rango_pp_anio"] > 0 for v in escenarios.values())
