"""Panel AGEB x corte, capas de demanda y oferta (plan `backend_plan.md` §4).

Este módulo construye las dos tablas intermedias que alimentan `modelos.py`:

- `construir_panel_demanda`: una fila por AGEB del universo (2,453), con la
  población 0-14 del censo 2010 y 2020 y el tratamiento geográfico del
  traslape 2010 → 2020 (`docs/metodologia.md` §5).
- `construir_panel_oferta`: formato largo AGEB x corte (3 cortes DENUE
  `Principal`, `docs/metodologia.md` §6), con ceros explícitos.
- `reporte_cobertura`: conteos agregados de ambas capas para el log del
  pipeline y el backtest (plan §4).

Ninguna función de este módulo lee `data/` directamente: reciben los marcos
ya cargados por `io.py`, para poder probarlas con fixtures sintéticas
(`backend/tests/conftest.py`).
"""

from __future__ import annotations

import pandas as pd

from chipos.io import CORTES_OFERTA

# ---------------------------------------------------------------------------
# Demanda (B3)
# ---------------------------------------------------------------------------

# `motivo_sin_datos` posibles (plan §4.1 / metodología §8). `sin_poligono`
# (2 claves censales 2020 sin polígono) y `sin_censo` (AGEB urbana del
# universo sin ninguna fila censal) no ocurren hoy con los datos reales
# (verificado: las 2,431 claves urbanas del universo tienen exactamente una
# fila en `equivalencia_ageb_2010_2020.parquet` y en el censo 2020); quedan
# como ramas defensivas y como valores válidos del contrato. `sin_poligono`
# en particular se refiere a claves que *no* están en el universo de
# polígonos, por lo que nunca puede aparecer como fila de este panel (que
# parte del universo); esas 2 claves quedan documentadas en
# `docs/perfil_datos.md` (no se recalculan aquí porque `reporte_cobertura`
# solo recibe los paneles ya construidos, no el censo crudo).
MOTIVOS_SIN_DATOS: tuple[str, ...] = (
    "rural",
    "suprimido_inegi",
    "d2020_menor_20",
    "sin_poligono",
    "sin_censo",
)

# Umbral de supresión de `D_2020` (metodología §8; CLAUDE.md "Decisiones
# vigentes"): por debajo de 20 niños, el conteo censal es demasiado ruidoso
# para tasas y se marca `sin_datos` en vez de modelarlo.
_D2020_MINIMO = 20


def construir_panel_demanda(
    censo: pd.DataFrame, equivalencia: pd.DataFrame, universo: pd.DataFrame
) -> pd.DataFrame:
    """Panel de demanda: una fila por AGEB del universo (2,453).

    Columnas: `cvegeo, cve_mun, ambito, relacion, d_2010, d_2020,
    motivo_sin_datos`.

    - `d_2020` = `pob_0a14` del censo 2020 para la misma clave (AGEB rural:
      `NaN`, no hay censo urbano de rurales).
    - `d_2010` = `pob_0a14` del censo 2010 para la clave `cvegeo_2010` que
      la equivalencia 2010→2020 asocia a este AGEB (columna
      `equivalencia.cvegeo_2010`; para `relacion == "misma"` coincide con la
      propia clave). Este mismo criterio cubre el caso `division`: la
      decisión del equipo (`docs/metodologia.md` §5, "división: hereda la
      tasa de la madre") es que la hija use el `D_2010` **completo** de la
      madre, sin reescalarlo por `frac_de_2010` — que es exactamente lo que
      produce esta unión, porque nunca se multiplica por `frac_de_2010`.
    - `relacion` viene de `equivalencia.relacion` (`misma`, `division`,
      `fusion_o_expansion`, `cambio_limites`); `None` en AGEB rural;
      `"sin_contraparte"` si una AGEB urbana no tiene fila de equivalencia
      (no ocurre hoy, ver `MOTIVOS_SIN_DATOS`; rama defensiva).
    - `motivo_sin_datos`: `rural` (ambito rural); `sin_censo` (urbana sin
      ninguna fila en el censo 2020); `suprimido_inegi` (fila censal con
      `pob_0a14` nulo, 41 AGEB 2020); `d2020_menor_20` (`D_2020 < 20`, 23
      AGEB); `None` si hay dato utilizable. El tope de confianza por
      `relacion` (`media` si no es `misma`; `baja`/`n_obs=1` si
      `sin_contraparte`) se aplica en `modelos.py` (B6), no aquí.
    """
    censo_2010 = (
        censo.loc[censo["anio"] == 2010, ["cvegeo", "pob_0a14"]]
        .rename(columns={"cvegeo": "cvegeo_2010", "pob_0a14": "d_2010"})
    )
    censo_2020 = (
        censo.loc[censo["anio"] == 2020, ["cvegeo", "pob_0a14"]]
        .rename(columns={"pob_0a14": "d_2020"})
    )

    panel = universo[["cvegeo", "cve_mun", "ambito"]].copy()

    panel = panel.merge(
        censo_2020, on="cvegeo", how="left", indicator="_tiene_censo_2020"
    )
    panel = panel.merge(
        equivalencia[["cvegeo", "cvegeo_2010", "relacion"]], on="cvegeo", how="left"
    )
    panel = panel.merge(censo_2010, on="cvegeo_2010", how="left")

    es_rural = panel["ambito"] == "rural"
    es_urbano = ~es_rural

    panel.loc[es_rural, "relacion"] = None
    sin_contraparte = es_urbano & panel["relacion"].isna()
    panel.loc[sin_contraparte, "relacion"] = "sin_contraparte"
    panel.loc[sin_contraparte, "d_2010"] = pd.NA

    motivo = pd.Series(pd.NA, index=panel.index, dtype=object)
    motivo[es_rural] = "rural"

    sin_censo = es_urbano & (panel["_tiene_censo_2020"] == "left_only")
    motivo[sin_censo] = "sin_censo"

    suprimido = (
        es_urbano
        & (panel["_tiene_censo_2020"] == "both")
        & panel["d_2020"].isna()
    )
    motivo[suprimido] = "suprimido_inegi"

    menor_20 = es_urbano & panel["d_2020"].notna() & (panel["d_2020"] < _D2020_MINIMO)
    motivo[menor_20] = "d2020_menor_20"

    panel["motivo_sin_datos"] = motivo

    columnas = [
        "cvegeo",
        "cve_mun",
        "ambito",
        "relacion",
        "d_2010",
        "d_2020",
        "motivo_sin_datos",
    ]
    return (
        panel[columnas]
        .sort_values("cvegeo")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Oferta (B4)
# ---------------------------------------------------------------------------

# Verificación de catálogo SCIAN (plan §4.3, problema M1): con datos reales
# (`data/processed/infancias/`, `Alcance = 'Principal'`), los 14 códigos
# SCIAN presentes en los 3 cortes de oferta (2016-10, 2019-11, 2024-11) son
# exactamente los mismos en las tres ediciones (611111, 611112, 611121,
# 611122, 611131, 611132, 611141, 611142, 611171, 611172, 611181, 611182,
# 624411, 624412); ninguno aparece o desaparece del catálogo entre cortes
# (totales de registros `Principal` por corte: 8,886 / 8,321 / 7,309, caída
# consistente con el cierre real documentado en CLAUDE.md, no con un cambio
# de catálogo SCIAN). Decisión: no se excluye ningún código SCIAN de la capa
# de oferta. `docs/metodologia.md` §6 registrará esta decisión en B12; aquí
# solo se documenta y el conteo se puede reproducir con
# `denue.loc[denue["alcance"] == "Principal"].groupby(["edicion", "scian"]).size()`.


def construir_panel_oferta(
    denue: pd.DataFrame,
    universo: pd.DataFrame,
    cortes: dict[str, float] = CORTES_OFERTA,
) -> pd.DataFrame:
    """Panel de oferta, formato largo: `cvegeo, cve_mun, t, s, s_2024`.

    `s` = número de `ID` distintos con `alcance == "Principal"` por AGEB
    urbana y corte (uno de `cortes.values()`, por defecto `CORTES_OFERTA`).
    `s_2024` repite, en todas las filas de un mismo AGEB, el valor de `s`
    del corte más reciente (`max(cortes.values())`), para que `features.py`
    calcule la brecha `S_2024 / D_2020` sin tener que volver a filtrar.

    Filtros (plan §4.3 / problema M2, claves fuera de CDMX con coordenadas
    marcadas como válidas): clave de 13 caracteres, prefijo `"09"`,
    `cve_mun` en `002`-`017`, y presente en el universo urbano. Las AGEB
    urbanas sin ningún establecimiento en un corte quedan con `s = 0`
    explícito (nunca se omite la fila); las claves rurales/sin polígono se
    cuentan en `reporte_cobertura`, no aparecen en esta tabla.
    """
    urbano = universo.loc[universo["ambito"] == "urbano", ["cvegeo", "cve_mun"]]
    claves_urbanas = set(urbano["cvegeo"])
    cortes_t = sorted(set(cortes.values()))

    principal = denue.loc[denue["alcance"] == "Principal"].copy()
    principal = principal[
        (principal["cvegeo"].str.len() == 13)
        & (principal["cvegeo"].str.slice(0, 2) == "09")
        & principal["cve_mun"].between("002", "017")
        & principal["cvegeo"].isin(claves_urbanas)
        & principal["t"].isin(cortes_t)
    ]

    conteos = (
        principal.groupby(["cvegeo", "t"])["id"]
        .nunique()
        .rename("s")
        .reset_index()
    )

    malla = urbano.merge(pd.DataFrame({"t": cortes_t}), how="cross")
    panel = malla.merge(conteos, on=["cvegeo", "t"], how="left")
    panel["s"] = panel["s"].fillna(0).astype(int)

    if panel.duplicated(["cvegeo", "t"]).any():
        raise ValueError(
            "cvegeo duplicado por corte en el panel de oferta (no debería "
            "ocurrir: la malla es producto cartesiano AGEB x corte)."
        )

    ultimo_corte = max(cortes_t)
    s_2024 = panel.loc[panel["t"] == ultimo_corte, ["cvegeo", "s"]].rename(
        columns={"s": "s_2024"}
    )
    panel = panel.merge(s_2024, on="cvegeo", how="left")

    return (
        panel[["cvegeo", "cve_mun", "t", "s", "s_2024"]]
        .sort_values(["cvegeo", "t"])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Reporte de cobertura (B4)
# ---------------------------------------------------------------------------


def reporte_cobertura(
    panel_d: pd.DataFrame, panel_o: pd.DataFrame, universo: pd.DataFrame
) -> dict:
    """Conteos agregados de ambas capas, para el log del pipeline y el backtest.

    No recalcula nada fuera de lo ya contenido en `panel_d`/`panel_o`
    (firma fija, plan §4): las 2 claves censales sin polígono y otros
    hechos que dependen del censo crudo ya están documentados en
    `docs/perfil_datos.md` y no se repiten aquí.
    """
    urbano = universo.loc[universo["ambito"] == "urbano"]

    motivo_counts = (
        panel_d["motivo_sin_datos"].value_counts(dropna=True).astype(int).to_dict()
    )
    n_con_dato = int(panel_d["motivo_sin_datos"].isna().sum())

    relacion_counts = (
        panel_d.loc[panel_d["ambito"] == "urbano", "relacion"]
        .value_counts(dropna=True)
        .astype(int)
        .to_dict()
    )

    total_por_corte = {
        float(t): int(s) for t, s in panel_o.groupby("t")["s"].sum().items()
    }
    ageb_sin_oferta_ningun_corte = int(
        panel_o.groupby("cvegeo")["s"].sum().eq(0).sum()
    )

    return {
        "universo_total": int(len(universo)),
        "universo_urbano": int(len(urbano)),
        "universo_rural": int(len(universo) - len(urbano)),
        "demanda_motivo_sin_datos": motivo_counts,
        "demanda_n_con_dato": n_con_dato,
        "demanda_relacion": relacion_counts,
        "oferta_total_principal_por_corte": total_por_corte,
        "oferta_ageb_sin_establecimientos_en_ningun_corte": ageb_sin_oferta_ningun_corte,
    }
