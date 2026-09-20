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
# para tasas y se marca `sin_datos` en vez de modelarlo. Se aplica igual a
# cada segmento (Fase 4): un segmento con pocos casos es igual de ruidoso.
_D2020_MINIMO = 20

# Segmentos de población objetivo (metodología §1.1, Fase 4 de
# `correccion/action_plan.md`): columnas del censo (`tools/build_censo.py`,
# ya en disco, sin fuente nueva) que se suman para cada uno. `todas` (0-17)
# es el valor por omisión del selector (action_plan.md #24) -- NO es
# `total`/0-14: Habitancia ya no tiene como alcance "infancias 0-14".
COLUMNAS_SEGMENTO: dict[str, tuple[str, ...]] = {
    "todas": ("p_0a2", "p_3a5", "p_6a11", "p_12a14", "p_15a17"),
    "primera_infancia": ("p_0a2",),
    "preescolar": ("p_3a5",),
    "primaria": ("p_6a11",),
    "secundaria": ("p_12a14",),
    "adolescencia": ("p_15a17",),
    # Alias transitorio, SOLO para no cambiar lo que `exportar.py` ya emite en el
    # contrato v1.2 (0-14) hasta que la Fase 6 haga el salto a v1.4 en un único bloque
    # (`plans/backend_plan.md` §9.2: "no tocar exportar.py/validar_contrato tres veces").
    # Reproduce exactamente `pob_0a14` (idéntico a la suma de estas 4 bandas, verificado
    # en `test_io.py`). No es uno de los 6 segmentos de Habitancia: se excluye de
    # `SEGMENTOS_DEMANDA` y se retira en la Fase 6.
    "total_0a14": ("p_0a2", "p_3a5", "p_6a11", "p_12a14"),
}
SEGMENTOS_DEMANDA: tuple[str, ...] = (
    "todas",
    "primera_infancia",
    "preescolar",
    "primaria",
    "secundaria",
    "adolescencia",
)
SEGMENTO_POR_OMISION: str = "todas"


def _columna_segmento(censo: pd.DataFrame, anio: int, segmento: str) -> pd.DataFrame:
    """Suma las columnas censales del `segmento` para un `anio`, una fila por `cvegeo`.

    `min_count=len(columnas)` (no el valor por omisión de pandas, 0): la
    suma solo es válida si **todas** las columnas del segmento tienen dato
    en esa fila; si falta una (p. ej. `p_15a17` suprimida por INEGI en una
    AGEB donde las demás bandas sí se publican), el segmento completo queda
    `NaN` -- nunca se trata la banda faltante como cero (CLAUDE.md, "no
    imputar sin documentarlo").
    """
    columnas = list(COLUMNAS_SEGMENTO[segmento])
    filas = censo.loc[censo["anio"] == anio, ["cvegeo", *columnas]]
    valor = filas[columnas].sum(axis=1, min_count=len(columnas))
    return pd.DataFrame({"cvegeo": filas["cvegeo"].to_numpy(), "valor": valor.to_numpy()})


def construir_panel_demanda(
    censo: pd.DataFrame,
    equivalencia: pd.DataFrame,
    universo: pd.DataFrame,
    segmento: str = SEGMENTO_POR_OMISION,
) -> pd.DataFrame:
    """Panel de demanda: una fila por AGEB del universo (2,453).

    Columnas: `cvegeo, cve_mun, ambito, relacion, segmento, d_2010, d_2020,
    motivo_sin_datos`.

    `segmento` (Fase 4, metodología §1.1): una de `SEGMENTOS_DEMANDA`
    (`todas` por omisión, población objetivo 0-17; `primera_infancia`,
    `preescolar`, `primaria`, `secundaria`, `adolescencia`). No requiere una
    fuente nueva: `COLUMNAS_SEGMENTO` ya está en `data/interim/censo_ageb_panel.parquet`
    (`tools/build_censo.py`). `modelos.py` no cambia: recibe este panel
    (con la columna `segmento` ya fija) exactamente como recibía el de
    `pob_0a14` (0-14) antes de la Fase 4.

    - `d_2020` = suma de las columnas del segmento en el censo 2020 para la
      misma clave (AGEB rural: `NaN`, no hay censo urbano de rurales).
    - `d_2010` = suma de las columnas del segmento en el censo 2010 para la
      clave `cvegeo_2010` que la equivalencia 2010→2020 asocia a este AGEB
      (columna `equivalencia.cvegeo_2010`; para `relacion == "misma"`
      coincide con la propia clave). Este mismo criterio cubre el caso
      `division`: la decisión del equipo (`docs/metodologia.md` §5,
      "división: hereda la tasa de la madre") es que la hija use el
      `D_2010` **completo** de la madre, sin reescalarlo por
      `frac_de_2010` — que es exactamente lo que produce esta unión, porque
      nunca se multiplica por `frac_de_2010`.
    - `relacion` viene de `equivalencia.relacion` (`misma`, `division`,
      `fusion_o_expansion`, `cambio_limites`); `None` en AGEB rural;
      `"sin_contraparte"` si una AGEB urbana no tiene fila de equivalencia
      (no ocurre hoy, ver `MOTIVOS_SIN_DATOS`; rama defensiva).
    - `motivo_sin_datos`: `rural` (ambito rural); `sin_censo` (urbana sin
      ninguna fila en el censo 2020); `suprimido_inegi` (fila censal del
      segmento con dato nulo -- alguna columna del segmento suprimida por
      INEGI, ver `_columna_segmento`); `d2020_menor_20` (`D_2020 < 20` de
      ese segmento); `None` si hay dato utilizable. El tope de confianza por
      `relacion` (`media` si no es `misma`; `baja`/`n_obs=1` si
      `sin_contraparte`) se aplica en `modelos.py` (B6), no aquí. El
      segmento `adolescencia` (15-17) lleva además tope `media` obligatorio
      por la oferta poco confiable de esa banda (metodología §1.1), aplicado
      en `exportar.py`, no aquí (este panel es solo de demanda).
    """
    if segmento not in COLUMNAS_SEGMENTO:
        raise ValueError(f"segmento desconocido: {segmento!r} (válidos: {SEGMENTOS_DEMANDA})")

    censo_2010 = _columna_segmento(censo, 2010, segmento).rename(
        columns={"cvegeo": "cvegeo_2010", "valor": "d_2010"}
    )
    censo_2020 = _columna_segmento(censo, 2020, segmento).rename(columns={"valor": "d_2020"})

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
    panel["segmento"] = segmento

    columnas = [
        "cvegeo",
        "cve_mun",
        "ambito",
        "relacion",
        "segmento",
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


def _filtro_territorio(df: pd.DataFrame, claves_urbanas: set[str]) -> pd.Series:
    """Filtro de territorio (plan §4.3 / problema M2): clave de 13 caracteres, prefijo
    `"09"`, `cve_mun` en `002`-`017`, y presente en el universo urbano. Compartido por
    `construir_panel_oferta` y `construir_panel_oferta_celda` (Fase 5)."""
    return (
        (df["cvegeo"].str.len() == 13)
        & (df["cvegeo"].str.slice(0, 2) == "09")
        & df["cve_mun"].between("002", "017")
        & df["cvegeo"].isin(claves_urbanas)
    )


def _panel_desde_filas(
    filas: pd.DataFrame, urbano: pd.DataFrame, cortes_t: list[float]
) -> pd.DataFrame:
    """Cuenta `id` únicos por AGEB x corte sobre `filas` (ya filtradas por territorio y,
    si aplica, por celda) y completa la malla urbana x corte con ceros explícitos.
    `filas` trae `cvegeo, cve_mun, t, id`. Devuelve `cvegeo, cve_mun, t, s, s_2024`."""
    conteos = filas.groupby(["cvegeo", "t"])["id"].nunique().rename("s").reset_index()

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


def construir_panel_oferta(
    denue: pd.DataFrame,
    universo: pd.DataFrame,
    cortes: dict[str, float] = CORTES_OFERTA,
) -> pd.DataFrame:
    """Panel de oferta educación (rama completa, `Alcance = 'Principal'`), formato largo:
    `cvegeo, cve_mun, t, s, s_2024`.

    `s` = número de `ID` distintos con `alcance == "Principal"` por AGEB
    urbana y corte (uno de `cortes.values()`, por defecto `CORTES_OFERTA`).
    `s_2024` repite, en todas las filas de un mismo AGEB, el valor de `s`
    del corte más reciente (`max(cortes.values())`), para que `features.py`
    calcule la brecha `S_2024 / D_2020` sin tener que volver a filtrar.

    Las AGEB urbanas sin ningún establecimiento en un corte quedan con
    `s = 0` explícito (nunca se omite la fila); las claves rurales/sin
    polígono se cuentan en `reporte_cobertura`, no aparecen en esta tabla.

    Mantenida sin cambios de comportamiento (contrato v1.2 todavía la usa,
    `exportar.py`); `construir_panel_oferta_celda` (Fase 5) generaliza esto
    por celda de filtro para las 4 ramas de Habitancia.
    """
    urbano = universo.loc[universo["ambito"] == "urbano", ["cvegeo", "cve_mun"]]
    claves_urbanas = set(urbano["cvegeo"])
    cortes_t = sorted(set(cortes.values()))

    principal = denue.loc[denue["alcance"] == "Principal"].copy()
    principal = principal[_filtro_territorio(principal, claves_urbanas) & principal["t"].isin(cortes_t)]

    return _panel_desde_filas(principal, urbano, cortes_t)


def construir_panel_oferta_celda(
    denue: pd.DataFrame,
    universo: pd.DataFrame,
    filtro_celda: pd.Series,
    cortes: dict[str, float] = CORTES_OFERTA,
) -> pd.DataFrame:
    """Panel de oferta para una celda de filtro genérica (Fase 5, metodología §10.6).

    `filtro_celda`: máscara booleana alineada con el índice de `denue`, que
    quien llama ya construyó (SCIAN + alcance para educación y salud,
    `subcategoria` para comercio -- ver `filtro_celda_educacion`,
    `filtro_celda_salud`, `filtro_celda_comercio`). A diferencia de
    `construir_panel_oferta`, esta función **no** filtra por
    `alcance == 'Principal'`: cada rama decide su propio criterio de
    inclusión antes de llamar aquí (p. ej. educación sí usa `Principal` para
    la mayoría de sus celdas, pero `media_superior_tecnica` y
    `recreacion_cultura` son `Complementario`; comercio no distingue por
    `alcance` en absoluto).

    Misma forma de salida que `construir_panel_oferta`: `cvegeo, cve_mun, t,
    s, s_2024`.
    """
    urbano = universo.loc[universo["ambito"] == "urbano", ["cvegeo", "cve_mun"]]
    claves_urbanas = set(urbano["cvegeo"])
    cortes_t = sorted(set(cortes.values()))

    filas = denue.loc[filtro_celda].copy()
    filas = filas[_filtro_territorio(filas, claves_urbanas) & filas["t"].isin(cortes_t)]

    return _panel_desde_filas(filas, urbano, cortes_t)


# ---------------------------------------------------------------------------
# Celdas de filtro por rama (Fase 5, `correccion/frontend_requisitos.md` §10)
# ---------------------------------------------------------------------------

# Sector (público/privado), Fase 5 (rework): cruza nivel/tipo en educación y salud
# (`correccion/frontend_requisitos.md` §10.11.1/§10.11.2 exige un selector "Todos ·
# Público · Privado"). La columna cruda `Sector` de DENUE ya trae exactamente estos 3
# valores (verificado en datos reales, `docs/perfil_datos.md`); `no_especificado` se
# publica como celda propia -- nunca se descarta -- para que "Todos" (la suma de las 3)
# reproduzca exactamente el total sin sector que ya validaba `test_panel.py` antes de
# este cruce (invariante Σ celdas = total, `correccion/action_plan.md` #40).
SECTORES: dict[str, str] = {
    "publico": "Público",
    "privado": "Privado",
    "no_especificado": "No especificado",
}

# Educación y cultura (§10.1): SCIAN verificado en datos reales
# (`docs/metodologia.md` cita los códigos `Principal`; los `Complementario`
# se verificaron por "Actividad SCIAN" -- ver commit de la Fase 5). Los 8
# niveles/tipos reproducen exactamente el conjunto que ya usaba
# `construir_panel_oferta`; `media_superior_tecnica`/`recreacion_cultura`
# son código nuevo, `Complementario` (metodología §1.1: "15-17 aparece sobre
# todo en Complementario", mismo principio aplicado aquí a nivel de celda).
_NIVELES_EDUCACION: dict[str, dict] = {
    "guarderia": {"alcance": "Principal", "scian": (624411, 624412)},
    "preescolar": {"alcance": "Principal", "scian": (611111, 611112)},
    "primaria": {"alcance": "Principal", "scian": (611121, 611122)},
    "secundaria": {"alcance": "Principal", "scian": (611131, 611132, 611141, 611142)},
    "educacion_especial": {"alcance": "Principal", "scian": (611181, 611182)},
    "varios_niveles": {"alcance": "Principal", "scian": (611171, 611172)},
    "media_superior_tecnica": {
        "alcance": "Complementario",
        "scian": (611151, 611152, 611161, 611162, 611512),
    },
    "recreacion_cultura": {
        "alcance": "Complementario",
        "scian": (611611, 611612, 611621, 611622, 611631, 611632, 611691, 611698, 611699),
    },
}

# Clave de celda `{nivel}__{sector}` (`plans/frontend_specs.md` §17.3): 8 niveles x 3
# sectores = 24 celdas.
CELDAS_EDUCACION: dict[str, dict] = {
    f"{nivel}__{sector}": {**spec, "sector": sector_crudo}
    for nivel, spec in _NIVELES_EDUCACION.items()
    for sector, sector_crudo in SECTORES.items()
}


def filtro_celda_educacion(denue: pd.DataFrame, celda: str) -> pd.Series:
    """Máscara booleana para una celda de `CELDAS_EDUCACION` sobre un DataFrame de
    `io.leer_denue_infancias` (columnas `alcance`, `scian`, `sector`)."""
    spec = CELDAS_EDUCACION[celda]
    return (
        (denue["alcance"] == spec["alcance"])
        & denue["scian"].isin(spec["scian"])
        & (denue["sector"] == spec["sector"])
    )


# Salud (§10.2): tipo ya viene como columna booleana en el dato
# (`io.leer_denue_salud`), más directo y confiable que reclasificar por
# SCIAN (51 códigos distintos en salud, sin un mapeo 1:1 tan limpio como
# educación); sector cruza igual que en educación (`SECTORES` arriba).
_TIPOS_SALUD: dict[str, str] = {
    "clinicas": "es_clinica",
    "hospitales": "es_hospital",
    "salud_mental": "es_salud_mental",
    "farmacias": "es_farmacia",
}

# Clave de celda `{tipo}__{sector}`: 4 tipos x 3 sectores = 12 celdas.
CELDAS_SALUD: dict[str, dict] = {
    f"{tipo}__{sector}": {"columna": columna, "sector": sector_crudo}
    for tipo, columna in _TIPOS_SALUD.items()
    for sector, sector_crudo in SECTORES.items()
}


def filtro_celda_salud(denue: pd.DataFrame, celda: str) -> pd.Series:
    """Máscara booleana para una celda de `CELDAS_SALUD` sobre un DataFrame de
    `io.leer_denue_salud` (columna booleana del tipo + `sector`)."""
    spec = CELDAS_SALUD[celda]
    return (denue[spec["columna"]] == 1) & (denue["sector"] == spec["sector"])


# Comercio (§10.3): por `subcategoria_proyecto` (verificado en datos reales, Fase 5).
# A diferencia de educación/salud, no se filtra por `alcance`: en comercios esa
# columna separa "las 3 categorías más grandes" de "el resto", no relevancia
# (`io.leer_denue_comercios`). `farmacias` es la única celda con
# `es_primera_necesidad='NO'` en el dato real -- DENUE no las cuenta como "primera
# necesidad" (aparecen también en la rama salud, `io.leer_denue_salud`); se incluyen
# aquí igual porque el requisito las deja como opcionales, no excluidas
# (`correccion/frontend_requisitos.md` §10.3: "si se decide incluirlas en esta rama").
CELDAS_COMERCIO: dict[str, tuple[str, ...]] = {
    "supermercados_minisupers": ("Minisúper", "Supermercado"),
    "abarrotes": ("Abarrotes, ultramarinos y misceláneas",),
    "frutas_verduras": ("Frutas y verduras",),
    "carnes_otros_alimentos": (
        "Carne de aves",
        "Carnes rojas",
        "Pescados y mariscos",
        "Otros alimentos",
        "Leche, lácteos y embutidos",
        "Semillas, granos, especias y chiles secos",
    ),
    "farmacias": ("Farmacia con minisúper", "Farmacia sin minisúper"),
}


def filtro_celda_comercio(denue: pd.DataFrame, celda: str) -> pd.Series:
    """Máscara booleana para una celda de `CELDAS_COMERCIO` sobre un DataFrame de
    `io.leer_denue_comercios`."""
    return denue["subcategoria"].isin(CELDAS_COMERCIO[celda])


# Verde (§10.4): sin proyección (metodología §10.1, un solo corte). Las 3 celdas ya
# vienen agregadas por AGEB en `io.leer_contexto_cdmx()`: no hay panel temporal que
# construir aquí, solo el nombre de columna de conteo/área que corresponde a cada una.
CELDAS_VERDE: dict[str, tuple[str, str]] = {
    "cobertura_verde": ("n_cobertura_verde", "area_cobertura_verde_m2"),
    "areas_recreativas": ("n_areas_recreativas", "area_areas_recreativas_m2"),
    "espacios_publicos": ("n_espacios_publicos", "area_espacios_publicos_m2"),
}


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
