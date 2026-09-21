// frontend/js/textos.js
// Fuente única de todas las cadenas de la interfaz (plans/frontend_specs.md §14, más las
// plantillas que remite a §5, §8, §9, §10.5, §10.7, §10.10-§10.13 de ese mismo documento y a
// `correccion/frontend_requisitos.md`). Ningún otro módulo de frontend/ debe tener texto de cara
// a la persona usuaria escrito a mano: siempre se importa de aquí.
//
// Reescrito para Habitancia (plans/frontend_plan.md §0): el titular de frase autogenerada
// (`titularDemandaGeneral`/`titularOfertaGeneral`/etc. de la versión anterior) se retira por
// completo -- lo sustituye el resumen estructurado de §6 (`resumen.js`), sin texto interpretativo
// dinámico. Nunca se genera una frase nueva en tiempo de ejecución: todo lo que ve la persona
// usuaria sale de aquí, como valores fijos o plantillas con variables (nunca decisiones de
// redacción).
//
// Convenciones de este módulo:
// - Los valores "hoja" son cadenas fijas o funciones de interpolación `(variables) => cadena`.
// - `texto(ruta, variables)` es un atajo genérico: busca `ruta` (con puntos) dentro de `textos`
//   y, si es función, la invoca con `variables`; si es cadena con `{marcadores}`, interpola.
// - Siempre "alcaldía" y "AGEB" (frente a la persona usuaria, "zona"); nunca el sinónimo
//   histórico previo a la reforma de 2016, ni jerga técnica del modelo (CLAUDE.md §2).

/** Números en palabra para menores de 10. */
const NUMEROS_EN_PALABRA = [
  'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve',
];

/** Convierte un entero no negativo menor que 10 a su palabra en español. */
export function numeroEnPalabras(numero) {
  if (Number.isInteger(numero) && numero >= 0 && numero < NUMEROS_EN_PALABRA.length) {
    return NUMEROS_EN_PALABRA[numero];
  }
  return String(numero);
}

/** Inserta espacios entre caracteres para que un lector de pantalla lea la clave dígito a dígito. */
export function digitosSeparados(clave) {
  return String(clave).split('').join(' ');
}

/** Interpolación simple de plantillas `{variable}` con `String(valor)`; sin lógica adicional. */
function interpolar(plantilla, variables = {}) {
  return plantilla.replace(/\{(\w+)\}/g, (coincidencia, clave) => (
    Object.prototype.hasOwnProperty.call(variables, clave)
      ? String(variables[clave])
      : coincidencia
  ));
}

// ---------------------------------------------------------------------------------------------
// §2, §14.1 Producto, navegación
// ---------------------------------------------------------------------------------------------

const producto = {
  nombre: 'Habitancia',
  nombreLargo: 'Habitancia — Oportunidades de servicios para infancias y adolescencias en la CDMX',
};

const navegacion = {
  raiz: 'CDMX',
  rutaAriaLabel: 'Ruta',
  volverGeneral: '← Todas las alcaldías',
  volverAlcaldia: (alcaldia) => interpolar('← Volver a {alcaldia}', { alcaldia }),
  explorar: 'Explorar alcaldía →',
  reencuadrar: 'Reencuadrar',
  entenderZona: 'Entender esta zona →',
};

// ---------------------------------------------------------------------------------------------
// §5.2 Buscador de alcaldía (siempre visible)
// ---------------------------------------------------------------------------------------------

const buscadorAlcaldia = {
  etiqueta: 'Selecciona o busca una alcaldía.',
  sinResultados: (v) => interpolar('Ninguna alcaldía coincide con «{texto}».', v),
};

// ---------------------------------------------------------------------------------------------
// §9 Vista de mapa (vista general + 4 ramas)
// ---------------------------------------------------------------------------------------------

const vista = {
  nombre: {
    general: 'Vista general',
    educacion: 'Educación y cultura',
    salud: 'Salud',
    comercio: 'Comercio',
    verde: 'Áreas verdes y espacio público',
  },
  controlEtiqueta: '¿Qué quieres ver en el mapa?',
};

// ---------------------------------------------------------------------------------------------
// §5.5 Tipo de búsqueda
// ---------------------------------------------------------------------------------------------

const busqueda = {
  nombre: {
    oportunidad: 'Dónde ampliar servicios',
    disponibilidad: 'Cobertura actual',
  },
  controlEtiqueta: '¿Qué quieres consultar?',
  ayuda: {
    oportunidad: 'Zonas con menor cobertura relativa y posible prioridad de expansión.',
    disponibilidad: 'Zonas con mayor cobertura relativa en la actualidad.',
  },
};

// ---------------------------------------------------------------------------------------------
// §5.3 Población objetivo (6 segmentos)
// ---------------------------------------------------------------------------------------------

const poblacion = {
  controlEtiqueta: 'Elige la población objetivo',
  nombre: {
    todas: '0 a 17 años (todas)',
    primera_infancia: 'Primera infancia · 0 a 2 años',
    preescolar: 'Preescolar · 3 a 5 años',
    primaria: 'Primaria · 6 a 11 años',
    secundaria: 'Secundaria · 12 a 14 años',
    adolescencia: 'Adolescencia · 15 a 17 años',
  },
  notaAdolescencia: 'Este rango tiene menos datos disponibles; su confianza máxima es media.',
};

// ---------------------------------------------------------------------------------------------
// §8 Control de horizonte
// ---------------------------------------------------------------------------------------------

const horizonte = {
  etiqueta: 'Horizonte',
  opcion: (v) => interpolar('{h} año(s) · {anio}', v),
  etiquetaAnios: (h) => interpolar('{h} año(s)', { h }),
  ariaValuetext: (v) => interpolar('{h} años, a mediados de {anio}', v),
  nota: {
    1: 'Proyección a corto plazo.',
    3: 'Equilibrio entre certeza y utilidad para planear.',
    5: 'A mayor plazo, mayor incertidumbre.',
  },
  // Ramas con proyección (educación/salud/comercio) solo reportan h1/h3 -- verde ninguno.
  deshabilitadoRama: (v) => interpolar(
    'Esta rama se pronostica solo a {h} año(s) ({anio}): los levantamientos disponibles no '
    + 'permiten proyectar más lejos.',
    v,
  ),
  sinProyeccion: 'Esta rama no tiene proyección: muestra su situación actual, sin línea futura.',
  deshabilitadoUnico: (anio) => interpolar(
    'Este conjunto de datos trae un solo horizonte: mediados de {anio}.',
    { anio },
  ),
};

// ---------------------------------------------------------------------------------------------
// Veredicto (demanda), confianza, oportunidad/disponibilidad (§4.2, §7.1)
// ---------------------------------------------------------------------------------------------

const veredicto = {
  palabra: {
    sube: 'Sube',
    se_mantiene: 'Se mantiene',
    baja: 'Baja',
    sin_datos: 'Sin datos',
  },
  simbolo: {
    sube: '▲',
    se_mantiene: '■',
    baja: '▼',
    sin_datos: '∅',
  },
};

/** Terciles de oportunidad/disponibilidad relativa (spec §4.2, §6.2): Alta/Media/Baja, nunca solo color. */
const tercil = {
  palabra: { alta: 'Alta', media: 'Media', baja: 'Baja', sin_datos: 'Sin datos' },
  simbolo: { alta: '●●●', media: '●●○', baja: '●○○', sin_datos: '∅' },
};

const confianza = {
  palabra: { alta: 'Alta', media: 'Media', baja: 'Baja' },
  simbolo: { alta: '●', media: '◐', baja: '○' },
  // §14.3, heredadas sin cambio.
  explicacion: {
    alta: 'el resultado se sostiene aun con supuestos distintos.',
    media: 'el sentido del cambio es probable, pero su tamaño es incierto.',
    baja: 'los datos no permiten afirmar el sentido del cambio con seguridad.',
  },
  ariaLabel: (v) => interpolar('confianza {nivel}', v),
};

// ---------------------------------------------------------------------------------------------
// §10.10 Prioridades (pesos) y §10.11 Filtros por rama
// ---------------------------------------------------------------------------------------------

const rama = {
  nombre: {
    educacion: 'Educación y cultura',
    salud: 'Salud',
    comercio: 'Comercio',
    verde: 'Áreas verdes y espacio público',
  },
};

const prioridades = {
  titulo: 'Prioridad por rama',
  circuloAriaLabel: (v) => interpolar('{rama}: prioridad {peso} de 5', v),
  restablecer: 'Restablecer prioridades',
  ayuda: 'Asigna de 1 a 5. Esto solo cambia el orden de los resultados.',
};

const filtros = {
  restablecer: 'Restablecer filtros',
  resumenActivo: (texto) => texto, // ya viene armado por filtros.js con nombres de textos.js.
  todos: 'Todos',
  ayuda: 'Elige qué servicios incluir en el análisis.',
  educacion: {
    pregunta: 'Educación y cultura',
    nivel: {
      guarderia: 'Guarderías y estancias infantiles',
      preescolar: 'Preescolar',
      primaria: 'Primaria',
      secundaria: 'Secundaria',
      educacion_especial: 'Educación especial',
      varios_niveles: 'Varios niveles',
      media_superior_tecnica: 'Media superior o técnica',
      recreacion_cultura: 'Recreación o cultura infantil',
    },
    ayuda: 'Selecciona los servicios que quieres analizar.',
  },
  salud: {
    pregunta: 'Salud',
    nivel: {
      clinicas: 'Clínicas o consultorios',
      hospitales: 'Hospitales',
      salud_mental: 'Salud mental o psicológica',
      farmacias: 'Farmacias',
    },
    ayuda: 'Solo se contabilizan las instalaciones seleccionadas.',
  },
  comercio: {
    pregunta: 'Comercio',
    primeraNecesidad: 'Comercios de primera necesidad',
    nivel: {
      supermercados_minisupers: 'Supermercados y minisúpers',
      abarrotes: 'Abarrotes',
      frutas_verduras: 'Frutas y verduras',
      carnes_otros_alimentos: 'Carnes y otros alimentos',
      farmacias: 'Farmacias',
    },
    ayuda: 'Selecciona los comercios que quieres contabilizar.',
  },
  verde: {
    pregunta: 'Áreas verdes y espacio público',
    nivel: {
      cobertura_verde: 'Cobertura verde',
      areas_recreativas: 'Áreas recreativas',
      espacios_publicos: 'Espacios públicos',
    },
    ayuda: 'Distingue cobertura verde, recreación y espacio público.',
  },
  sector: { todos: 'Todos', publico: 'Público', privado: 'Privado' },
  sectorEtiqueta: 'Sector',
};

const riesgo = {
  etiqueta: 'Confianza mínima',
  ayuda: 'Oculta resultados con menor confianza; no modifica los datos.',
};

// ---------------------------------------------------------------------------------------------
// §6 Resumen estructurado Nivel 1
// ---------------------------------------------------------------------------------------------

const resumen = {
  tituloGeneral: (v) => interpolar('CDMX · {poblacion} · {h} año(s)', v),
  tituloAlcaldia: (v) => interpolar('{alcaldia} · {poblacion} · {h} año(s)', v),
  campo: {
    poblacionObjetivo: 'Población objetivo',
    horizonte: 'Horizonte',
    oportunidad: 'Oportunidad relativa',
    disponibilidad: 'Disponibilidad relativa',
    confianza: 'Confianza',
    ramasIncidencia: 'Ramas con mayor incidencia',
  },
  sinRamas: 'Ninguna rama con datos suficientes en esta zona.',
};

// ---------------------------------------------------------------------------------------------
// §6.4 Motivos principales del resultado / §10.7 explicación por rama
// ---------------------------------------------------------------------------------------------

const explicacion = {
  titulo: '¿Qué explica este resultado?',
  circuloAriaLabel: (v) => interpolar('{rama}: señal {valor} de 5', v),
  ayuda: 'Los círculos muestran cuánto influye cada rama en el resultado.',
  peso: (peso) => interpolar('Peso {peso}/5', { peso }),
  contribucion: (pct) => interpolar('{pct}% del resultado combinado', { pct }),
};

// ---------------------------------------------------------------------------------------------
// §7 Ranking por AGEB
// ---------------------------------------------------------------------------------------------

const ranking = {
  tituloGeneral: 'Ranking de zonas · CDMX',
  tituloAlcaldia: (alcaldia) => interpolar('Ranking de zonas · {alcaldia}', { alcaldia }),
  columnas: {
    zona: 'Zona',
    alcaldia: 'Alcaldía',
    oportunidad: 'Oportunidad',
    disponibilidad: 'Disponibilidad',
    poblacion: 'Población objetivo',
    confianza: 'Confianza',
    ramaPrincipal: 'Rama principal',
  },
  detalle: {
    percentil: (v) => interpolar('percentil {percentil} entre las zonas de CDMX', v),
    ramas: 'Ramas',
  },
  ordenarPor: {
    oportunidad: 'Ordenar por oportunidad',
    disponibilidad: 'Ordenar por disponibilidad',
    alcaldia: 'Ordenar por alcaldía',
    confianza: 'Ordenar por confianza',
  },
  verMas: (n) => interpolar('Ver más ({n})', { n }),
  verSiguientes: (v) => interpolar('Mostrar {n} zonas más ({restantes} restantes)', v),
  topN: (n) => interpolar('Mostrando las {n} zonas con mayor prioridad', { n }),
  buscador: {
    etiqueta: 'Buscar AGEB por clave',
    sinResultados: (v) => interpolar('Ninguna clave coincide con «{texto}».', v),
  },
  verTodos: (v) => interpolar('Ver los {n} AGEB ↓', v),
  sinAgeb: 'No se encontraron AGEB para esta alcaldía.',
};

// ---------------------------------------------------------------------------------------------
// §7.4 Ficha de zona (AGEB)
// ---------------------------------------------------------------------------------------------

const ficha = {
  // "{tipo}" (urbana/rural, §7.4 de la versión anterior) se retiró: el contrato no trae un
  // indicador urbano/rural fuera del motivo "rural" de `motivosSinDatos` (solo aparece cuando la
  // zona además es sin_datos) -- no hay una columna que lo dé siempre, así que la ubicación usa
  // la clave AGEB en su lugar, dato que sí siempre existe (CLAUDE.md: no inventar datos).
  ubicacion: (v) => interpolar('{alcaldia} · AGEB {cvegeo}', v),
  oportunidadLabel: 'Oportunidad relativa',
  disponibilidadLabel: 'Disponibilidad relativa',
  confianzaLabel: 'Confianza',
  confianzaValor: (nivel) => interpolar(
    '{simbolo} {palabra} — {explicacion}',
    {
      simbolo: confianza.simbolo[nivel],
      palabra: confianza.palabra[nivel],
      explicacion: confianza.explicacion[nivel],
    },
  ),
  entenderZona: navegacion.entenderZona,
};

// ---------------------------------------------------------------------------------------------
// §10.5 Gráficas de Nivel 2
// ---------------------------------------------------------------------------------------------

const graficas = {
  poblacion: {
    titulo: 'Población objetivo: histórico y proyección',
    figcaption: (v) => interpolar(
      'En {anioA} había {valorA}; en {anioB}, {valorB}. La proyección a mediados de {anioH} es '
      + '{valorH} (rango probable entre {lo} y {hi}).',
      v,
    ),
  },
  servicios: {
    titulo: (rama) => interpolar('Oferta de {rama}: histórico y proyección', { rama }),
    sinProyeccion: (rama) => interpolar(
      '{rama} no tiene proyección: se muestra la situación actual, sin línea futura.',
      { rama },
    ),
  },
  cobertura: {
    titulo: 'Cobertura frente a la CDMX',
    referenciaCdmx: 'Referencia CDMX',
  },
  sinDatos: 'No hay serie disponible para esta selección.',
};

// Nivel 2 de zona (§10.6): "¿Qué tan confiable es la estimación?" -- cifras reales de
// docs/backtest.md (F-7 de correccion/avance_plan.md), citadas aquí en vez de recalculadas en
// cliente. Se actualizan a mano si se corre `make backtest` con datos distintos.
const confiabilidad = {
  titulo: '¿Qué tan confiable es la estimación?',
  parrafo:
    'La demanda mostró buen desempeño al compararse con datos pasados. La oferta identifica mejor '
    + 'la dirección que el tamaño del cambio; por eso su confianza máxima es media.',
};

// ---------------------------------------------------------------------------------------------
// §10.6 Franja lateral y drawer "Entender esta zona / Metodología"
// ---------------------------------------------------------------------------------------------

const metodologia = {
  enlaceCabecera: 'Metodología ↗',
  franja: 'Metodología y limitaciones ↓',
  tituloDrawer: 'Metodología y limitaciones',
  tituloEntenderZona: 'Entender esta zona',
  cerrar: 'Cerrar',
  // Versión resumida para lectura rápida; conserva método, fuentes y límites esenciales.
  secciones: (generado) => [
    {
      titulo: 'Qué muestra Habitancia',
      parrafos: [
        'Identifica zonas de la CDMX donde podría ser útil ampliar servicios para niñas, niños y '
        + 'adolescentes.',
      ],
    },
    {
      titulo: 'Cómo leer los resultados',
      parrafos: [
        'La oportunidad compara población y servicios entre zonas. Sirve para investigar dónde '
        + 'prestar atención; no es una recomendación automática de inversión.',
      ],
    },
    {
      titulo: 'Cómo se calcula',
      parrafos: [
        'Se compara la oferta con la población proyectada. Las zonas con menor cobertura relativa '
        + 'aparecen primero. Pesos y filtros ajustan el análisis, no los datos originales.',
      ],
    },
    {
      titulo: 'Fuentes',
      lista: [
        'Censos 2010 y 2020 y Marco Geoestadístico 2020 del INEGI.',
        'Proyecciones de población de CONAPO.',
        'DENUE del INEGI para educación, salud y comercio.',
        'Datos Abiertos CDMX para áreas verdes y espacio público.',
      ],
    },
    {
      titulo: 'Confiabilidad y límites',
      lista: [
        'Las proyecciones orientan; no son certezas.',
        'La oferta predice mejor la dirección que la magnitud del cambio.',
        '“Sin datos” no significa “sin necesidad”.',
        'El registro de un establecimiento no mide su capacidad ni calidad.',
        'Antes de invertir, se requiere investigación adicional de la zona.',
        interpolar('Datos generados el {generado}.', { generado }),
      ],
    },
  ],
};

// ---------------------------------------------------------------------------------------------
// §10.13 Comparar alcaldías
// ---------------------------------------------------------------------------------------------

const comparar = {
  titulo: 'Comparar alcaldías',
  boton: 'Comparar',
  seleccionA: 'Primera alcaldía',
  seleccionB: 'Segunda alcaldía',
  quitar: 'Dejar de comparar',
  nota: 'Usa la configuración activa y no elige una ganadora.',
};

// ---------------------------------------------------------------------------------------------
// §10.14 Iconos "?" (9 conceptos, texto de 3 partes: qué es / por qué importa / cómo interpretarlo)
// ---------------------------------------------------------------------------------------------

const ayuda = {
  abrir: (concepto) => interpolar('Ayuda: {concepto}', { concepto }),
  poblacionObjetivo: {
    queEs: 'Niñas, niños o adolescentes del rango elegido que viven en la zona.',
    porQueImporta: 'Permite comparar población y servicios.',
    comoInterpretar: 'El rango cambia la población analizada, no la calidad de la zona.',
  },
  oportunidad: {
    queEs: 'Compara la cobertura proyectada de cada zona con el resto de la CDMX.',
    porQueImporta: 'Ayuda a decidir qué zonas investigar primero.',
    comoInterpretar: 'Una oportunidad alta es una señal, no una recomendación de inversión.',
  },
  disponibilidad: {
    queEs: 'Compara los servicios actuales con la población de cada zona.',
    porQueImporta: 'Muestra dónde existe mayor cobertura actualmente.',
    comoInterpretar: 'Cobertura actual y oportunidad de expansión se consultan por separado.',
  },
  prioridades: {
    queEs: 'La importancia que asignas a cada rama, de 1 a 5.',
    porQueImporta: 'Define cómo se combinan las ramas.',
    comoInterpretar: 'Cambia el orden, no los datos originales.',
  },
  filtros: {
    queEs: 'Los servicios que se incluyen en cada rama.',
    porQueImporta: 'Enfocan el análisis en lo que te interesa.',
    comoInterpretar: 'Cambian la cobertura calculada, no los datos originales.',
  },
  riesgo: {
    queEs: 'La confianza mínima aceptada para mostrar un resultado.',
    porQueImporta: 'Oculta estimaciones menos firmes.',
    comoInterpretar: 'Filtra resultados; no cambia los cálculos.',
  },
  confianza: {
    queEs: 'Qué tan firme es el resultado ante distintos supuestos.',
    porQueImporta: 'Una señal con baja confianza requiere más cautela.',
    comoInterpretar: 'Alta: firme. Media: probable. Baja: insuficiente para concluir.',
  },
  horizonte: {
    queEs: 'El plazo del pronóstico: 1, 3 o 5 años.',
    porQueImporta: 'Los plazos largos acumulan más incertidumbre.',
    comoInterpretar: 'El horizonte cambia la magnitud proyectada.',
  },
  equivalenciaAgebZona: {
    queEs: 'Una zona corresponde a una AGEB, unidad geográfica del INEGI.',
    porQueImporta: 'Es la unidad que colorea el mapa y ordena el ranking.',
    comoInterpretar: 'Cada alcaldía agrupa varias zonas.',
  },
};

// ---------------------------------------------------------------------------------------------
// §10.4 Leyenda
// ---------------------------------------------------------------------------------------------

const leyenda = {
  encabezadoGeneral: (v) => interpolar('Leyenda · {vista} · {anio}', v),
  encabezadoAlcaldia: (v) => interpolar('Leyenda · {alcaldia} · {vista} · {anio}', v),
  confianzaBaja: (n) => interpolar('{n} con confianza baja en la demanda que alimenta el índice.', { n }),
  filtroActivo: (v) => interpolar('Mostrando {n} de {total} · Quitar filtro', v),
};

// ---------------------------------------------------------------------------------------------
// §10.1, §13 Mapa
// ---------------------------------------------------------------------------------------------

const mapa = {
  regionLabel: 'Mapa de la CDMX',
  resumenAria: (v) => interpolar(
    'Mapa de la CDMX, vista {vista}, a {h} año(s): {nAlta} con oportunidad alta, {nMedia} media, '
    + '{nBaja} baja. El ranking contiene el detalle.',
    v,
  ),
};

// ---------------------------------------------------------------------------------------------
// §14.2 Tooltips
// ---------------------------------------------------------------------------------------------

const tooltip = {
  vistaTercil: (v) => interpolar('{vista}: {simbolo} {tercil}', v),
  vecina: (nombre) => interpolar('Ir a {nombre}', { nombre }),
  ageb: (v) => interpolar('AGEB {cvegeo}', v),
  agebSinDatos: (motivo) => interpolar('Sin datos: {motivo}', { motivo }),
};

// ---------------------------------------------------------------------------------------------
// §14.4 Motivos de sin_datos
// ---------------------------------------------------------------------------------------------

const motivosSinDatosMapa = {
  rural: 'AGEB rural: el censo no publica datos de población infantil por AGEB rural.',
  suprimido_inegi: 'El INEGI no publica esta cifra para proteger la confidencialidad.',
  poblacion_menor_20: 'Hay menos de 20 niñas y niños: la cifra es demasiado pequeña para '
    + 'pronosticar.',
  sin_poligono: 'Esta clave no tiene correspondencia entre el mapa y el censo.',
  sin_censo: 'Esta clave no tiene correspondencia entre el mapa y el censo.',
  sin_establecimientos: 'No hay establecimientos registrados en ningún levantamiento, para esta '
    + 'rama y estos filtros.',
  rama_sin_dato: 'Esta rama no tiene información suficiente en esta zona.',
  contrato_v1_2: 'Este conjunto de datos no trae esta información (versión anterior del contrato).',
};

const AUSENTE = 'No hay estimación para esta unidad.';

const motivosSinDatos = {
  mapa: motivosSinDatosMapa,
  ausente: AUSENTE,
  /** Devuelve el texto en lenguaje claro para un código de motivo; si no hay código, "(ausente)". */
  obtener: (codigo) => (codigo && motivosSinDatosMapa[codigo]) || AUSENTE,
};

// ---------------------------------------------------------------------------------------------
// §13 Accesibilidad transversal (región viva global)
// ---------------------------------------------------------------------------------------------

const accesibilidad = {
  cargandoPronosticos: 'Cargando pronósticos…',
  anuncioVistaAlcaldia: (v) => interpolar('Vista de {alcaldia}: {n} zonas con datos.', v),
  anuncioVistaGeneral: 'Vista general de la CDMX.',
  anuncioHorizonte: (v) => interpolar('Horizonte: {h} años, a mediados de {anio}.', v),
  anuncioVistaMapa: (v) => interpolar('Vista de mapa: {vista}.', v),
  anuncioPoblacion: (v) => interpolar('Población objetivo: {poblacion}.', v),
  anuncioBusqueda: (v) => interpolar('Explorando: {busqueda}.', v),
  anuncioPeso: (v) => interpolar('{rama}: prioridad {peso} de 5.', v),
  anuncioFiltroRama: (v) => interpolar('Filtro de {rama} actualizado: {resumen}.', v),
  anuncioAgeb: (v) => interpolar('Zona {cvegeo}: oportunidad {tercil}.', v),
  anuncioFiltroLeyenda: (tercilActivo) => interpolar('Filtro: solo {tercil}.', { tercil: tercilActivo }),
  anuncioComparar: (v) => interpolar('Comparando {a} y {b}.', v),
};

// ---------------------------------------------------------------------------------------------
// §15 Estados de carga, error y vacío
// ---------------------------------------------------------------------------------------------

const estados = {
  reintentar: 'Reintentar',
  error: {
    mensaje: 'No pudimos cargar los datos. Revise su conexión e intente de nuevo.',
    detalle: (causa) => interpolar('(Detalle: {causa})', { causa }),
    causas: {
      sinConexion: 'sin conexión',
      archivoInvalido: 'el archivo no es válido',
      versionIncompatible: (v) => interpolar('versión de datos incompatible ({v})', { v }),
    },
  },
  vacio: {
    mensaje: (v) => interpolar(
      'En {alcaldia} no hay zonas con datos suficientes para esta selección.',
      v,
    ),
    prefijoMotivos: 'Motivos:',
  },
  incompletos: (n) => interpolar(
    'Faltan estimaciones para {n} unidades; se muestran como sin datos.',
    { n },
  ),
  ramaSinDato: 'Esta rama no tiene datos suficientes en esta zona; el resultado usa las demás.',
  todasSinDato: 'En esta zona no hay información suficiente en ninguna de las cuatro ramas.',
  cargandoAgeb: (alcaldiaNombre) => interpolar(
    'Cargando zonas de {alcaldia}…',
    { alcaldia: alcaldiaNombre },
  ),
};

// ---------------------------------------------------------------------------------------------
// Pie de página
// ---------------------------------------------------------------------------------------------

// ---------------------------------------------------------------------------------------------
// §10.15 Modo presentación
// ---------------------------------------------------------------------------------------------

const presentacion = {
  boton: 'Modo presentación',
  simbolo: '⤢',
  activar: 'Activar modo presentación',
  desactivar: 'Salir del modo presentación',
};

const pie = {
  fuentes: 'Fuentes: INEGI, CONAPO y Datos Abiertos CDMX.',
  datosGenerados: (fecha) => interpolar('Actualización: {fecha}', { fecha }),
  advertenciaSesgos: 'Consulta orientativa; valida antes de invertir.',
};

// ---------------------------------------------------------------------------------------------
// Objeto exportado y helper genérico `texto(ruta, variables)`
// ---------------------------------------------------------------------------------------------

export const textos = {
  producto,
  navegacion,
  buscadorAlcaldia,
  vista,
  busqueda,
  poblacion,
  horizonte,
  veredicto,
  tercil,
  confianza,
  rama,
  prioridades,
  filtros,
  riesgo,
  resumen,
  explicacion,
  ranking,
  ficha,
  graficas,
  confiabilidad,
  metodologia,
  comparar,
  ayuda,
  leyenda,
  mapa,
  tooltip,
  motivosSinDatos,
  accesibilidad,
  estados,
  presentacion,
  pie,
};

function resolverRuta(ruta) {
  return ruta.split('.').reduce((nodo, clave) => (nodo == null ? undefined : nodo[clave]), textos);
}

/**
 * Atajo genérico: `texto("horizonte.etiqueta")` o `texto("resumen.tituloGeneral", {poblacion, h})`.
 * Si el valor resuelto es función, la invoca con `variables`; si es cadena con `{marcadores}`, la
 * interpola; cualquier otro valor (número, array, objeto de subclaves) se devuelve tal cual.
 */
export function texto(ruta, variables) {
  const valor = resolverRuta(ruta);
  if (typeof valor === 'function') return valor(variables);
  if (typeof valor === 'string' && variables) return interpolar(valor, variables);
  return valor;
}
