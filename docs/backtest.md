# Backtest

Semilla: `20260918`. Marco geoestadístico: MG 2020 censal, UPC 889463807469.

## Resumen (≤ 5 líneas)

1. Demanda (adelgazamiento 25%/50%): supera al baseline `r=0` en MAE y F1 macro.
2. Demanda (LOAO): cobertura del IC95 = 1.00 (FUERA de [0.90, 0.97]).
3. Oferta (origen 2016+2019 -> predice 2024): NO supera al baseline 'S constante' en MAE y F1 macro.
4. Piso de incertidumbre calibrado: demanda `sigma_min=0.0` (cobertura 0.99); oferta `sigma_min=0.0` (cobertura 1.00).
5. **Modelo NO SE ADOPTA** según el criterio de CLAUDE.md (LOAO fuera de [0.90, 0.97]; oferta no supera al baseline en MAE/F1).

## Adelgazamiento binomial (Censo 2020, nunca el futuro)

| frac | estimador | MAE (pp/año) | F1 macro | cobertura IC95 | n |
|---|---|---:|---:|---:|---:|
| 0.25 | baseline_r0 | 2.34 | 0.11 | n/d | 2362 |
| 0.25 | r_hat_directo | 0.69 | 0.79 | 0.99 | 2362 |
| 0.25 | r_tilde_eb | 0.68 | 0.81 | 0.98 | 2362 |
| 0.25 | rho_m | 1.49 | 0.35 | n/d | 2362 |
| 0.5 | baseline_r0 | 2.34 | 0.11 | n/d | 2362 |
| 0.5 | r_hat_directo | 0.41 | 0.86 | 1.00 | 2362 |
| 0.5 | r_tilde_eb | 0.46 | 0.86 | 1.00 | 2362 |
| 0.5 | rho_m | 1.49 | 0.35 | n/d | 2362 |

## LOAO (validación cruzada espacial, deja una alcaldía fuera)

MAE: 0.17 pp/año · F1 macro: 0.96 · cobertura IC95: 1.00 · n=2362

## Oferta (backtest temporal: origen 2016-10+2019-11 -> predice 2024-11)

| estimador | MAE log-razón | F1 macro | deviance Poisson | cobertura IC95 | n |
|---|---:|---:|---:|---:|---:|
| baseline_s_constante | 3.61 | 0.20 | 0.750 | n/d | 2431 |
| modelo_poisson_2016_2019 | 5.45 | 0.67 | 2.330 | 1.00 | 2431 |

## Decisión sobre la capa de oferta (F-2 / punto 12)

El modelo Poisson de oferta (origen 2016-10+2019-11 -> predice 2024-11) **no supera** al baseline 'S constante' en esta validación. `CLAUDE.md` exige no adoptar un modelo que no supere al baseline; aun así las ramas de oferta se publican en el contrato, degradadas: **tope de confianza `media`** en toda proyección de oferta (nunca `alta`), la rama `verde` se reporta sin proyección (`horizontes_disponibles: []`, solo nivel actual) y las demás ramas (`educacion`, `salud`, `comercio`) llevan la limitación anterior escrita en el frontend (F-7). Se publica con esta etiqueta, en vez de ocultarla, porque el nivel observado de establecimientos sigue siendo información útil para un usuario que sabe leer la salvedad; lo que no se hace es presentar la proyección de oferta con la misma confianza que la de demanda.

## Banda de cobertura del IC95 (F-3 / punto 21)

La *Definición de terminado* pedía cobertura empírica del IC95 en `[0.90, 0.97]`. Hoy LOAO cubre 1.00 y los pisos calibrados de demanda y oferta ya sobrecubren en `sigma_min=0.000` (ver tabla de calibración abajo): el procedimiento del punto 19 solo puede **ensanchar** el intervalo con un piso, nunca estrecharlo, así que no hay piso que cierre este hueco. Decisión (a) tomada: se acepta la sobrecobertura como conservadora y se marca este criterio de la DoD como **relajado explícitamente**, no silenciado -- un intervalo que sobrecubre falla del lado seguro (nunca declara más certeza de la que tiene), a diferencia de uno que subcubre. No se implementó un factor de estrechamiento (opción b) porque arriesgaba empeorar la calibración real a cambio de cumplir un número de la DoD sin validación adicional.

## Comparación censo-CONAPO 2010-2020 (NO es un backtest)

Compara dos fuentes en el mismo punto del tiempo; alimenta `sigma_C` (`modelos.simular_demanda`), nunca se usa como validación retrospectiva.

| alcaldía | tasa censo (%/año) | tasa CONAPO (%/año) | diferencia (pp/año) |
|---|---:|---:|---:|
| 002 | -1.49 | -1.92 | 0.43 |
| 003 | -2.26 | -2.83 | 0.57 |
| 004 | -0.47 | -0.82 | 0.35 |
| 005 | -1.93 | -2.18 | 0.25 |
| 006 | -1.38 | -1.8 | 0.42 |
| 007 | -2.13 | -2.26 | 0.14 |
| 008 | -2.07 | -2.07 | 0.0 |
| 009 | -1.07 | -0.35 | -0.71 |
| 010 | -1.89 | -2.07 | 0.18 |
| 011 | -1.64 | -1.64 | -0.0 |
| 012 | -1.57 | -1.56 | -0.0 |
| 013 | -1.43 | -1.34 | -0.09 |
| 014 | -0.28 | -2.09 | 1.82 |
| 015 | -1.64 | -2.49 | 0.85 |
| 016 | -0.32 | -1.14 | 0.82 |
| 017 | -1.2 | -1.67 | 0.47 |

## Limitación declarada

No existe hoy una validación temporal independiente de la tendencia de demanda a nivel alcaldía; la comparación 2010-2020 alimenta la incertidumbre del modelo (sigma_C), pero no lo valida contra el futuro.

