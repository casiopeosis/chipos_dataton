// frontend/js/textos.js
// Fuente única de todas las cadenas de la interfaz (plans/frontend_specs.md §14, más las
// plantillas que §14 remite a §6.3-§6.5 y §7). Ningún otro módulo de frontend/ debe tener
// texto de cara a la persona usuaria escrito a mano: siempre se importa de aquí.
//
// Convenciones de este módulo:
// - Los valores "hoja" son cadenas fijas o funciones de interpolación `(variables) => cadena`.
//   Las funciones NO deciden qué plantilla usar (esa lógica vive en veredictos.js/titular.js,
//   §16 del plan); solo arman la frase con las variables que reciben.
// - Muchas etiquetas que en los wireframes aparecen en MAYÚSCULAS (--t-etiqueta, §4.5) se
//   guardan aquí en minúscula/mayúscula normal: la transformación a versalitas es de `base.css`
//   (`text-transform`), no de este módulo, para no acoplar texto y presentación.
// - `texto(ruta, variables)` es un atajo genérico: busca `ruta` (con puntos) dentro de `textos`
//   y, si es función, la invoca con `variables`; si es cadena con `{marcadores}`, interpola.
// - Siempre "alcaldía" y "AGEB"; nunca el sinónimo histórico previo a la reforma de 2016, ni
//   jerga técnica del modelo (CLAUDE.md §2).

/** Números en palabra para menores de 10, salvo que acompañen a "de las 16" (§6.3). */
const NUMEROS_EN_PALABRA = [
  'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve',
];

/**
 * Convierte un entero no negativo menor que 10 a su palabra en español; de lo contrario
 * devuelve el número tal cual (como cadena). Uso: frases donde el número no va pegado a
 * "de las 16 alcaldías" (§6.3).
 */
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
// §14.1 Etiquetas fijas, navegación y producto
// ---------------------------------------------------------------------------------------------

const producto = {
  nombre: 'Infancias CDMX',
  nombreLargo: 'Infancias CDMX — Pronóstico de demanda',
};

const navegacion = {
  raiz: 'CDMX',
  rutaAriaLabel: 'Ruta',
  volverGeneral: '← Todas las alcaldías',
  volverAlcaldia: (alcaldia) => interpolar('← Volver a {alcaldia}', { alcaldia }),
  explorar: 'Explorar alcaldía →',
  reencuadrar: 'Reencuadrar',
};

const metodologia = {
  enlaceTitular: 'Ver metodología ↗',
  enlaceCabecera: 'Metodología ↗',
  franja: 'Metodología y limitaciones ↓',
  tituloDrawer: 'Metodología y limitaciones',
  cerrar: 'Cerrar',
  // §14.6: texto íntegro del drawer, en el orden del wireframe 7. `generado` ya viene formateado
  // (p. ej. "18 sep 2026"; el formato es responsabilidad de formato.js).
  secciones: (generado) => [
    {
      titulo: 'Qué mide esta herramienta',
      parrafos: [
        'Pronostica si la población de 0 a 14 años de cada alcaldía y de cada AGEB urbana de la '
        + 'Ciudad de México subirá, se mantendrá o bajará a 1, 3 y 5 años. Esa población es la '
        + 'demanda potencial de servicios para infancias: guarderías, preescolares, primarias, '
        + 'secundarias y servicios de apoyo.',
      ],
    },
    {
      titulo: 'Demanda y oferta',
      parrafos: [
        'La demanda es el número de niñas y niños de 0 a 14 años que viven en cada zona. La oferta '
        + 'es el número de establecimientos dedicados principalmente a la infancia, registrados en '
        + 'el Directorio Estadístico Nacional de Unidades Económicas (DENUE) del INEGI. Son cosas '
        + 'distintas y se muestran en capas separadas. Que una baje no implica que la otra deba bajar.',
      ],
    },
    {
      titulo: 'Por qué de 0 a 14 años',
      parrafos: [
        'Todos los establecimientos dedicados principalmente a la infancia atienden edades dentro '
        + 'de ese rango. Las edades se suman sin ponderaciones.',
      ],
    },
    {
      titulo: 'De dónde vienen los datos',
      lista: [
        'Censos de Población y Vivienda 2010 y 2020 del INEGI, por AGEB urbana.',
        'Proyecciones de población por municipio del Consejo Nacional de Población (CONAPO).',
        'DENUE (INEGI), levantamientos de 2016, 2019 y 2024.',
        'Marco Geoestadístico 2020 del INEGI.',
      ],
    },
    {
      titulo: 'Cómo se calcula',
      parrafos: [
        'Para cada AGEB se mide cómo cambió su población infantil entre 2010 y 2020. En las AGEB '
        + 'pequeñas, ese cambio se acerca al de su alcaldía, porque con pocas personas una variación '
        + 'puede deberse al azar. La tendencia de cada alcaldía se ajusta a las proyecciones de '
        + 'CONAPO. Con miles de simulaciones se obtiene un rango probable para cada resultado.',
      ],
    },
    {
      titulo: 'Cómo se decide si algo sube, baja o se mantiene',
      lista: [
        'Un cambio menor a 1 % por año, en cualquier sentido, cuenta como "se mantiene".',
        'Se dice que algo sube o baja solo cuando la probabilidad de que el cambio supere ese '
        + 'umbral en ese sentido es de al menos 80 %.',
        'La confianza es alta si esa probabilidad es de 95 % o más y el resultado no depende de '
        + 'los supuestos. Es media si está entre 80 % y 95 %. Es baja en los demás casos, y '
        + 'también cuando hay muy pocas niñas y niños o un solo dato.',
      ],
    },
    {
      titulo: 'Por qué a 5 años hay más incertidumbre',
      parrafos: [
        'Solo hay dos censos con datos por AGEB. Todo pronóstico supone que las tendencias de '
        + '2010–2020 y las proyecciones de CONAPO siguen vigentes. Cuanto más lejano el horizonte, '
        + 'más amplio el rango probable. A 5 años, el resultado es una orientación, no una '
        + 'predicción precisa.',
      ],
    },
    {
      titulo: 'AGEB rurales y sin datos',
      parrafos: [
        'El censo no publica la población infantil por AGEB rural (22 en la ciudad, en Milpa Alta, '
        + 'Tlalpan y Xochimilco, entre otras), así que se muestran como "Sin datos". Tampoco se '
        + 'pronostican las AGEB donde el INEGI reserva la cifra o donde viven menos de 20 niñas y '
        + 'niños. Nunca se inventa un valor.',
      ],
    },
    {
      titulo: 'El levantamiento del DENUE de 2024',
      parrafos: [
        'Entre 2020 y 2023, el DENUE casi no se actualizó en campo. Cuando el INEGI volvió a '
        + 'recorrer la ciudad en 2024, registró de una sola vez los cierres acumulados en esos años, '
        + 'sobre todo de preescolares y guarderías privadas. Por eso la oferta se mide entre '
        + 'levantamientos y su confianza máxima es media.',
      ],
    },
    {
      titulo: 'Advertencias',
      lista: [
        'Estos pronósticos describen tendencias de población, no necesidades de servicio ni '
        + 'calidad de la atención.',
        'Una alcaldía puede tener AGEB que suben aunque en conjunto baje.',
        'Las cifras de CONAPO y del censo no coinciden exactamente. Por eso se usa la tasa de '
        + 'cambio de CONAPO y no su nivel.',
        interpolar('Datos generados el {generado}.', { generado }),
      ],
    },
  ],
};

// ---------------------------------------------------------------------------------------------
// Veredictos y confianza (§4.2, §7.1)
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

const confianza = {
  palabra: { alta: 'Alta', media: 'Media', baja: 'Baja' },
  simbolo: { alta: '●', media: '◐', baja: '○' },
  explicacion: {
    alta: 'el resultado se sostiene aun con supuestos distintos.',
    media: 'el sentido del cambio es probable, pero su tamaño es incierto.',
    baja: 'los datos no permiten afirmar el sentido del cambio con seguridad.',
  },
  // Recibe {nivel}, como el resto de plantillas que se llaman vía texto()/t() con un objeto de
  // variables (alcaldia.js, tabla.js): antes tomaba `nivel` como valor posicional, así que t()
  // le pasaba el objeto entero y el resultado era literalmente "confianza [object Object]".
  ariaLabel: (v) => interpolar('confianza {nivel}', v),
};

// ---------------------------------------------------------------------------------------------
// Capas (§9)
// ---------------------------------------------------------------------------------------------

const capa = {
  nombre: { demanda: 'Demanda', oferta: 'Oferta', brecha: 'Brecha' },
  // §9: aria-label del control segmentado de la cabecera (role="radiogroup").
  controlEtiqueta: 'Elegir capa',
  unidadBrecha: 'establecimientos por cada 1,000 niñas y niños de 0 a 14 años',
  confianzaMaximaOferta: 'Confianza máxima de esta capa: media.',
};

// ---------------------------------------------------------------------------------------------
// §8 Control de horizonte
// ---------------------------------------------------------------------------------------------

const horizonte = {
  etiqueta: 'Horizonte',
  opcion: (v) => interpolar('{h} años · {anio}', v),
  etiquetaAnios: (h) => interpolar('{h} años', { h }),
  ariaValuetext: (v) => interpolar('{h} años, a mediados de {anio}', v),
  // §8.1: nota bajo el slider, según el valor de h en años.
  nota: {
    3: 'Proyección a corto plazo.',
    5: 'El rango probable se amplía con el plazo.',
    7: 'A 7 años es una extrapolación de tendencias: úsela como orientación.',
  },
  // §8.5: capa oferta (o brecha) fuerza un solo horizonte disponible.
  deshabilitadoOferta: (v) => interpolar(
    'La oferta se pronostica solo a {h} años ({anio}): los levantamientos del DENUE no permiten '
    + 'proyectar más lejos.',
    v,
  ),
  // §8.6: degradación con el contrato v1.1 (un solo horizonte en el archivo).
  deshabilitadoUnico: (anio) => interpolar(
    'Este conjunto de datos trae un solo horizonte: mediados de {anio}.',
    { anio },
  ),
};

// ---------------------------------------------------------------------------------------------
// §6 Titular dinámico (plantillas; la selección de escenario la hace veredictos.js/titular.js)
// ---------------------------------------------------------------------------------------------

const titularDemandaGeneral = {
  baja: ({ h, nBaja, nSube }) => {
    const clausula = nSube > 0
      ? interpolar(' y subiría en {n}', { n: numeroEnPalabras(nSube) })
      : '; en ninguna subiría';
    return interpolar(
      'A {h} años, la población de 0 a 14 años —la demanda de servicios para infancias— bajaría '
      + 'en {nBaja} de las 16 alcaldías{clausula}.',
      { h, nBaja, clausula },
    );
  },
  sube: ({ h, nSube, nBaja }) => {
    const clausula = nBaja > 0
      ? interpolar(' y bajaría en {n}', { n: numeroEnPalabras(nBaja) })
      : '; en ninguna bajaría';
    return interpolar(
      'A {h} años, la población de 0 a 14 años —la demanda de servicios para infancias— subiría '
      + 'en {nSube} de las 16 alcaldías{clausula}.',
      { h, nSube, clausula },
    );
  },
  polarizado: (v) => interpolar(
    'A {h} años, la demanda de servicios para infancias iría en direcciones opuestas: subiría en '
    + '{nSube} alcaldías y bajaría en {nBaja}.',
    v,
  ),
  mantiene: (v) => interpolar(
    'A {h} años, la demanda de servicios para infancias se mantendría estable en {nMant} de las '
    + '16 alcaldías.',
    v,
  ),
  mixto: (v) => interpolar(
    'A {h} años, la demanda de servicios para infancias no muestra una dirección común: {nBaja} '
    + 'alcaldías bajarían, {nMant} se mantendrían y {nSube} subirían.',
    v,
  ),
  insuficiente: () => 'Aún no hay datos suficientes para pronosticar la demanda de servicios '
    + 'para infancias en la mayoría de las alcaldías.',
};

const titularOfertaGeneral = {
  baja: (v) => interpolar(
    'A {h} años, el número de establecimientos para infancias tendería a bajar en {nBaja} de las '
    + '16 alcaldías.',
    v,
  ),
  sube: (v) => interpolar(
    'A {h} años, el número de establecimientos para infancias tendería a subir en {nSube} de las '
    + '16 alcaldías.',
    v,
  ),
  polarizado: (v) => interpolar(
    'A {h} años, los establecimientos para infancias tenderían a subir en {nSube} alcaldías y a '
    + 'bajar en {nBaja}.',
    v,
  ),
  mantiene: (v) => interpolar(
    'A {h} años, el número de establecimientos para infancias se mantendría en {nMant} de las '
    + '16 alcaldías.',
    v,
  ),
  mixto: () => 'A {h} años, los establecimientos para infancias no muestran una tendencia común '
    + 'entre alcaldías.',
  insuficiente: () => 'No hay registros suficientes de establecimientos para pronosticar la '
    + 'oferta en la mayoría de las alcaldías.',
};

const titularAlcaldiaDemanda = {
  baja: (v) => interpolar(
    'En {alc}, la población de 0 a 14 años bajaría a {h} años en {nBaja} de sus {vA} AGEB '
    + '({pBaja} %).',
    v,
  ),
  sube: (v) => interpolar(
    'En {alc}, la población de 0 a 14 años subiría a {h} años en {nSube} de sus {vA} AGEB '
    + '({pSube} %).',
    v,
  ),
  polarizado: (v) => interpolar(
    'En {alc}, la demanda iría en direcciones opuestas: {nSube} AGEB subirían y {nBaja} bajarían '
    + 'a {h} años.',
    v,
  ),
  mantiene: (v) => interpolar(
    'En {alc}, la demanda se mantendría estable a {h} años en {nMant} de sus {vA} AGEB.',
    v,
  ),
  mixto: (v) => interpolar(
    'En {alc}, a {h} años, {nBaja} AGEB bajarían, {nMant} se mantendrían y {nSube} subirían.',
    v,
  ),
  insuficiente: (v) => interpolar(
    'En {alc} no hay datos suficientes para pronosticar la mayoría de sus AGEB.',
    v,
  ),
  sinDatosExtra: (nSin) => interpolar(
    '{nSin} AGEB no tienen datos suficientes.',
    { nSin },
  ),
};

const titularAlcaldiaOferta = {
  baja: (v) => interpolar(
    'En {alc}, el número de establecimientos para infancias tendería a bajar a {h} años en '
    + '{nBaja} de sus {vA} AGEB ({pBaja} %).',
    v,
  ),
  sube: (v) => interpolar(
    'En {alc}, el número de establecimientos para infancias tendería a subir a {h} años en '
    + '{nSube} de sus {vA} AGEB ({pSube} %).',
    v,
  ),
  polarizado: (v) => interpolar(
    'En {alc}, los establecimientos para infancias irían en direcciones opuestas: {nSube} AGEB '
    + 'tenderían a subir y {nBaja} a bajar, a {h} años.',
    v,
  ),
  mantiene: (v) => interpolar(
    'En {alc}, el número de establecimientos para infancias se mantendría estable a {h} años en '
    + '{nMant} de sus {vA} AGEB.',
    v,
  ),
  mixto: (v) => interpolar(
    'En {alc}, a {h} años, {nBaja} AGEB tenderían a bajar, {nMant} se mantendrían y {nSube} '
    + 'tenderían a subir.',
    v,
  ),
  insuficiente: (v) => interpolar(
    'En {alc} no hay registros suficientes de establecimientos para pronosticar la mayoría de '
    + 'sus AGEB.',
    v,
  ),
};

const titular = {
  demanda: { general: titularDemandaGeneral, alcaldia: titularAlcaldiaDemanda },
  oferta: { general: titularOfertaGeneral, alcaldia: titularAlcaldiaOferta },
  // §6.3, capa brecha: sin veredicto, una sola plantilla.
  brecha: (v) => interpolar(
    'Hay {min} a {max} establecimientos para infancias por cada 1,000 niñas y niños, según la '
    + 'alcaldía; la cifra más baja está en {alcaldiaMin}.',
    v,
  ),
  // §6.2: matiz por horizonte h = 7; reemplaza el "A {h} años" inicial de la frase.
  prefijoH7: 'De mantenerse las tendencias, a 7 años',
  // §6.2/§6.4: matiz por confianza baja dominante; sustituye el punto final de la frase.
  sufijoConfianzaBaja: ', aunque con certeza limitada en la mayoría de los casos.',
  subtitulo: {
    conAgregado: (v) => interpolar(
      '{capa} · MEDIADOS DE {anio} · CDMX {cambio} (ENTRE {lo} Y {hi} %)',
      v,
    ),
    sinAgregado: (v) => interpolar('{capa} · MEDIADOS DE {anio}', v),
    oferta: (v) => interpolar('OFERTA (ESTABLECIMIENTOS DENUE) · MEDIADOS DE {anio}', v),
    alcaldia: (v) => interpolar(
      'DEMANDA · MEDIADOS DE {anio} · {alcaldia} {cambio} (ENTRE {lo} Y {hi} %)',
      v,
    ),
    // Degradación no contemplada literalmente en el wireframe: si la alcaldía no trae su propio
    // registro agregado (p. ej. contrato incompleto), se omite el bloque "{ALC} {cambio} (...)"
    // en vez de mostrar cifras inventadas (CLAUDE.md: nunca un veredicto/cifra inventada).
    alcaldiaSinAgregado: (v) => interpolar('DEMANDA · MEDIADOS DE {anio} · {alcaldia}', v),
  },
  notaOferta: 'Confianza máxima: media. El levantamiento de 2024 registró de una vez cierres '
    + 'ocurridos entre 2020 y 2023.',
};

// ---------------------------------------------------------------------------------------------
// §7.1-§7.2 Tabla de predicciones
// ---------------------------------------------------------------------------------------------

const tabla = {
  caption: (v) => interpolar('Pronóstico por alcaldía, capa {capa}, a mediados de {anio}', v),
  encabezados: {
    alcaldia: 'Alcaldía',
    ageb: 'AGEB',
    veredicto: 'Veredicto',
    confianza: 'Conf.',
    // §7.5: el encabezado de cambio siempre nombra la capa.
    cambio: (capaActiva, anio) => (
      capaActiva === 'oferta'
        ? interpolar('Cambio en establecimientos a {anio}', { anio })
        : interpolar('Cambio en demanda a {anio}', { anio })
    ),
    // §9: la capa brecha reemplaza las columnas de cambio/veredicto.
    brecha: ['Alcaldía', 'Establecimientos por 1,000', 'Niñas y niños', 'Establecimientos'],
  },
  filaDetalle: {
    cambioEsperado: (v) => interpolar('Cambio esperado a mediados de {anio}: {cambio}', v),
    rangoProbable: (v) => interpolar('Rango probable (95 %): entre {lo} y {hi}', v),
    confianzaLinea: (nivel) => interpolar(
      'Confianza {palabra}: {explicacion}',
      { palabra: confianza.palabra[nivel], explicacion: confianza.explicacion[nivel] },
    ),
    nObs: {
      demanda: (n) => interpolar('Basado en {n} censos (2010 y 2020).', { n }),
      oferta: (n) => interpolar(
        'Basado en {n} levantamientos del DENUE (2016, 2019 y 2024).',
        { n },
      ),
    },
    distribucion: (v) => interpolar(
      '{nBaja} bajan · {nMant} se mantienen · {nSube} suben · {nSin} sin datos',
      v,
    ),
    distribucionCargando: 'Cargando distribución de AGEB…',
    distribucionSinAgeb: 'No se encontraron AGEB para esta alcaldía.',
    explorar: navegacion.explorar,
  },
  // §7.1: nombre accesible de los encabezados ordenables (botón dentro del `<th>`).
  ordenarPor: {
    alcaldia: 'Ordenar por alcaldía',
    cambio: 'Ordenar por cambio',
    confianza: 'Ordenar por confianza',
  },
};

// ---------------------------------------------------------------------------------------------
// §7.3 Vista de alcaldía
// ---------------------------------------------------------------------------------------------

const alcaldia = {
  buscador: {
    etiqueta: 'Buscar AGEB por clave',
    sinResultados: (v) => interpolar('Ninguna clave coincide con «{texto}».', v),
  },
  // Recibe {n} (se llama vía t() con un objeto, como alcaldia.js): antes tomaba `n` posicional.
  verTodos: (v) => interpolar('Ver los {n} AGEB ↓', v),
  caption: (v) => interpolar('AGEB de {alcaldia}, capa {capa}, a mediados de {anio}', v),
  ordenarPor: {
    clave: 'Ordenar por clave',
    cambio: 'Ordenar por cambio',
    confianza: 'Ordenar por confianza',
  },
  sinAgeb: 'No se encontraron AGEB para esta alcaldía.',
};

// ---------------------------------------------------------------------------------------------
// §7.4 Ficha de AGEB
// ---------------------------------------------------------------------------------------------

const ficha = {
  ubicacion: (v) => interpolar('{alcaldia} · {tipo}', v),
  tipoAgeb: { urbana: 'Urbana', rural: 'Rural' },
  cambioContexto: (v) => interpolar('a mediados de {anio}, frente a mediados de {anioBase}', v),
  tasaAnualLabel: 'Tasa anual',
  tasaAnualValor: (cambio) => interpolar('{cambio} por año', { cambio }),
  rangoLabel: 'Rango probable 95 %',
  rangoValor: (v) => interpolar('entre {lo} y {hi}', v),
  confianzaLabel: 'Confianza',
  confianzaValor: (nivel) => interpolar(
    '{simbolo} {palabra} — {explicacion}',
    {
      simbolo: confianza.simbolo[nivel],
      palabra: confianza.palabra[nivel],
      explicacion: confianza.explicacion[nivel],
    },
  ),
  observacionesLabel: 'Observaciones',
  nObs: {
    demanda: (n) => interpolar('{n} censos (2010 y 2020)', { n }),
    oferta: (n) => interpolar('{n} levantamientos del DENUE (2016, 2019 y 2024)', { n }),
  },
  tituloSerie: {
    demanda: 'Niñas y niños de 0 a 14 años',
    oferta: 'Establecimientos DENUE (alcance Principal)',
  },
  figcaption: (v) => interpolar(
    'En {anioA} había {valorA} niñas y niños de 0 a 14 años; en {anioB}, {valorB}. La proyección '
    + 'a mediados de {anioH} es {valorH} (rango probable entre {lo} y {hi}).',
    v,
  ),
  etiquetaHorizonte: (v) => interpolar('{anio}: {valor}', v),
  reglaHoy: (anio) => interpolar('Mediados de {anio}', { anio }),
  notaProyeccion: 'Proyección basada en los censos 2010 y 2020 y en las proyecciones de CONAPO.',
  sinSerie: 'La serie histórica de este AGEB no está disponible en este conjunto de datos.',
  confianzaMenorNota: 'La confianza es menor a 7 años que a 3.',
};

// ---------------------------------------------------------------------------------------------
// §10.4 Leyenda
// ---------------------------------------------------------------------------------------------

const leyenda = {
  encabezadoGeneral: (v) => interpolar('Leyenda · {capa} · {anio}', v),
  encabezadoAlcaldia: (v) => interpolar('Leyenda · {alcaldia} · {anio}', v),
  intensidad: 'Más intensidad = cambio anual mayor',
  confianzaBaja: (n) => interpolar('Confianza baja ({n})', { n }),
  filtroActivo: (v) => interpolar('Mostrando {n} de {total} · Quitar filtro', v),
};

// ---------------------------------------------------------------------------------------------
// §10.1, §13 Mapa
// ---------------------------------------------------------------------------------------------

const mapa = {
  regionLabel: 'Mapa de la CDMX',
  resumenAria: (v) => interpolar(
    'Mapa de la CDMX por alcaldía, capa {capa}, a mediados de {anio}: {nBaja} bajan, {nMant} se '
    + 'mantienen, {nSube} suben. La tabla contiene el detalle.',
    v,
  ),
};

// ---------------------------------------------------------------------------------------------
// §14.2 Tooltips
// ---------------------------------------------------------------------------------------------

const tooltip = {
  capaVeredicto: (v) => interpolar('{capa}: {simbolo} {veredicto}', v),
  vecina: (nombre) => interpolar('Ir a {nombre}', { nombre }),
  // Recibe {cvegeo} (se llama vía t() con un objeto, como tabla.js): antes tomaba `cvegeo` posicional.
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
  sin_establecimientos: 'No hay establecimientos registrados en ningún levantamiento.',
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
  anuncioVistaAlcaldia: (v) => interpolar('Vista de {alcaldia}: {n} AGEB con datos.', v),
  anuncioVistaGeneral: 'Vista general de la CDMX.',
  anuncioHorizonte: (v) => interpolar('Horizonte: {h} años, a mediados de {anio}.', v),
  detalleCapa: {
    demanda: 'población de 0 a 14 años',
    oferta: 'establecimientos DENUE',
    brecha: 'establecimientos por 1,000 niñas y niños',
  },
  anuncioCapa(capaActiva) {
    return interpolar('Capa: {capa}, {detalle}.', {
      capa: capaActiva,
      detalle: this.detalleCapa[capaActiva] || '',
    });
  },
  anuncioAgeb: (v) => interpolar('AGEB {cvegeo}: {veredicto}, {cambio}.', v),
  anuncioFiltro: (veredictoActivo) => interpolar('Filtro: solo {veredicto}.', { veredicto: veredictoActivo }),
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
      'En {alcaldia} no hay AGEB con datos suficientes para pronosticar la {capa}.',
      v,
    ),
    prefijoMotivos: 'Motivos:',
  },
  incompletos: (n) => interpolar(
    'Faltan estimaciones para {n} unidades; se muestran como sin datos.',
    { n },
  ),
  cargandoAgeb: (alcaldiaNombre) => interpolar(
    'Cargando AGEB de {alcaldia}…',
    { alcaldia: alcaldiaNombre },
  ),
};

// ---------------------------------------------------------------------------------------------
// Pie de página (§5.3)
// ---------------------------------------------------------------------------------------------

const pie = {
  fuentes: 'Fuentes: INEGI, Censos 2010 y 2020 · CONAPO · DENUE',
  datosGenerados: (fecha) => interpolar('Datos: {fecha}', { fecha }),
};

// ---------------------------------------------------------------------------------------------
// §11 Móvil y §10.9 Modo presentación
// ---------------------------------------------------------------------------------------------

const movil = {
  alturas: { baja: 'baja', media: 'media', alta: 'alta' },
  asaAriaLabel: (altura) => interpolar('Ajustar panel: altura {altura}', { altura }),
};

const presentacion = {
  boton: 'Modo presentación',
  simbolo: '⤢',
};

// ---------------------------------------------------------------------------------------------
// Objeto público y atajo genérico `texto(ruta, variables)`
// ---------------------------------------------------------------------------------------------

export const textos = {
  producto,
  navegacion,
  metodologia,
  veredicto,
  confianza,
  capa,
  horizonte,
  titular,
  tabla,
  alcaldia,
  ficha,
  leyenda,
  mapa,
  tooltip,
  motivosSinDatos,
  accesibilidad,
  estados,
  pie,
  movil,
  presentacion,
};

/**
 * Atajo genérico: busca `ruta` ("titular.demanda.general.baja", "estados.reintentar", …) dentro
 * de `textos` y, si el valor es función, la invoca con `variables`; si es cadena, la interpola.
 * No decide qué plantilla corresponde: eso lo resuelve quien llama (p. ej. veredictos.js).
 */
export function texto(ruta, variables) {
  const nodo = ruta.split('.').reduce(
    (actual, clave) => (actual == null ? undefined : actual[clave]),
    textos,
  );
  if (typeof nodo === 'function') {
    return nodo(variables);
  }
  if (typeof nodo === 'string') {
    return interpolar(nodo, variables);
  }
  return nodo;
}
