"""Normalización de alcaldía a clave única (cve_alc, 3 dígitos INEGI, entidad 09).

Las 5 familias de datos identifican alcaldía de forma distinta (CLAUDE.md §1.1,
docs/architecture-plan.md línea 16):

    - Gen A (deporte/adultos mayores 2016-2021): columna `clave_alcaldia`, ej. "002".
    - Gen B / Comercios (DENUE depurado): columna `cve_mun`, ej. "003".
    - Cultura (AREAS_CULTURALES_CDMX): columna `municipio_id`, entero sin ceros, ej. 3.
    - Infancias / Salud / PILARES: solo el nombre (columna `Alcaldía` / `alcaldia`),
      con acentos y capitalización inconsistentes; Gen A también tiene el nombre
      con mojibake (ej. "Benito JuÃ¡rez") en su columna `alcaldia`, pero ahí se
      une por `clave_alcaldia`, nunca por nombre.

Todo pasa por `normalizar_alcaldia(valor, tipo)` para no reimplementar la
normalización en cada lector.
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

_REF_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "reference" / "alcaldias.csv"

CLAVES_VALIDAS: frozenset[str] = frozenset(
    f"{i:03d}" for i in range(2, 18)
)  # 002..017, las 16 alcaldías de CDMX (entidad 09)


def _quitar_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _reparar_mojibake(texto: str) -> str:
    """Revierte UTF-8 mal decodificado como Latin-1 (ej. 'JuÃ¡rez' -> 'Juárez').

    Solo se aplica si el texto contiene el patrón típico de mojibake; si el
    intento de reparación falla, se conserva el texto original.
    """
    if "Ã" not in texto and "Â" not in texto:
        return texto
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def _clave_normalizada(texto: str) -> str:
    """Forma canónica para comparar nombres: sin mojibake, sin acentos, mayúsculas,
    sin puntuación, espacios colapsados."""
    texto = _reparar_mojibake(texto)
    texto = _quitar_acentos(texto)
    texto = texto.upper().replace(".", "")
    texto = " ".join(texto.split())
    return texto


def _cargar_nombre_a_clave() -> dict[str, str]:
    mapa: dict[str, str] = {}
    with _REF_PATH.open(encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            cve = fila["cve_alc"]
            mapa[_clave_normalizada(fila["nombre_oficial"])] = cve
    # Alias observados en los datos (INFANCIAS_*, SALUD_CDMX_*, PILARES, Gen A)
    # que no colapsan al nombre oficial solo quitando acentos/puntuación.
    alias = {
        "GUSTAVO A MADERO": "005",
        "MAGDALENA CONTRERAS": "008",
        "ALVARO OBREGON": "010",
        "CUAUHTEMOC": "015",
        "TLAHUAC": "011",
        "VENUSTIANO CARRANZA": "017",
        "IZTAPALAPA": "007",
        "MILPA ALTA": "009",
        "CUAJIMALPA": "004",
        "BENITO JUAREZ": "014",
        "MIGUEL HIDALGO": "016",
        "AZCAPOTZALCO": "002",
        "COYOACAN": "003",
        "IZTACALCO": "006",
        "TLALPAN": "012",
        "XOCHIMILCO": "013",
        # INFANCIAS_2016_10/2017_11/2018_11: "Álvaro Obregón" viene con una
        # corrupción irreversible (no simple mojibake latin-1<->utf-8): el
        # byte UTF-8 de "Á" (0xC3 0x81) se decodificó con un códec donde 0x81
        # es un byte indefinido y se sustituyó por U+FFFD ("�") antes de
        # guardar el CSV, así que el carácter original ya no está recuperable
        # por _reparar_mojibake (que sí revierte "ó" -> "Ã³" en la misma
        # palabra, pero no puede reencodear una cadena que contiene U+FFFD).
        # Se registra el resultado exacto de _clave_normalizada sobre el
        # valor corrupto observado ("Ã�lvaro ObregÃ³n") como alias explícito,
        # en vez de intentar reparar el mojibake de forma genérica.
        "A�LVARO OBREGA3N": "010",
    }
    for nombre, cve in alias.items():
        mapa.setdefault(nombre, cve)
    return mapa


_NOMBRE_A_CLAVE = _cargar_nombre_a_clave()


def normalizar_alcaldia(valor, tipo: str) -> str:
    """Devuelve cve_alc (3 dígitos, '002'..'017') o levanta ValueError.

    tipo:
      - "clave": clave_alcaldia (Gen A) o cve_mun (Gen B/Comercios), ya viene
        como el código INEGI de 3 dígitos (str o int).
      - "municipio_id": Cultura, entero sin ceros a la izquierda (ej. 3).
      - "nombre": Infancias/Salud/PILARES, texto libre con acentos/capitalización
        inconsistentes.
    """
    if tipo in ("clave", "municipio_id"):
        cve = f"{int(valor):03d}"
        if cve not in CLAVES_VALIDAS:
            raise ValueError(f"clave de alcaldía fuera de las 16 válidas: {valor!r} -> {cve}")
        return cve
    if tipo == "nombre":
        if valor is None:
            raise ValueError("nombre de alcaldía vacío")
        clave_norm = _clave_normalizada(str(valor))
        if clave_norm not in _NOMBRE_A_CLAVE:
            raise ValueError(f"nombre de alcaldía no reconocido: {valor!r} (normalizado: {clave_norm!r})")
        return _NOMBRE_A_CLAVE[clave_norm]
    raise ValueError(f"tipo desconocido: {tipo!r} (usar 'clave', 'municipio_id' o 'nombre')")
