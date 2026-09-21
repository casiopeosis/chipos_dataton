"""Panel censal oficial por AGEB urbana, 2010 y 2020 (INEGI RESAGEBURB) → data/interim/.

Entradas (data/processed/censo/):
- inegi_2010/resultados_ageb_urbana_09_cpv2010.csv
- inegi_2020/conjunto_de_datos_ageb_urbana_09_cpv2020.csv

Salidas (data/interim/):
- censo_ageb_2010.parquet, censo_ageb_2020.parquet: una fila por AGEB urbana (MZA = '000',
  AGEB ≠ '0000'); `cvegeo` = '09' + MUN(3) + LOC(4) + AGEB(4) (13 caracteres).
- censo_ageb_panel.parquet: ambos años en formato largo.

Todas las filas son AGEB **urbanas**: INEGI no publica resultados por AGEB rural (la población
rural solo existe por localidad, ITER). Los valores '*' (confidencialidad) y 'N/D' → NULL; no se
imputan. `pob_0a14` = suma de grupos (NULL si alguno falta); `pob0_14_inegi` es la columna
POB0_14 publicada por INEGI, para contraste.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
CENSO = RAIZ / "data" / "processed" / "censo"
INTERIM = RAIZ / "data" / "interim"
ARCHIVOS = {
    2010: CENSO / "inegi_2010" / "resultados_ageb_urbana_09_cpv2010.csv",
    2020: CENSO / "inegi_2020" / "conjunto_de_datos_ageb_urbana_09_cpv2020.csv",
}
FECHA_LEVANTAMIENTO = {2010: 2010.44, 2020: 2020.20}  # fechas de referencia: 12-jun-2010 y 15-mar-2020
EDADES = ["p_0a2", "p_3a5", "p_6a11", "p_12a14", "p_15a17"]


def num(col: str) -> str:
    return f"TRY_CAST(NULLIF(NULLIF({col}, '*'), 'N/D') AS INTEGER)"


def construir(con: duckdb.DuckDBPyConnection, anio: int) -> None:
    edades = ", ".join(f"{num(e)} AS {e}" for e in EDADES)
    con.sql(
        f"""CREATE OR REPLACE TABLE c{anio} AS
        SELECT '09' || mun || loc || ageb AS cvegeo, {anio} AS anio, {FECHA_LEVANTAMIENTO[anio]} AS t,
               mun AS cve_mun, loc AS cve_loc, ageb AS cve_ageb, nom_mun, nom_loc,
               'urbano' AS ambito_censo,
               {num('pobtot')} AS pobtot, {edades},
               {num('pob0_14')} AS pob0_14_inegi
        FROM read_csv('{ARCHIVOS[anio]}', all_varchar=true, header=true, normalize_names=true)
        WHERE mza = '000' AND ageb <> '0000'"""
    )
    con.sql(f"ALTER TABLE c{anio} ADD COLUMN pob_0a14 INTEGER")
    con.sql(f"UPDATE c{anio} SET pob_0a14 = p_0a2 + p_3a5 + p_6a11 + p_12a14")
    n, dup, largo = con.sql(
        f"SELECT count(*), count(*) - count(DISTINCT cvegeo), bool_and(length(cvegeo) = 13) FROM c{anio}"
    ).fetchone()
    if dup or not largo:
        raise ValueError(f"{anio}: CVEGEO duplicado o de longitud distinta de 13")
    con.sql(f"COPY c{anio} TO '{INTERIM / f'censo_ageb_{anio}.parquet'}' (FORMAT parquet)")
    print(f"censo_ageb_{anio}.parquet: {n} AGEB urbanas")


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for anio in ARCHIVOS:
        construir(con, anio)
    con.sql(
        f"COPY (SELECT * FROM c2010 UNION ALL BY NAME SELECT * FROM c2020 ORDER BY cvegeo, anio) "
        f"TO '{INTERIM / 'censo_ageb_panel.parquet'}' (FORMAT parquet)"
    )


if __name__ == "__main__":
    main()
