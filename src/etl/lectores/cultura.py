"""Lector de la familia `cultura` (AREAS_CULTURALES_CDMX/) al esquema largo común.

Alcance: SOLO `data/AREAS_CULTURALES_CDMX/`. No toca PILARES CDMX (otra familia,
otro lector) ni ninguna otra carpeta de `data/`.

Diferencias frente a las familias DENUE (Gen A / Gen B / temáticos) que
justifican las decisiones de mapeo de este módulo:

- **No es serie histórica.** `AREAS_CULTURALES_CDMX` es una fotografía única
  del directorio SIC (Sistema de Información Cultural) descargado, no un
  snapshot mensual/anual repetido como los cortes DENUE (CLAUDE.md §2,
  docs/current-state.md §7). Por lo tanto no existe `fuente.edicion` ni
  carpeta con fecha en el nombre, y `src/etl/ediciones.py` (pensado para
  resolver YYYY-MM de las familias DENUE, incluida la regla especial de
  Gen A) NO aplica aquí. Se fija `edicion="unica"` y `edicion_verificada=None`
  ("no aplica", no "no verificada") de forma explícita en cada fila.
- **No tiene `clee` ni `scian`** (no es un registro DENUE). Se reutiliza la
  columna `clee` del esquema común para portar un identificador estable del
  registro cultural: `id_cultural`, no `id_sic`. Se probaron ambos contra los
  868 registros reales: `id_sic` tiene 36 valores duplicados (no es único),
  mientras que `id_cultural` no tiene ningún duplicado. `scian` queda en
  `None` para todas las filas.
- **`sector`** se deriva de `tipo_gestion` (PUBLICO/PRIVADO/MIXTO/
  NO_DETERMINADO), la columna más cercana a un "sector" en este dataset (no
  existe una columna de sector económico como en DENUE).
- **`alcance`** (concepto DENUE de Gen B: Principal/Complementario, ver
  docs/architecture-plan.md) no aplica a esta familia: los tres tipos
  incluidos (TEATRO, CENTRO_CULTURAL, CINE) son directamente el objeto del
  dominio "cultura", no establecimientos complementarios de otro giro. Se
  deja `None` para todas las filas.
- `es_pilares` (SI/NO) y `dataset_relacionado` (p. ej. "PILARES" o vacío) se
  conservan tal cual vienen del CSV depurado; son la señal para evitar doble
  conteo si en el futuro se combina esta capa con el dataset específico de
  PILARES (fuera del alcance de este módulo decidir cómo se combina).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")

from etl.catalogo import normalizar_alcaldia  # noqa: E402

_ARCHIVO = "areas_culturales_cdmx_depurado.csv"

_COLUMNAS_NECESARIAS = [
    "id_cultural",
    "municipio_id",
    "tipo_cultural",
    "tipo_gestion",
    "revision_manual",
    "es_pilares",
    "dataset_relacionado",
]


def leer_todas(data_dir: Path) -> pd.DataFrame:
    """Lee `AREAS_CULTURALES_CDMX/areas_culturales_cdmx_depurado.csv` y devuelve
    el esquema largo común:

        familia, edicion, edicion_verificada, cve_alc, clee, scian, dominio,
        subcategoria, sector, alcance, revision_manual, es_pilares,
        dataset_relacionado

    Un registro de entrada = un registro de salida (no hay deduplicación:
    el README del dataset indica explícitamente que un mismo inmueble puede
    aparecer como teatro, centro cultural y/o cine).

    `municipio_id` que no caiga en las 16 claves válidas de
    `normalizar_alcaldia` se reporta como warning (print a stderr) con el
    valor exacto y la fila se descarta de la salida (no se descarta
    silenciosamente).
    """
    ruta = Path(data_dir) / "AREAS_CULTURALES_CDMX" / _ARCHIVO
    df = pd.read_csv(ruta, usecols=_COLUMNAS_NECESARIAS)

    faltantes = set(_COLUMNAS_NECESARIAS) - set(df.columns)
    if faltantes:
        raise ValueError(f"columnas esperadas ausentes en {ruta}: {sorted(faltantes)}")

    cve_alc = []
    filas_validas = []
    for idx, valor in df["municipio_id"].items():
        try:
            cve_alc.append(normalizar_alcaldia(valor, tipo="municipio_id"))
            filas_validas.append(idx)
        except ValueError as exc:
            print(
                f"WARNING [cultura]: municipio_id no reconocido en fila id_cultural="
                f"{df.at[idx, 'id_cultural']!r}: {valor!r} ({exc})",
                file=sys.stderr,
            )

    df = df.loc[filas_validas].copy()
    df["cve_alc"] = cve_alc

    salida = pd.DataFrame(
        {
            "familia": "cultura",
            "edicion": "unica",
            "edicion_verificada": None,
            "cve_alc": df["cve_alc"].to_numpy(),
            "clee": df["id_cultural"].to_numpy(),
            "scian": None,
            "dominio": "cultura",
            "subcategoria": df["tipo_cultural"].to_numpy(),
            "sector": df["tipo_gestion"].to_numpy(),
            "alcance": None,
            "revision_manual": df["revision_manual"].to_numpy(),
            "es_pilares": df["es_pilares"].to_numpy(),
            "dataset_relacionado": df["dataset_relacionado"].to_numpy(),
        }
    )

    return salida.reset_index(drop=True)


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
    out = leer_todas(data_dir)

    out_path = data_dir / "processed" / "cultura.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    print(f"Filas escritas: {len(out)} -> {out_path}")
    print(out["subcategoria"].value_counts())
    print(f"cve_alc fuera de las 16 claves válidas: {(~out['cve_alc'].isin([f'{i:03d}' for i in range(2, 18)])).sum()}")
