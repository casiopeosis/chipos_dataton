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
  volverGeneral: '← Ver todas las alcaldías',
  volverAlcaldia: (alcaldia) => interpolar('← Volver a {alcaldia}', { alcaldia }),
  explorar: 'Ver esta alcaldía →',
  reencuadrar: 'Volver a centrar',
  entenderZona: 'Ver más de esta zona →',
};

// ---------------------------------------------------------------------------------------------
// §5.2 Buscador de alcaldía (siempre visible)
// ---------------------------------------------------------------------------------------------

const buscadorAlcaldia = {
  etiqueta: 'Toca una alcaldía en el mapa o escribe su nombre aquí:',
  sinResultados: (v) => interpolar('No encontramos «{texto}». Revisa cómo lo escribiste.', v),
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
    oportunidad: '¿Dónde hacen falta más servicios?',
    disponibilidad: '¿Dónde ya hay más servicios?',
  },
  controlEtiqueta: '¿Qué quieres buscar?',
  ayuda: {
    oportunidad: 'Zonas donde faltan servicios para la cantidad de niñas, niños y adolescentes '
      + 'que viven ahí. Aquí podría convenir abrir o ampliar algo.\n', 
    disponibilidad: 'Zonas donde hay suficientes servicios para las familias que hoy viven ahí.',
  },
};

// ---------------------------------------------------------------------------------------------
// §5.3 Población objetivo (6 segmentos)
// ---------------------------------------------------------------------------------------------

const poblacion = {
  controlEtiqueta: '¿De qué edad son los niños o adolescentes de interés?',
  nombre: {
    todas: 'Todas las edades (0-17 años)',
    primera_infancia: 'Bebés y niños pequeños (0-2 años)',
    preescolar: 'Preescolar (3-5 años)',
    primaria: 'Primaria (6-11 años)',
    secundaria: 'Secundaria (12-14 años)',
    adolescencia: 'Adolescentes (15-17 años)',
  },
  notaAdolescencia: '',
};

// ---------------------------------------------------------------------------------------------
// §8 Control de horizonte
// ---------------------------------------------------------------------------------------------

const horizonte = {
  etiqueta: '¿cuántos años hacia el futuro?',
  opcion: (v) => interpolar('{h} año(s) · {anio}', v),
  etiquetaAnios: (h) => interpolar('{h} año(s)', { h }),
  ariaValuetext: (v) => interpolar('{h} años, a mediados de {anio}', v),
  nota: {
    1: 'La opción más cercana y más segura de acertar.',
    3: 'Un buen punto medio: suficiente tiempo para planear, sin adivinar demasiado.',
    5: 'A más plazo, más incertidumbre. Tómalo como una idea general, no como una cifra exacta.',
  },
  // Ramas con proyección (educación/salud/comercio) solo reportan h1/h3 -- verde ninguno.
  deshabilitadoRama: (v) => interpolar(
    'Para esta rama solo podemos calcular hasta {h} año(s) ({anio}): no hay suficiente '
    + 'información para ir más lejos.',
    v,
  ),
  sinProyeccion: 'Esta rama solo muestra cómo está hoy: no podemos calcular a futuro.',
  deshabilitadoUnico: (anio) => interpolar(
    'Estos datos solo tienen un momento disponible: mediados de {anio}.',
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
    alta: 'este resultado es bastante seguro.',
    media: 'es probable, pero no podemos decir con exactitud qué tanto.',
    baja: 'todavía no hay suficiente información para estar seguros.',
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
  titulo: '¿Qué es más importante para ti?',
  circuloAriaLabel: (v) => interpolar('{rama}: prioridad {peso} de 5', v),
  restablecer: 'Empezar de nuevo',
  ayuda: 'Marca más círculos en lo que más te importa (del 1 al 5). Esto no cambia la '
    + 'información: solo cambia el orden en que se muestran los resultados.',
};

const filtros = {
  restablecer: 'Quitar filtros',
  resumenActivo: (texto) => texto, // ya viene armado por filtros.js con nombres de textos.js.
  todos: 'Todos',
  ayuda: 'Elige qué tipo de lugares quieres contar en esta rama. Esto no cambia la información, '
    + 'solo qué se toma en cuenta.',
  educacion: {
    pregunta: '¿Qué lugares de educación y culturales considerarás?',
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
    ayuda: 'Elige qué tipo de escuelas o espacios culturales quieres incluir en esta búsqueda.',
  },
  salud: {
    pregunta: '¿Qué establecimientos de salud considerarás?',
    nivel: {
      clinicas: 'Clínicas o consultorios',
      hospitales: 'Hospitales',
      salud_mental: 'Salud mental o psicológica',
      farmacias: 'Farmacias',
    },
    ayuda: 'Solo se cuentan los tipos de lugares que marques aquí.',
  },
  comercio: {
    pregunta: '¿Qué tipo de comercios quieres tomar en cuenta?',
    primeraNecesidad: 'Tiendas de productos básicos',
    nivel: {
      supermercados_minisupers: 'Supermercados y minisúpers',
      abarrotes: 'Abarrotes',
      frutas_verduras: 'Frutas y verduras',
      carnes_otros_alimentos: 'Carnes y otros alimentos',
      farmacias: 'Farmacias',
    },
    ayuda: 'Elige qué tipo de tiendas de todos los días quieres tomar en cuenta.',
  },
  verde: {
    pregunta: '¿Qué tipo de espacios quieres tomar en cuenta?',
    nivel: {
      cobertura_verde: 'Áreas verdes en general',
      areas_recreativas: 'Áreas recreativas',
      espacios_publicos: 'Espacios públicos',
    },
    ayuda: 'No todo lo verde sirve para jugar o convivir. Aquí puedes diferenciar entre áreas verdes '
      + 'en general y espacios pensados para reunirse o recrearse.',
  },
  sector: { todos: 'Todos', publico: 'Público', privado: 'Privado' },
  sectorEtiqueta: 'Sector',
};

const riesgo = {
  etiqueta: '¿Qué tan seguros deben estar los resultados que ves?',
  ayuda: 'Mueve esto para ocultar zonas donde el pronóstico es poco confiable. No cambia la '
    + 'información: solo qué se muestra en la lista.',
};

// ---------------------------------------------------------------------------------------------
// §6 Resumen estructurado Nivel 1
// ---------------------------------------------------------------------------------------------

const resumen = {
  tituloGeneral: (v) => interpolar('CDMX · {poblacion} · {h} año(s)', v),
  tituloAlcaldia: (v) => interpolar('{alcaldia} · {poblacion} · {h} año(s)', v),
  campo: {
    poblacionObjetivo: 'Población',
    horizonte: 'A futuro',
    oportunidad: 'Qué tanto hace falta',
    disponibilidad: 'Qué tanto ya hay',
    confianza: 'Qué tan seguro es esto',
    ramasIncidencia: 'Lo que más pesó en este resultado',
  },
  sinRamas: 'No hay suficiente información en esta zona.',
};

// ---------------------------------------------------------------------------------------------
// §6.4 Motivos principales del resultado / §10.7 explicación por rama
// ---------------------------------------------------------------------------------------------

const explicacion = {
  titulo: '¿Por qué salió este resultado?',
  circuloAriaLabel: (v) => interpolar('{rama}: señal {valor} de 5', v),
  ayuda: 'Estos círculos no se pueden mover: solo muestran qué tanto pesó cada rama en el '
    + 'resultado final.',
  peso: (peso) => interpolar('Peso {peso}/5', { peso }),
  contribucion: (pct) => interpolar('{pct}% del resultado', { pct }),
};

// ---------------------------------------------------------------------------------------------
// §7 Ranking por AGEB
// ---------------------------------------------------------------------------------------------

const ranking = {
  tituloGeneral: 'Lista de zonas · CDMX',
  tituloAlcaldia: (alcaldia) => interpolar('Lista de zonas · {alcaldia}', { alcaldia }),
  columnas: {
    zona: 'Zona',
    alcaldia: 'Alcaldía',
    oportunidad: 'Hace falta',
    disponibilidad: 'Ya hay',
    poblacion: 'Población',
    confianza: 'Qué tan seguro',
    ramaPrincipal: 'Lo más importante',
  },
  detalle: {
    percentil: (v) => interpolar('Más alta que el {percentil}% de las zonas de la CDMX', v),
    ramas: 'Por tema',
  },
  ordenarPor: {
    oportunidad: 'Ordenar por lo que hace falta',
    disponibilidad: 'Ordenar por lo que ya hay',
    alcaldia: 'Ordenar por alcaldía',
    confianza: 'Ordenar por qué tan seguro es',
  },
  verMas: (n) => interpolar('Ver más ({n})', { n }),
  topN: (n) => interpolar('Mostrando las {n} zonas con más prioridad', { n }),
  buscador: {
    etiqueta: 'Busca una zona por su clave',
    sinResultados: (v) => interpolar('No encontramos «{texto}».', v),
  },
  verTodos: (v) => interpolar('Ver las {n} zonas ↓', v),
  sinAgeb: 'No encontramos zonas para esta alcaldía.',
};

// ---------------------------------------------------------------------------------------------
// §7.4 Ficha de zona (AGEB)
// ---------------------------------------------------------------------------------------------

const ficha = {
  // "{tipo}" (urbana/rural, §7.4 de la versión anterior) se retiró: el contrato no trae un
  // indicador urbano/rural fuera del motivo "rural" de `motivosSinDatos` (solo aparece cuando la
  // zona además es sin_datos) -- no hay una columna que lo dé siempre, así que la ubicación usa
  // la clave AGEB en su lugar, dato que sí siempre existe (CLAUDE.md: no inventar datos).
  ubicacion: (v) => interpolar('{alcaldia} · Zona {cvegeo}', v),
  oportunidadLabel: 'Qué tanto hace falta',
  disponibilidadLabel: 'Qué tanto ya hay',
  confianzaLabel: 'Qué tan seguro es esto',
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
    titulo: 'Cuántos niños y adolescentes hay, antes y después',
    figcaption: (v) => interpolar(
      'En {anioA} había {valorA}; en {anioB}, {valorB}. Para mediados de {anioH} calculamos '
      + '{valorH} (entre {lo} y {hi}, según cómo se comporten las cosas).',
      v,
    ),
  },
  servicios: {
    titulo: (rama) => interpolar('{rama}: antes y después', { rama }),
    sinProyeccion: (rama) => interpolar(
      'De {rama} solo mostramos cómo está hoy: no podemos calcular a futuro.',
      { rama },
    ),
  },
  cobertura: {
    titulo: 'Comparado con el resto de la CDMX',
    referenciaCdmx: 'Promedio de la CDMX',
  },
  sinDatos: 'No hay suficiente información para mostrar esta gráfica.',
};

// Nivel 2 de zona (§10.6): "¿Qué tan confiable es la estimación?" -- cifras reales de
// docs/backtest.md (F-7 de correccion/avance_plan.md), citadas aquí en vez de recalculadas en
// cliente. Se actualizan a mano si se corre `make backtest` con datos distintos.
const confiabilidad = {
  titulo: '¿Qué tan confiable es esto?',
  parrafo:
    'Probamos el método con datos del pasado, como si fuera un examen: para calcular cuántos '
    + 'niños y niñas hay, acertó mejor que simplemente suponer "todo sigue igual". Para calcular '
    + 'cuántos servicios hay, acierta si van a subir o bajar, pero se le dificulta más acertar '
    + 'exactamente cuánto. Por eso, en los resultados sobre servicios, nunca vas a ver el nivel '
    + 'de seguridad más alto. Si quieres los números exactos de esta prueba, están en '
    + 'docs/backtest.md.',
};

// ---------------------------------------------------------------------------------------------
// §10.6 Franja lateral y drawer "Entender esta zona / Metodología"
// ---------------------------------------------------------------------------------------------

const metodologia = {
  enlaceCabecera: 'Cómo funciona ↗',
  franja: 'Cómo funciona y qué límites tiene ↓',
  tituloDrawer: 'Cómo funciona y qué límites tiene',
  tituloEntenderZona: 'Más sobre esta zona',
  cerrar: 'Cerrar',
  // §14.6, texto íntegro del drawer, en el orden del spec.
  secciones: (generado) => [
    {
      titulo: 'Qué hace Habitancia',
      parrafos: [
        'Te muestra zonas de la Ciudad de México donde, según cuántos niños, niñas y '
        + 'adolescentes viven ahí y qué tantos servicios hay (escuelas, salud, tiendas, áreas '
        + 'verdes), podría hacer falta más infraestructura para ellos.',
      ],
    },
    {
      titulo: 'Dos cosas distintas: cuántos niños hay, y cuántos servicios hay',
      parrafos: [
        'Una cosa es cuántas niñas, niños o adolescentes de la edad que elegiste viven en una '
        + 'zona. Otra cosa, muy distinta, es cuántas escuelas, clínicas, tiendas o parques hay '
        + 'ahí. Que baje el número de niños no significa que deban cerrar servicios, y al revés.',
      ],
    },
    {
      titulo: 'Esto es una comparación, no una certeza',
      parrafos: [
        'Cuando decimos que una zona "hace más falta" que otra, es una comparación entre zonas '
        + 'con los criterios que tú elegiste. No significa que ahí sí o sí deba abrirse un '
        + 'negocio, ni que haya un mercado garantizado, ni que Habitancia te esté diciendo qué '
        + 'hacer.',
      ],
    },
    {
      titulo: 'De dónde sacamos la información',
      lista: [
        'Censos de Población y Vivienda 2010 y 2020 (INEGI).',
        'Proyecciones de población a futuro por alcaldía (CONAPO).',
        'Directorio de escuelas, clínicas y comercios (DENUE, INEGI), actualizado varias veces '
        + 'entre 2016 y 2026.',
        'Áreas verdes y espacio público: Datos Abiertos de la Ciudad de México.',
        'Mapas de zonas del INEGI (2020).',
      ],
    },
    {
      titulo: 'Cómo decidimos qué zona hace más falta',
      parrafos: [
        'En cada tema (escuelas, salud, comercio, áreas verdes) comparamos cuántos servicios hay '
        + 'contra cuántos niños viven ahí, y ordenamos todas las zonas de la CDMX de esa manera: '
        + 'las que tienen menos servicios para su población quedan primero. Lo que marcaste como '
        + 'más importante y los filtros que elegiste cambian el orden de la lista, pero nunca '
        + 'cambian la información original.',
      ],
    },
    {
      titulo: 'Qué tan bien le atinamos en el pasado',
      parrafos: [
        'Probamos el método con datos viejos, como un examen: le preguntamos qué habría '
        + 'pronosticado antes y lo comparamos con lo que pasó de verdad. Para calcular cuántos '
        + 'niños hay, le fue mejor que simplemente suponer "todo sigue igual". Para calcular '
        + 'cuántos servicios hay, acierta casi siempre si van a subir o bajar, pero le cuesta más '
        + 'trabajo acertar la cantidad exacta -- sobre todo por lo que pasó en 2024 (ver abajo). '
        + 'Por eso los resultados sobre servicios nunca muestran el nivel de seguridad más alto. '
        + 'Los números completos de esta prueba están en docs/backtest.md, si te interesan.',
      ],
    },
    {
      titulo: 'Zonas rurales y zonas sin datos',
      parrafos: [
        'El censo no publica cuántos niños viven en las zonas rurales, así que ahí decimos "Sin '
        + 'datos". Nunca inventamos un número donde no lo hay -- y que no haya datos no quiere '
        + 'decir que no haya necesidad.',
      ],
    },
    {
      titulo: 'Por qué a veces baja de golpe la oferta de escuelas',
      parrafos: [
        'Entre 2020 y 2023 casi no se actualizó el directorio de escuelas, clínicas y comercios. '
        + 'Cuando se volvió a actualizar en 2024, aparecieron de golpe muchos cierres que en '
        + 'realidad habían pasado antes, sobre todo en preescolares y guarderías privadas. Por '
        + 'eso, en escuelas y cultura, nunca mostramos el nivel de seguridad más alto: creemos que '
        + 'es lo que pasó, pero no lo podemos confirmar del todo.',
      ],
    },
    {
      titulo: 'Cosas que debes saber antes de usar esto',
      lista: [
        'Todo lo que ves a futuro es un cálculo, no una promesa.',
        'Que dos cosas hayan pasado juntas antes no significa que una sea la causa de la otra.',
        'Que no haya datos de una zona no significa que ahí no haga falta nada.',
        'Que un lugar esté registrado no nos dice qué tan grande, bueno o lleno está.',
        'No toda la ciudad tiene la misma cantidad de información. Usar esto para decidir dónde '
        + 'vivir o invertir, sin pensar en otras cosas (seguridad, vivienda, transporte, precios), '
        + 'puede llevarte a una mala decisión.',
        interpolar('Esta información se generó el {generado}.', { generado }),
      ],
    },
  ],
};

// ---------------------------------------------------------------------------------------------
// §10.13 Comparar alcaldías
// ---------------------------------------------------------------------------------------------

const comparar = {
  titulo: 'Comparar dos alcaldías',
  boton: 'Comparar',
  seleccionA: 'Primera alcaldía',
  seleccionB: 'Segunda alcaldía',
  quitar: 'Ya no comparar',
  nota: 'La comparación usa la misma edad, plazo, búsqueda y filtros que ya elegiste.  '
    + '',
};

// ---------------------------------------------------------------------------------------------
// §10.14 Iconos "?" (9 conceptos, texto de 3 partes: qué es / por qué importa / cómo interpretarlo)
// ---------------------------------------------------------------------------------------------

const ayuda = {
  abrir: (concepto) => interpolar('Ayuda: {concepto}', { concepto }),
  poblacionObjetivo: {
    queEs: 'Cuántas niñas, niños o adolescentes de la edad que elegiste viven en esa zona.',
    porQueImporta: 'Es el punto de partida: si no sabemos cuántos niños hay, no podemos decir si '
      + 'los servicios alcanzan.',
    comoInterpretar: 'Que haya más o menos niños no es "bueno" ni "malo": solo nos dice a cuánta '
      + 'gente describe el resto de la información.',
  },
  oportunidad: {
    queEs: 'Qué tan poco alcanzan los servicios frente a la cantidad de niños de esa zona, '
      + 'comparado con el resto de la CDMX.',
    porQueImporta: 'Te ayuda a saber por dónde empezar a mirar, entre cientos de zonas.',
    comoInterpretar: 'Que salga "alta" no es una recomendación de negocio: es solo una señal para '
      + 'seguir investigando.',
  },
  disponibilidad: {
    queEs: 'Qué tantos servicios ya existen hoy frente a la cantidad de niños de esa zona.',
    porQueImporta: 'Sirve para familias que buscan dónde ya hay servicios disponibles.',
    comoInterpretar: 'No se mezcla con "qué tanto hace falta": una zona puede necesitar más '
      + 'servicios y, al mismo tiempo, ya tener algunos disponibles hoy.',
  },
  prioridades: {
    queEs: 'Qué tan importante es cada tema para ti, en una escala de 1 a 5.',
    porQueImporta: 'Cambia el orden en que se muestran las zonas.',
    comoInterpretar: 'No cambia ningún dato: solo reordena la lista según lo que te importa.',
  },
  filtros: {
    queEs: 'Qué tipo de lugares cuentan como parte de cada tema.',
    porQueImporta: 'Te deja enfocarte en el tipo de servicio que te interesa.',
    comoInterpretar: 'Cambiar un filtro cambia el cálculo, no cambia la información original.',
  },
  riesgo: {
    queEs: 'Qué tan seguro debe ser un resultado para que te lo mostremos.',
    porQueImporta: 'Te deja ocultar las zonas donde no estamos muy seguros del pronóstico.',
    comoInterpretar: 'Solo oculta o muestra zonas: no cambia el cálculo de ninguna.',
  },
  confianza: {
    queEs: 'Qué tan seguro está Habitancia de un resultado.',
    porQueImporta: 'Un resultado que "hace mucha falta" pero con poca seguridad merece más '
      + 'cautela que uno con mucha seguridad.',
    comoInterpretar: 'Alta: puedes confiar en el resultado. Media: probablemente es así, pero no '
      + 'sabemos exactamente cuánto. Baja: todavía no hay suficiente información.',
  },
  horizonte: {
    queEs: 'Cuánto tiempo hacia adelante quieres ver: 1, 3 o 5 años desde mediados de 2026.',
    porQueImporta: 'Entre más lejos veamos al futuro, menos seguro es el cálculo.',
    comoInterpretar: 'El resultado y qué tan seguro es no cambian entre plazos: solo cambia el '
      + 'tamaño del cambio calculado.',
  },
  equivalenciaAgebZona: {
    queEs: '"Zona" es como le llamamos aquí a una AGEB, que es la manera en que el INEGI divide '
      + 'la ciudad en pedazos pequeños para contar a la población.',
    porQueImporta: 'Es el pedazo más pequeño que coloreamos en el mapa y ordenamos en la lista.',
    comoInterpretar: 'Una alcaldía junta muchas zonas; el color del mapa y la lista siempre se '
      + 'calculan zona por zona, nunca solo por alcaldía completa.',
  },
};

// ---------------------------------------------------------------------------------------------
// §10.4 Leyenda
// ---------------------------------------------------------------------------------------------

const leyenda = {
  encabezadoGeneral: (v) => interpolar('Cómo leer el mapa · {vista} · {anio}', v),
  encabezadoAlcaldia: (v) => interpolar('Cómo leer el mapa · {alcaldia} · {vista} · {anio}', v),
  confianzaBaja: (n) => interpolar('{n} con poca seguridad en el número de niños que usamos.', { n }),
  filtroActivo: (v) => interpolar('Mostrando {n} de {total} · Quitar filtro', v),
};

// ---------------------------------------------------------------------------------------------
// §10.1, §13 Mapa
// ---------------------------------------------------------------------------------------------

const mapa = {
  regionLabel: 'Mapa de la CDMX',
  resumenAria: (v) => interpolar(
    'Mapa de la CDMX, vista {vista}, a {h} año(s): {nAlta} zonas con mucha necesidad, {nMedia} '
    + 'con necesidad media, {nBaja} con poca. Consulta la lista para ver el detalle.',
    v,
  ),
};

// ---------------------------------------------------------------------------------------------
// §14.2 Tooltips
// ---------------------------------------------------------------------------------------------

const tooltip = {
  vistaTercil: (v) => interpolar('{vista}: {simbolo} {tercil}', v),
  vecina: (nombre) => interpolar('Ir a {nombre}', { nombre }),
  ageb: (v) => interpolar('Zona {cvegeo}', v),
  agebSinDatos: (motivo) => interpolar('Sin datos: {motivo}', { motivo }),
};

// ---------------------------------------------------------------------------------------------
// §14.4 Motivos de sin_datos
// ---------------------------------------------------------------------------------------------

const motivosSinDatosMapa = {
  rural: 'Es una zona rural: ahí el censo no cuenta cuántos niños hay.',
  suprimido_inegi: 'El INEGI no publica esta cifra, para proteger la privacidad de quienes viven ahí.',
  poblacion_menor_20: 'Hay muy pocos niños registrados (menos de 20): es muy poco para calcular '
    + 'algo confiable.',
  sin_poligono: 'No pudimos ubicar esta zona en el mapa.',
  sin_censo: 'No pudimos ubicar esta zona en el mapa.',
  sin_establecimientos: 'No encontramos ningún lugar de este tipo registrado aquí.',
  rama_sin_dato: 'No hay suficiente información de este tema en esta zona.',
  contrato_v1_2: 'Estos datos no incluyen esta información todavía.',
};

const AUSENTE = 'No hay información para esta zona.';

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
  cargandoPronosticos: 'Cargando información…',
  anuncioVistaAlcaldia: (v) => interpolar('Viendo {alcaldia}: {n} zonas con datos.', v),
  anuncioVistaGeneral: 'Viendo toda la Ciudad de México.',
  anuncioHorizonte: (v) => interpolar('A futuro: {h} años, a mediados de {anio}.', v),
  anuncioVistaMapa: (v) => interpolar('Vista de mapa: {vista}.', v),
  anuncioPoblacion: (v) => interpolar('Edad: {poblacion}.', v),
  anuncioBusqueda: (v) => interpolar('Buscando: {busqueda}.', v),
  anuncioPeso: (v) => interpolar('{rama}: prioridad {peso} de 5.', v),
  anuncioFiltroRama: (v) => interpolar('Filtro de {rama} actualizado: {resumen}.', v),
  anuncioAgeb: (v) => interpolar('Zona {cvegeo}: necesidad {tercil}.', v),
  anuncioFiltroLeyenda: (tercilActivo) => interpolar('Filtro: solo {tercil}.', { tercil: tercilActivo }),
  anuncioComparar: (v) => interpolar('Comparando {a} y {b}.', v),
};

// ---------------------------------------------------------------------------------------------
// §15 Estados de carga, error y vacío
// ---------------------------------------------------------------------------------------------

const estados = {
  reintentar: 'Intentar de nuevo',
  error: {
    mensaje: 'No pudimos cargar la información. Revisa tu conexión a internet e intenta de nuevo.',
    detalle: (causa) => interpolar('(Detalle: {causa})', { causa }),
    causas: {
      sinConexion: 'sin conexión',
      archivoInvalido: 'el archivo no es válido',
      versionIncompatible: (v) => interpolar('versión de datos incompatible ({v})', { v }),
    },
  },
  vacio: {
    mensaje: (v) => interpolar(
      'En {alcaldia} no hay suficiente información para esta búsqueda.',
      v,
    ),
    prefijoMotivos: 'Por qué:',
  },
  incompletos: (n) => interpolar(
    'No tenemos suficiente información para calcular {n} zonas; las mostramos como sin datos.',
    { n },
  ),
  ramaSinDato: 'Este tema no tiene suficiente información en esta zona; el resultado usa los demás.',
  todasSinDato: 'En esta zona no hay suficiente información en ningún tema.',
  cargandoAgeb: (alcaldiaNombre) => interpolar(
    'Cargando las zonas de {alcaldia}…',
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
  fuentes: 'De dónde sale la información: INEGI, CONAPO, DENUE, Datos Abiertos CDMX',
  datosGenerados: (fecha) => interpolar('Actualizado: {fecha}', { fecha }),
  advertenciaSesgos: 'Habitancia compara zonas entre sí; no te dice dónde vivir ni garantiza que '
    + 'un negocio vaya a funcionar. Además, no toda la ciudad tiene la misma cantidad de '
    + 'información.',
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
