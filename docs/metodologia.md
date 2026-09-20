# Metodología

Veredicto `sube | se_mantiene | baja | sin_datos` por AGEB y alcaldía, fecha base **2026-06**
(2026.5); horizontes de reporte **2027-06** (1 año), **2029-06** (3 años) y **2031-06** (5 años),
contrato `version 1.4` con capas `demanda` (por segmento de población objetivo) y cuatro **ramas**
de oferta/disponibilidad (educación y cultura, salud, comercio, áreas verdes y espacio público).
Decisiones vigentes en CLAUDE.md; hechos en `docs/perfil_datos.md` y `docs/problemas_datos.md`.

Revisión **2026-09-20**: producto **Habitancia** (`correccion/frontend_requisitos.md`) — cuatro
ramas con pesos y filtros del usuario, índice de oportunidad con fórmula exacta y tratamiento
explícito de oferta cero (§10), calibración del piso de incertidumbre contra el backtest en vez de
un ancho mínimo arbitrario (§2.7, §6.2), y corrección de la fuga de futuro en el backtest de CONAPO
(§4.1). Revisión anterior, **2026-09-19b**: horizontes 1/3/5 años, validación retrospectiva real,
segmentación por grupo de edad. Referencias: `correccion/rubrica.md` §5-6,
`correccion/detalles_a_tratar.md` §9, `correccion/frontend_requisitos.md`. El plan de ejecución por
fases está en **`correccion/action_plan.md`**; este documento es la fuente de verdad del *método*.

> **Estado de cada bloque.** Este documento describe el método acordado, no solo el código de hoy.
> Cada sección lleva una marca:
> **✅ implementado** (existe en `backend/src/chipos/` y está cubierto por `make test`) ·
> **🔄 acordado, pendiente** (con la fase de `correccion/action_plan.md` que lo entrega).
> Nunca se marca ✅ algo cuyo archivo de resultados no exista en el repositorio. Un bloque marcado
> ✅ en una revisión anterior que esta revisión **corrigió** (§2.7, §4.1, §6.2, §10) vuelve a 🔄:
> la corrección en sí misma es trabajo pendiente, aunque el bloque original ya existiera.

## 1. Variables y fuentes

**Demanda potencial (capa principal). ✅ (panel por segmento ✅ `panel.construir_panel_demanda`;
contrato v1.4 con los 6 segmentos ✅ `exportar.construir_capa_demanda_v14`; frontend 🔄 fase 7/9)**
`D_it = P_0A2 + P_3A5 +
P_6A11 + P_12A14` (0–14, suma simple), AGEB urbana *i*, censo *t* ∈ {2010.44, 2020.20} (fechas de
referencia 12-jun-2010 y 15-mar-2020; Δt = 9.76). Fuente: INEGI RESAGEBURB 2010 y 2020
(`data/interim/censo_ageb_panel.parquet`). El panel censal **ya trae** `p_15a17` (verificado en
disco), así que ampliar el rango a 0–17 no requiere una fuente nueva — solo sumar esa columna al
segmento correspondiente (§1.1). La limitación real es de **oferta**, no de demanda: casi todo
establecimiento `Alcance = Principal` de DENUE infancias atiende 0–14; 15–17 aparece sobre todo en
`Complementario` (media superior, recreación juvenil), una categoría con cobertura y tendencia menos
confiables. Esto se documenta como advertencia en la ficha del segmento 15–17, no como motivo para
excluirlo: `correccion/frontend_requisitos.md` §5 exige que 15–17 esté disponible.

**El nombre importa: es *demanda potencial*, no demanda observada.** Mil niñas, niños o adolescentes
no generan la misma demanda de servicios en todas las zonas: intervienen la edad exacta, la
escolaridad, el ingreso, la participación laboral de quien cuida, el tipo de servicio, el acceso a
oferta pública o privada y las distancias. Nada de eso está en los datos disponibles. La etiqueta
"demanda potencial" es obligatoria en la UI y en la documentación
(`correccion/detalles_a_tratar.md` §6C); en Habitancia, la interfaz nunca usa la palabra "demanda"
a secas frente a personas no técnicas — usa "población objetivo" (§1.1) y explica la diferencia
solo en el icono "?" (`correccion/frontend_requisitos.md` §20).

**Control externo. ✅** CONAPO, población a mitad de año por municipio y grupo quinquenal 1990–2040
(`conapo_mun_0a14.parquet`, 0–14 = 00_04 + 05_09 + 10_14; `conapo_mun_quinq.parquet` conserva el
detalle quinquenal, incluido 15–19 — que **no** coincide exactamente con 15–17; ver §1.1).

**Cuatro ramas de oferta/disponibilidad (datos y modelo ✅ fase 5; contrato v1.4 ✅ fase 6,
generaliza lo que antes era una sola capa "oferta").** Habitancia no expone una sola capa de
oferta: expone cuatro ramas
(`correccion/frontend_requisitos.md` §2), cada una con su propia fuente y su propio tratamiento
temporal:

| Rama | Fuente | Series con tendencia | Proyección |
|---|---|---|---|
| **Educación y cultura** | DENUE infancias, `Alcance = Principal` | 2016-10, 2019-11, 2024-11 (§6) | Sí, Poisson log-lineal (§6) |
| **Salud** | DENUE salud | mismos 3 cortes que infancias (mismas ediciones DENUE) | Sí, mismo método (§10.6) |
| **Comercio** | DENUE comercios (GeoJSON) | 11 ediciones 2016–2026, mismo criterio de "1 corte por periodo" que §6 | Sí, mismo método |
| **Áreas verdes y espacio público** | `areas_verdes/`, `espacios_publicos/` (Datos Abiertos CDMX) | un solo corte (inventario estático) | **No** — solo valor actual (§10.1) |

Educación, salud y comercio comparten exactamente el mismo tratamiento estadístico que hoy tiene
"oferta" (§6): Poisson log-lineal + EB hacia la alcaldía + sobredispersión (§6.2), generalizado por
rama y por celda de filtro (§10.6). Áreas verdes y espacio público no tienen manera honesta de
proyectarse (un solo corte no identifica tendencia, igual que §3 con un solo censo sería imposible) y
se publican como disponibilidad **actual**, nunca como una línea futura inventada
(`correccion/frontend_requisitos.md` §16: "Si una rama solo tiene información actual, mostrar su
situación actual y NO inventar una línea futura").

### 1.1 Población objetivo (selector de Habitancia)

`correccion/frontend_requisitos.md` §5 exige este selector completo, incluido 0–17 y 15–17:

| Población objetivo | Columna censal | Cobertura de oferta (educación) |
|---|---|---|
| Todas las infancias y adolescencias · 0–17 | `p_0a2+p_3a5+p_6a11+p_12a14+p_15a17` | Mixta: 0–14 bien cubierto, 15–17 parcial |
| Primera infancia · 0–2 | `p_0a2` | Guardería/estancia infantil |
| Preescolar · 3–5 | `p_3a5` | Preescolar |
| Primaria · 6–11 | `p_6a11` | Primaria |
| Secundaria · 12–14 | `p_12a14` | Secundaria |
| Adolescencia · 15–17 | `p_15a17` | Solo `Complementario`; confianza tope `media` obligatorio |

**Brecha y oportunidad (§10). ✅ fase 6.** Cobertura proyectada `Ŝ/D̂ × 1000` por horizonte e índice
de oportunidad de expansión, implementados en `features.py` y publicados en el contrato v1.4 (§10).
**`capas.brecha` se retiró del contrato**: la razón histórica `S_2024 / D_2020 × 1000` que mezclaba
dos momentos distintos ya no se publica; el cálculo equivalente pasa al motor de composición del
frontend (Fase 7).

### 1.2 Segmentos de servicio y población objetivo — mapeo SCIAN de la oferta ✅ fase 5

> **Nota de consistencia — resuelta en Fase 5 (B22).** La tabla que traía esta sección (nombres
> `total`/`mixto`, anterior a la ampliación a 0–17) se reemplazó por las **celdas de filtro reales**
> por rama (`panel.CELDAS_EDUCACION`/`CELDAS_SALUD`/`CELDAS_COMERCIO`, §10.6), que no coinciden 1:1
> con los 6 segmentos de **demanda** de §1.1 — cada celda de oferta es su propio ajuste Poisson+EB,
> independiente del segmento de demanda activo en el cliente (el cliente combina ambos lados solo al
> calcular cobertura, §10.1). La fila `mixto` (SCIAN sin segmentar) se resolvió **dividiéndola en dos
> celdas propias** en vez de mantenerla fusionada: `varios_niveles` (611171, 611172) y
> `educacion_especial` (611181, 611182); además se agregaron dos celdas `Complementario` nuevas que
> esta tabla no tenía, `media_superior_tecnica` y `recreacion_cultura` (cubren, entre otras cosas, la
> oferta relevante para el segmento de demanda `adolescencia`, 15–17, que tampoco tenía celda propia
> aquí).

Sumar todas las edades 0–14 contra todos los establecimientos oculta desajustes reales: una
guardería y una secundaria no atienden a la misma población. Los datos **ya están desagregados en
disco** — el censo trae las cuatro bandas por AGEB y el DENUE trae `Subcategoría` + `Código SCIAN`—,
así que la segmentación no requiere fuentes nuevas.

| Celda (`panel.CELDAS_EDUCACION`) | Alcance | SCIAN | Establecimientos 2024-11 | AGEB con presencia |
|---|---|---|---:|---:|
| `guarderia` | Principal | 624411, 624412 | 591 | 490 |
| `preescolar` | Principal | 611111, 611112 | 2 261 | 1 302 |
| `primaria` | Principal | 611121, 611122 | 2 286 | 1 132 |
| `secundaria` | Principal | 611131, 611132, 611141, 611142 | 894 | 515 |
| `varios_niveles` | Principal | 611171, 611172 | 885 | 615 |
| `educacion_especial` | Principal | 611181, 611182 | 386 | 285 |
| `media_superior_tecnica` | Complementario | 611151, 611152, 611161, 611162, 611512 | 364 | 270 |
| `recreacion_cultura` | Complementario | 611611, 611612, 611621, 611622, 611631, 611632, 611691, 611698, 611699 | 1 588 | 898 |

No hay una celda "total" publicada: cada celda es su propio registro en el contrato
(`capas.ramas.educacion[cvegeo].celdas.<celda>`); el segmento de demanda por omisión (`todas`, 0–17)
sigue siendo el valor por omisión del mapa y del veredicto principal, pero eso es un eje aparte del
de las celdas de oferta.

**Sector (público/privado), rework de Fase 5 -- ver `plans/frontend_specs.md` §10.11/§17.3.**
`frontend_requisitos.md` exige un selector SECTOR (Todos/Público/Privado) para educación y salud
que la tabla de arriba no tenía: DENUE sí trae una columna `Sector` cruda (Público/Privado/No
especificado, verificado en datos reales) que `io.leer_denue_infancias`/`leer_denue_salud` ya
leían pero `panel.py` no usaba. Cada nivel/tipo de la tabla de arriba se cruza con los 3 valores de
sector (`panel.SECTORES`), publicando **3 celdas por fila** en vez de 1: educación pasa de 8 a
**24 celdas**, salud de 4 a **12**. `no_especificado` se publica como celda propia (nunca se
descarta): es necesario para que "Todos" siga sumando exactamente el total sin sector — en
`salud/farmacias`, el caso extremo, el 100 % de los establecimientos son `no_especificado` (DENUE
nunca clasifica el sector de una farmacia), así que sin esa celda "Todos" perdería el 100% del
dato. Comercio y verde no tienen esta columna en el dato crudo, así que no se cruzan por sector.
Esto sube el total de celdas con proyección de 17 a **41** (24 + 12 + 5) y el peso del contrato de
~1.02 MB a ~1.42 MB gzip (`plans/frontend_specs.md` §16.1).

**Aproximación documentada:** CONAPO publica grupos quinquenales (00_04, 05_09, 10_14) que **no**
coinciden con las bandas censales 0–2 / 3–5 / 6–11 / 12–14. El ancla municipal (§2.3, §2.5) se
aplica sobre 0–14 y los segmentos **heredan el mismo factor de control** `k_m^s`. Es una
aproximación, no una identidad: se declara aquí, en `diagnostico.json` y en el panel de metodología
del frontend. No se inventa un desglose quinquenal que CONAPO no publica.

### 1.3 Momentos históricos comparables (§ rúbrica 5) ✅ fase 5

`correccion/rubrica.md` §5 pide **al menos tres momentos históricos comparables**. La respuesta
honesta no es la misma en cada rama/capa, y hay que decirla tal cual:

| Capa / nivel | Momentos comparables | Fuente |
|---|---:|---|
| Oferta educación, por AGEB | **3** (2016.79, 2019.87, 2024.87) | DENUE infancias, fechas de levantamiento |
| Oferta salud, por AGEB | **3** (2016.79, 2019.87, 2024.87) | DENUE salud, mismas ediciones que infancias |
| Oferta comercio, por AGEB | **3** (2016.79, 2019.87, 2024.87) | DENUE comercios, mismo criterio "1 corte por periodo" pese a tener 11 ediciones disponibles |
| Verde (áreas verdes y espacio público), por AGEB | **1** (inventario 2026, sin fecha de levantamiento por establecimiento) | Datos Abiertos CDMX; sin tendencia, se publica como disponibilidad actual (§10.1), nunca una línea futura inventada |
| Demanda, por alcaldía | **serie anual 1990–2040** (31 observados hasta 2020) | CONAPO municipal |
| Demanda, por AGEB | **2** (2010.44, 2020.20) | Censo INEGI |

La rama verde es la única con un solo momento: un solo corte no identifica tendencia, igual que un
solo censo no la identificaría (§3) -- no se inventa una comparación que los datos no permiten.

Dos censos es el límite de INEGI por AGEB, no una omisión del equipo: la Encuesta Intercensal 2015
no se publica a ese nivel. Esa es exactamente la razón de ser de la contracción hacia la alcaldía
(§2.2) y del ancla CONAPO (§2.3): la tendencia municipal, que sí tiene serie larga, aporta la
información temporal que el AGEB no tiene. El backtest temporal (§4) se corre sobre las dos series
que sí tienen tres o más momentos: CONAPO municipal y DENUE por AGEB.

### 1.4 Capas de contexto de la CDMX ✅ fase 5

`data/processed/areas_verdes/` y `data/processed/espacios_publicos/` (Datos Abiertos de la CDMX) se
incorporan vía `io.leer_contexto_cdmx()` (conteo y superficie de equipamiento comunitario, join
espacial en WGS84, `gpd.sjoin` con punto representativo). No entran al modelo de tendencia: son
covariables estáticas de un solo corte y §9 ya descarta usarlas como modelo principal — pero, a
diferencia de lo que preveía esta sección originalmente, **no se quedan como contexto descriptivo de
fondo**: alimentan directamente la rama "verde" del contrato v1.4 (`capas.ramas.verde`, §10.1), con
sus propias 3 celdas de filtro (`panel.CELDAS_VERDE`: cobertura verde, áreas recreativas, espacios
públicos). Diversidad de fuentes (`correccion/rubrica.md` §3, que pide integrar Datos Abiertos de la
CDMX junto a INEGI).

## 2. Método principal de demanda: tasa log-lineal + contracción EB + control CONAPO ✅

1. **Tasa directa** por AGEB: `r̂_i = ln[(D_i,2020 + 0.5)/(D_i,2010 + 0.5)] / 9.76`, con varianza
   Poisson `ψ_i = [1/(D_i,2020 + 0.5) + 1/(D_i,2010 + 0.5)] / 9.76²`.
2. **Contracción (Fay-Herriot)** hacia la alcaldía: `r_i ~ N(ρ_m, τ²)`; `ρ_m` = tasa censal de la
   alcaldía (Σ AGEB), `τ²` por momentos; `r̃_i = B_i ρ_m + (1 − B_i) r̂_i`, `B_i = ψ_i/(ψ_i + τ²)`.
3. **Tasa futura**: la alcaldía toma la tasa CONAPO y la AGEB conserva parte de su desviación:
   `r_i,fut = ρ_m,CONAPO + λ (r̃_i − ρ_m)`, con `ρ_m,CONAPO = ln(C_m,2031.5 / C_m,2020.5)/11.0`
   (CONAPO publica población a mitad de año; el control se ancla al horizonte de reporte **más
   lejano**, `2031.5` = mediados de 2031 = fecha base + 5 años, ver §7).
4. **Proyección** `D̂_i(t) = D_i,2020 · exp(r_i,fut (t − 2020.20))`.
5. **Control por tasa, no por nivel:** reescalar por alcaldía para que
   `Σ_i D̂_i,2031.5 / Σ_i D_i,2020 = C_m,2031.5 / C_m,2020.20`. Se usa la **razón** de CONAPO, no
   su nivel, porque CONAPO incluye población rural y está conciliada (+5.9 % en 0–14 frente al
   censo urbano en 2020; problemas N1). `C_m,2020.20` se interpola log-linealmente entre las cifras
   2019 (2019.5) y 2020 (2020.5). El control se aplica **una sola vez**, contra el horizonte más
   lejano (`h5`, 2031.5): los horizontes `h1`/`h3` (2027-06, 2029-06) se leen sobre la **misma**
   trayectoria de tasa `r_i,fut` ya controlada, sin volver a controlar contra CONAPO en cada
   horizonte por separado. No es una pérdida de precisión: con dos censos no se identifica
   curvatura de la tendencia (§3), así que no hay información para justificar tres controles
   independientes; controlar una sola vez, al horizonte más lejano, es la opción más conservadora.
   Anclar en 2031.5 y no en 2033.5 mantiene el control dentro del tramo de CONAPO más cercano a su
   base censal 2020 (`correccion/detalles_a_tratar.md` §2).
6. **Simulación** (semilla fija, 4,000 réplicas): `r_i ~ N(r̃_i, (1 − B_i)ψ_i)`, `λ ~ U(0.25, 1)`,
   choque de alcaldía compartido `N(0, σ_C²)` con `σ_C` = discrepancia censo-CONAPO 2010–20 de esa
   alcaldía (§4.3) → `IC95`, `P(sube)`, `P(baja)` e IC de alcaldía.
7. **Piso de incertidumbre, calibrado con el backtest (✅ fase 3, ver nota).** La varianza
   posterior de la tasa nunca baja de `SIGMA_MIN_TASA²` (`config.py`). Justificación: `(1 − B_i)ψ_i`
   solo representa el error de conteo censal; no cubre cambios metodológicos del censo,
   reconciliación CONAPO ni choques posteriores a 2020 a escala AGEB (§3, fila "no se identifica").
   Sin ese piso el modelo publica intervalos más seguros de lo que realmente está
   (`correccion/detalles_a_tratar.md` §6H). **`SIGMA_MIN_TASA` no se elige a ojo ni para forzar un
   ancho mínimo arbitrario: se calibra con la cobertura empírica del propio backtest de la fase 2**
   (adelgazamiento binomial + leave-one-alcaldía-out para demanda; origen 2019→2024 para oferta).
   Procedimiento (`backtest.calibrar_piso_incertidumbre`, §4.4 más abajo y plan §6):
   1. Recorrer una rejilla de candidatos (p. ej. `{0.000, 0.005, 0.010, 0.015, 0.020}` %/año).
   2. Para cada candidato, recalcular el IC95 simulado **sobre los folds del backtest** (donde sí
      hay un valor verdadero conocido con el que comparar) y medir la cobertura empírica: fracción
      de folds donde el valor real cae dentro del IC95 predicho.
   3. Elegir el **candidato más pequeño** cuya cobertura cae dentro de la banda ya usada para
      leave-one-alcaldía-out, `[0.90, 0.97]` (ni subcubierto ni sobrecubierto).
   4. Si ningún candidato de la rejilla alcanza `0.90`, ampliar la rejilla; si el candidato `0.000`
      ya sobrecubre (> 0.97), **no se añade piso** y se documenta que el error de conteo ya es
      suficiente — el piso no es obligatorio por diseño, es la consecuencia de una medición.
   El resultado (piso elegido + cobertura lograda) se escribe en `docs/backtest.md`, nunca se
   redondea "para que se vea bien": si la cobertura lograda queda en `0.88` en vez de `0.90`, se
   reporta `0.88` y se explica.

   **Resultado real:** `SIGMA_MIN_DEMANDA = 0.0` (el candidato `0.000` ya sobrecubre: 0.98-1.00 en
   adelgazamiento, 1.00 en LOAO — ver `docs/backtest.md`). Implementado en `config.py`
   (`SIGMA_MIN_DEMANDA`) y aplicado en `modelos.simular_demanda` como
   `var_post = np.maximum(var_post, SIGMA_MIN_DEMANDA**2)`. Para oferta, la calibración también dio
   `0.0`, pero ese resultado por sí solo **no bastaba** para el hallazgo 0.5 de
   `correccion/action_plan.md` (IC95 degenerado) — ver §6.2 para el hallazgo adicional que sí lo
   corrige.

Salidas, una vez fijada `r_i,fut` (§2.3-2.5): `tasa_anual_pct` = `r_i,fut` proyectada × 100 — **es
la misma en los tres horizontes de reporte** (`h1`, `h3`, `h5`): depende solo de la tasa, no del
horizonte al que se mira. `delta_pct` = cambio acumulado desde la **fecha base** (2026.5, no desde
el censo 2020) hasta cada horizonte de reporte (2027-06, 2029-06 o 2031-06); por eso `delta_pct`
crece en magnitud de `h1` a `h5` aunque la tasa no cambie (`modelos.resumir()`). **El veredicto usa
la tasa `r_i,fut`**, así que tampoco cambia entre horizontes (§7). Baseline ingenuo: `r = 0` (igual
que el censo 2020).

## 3. (a) Qué se identifica con dos censos ✅

| se identifica | no se identifica |
|---|---|
| Tasa media 2010–2020 por AGEB (`r̂_i`) y su ruido Poisson (`ψ_i`) | Curvatura o aceleración de la tendencia local |
| Dispersión real entre AGEB de una alcaldía (`τ`) | Si la desviación local de 2010–20 **persiste** (`λ`) |
| Tendencia futura por alcaldía (CONAPO, externo) | Choques posteriores a 2020 a escala AGEB |

Hechos (censo completo, 2,268 AGEB "misma unidad" con ≥ 20 niños en ambos censos): mediana de `r̂`
−1.97 %/año (p10 −3.78, p90 +0.31); DE 2.09 %/año; `τ` intra-alcaldía 1.89 %/año; error Poisson
mediano 0.58 %/año (AGEB mediana: 583 niños). La incertidumbre dominante es **estructural** (`λ`);
IC solo Poisson serían ~3.5 veces más estrechos que la dispersión real. `λ` no es estimable con dos
puntos: previa `U(0.25, 1)` y veredicto reportado con `λ` = 0.25, 0.6 y 1; si cambia entre extremos,
la confianza baja un nivel.

Con dos puntos **no se puede saber** si la caída se aceleró, si la tendencia se frenó o si hubo un
cambio después de 2020. El modelo lo reconoce explícitamente (previa amplia sobre `λ`, piso de
incertidumbre §2.7) y la UI lo dice. Lo que no se hace es fingir precisión que los datos no tienen.

## 4. (b) Validación retrospectiva ✅ (implementado; resultado real 🔄, ver nota)

> **Estado: implementado.** `backend/src/chipos/backtest.py`, `data/outputs/backtest.json` y
> `docs/backtest.md` ya existen y `exportar.main()` los invoca en cada `make pipeline`
> (`io → panel → backtest → modelos → exportar`), deterministas con `SEMILLA`. Las 4 validaciones
> de §4.2-4.3 corren sobre datos reales: 154 tests de backend en verde
> (`backend/tests/test_backtest.py`).
>
> **Resultado real, sin maquillar (`docs/backtest.md`, corrida sobre datos reales):**
> demanda supera al baseline `r=0` en MAE y F1 macro en ambas fracciones de adelgazamiento
> (MAE 0.68-0.69 vs 2.34 pp/año; F1 0.79-0.86 vs 0.11), pero la cobertura del IC95 de LOAO sale en
> **1.00** (por encima de la banda `[0.90, 0.97]`: el intervalo está sobrecubierto, no
> subcubierto). **Oferta NO supera al baseline "S constante" en MAE** (5.45 vs 3.61 en log-razón),
> aunque sí lo supera en F1 macro (0.67 vs 0.20): el modelo acierta mejor la *dirección* del
> cambio pero se equivoca más en la *magnitud*, consistente con que el objetivo 2024 contiene la
> caída C3 (§6.1) — una extrapolación de 2016→2019 no puede anticipar un ajuste de padrón que
> ocurre después. Con el criterio de adopción sin escapatoria de §4.3, `modelo_se_adopta = False`
> (el campo `adopcion` de `backtest.json` reporta esto tal cual, sin forzarlo a `True`).
>
> **Decisión del equipo (2026-09-20), pregunta abierta B1 de `plans/backend_plan.md` §9.2
> resuelta:** se mantiene el modelo Poisson+EB actual para educación/salud/comercio (Fase 5), con
> su tope de confianza `media` ya existente, y se documenta la limitación explícitamente en vez de
> ocultarla u omitir la rama: *"este modelo acierta la dirección del cambio (F1 mejor que el
> baseline) mejor de lo que acierta su magnitud exacta (MAE peor que el baseline), sobre todo
> alrededor de la caída de cobertura DENUE de 2024"*. Esta nota va al drawer de metodología del
> frontend (Fase 7, §10.6 "Lo que la oferta NO mide") y no cambia el diseño de las Fases 5-6: la
> rama conserva veredicto, `tasa_anual_pct` e IC95 igual que hoy. La cobertura IC95 de LOAO
> (1.00, sobrecubierta, fuera de `[0.90, 0.97]`) tampoco bloquea la Fase 3: el sobrecubrimiento
> no es peligroso (el modelo es conservador, no *overconfident*) y `calibrar_piso_incertidumbre`
> ya contempla este caso por diseño (§2.7 punto 4: si el candidato `0.000` ya sobrecubre, no se
> añade piso, se documenta la cobertura lograda tal cual).

### 4.1 El backtest de CONAPO original estaba mal planteado — corregido aquí

La versión anterior de este documento proponía un "origen móvil sobre la serie municipal CONAPO
1990–2020" (orígenes 2000/2005/2010/2015 → horizontes 1/3/5). **Es inválido y se retira.** El
archivo `data/processed/conapo/pobproy_quinq1.csv` es **una sola vintage**, reconciliada en bloque
contra el Censo 2020 (`tools/build_conapo.py`, docstring: "conciliada con las proyecciones
estatales 2020-2070, base Censo 2020"). Eso significa que el valor que el archivo asigna al año
2005, por ejemplo, ya fue ajustado usando información de 2020 — no es "lo que se sabía en 2005".
Usar ese archivo como si fuera una serie de orígenes independientes sería exactamente el error que
`correccion/detalles_a_tratar.md` y la revisión del equipo señalan: **validar una proyección contra
otra proyección construida con información futura**, no contra un hecho observado.

**Lo único genuinamente observado que tenemos es el Censo 2010 y el Censo 2020** (fuentes
independientes, INEGI, no reconciliadas entre sí por CONAPO). Con dos puntos censales reales no hay
manera de construir un backtest de origen móvil sin fuga: cualquier "origen" intermedio dependería
de la misma reconciliación de 2020.

**Corrección adoptada:**

1. **Se retira** el backtest de origen móvil sobre el archivo CONAPO reconciliado. No se publica
   ninguna métrica que lo use como si fuera una serie de observaciones independientes.
2. **Comparación censo-CONAPO 2010–2020 (§4.3 más abajo) se conserva**, pero se reclasifica: no es
   un backtest temporal (no predice el futuro), es una **comparación entre dos fuentes en el mismo
   punto en el tiempo** — mide desacuerdo de nivel, no error de proyección. Alimenta `σ_C` (§2.6),
   nunca se presenta como validación retrospectiva.
3. **Vía honesta para un backtest real de demanda a nivel alcaldía (🔄 fase 7, opcional):**
   CONAPO publica ediciones sucesivas de sus proyecciones (p. ej. una edición "2016–2050, base
   Censo 2010", anterior a la que usamos hoy, "2020–2070, base Censo 2020"). Si se consigue esa
   edición anterior —publicada **antes** de que existiera el Censo 2020—, su predicción de la
   población 2020 se puede comparar contra el **Censo 2020 real** sin ninguna fuga: es exactamente
   "respetar la información disponible en cada año y comparar contra datos posteriores observados".
   Esto requiere descargar un archivo que hoy no está en el repositorio; se documenta como tarea
   opcional (B21 en `plans/backend_plan.md`), no se simula ni se aproxima mientras no exista.
4. **Mientras tanto, se declara la limitación explícitamente**, en vez de maquillarla con una
   métrica inválida: *"No existe hoy una validación temporal independiente de la tendencia de
   demanda a nivel alcaldía; la comparación 2010–2020 alimenta la incertidumbre del modelo (`σ_C`),
   pero no lo valida contra el futuro."* Esta frase va en `docs/backtest.md` y en el drawer de
   metodología del frontend.

### 4.2 Backtest temporal genuino que sí es válido con los datos actuales

1. **Oferta por AGEB:** origen 2019-11 (ajuste sobre 2016-10 + 2019-11, sin ver 2024-11) → predecir
   2024-11. Baseline: `S` constante. Métricas: MAE de la log-razón, deviance Poisson, F1 macro de
   3 clases. Es válido porque el ajuste del origen usa solo los dos cortes anteriores a la fecha que
   predice — nada reconciliado con el futuro. Nota obligatoria: el objetivo 2024 contiene la caída
   C3, difícil para ambos modelos (§6.1).

### 4.3 Sustitutos para la demanda a nivel AGEB (no usan el futuro)

Con dos censos no hay tercer punto que predecir: todo origen móvil tendría fuga. Excepción explícita
a la regla de backtest, compensada con (semilla fija):

2. **Adelgazamiento binomial:** submuestrear conteos al 25 % y 50 % **del propio Censo 2020**
   (nunca del futuro), estimar `r̃` y medir el error contra `r̂` completo; debe superar a `r̂`
   directo y a `ρ_m` (MAE y cobertura del IC95).
3. **Validación cruzada dejando una alcaldía fuera** para `τ²` y el IC (cobertura 0.90–0.97). Válida
   porque es una partición **espacial**, no temporal: nunca usa datos "futuros" de la alcaldía excluida.
4. **Censo vs CONAPO 2010–2020 por alcaldía** (comparación de fuentes, no backtest — §4.1 punto 2):
   diferencias ≤ 0.6 pp/año en 13 alcaldías; 014 −0.28 vs −2.14, 015 −1.72 vs −2.50, 016 −0.33 vs
   −1.10 (alcaldías centrales: el censo urbano cae menos que CONAPO). Esa discrepancia alimenta
   `σ_C` (§2.6) y se reporta en el panel, etiquetada explícitamente como "diferencia entre dos
   fuentes en 2020", no como "error de predicción".

**Criterio de adopción, sin escapatoria:** el modelo de demanda se adopta si (2) y (3) superan al
baseline `r = 0` en MAE **y** F1 macro, con cobertura del IC95 en rango; el de oferta, si (1) supera
a `S` constante. Si alguno no lo supera, CLAUDE.md obliga a no adoptarlo: el hallazgo se publica y
se discute, no se esconde.

**Comunicación (§ rúbrica 6-7).** El backtest no basta con existir: `docs/backtest.md` lleva un
resumen de ≤ 5 líneas más la tabla, incluida la limitación de §4.1, y el drawer de metodología del
frontend muestra dos o tres cifras de "qué tan bien acertó el modelo en el pasado" en lenguaje
llano — sin presentar la comparación censo-CONAPO como si fuera esa validación.

## 5. (c) Geografía AGEB 2010 → 2020 (datos completos) ✅

- Claves: 2,430 en ambos censos, 3 solo en 2020, 2 solo en 2010 (`censo_ageb_panel.parquet`).
- Traslape de áreas MG 2010 v5.0 vs MG 2020 (`equivalencia_ageb_2010_2020.parquet`), por AGEB
  urbana 2020: **misma** 2,331 (≥ 95 % de área compartida en ambos sentidos); **fusión/expansión** 62
  (la 2020 cubre ≥ 95 % de la 2010 pero es mayor: bordes urbanos que crecieron); **cambio de
  límites** 37; **división** 1. Las 100 no-"misma" suman 60,820 niños (3.7 % del total 2020).
- Tratamiento: "misma" → tasa directa; división → **tasa** de la madre 2010 aplicada a la hija (sin
  reescalar `D_2010` por `frac_de_2010`; ambas variantes dan la misma tasa y difieren solo en `ψ`);
  fusión/expansión y cambio de límites → tasa directa con la misma clave, pero confianza máxima
  **media** (el denominador 2010 cubre otra superficie); sin contraparte → `r̃_i = ρ_m`,
  `n_obs = 1`, confianza **baja**.

## 6. Oferta

Tasa Poisson log-lineal sobre las fechas de levantamiento (2016.79, 2019.87, 2024.87) + EB hacia la
alcaldía, sin control externo. ✅ Tope de confianza **media** en toda la capa. ✅ `sin_datos` si
`S = 0` en los tres cortes. ✅

### 6.1 La caída 2024-11 es una hipótesis, no un hecho ✅ (fase 3)

La caída del corte 2024-11 (−11.2 % global; privado −22.8 %, preescolar privado −38.7 %; público
+1.2 %; solo reaparece el 3 % de las bajas) se venía tratando como **certeza**: cierres reales
acumulados 2020–2023 registrados de golpe al volver a campo. Es la lectura más plausible, pero **no
está demostrada** (`correccion/detalles_a_tratar.md` §4). Se reporta como dos escenarios:

| Escenario | Supuesto | Efecto sobre la tasa de oferta |
|---|---|---|
| **A** (principal) | Cierres reales acumulados 2020–2023, registrados al volver a campo | Tasa repartida en los 5 años entre levantamientos (comportamiento actual) |
| **B** (sensibilidad) | Parte de la caída es depuración del padrón, no cierre | Tasa atenuada; el rango A–B se publica como sensibilidad |

Ambos escenarios van a `diagnostico.json` y el rango entre ellos se menciona en el drawer. No se
duplica el contrato: el veredicto publicado sigue siendo el del escenario A.

### 6.2 Sobredispersión y piso de incertidumbre ✅ (fase 3; hallazgo adicional, ver nota)

El Poisson puro subestima la varianza: con 3 cortes y 2 parámetros, `var(b_i)` sale del error de
conteo y produce intervalos de ancho casi nulo — el hallazgo original era
`agregado_cdmx.oferta.h3.ic95 = [-6.9, -6.9]`, un intervalo degenerado. Dos correcciones estaban
previstas, de naturaleza distinta:

- **Factor quasi-Poisson** `φ_m = χ²(Pearson)/gl`, estimado **agrupado por alcaldía** (con 1 grado
  de libertad por AGEB, `φ` individual es puro ruido) y aplicado por AGEB: `var(b_i) ← φ_m · var(b_i)`,
  con `φ_m ≥ 1`. Implementado en `modelos.calcular_phi_por_alcaldia`. Con datos reales, `φ_m = 1.0`
  en las 16 alcaldías (sin sobredispersión detectable más allá del error de conteo puro).
- **Piso `SIGMA_MIN_OFERTA`** (§2.7): calibrado en `0.0` (igual que demanda).

**Ninguna de las dos, por sí sola ni juntas, corrigió el intervalo degenerado.** El hallazgo real,
descubierto al verificar el pipeline con datos reales tras implementarlas (no estaba en ningún plan
anterior), tiene dos partes:

1. **Ajustes casi separados envenenan el promedio de `tau2`.** Conteos como `[1, 0, 0]`
   (un establecimiento en 2016, ninguno después) hacen que la matriz de información de Fisher de
   `_newton_raphson_poisson` sea casi singular: `var(b_i)` explota a ~3×10⁹ (73 de 2023 AGEB con
   dato, separación nítida frente al resto: ~0.01-0.1). `contraccion_eb` estima `tau2` como
   `mean((b̂-b_m)²) - mean(var(b))` **agrupado sobre todas las unidades que recibe**: un puñado de
   `var(b)` astronómicos domina esa media y colapsa `tau2` a `0` para **toda la alcaldía**, no solo
   para esas AGEB. Corrección: `contraccion_eb` acepta ahora una máscara opcional
   `usar_para_tau2` — las AGEB con ajuste no confiable (`ajustar_oferta` añade la columna
   `ajuste_confiable`) se excluyen **solo** del promedio que estima `tau2`, pero siguen recibiendo
   su propio `B_i`/`r̃_i`/`var_post_i` con su varianza real (con `tau2` ya sano, su enorme `psi`
   las contrae casi del todo hacia la alcaldía — la respuesta correcta para un ajuste no confiable,
   no un valor inventado).
2. **Con `tau2` ya sano, seguía colapsando.** Las 16 alcaldías de CDMX muestran, genuinamente,
   *menos* dispersión entre sus AGEB (`mean((b̂-b_m)²) ≈ 0.0059`) que ruido de conteo dentro de cada
   una (`mean(var(b)) ≈ 0.0157`, con las 73 AGEB ya excluidas) — un resultado honesto del método de
   momentos, no un error. Eso empuja `B_i → 1` para casi todas las AGEB, y la fórmula ingenua de
   Fay-Herriot `var_post = (1-B)·ψ` colapsa a `~0` cuando `B → 1`, **porque trata `b_m` (la
   pendiente de la alcaldía) como una constante exacta** — pero `b_m` es ella misma una estimación
   (`_newton_raphson_poisson` sobre la suma de conteos de la alcaldía), con su propia varianza
   muestral. Corrección: `modelos.simular_oferta` propaga esa varianza con la aproximación de
   primer orden `var_post ← var_post + B_i² · var(b_m) · φ_m` (tratando `b_m` como aleatoria en
   `r̃ = B·b_m + (1-B)·b̂`). Esto **no inventa precisión**: al contrario, reconoce una fuente de
   incertidumbre real que la fórmula Fay-Herriot ingenua (la que ya se usaba, sin cambios, para
   demanda) pasaba por alto. Demanda no mostró el mismo colapso porque el choque compartido `ε_m`
   (§2.6) ya inyecta una varianza de alcaldía después de la contracción EB; oferta no tenía ningún
   término análogo.

Verificado con datos reales tras ambas correcciones: `agregado_cdmx.oferta.h3.ic95 = [-7.0, -6.8]`
(antes `[-6.9, -6.9]`); AGEB individuales pasan de intervalos idénticos y degenerados a intervalos
propios y no triviales (p. ej. `[-11.0, -1.3]`). `test_modelos.py` incluye una prueba de regresión
específica (`test_ic95_no_degenerado_cuando_tau2_colapsa_honestamente`).

**Lo que se retira de esta sección:** la versión anterior de este documento proponía como criterio
de aceptación "ningún registro con `ic95[1] − ic95[0] < 0.2`". Es un criterio equivocado: fuerza un
ancho mínimo elegido a ojo, sin relación con qué tan bien calibrado está el modelo — un intervalo
ancho no es automáticamente un intervalo *correcto*. El criterio correcto, y el único que se usa de
aquí en adelante, es el de §2.7: **cobertura empírica del IC95 en el backtest dentro de
`[0.90, 0.97]`**. Un intervalo puede ser angosto y estar bien calibrado (si el backtest lo confirma),
o ancho y seguir mal calibrado; el ancho por sí solo no dice nada.

### 6.3 Horizontes de reporte de la oferta

**La oferta reporta `h1` y `h3` (2027-06 y 2029-06); no reporta `h5`.** A diferencia de la demanda,
la oferta no se controla contra ninguna serie externa y su único ancla temporal es el propio
levantamiento DENUE (§1); 3 años desde la fecha base sigue siendo el techo defendible, pero un año
sí es reportable y la rúbrica lo pide. `h5` no se calcula ni se publica para esta capa
(`config.HORIZONTES_OFERTA = ("h1", "h3")`, contrato v1.4: `horizontes_disponibles: ["h1","h3"]`).

### 6.4 Lo que la oferta NO mide

Un establecimiento cuenta igual que otro. No se conoce su capacidad, su matrícula ni su calidad; no
se distingue con precisión disponibilidad pública de privada; no se calcula distancia ni tiempo de
traslado. Por eso "establecimientos por cada 1,000 niñas y niños" es una **aproximación de
disponibilidad**, no una medida de cobertura real (`correccion/detalles_a_tratar.md` §6E). Esta
advertencia es obligatoria en el drawer de metodología del frontend.

## 7. (d) Regla de decisión y sensibilidad de la banda ✅

Regla única (`modelos.py`) sobre la distribución simulada de la tasa proyectada:
- `sube` si `P(tasa > +δ) ≥ 0.80`; `baja` si `P(tasa < −δ) ≥ 0.80`; `se_mantiene` si
  `P(|tasa| ≤ δ) ≥ 0.50`; si no, `se_mantiene` con confianza **baja**.
- Confianza: **alta** si la probabilidad decisiva ≥ 0.95 y el veredicto no cambia con `λ`;
  **media** si ≥ 0.80; **baja** en el resto, y siempre con `n_obs = 1` o `D_2020 < 100` (141 AGEB).

**`tasa_anual_pct` y `delta_pct` (contrato v1.4, `modelos.resumir()`).** `tasa_anual_pct` es la
tasa `r_i,fut` proyectada × 100 (tasa logarítmica, coherente con la banda δ): depende solo de la
simulación de la tasa, no del horizonte de reporte, así que **es idéntica en `h1`, `h3` y `h5`** —
al igual que el veredicto y la confianza, que se calculan sobre esa misma tasa (`P(tasa > +δ)`,
etc.). Lo único que varía entre horizontes es `delta_pct`/`ic95`: se miden desde la **fecha base**
(`T_BASE = 2026.5`, no desde el censo 2020) hasta cada horizonte
(`100·(e^(r·(t_horizonte − 2026.5)) − 1)`), por lo que su magnitud crece de `h1` a `h5` aunque la
tasa no cambie. Esto es deliberado: separa "¿hacia dónde va la tendencia?" (una sola respuesta, la
tasa) de "¿cuánto se acumula a 1, 3 o 5 años?" (tres respuestas, el `delta_pct`).

> **Decir esto antes de que lo pregunten.** Que el veredicto no cambie entre horizontes es una
> propiedad del modelo log-lineal, no un error de implementación: con una sola tasa por unidad, el
> signo de la tendencia no puede depender de cuándo se la mire. Va explicado en el drawer de
> metodología del frontend.

Sensibilidad con tasas **históricas** directas 2010–2020 (2,268 AGEB), % por clase:

| δ (%/año) | baja | se_mantiene | sube |
|---|---|---|---|
| 0.5 | 82.0 | 9.1 | 8.9 |
| **1.0** | **73.9** | **19.1** | **6.9** |
| 2.0 | 49.3 | 46.3 | 4.4 |

Con CONAPO las tasas 2020–2027 de alcaldía son más negativas (−1.45 a −4.19 %/año, problemas N2):
el reparto proyectado tendrá aún más `baja`. **Umbral final: δ = 1 %/año y probabilidad ≥ 0.80**
(≈ 0.5 τ; ±5 % acumulado a 2031-06, ~29 niños en la AGEB mediana de 583, 1–2 grupos escolares). Se
publican las tres bandas en el panel de metodología.

### 7.1 Por qué el veredicto no basta como producto

Con estas tasas, casi toda la ciudad sale `baja` (AGEB, `h3`: `baja` 2 181, `se_mantiene` 180,
`sube` 6, `sin_datos` 86). Eso es demográficamente correcto y **no** se maquilla, pero un mapa casi
monocromo no ayuda a decidir (`correccion/detalles_a_tratar.md` §6G). La pregunta útil no es "¿dónde
disminuye la población infantil?" sino "¿dónde disminuirá **más lentamente la demanda que la
oferta**, y por tanto crecerá la presión sobre los servicios existentes?". Esa pregunta la responde
el §10, no el veredicto.

## 8. Datos insuficientes y agregación ✅

- `sin_datos` (demanda): AGEB rural (22 en `09ar`, CVEGEO de 9 caracteres); 0–14 suprimido por
  INEGI (41 AGEB en 2020); `D_2020 < 20` (23); AGEB urbana 2020 sin polígono (2) o sin censo. Nunca se imputa.
- Alcaldía: `D_m = Σ_{i∈m} D_i` sobre AGEB urbanas con dato; `Δ%` desde sumas, no promedios; IC de
  la simulación conjunta; cobertura vs CONAPO reportada. Tests: suma AGEB = alcaldía, sin `CVEGEO`
  duplicados, veredictos en el conjunto válido.
- Milpa Alta (009): las AGEB urbanas cubren 82.8 % de su población. El veredicto de alcaldía se
  publica igual, **etiquetado "solo urbano"** en la ficha y en el drawer; no se le aplica tope de
  confianza, porque la limitación es de cobertura territorial, no de calidad del dato.
- **Ausencia de datos ≠ ausencia de demanda** (`correccion/rubrica.md` §8). `sin_datos` significa
  "no podemos estimarlo", nunca "aquí no hace falta el servicio". La leyenda del mapa lo dice con
  patrón y etiqueta, no solo con color.

## 9. Métodos descartados (una línea)

Theil-Sen/Mann-Kendall: 2–3 puntos efectivos. · Poisson/BN independiente: sin contracción e IC
~3.5× estrechos. · GLMM con pendiente aleatoria: equivalente al EB e inestable con 2 tiempos. ·
Hamilton-Perry: requiere quinquenios por AGEB. · Covariables espaciales estáticas como modelo
principal: no identifican cambio; solo como media previa del EB si mejoran §4, o como contexto
descriptivo (§1.4). · Aprendizaje automático (bosques, redes): con 2–3 momentos por unidad
sobreajusta y pierde interpretabilidad sin ganar precisión verificable; la rúbrica valora
"coherencia, interpretación y reproducibilidad" por encima de la sofisticación técnica aislada
(`correccion/rubrica.md` §4).

## 10. Cobertura proyectada, índice de oportunidad e índice de disponibilidad (✅ fase 6:
fórmulas en `features.py` y publicación en el contrato v1.4)

La rúbrica pide que la aplicación diga **dónde hay oportunidades de expansión y cómo rankearlas**
(`correccion/rubrica.md` §2), y su caso de prueba es "zonas donde la demanda aumentará en tres años,
evitando áreas con oferta ya saturada". Hoy el sistema proyecta demanda y oferta **por separado** y
nunca las combina hacia el futuro: la brecha publicada es `S_2024 / D_2020 × 1000`, histórica y con
dos años distintos en numerador y denominador.

**Generalización a cuatro ramas (Habitancia, `correccion/frontend_requisitos.md`).** El producto ya
no expone una sola capa de oferta; expone cuatro **ramas** — educación y cultura, salud, comercio,
áreas verdes y espacio público — cada una con su propia disponibilidad. Esta sección define el
índice **por rama** (§10.2) y cómo el frontend lo combina en un índice compuesto sin volver a llamar
al backend (§10.5). El backend nunca decide el peso de cada rama: eso es una preferencia del usuario,
aplicada en el cliente (`correccion/frontend_requisitos.md` §9, "los pesos NO alteran los datos").

### 10.1 Cobertura proyectada por rama ✅ fase 6 (`features.cobertura_proyectada`,
`nivel_rama_por_celda`)

Por AGEB *i*, horizonte *h*, segmento de población objetivo (§1.1) y rama *r* ∈
{educación, salud, comercio, verde}, calculada **sobre las mismas réplicas Monte Carlo** de §2.6 y
§6 — no sobre las medianas —, de modo que el intervalo de la cobertura sale de la propia simulación
y no de una propagación aparte:

```
cobertura_{i,h,r}^s = Ŝ_{i,h,r}^s / D̂_{i,h,seg}^s × 1000
```

`Ŝ_{i,h,r}` es la oferta proyectada de la rama (§10.6: educación, salud y comercio tienen serie
DENUE con tendencia; áreas verdes y espacio público no tienen serie temporal, así que `Ŝ_{i,r}` es
el valor **actual**, sin proyección — nunca se inventa una tendencia donde no hay datos para
estimarla, ver `correccion/frontend_requisitos.md` §16). Se publican mediana e IC95.
`Ŝ` y `D̂` se evalúan en el **mismo** instante `t_h`, a diferencia de la brecha histórica actual.

**Tratamiento de oferta cero (obligatorio, no opcional).** `Ŝ_{i,h,r} = 0` con `D̂_{i,h,seg} > 0` es
un valor **válido**, no `sin_datos`: una zona con población objetivo y cero establecimientos de una
rama es exactamente la señal de mayor oportunidad, y debe aparecer arriba del ranking, no
desaparecer de él. Solo se marca `sin_datos` cuando el **denominador** es inválido: `D̂ = 0`,
`D̂` no calculable (AGEB rural o suprimida, §8) o el conteo base de esa rama en esa AGEB nunca superó
el umbral mínimo de conteo (an análogo a `D_MIN_CONF`, ver plan §5 `S_MIN_CONF`). Un `Ŝ = 0`
genuino nunca se sustituye, no se suma `+0.5` fuera del ajuste Poisson interno (que ya lo maneja),
y no se excluye del ranking.

### 10.2 Índice de oportunidad por rama — fórmula exacta ✅ fase 6 (`features.indice_oportunidad`,
`sensibilidad_indice_oportunidad`)

**Variables de entrada**, todas ya definidas arriba o en modelos.py:
- `cobertura_{i,h,r}` (mediana de §10.1): nivel de disponibilidad proyectada.
- `tasa_D_{i,seg}` = `tasa_anual_pct` de la demanda potencial del segmento elegido (§2, idéntica en
  todos los horizontes).
- `tasa_S_{i,r}` = `tasa_anual_pct` de la oferta de la rama (§6; `= 0` sin cambio para verde, que no
  tiene tendencia).

**Paso 1 — nivel, por percentil inverso.** Entre las AGEB con `cobertura` válida (no `sin_datos`)
del mismo segmento, horizonte y rama:

```
N_{i,h,r} = 1 − rango_percentil( cobertura_{i,h,r} )        ∈ [0, 1]
```

`rango_percentil` usa el método de **rango fraccionario con empates promediados** (`scipy`-style
`average`): todas las AGEB con `cobertura = 0` reciben el mismo rango (el más bajo) y por tanto el
mismo `N = 1` (máxima oportunidad de nivel) — así es como se resuelve el caso de oferta cero sin
tratarlo como un caso especial de la fórmula: cae naturalmente en el extremo superior del ranking.

**Paso 2 — tendencia comparativa, acotada.** Una zona donde la demanda cae más lento que la oferta
(o crece mientras la oferta no) tiene más presión futura que una con el mismo nivel de cobertura
hoy pero tendencias parejas:

```
Δ_{i,r} = tasa_D_{i,seg} − tasa_S_{i,r}                      (pp/año, log-tasa)
ajuste_{i,r} = clip( Δ_{i,r} / K, −0.15, +0.15 )
```

`K` es la constante de normalización, en puntos porcentuales anuales que producen el ajuste máximo
de ±0.15; **valor por omisión `K = 5`** (una brecha de 5 pp/año entre demanda y oferta ya satura el
ajuste). El límite ±0.15 es deliberado: el nivel de cobertura (paso 1) sigue siendo el componente
dominante del índice; la tendencia solo puede mover el resultado 15 puntos porcentuales del rango
`[0,1]`, nunca invertir un extremo por el otro.

**Paso 3 — índice final por rama:**

```
O_{i,h,r} = clip( N_{i,h,r} + ajuste_{i,r}, 0, 1 )
```

**Análisis de sensibilidad (obligatorio, va a `diagnostico.json`, no al contrato):** `O_{i,h,r}` se
recalcula con `K ∈ {3, 5, 8}` pp/año. Si el orden relativo de las AGEB cambia sustancialmente entre
`K=3` y `K=8` para una unidad, esa unidad se marca con una bandera de sensibilidad en el
diagnóstico (mismo patrón que la sensibilidad de `δ` en §7). El valor de `K` **no se expone como
parámetro de usuario** en esta fase: es una constante de calibración del backend, documentada aquí;
`correccion/rubrica.md` no pide que el usuario la ajuste, y exponerla sin explicación violaría
`correccion/frontend_requisitos.md` ("no mostrar fórmulas ni parámetros internos del modelo").

### 10.3 Índice compuesto (client-side, tiempo real) — vista general de Habitancia

El **índice compuesto** que colorea la "Vista general" del mapa (`correccion/frontend_requisitos.md`
§11A) se calcula **en el navegador**, no en el backend, porque depende de los pesos que el usuario
mueve en tiempo real:

```
IC_{i,h} = ( Σ_{r ∈ ramas_con_dato} w_r · O_{i,h,r} ) / ( Σ_{r ∈ ramas_con_dato} w_r )
```

`w_r` ∈ {1, 2, 3, 4, 5} (los cinco círculos de prioridad). **Renormalización sobre ramas con dato:**
si una rama es `sin_datos` para esa AGEB, se excluye tanto del numerador como del denominador —
nunca se sustituye por 0 (bajaría artificialmente el índice) ni por el promedio de las demás (lo
inventaría). Si **todas** las ramas son `sin_datos` para una AGEB, la AGEB completa es `sin_datos`
en la vista general y se muestra con el patrón correspondiente (nunca oculta ni con valor `0`).

Este cálculo, y el de §10.2 sobre subconjuntos filtrados de establecimientos, son responsabilidad
del **motor de composición del frontend** (`plans/frontend_specs.md` §17, "motor de composición
cliente"); el backend solo garantiza que cada rama, para cada combinación de filtro que publica
(§10.6), traiga los ingredientes (`cobertura`, `tasa_D`, `tasa_S`, o los conteos base para
recomponerlos) necesarios para que el cliente evalúe §10.1–10.3 sin volver a pedir datos.

### 10.4 Filtro de nivel de riesgo

`correccion/rubrica.md` §2 lista el **nivel de riesgo aceptable** como entrada esperada de la
aplicación. Se expone `p_dec` y la confianza de la capa demanda (por segmento) como umbral
ajustable: el ranking solo lista unidades que lo superan. Esto también resuelve §7.1 — deja de
importar que casi todo sea `baja`, porque el orden lo da `O_{i,h,r}` / `IC_{i,h}`, no el signo del
veredicto.

### 10.5 Índice de disponibilidad para familias (vista separada) ✅ fase 6 (`features.indice_disponibilidad`;
`ajuste_estabilidad` es una elección de ingeniería documentada en el docstring, el plan no fija
la fórmula exacta de combinar confianza y tendencia)

`correccion/frontend_requisitos.md` §7 pide una segunda lectura, "Disponibilidad para familias":
ordena primero las zonas con **mayor** disponibilidad relativa de los servicios seleccionados —
justo lo opuesto del índice de oportunidad. Reutiliza los mismos ingredientes de §10.1–10.3, sin
invertir el signo de forma naíf (una alta cobertura hoy no es automáticamente estable): se define
como

```
F_{i,h,r} = clip( rango_percentil( cobertura_{i,h,r} ) + ajuste_estabilidad_{i,r}, 0, 1 )
```

con `ajuste_estabilidad` premiando confianza alta y tendencia de oferta no decreciente (mismo
mecanismo de recorte ±0.15 que §10.2, sobre la sola tasa de oferta, no la comparativa). **Nunca se
mezcla con `O_{i,h,r}`** (`correccion/frontend_requisitos.md` §7: "una zona con poca oferta puede
representar una oportunidad de expansión, pero al mismo tiempo tener baja disponibilidad actual
para las familias").

### 10.6 Ramas, filtros y el contrato de datos ✅ fase 6 (celdas fase 5 `panel.py`; contrato fase 6)

Los filtros de `correccion/frontend_requisitos.md` §10 (nivel/tipo × sector dentro de cada rama)
cambian **qué establecimientos cuentan** como `S` de esa rama — es decir, cambian el subconjunto de
SCIAN/subcategoría sobre el que se ajusta la tendencia Poisson de §6. Para que el filtro se aplique
en tiempo real sin volver a llamar al pipeline, el backend no publica una sola serie `Ŝ_{i,r}` por
rama: publica una serie **por celda de filtro** (segmento SCIAN × sector), y el cliente **suma
valores proyectados y varianzas** de las celdas seleccionadas (nunca suma tasas: la tasa no es
lineal en el conteo, el conteo proyectado sí):

**Celdas implementadas (Fase 5, `panel.py`; cruce por sector añadido en el rework post-Fase 6, ver
§1.2):** educación 24 (8 niveles/tipo `guarderia, preescolar, primaria, secundaria,
educacion_especial, varios_niveles` por SCIAN `Principal`, `media_superior_tecnica,
recreacion_cultura` por SCIAN `Complementario` — verificado en datos reales, "Actividad SCIAN"
literal, nunca supuesto — × 3 sectores `publico/privado/no_especificado`); salud 12 (4 tipos
`clinicas, hospitales, salud_mental, farmacias`, columnas booleanas ya presentes en el dato, más
directas que reclasificar 51 códigos SCIAN, × 3 sectores); comercio 5 (sin sector:
`supermercados_minisupers, abarrotes, frutas_verduras, carnes_otros_alimentos, farmacias`, por
`subcategoria_proyecto`; `farmacias` es la única celda fuera de `es_primera_necesidad`, incluida
porque `correccion/frontend_requisitos.md` §10.3 la deja como opcional, no excluida); verde 3 (sin
sector: `cobertura_verde, areas_recreativas, espacios_publicos`, agregado espacial, sin componente
temporal). `modelos.ajustar_oferta`/`simular_oferta` se reutilizan sin ningún cambio de código por
celda (verificado extremo a extremo con la celda `salud/clinicas`, metodología §6.2 incluida) —
salvo dos guardas nuevas que el cruce por sector hizo necesarias: una celda puede quedar vacía en
TODA la ciudad (`salud/farmacias__publico`, 0 establecimientos en las 3 ediciones: `simular_oferta`
devuelve una `Simulacion` vacía en vez de intentar un ajuste sobre un arreglo de 0 filas) o una
alcaldía puede tener AGEB con dato histórico pero 0 establecimientos en el corte más reciente
(`agregar_alcaldia` excluye esas alcaldías, nunca publica un `nan`); y un tope numérico
`_TASA_MAX=20` sobre la tasa simulada (`modelos.py`, nunca sobre `var_post`, que sigue sin techo)
evita que la cola de una celda muy escasa desborde `exp()` a `inf`/`nan` en cualquier consumidor de
`Simulacion.r_fut`. La publicación de estas celdas en el contrato v1.4
(`construir_capa_rama_v14`/`construir_capa_verde`, `exportar.py`) es Fase 6, entregada:
`capas.ramas.<rama>[cvegeo].celdas.<celda>`.

```
Ŝ_{i,h,r}(filtro) = Σ_{c ∈ celdas(filtro)} Ŝ_{i,h,c}
var(Ŝ_{i,h,r}(filtro)) = Σ_{c ∈ celdas(filtro)} var(Ŝ_{i,h,c})     (independencia aproximada entre celdas, documentada como supuesto)
```

Detalle de celdas por rama, tamaño del contrato y firmas exactas: `plans/backend_plan.md` §11
(tarea B22, "capas por rama y celda de filtro"). Áreas verdes y espacio público no tienen
proyección (§10.1): sus "celdas" son solo el conteo/superficie actual, sin componente temporal.

**Límite de la promesa.** Ni §10.2 ni §10.5 permiten decir "en qué alcaldías conviene vivir": eso
exigiría vivienda, seguridad, movilidad, precios, calidad escolar y capacidad de atención, que no
están en estos datos. La promesa sostenible, y la que usa Habitancia, es: *identificar zonas de la
CDMX donde, de acuerdo con la evolución de la población infantil y la disponibilidad de servicios,
podría existir una mayor oportunidad relativa de ampliar o fortalecer infraestructura para
infancias* (`correccion/frontend_requisitos.md`, línea de misión).
