#!/usr/bin/env python3
"""Genera los mocks deterministas del contrato v1.1 para el frontend.

Lee UNICAMENTE las propiedades (cvegeo, cve_mun, ambito) de
``data/reference/ageb_cdmx_simplificado.geojson`` -- nunca geometrias -- para
obtener el universo real de AGEB y alcaldias, y con eso escribe:

- ``prediccion_ageb.json``            contrato v1.1, capas demanda + oferta.
- ``prediccion_alcaldia.json``        mismo contrato, agregado por CVE_MUN.
- ``prediccion_ageb_v11_invalido.json``  mismo esquema con ``version``
  incompatible, para ejercitar el estado de error del frontend.

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
VERSION_CONTRATO = "1.1"
VERSION_INVALIDA = "1.9"
HORIZONTE = "2027-06"

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


def escribir_json(ruta: pathlib.Path, contenido: dict) -> None:
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


def main() -> None:
    universo = leer_universo_ageb()
    generado = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    demanda_ageb, oferta_ageb, conteos = generar_capa_ageb(universo)
    prediccion_ageb = {
        "version": VERSION_CONTRATO,
        "generado": generado,
        "horizonte": HORIZONTE,
        "capas": {"demanda": demanda_ageb, "oferta": oferta_ageb},
    }
    escribir_json(DIR_SALIDA / "prediccion_ageb.json", prediccion_ageb)

    demanda_alc, oferta_alc = generar_capa_alcaldia(universo)
    prediccion_alcaldia = {
        "version": VERSION_CONTRATO,
        "generado": generado,
        "horizonte": HORIZONTE,
        "capas": {"demanda": demanda_alc, "oferta": oferta_alc},
    }
    escribir_json(DIR_SALIDA / "prediccion_alcaldia.json", prediccion_alcaldia)

    # Version incompatible: mismo esquema, "version" que el cliente debe
    # rechazar (contrato vigente es 1.1; 1.9 no es compatible con el
    # adaptador v1.1 -> v1.2 de api.js).
    prediccion_invalida = {
        "version": VERSION_INVALIDA,
        "generado": generado,
        "horizonte": HORIZONTE,
        "capas": {"demanda": demanda_ageb, "oferta": oferta_ageb},
    }
    escribir_json(DIR_SALIDA / "prediccion_ageb_v11_invalido.json", prediccion_invalida)

    print(f"universo AGEB: {conteos['total_universo']} (rural={conteos['rural']})")
    print(f"claves ausentes a proposito: {conteos['ausentes']}")
    print(f"demanda AGEB veredictos: {conteos['veredictos_demanda']}")
    print(f"demanda AGEB confianzas: {conteos['confianzas_demanda']}")
    print(f"oferta AGEB veredictos: {conteos['veredictos_oferta']}")
    print(f"oferta AGEB confianzas: {conteos['confianzas_oferta']}")
    print(
        "alcaldia casi vacia "
        f"({ALCALDIA_CASI_VACIA}): sin_datos={conteos['alcaldia_vacia_ageb_sin_datos']}"
        f"/{conteos['alcaldia_vacia_ageb_total']}"
    )


if __name__ == "__main__":
    main()
