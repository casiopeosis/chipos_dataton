#!/usr/bin/env python3
"""Genera los mocks deterministas del frontend (contratos v1.4 y v1.1).

Lee UNICAMENTE las propiedades (cvegeo, cve_mun, ambito) de
``data/reference/ageb_cdmx_simplificado.geojson`` -- nunca geometrias -- para
obtener el universo real de AGEB y alcaldias, y con eso escribe:

- ``prediccion_ageb.json`` / ``prediccion_alcaldia.json``
  Contrato v1.4 (plans/frontend_specs.md §17): seis segmentos de demanda y
  cuatro ramas de servicios desagregadas por las 44 celdas de filtro reales.
  Es el mock base de ``?mock=1``.
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
VERSION_CONTRATO_V14 = "1.4"
VERSION_INVALIDA = "1.9"
HORIZONTE = "2027-06"  # v1.1: horizonte unico (decision previa, ver CLAUDE.md).

# v1.2 (horizontes 1/3/5 anios, correccion/action_plan.md Fase 1: cumple
# correccion/rubrica.md §5 "uno, tres o cinco anios"; version del contrato se
# queda en 1.2 hasta que las Fases 4-6 completen el salto a 1.4).
FECHA_BASE_V12 = "2026-06"
HORIZONTES_V12 = (
    {"clave": "h1", "anios": 1, "fecha": "2027-06"},
    {"clave": "h3", "anios": 3, "fecha": "2029-06"},
    {"clave": "h5", "anios": 5, "fecha": "2031-06"},
)
_ANIOS_POR_CLAVE = {h["clave"]: h["anios"] for h in HORIZONTES_V12}
# La oferta reporta h1 y h3, no h5 (metodologia §6.3): sin control externo,
# 3 anios sigue siendo el techo defendible pero 1 anio si es reportable.
HORIZONTES_OFERTA_V12 = ("h1", "h3")
T_2010 = 2010.44
T_2020 = 2020.20
T_BASE_V12 = 2026.5

VEREDICTOS_VALIDOS = ("sube", "se_mantiene", "baja")  # sin_datos se trata aparte
CONFIANZAS = ("alta", "media", "baja")
CONFIANZAS_OFERTA = ("media", "baja")  # tope de confianza "media" (CLAUDE.md)

SEGMENTOS_DEMANDA = (
    "todas",
    "primera_infancia",
    "preescolar",
    "primaria",
    "secundaria",
    "adolescencia",
)

NIVELES_EDUCACION = (
    "guarderia",
    "preescolar",
    "primaria",
    "secundaria",
    "educacion_especial",
    "varios_niveles",
    "media_superior_tecnica",
    "recreacion_cultura",
)
TIPOS_SALUD = ("clinicas", "hospitales", "salud_mental", "farmacias")
SECTORES = ("publico", "privado", "no_especificado")
CELDAS_RAMA = {
    "educacion": tuple(f"{nivel}__{sector}" for nivel in NIVELES_EDUCACION for sector in SECTORES),
    "salud": tuple(f"{tipo}__{sector}" for tipo in TIPOS_SALUD for sector in SECTORES),
    "comercio": (
        "supermercados_minisupers",
        "abarrotes",
        "frutas_verduras",
        "carnes_otros_alimentos",
        "farmacias",
    ),
    "verde": ("cobertura_verde", "areas_recreativas", "espacios_publicos"),
}

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
    for entrada in HORIZONTES_V12:
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
    (nivel proyectado en `T_BASE_V12`, spec §17 P3)."""
    nivel_2020 = rng.randint(50, 3000)
    nivel_2010 = max(0, round(nivel_2020 * (1 - tasa_anual_pct / 100 * (T_2020 - T_2010))))
    nivel_base = max(0, round(nivel_2020 * (1 + tasa_anual_pct / 100 * (T_BASE_V12 - T_2020))))
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
        for entrada in HORIZONTES_V12
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
            for clave in HORIZONTES_OFERTA_V12
        }
        registro = {
            "n_obs": rng.choice([0, 1]),
            "motivo_sin_datos": "cobertura_denue",
            "serie": None,
            "nivel_base": None,
            "horizontes_disponibles": list(HORIZONTES_OFERTA_V12),
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
    for clave in HORIZONTES_OFERTA_V12:
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
        "horizontes_disponibles": list(HORIZONTES_OFERTA_V12),
        "h": h,
    }
    if cve_mun is not None:
        registro = {"cve_mun": cve_mun, **registro}
    return registro


def generar_capa_ageb_v12(universo: list[dict]) -> tuple[dict, dict]:
    demanda: dict[str, dict] = {}
    oferta: dict[str, dict] = {}

    for indice, ageb in enumerate(universo):
        cvegeo = ageb["cvegeo"]
        cve_mun = ageb["cve_mun"]
        ambito = ageb["ambito"]

        if ambito == "urbano" and indice % PASO_AUSENCIA == 0:
            continue  # ausencia deliberada, igual que v1.1 (degrada a sin_datos en el cliente).

        rng_d = _rng(f"demanda-v12:{cvegeo}")
        forzar_vacio = cve_mun == ALCALDIA_CASI_VACIA and rng_d.random() < PROPORCION_VACIA
        if ambito == "rural":
            demanda[cvegeo] = _registro_demanda_sin_datos_v12(rng_d, cve_mun, "rural")
        elif forzar_vacio:
            demanda[cvegeo] = _registro_demanda_sin_datos_v12(rng_d, cve_mun, "n_insuficiente")
        else:
            demanda[cvegeo] = _registro_demanda_v12(rng_d, cve_mun)

        rng_o = _rng(f"oferta-v12:{cvegeo}")
        oferta[cvegeo] = _registro_oferta_v12(rng_o, cve_mun)

    return demanda, oferta


def generar_capa_alcaldia_v12(universo: list[dict]) -> tuple[dict, dict]:
    alcaldias = sorted({ageb["cve_mun"] for ageb in universo})
    demanda: dict[str, dict] = {}
    oferta: dict[str, dict] = {}

    for cve_mun in alcaldias:
        rng_d = _rng(f"alcaldia-demanda-v12:{cve_mun}")
        if cve_mun == ALCALDIA_CASI_VACIA:
            demanda[cve_mun] = _registro_demanda_sin_datos_v12(rng_d, None, "n_insuficiente")
        else:
            demanda[cve_mun] = _registro_demanda_v12(rng_d, None)

        rng_o = _rng(f"alcaldia-oferta-v12:{cve_mun}")
        oferta[cve_mun] = _registro_oferta_v12(rng_o, None)

    return demanda, oferta


def calcular_distribucion_ageb(
    registros_capa: dict, universo: list[dict], claves_horizonte: tuple[str, ...]
) -> dict[str, dict]:
    """`distribucion_ageb` por alcaldia y horizonte (spec §17 P4), para UNA capa (demanda u
    oferta: cada una lleva la suya, "en cada alcaldia de demanda y oferta"). El veredicto no
    cambia entre horizontes de demanda (docs/metodologia.md §3), asi que sus 3 distribuciones por
    alcaldia son iguales; oferta trae `h1`/`h3`, nunca `h5` (metodologia §6.3)."""
    alcaldias = sorted({ageb["cve_mun"] for ageb in universo})
    resultado: dict[str, dict] = {}
    for cve_mun in alcaldias:
        cvegeos_alcaldia = [a["cvegeo"] for a in universo if a["cve_mun"] == cve_mun]
        por_horizonte: dict[str, dict] = {}
        for clave in claves_horizonte:
            conteo = {"sube": 0, "se_mantiene": 0, "baja": 0, "sin_datos": 0}
            for cvegeo in cvegeos_alcaldia:
                registro = registros_capa.get(cvegeo)
                veredicto = registro["h"][clave]["veredicto"] if registro else "sin_datos"
                conteo[veredicto] += 1
            por_horizonte[clave] = conteo
        resultado[cve_mun] = por_horizonte
    return resultado


def calcular_agregado_cdmx(demanda_alc: dict, oferta_alc: dict) -> dict:
    """`agregado_cdmx` en la raiz de prediccion_alcaldia.json (spec §17 P2): un registro "CDMX"
    generado con la misma semilla determinista que el resto (rng propio, no un promedio de las
    16 alcaldias: es solo un mock de desarrollo, no una cifra real)."""
    rng_d = _rng("agregado-cdmx-demanda")
    rng_o = _rng("agregado-cdmx-oferta")
    return {
        "demanda": _registro_demanda_v12(rng_d, None),
        "oferta": _registro_oferta_v12(rng_o, None),
    }


# -------------------------------------------------------------------------------------------
# Contrato v1.4: seis segmentos de demanda y cuatro ramas por celdas de filtro.
# -------------------------------------------------------------------------------------------


def _registro_demanda_v14(rng: random.Random, *, sin_datos: bool = False, motivo: str = "n_insuficiente") -> dict:
    """Registro de un segmento del contrato v1.4.

    Reutiliza la semántica temporal comprobada del fixture v1.2, pero la deja dentro de
    ``capas.demanda.<unidad>.segmentos.<segmento>`` y sin repetir ``cve_mun`` en cada segmento.
    """
    if sin_datos:
        return _registro_demanda_sin_datos_v12(rng, None, motivo)
    return _registro_demanda_v12(rng, None)


def _registro_celda_proyectada_v14(rng: random.Random, *, cero: bool = False) -> dict:
    """Celda DENUE v1.4 con h1/h3 y confianza limitada a media.

    ``cero=True`` crea el caso crítico Ŝ=0/D̂>0: es un cero publicado y válido, no ``sin_datos``.
    """
    if cero:
        bloque = {"veredicto": "se_mantiene", "delta_pct": 0.0}
        return {"nivel_base": 0, "h": {clave: dict(bloque) for clave in HORIZONTES_OFERTA_V12}}
    completo = _registro_oferta_v12(rng, None)
    # El historial por celda no interviene en la composición ni puede sumarse honestamente cuando
    # hay varias celdas activas. El fixture conserva los ingredientes necesarios y evita inflarlo
    # con 41 copias de fechas por AGEB; el backend real sí publica las series observadas.
    return {
        "nivel_base": completo["nivel_base"],
        "h": {
            clave: {
                "veredicto": bloque["veredicto"],
                "delta_pct": bloque["delta_pct"],
            }
            for clave, bloque in completo["h"].items()
        },
    }


def _registro_celda_verde_v14(rng: random.Random, celda: str, *, sin_datos: bool = False) -> dict:
    if sin_datos:
        return {
            "n_obs": 0,
            "motivo_sin_datos": "sin_geometria",
            "serie": None,
            "nivel_base": None,
            "unidad": "m2" if celda != "cobertura_verde" else "porcentaje",
        }
    if celda == "cobertura_verde":
        nivel = _redondear(rng.uniform(2.0, 38.0))
        unidad = "porcentaje"
    else:
        nivel = rng.randint(0, 25000)
        unidad = "m2"
    return {
        "n_obs": rng.randint(1, 12),
        "motivo_sin_datos": None,
        "serie": None,
        "nivel_base": nivel,
        "area_m2": nivel if unidad == "m2" else None,
        "unidad": unidad,
    }


def generar_capas_v14(universo: list[dict], *, nivel: str) -> tuple[dict, dict]:
    """Genera ``(demanda, ramas)`` para AGEB o alcaldía con la forma exacta de v1.4."""
    if nivel == "ageb":
        unidades = [(a["cvegeo"], a["cve_mun"], a["ambito"]) for a in universo]
    else:
        unidades = [(cve_mun, cve_mun, "urbano") for cve_mun in sorted({a["cve_mun"] for a in universo})]

    demanda: dict[str, dict] = {}
    ramas: dict[str, dict] = {rama: {} for rama in CELDAS_RAMA}

    for indice, (clave, cve_mun, ambito) in enumerate(unidades):
        # En AGEB se conservan todas las claves. Las rurales existen explícitamente como sin_datos;
        # así el mapa no confunde una ausencia del archivo con un dato rural conocido.
        forzar_vacio = ambito == "rural" or (
            cve_mun == ALCALDIA_CASI_VACIA and _rng(f"v14-vacio:{nivel}:{clave}").random() < PROPORCION_VACIA
        )
        segmentos = {}
        for segmento in SEGMENTOS_DEMANDA:
            rng_segmento = _rng(f"v14:{nivel}:demanda:{clave}:{segmento}")
            segmentos[segmento] = _registro_demanda_v14(
                rng_segmento,
                sin_datos=forzar_vacio,
                motivo="rural" if ambito == "rural" else "n_insuficiente",
            )
        demanda[clave] = {"cve_mun": cve_mun, "segmentos": segmentos}

        for rama in ("educacion", "salud", "comercio"):
            celdas = {}
            rama_sin_datos = forzar_vacio or (nivel == "ageb" and indice % 41 == 0 and rama == "salud")
            for numero_celda, celda in enumerate(CELDAS_RAMA[rama]):
                rng_celda = _rng(f"v14:{nivel}:{rama}:{clave}:{celda}")
                registro = _registro_celda_proyectada_v14(
                    rng_celda,
                    cero=not rama_sin_datos and (indice + numero_celda) % 53 == 0,
                )
                if rama_sin_datos:
                    registro = {
                        "motivo_sin_datos": "n_insuficiente",
                        "nivel_base": None,
                    }
                celdas[celda] = registro
            ramas[rama][clave] = {
                "cve_mun": cve_mun,
                "horizontes_disponibles": list(HORIZONTES_OFERTA_V12),
                "celdas": celdas,
            }

        celdas_verde = {
            celda: _registro_celda_verde_v14(
                _rng(f"v14:{nivel}:verde:{clave}:{celda}"), celda, sin_datos=forzar_vacio
            )
            for celda in CELDAS_RAMA["verde"]
        }
        ramas["verde"][clave] = {
            "cve_mun": cve_mun,
            "horizontes_disponibles": [],
            "celdas": celdas_verde,
        }

    return demanda, ramas


def agregar_distribucion_ageb_v14(demanda_alcaldia: dict, demanda_ageb: dict, universo: list[dict]) -> None:
    """Añade una distribución reproducible por tercil para las 16 alcaldías.

    Es un fixture visual; los terciles reales se recomputan en el cliente a partir del escenario
    activo. La suma siempre coincide con el universo geográfico de cada alcaldía.
    """
    for cve_mun, registro in demanda_alcaldia.items():
        total = sum(1 for ageb in universo if ageb["cve_mun"] == cve_mun)
        sin_datos = sum(
            1
            for clave, entrada in demanda_ageb.items()
            if entrada["cve_mun"] == cve_mun
            and entrada["segmentos"]["todas"]["h"]["h3"]["veredicto"] == "sin_datos"
        )
        validos = total - sin_datos
        baja = validos // 3
        media = validos // 3
        alta = validos - baja - media
        registro["distribucion_ageb"] = {
            h: {"baja": baja, "media": media, "alta": alta, "sin_datos": sin_datos}
            for h in ("h1", "h3", "h5")
        }


def construir_agregado_cdmx_v14() -> dict:
    demanda = {
        segmento: _registro_demanda_v14(_rng(f"v14:cdmx:demanda:{segmento}"))
        for segmento in SEGMENTOS_DEMANDA
    }
    ramas = {}
    for rama, celdas in CELDAS_RAMA.items():
        if rama == "verde":
            ramas[rama] = {
                "celdas": {
                    celda: _registro_celda_verde_v14(_rng(f"v14:cdmx:{rama}:{celda}"), celda)
                    for celda in celdas
                }
            }
        else:
            ramas[rama] = {
                "celdas": {
                    celda: _registro_celda_proyectada_v14(_rng(f"v14:cdmx:{rama}:{celda}"))
                    for celda in celdas
                }
            }
    return {"demanda": {"segmentos": demanda}, "ramas": ramas}


def escribir_json(ruta: pathlib.Path, contenido: dict, *, compacto: bool = False) -> None:
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(
            contenido,
            f,
            ensure_ascii=False,
            indent=None if compacto else 2,
            separators=(",", ":") if compacto else None,
            sort_keys=False,
        )
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

    # --- v1.4: mock base con segmentos y cuatro ramas, `?mock=1` (js/config.js). ---
    demanda_ageb_v14, ramas_ageb_v14 = generar_capas_v14(universo, nivel="ageb")
    prediccion_ageb_v14 = {
        "version": VERSION_CONTRATO_V14,
        "generado": generado,
        "fecha_base": FECHA_BASE_V12,
        "horizontes": list(HORIZONTES_V12),
        "capas": {"demanda": demanda_ageb_v14, "ramas": ramas_ageb_v14},
    }
    # Compacto para respetar el presupuesto del fixture sin sacrificar las 2 453 AGEB ni celdas.
    escribir_json(DIR_SALIDA / "prediccion_ageb.json", prediccion_ageb_v14, compacto=True)

    demanda_alc_v14, ramas_alc_v14 = generar_capas_v14(universo, nivel="alcaldia")
    agregar_distribucion_ageb_v14(demanda_alc_v14, demanda_ageb_v14, universo)
    prediccion_alcaldia_v14 = {
        "version": VERSION_CONTRATO_V14,
        "generado": generado,
        "fecha_base": FECHA_BASE_V12,
        "horizontes": list(HORIZONTES_V12),
        "capas": {"demanda": demanda_alc_v14, "ramas": ramas_alc_v14},
        "agregado_cdmx": construir_agregado_cdmx_v14(),
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
