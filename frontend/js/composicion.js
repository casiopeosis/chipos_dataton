// frontend/js/composicion.js
//
// MOTOR DE COMPOSICIÓN CLIENTE (plans/frontend_specs.md §17.4, docs/metodologia.md §10).
// Puro, sin DOM: recibe los registros ya indexados por api.js y devuelve cobertura, índice de
// oportunidad, índice de disponibilidad e índice compuesto para el universo activo de AGEB (o
// alcaldías), recalculando en el navegador cada vez que cambian filtro/pesos/horizonte/segmento
// (correccion/frontend_requisitos.md §9/§21/§22: "los pesos y filtros no alteran los datos
// originales" y "sin recargar la página"). Ningún componente de UI lee `registro.celdas`/
// `registro.segmentos` crudos ni repite estas fórmulas: todos consumen la salida de este módulo
// (plans/frontend_plan.md §2).
//
// El backend publica, por horizonte, `nivel_base` + `delta_pct` (nivel proyectado en el horizonte
// = `nivel_base * (1 + delta_pct/100)`) por segmento de demanda y por celda de oferta -- nunca las
// réplicas Monte Carlo crudas (impublicables en tamaño). Este módulo combina esos ingredientes
// exactamente como el backend combina AGEB en alcaldía (`modelos.agregar_alcaldia`): sumar NIVELES
// en vez de promediar tasas, y derivar la tasa implícita de la combinación por log-razón. Es el
// mismo principio matemático aplicado del lado del cliente, documentado aquí en vez de asumido.

/** K de normalización del ajuste de tendencia (docs/metodologia.md §10.2, `K_OPORTUNIDAD_DEFECTO`
 * en `features.py`): constante interna, nunca expuesta al usuario. */
export const K_OPORTUNIDAD = 5.0;

/** Límite del ajuste de tendencia, mismo valor que `features.AJUSTE_TENDENCIA_MAX`. */
const AJUSTE_TENDENCIA_MAX = 0.15;

const FACTOR_CONFIANZA = Object.freeze({ alta: 1.0, media: 0.5, baja: 0.0 });

/**
 * Nivel proyectado de un registro de celda/segmento en un horizonte dado.
 * `null`/`undefined` (celda `sin_datos`, p. ej. `sin_establecimientos`) es un **cero legítimo**,
 * no una ausencia (metodología §10.1: "Ŝ=0 con D̂>0 es un valor válido"): si `nivel_base` es nulo,
 * la celda no tiene ningún establecimiento observado, así que aporta 0 a la suma.
 *
 * @param {{nivel_base: number|null, h?: Record<string, {delta_pct: number|null}>}} registro
 * @param {string|null} horizonte - clave de horizonte (`"h1"`/`"h3"`/`"h5"`), o `null` para verde
 *   (sin componente temporal: el nivel es el mismo en cualquier horizonte, metodología §10.1).
 * @returns {number}
 */
export function nivelEnHorizonte(registro, horizonte) {
  if (!registro || registro.nivel_base === null || registro.nivel_base === undefined) return 0;
  if (horizonte === null) return registro.nivel_base; // verde: sin proyección.
  const bloqueH = registro.h?.[horizonte];
  if (!bloqueH || bloqueH.delta_pct === null || bloqueH.delta_pct === undefined) {
    return registro.nivel_base; // horizonte sin delta_pct (no debería ocurrir si nivel_base existe).
  }
  return registro.nivel_base * (1 + bloqueH.delta_pct / 100);
}

/**
 * Suma de celdas seleccionadas (metodología §10.6, paso 1): `Ŝ_{i,r}(filtro) = Σ_c Ŝ_{i,c}`.
 * Devuelve el nivel base combinado y el nivel proyectado combinado en el horizonte dado.
 *
 * @param {Record<string, object>} celdas - `registro.celdas` de una rama (`api.js`).
 * @param {string[]} clavesSeleccionadas - claves de celda activas del filtro (`filtros.js`).
 * @param {string|null} horizonte
 * @returns {{nivelBase: number, nivelHorizonte: number}}
 */
export function sumaCeldas(celdas, clavesSeleccionadas, horizonte) {
  let nivelBase = 0;
  let nivelHorizonte = 0;
  for (const clave of clavesSeleccionadas) {
    const registro = celdas[clave];
    if (!registro) continue;
    nivelBase += registro.nivel_base ?? 0;
    nivelHorizonte += nivelEnHorizonte(registro, horizonte);
  }
  return { nivelBase, nivelHorizonte };
}

/**
 * Tasa anual implícita (%/año) de una combinación de celdas, derivada de dos niveles ya sumados
 * (nivel base y nivel proyectado), por log-razón anualizada -- mismo principio que
 * `modelos.agregar_alcaldia` (`tasa = ln(nivel_horizonte/nivel_base)/años`), aplicado aquí sobre
 * la suma de celdas en vez de la suma de AGEB. `anios` es la distancia en años entre `fecha_base`
 * y el horizonte usado (p. ej. 3 para `h3`). Devuelve `0` si ambos niveles son 0 (sin
 * establecimientos en ningún horizonte: una tasa de "cero a cero" no está definida, se trata como
 * sin cambio, no como error).
 *
 * @param {number} nivelBase
 * @param {number} nivelHorizonte
 * @param {number} anios
 * @returns {number}
 */
export function tasaAnualImplicita(nivelBase, nivelHorizonte, anios) {
  if (nivelBase <= 0) return 0;
  if (nivelHorizonte <= 0) return -100; // toda la oferta desaparece: tasa muy negativa, no NaN.
  return (100 * Math.log(nivelHorizonte / nivelBase)) / anios;
}

/**
 * Cobertura proyectada (metodología §10.1): `Ŝ/D̂ × 1000`. `D̂ <= 0` (demanda inválida, AGEB
 * `sin_datos`) produce `NaN` -- nunca se imputa un denominador. `Ŝ = 0` con `D̂ > 0` produce `0`,
 * un valor válido (la señal de mayor oportunidad posible), nunca `NaN`.
 *
 * @param {number} nivelOferta
 * @param {number} nivelDemanda
 * @returns {number}
 */
export function coberturaProyectada(nivelOferta, nivelDemanda) {
  if (!(nivelDemanda > 0)) return NaN;
  return (nivelOferta / nivelDemanda) * 1000;
}

/**
 * Rango percentil fraccionario ∈ [0,1], empates promediados (metodología §10.2, paso 1;
 * equivalente a `scipy.stats.rankdata(method="average")` restringido a valores válidos,
 * `features._rango_percentil_promediado`). `NaN` se propaga. Con un solo valor válido, 0.5.
 *
 * @param {ArrayLike<number>} valores
 * @returns {Float64Array}
 */
export function rangoPercentilPromediado(valores) {
  const n = valores.length;
  const resultado = new Float64Array(n).fill(NaN);
  const indicesValidos = [];
  for (let i = 0; i < n; i++) {
    if (!Number.isNaN(valores[i])) indicesValidos.push(i);
  }
  const nValidos = indicesValidos.length;
  if (nValidos === 0) return resultado;
  if (nValidos === 1) {
    resultado[indicesValidos[0]] = 0.5;
    return resultado;
  }
  // Ordena los índices válidos por valor; asigna rango 1..nValidos con empates promediados.
  const ordenados = indicesValidos.slice().sort((a, b) => valores[a] - valores[b]);
  const rangos = new Float64Array(nValidos);
  let i = 0;
  while (i < nValidos) {
    let j = i;
    while (j + 1 < nValidos && valores[ordenados[j + 1]] === valores[ordenados[i]]) j++;
    const rangoPromedio = (i + 1 + j + 1) / 2; // 1-indexado, promedio del bloque de empates.
    for (let k = i; k <= j; k++) rangos[k] = rangoPromedio;
    i = j + 1;
  }
  for (let k = 0; k < nValidos; k++) {
    resultado[ordenados[k]] = (rangos[k] - 1) / (nValidos - 1);
  }
  return resultado;
}

/**
 * Índice de oportunidad por rama, `O_{i,r}` (metodología §10.2, fórmula exacta,
 * `features.indice_oportunidad`).
 *
 * Paso 1 (nivel): `N = 1 - rango_percentil(cobertura)` -- cobertura 0 comparte el rango más bajo,
 * por tanto `N=1` (máxima oportunidad), sin caso especial para `Ŝ=0`.
 * Paso 2 (tendencia, acotada): `ajuste = clip((tasa_d - tasa_s)/K, -0.15, +0.15)`. `tasaS` es
 * `null` para la rama verde (sin tendencia, metodología §10.1): el ajuste queda en 0, no se
 * inventa una comparación que los datos no permiten (decisión de ingeniería, `docs/metodologia.md`
 * §10.6 no cubre este caso porque verde no tenía tendencia que comparar).
 * Paso 3: `O = clip(N + ajuste, 0, 1)`. `NaN` en `cobertura` se propaga.
 *
 * @param {Float64Array|number[]} coberturas
 * @param {Float64Array|number[]} tasasDemanda - `tasa_anual_pct` del segmento activo, %/año.
 * @param {(Float64Array|number[]|null)} tasasOferta - tasa implícita de la rama/filtro, %/año, o
 *   `null` para verde.
 * @param {number} [k]
 * @returns {Float64Array}
 */
export function indiceOportunidad(coberturas, tasasDemanda, tasasOferta, k = K_OPORTUNIDAD) {
  const n = coberturas.length;
  const rango = rangoPercentilPromediado(coberturas);
  const resultado = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    if (Number.isNaN(coberturas[i])) {
      resultado[i] = NaN;
      continue;
    }
    const nivel = 1 - rango[i];
    const tasaS = tasasOferta === null ? 0 : tasasOferta[i];
    const ajusteCrudo = (tasasDemanda[i] - tasaS) / k;
    const ajuste = tasasOferta === null ? 0 : Math.min(Math.max(ajusteCrudo, -AJUSTE_TENDENCIA_MAX), AJUSTE_TENDENCIA_MAX);
    resultado[i] = Math.min(Math.max(nivel + ajuste, 0), 1);
  }
  return resultado;
}

/**
 * Índice de disponibilidad para familias, `F_{i,r}` (metodología §10.5, `features.indice_disponibilidad`):
 * mismo motor, orientación inversa (`rango` directo, no `1-rango`: cobertura alta ya significa
 * disponibilidad alta). `ajuste_estabilidad = clip(tasa_s/K, -0.15, 0.15) * factorConfianza`
 * (`alta=1, media=0.5, baja=0`): una tendencia de oferta positiva solo premia si la confianza la
 * respalda. **Nunca se combina con `indiceOportunidad`** en el mismo campo.
 *
 * @param {Float64Array|number[]} coberturas
 * @param {(Float64Array|number[]|null)} tasasOferta
 * @param {string[]} confianzas - `"alta"|"media"|"baja"` por unidad.
 * @param {number} [k]
 * @returns {Float64Array}
 */
export function indiceDisponibilidad(coberturas, tasasOferta, confianzas, k = K_OPORTUNIDAD) {
  const n = coberturas.length;
  const rango = rangoPercentilPromediado(coberturas);
  const resultado = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    if (Number.isNaN(coberturas[i])) {
      resultado[i] = NaN;
      continue;
    }
    let ajuste = 0;
    if (tasasOferta !== null) {
      const ajusteCrudo = tasasOferta[i] / k;
      const acotado = Math.min(Math.max(ajusteCrudo, -AJUSTE_TENDENCIA_MAX), AJUSTE_TENDENCIA_MAX);
      ajuste = acotado * (FACTOR_CONFIANZA[confianzas[i]] ?? 0);
    }
    resultado[i] = Math.min(Math.max(rango[i] + ajuste, 0), 1);
  }
  return resultado;
}

/** Las 4 ramas del contrato v1.4, en el orden fijo del hash de pesos (`estado.js`). */
export const RAMAS = Object.freeze(["educacion", "salud", "comercio", "verde"]);

/**
 * Índice compuesto, `IC_i = Σ w_r·O_{i,r} / Σ w_r` sobre ramas con dato (metodología §10.3),
 * renormalizado cuando una rama es `sin_datos` para esa AGEB -- nunca se trata la rama ausente
 * como 0 (`correccion/frontend_requisitos.md` §9). Si TODAS las ramas son `sin_datos` para una
 * unidad, el resultado es `NaN` (estado 9 de §15 del spec: "ninguna de las cuatro ramas").
 *
 * @param {Record<string, Float64Array|number[]>} oPorRama - `{educacion, salud, comercio, verde}`.
 * @param {Record<string, number>} pesos - `{educacion, salud, comercio, verde}`, 1-5 cada uno.
 * @returns {Float64Array}
 */
export function indiceCompuesto(oPorRama, pesos) {
  const n = oPorRama[RAMAS[0]].length;
  const resultado = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    let sumaPesada = 0;
    let sumaPesos = 0;
    for (const rama of RAMAS) {
      const o = oPorRama[rama][i];
      if (Number.isNaN(o)) continue;
      sumaPesada += pesos[rama] * o;
      sumaPesos += pesos[rama];
    }
    resultado[i] = sumaPesos > 0 ? sumaPesada / sumaPesos : NaN;
  }
  return resultado;
}

/**
 * Clasificador genérico por `n` cortes de percentil iguales (p. ej. `n=3` terciles, `n=5`
 * quintiles), sobre los valores válidos de un índice `O`/`IC`. `NaN`/`sin_datos` siempre clasifica
 * aparte, nunca se mezcla con el corte más bajo.
 *
 * @param {Float64Array|number[]} valores
 * @param {number} n
 * @returns {(v: number) => number|"sin_datos"} `1..n` (1 = menor prioridad relativa) o `"sin_datos"`.
 */
export function clasificadorPercentiles(valores, n) {
  const validos = Array.from(valores).filter((v) => !Number.isNaN(v)).sort((a, b) => a - b);
  if (validos.length === 0) {
    return () => "sin_datos";
  }
  const cortes = [];
  for (let i = 1; i < n; i++) {
    cortes.push(validos[Math.min(validos.length - 1, Math.floor((i / n) * validos.length))]);
  }
  return (v) => {
    if (Number.isNaN(v)) return "sin_datos";
    for (let i = 0; i < cortes.length; i++) {
      if (v <= cortes[i]) return i + 1;
    }
    return n;
  };
}

/**
 * Terciles de oportunidad/disponibilidad relativa (spec §6.2, resumen estructurado Nivel 1):
 * percentil 33/66, `1|2|3` traducido a `"baja"|"media"|"alta"`.
 *
 * @param {Float64Array|number[]} valores
 * @returns {(v: number) => "alta"|"media"|"baja"|"sin_datos"}
 */
export function clasificadorTerciles(valores) {
  const base = clasificadorPercentiles(valores, 3);
  const NOMBRE = { 1: "baja", 2: "media", 3: "alta" };
  return (v) => {
    const resultado = base(v);
    return resultado === "sin_datos" ? "sin_datos" : NOMBRE[resultado];
  };
}

/**
 * Quintiles del color del mapa (spec §4.2: "el mapa se pinta con los 5 tonos... la leyenda agrupa
 * en 3 categorías"): percentiles 20/40/60/80, `1..5` (1 = `--prioridad-1`, menor prioridad
 * relativa; 5 = `--prioridad-5`, mayor). La leyenda agrupa `{1,2}→baja, {3}→media, {4,5}→alta`
 * para las 3 categorías legibles (`leyenda.js`), sin definir un segundo corte independiente.
 *
 * @param {Float64Array|number[]} valores
 * @returns {(v: number) => number|"sin_datos"}
 */
export function clasificadorQuintiles(valores) {
  return clasificadorPercentiles(valores, 5);
}

/** Agrupa un quintil (1..5) en el tercil legible de la leyenda (spec §4.2). */
export function tercilDeQuintil(quintil) {
  if (quintil === "sin_datos") return "sin_datos";
  if (quintil <= 2) return "baja";
  if (quintil === 3) return "media";
  return "alta";
}
