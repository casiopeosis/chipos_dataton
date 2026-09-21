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

# Colonias (IECM 2022, ver tools/build_colonias.py y docs/data_manifest.md; no se reescriben)
RUTA_COLONIAS_RAW: Path = DIR_PROCESSED / "colonias" / "colonias_iecm_2022.geojson"
RUTA_COLONIAS_GEOJSON: Path = DIR_REFERENCE / "colonias_cdmx.geojson"
RUTA_COLONIAS_GEOJSON_SIMPLIFICADO: Path = DIR_REFERENCE / "colonias_cdmx_simplificado.geojson"

# Derivados de `data/interim/` (ver plan §3)
RUTA_CENSO_PANEL: Path = DIR_INTERIM / "censo_ageb_panel.parquet"
RUTA_CONAPO_MUN_0A14: Path = DIR_INTERIM / "conapo_mun_0a14.parquet"
RUTA_EQUIVALENCIA_AGEB: Path = DIR_INTERIM / "equivalencia_ageb_2010_2020.parquet"
RUTA_PROYECCION_AGEB: Path = DIR_INTERIM / "proyeccion_ageb.parquet"
RUTA_AGEB_COLONIA: Path = DIR_INTERIM / "ageb_colonia.parquet"

# Salidas del contrato (plan §7 y CLAUDE.md)
RUTA_PREDICCION_AGEB: Path = DIR_OUTPUTS / "prediccion_ageb.json"
RUTA_PREDICCION_ALCALDIA: Path = DIR_OUTPUTS / "prediccion_alcaldia.json"
RUTA_DIAGNOSTICO: Path = DIR_OUTPUTS / "diagnostico.json"
RUTA_BACKTEST_JSON: Path = DIR_OUTPUTS / "backtest.json"
RUTA_BACKTEST_MD: Path = DIR_DOCS / "backtest.md"
# Fuera del contrato versionado (como diagnostico.json): lookup AGEB -> colonia para el frontend.
RUTA_COLONIAS_AGEB_JSON: Path = DIR_OUTPUTS / "colonias_ageb.json"

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

# Fecha base de reporte (mediados de 2026) y horizontes de 1, 3 y 5 años
# (`correccion/rubrica.md` §5: "uno, tres o cinco años"; contrato se queda en
# v1.2 hasta que las Fases 4-6 completen el salto a v1.4, `plans/backend_plan.md`
# tarea B13): `delta_pct`/`ic95` se miden desde `T_BASE`, no desde el censo
# 2020 (ver `resumir()` en `modelos.py` y `docs/metodologia.md` §2/§7).
T_BASE: float = 2026.5
HORIZONTES: dict[str, float] = {"h1": T_BASE + 1, "h3": T_BASE + 3, "h5": T_BASE + 5}
T_HOR: float = HORIZONTES["h5"]  # ancla del control CONAPO (horizonte más lejano)

# La oferta reporta h1 y h3, no h5 (metodología §6.3): no tiene control
# externo y su único ancla temporal es el propio levantamiento DENUE; 3 años
# desde la fecha base sigue siendo el techo defendible, pero 1 año sí es
# reportable y la rúbrica lo pide.
HORIZONTES_OFERTA: tuple[str, ...] = ("h1", "h3")

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

# ---------------------------------------------------------------------------
# Sobredispersión y piso de incertidumbre (Fase 3 de `correccion/action_plan.md`,
# metodología §2.7/§6.2; calibrado con `backtest.calibrar_piso_incertidumbre`
# sobre `data/outputs/backtest.json`, corrida 2026-09-20).
# ---------------------------------------------------------------------------

# Factor quasi-Poisson mínimo (nunca reduce la varianza de la oferta, metodología §6.2).
PHI_MINIMO: float = 1.0

# Piso de la desviación estándar de la tasa (unidades de tasa, no pp/año).
# Calibrado por cobertura empírica del IC95 en `[0.90, 0.97]` (metodología §2.7):
# con los datos reales, el candidato `0.000` ya sobrecubre en ambas capas
# (demanda: adelgazamiento 0.98-1.00, LOAO 1.00; oferta: 1.00) -- ninguna
# alcanza a estar POR DEBAJO del piso de cobertura 0.90, así que no hace
# falta ensanchar más los intervalos: el error de conteo (más, en oferta, el
# factor quasi-Poisson `PHI_MINIMO`/`phi_m`) ya basta. Ver `docs/backtest.md`
# y `docs/metodologia.md` §2.7 para la rejilla completa y la nota de que la
# rejilla no alcanzó la banda por ARRIBA (sobrecobertura), no por abajo.
SIGMA_MIN_DEMANDA: float = 0.0
SIGMA_MIN_OFERTA: float = 0.0
