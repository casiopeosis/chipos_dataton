Sí revisé el documento del reto y las carpetas `docs`, `data` y `backend` de la rama `jaladas2`. No hice cambios.

Mi conclusión directa: **el proyecto tiene una base técnica bastante buena, pero todavía no está listo para entregarse**. El algoritmo de demanda es serio y está mejor pensado que un promedio simple, pero hay inconsistencias importantes con la convocatoria y todavía no responde por completo la pregunta que ustedes quieren mostrar.

## 1. ¿La idea cumple con el reto?

Sí, pero deben ajustar cómo presentan el problema.

El reto pregunta esencialmente:

> ¿En qué zonas cambiará la demanda de un servicio durante los próximos años, por qué cambiará y qué tan segura es la predicción?

Su proyecto responde esto para servicios dirigidos a infancias mediante:

* Población infantil futura como demanda potencial.
* Establecimientos destinados a infancias como oferta.
* Resultados geográficos por AGEB y alcaldía.
* Una clasificación: `sube`, `se_mantiene`, `baja` o `sin_datos`.
* Intervalos de incertidumbre.

Eso sí cumple con la temática.

El problema está en decir:

> “La aplicación muestra en qué alcaldías conviene vivir”.

Los datos actuales **no permiten afirmar eso**. Para decir dónde conviene vivir también necesitarían vivienda, seguridad, movilidad, precios, calidad escolar, distancia a servicios, capacidad de atención, áreas verdes, etc.

Con lo que tienen actualmente, la promesa correcta sería:

> **La aplicación identifica las zonas de la CDMX donde podría existir mayor presión, déficit u oportunidad de expansión de servicios para infancias durante los próximos años.**

Eso está mucho más alineado con el reto y es defendible ante los jueces.

## 2. Corrección urgente de los horizontes

El documento del reto exige explícitamente proyecciones de:

* 1 año.
* 3 años.
* 5 años.

Ustedes pensaban usar 1, 3 y 8 años, pero el repositorio actualmente usa:

* 3 años: 2029.
* 5 años: 2031.
* 7 años: 2033.

Por lo tanto, **ninguna de las dos configuraciones cumple exactamente con el requisito**.

Hay que cambiar el backend y el frontend a:

```text
h1 = 2027
h3 = 2029
h5 = 2031
```

También convendría utilizar 2031 como punto de control final de CONAPO, no 2033.

## 3. ¿Qué hace actualmente el algoritmo de demanda?

El algoritmo se encuentra principalmente en [`modelos.py`](https://github.com/casiopeosis/chipos_dataton/blob/jaladas2/backend/src/chipos/modelos.py) y está explicado en [`metodologia.md`](https://github.com/casiopeosis/chipos_dataton/blob/jaladas2/docs/metodologia.md).

### Paso 1: mide cuántas infancias había

Para cada AGEB suma la población de:

* 0 a 2 años.
* 3 a 5 años.
* 6 a 11 años.
* 12 a 14 años.

Eso produce la población infantil total de 0 a 14 años en 2010 y 2020.

### Paso 2: calcula la tendencia histórica

Compara la población de 2010 contra la de 2020 y obtiene una tasa anual.

Por ejemplo, si un AGEB pasó de 1,000 a 800 niñas y niños, el algoritmo detecta una tendencia decreciente.

Usa una tasa logarítmica:

$$
r_i=
\frac{\ln\left(\frac{D_{2020}+0.5}{D_{2010}+0.5}\right)}
{2020.20-2010.44}
$$

El `+0.5` evita problemas cuando hay conteos muy pequeños o iguales a cero.

### Paso 3: corrige resultados extremos

Algunas AGEB tienen muy poca población. En ellas, una diferencia pequeña puede producir un porcentaje exagerado.

Para evitarlo utiliza una técnica llamada **contracción Empirical Bayes**. En palabras sencillas:

> Si un AGEB tiene pocos datos, el algoritmo no confía completamente en su cambio particular y lo acerca un poco a la tendencia general de su alcaldía.

Si el AGEB tiene mucha población y datos más estables, conserva más de su propia tendencia.

Esta es una decisión metodológica razonable.

### Paso 4: incorpora las proyecciones de CONAPO

Después combina:

* La tendencia histórica del AGEB.
* La tendencia de su alcaldía.
* La proyección futura municipal de CONAPO.

CONAPO guía la cantidad total de población infantil que debería tener cada alcaldía. Los AGEB distribuyen internamente ese cambio.

En términos sencillos:

> CONAPO dice cuánto crecerá o disminuirá aproximadamente la alcaldía, mientras que el comportamiento histórico determina cómo se reparte ese cambio entre sus AGEB.

### Paso 5: reconoce que no sabe cuánto persistirá la tendencia local

El parámetro \(\lambda\) controla cuánto se conserva el comportamiento particular del AGEB:

* \(\lambda=0.25\): predomina la tendencia de la alcaldía.
* \(\lambda=1\): se conserva por completo la diferencia histórica del AGEB.

Como no existe información suficiente para conocer el valor exacto, el programa prueba valores entre `0.25` y `1`.

Esta incertidumbre está bien reconocida y es uno de los puntos fuertes del modelo.

### Paso 6: realiza 4,000 simulaciones

El algoritmo no genera una sola respuesta. Simula 4,000 futuros posibles considerando:

* Ruido estadístico.
* Incertidumbre de la tendencia local.
* Diferencias entre INEGI y CONAPO.
* Variaciones compartidas dentro de una alcaldía.

De esas simulaciones obtiene:

* Predicción central.
* Intervalo del 95 %.
* Probabilidad de aumento.
* Probabilidad de disminución.
* Nivel de confianza.

### Paso 7: genera el veredicto

La regla actual es:

* `sube`: al menos 80 % de probabilidad de crecer más de 1 % anual.
* `baja`: al menos 80 % de probabilidad de caer más de 1 % anual.
* `se_mantiene`: el cambio probablemente está dentro de ±1 % anual.
* `sin_datos`: no existe información suficiente.

La regla es clara, reproducible y fácil de explicar.

## 4. ¿Qué hace el algoritmo de oferta?

La oferta se construye con establecimientos DENUE dedicados a infancias.

Aunque existen 11 archivos DENUE, el equipo detectó correctamente que no representan 11 mediciones independientes. Muchos cortes son prácticamente copias y existen actualizaciones grandes en 2019 y 2024.

Por eso utiliza únicamente tres momentos efectivos:

* Octubre de 2016.
* Noviembre de 2019.
* Noviembre de 2024.

Para cada AGEB ajusta una tendencia Poisson y después aplica una contracción hacia la tendencia de la alcaldía.

En palabras sencillas:

> Cuenta cuántos establecimientos había en esos tres momentos, estima si la oferta está aumentando o disminuyendo y evita confiar demasiado en AGEB con muy pocos establecimientos.

Es una elección razonable para los datos disponibles.

Sin embargo, el algoritmo supone que la fuerte caída registrada en 2024 corresponde a cierres reales acumulados. Eso es posible, pero **no está completamente demostrado**. Debería presentarse como una hipótesis y no como una certeza.

## 5. Lo mejor del trabajo actual

El repositorio tiene varias decisiones técnicas muy buenas:

* Diferencia correctamente demanda y oferta.
* Utiliza datos oficiales de INEGI, CONAPO y DENUE.
* Trabaja por AGEB y agrega correctamente por alcaldía.
* Documenta problemas de claves, geometrías y cambios territoriales.
* No inventa resultados cuando faltan datos.
* Reconoce que las AGEB pequeñas son más inestables.
* Incluye incertidumbre y niveles de confianza.
* Utiliza semillas fijas para obtener resultados reproducibles.
* Tiene bastantes pruebas automatizadas.
* No trata los 11 DENUE como 11 años independientes.

No necesitan reemplazar todo con una red neuronal o un algoritmo “más avanzado”. Con pocos momentos históricos, un modelo complejo probablemente produciría resultados menos explicables y más fáciles de sobreajustar.

## 6. Problemas importantes que encontré

### A. La validación retrospectiva no está implementada

Este es el problema técnico más grave.

La documentación afirma que existen:

* Backtest de CONAPO.
* Adelgazamiento binomial.
* Validación dejando una alcaldía fuera.
* Comparación contra un modelo ingenuo.
* Resultados de MAE y F1.

Pero en la rama:

* No existe `backend/src/chipos/backtest.py`.
* No existe `docs/backtest.md`.
* `diagnostico.json` solamente contiene la brecha.
* No aparecen métricas reales del modelo contra el baseline.

Es decir: **la metodología dice que la validación existe, pero los archivos de resultados no la demuestran**.

Esto incumple uno de los requisitos explícitos del reto y puede ser detectado fácilmente en la verificación en vivo.

### B. Solo hay dos momentos históricos de demanda a nivel AGEB

Para cada AGEB únicamente se utilizan 2010 y 2020. Con dos puntos se puede obtener una línea, pero no saber si:

* La caída se está acelerando.
* La tendencia se frenó.
* Existió un cambio después de 2020.
* El comportamiento fue irregular.

CONAPO sí aporta una serie larga a nivel alcaldía, pero la tendencia local del AGEB continúa dependiendo de dos observaciones.

El modelo reconoce esta limitación, lo cual está bien, pero el reto solicita al menos tres momentos históricos comparables. Deben explicar que:

* A nivel alcaldía se usan múltiples años de CONAPO.
* Para la oferta se usan tres periodos DENUE.
* A nivel AGEB censal solo existen dos momentos comparables.

Aun así, sería mejor incorporar un tercer punto comparable si es viable.

### C. “Demanda” realmente significa población infantil

El algoritmo supone:

$$
\text{demanda potencial}=\text{población de 0 a 14 años}
$$

Pero 1,000 niñas y niños no necesariamente generan la misma demanda en todas las zonas. También influyen:

* Edad específica.
* Escolaridad.
* Ingreso.
* Participación laboral de madres, padres o tutores.
* Tipo de servicio.
* Acceso a servicios públicos o privados.
* Distancias y movilidad.

Conviene llamarla **demanda potencial** y no demanda observada.

### D. Se mezclan servicios muy diferentes

Actualmente se suman todas las personas de 0 a 14 años y también distintos establecimientos.

Pero una guardería atiende principalmente a edades pequeñas, mientras que una primaria atiende otro grupo. Un mismo denominador para todos los servicios puede ocultar problemas.

Sería mucho mejor separar por lo menos:

| Servicio                      | Población relacionada |
| ----------------------------- | --------------------: |
| Guarderías y primera infancia |             0–2 o 0–5 |
| Preescolar                    |                   3–5 |
| Primaria                      |                  6–11 |
| Servicios para adolescentes   |                 12–14 |

Esto produciría recomendaciones mucho más útiles.

### E. Todos los establecimientos cuentan igual

Un establecimiento pequeño vale lo mismo que uno grande. Además:

* No se conoce su capacidad.
* No se mide calidad.
* No se mide matrícula.
* No se distingue claramente disponibilidad pública y privada.
* No se calcula distancia o tiempo de traslado.

Por eso la razón “establecimientos por cada 1,000 infancias” es útil como aproximación, pero no representa cobertura real.

### F. No existe todavía un ranking de oportunidad

La brecha actual es:

$$
\frac{\text{establecimientos 2024}}
{\text{población infantil 2020}}\times1000
$$

Esta brecha:

* Mezcla años diferentes.
* Es histórica, no futura.
* No integra simultáneamente la proyección de demanda y oferta.
* No genera directamente “oportunidades de expansión”.

El sistema proyecta ambas capas por separado, pero todavía falta combinarlas.

### G. Los resultados diferencian poco a las alcaldías

En el archivo de salida actual:

* La demanda baja en 15 de las 16 alcaldías.
* La oferta baja en 14 de las 16.
* 14 alcaldías reciben confianza alta en la demanda.

Eso puede ser demográficamente correcto, pero una aplicación que colorea casi todo como “baja” ayuda poco a tomar decisiones.

La pregunta útil no debería ser solamente:

> ¿Dónde disminuye la población infantil?

Sino:

> ¿Dónde disminuirá más lentamente la demanda que la oferta y, por lo tanto, podría crecer la presión sobre los servicios existentes?

### H. Hay intervalos de confianza sospechosamente estrechos

En algunas alcaldías, el intervalo reportado es prácticamente cero. Por ejemplo, en el horizonte de tres años hay intervalos con anchura `0.0` o `0.1`.

También la oferta total de la CDMX muestra un intervalo idéntico en ambos extremos.

Eso sugiere que el modelo está representando principalmente el error estadístico de los conteos, pero no toda la incertidumbre estructural del DENUE, como:

* Cambios de levantamiento.
* Depuración de registros.
* Reclasificación.
* Choques posteriores a 2024.
* Diferencias en la capacidad de los establecimientos.

Los resultados parecen más seguros de lo que realmente son.

### I. La documentación está desactualizada

[`estado_datos.md`](https://github.com/casiopeosis/chipos_dataton/blob/jaladas2/docs/estado_datos.md) todavía dice que falta implementar el backend, aunque ya existe.

Además, `CLAUDE.md` declara archivos de backtest que no están en la rama. Esto puede confundir al equipo y a los jueces.

## 7. ¿Es óptimo el algoritmo?

No existe un algoritmo “óptimo” sin definir primero qué quieren optimizar.

Para predecir población infantil con datos limitados, la combinación de:

* Tendencia logarítmica.
* Contracción hacia la alcaldía.
* Control con CONAPO.
* Simulación Monte Carlo.

es una buena elección. Es interpretable y está mejor justificada que aplicar aprendizaje automático solo para decir que utilizaron IA.

Pero para identificar oportunidades de servicios, el algoritmo está incompleto porque todavía no combina adecuadamente demanda futura y oferta futura.

## 8. Mejora que les recomiendo

Crearía dos índices distintos.

### Índice de oportunidad de expansión

Pensado para organizaciones o proveedores:

$$
O_{i,h}
=
\text{demanda futura relativa}
-
\text{oferta futura relativa}
$$

Una versión fácil de explicar sería:

1. Proyectar la población objetivo del servicio.
2. Proyectar los establecimientos.
3. Calcular:

$$
\text{cobertura futura}_{i,h}
=
\frac{\widehat S_{i,h}}
{\widehat D_{i,h}}\times1000
$$

4. Compararla con la cobertura actual y con la mediana de la CDMX.
5. Dar mayor prioridad a zonas donde:

* La demanda es grande o disminuye lentamente.
* La oferta es baja o cae más rápido.
* El intervalo de incertidumbre permite sostener esa conclusión.

### Índice para familias

Si quieren conservar la idea de “dónde conviene vivir”, debe ser una vista separada y llamarse algo como:

> Disponibilidad proyectada de servicios para infancias.

Este índice debería premiar:

* Mayor cobertura proyectada.
* Oferta pública.
* Diversidad de servicios.
* Cercanía.
* Estabilidad de la oferta.
* Confianza de la predicción.

No debe mezclarse con el índice de oportunidad comercial porque una zona buena para abrir servicios puede ser precisamente una zona con baja cobertura actual.

## 9. Prioridades antes de entregar

Yo avanzaría en este orden:

1. Cambiar los horizontes a **1, 3 y 5 años**.
2. Implementar y guardar el backtest real.
3. Comparar el modelo contra “el último valor permanece igual”.
4. Crear la brecha futura entre oferta y demanda.
5. Generar un ranking de oportunidad.
6. Separar por grupos de edad o tipos de servicio.
7. Añadir sobredispersión o un piso mínimo de incertidumbre.
8. Presentar la caída DENUE 2024 mediante dos escenarios.
9. Actualizar la documentación para que coincida con el código.
10. Cambiar el mensaje de “dónde conviene vivir” por uno que realmente puedan demostrar.

En resumen: **no cambiaría completamente el modelo de demanda**. Primero corregiría horizontes, validación, incertidumbre y la combinación oferta-demanda. Esos cambios mejorarían mucho más la propuesta que sustituirla por un algoritmo sofisticado pero difícil de justificar.