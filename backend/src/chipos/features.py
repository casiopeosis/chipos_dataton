"""Brecha demanda/oferta (`plans/backend_plan.md` §8, tarea B10).

Alcance mínimo, tal como lo fija el plan: `brecha = S_2024 / D_2020 * 1000`
por AGEB y por alcaldía, escrita en `data/outputs/diagnostico.json` (fuera
del contrato v1.1 versionado de `CLAUDE.md`; es solo diagnóstico interno,
no lo consume el frontend).

Deliberadamente **no** se implementan covariables estáticas (áreas verdes,
espacios públicos): el plan dice que por defecto no se implementan salvo que
mejoren el backtest de la contracción EB (§6.1), y esa decisión no se ha
tomado (ver plan §8 y pregunta abierta B2).

Regla de agregación (irrenunciable, CLAUDE.md "no inventar datos" + plan
§5.4 "Δ% desde sumas, nunca promedio de %"): la brecha de alcaldía se
calcula agregando `S_2024` y `D_2020` **por separado** y dividiendo al
final; nunca promediando la razón `brecha_por_mil` de las AGEB de la
alcaldía.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from chipos.config import RUTA_DIAGNOSTICO

# Escala de la brecha (plan §8): establecimientos "Principal" por cada 1,000
# niñas y niños de 0-14 años (censo 2020).
_ESCALA_BRECHA = 1000.0


def _brecha_por_mil(s: pd.Series, d: pd.Series) -> pd.Series:
    """`s / d * 1000`, `NaN` donde `d` es nulo o cero (denominador inválido)."""
    d = d.astype(float)
    s = s.astype(float)
    valido = d.notna() & (d > 0)
    resultado = pd.Series(pd.NA, index=s.index, dtype="Float64")
    resultado[valido] = (s[valido] / d[valido]) * _ESCALA_BRECHA
    return resultado


def calcular_brecha_ageb(panel_d: pd.DataFrame, panel_o: pd.DataFrame) -> pd.DataFrame:
    """Brecha oferta/demanda por AGEB urbana.

    `panel_d`: forma de `construir_panel_demanda()` (una fila por AGEB del
    universo, columnas `cvegeo, cve_mun, ambito, d_2020, ...`).
    `panel_o`: forma de `construir_panel_oferta()` (formato largo AGEB x
    corte, con `s_2024` repetido en todas las filas de cada AGEB).

    Devuelve una fila por AGEB **urbana** presente en `panel_o` (el universo
    de oferta; las rurales no tienen `s_2024` porque `construir_panel_oferta`
    ya las excluye), con columnas `cvegeo, cve_mun, s_2024, d_2020,
    brecha_por_mil`. `brecha_por_mil` es `NaN` cuando `d_2020` es nulo (AGEB
    `sin_datos` de demanda: suprimida INEGI, sin censo) o cero, para no
    inventar una razón sobre un denominador inválido.
    """
    s_por_ageb = panel_o.drop_duplicates("cvegeo")[["cvegeo", "cve_mun", "s_2024"]]
    d_por_ageb = panel_d[["cvegeo", "d_2020"]]

    tabla = s_por_ageb.merge(d_por_ageb, on="cvegeo", how="left")
    tabla["brecha_por_mil"] = _brecha_por_mil(tabla["s_2024"], tabla["d_2020"])

    return (
        tabla[["cvegeo", "cve_mun", "s_2024", "d_2020", "brecha_por_mil"]]
        .sort_values("cvegeo")
        .reset_index(drop=True)
    )


def calcular_brecha_alcaldia(brecha_ageb: pd.DataFrame) -> pd.DataFrame:
    """Brecha oferta/demanda por alcaldía, a partir de `calcular_brecha_ageb()`.

    Suma `s_2024` y `d_2020` de las AGEB de cada alcaldía por separado y
    divide al final (nunca promedia `brecha_por_mil` de las AGEB, ver
    docstring del módulo). Solo entran a la suma de `d_2020` las AGEB con
    dato (las `NaN` se excluyen de la suma, no se tratan como cero).
    """
    agregado = brecha_ageb.groupby("cve_mun").agg(
        s_2024=("s_2024", "sum"), d_2020=("d_2020", "sum")
    )
    agregado["brecha_por_mil"] = _brecha_por_mil(agregado["s_2024"], agregado["d_2020"])
    return agregado.reset_index().sort_values("cve_mun").reset_index(drop=True)


def _tabla_a_dict_ageb(tabla: pd.DataFrame) -> dict:
    salida: dict = {}
    for fila in tabla.itertuples(index=False):
        salida[fila.cvegeo] = {
            "cve_mun": fila.cve_mun,
            "s_2024": int(fila.s_2024),
            "d_2020": None if pd.isna(fila.d_2020) else round(float(fila.d_2020), 1),
            "brecha_por_mil": (
                None if pd.isna(fila.brecha_por_mil) else round(float(fila.brecha_por_mil), 2)
            ),
        }
    return dict(sorted(salida.items()))


def _tabla_a_dict_alcaldia(tabla: pd.DataFrame) -> dict:
    salida: dict = {}
    for fila in tabla.itertuples(index=False):
        salida[fila.cve_mun] = {
            "s_2024": int(fila.s_2024),
            "d_2020": None if pd.isna(fila.d_2020) else round(float(fila.d_2020), 1),
            "brecha_por_mil": (
                None if pd.isna(fila.brecha_por_mil) else round(float(fila.brecha_por_mil), 2)
            ),
        }
    return dict(sorted(salida.items()))


def construir_diagnostico(panel_d: pd.DataFrame, panel_o: pd.DataFrame) -> dict:
    """Bloque `brecha` de `diagnostico.json` (plan §8, tarea B10).

    Estructura: `{"generado": ISO-8601, "brecha": {"ageb": {...}, "alcaldia":
    {...}}}`. Fuera del contrato v1.1 de CLAUDE.md (no lo valida
    `exportar.validar_contrato`); solo diagnóstico interno.
    """
    brecha_ageb = calcular_brecha_ageb(panel_d, panel_o)
    brecha_alcaldia = calcular_brecha_alcaldia(brecha_ageb)

    return {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "brecha": {
            "escala": "establecimientos Principal por 1000 ninas y ninos 0-14 (censo 2020)",
            "ageb": _tabla_a_dict_ageb(brecha_ageb),
            "alcaldia": _tabla_a_dict_alcaldia(brecha_alcaldia),
        },
    }


def escribir_diagnostico(diagnostico: dict, ruta: Path = RUTA_DIAGNOSTICO) -> None:
    """Escribe (o actualiza) `diagnostico.json`.

    `diagnostico.json` es compartido con otras tareas del plan (B9 backtest
    también escribe ahí, plan §5.3/§6); si el archivo ya existe se actualiza
    solo la clave de nivel superior que trae `diagnostico` (aquí: `brecha` y
    `generado`), preservando el resto (p. ej. `sensibilidad`, `backtest`)
    para no pisar el trabajo de otras tareas paralelas ({B8, B9, B10} del
    plan §9).
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    existente: dict = {}
    if ruta.exists():
        with ruta.open(encoding="utf-8") as f:
            existente = json.load(f)

    existente.update(diagnostico)

    with ruta.open("w", encoding="utf-8") as f:
        json.dump(existente, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    """Punto de entrada: lee datos reales, calcula la brecha y la escribe.

    No forma parte de `exportar.main()` (B11, pendiente); se puede invocar
    de forma independiente (`python -m chipos.features`) para regenerar solo
    el bloque `brecha` de `diagnostico.json`.
    """
    from chipos.io import (
        CORTES_OFERTA,
        conectar,
        leer_censo_panel,
        leer_denue_infancias,
        leer_equivalencia,
        leer_universo_ageb,
    )
    from chipos.panel import construir_panel_demanda, construir_panel_oferta

    universo = leer_universo_ageb()
    censo = leer_censo_panel()
    equivalencia = leer_equivalencia()
    panel_d = construir_panel_demanda(censo, equivalencia, universo)

    con = conectar()
    denue = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))
    panel_o = construir_panel_oferta(denue, universo)

    diagnostico = construir_diagnostico(panel_d, panel_o)
    escribir_diagnostico(diagnostico)


if __name__ == "__main__":
    main()
