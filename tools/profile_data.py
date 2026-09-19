"""Perfilado acotado de data/processed y data/reference.

Escribe docs/perfil_datos.md con, por archivo: filas, columnas, dtypes, % nulos,
cardinalidad, min/max y 2 filas de ejemplo. Nunca carga ni imprime datos completos:
todo se calcula con agregados SQL en DuckDB.

Familias DENUE (infancias, salud, comercios): la edición más reciente se perfila a
fondo; las demás solo por diferencias (filas, columnas, tipos, nulos).

Uso: python tools/profile_data.py
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
PROCESADOS = RAIZ / "data" / "processed"
REFERENCIA = RAIZ / "data" / "reference"
INTERIM = RAIZ / "data" / "interim"
SALIDA = RAIZ / "docs" / "perfil_datos.md"

MAX_JSON = 400_000_000  # bytes; los GeoJSON de comercios pesan ~60 MB
UMBRAL_TOP = 12  # cardinalidad máxima para listar valores frecuentes
UMBRAL_DELTA_NULOS = 2.0  # puntos porcentuales para reportar cambio de nulos
LARGO_VALOR = 28

NUMERICOS = ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "DOUBLE", "FLOAT", "DECIMAL")


def q(nombre: str) -> str:
    """Cita un identificador SQL."""
    return '"' + nombre.replace('"', '""') + '"'


def corto(valor, largo: int = LARGO_VALOR) -> str:
    texto = str(valor).replace("|", "/").replace("\n", " ")
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


def es_numerico(tipo: str) -> bool:
    return tipo.upper().startswith(NUMERICOS)


def es_fecha(tipo: str) -> bool:
    return tipo.upper().startswith(("DATE", "TIMESTAMP"))


def fuente_csv(ruta: Path) -> str:
    return f"read_csv_auto('{ruta}', sample_size=-1)"


def fuente_geojson_props(ruta: Path) -> str:
    """Relación con las properties de cada feature (sin geometría)."""
    return (
        f"(SELECT unnest(f.properties) FROM "
        f"(SELECT unnest(features) AS f FROM read_json('{ruta}', maximum_object_size={MAX_JSON})))"
    )


def esquema(con, fuente: str) -> list[tuple[str, str]]:
    return [(r[0], r[1]) for r in con.sql(f"DESCRIBE SELECT * FROM {fuente}").fetchall()]


def estadisticas(con, fuente: str, cols: list[tuple[str, str]]) -> dict:
    """Un solo escaneo: filas, nulos, distintos, min/max por columna."""
    exprs = ["count(*)"]
    for nombre, tipo in cols:
        c = q(nombre)
        exprs.append(f"count({c})")
        exprs.append(f"count(DISTINCT {c})")
        if es_numerico(tipo) or es_fecha(tipo):
            exprs += [f"min({c})", f"max({c})"]
        else:
            # cadena vacía cuenta como "vacío" (frecuente en DENUE)
            exprs += [f"sum(CASE WHEN trim(CAST({c} AS VARCHAR)) = '' THEN 1 ELSE 0 END)", "NULL"]
    fila = con.sql(f"SELECT {', '.join(exprs)} FROM {fuente}").fetchone()
    n = fila[0]
    res = {"filas": n, "cols": {}}
    for i, (nombre, tipo) in enumerate(cols):
        no_nulos, distintos, a, b = fila[1 + 4 * i : 5 + 4 * i]
        nulos = n - no_nulos
        d = {"tipo": tipo, "pct_nulo": 100 * nulos / n if n else 0, "distintos": distintos}
        if es_numerico(tipo) or es_fecha(tipo):
            d["min"], d["max"] = a, b
        else:
            d["pct_vacio"] = 100 * (a or 0) / n if n else 0
        res["cols"][nombre] = d
    return res


def top_valores(con, fuente: str, col: str, k: int = 4) -> str:
    filas = con.sql(
        f"SELECT {q(col)} AS v, count(*) AS n FROM {fuente} GROUP BY 1 ORDER BY 2 DESC LIMIT {k}"
    ).fetchall()
    return ", ".join(f"{corto(v, 22)} ({n})" for v, n in filas)


def ejemplos(con, fuente: str, cols: list[tuple[str, str]], n: int = 2) -> list[str]:
    """Filas de ejemplo compactas: solo campos no vacíos, truncados."""
    nombres = [c for c, _ in cols]
    filas = con.sql(f"SELECT * FROM {fuente} LIMIT {n}").fetchall()
    salida = []
    for fila in filas:
        partes = [f"{k}={corto(v, 20)}" for k, v in zip(nombres, fila) if v not in (None, "")]
        linea = "; ".join(partes)
        salida.append(corto(linea, 420))
    return salida


def tabla_columnas(con, fuente: str, est: dict, agrupar: set[str] | None = None) -> list[str]:
    agrupar = agrupar or set()
    lin = ["| columna | tipo | %nulo | %vacío | distintos | min | max / top |", "|---|---|---|---|---|---|---|"]
    grupo = []
    for nombre, d in est["cols"].items():
        if nombre in agrupar:
            grupo.append((nombre, d))
            continue
        vacio = f"{d['pct_vacio']:.1f}" if "pct_vacio" in d else ""
        if "min" in d:
            mn, mx = corto(d["min"]), corto(d["max"])
            if d["distintos"] <= 3 and es_numerico(d["tipo"]):
                mx = f"{mx} · {top_valores(con, fuente, nombre, 3)}"
        else:
            mn = ""
            mx = top_valores(con, fuente, nombre) if d["distintos"] <= UMBRAL_TOP else ""
        lin.append(
            f"| {nombre} | {d['tipo']} | {d['pct_nulo']:.1f} | {vacio} | {d['distintos']} | {mn} | {mx} |"
        )
    if grupo:
        mins = [g[1]["min"] for g in grupo if g[1].get("min") is not None]
        maxs = [g[1]["max"] for g in grupo if g[1].get("max") is not None]
        nul = [g[1]["pct_nulo"] for g in grupo]
        lin.append(
            f"| *{len(grupo)} cols agrupadas* ({grupo[0][0]} … {grupo[-1][0]}) | "
            f"{grupo[0][1]['tipo']} | {min(nul):.1f}–{max(nul):.1f} | | | {min(mins)} | {max(maxs)} |"
        )
    return lin


def perfil_completo(con, titulo: str, fuente: str, agrupar: set[str] | None = None) -> tuple[list[str], dict]:
    cols = esquema(con, fuente)
    est = estadisticas(con, fuente, cols)
    lin = [f"### {titulo}", f"Filas: **{est['filas']:,}** · Columnas: **{len(cols)}**", ""]
    lin += tabla_columnas(con, fuente, est, agrupar)
    lin += ["", "Ejemplos (campos no vacíos, truncados):"]
    lin += [f"- `{e}`" for e in ejemplos(con, fuente, cols)]
    lin.append("")
    return lin, est


def diferencias(ref: dict, est: dict) -> str:
    """Resume en una celda las diferencias de esquema/nulos respecto a la referencia."""
    rc, ec = ref["cols"], est["cols"]
    notas = []
    faltan = [c for c in rc if c not in ec]
    sobran = [c for c in ec if c not in rc]
    if faltan:
        notas.append("faltan: " + ", ".join(faltan))
    if sobran:
        notas.append("añadidas: " + ", ".join(sobran))
    tipos = [f"{c} {rc[c]['tipo']}→{ec[c]['tipo']}" for c in rc if c in ec and rc[c]["tipo"] != ec[c]["tipo"]]
    if tipos:
        notas.append("tipo: " + ", ".join(tipos))
    nul = []
    for c in rc:
        if c not in ec:
            continue
        a = rc[c]["pct_nulo"] + rc[c].get("pct_vacio", 0)
        b = ec[c]["pct_nulo"] + ec[c].get("pct_vacio", 0)
        if abs(b - a) >= UMBRAL_DELTA_NULOS:
            nul.append(f"{c} {b:.0f}% (ref {a:.0f}%)")
    if nul:
        notas.append("nulo/vacío: " + ", ".join(nul))
    return "; ".join(notas) or "sin cambios de esquema"


def edicion_de(ruta: Path) -> str:
    m = re.search(r"(\d{4})_(\d{2})", ruta.name)
    return f"{m.group(1)}-{m.group(2)}" if m else ruta.stem


def perfil_familia(con, nombre: str, archivos: list[Path], geo: bool, clave_ageb: str) -> list[str]:
    archivos = sorted(archivos)
    ref_ruta = archivos[-1]
    fuente = (fuente_geojson_props if geo else fuente_csv)(ref_ruta)
    lin = [f"## Familia `{nombre}` ({len(archivos)} ediciones)", ""]
    sub, ref = perfil_completo(con, f"Referencia: `{ref_ruta.name}`", fuente)
    lin += sub
    if geo:
        lin += geo_puntos(con, ref_ruta)
    lin += [
        "### Diferencias por edición (vs referencia)",
        f"| edición | filas | Δ filas vs anterior | {clave_ageb} distintos | diferencias |",
        "|---|---|---|---|---|",
    ]
    previo = None
    for ruta in archivos:
        f = (fuente_geojson_props if geo else fuente_csv)(ruta)
        est = ref if ruta == ref_ruta else estadisticas(con, f, esquema(con, f))
        filas = est["filas"]
        delta = "" if previo is None else f"{100 * (filas - previo) / previo:+.1f}%"
        ageb = est["cols"].get(clave_ageb, {}).get("distintos", "—")
        nota = "(referencia)" if ruta == ref_ruta else diferencias(ref, est)
        lin.append(f"| {edicion_de(ruta)} | {filas:,} | {delta} | {ageb} | {corto(nota, 600)} |")
        previo = filas
    lin.append("")
    return lin


def geo_puntos(con, ruta: Path) -> list[str]:
    """Tipos de geometría y bbox de un GeoJSON de puntos, sin materializar geometrías."""
    base = f"(SELECT unnest(features) AS f FROM read_json('{ruta}', maximum_object_size={MAX_JSON}))"
    fila = con.sql(
        f"SELECT string_agg(DISTINCT f.geometry.type, ','), "
        f"min(f.geometry.coordinates[1]), min(f.geometry.coordinates[2]), "
        f"max(f.geometry.coordinates[1]), max(f.geometry.coordinates[2]) FROM {base}"
    ).fetchone()
    return [f"Geometría: {fila[0]} · bbox [{fila[1]:.4f}, {fila[2]:.4f}, {fila[3]:.4f}, {fila[4]:.4f}]", ""]


def _recorrer(coords, acc):
    if coords and isinstance(coords[0], (int, float)):
        acc[0] = min(acc[0], coords[0]); acc[1] = min(acc[1], coords[1])
        acc[2] = max(acc[2], coords[0]); acc[3] = max(acc[3], coords[1])
    else:
        for c in coords:
            _recorrer(c, acc)


def perfil_geojson_simple(ruta: Path) -> list[str]:
    """GeoJSON de polígonos: conteo, tipos de geometría, bbox, CRS y properties del 1er feature."""
    with open(ruta, encoding="utf-8") as fh:
        datos = json.load(fh)
    feats = datos.get("features", [])
    tipos: dict[str, int] = {}
    acc = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    sin_geom = 0
    for ft in feats:
        g = ft.get("geometry")
        if not g:
            sin_geom += 1
            continue
        tipos[g["type"]] = tipos.get(g["type"], 0) + 1
        _recorrer(g["coordinates"], acc)
    crs = datos.get("crs", {}).get("properties", {}).get("name", "no declarado (RFC 7946 ⇒ WGS84)")
    props = feats[0]["properties"] if feats else {}
    claves = sorted({k for ft in feats for k in (ft.get("properties") or {})})
    return [
        f"### `{ruta.relative_to(RAIZ)}`",
        f"Features: **{len(feats):,}** · sin geometría: {sin_geom} · tipos: {tipos} · CRS: {crs}",
        f"bbox: [{acc[0]:.4f}, {acc[1]:.4f}, {acc[2]:.4f}, {acc[3]:.4f}]",
        f"Claves de properties ({len(claves)}): {', '.join(claves)}",
        f"1er feature: `{corto(json.dumps(props, ensure_ascii=False), 400)}`",
        "",
    ]


def perfil_censo(con) -> list[str]:
    """Censo oficial 2010/2020, contraste con el xlsx, CONAPO y geometría (parquet de `make datos`)."""
    r = {a: INTERIM / f"censo_ageb_{a}.parquet" for a in (2010, 2020)}
    x = {a: INTERIM / f"censo_xlsx_ageb_{a}.parquet" for a in (2010, 2020)}
    conapo = INTERIM / "conapo_mun_0a14.parquet"
    eq = INTERIM / "equivalencia_ageb_2010_2020.parquet"
    geo = REFERENCIA / "ageb_cdmx.geojson"
    requeridos = [*r.values(), *x.values(), conapo, eq, geo]
    if not all(p.exists() for p in requeridos):
        return ["## Censo, CONAPO y marco", "- Faltan derivados: ejecutar `make datos`.", ""]
    lin = [
        "## Censo por AGEB urbana (INEGI RESAGEBURB 2010 y 2020, `data/processed/censo/inegi_*`)",
        "Filas AGEB = `MZA = '000'` y `AGEB <> '0000'`; `cvegeo` = '09'+MUN+LOC+AGEB. '*' y 'N/D' → NULL.",
        "Columnas usadas: POBTOT, P_0A2, P_3A5, P_6A11, P_12A14, P_15A17, POB0_14 (198 cols en 2010, 230 en 2020).",
        "",
        "| año | AGEB | alcaldías | pob. total | pob. 0–14 | 0–14 suprimido | suma grupos ≠ POB0_14 |",
        "|---|---|---|---|---|---|---|",
    ]
    for a, ruta in r.items():
        f = con.sql(
            f"SELECT count(*), count(DISTINCT cve_mun), sum(pobtot), sum(pob_0a14), count(*) FILTER (WHERE pob_0a14 IS NULL), "
            f"count(*) FILTER (WHERE pob_0a14 <> pob0_14_inegi) FROM '{ruta}'"
        ).fetchone()
        lin.append(f"| {a} | {f[0]:,} | {f[1]} | {f[2]:,} | {f[3]:,} | {f[4]} | {f[5]} |")
    par = con.sql(
        f"SELECT count(*) FILTER (WHERE b.cvegeo IS NOT NULL), count(*) FILTER (WHERE b.cvegeo IS NULL), "
        f"(SELECT count(*) FROM '{r[2010]}' WHERE cvegeo NOT IN (SELECT cvegeo FROM '{r[2020]}')) "
        f"FROM '{r[2020]}' a LEFT JOIN '{r[2010]}' b USING (cvegeo)"
    ).fetchone()
    dif = con.sql(
        f"""SELECT max(abs(o.p / x.p - 1)) * 100, count(*) FILTER (WHERE x.p IS NULL OR abs(o.p / x.p - 1) >= 0.01) FROM
        (SELECT cve_mun, sum(pob_0a14) p FROM '{r[2020]}' GROUP BY 1) o LEFT JOIN
        (SELECT cve_mun, sum(p_0a2 + p_3a5 + p_6a11 + p_12a14) p FROM '{x[2020]}' GROUP BY 1) x USING (cve_mun)"""
    ).fetchone()
    ref = sorted((PROCESADOS / "infancias").glob("*.csv"))[-1]
    denue = f"(SELECT DISTINCT \"Clave geográfica AGEB\" AS k FROM read_csv_auto('{ref}') WHERE \"Alcance\" = 'Principal')"
    m = con.sql(
        f"SELECT count(*), avg((k IN (SELECT cvegeo FROM '{r[2020]}'))::INT), avg((k IN (SELECT cvegeo FROM '{r[2010]}'))::INT) FROM {denue}"
    ).fetchone()
    lin += [
        "",
        f"- Pareo por CVEGEO 2010↔2020: {par[0]:,} en ambos, {par[1]} solo 2020, {par[2]} solo 2010.",
        f"- xlsx 2020 vs oficial (0–14 por alcaldía): diferencia máx. {dif[0]:.2f} %, alcaldías con ≥ 1 %: {dif[1]}. "
        "El xlsx 2010 está truncado (superseded, ver data_manifest).",
        f"- Claves DENUE `{ref.name}` (Principal, {m[0]:,}): {100 * m[1]:.1f} % en censo 2020, {100 * m[2]:.1f} % en 2010.",
        "",
        "## CONAPO municipal (`data/processed/conapo/pobproy_quinq1.csv`)",
    ]
    c = con.sql(
        f"""SELECT count(DISTINCT m.cve_mun), min(m.anio), max(m.anio),
        string_agg(m.cve_mun || ' ' || round(100 * (m.pob_0a14 / c.p - 1), 1)::VARCHAR || '%', ', ' ORDER BY m.cve_mun)
          FILTER (WHERE abs(m.pob_0a14 / c.p - 1) > 0.05)
        FROM '{conapo}' m LEFT JOIN (SELECT cve_mun, sum(pob_0a14) p FROM '{r[2020]}' GROUP BY 1) c
          ON c.cve_mun = m.cve_mun AND m.anio = 2020"""
    ).fetchone()
    lin += [
        "Población a mitad de año por municipio, sexo y grupo quinquenal (0-4 … 85+), 1990–2040; ancho → tidy.",
        f"- {c[0]} alcaldías, {c[1]}–{c[2]}. 0–14 = 00_04 + 05_09 + 10_14 (coincide con el censo).",
        f"- CONAPO 2020 vs Σ AGEB urbanas 2020 (0–14), desvíos > 5 %: {c[3] or 'ninguno'}.",
        "",
        "## Marco Geoestadístico → `data/reference/ageb_cdmx*.geojson`",
    ]
    g = con.sql(
        f"""SELECT count(*), count(*) FILTER (WHERE f.properties.ambito = 'urbano'), count(*) FILTER (WHERE f.properties.ambito = 'rural')
        FROM (SELECT unnest(features) f FROM read_json('{geo}', maximum_object_size=100000000))"""
    ).fetchone()
    cls = con.sql(f"SELECT string_agg(relacion || ' ' || n, ', ' ORDER BY n DESC) FROM (SELECT relacion, count(*) n FROM '{eq}' GROUP BY 1)").fetchone()[0]
    tam = {p.name: p.stat().st_size / 1e6 for p in REFERENCIA.glob("ageb_cdmx*.geojson")}
    lin += [
        f"- MG 2020 (censal): {g[0]:,} AGEB ({g[1]:,} urbanas, {g[2]} rurales; CVEGEO rural de 9 caracteres). "
        f"Tamaños: {', '.join(f'{k} {v:.2f} MB' for k, v in sorted(tam.items()))}.",
        f"- Equivalencia AGEB urbanas 2020 → 2010 (MG 2010 v5.0, traslape de áreas): {cls}.",
        "",
    ]
    return lin


def main() -> None:
    con = duckdb.connect()
    lin = [
        "# Perfil de datos",
        "",
        f"Generado por `tools/profile_data.py` el {dt.date.today().isoformat()}. No editar a mano; "
        "regenerar con `python tools/profile_data.py`.",
        "%vacío = cadenas vacías (distinto de NULL). En columnas numéricas binarias se muestran los valores.",
        "",
        "## Inventario (por carpeta)",
        "| carpeta | archivos | MB total | ejemplo |",
        "|---|---|---|---|",
    ]
    grupos: dict[Path, list[Path]] = {}
    for ruta in sorted(list(PROCESADOS.rglob("*.*")) + list(REFERENCIA.rglob("*.*"))):
        if not ruta.name.startswith("."):
            grupos.setdefault(ruta.parent, []).append(ruta)
    for carpeta, rutas in grupos.items():
        mb = sum(r.stat().st_size for r in rutas) / 1e6
        ejemplo = rutas[-1].name if len(rutas) > 1 else ""
        nombres = ", ".join(r.name for r in rutas) if len(rutas) <= 3 else f"{len(rutas)} ediciones, p. ej. {ejemplo}"
        lin.append(f"| {carpeta.relative_to(RAIZ)} | {len(rutas)} | {mb:.1f} | {nombres} |")
    lin.append("")

    lin += perfil_familia(con, "infancias", list((PROCESADOS / "infancias").glob("*.csv")), False, "Clave geográfica AGEB")
    lin += perfil_familia(con, "salud", list((PROCESADOS / "salud").glob("*.csv")), False, "Clave geográfica AGEB")
    lin += perfil_familia(con, "comercios", list((PROCESADOS / "comercios").glob("*.geojson")), True, "cve_geo_ageb")

    lin += ["## Covariables estáticas y encuesta", ""]
    enut = PROCESADOS / "enut" / "enut_2024_cdmx_uso_tiempo.csv"
    cols_enut = [c for c, _ in esquema(con, fuente_csv(enut))]
    horas = set(cols_enut[cols_enut.index("activ_prod_con_cp") : cols_enut.index("activ_conviv") + 1])
    sub, _ = perfil_completo(con, f"`{enut.relative_to(RAIZ)}`", fuente_csv(enut), agrupar=horas)
    lin += sub
    for ruta in sorted((PROCESADOS / "areas_verdes").glob("*.csv")):
        sub, _ = perfil_completo(con, f"`{ruta.relative_to(RAIZ)}`", fuente_csv(ruta))
        lin += sub
    for ruta in sorted(list((PROCESADOS / "areas_verdes").glob("*.geojson")) + list((PROCESADOS / "espacios_publicos").glob("*.geojson"))):
        lin += perfil_geojson_simple(ruta)

    lin += perfil_censo(con)

    lin += ["## Referencia", ""]
    for ruta in sorted(REFERENCIA.glob("*.csv")):
        sub, _ = perfil_completo(con, f"`{ruta.relative_to(RAIZ)}`", fuente_csv(ruta))
        lin += sub
    for ruta in sorted(REFERENCIA.glob("*.geojson")):
        lin += perfil_geojson_simple(ruta)
    lin += [
        "### Brecha",
        "- `data/reference/ageb_cdmx.geojson` **no existe**: no hay geometría AGEB (ver docs/problemas_datos.md).",
        "",
    ]

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(lin), encoding="utf-8")
    print(f"{SALIDA.relative_to(RAIZ)}: {len(lin)} líneas")


if __name__ == "__main__":
    main()
