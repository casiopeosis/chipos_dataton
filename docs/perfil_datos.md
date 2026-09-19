# Perfil de datos

Generado por `tools/profile_data.py` el 2026-09-18. No editar a mano; regenerar con `python tools/profile_data.py`.
%vacío = cadenas vacías (distinto de NULL). En columnas numéricas binarias se muestran los valores.

## Inventario (por carpeta)
| carpeta | archivos | MB total | ejemplo |
|---|---|---|---|
| data/processed/areas_verdes | 2 | 20.4 | inventario_areas_verdes_cdmx_depurado.csv, inventario_areas_verdes_cdmx_depurado.geojson |
| data/processed/censo | 1 | 0.3 | AGEB_2010_2020.xlsx |
| data/processed/censo/inegi_2010 | 3 | 36.8 | fd_resultados_ageb_urbana_cpv2010.csv, metadatos_resultados_ageb_urbana_cpv2010.txt, resultados_ageb_urbana_09_cpv2010.csv |
| data/processed/censo/inegi_2020 | 3 | 44.1 | conjunto_de_datos_ageb_urbana_09_cpv2020.csv, diccionario_datos_ageb_urbana_09_cpv2020.csv, metadatos_ageb_urbana_09_cpv2020.txt |
| data/processed/comercios | 11 | 675.0 | 11 ediciones, p. ej. denue_comercios_cdmx_2026_05_depurado.geojson |
| data/processed/conapo | 1 | 36.7 | pobproy_quinq1.csv |
| data/processed/enut | 1 | 0.7 | enut_2024_cdmx_uso_tiempo.csv |
| data/processed/espacios_publicos | 1 | 7.5 | espacio_publico_cdmx_depurado.geojson |
| data/processed/infancias | 11 | 69.9 | 11 ediciones, p. ej. denue_infancias_cdmx_2026_05.csv |
| data/processed/marco_geo/mg2010v5 | 2 | 3.7 | ageb_urbana_2010_09.gpkg, municipios_2010_09.gpkg |
| data/processed/marco_geo/mg2020 | 16 | 3.4 | 16 ediciones, p. ej. mg_cpyv2020_09.txt |
| data/processed/salud | 11 | 129.9 | 11 ediciones, p. ej. denue_salud_cdmx_2026_05.csv |
| data/reference | 5 | 6.6 | 5 ediciones, p. ej. dominios_scian.csv |

## Familia `infancias` (11 ediciones)

### Referencia: `denue_infancias_cdmx_2026_05.csv`
Filas: **10,326** · Columnas: **52**

| columna | tipo | %nulo | %vacío | distintos | min | max / top |
|---|---|---|---|---|---|---|
| Registro origen | BIGINT | 0.0 |  | 10326 | 270047 | 444536 |
| ID | BIGINT | 0.0 |  | 10326 | 631670 | 12333961 |
| CLEE | VARCHAR | 0.0 | 0.0 | 10326 |  |  |
| Establecimiento | VARCHAR | 0.1 | 0.0 | 9677 |  |  |
| Razón social | VARCHAR | 29.5 | 0.0 | 3041 |  |  |
| Código SCIAN | BIGINT | 0.0 |  | 44 | 531113 | 813230 |
| Actividad SCIAN | VARCHAR | 0.0 | 0.0 | 44 |  |  |
| Categoría del proyecto | VARCHAR | 0.0 | 0.0 | 1 |  | Infancias (10326) |
| Subcategoría | VARCHAR | 0.0 | 0.0 | 22 |  |  |
| Población objetivo estimada | VARCHAR | 0.0 | 0.0 | 10 |  | Primera infancia (0 a… (2854), Niñez escolar (6 a 11… (2273), Edades mixtas o no es… (1641), Niñez y adolescencia … (1257) |
| Sector | VARCHAR | 0.0 | 0.0 | 3 |  | Público (5481), Privado (4367), No especificado (478) |
| Alcance | VARCHAR | 0.0 | 0.0 | 2 |  | Principal (7267), Complementario (3059) |
| Dedicación a infancias | VARCHAR | 0.0 | 0.0 | 3 |  | Directa por código (8182), Mixta por código (1643), Probable por palabras (501) |
| Regla de inclusión | VARCHAR | 0.0 | 0.0 | 6 |  | Código SCIAN principa… (7267), Código SCIAN de forma… (1526), Código SCIAN de orien… (550), Clase SCIAN amplia má… (501) |
| Palabras clave detectadas | VARCHAR | 71.0 | 0.0 | 100 |  |  |
| Es guardería o estancia infantil | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (9723), 1 (603) |
| Es preescolar | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (8075), 1 (2251) |
| Es primaria | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (8053), 1 (2273) |
| Es secundaria | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (9443), 1 (883) |
| Es escuela de varios niveles | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (9443), 1 (883) |
| Es educación especial | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (9952), 1 (374) |
| Es media superior o técnica | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (9961), 1 (365) |
| Es formación complementaria | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (8800), 1 (1526) |
| Es club o deporte | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (9532), 1 (794) |
| Es recreación o cultura infantil | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (10106), 1 (220) |
| Es apoyo social o residencia | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (9695), 1 (631) |
| Enfoque primera infancia | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (7448), 1 (2878) |
| Revisión manual | VARCHAR | 0.0 | 0.0 | 2 |  | NO (7515), SI (2811) |
| Motivo de revisión | VARCHAR | 72.8 | 0.0 | 14 |  |  |
| Personal ocupado | VARCHAR | 0.0 | 0.0 | 7 |  | 11 a 30 personas (3997), 0 a 5 personas (2869), 6 a 10 personas (1648), 31 a 50 personas (862) |
| Tipo de unidad económica | VARCHAR | 0.0 | 0.0 | 2 |  | Fijo (10292), Semifijo (34) |
| Alcaldía | VARCHAR | 0.0 | 0.0 | 16 |  |  |
| Localidad | VARCHAR | 0.0 | 0.0 | 40 |  |  |
| Asentamiento | VARCHAR | 0.0 | 0.0 | 1168 |  |  |
| Código postal | VARCHAR | 0.0 | 0.0 | 1116 |  |  |
| Código postal válido | BIGINT | 0.0 |  | 2 | 0 | 1 · 1 (10030), 0 (296) |
| Tipo de vialidad | VARCHAR | 0.0 | 0.0 | 21 |  |  |
| Vialidad | VARCHAR | 0.0 | 0.0 | 4082 |  |  |
| Número exterior | BIGINT | 33.3 |  | 1239 | 0 | 10040 |
| Clave geográfica AGEB | VARCHAR | 0.0 | 0.0 | 2047 |  |  |
| AGEB | VARCHAR | 0.0 | 0.0 | 1694 |  |  |
| Manzana | VARCHAR | 0.0 | 0.0 | 83 |  |  |
| Latitud | DOUBLE | 0.0 |  | 9554 | 19.13388207 | 19.57813453 |
| Longitud | DOUBLE | 0.0 |  | 9549 | -99.33455071 | -98.95164427 |
| Coordenadas válidas | BIGINT | 0.0 |  | 1 | 1 | 1 · 1 (10326) |
| Fecha de alta DENUE | VARCHAR | 0.0 | 0.0 | 22 |  |  |
| Año de alta DENUE | BIGINT | 0.0 |  | 16 | 2010 | 2026 |
| Versión SCIAN declarada | BIGINT | 0.0 |  | 1 | 2018 | 2018 · 2018 (10326) |
| Año de datos | BIGINT | 0.0 |  | 1 | 2026 | 2026 · 2026 (10326) |
| Mes de corte | VARCHAR | 0.0 | 0.0 | 1 |  | 05 (10326) |
| Edición DENUE | VARCHAR | 0.0 | 0.0 | 1 |  | 2026-05 (10326) |
| Archivo fuente | VARCHAR | 0.0 | 0.0 | 1 |  | denue_09_shp.zip (10326) |

Ejemplos (campos no vacíos, truncados):
- `Registro origen=305713; ID=10068869; CLEE=0901562419800030200…; Establecimiento=CIENCIA ARTE Y CULT…; Razón social=FRENTE NACIONAL DE …; Código SCIAN=624198; Actividad SCIAN=Otros servicios de …; Categoría del proyecto=Infancias; Subcategoría=Apoyo social o refu…; Población objetivo estimada=Probable niñez o ad…; Sector=Privado; Alcance=Complementario; Dedicación a infancias=Probable por palabr…; Regla de inclusión=…`
- `Registro origen=325687; ID=9401718; CLEE=0901562422100008200…; Establecimiento=FUNDACION PRO NINOS…; Razón social=FUNDACION PRO NINOS…; Código SCIAN=624221; Actividad SCIAN=Refugios temporales…; Categoría del proyecto=Infancias; Subcategoría=Apoyo social o refu…; Población objetivo estimada=Probable niñez o ad…; Sector=Privado; Alcance=Complementario; Dedicación a infancias=Probable por palabr…; Regla de inclusión=C…`

### Diferencias por edición (vs referencia)
| edición | filas | Δ filas vs anterior | Clave geográfica AGEB distintos | diferencias |
|---|---|---|---|---|
| 2016-10 | 11,589 |  | 2083 | tipo: Año de alta DENUE BIGINT→VARCHAR, Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Razón social 40% (ref 29%), Palabras clave detectadas 81% (ref 71%), Motivo de revisión 77% (ref 73%), Número exterior 0% (ref 33%), Año de alta DENUE 100% (ref 0%) |
| 2017-11 | 11,610 | +0.2% | 2085 | tipo: Año de alta DENUE BIGINT→VARCHAR, Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Razón social 40% (ref 29%), Palabras clave detectadas 81% (ref 71%), Motivo de revisión 77% (ref 73%), Número exterior 0% (ref 33%), Año de alta DENUE 100% (ref 0%) |
| 2018-11 | 11,624 | +0.1% | 2085 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Razón social 40% (ref 29%), Palabras clave detectadas 81% (ref 71%), Motivo de revisión 76% (ref 73%), Número exterior 0% (ref 33%) |
| 2019-11 | 11,221 | -3.5% | 2091 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Palabras clave detectadas 67% (ref 71%), Motivo de revisión 76% (ref 73%), Número exterior 24% (ref 33%) |
| 2020-11 | 11,570 | +3.1% | 2109 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Razón social 37% (ref 29%), Palabras clave detectadas 68% (ref 71%), Número exterior 23% (ref 33%) |
| 2021-11 | 11,498 | -0.6% | 2105 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Razón social 37% (ref 29%), Palabras clave detectadas 68% (ref 71%), Número exterior 23% (ref 33%) |
| 2022-11 | 11,496 | -0.0% | 2105 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Razón social 37% (ref 29%), Palabras clave detectadas 68% (ref 71%), Número exterior 23% (ref 33%) |
| 2023-11 | 11,484 | -0.1% | 2104 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Razón social 37% (ref 29%), Palabras clave detectadas 68% (ref 71%), Número exterior 23% (ref 33%) |
| 2024-11 | 10,197 | -11.2% | 2041 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Código postal 3% (ref 0%), Número exterior 5% (ref 33%) |
| 2025-05 | 10,210 | +0.1% | 2042 | nulo/vacío: Motivo de revisión 75% (ref 73%), Número exterior 4% (ref 33%) |
| 2026-05 | 10,326 | +1.1% | 2047 | (referencia) |

## Familia `salud` (11 ediciones)

### Referencia: `denue_salud_cdmx_2026_05.csv`
Filas: **28,880** · Columnas: **44**

| columna | tipo | %nulo | %vacío | distintos | min | max / top |
|---|---|---|---|---|---|---|
| Registro origen | BIGINT | 0.0 |  | 28880 | 50431 | 330000 |
| ID | BIGINT | 0.0 |  | 28880 | 631691 | 12329490 |
| CLEE | VARCHAR | 0.0 | 0.0 | 28880 |  |  |
| Establecimiento | VARCHAR | 0.1 | 0.0 | 17429 |  |  |
| Razón social | VARCHAR | 77.9 | 0.0 | 3619 |  |  |
| Código SCIAN | BIGINT | 0.0 |  | 51 | 464111 | 624199 |
| Actividad SCIAN | VARCHAR | 0.0 | 0.0 | 51 |  |  |
| Categoría del proyecto | VARCHAR | 0.0 | 0.0 | 1 |  | Salud (28880) |
| Subcategoría | VARCHAR | 0.0 | 0.0 | 29 |  |  |
| Sector | VARCHAR | 0.0 | 0.0 | 3 |  | Privado (18594), No especificado (9442), Público (844) |
| Alcance | VARCHAR | 0.0 | 0.0 | 2 |  | Principal (19794), Complementario (9086) |
| Regla de inclusión | VARCHAR | 0.0 | 0.0 | 4 |  | Prefijo SCIAN 621 o 6… (19794), Código SCIAN de farma… (7450), Código SCIAN de resid… (1621), Código social amplio … (15) |
| Palabras clave detectadas | VARCHAR | 92.1 | 0.0 | 40 |  |  |
| Es hospital | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (28491), 1 (389) |
| Es sanatorio (por nombre) | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (28818), 1 (62) |
| Es clínica o consultorio | BIGINT | 0.0 |  | 2 | 0 | 1 · 1 (18543), 0 (10337) |
| Es salud mental o psicológica | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (26581), 1 (2299) |
| Es farmacia | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (21430), 1 (7450) |
| Es residencia o cuidado | BIGINT | 0.0 |  | 2 | 0 | 1 · 0 (28566), 1 (314) |
| Revisión manual | VARCHAR | 0.0 | 0.0 | 2 |  | NO (26152), SI (2728) |
| Motivo de revisión | VARCHAR | 90.6 | 0.0 | 6 |  | None (26152), Posible duplicado: mi… (1870), Código postal faltant… (697), SCIAN mezcla atención… (126) |
| Personal ocupado | VARCHAR | 0.0 | 0.0 | 7 |  | 0 a 5 personas (25068), 6 a 10 personas (2025), 11 a 30 personas (1244), 31 a 50 personas (214) |
| Tipo de unidad económica | VARCHAR | 0.0 | 0.0 | 2 |  | Fijo (28775), Semifijo (105) |
| Alcaldía | VARCHAR | 0.0 | 0.0 | 16 |  |  |
| Localidad | VARCHAR | 0.0 | 0.0 | 44 |  |  |
| Asentamiento | VARCHAR | 0.0 | 0.0 | 1523 |  |  |
| Código postal | VARCHAR | 0.0 | 0.0 | 1385 |  |  |
| Código postal válido | BIGINT | 0.0 |  | 2 | 0 | 1 · 1 (28180), 0 (700) |
| Tipo de vialidad | VARCHAR | 0.0 | 0.0 | 22 |  |  |
| Vialidad | VARCHAR | 0.0 | 0.0 | 6107 |  |  |
| Número exterior | BIGINT | 13.2 |  | 2296 | 0 | 78888 |
| Clave geográfica AGEB | VARCHAR | 0.0 | 0.0 | 2223 |  |  |
| AGEB | VARCHAR | 0.0 | 0.0 | 1813 |  |  |
| Manzana | VARCHAR | 0.0 | 0.0 | 90 |  |  |
| Latitud | DOUBLE | 0.0 |  | 22938 | 19.13281879 | 19.57906731 |
| Longitud | DOUBLE | 0.0 |  | 22941 | -99.33850771 | -98.95139071 |
| Coordenadas válidas | BIGINT | 0.0 |  | 1 | 1 | 1 · 1 (28880) |
| Fecha de alta DENUE | VARCHAR | 0.0 | 0.0 | 24 |  |  |
| Año de alta DENUE | BIGINT | 0.0 |  | 16 | 2010 | 2026 |
| Versión SCIAN declarada | BIGINT | 0.0 |  | 1 | 2018 | 2018 · 2018 (28880) |
| Año de datos | BIGINT | 0.0 |  | 1 | 2026 | 2026 · 2026 (28880) |
| Mes de corte | VARCHAR | 0.0 | 0.0 | 1 |  | 05 (28880) |
| Edición DENUE | VARCHAR | 0.0 | 0.0 | 1 |  | 2026-05 (28880) |
| Archivo fuente | VARCHAR | 0.0 | 0.0 | 1 |  | denue_09_shp.zip (28880) |

Ejemplos (campos no vacíos, truncados):
- `Registro origen=300970; ID=683216; CLEE=0900262331200001600…; Establecimiento=CASA HOGAR VICENTE …; Razón social=SISTEMA NACIONAL PA…; Código SCIAN=623312; Actividad SCIAN=Asilos y otras resi…; Categoría del proyecto=Salud; Subcategoría=Asilo o residencia …; Sector=Público; Alcance=Complementario; Regla de inclusión=Código SCIAN de res…; Es hospital=0; Es sanatorio (por nombre)=0; Es clínica o consultorio=0; Es salu…`
- `Registro origen=324084; ID=667589; CLEE=0900262331100004400…; Establecimiento=INSTITUCION DE ASIS…; Razón social=INSTITUCION DE ASIS…; Código SCIAN=623311; Actividad SCIAN=Asilos y otras resi…; Categoría del proyecto=Salud; Subcategoría=Asilo o residencia …; Sector=Privado; Alcance=Complementario; Regla de inclusión=Código SCIAN de res…; Es hospital=0; Es sanatorio (por nombre)=0; Es clínica o consultorio=0; Es salu…`

### Diferencias por edición (vs referencia)
| edición | filas | Δ filas vs anterior | Clave geográfica AGEB distintos | diferencias |
|---|---|---|---|---|
| 2016-10 | 27,003 |  | 2165 | tipo: Año de alta DENUE BIGINT→VARCHAR, Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Razón social 80% (ref 78%), Palabras clave detectadas 97% (ref 92%), Motivo de revisión 87% (ref 91%), Número exterior 0% (ref 13%), Año de alta DENUE 100% (ref 0%) |
| 2017-11 | 27,129 | +0.5% | 2168 | tipo: Año de alta DENUE BIGINT→VARCHAR, Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Palabras clave detectadas 97% (ref 92%), Motivo de revisión 86% (ref 91%), Número exterior 0% (ref 13%), Año de alta DENUE 100% (ref 0%) |
| 2018-11 | 27,138 | +0.0% | 2168 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Palabras clave detectadas 97% (ref 92%), Motivo de revisión 86% (ref 91%), Número exterior 0% (ref 13%) |
| 2019-11 | 27,282 | +0.5% | 2196 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%) |
| 2020-11 | 27,432 | +0.5% | 2201 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: CLEE 100% (ref 0%), Número exterior 9% (ref 13%) |
| 2021-11 | 27,428 | -0.0% | 2201 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Razón social 80% (ref 78%), Número exterior 9% (ref 13%) |
| 2022-11 | 27,458 | +0.1% | 2201 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Razón social 80% (ref 78%), Número exterior 9% (ref 13%) |
| 2023-11 | 27,612 | +0.6% | 2198 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Número exterior 9% (ref 13%) |
| 2024-11 | 27,943 | +1.2% | 2218 | tipo: Mes de corte VARCHAR→BIGINT; nulo/vacío: Número exterior 2% (ref 13%) |
| 2025-05 | 28,266 | +1.2% | 2215 | nulo/vacío: Código postal 2% (ref 0%), Número exterior 2% (ref 13%) |
| 2026-05 | 28,880 | +2.2% | 2223 | (referencia) |

## Familia `comercios` (11 ediciones)

### Referencia: `denue_comercios_cdmx_2026_05_depurado.geojson`
Filas: **88,738** · Columnas: **21**

| columna | tipo | %nulo | %vacío | distintos | min | max / top |
|---|---|---|---|---|---|---|
| id | BIGINT | 0.0 |  | 88738 | 631840 | 12329490 |
| clee | VARCHAR | 0.0 | 0.0 | 88738 |  |  |
| nom_estab | VARCHAR | 0.0 | 0.0 | 48539 |  |  |
| raz_social | VARCHAR | 0.0 | 86.8 | 5470 |  |  |
| codigo_act | VARCHAR | 0.0 | 0.0 | 12 |  | 461110 (38996), 461130 (13165), 461122 (7123), 464111 (6572) |
| nombre_act | VARCHAR | 0.0 | 0.0 | 12 |  | Comercio al por menor… (38996), Comercio al por menor… (13165), Comercio al por menor… (7123), Farmacias sin minisúp… (6572) |
| municipio | VARCHAR | 0.0 | 0.0 | 16 |  |  |
| localidad | VARCHAR | 0.0 | 0.0 | 222 |  |  |
| ageb | VARCHAR | 0.0 | 0.0 | 1899 |  |  |
| tipoCenCom | VARCHAR | 0.0 | 76.5 | 16 |  |  |
| nom_CenCom | VARCHAR | 0.0 | 76.5 | 1016 |  |  |
| edicion_denue | VARCHAR | 0.0 | 0.0 | 1 |  | 2026-05 (88738) |
| categoria_proyecto | VARCHAR | 0.0 | 0.0 | 2 |  | Primera necesidad (81288), Complementario (7450) |
| subcategoria_proyecto | VARCHAR | 0.0 | 0.0 | 12 |  | Abarrotes, ultramarin… (38996), Frutas y verduras (13165), Carne de aves (7123), Farmacia sin minisúper (6572) |
| alcance_analitico | VARCHAR | 0.0 | 0.0 | 2 |  | Complementario (46364), Principal (42374) |
| es_primera_necesidad | VARCHAR | 0.0 | 0.0 | 2 |  | SI (81288), NO (7450) |
| es_tienda_imss | VARCHAR | 0.0 | 0.0 | 2 |  | NO (88733), SI (5) |
| infraestructura_comercial | VARCHAR | 0.0 | 77.2 | 5 |  |  (68489), MERCADO PUBLICO (15365), CENTRAL DE ABASTO (4020), CENTRO Y PLAZA COMERC… (844) |
| revision_manual | VARCHAR | 0.0 | 0.0 | 2 |  | NO (88700), SI (38) |
| motivo_revision | VARCHAR | 0.0 | 100.0 | 2 |  |  (88700), Infraestructura comer… (38) |
| cve_geo_ageb | VARCHAR | 0.0 | 0.0 | 2523 |  |  |

Ejemplos (campos no vacíos, truncados):
- `id=1044127; clee=0901546112300051100…; nom_estab=7 MARES DE CUAUHTEM…; codigo_act=461123; nombre_act=Comercio al por men…; municipio=Cuauhtémoc; localidad=Cuauhtémoc; ageb=1074; edicion_denue=2026-05; categoria_proyecto=Primera necesidad; subcategoria_proyecto=Pescados y mariscos; alcance_analitico=Complementario; es_primera_necesidad=SI; es_tienda_imss=NO; revision_manual=NO; cve_geo_ageb=0901500011074`
- `id=11758795; clee=0901746211200289400…; nom_estab=7 ELEVEN SUC 2934 P…; raz_social=7-ELEVEN MEXICO; codigo_act=462112; nombre_act=Comercio al por men…; municipio=Venustiano Carranza; localidad=Venustiano Carranza; ageb=0121; edicion_denue=2026-05; categoria_proyecto=Primera necesidad; subcategoria_proyecto=Minisúper; alcance_analitico=Principal; es_primera_necesidad=SI; es_tienda_imss=NO; revision_manual=NO; cve_geo…`

Geometría: Point · bbox [-99.3486, 19.1148, -98.9452, 19.5792]

### Diferencias por edición (vs referencia)
| edición | filas | Δ filas vs anterior | cve_geo_ageb distintos | diferencias |
|---|---|---|---|---|
| 2016-10 | 86,534 |  | 2460 | faltan: clee; nulo/vacío: raz_social 93% (ref 87%), tipoCenCom 80% (ref 77%), infraestructura_comercial 97% (ref 77%) |
| 2017-11 | 86,831 | +0.3% | 2461 | faltan: clee; nulo/vacío: raz_social 93% (ref 87%), tipoCenCom 80% (ref 77%), infraestructura_comercial 97% (ref 77%) |
| 2018-11 | 86,997 | +0.2% | 2461 | faltan: clee; nulo/vacío: raz_social 92% (ref 87%), tipoCenCom 80% (ref 77%), infraestructura_comercial 97% (ref 77%) |
| 2019-11 | 85,710 | -1.5% | 2494 | faltan: clee; nulo/vacío: raz_social 92% (ref 87%) |
| 2020-11 | 85,309 | -0.5% | 2491 | faltan: clee; nulo/vacío: raz_social 92% (ref 87%), tipoCenCom 79% (ref 77%), nom_CenCom 79% (ref 76%), infraestructura_comercial 80% (ref 77%) |
| 2021-11 | 85,283 | -0.0% | 2491 | nulo/vacío: raz_social 93% (ref 87%), tipoCenCom 79% (ref 77%), nom_CenCom 79% (ref 76%), infraestructura_comercial 80% (ref 77%) |
| 2022-11 | 85,348 | +0.1% | 2491 | nulo/vacío: raz_social 93% (ref 87%), tipoCenCom 79% (ref 77%), nom_CenCom 79% (ref 76%), infraestructura_comercial 80% (ref 77%) |
| 2023-11 | 85,366 | +0.0% | 2489 | nulo/vacío: raz_social 93% (ref 87%), tipoCenCom 80% (ref 77%), nom_CenCom 79% (ref 76%), infraestructura_comercial 80% (ref 77%) |
| 2024-11 | 86,405 | +1.2% | 2518 | nulo/vacío: raz_social 92% (ref 87%) |
| 2025-05 | 88,116 | +2.0% | 2521 | nulo/vacío: raz_social 93% (ref 87%) |
| 2026-05 | 88,738 | +0.7% | 2523 | (referencia) |

## Covariables estáticas y encuesta

### `data/processed/enut/enut_2024_cdmx_uso_tiempo.csv`
Filas: **2,107** · Columnas: **66**

| columna | tipo | %nulo | %vacío | distintos | min | max / top |
|---|---|---|---|---|---|---|
| llavemod | DOUBLE | 0.0 |  | 2107 | 90002901101.0 | 96004510103.0 |
| llaveviv | BIGINT | 0.0 |  | 852 | 90002901 | 96004510 |
| llavehog | BIGINT | 0.0 |  | 863 | 900029011 | 960045101 |
| edad | BIGINT | 0.0 |  | 87 | 12 | 98 |
| sexo | BIGINT | 0.0 |  | 2 | 1 | 2 · 2 (1144), 1 (963) |
| niv | BIGINT | 0.0 |  | 12 | 0 | 99 |
| gra | BIGINT | 0.0 |  | 9 | 0 | 9 |
| cvegeo_x | BIGINT | 0.0 |  | 1 | 9 | 9 · 9 (2107) |
| cve_ent_x | BIGINT | 0.0 |  | 1 | 9 | 9 · 9 (2107) |
| tloc_x | BIGINT | 0.0 |  | 4 | 1 | 4 |
| menor10 | BIGINT | 0.0 |  | 2 | 1 | 2 · 2 (2052), 1 (55) |
| escolaridad | DOUBLE | 0.0 |  | 5 | 1.0 | 5.0 |
| cond_ind | BIGINT | 0.0 |  | 3 | 1 | 9 · 2 (1955), 1 (149), 9 (3) |
| cond_disc | BIGINT | 0.0 |  | 2 | 1 | 2 · 2 (1983), 1 (124) |
| cond_aee | BIGINT | 0.0 |  | 6 | 1 | 6 |
| est_dis_x | BIGINT | 0.0 |  | 5 | 73 | 77 |
| upm_dis_x | BIGINT | 0.0 |  | 185 | 1148 | 1333 |
| fac_per | BIGINT | 0.0 |  | 1219 | 1040 | 7012 |
| control | BIGINT | 0.0 |  | 185 | 900029 | 960045 |
| viv_sel | BIGINT | 0.0 |  | 10 | 1 | 10 |
| hogar | BIGINT | 0.0 |  | 3 | 1 | 3 · 1 (2083), 2 (19), 3 (5) |
| n_ren | BIGINT | 0.0 |  | 8 | 1 | 8 |
| cve_ent_y | BIGINT | 0.0 |  | 1 | 9 | 9 · 9 (2107) |
| cvegeo_y | BIGINT | 0.0 |  | 1 | 9 | 9 · 9 (2107) |
| tloc_y | BIGINT | 0.0 |  | 4 | 1 | 4 |
| est_dis_y | BIGINT | 0.0 |  | 5 | 73 | 77 |
| upm_dis_y | BIGINT | 0.0 |  | 185 | 1148 | 1333 |
| fac_viv | BIGINT | 0.0 |  | 177 | 1065 | 6861 |
| *38 cols agrupadas* (activ_prod_con_cp … activ_conviv) | DOUBLE | 0.0–0.0 | | | 0.0 | 296.96666666666664 |

Ejemplos (campos no vacíos, truncados):
- `llavemod=90002901101.0; llaveviv=90002901; llavehog=900029011; activ_prod_con_cp=32.75; activ_prod_sin_cp=12.75; activ_merc=0.0; trab_merc_pv=0.0; tras_trab=0.0; bus_trab=0.0; prod_bien_trab_auto=0.0; trab_no_rem_vol=32.75; trab_no_rem_hog=12.75; prep_serv_alim=6.0; limp_viv=2.16666666666666; limp_rop=1.0; mant_viv=0.0; compras_hog=3.0; pagos_tram_hog=0.0; org_sup_hog=0.58333333333333; trab_no_rem_con_cp=20.0; trab_…`
- `llavemod=90002901102.0; llaveviv=90002901; llavehog=900029011; activ_prod_con_cp=75.78333333333333; activ_prod_sin_cp=65.78333333333333; activ_merc=45.0; trab_merc_pv=40.0; tras_trab=5.0; bus_trab=0.0; prod_bien_trab_auto=0.0; trab_no_rem_vol=30.78333333333333; trab_no_rem_hog=20.78333333333333; prep_serv_alim=14.0; limp_viv=2.5; limp_rop=2.0; mant_viv=0.0; compras_hog=2.0; pagos_tram_hog=0.16666666666666; org_sup_h…`

### `data/processed/areas_verdes/inventario_areas_verdes_cdmx_depurado.csv`
Filas: **11,739** · Columnas: **11**

| columna | tipo | %nulo | %vacío | distintos | min | max / top |
|---|---|---|---|---|---|---|
| id_area_verde | VARCHAR | 0.0 | 0.0 | 11739 |  |  |
| nombre | VARCHAR | 52.1 | 0.0 | 1268 |  |  |
| categoria_fuente | VARCHAR | 0.0 | 0.0 | 11 |  | Áreas verdes compleme… (5776), Equipamientos urbanos… (3653), Parques, arboledas y … (1538), Plazas y jardines (315) |
| subcategoria_fuente | VARCHAR | 0.4 | 0.0 | 27 |  |  |
| tipo_analitico | VARCHAR | 0.0 | 0.0 | 7 |  | cobertura_verde_vial (5753), vegetacion_en_equipam… (3258), oferta_verde_recreati… (1849), revisar (595) |
| usar_cobertura_verde | BOOLEAN | 0.0 | 0.0 | 2 |  | True (11539), False (200) |
| usar_oferta_recreativa | BOOLEAN | 0.0 | 0.0 | 2 |  | False (9890), True (1849) |
| revision_manual | BOOLEAN | 0.0 | 0.0 | 2 |  | False (11144), True (595) |
| motivo_criterio | VARCHAR | 0.0 | 0.0 | 34 |  |  |
| area_m2 | DOUBLE | 0.5 |  | 11389 | 2.26 | 2478293.69 |
| area_ha | DOUBLE | 0.5 |  | 4760 | 0.0002 | 247.8294 |

Ejemplos (campos no vacíos, truncados):
- `id_area_verde=AV000001; categoria_fuente=Áreas verdes comple…; subcategoria_fuente=Veg. Arbórea, arbus…; tipo_analitico=cobertura_verde_vial; usar_cobertura_verde=True; usar_oferta_recreativa=False; revision_manual=False; motivo_criterio=Vegetación asociada…; area_m2=2270.59; area_ha=0.2271`
- `id_area_verde=AV000002; categoria_fuente=Áreas verdes urbana…; subcategoria_fuente=Terrenos baldíos; tipo_analitico=revisar; usar_cobertura_verde=False; usar_oferta_recreativa=False; revision_manual=True; motivo_criterio=Un terreno baldío n…; area_m2=27120.04; area_ha=2.712`

### `data/processed/areas_verdes/inventario_areas_verdes_cdmx_depurado.geojson`
Features: **11,739** · sin geometría: 56 · tipos: {'Polygon': 10601, 'MultiPolygon': 1082} · CRS: no declarado (RFC 7946 ⇒ WGS84)
bbox: [-99.3322, 19.1723, -98.9423, 19.5698]
Claves de properties (11): area_ha, area_m2, categoria_fuente, id_area_verde, motivo_criterio, nombre, revision_manual, subcategoria_fuente, tipo_analitico, usar_cobertura_verde, usar_oferta_recreativa
1er feature: `{"id_area_verde": "AV000001", "nombre": null, "categoria_fuente": "Áreas verdes complementarias o ligadas a la red vial", "subcategoria_fuente": "Veg. Arbórea, arbustiva y herbácea de glorietas", "tipo_analitico": "cobertura_verde_vial", "usar_cobertura_verde": true, "usar_oferta_recreativa": false, "revision_manual": false, "motivo_criterio": "Vegetación asociada a glorietas viales", "area_m2": …`

### `data/processed/espacios_publicos/espacio_publico_cdmx_depurado.geojson`
Features: **8,498** · sin geometría: 0 · tipos: {'Polygon': 8498} · CRS: no declarado (RFC 7946 ⇒ WGS84)
bbox: [-99.3318, 19.1347, -98.9515, 19.5797]
Claves de properties (5): area_ha, area_m2, id_espacio_publico, id_fuente, parte_original
1er feature: `{"id_espacio_publico": "EP000001", "id_fuente": 1, "parte_original": 1, "area_m2": 23794.97, "area_ha": 2.3795}`

## Censo por AGEB urbana (INEGI RESAGEBURB 2010 y 2020, `data/processed/censo/inegi_*`)
Filas AGEB = `MZA = '000'` y `AGEB <> '0000'`; `cvegeo` = '09'+MUN+LOC+AGEB. '*' y 'N/D' → NULL.
Columnas usadas: POBTOT, P_0A2, P_3A5, P_6A11, P_12A14, P_15A17, POB0_14 (198 cols en 2010, 230 en 2020).

| año | AGEB | alcaldías | pob. total | pob. 0–14 | 0–14 suprimido | suma grupos ≠ POB0_14 |
|---|---|---|---|---|---|---|
| 2010 | 2,432 | 16 | 8,810,393 | 1,924,275 | 30 | 0 |
| 2020 | 2,433 | 16 | 9,145,632 | 1,635,575 | 41 | 0 |

- Pareo por CVEGEO 2010↔2020: 2,430 en ambos, 3 solo 2020, 2 solo 2010.
- xlsx 2020 vs oficial (0–14 por alcaldía): diferencia máx. 0.00 %, alcaldías con ≥ 1 %: 0. El xlsx 2010 está truncado (superseded, ver data_manifest).
- Claves DENUE `denue_infancias_cdmx_2026_05.csv` (Principal, 1,863): 99.7 % en censo 2020, 99.7 % en 2010.

## CONAPO municipal (`data/processed/conapo/pobproy_quinq1.csv`)
Población a mitad de año por municipio, sexo y grupo quinquenal (0-4 … 85+), 1990–2040; ancho → tidy.
- 16 alcaldías, 1990–2040. 0–14 = 00_04 + 05_09 + 10_14 (coincide con el censo).
- CONAPO 2020 vs Σ AGEB urbanas 2020 (0–14), desvíos > 5 %: 004 7.3%, 005 5.3%, 007 5.6%, 008 7.2%, 009 29.7%, 010 5.4%, 011 8.3%, 012 9.6%, 013 10.8%, 017 5.3%.

## Marco Geoestadístico → `data/reference/ageb_cdmx*.geojson`
- MG 2020 (censal): 2,453 AGEB (2,431 urbanas, 22 rurales; CVEGEO rural de 9 caracteres). Tamaños: ageb_cdmx.geojson 5.08 MB, ageb_cdmx_simplificado.geojson 1.51 MB.
- Equivalencia AGEB urbanas 2020 → 2010 (MG 2010 v5.0, traslape de áreas): misma 2331, fusion_o_expansion 62, cambio_limites 37, division 1.

## Referencia

### `data/reference/alcaldias.csv`
Filas: **16** · Columnas: **3**

| columna | tipo | %nulo | %vacío | distintos | min | max / top |
|---|---|---|---|---|---|---|
| cve_alc | VARCHAR | 0.0 | 0.0 | 16 |  |  |
| cvegeo | VARCHAR | 0.0 | 0.0 | 16 |  |  |
| nombre_oficial | VARCHAR | 0.0 | 0.0 | 16 |  |  |

Ejemplos (campos no vacíos, truncados):
- `cve_alc=002; cvegeo=09002; nombre_oficial=Azcapotzalco`
- `cve_alc=003; cvegeo=09003; nombre_oficial=Coyoacán`

### `data/reference/dominios_scian.csv`
Filas: **10** · Columnas: **5**

| columna | tipo | %nulo | %vacío | distintos | min | max / top |
|---|---|---|---|---|---|---|
| scian | BIGINT | 0.0 |  | 10 | 611621 | 713944 |
| dominio | VARCHAR | 0.0 | 0.0 | 1 |  | adultos_mayores (10) |
| subcategoria | VARCHAR | 0.0 | 0.0 | 3 |  | deporte (6), cuidado_diurno (2), residencias (2) |
| en_serie_armonizada | BOOLEAN | 0.0 | 0.0 | 2 |  | True (8), False (2) |
| nota | VARCHAR | 0.0 | 0.0 | 4 |  | Clubes deportivos y d… (4), Centros de cuidado di… (2), Asilos y residencias … (2), Escuelas de deporte; … (2) |

Ejemplos (campos no vacíos, truncados):
- `scian=713941; dominio=adultos_mayores; subcategoria=deporte; en_serie_armonizada=True; nota=Clubes deportivos y…`
- `scian=713942; dominio=adultos_mayores; subcategoria=deporte; en_serie_armonizada=True; nota=Clubes deportivos y…`

### `data/reference/ageb_cdmx.geojson`
Features: **2,453** · sin geometría: 0 · tipos: {'Polygon': 2453} · CRS: urn:ogc:def:crs:OGC:1.3:CRS84
bbox: [-99.3649, 19.0482, -98.9403, 19.5928]
Claves de properties (3): ambito, cve_mun, cvegeo
1er feature: `{"cvegeo": "0901000011716", "cve_mun": "010", "ambito": "urbano"}`

### `data/reference/ageb_cdmx_simplificado.geojson`
Features: **2,453** · sin geometría: 0 · tipos: {'Polygon': 2453} · CRS: no declarado (RFC 7946 ⇒ WGS84)
bbox: [-99.3649, 19.0482, -98.9403, 19.5927]
Claves de properties (3): ambito, cve_mun, cvegeo
1er feature: `{"cvegeo": "0901000011716", "cve_mun": "010", "ambito": "urbano"}`

### `data/reference/alcaldias.geojson`
Features: **16** · sin geometría: 0 · tipos: {'Polygon': 16} · CRS: no declarado (RFC 7946 ⇒ WGS84)
bbox: [-99.3649, 19.0482, -98.9403, 19.5928]
Claves de properties (2): cve_alc, nombre
1er feature: `{"cve_alc": "002", "nombre": "Azcapotzalco"}`

### Brecha
- `data/reference/ageb_cdmx.geojson` **no existe**: no hay geometría AGEB (ver docs/problemas_datos.md).
