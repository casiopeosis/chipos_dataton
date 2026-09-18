# Metodología — estimador de demanda no cubierta por alcaldía con intervalos de confianza

Estado: **propuesta para revisión del equipo** (CLAUDE.md §4: se discute y aprueba antes de escribir código de modelado).
Fecha: 2026-09-18. Rama: `reorganizacion`.
Insumos leídos: `CLAUDE.md`, `docs/current-state.md`, `docs/architecture-plan.md`, `docs/legacy/semaforo_v1.json` y el código que lo generó (`src/engine.py`).

Alcance: **solo alcaldía** (16 unidades). No hay AGEB en ninguna parte de este documento, ni ganchos para agregarlo después (CLAUDE.md §1, §3).

---

## 0. Decisiones que este documento toma

| # | Decisión | Por qué | Sección |
|---|---|---|---|
| D1 | El semáforo mide **demanda no cubierta relativa**: el déficit de oferta por cada 100 mil personas del grupo objetivo, comparado con el promedio de la CDMX. No mide la población objetivo sola. | La población objetivo por sí sola no requiere estimación ni intervalo (es un conteo censal) y pintaría siempre de rojo a Iztapalapa y Gustavo A. Madero. | §1 |
| D2 | **Rojo = demanda alta / déficit.** Es la semántica **inversa** a la de v1, donde verde significaba "baja oferta, oportunidad de inversión". | CLAUDE.md §1: el mapa colorea "según el nivel de demanda estimado". | §7 |
| D3 | Gimnasios y escuelas de deporte **quedan fuera** del dominio adultos mayores. PILARES **no se suma** a ningún dominio y se muestra solo como contexto. | Los gimnasios no están dirigidos a personas de 60 años o más (README del censo: "no es correcto dividir todos los gimnasios entre 60+"). La pregunta 9 de current-state (a quién atiende PILARES) sigue abierta. | §2 |
| D4 | La población se toma **fija en 2020**. La parte "a futuro" del semáforo solo refleja la tendencia de la oferta. | Solo hay un año censal en `data/`, así que el cambio poblacional no se puede estimar. Si el equipo consigue las proyecciones de CONAPO por municipio y edad, el método las admite sin cambios (§6.4). | §6.4, §9 |
| D5 | Cultura usa un intervalo de **otra naturaleza** (Poisson sobre una sola foto) y **no tiene tendencia ni proyección**. | `AREAS_CULTURALES_CDMX` es un único corte del SIC, no una serie. | §5 |
| D6 | El umbral de materialidad es δ = 10 % del promedio de la CDMX, y el nivel del intervalo es 95 % individual. Ambos quedan fijados **antes** de ver los resultados. | Evita ajustar la regla a posteriori para que el mapa "se vea bien". | §7, §11 |

---

## 1. Qué se estima (el estimando)

Notación. `a` es una alcaldía (16), `d` un dominio (infancia, adultos mayores, cultura), `g(d)` el grupo poblacional asociado al dominio y `t*` la fecha de referencia del semáforo.

- **Población objetivo** `P_a`: personas del grupo `g(d)` en la alcaldía `a`, según el Censo 2020. Se trata como constante conocida (§9).
- **Nivel de oferta** `μ_a(t*)`: número *esperado* de establecimientos del dominio en `a` en la fecha `t*`. Es el nivel estructural, sin el ruido de captura entre ediciones del DENUE (altas y bajas no registradas a tiempo, reclasificaciones SCIAN).
- **Cobertura**: `θ_a = 10⁵ · μ_a / P_a`, en establecimientos por cada 100 mil personas del grupo.
- **Cobertura de referencia de la CDMX**: `θ_ref = 10⁵ · Σ_b μ_b / Σ_b P_b`. Es la cobertura de la ciudad completa, no el promedio simple de las 16 tasas.
- **Estimando principal: déficit de cobertura**

  ```
  D_a = θ_ref − θ_a
  ```

  `D_a > 0` significa que la alcaldía tiene menos oferta por habitante del grupo que la ciudad en conjunto, es decir, más demanda no cubierta. `D_a` está en las mismas unidades que θ.
- **Estimando derivado para la UI: establecimientos faltantes**, `F_a = D_a · P_a / 10⁵`. Es el número de establecimientos que harían falta para igualar la cobertura de la CDMX.

**Por qué este estimando y no la razón `θ_a / θ_ref`.** `D_a` es una **combinación lineal** de los `μ_b`, porque las `P` son constantes. Si cada `μ̂_b` es insesgado, `D̂_a` es **exactamente insesgado** y su varianza tiene forma cerrada (§6). Una razón o un logaritmo solo serían insesgados de manera asintótica (desigualdad de Jensen), y con conteos de 5 a 40 establecimientos, como en adultos mayores, ese sesgo no es despreciable.

**Qué significa "insesgado" aquí, con precisión.** El estimador es insesgado para `D_a` tal como está definido arriba (oferta registrada en DENUE/SIC por población censal), bajo el modelo de §4. **No** es insesgado para la "demanda real no cubierta" en sentido amplio: capacidad por establecimiento, uso entre alcaldías, oferta informal y subregistro del DENUE son sesgos del estimando, no del estimador. Se listan en §9 y deben mostrarse en la UI.

---

## 2. Insumos por dominio

| | Infancia | Adultos mayores | Cultura |
|---|---|---|---|
| Fuente | `INFANCIAS_YYYY_MM` (11 ediciones) | Gen A `OCTUBRE 2016`, `NOVIEMBRE 2017/2018/2020 CDMX` + Gen B `NOVIEMBRE 2022/2023/2024`, `MAYO 2025/2026 CDMX` | `AREAS_CULTURALES_CDMX` (1 foto del SIC) |
| Qué se cuenta | Códigos SCIAN **núcleo** del catálogo de infancias (guarderías 624411–624412 y educación 6111xx que el catálogo marca como principales). **Se excluyen** los códigos que solo entran por las banderas opcionales (`incluir_apoyo_social_y_residencias`, `incluir_clubes_y_recreacion`, `incluir_formacion_complementaria`, `incluir_media_superior`). | SCIAN **623311–623312** (asilos y residencias para adultos mayores). Los centros de cuidado diurno 624121–624122 (`alcance_analitico = Complementario`) solo entran en el análisis de sensibilidad. | Todos los registros SIC de TEATRO, CENTRO_CULTURAL y CINE (868), incluidos los que son PILARES (`es_pilares = SI`). **No** se suma `PILARES CDMX` aparte. |
| Denominador `P_a` | Población de 0–17 años | Población de 60 años o más (65+ en sensibilidad; nunca se suman) | Población total |
| Ediciones en el ajuste principal | Las 11: 2016-10 → 2026-05 | 9 verificadas: 2016-10, 2017-11, 2018-11, 2020-11, 2022-11, 2023-11, 2024-11, 2025-05, 2026-05. **Fuera:** 2021-11 (carpeta rota, `edicion_verificada=false`) y 2019-11 (no existe). | 1 |
| Modelo de oferta | Tendencia lineal cuasi-Poisson agrupada (§4) | Tendencia lineal cuasi-Poisson agrupada (§4) | Poisson de un solo corte (§5) |

Reglas de datos que el ETL debe garantizar antes de modelar. Ya están en `docs/architecture-plan.md` y aquí se vuelven requisito:

1. **Fechas de Gen A**: la edición se resuelve **solo** desde `fuente.archivo` (`denue_09_MMAA.zip`). Nunca se usan `anio_datos`, `mes_corte`, `edicion` ni `nota_temporal`, ni del JSON ni de las columnas de fila (CLAUDE.md §1.1). Una fecha mal resuelta desplaza el eje `t` y sesga la pendiente, que es exactamente el sesgo que este estimador promete no tener.
2. **Conjunto SCIAN armonizado**: el conjunto de códigos contados debe ser **idéntico en todas las ediciones** de un dominio. Si 623311–623312 no aparece con la misma definición en Gen A y Gen B, la serie de adultos mayores no se modela sin antes resolverlo con el equipo.
3. **Ceros explícitos**: una alcaldía sin establecimientos en una edición vale 0, no falta.
4. **Unión por clave**: por `cve_alc`, nunca por nombre, por el mojibake de Gen A.
5. **Tiempo real**: `t` se mide en años transcurridos desde la primera edición del dominio, con fechas reales (día 1 del mes de corte). No se asume espaciado uniforme, igual que en v1.

---

## 3. Punto de partida: qué hace v1 y qué cambia

v1 (`src/engine.py`, salida `docs/legacy/semaforo_v1.json`) ajusta, por alcaldía y categoría, una recta de mínimos cuadrados a 5 ediciones Gen B (2022-11 → 2026-05). Proyecta a 3, 5 y 7 años con intervalos de **predicción** t de Student (gl = 3, t = 3.18) y clasifica el semáforo por terciles de percentiles de oferta per cápita y de pendiente.

Se **conserva** de v1:
- la regresión lineal sobre el tiempo real en años;
- la distribución t de Student en lugar de z = 1.96;
- la validación retrospectiva y la validación cruzada, que se generalizan en §10;
- la serie histórica y el desglose por subcategoría y sector como contenido del panel de detalle.

Se **cambia**, con evidencia medida sobre el propio `semaforo_v1.json`:

| Problema en v1 | Evidencia | Qué hace esta metodología |
|---|---|---|
| El error estándar se estima **por serie**, con 3 grados de libertad. Una serie que casi cae sobre la recta obtiene una banda casi nula, y una ruidosa, una enorme: el ancho del intervalo depende del azar de 5 puntos. | `tendencia_dof = 3`, `t_crit = 3.18` en las 32 zonas. | Dispersión **agrupada** entre las 16 alcaldías de un dominio, con varianza proporcional a la media (§4.3). Con los mismos datos de v1: φ̂ = 0.147 (gimnasios) y 0.097 (adultos mayores), gl = 48, t = 2.01. Con la serie completa de 9 a 11 ediciones, gl ≥ 112. |
| El intervalo que se muestra es de **predicción** (`1 + 1/n + …`): incertidumbre sobre el próximo conteo observado, no sobre el nivel de oferta. | `ols_fit.predict` en `src/engine.py`. | El semáforo usa el intervalo de **confianza** del nivel `μ_a(t*)` (§4.4). El de predicción queda solo para la validación (§10), que es donde corresponde. |
| `max(y0, 0)` trunca la estimación puntual en cero. | `src/engine.py`, `predict`. | La estimación puntual **no se trunca**, porque truncar introduce sesgo. Solo el límite inferior *mostrado* se recorta a 0, y se marca (§12). |
| Semáforo por percentiles de estimaciones **puntuales**: el intervalo no influye en el color. La regla además tiene `oferta_baja and (crece or True)`, así que toda alcaldía de oferta baja sale verde sin importar la tendencia. | `classify_semaforo`. | El color se decide con el intervalo de `D_a` contra 0 y contra un umbral de materialidad δ (§7). Una alcaldía cuyo intervalo no permite concluir **no** recibe rojo ni verde. |
| Horizontes de 3, 5 y 7 años a partir de una ventana de 3.5 años: extrapolación de hasta el doble de la ventana observada. | `horizontes: [3, 5, 7]`. | El semáforo usa la fecha de la última edición. Las proyecciones son secundarias y se limitan a `h ≤ min(3, ventana/2)` (§8). |
| La validación retrospectiva entrena con 3 puntos (gl = 1, t = 12.7). La cobertura de 62/64 que reporta **no es evidencia de calibración**: los intervalos son enormes por construcción. | `validacion_retrospectiva` con entrenamiento 2022–2024. | Validación con origen móvil agrupada, criterio de aceptación numérico y corrección automática de φ si falla (§10). |
| El denominador es la población **total** para todas las categorías. | `poblacion_2020` es la total en ambas categorías. | Población del grupo objetivo desde el xlsx del censo (§2). |
| Los gimnasios se tratan como dominio junto a adultos mayores. | `categorias`. | Fuera del semáforo (D3). |

---

## 4. Modelo de oferta para dominios con serie histórica (infancia, adultos mayores)

### 4.1 Modelo

Para cada alcaldía `a` y cada edición `j` con fecha `t_j`:

```
y_aj = α_a + β_a · t_j + ε_aj
E[ε_aj] = 0,   Var(ε_aj) = φ · m_a,   ε independientes entre alcaldías
```

- `y_aj` es el conteo observado de establecimientos.
- La **media** es lineal en `t`, con intercepto y pendiente propios de cada alcaldía, como en v1.
- La **varianza** es proporcional al nivel medio de la serie `m_a` (varianza tipo cuasi-Poisson). Una sola constante φ, **común a las 16 alcaldías del dominio**, mide cuánto fluctúa un conteo entre ediciones en relación con su tamaño. Así se puede agrupar la información de todas las alcaldías aunque sus conteos vayan de 5 a más de 500.
- Se toma `m_a` constante dentro de cada serie (su nivel medio) y no `μ_aj`. Con series que se mueven ±10 % alrededor de su media la diferencia es despreciable, y a cambio la estimación puntual queda en OLS puro, que es exactamente insesgado (§4.2).

Por qué varianza ∝ media y no constante: los conteos de adultos mayores rondan la decena y los de infancia llegan a cientos por alcaldía. Una varianza constante agrupada subestimaría el ruido en las alcaldías grandes y lo sobreestimaría en las chicas.

Por qué φ puede ser menor que 1: el DENUE es un directorio de establecimientos, casi un censo, no una muestra. El conteo de una edición a la siguiente se parece más a un stock persistente que a un proceso de Poisson independiente. v1 lo confirma: φ̂ ≈ 0.10–0.15. Se estima φ en lugar de suponer φ = 1.

### 4.2 Estimación puntual (insesgada)

Como `Var(ε_aj)` es constante dentro de cada serie, los mínimos cuadrados ponderados con peso `1/(φ m_a)` coinciden con **OLS por alcaldía**:

```
β̂_a = Σ_j (t_j − t̄_a)(y_aj − ȳ_a) / S_a,      S_a = Σ_j (t_j − t̄_a)²
α̂_a = ȳ_a − β̂_a · t̄_a
μ̂_a(t*) = α̂_a + β̂_a · t*
```

Bajo el modelo, `E[μ̂_a(t*)] = μ_a(t*)` exactamente (teorema de Gauss-Markov; no requiere normalidad). La estimación **no se trunca** en 0.

### 4.3 Dispersión agrupada

```
φ̂ = (1/ν) · Σ_a RSS_a / ȳ_a,      RSS_a = Σ_j (y_aj − α̂_a − β̂_a t_j)²,      ν = Σ_a (n_a − 2)
```

- `E[RSS_a] = (n_a − 2) φ m_a`, así que φ̂ es insesgado si se conoce `m_a` y aproximadamente insesgado con `ȳ_a` en su lugar.
- Grados de libertad: infancia ν = 16 × (11 − 2) = 144; adultos mayores ν = 16 × (9 − 2) = 112.
- Las alcaldías con `ȳ_a = 0` (ningún establecimiento en toda la serie) no aportan a φ̂. Su `μ̂ = 0` y `V = 0`, y se marcan `sin_oferta_observada`.
- Si la validación (§10.1) muestra infracobertura, φ̂ se reemplaza por `κ · φ̂`.

### 4.4 Varianza e intervalo de confianza del nivel de oferta

```
V_a = Var(μ̂_a(t*)) = φ̂ · ȳ_a · [ 1/n_a + (t* − t̄_a)² / S_a ]
IC_{1−α}(μ_a) = μ̂_a(t*) ± t_{ν, 1−α/2} · √V_a
```

Es un intervalo de **confianza** del nivel, sin el término `1 +` del intervalo de predicción. Con la serie de adultos mayores (9 ediciones), una alcaldía con ȳ ≈ 10 y φ ≈ 0.1 da un semiancho de ≈ ±1.2 establecimientos en la última edición. Estos intervalos del DENUE van a ser **estrechos**, y por eso son necesarios el umbral de materialidad (§7) y la lista explícita de lo que el intervalo no cubre (§9).

### 4.5 Fecha de referencia

`t*` = fecha de la **última edición verificada común** (hoy 2026-05). Es un *nowcast* suavizado: la tendencia estimada con toda la serie, evaluada en el presente. Se prefiere al último conteo crudo porque este tiene varianza `φ m_a`, mientras que el ajustado tiene `φ m_a · (1/n + …)`: alrededor de un tercio con 10 ediciones. El precio es depender de la linealidad, que se verifica en §10.3 con una regla de respaldo definida de antemano.

---

## 5. Modelo de oferta para cultura (foto única)

Sin serie temporal no hay ruido entre ediciones que medir. El modelo es:

```
y_a ~ Poisson(μ_a)   →   μ̂_a = y_a  (insesgado),   V_a = y_a,   gl = ∞ (z)
```

- Interpretación: `μ_a` es la tasa estructural de oferta cultural de la alcaldía, y el conteo del SIC es una realización de ella. Es la convención estándar en epidemiología para tasas de conteos completos.
- Con φ = 1 este intervalo es **más ancho** que el que tendría un dominio DENUE comparable (φ̂ ≈ 0.1–0.15, así que su semiancho sería unas 2.5–3 veces menor). No hay manera de estimar φ para el SIC con una sola foto, así que se elige la opción conservadora y se dice explícitamente.
- Si `y_a = 0`, el intervalo mostrado de `μ_a` es el exacto de Garwood `[0, 3.69]`. Para el contraste `D_a` se usa `V_a = y_a` según §6.
- En el JSON se marca `tipo_intervalo: "poisson_foto_unica"` (frente a `"tendencia_cuasi_poisson"`), para que la UI pueda aclararlo. **Cultura no tiene tendencia ni proyección.**

---

## 6. Del nivel de oferta al déficit

### 6.1 Estimadores

```
θ̂_a   = 10⁵ · μ̂_a / P_a
θ̂_ref = 10⁵ · Σ_b μ̂_b / P_tot,        P_tot = Σ_b P_b
D̂_a   = θ̂_ref − θ̂_a
F̂_a   = D̂_a · P_a / 10⁵
```

`D̂_a = Σ_b c_ab · μ̂_b`, con coeficientes

```
c_aa = 10⁵ · (1/P_tot − 1/P_a)
c_ab = 10⁵ / P_tot           (b ≠ a)
```

Como las `P` son constantes y cada `μ̂_b` es insesgado, **`D̂_a` es exactamente insesgado**. Lo mismo vale para `θ̂_a`, `θ̂_ref` y `F̂_a`.

### 6.2 Varianza

Las `μ̂_b` son independientes entre alcaldías, porque cada una se estima con su propia serie. φ̂ es compartido, pero eso afecta la estimación de la varianza, no la independencia de las estimaciones puntuales, y la distribución t con ν gl lo absorbe:

```
Var(D̂_a) = Σ_b c_ab² · V_b = 10¹⁰ · [ (1/P_tot − 1/P_a)² · V_a + Σ_{b≠a} V_b / P_tot² ]
```

Igual para `Var(θ̂_a) = 10¹⁰ V_a / P_a²` y `Var(F̂_a) = (P_a/10⁵)² Var(D̂_a)`.

### 6.3 Intervalo

```
IC_95(D_a) = D̂_a ± t_{ν, 0.975} · √Var(D̂_a)       (z = 1.96 en cultura)
```

La comprobación por simulación de §10.5 verifica que estas fórmulas dan cobertura ≈ 95 % bajo el modelo. Además sirve de prueba unitaria de la implementación.

### 6.4 Si más adelante hay población proyectada

Si el equipo incorpora las proyecciones de CONAPO por alcaldía y edad, `P_a` se sustituye por `P_a(t*)`. Si esas proyecciones traen su propio intervalo, este se propaga por el método delta o por simulación. Nada más del método cambia. Mientras no existan, **`P_a` = Censo 2020 fijo** (D4).

---

## 7. Regla del semáforo

Parámetros fijados de antemano: nivel 95 %, δ = 0.10 · θ̂_ref del dominio. Sea `[L_a, U_a]` el IC95 de `D_a`.

| Nivel (`nivel`) | Color | Condición | Lectura |
|---|---|---|---|
| `alto` | rojo | `L_a > 0` **y** `D̂_a ≥ δ` | Déficit estadísticamente distinguible de cero y de al menos 10 % de la cobertura de la ciudad: demanda no cubierta alta. |
| `bajo` | verde | `U_a < 0` **y** `D̂_a ≤ −δ` | Cobertura por encima de la ciudad por al menos 10 %, con evidencia. |
| `medio` + `certeza: concluyente` | amarillo | `L_a > −δ` **y** `U_a < δ` | El intervalo completo cae dentro de ±δ: la alcaldía está en línea con la ciudad (prueba de equivalencia). |
| `medio` + `certeza: indeterminado` | amarillo con trama | cualquier otro caso | Los datos no alcanzan para clasificar. **No** es lo mismo que "promedio", y la UI debe distinguirlo con un patrón y una etiqueta, no solo con el color. |

Notas:

- Rojo y verde son concluyentes por construcción.
- Por qué δ: con φ̂ ≈ 0.1 los intervalos del DENUE son estrechos, y sin un umbral cualquier diferencia de 2 % sería "significativa" y roja. δ separa lo estadísticamente distinguible de lo relevante.
- Comparaciones múltiples: cada mapa hace 16 comparaciones. Con intervalos individuales al 95 %, si ninguna alcaldía se desviara realmente, se esperaría en promedio ≈ 0.8 clasificaciones rojo/verde espurias por mapa, y el δ lo reduce más. Se muestran intervalos **individuales** porque son los que se interpretan alcaldía por alcaldía. El reporte de validación incluye cuántos colores cambiarían con Bonferroni (nivel 1 − 0.05/16) (§11).
- La clasificación es **absoluta contra la ciudad**, no por terciles. Si ninguna alcaldía tiene déficit claro, el mapa no tendrá rojos, y así debe ser. v1 forzaba por construcción que alrededor de un tercio de las alcaldías cayera en cada extremo de oferta.

---

## 8. Proyecciones (secundarias, fuera del semáforo)

Solo para infancia y adultos mayores, y solo en el panel de detalle:

- Horizontes `h ∈ {1, 2, 3}` años, **acotados por `h ≤ min(3, ventana/2)`**. Con ventanas de 9.6 años (infancia) y 9.6 años (adultos mayores, 2016-10 → 2026-05) se permite hasta 3 años. La regla queda escrita para cuando cambien las ventanas.
- Estimación: `μ̂_a(t* + h)` con el mismo modelo y la varianza de §4.4. Es el intervalo de confianza del nivel esperado. Si la UI muestra "cuántos establecimientos habrá", debe usar el de predicción (con el `1 +`).
- Toda proyección se etiqueta "si la población objetivo se mantiene como en 2020" (D4). **No se proyecta el semáforo.**

---

## 9. Qué cubre y qué no cubre el intervalo

**Cubre:** la incertidumbre estadística sobre el nivel de oferta registrado, que viene de la fluctuación entre ediciones del DENUE (o de la variación de Poisson en cultura) y de la estimación de la tendencia, bajo el modelo de §4 o §5.

**No cubre.** Son sesgos del estimando, que el intervalo no protege y que la UI debe declarar en una nota fija por dominio:

1. **Capacidad**: un establecimiento no es una plaza. Una guardería IMSS de 200 lugares y una estancia de 15 cuentan igual.
2. **Uso entre alcaldías**: Cuauhtémoc, Benito Juárez y Miguel Hidalgo concentran servicios que usa población de otras alcaldías. Su cobertura "por residente" sobreestima la disponible para sus residentes, y la de sus vecinas la subestima.
3. **Subregistro y oferta informal del DENUE**: el cuidado de adultos mayores y de infancias ocurre en buena medida en el hogar. `enut/` podría informar esto más adelante, cuando tenga diccionario (pregunta 8 de current-state).
4. **Cambio poblacional 2020 → 2026**: la población es la de 2020 (D4). Las alcaldías que envejecen más rápido tienen su déficit de adultos mayores **subestimado**.
5. **Clasificación SCIAN**: establecimientos mal codificados entran o salen del conteo. El análisis de sensibilidad (§11) varía los conjuntos SCIAN límite.
6. **Reparto del grupo 15–19** entre 0–17 y 18–29 (supuesto uniforme del README del censo): efecto menor sobre el denominador de infancia.

---

## 10. Validación y diagnósticos (definidos de antemano, con regla de acción)

Todos se calculan por dominio, agrupando las 16 alcaldías, y se publican en `validacion/{dominio}.json` junto con el semáforo.

### 10.1 Calibración con origen móvil

Para cada origen `k = 4, …, n−1`: se ajusta con las ediciones `1..k` (φ̂ recalculado solo con esas), se predice la edición `k+1` con intervalo de **predicción** al 95 % y se registra si el valor observado cae dentro, junto con el error estandarizado `z = (y − ŷ)/se_pred`.

- Tamaño: infancia 16 × 7 = 112 predicciones; adultos mayores 16 × 5 = 80.
- **Criterio**: cobertura empírica ≥ 90 %, aproximadamente el límite inferior del intervalo binomial al 95 % para n ≈ 80–110 y p = 0.95.
- **Si falla**: κ = media de `z²` y se usa `κ · φ̂` en todo el dominio. κ se reporta.
- Se compara también el error absoluto medio contra el pronóstico ingenuo "último valor observado". Si la tendencia no le gana al pronóstico ingenuo, se reporta. No cambia el método, pero es una señal para revisar §4.5.

### 10.2 Sesgo

Media de los errores firmados `y − ŷ` de 10.1, con su prueba t.

- **Si |t| es significativo al 1 %**, la tendencia lineal está sesgada en la práctica: se activa el respaldo de §10.3.

### 10.3 Linealidad y cambio de generación Gen A → Gen B

- Prueba F agrupada de un término cuadrático por alcaldía (16 parámetros adicionales).
- Solo en adultos mayores: prueba F agrupada de un escalón por alcaldía a partir de 2022-11 (cambio de pipeline Gen A → Gen B).
- **Regla**: si el escalón es significativo al 1 %, el modelo incluye el escalón y el estimando pasa a ser el nivel post-2022. Si la curvatura es significativa al 1 %, o falla 10.2, el ajuste se restringe a la **ventana de las 5 ediciones verificadas más recientes**, con el mismo método. En ambos casos se registra en `metodo_id`.

### 10.4 Autocorrelación

Correlación de rezago 1 de los residuos, agrupada. Los residuos de OLS con pocos puntos tienen correlación **negativa por construcción**: en v1 da −0.43 y −0.38 con n = 5, sin evidencia de persistencia. Por eso el valor de referencia se obtiene por simulación bajo independencia, no con 0.

- **Si ρ̂ es significativamente mayor que la referencia**: `V_a` se multiplica por `(1+ρ̂)/(1−ρ̂)`.

### 10.5 Simulación de control (prueba de la implementación)

Se simulan 2,000 conjuntos de series desde el modelo ajustado (errores normales con varianza `φ̂ ȳ_a`, y además una variante Poisson escalada) y se reestima todo. Se verifica que:

1. el sesgo medio de `D̂_a` sea compatible con 0;
2. la cobertura del IC95 de `D_a` quede en [93.5 %, 96.5 %] para cada alcaldía.

Es la prueba automática de que las fórmulas de §4 y §6 están bien implementadas.

---

## 11. Análisis de sensibilidad (se reporta; no cambia el semáforo principal)

Para cada variante se publica cuántas alcaldías cambian de color frente al resultado principal:

| Variante | Qué cambia |
|---|---|
| δ | 5 % y 20 % en lugar de 10 % |
| Multiplicidad | IC de Bonferroni al 1 − 0.05/16 |
| Adultos mayores | + centros de cuidado diurno 624121–624122; denominador 65+ en lugar de 60+; + edición 2021-11 no verificada |
| Infancia | + códigos de las banderas opcionales (apoyo social/residencias, media superior, etc.) |
| Cultura | sin los registros `es_pilares = SI` |
| Fecha de referencia | último conteo crudo `y_a(t_last)` en lugar del nowcast suavizado |

Si en un dominio más de 3 alcaldías cambian de color entre la versión principal y alguna variante de inclusión, la UI muestra una nota de robustez para ese dominio.

---

## 12. Contrato de salida para el frontend

`src/app/data/semaforo/{dominio}.json`. Completa el contrato que dejó abierto `docs/architecture-plan.md` §5. `estimacion`, `ic_inf`, `ic_sup`, `nivel_ic`, `nivel` y `metodo_id` se mantienen con esos nombres; `estimacion` = `D̂_a`.

```json
{
  "dominio": "adultos_mayores",
  "metodo_id": "tendencia_cq_agrupada@1",
  "tipo_intervalo": "tendencia_cuasi_poisson",
  "fecha_referencia": "2026-05",
  "grupo_poblacional": "60+",
  "nivel_ic": 0.95,
  "unidad": "establecimientos por 100 mil personas del grupo",
  "referencia_cdmx": { "cobertura_100k": 0.0, "delta": 0.0 },
  "parametros": { "phi": 0.0, "kappa": 1.0, "gl": 112, "t_crit": 0.0, "ediciones": ["2016-10", "..."] },
  "alcaldias": {
    "002": {
      "poblacion_objetivo": 0,
      "oferta":      { "estimacion": 0.0, "ic_inf": 0.0, "ic_sup": 0.0, "ic_inf_recortado": false },
      "cobertura":   { "estimacion": 0.0, "ic_inf": 0.0, "ic_sup": 0.0 },
      "estimacion": 0.0, "ic_inf": 0.0, "ic_sup": 0.0,
      "faltantes":   { "estimacion": 0.0, "ic_inf": 0.0, "ic_sup": 0.0 },
      "nivel": "alto | medio | bajo",
      "certeza": "concluyente | indeterminado",
      "banderas": ["sin_oferta_observada", "ic_inf_recortado"]
    }
  }
}
```

- Las estimaciones puntuales **nunca** se truncan. Solo `oferta.ic_inf` se recorta a 0 para mostrarse, con `ic_inf_recortado: true`.
- La serie histórica, el desglose por subcategoría y las proyecciones de §8 viven en `oferta/{dominio}.json` (plan de arquitectura), no aquí.
- **Nada de columnas ni llaves de AGEB.**

---

## 13. Resumen de parámetros fijados

| Parámetro | Valor | Dónde |
|---|---|---|
| Estimando | `D_a = θ_ref − θ_a` | §1 |
| Fecha de referencia | última edición verificada común (2026-05) | §4.5 |
| Modelo de media | lineal en el tiempo real, por alcaldía | §4.1 |
| Modelo de varianza | `φ · m_a`, con φ agrupado por dominio; φ = 1 en cultura | §4.3, §5 |
| Nivel del IC | 95 % individual, t con ν gl | §6.3 |
| Materialidad δ | 10 % de θ̂_ref | §7 |
| Horizonte máximo de proyección | `min(3, ventana/2)` años | §8 |
| Criterio de calibración | cobertura con origen móvil ≥ 90 %; si no, se infla φ por κ | §10.1 |
| Umbral de las pruebas de diagnóstico | 1 % | §10.2–10.4 |

## 14. Qué falta antes de implementar

1. Aprobación de D1–D6 por el equipo.
2. El ETL de `docs/architecture-plan.md` entregando `oferta_alcaldia.csv` y `poblacion_alcaldia.csv`, con las reglas de §2. En especial, la comprobación de que el conjunto SCIAN de adultos mayores es idéntico en Gen A y Gen B, y la lista final de códigos núcleo de infancia congelada en `data/reference/dominios_scian.csv`.
3. (Opcional, mejora D4) Proyecciones de población de CONAPO por alcaldía y edad.

La implementación va en `src/modeling/` y se limita a codificar este documento. Cualquier cambio de estimando, modelo o regla se hace primero aquí.
