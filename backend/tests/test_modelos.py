"""Tests de `chipos.modelos.veredicto` y `chipos.modelos.confianza` (B5).

Solo cubren la regla de decisión y de confianza (plan §5.3, metodología §7).
Las funciones de simulación (EB, oferta) se prueban en B6/B7a.
"""

from __future__ import annotations

import pytest

from chipos.modelos import confianza, veredicto


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
