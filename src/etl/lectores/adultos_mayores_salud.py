"""Lectores de la familia salud + adultos mayores/deporte (Gen A + Gen B + Salud DENUE).

Produce el esquema largo común (un registro por establecimiento):

    familia, generacion, edicion, edicion_verificada, cve_alc, clee, scian,
    dominio, subcategoria, sector, alcance, revision_manual

- `leer_deporte_adultos_mayores`: unifica Gen A (2016-2020, sin README, esquema
  "enfoque") y Gen B (2022-2026, con README, esquema "depurado") en un solo
  DataFrame. `generacion` distingue de qué pipeline de origen vino cada fila.
- `leer_salud`: las 11 carpetas `SALUD_CDMX_*` (esquema propio, ya trae su
  clasificación temática resuelta en el CSV, no pasa por `dominios_scian.csv`).

Reglas duras que este módulo respeta (CLAUDE.md §1.1, docs/current-state.md §6,
docs/architecture-plan.md):

1. Gen A: la edición se resuelve **solo** con `resolver_edicion_gen_a`, que a su
   vez ignora `anio_datos`/`mes_corte`/`edicion`/`nota_temporal` del JSON y las
   columnas de fila equivalentes. Nunca se leen esos campos aquí.
2. Gen A se une por `clave_alcaldia` (nunca por el nombre con mojibake).
3. Salud no trae `cve_mun`: solo la columna `Alcaldía` (nombre, sin mojibake),
   se normaliza con `tipo="nombre"`.
4. `dominio`/`subcategoria` de adultos_mayores/deporte (Gen A y Gen B) salen de
   `data/reference/dominios_scian.csv` por código SCIAN, nunca de los textos
   descriptivos (`categoria_enfoque`, `subcategoria_proyecto`) que trae cada
   CSV — así la subcategoría queda comparable entre generaciones. Cualquier
   SCIAN no catalogado se reporta como warning y queda con `dominio=None`.
5. Si `dominios_scian.csv` marca en su `nota` que un código fuerza revisión
   manual ("revision_manual=true"), se aplica sin importar el flag original
   del archivo (aplica a 624121/624122, mezcla de poblaciones).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ..catalogo import normalizar_alcaldia
from ..ediciones import resolver_edicion_confiable, resolver_edicion_gen_a

log = logging.getLogger(__name__)

_REF_DOMINIOS = Path(__file__).resolve().parent.parent.parent.parent / "data" / "reference" / "dominios_scian.csv"

_GEN_A_FOLDERS = [
    "OCTUBRE 2016 CDMX",
    "NOVIEMBRE 2017 CDMX",
    "NOVIEMBRE 2018 CDMX",
    "NOVIEMBRE 2020 CDMX",
    "NOVIEMBRE 2021 CDMX",
]
_GEN_B_FOLDERS = [
    "NOVIEMBRE 2022 CDMX",
    "NOVIEMBRE 2023 CDMX",
    "NOVIEMBRE 2024 CDMX",
    "MAYO 2025 CDMX",
    "MAYO 2026 CDMX",
]
_SALUD_GLOB = "SALUD_CDMX_*"

_ESQUEMA_COLUMNAS = [
    "familia",
    "generacion",
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
]


def _cargar_catalogo_scian() -> dict[str, dict]:
    """scian -> {dominio, subcategoria, en_serie_armonizada, nota, revision_forzada}.

    `dominios_scian.csv` trae `nota` como texto libre con comas SIN encomillar
    (ej. la fila 611621: "...(2022+), no comparable..."), lo que rompe un
    `pd.read_csv` normal. Se parsea a mano: las primeras 4 columnas son
    estructuradas, todo lo que sigue a la 4a coma es `nota`.
    """
    import csv

    catalogo: dict[str, dict] = {}
    with _REF_DOMINIOS.open(encoding="utf-8", newline="") as f:
        lector = csv.reader(f)
        encabezado = next(lector)
        assert encabezado[:4] == ["scian", "dominio", "subcategoria", "en_serie_armonizada"], encabezado
        for fila in lector:
            if not fila:
                continue
            scian, dominio, subcategoria, _en_serie, *resto = fila
            nota = ",".join(resto)
            catalogo[scian] = {
                "dominio": dominio,
                "subcategoria": subcategoria,
                "revision_forzada": "revision_manual=true" in nota,
            }
    return catalogo


_CATALOGO_SCIAN = _cargar_catalogo_scian()


def _mapear_alcaldia_serie(serie: pd.Series, tipo: str, contexto: str) -> pd.Series:
    """Normaliza una columna de alcaldía valor por valor (cardinalidad baja),
    reportando como warning cualquier valor no reconocido (queda como None)."""
    valores_unicos = serie.dropna().unique()
    mapa: dict[object, str | None] = {}
    no_reconocidos: dict[object, int] = {}
    for valor in valores_unicos:
        try:
            mapa[valor] = normalizar_alcaldia(valor, tipo=tipo)
        except ValueError:
            mapa[valor] = None
            no_reconocidos[valor] = int((serie == valor).sum())
    if no_reconocidos:
        log.warning("%s: alcaldías no reconocidas %s", contexto, no_reconocidos)
    return serie.map(mapa)


def _mapear_scian(serie: pd.Series, contexto: str) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Devuelve (dominio, subcategoria, revision_forzada) para una columna scian,
    reportando como warning cualquier código no catalogado (dominio=None)."""
    no_catalogados: dict[str, int] = {}
    conteo_por_scian = serie.value_counts()
    for codigo in serie.unique():
        if codigo not in _CATALOGO_SCIAN:
            no_catalogados[codigo] = int(conteo_por_scian.get(codigo, 0))
    if no_catalogados:
        log.warning("%s: códigos SCIAN no catalogados en dominios_scian.csv %s", contexto, no_catalogados)

    dominio_map = {c: i["dominio"] for c, i in _CATALOGO_SCIAN.items()}
    subcat_map = {c: i["subcategoria"] for c, i in _CATALOGO_SCIAN.items()}
    forzada_map = {c: i["revision_forzada"] for c, i in _CATALOGO_SCIAN.items()}
    dominios = serie.map(dominio_map)
    subcats = serie.map(subcat_map)
    forzadas = serie.map(forzada_map).fillna(False)
    return dominios, subcats, forzadas


def _bool_si_no(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.strip().str.upper().map({"SI": True, "NO": False, "1": True, "0": False})


def _leer_gen_a(carpeta: Path) -> pd.DataFrame:
    nombre_carpeta = carpeta.name
    json_path = carpeta / f"reporte_calidad_denue_{_sufijo_anio(nombre_carpeta)}.json"
    fuente: dict = {}
    if json_path.exists():
        import json

        with json_path.open(encoding="utf-8") as f:
            fuente = json.load(f).get("fuente", {})
    else:
        log.warning("%s: sin reporte_calidad JSON, edición cae al fallback por carpeta", nombre_carpeta)

    edicion_info = resolver_edicion_gen_a(fuente, nombre_carpeta)

    candidatos = sorted(carpeta.glob("denue_enfoque_gimnasios_adultos_mayores_cdmx_*.csv"))
    if not candidatos:
        raise FileNotFoundError(f"Gen A: no se encontró el CSV de unión en {nombre_carpeta!r}")
    union_path = candidatos[0]

    # Aviso explícito: en NOVIEMBRE 2021 CDMX el archivo temático de adultos
    # mayores trae sufijo " (2)" (descarga duplicada). No se usa (solo se usa
    # el archivo de unión ya deduplicado), pero se deja constancia.
    duplicado = sorted(set(carpeta.glob("* (2).csv")))
    if duplicado:
        log.warning(
            "%s: se encontró archivo con sufijo de descarga duplicada %s (no se usa; se lee solo el archivo de unión)",
            nombre_carpeta,
            [p.name for p in duplicado],
        )

    df = pd.read_csv(
        union_path,
        dtype=str,
        usecols=["id_denue", "clee", "codigo_scian", "clave_alcaldia", "sector", "requiere_revision_manual"],
    )

    dup_id = df["id_denue"].duplicated().sum()
    if dup_id:
        log.warning("%s: %d filas con id_denue duplicado, se descartan", nombre_carpeta, dup_id)
        df = df.drop_duplicates(subset="id_denue")

    cve_alc = _mapear_alcaldia_serie(df["clave_alcaldia"], tipo="clave", contexto=nombre_carpeta)
    dominio, subcategoria, forzada = _mapear_scian(df["codigo_scian"], contexto=nombre_carpeta)
    revision_manual = _bool_si_no(df["requiere_revision_manual"]) | forzada

    return pd.DataFrame(
        {
            "familia": "adultos_mayores_deporte",
            "generacion": "gen_a",
            "edicion": edicion_info.edicion,
            "edicion_verificada": edicion_info.verificada,
            "cve_alc": cve_alc,
            "clee": df["clee"],
            "scian": df["codigo_scian"],
            "dominio": dominio,
            "subcategoria": subcategoria,
            "sector": df["sector"],
            "alcance": None,
            "revision_manual": revision_manual,
        }
    )


def _sufijo_anio(nombre_carpeta: str) -> str:
    """"OCTUBRE 2016 CDMX" -> "2016"; usado solo para construir el nombre del
    JSON de calidad (que siempre trae el año calendario de la carpeta, no el
    campo con bug)."""
    for token in nombre_carpeta.split():
        if token.isdigit() and len(token) == 4:
            return token
    raise ValueError(f"no se pudo derivar el año de la carpeta: {nombre_carpeta!r}")


def _leer_gen_b(carpeta: Path) -> pd.DataFrame:
    nombre_carpeta = carpeta.name
    json_path = carpeta / "resumen_calidad.json"
    fuente = None
    if json_path.exists():
        import json

        with json_path.open(encoding="utf-8") as f:
            fuente = json.load(f).get("fuente", {})
    else:
        log.warning("%s: sin resumen_calidad.json, edición cae al fallback por carpeta", nombre_carpeta)

    edicion_info = resolver_edicion_confiable(fuente, nombre_carpeta)

    candidatos = sorted(carpeta.glob("denue_cdmx_*_depurado.csv"))
    if not candidatos:
        raise FileNotFoundError(f"Gen B: no se encontró el CSV depurado en {nombre_carpeta!r}")
    path = candidatos[0]

    df = pd.read_csv(
        path,
        dtype=str,
        usecols=["id", "clee", "codigo_act", "cve_mun", "sector_gestion", "alcance_analitico", "revision_manual"],
    )

    dup_id = df["id"].duplicated().sum()
    if dup_id:
        log.warning("%s: %d filas con id duplicado, se descartan", nombre_carpeta, dup_id)
        df = df.drop_duplicates(subset="id")

    cve_alc = _mapear_alcaldia_serie(df["cve_mun"], tipo="clave", contexto=nombre_carpeta)
    dominio, subcategoria, forzada = _mapear_scian(df["codigo_act"], contexto=nombre_carpeta)
    revision_manual = _bool_si_no(df["revision_manual"]) | forzada

    return pd.DataFrame(
        {
            "familia": "adultos_mayores_deporte",
            "generacion": "gen_b",
            "edicion": edicion_info.edicion,
            "edicion_verificada": edicion_info.verificada,
            "cve_alc": cve_alc,
            "clee": df["clee"],
            "scian": df["codigo_act"],
            "dominio": dominio,
            "subcategoria": subcategoria,
            "sector": df["sector_gestion"],
            "alcance": df["alcance_analitico"],
            "revision_manual": revision_manual,
        }
    )


def leer_deporte_adultos_mayores(data_dir: Path) -> pd.DataFrame:
    """Unifica Gen A (5 carpetas, 2016-2021) + Gen B (5 carpetas, 2022-2026)
    en el esquema largo común. NOVIEMBRE 2019 no existe en esta familia (hueco
    real y esperado, no se rellena)."""
    partes = []
    for nombre in _GEN_A_FOLDERS:
        carpeta = data_dir / nombre
        if not carpeta.is_dir():
            raise FileNotFoundError(f"carpeta Gen A no encontrada: {carpeta}")
        partes.append(_leer_gen_a(carpeta))
    for nombre in _GEN_B_FOLDERS:
        carpeta = data_dir / nombre
        if not carpeta.is_dir():
            raise FileNotFoundError(f"carpeta Gen B no encontrada: {carpeta}")
        partes.append(_leer_gen_b(carpeta))

    resultado = pd.concat(partes, ignore_index=True)[_ESQUEMA_COLUMNAS]

    # Cada carpeta Gen A resuelve su edición de forma independiente (a partir
    # de su propio fuente.archivo, vía resolver_edicion_gen_a en _leer_gen_a),
    # así que si dos carpetas distintas resolvieran a "2020-11" sería una señal
    # de que el bug de metadatos se coló. Chequeo de forma agregada aquí.
    ediciones_gen_a = sorted(resultado.loc[resultado["generacion"] == "gen_a", "edicion"].unique())
    if len(ediciones_gen_a) != 5:
        log.warning("Gen A: se esperaban 5 ediciones distintas de carpeta, se obtuvieron %s", ediciones_gen_a)
    return resultado


def leer_salud(data_dir: Path) -> pd.DataFrame:
    """Las 11 carpetas `SALUD_CDMX_*`. `generacion` queda en None (no aplica
    el split Gen A/B a esta familia)."""
    carpetas = sorted(data_dir.glob(_SALUD_GLOB))
    if len(carpetas) != 11:
        log.warning("se esperaban 11 carpetas SALUD_CDMX_*, se encontraron %d: %s", len(carpetas), [c.name for c in carpetas])

    partes = []
    for carpeta in carpetas:
        nombre_carpeta = carpeta.name
        candidatos = sorted(carpeta.glob("denue_salud_cdmx_*.csv"))
        if not candidatos:
            raise FileNotFoundError(f"Salud: no se encontró el CSV principal en {nombre_carpeta!r}")
        path = candidatos[0]

        json_candidatos = sorted(carpeta.glob("reporte_calidad_salud_*.json"))
        fuente = None
        if json_candidatos:
            import json

            with json_candidatos[0].open(encoding="utf-8") as f:
                fuente = json.load(f).get("fuente", {})
        else:
            log.warning("%s: sin reporte_calidad JSON, edición cae al fallback por carpeta", nombre_carpeta)

        edicion_info = resolver_edicion_confiable(fuente, nombre_carpeta)

        df = pd.read_csv(
            path,
            dtype=str,
            usecols=["ID", "CLEE", "Código SCIAN", "Subcategoría", "Sector", "Alcance", "Revisión manual", "Alcaldía"],
        )

        dup_id = df["ID"].duplicated().sum()
        if dup_id:
            log.warning("%s: %d filas con ID duplicado, se descartan", nombre_carpeta, dup_id)
            df = df.drop_duplicates(subset="ID")

        cve_alc = _mapear_alcaldia_serie(df["Alcaldía"], tipo="nombre", contexto=nombre_carpeta)
        revision_manual = _bool_si_no(df["Revisión manual"])

        partes.append(
            pd.DataFrame(
                {
                    "familia": "salud",
                    "generacion": None,
                    "edicion": edicion_info.edicion,
                    "edicion_verificada": edicion_info.verificada,
                    "cve_alc": cve_alc,
                    "clee": df["CLEE"],
                    "scian": df["Código SCIAN"],
                    "dominio": "salud",
                    "subcategoria": df["Subcategoría"],
                    "sector": df["Sector"],
                    "alcance": df["Alcance"],
                    "revision_manual": revision_manual,
                }
            )
        )

    return pd.concat(partes, ignore_index=True)[_ESQUEMA_COLUMNAS]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("=== leer_deporte_adultos_mayores ===")
    am = leer_deporte_adultos_mayores(data_dir)
    print(am.groupby(["generacion", "edicion", "edicion_verificada"]).size())

    print()
    print("=== Chequeo Gen A: 2020-11 solo debe venir de NOVIEMBRE 2020 CDMX ===")
    # Se reconstruye la validación por carpeta para dar un mensaje inequívoco.
    from ..catalogo import CLAVES_VALIDAS

    assert set(am["cve_alc"].dropna().unique()) <= CLAVES_VALIDAS, "hay cve_alc fuera de las 16 claves válidas"
    ediciones_gen_a = am.loc[am["generacion"] == "gen_a", "edicion"].unique()
    print("ediciones Gen A distintas:", sorted(ediciones_gen_a))
    assert len(ediciones_gen_a) == 5, f"se esperaban 5 ediciones Gen A distintas, hay {len(ediciones_gen_a)}"

    out_am = processed_dir / "adultos_mayores.csv"
    am.to_csv(out_am, index=False)
    print(f"escrito {out_am} ({len(am)} filas)")

    print()
    print("=== leer_salud ===")
    salud = leer_salud(data_dir)
    print(salud.groupby(["edicion", "edicion_verificada"]).size())
    assert set(salud["cve_alc"].dropna().unique()) <= CLAVES_VALIDAS, "hay cve_alc fuera de las 16 claves válidas"

    out_salud = processed_dir / "salud.csv"
    salud.to_csv(out_salud, index=False)
    print(f"escrito {out_salud} ({len(salud)} filas)")
