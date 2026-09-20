"""Tests de `chipos.modelos` (B5: `veredicto`/`confianza`; B6: demanda;
B7a: oferta).

B5 cubre solo la regla de decisión y de confianza (plan §5.3, metodología
§7). B6/B7a cubren el algoritmo de simulación completo (plan §5.1, §5.2,
§5.4; fórmulas exactas en `docs/metodologia.md` §2 y §6).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from chipos.config import HORIZONTES, HORIZONTES_OFERTA, SEMILLA, T_2010, T_2020, T_HOR
from chipos.io import CORTES_OFERTA
from chipos.modelos import (
    Simulacion,
    _control_por_razon,
    _newton_raphson_poisson,
    agregar_alcaldia,
    ajustar_oferta,
    confianza,
    contraccion_eb,
    resumir,
    simular_demanda,
    simular_oferta,
    tasa_conapo,
    tasa_directa,
    veredicto,
)


# ---------------------------------------------------------------------------
# veredicto
# ---------------------------------------------------------------------------


class TestVeredicto:
    def test_sube_en_el_umbral(self) -> None:
        v, p_dec = veredicto(p_sube=0.80, p_baja=0.05, p_mantiene=0.15)
        assert v == "sube"
        assert p_dec == 0.80

    def test_justo_debajo_del_umbral_no_es_sube(self) -> None:
        v, p_dec = veredicto(p_sube=0.7999, p_baja=0.05, p_mantiene=0.1501)
        assert v == "se_mantiene"
        assert p_dec == 0.1501

    def test_baja_en_el_umbral(self) -> None:
        v, p_dec = veredicto(p_sube=0.05, p_baja=0.80, p_mantiene=0.15)
        assert v == "baja"
        assert p_dec == 0.80

    def test_justo_debajo_del_umbral_no_es_baja(self) -> None:
        v, p_dec = veredicto(p_sube=0.05, p_baja=0.7999, p_mantiene=0.1501)
        assert v == "se_mantiene"
        assert p_dec == 0.1501

    def test_se_mantiene_en_el_umbral_de_p_mantiene(self) -> None:
        v, p_dec = veredicto(p_sube=0.30, p_baja=0.20, p_mantiene=0.50)
        assert v == "se_mantiene"
        assert p_dec == 0.50

    def test_se_mantiene_residual_bajo_p_mantiene(self) -> None:
        """`p_mantiene < 0.50`: sigue siendo `se_mantiene` (rama residual)."""
        v, p_dec = veredicto(p_sube=0.30, p_baja=0.20, p_mantiene=0.49)
        assert v == "se_mantiene"
        assert p_dec == 0.49

    def test_prioridad_sube_sobre_baja(self) -> None:
        """Orden de evaluación: `sube` se comprueba antes que `baja`."""
        v, p_dec = veredicto(p_sube=0.85, p_baja=0.90, p_mantiene=0.0)
        assert v == "sube"
        assert p_dec == 0.85


# ---------------------------------------------------------------------------
# confianza
# ---------------------------------------------------------------------------


class TestConfianza:
    def test_alta_en_el_umbral_estable(self) -> None:
        nivel = confianza(
            p_dec=0.95, estable_lambda=True, n_obs=2, d2020=200.0, tope=None
        )
        assert nivel == "alta"

    def test_justo_debajo_de_alta_es_media(self) -> None:
        nivel = confianza(
            p_dec=0.9499, estable_lambda=True, n_obs=2, d2020=200.0, tope=None
        )
        assert nivel == "media"

    def test_media_en_el_umbral(self) -> None:
        nivel = confianza(
            p_dec=0.80, estable_lambda=True, n_obs=2, d2020=200.0, tope=None
        )
        assert nivel == "media"

    def test_justo_debajo_de_media_es_baja(self) -> None:
        nivel = confianza(
            p_dec=0.7999, estable_lambda=True, n_obs=2, d2020=200.0, tope=None
        )
        assert nivel == "baja"

    def test_inestabilidad_baja_alta_a_media(self) -> None:
        nivel = confianza(
            p_dec=0.99, estable_lambda=False, n_obs=2, d2020=200.0, tope=None
        )
        assert nivel == "media"

    def test_inestabilidad_baja_media_a_baja(self) -> None:
        nivel = confianza(
            p_dec=0.85, estable_lambda=False, n_obs=2, d2020=200.0, tope=None
        )
        assert nivel == "baja"

    def test_inestabilidad_no_empeora_baja(self) -> None:
        nivel = confianza(
            p_dec=0.50, estable_lambda=False, n_obs=2, d2020=200.0, tope=None
        )
        assert nivel == "baja"

    def test_n_obs_1_fuerza_baja_aunque_p_dec_sea_alto(self) -> None:
        nivel = confianza(
            p_dec=0.99, estable_lambda=True, n_obs=1, d2020=200.0, tope=None
        )
        assert nivel == "baja"

    def test_d2020_justo_bajo_el_umbral_fuerza_baja(self) -> None:
        nivel = confianza(
            p_dec=0.99, estable_lambda=True, n_obs=2, d2020=99.999, tope=None
        )
        assert nivel == "baja"

    def test_d2020_justo_en_el_umbral_no_fuerza_baja(self) -> None:
        nivel = confianza(
            p_dec=0.99, estable_lambda=True, n_obs=2, d2020=100.0, tope=None
        )
        assert nivel == "alta"

    def test_d2020_none_no_aplica_el_criterio(self) -> None:
        """Capa de oferta: no hay `D_2020`, se pasa `None` sin forzar `baja`."""
        nivel = confianza(
            p_dec=0.99, estable_lambda=True, n_obs=3, d2020=None, tope=None
        )
        assert nivel == "alta"

    def test_tope_media_limita_alta(self) -> None:
        nivel = confianza(
            p_dec=0.99, estable_lambda=True, n_obs=2, d2020=200.0, tope="media"
        )
        assert nivel == "media"

    def test_tope_media_no_sube_baja_a_media(self) -> None:
        nivel = confianza(
            p_dec=0.50, estable_lambda=True, n_obs=2, d2020=200.0, tope="media"
        )
        assert nivel == "baja"

    def test_tope_baja_limita_todo(self) -> None:
        nivel = confianza(
            p_dec=0.99, estable_lambda=True, n_obs=2, d2020=200.0, tope="baja"
        )
        assert nivel == "baja"

    def test_tope_oferta_media_caso_tipico(self) -> None:
        """Capa de oferta: `d2020=None`, `tope='media'` (metodología §6)."""
        nivel = confianza(
            p_dec=0.96, estable_lambda=True, n_obs=3, d2020=None, tope="media"
        )
        assert nivel == "media"

    @pytest.mark.parametrize("tope", ["alta", None])
    def test_tope_alta_o_ninguno_no_limita(self, tope: str | None) -> None:
        nivel = confianza(
            p_dec=0.95, estable_lambda=True, n_obs=2, d2020=200.0, tope=tope
        )
        assert nivel == "alta"

    def test_orden_forzado_baja_y_tope_media_siguen_en_baja(self) -> None:
        """`n_obs=1` fuerza `baja`; un `tope` mayor no la puede subir."""
        nivel = confianza(
            p_dec=0.99, estable_lambda=True, n_obs=1, d2020=200.0, tope="media"
        )
        assert nivel == "baja"


# ---------------------------------------------------------------------------
# integración veredicto + confianza (rama residual del plan §5.3)
# ---------------------------------------------------------------------------


def test_veredicto_residual_produce_confianza_baja() -> None:
    """`p_mantiene < P_MANTIENE` (rama "si no") acaba en confianza `baja`.

    Verifica la nota de `veredicto()`: no hace falta forzar `baja` a mano
    porque `p_mantiene` queda automáticamente por debajo de `P_DECISION`.
    """
    v, p_dec = veredicto(p_sube=0.30, p_baja=0.25, p_mantiene=0.45)
    assert v == "se_mantiene"
    nivel = confianza(
        p_dec=p_dec, estable_lambda=True, n_obs=2, d2020=200.0, tope=None
    )
    assert nivel == "baja"


# ---------------------------------------------------------------------------
# B6: tasa_directa, contraccion_eb, tasa_conapo
# ---------------------------------------------------------------------------


class TestTasaDirecta:
    def test_formula_basica(self) -> None:
        r_hat, psi = tasa_directa(np.array([120.0]), np.array([110.0]), 9.76)
        esperado_r = np.log((110.0 + 0.5) / (120.0 + 0.5)) / 9.76
        esperado_psi = (1.0 / 110.5 + 1.0 / 120.5) / 9.76**2
        assert r_hat[0] == pytest.approx(esperado_r)
        assert psi[0] == pytest.approx(esperado_psi)

    def test_vectorizado(self) -> None:
        r_hat, psi = tasa_directa(
            np.array([100.0, 50.0, 0.0]), np.array([100.0, 25.0, 10.0]), 9.76
        )
        assert r_hat.shape == (3,)
        assert psi.shape == (3,)
        assert r_hat[0] == pytest.approx(0.0, abs=1e-9)
        assert r_hat[1] < 0  # cae a la mitad
        assert r_hat[2] > 0  # crece de 0 a 10


class TestContraccionEB:
    def test_tau2_grande_r_tilde_igual_r_hat(self) -> None:
        """psi ínfimo y homogéneo, r_hat muy disperso -> tau2 grande -> r_tilde ~ r_hat."""
        rng = np.random.default_rng(1)
        n = 30
        rho_m = np.zeros(n)
        r_hat = rng.normal(0.0, 0.5, n)
        psi = np.full(n, 1e-6)

        r_tilde, var_post, tau2 = contraccion_eb(r_hat, psi, rho_m)

        assert tau2 > 0.05  # dominado por la dispersión de r_hat, no por psi
        assert np.max(np.abs(r_tilde - r_hat)) < 1e-4
        assert np.all(var_post < 1e-4)  # var. posterior ~ (1-B)*psi ~ psi, chica

    def test_psi_grande_r_tilde_tiende_a_rho_m(self) -> None:
        """Una unidad con psi mucho mayor que tau2 -> esa unidad se contrae a rho_m."""
        rng = np.random.default_rng(3)
        n = 20
        rho_m = np.zeros(n)
        r_hat = rng.normal(0.0, 0.05, n)
        psi = np.full(n, 0.001)
        psi[0] = 0.05  # outlier: 50x el resto, pero no tanto como para forzar tau2=0

        r_tilde, var_post, tau2 = contraccion_eb(r_hat, psi, rho_m)

        assert tau2 > 0  # no degenera a la contracción total de todas las unidades
        b0 = psi[0] / (psi[0] + tau2)
        assert b0 > 0.99  # la unidad de psi grande está casi totalmente contraída
        assert abs(r_tilde[0] - rho_m[0]) < 0.02
        # el resto, con psi típico, se contrae solo parcialmente (no al límite).
        b_resto = psi[1:] / (psi[1:] + tau2)
        assert b_resto.mean() < 0.9

    def test_tau2_nunca_negativo(self) -> None:
        """`tau2 = max(0, ...)`: si mean(psi) > mean((r_hat-rho_m)**2), tau2 = 0."""
        r_hat = np.array([0.01, -0.01, 0.02, -0.02])
        rho_m = np.zeros(4)
        psi = np.full(4, 10.0)  # psi enorme frente a la dispersión de r_hat

        _, _, tau2 = contraccion_eb(r_hat, psi, rho_m)

        assert tau2 == 0.0


class TestTasaConapo:
    @pytest.fixture
    def conapo_anual(self) -> pd.DataFrame:
        """Serie CONAPO anual sintética (dos alcaldías, 2009-2028), decreciente."""
        filas = []
        for mun, base, tasa in [("002", 90000.0, -0.02), ("003", 150000.0, -0.015)]:
            for anio in range(2009, 2029):
                pob = base * np.exp(tasa * (anio - 2009))
                filas.append({"cve_mun": mun, "anio": anio, "pob_0a14": pob})
        return pd.DataFrame(filas)

    def test_tasa_recupera_la_tasa_generadora(self, conapo_anual: pd.DataFrame) -> None:
        """Con una serie exponencial pura, `tasa_conapo` recupera la tasa exacta."""
        r = tasa_conapo(conapo_anual, 2020.5, 2027.5)
        assert r.loc["002"] == pytest.approx(-0.02, abs=1e-9)
        assert r.loc["003"] == pytest.approx(-0.015, abs=1e-9)

    def test_interpolacion_en_tiempo_no_entero(self, conapo_anual: pd.DataFrame) -> None:
        """`t0`/`t1` fuera de los puntos `anio+0.5` también recuperan la tasa exacta
        (interpolación log-lineal == exponencial exacta en una serie exponencial)."""
        r = tasa_conapo(conapo_anual, T_2010, T_2020)
        assert r.loc["002"] == pytest.approx(-0.02, abs=1e-6)


class TestControlPorRazon:
    def test_reproduce_la_razon_conapo_por_alcaldia(self) -> None:
        rng = np.random.default_rng(7)
        cve_mun = np.array(["002"] * 3 + ["003"] * 4)
        n, n_sim = len(cve_mun), 50
        r_pre = rng.normal(-0.02, 0.01, size=(n, n_sim))
        base = rng.uniform(50, 500, size=n)
        razon = pd.Series({"002": 1.05, "003": 0.88})
        horizonte = 7.3

        r_ctrl = _control_por_razon(r_pre, base, cve_mun, razon, horizonte)

        for m in ("002", "003"):
            idx = np.where(cve_mun == m)[0]
            proyectado = (base[idx, None] * np.exp(r_ctrl[idx, :] * horizonte)).sum(axis=0)
            razon_obtenida = proyectado / base[idx].sum()
            assert np.max(np.abs(razon_obtenida - razon[m])) < 1e-9

    def test_mantiene_la_forma_log_lineal(self) -> None:
        """El ajuste es un desplazamiento constante por alcaldía y réplica."""
        cve_mun = np.array(["002", "002"])
        r_pre = np.array([[0.01, -0.02], [0.03, 0.00]])
        base = np.array([100.0, 200.0])
        razon = pd.Series({"002": 1.0})
        r_ctrl = _control_por_razon(r_pre, base, cve_mun, razon, horizonte=7.0)
        diferencia = r_ctrl - r_pre
        # misma alcaldía y misma réplica -> mismo ajuste para ambas unidades.
        assert diferencia[0, 0] == pytest.approx(diferencia[1, 0])
        assert diferencia[0, 1] == pytest.approx(diferencia[1, 1])


# ---------------------------------------------------------------------------
# B6: simular_demanda (integración)
# ---------------------------------------------------------------------------


@pytest.fixture
def conapo_anual_dos_mun() -> pd.DataFrame:
    filas = []
    for mun, base, tasa in [("002", 90000.0, -0.015), ("003", 150000.0, -0.02)]:
        for anio in range(2009, 2029):
            pob = base * np.exp(tasa * (anio - 2009))
            filas.append({"cve_mun": mun, "anio": anio, "pob_0a14": pob})
    return pd.DataFrame(filas)


class TestSimularDemanda:
    def test_determinismo_con_semilla_fija(
        self, panel_demanda_sintetico: pd.DataFrame, conapo_anual_dos_mun: pd.DataFrame
    ) -> None:
        rng1 = np.random.default_rng(SEMILLA)
        rng2 = np.random.default_rng(SEMILLA)
        sim1 = simular_demanda(panel_demanda_sintetico, conapo_anual_dos_mun, rng1, n_sim=200)
        sim2 = simular_demanda(panel_demanda_sintetico, conapo_anual_dos_mun, rng2, n_sim=200)

        np.testing.assert_array_equal(sim1.r_fut, sim2.r_fut)
        np.testing.assert_array_equal(sim1.clave, sim2.clave)
        for lam in sim1.r_fut_lambdas:
            np.testing.assert_array_equal(sim1.r_fut_lambdas[lam], sim2.r_fut_lambdas[lam])

    def test_excluye_sin_datos_e_incluye_sin_contraparte(
        self, panel_demanda_sintetico: pd.DataFrame, conapo_anual_dos_mun: pd.DataFrame
    ) -> None:
        rng = np.random.default_rng(SEMILLA)
        sim = simular_demanda(panel_demanda_sintetico, conapo_anual_dos_mun, rng, n_sim=100)

        # la AGEB rural (motivo_sin_datos='rural') no debe aparecer.
        assert "090150001" not in set(sim.clave)
        # sin_contraparte (0900300010128) sí, con n_obs=1.
        idx = list(sim.clave).index("0900300010128")
        assert sim.n_obs[idx] == 1
        # las demás (misma/division) tienen n_obs=2.
        idx_misma = list(sim.clave).index("0900200011991")
        assert sim.n_obs[idx_misma] == 2

    def test_resumir_produce_veredictos_validos(
        self, panel_demanda_sintetico: pd.DataFrame, conapo_anual_dos_mun: pd.DataFrame
    ) -> None:
        rng = np.random.default_rng(SEMILLA)
        sim = simular_demanda(panel_demanda_sintetico, conapo_anual_dos_mun, rng, n_sim=300)
        res = resumir(sim, HORIZONTES)["h3"]

        assert set(res["veredicto"]) <= {"sube", "se_mantiene", "baja"}
        assert set(res["confianza"]) <= {"alta", "media", "baja"}
        # sin_contraparte (n_obs=1) siempre fuerza confianza baja.
        fila = res.set_index("clave").loc["0900300010128"]
        assert fila["confianza"] == "baja"
        # las AGEB de ic95 respetan ic95[0] <= delta_pct <= ic95[1].
        for delta_pct, ic in zip(res["delta_pct"], res["ic95"]):
            assert ic[0] <= delta_pct <= ic[1]

    def test_lam_fijo_se_usa_en_la_replica_principal(
        self, panel_demanda_sintetico: pd.DataFrame, conapo_anual_dos_mun: pd.DataFrame
    ) -> None:
        """Con `lam` fijo, la réplica principal coincide con la variante de
        `r_fut_lambdas` para ese mismo valor (mismos sorteos subyacentes)."""
        rng1 = np.random.default_rng(SEMILLA)
        rng2 = np.random.default_rng(SEMILLA)
        sim_fijo = simular_demanda(
            panel_demanda_sintetico, conapo_anual_dos_mun, rng1, n_sim=150, lam=0.6
        )
        sim_random = simular_demanda(
            panel_demanda_sintetico, conapo_anual_dos_mun, rng2, n_sim=150, lam=None
        )
        # mismos sorteos de r_post/eps (misma semilla), solo difiere lam de la
        # réplica principal: la principal de `sim_fijo` debe coincidir con la
        # variante lam=0.6 de `sim_random` (misma lam, mismos sorteos).
        np.testing.assert_allclose(sim_fijo.r_fut, sim_random.r_fut_lambdas[0.6])


# ---------------------------------------------------------------------------
# B6: tau agrupado sobre datos reales (validación contra docs/metodologia.md §3)
# ---------------------------------------------------------------------------


@pytest.mark.datos
def test_tau_agrupado_datos_reales_aproxima_metodologia() -> None:
    """Reproduce el diagnóstico documentado en `docs/metodologia.md` §3:
    "2,268 AGEB 'misma unidad' con >= 20 niños en ambos censos ... tau
    intra-alcaldía 1.89 %/año". Sirve para validar que `tasa_directa` +
    `contraccion_eb` reproducen la cifra de referencia (no es exactamente el
    universo que usa `simular_demanda`, que opera sobre todas las AGEB con
    dato, plan §5.1: "agrupado en toda la CDMX")."""
    from chipos.io import leer_censo_panel, leer_equivalencia, leer_universo_ageb
    from chipos.panel import construir_panel_demanda

    censo = leer_censo_panel()
    equivalencia = leer_equivalencia()
    universo = leer_universo_ageb()
    panel = construir_panel_demanda(censo, equivalencia, universo)

    subconjunto = panel.loc[
        (panel["relacion"] == "misma") & (panel["d_2010"] >= 20) & (panel["d_2020"] >= 20)
    ]
    assert len(subconjunto) == 2268  # cifra documentada en metodología §3

    dt = T_2020 - T_2010
    r_hat, psi = tasa_directa(
        subconjunto["d_2010"].to_numpy(dtype=float),
        subconjunto["d_2020"].to_numpy(dtype=float),
        dt,
    )
    agregado = subconjunto.groupby("cve_mun")[["d_2010", "d_2020"]].sum()
    rho_m_serie = np.log((agregado["d_2020"] + 0.5) / (agregado["d_2010"] + 0.5)) / dt
    rho_m_por_ageb = subconjunto["cve_mun"].map(rho_m_serie).to_numpy(dtype=float)

    _, _, tau2 = contraccion_eb(r_hat, psi, rho_m_por_ageb)
    tau_pct = np.sqrt(tau2) * 100

    assert tau_pct == pytest.approx(1.89, abs=0.1)


# ---------------------------------------------------------------------------
# B7a: Newton-Raphson vectorizado == GLM Poisson de statsmodels
# ---------------------------------------------------------------------------


class TestNewtonRaphsonPoisson:
    def test_paridad_con_statsmodels(self) -> None:
        tiempos = np.array(sorted(CORTES_OFERTA.values()))
        t_centro = CORTES_OFERTA["2019-11"]
        x = np.column_stack([np.ones(3), tiempos - t_centro])
        # conteos "bien comportados" (sin separación perfecta / conteos todos
        # nulos salvo uno, que hace divergir la MLE y no converge igual en
        # ambas implementaciones).
        y = np.array(
            [
                [5.0, 4.0, 2.0],
                [0.0, 1.0, 0.0],
                [10.0, 12.0, 15.0],
                [3.0, 3.0, 3.0],
                [8.0, 5.0, 4.0],
            ]
        )

        beta, cov = _newton_raphson_poisson(x, y)

        for i in range(y.shape[0]):
            modelo = sm.GLM(y[i], x, family=sm.families.Poisson())
            resultado = modelo.fit()
            assert beta[i, 0] == pytest.approx(resultado.params[0], abs=1e-6)
            assert beta[i, 1] == pytest.approx(resultado.params[1], abs=1e-6)
            assert cov[i, 1, 1] == pytest.approx(resultado.cov_params()[1, 1], abs=1e-6)


# ---------------------------------------------------------------------------
# B7a: ajustar_oferta, simular_oferta
# ---------------------------------------------------------------------------


@pytest.fixture
def panel_oferta_para_ajuste() -> pd.DataFrame:
    cvegeos = ["0900200011991", "0900200012005", "0900300010112", "0900300010128"]
    conteos = {
        "0900200011991": [8, 6, 5],  # tendencia a la baja, con dato
        "0900200012005": [2, 3, 4],  # tendencia al alza, con dato
        "0900300010112": [0, 0, 0],  # sin ningún establecimiento -> sin_datos
        "0900300010128": [12, 10, 9],
    }
    cortes = sorted(CORTES_OFERTA.values())
    filas = [
        {"cvegeo": cve, "cve_mun": cve[2:5], "t": t, "s": s}
        for cve in cvegeos
        for t, s in zip(cortes, conteos[cve])
    ]
    return pd.DataFrame(filas)


class TestAjustarOferta:
    def test_marca_sin_datos_si_s_es_cero_en_los_tres_cortes(
        self, panel_oferta_para_ajuste: pd.DataFrame
    ) -> None:
        ajuste = ajustar_oferta(panel_oferta_para_ajuste)
        fila = ajuste.set_index("cvegeo").loc["0900300010112"]
        assert fila["sin_datos"]
        assert pd.isna(fila["b_hat"]) and pd.isna(fila["var_b"])

    def test_con_datos_tiene_b_hat_finito(self, panel_oferta_para_ajuste: pd.DataFrame) -> None:
        ajuste = ajustar_oferta(panel_oferta_para_ajuste)
        con_datos = ajuste.loc[~ajuste["sin_datos"]]
        assert con_datos["b_hat"].notna().all()
        assert (con_datos["var_b"] > 0).all()
        # AGEB con tendencia al alza -> b_hat > 0; a la baja -> b_hat < 0.
        assert ajuste.set_index("cvegeo").loc["0900200012005", "b_hat"] > 0
        assert ajuste.set_index("cvegeo").loc["0900200011991", "b_hat"] < 0


class TestSimularOferta:
    def test_excluye_sin_datos(self, panel_oferta_para_ajuste: pd.DataFrame) -> None:
        ajuste = ajustar_oferta(panel_oferta_para_ajuste)
        rng = np.random.default_rng(SEMILLA)
        sim = simular_oferta(ajuste, rng, n_sim=200)
        assert "0900300010112" not in set(sim.clave)

    def test_n_obs_siempre_3_y_d2020_conf_none(
        self, panel_oferta_para_ajuste: pd.DataFrame
    ) -> None:
        ajuste = ajustar_oferta(panel_oferta_para_ajuste)
        rng = np.random.default_rng(SEMILLA)
        sim = simular_oferta(ajuste, rng, n_sim=200)
        assert np.all(sim.n_obs == 3)
        assert sim.d2020_conf is None

    def test_confianza_nunca_alta(self, panel_oferta_para_ajuste: pd.DataFrame) -> None:
        """Tope `media` siempre en la capa de oferta (CLAUDE.md, metodología §6),
        incluso si la probabilidad decisiva es altísima (`p_dec=0.999`)."""
        assert confianza(p_dec=0.999, estable_lambda=True, n_obs=3, d2020=None, tope="media") == "media"

        ajuste = ajustar_oferta(panel_oferta_para_ajuste)
        rng = np.random.default_rng(SEMILLA)
        sim = simular_oferta(ajuste, rng, n_sim=500)
        res = resumir(sim, {"h3": HORIZONTES["h3"]})["h3"]
        assert "alta" not in set(res["confianza"])
        assert np.all(sim.tope == "media")


# ---------------------------------------------------------------------------
# agregar_alcaldia (§5.4): suma de réplicas AGEB == alcaldía
# ---------------------------------------------------------------------------


class TestAgregarAlcaldia:
    def test_suma_ageb_igual_a_alcaldia_por_replica(
        self, panel_demanda_sintetico: pd.DataFrame, conapo_anual_dos_mun: pd.DataFrame
    ) -> None:
        rng = np.random.default_rng(SEMILLA)
        sim = simular_demanda(panel_demanda_sintetico, conapo_anual_dos_mun, rng, n_sim=100)
        sim_mun = agregar_alcaldia(sim)

        for j, m in enumerate(sim_mun.cve_mun):
            idx = np.where(sim.cve_mun == m)[0]
            proyectado_ageb = (
                sim.base[idx, None] * np.exp(sim.r_fut[idx, :] * sim.horizonte_control)
            ).sum(axis=0)
            proyectado_mun = (
                sim_mun.base[j] * np.exp(sim_mun.r_fut[j, :] * sim_mun.horizonte_control)
            )
            np.testing.assert_allclose(proyectado_ageb, proyectado_mun, rtol=1e-9)
            assert sim_mun.base[j] == pytest.approx(sim.base[idx].sum())

    def test_n_obs_y_claves_de_alcaldia(
        self, panel_demanda_sintetico: pd.DataFrame, conapo_anual_dos_mun: pd.DataFrame
    ) -> None:
        rng = np.random.default_rng(SEMILLA)
        sim = simular_demanda(panel_demanda_sintetico, conapo_anual_dos_mun, rng, n_sim=50)
        sim_mun = agregar_alcaldia(sim)

        assert set(sim_mun.cve_mun) == set(sim.cve_mun)
        assert not pd.Series(sim_mun.clave).duplicated().any()
        assert np.all(sim_mun.n_obs <= 2)

    def test_agregacion_de_oferta_usa_tope_media(
        self, panel_oferta_para_ajuste: pd.DataFrame
    ) -> None:
        ajuste = ajustar_oferta(panel_oferta_para_ajuste)
        rng = np.random.default_rng(SEMILLA)
        sim = simular_oferta(ajuste, rng, n_sim=100)
        sim_mun = agregar_alcaldia(sim)
        assert np.all(sim_mun.tope == "media")
        assert np.all(sim_mun.n_obs == 3)
        res_mun = resumir(sim_mun, {"h3": HORIZONTES["h3"]})["h3"]
        assert "alta" not in set(res_mun["confianza"])


# ---------------------------------------------------------------------------
# resumir: horizontes de reporte 1/3/5 años (`correccion/rubrica.md` §5)
# ---------------------------------------------------------------------------


class TestResumirHorizontes:
    def test_mismo_veredicto_y_confianza_en_los_tres_horizontes(
        self, panel_demanda_sintetico: pd.DataFrame, conapo_anual_dos_mun: pd.DataFrame
    ) -> None:
        rng = np.random.default_rng(SEMILLA)
        sim = simular_demanda(panel_demanda_sintetico, conapo_anual_dos_mun, rng, n_sim=300)
        res = resumir(sim, HORIZONTES)

        assert set(res.keys()) == {"h1", "h3", "h5"}
        pd.testing.assert_series_equal(
            res["h1"]["veredicto"], res["h3"]["veredicto"], check_names=False
        )
        pd.testing.assert_series_equal(
            res["h3"]["veredicto"], res["h5"]["veredicto"], check_names=False
        )
        pd.testing.assert_series_equal(
            res["h1"]["confianza"], res["h3"]["confianza"], check_names=False
        )
        pd.testing.assert_series_equal(
            res["h3"]["confianza"], res["h5"]["confianza"], check_names=False
        )
        pd.testing.assert_series_equal(
            res["h3"]["tasa_anual_pct"], res["h5"]["tasa_anual_pct"], check_names=False
        )

        # `delta_pct` crece en magnitud (valor absoluto) de h1 -> h3 -> h5
        # (monotonía de `exp`, mismo signo de la tasa en cada unidad).
        mag_h1 = res["h1"]["delta_pct"].abs().to_numpy()
        mag_h3 = res["h3"]["delta_pct"].abs().to_numpy()
        mag_h5 = res["h5"]["delta_pct"].abs().to_numpy()
        assert np.all(mag_h3 >= mag_h1)
        assert np.all(mag_h5 >= mag_h3)

    def test_oferta_admite_h1_y_h3_nunca_h5(self, panel_oferta_para_ajuste: pd.DataFrame) -> None:
        ajuste = ajustar_oferta(panel_oferta_para_ajuste)
        rng = np.random.default_rng(SEMILLA)
        sim = simular_oferta(ajuste, rng, n_sim=200)
        res = resumir(sim, {h: HORIZONTES[h] for h in HORIZONTES_OFERTA})
        assert set(res.keys()) == {"h1", "h3"}
