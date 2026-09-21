#!/usr/bin/env python3
"""Genera los mocks deterministas del frontend (contratos v1.1 y v1.4).

Lee UNICAMENTE las propiedades (cvegeo, cve_mun, ambito) de
``data/reference/ageb_cdmx_simplificado.geojson`` -- nunca geometrias -- para
obtener el universo real de AGEB y alcaldias, y con eso escribe:

- ``prediccion_ageb.json`` / ``prediccion_alcaldia.json``
  Contrato v1.4 (plans/frontend_specs.md §17-18, CLAUDE.md "Contrato de
  salida"): ``fecha_base``, 3 horizontes (``h1``/``h3``/``h5``), 6 segmentos
  de demanda (``segmentos.<segmento>``) y 4 ramas de oferta
  (``ramas.{educacion,salud,comercio,verde}.celdas.<celda>``), con
  ``distribucion_ageb``/``agregado_cdmx`` en el archivo de alcaldia. Es el
  mock "base" (``?mock=1``/sin parametro), fixture principal de desarrollo.
  Actualizado en F-5 de `correccion/avance_plan.md` -- antes se quedaba en
  v1.2 (a medias de la migracion real de `exportar.py`).
- ``prediccion_ageb_v11.json`` / ``prediccion_alcaldia_v11.json``
  Contrato v1.1 (un solo horizonte), para probar la degradacion del slider
  (``?mock=v11``, js/config.js).
- ``prediccion_ageb_v11_invalido.json``  mismo esquema v1.1 con ``version``
  incompatible, para ejercitar el estado de error del frontend
  (``?mock=version_invalida``).

Solo biblioteca estandar de Python. Sin geopandas. Determinista: para una
misma version de ``data/reference/ageb_cdmx_simplificado.geojson`` y esta
misma semilla, dos ejecuciones producen exactamente los mismos valores salvo
el campo ``generado`` (marca de tiempo de la ejecucion).

Uso:
    python3 frontend/mock/generar_mock.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import random
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parents[2]
GEOJSON_AGEB = RAIZ / "data" / "reference" / "ageb_cdmx_simplificado.geojson"
DIR_SALIDA = pathlib.Path(__file__).resolve().parent

SEMILLA = "chipos-dataton-mock-v1"
VERSION_CONTRATO_V11 = "1.1"
VERSION_INVALIDA = "1.9"
HORIZONTE = "2027-06"  # v1.1: horizonte unico (decision previa, ver CLAUDE.md).

# Horizontes 1/3/5 anios (correccion/action_plan.md Fase 1: cumple
# correccion/rubrica.md §5 "uno, tres o cinco anios"), version del contrato v1.4 (Fase 6).
FECHA_BASE_V14 = "2026-06"
HORIZONTES_V14 = (
    {"clave": "h1", "anios": 1, "fecha": "2027-06"},
    {"clave": "h3", "anios": 3, "fecha": "2029-06"},
    {"clave": "h5", "anios": 5, "fecha": "2031-06"},
)
_ANIOS_POR_CLAVE = {h["clave"]: h["anios"] for h in HORIZONTES_V14}
# La oferta reporta h1 y h3, no h5 (metodologia §6.3): sin control externo,
# 3 anios sigue siendo el techo defendible pero 1 anio si es reportable.
HORIZONTES_OFERTA_V14 = ("h1", "h3")
T_2010 = 2010.44
T_2020 = 2020.20
T_BASE_V14 = 2026.5

VEREDICTOS_VALIDOS = ("sube", "se_mantiene", "baja")  # sin_datos se trata aparte
CONFIANZAS = ("alta", "media", "baja")
CONFIANZAS_OFERTA = ("media", "baja")  # tope de confianza "media" (CLAUDE.md)

# Alcaldia elegida para quedar "casi toda sin_datos" (estado vacio, wireframe 9
# del spec, seccion 15). Milpa Alta: pequena, con AGEB rurales genuinos.
ALCALDIA_CASI_VACIA = "009"
PROPORCION_VACIA = 0.9  # fraccion de sus AGEB urbanos forzados a sin_datos

# Fraccion de AGEB urbanos cuya clave se omite por completo del JSON, a
# proposito, para probar la degradacion a "sin_datos" quel el cliente aplica
# cuando una clave del universo no aparece en el archivo.
PASO_AUSENCIA = 25  # 1 de cada 25 (~4 %) queda fuera


def _rng(clave: str) -> random.Random:
    """PRNG determinista e independiente del orden de iteracion: semillado por
    hash(SEMILLA + clave), asi el resultado no depende del orden en que se
    recorra el universo de AGEB/alcaldias."""
    huella = hashlib.sha256(f"{SEMILLA}:{clave}".encode("utf-8")).hexdigest()
    return random.Random(int(huella, 16))


def leer_universo_ageb() -> list[dict]:
    """Lee solo las propiedades del GeoJSON de AGEB (jamas la geometria)."""
    with GEOJSON_AGEB.open(encoding="utf-8") as f:
        datos = json.load(f)
    universo = []
    for feature in datos["features"]:
        props = feature["properties"]
        universo.append(
            {
                "cvegeo": props["cvegeo"],
                "cve_mun": props["cve_mun"],
                "ambito": props.get("ambito", "urbano"),
            }
        )
    universo.sort(key=lambda r: r["cvegeo"])
    return universo


def _redondear(x: float, decimales: int = 1) -> float:
    return round(x, decimales)


def _registro_sin_datos(rng: random.Random, con_cve_mun: str | None) -> dict:
    registro = {
        "veredicto": "sin_datos",
        "delta_pct": None,
        "tasa_anual_pct": None,
        "ic95": None,
        "confianza": "baja",
        "n_obs": rng.choice([0, 1]),
    }
    if con_cve_mun is not None:
        registro = {"cve_mun": con_cve_mun, **registro}
    return registro


def _registro_demanda_valido(rng: random.Random, con_cve_mun: str | None) -> dict:
    veredicto = rng.choices(VEREDICTOS_VALIDOS, weights=[30, 25, 45])[0]
    confianza = rng.choices(CONFIANZAS, weights=[35, 40, 25])[0]
    n_obs = {
        "alta": rng.randint(8, 11),
        "media": rng.randint(4, 7),
        "baja": rng.randint(2, 3),
    }[confianza]

    if veredicto == "sube":
        tasa_anual = rng.uniform(1.1, 4.5)
    elif veredicto == "baja":
        tasa_anual = -rng.uniform(1.1, 4.5)
    else:  # se_mantiene: dentro de la banda muerta +/-1 %/anio
        tasa_anual = rng.uniform(-0.9, 0.9)

    anios_horizonte = rng.uniform(2.0, 3.0)
    delta_pct = _redondear(tasa_anual * anios_horizonte + rng.uniform(-1.5, 1.5))
    tasa_anual = _redondear(tasa_anual)

    # IC95 asimetrico: el margen inferior y superior nunca coinciden.
    margen_bajo = rng.uniform(2.0, 9.0)
    margen_alto = margen_bajo + rng.uniform(1.5, 6.0)
    if rng.random() < 0.5:
        margen_bajo, margen_alto = margen_alto, margen_bajo
    ic95 = [
        _redondear(delta_pct - margen_bajo),
        _redondear(delta_pct + margen_alto),
    ]

    registro = {
        "veredicto": veredicto,
        "delta_pct": delta_pct,
        "tasa_anual_pct": tasa_anual,
        "ic95": ic95,
        "confianza": confianza,
        "n_obs": n_obs,
    }
    if con_cve_mun is not None:
        registro = {"cve_mun": con_cve_mun, **registro}
    return registro


def _registro_oferta(rng: random.Random) -> dict:
    """Capa oferta: mismo veredicto v/sin_datos, pero SIN tasa_anual_pct ni
    ic95 (siguiendo el ejemplo literal de CLAUDE.md) y con tope de confianza
    'media' (nunca 'alta'), por la caida de cobertura DENUE 2024-11."""
    veredicto = rng.choices(
        VEREDICTOS_VALIDOS + ("sin_datos",), weights=[25, 25, 35, 15]
    )[0]
    if veredicto == "sin_datos":
        return {
            "veredicto": "sin_datos",
            "delta_pct": None,
            "confianza": "baja",
            "n_obs": rng.choice([0, 1]),
        }
    confianza = rng.choices(CONFIANZAS_OFERTA, weights=[55, 45])[0]
    n_obs = rng.randint(3, 7) if confianza == "media" else rng.randint(1, 3)
    if veredicto == "sube":
        delta_pct = rng.uniform(1.0, 9.0)
    elif veredicto == "baja":
        delta_pct = -rng.uniform(1.0, 15.0)  # cierres DENUE: caidas mas fuertes
    else:
        delta_pct = rng.uniform(-2.0, 2.0)
    return {
        "veredicto": veredicto,
        "delta_pct": _redondear(delta_pct),
        "confianza": confianza,
        "n_obs": n_obs,
    }


def generar_capa_ageb(universo: list[dict]) -> tuple[dict, dict, dict]:
    """Devuelve (demanda, oferta, conteos) para prediccion_ageb.json."""
    demanda: dict[str, dict] = {}
    oferta: dict[str, dict] = {}
    conteos = {
        "total_universo": len(universo),
        "rural": 0,
        "ausentes": 0,
        "veredictos_demanda": {},
        "confianzas_demanda": {},
        "veredictos_oferta": {},
        "confianzas_oferta": {},
        "alcaldia_vacia_ageb_sin_datos": 0,
        "alcaldia_vacia_ageb_total": 0,
    }

    for indice, ageb in enumerate(universo):
        cvegeo = ageb["cvegeo"]
        cve_mun = ageb["cve_mun"]
        ambito = ageb["ambito"]

        if cve_mun == ALCALDIA_CASI_VACIA:
            conteos["alcaldia_vacia_ageb_total"] += 1
        if ambito == "rural":
            conteos["rural"] += 1

        # Ausencia deliberada de la clave en el JSON (degradacion a
        # sin_datos en el cliente cuando falta el registro).
        if ambito == "urbano" and indice % PASO_AUSENCIA == 0:
            conteos["ausentes"] += 1
            continue

        rng_d = _rng(f"demanda:{cvegeo}")
        forzar_vacio = cve_mun == ALCALDIA_CASI_VACIA and rng_d.random() < PROPORCION_VACIA
        if ambito == "rural" or forzar_vacio:
            registro_d = _registro_sin_datos(rng_d, cve_mun)
        else:
            registro_d = _registro_demanda_valido(rng_d, cve_mun)
        demanda[cvegeo] = registro_d
        conteos["veredictos_demanda"][registro_d["veredicto"]] = (
            conteos["veredictos_demanda"].get(registro_d["veredicto"], 0) + 1
        )
        conteos["confianzas_demanda"][registro_d["confianza"]] = (
            conteos["confianzas_demanda"].get(registro_d["confianza"], 0) + 1
        )
        if cve_mun == ALCALDIA_CASI_VACIA and registro_d["veredicto"] == "sin_datos":
            conteos["alcaldia_vacia_ageb_sin_datos"] += 1

        rng_o = _rng(f"oferta:{cvegeo}")
        if ambito == "rural" or forzar_vacio:
            registro_o = _registro_oferta_sin_datos(rng_o)
        else:
            registro_o = _registro_oferta(rng_o)
        oferta[cvegeo] = registro_o
        conteos["veredictos_oferta"][registro_o["veredicto"]] = (
            conteos["veredictos_oferta"].get(registro_o["veredicto"], 0) + 1
        )
        conteos["confianzas_oferta"][registro_o["confianza"]] = (
            conteos["confianzas_oferta"].get(registro_o["confianza"], 0) + 1
        )

    return demanda, oferta, conteos


def _registro_oferta_sin_datos(rng: random.Random) -> dict:
    return {
        "veredicto": "sin_datos",
        "delta_pct": None,
        "confianza": "baja",
        "n_obs": rng.choice([0, 1]),
    }


def generar_capa_alcaldia(universo: list[dict]) -> tuple[dict, dict]:
    """Devuelve (demanda, oferta) para prediccion_alcaldia.json, una entrada
    por cve_mun distinto presente en el universo de AGEB."""
    alcaldias = sorted({ageb["cve_mun"] for ageb in universo})
    demanda: dict[str, dict] = {}
    oferta: dict[str, dict] = {}

    for cve_mun in alcaldias:
        rng_d = _rng(f"alcaldia-demanda:{cve_mun}")
        if cve_mun == ALCALDIA_CASI_VACIA:
            demanda[cve_mun] = _registro_sin_datos(rng_d, None)
        else:
            demanda[cve_mun] = _registro_demanda_valido(rng_d, None)

        rng_o = _rng(f"alcaldia-oferta:{cve_mun}")
        if cve_mun == ALCALDIA_CASI_VACIA:
            oferta[cve_mun] = _registro_oferta_sin_datos(rng_o)
        else:
            oferta[cve_mun] = _registro_oferta(rng_o)

    return demanda, oferta


# -------------------------------------------------------------------------------------------
# Contrato v1.4 (Fase 6 de correccion/action_plan.md; horizontes 1/3/5 anios, 6 segmentos de
# demanda, 4 ramas de oferta -- F-5 de correccion/avance_plan.md: los mocks se habian quedado en
# v1.2, a medias de la migracion real de exportar.py).
# -------------------------------------------------------------------------------------------

VERSION_CONTRATO_V14 = "1.4"

# 6 segmentos de poblacion objetivo (metodologia §1.1, backend/src/chipos/panel.py
# SEGMENTOS_DEMANDA). Se repite aqui como constante literal, no como import de chipos.panel:
# generar_mock.py se mantiene "solo biblioteca estandar" (ver docstring del modulo) para poder
# correr sin backend/venv instalado; si `panel.SEGMENTOS_DEMANDA` cambia, esta lista debe
# actualizarse a mano (test_generar_mock verifica que coincidan si el backend esta disponible).
SEGMENTOS_DEMANDA = (
    "todas",
    "primera_infancia",
    "preescolar",
    "primaria",
    "secundaria",
    "adolescencia",
)

# Celdas por rama, espejo literal de `panel.CELDAS_EDUCACION`/`CELDAS_SALUD`/`CELDAS_COMERCIO`/
# `CELDAS_VERDE` (mismo comentario de arriba: constante duplicada a proposito).
_SECTORES_CELDA = ("publico", "privado", "no_especificado")
_NIVELES_EDUCACION = (
    "guarderia",
    "preescolar",
    "primaria",
    "secundaria",
    "educacion_especial",
    "varios_niveles",
    "media_superior_tecnica",
    "recreacion_cultura",
)
CELDAS_EDUCACION = tuple(f"{nivel}__{sector}" for nivel in _NIVELES_EDUCACION for sector in _SECTORES_CELDA)
_TIPOS_SALUD = ("clinicas", "hospitales", "salud_mental", "farmacias")
CELDAS_SALUD = tuple(f"{tipo}__{sector}" for tipo in _TIPOS_SALUD for sector in _SECTORES_CELDA)
CELDAS_COMERCIO = (
    "supermercados_minisupers",
    "abarrotes",
    "frutas_verduras",
    "carnes_otros_alimentos",
    "farmacias",
)
CELDAS_VERDE = ("cobertura_verde", "areas_recreativas", "espacios_publicos")

RAMAS_CON_PROYECCION = ("educacion", "salud", "comercio")
_CELDAS_POR_RAMA_CON_PROYECCION = {
    "educacion": CELDAS_EDUCACION,
    "salud": CELDAS_SALUD,
    "comercio": CELDAS_COMERCIO,
}


def generar_capa_demanda_ageb_v14(universo: list[dict]) -> dict:
    """`capas.demanda[cvegeo] = {cve_mun, segmentos: {segmento: {...}}}` (metodología §1.1)."""
    resultado: dict[str, dict] = {}
    for indice, ageb in enumerate(universo):
        cvegeo, cve_mun, ambito = ageb["cvegeo"], ageb["cve_mun"], ageb["ambito"]
        if ambito == "urbano" and indice % PASO_AUSENCIA == 0:
            continue  # ausencia deliberada, igual que v1.1/v1.2.

        segmentos: dict[str, dict] = {}
        for segmento in SEGMENTOS_DEMANDA:
            rng_d = _rng(f"demanda-v14:{segmento}:{cvegeo}")
            forzar_vacio = cve_mun == ALCALDIA_CASI_VACIA and rng_d.random() < PROPORCION_VACIA
            if ambito == "rural":
                segmentos[segmento] = _registro_demanda_sin_datos_v12(rng_d, None, "rural")
            elif forzar_vacio:
                segmentos[segmento] = _registro_demanda_sin_datos_v12(rng_d, None, "n_insuficiente")
            else:
                segmentos[segmento] = _registro_demanda_v12(rng_d, None)
        resultado[cvegeo] = {"cve_mun": cve_mun, "segmentos": segmentos}
    return resultado


def generar_capa_demanda_alcaldia_v14(universo: list[dict]) -> dict:
    alcaldias = sorted({a["cve_mun"] for a in universo})
    resultado: dict[str, dict] = {}
    for cve_mun in alcaldias:
        segmentos: dict[str, dict] = {}
        for segmento in SEGMENTOS_DEMANDA:
            rng_d = _rng(f"alcaldia-demanda-v14:{segmento}:{cve_mun}")
            if cve_mun == ALCALDIA_CASI_VACIA:
                segmentos[segmento] = _registro_demanda_sin_datos_v12(rng_d, None, "n_insuficiente")
            else:
                segmentos[segmento] = _registro_demanda_v12(rng_d, None)
        resultado[cve_mun] = {"cve_mun": cve_mun, "segmentos": segmentos}
    return resultado


def generar_capa_rama_ageb_v14(universo: list[dict], rama: str) -> dict:
    """`capas.ramas.<rama>[cvegeo] = {cve_mun, horizontes_disponibles, celdas: {...}}`
    (metodología §10.6), para una rama CON proyección (educación/salud/comercio)."""
    celdas_rama = _CELDAS_POR_RAMA_CON_PROYECCION[rama]
    resultado: dict[str, dict] = {}
    for indice, ageb in enumerate(universo):
        cvegeo, cve_mun = ageb["cvegeo"], ageb["cve_mun"]
        if ageb["ambito"] == "urbano" and indice % PASO_AUSENCIA == 0:
            continue

        celdas_registro: dict[str, dict] = {}
        for celda in celdas_rama:
            rng_o = _rng(f"oferta-v14:{rama}:{celda}:{cvegeo}")
            registro = _registro_oferta_v12(rng_o, None)
            registro.pop("horizontes_disponibles", None)  # vive a nivel rama, no celda.
            celdas_registro[celda] = registro
        resultado[cvegeo] = {
            "cve_mun": cve_mun,
            "horizontes_disponibles": list(HORIZONTES_OFERTA_V14),
            "celdas": celdas_registro,
        }
    return resultado


def generar_capa_rama_alcaldia_v14(universo: list[dict], rama: str) -> dict:
    celdas_rama = _CELDAS_POR_RAMA_CON_PROYECCION[rama]
    alcaldias = sorted({a["cve_mun"] for a in universo})
    resultado: dict[str, dict] = {}
    for cve_mun in alcaldias:
        celdas_registro: dict[str, dict] = {}
        for celda in celdas_rama:
            rng_o = _rng(f"alcaldia-oferta-v14:{rama}:{celda}:{cve_mun}")
            registro = _registro_oferta_v12(rng_o, None)
            registro.pop("horizontes_disponibles", None)
            celdas_registro[celda] = registro
        resultado[cve_mun] = {
            "cve_mun": cve_mun,
            "horizontes_disponibles": list(HORIZONTES_OFERTA_V14),
            "celdas": celdas_registro,
        }
    return resultado


def _registro_celda_verde(rng: random.Random, es_rural: bool) -> dict:
    if es_rural:
        return {"nivel_base": None, "area_m2": None, "motivo_sin_datos": "rural"}
    return {
        "nivel_base": rng.randint(0, 12),
        "area_m2": _redondear(rng.uniform(0.0, 50000.0), 1),
        "motivo_sin_datos": None,
    }


def generar_capa_verde_ageb_v14(universo: list[dict]) -> dict:
    """`capas.ramas.verde[cvegeo]`: un solo corte, sin proyección (metodología §10.1) --
    `horizontes_disponibles: []`, celdas sin `h`/`serie`. Nunca se omite una clave del universo
    aquí (a diferencia de las demás capas): verde no depende de DENUE/censo, así que no hay
    ausencia deliberada que simular."""
    resultado: dict[str, dict] = {}
    for ageb in universo:
        cvegeo, cve_mun = ageb["cvegeo"], ageb["cve_mun"]
        es_rural = ageb["ambito"] == "rural"
        celdas_registro = {
            celda: _registro_celda_verde(_rng(f"verde-v14:{celda}:{cvegeo}"), es_rural)
            for celda in CELDAS_VERDE
        }
        resultado[cvegeo] = {"cve_mun": cve_mun, "horizontes_disponibles": [], "celdas": celdas_registro}
    return resultado


def generar_capa_verde_alcaldia_v14(universo: list[dict]) -> dict:
    alcaldias = sorted({a["cve_mun"] for a in universo})
    resultado: dict[str, dict] = {}
    for cve_mun in alcaldias:
        celdas_registro = {
            celda: _registro_celda_verde(_rng(f"alcaldia-verde-v14:{celda}:{cve_mun}"), False)
            for celda in CELDAS_VERDE
        }
        resultado[cve_mun] = {"cve_mun": cve_mun, "horizontes_disponibles": [], "celdas": celdas_registro}
    return resultado


def calcular_distribucion_demanda_v14(capa_demanda_ageb: dict, claves_horizonte: tuple[str, ...]) -> dict:
    """`distribucion_ageb` por alcaldía y horizonte (spec §17 P4), leyendo el veredicto del
    segmento `todas` (metodología §10.6: "distribucion_ageb se publica solo para demanda,
    segmento todas")."""
    resultado: dict[str, dict] = {}
    for registro in capa_demanda_ageb.values():
        cve_mun = registro["cve_mun"]
        bucket = resultado.setdefault(
            cve_mun,
            {h: {"sube": 0, "se_mantiene": 0, "baja": 0, "sin_datos": 0} for h in claves_horizonte},
        )
        registro_todas = registro["segmentos"]["todas"]
        for h in claves_horizonte:
            veredicto = registro_todas["h"][h]["veredicto"]
            bucket[h][veredicto] += 1
    return resultado


def calcular_agregado_cdmx_v14(rng_semilla: str = "agregado-cdmx-v14") -> dict:
    """`agregado_cdmx` (P2, generalizado a v1.4): un registro sintético "CDMX" por segmento de
    demanda y por celda de cada rama, con la misma semilla determinista que el resto -- no es un
    promedio real de las 16 alcaldías, es solo un mock de desarrollo."""
    demanda = {
        segmento: _registro_demanda_v12(_rng(f"{rng_semilla}:demanda:{segmento}"), None)
        for segmento in SEGMENTOS_DEMANDA
    }
    ramas: dict = {}
    for rama in RAMAS_CON_PROYECCION:
        celdas = {
            celda: _registro_oferta_v12(_rng(f"{rng_semilla}:{rama}:{celda}"), None)
            for celda in _CELDAS_POR_RAMA_CON_PROYECCION[rama]
        }
        for registro in celdas.values():
            registro.pop("horizontes_disponibles", None)
        ramas[rama] = {"celdas": celdas}
    ramas["verde"] = {
        "horizontes_disponibles": [],
        "celdas": {
            celda: _registro_celda_verde(_rng(f"{rng_semilla}:verde:{celda}"), False)
            for celda in CELDAS_VERDE
        },
    }
    return {"demanda": {"segmentos": demanda}, "ramas": ramas}


# -------------------------------------------------------------------------------------------
# Contrato v1.2 (horizontes 3/5/7 anios, plans/frontend_specs.md §17).
# -------------------------------------------------------------------------------------------


def _horizontes_demanda_v12(rng: random.Random, veredicto: str, confianza: str, n_obs: int) -> dict:
    """Un `h.{h1,h3,h5}` con el MISMO veredicto/confianza en los 3 (el modelo real controla la
    tasa una sola vez contra el horizonte mas lejano, docs/metodologia.md §2.5/§7): solo escalan
    `delta_pct`/`ic95`, aproximadamente proporcional a los anios."""
    if veredicto == "sube":
        tasa_anual = rng.uniform(1.1, 4.5)
    elif veredicto == "baja":
        tasa_anual = -rng.uniform(1.1, 4.5)
    else:
        tasa_anual = rng.uniform(-0.9, 0.9)
    tasa_anual = _redondear(tasa_anual)

    delta_pct_h3 = _redondear(tasa_anual * 3 + rng.uniform(-1.0, 1.0))
    margen_bajo = rng.uniform(2.0, 9.0)
    margen_alto = margen_bajo + rng.uniform(1.5, 6.0)
    if rng.random() < 0.5:
        margen_bajo, margen_alto = margen_alto, margen_bajo

    h = {}
    for entrada in HORIZONTES_V14:
        clave, anios = entrada["clave"], entrada["anios"]
        factor = anios / 3
        delta_pct = _redondear(delta_pct_h3 * factor)
        ic95 = [
            _redondear(delta_pct - margen_bajo * factor),
            _redondear(delta_pct + margen_alto * factor),
        ]
        h[clave] = {
            "veredicto": veredicto,
            "delta_pct": delta_pct,
            "tasa_anual_pct": tasa_anual,
            "ic95": ic95,
            "confianza": confianza,
        }
    return h


def _serie_demanda_v12(rng: random.Random, tasa_anual_pct: float) -> tuple[dict, float]:
    """Serie censal 2010/2020 (2 puntos) coherente con `tasa_anual_pct`, mas `nivel_base`
    (nivel proyectado en `T_BASE_V14`, spec §17 P3)."""
    nivel_2020 = rng.randint(50, 3000)
    nivel_2010 = max(0, round(nivel_2020 * (1 - tasa_anual_pct / 100 * (T_2020 - T_2010))))
    nivel_base = max(0, round(nivel_2020 * (1 + tasa_anual_pct / 100 * (T_BASE_V14 - T_2020))))
    serie = {"t": [T_2010, T_2020], "valor": [nivel_2010, nivel_2020]}
    return serie, nivel_base


def _registro_demanda_v12(rng: random.Random, cve_mun: str | None) -> dict:
    veredicto = rng.choices(VEREDICTOS_VALIDOS, weights=[30, 25, 45])[0]
    confianza = rng.choices(CONFIANZAS, weights=[35, 40, 25])[0]
    n_obs = {
        "alta": rng.randint(8, 11),
        "media": rng.randint(4, 7),
        "baja": rng.randint(2, 3),
    }[confianza]

    h = _horizontes_demanda_v12(rng, veredicto, confianza, n_obs)
    serie, nivel_base = _serie_demanda_v12(rng, h["h3"]["tasa_anual_pct"])

    registro = {
        "n_obs": n_obs,
        "motivo_sin_datos": None,
        "serie": serie,
        "nivel_base": nivel_base,
        "h": h,
    }
    if cve_mun is not None:
        registro = {"cve_mun": cve_mun, **registro}
    return registro


def _registro_demanda_sin_datos_v12(rng: random.Random, cve_mun: str | None, motivo: str) -> dict:
    h = {
        entrada["clave"]: {
            "veredicto": "sin_datos",
            "delta_pct": None,
            "tasa_anual_pct": None,
            "ic95": None,
            "confianza": "baja",
        }
        for entrada in HORIZONTES_V14
    }
    registro = {
        "n_obs": rng.choice([0, 1]),
        "motivo_sin_datos": motivo,
        "serie": None,
        "nivel_base": None,
        "h": h,
    }
    if cve_mun is not None:
        registro = {"cve_mun": cve_mun, **registro}
    return registro


def _registro_oferta_v12(rng: random.Random, cve_mun: str | None) -> dict:
    """Oferta: `h1` y `h3` (metodologia §6.3, tope de confianza 'media', CLAUDE.md); nunca `h5`."""
    veredicto = rng.choices(VEREDICTOS_VALIDOS + ("sin_datos",), weights=[25, 25, 35, 15])[0]

    t_denue = [2016.79, 2019.87, 2024.87]
    if veredicto == "sin_datos":
        h_sin_datos = {
            clave: {"veredicto": "sin_datos", "delta_pct": None, "tasa_anual_pct": None, "ic95": None, "confianza": "baja"}
            for clave in HORIZONTES_OFERTA_V14
        }
        registro = {
            "n_obs": rng.choice([0, 1]),
            "motivo_sin_datos": "cobertura_denue",
            "serie": None,
            "nivel_base": None,
            "horizontes_disponibles": list(HORIZONTES_OFERTA_V14),
            "h": h_sin_datos,
        }
        if cve_mun is not None:
            registro = {"cve_mun": cve_mun, **registro}
        return registro

    confianza = rng.choices(CONFIANZAS_OFERTA, weights=[55, 45])[0]
    n_obs = rng.randint(3, 7) if confianza == "media" else rng.randint(1, 3)
    if veredicto == "sube":
        delta_pct_h3 = rng.uniform(1.0, 9.0)
    elif veredicto == "baja":
        delta_pct_h3 = -rng.uniform(1.0, 15.0)
    else:
        delta_pct_h3 = rng.uniform(-2.0, 2.0)
    tasa_anual_pct = _redondear(delta_pct_h3 / 3)

    h = {}
    for clave in HORIZONTES_OFERTA_V14:
        factor = _ANIOS_POR_CLAVE[clave] / 3
        delta_pct = _redondear(delta_pct_h3 * factor)
        h[clave] = {
            "veredicto": veredicto,
            "delta_pct": delta_pct,
            "tasa_anual_pct": tasa_anual_pct,
            "ic95": [_redondear(delta_pct - rng.uniform(5, 15)), _redondear(delta_pct + rng.uniform(5, 15))],
            "confianza": confianza,
        }

    nivel_2024 = rng.randint(1, 30)
    nivel_2019 = max(0, nivel_2024 + rng.randint(-2, 2))
    nivel_2016 = max(0, nivel_2019 + rng.randint(-2, 2))
    registro = {
        "n_obs": n_obs,
        "motivo_sin_datos": None,
        "serie": {"t": t_denue, "valor": [nivel_2016, nivel_2019, nivel_2024]},
        "nivel_base": nivel_2024,
        "horizontes_disponibles": list(HORIZONTES_OFERTA_V14),
        "h": h,
    }
    if cve_mun is not None:
        registro = {"cve_mun": cve_mun, **registro}
    return registro


def escribir_json(ruta: pathlib.Path, contenido: dict) -> None:
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


def main() -> None:
    universo = leer_universo_ageb()
    generado = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    # --- v1.1 (un solo horizonte): mock de degradacion, `?mock=v11` (js/config.js). ---
    demanda_ageb, oferta_ageb, conteos = generar_capa_ageb(universo)
    prediccion_ageb_v11 = {
        "version": VERSION_CONTRATO_V11,
        "generado": generado,
        "horizonte": HORIZONTE,
        "capas": {"demanda": demanda_ageb, "oferta": oferta_ageb},
    }
    escribir_json(DIR_SALIDA / "prediccion_ageb_v11.json", prediccion_ageb_v11)

    demanda_alc, oferta_alc = generar_capa_alcaldia(universo)
    prediccion_alcaldia_v11 = {
        "version": VERSION_CONTRATO_V11,
        "generado": generado,
        "horizonte": HORIZONTE,
        "capas": {"demanda": demanda_alc, "oferta": oferta_alc},
    }
    escribir_json(DIR_SALIDA / "prediccion_alcaldia_v11.json", prediccion_alcaldia_v11)

    # Version incompatible: mismo esquema v1.1, "version" que el cliente debe
    # rechazar (1.9 no esta en VERSIONES_CONTRATO_ACEPTADAS de js/config.js).
    prediccion_invalida = {
        "version": VERSION_INVALIDA,
        "generado": generado,
        "horizonte": HORIZONTE,
        "capas": {"demanda": demanda_ageb, "oferta": oferta_ageb},
    }
    escribir_json(DIR_SALIDA / "prediccion_ageb_v11_invalido.json", prediccion_invalida)

    # --- v1.4 (6 segmentos de demanda, 4 ramas de oferta): mock "base", `?mock=1`/sin
    # parametro (js/config.js). F-5 de correccion/avance_plan.md: reemplaza al mock v1.2. ---
    demanda_ageb_v14 = generar_capa_demanda_ageb_v14(universo)
    capas_ramas_ageb_v14: dict[str, dict] = {
        rama: generar_capa_rama_ageb_v14(universo, rama) for rama in RAMAS_CON_PROYECCION
    }
    capas_ramas_ageb_v14["verde"] = generar_capa_verde_ageb_v14(universo)
    prediccion_ageb_v14 = {
        "version": VERSION_CONTRATO_V14,
        "generado": generado,
        "fecha_base": FECHA_BASE_V14,
        "horizontes": list(HORIZONTES_V14),
        "capas": {"demanda": demanda_ageb_v14, "ramas": capas_ramas_ageb_v14},
    }
    escribir_json(DIR_SALIDA / "prediccion_ageb.json", prediccion_ageb_v14)

    demanda_alc_v14 = generar_capa_demanda_alcaldia_v14(universo)
    capas_ramas_alc_v14: dict[str, dict] = {
        rama: generar_capa_rama_alcaldia_v14(universo, rama) for rama in RAMAS_CON_PROYECCION
    }
    capas_ramas_alc_v14["verde"] = generar_capa_verde_alcaldia_v14(universo)
    claves_todas = tuple(h["clave"] for h in HORIZONTES_V14)
    distribucion_demanda_v14 = calcular_distribucion_demanda_v14(demanda_ageb_v14, claves_todas)
    demanda_alc_v14_con_distribucion = {
        cve_mun: {**registro, "distribucion_ageb": distribucion_demanda_v14.get(cve_mun, {})}
        for cve_mun, registro in demanda_alc_v14.items()
    }
    agregado_cdmx_v14 = calcular_agregado_cdmx_v14()
    prediccion_alcaldia_v14 = {
        "version": VERSION_CONTRATO_V14,
        "generado": generado,
        "fecha_base": FECHA_BASE_V14,
        "horizontes": list(HORIZONTES_V14),
        "capas": {"demanda": demanda_alc_v14_con_distribucion, "ramas": capas_ramas_alc_v14},
        "agregado_cdmx": agregado_cdmx_v14,
    }
    escribir_json(DIR_SALIDA / "prediccion_alcaldia.json", prediccion_alcaldia_v14)

    print(f"universo AGEB: {conteos['total_universo']} (rural={conteos['rural']})")
    print(f"claves ausentes a proposito: {conteos['ausentes']}")
    print(f"demanda AGEB veredictos (v1.1): {conteos['veredictos_demanda']}")
    print(f"demanda AGEB confianzas (v1.1): {conteos['confianzas_demanda']}")
    print(f"oferta AGEB veredictos (v1.1): {conteos['veredictos_oferta']}")
    print(f"oferta AGEB confianzas (v1.1): {conteos['confianzas_oferta']}")
    print(
        "alcaldia casi vacia "
        f"({ALCALDIA_CASI_VACIA}): sin_datos={conteos['alcaldia_vacia_ageb_sin_datos']}"
        f"/{conteos['alcaldia_vacia_ageb_total']}"
    )
    print(
        "archivos generados: prediccion_ageb.json, prediccion_alcaldia.json (v1.4), "
        "prediccion_ageb_v11.json, prediccion_alcaldia_v11.json (v1.1), "
        "prediccion_ageb_v11_invalido.json (invalido)"
    )


if __name__ == "__main__":
    main()
