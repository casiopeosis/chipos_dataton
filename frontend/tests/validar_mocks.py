#!/usr/bin/env python3
"""Valida los fixtures v1.4 del frontend sin dependencias externas."""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MOCK = RAIZ / "mock"

SEGMENTOS = {
    "todas",
    "primera_infancia",
    "preescolar",
    "primaria",
    "secundaria",
    "adolescencia",
}
RAMAS = {"educacion", "salud", "comercio", "verde"}
CELDAS_ESPERADAS = {
    "educacion": {
        f"{nivel}__{sector}"
        for nivel in (
            "guarderia",
            "preescolar",
            "primaria",
            "secundaria",
            "educacion_especial",
            "varios_niveles",
            "media_superior_tecnica",
            "recreacion_cultura",
        )
        for sector in ("publico", "privado", "no_especificado")
    },
    "salud": {
        f"{tipo}__{sector}"
        for tipo in ("clinicas", "hospitales", "salud_mental", "farmacias")
        for sector in ("publico", "privado", "no_especificado")
    },
    "comercio": {
        "supermercados_minisupers",
        "abarrotes",
        "frutas_verduras",
        "carnes_otros_alimentos",
        "farmacias",
    },
    "verde": {"cobertura_verde", "areas_recreativas", "espacios_publicos"},
}


def cargar(nombre: str) -> dict:
    with (MOCK / nombre).open(encoding="utf-8") as archivo:
        return json.load(archivo)


def validar_raiz(documento: dict, cantidad: int) -> None:
    assert documento["version"] == "1.4"
    assert documento["fecha_base"] == "2026-06"
    assert [h["clave"] for h in documento["horizontes"]] == ["h1", "h3", "h5"]
    assert len(documento["capas"]["demanda"]) == cantidad
    assert set(documento["capas"]["ramas"]) == RAMAS
    for rama in RAMAS:
        assert len(documento["capas"]["ramas"][rama]) == cantidad


def validar_unidad(documento: dict, clave: str) -> None:
    demanda = documento["capas"]["demanda"][clave]
    assert set(demanda["segmentos"]) == SEGMENTOS
    for segmento in demanda["segmentos"].values():
        assert set(segmento["h"]) == {"h1", "h3", "h5"}

    for rama in RAMAS:
        registro = documento["capas"]["ramas"][rama][clave]
        assert set(registro["celdas"]) == CELDAS_ESPERADAS[rama]
        esperados = [] if rama == "verde" else ["h1", "h3"]
        assert registro["horizontes_disponibles"] == esperados


def main() -> None:
    ageb = cargar("prediccion_ageb.json")
    alcaldia = cargar("prediccion_alcaldia.json")

    validar_raiz(ageb, 2453)
    validar_raiz(alcaldia, 16)
    for clave in ageb["capas"]["demanda"]:
        validar_unidad(ageb, clave)
    for clave in alcaldia["capas"]["demanda"]:
        validar_unidad(alcaldia, clave)

    celdas = (
        celda
        for rama in RAMAS
        for unidad in ageb["capas"]["ramas"][rama].values()
        for celda in unidad["celdas"].values()
    )
    assert any(celda.get("nivel_base") == 0 for celda in celdas), "falta el caso de oferta cero"
    assert alcaldia.get("agregado_cdmx", {}).get("demanda", {}).get("segmentos", {}).get("todas")

    print("Mocks v1.4 válidos: 2453 AGEB, 16 alcaldías, 6 segmentos y 44 celdas por unidad")


if __name__ == "__main__":
    main()
