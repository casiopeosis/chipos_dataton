"""Regla de veredicto y de confianza, y modelos de demanda/oferta.

Plan `plans/backend_plan.md` §5; fórmulas exactas en `docs/metodologia.md`
§2 (demanda), §6 (oferta), §7 (regla de decisión).

Contenido:
- `veredicto`, `confianza` (B5): regla de decisión y de nivel de confianza,
  compartidas por ambas capas.
- `tasa_directa`, `contraccion_eb`, `tasa_conapo`, `simular_demanda` (B6):
  tasa log-lineal por AGEB con contracción Fay-Herriot hacia la alcaldía y
  ancla CONAPO, simulada por Monte Carlo.
- `ajustar_oferta`, `simular_oferta` (B7a): pendiente Poisson log-lineal por
  AGEB (Newton-Raphson vectorizado, sin bucle `statsmodels`), con la misma
  contracción hacia la alcaldía, sin control externo, tope de confianza
  `media`.
- `resumir`, `agregar_alcaldia`: comparten una estructura `Simulacion` para
  ambas capas y ambos niveles territoriales (AGEB / alcaldía), porque el
  resto de la lógica (regla de veredicto, agregación por réplica) es
  idéntica una vez que se tiene una matriz `(n_unidades, n_sim)` de tasas
  proyectadas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from chipos.config import (
    D_MIN_CONF,
    DELTA,
    HORIZONTES,
    LAMBDA_PREVIA,
    LAMBDAS_SENS,
    N_SIM,
    P_ALTA,
    P_DECISION,
    P_MANTIENE,
    PHI_MINIMO,
    SIGMA_MIN_DEMANDA,
    SIGMA_MIN_OFERTA,
    T_2010,
    T_2020,
    T_BASE,
    T_HOR,
)
from chipos.io import CORTES_OFERTA

# Orden de los niveles de confianza, de menor a mayor (para "bajar un nivel"
# y para aplicar un `tope` como techo).
_NIVELES: tuple[str, str, str] = ("baja", "media", "alta")
_RANGO: dict[str, int] = {nivel: i for i, nivel in enumerate(_NIVELES)}


def veredicto(p_sube: float, p_baja: float, p_mantiene: float) -> tuple[str, float]:
    """Regla de decisión única (plan §5.3, metodología §7).

    - `sube` si `p_sube >= P_DECISION`, con `p_dec = p_sube`.
    - `baja` si `p_baja >= P_DECISION`, con `p_dec = p_baja`.
    - en cualquier otro caso, `se_mantiene` con `p_dec = p_mantiene`.

    Nota: la regla del plan distingue un caso "`se_mantiene` con
    `p_mantiene >= P_MANTIENE`" de un caso residual "si no, `se_mantiene`
    con confianza forzada `baja`". No hace falta distinguirlos aquí: como
    `P_MANTIENE (0.50) < P_DECISION (0.80)`, cualquier `p_mantiene` por
    debajo de `P_MANTIENE` también queda por debajo de `P_DECISION`, así
    que `confianza()` ya devuelve `baja` en ese caso al aplicar sus
    umbrales estándar sobre `p_dec = p_mantiene`.
    """
    if p_sube >= P_DECISION:
        return "sube", p_sube
    if p_baja >= P_DECISION:
        return "baja", p_baja
    return "se_mantiene", p_mantiene


def _bajar_un_nivel(nivel: str) -> str:
    """Un escalón hacia abajo en `_NIVELES` (`baja` se queda en `baja`)."""
    indice = max(0, _RANGO[nivel] - 1)
    return _NIVELES[indice]


def _aplicar_tope(nivel: str, tope: str) -> str:
    """Techo del nivel de confianza: `min(nivel, tope)` en `_NIVELES`."""
    if _RANGO[tope] < _RANGO[nivel]:
        return tope
    return nivel


def confianza(
    p_dec: float,
    estable_lambda: bool,
    n_obs: int,
    d2020: float | None,
    tope: str | None = None,
) -> str:
    """Nivel de confianza a partir de `p_dec` y señales adicionales.

    Orden de aplicación (plan §5.3 / metodología §7):
    1. Umbral base sobre `p_dec`: `alta` si `>= P_ALTA`, `media` si
       `>= P_DECISION`, si no `baja`.
    2. Si el veredicto cambia con `λ` (`estable_lambda is False`), bajar un
       nivel.
    3. Forzar `baja` si `n_obs == 1` o `d2020 < D_MIN_CONF` (cuando
       `d2020` aplica; en la capa de oferta no hay `D_2020` y se pasa
       `None`, sin efecto en esta regla).
    4. Aplicar `tope` (p. ej. `'media'` para `relacion != 'misma'` o para
       toda la capa de oferta) como techo final.
    """
    if p_dec >= P_ALTA:
        nivel = "alta"
    elif p_dec >= P_DECISION:
        nivel = "media"
    else:
        nivel = "baja"

    if not estable_lambda:
        nivel = _bajar_un_nivel(nivel)

    if n_obs == 1 or (d2020 is not None and d2020 < D_MIN_CONF):
        nivel = "baja"

    if tope is not None:
        nivel = _aplicar_tope(nivel, tope)

    return nivel


# ---------------------------------------------------------------------------
# Estructura compartida por demanda y oferta, a nivel AGEB o alcaldía (B6/B7a)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Simulacion:
    """Matriz `(n_unidades, n_sim)` de tasas proyectadas + metadatos.

    Estructura compartida por `simular_demanda`/`simular_oferta` (nivel
    AGEB) y por `agregar_alcaldia` (nivel alcaldía): una vez que se tiene una
    tasa log-lineal simulada por unidad y réplica, `resumir()` y
    `agregar_alcaldia()` son idénticos para ambas capas y ambos niveles.

    - `clave`: identificador de la unidad (`cvegeo` a nivel AGEB, `cve_mun`
      a nivel alcaldía).
    - `cve_mun`: alcaldía de cada unidad (igual a `clave` a nivel alcaldía).
    - `n_obs`: 2 o 1 (demanda AGEB), 2 (demanda alcaldía), 3 (oferta).
    - `base`: población/oferta base para proyectar y agregar por réplica
      (`D_2020` en demanda, `S` del último corte en oferta).
    - `d2020_conf`: `D_2020` para el criterio de confianza `D_MIN_CONF`
      (`None` en la capa de oferta, que no tiene ese concepto).
    - `tope`: techo de confianza por unidad (`'media'` o `None`).
    - `r_fut`: `(n, n_sim)` tasa anual proyectada (log-lineal) por réplica,
      con la incertidumbre principal (λ aleatorio en demanda).
    - `r_fut_lambdas`: `{lambda_fijo: (n, n_sim)}`, mismas réplicas de ruido
      pero con λ fijo (plan §5.3, sensibilidad); vacío en la capa de oferta
      (no aplica: `estable_lambda = True` siempre).
    - `horizonte_control`: horizonte (años, desde `t0`) usado internamente
      para pasar de tasa a nivel proyectado en `_control_por_razon`
      (demanda) y en `agregar_alcaldia` (ambas capas). NO es el horizonte
      que se reporta al cliente: el reporte usa varios horizontes a la vez
      (`config.HORIZONTES`), parametrizados en `resumir()`.
    """

    clave: np.ndarray
    cve_mun: np.ndarray
    n_obs: np.ndarray
    base: np.ndarray
    d2020_conf: np.ndarray | None
    tope: np.ndarray
    r_fut: np.ndarray
    r_fut_lambdas: dict[float, np.ndarray]
    horizonte_control: float


# Alias documentales (misma estructura, plan §5 firmas `SimDemanda`/`SimOferta`).
SimDemanda = Simulacion
SimOferta = Simulacion


# ---------------------------------------------------------------------------
# Demanda (B6): tasa directa + contracción EB + ancla CONAPO + simulación
# ---------------------------------------------------------------------------


def tasa_directa(
    d0: np.ndarray, d1: np.ndarray, dt: float
) -> tuple[np.ndarray, np.ndarray]:
    """Tasa log-lineal directa y su varianza Poisson (metodología §2.1).

    `r_hat = ln[(d1+0.5)/(d0+0.5)] / dt`;
    `psi = [1/(d1+0.5) + 1/(d0+0.5)] / dt**2`.
    """
    d0 = np.asarray(d0, dtype=float)
    d1 = np.asarray(d1, dtype=float)
    r_hat = np.log((d1 + 0.5) / (d0 + 0.5)) / dt
    psi = (1.0 / (d1 + 0.5) + 1.0 / (d0 + 0.5)) / dt**2
    return r_hat, psi


def contraccion_eb(
    r_hat: np.ndarray,
    psi: np.ndarray,
    rho_m_por_ageb: np.ndarray,
    usar_para_tau2: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Contracción Fay-Herriot hacia la media de la alcaldía (metodología §2.2-2.3).

    `tau2` por momentos, agrupado sobre todas las unidades recibidas (quien
    llama decide el universo: "toda la CDMX" en demanda, "todo AGEB con
    dato" en oferta): `tau2 = max(0, mean((r_hat-rho_m)**2) - mean(psi))`.
    `B = psi/(psi+tau2)`; `r_tilde = B*rho_m + (1-B)*r_hat`;
    `var_post = (1-B)*psi`.

    `usar_para_tau2`: máscara booleana opcional (Fase 3, metodología §6.2)
    que restringe QUÉ unidades participan en el promedio de `tau2` -- todas
    las unidades reciben su propio `B_i`/`r_tilde`/`var_post` de todas
    formas, con su `psi` real, sin excepción. Pensado para ajustes
    individuales numéricamente inestables (p. ej. `ajustar_oferta` con
    conteos casi separados, `psi` ~1e9): incluirlos en el promedio colapsa
    `tau2` a 0 para todo el grupo; excluirlos SOLO del promedio, pero
    seguir aplicándoles la fórmula con su `psi` real, hace que reciban la
    contracción casi total hacia la alcaldía que les corresponde (en vez de
    sesgar su propio resultado con un `psi` inventado). `None` (por
    omisión): usa todas las unidades, comportamiento sin cambios.
    """
    r_hat = np.asarray(r_hat, dtype=float)
    psi = np.asarray(psi, dtype=float)
    rho_m = np.asarray(rho_m_por_ageb, dtype=float)

    if usar_para_tau2 is None:
        r_hat_tau2, psi_tau2, rho_m_tau2 = r_hat, psi, rho_m
    else:
        mascara = np.asarray(usar_para_tau2, dtype=bool)
        r_hat_tau2, psi_tau2, rho_m_tau2 = r_hat[mascara], psi[mascara], rho_m[mascara]
        if r_hat_tau2.size == 0:  # defensivo: si la máscara vacía todo, usar el conjunto completo
            r_hat_tau2, psi_tau2, rho_m_tau2 = r_hat, psi, rho_m

    tau2 = max(0.0, float(np.mean((r_hat_tau2 - rho_m_tau2) ** 2) - np.mean(psi_tau2)))
    b = psi / (psi + tau2)
    r_tilde = b * rho_m + (1.0 - b) * r_hat
    var_post = (1.0 - b) * psi
    return r_tilde, var_post, tau2


def _interp_conapo_valor(conapo: pd.DataFrame, t: float) -> pd.Series:
    """Población 0-14 por `cve_mun` en el tiempo `t`, interpolación log-lineal.

    CONAPO publica cifras a mitad de año (`anio` -> tiempo `anio + 0.5`,
    metodología §2.6). La interpolación es lineal en `log(pob_0a14)` entre
    los dos años más cercanos (equivale a suponer una tasa constante entre
    ellos); fuera del rango cubierto por `conapo` se usa el valor extremo
    (comportamiento de `np.interp`, sin extrapolación log-lineal).
    """
    resultados: dict[str, float] = {}
    for mun, grupo in conapo.groupby("cve_mun"):
        grupo = grupo.sort_values("anio")
        tiempos = grupo["anio"].to_numpy(dtype=float) + 0.5
        log_valores = np.log(grupo["pob_0a14"].to_numpy(dtype=float))
        resultados[mun] = float(np.exp(np.interp(t, tiempos, log_valores)))
    return pd.Series(resultados, name="pob_0a14")


def tasa_conapo(conapo: pd.DataFrame, t0: float, t1: float) -> pd.Series:
    """Tasa log-lineal anualizada de CONAPO por `cve_mun` entre `t0` y `t1`.

    `ln[C_m(t1)/C_m(t0)] / (t1 - t0)`, con `C_m(t)` interpolado
    log-linealmente (`_interp_conapo_valor`). Reutilizada tanto para el ancla
    futura (`t0=2020.5, t1=T_HOR`, metodología §2.3) como para la
    discrepancia censo-CONAPO 2010-2020 que alimenta `sigma_C`
    (`t0=T_2010, t1=T_2020`, metodología §2.6).
    """
    valor0 = _interp_conapo_valor(conapo, t0)
    valor1 = _interp_conapo_valor(conapo, t1)
    return np.log(valor1 / valor0) / (t1 - t0)


def _control_por_razon(
    r_pre: np.ndarray,
    base: np.ndarray,
    cve_mun_por_unidad: np.ndarray,
    razon_conapo_por_mun: pd.Series,
    horizonte: float,
) -> np.ndarray:
    """Reescala `r_pre` por alcaldía y réplica para reproducir la razón CONAPO.

    Metodología §2.5 / plan §5.1 paso 8: para cada alcaldía `m` y réplica
    `s`, `k_m^s = razon_conapo[m] * sum(base_i) / sum(base_i * exp(r_pre_i^s
    * horizonte))`; se suma `ln(k_m^s)/horizonte` a `r_pre_i^s` (mantiene la
    forma log-lineal). Tras esto, por construcción algebraica,
    `sum(base_i * exp(r_controlado_i^s * horizonte)) / sum(base_i) ==
    razon_conapo[m]` exactamente (hasta precisión de punto flotante): es la
    identidad que verifica `test_modelos.py`.
    """
    cve_mun_arr = np.asarray(cve_mun_por_unidad)
    base = np.asarray(base, dtype=float)
    proyectado_pre = base[:, None] * np.exp(r_pre * horizonte)  # (n, n_sim)

    r_controlado = np.empty_like(r_pre)
    for m in sorted(set(cve_mun_arr.tolist())):
        idx = np.where(cve_mun_arr == m)[0]
        base_m = base[idx].sum()
        proyectado_m = proyectado_pre[idx, :].sum(axis=0)  # (n_sim,)
        objetivo = razon_conapo_por_mun.loc[m] * base_m
        k_m = objetivo / proyectado_m  # (n_sim,)
        r_controlado[idx, :] = r_pre[idx, :] + (np.log(k_m) / horizonte)[None, :]
    return r_controlado


def simular_demanda(
    panel_d: pd.DataFrame,
    conapo: pd.DataFrame,
    rng: np.random.Generator,
    n_sim: int = N_SIM,
    lam: float | None = None,
) -> Simulacion:
    """Simulación Monte Carlo de la tasa de demanda futura por AGEB (B6).

    Pasos 1-9 de `plans/backend_plan.md` §5.1 / `docs/metodologia.md` §2:
    tasa directa (`tasa_directa`) -> contracción EB hacia la alcaldía
    (`contraccion_eb`, `tau2` agrupado sobre las AGEB con `r_hat` calculable)
    -> ancla CONAPO futura + persistencia `lam` -> control por razón
    (`_control_por_razon`, aplicado ANTES del choque de alcaldía) -> choque
    compartido `eps_m` (después del control, metodología §2.5 nota) ->
    `n_sim` réplicas.

    Solo entran las AGEB de `panel_d` con `motivo_sin_datos` nulo (rurales,
    suprimidas, `D_2020 < 20` y sin censo quedan fuera: `sin_datos`, se
    resuelven en `exportar.py`). Las AGEB `sin_contraparte` (sin `d_2010`)
    quedan con `r_tilde = rho_m` y `var_post = tau2` (límite `psi -> inf` de
    `contraccion_eb`, `n_obs = 1`).

    `lam`: si es `None`, la réplica principal usa `lam^s ~ U(0.25, 1)`
    (incertidumbre de persistencia); si se fija un valor, la réplica
    principal usa ese `lam` constante (p. ej. para `backtest.py`). En ambos
    casos se calculan además las 3 variantes de `lam` fijo de `LAMBDAS_SENS`
    (reutilizando los mismos sorteos de `r_post`/`eps_m`) para el criterio
    `estable_lambda` de `confianza()`.
    """
    df = panel_d.loc[panel_d["motivo_sin_datos"].isna()].reset_index(drop=True)
    n = len(df)
    tiene_r = df["d_2010"].notna().to_numpy()

    dt = T_2020 - T_2010
    r_hat = np.full(n, np.nan)
    psi = np.full(n, np.nan)
    r_hat[tiene_r], psi[tiene_r] = tasa_directa(
        df.loc[tiene_r, "d_2010"].to_numpy(dtype=float),
        df.loc[tiene_r, "d_2020"].to_numpy(dtype=float),
        dt,
    )

    # rho_m censal (paso 2): mismas fórmulas, sumas de la alcaldía, solo con
    # las AGEB que aportan r_hat (tienen d_2010 y d_2020).
    agregado = (
        df.loc[tiene_r]
        .groupby("cve_mun")[["d_2010", "d_2020"]]
        .sum()
    )
    rho_m_serie = np.log((agregado["d_2020"] + 0.5) / (agregado["d_2010"] + 0.5)) / dt
    rho_m_por_unidad = df["cve_mun"].map(rho_m_serie).to_numpy(dtype=float)

    r_tilde = np.full(n, np.nan)
    var_post = np.full(n, np.nan)
    r_tilde[tiene_r], var_post[tiene_r], tau2 = contraccion_eb(
        r_hat[tiene_r], psi[tiene_r], rho_m_por_unidad[tiene_r]
    )
    # sin_contraparte (paso 4, límite psi -> inf): r_tilde = rho_m, var_post = tau2.
    r_tilde[~tiene_r] = rho_m_por_unidad[~tiene_r]
    var_post[~tiene_r] = tau2

    # Piso de incertidumbre (metodología §2.7, calibrado en backtest.py sobre
    # data/outputs/backtest.json): la varianza posterior nunca baja de
    # SIGMA_MIN_DEMANDA**2. Con los datos reales el piso calibrado es 0.0 (el
    # error de conteo ya sobrecubre, ver config.py), así que hoy este `maximum`
    # no cambia nada -- se aplica de todas formas para que una recalibración
    # futura (nueva corrida del backtest) solo tenga que cambiar la constante.
    var_post = np.maximum(var_post, SIGMA_MIN_DEMANDA**2)

    r_post = r_tilde[:, None] + rng.standard_normal((n, n_sim)) * np.sqrt(var_post)[:, None]

    # Choque compartido por alcaldía (paso 7): sigma_C = |rho_m,censo - rho_m,CONAPO| 2010-2020.
    rho_m_conapo_10_20 = tasa_conapo(conapo, T_2010, T_2020)
    sigma_c_por_mun = (rho_m_serie - rho_m_conapo_10_20.reindex(rho_m_serie.index)).abs()
    munes = sorted(df["cve_mun"].unique())
    eps_por_mun = {m: rng.standard_normal(n_sim) * sigma_c_por_mun.loc[m] for m in munes}
    eps_por_unidad = np.vstack([eps_por_mun[m] for m in df["cve_mun"]])

    # Ancla CONAPO futura (paso 5): mitad de año a mitad de año, 7 años exactos.
    rho_m_conapo_fut = tasa_conapo(conapo, 2020.5, T_HOR)
    rho_m_conapo_fut_por_unidad = df["cve_mun"].map(rho_m_conapo_fut).to_numpy(dtype=float)

    # Razón de control (paso 8): nivel censal exacto en T_2020 (interpolado, paso 6).
    razon_control_por_mun = _interp_conapo_valor(conapo, T_HOR) / _interp_conapo_valor(
        conapo, T_2020
    )
    horizonte_control = T_HOR - T_2020
    d_2020 = df["d_2020"].to_numpy(dtype=float)
    cve_mun_arr = df["cve_mun"].to_numpy()

    def _proyectar(lam_vec: np.ndarray) -> np.ndarray:
        r_pre = rho_m_conapo_fut_por_unidad[:, None] + lam_vec[None, :] * (
            r_post - rho_m_por_unidad[:, None]
        )
        r_controlado = _control_por_razon(
            r_pre, d_2020, cve_mun_arr, razon_control_por_mun, horizonte_control
        )
        return r_controlado + eps_por_unidad

    lam_vec_principal = (
        rng.uniform(*LAMBDA_PREVIA, size=n_sim) if lam is None else np.full(n_sim, float(lam))
    )
    r_fut_principal = np.clip(_proyectar(lam_vec_principal), -_TASA_MAX, _TASA_MAX)
    r_fut_lambdas = {
        lam_fijo: np.clip(_proyectar(np.full(n_sim, lam_fijo)), -_TASA_MAX, _TASA_MAX)
        for lam_fijo in LAMBDAS_SENS
    }

    n_obs = np.where(tiene_r, 2, 1)
    relacion = df["relacion"].to_numpy()
    tope = np.where(
        np.isin(relacion, ["division", "fusion_o_expansion", "cambio_limites"]),
        "media",
        None,
    )

    return Simulacion(
        clave=df["cvegeo"].to_numpy(),
        cve_mun=cve_mun_arr,
        n_obs=n_obs,
        base=d_2020,
        d2020_conf=d_2020,
        tope=tope,
        r_fut=r_fut_principal,
        r_fut_lambdas=r_fut_lambdas,
        horizonte_control=horizonte_control,
    )


# ---------------------------------------------------------------------------
# Oferta (B7a): Poisson log-lineal (Newton-Raphson vectorizado) + EB
# ---------------------------------------------------------------------------


def _newton_raphson_poisson(
    x: np.ndarray, y: np.ndarray, max_iter: int = 25, tol: float = 1e-10
) -> tuple[np.ndarray, np.ndarray]:
    """Ajuste Poisson log-lineal vectorizado por fila de `y` (IRLS = Newton-Raphson).

    `x`: diseño compartido `(n_t, p)`. `y`: `(n_unidades, n_t)` conteos.
    Devuelve `(beta, cov)` con `beta: (n_unidades, p)` y
    `cov: (n_unidades, p, p)` (inversa de la información de Fisher en el
    óptimo). Sin bucle por unidad: todas comparten el mismo diseño `x`
    (mismos 3 tiempos de corte), así que cada paso IRLS es una operación
    `einsum`/`solve` por lotes sobre las `n_unidades` filas de `y`.
    """
    n_unidades, p = y.shape[0], x.shape[1]
    beta = np.zeros((n_unidades, p))
    medias = np.clip(y.mean(axis=1), 0.1, None)
    beta[:, 0] = np.log(medias)

    xtwx = np.eye(p)[None, :, :].repeat(n_unidades, axis=0)  # por si max_iter=0
    for _ in range(max_iter):
        eta = np.clip(beta @ x.T, -30, 30)
        mu = np.exp(eta)
        z = eta + (y - mu) / mu
        xtwx = np.einsum("tk,nt,tl->nkl", x, mu, x)
        xtwz = np.einsum("tk,nt->nk", x, mu * z)
        beta_nuevo = np.linalg.solve(xtwx, xtwz[..., None])[..., 0]
        if np.max(np.abs(beta_nuevo - beta)) < tol:
            beta = beta_nuevo
            break
        beta = beta_nuevo

    eta = np.clip(beta @ x.T, -30, 30)
    mu = np.exp(eta)
    xtwx = np.einsum("tk,nt,tl->nkl", x, mu, x)
    cov = np.linalg.inv(xtwx)
    return beta, cov


def _columnas_s_oferta() -> list[str]:
    """Nombre de columna de conteos crudos por corte, en orden cronológico."""
    return [
        f"s_{edicion.replace('-', '_')}"
        for edicion, _t in sorted(CORTES_OFERTA.items(), key=lambda kv: kv[1])
    ]


# Umbral de "ajuste numéricamente confiable" (metodología §6.2, hallazgo de la Fase 3 -- no
# documentado en el plan original, descubierto al verificar que la sobredispersión y el piso
# NO bastaban para corregir el hallazgo 0.5 de `correccion/action_plan.md`, "IC de oferta
# degenerados"). Conteos casi separados (p. ej. [1,0,0]: un establecimiento en 2016, ninguno
# después) hacen que la matriz de información de Fisher de `_newton_raphson_poisson` sea casi
# singular: su inversa (`var_b`) explota a ~3e9, frente a ~0.01-0.1 en ajustes normales
# (verificado con datos reales: 73 de 2023 AGEB, todas con este patrón, separación nítida sin
# valores intermedios). Ese puñado de AGEB, si se deja igual, domina el PROMEDIO que
# `contraccion_eb` usa para `tau2` (agrupado por alcaldía) y lo colapsa a 0 para TODA la
# alcaldía -- el origen real del IC95 degenerado, no solo falta de sobredispersión.
#
# La corrección NO topa `var_b` (eso sesgaría la contracción de esas AGEB específicas: con un
# `var_b` artificialmente pequeño recibirían MENOS contracción hacia la alcaldía, justo lo
# contrario de lo que corresponde cuando el ajuste no es confiable). En vez de eso, estas AGEB
# se EXCLUYEN solo del cómputo de `tau2` (`contraccion_eb(..., usar_para_tau2=...)`): siguen
# recibiendo su propio `B_i`/`r_tilde`/`var_post` con su `var_b` real (typically ~100% de
# contracción hacia la alcaldía, que es la respuesta correcta para un ajuste no confiable).
_VAR_B_CONFIABLE_MAXIMA: float = 10.0

# Tope numérico (no estadístico) sobre la tasa `r`/`b` simulada. `var_post` solo tiene piso
# (`SIGMA_MIN_OFERTA`, config.py), nunca techo: es correcto que quede enorme cuando el ajuste de
# alcaldía de una celda muy escasa (p. ej. una celda `__no_especificado` con un puñado de
# establecimientos en una sola alcaldía, Fase 5 rework de sector) está genuinamente mal
# determinado -- "no inventar precisión que no existe" (docstring de `simular_oferta`) corta en
# las dos direcciones. Sin tope, algunas réplicas Monte Carlo generan `b` de cientos (varias
# desviaciones estándar sobre un `var_post` de miles); `exp(b*horizonte)` desborda a `inf` en
# float64 (> ~709) en CUALQUIER consumidor de `Simulacion.r_fut` (`resumir`, `agregar_alcaldia`,
# `exportar.nivel_en`), y una vez que hay `inf` de por medio, un `np.percentile`/`np.log` puede
# devolver `nan` -- un problema numérico, no estadístico, que rompe `validar_contrato` (`ic95` debe
# contener `delta_pct`, `nan` no lo hace nunca). Por eso el tope se aplica una sola vez, aquí, al
# construir la `Simulacion`, no en cada consumidor por separado. `_TASA_MAX=20` acota
# `delta_pct`/`ic95` a un techo absurdamente generoso (`exp(20)≈4.85e8`, es decir ±4.85e10 % --
# nunca se acerca ningún valor sustantivo real) que solo actúa sobre estas colas patológicas,
# nunca sobre una tasa de crecimiento con sentido económico.
_TASA_MAX: float = 20.0


def ajustar_oferta(panel_o: pd.DataFrame) -> pd.DataFrame:
    """Pendiente Poisson log-lineal por AGEB sobre los 3 cortes de oferta (B7a).

    `log E[S_it] = a_i + b_i * (t - t_centro)`, `t_centro` = fecha del corte
    intermedio (`CORTES_OFERTA["2019-11"]`), ajuste Newton-Raphson vectorizado
    (`_newton_raphson_poisson`, sin bucle `statsmodels` por AGEB; el test de
    paridad sí usa `statsmodels`, por unidad, solo para verificar).

    Columnas de salida: `cvegeo, cve_mun, a_hat, b_hat, var_b, sin_datos,
    ajuste_confiable` (`sin_datos = True` si `S = 0` en los 3 cortes: esas
    filas no se ajustan, quedan con `a_hat/b_hat/var_b = NaN`;
    `ajuste_confiable = var_b < _VAR_B_CONFIABLE_MAXIMA`, ver su comentario)
    + una columna `s_<edicion>` por corte (conteos crudos, orden
    cronológico), que `simular_oferta` reutiliza para ajustar la pendiente
    de la alcaldía sin volver a leer `panel_o`.
    """
    t_centro = CORTES_OFERTA["2019-11"]
    tiempos = sorted(CORTES_OFERTA.values())

    tabla = panel_o.pivot(index="cvegeo", columns="t", values="s")[tiempos]
    cve_mun = (
        panel_o.drop_duplicates("cvegeo").set_index("cvegeo")["cve_mun"].reindex(tabla.index)
    )

    y = tabla.to_numpy(dtype=float)
    x_diseno = np.column_stack([np.ones(len(tiempos)), np.array(tiempos) - t_centro])

    n = y.shape[0]
    con_datos = y.sum(axis=1) > 0
    a_hat = np.full(n, np.nan)
    b_hat = np.full(n, np.nan)
    var_b = np.full(n, np.nan)

    if con_datos.any():
        beta, cov = _newton_raphson_poisson(x_diseno, y[con_datos])
        a_hat[con_datos] = beta[:, 0]
        b_hat[con_datos] = beta[:, 1]
        var_b[con_datos] = cov[:, 1, 1]

    ajuste_confiable = con_datos & (var_b < _VAR_B_CONFIABLE_MAXIMA)

    salida = pd.DataFrame(
        {
            "cvegeo": tabla.index,
            "cve_mun": cve_mun.to_numpy(),
            "a_hat": a_hat,
            "b_hat": b_hat,
            "var_b": var_b,
            "sin_datos": ~con_datos,
            "ajuste_confiable": ajuste_confiable,
        }
    )
    for nombre_col, columna_t in zip(_columnas_s_oferta(), tiempos):
        salida[nombre_col] = tabla[columna_t].to_numpy()
    return salida.reset_index(drop=True)


def calcular_phi_por_alcaldia(ajuste: pd.DataFrame) -> pd.Series:
    """Factor de sobredispersión quasi-Poisson `phi_m` por alcaldía (metodología §6.2).

    `phi_m = chi2(Pearson)/gl`, agrupado por alcaldía: cada AGEB aporta
    exactamente 1 grado de libertad (3 cortes, 2 parámetros `a_i, b_i` ya
    ajustados en `ajustar_oferta`), así que un `phi` individual por AGEB
    sería puro ruido -- se agrega toda la alcaldía. `phi_m >= PHI_MINIMO`
    (nunca reduce la varianza; es una corrección estadística estándar de GLM
    quasi-Poisson, no un parámetro libre).

    Devuelve una `pd.Series` indexada por `cve_mun`. AGEB `sin_datos` (S=0 en
    los 3 cortes) se excluyen del cómputo (no tienen `a_hat`/`b_hat`).
    """
    df = ajuste.loc[~ajuste["sin_datos"]].reset_index(drop=True)
    columnas_s = _columnas_s_oferta()
    tiempos = np.array(sorted(CORTES_OFERTA.values()))
    t_centro = CORTES_OFERTA["2019-11"]

    y = df[columnas_s].to_numpy(dtype=float)
    mu = np.exp(
        df["a_hat"].to_numpy(dtype=float)[:, None]
        + df["b_hat"].to_numpy(dtype=float)[:, None] * (tiempos - t_centro)[None, :]
    )
    mu = np.clip(mu, 1e-6, None)
    pearson = (y - mu) ** 2 / mu  # (n_ageb, n_t)

    resultado: dict[str, float] = {}
    for m, grupo in df.groupby("cve_mun"):
        idx = grupo.index.to_numpy()
        gl = len(idx)  # 1 grado de libertad por AGEB
        if gl == 0:
            continue
        chi2 = float(pearson[idx, :].sum())
        resultado[m] = max(PHI_MINIMO, chi2 / gl)
    return pd.Series(resultado, name="phi_m")


def simular_oferta(
    ajuste: pd.DataFrame, rng: np.random.Generator, n_sim: int = N_SIM
) -> Simulacion:
    """Simulación Monte Carlo de la pendiente de oferta futura por AGEB (B7a).

    EB hacia la pendiente Poisson de la alcaldía (mismo `contraccion_eb` de
    B6, reajustada aquí sobre la suma de conteos `S` por alcaldía y corte);
    sin control externo (metodología §6). Excluye las AGEB `sin_datos`
    (`S = 0` en los 3 cortes; las rurales ya están fuera de `panel_o`/
    `ajuste`, ver `panel.py`). Tope de confianza `'media'` siempre y
    `d2020_conf = None` (no aplica el criterio `D_MIN_CONF` en esta capa).

    Sobredispersión (metodología §6.2, Fase 3): `var_b` se infla por
    `phi_m` (`calcular_phi_por_alcaldia`) **antes** de la contracción EB
    (para que la propia contracción ya vea la varianza correcta), y la
    varianza posterior resultante nunca baja de `SIGMA_MIN_OFERTA**2`.

    `tau2` se estima **solo** con las AGEB de `ajuste_confiable`
    (`ajustar_oferta`, conteos sin separación numérica): un puñado de
    ajustes con `var_b` astronómico (~1e9, por conteos casi separados como
    `[1,0,0]`) colapsaría `tau2` a 0 para toda la ciudad si se incluyeran en
    ese promedio (`contraccion_eb`'s docstring). Las AGEB no confiables
    siguen recibiendo su propio `B_i`/`b_tilde`/`var_post` con su `var_b`
    real (nunca se excluyen de la simulación ni del contrato): con ese
    `tau2` ya sano, su propio `psi` enorme las contrae casi del todo hacia
    la alcaldía, que es la respuesta correcta para un ajuste no confiable.

    **La incertidumbre de la propia pendiente de la alcaldía se propaga**
    (hallazgo adicional de la Fase 3, no estaba en el plan original): con
    `tau2` genuinamente bajo (las 16 alcaldías de CDMX muestran menos
    dispersión ENTRE sus AGEB que el ruido de conteo `psi` DENTRO de cada
    una, un resultado honesto del método de momentos, no un error), `B_i`
    queda cerca de 1 para casi todas las AGEB y `(1-B_i)*psi_i` por sí solo
    colapsa a ~0 -- pero eso trata `b_m` (la pendiente de la alcaldía) como
    si fuera una constante exacta, cuando es ella misma una estimación con
    su propia varianza muestral (`_cov_mun`, antes descartada). Se propaga
    con la aproximación de primer orden `var_post += B_i**2 * var(b_m)`
    (`r_tilde = B*rho_m + (1-B)*r_hat`, tratando a `rho_m` como aleatoria):
    nunca inventa precisión que no exista, al contrario, reconoce una fuente
    de incertidumbre real que la fórmula ingenua de Fay-Herriot pasaba por
    alto. Es la causa real del hallazgo 0.5 de `correccion/action_plan.md`.
    """
    df = ajuste.loc[~ajuste["sin_datos"]].reset_index(drop=True)
    n = len(df)
    columnas_s = _columnas_s_oferta()
    tiempos = sorted(CORTES_OFERTA.values())
    t_centro = CORTES_OFERTA["2019-11"]
    x_diseno = np.column_stack([np.ones(len(tiempos)), np.array(tiempos) - t_centro])

    if n == 0:
        # Celda vacía en toda la ciudad (posible desde el cruce por sector de la Fase 5
        # rework: p. ej. `farmacias__publico`/`farmacias__privado` en salud tienen 0
        # establecimientos en las 3 ediciones -- DENUE nunca clasifica farmacias con
        # `Sector` distinto de "No especificado"). Sin AGEB con dato no hay nada que
        # ajustar ni agregar por alcaldía: `Simulacion` vacía, que `resumir`/
        # `agregar_alcaldia`/`construir_capa` ya saben tratar como `sin_datos` en todas
        # las unidades (motivo `sin_establecimientos`, `motivos_oferta_por_clave`).
        return Simulacion(
            clave=np.array([], dtype=object),
            cve_mun=np.array([], dtype=object),
            n_obs=np.zeros(0, dtype=int),
            base=np.zeros(0, dtype=float),
            d2020_conf=None,
            tope=np.zeros(0, dtype=object),
            r_fut=np.empty((0, n_sim)),
            r_fut_lambdas={},
            horizonte_control=HORIZONTES["h3"] - max(CORTES_OFERTA.values()),
        )

    agregado_mun = df.groupby("cve_mun")[columnas_s].sum()
    beta_mun, cov_mun = _newton_raphson_poisson(x_diseno, agregado_mun.to_numpy(dtype=float))
    b_m_serie = pd.Series(beta_mun[:, 1], index=agregado_mun.index)
    var_b_m_serie = pd.Series(cov_mun[:, 1, 1], index=agregado_mun.index)
    b_m_por_unidad = df["cve_mun"].map(b_m_serie).to_numpy(dtype=float)
    var_b_m_por_unidad = df["cve_mun"].map(var_b_m_serie).to_numpy(dtype=float)

    phi_por_mun = calcular_phi_por_alcaldia(ajuste)
    phi_por_unidad = df["cve_mun"].map(phi_por_mun).fillna(PHI_MINIMO).to_numpy(dtype=float)

    b_hat = df["b_hat"].to_numpy(dtype=float)
    var_b = df["var_b"].to_numpy(dtype=float) * phi_por_unidad
    ajuste_confiable = df["ajuste_confiable"].to_numpy(dtype=bool)
    b_tilde, var_post, _tau2_b = contraccion_eb(
        b_hat, var_b, b_m_por_unidad, usar_para_tau2=ajuste_confiable
    )
    b_i = var_b / (var_b + _tau2_b)  # mismo B que contraccion_eb calcula internamente
    var_post = var_post + (b_i**2) * var_b_m_por_unidad * phi_por_unidad
    var_post = np.maximum(var_post, SIGMA_MIN_OFERTA**2)

    b_post = b_tilde[:, None] + rng.standard_normal((n, n_sim)) * np.sqrt(var_post)[:, None]
    b_post = np.clip(b_post, -_TASA_MAX, _TASA_MAX)

    ultimo_corte = max(CORTES_OFERTA.values())
    # Oferta nunca reporta más allá de h3 (config.HORIZONTES_OFERTA): no tiene
    # sentido controlar/proyectar el nivel base más lejos que eso.
    horizonte_control = HORIZONTES["h3"] - ultimo_corte
    base = df[columnas_s[-1]].to_numpy(dtype=float)  # S del corte más reciente (2024-11)

    return Simulacion(
        clave=df["cvegeo"].to_numpy(),
        cve_mun=df["cve_mun"].to_numpy(),
        n_obs=np.full(n, 3),
        base=base,
        d2020_conf=None,
        tope=np.full(n, "media", dtype=object),
        r_fut=b_post,
        r_fut_lambdas={},
        horizonte_control=horizonte_control,
    )


# ---------------------------------------------------------------------------
# Resumen por unidad y agregación a alcaldía (B6/B7a, plan §5.4)
# ---------------------------------------------------------------------------


def resumir(
    sim: Simulacion, horizontes: dict[str, float], delta: float = DELTA
) -> dict[str, pd.DataFrame]:
    """Una tabla por horizonte de reporte: tasa, delta, IC95, veredicto.

    Válido tanto para demanda como para oferta y tanto a nivel AGEB como
    alcaldía (plan §5.1 paso 9 / §5.4): la regla es la misma una vez que se
    tiene la matriz `(n, n_sim)` de tasas proyectadas `sim.r_fut`.
    `estable_lambda` (plan §5.3) compara el veredicto bajo los 3 valores
    fijos de `sim.r_fut_lambdas`; si está vacío (capa de oferta, que no
    tiene λ), se considera estable por definición.

    `horizontes`: `{clave: t_horizonte}` en años decimales absolutos (p. ej.
    `config.HORIZONTES` para demanda, `{h: config.HORIZONTES[h] for h in
    config.HORIZONTES_OFERTA}` para oferta). Para cada horizonte se calcula
    `horizonte_reporte = t_horizonte - config.T_BASE` y `delta_draws_pct =
    100*(exp(r*horizonte_reporte) - 1)` (`delta_pct`/`ic95`/`tasa_anual_pct`
    se miden desde `T_BASE`, NO desde `T_2020` ni desde `sim.horizonte_control`).

    Importante: el veredicto y la confianza NO dependen del horizonte de
    reporte (solo de la tasa `r` simulada, que es una sola por unidad y
    réplica); por diseño salen IGUALES en todas las tablas devueltas (`h1`,
    `h3`, `h5`). Lo único que cambia entre horizontes es `delta_pct`/`ic95`
    /`tasa_anual_pct` (crecen en magnitud con el horizonte, vía `exp`).

    Devuelve `dict[str, pd.DataFrame]`, una entrada por clave de
    `horizontes`, con las mismas columnas de antes: `clave, cve_mun, n_obs,
    tasa_anual_pct, delta_pct, ic95, p_sube, p_baja, p_mantiene, p_dec,
    veredicto, confianza`.
    """
    r = sim.r_fut
    n = r.shape[0]

    p_sube = (r > delta).mean(axis=1)
    p_baja = (r < -delta).mean(axis=1)
    p_mantiene = (np.abs(r) <= delta).mean(axis=1)

    veredictos: list[str] = []
    p_decs: list[float] = []
    for i in range(n):
        v, p = veredicto(float(p_sube[i]), float(p_baja[i]), float(p_mantiene[i]))
        veredictos.append(v)
        p_decs.append(p)

    if sim.r_fut_lambdas:
        veredictos_por_lambda: dict[float, list[str]] = {}
        for lam_fijo, r_lam in sim.r_fut_lambdas.items():
            p_s = (r_lam > delta).mean(axis=1)
            p_b = (r_lam < -delta).mean(axis=1)
            p_m = (np.abs(r_lam) <= delta).mean(axis=1)
            veredictos_por_lambda[lam_fijo] = [
                veredicto(float(p_s[i]), float(p_b[i]), float(p_m[i]))[0] for i in range(n)
            ]
        estable_lambda = [
            len({veredictos_por_lambda[lam][i] for lam in veredictos_por_lambda}) == 1
            for i in range(n)
        ]
    else:
        estable_lambda = [True] * n

    niveles = [
        confianza(
            p_decs[i],
            estable_lambda[i],
            int(sim.n_obs[i]),
            float(sim.d2020_conf[i]) if sim.d2020_conf is not None else None,
            sim.tope[i],
        )
        for i in range(n)
    ]

    resultado: dict[str, pd.DataFrame] = {}
    for clave_horizonte, t_horizonte in horizontes.items():
        horizonte_reporte = t_horizonte - T_BASE
        tasa_anual_pct = 100.0 * np.median(r, axis=1)
        delta_draws_pct = 100.0 * (np.exp(r * horizonte_reporte) - 1.0)
        delta_pct = np.median(delta_draws_pct, axis=1)
        ic95 = np.percentile(delta_draws_pct, [2.5, 97.5], axis=1).T  # (n, 2)

        resultado[clave_horizonte] = pd.DataFrame(
            {
                "clave": sim.clave,
                "cve_mun": sim.cve_mun,
                "n_obs": sim.n_obs.astype(int),
                "tasa_anual_pct": tasa_anual_pct,
                "delta_pct": delta_pct,
                "ic95": list(ic95),
                "p_sube": p_sube,
                "p_baja": p_baja,
                "p_mantiene": p_mantiene,
                "p_dec": p_decs,
                "veredicto": veredictos,
                "confianza": niveles,
            }
        )
    return resultado


def agregar_alcaldia(sim: Simulacion) -> Simulacion:
    """Agrega `sim` (nivel AGEB) a nivel alcaldía, por réplica (plan §5.4).

    `base_m = sum(base_i)`; `D_hat_m^s = sum(base_i * exp(r_fut_i^s *
    horizonte))`; tasa de alcaldía = `ln(D_hat_m^s / base_m) / horizonte`
    (log-razón anualizada, no promedio de tasas). `n_obs` de la alcaldía =
    el máximo de sus AGEB (2 en demanda, salvo alcaldías sin ninguna AGEB
    `misma`/`división`/etc. con `d_2010`, caso no observado hoy; 3 en
    oferta). `d2020_conf` = suma de `D_2020` (solo demanda); `tope` = `None`
    en demanda (la agregación ya no arrastra el motivo AGEB-por-AGEB del
    tope), `'media'` en oferta (toda la capa).

    **Alcaldías con `base_m = 0` se excluyen** (nunca `nan`): posible en oferta desde el cruce
    por sector de la Fase 5 rework -- una alcaldía puede tener AGEB con dato en cortes anteriores
    (ninguna de sus AGEB quedó `sin_datos` a nivel individual) pero cero establecimientos de esa
    celda en el corte más reciente (`base` = S del corte 2024-11), de modo que `base_m` (la suma)
    da exactamente 0. Una tasa a partir de un nivel base cero no es una cantidad definida
    (`log(0/0)`); se trata igual que una unidad `sin_datos`: se excluye de `Simulacion` (nunca
    aparece en `resumir()`) para que `construir_capa` la marque `sin_datos` por ausencia, el mismo
    mecanismo ya usado para AGEB sin ningún establecimiento en los 3 cortes.
    """
    munes_todas = sorted(set(np.asarray(sim.cve_mun).tolist()))
    n_sim = sim.r_fut.shape[1]
    es_demanda = sim.d2020_conf is not None

    proyectado = sim.base[:, None] * np.exp(sim.r_fut * sim.horizonte_control)
    proyectado_lambdas = {
        lam: sim.base[:, None] * np.exp(r * sim.horizonte_control)
        for lam, r in sim.r_fut_lambdas.items()
    }

    munes: list[str] = []
    base_mun_lista: list[float] = []
    r_fut_mun_lista: list[np.ndarray] = []
    n_obs_mun_lista: list[int] = []
    d2020_conf_mun_lista: list[float] = []
    tope_mun_lista: list[str | None] = []
    r_fut_lambdas_mun: dict[float, list[np.ndarray]] = {lam: [] for lam in sim.r_fut_lambdas}

    for m in munes_todas:
        idx = np.where(np.asarray(sim.cve_mun) == m)[0]
        base_m = sim.base[idx].sum()
        if base_m == 0:
            continue
        munes.append(m)
        base_mun_lista.append(base_m)
        r_fut_mun_lista.append(
            np.log(proyectado[idx, :].sum(axis=0) / base_m) / sim.horizonte_control
        )
        n_obs_mun_lista.append(int(sim.n_obs[idx].max()))
        if es_demanda:
            d2020_conf_mun_lista.append(sim.d2020_conf[idx].sum())
            tope_mun_lista.append(None)
        else:
            tope_mun_lista.append("media")
        for lam, proy_lam in proyectado_lambdas.items():
            r_fut_lambdas_mun[lam].append(
                np.log(proy_lam[idx, :].sum(axis=0) / base_m) / sim.horizonte_control
            )

    return Simulacion(
        clave=np.array(munes),
        cve_mun=np.array(munes),
        n_obs=np.array(n_obs_mun_lista, dtype=int),
        base=np.array(base_mun_lista, dtype=float),
        d2020_conf=np.array(d2020_conf_mun_lista, dtype=float) if es_demanda else None,
        tope=np.array(tope_mun_lista, dtype=object),
        r_fut=np.array(r_fut_mun_lista) if munes else np.empty((0, n_sim)),
        r_fut_lambdas={
            lam: (np.array(filas) if filas else np.empty((0, n_sim)))
            for lam, filas in r_fut_lambdas_mun.items()
        },
        horizonte_control=sim.horizonte_control,
    )
