"""
hexgrid.py — MOTOR DE HEXAGONIZACIÓN
=====================================

Primitivas reutilizables. No sabe nada de infancias ni de capas concretas:
recibe datos y devuelve tablas por hexágono. Toda la lógica de negocio vive
en capas_config.py.

FUNCIONES PRINCIPALES
  construir_rejilla()        límite -> GeoDataFrame de hexágonos H3
  puntos_a_hex()             puntos -> conteo por hexágono
  poligonos_a_hex()          polígonos -> valor repartido por área de traslape
  accesibilidad()            oferta local -> oferta accesible con decaimiento
  normalizar()               valor crudo -> 0-1 (percentil o min-max)
  a_deficit()                oferta per cápita -> déficit 0-1 (invierte dirección)

Verificado contra h3-py 4.5 y geopandas 1.1 sobre los datos reales del repo:
interpolación areal de áreas verdes con 99.91% de conservación de masa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    import h3
    from shapely.geometry import MultiPoint, Polygon
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Faltan dependencias. Instala:\n"
        '    pip install "h3>=4.0" geopandas shapely pandas numpy'
    ) from e

from capas_config import CRS_GEOGRAFICO, CRS_METRICO, RESOLUCION_H3


# ---------------------------------------------------------------------------
# 1. Rejilla
# ---------------------------------------------------------------------------
def construir_rejilla(limite_path: str | None = None,
                      capas_fallback: list | None = None,
                      resolucion: int = RESOLUCION_H3) -> gpd.GeoDataFrame:
    """Genera la rejilla H3 que cubre CDMX.

    limite_path: ruta al polígono oficial de CDMX (Marco Geoestadístico INEGI).
        ES LA OPCIÓN CORRECTA y la que hay que usar para la entrega final.

    capas_fallback: lista de GeoDataFrames con los que construir una
        envolvente convexa provisional, SÓLO mientras no se descarga el
        Marco Geoestadístico. Advertencia: la envolvente convexa incluye
        zona que no es CDMX y excluye entrantes del polígono real, así que
        la conservación de masa y los denominadores poblacionales salen
        distorsionados en los bordes.
    """
    if limite_path:
        limite = gpd.read_file(limite_path).to_crs(CRS_GEOGRAFICO)
        geom = limite.union_all()
    elif capas_fallback:
        print("  [!] Usando envolvente convexa provisional (sin Marco "
              "Geoestadístico). Sustituir antes de la entrega final.")
        pts = []
        for gdf in capas_fallback:
            g = gdf[gdf.geometry.notna()]
            pts.extend(list(g.geometry.representative_point()))
        geom = MultiPoint(pts).convex_hull
    else:
        raise ValueError("Se requiere limite_path o capas_fallback")

    celdas = h3.geo_to_cells(geom, resolucion)
    recs = [
        {
            "hex_id": c,
            "geometry": Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]),
        }
        for c in celdas
    ]
    grid = gpd.GeoDataFrame(recs, crs=CRS_GEOGRAFICO)
    centros = [h3.cell_to_latlng(c) for c in grid["hex_id"]]
    grid["lat"] = [round(p[0], 6) for p in centros]
    grid["lon"] = [round(p[1], 6) for p in centros]
    print(f"  Rejilla res{resolucion}: {len(grid):,} hexágonos "
          f"({h3.average_hexagon_area(resolucion, 'km^2'):.4f} km² c/u)")
    return grid


# ---------------------------------------------------------------------------
# 2. Puntos -> hexágono
# ---------------------------------------------------------------------------
def puntos_a_hex(lat: pd.Series, lon: pd.Series,
                 resolucion: int = RESOLUCION_H3,
                 peso: pd.Series | None = None) -> pd.Series:
    """Cuenta (o suma `peso`) de puntos por hexágono. Devuelve Series
    indexada por hex_id."""
    ok = lat.notna() & lon.notna()
    celdas = [h3.latlng_to_cell(la, lo, resolucion)
              for la, lo in zip(lat[ok], lon[ok])]
    df = pd.DataFrame({"hex_id": celdas})
    df["valor"] = 1.0 if peso is None else peso[ok].to_numpy()
    return df.groupby("hex_id")["valor"].sum()


# ---------------------------------------------------------------------------
# 3. Polígonos -> hexágono (interpolación areal)
# ---------------------------------------------------------------------------
def poligonos_a_hex(poligonos: gpd.GeoDataFrame,
                    rejilla: gpd.GeoDataFrame,
                    columna_valor: str,
                    verbose: bool = True) -> pd.Series:
    """Reparte `columna_valor` de cada polígono entre los hexágonos que toca,
    proporcional al área de traslape.

    Supuesto explícito: densidad uniforme dentro del polígono. Para áreas
    verdes esto es casi exacto (el m² de parque SÍ está uniformemente
    distribuido en el polígono del parque). Para población por AGEB es una
    aproximación — por eso se prefiere manzana cuando esté disponible.
    """
    p = poligonos[poligonos.geometry.notna()].copy()

    invalidas = int((~p.geometry.is_valid).sum())
    if invalidas:
        if verbose:
            print(f"  [!] {invalidas} geometrías inválidas -> make_valid()")
        p["geometry"] = p.geometry.make_valid()

    p_m = p.to_crs(CRS_METRICO)
    hex_m = rejilla.to_crs(CRS_METRICO)
    p_m["_area_orig"] = p_m.geometry.area

    inter = gpd.overlay(
        p_m[["geometry", columna_valor, "_area_orig"]],
        hex_m[["geometry", "hex_id"]],
        how="intersection",
        keep_geom_type=True,
    )
    frac = inter.geometry.area / inter["_area_orig"].replace(0, np.nan)
    inter["_asignado"] = inter[columna_valor] * frac.fillna(0)

    resultado = inter.groupby("hex_id")["_asignado"].sum()

    if verbose:
        total_o = p[columna_valor].sum()
        total_a = resultado.sum()
        pct = 100 * total_a / total_o if total_o else 0
        flag = "" if pct > 98 else "   <-- REVISAR: fuga en bordes de la rejilla"
        print(f"  Conservación de masa: {pct:.2f}%{flag}")

    return resultado


# ---------------------------------------------------------------------------
# 4. Accesibilidad con decaimiento por distancia
# ---------------------------------------------------------------------------
def accesibilidad(oferta_local: pd.Series,
                  hex_ids: pd.Index | list,
                  radio_m: int,
                  resolucion: int = RESOLUCION_H3,
                  cortes_radio: float = 2.5) -> pd.Series:
    """Convierte oferta EN el hexágono en oferta ACCESIBLE DESDE el hexágono.

        acceso_i = Σ_j  oferta_j · exp(-d_ij / radio)

    Por qué esto importa y no es un adorno:

    1. Un parque en el hexágono vecino sirve igual de bien. Contar sólo lo
       que cae dentro del hexágono produce un mapa de ruido, no de acceso.

    2. Resuelve la dispersión. Capas como cultura infantil tienen ~300
       registros en 10,000 hexágonos: sin decaimiento, el 97% del mapa sale
       en cero y el usuario ve un mapa vacío que parece un bug.

    3. Hace que el modelo predictivo se comporte. Una serie de conteos
       crudos por hexágono es casi toda ceros con saltos de 0 a 1; la serie
       de accesibilidad es continua y suave, y sobre ella la regresión sí
       tiene sentido.

    `cortes_radio` define hasta cuántos radios se propaga (2.5 -> peso
    residual e^-2.5 ≈ 8%, corte razonable).
    """
    paso_m = h3.average_hexagon_edge_length(resolucion, "m") * np.sqrt(3)
    k_max = max(1, int(np.ceil(cortes_radio * radio_m / paso_m)))

    pesos_k = {k: float(np.exp(-(k * paso_m) / radio_m)) for k in range(k_max + 1)}

    acumulado: dict[str, float] = {}
    for hex_origen, valor in oferta_local.items():
        if valor == 0 or pd.isna(valor):
            continue
        for k in range(k_max + 1):
            anillo = h3.grid_ring(hex_origen, k) if k else [hex_origen]
            w = pesos_k[k]
            for destino in anillo:
                acumulado[destino] = acumulado.get(destino, 0.0) + valor * w

    serie = pd.Series(acumulado, name="acceso")
    return serie.reindex(hex_ids).fillna(0.0)


# ---------------------------------------------------------------------------
# 5. Normalización y conversión a déficit
# ---------------------------------------------------------------------------
def normalizar(valores: pd.Series, metodo: str = "percentil") -> pd.Series:
    """Lleva cualquier métrica a 0-1.

    percentil (recomendado): robusto a outliers. Chapultepec destruiría un
        min-max de áreas verdes — un solo polígono dejaría al 99% del mapa
        pegado a cero. Además hace que un peso de 0.3 signifique lo mismo
        en todas las capas, que es lo que el usuario asume al mover sliders.
        Costo: el resultado es RELATIVO a CDMX, no absoluto.

    minmax: conserva magnitud relativa, útil si se quiere comparar contra
        un estándar externo (p. ej. los 9 m²/hab de la OMS).
    """
    v = valores.astype(float)
    if metodo == "percentil":
        return v.rank(method="average", pct=True)
    rango = v.max() - v.min()
    if rango == 0:
        return pd.Series(0.5, index=v.index)
    return (v - v.min()) / rango


def a_deficit(acceso: pd.Series,
              poblacion: pd.Series,
              metodo: str = "percentil",
              pob_minima: float = 10.0) -> pd.Series:
    """Oferta accesible + población demandante -> déficit 0-1 (1 = más necesidad).

    Los hexágonos con población por debajo de `pob_minima` (cerros, zona de
    conservación, industrial) se marcan NaN en vez de 0: un hexágono sin
    habitantes no tiene "déficit", simplemente no aplica. Pintarlos de rojo
    sería recomendar invertir donde no vive nadie — exactamente el tipo de
    error que el reto pide evitar.
    """
    pob = poblacion.reindex(acceso.index).astype(float)
    percapita = acceso / pob.where(pob >= pob_minima)
    deficit = 1.0 - normalizar(percapita.dropna(), metodo)
    return deficit.reindex(acceso.index)


# ---------------------------------------------------------------------------
# 6. Utilidad: score combinado (la misma fórmula que usará el frontend)
# ---------------------------------------------------------------------------
def score_ponderado(hex_master: pd.DataFrame,
                    pesos: dict[str, float],
                    sufijo: str = "") -> pd.Series:
    """score = Σ (peso_capa · deficit_capa), con pesos renormalizados a 1.

    Se incluye aquí para que el backend pueda validar que el frontend
    produce exactamente el mismo número. Si los dos lados no coinciden,
    hay un bug de contrato.
    """
    total = sum(pesos.values())
    if total == 0:
        raise ValueError("Todos los pesos son cero")
    acc = pd.Series(0.0, index=hex_master.index)
    peso_valido = pd.Series(0.0, index=hex_master.index)
    for capa_id, w in pesos.items():
        col = f"deficit_{capa_id}{sufijo}"
        if col not in hex_master.columns or w == 0:
            continue
        vals = hex_master[col]
        presente = vals.notna()
        acc = acc.add((vals.fillna(0) * w), fill_value=0)
        peso_valido = peso_valido.add(presente.astype(float) * w, fill_value=0)
    # renormaliza por los pesos efectivamente disponibles en cada hexágono
    return (acc / peso_valido.replace(0, np.nan)).clip(0, 1)
