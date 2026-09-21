"""Fixtures compartidas de `backend/tests/`.

Regla del plan (`plans/backend_plan.md` §8): los tests no leen `data/` salvo
que estén marcados `@pytest.mark.datos`; esos se saltan automáticamente si
falta `data/interim/` (es decir, si no se corrió `make datos`).

Las fixtures sintéticas son deliberadamente pequeñas y reproducen solo la
forma (columnas, tipos) de las tablas descritas en el plan §3 y §4, no datos
reales.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Permite `import chipos...` sin depender de que el runner fije PYTHONPATH
# (el Makefile ya lo hace via `PYTHONPATH=backend/src`, esto es un respaldo).
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from chipos.config import DIR_INTERIM, SEMILLA  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "datos: requiere data/interim/ real (se salta si falta, ver `make datos`)",
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """No fallar `make test` cuando aún no hay tests (fase B0 del plan).

    pytest sale con código 5 ("no tests collected"); una vez que B1+ añadan
    tests este hook deja de tener efecto (el exit status real ya no es 5).
    """
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if DIR_INTERIM.is_dir() and any(DIR_INTERIM.glob("*.parquet")):
        return
    faltan = pytest.mark.skip(reason="falta data/interim/: ejecuta `make datos`")
    for item in items:
        if "datos" in item.keywords:
            item.add_marker(faltan)


@pytest.fixture
def rng() -> np.random.Generator:
    """Generador con la semilla global del proyecto (reproducibilidad)."""
    return np.random.default_rng(SEMILLA)


@pytest.fixture
def universo_ageb_sintetico() -> pd.DataFrame:
    """Universo mínimo de AGEB (forma de `leer_universo_ageb()`, plan §3).

    Incluye AGEB urbanas de dos alcaldías y una AGEB rural, para ejercer las
    ramas de `sin_datos` sin tocar `data/reference/`.
    """
    return pd.DataFrame(
        {
            "cvegeo": [
                "0900200011991",
                "0900200012005",
                "0900300010112",
                "0900300010128",
                "090150001",  # rural: 9 caracteres
            ],
            "cve_mun": ["002", "002", "003", "003", "015"],
            "ambito": ["urbano", "urbano", "urbano", "urbano", "rural"],
        }
    )


@pytest.fixture
def panel_demanda_sintetico() -> pd.DataFrame:
    """Panel de demanda mínimo (forma de `construir_panel_demanda()`, plan §4.1)."""
    return pd.DataFrame(
        {
            "cvegeo": [
                "0900200011991",
                "0900200012005",
                "0900300010112",
                "0900300010128",
                "090150001",
            ],
            "cve_mun": ["002", "002", "003", "003", "015"],
            "ambito": ["urbano", "urbano", "urbano", "urbano", "rural"],
            "relacion": ["misma", "division", "misma", "sin_contraparte", None],
            "d_2010": [120.0, 45.0, 300.0, np.nan, np.nan],
            "d_2020": [110.0, 60.0, 280.0, 15.0, np.nan],
            "motivo_sin_datos": [None, None, None, None, "rural"],
        }
    )


@pytest.fixture
def panel_oferta_sintetico() -> pd.DataFrame:
    """Panel de oferta mínimo, formato largo (forma del plan §4.3)."""
    cvegeos = ["0900200011991", "0900200012005", "0900300010112", "0900300010128"]
    cortes = [2016.79, 2019.87, 2024.87]
    filas = [
        {"cvegeo": cve, "cve_mun": cve[2:5], "t": t, "s": s}
        for cve in cvegeos
        for t, s in zip(cortes, [1, 2, 2])
    ]
    return pd.DataFrame(filas)


@pytest.fixture
def conapo_sintetico() -> pd.DataFrame:
    """Proyección CONAPO mínima por alcaldía (forma de `leer_conapo_0a14()`)."""
    return pd.DataFrame(
        {
            "cve_mun": ["002", "002", "003", "003"],
            "anio": [2020, 2027, 2020, 2027],
            "pob_0a14": [5000.0, 4700.0, 8200.0, 7600.0],
        }
    )
