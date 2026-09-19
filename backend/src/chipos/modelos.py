"""Regla de veredicto y de confianza (plan §5.3, metodología §7).

Este módulo solo contiene, por ahora, las dos funciones puras y compartidas
por las capas de demanda y oferta:

- `veredicto`: convierte tres probabilidades (de una distribución simulada
  de la tasa proyectada) en un veredicto ∈ {sube, se_mantiene, baja} y la
  probabilidad decisiva `p_dec` asociada.
- `confianza`: convierte `p_dec` (más señales adicionales) en un nivel de
  confianza ∈ {alta, media, baja}.

Las funciones de simulación (EB, control CONAPO, ajuste Poisson de oferta,
etc.) se implementan en tareas posteriores (B6/B7a) en este mismo archivo.
"""

from __future__ import annotations

from chipos.config import D_MIN_CONF, P_ALTA, P_DECISION, P_MANTIENE

# Orden de los niveles de confianza, de menor a mayor (para "bajar un nivel"
# y para aplicar un `tope` como techo).
_NIVELES: tuple[str, str, str] = ("baja", "media", "alta")
_RANGO: dict[str, int] = {nivel: i for i, nivel in enumerate(_NIVELES)}


def veredicto(p_sube: float, p_baja: float, p_mantiene: float) -> tuple[str, float]:
    """Regla de decisión única (plan §5.3, metodología §7).

    - `sube` si `p_sube >= P_DECISION`, con `p_dec = p_sube`.
    - `baja` si `p_baja >= P_DECISION`, con `p_dec = p_baja`.
    - en cualquier otro caso, `se_mantiene` con `p_dec = p_mantiene`.

    Nota: la regla del plan distingue un caso "`se_mantiene` con
    `p_mantiene >= P_MANTIENE`" de un caso residual "si no, `se_mantiene`
    con confianza forzada `baja`". No hace falta distinguirlos aquí: como
    `P_MANTIENE (0.50) < P_DECISION (0.80)`, cualquier `p_mantiene` por
    debajo de `P_MANTIENE` también queda por debajo de `P_DECISION`, así
    que `confianza()` ya devuelve `baja` en ese caso al aplicar sus
    umbrales estándar sobre `p_dec = p_mantiene`.
    """
    if p_sube >= P_DECISION:
        return "sube", p_sube
    if p_baja >= P_DECISION:
        return "baja", p_baja
    return "se_mantiene", p_mantiene


def _bajar_un_nivel(nivel: str) -> str:
    """Un escalón hacia abajo en `_NIVELES` (`baja` se queda en `baja`)."""
    indice = max(0, _RANGO[nivel] - 1)
    return _NIVELES[indice]


def _aplicar_tope(nivel: str, tope: str) -> str:
    """Techo del nivel de confianza: `min(nivel, tope)` en `_NIVELES`."""
    if _RANGO[tope] < _RANGO[nivel]:
        return tope
    return nivel


def confianza(
    p_dec: float,
    estable_lambda: bool,
    n_obs: int,
    d2020: float | None,
    tope: str | None = None,
) -> str:
    """Nivel de confianza a partir de `p_dec` y señales adicionales.

    Orden de aplicación (plan §5.3 / metodología §7):
    1. Umbral base sobre `p_dec`: `alta` si `>= P_ALTA`, `media` si
       `>= P_DECISION`, si no `baja`.
    2. Si el veredicto cambia con `λ` (`estable_lambda is False`), bajar un
       nivel.
    3. Forzar `baja` si `n_obs == 1` o `d2020 < D_MIN_CONF` (cuando
       `d2020` aplica; en la capa de oferta no hay `D_2020` y se pasa
       `None`, sin efecto en esta regla).
    4. Aplicar `tope` (p. ej. `'media'` para `relacion != 'misma'` o para
       toda la capa de oferta) como techo final.
    """
    if p_dec >= P_ALTA:
        nivel = "alta"
    elif p_dec >= P_DECISION:
        nivel = "media"
    else:
        nivel = "baja"

    if not estable_lambda:
        nivel = _bajar_un_nivel(nivel)

    if n_obs == 1 or (d2020 is not None and d2020 < D_MIN_CONF):
        nivel = "baja"

    if tope is not None:
        nivel = _aplicar_tope(nivel, tope)

    return nivel
