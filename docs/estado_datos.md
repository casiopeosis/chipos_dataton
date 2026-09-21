# Estado de datos — LISTO PARA PROMPT 2

Revisión 2026-09-18. Regenerar: `make descargas && make datos && make perfil`.

## Preparación
- ✅ `streamlit` desinstalado de `.venv`; no figura en `requirements.txt`.
- ✅ Decisiones vigentes en CLAUDE.md: 0–14 confirmado; banda ±1 %/año con probabilidad ≥ 0.80;
  caída DENUE 2024-11 = cierres reales 2020–2023 registrados de golpe (eje = fechas de
  levantamiento, oferta con tope de confianza `media`). Ruta de la fuente censal actualizada.

## Fuentes
- ✅ Censo 2010 RESAGEBURB entidad 09 completo: 2,432 AGEB, 16 alcaldías (015, 016, 017 y 014 completas).
- ✅ Censo 2020 AGEB urbana entidad 09: 2,433 AGEB; xlsx 2020 coincide al 0.00 % por alcaldía.
- ✅ CONAPO municipal 1990–2040 por sexo y grupo quinquenal (base Censo 2020): 16 alcaldías; cubre 2020–2027.
- ✅ Marco Geoestadístico 2020 (edición censal): AGEB urbanas (2,431), rurales (22), municipios (16).
- ✅ Marco Geoestadístico 2010 v5.0: AGEB urbanas (2,432) y municipios de la CDMX. ⚪ No existe capa
  de AGEB rurales 2010 en ese producto (no se necesita: el censo por AGEB es solo urbano).
- ✅ Equivalencia AGEB 2010↔2020: calculada por traslape (INEGI no la publica como tabla).
- ✅ URL, fecha, bytes y sha256 de cada descarga en `docs/data_manifest.md`; `unzip -t` sin errores.

## Validaciones
- ✅ Claves DENUE infancias Principal (2026-05) con pareja: 99.7 % en 2020 y **99.7 % en 2010** (antes 79.5 %).
- ✅ Censo 2020 oficial vs xlsx: diferencia 0–14 por alcaldía 0.00 % (< 1 %).
- ⚠️ CONAPO 2020 vs censo urbano 2020 (0–14) dentro de ±5 %: **no** en 10 de 16 alcaldías (bruto
  hasta +29.7 % en Milpa Alta). Explicado por cobertura rural y conciliación (+3.7 % en proporción
  0–14); tratado usando la **tasa** de CONAPO, no su nivel (problemas N1, metodología §2.5).
- ✅ Marco: 2,431 AGEB urbanas vs 2,433 del censo; join censo→polígono 99.92 % (2 sin polígono);
  2,453/2,453 geometrías válidas; bbox [−99.365, 19.048, −98.940, 19.593] dentro de CDMX; 22 rurales
  con `ambito = rural`.
- ✅ Simplificado para frontend: 1.51 MB (< 5 MB), 5 decimales, mapshaper 25 % con topología compartida.
- ✅ `make datos` y `make perfil` corren limpios y son deterministas (reejecución → archivos idénticos).
- ✅ Ningún archivo nuevo > 50 MB (mayor: CSV censo 2020, 44.1 MB). Los 11 GeoJSON de comercios
  (> 50 MB) ya estaban versionados antes; no se tocaron.

## Pendiente para el modelado (no bloquea)
- ⚪ `backend/src/chipos/` ya implementa demanda y oferta (B0-B8, B10-B12); pendiente
  `backtest.py` (validaciones de `docs/metodologia.md` §4, `correccion/action_plan.md` Fase 2) y la
  generalización a horizontes 1/3/5, segmentos 0–17 y cuatro ramas (Fases 1, 3-6).
- ⚪ Decidir si las 5 claves DENUE de localidades rurales se asignan a su AGEB rural de 9 caracteres
  (quedan `sin_datos` en demanda de todos modos).

## Descargas manuales
Ninguna: todo se obtuvo en línea. `conapo.segob.gob.mx` no respondió desde esta red; se usó el
espejo oficial de datos.gob.mx (misma serie).
