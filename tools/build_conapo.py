"""Proyecciones CONAPO por municipio (CDMX) → data/interim/ en formato tidy.

Entrada: data/processed/conapo/pobproy_quinq1.csv (CONAPO, "Población a mitad de año por
municipio y grupos quinquenales de edad, 1990-2040", datos.gob.mx; conciliada con las
proyecciones estatales 2020-2070, base Censo 2020). Formato ancho por grupo quinquenal.

Salidas (data/interim/):
- conapo_mun_quinq.parquet: `cve_mun`, `anio`, `sexo` (hombres|mujeres), `edad` (grupo
  quinquenal, p. ej. '00_04', '85_mm'), `poblacion`. Solo entidad 09.
- conapo_mun_0a14.parquet: `cve_mun`, `anio`, `pob_0a14` (ambos sexos), `pob_total`.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "data" / "processed" / "conapo" / "pobproy_quinq1.csv"
INTERIM = RAIZ / "data" / "interim"


def main() -> None:
    con = duckdb.connect()
    # quote explícito: hay nombres de municipio con comas entre comillas
    con.sql(
        f"""CREATE TABLE crudo AS SELECT * FROM read_csv('{ORIGEN}', header=true, quote='"', all_varchar=true)
        WHERE CLAVE_ENT = '9'"""
    )
    cols_edad = [c for (c,) in con.sql("SELECT column_name FROM (DESCRIBE crudo) WHERE column_name LIKE 'POB\\_%' ESCAPE '\\' AND column_name <> 'POB_TOTAL'").fetchall()]
    union = " UNION ALL ".join(
        f"SELECT CLAVE, ANO, SEXO, '{c.removeprefix('POB_').replace('010_014', '10_14').replace('015_019', '15_19')}' AS edad, "
        f"CAST({c} AS BIGINT) AS poblacion FROM crudo"
        for c in cols_edad
    )
    con.sql(
        f"""CREATE TABLE tidy AS SELECT lpad(substr(CLAVE, 2), 3, '0') AS cve_mun, CAST(ANO AS INTEGER) AS anio,
        lower(SEXO) AS sexo, edad, poblacion FROM ({union})"""
    )
    n_mun, amin, amax = con.sql("SELECT count(DISTINCT cve_mun), min(anio), max(anio) FROM tidy").fetchone()
    if n_mun != 16:
        raise ValueError(f"CONAPO: se esperaban 16 alcaldías, hay {n_mun}")
    # consistencia: suma de grupos = POB_TOTAL publicado
    dif = con.sql(
        """SELECT count(*) FROM (SELECT CLAVE, ANO, SEXO, CAST(POB_TOTAL AS BIGINT) t FROM crudo) a
        JOIN (SELECT lpad(substr(CLAVE,2),3,'0') m, CLAVE, ANO, SEXO FROM crudo) USING (CLAVE, ANO, SEXO)
        JOIN (SELECT cve_mun, anio, sexo, sum(poblacion) s FROM tidy GROUP BY ALL) b
          ON b.cve_mun = m AND b.anio = CAST(ANO AS INTEGER) AND b.sexo = lower(SEXO) WHERE s <> t"""
    ).fetchone()[0]
    if dif:
        raise ValueError(f"CONAPO: {dif} filas donde la suma de grupos ≠ POB_TOTAL")
    con.sql(f"COPY (SELECT * FROM tidy ORDER BY ALL) TO '{INTERIM / 'conapo_mun_quinq.parquet'}' (FORMAT parquet)")
    con.sql(
        f"""COPY (SELECT cve_mun, anio, sum(poblacion) FILTER (WHERE edad IN ('00_04','05_09','10_14')) AS pob_0a14,
        sum(poblacion) AS pob_total FROM tidy GROUP BY ALL ORDER BY ALL) TO '{INTERIM / 'conapo_mun_0a14.parquet'}' (FORMAT parquet)"""
    )
    print(f"conapo: 16 alcaldías, {amin}-{amax}")


if __name__ == "__main__":
    main()
