"""
capas_config.py — REGISTRO CENTRAL DE CAPAS
============================================

Este archivo es la ÚNICA fuente de verdad sobre qué capas existen, de dónde
salen, cómo se filtran, a qué radio se calcula su accesibilidad, contra qué
grupo de edad se normalizan y con qué peso entran por defecto.

Todo lo demás del pipeline (hexgrid, build_hex_master, modelo_predictivo) lee
de aquí. El frontend recibe una versión serializada de esto en
`layers_metadata.json` y genera sus sliders automáticamente.

=> Agregar una capa nueva = agregar una entrada aquí. Nada más.

DECISIONES DE DISEÑO QUE ESTÁN CODIFICADAS AQUÍ
------------------------------------------------
1. Todas las capas se convierten a un DÉFICIT normalizado 0-1 donde
   1 = máxima necesidad. Si no fueran todas la misma dirección y la misma
   escala, los pesos del usuario no significarían nada.

2. El radio (`radio_m`) no es decorativo: define hasta dónde "sirve" un
   equipamiento. Para infancias esto es crítico — un parque a 2 km no
   existe para un niño de 7 años. Los radios están calibrados a distancia
   peatonal infantil, más amplios para servicios que se visitan con adulto
   y en transporte (salud hospitalaria).

3. El denominador (`denominador`) es el grupo de edad que realmente demanda
   ese servicio. Una guardería se normaliza contra población 0-5, no contra
   población total: si no, las zonas envejecidas parecen "bien servidas".

4. `temporal=True` marca las capas que tienen series históricas DENUE y por
   lo tanto entran al modelo predictivo. Las capas sin serie (áreas verdes,
   espacio público) se proyectan como constantes y así se declara en el
   dashboard — no inventamos una tendencia que no medimos.

5. Las capas de puntos (DENUE) pueden ponderar cada registro por tamaño
   (`col_personal_ocupado`), por sector público/privado (`col_sector` +
   `factor_sector`) y por relevancia (`col_alcance` + `factor_alcance`) antes
   de sumarlo al hexágono. Esto no cambia la escala final —la normalización
   por percentil la vuelve a poner en 0-1— pero sí cambia el ORDEN relativo
   de los hexágonos, que es lo único que importa para el semáforo.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Factores de ponderación reutilizables entre capas DENUE
# ---------------------------------------------------------------------------
# Un consultorio privado o una escuela "complementaria" no ofrecen el mismo
# acceso real que su contraparte pública/principal. Estos factores NO
# eliminan el registro (seguimos sin poder distinguir con certeza en 8,972+
# casos "No especificado"): lo descuentan.
FACTOR_SECTOR_DEFAULT = {
    "Privado": 0.70,
    "Público": 1.00,
    "No especificado": 0.85,   # penalización leve: no sabemos, pero DENUE
                                # tiende a sub-registrar público más que privado
}
FACTOR_ALCANCE_DEFAULT = {
    "Principal": 1.00,
    "Complementario": 0.50,    # un salón de fiestas no es lo mismo que una escuela
}


# ---------------------------------------------------------------------------
# Grupos de edad (denominadores de demanda)
# ---------------------------------------------------------------------------
# Deben existir como columnas en la tabla de población por hexágono.
# OJO: estas columnas todavía NO se pueden construir — falta el Censo por
# AGEB/manzana con desglose por edad. Ver README_PIPELINE.md, bloqueo #1.
GRUPOS_EDAD = {
    "pob_0a5":   "Primera infancia (0-5 años)",
    "pob_6a11":  "Niñez escolar (6-11 años)",
    "pob_12a17": "Adolescencia (12-17 años)",
    "pob_6a17":  "Niñez y adolescencia (6-17 años)",
    "pob_0a17":  "Total infancias (0-17 años)",
    "pob_total": "Población total",
}


@dataclass
class Capa:
    """Definición de una capa de necesidad."""

    id: str                      # nombre de columna: deficit_<id>
    label: str                   # texto que ve el usuario final
    descripcion: str             # tooltip / ficha explicativa
    tipo: str                    # "punto" | "poligono"
    archivo: str                 # nombre del archivo en data/
    metrica: str                 # "conteo" | "m2"
    radio_m: int                 # radio de accesibilidad (decaimiento exponencial)
    denominador: str             # clave de GRUPOS_EDAD
    peso_default: float          # peso inicial del slider (0-1)
    fuente: str                  # atribución para la ficha
    filtro: dict = field(default_factory=dict)   # {columna: valor o lista}
    columna_valor: Optional[str] = None          # para metrica="m2"
    temporal: bool = False       # ¿tiene series históricas DENUE?
    patron_temporal: Optional[str] = None         # glob de las ediciones
    nota_limitacion: str = ""    # se muestra en la ficha de explicabilidad

    # --- ponderación por registro (solo aplica a tipo="punto") -------------
    col_personal_ocupado: Optional[str] = None    # columna de rango de tamaño
    col_sector: Optional[str] = None              # columna Privado/Público/...
    factor_sector: Optional[dict] = None
    col_alcance: Optional[str] = None             # columna Principal/Complementario
    factor_alcance: Optional[dict] = None

    def col_deficit(self) -> str:
        return f"deficit_{self.id}"

    def col_acceso(self) -> str:
        return f"acceso_{self.id}"


# ---------------------------------------------------------------------------
# EL REGISTRO
# ---------------------------------------------------------------------------
CAPAS = [

    # --- Capa 1: áreas verdes recreativas -----------------------------------
    # La más importante para bienestar infantil. Usa la bandera analítica
    # `usar_oferta_recreativa` que ya trae la base depurada (1,849 de 11,739
    # polígonos, 1,632 ha): excluye camellones y glorietas, que son cobertura
    # verde pero NO son espacio donde un niño puede jugar.
    Capa(
        id="verde_recreativo",
        label="Áreas verdes recreativas",
        descripcion="m² de área verde efectivamente recreativa accesible a pie, por niño",
        tipo="poligono",
        archivo="inventario_areas_verdes_cdmx_depurado.geojson",
        filtro={"usar_oferta_recreativa": True},
        metrica="m2",
        columna_valor="area_m2",
        radio_m=400,             # distancia peatonal infantil sin cruzar avenidas
        denominador="pob_0a17",
        peso_default=0.22,
        fuente="Inventario de Áreas Verdes CDMX — Datos Abiertos",
        temporal=False,
        nota_limitacion=(
            "Sin serie histórica: se proyecta constante. La OMS recomienda "
            "9 m²/hab de área verde; aquí se mide accesibilidad relativa "
            "dentro de CDMX, no cumplimiento del estándar."
        ),
    ),

    # --- Capa 2: cobertura verde (ambiental, no recreativa) -----------------
    # Peso bajo a propósito: importa para calidad del aire y sombra, pero no
    # es espacio de juego. Se separa de la capa 1 para que el usuario pueda
    # distinguir "hay verde" de "hay dónde jugar".
    Capa(
        id="cobertura_verde",
        label="Cobertura verde ambiental",
        descripcion="m² de cualquier vegetación (incluye camellones y glorietas) por habitante",
        tipo="poligono",
        archivo="inventario_areas_verdes_cdmx_depurado.geojson",
        filtro={"usar_cobertura_verde": True},
        metrica="m2",
        columna_valor="area_m2",
        radio_m=600,
        denominador="pob_total",
        peso_default=0.06,
        fuente="Inventario de Áreas Verdes CDMX — Datos Abiertos",
        temporal=False,
        nota_limitacion="Incluye vegetación vial no pisable; NO es oferta de juego.",
    ),

    # --- Capa 3: espacio público --------------------------------------------
    Capa(
        id="espacio_publico",
        label="Espacio público",
        descripcion="m² de plazas, explanadas y espacio público abierto por niño",
        tipo="poligono",
        archivo="espacio_publico_cdmx_depurado.geojson",
        filtro={},
        metrica="m2",
        columna_valor="area_m2",
        radio_m=500,
        denominador="pob_0a17",
        peso_default=0.10,
        fuente="Espacio Público CDMX — Datos Abiertos",
        temporal=False,
        nota_limitacion=(
            "La base no distingue tipo de espacio ni estado de conservación; "
            "un m² de plaza cuenta igual que un m² de explanada."
        ),
    ),

    # --- Capa 4: educación básica -------------------------------------------
    # De la base de infancias. Usa las banderas ya construidas.
    Capa(
        id="educativo_basico",
        label="Escuelas de educación básica",
        descripcion="Preescolar, primaria y secundaria accesibles, por niño en edad escolar",
        tipo="punto",
        archivo="denue_infancias_cdmx_{edicion}.csv",
        filtro={"_flags_or": ["Es preescolar", "Es primaria", "Es secundaria",
                              "Es escuela de varios niveles"]},
        metrica="conteo",
        radio_m=800,
        denominador="pob_6a11",
        peso_default=0.14,
        fuente="DENUE — INEGI (ediciones 2017-2026)",
        temporal=True,
        patron_temporal="denue_infancias_cdmx_*.csv",
        col_personal_ocupado="Personal ocupado",
        col_sector="Sector",
        factor_sector=FACTOR_SECTOR_DEFAULT,
        col_alcance="Alcance",
        factor_alcance=FACTOR_ALCANCE_DEFAULT,
        nota_limitacion=(
            "DENUE registra la unidad económica, no su capacidad (matrícula). "
            "Se aproxima con el rango de personal ocupado como peso relativo; "
            "dos escuelas del mismo tamaño SÍ pesan igual, pero esto sigue "
            "siendo un proxy, no una matrícula real."
        ),
    ),

    # --- Capa 5: primera infancia (guarderías) ------------------------------
    Capa(
        id="primera_infancia",
        label="Guarderías y estancias infantiles",
        descripcion="Cuidado infantil accesible, por niño de 0 a 5 años",
        tipo="punto",
        archivo="denue_infancias_cdmx_{edicion}.csv",
        filtro={"_flags_or": ["Es guardería o estancia infantil"]},
        metrica="conteo",
        radio_m=1000,            # se llega con adulto, radio mayor
        denominador="pob_0a5",
        peso_default=0.12,
        fuente="DENUE — INEGI (ediciones 2017-2026)",
        temporal=True,
        patron_temporal="denue_infancias_cdmx_*.csv",
        col_personal_ocupado="Personal ocupado",
        col_sector="Sector",
        factor_sector=FACTOR_SECTOR_DEFAULT,
        col_alcance="Alcance",
        factor_alcance=FACTOR_ALCANCE_DEFAULT,
    ),

    # --- Capa 6: cultura y recreación infantil ------------------------------
    # Capa dispersa (296 + 544 + 8 registros): el suavizado por k-ring es
    # indispensable aquí o el mapa sale casi todo en cero.
    Capa(
        id="cultural_recreativo",
        label="Cultura y recreación infantil",
        descripcion="Escuelas de arte, bibliotecas, museos y recreación infantil accesibles",
        tipo="punto",
        archivo="denue_infancias_cdmx_{edicion}.csv",
        filtro={"_flags_or": ["Es recreación o cultura infantil",
                              "Es formación complementaria"]},
        metrica="conteo",
        radio_m=1200,
        denominador="pob_6a17",
        peso_default=0.12,
        fuente="DENUE — INEGI (ediciones 2017-2026)",
        temporal=True,
        patron_temporal="denue_infancias_cdmx_*.csv",
        col_personal_ocupado="Personal ocupado",
        col_sector="Sector",
        factor_sector=FACTOR_SECTOR_DEFAULT,
        col_alcance="Alcance",
        factor_alcance=FACTOR_ALCANCE_DEFAULT,
        nota_limitacion=(
            "Capa dispersa: muchos hexágonos en cero por baja densidad de "
            "registros, no necesariamente por ausencia real de oferta "
            "(ver principio del reto: 'la ausencia de datos no equivale a "
            "ausencia de demanda')."
        ),
    ),

    # --- Capa 7: deporte infantil -------------------------------------------
    Capa(
        id="deporte_infantil",
        label="Deporte y actividad física infantil",
        descripcion="Escuelas de deporte, clubes y ligas accesibles, por niño",
        tipo="punto",
        archivo="denue_infancias_cdmx_{edicion}.csv",
        filtro={"_flags_or": ["Es club o deporte"]},
        metrica="conteo",
        radio_m=1000,
        denominador="pob_6a17",
        peso_default=0.08,
        fuente="DENUE — INEGI (ediciones 2017-2026)",
        temporal=True,
        patron_temporal="denue_infancias_cdmx_*.csv",
        col_personal_ocupado="Personal ocupado",
        col_sector="Sector",
        factor_sector=FACTOR_SECTOR_DEFAULT,
        col_alcance="Alcance",
        factor_alcance=FACTOR_ALCANCE_DEFAULT,
    ),

    # --- Capa 8: salud de primer contacto -----------------------------------
    # De la base de salud. Filtra a lo relevante para infancias: consultorios
    # de medicina general y especializada, clínicas, hospitales generales.
    # Deliberadamente EXCLUYE consultorios dentales (6,895 registros) porque
    # inflarían la capa sin representar atención primaria pediátrica.
    Capa(
        id="salud_primaria",
        label="Salud de primer contacto",
        descripcion="Consultorios, clínicas y hospitales accesibles, por niño",
        tipo="punto",
        archivo="denue_salud_cdmx_{edicion}.csv",
        filtro={"_flags_or": ["Es clínica o consultorio", "Es hospital"]},
        metrica="conteo",
        radio_m=1500,            # se llega en transporte
        denominador="pob_0a17",
        peso_default=0.10,
        fuente="DENUE — INEGI (ediciones 2016-2026)",
        temporal=True,
        patron_temporal="denue_salud_cdmx_*.csv",
        col_personal_ocupado="Personal ocupado",
        col_sector="Sector",
        factor_sector=FACTOR_SECTOR_DEFAULT,
        col_alcance="Alcance",
        factor_alcance=FACTOR_ALCANCE_DEFAULT,
        nota_limitacion=(
            "DENUE no distingue público de privado de forma confiable "
            "(8,972 registros con sector 'No especificado'): se aplica un "
            "descuento de peso (0.70 privado / 0.85 no especificado) en vez "
            "de excluirlos, porque excluir 8,972 registros perdería demasiada "
            "información en zonas donde son la única oferta registrada."
        ),
    ),

    # --- Capa 9: abasto de primera necesidad --------------------------------
    Capa(
        id="abasto_alimentario",
        label="Abasto de alimentos frescos",
        descripcion="Fruterías, carnicerías, supermercados y abarrotes accesibles a pie",
        tipo="punto",
        archivo="denue_comercios_cdmx_{edicion}_depurado.geojson",
        filtro={"categoria_proyecto": "Primera necesidad"},
        metrica="conteo",
        radio_m=800,
        denominador="pob_total",
        peso_default=0.06,
        fuente="DENUE — INEGI (ediciones 2016-2026)",
        temporal=True,
        patron_temporal="denue_comercios_cdmx_*_depurado.geojson",
        col_alcance="alcance_analitico",
        factor_alcance=FACTOR_ALCANCE_DEFAULT,
        nota_limitacion=(
            "Alta densidad (78,889 registros en 2020): esta capa satura "
            "rápido y aporta poca discriminación entre hexágonos urbanos. "
            "Peso bajo a propósito. No trae 'Personal ocupado' ni 'Sector' "
            "en esta base, así que sólo se pondera por alcance."
        ),
    ),
]

# Validación de integridad al importar
_ids = [c.id for c in CAPAS]
assert len(_ids) == len(set(_ids)), "IDs de capa duplicados"
_suma = round(sum(c.peso_default for c in CAPAS), 4)
assert abs(_suma - 1.0) < 1e-6, f"Los pesos default suman {_suma}, deben sumar 1.0"
for _c in CAPAS:
    assert _c.denominador in GRUPOS_EDAD, f"{_c.id}: denominador '{_c.denominador}' no existe"
    assert _c.tipo in ("punto", "poligono"), f"{_c.id}: tipo inválido"

CAPAS_POR_ID = {c.id: c for c in CAPAS}
CAPAS_TEMPORALES = [c for c in CAPAS if c.temporal]


# ---------------------------------------------------------------------------
# Perfiles de riesgo (requisito explícito del reto)
# ---------------------------------------------------------------------------
# El reto pide "nivel de riesgo aceptable" como entrada. Se implementa como
# un penalizador sobre la incertidumbre de la proyección: un inversionista
# conservador descuenta las zonas cuya predicción tiene banda ancha.
PERFILES_RIESGO = {
    "conservador": {
        "label": "Conservador — zonas estables",
        "penalizacion_incertidumbre": 0.60,
        "descripcion": "Descuenta fuerte las zonas con proyección incierta.",
    },
    "balanceado": {
        "label": "Balanceado",
        "penalizacion_incertidumbre": 0.25,
        "descripcion": "Penalización moderada por incertidumbre.",
    },
    "alto_impacto": {
        "label": "Alto impacto — zonas en transformación",
        "penalizacion_incertidumbre": 0.0,
        "descripcion": "Ignora la incertidumbre; prioriza magnitud del déficit proyectado.",
    },
}


# ---------------------------------------------------------------------------
# Parámetros globales del pipeline
# ---------------------------------------------------------------------------
RESOLUCION_H3 = 9            # ~0.105 km², arista ~201 m, ~400 m de punta a punta
CRS_GEOGRAFICO = "EPSG:4326"
CRS_METRICO = "EPSG:6372"    # México ITRF2008/LCC — obligatorio para áreas
HORIZONTES = [1, 3, 5]       # años de proyección (requisito del reto)
METODO_NORMALIZACION = "percentil"   # "percentil" | "minmax"


def exportar_metadata(path: str = "layers_metadata.json") -> dict:
    """Serializa el registro para que el frontend arme sus controles solo.

    Esta función es el contrato: si el frontend lee esto, nunca tiene que
    hardcodear nombres de capa ni pesos.
    """
    import json

    meta = {
        "version_contrato": "1.0",
        "resolucion_h3": RESOLUCION_H3,
        "horizontes": HORIZONTES,
        "metodo_normalizacion": METODO_NORMALIZACION,
        "grupos_edad": GRUPOS_EDAD,
        "perfiles_riesgo": PERFILES_RIESGO,
        "capas": [
            {
                "id": c.id,
                "label": c.label,
                "descripcion": c.descripcion,
                "columna_deficit": c.col_deficit(),
                "peso_default": c.peso_default,
                "radio_m": c.radio_m,
                "denominador": c.denominador,
                "fuente": c.fuente,
                "tiene_proyeccion": c.temporal,
                "nota_limitacion": c.nota_limitacion,
            }
            for c in CAPAS
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    return meta


if __name__ == "__main__":
    print(f"{len(CAPAS)} capas registradas | pesos suman {_suma}")
    for c in CAPAS:
        t = "temporal" if c.temporal else "estática"
        print(f"  {c.id:22s} peso={c.peso_default:.2f} radio={c.radio_m:5d}m "
              f"denom={c.denominador:10s} [{t}]")
    exportar_metadata()
    print("\nlayers_metadata.json escrito.")
