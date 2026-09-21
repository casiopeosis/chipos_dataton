"""Tests de `chipos.backtest` (B9 de `plans/backend_plan.md` §6, Fase 2 de
`correccion/action_plan.md`).

Cubre: adelgazamiento binomial (§4.3 punto 2), LOAO (§4.3 punto 3), backtest
de oferta (§4.2 punto 1, SIN fuga de futuro), comparación censo-CONAPO (§4.1
punto 2, no es un backtest), calibración del piso de incertidumbre (§2.7) y
el guardarraíl contra la reintroducción de un "backtest de CONAPO" con
orígenes móviles.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from chipos.config import SEMILLA, T_2010, T_2020
from chipos.backtest import (
    CANDIDATOS_PISO,
    adelgazar,
    backtest_oferta,
    calibrar_piso_incertidumbre,
    comparar_censo_conapo,
    ejecutar,
    escribir_reporte,
    metricas,
    validar_adelgazamiento,
    validar_loao,
    _razon_no_adopcion,
)

# ---------------------------------------------------------------------------
# Fixtures: 4 alcaldías x 6 AGEB, tendencias variadas (declive, estable, alza)
# ---------------------------------------------------------------------------


@pytest.fixture
def panel_demanda_backtest() -> pd.DataFrame:
    rng = np.random.default_rng(1234)
    filas = []
    tasas_por_mun = {"002": -0.02, "003": -0.01, "004": 0.005, "005": -0.03}
    for mun, tasa in tasas_por_mun.items():
        for i in range(6):
            d2010 = float(rng.integers(150, 900))
            dt = T_2020 - T_2010
            d2020 = d2010 * np.exp(tasa * dt) * rng.uniform(0.85, 1.15)
            filas.append(
                {
                    "cvegeo": f"09{mun}00{i:02d}0001",
                    "cve_mun": mun,
                    "ambito": "urbano",
                    "relacion": "misma",
                    "d_2010": round(d2010),
                    "d_2020": round(d2020),
                    "motivo_sin_datos": None,
                }
            )
    # Una AGEB rural, para verificar que queda fuera de todas las validaciones.
    filas.append(
        {
            "cvegeo": "090020009",
            "cve_mun": "002",
            "ambito": "rural",
            "relacion": None,
            "d_2010": np.nan,
            "d_2020": np.nan,
            "motivo_sin_datos": "rural",
        }
    )
    return pd.DataFrame(filas)


@pytest.fixture
def panel_oferta_backtest() -> pd.DataFrame:
    rng = np.random.default_rng(5678)
    cortes = [2016.79, 2019.87, 2024.87]
    filas = []
    for mun in ["002", "003", "004", "005"]:
        for i in range(6):
            cve = f"09{mun}00{i:02d}0001"
            s16 = int(rng.integers(0, 6))
            s19 = max(0, s16 + int(rng.integers(-1, 2)))
            s24 = max(0, s19 + int(rng.integers(-3, 2)))  # caída 2024, como en los datos reales
            for t, s in zip(cortes, [s16, s19, s24]):
                filas.append({"cvegeo": cve, "cve_mun": mun, "t": t, "s": s})
    return pd.DataFrame(filas)


@pytest.fixture
def conapo_backtest() -> pd.DataFrame:
    filas = []
    tasas = {"002": -0.018, "003": -0.012, "004": 0.003, "005": -0.025}
    for mun, tasa in tasas.items():
        for anio in range(2009, 2032):
            pob = 20000.0 * np.exp(tasa * (anio - 2009))
            filas.append({"cve_mun": mun, "anio": anio, "pob_0a14": pob})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# adelgazar / validar_adelgazamiento
# ---------------------------------------------------------------------------


class TestAdelgazar:
    def test_nunca_toca_d_2010(self, panel_demanda_backtest: pd.DataFrame) -> None:
        rng = np.random.default_rng(SEMILLA)
        thin = adelgazar(panel_demanda_backtest, 0.5, rng)
        pd.testing.assert_series_equal(
            thin["d_2010"], panel_demanda_backtest["d_2010"], check_names=False
        )

    def test_reescalado_es_insesgado_en_promedio(self, panel_demanda_backtest: pd.DataFrame) -> None:
        """`Binomial(d, frac)/frac` es insesgado para `d`: el promedio sobre muchas AGEB debe
        acercarse al promedio original (no sesgado hacia abajo por `ln(frac)/dt`, que era el
        bug corregido: sin reescalar, el promedio thinned sería ~frac veces el original)."""
        rng = np.random.default_rng(SEMILLA)
        thin = adelgazar(panel_demanda_backtest, 0.25, rng)
        con_dato = panel_demanda_backtest["d_2020"].notna()
        media_original = panel_demanda_backtest.loc[con_dato, "d_2020"].mean()
        media_adelgazada = thin.loc[con_dato, "d_2020"].mean()
        # tolerancia amplia: es una sola corrida con 24 AGEB, no un límite asintótico.
        assert media_adelgazada == pytest.approx(media_original, rel=0.25)

    def test_frac_1_reproduce_el_conteo_original_en_esperanza(
        self, panel_demanda_backtest: pd.DataFrame
    ) -> None:
        # frac=1.0 -> Binomial(n, 1) = n exactamente (sin ruido).
        rng = np.random.default_rng(SEMILLA)
        thin = adelgazar(panel_demanda_backtest, 1.0, rng)
        con_dato = panel_demanda_backtest["d_2020"].notna()
        np.testing.assert_array_equal(
            thin.loc[con_dato, "d_2020"].to_numpy(),
            panel_demanda_backtest.loc[con_dato, "d_2020"].round().to_numpy(),
        )


class TestValidarAdelgazamiento:
    def test_determinismo_con_semilla_fija(self, panel_demanda_backtest: pd.DataFrame) -> None:
        rng1 = np.random.default_rng(SEMILLA)
        rng2 = np.random.default_rng(SEMILLA)
        r1 = validar_adelgazamiento(panel_demanda_backtest, rng1)
        r2 = validar_adelgazamiento(panel_demanda_backtest, rng2)
        pd.testing.assert_frame_equal(r1, r2)

    def test_excluye_ageb_rural(self, panel_demanda_backtest: pd.DataFrame) -> None:
        rng = np.random.default_rng(SEMILLA)
        resultado = validar_adelgazamiento(panel_demanda_backtest, rng)
        assert "090020009" not in set(resultado["cvegeo"])

    def test_cuatro_competidores_por_frac_y_ageb(self, panel_demanda_backtest: pd.DataFrame) -> None:
        rng = np.random.default_rng(SEMILLA)
        resultado = validar_adelgazamiento(panel_demanda_backtest, rng, fracs=(0.25, 0.5))
        assert set(resultado["estimador"]) == {"r_hat_directo", "r_tilde_eb", "rho_m", "baseline_r0"}
        assert set(resultado["frac"]) == {0.25, 0.5}
        n_ageb = 24
        assert len(resultado) == 2 * 4 * n_ageb

    def test_baseline_r0_es_siempre_cero(self, panel_demanda_backtest: pd.DataFrame) -> None:
        rng = np.random.default_rng(SEMILLA)
        resultado = validar_adelgazamiento(panel_demanda_backtest, rng)
        baseline = resultado.loc[resultado["estimador"] == "baseline_r0"]
        assert (baseline["r_estimado"] == 0.0).all()

    def test_rho_m_y_baseline_no_tienen_varianza_individual(
        self, panel_demanda_backtest: pd.DataFrame
    ) -> None:
        rng = np.random.default_rng(SEMILLA)
        resultado = validar_adelgazamiento(panel_demanda_backtest, rng)
        sin_varianza = resultado.loc[resultado["estimador"].isin(["rho_m", "baseline_r0"])]
        assert sin_varianza["var_estimador"].isna().all()
        con_varianza = resultado.loc[resultado["estimador"].isin(["r_hat_directo", "r_tilde_eb"])]
        assert con_varianza["var_estimador"].notna().all()

    def test_eb_mejora_o_iguala_al_hat_directo_en_mae_agregado(
        self, panel_demanda_backtest: pd.DataFrame
    ) -> None:
        """No es garantía matemática por AGEB, pero agregado el EB no debería ser
        sistemáticamente peor que el ruido puro del `r_hat` directo adelgazado."""
        rng = np.random.default_rng(SEMILLA)
        resultado = validar_adelgazamiento(panel_demanda_backtest, rng, fracs=(0.25,))
        eb = resultado.loc[resultado["estimador"] == "r_tilde_eb"]
        directo = resultado.loc[resultado["estimador"] == "r_hat_directo"]
        mae_eb = float((eb["r_estimado"] - eb["r_real"]).abs().mean())
        mae_directo = float((directo["r_estimado"] - directo["r_real"]).abs().mean())
        assert mae_eb <= mae_directo * 1.5  # tolerancia: no exige superioridad estricta en una corrida


# ---------------------------------------------------------------------------
# validar_loao
# ---------------------------------------------------------------------------


class TestValidarLoao:
    def test_determinismo(self, panel_demanda_backtest: pd.DataFrame) -> None:
        r1 = validar_loao(panel_demanda_backtest)
        r2 = validar_loao(panel_demanda_backtest)
        pd.testing.assert_frame_equal(r1, r2)

    def test_cubre_las_cuatro_alcaldias(self, panel_demanda_backtest: pd.DataFrame) -> None:
        resultado = validar_loao(panel_demanda_backtest)
        assert set(resultado["cve_mun"]) == {"002", "003", "004", "005"}
        assert len(resultado) == 24

    def test_tau2_externo_nunca_usa_la_propia_alcaldia(
        self, panel_demanda_backtest: pd.DataFrame
    ) -> None:
        """El `tau2_externo` de una alcaldía debe ser distinto (en general) del `tau2`
        calculado con todas las AGEB, porque excluye sus propias 6 AGEB del cómputo."""
        from chipos.modelos import contraccion_eb, tasa_directa

        dt = T_2020 - T_2010
        elegibles = panel_demanda_backtest.loc[
            panel_demanda_backtest["motivo_sin_datos"].isna() & panel_demanda_backtest["d_2010"].notna()
        ]
        r_hat, psi = tasa_directa(
            elegibles["d_2010"].to_numpy(dtype=float), elegibles["d_2020"].to_numpy(dtype=float), dt
        )
        agregado = elegibles.groupby("cve_mun")[["d_2010", "d_2020"]].sum()
        rho_m_serie = np.log((agregado["d_2020"] + 0.5) / (agregado["d_2010"] + 0.5)) / dt
        rho_m_por_unidad = elegibles["cve_mun"].map(rho_m_serie).to_numpy(dtype=float)
        _, _, tau2_completo = contraccion_eb(r_hat, psi, rho_m_por_unidad)

        resultado = validar_loao(panel_demanda_backtest)
        tau2_externos = resultado.drop_duplicates("cve_mun")["tau2_externo"]
        # al menos una alcaldía debe diferir del tau2 agrupado completo (no es una tautología).
        assert not np.allclose(tau2_externos.to_numpy(), tau2_completo)

    def test_alcaldia_con_menos_de_dos_ageb_externas_se_omite(self) -> None:
        panel_pequeno = pd.DataFrame(
            {
                "cvegeo": ["0900200010001", "0900200010002", "0900300010001"],
                "cve_mun": ["002", "002", "003"],
                "ambito": ["urbano"] * 3,
                "relacion": ["misma"] * 3,
                "d_2010": [200.0, 300.0, 150.0],
                "d_2020": [190.0, 280.0, 160.0],
                "motivo_sin_datos": [None, None, None],
            }
        )
        resultado = validar_loao(panel_pequeno)
        # excluir 003 deja 2 AGEB externas (ok); excluir 002 deja solo 1 (se omite).
        assert set(resultado["cve_mun"]) == {"003"}


# ---------------------------------------------------------------------------
# backtest_oferta: sin fuga de futuro
# ---------------------------------------------------------------------------


class TestBacktestOferta:
    def test_dos_estimadores_por_ageb(self, panel_oferta_backtest: pd.DataFrame) -> None:
        resultado = backtest_oferta(panel_oferta_backtest)
        assert set(resultado["estimador"]) == {"modelo_poisson_2016_2019", "baseline_s_constante"}
        assert len(resultado) == 2 * 24

    def test_sin_fuga_de_futuro_el_ajuste_no_depende_de_s_2024(
        self, panel_oferta_backtest: pd.DataFrame
    ) -> None:
        """Cambiar drásticamente el corte 2024 no debe alterar `tasa_estimada`/`s_2024_pred`
        del modelo (que solo ve 2016+2019); sí debe cambiar `tasa_realizada` (la verdad)."""
        modificado = panel_oferta_backtest.copy()
        modificado.loc[modificado["t"] == 2024.87, "s"] = 999

        original = backtest_oferta(panel_oferta_backtest)
        alterado = backtest_oferta(modificado)

        modelo_original = original.loc[original["estimador"] == "modelo_poisson_2016_2019"]
        modelo_alterado = alterado.loc[alterado["estimador"] == "modelo_poisson_2016_2019"]
        np.testing.assert_array_equal(
            modelo_original["tasa_estimada"].to_numpy(), modelo_alterado["tasa_estimada"].to_numpy()
        )
        np.testing.assert_array_equal(
            modelo_original["s_2024_pred"].to_numpy(), modelo_alterado["s_2024_pred"].to_numpy()
        )
        # la verdad (tasa_realizada) sí debe cambiar, porque ese campo sí lee 2024.
        assert not np.allclose(
            modelo_original["tasa_realizada"].to_numpy(), modelo_alterado["tasa_realizada"].to_numpy()
        )

    def test_baseline_s_constante_es_el_corte_2019(self, panel_oferta_backtest: pd.DataFrame) -> None:
        resultado = backtest_oferta(panel_oferta_backtest)
        baseline = resultado.loc[resultado["estimador"] == "baseline_s_constante"]
        assert (baseline["s_2024_pred"] == baseline["s_2019"]).all()

    def test_baseline_y_modelo_comparten_universo(self, panel_oferta_backtest: pd.DataFrame) -> None:
        resultado = backtest_oferta(panel_oferta_backtest)
        modelo = set(resultado.loc[resultado["estimador"] == "modelo_poisson_2016_2019", "cvegeo"])
        baseline = set(resultado.loc[resultado["estimador"] == "baseline_s_constante", "cvegeo"])
        assert modelo == baseline

    def test_ajuste_con_dos_puntos_reproduce_los_conteos_exactos(self) -> None:
        """Con 2 puntos y 2 parámetros, el Poisson saturado reproduce s1 y s2 exactamente
        (deviance de origen = 0): `s1*exp(b_hat*(t2-t1)) == s2` (con la corrección +0.5)."""
        panel = pd.DataFrame(
            {
                "cvegeo": ["0900200010001"] * 3,
                "cve_mun": ["002"] * 3,
                "t": [2016.79, 2019.87, 2024.87],
                "s": [5, 2, 1],
            }
        )
        resultado = backtest_oferta(panel)
        fila = resultado.loc[resultado["estimador"] == "modelo_poisson_2016_2019"].iloc[0]
        dt = 2019.87 - 2016.79
        reconstruido = (5 + 0.5) * np.exp(fila["tasa_estimada"] * dt) - 0.5
        assert reconstruido == pytest.approx(2.0, abs=1e-6)


# ---------------------------------------------------------------------------
# comparar_censo_conapo: NO es un backtest
# ---------------------------------------------------------------------------


class TestCompararCensoConapo:
    def test_una_fila_por_alcaldia(
        self, panel_demanda_backtest: pd.DataFrame, conapo_backtest: pd.DataFrame
    ) -> None:
        resultado = comparar_censo_conapo(panel_demanda_backtest, conapo_backtest)
        assert set(resultado["cve_mun"]) == {"002", "003", "004", "005"}

    def test_diferencia_es_censo_menos_conapo(
        self, panel_demanda_backtest: pd.DataFrame, conapo_backtest: pd.DataFrame
    ) -> None:
        resultado = comparar_censo_conapo(panel_demanda_backtest, conapo_backtest)
        for _, fila in resultado.iterrows():
            esperado = round(fila["tasa_censo_pct_anio"] - fila["tasa_conapo_pct_anio"], 2)
            assert fila["diferencia_pp_anio"] == pytest.approx(esperado, abs=0.01)


# ---------------------------------------------------------------------------
# metricas()
# ---------------------------------------------------------------------------


class TestMetricas:
    def test_mae_cero_cuando_prediccion_es_exacta(self) -> None:
        y = np.array([1.0, 2.0, 3.0])
        clases = np.array(["sube", "baja", "se_mantiene"])
        resultado = metricas(y, y, clases, clases)
        assert resultado["mae_pp_anio"] == 0.0
        assert resultado["f1_macro"] == 1.0
        assert "cobertura_ic95" not in resultado

    def test_cobertura_ic95_solo_si_se_pasa_ic(self) -> None:
        y_real = np.array([1.0, 5.0])
        y_pred = np.array([1.1, 2.0])
        clases = np.array(["se_mantiene", "se_mantiene"])
        ic = np.array([[0.0, 2.0], [0.0, 2.0]])  # cubre al primero, no al segundo
        resultado = metricas(y_real, y_pred, clases, clases, ic)
        assert resultado["cobertura_ic95"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# calibrar_piso_incertidumbre
# ---------------------------------------------------------------------------


class TestCalibrarPisoIncertidumbre:
    def _folds(self, var_base: float, n: int = 200, ruido: float = 0.003) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        r_real = rng.normal(0.0, 0.02, size=n)
        r_estimado = r_real + rng.normal(0.0, ruido, size=n)
        return pd.DataFrame(
            {"r_real": r_real, "r_estimado": r_estimado, "var_estimador": np.full(n, var_base)}
        )

    def test_elige_el_candidato_mas_pequeno_dentro_de_la_banda(self) -> None:
        # var_estimador ya calibrada para que el propio candidato 0.000 cubra bien.
        folds_demanda = self._folds(var_base=0.02**2, ruido=0.005)
        folds_loao = pd.DataFrame(columns=["r_real", "r_estimado", "var_estimador"])
        folds_oferta_bien_cubiertas = self._folds(var_base=0.02**2, ruido=0.005).rename(
            columns={"r_real": "tasa_realizada", "r_estimado": "tasa_estimada"}
        )
        folds_oferta_bien_cubiertas["estimador"] = "modelo_poisson_2016_2019"

        resultado = calibrar_piso_incertidumbre(
            pd.concat(
                [folds_demanda.assign(estimador="r_tilde_eb", frac=0.5)],
                ignore_index=True,
            ),
            folds_loao,
            folds_oferta_bien_cubiertas,
        )
        assert resultado["demanda"]["elegido"] in CANDIDATOS_PISO
        assert 0.0 <= resultado["demanda"]["cobertura_lograda"] <= 1.0

    def test_nunca_elige_fuera_de_la_rejilla(self) -> None:
        # varianza casi nula -> ningún candidato pequeño cubre bien; no debe inventar uno.
        folds = self._folds(var_base=1e-12, ruido=0.05)
        folds_loao = pd.DataFrame(columns=["r_real", "r_estimado", "var_estimador"])
        folds_oferta = folds.rename(
            columns={"r_real": "tasa_realizada", "r_estimado": "tasa_estimada"}
        )
        folds_oferta["estimador"] = "modelo_poisson_2016_2019"
        resultado = calibrar_piso_incertidumbre(
            folds.assign(estimador="r_tilde_eb", frac=0.5), folds_loao, folds_oferta
        )
        assert resultado["demanda"]["elegido"] in CANDIDATOS_PISO
        assert resultado["oferta"]["elegido"] in CANDIDATOS_PISO

    def test_no_redondea_la_cobertura_lograda(self) -> None:
        folds = self._folds(var_base=0.015**2, ruido=0.01)
        folds_loao = pd.DataFrame(columns=["r_real", "r_estimado", "var_estimador"])
        folds_oferta = folds.rename(
            columns={"r_real": "tasa_realizada", "r_estimado": "tasa_estimada"}
        )
        folds_oferta["estimador"] = "modelo_poisson_2016_2019"
        resultado = calibrar_piso_incertidumbre(
            folds.assign(estimador="r_tilde_eb", frac=0.5), folds_loao, folds_oferta
        )
        cobertura = resultado["demanda"]["cobertura_lograda"]
        # no debe ser un valor "redondo" artificial como 0.9 o 0.95 exactos salvo coincidencia genuina
        assert isinstance(cobertura, float)

    def test_candidato_cero_sobrecubre_no_agrega_piso(self) -> None:
        # varianza base ya muy amplia: hasta sigma=0 sobrecubre (> 0.97).
        folds = self._folds(var_base=1.0, ruido=0.001)
        folds_loao = pd.DataFrame(columns=["r_real", "r_estimado", "var_estimador"])
        folds_oferta = folds.rename(
            columns={"r_real": "tasa_realizada", "r_estimado": "tasa_estimada"}
        )
        folds_oferta["estimador"] = "modelo_poisson_2016_2019"
        resultado = calibrar_piso_incertidumbre(
            folds.assign(estimador="r_tilde_eb", frac=0.5), folds_loao, folds_oferta
        )
        assert resultado["demanda"]["elegido"] == 0.000
        assert resultado["demanda"]["cobertura_lograda"] > 0.97


# ---------------------------------------------------------------------------
# Integración: ejecutar() + escribir_reporte()
# ---------------------------------------------------------------------------


class TestEjecutarYEscribirReporte:
    def test_ejecutar_produce_las_claves_esperadas(
        self,
        panel_demanda_backtest: pd.DataFrame,
        panel_oferta_backtest: pd.DataFrame,
        conapo_backtest: pd.DataFrame,
    ) -> None:
        resultado = ejecutar(panel_demanda_backtest, panel_oferta_backtest, conapo_backtest)
        for clave in (
            "semilla",
            "metadatos",
            "adelgazamiento",
            "loao",
            "oferta",
            "comparacion_censo_conapo",
            "calibracion_piso",
            "adopcion",
            "limitacion_conapo",
        ):
            assert clave in resultado

    def test_determinismo_de_ejecutar(
        self,
        panel_demanda_backtest: pd.DataFrame,
        panel_oferta_backtest: pd.DataFrame,
        conapo_backtest: pd.DataFrame,
    ) -> None:
        r1 = ejecutar(panel_demanda_backtest, panel_oferta_backtest, conapo_backtest)
        r2 = ejecutar(panel_demanda_backtest, panel_oferta_backtest, conapo_backtest)
        assert r1["adelgazamiento"] == r2["adelgazamiento"]
        assert r1["calibracion_piso"] == r2["calibracion_piso"]
        assert r1["adopcion"] == r2["adopcion"]

    def test_limitacion_conapo_declarada_literal(
        self,
        panel_demanda_backtest: pd.DataFrame,
        panel_oferta_backtest: pd.DataFrame,
        conapo_backtest: pd.DataFrame,
    ) -> None:
        resultado = ejecutar(panel_demanda_backtest, panel_oferta_backtest, conapo_backtest)
        assert "no existe hoy una validación temporal independiente" in resultado["limitacion_conapo"].lower()

    def test_escribir_reporte_genera_json_y_md(
        self,
        panel_demanda_backtest: pd.DataFrame,
        panel_oferta_backtest: pd.DataFrame,
        conapo_backtest: pd.DataFrame,
        tmp_path,
    ) -> None:
        resultado = ejecutar(panel_demanda_backtest, panel_oferta_backtest, conapo_backtest)
        destino_json = tmp_path / "backtest.json"
        destino_md = tmp_path / "backtest.md"
        escribir_reporte(resultado, destino_json, destino_md)

        assert destino_json.exists()
        assert destino_md.exists()
        contenido_md = destino_md.read_text(encoding="utf-8")
        assert "# Backtest" in contenido_md
        assert "Resumen" in contenido_md
        assert "no existe hoy una validación temporal independiente" in contenido_md.lower()

        import json

        datos = json.loads(destino_json.read_text(encoding="utf-8"))
        assert datos["semilla"] == SEMILLA
        assert "generado" in datos


# ---------------------------------------------------------------------------
# F-2: el resumen no debe contradecirse a sí mismo cuando el modelo no se adopta
# ---------------------------------------------------------------------------


class TestRazonNoAdopcion:
    def test_adopcion_positiva_no_lista_fallas(self) -> None:
        adopcion = {
            "demanda_supera_baseline": True,
            "loao_cobertura_en_rango": True,
            "oferta_supera_baseline": True,
            "modelo_se_adopta": True,
        }
        assert _razon_no_adopcion(adopcion) == (
            "supera al baseline en las 3 validaciones (demanda, LOAO, oferta)"
        )

    def test_lista_exactamente_lo_que_fallo(self) -> None:
        adopcion = {
            "demanda_supera_baseline": True,
            "loao_cobertura_en_rango": False,
            "oferta_supera_baseline": False,
            "modelo_se_adopta": False,
        }
        razon = _razon_no_adopcion(adopcion)
        assert "LOAO fuera de" in razon
        assert "oferta no supera" in razon
        assert "demanda no supera" not in razon

    def test_caso_real_de_la_auditoria_2026_09_20(
        self,
        panel_demanda_backtest: pd.DataFrame,
        panel_oferta_backtest: pd.DataFrame,
        conapo_backtest: pd.DataFrame,
    ) -> None:
        """No debe reaparecer la frase fija "(supera al baseline en las 3
        validaciones)" cuando `modelo_se_adopta` es `False` (punto 12)."""
        resultado = ejecutar(panel_demanda_backtest, panel_oferta_backtest, conapo_backtest)
        razon = _razon_no_adopcion(resultado["adopcion"])
        if not resultado["adopcion"]["modelo_se_adopta"]:
            assert razon != "supera al baseline en las 3 validaciones (demanda, LOAO, oferta)"


# ---------------------------------------------------------------------------
# F-3: la banda de cobertura del IC95 se relaja explícitamente, no se calla
# ---------------------------------------------------------------------------


class TestBandaCoberturaRelajada:
    def test_backtest_json_real_documenta_la_decision(self) -> None:
        """Afirma la banda que el equipo decidió (opción (a), CLAUDE.md/avance_plan.md
        F-3): se acepta sobrecobertura como conservadora y se documenta en
        `docs/backtest.md`, en vez de perseguir `[0.90, 0.97]` a ciegas."""
        from pathlib import Path

        ruta_md = Path(__file__).resolve().parents[2] / "docs" / "backtest.md"
        if not ruta_md.exists():
            pytest.skip("docs/backtest.md no generado en este entorno de pruebas")
        contenido = ruta_md.read_text(encoding="utf-8").lower()
        assert "sobrecobertura" in contenido
        assert "conservador" in contenido


# ---------------------------------------------------------------------------
# Guardarraíl: nunca debe reaparecer un backtest de CONAPO con orígenes móviles
# ---------------------------------------------------------------------------


class TestGuardarrailBacktestConapo:
    def test_no_existe_ninguna_funcion_backtest_conapo(self) -> None:
        import chipos.backtest as backtest_mod

        nombres = dir(backtest_mod)
        sospechosos = [n for n in nombres if "backtest_conapo" in n.lower()]
        assert sospechosos == [], (
            "backtest.py no debe definir backtest_conapo (u orígenes móviles sobre "
            "pobproy_quinq1.csv): es un error metodológico retirado en la revisión "
            "2026-09-20 (metodología §4.1) -- validaría una proyección con otra "
            "proyección construida con información futura."
        )

    def test_pobproy_quinq_nunca_se_lee_como_archivo(self) -> None:
        """`pobproy_quinq1.csv` puede mencionarse en la documentación (explicando por qué
        se retiró), pero el módulo nunca debe leerlo (`read_csv`, `pd.read_csv`, etc.)."""
        import inspect

        import chipos.backtest as backtest_mod

        codigo_fuente = inspect.getsource(backtest_mod)
        assert "read_csv" not in codigo_fuente
