"""Exportación del contrato v1.4 (`exportar.py`, punto de entrada de `make pipeline`).

Fase 6 de `correccion/action_plan.md`: salto de contrato de v1.2 a v1.4 en un
solo bloque (comparten el cambio las Fases 4 -- segmentos --, 5 -- ramas -- y
6 -- índice de oportunidad --, `plans/backend_plan.md` §9.2: "no tocar
exportar.py/validar_contrato tres veces").

Contenido:
- `construir_capa`: bloque reutilizable de UN segmento/celda (AGEB o
  alcaldía comparten estructura) -- sin cambios de forma desde v1.2.
- `construir_capa_demanda_v14` / `construir_capa_rama_v14`: envuelven N
  llamadas a `construir_capa` (una por segmento o por celda) en la forma
  anidada del contrato v1.4 (`capas.demanda[cvegeo].segmentos.<seg>`,
  `capas.ramas.<rama>[cvegeo].celdas.<celda>`).
- `construir_capa_verde`: la rama sin proyección (metodología §10.1), sin
  pasar por `modelos.py`/`resumir()`.
- `construir_salida_ageb` / `construir_salida_alcaldia`: ensamblan el
  documento completo (`version`, `fecha_base`, `horizontes`, `capas`, y en
  alcaldía además `agregado_cdmx`). `capas.brecha` se retira del contrato
  (`correccion/action_plan.md` #34); el cálculo equivalente es
  responsabilidad del motor de composición del frontend (metodología §10.3).
- `validar_contrato`: valida un documento (AGEB o alcaldía) por separado;
  `verificar_suma_ageb_alcaldia` valida la identidad cruzada entre ambos
  archivos (Σ AGEB == alcaldía), sobre el segmento `todas`.
- `main()`: orquesta `io → panel → backtest → modelos → exportar` y escribe
  los dos JSON de `data/outputs/` más `data/outputs/backtest.json` /
  `docs/backtest.md` (ver docstring de `main`).
"""

from __future__ import annotations

import dataclasses
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from chipos.config import (
    HORIZONTES,
    HORIZONTES_OFERTA,
    RUTA_DIAGNOSTICO,
    RUTA_PREDICCION_AGEB,
    RUTA_PREDICCION_ALCALDIA,
    SEMILLA,
    T_2010,
    T_2020,
    T_BASE,
)
from chipos.io import CORTES_OFERTA
from chipos.modelos import Simulacion, agregar_alcaldia, resumir
from chipos.panel import (
    CELDAS_COMERCIO,
    CELDAS_EDUCACION,
    CELDAS_SALUD,
    CELDAS_VERDE,
    SEGMENTOS_DEMANDA,
)

# ---------------------------------------------------------------------------
# Constantes del contrato (tablas literales; nunca conversión numérica
# año-decimal -> "YYYY-MM" genérica, ver plan de migración).
# ---------------------------------------------------------------------------

VERSION_CONTRATO = "1.4"
FECHA_BASE_ETIQUETA = "2026-06"
ORDEN_HORIZONTES: tuple[str, ...] = ("h1", "h3", "h5")
FECHAS_HORIZONTE: dict[str, str] = {"h1": "2027-06", "h3": "2029-06", "h5": "2031-06"}
ANIOS_HORIZONTE: dict[str, int] = {"h1": 1, "h3": 3, "h5": 5}

# Ramas de oferta/disponibilidad (Fase 5/6, metodología §1 y §10.6). `educacion` reutiliza el
# panel de `construir_panel_oferta`/DENUE infancias que ya existía en v1.2; `salud`/`comercio`
# son nuevas en Fase 5; `verde` no pasa por `modelos.py` (sin proyección).
RAMAS: tuple[str, ...] = ("educacion", "salud", "comercio", "verde")
RAMAS_CON_PROYECCION: tuple[str, ...] = ("educacion", "salud", "comercio")

VEREDICTOS_VALIDOS: frozenset[str] = frozenset(
    {"sube", "se_mantiene", "baja", "sin_datos"}
)
CONFIANZAS_VALIDAS: frozenset[str] = frozenset({"alta", "media", "baja"})

# `docs/metodologia.md` §8 / `panel.py` -> códigos de `plans/frontend_specs.md`
# §14.4 (lenguaje del frontend). `d2020_menor_20` (interno) se traduce a
# `poblacion_menor_20` (código de cara al cliente); el resto coincide.
_MOTIVOS_DEMANDA_A_CONTRATO: dict[str, str] = {
    "rural": "rural",
    "suprimido_inegi": "suprimido_inegi",
    "d2020_menor_20": "poblacion_menor_20",
    "sin_poligono": "sin_poligono",
    "sin_censo": "sin_censo",
}

_ALCALDIAS_VALIDAS: frozenset[str] = frozenset(f"{i:03d}" for i in range(2, 18))


class ErrorContrato(Exception):
    """El documento no cumple el contrato v1.2 (`validar_contrato`)."""


# ---------------------------------------------------------------------------
# Series y nivel base (P3 de frontend_specs.md §17)
# ---------------------------------------------------------------------------


def serie_demanda_por_clave(panel_d: pd.DataFrame) -> dict[str, dict]:
    """`{"t":[2010.44,2020.20],"valor":[D_2010,D_2020]}` por AGEB, solo puntos con dato."""
    resultado: dict[str, dict] = {}
    for fila in panel_d.itertuples(index=False):
        t: list[float] = []
        valor: list[float] = []
        if pd.notna(fila.d_2010):
            t.append(T_2010)
            valor.append(round(float(fila.d_2010), 1))
        if pd.notna(fila.d_2020):
            t.append(T_2020)
            valor.append(round(float(fila.d_2020), 1))
        resultado[fila.cvegeo] = {"t": t, "valor": valor}
    return resultado


def serie_demanda_alcaldia_por_clave(panel_d: pd.DataFrame) -> dict[str, dict]:
    """Igual que `serie_demanda_por_clave`, agregada por `cve_mun` (solo AGEB con dato)."""
    agregado = panel_d.groupby("cve_mun")[["d_2010", "d_2020"]].sum(min_count=1)
    resultado: dict[str, dict] = {}
    for cve_mun, fila in agregado.iterrows():
        t: list[float] = []
        valor: list[float] = []
        if pd.notna(fila["d_2010"]):
            t.append(T_2010)
            valor.append(round(float(fila["d_2010"]), 1))
        if pd.notna(fila["d_2020"]):
            t.append(T_2020)
            valor.append(round(float(fila["d_2020"]), 1))
        resultado[cve_mun] = {"t": t, "valor": valor}
    return resultado


def serie_oferta_por_clave(panel_o: pd.DataFrame) -> dict[str, dict]:
    """`{"t":[2016.79,2019.87,2024.87],"valor":[S,...]}` por AGEB (los 3 cortes de `CORTES_OFERTA`)."""
    cortes = sorted(CORTES_OFERTA.values())
    tabla = panel_o.pivot(index="cvegeo", columns="t", values="s")[cortes]
    return {
        cve: {"t": list(cortes), "valor": [int(v) for v in fila.to_numpy()]}
        for cve, fila in tabla.iterrows()
    }


def serie_oferta_alcaldia_por_clave(panel_o: pd.DataFrame) -> dict[str, dict]:
    cortes = sorted(CORTES_OFERTA.values())
    agregado = panel_o.groupby(["cve_mun", "t"])["s"].sum().unstack("t")[cortes]
    return {
        cve_mun: {"t": list(cortes), "valor": [int(v) for v in fila.to_numpy()]}
        for cve_mun, fila in agregado.iterrows()
    }


def nivel_en(sim: Simulacion, t0: float, t: float = T_BASE) -> dict[str, float]:
    """Nivel proyectado por unidad de `sim` en el tiempo `t` (por defecto `T_BASE`).

    `base * exp(mediana(r_fut) * (t - t0))`: trata `T_BASE` como un
    horizonte de conveniencia más (mismo mecanismo que `resumir()`, pero
    sobre el nivel en vez del `delta_pct`). `t0`: `T_2020` en demanda,
    `max(CORTES_OFERTA.values())` en oferta.
    """
    r_mediana = np.median(sim.r_fut, axis=1)
    niveles = np.asarray(sim.base, dtype=float) * np.exp(r_mediana * (t - t0))
    return {clave: round(float(v), 1) for clave, v in zip(sim.clave, niveles)}


# ---------------------------------------------------------------------------
# Motivos de `sin_datos` (P4 de frontend_specs.md §17, códigos §14.4)
# ---------------------------------------------------------------------------


def motivos_demanda_por_clave(panel_d: pd.DataFrame) -> dict[str, str | None]:
    return {
        fila.cvegeo: _MOTIVOS_DEMANDA_A_CONTRATO.get(fila.motivo_sin_datos)
        if pd.notna(fila.motivo_sin_datos)
        else None
        for fila in panel_d.itertuples(index=False)
    }


def motivos_oferta_por_clave(
    universo: pd.DataFrame, ajuste: pd.DataFrame
) -> dict[str, str | None]:
    """`rural` (AGEB fuera del panel de oferta) o `sin_establecimientos` (`S=0` en los 3 cortes)."""
    sin_establecimientos = set(ajuste.loc[ajuste["sin_datos"], "cvegeo"])
    resultado: dict[str, str | None] = {}
    for fila in universo.itertuples(index=False):
        if fila.ambito == "rural":
            resultado[fila.cvegeo] = "rural"
        elif fila.cvegeo in sin_establecimientos:
            resultado[fila.cvegeo] = "sin_establecimientos"
        else:
            resultado[fila.cvegeo] = None
    return resultado


def _n_obs_sin_datos(motivos: dict[str, str | None]) -> dict[str, int]:
    """`n_obs` "real" para unidades ausentes del resumen (plan §7): 0 salvo
    `sin_establecimientos` (oferta), que sí observó los 3 cortes (en cero)."""
    return {
        clave: 3 if motivo == "sin_establecimientos" else 0
        for clave, motivo in motivos.items()
    }


# ---------------------------------------------------------------------------
# Bloques del contrato
# ---------------------------------------------------------------------------

_REGISTRO_H_SIN_DATOS: dict = {
    "veredicto": "sin_datos",
    "delta_pct": None,
    "tasa_anual_pct": None,
    "ic95": None,
    "confianza": "baja",
}


def _registro_h_valido(fila: pd.Series) -> dict:
    ic0, ic1 = fila["ic95"]
    return {
        "veredicto": str(fila["veredicto"]),
        "delta_pct": round(float(fila["delta_pct"]), 1),
        "tasa_anual_pct": round(float(fila["tasa_anual_pct"]), 1),
        "ic95": [round(float(ic0), 1), round(float(ic1), 1)],
        "confianza": str(fila["confianza"]),
    }


def construir_capa(
    resumenes_por_horizonte: dict[str, pd.DataFrame],
    universo: pd.DataFrame,
    series_por_clave: dict[str, dict],
    nivel_base_por_clave: dict[str, float | None],
    horizontes_disponibles: list[str],
    motivo_por_clave: dict[str, str | None],
    incluir_horizontes_disponibles: bool = False,
) -> dict:
    """Una capa completa (demanda u oferta), a nivel AGEB o alcaldía.

    `universo`: filas con `cvegeo` (clave de la unidad: `CVEGEO` o `cve_mun`)
    y `cve_mun`; TODAS sus claves aparecen en el resultado (regla del
    contrato: ninguna unidad se omite, aunque sea `sin_datos` en todos los
    horizontes). `resumenes_por_horizonte`: salida de `modelos.resumir()`
    (`{clave_horizonte: DataFrame}`); las unidades ausentes de una tabla se
    completan con `sin_datos`.
    """
    n_obs_faltante = _n_obs_sin_datos(motivo_por_clave)
    indices = {h: df.set_index("clave") for h, df in resumenes_por_horizonte.items()}

    capa: dict = {}
    for fila in universo.itertuples(index=False):
        clave = fila.cvegeo
        registro_h: dict = {}
        n_obs: int | None = None
        for h in horizontes_disponibles:
            idx = indices[h]
            if clave in idx.index:
                fila_res = idx.loc[clave]
                registro_h[h] = _registro_h_valido(fila_res)
                n_obs = int(fila_res["n_obs"])
            else:
                registro_h[h] = dict(_REGISTRO_H_SIN_DATOS)
        if n_obs is None:
            n_obs = int(n_obs_faltante.get(clave, 0))

        registro = {
            "cve_mun": fila.cve_mun,
            "n_obs": n_obs,
            "motivo_sin_datos": motivo_por_clave.get(clave),
            "serie": series_por_clave.get(clave, {"t": [], "valor": []}),
            "nivel_base": nivel_base_por_clave.get(clave),
            "h": registro_h,
        }
        if incluir_horizontes_disponibles:
            registro["horizontes_disponibles"] = list(horizontes_disponibles)
        capa[clave] = registro
    return dict(sorted(capa.items()))


def construir_capa_demanda_v14(capas_por_segmento: dict[str, dict]) -> dict:
    """Envuelve N capas (una por segmento, cada una en la forma de `construir_capa`) en la
    forma anidada `capas.demanda[cvegeo] = {cve_mun, segmentos: {segmento: {...}}}` del
    contrato v1.4 (metodología §1.1, `correccion/action_plan.md` #24).

    `capas_por_segmento`: `{segmento: construir_capa(...)}`, TODAS con el mismo universo de
    claves (mismo `universo` pasado a cada llamada de `construir_capa`) -- si no, esta función
    lanza `KeyError` al alinear.
    """
    primera = next(iter(capas_por_segmento.values()))
    resultado: dict = {}
    for clave in primera:
        resultado[clave] = {
            "cve_mun": primera[clave]["cve_mun"],
            "segmentos": {
                segmento: {k: v for k, v in capa[clave].items() if k != "cve_mun"}
                for segmento, capa in capas_por_segmento.items()
            },
        }
    return dict(sorted(resultado.items()))


def construir_capa_rama_v14(
    capas_por_celda: dict[str, dict], horizontes_disponibles: list[str]
) -> dict:
    """Envuelve N capas (una por celda, forma de `construir_capa`) en
    `capas.ramas.<rama>[cvegeo] = {cve_mun, horizontes_disponibles, celdas: {celda: {...}}}`
    (metodología §10.6, `correccion/action_plan.md` #39).
    """
    primera = next(iter(capas_por_celda.values()))
    resultado: dict = {}
    for clave in primera:
        resultado[clave] = {
            "cve_mun": primera[clave]["cve_mun"],
            "horizontes_disponibles": list(horizontes_disponibles),
            "celdas": {
                celda: {k: v for k, v in capa[clave].items() if k not in ("cve_mun", "horizontes_disponibles")}
                for celda, capa in capas_por_celda.items()
            },
        }
    return dict(sorted(resultado.items()))


def construir_capa_verde(
    contexto: pd.DataFrame, universo: pd.DataFrame, celdas: dict[str, tuple[str, str]]
) -> dict:
    """`capas.ramas.verde[cvegeo] = {cve_mun, horizontes_disponibles: [], celdas: {celda:
    {nivel_base, area_m2, motivo_sin_datos}}}` (metodología §10.1: un solo corte, sin
    proyección -- nunca se inventa una línea futura, así que no hay `h` ni `serie` temporal
    aquí, a diferencia de las otras 3 ramas).

    `celdas`: `panel.CELDAS_VERDE` (`{celda: (columna_conteo, columna_area)}`).
    `contexto`: salida de `io.leer_contexto_cdmx()`. AGEB rural (fuera de `contexto`, que solo
    cubre el universo con geometría urbana -- en realidad `leer_contexto_cdmx` sí las incluye
    con ceros, pero se marcan `motivo_sin_datos='rural'` para que el frontend no las trate como
    "cero áreas verdes reales" sino como "no se puede estimar", igual que las demás capas).
    """
    tabla = contexto.set_index("cvegeo")
    rurales = set(universo.loc[universo["ambito"] == "rural", "cvegeo"])
    resultado: dict = {}
    for fila in universo.itertuples(index=False):
        clave = fila.cvegeo
        es_rural = clave in rurales
        celdas_registro: dict = {}
        for celda, (col_n, col_area) in celdas.items():
            if clave in tabla.index and not es_rural:
                celdas_registro[celda] = {
                    "nivel_base": int(tabla.loc[clave, col_n]),
                    "area_m2": round(float(tabla.loc[clave, col_area]), 1),
                    "motivo_sin_datos": None,
                }
            else:
                celdas_registro[celda] = {
                    "nivel_base": None,
                    "area_m2": None,
                    "motivo_sin_datos": "rural" if es_rural else "sin_poligono",
                }
        resultado[clave] = {
            "cve_mun": fila.cve_mun,
            "horizontes_disponibles": [],
            "celdas": celdas_registro,
        }
    return dict(sorted(resultado.items()))


def construir_distribucion_ageb(
    capa_ageb: dict, horizontes: list[str]
) -> dict[str, dict[str, dict[str, int]]]:
    """`{cve_mun: {horizonte: {veredicto: conteo}}}`, contando las AGEB de `capa_ageb`.

    P4 de `frontend_specs.md` §17. `capa_ageb`: la capa (demanda u oferta) ya
    construida por `construir_capa` a nivel AGEB (con `sin_datos` incluido).
    """
    resultado: dict[str, dict[str, dict[str, int]]] = {}
    for registro in capa_ageb.values():
        cve_mun = registro["cve_mun"]
        bucket = resultado.setdefault(
            cve_mun,
            {h: {"sube": 0, "se_mantiene": 0, "baja": 0, "sin_datos": 0} for h in horizontes},
        )
        for h in horizontes:
            veredicto = registro["h"][h]["veredicto"]
            bucket[h][veredicto] += 1
    return resultado


def _simulacion_cdmx(sim: Simulacion) -> Simulacion:
    """Agrega `sim` a una sola unidad "toda la CDMX" (reutiliza `agregar_alcaldia`)."""
    sim_uniforme = dataclasses.replace(sim, cve_mun=np.full(len(sim.clave), "cdmx", dtype=object))
    return agregar_alcaldia(sim_uniforme)


def _bloque_cdmx(resumen: dict[str, pd.DataFrame]) -> dict:
    """Agregado CDMX de un horizonte. `resumen[h]` puede llegar vacío (0 filas) cuando la
    celda no tiene ningún establecimiento en toda la ciudad (p. ej. `salud/farmacias__publico`,
    Fase 5 rework de sector): en ese caso el agregado CDMX también es `sin_datos`, nunca un
    `iloc[0]` sobre un DataFrame vacío."""
    primera = next(iter(resumen.values()))
    if primera.empty:
        return {"n_obs": 0, "h": {h: dict(_REGISTRO_H_SIN_DATOS) for h in resumen}}
    return {
        "n_obs": int(primera.iloc[0]["n_obs"]),
        "h": {h: _registro_h_valido(df.iloc[0]) for h, df in resumen.items()},
    }


def construir_agregado_cdmx(
    resumenes_demanda_cdmx: dict[str, dict[str, pd.DataFrame]],
    resumenes_ramas_cdmx: dict[str, dict[str, dict[str, pd.DataFrame]]],
    capa_verde_cdmx: dict,
) -> dict:
    """P2 de `frontend_specs.md` §17, generalizado a v1.4: agregado de toda la CDMX.

    `resumenes_demanda_cdmx`: `{segmento: resumen}` (salida de `modelos.resumir` sobre la
    simulación agregada a CDMX, `_simulacion_cdmx`). `resumenes_ramas_cdmx`: `{rama: {celda:
    resumen}}` para las 3 ramas con proyección. `capa_verde_cdmx`: registro único ya armado
    (mismo formato que una celda de `construir_capa_verde`, sin `cve_mun`).
    """
    demanda = {
        segmento: _bloque_cdmx(resumen) for segmento, resumen in resumenes_demanda_cdmx.items()
    }
    ramas: dict = {
        rama: {"celdas": {celda: _bloque_cdmx(resumen) for celda, resumen in celdas.items()}}
        for rama, celdas in resumenes_ramas_cdmx.items()
    }
    ramas["verde"] = capa_verde_cdmx
    return {"demanda": {"segmentos": demanda}, "ramas": ramas}


def _bloque_horizontes() -> list[dict]:
    return [
        {"clave": h, "anios": ANIOS_HORIZONTE[h], "fecha": FECHAS_HORIZONTE[h]}
        for h in ORDEN_HORIZONTES
    ]


def construir_salida_ageb(
    capa_demanda: dict, capas_ramas: dict[str, dict], generado: str
) -> dict:
    """Documento completo de `prediccion_ageb.json` (contrato v1.4).

    `capas_ramas`: `{rama: capa}`, ya en la forma anidada de
    `construir_capa_rama_v14`/`construir_capa_verde`. `capas.brecha` no existe en v1.4
    (`correccion/action_plan.md` #34).
    """
    return {
        "version": VERSION_CONTRATO,
        "generado": generado,
        "fecha_base": FECHA_BASE_ETIQUETA,
        "horizontes": _bloque_horizontes(),
        "capas": {"demanda": capa_demanda, "ramas": capas_ramas},
    }


def construir_salida_alcaldia(
    capa_demanda_mun: dict,
    capas_ramas_mun: dict[str, dict],
    distribucion_demanda: dict,
    agregado_cdmx: dict,
    generado: str,
) -> dict:
    """Documento completo de `prediccion_alcaldia.json` (contrato v1.4).

    `distribucion_ageb` (P4) se publica solo para demanda, segmento `todas` (el veredicto
    principal); las ramas no tienen un "veredicto" único a nivel celda que agregar de forma
    natural (cada celda tiene el suyo) -- alcance reducido deliberado de esta fase, documentado
    en `docs/metodologia.md` §10.6. `agregado_cdmx` (P2) en la raíz.
    """
    capa_demanda_mun = {
        cve_mun: {**registro, "distribucion_ageb": distribucion_demanda.get(cve_mun, {})}
        for cve_mun, registro in capa_demanda_mun.items()
    }
    return {
        "version": VERSION_CONTRATO,
        "generado": generado,
        "fecha_base": FECHA_BASE_ETIQUETA,
        "horizontes": _bloque_horizontes(),
        "capas": {"demanda": capa_demanda_mun, "ramas": capas_ramas_mun},
        "agregado_cdmx": agregado_cdmx,
    }


# ---------------------------------------------------------------------------
# Validación del contrato
# ---------------------------------------------------------------------------


def _validar_registro_h(clave: str, h_clave: str, bloque: dict, tope_confianza: str | None) -> None:
    if "veredicto" not in bloque or "confianza" not in bloque:
        raise ErrorContrato(f"{clave}/{h_clave}: falta 'veredicto' o 'confianza'")
    if bloque["veredicto"] not in VEREDICTOS_VALIDOS:
        raise ErrorContrato(f"{clave}/{h_clave}: veredicto inválido {bloque['veredicto']!r}")
    if bloque["confianza"] not in CONFIANZAS_VALIDAS:
        raise ErrorContrato(f"{clave}/{h_clave}: confianza inválida {bloque['confianza']!r}")
    if tope_confianza == "media" and bloque["confianza"] == "alta":
        raise ErrorContrato(
            f"{clave}/{h_clave}: la capa de oferta nunca debe tener confianza 'alta'"
        )
    if bloque["delta_pct"] is not None:
        if bloque["ic95"] is None:
            raise ErrorContrato(f"{clave}/{h_clave}: ic95 nulo con delta_pct no nulo")
        ic0, ic1 = bloque["ic95"]
        if not (ic0 <= bloque["delta_pct"] <= ic1):
            raise ErrorContrato(
                f"{clave}/{h_clave}: ic95 {bloque['ic95']} no contiene delta_pct {bloque['delta_pct']}"
            )


def _validar_capa(nombre_capa: str, capa: dict, horizontes_esperados: list[str], tope_confianza: str | None) -> None:
    for clave, registro in capa.items():
        if len(clave) not in (9, 13, 3):
            raise ErrorContrato(f"capa {nombre_capa}: clave con longitud inválida {clave!r}")
        if "n_obs" not in registro:
            raise ErrorContrato(f"capa {nombre_capa}/{clave}: falta 'n_obs'")
        h = registro.get("h")
        if h is None or list(h.keys()) != horizontes_esperados:
            raise ErrorContrato(
                f"capa {nombre_capa}/{clave}: 'h' debe traer exactamente "
                f"{horizontes_esperados} en orden, llegó {list(h.keys()) if h else h}"
            )
        for h_clave, bloque in h.items():
            _validar_registro_h(f"{nombre_capa}/{clave}", h_clave, bloque, tope_confianza)


_CELDAS_POR_RAMA: dict[str, dict] = {
    "educacion": CELDAS_EDUCACION,
    "salud": CELDAS_SALUD,
    "comercio": CELDAS_COMERCIO,
    "verde": CELDAS_VERDE,
}


def validar_contrato(salida: dict, nivel: Literal["ageb", "alcaldia"]) -> None:
    """Valida un documento completo (AGEB o alcaldía) contra el contrato v1.4.

    No valida la identidad cruzada Σ AGEB == alcaldía (necesita ambos
    documentos a la vez): eso lo hace `verificar_suma_ageb_alcaldia`.
    """
    if salida.get("version") != VERSION_CONTRATO:
        raise ErrorContrato(
            f"version debe ser {VERSION_CONTRATO!r}, llegó {salida.get('version')!r}"
        )

    horizontes = salida.get("horizontes") or []
    claves_horizonte = [h.get("clave") for h in horizontes]
    if claves_horizonte != list(ORDEN_HORIZONTES):
        raise ErrorContrato(
            f"'horizontes' debe traer exactamente {ORDEN_HORIZONTES} en orden, "
            f"llegó {claves_horizonte}"
        )

    capas = salida.get("capas") or {}
    if "demanda" not in capas or "ramas" not in capas:
        raise ErrorContrato("faltan las capas 'demanda' y/o 'ramas'")

    demanda = capas["demanda"]
    for clave, registro in demanda.items():
        if len(clave) not in (9, 13, 3):
            raise ErrorContrato(f"demanda: clave con longitud inválida {clave!r}")
        segmentos = registro.get("segmentos")
        if segmentos is None or set(segmentos) != set(SEGMENTOS_DEMANDA):
            raise ErrorContrato(
                f"demanda/{clave}: 'segmentos' debe traer exactamente {SEGMENTOS_DEMANDA}, "
                f"llegó {sorted(segmentos) if segmentos else segmentos}"
            )
        for segmento, sub in segmentos.items():
            _validar_capa(
                f"demanda.{segmento}", {clave: sub}, list(ORDEN_HORIZONTES), tope_confianza=None
            )

    ramas = capas["ramas"]
    if set(ramas) != set(RAMAS):
        raise ErrorContrato(f"'ramas' debe traer exactamente {RAMAS}, llegó {sorted(ramas)}")

    horizontes_rama = list(HORIZONTES_OFERTA)
    for rama in RAMAS_CON_PROYECCION:
        capa_rama = ramas[rama]
        celdas_esperadas = set(_CELDAS_POR_RAMA[rama])
        for clave, registro in capa_rama.items():
            if registro.get("horizontes_disponibles") != horizontes_rama:
                raise ErrorContrato(
                    f"{rama}/{clave}: horizontes_disponibles debe ser {horizontes_rama}, "
                    f"llegó {registro.get('horizontes_disponibles')}"
                )
            celdas = registro.get("celdas")
            if celdas is None or set(celdas) != celdas_esperadas:
                raise ErrorContrato(
                    f"{rama}/{clave}: 'celdas' debe traer exactamente {sorted(celdas_esperadas)}"
                )
            for celda_nombre, sub in celdas.items():
                _validar_capa(
                    f"{rama}.{celda_nombre}", {clave: sub}, horizontes_rama, tope_confianza="media"
                )

    capa_verde = ramas["verde"]
    celdas_verde_esperadas = set(_CELDAS_POR_RAMA["verde"])
    for clave, registro in capa_verde.items():
        if registro.get("horizontes_disponibles") != []:
            raise ErrorContrato(f"verde/{clave}: horizontes_disponibles debe ser []")
        celdas = registro.get("celdas")
        if celdas is None or set(celdas) != celdas_verde_esperadas:
            raise ErrorContrato(f"verde/{clave}: 'celdas' debe traer exactamente {sorted(celdas_verde_esperadas)}")
        for celda_nombre, sub in celdas.items():
            if "h" in sub or "serie" in sub:
                raise ErrorContrato(
                    f"verde/{clave}/{celda_nombre}: no debe traer 'h' ni 'serie' (sin proyección, metodología §10.1)"
                )
            if "nivel_base" not in sub or "motivo_sin_datos" not in sub:
                raise ErrorContrato(f"verde/{clave}/{celda_nombre}: faltan 'nivel_base'/'motivo_sin_datos'")

    if nivel == "alcaldia":
        if set(demanda.keys()) != _ALCALDIAS_VALIDAS:
            raise ErrorContrato(
                f"capa demanda: se esperaban las 16 claves cve_mun 002-017, "
                f"llegó {sorted(demanda.keys())}"
            )
        for rama in RAMAS:
            if set(ramas[rama].keys()) != _ALCALDIAS_VALIDAS:
                raise ErrorContrato(f"rama {rama}: se esperaban las 16 claves cve_mun 002-017")
        if "agregado_cdmx" not in salida:
            raise ErrorContrato("falta 'agregado_cdmx' en el documento de alcaldía")
    else:
        for clave in demanda:
            if len(clave) not in (9, 13):
                raise ErrorContrato(f"cvegeo con longitud inválida: {clave!r}")


def verificar_suma_ageb_alcaldia(
    salida_ageb: dict, salida_alcaldia: dict, rtol: float = 0.05
) -> None:
    """Σ nivel AGEB == nivel alcaldía por horizonte, capa demanda (plan §7).

    La identidad **exacta** (`1e-9`) es una propiedad algebraica de
    `agregar_alcaldia` sobre el nivel proyectado por réplica Monte Carlo
    (`Σ_i base_i·exp(r_fut_i^s·horizonte) == base_mun·exp(r_fut_mun^s·horizonte)`
    para cada réplica `s`; ya probada en
    `test_modelos.py::TestAgregarAlcaldia`). Pero `delta_pct`/`nivel_base`
    del contrato son la **mediana** de esa cantidad a través de las réplicas
    (`resumir()`), y la mediana no es lineal (Jensen): la mediana de una
    suma no es la suma de las medianas, ni siquiera antes de redondear a 1
    decimal. Verificado con datos reales: la alcaldía más discrepante
    (`016`) llega a ~4.4 % de error relativo en `h3` por esta no linealidad,
    sin que haya ningún error de agregación. Por eso esta función usa una
    tolerancia relativa laxa (`0.05` = 5 % por defecto) pensada para atrapar
    errores gruesos (una alcaldía completa faltante o mal sumada), no para
    exigir una precisión que la propia definición estadística del contrato
    ya excluye. Desviación deliberada, documentada, de la cifra `1e-6` del
    plan original (pensada sobre la tabla intermedia sin redondear y sin
    medianas, `data/interim/proyeccion_ageb.parquet`, no sobre el JSON
    final).
    """
    # Segmento "todas" (metodología §1.1): el veredicto principal, mismo que verificaba esta
    # función en v1.2 antes de que la demanda se anidara por segmento (Fase 4/6).
    capa_ageb = {
        clave: registro["segmentos"]["todas"] for clave, registro in salida_ageb["capas"]["demanda"].items()
    }
    capa_mun = {
        clave: registro["segmentos"]["todas"] for clave, registro in salida_alcaldia["capas"]["demanda"].items()
    }

    for h in ORDEN_HORIZONTES:
        niveles_por_mun: dict[str, float] = {}
        for clave, registro in capa_ageb.items():
            cve_mun = salida_ageb["capas"]["demanda"][clave]["cve_mun"]
            nivel_base = registro["nivel_base"]
            delta_pct = registro["h"][h]["delta_pct"]
            if nivel_base is None or delta_pct is None:
                continue
            nivel = nivel_base * (1.0 + delta_pct / 100.0)
            niveles_por_mun[cve_mun] = niveles_por_mun.get(cve_mun, 0.0) + nivel

        for cve_mun, registro_mun in capa_mun.items():
            esperado = niveles_por_mun.get(cve_mun, 0.0)
            nivel_base_mun = registro_mun["nivel_base"]
            delta_pct_mun = registro_mun["h"][h]["delta_pct"]
            if nivel_base_mun is None or delta_pct_mun is None:
                continue
            obtenido = nivel_base_mun * (1.0 + delta_pct_mun / 100.0)
            if esperado == 0.0:
                continue
            error_relativo = abs(obtenido - esperado) / abs(esperado)
            if error_relativo > rtol:
                raise ErrorContrato(
                    f"suma AGEB != alcaldía en {cve_mun}/{h}: "
                    f"Σ AGEB={esperado:.2f}, alcaldía={obtenido:.2f} "
                    f"(error relativo {error_relativo:.2e} > {rtol:.0e})"
                )


# ---------------------------------------------------------------------------
# Escritura determinista
# ---------------------------------------------------------------------------


def escribir_json(salida: dict, ruta: Path) -> None:
    """Escribe `salida` de forma determinista: `ensure_ascii=False`, claves
    ordenadas, separadores compactos (misma semilla -> mismo archivo byte a
    byte salvo `generado`)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _generado_iso() -> str:
    """ISO-8601 con zona; usa `SOURCE_DATE_EPOCH` si está definido (reproducibilidad)."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat(timespec="seconds")
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Orquestación (`make pipeline`)
# ---------------------------------------------------------------------------


def _agregar_verde_tabla(contexto: pd.DataFrame, clave_col: str, celdas: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """Suma las columnas de conteo/área de `io.leer_contexto_cdmx()` agrupando por `clave_col`
    (`cve_mun` para el nivel alcaldía; se usa tal cual, sin agrupar, para CDMX)."""
    columnas = [c for par in celdas.values() for c in par]
    agregado = contexto.groupby(clave_col)[columnas].sum().reset_index()
    agregado = agregado.rename(columns={clave_col: "cvegeo"})
    agregado["cve_mun"] = agregado["cvegeo"]
    return agregado


def main() -> None:
    """`io -> panel -> backtest -> modelos -> features -> exportar`; log en español con conteos.

    Contrato v1.4 (Fase 6 de `correccion/action_plan.md`): 6 segmentos de demanda
    (`panel.SEGMENTOS_DEMANDA`) x 3 niveles territoriales (AGEB, alcaldía, CDMX) + 3 ramas con
    proyección (`educacion` 8 celdas, `salud` 4, `comercio` 5, `panel.CELDAS_*`) x 3 niveles +
    la rama `verde` sin proyección. `backtest.py` corre una sola vez, sobre el panel
    `segmento="total_0a14"` (el alcance ya validado en las Fases 2/3, `docs/backtest.md`): no
    se revalida por cada uno de los 6 segmentos ni de las 17 celdas.
    """
    from chipos.backtest import ejecutar as ejecutar_backtest, escribir_reporte as escribir_reporte_backtest
    from chipos.io import (
        conectar,
        leer_censo_panel,
        leer_conapo_0a14,
        leer_contexto_cdmx,
        leer_denue_comercios,
        leer_denue_infancias,
        leer_denue_salud,
        leer_equivalencia,
        leer_universo_ageb,
    )
    from chipos.modelos import ajustar_oferta, simular_demanda, simular_oferta
    from chipos.panel import (
        construir_panel_demanda,
        construir_panel_oferta,
        construir_panel_oferta_celda,
        filtro_celda_comercio,
        filtro_celda_educacion,
        filtro_celda_salud,
        reporte_cobertura,
    )

    print("chipos.exportar: leyendo datos...")
    universo = leer_universo_ageb()
    censo = leer_censo_panel()
    equivalencia = leer_equivalencia()
    conapo = leer_conapo_0a14()
    con = conectar()
    infancias = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))
    salud = leer_denue_salud(con, list(CORTES_OFERTA.keys()))
    comercios = leer_denue_comercios(list(CORTES_OFERTA.keys()))
    contexto_cdmx = leer_contexto_cdmx()

    panel_d_backtest = construir_panel_demanda(censo, equivalencia, universo, segmento="total_0a14")
    panel_o_backtest = construir_panel_oferta(infancias, universo)
    cobertura = reporte_cobertura(panel_d_backtest, panel_o_backtest, universo)
    print(
        f"chipos.exportar: universo={cobertura['universo_total']} "
        f"(urbano={cobertura['universo_urbano']}, rural={cobertura['universo_rural']}); "
        f"demanda con dato={cobertura['demanda_n_con_dato']}"
    )

    print("chipos.exportar: corriendo backtest (validación retrospectiva)...")
    rng_backtest = np.random.default_rng(SEMILLA)
    resultados_backtest = ejecutar_backtest(panel_d_backtest, panel_o_backtest, conapo, rng_backtest)
    escribir_reporte_backtest(resultados_backtest)
    print(
        f"chipos.exportar: backtest -> modelo_se_adopta="
        f"{resultados_backtest['adopcion']['modelo_se_adopta']} "
        f"(ver docs/backtest.md)"
    )

    rng = np.random.default_rng(SEMILLA)
    munes = pd.DataFrame({"cvegeo": sorted(_ALCALDIAS_VALIDAS), "cve_mun": sorted(_ALCALDIAS_VALIDAS)})

    # --- Demanda: 6 segmentos (metodología §1.1) ---
    print(f"chipos.exportar: simulando demanda ({len(SEGMENTOS_DEMANDA)} segmentos)...")
    capas_demanda_ageb: dict[str, dict] = {}
    capas_demanda_mun: dict[str, dict] = {}
    resumenes_demanda_cdmx: dict[str, dict] = {}
    for segmento in SEGMENTOS_DEMANDA:
        panel_d_seg = construir_panel_demanda(censo, equivalencia, universo, segmento=segmento)
        sim_d = simular_demanda(panel_d_seg, conapo, rng)
        sim_d_mun = agregar_alcaldia(sim_d)

        res_d = resumir(sim_d, HORIZONTES)
        res_d_mun = resumir(sim_d_mun, HORIZONTES)
        motivos_d = motivos_demanda_por_clave(panel_d_seg)
        nivel_base_d = nivel_en(sim_d, T_2020)
        nivel_base_d_mun = nivel_en(sim_d_mun, T_2020)

        capas_demanda_ageb[segmento] = construir_capa(
            res_d, universo, serie_demanda_por_clave(panel_d_seg), nivel_base_d,
            list(ORDEN_HORIZONTES), motivos_d,
        )
        capas_demanda_mun[segmento] = construir_capa(
            res_d_mun, munes, serie_demanda_alcaldia_por_clave(panel_d_seg), nivel_base_d_mun,
            list(ORDEN_HORIZONTES), {m: None for m in _ALCALDIAS_VALIDAS},
        )
        resumenes_demanda_cdmx[segmento] = resumir(_simulacion_cdmx(sim_d), HORIZONTES)

    capa_demanda = construir_capa_demanda_v14(capas_demanda_ageb)
    capa_demanda_mun = construir_capa_demanda_v14(capas_demanda_mun)
    distribucion_demanda = construir_distribucion_ageb(capas_demanda_ageb["todas"], list(ORDEN_HORIZONTES))

    # --- Ramas con proyección: educación, salud, comercio (celdas, metodología §10.6) ---
    horizontes_oferta = {h: HORIZONTES[h] for h in HORIZONTES_OFERTA}
    denue_por_rama = {"educacion": infancias, "salud": salud, "comercio": comercios}
    filtro_por_rama = {
        "educacion": filtro_celda_educacion,
        "salud": filtro_celda_salud,
        "comercio": filtro_celda_comercio,
    }

    capas_ramas_ageb: dict[str, dict] = {}
    capas_ramas_mun: dict[str, dict] = {}
    resumenes_ramas_cdmx: dict[str, dict] = {}

    for rama in RAMAS_CON_PROYECCION:
        celdas_rama = _CELDAS_POR_RAMA[rama]
        denue_rama = denue_por_rama[rama]
        filtro_fn = filtro_por_rama[rama]
        print(f"chipos.exportar: simulando rama '{rama}' ({len(celdas_rama)} celdas)...")

        capas_celda_ageb: dict[str, dict] = {}
        capas_celda_mun: dict[str, dict] = {}
        resumenes_celda_cdmx: dict[str, dict] = {}

        for celda in celdas_rama:
            filtro = filtro_fn(denue_rama, celda)
            panel_o_celda = construir_panel_oferta_celda(denue_rama, universo, filtro)
            ajuste_celda = ajustar_oferta(panel_o_celda)
            sim_o = simular_oferta(ajuste_celda, rng)
            sim_o_mun = agregar_alcaldia(sim_o)

            res_o = resumir(sim_o, horizontes_oferta)
            res_o_mun = resumir(sim_o_mun, horizontes_oferta)
            motivos_o = motivos_oferta_por_clave(universo, ajuste_celda)
            nivel_base_o = nivel_en(sim_o, max(CORTES_OFERTA.values()))
            nivel_base_o_mun = nivel_en(sim_o_mun, max(CORTES_OFERTA.values()))

            capas_celda_ageb[celda] = construir_capa(
                res_o, universo, serie_oferta_por_clave(panel_o_celda), nivel_base_o,
                list(HORIZONTES_OFERTA), motivos_o, incluir_horizontes_disponibles=True,
            )
            capas_celda_mun[celda] = construir_capa(
                res_o_mun, munes, serie_oferta_alcaldia_por_clave(panel_o_celda), nivel_base_o_mun,
                list(HORIZONTES_OFERTA), {m: None for m in _ALCALDIAS_VALIDAS}, incluir_horizontes_disponibles=True,
            )
            resumenes_celda_cdmx[celda] = resumir(_simulacion_cdmx(sim_o), horizontes_oferta)

        capas_ramas_ageb[rama] = construir_capa_rama_v14(capas_celda_ageb, list(HORIZONTES_OFERTA))
        capas_ramas_mun[rama] = construir_capa_rama_v14(capas_celda_mun, list(HORIZONTES_OFERTA))
        resumenes_ramas_cdmx[rama] = resumenes_celda_cdmx

    # --- Verde: sin proyección (metodología §10.1) ---
    print("chipos.exportar: capa 'verde' (sin proyección, un solo corte)...")
    capas_ramas_ageb["verde"] = construir_capa_verde(contexto_cdmx, universo, CELDAS_VERDE)

    contexto_mun = _agregar_verde_tabla(contexto_cdmx, "cve_mun", CELDAS_VERDE)
    munes_urbanas = munes.assign(ambito="urbano")
    capas_ramas_mun["verde"] = construir_capa_verde(contexto_mun, munes_urbanas, CELDAS_VERDE)

    fila_cdmx = contexto_cdmx[[c for par in CELDAS_VERDE.values() for c in par]].sum()
    capa_verde_cdmx = {
        "horizontes_disponibles": [],
        "celdas": {
            celda: {
                "nivel_base": int(fila_cdmx[col_n]),
                "area_m2": round(float(fila_cdmx[col_area]), 1),
                "motivo_sin_datos": None,
            }
            for celda, (col_n, col_area) in CELDAS_VERDE.items()
        },
    }

    generado = _generado_iso()
    salida_ageb = construir_salida_ageb(capa_demanda, capas_ramas_ageb, generado)
    validar_contrato(salida_ageb, "ageb")
    escribir_json(salida_ageb, RUTA_PREDICCION_AGEB)
    print(f"chipos.exportar: {RUTA_PREDICCION_AGEB} escrito ({len(capa_demanda)} AGEB).")

    agregado_cdmx = construir_agregado_cdmx(resumenes_demanda_cdmx, resumenes_ramas_cdmx, capa_verde_cdmx)
    salida_alcaldia = construir_salida_alcaldia(
        capa_demanda_mun, capas_ramas_mun, distribucion_demanda, agregado_cdmx, generado,
    )
    validar_contrato(salida_alcaldia, "alcaldia")
    verificar_suma_ageb_alcaldia(salida_ageb, salida_alcaldia)
    escribir_json(salida_alcaldia, RUTA_PREDICCION_ALCALDIA)
    print(f"chipos.exportar: {RUTA_PREDICCION_ALCALDIA} escrito (16 alcaldías).")

    print("chipos.exportar: sensibilidad K del índice de oportunidad (diagnostico.json)...")
    from chipos.features import construir_sensibilidad_oportunidad, escribir_diagnostico

    demanda_todas = {cve: reg["segmentos"]["todas"] for cve, reg in capa_demanda.items()}
    sensibilidad = construir_sensibilidad_oportunidad(
        demanda_todas, {r: capas_ramas_ageb[r] for r in RAMAS_CON_PROYECCION},
    )
    escribir_diagnostico({
        "generado": generado,
        "sensibilidad_oportunidad": sensibilidad,
    })
    print(f"chipos.exportar: {RUTA_DIAGNOSTICO} actualizado con sensibilidad_oportunidad.")


if __name__ == "__main__":
    main()
