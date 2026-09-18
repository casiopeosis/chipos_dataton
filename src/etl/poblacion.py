"""Lector del denominador poblacional: Censo 2020, hoja `Por alcaldía`.

Fuente: `data/ESTUDIO EDADES CENSO 2020/datos/ESTUDIO_POBLACION_TODAS_LAS_EDADES_CDMX_2020.xlsx`.

Este dataset NO es uno de los 3 dominios de demanda (adultos mayores, infancia,
cultura); es el insumo transversal que sirve de denominador poblacional para
el estimador (CLAUDE.md §4). Reemplaza el diccionario `POBLACION_2020_ALCALDIA`
hardcodeado en `src/engine.py`.

## Grupos de edad

`g0_17`, `g18_29`, `g30_59`, `g60m` cubren el total de la población sin
traslapes ni huecos. `g65m` es un indicador COMPLEMENTARIO: está CONTENIDO en
`g60m` (65+ ⊂ 60+) y nunca debe sumarse aparte al construir el total.

## Método de reparto del grupo quinquenal 15-19

Documentado en las hojas `Método` y `Diccionario` del propio xlsx (y resumido
en el README de la carpeta): la fuente censal original viene en grupos
quinquenales (0-4, 5-9, ..., 85+). Solo el corte 17/18 años cae dentro de un
grupo quinquenal (15-19), así que ese grupo se reparte asumiendo distribución
uniforme por edad dentro del quinquenio:

    0-17   = 0-4 + 5-9 + 10-14 + 0.60 * (15-19)
    18-29  = 0.40 * (15-19) + 20-24 + 25-29
    30-59  = 30-34 + ... + 55-59      (sin prorrateo)
    60+    = 60-64 + ... + 85+        (sin prorrateo)
    65+    = 65-69 + ... + 85+        (subconjunto informativo de 60+)

**Decisión de esta implementación**: no se re-deriva el prorrateo a mano desde
la base quinquenal (`Base alcaldía`, 576 filas). La hoja `Por alcaldía` del
mismo xlsx ya trae los 5 grupos (0-17, 18-29, 30-59, 60+, 65+) precalculados
con exactamente este método -- se verificó cruzando la hoja `Método` (pesos
0.60/0.40 para 15-19) contra los valores de `Por alcaldía`, y también trae su
propia columna de cuadre `Control` (debe ser 0 en las 16 filas y en la fila de
suma). Se usa ese cálculo ya hecho en vez de reimplementarlo, tal como permite
la instrucción de la tarea ("si el xlsx ya trae los grupos precalculados...
puede que no necesites re-derivar el reparto tú mismo").

## Nivel territorial

Solo alcaldía. La hoja `Base localidad` (alcaldía+localidad, 3,276 filas) NO
se lee aquí -- está fuera de alcance (CLAUDE.md §3, decisión de equipo cerrada
de no implementar AGEB/niveles sub-alcaldía). La fila de agregado
`CDMX (suma)` de `Por alcaldía` se excluye explícitamente: no es una alcaldía.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from etl.catalogo import normalizar_alcaldia  # noqa: E402

XLSX_RELATIVO = Path("ESTUDIO EDADES CENSO 2020") / "datos" / "ESTUDIO_POBLACION_TODAS_LAS_EDADES_CDMX_2020.xlsx"
HOJA = "Por alcaldía"
FILA_ENCABEZADO = 4  # 0-indexado para pandas -> fila 5 del xlsx ("Alcaldía", "Población total", ...)
FILA_AGREGADO = "CDMX (suma)"

POBLACION_ESPERADA_TOTAL = 9_200_318

_COLUMNAS_ESPERADAS = {
    "Alcaldía",
    "Población total",
    "0-17",
    "18-29",
    "30-59",
    "60+",
    "65+",
    "Control",
}


def leer_poblacion(data_dir: Path) -> pd.DataFrame:
    """Lee la hoja `Por alcaldía` del censo 2020 y devuelve el denominador
    poblacional por alcaldía.

    Parameters
    ----------
    data_dir:
        Ruta a la carpeta `data/` del repo (contiene `ESTUDIO EDADES CENSO 2020/`).

    Returns
    -------
    DataFrame con columnas:
        cve_alc, poblacion_total, g0_17, g18_29, g30_59, g60m, g65m

    16 filas, una por alcaldía (cve_alc '002'..'017'). `g65m` está CONTENIDO
    en `g60m` (65+ ⊂ 60+); nunca sumar ambos para obtener un total.

    Levanta ValueError si falta alguna alcaldía, si hay alcaldías repetidas,
    si `Control` != 0 para alguna fila, o si el xlsx no trae las columnas
    esperadas (para detectar temprano un cambio de esquema en la fuente).
    """
    xlsx_path = data_dir / XLSX_RELATIVO
    if not xlsx_path.exists():
        raise FileNotFoundError(f"No se encontró el xlsx de población: {xlsx_path}")

    df = pd.read_excel(xlsx_path, sheet_name=HOJA, header=FILA_ENCABEZADO)

    faltantes = _COLUMNAS_ESPERADAS - set(df.columns)
    if faltantes:
        raise ValueError(
            f"La hoja '{HOJA}' no trae las columnas esperadas; faltan: {sorted(faltantes)}. "
            "El esquema del xlsx pudo haber cambiado."
        )

    # Quitar filas totalmente vacías (separadores visuales del xlsx).
    df = df.dropna(subset=["Alcaldía"]).copy()

    # Separar la fila de agregado/cuadre explícitamente -- no es una alcaldía.
    es_agregado = df["Alcaldía"].astype(str).str.strip() == FILA_AGREGADO
    fila_agregado = df[es_agregado]
    df = df[~es_agregado].copy()

    if fila_agregado.empty:
        raise ValueError(
            f"No se encontró la fila de agregado '{FILA_AGREGADO}' en la hoja '{HOJA}'; "
            "no se puede confirmar que no se perdió/duplicó una fila real."
        )

    # Verificación de cuadre: Control debe ser 0 en todas las filas de alcaldía
    # y también en la fila de agregado.
    control_no_cero = df[df["Control"].round(6) != 0]
    if not control_no_cero.empty:
        raise ValueError(
            "Filas con columna 'Control' distinta de 0 (el reparto 0-17/18-29/30-59/60+ "
            f"no cuadra con 'Población total'): {control_no_cero['Alcaldía'].tolist()}"
        )
    if round(float(fila_agregado["Control"].iloc[0]), 6) != 0:
        raise ValueError(
            f"La fila de agregado '{FILA_AGREGADO}' tiene Control != 0: "
            f"{fila_agregado['Control'].iloc[0]!r}"
        )

    df["cve_alc"] = df["Alcaldía"].map(lambda v: normalizar_alcaldia(v, tipo="nombre"))

    if df["cve_alc"].duplicated().any():
        repetidas = df.loc[df["cve_alc"].duplicated(keep=False), "Alcaldía"].tolist()
        raise ValueError(f"Alcaldías repetidas tras normalizar: {repetidas}")

    from etl.catalogo import CLAVES_VALIDAS  # import local para evitar ciclo al tope del módulo

    faltan_claves = CLAVES_VALIDAS - set(df["cve_alc"])
    if faltan_claves:
        raise ValueError(f"Faltan alcaldías en la hoja '{HOJA}': claves ausentes {sorted(faltan_claves)}")

    resultado = df.rename(
        columns={
            "Población total": "poblacion_total",
            "0-17": "g0_17",
            "18-29": "g18_29",
            "30-59": "g30_59",
            "60+": "g60m",
            "65+": "g65m",
        }
    )[["cve_alc", "poblacion_total", "g0_17", "g18_29", "g30_59", "g60m", "g65m"]]

    resultado = resultado.sort_values("cve_alc").reset_index(drop=True)

    if (resultado["g60m"] < resultado["g65m"]).any():
        malas = resultado.loc[resultado["g60m"] < resultado["g65m"], "cve_alc"].tolist()
        raise ValueError(f"g60m < g65m (65+ debe estar contenido en 60+) para: {malas}")

    return resultado


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    out_dir = data_dir / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = leer_poblacion(data_dir)

    suma_total = df["poblacion_total"].sum()
    print(f"Filas: {len(df)}")
    print(f"Suma poblacion_total: {suma_total} (esperado {POBLACION_ESPERADA_TOTAL})")
    if round(suma_total) != POBLACION_ESPERADA_TOTAL:
        print(f"  DIFERENCIA: {suma_total - POBLACION_ESPERADA_TOTAL}")

    out_path = out_dir / "poblacion_alcaldia.csv"
    df.to_csv(out_path, index=False)
    print(f"Escrito: {out_path}")
