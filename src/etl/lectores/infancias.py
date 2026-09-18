"""Lector de la familia `infancias` (CLAUDE.md §2, dominio "Infancia").

Carpetas `data/INFANCIAS_YYYY_MM/` (11 ediciones, 2016-10 .. 2026-05). Cada una
trae `denue_infancias_cdmx_YYYY_MM.csv` (el CSV ya filtrado a establecimientos
de infancias), `reporte_calidad_infancias_YYYY_MM.json` (linaje + conteos) y
otros CSV auxiliares (rechazados, revisión manual, catálogo SCIAN) que no se
leen aquí. Solo `INFANCIAS_2016_10` trae `README.md`; el resto no, pero el
encabezado del CSV es **idéntico byte a byte** en las 11 carpetas (verificado
por hash de la primera línea de las 11 ediciones en esta sesión), así que la
ausencia de README no bloquea el mapeo de columnas.

Esta familia identifica la alcaldía **solo por nombre** (columna `Alcaldía`),
nunca por clave numérica (a diferencia de Gen A/Gen B/Comercios) ->
`etl.catalogo.normalizar_alcaldia(valor, tipo="nombre")`. La edición 2016-10
trae los nombres de alcaldía con el mismo mojibake que Gen A (ej.
"Benito JuÃ¡rez", "Ã�lvaro ObregÃ³n"); `normalizar_alcaldia` ya repara el
mojibake internamente (`_reparar_mojibake`), así que no se trata aparte aquí.

Solo alcaldía (CLAUDE.md §3): no se leen `Clave geográfica AGEB`, `AGEB`,
`Manzana`, `Localidad`, `Asentamiento`, coordenadas, ni ninguna otra columna
territorial fina, aunque estén presentes en el CSV origen.

Edición: `fuente.edicion` del JSON de calidad es confiable para esta familia
(no tiene el bug de metadatos de Gen A, CLAUDE.md §1.1) -> se resuelve con
`etl.ediciones.resolver_edicion_confiable`, que además cruza contra el nombre
de carpeta.

Mapeo de columnas reales (verificado con `head -1` sobre las 11 carpetas) al
esquema largo común:

    CLEE                              -> clee
    Código SCIAN                      -> scian
    Alcaldía                          -> cve_alc (normalizado, tipo="nombre")
    Subcategoría                      -> subcategoria (tal cual, sin reinterpretar)
    Sector                            -> sector
    Alcance                           -> alcance
    Revisión manual ("SI"/"NO")       -> revision_manual (bool)
    Población objetivo estimada       -> poblacion_objetivo_estimada (texto
                                          categórico tal cual, ej. "Primera
                                          infancia (0 a 5 años aprox.)"; pese
                                          al nombre de la columna NO es un
                                          número, es una franja de edad
                                          estimada por regla, se preserva como
                                          texto)
    Enfoque primera infancia (0/1)    -> es_primera_infancia (bool)
    Es guardería o estancia infantil,
    Es preescolar, Es primaria,
    Es secundaria, Es escuela de
    varios niveles, Es educación
    especial, Es media superior o
    técnica, Es formación
    complementaria, Es club o
    deporte, Es recreación o cultura
    infantil, Es apoyo social o
    residencia (todas 0/1)            -> flags_dominio

Decisión de diseño para `flags_dominio` (documentada aquí por instrucción
explícita de la tarea): en vez de una columna booleana por flag -que rompería
el esquema largo común compartido con familias que no tienen estos flags
(Gen A, Gen B/Comercios)-, se consolidan en una sola columna string con los
nombres de los flags en `True` separados por `;` (vacío si ninguno). Esto
preserva el 100% de la información (ningún flag se descarta) y mantiene el
esquema largo estable entre familias; la metodología de estimación (fuera de
este alcance) decide qué flags sumar, puede hacerlo con
`flags_dominio.str.contains(...)`. `Enfoque primera infancia` se excluye de
`flags_dominio` porque ya tiene su propia columna (`es_primera_infancia`) en
el esquema pedido para esta familia.

`Dedicación a infancias` (columna adicional del CSV, no listada en el esquema
de salida que fija esta tarea) no se propaga como columna propia: el esquema
de salida para `infancias.py` está fijado explícitamente en la tarea como
`familia, edicion, edicion_verificada, cve_alc, clee, scian, dominio,
subcategoria, sector, alcance, revision_manual, poblacion_objetivo_estimada,
es_primera_infancia, flags_dominio`, y se sigue tal cual para no introducir
una columna que ninguna otra familia tendría. Si la metodología la necesita
más adelante, está disponible en el CSV origen (`Dedicación a infancias`) y
puede añadirse explícitamente en un cambio de esquema aparte.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pandas as pd

_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR.parent.parent))  # para `python archivo.py` directo

from etl.catalogo import CLAVES_VALIDAS, normalizar_alcaldia  # noqa: E402
from etl.ediciones import resolver_edicion_confiable  # noqa: E402

FAMILIA = "infancias"
DOMINIO_FIJO = "infancia"

# Columnas "Es *" que se consolidan en flags_dominio (se excluye "Enfoque
# primera infancia": tiene columna propia es_primera_infancia).
_COLUMNAS_FLAG = [
    "Es guardería o estancia infantil",
    "Es preescolar",
    "Es primaria",
    "Es secundaria",
    "Es escuela de varios niveles",
    "Es educación especial",
    "Es media superior o técnica",
    "Es formación complementaria",
    "Es club o deporte",
    "Es recreación o cultura infantil",
    "Es apoyo social o residencia",
]

_COLUMNA_PRIMERA_INFANCIA = "Enfoque primera infancia"

_COLUMNAS_ORIGEN = [
    "CLEE",
    "Código SCIAN",
    "Alcaldía",
    "Subcategoría",
    "Sector",
    "Alcance",
    "Revisión manual",
    "Población objetivo estimada",
    _COLUMNA_PRIMERA_INFANCIA,
    *_COLUMNAS_FLAG,
]

_COLUMNAS_SALIDA = [
    "familia",
    "edicion",
    "edicion_verificada",
    "cve_alc",
    "clee",
    "scian",
    "dominio",
    "subcategoria",
    "sector",
    "alcance",
    "revision_manual",
    "poblacion_objetivo_estimada",
    "es_primera_infancia",
    "flags_dominio",
]


def _mapear_revision_manual(serie: pd.Series) -> pd.Series:
    mapa = {"SI": True, "SÍ": True, "NO": False}
    return serie.map(lambda v: mapa.get(str(v).strip().upper()) if pd.notna(v) else pd.NA)


def _mapear_bool_01(serie: pd.Series) -> pd.Series:
    return serie.map(lambda v: bool(int(v)) if pd.notna(v) else pd.NA)


def _flags_a_string(df: pd.DataFrame) -> pd.Series:
    """Concatena los nombres de las columnas `Es *` en 1, separados por ';'."""

    def _fila(fila) -> str:
        activos = [col for col in _COLUMNAS_FLAG if pd.notna(fila[col]) and int(fila[col]) == 1]
        return ";".join(activos)

    return df[_COLUMNAS_FLAG].apply(_fila, axis=1)


def _leer_una_carpeta(carpeta: Path) -> pd.DataFrame:
    nombre_carpeta = carpeta.name
    jsons = list(carpeta.glob("reporte_calidad_infancias_*.json"))
    if len(jsons) != 1:
        raise ValueError(f"[infancias] {nombre_carpeta}: se esperaba exactamente 1 reporte_calidad_infancias_*.json, hay {len(jsons)}")
    reporte = json.loads(jsons[0].read_text(encoding="utf-8"))
    fuente = reporte.get("fuente", {})

    edicion = resolver_edicion_confiable(fuente, nombre_carpeta)
    if not edicion.verificada:
        warnings.warn(
            f"[infancias] {nombre_carpeta}: edición no verificada ({edicion.edicion}, "
            f"procedencia={edicion.procedencia})"
        )

    csvs = list(carpeta.glob("denue_infancias_cdmx_*.csv"))
    if len(csvs) != 1:
        raise ValueError(f"[infancias] {nombre_carpeta}: se esperaba exactamente 1 denue_infancias_cdmx_*.csv, hay {len(csvs)}")
    ruta_csv = csvs[0]

    header = pd.read_csv(ruta_csv, nrows=0, encoding="utf-8-sig").columns.tolist()
    columnas_faltantes = [c for c in _COLUMNAS_ORIGEN if c not in header]
    columnas_presentes = [c for c in _COLUMNAS_ORIGEN if c in header]
    if columnas_faltantes:
        warnings.warn(
            f"[infancias] {nombre_carpeta}: columnas esperadas ausentes en el CSV: {columnas_faltantes} "
            f"(se rellenan con NA)"
        )

    df = pd.read_csv(
        ruta_csv,
        usecols=columnas_presentes,
        encoding="utf-8-sig",
        dtype={"CLEE": "string"} if "CLEE" in columnas_presentes else None,
    )

    for col in columnas_faltantes:
        df[col] = pd.NA

    # Alcaldía: solo nombre para esta familia -> tipo="nombre".
    filas_totales = len(df)
    cve_alc = []
    no_reconocidas: dict[str, int] = {}
    for valor in df["Alcaldía"]:
        try:
            cve_alc.append(normalizar_alcaldia(valor, tipo="nombre"))
        except ValueError:
            cve_alc.append(pd.NA)
            no_reconocidas[str(valor)] = no_reconocidas.get(str(valor), 0) + 1
    if no_reconocidas:
        warnings.warn(
            f"[infancias] {nombre_carpeta}: {sum(no_reconocidas.values())}/{filas_totales} filas con "
            f"Alcaldía no reconocida (se conservan con cve_alc=NA, no se descartan silenciosamente): "
            f"{no_reconocidas}"
        )

    # Columnas faltantes ya se rellenaron con pd.NA arriba, así que
    # _flags_a_string las trata como flag inactivo sin lanzar.
    flags_dominio = _flags_a_string(df)

    salida = pd.DataFrame(
        {
            "familia": FAMILIA,
            "edicion": edicion.edicion,
            "edicion_verificada": edicion.verificada,
            "cve_alc": cve_alc,
            "clee": df["CLEE"] if "CLEE" in df.columns else pd.NA,
            "scian": df["Código SCIAN"] if "Código SCIAN" in df.columns else pd.NA,
            "dominio": DOMINIO_FIJO,
            "subcategoria": df["Subcategoría"] if "Subcategoría" in df.columns else pd.NA,
            "sector": df["Sector"] if "Sector" in df.columns else pd.NA,
            "alcance": df["Alcance"] if "Alcance" in df.columns else pd.NA,
            "revision_manual": _mapear_revision_manual(df["Revisión manual"]) if "Revisión manual" in df.columns else pd.NA,
            "poblacion_objetivo_estimada": df["Población objetivo estimada"] if "Población objetivo estimada" in df.columns else pd.NA,
            "es_primera_infancia": _mapear_bool_01(df[_COLUMNA_PRIMERA_INFANCIA]) if _COLUMNA_PRIMERA_INFANCIA in df.columns else pd.NA,
            "flags_dominio": flags_dominio,
        }
    )

    # Chequeo cruzado contra reporte_calidad_infancias_*.json -> resultados["Registros de infancias seleccionados"]
    conteo_reportado = reporte.get("resultados", {}).get("Registros de infancias seleccionados")
    if conteo_reportado is not None and len(salida) != conteo_reportado:
        warnings.warn(
            f"[infancias] {nombre_carpeta}: filas leídas ({len(salida)}) != "
            f"resultados['Registros de infancias seleccionados'] ({conteo_reportado})"
        )

    return salida[_COLUMNAS_SALIDA]


def leer_todas(data_dir: Path) -> pd.DataFrame:
    """Recorre las 11 carpetas `INFANCIAS_*` bajo `data_dir` y devuelve el
    esquema largo común (ver docstring del módulo). No lanza si una carpeta
    individual falla de forma "blanda" (alcaldía no reconocida, edición no
    verificada, discrepancia de conteo: todo como warnings); sí propaga
    ValueError de linaje/edición (regla dura, CLAUDE.md §1.1 /
    docs/architecture-plan.md) o de estructura de archivos inesperada.
    """
    data_dir = Path(data_dir)
    carpetas = sorted(p for p in data_dir.glob("INFANCIAS_*") if p.is_dir())
    if not carpetas:
        raise ValueError(f"[infancias] no se encontraron carpetas INFANCIAS_* en {data_dir}")

    marcos = [_leer_una_carpeta(carpeta) for carpeta in carpetas]
    resultado = pd.concat(marcos, ignore_index=True)

    ediciones_distintas = resultado["edicion"].nunique()
    if ediciones_distintas != len(carpetas):
        warnings.warn(
            f"[infancias] se esperaban {len(carpetas)} ediciones distintas, se obtuvieron {ediciones_distintas}"
        )

    claves_invalidas = resultado.loc[~resultado["cve_alc"].isin(CLAVES_VALIDAS) & resultado["cve_alc"].notna()]
    if not claves_invalidas.empty:
        warnings.warn(f"[infancias] {len(claves_invalidas)} filas con cve_alc fuera del catálogo tras normalizar")

    return resultado


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent.parent.parent
    df = leer_todas(raiz / "data")
    salida = raiz / "data" / "processed" / "infancias.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False)
    print(f"Escrito {len(df)} filas en {salida}")
