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
    oportunidad: 'Oportunidad de expansión',
    disponibilidad: 'Disponibilidad para familias',
  },
  controlEtiqueta: '¿Qué quieres explorar?',
  ayuda: {
    oportunidad: 'Zonas donde la oferta actual y proyectada cubre relativamente poco frente a la '
      + 'población objetivo -- posibles prioridades de expansión.',
    disponibilidad: 'Zonas donde ya existe relativamente más oferta disponible para las familias '
      + 'que viven ahí hoy.',
  },
};

// ---------------------------------------------------------------------------------------------
// §5.3 Población objetivo (6 segmentos)
// ---------------------------------------------------------------------------------------------

const poblacion = {
  controlEtiqueta: '¿Qué población objetivo quieres explorar?',
  nombre: {
    todas: '0 a 17 años (todas)',
    primera_infancia: 'Primera infancia · 0 a 2 años',
    preescolar: 'Preescolar · 3 a 5 años',
    primaria: 'Primaria · 6 a 11 años',
    secundaria: 'Secundaria · 12 a 14 años',
    adolescencia: 'Adolescencia · 15 a 17 años',
  },
  notaAdolescencia: 'Este rango se apoya en menos establecimientos con datos (categoría '
    + '"Complementario" del DENUE): su confianza máxima es media.',
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
    3: 'Horizonte de referencia: el más equilibrado entre certeza y utilidad para planear.',
    5: 'El rango probable se amplía con el plazo: úselo como orientación, no como cifra exacta.',
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
  titulo: '¿Qué tan prioritaria es cada rama para ti?',
  circuloAriaLabel: (v) => interpolar('{rama}: prioridad {peso} de 5', v),
  restablecer: 'Restablecer prioridades',
  ayuda: 'Los círculos indican qué tan importante es cada rama para tu búsqueda (1 a 5). No '
    + 'cambian los datos originales: solo reordenan el ranking y el índice compuesto del mapa.',
};

const filtros = {
  restablecer: 'Restablecer filtros',
  resumenActivo: (texto) => texto, // ya viene armado por filtros.js con nombres de textos.js.
  todos: 'Todos',
  ayuda: 'Los filtros deciden qué establecimientos o espacios cuentan como oferta de esa rama. No '
    + 'cambian los datos originales, solo qué se suma.',
  educacion: {
    pregunta: '¿Qué servicios de educación y cultura quieres considerar?',
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
    ayuda: 'Estos filtros indican qué tipos de servicios educativos o culturales quieres incluir '
      + 'en el análisis de esta rama.',
  },
  salud: {
    pregunta: '¿Qué instalaciones de salud quieres considerar?',
    nivel: {
      clinicas: 'Clínicas o consultorios',
      hospitales: 'Hospitales',
      salud_mental: 'Salud mental o psicológica',
      farmacias: 'Farmacias',
    },
    ayuda: 'Habitancia utiliza únicamente los tipos de instalaciones que selecciones para calcular '
      + 'la disponibilidad de servicios de salud.',
  },
  comercio: {
    pregunta: '¿Qué comercios quieres considerar?',
    nivel: {
      supermercados_minisupers: 'Supermercados y minisúpers',
      abarrotes: 'Abarrotes',
      frutas_verduras: 'Frutas y verduras',
      carnes_otros_alimentos: 'Carnes y otros alimentos',
      farmacias: 'Farmacias',
    },
    ayuda: 'Este filtro permite decidir qué tipos de comercios cotidianos deben considerarse al '
      + 'analizar la disponibilidad de productos de primera necesidad.',
  },
  verde: {
    pregunta: '¿Qué tipo de espacio quieres considerar?',
    nivel: {
      cobertura_verde: 'Cobertura verde',
      areas_recreativas: 'Áreas recreativas',
      espacios_publicos: 'Espacios públicos',
    },
    ayuda: 'No toda superficie verde funciona como espacio recreativo. Este filtro permite '
      + 'diferenciar entre cobertura verde general y espacios que pueden tener una función de '
      + 'convivencia o recreación.',
  },
  sector: { todos: 'Todos', publico: 'Público', privado: 'Privado' },
};

const riesgo = {
  etiqueta: 'Nivel de riesgo aceptable',
  ayuda: 'Mueve el umbral para mostrar solo zonas cuya demanda tiene, al menos, esta confianza de '
    + 'pronóstico. No cambia los datos, solo filtra el ranking.',
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
  ayuda: 'Estos círculos no se editan: muestran, para cada rama, qué tan fuerte es la señal de '
    + 'oportunidad o disponibilidad detrás del resultado combinado.',
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
  ubicacion: (v) => interpolar('{alcaldia} · {tipo}', v),
  tipoAgeb: { urbana: 'Urbana', rural: 'Rural' },
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

// ---------------------------------------------------------------------------------------------
// §10.6 Franja lateral y drawer "Entender esta zona / Metodología"
// ---------------------------------------------------------------------------------------------

const metodologia = {
  enlaceCabecera: 'Metodología ↗',
  franja: 'Metodología y limitaciones ↓',
  tituloDrawer: 'Metodología y limitaciones',
  tituloEntenderZona: 'Entender esta zona',
  cerrar: 'Cerrar',
  // §14.6, texto íntegro del drawer, en el orden del spec.
  secciones: (generado) => [
    {
      titulo: 'Qué mide Habitancia',
      parrafos: [
        'Identifica zonas de la Ciudad de México donde, de acuerdo con la evolución de la '
        + 'población infantil y adolescente y la disponibilidad de servicios en cuatro ramas '
        + '(educación y cultura, salud, comercio, áreas verdes y espacio público), podría existir '
        + 'una mayor oportunidad relativa de ampliar o fortalecer infraestructura para infancias.',
      ],
    },
    {
      titulo: 'Población objetivo y oferta',
      parrafos: [
        'La población objetivo es el número de niñas, niños o adolescentes del rango de edad '
        + 'elegido que viven en cada zona. La oferta de cada rama es el número de establecimientos '
        + 'o espacios de ese tipo registrados en fuentes oficiales. Son cosas distintas: que la '
        + 'población baje no implica que la oferta deba bajar, y viceversa.',
      ],
    },
    {
      titulo: 'Oportunidad relativa, no una certeza',
      parrafos: [
        'Indica qué tan prioritaria aparece una zona frente a otras, bajo los criterios que '
        + 'elegiste -- no que sea obligatorio abrir un negocio ahí, ni que exista una necesidad de '
        + 'mercado comprobada, ni que el modelo esté recomendando una inversión.',
      ],
    },
    {
      titulo: 'De dónde vienen los datos',
      lista: [
        'Censos de Población y Vivienda 2010 y 2020 del INEGI, por AGEB urbana.',
        'Proyecciones de población por municipio del Consejo Nacional de Población (CONAPO).',
        'DENUE (INEGI): educación, salud y comercio, varios levantamientos entre 2016 y 2026.',
        'Áreas verdes y espacio público: Datos Abiertos de la Ciudad de México.',
        'Marco Geoestadístico 2020 del INEGI.',
      ],
    },
    {
      titulo: 'Cómo se decide si una zona tiene mayor oportunidad relativa',
      parrafos: [
        'Para cada rama se compara la oferta proyectada con la población objetivo proyectada, y se '
        + 'ordena esa relación entre todas las zonas de la CDMX: las zonas con menor cobertura '
        + 'relativa quedan arriba del ranking. Los pesos que elegiste combinan las cuatro ramas en '
        + 'un solo orden; los filtros deciden qué establecimientos cuentan en cada rama. Ninguno de '
        + 'los dos cambia los datos originales.',
      ],
    },
    {
      titulo: 'Qué tan bien acertó el modelo en el pasado',
      parrafos: [
        'Se probó el método comparando lo que habría predicho en el pasado contra lo que realmente '
        + 'ocurrió después, y contra la opción de "suponer que nada cambia". La demanda superó esa '
        + 'comparación; la oferta acierta mejor la dirección del cambio que su magnitud exacta, '
        + 'sobre todo tras el levantamiento DENUE de 2024 (ver más abajo). El detalle completo está '
        + 'en docs/backtest.md del repositorio.',
      ],
    },
    {
      titulo: 'AGEB rurales y sin datos',
      parrafos: [
        'El censo no publica la población infantil por AGEB rural, así que se muestran como "Sin '
        + 'datos". Nunca se inventa un valor donde falta información -- y la ausencia de datos '
        + 'nunca significa ausencia de necesidad.',
      ],
    },
    {
      titulo: 'El levantamiento del DENUE de 2024',
      parrafos: [
        'Entre 2020 y 2023 el DENUE casi no se actualizó en campo; al volver en 2024 registró de '
        + 'golpe varios cierres acumulados en esos años, sobre todo en preescolares y guarderías '
        + 'privadas. Por eso la rama de educación tiene su confianza máxima limitada. Se trata como '
        + 'una hipótesis razonable, no como un hecho comprobado.',
      ],
    },
    {
      titulo: 'Advertencias',
      lista: [
        'Las proyecciones son estimaciones condicionadas a los datos y escenarios usados, no '
        + 'certezas.',
        'Una asociación histórica no implica causalidad.',
        'La ausencia de datos no equivale a ausencia de necesidad.',
        'Un establecimiento registrado no mide su capacidad, calidad ni matrícula.',
        'Los datos disponibles no cubren igual todas las zonas; usar esta herramienta para decidir '
        + 'dónde invertir o vivir sin considerar otros factores (seguridad, vivienda, movilidad, '
        + 'precios) podría reforzar exclusión existente en vez de reducirla.',
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
  nota: 'La comparación conserva la población objetivo, el horizonte, la búsqueda, los pesos y '
    + 'los filtros activos. No declara una ganadora.',
};

// ---------------------------------------------------------------------------------------------
// §10.14 Iconos "?" (9 conceptos, texto de 3 partes: qué es / por qué importa / cómo interpretarlo)
// ---------------------------------------------------------------------------------------------

const ayuda = {
  abrir: (concepto) => interpolar('Ayuda: {concepto}', { concepto }),
  poblacionObjetivo: {
    queEs: 'El número de niñas, niños o adolescentes del rango de edad elegido que viven en la zona.',
    porQueImporta: 'Es el punto de partida: sin población objetivo no hay demanda que comparar '
      + 'contra la oferta.',
    comoInterpretar: 'Un rango con más población no es "mejor" ni "peor": solo cambia a quién '
      + 'describe el resto de la información.',
  },
  oportunidad: {
    queEs: 'Un ranking relativo de qué tan poca oferta proyectada hay frente a la población '
      + 'objetivo proyectada, comparado con el resto de la CDMX.',
    porQueImporta: 'Ayuda a priorizar dónde explorar primero, entre cientos de zonas.',
    comoInterpretar: 'Alta oportunidad no es una recomendación de inversión: es una señal relativa '
      + 'para seguir explorando.',
  },
  disponibilidad: {
    queEs: 'Un ranking relativo de qué tanta oferta ya existe hoy frente a la población objetivo '
      + 'de la zona.',
    porQueImporta: 'Es la vista útil para familias que buscan dónde ya hay servicios.',
    comoInterpretar: 'Nunca se combina con oportunidad: una zona puede representar una oportunidad '
      + 'de expansión y, al mismo tiempo, tener baja disponibilidad actual.',
  },
  prioridades: {
    queEs: 'Un peso de 1 a 5 por rama que decides tú.',
    porQueImporta: 'Cambia cómo se combinan las cuatro ramas en un solo orden.',
    comoInterpretar: 'No altera los datos originales de ninguna rama, solo el orden final.',
  },
  filtros: {
    queEs: 'Qué tipos de establecimientos o espacios cuentan como oferta de cada rama.',
    porQueImporta: 'Permite enfocar el análisis en el tipo de servicio que te interesa.',
    comoInterpretar: 'Cambiar un filtro puede cambiar la cobertura calculada, no los datos '
      + 'publicados originalmente.',
  },
  riesgo: {
    queEs: 'Un umbral sobre la confianza del pronóstico de demanda.',
    porQueImporta: 'Permite excluir zonas cuyo pronóstico es poco confiable.',
    comoInterpretar: 'Solo filtra qué se muestra; no cambia el cálculo de ninguna zona.',
  },
  confianza: {
    queEs: 'Qué tan firme es el resultado frente a distintos supuestos del modelo.',
    porQueImporta: 'Una oportunidad "alta" con confianza baja merece más cautela que una con '
      + 'confianza alta.',
    comoInterpretar: 'Alta: se sostiene con supuestos distintos. Media: el sentido es probable, el '
      + 'tamaño es incierto. Baja: los datos no alcanzan para afirmar el sentido del cambio.',
  },
  horizonte: {
    queEs: 'El plazo del pronóstico: 1, 3 o 5 años desde mediados de 2026.',
    porQueImporta: 'Entre más lejano el horizonte, más incertidumbre acumula la proyección.',
    comoInterpretar: 'El veredicto y la confianza no cambian entre horizontes: solo cambia la '
      + 'magnitud proyectada.',
  },
  equivalenciaAgebZona: {
    queEs: '"Zona" es el nombre que usa Habitancia para una AGEB (Área Geoestadística Básica, la '
      + 'unidad de conteo del INEGI).',
    porQueImporta: 'Es la unidad mínima que colorea el mapa y ordena el ranking.',
    comoInterpretar: 'La alcaldía agrupa muchas zonas; el color y el ranking siempre se calculan '
      + 'por zona, nunca solo por alcaldía.',
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
  fuentes: 'Fuentes: INEGI, CONAPO, DENUE, Datos Abiertos CDMX',
  datosGenerados: (fecha) => interpolar('Datos: {fecha}', { fecha }),
  advertenciaSesgos: 'Habitancia mide oportunidad relativa y disponibilidad relativa, no '
    + 'recomienda dónde vivir ni garantiza éxito comercial. Los datos disponibles no cubren igual '
    + 'todas las zonas.',
};

// ---------------------------------------------------------------------------------------------
// Objeto exportado y helper genérico `texto(ruta, variables)`
// ---------------------------------------------------------------------------------------------

export const textos = {
  producto,
  navegacion,
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
