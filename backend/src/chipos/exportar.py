"""Exportación del contrato v1.2 (`exportar.py`, punto de entrada de `make pipeline`).

Tarea B11 de `plans/backend_plan.md` (nunca implementada contra v1.1: se
construye aquí directo contra el shape v1.2 de `plans/frontend_specs.md`
§17, con las decisiones §18.1/§18.2 ya adoptadas — ver también el plan de
migración `graceful-swinging-shell.md`).

Contenido:
- `construir_capa` / `construir_distribucion_ageb` / `construir_agregado_cdmx`:
  bloques reutilizables del contrato (AGEB y alcaldía comparten estructura).
- `construir_salida_ageb` / `construir_salida_alcaldia`: ensamblan el
  documento completo (`version`, `fecha_base`, `horizontes`, `capas`, y en
  alcaldía además `agregado_cdmx`).
- `validar_contrato`: valida un documento (AGEB o alcaldía) por separado;
  `verificar_suma_ageb_alcaldia` valida la identidad cruzada entre ambos
  archivos (Σ AGEB == alcaldía).
- `main()`: orquesta `io → panel → modelos → exportar` y escribe los dos
  JSON de `data/outputs/`. `backtest.py` (B9) no existe todavía en el
  repositorio: `main()` no lo invoca (ver docstring de `main`).
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
    RUTA_PREDICCION_AGEB,
    RUTA_PREDICCION_ALCALDIA,
    SEMILLA,
    T_2010,
    T_2020,
    T_BASE,
)
from chipos.io import CORTES_OFERTA
from chipos.modelos import Simulacion, agregar_alcaldia, resumir

# ---------------------------------------------------------------------------
# Constantes del contrato (tablas literales; nunca conversión numérica
# año-decimal -> "YYYY-MM" genérica, ver plan de migración).
# ---------------------------------------------------------------------------

VERSION_CONTRATO = "1.2"
FECHA_BASE_ETIQUETA = "2026-06"
ORDEN_HORIZONTES: tuple[str, ...] = ("h3", "h5", "h7")
FECHAS_HORIZONTE: dict[str, str] = {"h3": "2029-06", "h5": "2031-06", "h7": "2033-06"}
ANIOS_HORIZONTE: dict[str, int] = {"h3": 3, "h5": 5, "h7": 7}

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

_UNIDAD_BRECHA = "establecimientos por 1,000 de 0 a 14 años"

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


def construir_agregado_cdmx(
    resumen_demanda_cdmx: dict[str, pd.DataFrame],
    resumen_oferta_cdmx: dict[str, pd.DataFrame],
) -> dict:
    """P2 de `frontend_specs.md` §17: agregado de toda la CDMX, para el titular."""

    def _bloque(resumen: dict[str, pd.DataFrame]) -> dict:
        primera = next(iter(resumen.values()))
        return {
            "n_obs": int(primera.iloc[0]["n_obs"]),
            "h": {h: _registro_h_valido(df.iloc[0]) for h, df in resumen.items()},
        }

    return {"demanda": _bloque(resumen_demanda_cdmx), "oferta": _bloque(resumen_oferta_cdmx)}


def construir_capa_brecha_ageb(brecha_ageb: pd.DataFrame) -> dict:
    """Capa `brecha` (P5, opcional, sin veredicto) a nivel AGEB, desde `features.calcular_brecha_ageb`."""
    t_oferta = max(CORTES_OFERTA.values())
    resultado: dict = {}
    for fila in brecha_ageb.itertuples(index=False):
        valor = fila.brecha_por_mil
        resultado[fila.cvegeo] = {
            "cve_mun": fila.cve_mun,
            "valor": None if pd.isna(valor) else round(float(valor), 2),
            "unidad": _UNIDAD_BRECHA,
            "t_oferta": t_oferta,
            "t_demanda": T_2020,
        }
    return dict(sorted(resultado.items()))


def construir_capa_brecha_alcaldia(brecha_alcaldia: pd.DataFrame) -> dict:
    """Capa `brecha` a nivel alcaldía, desde `features.calcular_brecha_alcaldia`."""
    t_oferta = max(CORTES_OFERTA.values())
    resultado: dict = {}
    for fila in brecha_alcaldia.itertuples(index=False):
        valor = fila.brecha_por_mil
        resultado[fila.cve_mun] = {
            "valor": None if pd.isna(valor) else round(float(valor), 2),
            "unidad": _UNIDAD_BRECHA,
            "t_oferta": t_oferta,
            "t_demanda": T_2020,
        }
    return dict(sorted(resultado.items()))


def _bloque_horizontes() -> list[dict]:
    return [
        {"clave": h, "anios": ANIOS_HORIZONTE[h], "fecha": FECHAS_HORIZONTE[h]}
        for h in ORDEN_HORIZONTES
    ]


def construir_salida_ageb(
    capa_demanda: dict, capa_oferta: dict, capa_brecha: dict, generado: str
) -> dict:
    """Documento completo de `prediccion_ageb.json` (contrato v1.2)."""
    return {
        "version": VERSION_CONTRATO,
        "generado": generado,
        "fecha_base": FECHA_BASE_ETIQUETA,
        "horizontes": _bloque_horizontes(),
        "capas": {"demanda": capa_demanda, "oferta": capa_oferta, "brecha": capa_brecha},
    }


def construir_salida_alcaldia(
    capa_demanda_mun: dict,
    capa_oferta_mun: dict,
    capa_brecha_mun: dict,
    distribucion_demanda: dict,
    distribucion_oferta: dict,
    agregado_cdmx: dict,
    generado: str,
) -> dict:
    """Documento completo de `prediccion_alcaldia.json`, con `distribucion_ageb` (P4) por
    alcaldía y capa, y `agregado_cdmx` (P2) en la raíz."""
    capa_demanda_mun = {
        cve_mun: {**registro, "distribucion_ageb": distribucion_demanda.get(cve_mun, {})}
        for cve_mun, registro in capa_demanda_mun.items()
    }
    capa_oferta_mun = {
        cve_mun: {**registro, "distribucion_ageb": distribucion_oferta.get(cve_mun, {})}
        for cve_mun, registro in capa_oferta_mun.items()
    }
    return {
        "version": VERSION_CONTRATO,
        "generado": generado,
        "fecha_base": FECHA_BASE_ETIQUETA,
        "horizontes": _bloque_horizontes(),
        "capas": {
            "demanda": capa_demanda_mun,
            "oferta": capa_oferta_mun,
            "brecha": capa_brecha_mun,
        },
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


def validar_contrato(salida: dict, nivel: Literal["ageb", "alcaldia"]) -> None:
    """Valida un documento completo (AGEB o alcaldía) contra el contrato v1.2.

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
    if "demanda" not in capas or "oferta" not in capas:
        raise ErrorContrato("faltan las capas 'demanda' y/o 'oferta'")

    _validar_capa("demanda", capas["demanda"], list(ORDEN_HORIZONTES), tope_confianza=None)
    _validar_capa("oferta", capas["oferta"], list(HORIZONTES_OFERTA), tope_confianza="media")

    if nivel == "alcaldia":
        for nombre_capa in ("demanda", "oferta"):
            claves = set(capas[nombre_capa].keys())
            if claves != _ALCALDIAS_VALIDAS:
                raise ErrorContrato(
                    f"capa {nombre_capa}: se esperaban las 16 claves cve_mun "
                    f"002-017, llegó {sorted(claves)}"
                )
        if "agregado_cdmx" not in salida:
            raise ErrorContrato("falta 'agregado_cdmx' en el documento de alcaldía")
    else:
        vistas: set[str] = set()
        for nombre_capa in ("demanda", "oferta"):
            for clave in capas[nombre_capa]:
                if nombre_capa == "demanda":
                    if clave in vistas:
                        raise ErrorContrato(f"cvegeo duplicado: {clave}")
                    vistas.add(clave)
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
    capa_ageb = salida_ageb["capas"]["demanda"]
    capa_mun = salida_alcaldia["capas"]["demanda"]

    for h in ORDEN_HORIZONTES:
        niveles_por_mun: dict[str, float] = {}
        for registro in capa_ageb.values():
            nivel_base = registro["nivel_base"]
            delta_pct = registro["h"][h]["delta_pct"]
            if nivel_base is None or delta_pct is None:
                continue
            nivel = nivel_base * (1.0 + delta_pct / 100.0)
            niveles_por_mun[registro["cve_mun"]] = niveles_por_mun.get(registro["cve_mun"], 0.0) + nivel

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


def main() -> None:
    """`io -> panel -> modelos -> exportar`; log en español con conteos.

    `backtest.py` (B9 de `plans/backend_plan.md`) no existe todavía en el
    repositorio (fuera del alcance de esta tarea): este `main()` no lo
    invoca; cuando exista, se añade aquí entre `panel` y `exportar` sin
    cambiar el resto del pipeline.
    """
    from chipos.features import calcular_brecha_ageb, calcular_brecha_alcaldia
    from chipos.io import (
        conectar,
        leer_censo_panel,
        leer_conapo_0a14,
        leer_denue_infancias,
        leer_equivalencia,
        leer_universo_ageb,
    )
    from chipos.panel import construir_panel_demanda, construir_panel_oferta, reporte_cobertura
    from chipos.modelos import ajustar_oferta, simular_demanda, simular_oferta

    print("chipos.exportar: leyendo datos...")
    universo = leer_universo_ageb()
    censo = leer_censo_panel()
    equivalencia = leer_equivalencia()
    conapo = leer_conapo_0a14()
    con = conectar()
    denue = leer_denue_infancias(con, list(CORTES_OFERTA.keys()))

    panel_d = construir_panel_demanda(censo, equivalencia, universo)
    panel_o = construir_panel_oferta(denue, universo)
    cobertura = reporte_cobertura(panel_d, panel_o, universo)
    print(
        f"chipos.exportar: universo={cobertura['universo_total']} "
        f"(urbano={cobertura['universo_urbano']}, rural={cobertura['universo_rural']}); "
        f"demanda con dato={cobertura['demanda_n_con_dato']}"
    )

    rng = np.random.default_rng(SEMILLA)
    sim_d = simular_demanda(panel_d, conapo, rng)
    sim_o = simular_oferta(ajustar_oferta(panel_o), rng)
    sim_d_mun = agregar_alcaldia(sim_d)
    sim_o_mun = agregar_alcaldia(sim_o)

    res_d = resumir(sim_d, HORIZONTES)
    res_o = resumir(sim_o, {"h3": HORIZONTES["h3"]})
    res_d_mun = resumir(sim_d_mun, HORIZONTES)
    res_o_mun = resumir(sim_o_mun, {"h3": HORIZONTES["h3"]})

    motivos_d = motivos_demanda_por_clave(panel_d)
    ajuste = ajustar_oferta(panel_o)
    motivos_o = motivos_oferta_por_clave(universo, ajuste)

    nivel_base_d = nivel_en(sim_d, T_2020)
    nivel_base_o = nivel_en(sim_o, max(CORTES_OFERTA.values()))
    nivel_base_d_mun = nivel_en(sim_d_mun, T_2020)
    nivel_base_o_mun = nivel_en(sim_o_mun, max(CORTES_OFERTA.values()))

    capa_demanda = construir_capa(
        res_d, universo, serie_demanda_por_clave(panel_d), nivel_base_d, list(ORDEN_HORIZONTES), motivos_d
    )
    capa_oferta = construir_capa(
        res_o, universo, serie_oferta_por_clave(panel_o), nivel_base_o,
        list(HORIZONTES_OFERTA), motivos_o, incluir_horizontes_disponibles=True,
    )

    brecha_ageb = calcular_brecha_ageb(panel_d, panel_o)
    brecha_alcaldia = calcular_brecha_alcaldia(brecha_ageb)
    capa_brecha_ageb = construir_capa_brecha_ageb(brecha_ageb)
    capa_brecha_alcaldia = construir_capa_brecha_alcaldia(brecha_alcaldia)

    generado = _generado_iso()
    salida_ageb = construir_salida_ageb(capa_demanda, capa_oferta, capa_brecha_ageb, generado)
    validar_contrato(salida_ageb, "ageb")
    escribir_json(salida_ageb, RUTA_PREDICCION_AGEB)
    print(f"chipos.exportar: {RUTA_PREDICCION_AGEB} escrito ({len(capa_demanda)} AGEB).")

    munes = pd.DataFrame({"cvegeo": sorted(_ALCALDIAS_VALIDAS), "cve_mun": sorted(_ALCALDIAS_VALIDAS)})
    capa_demanda_mun = construir_capa(
        res_d_mun, munes, serie_demanda_alcaldia_por_clave(panel_d), nivel_base_d_mun,
        list(ORDEN_HORIZONTES), {m: None for m in _ALCALDIAS_VALIDAS},
    )
    capa_oferta_mun = construir_capa(
        res_o_mun, munes, serie_oferta_alcaldia_por_clave(panel_o), nivel_base_o_mun,
        list(HORIZONTES_OFERTA), {m: None for m in _ALCALDIAS_VALIDAS}, incluir_horizontes_disponibles=True,
    )
    distribucion_demanda = construir_distribucion_ageb(capa_demanda, list(ORDEN_HORIZONTES))
    distribucion_oferta = construir_distribucion_ageb(capa_oferta, list(HORIZONTES_OFERTA))

    resumen_cdmx_d = resumir(_simulacion_cdmx(sim_d), HORIZONTES)
    resumen_cdmx_o = resumir(_simulacion_cdmx(sim_o), {"h3": HORIZONTES["h3"]})
    agregado_cdmx = construir_agregado_cdmx(resumen_cdmx_d, resumen_cdmx_o)

    salida_alcaldia = construir_salida_alcaldia(
        capa_demanda_mun, capa_oferta_mun, capa_brecha_alcaldia,
        distribucion_demanda, distribucion_oferta, agregado_cdmx, generado,
    )
    validar_contrato(salida_alcaldia, "alcaldia")
    verificar_suma_ageb_alcaldia(salida_ageb, salida_alcaldia)
    escribir_json(salida_alcaldia, RUTA_PREDICCION_ALCALDIA)
    print(f"chipos.exportar: {RUTA_PREDICCION_ALCALDIA} escrito (16 alcaldías).")


if __name__ == "__main__":
    main()
