# Problemas de datos

Hallazgos verificados con consultas SQL agregadas (DuckDB) sobre las 11 ediciones de cada
familia DENUE y el censo por AGEB. Perfil base en `docs/perfil_datos.md`. Fecha: 2026-09-18.
Severidad: **C** crítico (bloquea o sesga el objetivo), **A** alto, **M** medio, **B** bajo.

## 1. Críticos

**C1 · Demanda — ✅ RESUELTO (2026-09-18).** Censo oficial INEGI 2010 y 2020 por AGEB urbana y
CONAPO municipal 1990–2040 descargados (`docs/data_manifest.md`). ENUT sigue siendo solo contexto
(resolución de entidad). Quedan hallazgos derivados en N1–N4.

**C2 · Las 11 ediciones no son 11 observaciones independientes: hay dos re-levantamientos.**
Trazabilidad de `ID` entre ediciones consecutivas (altas/bajas = ID nuevo/desaparecido):

| transición | infancias perm./altas/bajas | salud altas/bajas | comercios altas/bajas |
|---|---|---|---|
| 2018-11→2019-11 | 8,661 / 2,560 / 2,963 | 10,430 / 10,286 | 27,200 / 28,487 |
| 2023-11→2024-11 | 8,547 / 1,650 / 2,937 | 9,131 / 8,800 | 27,078 / 26,039 |
| resto (8 transiciones) | altas ≤ 743, bajas ≤ 394 | ≤ 922 / ≤ 772 | ≤ 2,928 / ≤ 2,751 |
| 2021-11→2022-11 | 7 / 9 | 40 / 10 | 77 / 12 |

- Rotación de 25–35 % concentrada en 2019-11 y 2024-11 (actualizaciones tras Censos Económicos 2019 y
  2024); entre ellas los cortes son casi copias. La información efectiva es ~3 regímenes:
  2016-10…2018-11, 2019-11…2023-11, 2024-11…2026-05.
- Una tendencia ajustada a 11 puntos (Mann-Kendall, OLS) sobreestima la evidencia (pseudo-réplica) y
  confunde el escalón de levantamiento con cambio real.
- En 2023→2024 ninguna de las 2,937 bajas de `ID` conserva su `CLEE` en 2024 (0 coincidencias):
  no es re-asignación de identificador, son bajas de registro.

**C3 · Caída de oferta de infancias en 2024-11 (−11.2 %, 11,484 → 10,197): concentrada, no uniforme.**
- Por sector: Privado −22.8 % (5,486 → 4,234); No especificado −17.8 %; **Público +1.2 %** (5,432 → 5,498).
- Por SCIAN/subcategoría (Principal): preescolar privado 611111 −38.7 % (1,608 → 986), guardería
  privada 624411 −29.1 % (464 → 329), primaria privada −20.3 %; público: preescolar −1.2 %, primaria
  −0.6 %. 16 de 50 códigos caen > 20 %.
- De las 2,937 bajas de `ID`, reaparecen 70 en 2025-05 y 87 en 2026-05 (3 %); solo 91 tienen otro
  registro con el mismo nombre en el mismo AGEB entre 2024-11 y 2026-05. No es re-asignación de ID.
- En salud (+1.2 %) y comercios (+1.2 %) el mismo levantamiento no produjo caída neta.
- **Conclusión:** más probable **cierre real acumulado** (preescolares y guarderías privadas tras
  2020) que solo se registró al volver a campo en 2024; los cortes 2020-11…2023-11 arrastraban
  registros de 2019 (2021→2022: 7 altas, 9 bajas en plena pandemia). Es depuración en el *registro*
  de cierres reales, mal fechada en el tiempo. Tratamiento: `metodologia.md` §6 (fechas de
  levantamiento, confianza máxima media, nota visible).

**C4 · Geometría AGEB — ✅ RESUELTO.** `data/reference/ageb_cdmx.geojson` (MG 2020 censal: 2,431
urbanas + 22 rurales, EPSG:4326, todas válidas, bbox dentro de CDMX) y versión simplificada de
1.51 MB. Join con censo 2020: 2,431/2,433 (99.92 %); claves DENUE Principal 2026-05: 99.73 % (N3).

**C5 · Hoja `AGEB 2010` del xlsx truncada — ✅ RESUELTO.** Reemplazada por el CSV oficial
(2,432 AGEB, 16 alcaldías; hoja marcada superseded). Pareo 2010↔2020 por CVEGEO: 2,430 en ambos,
3 solo 2020, 2 solo 2010. Claves DENUE Principal con pareja en 2010: 79.5 % → **99.7 %**.

## 2. Altos

**A1 · Nombres de alcaldía con mojibake en 2016-10, 2017-11, 2018-11** (`Alcaldía`, infancias):
"CuauhtÃ©moc", "Benito JuÃ¡rez", "CoyoacÃ¡n", "Ã\u0081lvaro ObregÃ³n", "TlÃ¡huac" → 21 nombres para 16
claves. Mismo problema en `Personal ocupado` ("251 y mÃ¡s personas", 44 filas en 2016-10).
**Regla:** agrupar siempre por `CVE_MUN` de la clave AGEB, nunca por nombre.

**A2 · `CLEE` 100 % nula en 2016-10…2020-11** (infancias y salud); en comercios la columna `clee` no
existe en esas ediciones. El único identificador trazable en las 11 ediciones es `ID`/`id`.

**A3 · `Año de alta DENUE` 100 % nulo en 2016-10 y 2017-11** (infancias y salud). `Fecha de alta` es
fecha de incorporación por lote, no de apertura: en 2026-05 el 55 % dice 2010-07 (5,664) y 16 %
2014-12. No sirve para reconstruir aperturas.

**A4 · Dispersión alta por AGEB** (infancias, 2026-05): 2,047 AGEB con ≥1 establecimiento; mediana 4,
p25 = 2, p95 = 12, máx 31; 29 % de AGEB con ≤ 2 y 66 % con ≤ 5. Con alcance `Principal`, 1,811 AGEB
tienen establecimientos en las 11 ediciones, 65 en solo 3. Cambios de ±1 establecimiento = ±25–50 %.

**A5 · 336 claves AGEB con `CVE_LOC` ≠ `0001`** (unión de las 3 familias; alcaldías 004, 008, 009,
010, 011, 012, 013): localidades urbanas distintas de la cabecera (pueblos de Milpa Alta, Tlalpan,
Xochimilco, etc.). Deben existir en el marco urbano; verificar al unir la geometría.

## 3. Medios

**M1 · Cambio de SCIAN 2013 → 2018** en 2018-11 (`Versión SCIAN declarada`). Sin salto de filas en ese
corte (+0.1 % infancias), impacto bajo. Códigos que aparecen/desaparecen: 519121/519122 (bibliotecas,
48+46 filas, hasta 2023-11), 713111, 611421, 713944 (hasta 2023-11); 624199, 611512 (desde 2019-11).
`data/reference/dominios_scian.csv` solo cubre el dominio `adultos_mayores` (10 códigos): **no hay
tabla de armonización SCIAN para infancias**.

**M2 · Coordenadas fuera de CDMX pese a `Coordenadas válidas` = 1:** salud 2020-11: 85 puntos fuera
del bbox (−99.37, 19.04, −98.94, 19.60); salud 2024-11: 3; salud 2019-11: 1 (ID 6719752, lat 25.57,
además con `Clave geográfica AGEB` nula: única clave nula de todo el conjunto); infancias 2020-11: 6.
Usar la clave AGEB, no las coordenadas, para asignar territorio.

**M3 · Tipos inestables entre ediciones:** `Mes de corte` BIGINT (2016–2024) vs VARCHAR "05"
(2025–2026); `Año de alta DENUE` VARCHAR vacío en 2016–2017. Leer con `all_varchar` y castear.

**M4 · Intervalos irregulares:** 2016-10→2017-11 = 1.08 años; luego anuales (noviembre) hasta 2024-11;
2024-11→2025-05 = 0.5 años; 2025-05→2026-05 = 1 año. Modelar con años decimales (2016.79 … 2026.37);
con índice de edición el primer tramo se trata como 1.00 en vez de 1.08 años y el semestral como 1.0
en vez de 0.5 (su contribución a la pendiente se distorsiona ×2).

**M5 · `areas_verdes` y `espacios_publicos` sin clave territorial.** 56 de 11,739 áreas verdes sin
geometría; 595 marcadas `revisar`. Requieren join espacial (WGS84) con AGEB. Son un solo corte:
covariables estáticas, no explican cambio temporal.

## 4. Bajos / verificados sin problema

- **B1** Clave AGEB: 13 caracteres, prefijo `09`, `CVE_MUN` 002–017, 0 nulos (salvo M2) en infancias,
  salud y comercios; `AGEB` (4 caracteres) consistente.
- **B2** Sin `ID` duplicados dentro de ninguna edición en las 3 familias.
- **B3** Universo de claves estable: 2,653 claves en total, 2,505 en 2016-10 y 2,573 en 2026-05; solo 2
  claves de infancias 2016 no aparecen en 2026 en ninguna familia → marco AGEB consistente
  (compatible con Marco Geoestadístico 2010–2020; confirmar versión exacta al descargar).
- **B4** `Es secundaria` y `Es escuela de varios niveles` coinciden en total (883) en 2026-05 pero
  difieren fila a fila (1,766 filas distintas): coincidencia, no columna duplicada.

## 5. Hallazgos nuevos (fuentes descargadas)

**N1 · (A) CONAPO 2020 > censo urbano 2020 en 0–14.** Σ CDMX: +5.9 %. Por alcaldía, bruto: de −3.8 %
(014) a +29.7 % (009 Milpa Alta). Descomposición: (i) cobertura: las AGEB urbanas cubren 82.8 % de la
población de Milpa Alta y 95.6–98.9 % en el resto (lo rural no tiene AGEB censal); (ii) la
proporción 0–14 de CONAPO supera a la censal en +3.7 % (CDMX), por la conciliación demográfica
(corrección de subenumeración infantil) y el paso de marzo a mitad de año. Residuo > ±5 % tras
ajustar cobertura: 008 +5.4, 009 +7.4, 012 +5.9, 013 +6.0, 014 −5.1. **Consecuencia:** CONAPO se usa
para la **tasa** de cambio (razón 2027.5/2020), no para el nivel (`metodologia.md` §2).

**N2 · (M) CONAPO proyecta una caída más fuerte que la observada 2010–2020.** Tasa 0–14 2020→2027:
−1.45 %/año (009) a −4.19 %/año (003); en 2010–2020 el censo da −0.3 a −2.3 %/año por alcaldía y la reconstrucción CONAPO −0.4 a −2.8 %/año (máxima discrepancia: 014, −0.28 vs −2.14). Con la
banda ±1 %/año casi todo AGEB saldrá `baja`; es un resultado sustantivo, no un artefacto.

**N3 · (B) Claves sin polígono.** Censo 2020 sin polígono en MG 2020: `0901101101107` (3,050 hab.) y
`0901201351227` (4,058 hab.). Claves DENUE Principal sin polígono (5): `0901301370902`,
`0900400670157`, `0900902970539`, `0900901740100`, `0900400600157`; usan localidades rurales, cuyas
AGEB en `09ar` tienen CVEGEO de 9 caracteres (ENT+MUN+AGEB) → `sin_datos` (AGEB rural).

**N4 · (M) MG 2010 v5.0 no publica AGEB rurales** (solo `AGEB_urb_2010_5`). No afecta a la demanda
(el censo por AGEB es solo urbano); la equivalencia 2010↔2020 se calcula sobre urbanas.

**N5 · (B) Geografía 2010→2020 casi estable.** Traslape de áreas (MG 2010 v5.0 vs MG 2020): misma
unidad 2,331 (≥ 95 % de área compartida en ambos sentidos); fusión/expansión 62 y cambio de
límites 37 (en su mayoría con la misma clave: bordes urbanos que crecieron); división 1. Estas 100
AGEB suman 60,820 niños 0–14 en 2020 (3.7 %).

## 6. Bloqueantes

| sev. | ítem | estado |
|---|---|---|
| C | Censo 2010 completo | ✅ resuelto (C5) |
| C | Proyecciones CONAPO municipales | ✅ resuelto (serie 1990–2040 base 2020; cubre 2027) |
| C | Geometría AGEB 2020 | ✅ resuelto (C4) |
| A | Geometría AGEB 2010 y equivalencia | ✅ resuelto (N4, N5) |
| A | Identificación de AGEB rurales | ✅ resuelto: capa `09ar` (22 AGEB) → `ambito = rural` |
| M | Validación externa con series municipales 1990–2015 | ⚪ opcional: CONAPO trae la reconstrucción 1990–2019 por municipio (mismo archivo); se puede usar sin descargar nada más |
| M | Nivel CONAPO vs censo (N1) | ⚠️ tratado por método (tasa, no nivel); documentado |
