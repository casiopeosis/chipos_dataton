"""Brecha histórica (B10, retirada del contrato en Fase 6) e índice de oportunidad (Fase 6,
`plans/backend_plan.md` §8bis, fórmulas exactas en `docs/metodologia.md` §10).

Contenido:
- `calcular_brecha_ageb`/`calcular_brecha_alcaldia`: `S_2024 / D_2020 * 1000`, la brecha
  histórica original (B10). Ya NO se publica en el contrato v1.4
  (`correccion/action_plan.md` #34: "capas.brecha se retira"); se conserva aquí, fuera del
  contrato, como resumen de `diagnostico.json` (metodología §10, "diagnostico.json conserva
  un resumen agregado fuera del contrato").
- `cobertura_proyectada`, `indice_oportunidad`, `sensibilidad_indice_oportunidad`,
  `indice_disponibilidad`: el índice de oportunidad por rama (metodología §10.1-§10.2) y el
  índice de disponibilidad para familias (§10.5), sobre las mismas réplicas Monte Carlo de
  `modelos.py`. El backend **nunca** calcula el índice compuesto entre ramas (eso es del
  motor de composición del frontend, metodología §10.3): solo publica `O_{i,h,r}` por rama.

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

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from chipos.config import RUTA_DIAGNOSTICO
from chipos.io import CORTES_OFERTA
from chipos.modelos import Simulacion

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


# ---------------------------------------------------------------------------
# Índice de oportunidad e índice de disponibilidad (Fase 6, metodología §10)
# ---------------------------------------------------------------------------

# K de normalización del ajuste de tendencia (metodología §10.2): "una brecha de 5 pp/año
# entre demanda y oferta ya satura el ajuste". Constante interna, no expuesta al usuario
# (correccion/frontend_requisitos.md: "no mostrar fórmulas ni parámetros internos").
K_OPORTUNIDAD_DEFECTO: float = 5.0
K_SENSIBILIDAD: tuple[float, float, float] = (3.0, 5.0, 8.0)
# Límite del ajuste de tendencia (metodología §10.2, paso 2): el nivel de cobertura (paso 1)
# domina el índice; la tendencia solo puede mover el resultado 15 pp del rango [0,1].
AJUSTE_TENDENCIA_MAX: float = 0.15

# Umbral de "cambio sustancial de orden" entre K=3 y K=8 para la sensibilidad obligatoria
# (metodología §10.2: "si el orden relativo... cambia sustancialmente"). El plan no fija un
# número exacto; se elige 0.10 (10 puntos porcentuales de rango percentil) como umbral
# razonable y documentado -- una AGEB que se mueve más de una décima parte del ranking según
# qué tan sensible se calibre K merece la bandera; es una elección de ingeniería, no una cifra
# del plan.
_UMBRAL_CAMBIO_SUSTANCIAL_RANGO: float = 0.10


def _rango_percentil_promediado(valores: np.ndarray) -> np.ndarray:
    """Rango percentil fraccionario ∈ [0,1], empates promediados (metodología §10.2, paso 1:
    "rango fraccionario con empates promediados... `average`"). `NaN` se propaga (AGEB sin
    cobertura válida quedan fuera del ranking, ver `cobertura_proyectada`). Con un solo valor
    válido, el rango es 0.5 (ni el más alto ni el más bajo posible)."""
    valores = np.asarray(valores, dtype=float)
    resultado = np.full(valores.shape, np.nan)
    validos = ~np.isnan(valores)
    n_validos = int(validos.sum())
    if n_validos == 0:
        return resultado
    if n_validos == 1:
        resultado[validos] = 0.5
        return resultado
    rangos = rankdata(valores[validos], method="average")  # 1..n_validos, empates promediados
    resultado[validos] = (rangos - 1.0) / (n_validos - 1.0)
    return resultado


def nivel_proyectado_por_replica(sim: Simulacion, t0: float, t_horizonte: float) -> np.ndarray:
    """Nivel proyectado `(n_unidades, n_sim)` en `t_horizonte`, partiendo de `sim.base` en `t0`.

    Mismo cálculo que `exportar.nivel_en` pero sobre TODAS las réplicas (no la mediana): es el
    ingrediente que pide metodología §10.1 ("sobre las mismas réplicas Monte Carlo... no sobre
    las medianas, así el intervalo de la cobertura sale de la propia simulación").
    """
    return sim.base[:, None] * np.exp(sim.r_fut * (t_horizonte - t0))


def nivel_rama_por_celda(
    simulaciones_celda: dict[str, Simulacion],
    t0: float,
    t_horizonte: float,
    claves_universo: pd.Index,
) -> np.ndarray:
    """Ŝ_{i,h,r} `(len(claves_universo), n_sim)`: suma el nivel proyectado de TODAS las celdas
    de una rama, alineado por AGEB (metodología §10.6: `Ŝ_rama(filtro) = Σ_celdas Ŝ_celda`).

    Una AGEB ausente de la simulación de una celda (ajuste no confiable o sin ningún
    establecimiento en los 3 cortes) aporta 0 a esa celda -- **válido**, no se excluye
    (metodología §10.1: "Ŝ=0 con D̂>0 es un valor válido"). Todas las celdas deben compartir
    `n_sim` (mismo `N_SIM` global).
    """
    n_sim = next(iter(simulaciones_celda.values())).r_fut.shape[1]
    total = np.zeros((len(claves_universo), n_sim))
    for sim in simulaciones_celda.values():
        nivel = nivel_proyectado_por_replica(sim, t0, t_horizonte)
        tabla = pd.DataFrame(nivel, index=pd.Index(sim.clave, name="cvegeo"))
        alineado = tabla.reindex(claves_universo, fill_value=0.0)
        total += alineado.to_numpy()
    return total


def cobertura_proyectada(nivel_oferta: np.ndarray, nivel_demanda: np.ndarray) -> np.ndarray:
    """`cobertura_{i,h,r}^s = Ŝ_{i,h,r}^s / D̂_{i,h,seg}^s × 1000` (metodología §10.1).

    `nivel_oferta`/`nivel_demanda`: `(n, n_sim)`, ya alineados por AGEB (misma fila = misma
    AGEB en ambos). `D̂ <= 0` (AGEB inválida en demanda, p. ej. `sin_datos`) produce `NaN` --
    **nunca** se imputa un denominador. `Ŝ = 0` con `D̂ > 0` produce `0.0`, un valor válido, no
    `NaN` (metodología §10.1, "la señal de mayor oportunidad posible").
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(nivel_demanda > 0, nivel_oferta / nivel_demanda * 1000.0, np.nan)


def indice_oportunidad(
    cobertura_mediana: np.ndarray,
    tasa_d: np.ndarray,
    tasa_s: np.ndarray,
    k_normalizacion: float = K_OPORTUNIDAD_DEFECTO,
) -> np.ndarray:
    """`O_{i,h,r}` (metodología §10.2, fórmula exacta).

    Paso 1 (nivel): `N = 1 - rango_percentil(cobertura_mediana)` -- las AGEB con `cobertura=0`
    comparten el rango más bajo y por tanto el mismo `N=1` (máxima oportunidad), sin tratar
    `Ŝ=0` como caso especial: cae ahí por construcción de la fórmula.
    Paso 2 (tendencia, acotada): `ajuste = clip((tasa_d - tasa_s)/K, -0.15, +0.15)`.
    Paso 3: `O = clip(N + ajuste, 0, 1)`.

    `cobertura_mediana`: la MEDIANA de `cobertura_proyectada` a través de las réplicas (no las
    réplicas mismas: el percentil se calcula sobre un punto por AGEB, metodología §10.1 "nivel
    de disponibilidad proyectada"). `tasa_d`/`tasa_s`: `tasa_anual_pct` de demanda/oferta
    (idénticas en todos los horizontes, `modelos.resumir`), en las mismas unidades (pp/año o
    fracción -- ambas deben usar la MISMA escala, ya que se restan directamente).
    `NaN` en `cobertura_mediana` (D̂ inválido) se propaga a `O=NaN` (`sin_datos`).
    """
    n = 1.0 - _rango_percentil_promediado(cobertura_mediana)
    ajuste = np.clip(
        (np.asarray(tasa_d, dtype=float) - np.asarray(tasa_s, dtype=float)) / k_normalizacion,
        -AJUSTE_TENDENCIA_MAX,
        AJUSTE_TENDENCIA_MAX,
    )
    o = np.clip(n + ajuste, 0.0, 1.0)
    o[np.isnan(cobertura_mediana)] = np.nan
    return o


def sensibilidad_indice_oportunidad(
    cobertura_mediana: np.ndarray,
    tasa_d: np.ndarray,
    tasa_s: np.ndarray,
    claves: pd.Index,
    ks: tuple[float, ...] = K_SENSIBILIDAD,
) -> dict:
    """Sensibilidad obligatoria del índice de oportunidad a `K` (metodología §10.2).

    Recalcula `O` con cada candidato de `ks` y marca las AGEB cuyo **rango percentil de `O`**
    (no `O` mismo, que ya está acotado por diseño) cambia más de
    `_UMBRAL_CAMBIO_SUSTANCIAL_RANGO` entre el `K` más chico y el más grande. Va a
    `diagnostico.json`, nunca al contrato (metodología §10.2: "no se expone como parámetro de
    usuario").
    """
    resultados = {k: indice_oportunidad(cobertura_mediana, tasa_d, tasa_s, k) for k in ks}
    rango_min_k = _rango_percentil_promediado(resultados[min(ks)])
    rango_max_k = _rango_percentil_promediado(resultados[max(ks)])

    valido = ~np.isnan(rango_min_k) & ~np.isnan(rango_max_k)
    cambia = valido & (np.abs(rango_min_k - rango_max_k) > _UMBRAL_CAMBIO_SUSTANCIAL_RANGO)

    return {
        "k_candidatos": list(ks),
        "umbral_cambio_rango": _UMBRAL_CAMBIO_SUSTANCIAL_RANGO,
        "claves_con_cambio_sustancial": sorted(pd.Index(claves)[cambia].tolist()),
        "n_con_cambio": int(cambia.sum()),
        "n_evaluado": int(valido.sum()),
    }


def indice_disponibilidad(
    cobertura_mediana: np.ndarray,
    tasa_s: np.ndarray,
    confianza: np.ndarray,
    k_normalizacion: float = K_OPORTUNIDAD_DEFECTO,
) -> np.ndarray:
    """`F_{i,h,r}`, índice de disponibilidad para familias (metodología §10.5, vista separada).

    `F = clip(rango_percentil(cobertura) + ajuste_estabilidad, 0, 1)` -- **sin invertir** el
    signo del rango (a diferencia de `indice_oportunidad`, que usa `1 - rango`): cobertura alta
    ya significa disponibilidad alta, así que el rango se usa directo.

    `ajuste_estabilidad` (metodología §10.5: "premiando confianza alta y tendencia de oferta no
    decreciente, mismo mecanismo de recorte ±0.15 que §10.2, sobre la SOLA tasa de oferta, no
    la comparativa"): el plan no fija una fórmula exacta para combinar ambas señales -- se
    implementa como `clip(tasa_s/K, -0.15, 0.15)` escalado por un factor de confianza
    (`alta=1.0, media=0.5, baja=0.0`), de modo que una tendencia de oferta positiva SOLO premia
    si la confianza respalda esa tendencia (confianza baja no debe premiar estabilidad que no
    está bien fundamentada). Elección de ingeniería documentada, no una cifra del plan.

    **Nunca se combina con `indice_oportunidad`** en el mismo campo (metodología §10.5).
    """
    factor_confianza = pd.Series(confianza).map({"alta": 1.0, "media": 0.5, "baja": 0.0}).to_numpy()
    ajuste_tendencia = np.clip(
        np.asarray(tasa_s, dtype=float) / k_normalizacion, -AJUSTE_TENDENCIA_MAX, AJUSTE_TENDENCIA_MAX
    )
    ajuste_estabilidad = ajuste_tendencia * factor_confianza
    rango = _rango_percentil_promediado(cobertura_mediana)
    f = np.clip(rango + ajuste_estabilidad, 0.0, 1.0)
    f[np.isnan(cobertura_mediana)] = np.nan
    return f


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


def calcular_escenario_b_oferta(panel_o: pd.DataFrame) -> pd.Series:
    """Tasa "atenuada" (escenario B, metodología §6.1, Fase 3 de action_plan.md).

    Extrapola SOLO 2016-10 + 2019-11, ignorando la magnitud del corte
    2024-11: la hipótesis de sensibilidad es que parte de la caída 2024-11
    es depuración del padrón DENUE (no cierres reales), así que un
    estimador que nunca ve ese corte da la tasa que habría salido "si la
    caída no hubiera pasado". Mismo ajuste cerrado de 2 puntos, con la misma
    corrección de continuidad `+0.5`, que `backtest.backtest_oferta`.

    Devuelve una `pd.Series` (tasa, no pp/año) indexada por `cvegeo`.
    """
    t_2016, t_2019, _t_2024 = sorted(CORTES_OFERTA.values())
    dt = t_2019 - t_2016
    tabla = panel_o.pivot(index="cvegeo", columns="t", values="s")[[t_2016, t_2019]]
    s1 = tabla[t_2016].to_numpy(dtype=float)
    s2 = tabla[t_2019].to_numpy(dtype=float)
    tasa_b = np.log((s2 + 0.5) / (s1 + 0.5)) / dt
    return pd.Series(tasa_b, index=tabla.index, name="tasa_b")


def construir_escenarios_oferta(panel_o: pd.DataFrame) -> dict:
    """Bloque `oferta_escenarios_denue_2024` de `diagnostico.json` (metodología §6.1).

    Escenario A (el que se publica en el contrato): ajuste completo de los 3
    cortes (`modelos.ajustar_oferta`, antes de la contracción EB -- la
    contracción se aplica igual en ambos escenarios, así que compararlos
    antes de esa contracción aísla el efecto real de la hipótesis).
    Escenario B (sensibilidad): `calcular_escenario_b_oferta`. El rango
    `|A - B|` es la sensibilidad reportada; el veredicto publicado siempre
    usa A (metodología §6.1: "no se duplica el contrato").
    """
    from chipos.modelos import ajustar_oferta

    ajuste = ajustar_oferta(panel_o)
    tasa_a = ajuste.loc[~ajuste["sin_datos"]].set_index("cvegeo")["b_hat"]
    tasa_b = calcular_escenario_b_oferta(panel_o)

    claves_comunes = sorted(set(tasa_a.index) & set(tasa_b.index))
    resultado: dict = {}
    for cve in claves_comunes:
        a = float(tasa_a.loc[cve])
        b = float(tasa_b.loc[cve])
        if pd.isna(a) or pd.isna(b):
            continue
        resultado[cve] = {
            "tasa_a_pct_anio": round(a * 100, 2),
            "tasa_b_pct_anio": round(b * 100, 2),
            "rango_pp_anio": round(abs(a - b) * 100, 2),
        }

    return {
        "descripcion": (
            "A (principal, publicado en el contrato): cierres reales acumulados 2020-2023, "
            "registrados de golpe al volver a campo en 2024 -- tasa repartida en los 5 anios "
            "entre 2019-11 y 2024-11. B (sensibilidad, nunca publicado como veredicto): parte "
            "de la caida es depuracion del padron DENUE, no cierres reales -- tasa atenuada, "
            "extrapola solo 2016-10 -> 2019-11, ignora la magnitud del corte 2024-11. El "
            "veredicto y la confianza publicados siempre usan el escenario A; el rango A-B se "
            "reporta aqui como sensibilidad (metodologia S6.1)."
        ),
        "ageb": dict(sorted(resultado.items())),
    }


def construir_diagnostico(panel_d: pd.DataFrame, panel_o: pd.DataFrame) -> dict:
    """Bloque `brecha` + `oferta_escenarios_denue_2024` de `diagnostico.json` (plan §8,
    tarea B10; escenarios A/B de la Fase 3 de `correccion/action_plan.md`).

    Estructura: `{"generado": ISO-8601, "brecha": {"ageb": {...}, "alcaldia":
    {...}}, "oferta_escenarios_denue_2024": {...}}`. Fuera del contrato v1.1
    de CLAUDE.md (no lo valida `exportar.validar_contrato`); solo
    diagnóstico interno.
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
        "oferta_escenarios_denue_2024": construir_escenarios_oferta(panel_o),
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
    # segmento="total_0a14": mismo alcance 0-14 que usa exportar.py hoy (Fase 4, ver su comentario).
    panel_d = construir_panel_demanda(censo, equivalencia, universo, segmento="total_0a14")

    con = conectar()
    denue = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))
    panel_o = construir_panel_oferta(denue, universo)

    diagnostico = construir_diagnostico(panel_d, panel_o)
    escribir_diagnostico(diagnostico)


if __name__ == "__main__":
    main()
