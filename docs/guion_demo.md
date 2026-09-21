# Guión de demo (F-8, `correccion/avance_plan.md` punto 60)

Caso de uso de jueces (`correccion/frontend_requisitos.md` §24): primaria pública + hospitales y
clínicas + comercio de primera necesidad + áreas verdes recreativas, horizonte de 3 años,
educación y salud en alta prioridad. 3-4 minutos, sin recargar la página, sin errores de consola.
Servir con `make serve` y abrir `http://localhost:8000/` (datos reales de `frontend/data/`, no
`?mock=1`).

Cada paso trae: qué clic hacer, qué debería verse, y qué decir. Los textos entre comillas son
literales de la UI (`frontend/js/textos.js`), para que quien practique el guión pueda ubicarse
sin adivinar.

## 0. Antes de arrancar (10 s)

Tener la pestaña ya abierta y cargada (el primer `fetch` de `data/prediccion_ageb.json` puede
tardar unos segundos; no hacerlo en vivo frente al jurado). Consola del navegador abierta pero
minimizada, por si hay que enseñar "cero errores" si preguntan.

## 1. Qué hace Habitancia (20 s)

**Decir**, sin tocar nada todavía: "Habitancia identifica zonas de la Ciudad de México donde,
según cómo cambia la población infantil y adolescente y la oferta de servicios, podría haber
mayor oportunidad de ampliar infraestructura -- o, viéndolo al revés, mayor disponibilidad para
las familias que ya viven ahí." Señalar el mapa de alcaldías ya visible, coloreado por la vista
general.

## 2. Población objetivo: primaria (6-11 años) (15 s)

**Clic:** en el selector "¿Qué población objetivo quieres explorar?", botón **"Primaria · 6 a 11
años"**.

**Decir:** "Empezamos por la población que nos interesa: niñas y niños de 6 a 11 años, edad de
primaria."

## 3. Horizonte: 3 años (10 s)

**Clic:** mover el control **"HORIZONTE"** a la parada **"3 año(s) · 2029"**.

**Decir:** "Proyectamos a 3 años, uno de los tres horizontes que ofrece Habitancia (1, 3 y 5)."

## 4. Búsqueda: oportunidad de expansión (10 s)

**Clic:** radio **"Oportunidad de expansión"** (ya viene seleccionado por omisión; si no,
seleccionarlo).

**Decir:** "Buscamos zonas donde la oferta actual y proyectada cubre relativamente poco frente a
la población objetivo -- posibles prioridades de expansión. La otra vista, 'Disponibilidad para
familias', mide lo contrario: dónde ya hay más oferta para quien vive ahí hoy."

## 5. Prioridades: educación y salud altas (20 s)

**Clic:** en "¿Qué tan prioritaria es cada rama para ti?", subir los círculos de:
- **Educación y cultura** a 5 (el máximo).
- **Salud** a 5.
- Dejar **Comercio** y **Áreas verdes y espacio público** en su valor medio (3, el que trae por
  omisión) -- esto ya representa la prioridad "media" del caso de los jueces sin tocarlos.

**Decir:** "Le decimos a Habitancia que educación y salud nos importan más que comercio y áreas
verdes para esta búsqueda. Esto solo reordena el ranking y el índice compuesto del mapa -- nunca
cambia los datos originales."

## 6. Filtros por rama (40 s)

**Clic:** pestaña **"Educación y cultura"** (o abrir el panel de filtros si ya está en vista
general), sección "¿Qué servicios de educación y cultura quieres considerar?": marcar solo
**"Primaria"**, sector **"Público"**.

**Clic:** pestaña **"Salud"**, "¿Qué instalaciones de salud quieres considerar?": marcar
**"Hospitales"** y **"Clínicas o consultorios"**.

**Clic:** pestaña **"Comercio"**, botón/preset **"Comercios de primera necesidad"**.

**Clic:** pestaña **"Áreas verdes y espacio público"**, "¿Qué tipo de espacio quieres
considerar?": marcar **"Áreas recreativas"**.

**Decir:** "Los filtros deciden qué establecimientos cuentan como oferta de cada rama -- primaria
pública, hospitales y clínicas, comercio de primera necesidad, áreas verdes recreativas. Tampoco
tocan los datos originales, solo qué se suma." Volver a la pestaña **"Vista general"**.

## 7. Mapa y ranking (25 s)

**Decir**, señalando el mapa ya recoloreado: "El mapa por alcaldía usa una paleta con significado
fijo -- alta, media, baja oportunidad y 'sin datos' en gris con patrón, nunca solo color." Bajar a
la tabla de ranking. "El ranking ordena zonas por AGEB, no por alcaldía: la alcaldía es solo
navegación."

## 8. Abrir una zona (30 s)

**Clic:** en una alcaldía del mapa (p. ej. Cuauhtémoc) para entrar a su vista de AGEB, y luego en
un AGEB del ranking o del mapa.

**Decir**, leyendo la ficha (Nivel 1): "oportunidad relativa, confianza, y qué ramas explican el
resultado -- aquí Habitancia ya nos dice si el resultado depende más de educación o de salud, sin
necesidad de abrir nada más."

## 9. Entender esta zona: gráficas y confiabilidad (35 s)

**Clic:** botón **"Entender esta zona →"**.

**Decir**, mostrando las gráficas de población y de servicios por rama: "Aquí vemos el histórico y
la proyección -- nunca solo un número, siempre con su intervalo." Bajar a la sección **"¿Qué tan
confiable es la estimación?"**: "La demanda se validó contra el pasado y le ganó a 'suponer que
nada cambia'. La oferta, en cambio, **no** le ganó en esta validación -- predice bien la
dirección del cambio pero se equivoca más en la magnitud, sobre todo por el levantamiento del
DENUE de 2024. Por eso toda proyección de oferta muestra como máximo confianza 'media', nunca
'alta'. No lo escondemos: está en la ficha de cada zona y en `docs/backtest.md`."

## 10. Ausencia de datos ≠ ausencia de necesidad (20 s)

**Clic:** buscar y mostrar una AGEB rural o "sin datos" (p. ej. desde el buscador, escribir una
clave de Milpa Alta, o usar el filtro de nivel de riesgo para exhibir zonas grises en el mapa).

**Decir:** "Estas zonas grises no son 'sin necesidad' -- son zonas donde el censo no publica
población infantil por AGEB rural, o donde no hay suficientes observaciones. Habitancia nunca
inventa un veredicto donde falta información: lo marca como 'sin datos' explícitamente, con su
propio color y etiqueta en la leyenda."

## 11. Comparar dos alcaldías (25 s)

**Clic:** en "Comparar alcaldías", elegir dos alcaldías distintas (p. ej. Cuauhtémoc e
Iztapalapa) en los selectores "Primera alcaldía" / "Segunda alcaldía".

**Decir:** "La comparación conserva la población objetivo, el horizonte, los pesos y los filtros
que ya elegimos -- y deliberadamente **no declara una ganadora**: dos alcaldías con contextos muy
distintos no deberían resumirse en un solo número que diga cuál es 'mejor'." Cerrar con **"Dejar
de comparar"**.

## 12. Cierre (15 s)

**Decir:** "Todo esto sin recargar la página una sola vez, y sin un solo error en consola --
pueden verificarlo ustedes mismos. Las limitaciones del modelo, como la de la oferta, están
documentadas y visibles, no escondidas detrás de una cifra optimista."

---

## Notas para quien practique

- El guión completo toma entre 3 y 4 minutos si se dice el texto en voz natural sin pausas
  largas; cronometrarlo al menos una vez antes de la demo real.
- Practicar el flujo de principio a fin **sin recargar la página** y con la consola abierta, para
  confirmar que ningún paso produce un error (Definición de terminado de `CLAUDE.md`).
- Si el jurado pregunta por el rendimiento del mapa: mencionar la medición reproducible en
  `frontend/tests/medir_mapa.html` (16 alcaldías, tareas largas por clic).
- Si preguntan por qué la oferta no tiene la misma confianza que la demanda: remitir a
  `docs/backtest.md`, sección "Decisión sobre la capa de oferta".
