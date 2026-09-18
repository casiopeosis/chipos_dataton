"""Resolución de la edición (periodo "YYYY-MM") de una carpeta de datos.

Regla dura (CLAUDE.md §1.1, docs/current-state.md §6): las carpetas Gen A
(`OCTUBRE 2016 CDMX`, `NOVIEMBRE 2017/2018/2020 CDMX`) tienen los campos
`fuente.anio_datos`, `fuente.mes_corte`, `fuente.edicion` y `fuente.nota_temporal`
de su `reporte_calidad_denue_*.json` **idénticos e incorrectos** (los 4 dicen
"2020-11", es una plantilla no actualizada). Esa misma plantilla contamina las
columnas de fila equivalentes (`anio_datos`, `mes_corte`, `edicion_denue`) y
`archivos_generados`. Ninguno de esos campos se usa jamás para Gen A.

La única fuente de verdad para Gen A es `fuente.archivo` (nombre del zip de
entrada, ej. "denue_09_1016.zip") vía regex `denue_09_(MM)(AA)`, con
`fuente.sha256_archivo_entrada` como acompañante de linaje.

Para el resto de familias (Gen B, Comercios, Infancias, Salud) `fuente.edicion`
SÍ es confiable y se cruza contra el nombre de carpeta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MESES = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}

_RE_ARCHIVO = re.compile(r"denue_09_(\d{2})(\d{2})")
_RE_CARPETA_MES_ANIO = re.compile(r"([A-ZÑÁÉÍÓÚ]+)\s+(\d{4})", re.IGNORECASE)
_RE_CARPETA_ANIO_MES = re.compile(r"(\d{4})_(\d{2})")
_RE_EDICION_YYYY_MM = re.compile(r"(\d{4})[-/](\d{2})\b")
_RE_EDICION_MM_YYYY = re.compile(r"(\d{2})/(\d{4})")  # ej. "DENUE 05/2025" (Gen B / Comercios)


@dataclass(frozen=True)
class Edicion:
    edicion: str  # "YYYY-MM"
    verificada: bool
    procedencia: str


def edicion_desde_carpeta(nombre_carpeta: str) -> str | None:
    """"NOVIEMBRE 2018 CDMX" -> "2018-11"; "INFANCIAS_2025_05" -> "2025-05"."""
    m = _RE_CARPETA_ANIO_MES.search(nombre_carpeta)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = _RE_CARPETA_MES_ANIO.search(nombre_carpeta)
    if m:
        mes = _MESES.get(m.group(1).upper())
        if mes:
            return f"{m.group(2)}-{mes:02d}"
    return None


def edicion_desde_archivo_zip(nombre_archivo: str) -> str | None:
    """"denue_09_1016.zip" -> "2016-10" (grupo1=MM, grupo2=AA)."""
    m = _RE_ARCHIVO.search(nombre_archivo)
    if not m:
        return None
    mm, aa = m.group(1), m.group(2)
    return f"20{aa}-{mm}"


def resolver_edicion_gen_a(fuente: dict, nombre_carpeta: str) -> Edicion:
    """Gen A: SOLO `fuente.archivo`. Ignora anio_datos/mes_corte/edicion/nota_temporal
    del JSON, y las columnas anio_datos/mes_corte/edicion_denue de cada fila del CSV
    (nunca se leen para fechar).
    """
    archivo = fuente.get("archivo")
    cruce = edicion_desde_carpeta(nombre_carpeta)
    if not archivo:
        if cruce is None:
            raise ValueError(f"Gen A sin fuente.archivo ni edición derivable de la carpeta: {nombre_carpeta!r}")
        return Edicion(edicion=cruce, verificada=False, procedencia="carpeta (sin fuente.archivo, ej. NOVIEMBRE 2021)")
    edicion = edicion_desde_archivo_zip(archivo)
    if edicion is None:
        raise ValueError(f"fuente.archivo no coincide con el patrón denue_09_MMAA: {archivo!r}")
    if cruce is not None and cruce != edicion:
        raise ValueError(
            f"Gen A: edición de fuente.archivo ({edicion}) no coincide con la carpeta ({cruce}) en {nombre_carpeta!r}"
        )
    return Edicion(edicion=edicion, verificada=True, procedencia="fuente.archivo")


def resolver_edicion_confiable(fuente: dict | None, nombre_carpeta: str) -> Edicion:
    """Gen B / Comercios / Infancias / Salud: `fuente.edicion` es confiable
    (a diferencia de Gen A), se cruza contra el nombre de carpeta.
    """
    cruce = edicion_desde_carpeta(nombre_carpeta)
    edicion_raw = (fuente or {}).get("edicion")
    if not edicion_raw:
        if cruce is None:
            raise ValueError(f"Sin fuente.edicion ni edición derivable de la carpeta: {nombre_carpeta!r}")
        return Edicion(edicion=cruce, verificada=False, procedencia="carpeta (sin fuente.edicion, ej. SALUD_CDMX_2019_11)")
    texto = str(edicion_raw)
    m = _RE_EDICION_YYYY_MM.search(texto)
    if m:
        edicion = f"{m.group(1)}-{m.group(2)}"
    else:
        m = _RE_EDICION_MM_YYYY.search(texto)
        if not m:
            raise ValueError(f"fuente.edicion no tiene formato YYYY-MM ni MM/YYYY reconocible: {edicion_raw!r}")
        edicion = f"{m.group(2)}-{m.group(1)}"
    verificada = cruce == edicion if cruce is not None else False
    if cruce is not None and cruce != edicion:
        raise ValueError(
            f"edición de fuente.edicion ({edicion}) no coincide con la carpeta ({cruce}) en {nombre_carpeta!r}"
        )
    return Edicion(edicion=edicion, verificada=verificada, procedencia="fuente.edicion")
