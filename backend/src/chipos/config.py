"""Rutas y constantes del modelo (único lugar de parámetros).

Todas las rutas son absolutas, calculadas a partir de la ubicación de este
archivo (`backend/src/chipos/config.py`), para que el paquete funcione sin
importar el directorio de trabajo desde el que se invoque.

Las constantes numéricas reproducen exactamente `plans/backend_plan.md` §5
("Algoritmo de estimación"); cualquier cambio debe reflejarse también en
`docs/metodologia.md` §7.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

# backend/src/chipos/config.py -> .../chipos_dataton
RAIZ: Path = Path(__file__).resolve().parents[3]

DIR_DATA: Path = RAIZ / "data"
DIR_PROCESSED: Path = DIR_DATA / "processed"  # solo lectura
DIR_REFERENCE: Path = DIR_DATA / "reference"  # solo lectura
DIR_INTERIM: Path = DIR_DATA / "interim"
DIR_OUTPUTS: Path = DIR_DATA / "outputs"

DIR_DOCS: Path = RAIZ / "docs"

# Geometría AGEB (ver CLAUDE.md y plan §2; no se reescriben)
RUTA_AGEB_GEOJSON: Path = DIR_REFERENCE / "ageb_cdmx.geojson"
RUTA_AGEB_GEOJSON_SIMPLIFICADO: Path = DIR_REFERENCE / "ageb_cdmx_simplificado.geojson"
RUTA_ALCALDIAS_CSV: Path = DIR_REFERENCE / "alcaldias.csv"
RUTA_ALCALDIAS_GEOJSON: Path = DIR_REFERENCE / "alcaldias.geojson"
RUTA_DOMINIOS_SCIAN: Path = DIR_REFERENCE / "dominios_scian.csv"

# Derivados de `data/interim/` (ver plan §3)
RUTA_CENSO_PANEL: Path = DIR_INTERIM / "censo_ageb_panel.parquet"
RUTA_CONAPO_MUN_0A14: Path = DIR_INTERIM / "conapo_mun_0a14.parquet"
RUTA_EQUIVALENCIA_AGEB: Path = DIR_INTERIM / "equivalencia_ageb_2010_2020.parquet"
RUTA_PROYECCION_AGEB: Path = DIR_INTERIM / "proyeccion_ageb.parquet"

# Salidas del contrato (plan §7 y CLAUDE.md)
RUTA_PREDICCION_AGEB: Path = DIR_OUTPUTS / "prediccion_ageb.json"
RUTA_PREDICCION_ALCALDIA: Path = DIR_OUTPUTS / "prediccion_alcaldia.json"
RUTA_DIAGNOSTICO: Path = DIR_OUTPUTS / "diagnostico.json"
RUTA_BACKTEST_JSON: Path = DIR_OUTPUTS / "backtest.json"
RUTA_BACKTEST_MD: Path = DIR_DOCS / "backtest.md"

# ---------------------------------------------------------------------------
# Semilla global (reproducibilidad; CLAUDE.md regla 5, plan §0)
# ---------------------------------------------------------------------------

SEMILLA: int = 20260918

# ---------------------------------------------------------------------------
# Constantes del algoritmo de estimación (plan §5)
# ---------------------------------------------------------------------------

# Tiempo en años decimales de los censos y de los horizontes de proyección.
T_2010: float = 2010.44
T_2020: float = 2020.20

# Fecha base de reporte (mediados de 2026) y horizontes de 3, 5 y 7 años
# (contrato v1.2, `plans/frontend_specs.md` §17-18): `delta_pct`/`ic95` se
# miden desde `T_BASE`, no desde el censo 2020 (ver `resumir()` en
# `modelos.py` y `docs/metodologia.md` §2/§7).
T_BASE: float = 2026.5
HORIZONTES: dict[str, float] = {"h3": T_BASE + 3, "h5": T_BASE + 5, "h7": T_BASE + 7}
T_HOR: float = HORIZONTES["h7"]  # ancla del control CONAPO (horizonte más lejano)

# La capa de oferta solo reporta el horizonte más cercano (metodología §6:
# la caída 2024-11 y el tope de confianza `media` no justifican calibrar
# más allá de 3 años).
HORIZONTES_OFERTA: tuple[str, ...] = ("h3",)

# Banda muerta de "se_mantiene": ±1 %/año sobre la tasa proyectada.
DELTA: float = 0.01

# Umbrales de probabilidad de la regla de veredicto (plan §5.3).
P_DECISION: float = 0.80
P_ALTA: float = 0.95
P_MANTIENE: float = 0.50

# Número de réplicas de la simulación Monte Carlo.
N_SIM: int = 4000

# Previa de la persistencia de la desviación local (U(0.25, 1)).
LAMBDA_PREVIA: tuple[float, float] = (0.25, 1.0)

# Valores de sensibilidad reportados en `diagnostico.json`.
LAMBDAS_SENS: tuple[float, float, float] = (0.25, 0.6, 1.0)
DELTAS_SENS: tuple[float, float, float] = (0.005, 0.01, 0.02)

# Población infantil mínima (D_2020) para no forzar confianza 'baja'.
D_MIN_CONF: int = 100
