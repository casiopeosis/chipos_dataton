# CLAUDE.md — chipos_dataton

## 1. Qué es este proyecto

Analizamos en qué **alcaldías** de la Ciudad de México se va a experimentar demanda de ciertos servicios. El resultado final es un **semáforo** en una página web: el usuario elige un grupo demográfico, y el mapa colorea las 16 alcaldías según el nivel de demanda estimado para ese grupo.

Las estimaciones deben ser **insesgadas** y venir acompañadas de **intervalos de confianza**, construidos a partir de datos demográficos y de oferta/demanda de servicios ya recopilados en `data/`.

**Decisión de equipo: no se implementa nivel AGEB.** El proyecto original contemplaba drill-down a AGEB; el equipo decidió no hacerlo (no hay población por AGEB disponible en ningún dataset del repo, ver §1.1). Esto ya no es una fase condicional futura — es alcance cerrado. No construir infraestructura, columnas, ni estados de UI pensando en un AGEB que no se va a implementar.

## 1.1 Hallazgos críticos del inventario (`docs/current-state.md`) — leer antes de tocar código

- ⚠️ **BUG DE METADATOS EN GEN A — regla dura, no opcional.** Las carpetas `OCTUBRE 2016 CDMX`, `NOVIEMBRE 2017/2018/2020 CDMX` tienen `fuente.anio_datos`, `fuente.mes_corte`, `fuente.edicion` y `fuente.nota_temporal` **idénticos e incorrectos** en su JSON de calidad (los 4 dicen `2020-11`, es una plantilla no actualizada). **Nunca uses esos campos para fechar estas carpetas.** El dato correcto está en `fuente.archivo` (nombre del zip, ej. `denue_09_1016.zip`) y `fuente.sha256_archivo_entrada`. Cualquier subagente de ETL debe leer esta regla antes de tocar la familia Gen A (ver §6 de la reorganización propuesta).
- ⚠️ **BLOQUEADOR: no existe población por AGEB en ningún dataset de `data/`.** `ESTUDIO EDADES CENSO 2020` solo llega a nivel alcaldía (576 registros) y alcaldía+localidad (3,276). El denominador poblacional para el drill-down a AGEB no existe todavía — hay que conseguir la tabla censal de INEGI a nivel AGEB ("Principales resultados por AGEB", Censo 2020) o definir explícitamente un método de reparto proporcional desde alcaldía como fallback documentado. Esto bloquea la Fase 4 (metodología) a nivel AGEB, no solo el frontend.
- `data/semaforo_v0.json` y `semaforo_v1.json` eran pruebas de un frontend Streamlit descartado. El JSON y el código que los consumía se eliminan, **pero `v1` ya trae un aparato estadístico (error estándar de residuales, t-crítico, grados de libertad, LOO-CV) directamente relevante para el diseño de intervalos de confianza** — se archivan en `docs/legacy/` como referencia de metodología, no se borran sin revisar.
- Los cuatro cortes `COMERCIOS_*` / `MAYO|NOVIEMBRE|OCTUBRE * CDMX` / `INFANCIAS_*` / `SALUD_CDMX_*` para un mismo periodo **no son duplicados** — son cuatro filtros temáticos sobre la misma descarga DENUE (confirmado por hash del zip de origen). No hay que deduplicar esa parte.

## 2. Dominios de demanda (los tres focos del proyecto)

| Dominio | Carpetas de datos relevantes |
|---|---|
| Adultos mayores | `NOVIEMBRE * CDMX/denue_servicios_adultos_mayores_*`, `denue_enfoque_gimnasios_adultos_mayores_*`, `PILARES CDMX/` |
| Infancia (guarderías, etc.) | `INFANCIAS_*` (una carpeta por corte de tiempo, 2016–2026) |
| Cultura | `AREAS_CULTURALES_CDMX/` |

Datos transversales que probablemente alimentan el modelo (población base, contexto, no un dominio en sí):
- `ESTUDIO EDADES CENSO 2020/` — estructura de edades por zona, insumo clave para el denominador poblacional del estimador
- `enut/` — uso del tiempo, puede informar demanda de cuidado
- `ESPACIO PUBLICO CDMX/`, `AREAS VERDES CDMX/` — contexto de oferta urbana
- `COMERCIOS_*` / `MAYO * CDMX` / `NOVIEMBRE * CDMX` / `OCTUBRE 2016 CDMX` — snapshots DENUE genéricos; son la fuente de la que salen `INFANCIAS_*`, `SALUD_CDMX_*` y los de adultos mayores. **Ojo**: hay carpetas que parecen representar el mismo tipo de corte con nombres distintos (`COMERCIOS_2025_05` vs `MAYO 2025 CDMX`, `NOVIEMBRE 2022 CDMX`, `OCTUBRE 2016 CDMX`). Antes de modelar, hay que confirmar si son duplicados, cortes distintos, o el mismo insumo procesado dos veces.
- `semaforo_v0.json`, `semaforo_v1.json` — probablemente iteraciones previas del output final; revisar antes de asumir que hay que construirlo desde cero.

## 3. Jerarquía territorial — definitivo: solo alcaldía

```
Alcaldía   (único nivel — AGEB descartado por decisión de equipo)
```

- CDMX tiene 16 alcaldías. Es el único nivel territorial del proyecto.
- No hay shapefile de límites de AGEB ni población por AGEB en `data/`. Esto fue el motivo original de la duda, pero ya no es un bloqueador a resolver — es la razón por la que el equipo cerró el alcance en alcaldía.
- No diseñar, documentar ni dejar "ganchos" de código para un futuro AGEB. Si el equipo cambia de opinión más adelante, es un proyecto nuevo sobre esta base, no una fase pendiente de esta.

## 4. Metodología de estimación — principios, no receta cerrada

- El objetivo es un estimador **insesgado** de demanda por alcaldía y dominio, con **intervalo de confianza**, no solo un score puntual.
- Los snapshots DENUE multi-año (2016→2026) son la serie histórica disponible — probablemente el enfoque combine tendencia temporal de oferta existente + población en riesgo (censo/edades) como denominador.
- **Esta metodología debe diseñarse explícitamente antes de que cualquier agente empiece a escribir código de modelado.** No dejar que un subagente de implementación decida el estimador; eso se discute y se documenta aquí o en `docs/methodology.md` primero.

## 5. Frontend — decisión tomada: nivel "profesional", no prototipo

**Frontend definitivo: HTML/CSS/JS vanilla, sin Streamlit ni frameworks de dashboard (Dash, Gradio, etc.). Estándar de calidad: producto terminado, no prototipo de hackathon.**

- `src/app.py` y `.streamlit/config.toml` quedan **deprecados** — no se les agregan features nuevas. Se pueden dejar como referencia de lógica (si `app.py` ya calcula algo del semáforo) pero el output final no corre sobre Streamlit.
- `dashboard.html` se descarta como base — no se parte de él ni se itera encima; es un prototipo, no el punto de partida del frontend profesional.
- **"Profesional" significa, en concreto:**
  - Sistema visual propio: paleta y tipografía elegidas deliberadamente, no los defaults de un framework CSS ni "look de plantilla de Bootstrap".
  - Responsive de verdad (usable en laptop y en celular, no solo "no se rompe").
  - Jerarquía visual clara entre el selector de dominio, el mapa y cualquier panel de detalle — no todo con el mismo peso.
  - Estados de interacción cuidados: hover, selección activa, transición al cambiar de dominio — nada instantáneo/brusco, pero tampoco animación por animación.
  - Accesibilidad básica: contraste suficiente en los colores del semáforo (esto importa doble aquí, porque rojo/amarillo/verde es exactamente el caso donde el contraste y no depender solo del color importan para daltonismo), tamaños de texto legibles.
  - Carga rápida: el frontend consume JSON estático precalculado, no debe sentirse pesado.
- **Excepción explícita**: para el mapa coroplético con drill-down alcaldía→AGEB se permite usar una librería de mapas ligera (**Leaflet** o **MapLibre GL**) — no cuenta como "framework de dashboard", es la pieza de renderizado geoespacial que no tiene sentido reescribir a mano. Todo lo demás (layout, selector de dominio, tarjetas, estado de la UI) va en JS vanilla.
- El frontend consume **datos estáticos precalculados** (JSON generado por el pipeline de estimación), no hace llamadas en vivo a Python/un backend. Esto simplifica el hosting y evita depender de un servidor corriendo el modelo en tiempo real.

## 6. Reglas para Claude Code al trabajar en este repo

1. **Nunca cargar un `.csv`, `.geojson` o `.xlsx` completo en contexto.** Cada carpeta de dato ya trae:
   - `README.md` — descripción del dataset
   - `resumen_calidad.json` / `reporte_calidad_*.json` — resumen de calidad ya calculado
   - `diccionario_campos*.csv` — el schema
   Leer esos tres primero. Solo si es estrictamente necesario, usar `head -20` o `pandas.read_csv(..., nrows=20)` / `.info()` sobre el archivo real — nunca abrirlo entero.
2. Para shapefiles, usar `ogrinfo -so` (o el equivalente en `geopandas`, `gdf.head()` / `gdf.crs`) para ver estructura, no cargar todos los registros.
3. Antes de tocar código de modelado o del frontend, generar primero `docs/current-state.md` (inventario) y tenerlo revisado por el usuario.
4. No renombrar/mover carpetas de `data/` sin un plan explícito aprobado — varias tienen nombres inconsistentes que hay que unificar con cuidado (mismatch entre "MAYO 2025 CDMX" y "COMERCIOS_2025_05" podría ser el mismo corte).

## 7. Estructura objetivo propuesta (a validar, no aplicar aún)

```
chipos_dataton/
├── data/
│   ├── raw/            # snapshots originales, un subdirectorio por fuente+fecha, nombre normalizado
│   ├── processed/       # depurados actuales, mismo esquema de nombres
│   └── reference/       # AGEB shapefile, diccionarios de campos compartidos
├── src/
│   ├── etl/             # consolidación de snapshots
│   ├── modeling/         # estimador + intervalos de confianza
│   └── app/              # frontend: HTML/CSS/JS vanilla + Leaflet/MapLibre para el mapa
├── docs/
│   ├── current-state.md
│   └── methodology.md
└── CLAUDE.md
```
