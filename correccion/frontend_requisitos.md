PROMPT FUNCIONAL — FRONTEND HABITANCIA
ALCANCE ACTUAL: SOLO NIVEL 1 Y NIVEL 2 DE INFORMACIÓN

Quiero construir un frontend funcional para una aplicación web llamada Habitancia.

Habitancia nace de “habitar” + “infancia” y busca ayudar a una persona no técnica a explorar la Ciudad de México y detectar zonas donde, de acuerdo con la evolución de la población infantil y la disponibilidad de servicios, podría existir una mayor oportunidad relativa de ampliar o fortalecer infraestructura para infancias.

Este documento debe entenderse por sí solo. No se debe asumir que quien lo lea conoce prototipos anteriores, decisiones previas de diseño o versiones anteriores del frontend.

IMPORTANTE:
- No describir metodología estadística avanzada.
- No mostrar fórmulas ni parámetros internos del modelo.
- No obligar al usuario a conocer términos técnicos territoriales.
- El mapeo analítico se realiza por AGEB, pero en la interfaz principal se puede presentar al usuario como “zona” para no exigir conocimiento técnico previo.
- Utilizar lenguaje claro para personas que no conocen la Ciudad de México.
- Toda cifra o concepto poco intuitivo debe poder explicarse mediante un icono “?”.
- El frontend debe actualizarse en tiempo real al modificar filtros, pesos o selecciones.
- En esta fase solo se implementan NIVEL 1 y NIVEL 2 de información.

====================================================================
1. QUÉ SIGNIFICA NIVEL 1 Y NIVEL 2
====================================================================

NIVEL 1 — RESPUESTA RÁPIDA

Es la información mínima que una persona necesita para comprender el resultado sin conocimientos técnicos.

Debe responder:

- ¿Dónde está la zona?
- ¿Qué población se está analizando?
- ¿A qué horizonte se está proyectando?
- ¿Qué tipo de servicio o necesidad se está analizando?
- ¿Qué tan alta es la oportunidad relativa?
- ¿Qué tan confiable es el resultado?

El Nivel 1 NO debe saturar con gráficas, tablas ni estadísticas.

Debe mostrar primero un RESUMEN ESTRUCTURADO, no una frase autogenerada.

Ejemplo de estructura:

Zona: [nombre]
Población analizada: [rango de edad]
Horizonte: [1 / 3 / 5 años]
Oportunidad relativa: [alta / media / baja]
Confianza: [alta / media / baja]
Ramas con mayor incidencia: [Educación y cultura / Salud / Verde y espacio público / Comercio]

No se deben generar narrativas automáticas en lenguaje natural para explicar el resultado. La interpretación debe construirse con etiquetas, valores, gráficas y ayudas “?” predefinidas.

La expresión “oportunidad relativa” debe explicarse claramente.

OPORTUNIDAD RELATIVA significa:

“Qué tan prioritaria aparece una zona frente a otras bajo los criterios seleccionados por el usuario.”

Una oportunidad relativa puede aumentar cuando, por ejemplo:
- existe población infantil que podría necesitar un servicio;
- la oferta disponible es menor;
- la oferta crece más lentamente que la población objetivo;
- la cobertura resulta baja respecto a otras zonas;
- una rama priorizada por el usuario presenta menor disponibilidad.

NO significa:
- que sea obligatorio abrir un negocio;
- que exista una necesidad comprobada de mercado;
- que una zona sea buena o mala;
- que el modelo esté recomendando una inversión.

Es una forma de ordenar zonas para identificar dónde puede ser más útil investigar, intervenir o ampliar servicios.

NIVEL 2 — ENTENDER EL RESULTADO

Se abre únicamente cuando el usuario desea profundizar.

Debe explicar:
- cómo ha cambiado la zona;
- cómo podría cambiar;
- qué ocurre con la población objetivo;
- qué ocurre con los servicios disponibles;
- cómo influyen las cuatro ramas principales del análisis;
- qué filtros se están utilizando;
- qué prioridades o pesos eligió el usuario;
- qué tan incierta es la estimación;
- cómo se compara con otra alcaldía o zona.

====================================================================
2. OBJETIVO GENERAL DE HABITANCIA
====================================================================

Habitancia debe ayudar a responder:

“¿En qué zonas de la Ciudad de México podría existir una mayor oportunidad de ampliar o fortalecer servicios para infancias durante los próximos años?”

La aplicación debe combinar cuatro ramas principales:

1. EDUCACIÓN Y CULTURA PARA INFANCIAS
2. ÁREAS VERDES Y ESPACIO PÚBLICO
3. SALUD
4. COMERCIO Y ACCESO A PRODUCTOS DE PRIMERA NECESIDAD

Estas cuatro ramas funcionan como dimensiones del análisis.

El usuario puede decidir:
- cuáles quiere considerar;
- qué tanto peso tiene cada una;
- qué filtros específicos quiere aplicar dentro de cada rama.

Los pesos y filtros NO cambian las predicciones originales.
Cambian la forma en que Habitancia ordena y presenta los resultados.

====================================================================
3. FLUJO GENERAL DEL USUARIO
====================================================================

La navegación debe seguir esta secuencia:

1. El usuario entiende qué hace Habitancia.
2. Selecciona una alcaldía en el mapa o la busca por nombre.
3. Define la población objetivo.
4. Define el horizonte.
5. Define el tipo de búsqueda.
6. Define cuánto le importa cada una de las cuatro ramas.
7. Si quiere, abre “Filtros” para indicar qué tipos de servicios quiere incluir dentro de cada rama.
8. El mapa y el ranking se actualizan.
9. Selecciona una alcaldía o una zona.
10. Consulta primero un resumen breve de los resultados.
11. Si quiere profundizar, abre “Entiende esta zona”.
12. Consulta gráficas y el detalle de las cuatro ramas.
13. Puede comparar dos alcaldías.

No se debe mostrar toda la información de golpe.

====================================================================
4. PANTALLA INICIAL
====================================================================

La pantalla inicial debe explicar inmediatamente el propósito de Habitancia.

Texto principal sugerido:

“¿Dónde podrían hacer falta más servicios para las infancias?”

Texto secundario:

“Habitancia analiza cómo podría cambiar la población infantil y cómo se distribuyen distintos servicios en la Ciudad de México para identificar zonas que conviene explorar con mayor detalle.”

Debe existir un mapa general de la Ciudad de México construido a partir de polígonos de AGEB.

La AGEB es la UNIDAD GEOGRÁFICA BASE DEL MAPEO Y DEL CÁLCULO TERRITORIAL.

Las alcaldías funcionan como nivel de orientación, búsqueda y agrupación:
- sus límites deben ser visibles sobre el mapa;
- sus nombres pueden utilizarse para orientar al usuario;
- seleccionar o buscar una alcaldía debe enfocar las AGEB que pertenecen a ella.

En la interfaz dirigida a personas no técnicas, cada AGEB puede mostrarse como “zona”. Un icono “?” puede explicar, cuando sea necesario:

“Cada zona corresponde a una AGEB, una división geográfica utilizada por INEGI para organizar información estadística.”

FUNCIONALIDADES:

A. SELECCIÓN EN MAPA
- Cada alcaldía es seleccionable.
- Al pasar el cursor debe aparecer su nombre.
- Al hacer clic debe abrirse su vista.
- Debe existir una forma clara de volver a la vista general.

B. BUSCADOR
Debe existir un buscador visible.

El usuario puede:
- escribir una alcaldía;
- seleccionarla de una lista;
- ir directamente a ella.

Texto sugerido:

“Selecciona una alcaldía en el mapa o búscala por nombre.”

Esto es importante porque el público puede no conocer la geografía de CDMX.

====================================================================
5. POBLACIÓN OBJETIVO
====================================================================

Debe existir un selector:

“¿A quién quieres analizar?”

Opciones:

- Todas las infancias y adolescencias · 0–17 años
- Primera infancia · 0–2 años
- Preescolar · 3–5 años
- Primaria · 6–11 años
- Secundaria · 12–14 años
- Adolescencia · 15–17 años

Cada opción puede tener un icono sencillo.

Debe existir “?”:

“La población objetivo indica qué grupo de niñas y niños quieres analizar. Cambiarla modifica la población que se compara con los servicios disponibles.”

El rango de 15–17 años SÍ forma parte del análisis funcional y debe estar disponible como población objetivo.

====================================================================
6. HORIZONTE
====================================================================

Pregunta:

“¿A qué plazo quieres mirar?”

Opciones:

- 1 año · 2027
- 3 años · 2029
- 5 años · 2031

Al cambiar el horizonte deben actualizarse:
- mapa;
- ranking;
- resumen principal;
- gráficas;
- oportunidad relativa;
- incertidumbre.

“?”:

“Las proyecciones son estimaciones. Mientras más lejano es el horizonte, mayor puede ser la incertidumbre.”

====================================================================
7. TIPO DE BÚSQUEDA
====================================================================

Pregunta:

“¿Qué quieres encontrar?”

OPORTUNIDAD DE EXPANSIÓN

“Ordena primero las zonas donde, de acuerdo con los criterios seleccionados, podría existir mayor espacio para ampliar o fortalecer servicios.”

Ejemplo:
si una zona mantiene una población infantil relevante pero tiene poca cobertura de un servicio, puede aparecer con una oportunidad relativa mayor.

DISPONIBILIDAD PARA FAMILIAS

“Ordena primero las zonas donde existe una mayor disponibilidad relativa de los servicios seleccionados.”

Debe existir “?”:

“Una zona con poca oferta puede representar una oportunidad de expansión, pero al mismo tiempo tener baja disponibilidad actual para las familias. Por eso ambas búsquedas responden preguntas diferentes.”


====================================================================
9. PRIORIDADES GENERALES: LAS CUATRO RAMAS
====================================================================

Debe existir una sección:

“¿Qué es más importante para ti?”

Aquí aparecen las cuatro ramas:

Educación y cultura
● ● ● ● ○

Áreas verdes y espacio público
● ● ● ○ ○

Salud
● ● ● ● ●

Comercio
● ● ● ○ ○

Los círculos son interactivos.

Cinco círculos = prioridad muy alta.
Un círculo = prioridad baja.

IMPORTANTE:

Estos pesos NO alteran los datos.
NO alteran las predicciones.

Únicamente modifican:
- el índice compuesto;
- la oportunidad relativa;
- el orden del ranking.

Debe existir “?”:

“Los pesos indican qué tan importante es cada rama para tu búsqueda. Habitancia utiliza esa preferencia para ordenar las zonas, pero no cambia los datos originales.”

Debe existir:
“Restablecer prioridades”

El escenario inicial puede comenzar con pesos iguales.

====================================================================
10. FILTROS
====================================================================

Debe existir una pestaña o apartado llamado:

“Filtros”

Su función NO es añadir más complejidad matemática.

Su función es permitir que el usuario diga exactamente qué quiere incluir dentro de las cuatro ramas.

Los filtros modifican:
- qué registros se toman en cuenta;
- qué información se muestra;
- el resultado del índice compuesto;
- el ranking.

No modifican las predicciones originales.

La lógica debe ser muy sencilla.

--------------------------------------------------
10.1 EDUCACIÓN Y CULTURA
--------------------------------------------------

Pregunta:

“¿Qué servicios de educación y cultura quieres considerar?”

Filtros principales:

NIVEL / TIPO
- Guarderías y estancias infantiles
- Preescolar
- Primaria
- Secundaria
- Media superior o técnica
- Educación especial
- Recreación o cultura infantil

SECTOR
- Todos
- Público
- Privado

Si el usuario selecciona una población específica, Habitancia puede sugerir automáticamente el nivel educativo relacionado.

Ejemplo:

6–11 años
→ sugerir “Primaria”.

15–17 años
→ sugerir “Media superior o técnica”, cuando corresponda a los datos disponibles.

Pero el usuario puede modificar el filtro.

“?”:

“Estos filtros indican qué tipos de servicios educativos o culturales quieres incluir en el análisis de esta rama.”

--------------------------------------------------
10.2 SALUD
--------------------------------------------------

Pregunta:

“¿Qué instalaciones de salud quieres considerar?”

Filtros principales:

TIPO
- Clínicas o consultorios
- Hospitales
- Salud mental o psicológica
- Farmacias

SECTOR
- Todos
- Público
- Privado

No es necesario mostrar todos los campos de la base.
Solo los que cambian realmente la interpretación para una persona no técnica.

“?”:

“Habitancia utiliza únicamente los tipos de instalaciones que selecciones para calcular la disponibilidad de servicios de salud.”

--------------------------------------------------
10.3 COMERCIO
--------------------------------------------------

Pregunta:

“¿Qué comercios quieres considerar?”

Filtros principales:

TIPO
- Comercios de primera necesidad
- Supermercados y minisúpers
- Abarrotes
- Frutas y verduras
- Carnes y otros alimentos
- Farmacias, si se decide incluirlas en esta rama

El filtro puede permitir:
- “Todos”
- elegir uno o varios tipos.

No es necesario pedir más detalle salvo que el usuario lo solicite.

“?”:

“Este filtro permite decidir qué tipos de comercios cotidianos deben considerarse al analizar la disponibilidad de productos de primera necesidad.”

--------------------------------------------------
10.4 ÁREAS VERDES Y ESPACIO PÚBLICO
--------------------------------------------------

Pregunta:

“¿Qué tipo de espacio quieres considerar?”

Filtros principales:

- Áreas verdes recreativas
- Cobertura verde
- Espacio público

Si existen categorías disponibles en los datos, pueden utilizarse para refinar la selección, pero no debe convertirse en una lista extensa.

“?”:

“No toda superficie verde funciona como espacio recreativo. Este filtro permite diferenciar entre cobertura verde general y espacios que pueden tener una función de convivencia o recreación.”

--------------------------------------------------
10.5 COMPORTAMIENTO DE LOS FILTROS
--------------------------------------------------

Todos los filtros deben actualizar automáticamente:
- el mapa;
- el ranking;
- la ficha de la zona;
- la explicación de las cuatro ramas;
- las gráficas que correspondan.

Debe existir:
“Restablecer filtros”

Siempre debe ser visible un resumen breve del escenario activo.

Ejemplo:

“6–11 años · Primaria · 3 años ”

Si se están usando filtros más específicos:

“Primaria pública · hospitales y clínicas · comercio de primera necesidad · áreas verdes recreativas”

====================================================================
11. MAPA Y RANKING — MAPEO POR AGEB
====================================================================

Después de definir el escenario, el usuario debe ver:

A. MAPA
B. RANKING

REGLA GEOGRÁFICA OBLIGATORIA:

TODO EL MAPEO ANALÍTICO DE HABITANCIA SE REALIZA POR AGEB.

Cada polígono coloreado del mapa corresponde a una AGEB y recibe el valor que resulte del análisis activo:
- índice compuesto en la Vista general;
- indicador de Educación y cultura en esa vista;
- indicador de Salud en esa vista;
- indicador de Áreas verdes y espacio público en esa vista;
- indicador de Comercio en esa vista.

Las alcaldías NO son la unidad mínima que se colorea para representar el resultado.

Las alcaldías se utilizan para:
- orientar al usuario;
- mostrar límites y nombres;
- buscar una zona de la ciudad;
- agrupar resultados;
- hacer zoom;
- comparar resultados agregados entre alcaldías.

FUNCIONAMIENTO:

1. VISTA CDMX
   - Se muestran todas las AGEB de la Ciudad de México.
   - Cada AGEB se colorea según el indicador activo.
   - Los límites de alcaldía permanecen visibles como referencia.
   - El usuario puede buscar una alcaldía por nombre.

2. AL SELECCIONAR UNA ALCALDÍA
   - El mapa hace zoom a esa alcaldía.
   - Se conservan visibles únicamente o de forma destacada sus AGEB.
   - Cada AGEB mantiene su propio valor y color.
   - El usuario puede seleccionar cualquiera de esas zonas para abrir su ficha.

3. AL SELECCIONAR UNA AGEB
   - Se resalta el polígono correspondiente.
   - Se abre la ficha del Nivel 1.
   - “Entender esta zona” permite acceder al Nivel 2.

4. RANKING
   - El ranking de detalle se genera por AGEB.
   - Cada fila corresponde a una zona/AGEB.
   - Debe indicar al menos la alcaldía a la que pertenece, la oportunidad relativa y los indicadores básicos del escenario activo.
   - No es necesario mostrar la clave técnica de AGEB como dato principal.

LENGUAJE PARA EL USUARIO:

Aunque técnicamente el mapeo sea por AGEB, la interfaz principal puede utilizar “zona” como término visible.

Si el usuario abre el icono “?”:

“Las zonas del mapa corresponden a AGEB, divisiones geográficas utilizadas por INEGI para organizar información estadística y comparar áreas pequeñas dentro de una alcaldía.”

El mapa responde:
“¿Dónde están las zonas relevantes?”

El ranking responde:
“¿Qué zonas debería revisar primero según mis criterios?”

Al seleccionar una zona:
- el mapa la enfoca;
- se abre su ficha;
- se muestran sus indicadores;
- se conserva visible la alcaldía a la que pertenece.


====================================================================
11A. VISTA GENERAL Y VISTAS POR RAMA EN EL MAPA
====================================================================

Además del mapa general, Habitancia debe permitir cambiar la lectura del mapa según la rama que el usuario quiera observar.

Debe existir un selector sencillo:

“¿Qué quieres ver en el mapa?”

Opciones:

- Vista general
- Educación y cultura
- Áreas verdes y espacio público
- Salud
- Comercio

La idea es conservar EL MISMO MAPA DE AGEB y actualizar únicamente:
- el color de las zonas;
- la leyenda;
- el ranking;
- el título de la vista;
- la información que aparece al seleccionar una zona.

No abrir mapas separados para cada rama.

--------------------------------------------------
VISTA GENERAL
--------------------------------------------------

La vista general utiliza el índice compuesto.

Este índice combina las cuatro ramas utilizando los pesos elegidos previamente por el usuario.

Ejemplo:

Educación y cultura: peso alto
Salud: peso alto
Verde y espacio público: peso medio
Comercio: peso bajo

Cada AGEB del mapa se colorea según el resultado conjunto de esas prioridades.

Pregunta que responde:

“Considerando todo lo que seleccioné, ¿qué zonas aparecen con mayor oportunidad relativa?”

La leyenda debe expresar categorías comprensibles, por ejemplo:

- Mayor oportunidad relativa
- Oportunidad intermedia
- Menor oportunidad relativa

La vista general debe ser la opción predeterminada.

--------------------------------------------------
VISTA EDUCACIÓN Y CULTURA
--------------------------------------------------

Si el usuario selecciona:

“Educación y cultura”

cada AGEB deja de colorearse con el índice compuesto y pasa a colorearse únicamente con el resultado correspondiente a esta rama.

Debe respetar los filtros activos de Educación y cultura.

Ejemplo:

Si los filtros actuales son:

Primaria
Sector público

el mapa debe responder:

“¿Cómo se distribuye la disponibilidad u oportunidad relacionada con primarias públicas?”

El título, la leyenda y el ranking deben cambiar para reflejar esta rama.

--------------------------------------------------
VISTA SALUD
--------------------------------------------------

Si el usuario selecciona:

“Salud”

cada AGEB del mapa se colorea únicamente con la información de Salud.

Debe respetar los filtros activos.

Ejemplo:

Hospitales + clínicas
Sector público

Pregunta que responde:

“¿En qué zonas existe mayor o menor disponibilidad relativa de hospitales y clínicas públicas?”

--------------------------------------------------
VISTA ÁREAS VERDES Y ESPACIO PÚBLICO
--------------------------------------------------

Si el usuario selecciona esta rama, cada AGEB del mapa debe mostrar únicamente el indicador correspondiente al entorno verde y espacio público.

Debe respetar el filtro activo:

- áreas verdes recreativas;
- cobertura verde;
- espacio público.

Pregunta que responde:

“¿Cómo se distribuyen los espacios verdes o públicos seleccionados?”

--------------------------------------------------
VISTA COMERCIO
--------------------------------------------------

Si el usuario selecciona:

“Comercio”

cada AGEB del mapa debe mostrar únicamente el indicador de comercio correspondiente a los filtros activos.

Ejemplo:

Comercios de primera necesidad.

Pregunta que responde:

“¿Dónde existe mayor o menor disponibilidad relativa de los comercios que seleccioné?”

--------------------------------------------------
RELACIÓN ENTRE PESOS Y VISTAS POR RAMA
--------------------------------------------------

Es importante distinguir:

VISTA GENERAL
= sí utiliza los pesos elegidos por el usuario para combinar las cuatro ramas.

VISTA DE UNA RAMA
= muestra esa rama de forma individual.

Por ejemplo:

si Salud tiene peso 5/5 y Comercio 2/5:

- en “Vista general”, Salud influye más en el índice compuesto;
- en “Salud”, se muestra únicamente la información de Salud;
- en “Comercio”, se muestra únicamente la información de Comercio.

El peso no debe alterar artificialmente el color dentro de la vista individual de una rama.

Los filtros sí modifican la vista individual porque determinan qué información de esa rama se está analizando.

--------------------------------------------------
CAMBIO AUTOMÁTICO DE LEYENDA Y TITULAR
--------------------------------------------------

Cada vez que el usuario cambia de Vista general a una rama específica, deben actualizarse automáticamente:

1. el título fijo de la vista;
2. la leyenda;
3. el ranking por AGEB;
4. los indicadores visibles;
5. la ficha de la zona seleccionada.

No se requiere generar una narrativa automática.

Ejemplos:

VISTA GENERAL:
“¿Dónde existe mayor oportunidad relativa según tus criterios?”

SALUD:
“¿Cómo se distribuyen los servicios de salud seleccionados?”

EDUCACIÓN:
“¿Cómo se distribuyen los servicios educativos seleccionados?”

VERDE:
“¿Cómo se distribuyen los espacios verdes y públicos seleccionados?”

COMERCIO:
“¿Cómo se distribuyen los comercios seleccionados?”

--------------------------------------------------
POR QUÉ SE IMPLEMENTA ESTA FUNCIÓN
--------------------------------------------------

Esta funcionalidad permite que el usuario pase de:

“¿Qué zonas aparecen primero considerando todo?”

a:

“¿Qué está ocurriendo específicamente en Salud?”

sin abandonar el mapa ni cambiar de pantalla.

Hace más fácil entender qué rama está impulsando el resultado general y evita mostrar cuatro mapas diferentes.

También permite utilizar Habitancia en dos niveles:

1. análisis general;
2. exploración específica por rama.


====================================================================
12. VISTA DE ALCALDÍA
====================================================================

Cuando el usuario selecciona una alcaldía:

- el mapa debe enfocarla;
- las demás alcaldías pasan a segundo plano;
- aparece su nombre;
- existe un botón claro para volver.

Puede aparecer:

“Ciudad de México > Álvaro Obregón”

La primera información debe ser un RESUMEN ESTRUCTURADO de los datos principales, sin generar frases interpretativas.

Ejemplo:

Álvaro Obregón
Población: 6–11 años
Horizonte: 3 años
Búsqueda: Oportunidad de expansión
Oportunidad relativa: Alta
Confianza: Media–alta
Ramas con mayor incidencia: Educación y cultura / Salud

Después se muestran únicamente los datos principales.

====================================================================
13. NIVEL 1 — RESUMEN DE LA ZONA
====================================================================

El Nivel 1 debe mostrar:

- población objetivo;
- horizonte;
- servicio principal seleccionado;
- oportunidad relativa;
- confianza;
- comportamiento general de la población;
- resumen de disponibilidad de servicios.

Ejemplo:

Álvaro Obregón

Población:
6–11 años

Horizonte:
3 años

Búsqueda:
Oportunidad de expansión

Oportunidad relativa:
Alta

Confianza:
Media–alta

Motivos principales del resultado:

En lugar de una frase autogenerada, mostrar indicadores estructurados como:

Educación y cultura: disponibilidad relativa baja
Salud: disponibilidad relativa media
Áreas verdes y espacio público: disponibilidad relativa media
Comercio: disponibilidad relativa alta

Debe existir:

“Entender esta zona”

para pasar al Nivel 2.

====================================================================
14. NIVEL 2 — “ENTIENDE ESTA ZONA”
====================================================================

Debe responder:

A. ¿Cómo ha cambiado?
B. ¿Qué podría pasar?
C. ¿Qué explica el resultado?
D. ¿Qué ramas están pesando más bajo mis criterios?

====================================================================
15. GRÁFICA DE POBLACIÓN / DEMANDA POTENCIAL
====================================================================

Debe existir una gráfica:

“¿Cómo ha cambiado la población objetivo?”

Debe mostrar:
- histórico;
- punto actual;
- proyección;
- rango de incertidumbre.

Controles:

Histórico
Proyección a:
- 1 año
- 3 años
- 5 años

“?”:

“La parte histórica muestra los datos observados. La parte proyectada muestra cómo podría continuar la tendencia. El rango alrededor de la proyección representa la incertidumbre.”

====================================================================
16. GRÁFICA DE SERVICIOS / OFERTA
====================================================================

Debe existir una gráfica:

“¿Cómo han cambiado los servicios disponibles?”

Su contenido depende de los filtros activos.

Ejemplo:

Si el usuario seleccionó:
“Primaria · Público”

la gráfica debe mostrar la evolución de los establecimientos de primaria pública que correspondan a la selección.

Si seleccionó:
“Hospitales”

la gráfica debe mostrar la evolución de los hospitales considerados.

“?”:

“Esta gráfica muestra establecimientos registrados. No representa capacidad, calidad, matrícula ni número de lugares disponibles.”

IMPORTANTE:
Solo deben proyectarse variables para las que exista una proyección válida.
Si una rama solo tiene información actual, mostrar su situación actual y NO inventar una línea futura.

====================================================================
17. COBERTURA
====================================================================

Después de mostrar población y servicios, puede mostrarse una medida de cobertura.

Pregunta:

“¿Cómo se relaciona la cantidad de servicios con la población?”

Mostrar:
- cobertura actual;
- cobertura proyectada cuando exista;
- referencia de CDMX o comparación con otras zonas.

“?”:

“La cobertura relaciona los servicios disponibles con el tamaño de la población objetivo para poder comparar zonas de tamaños distintos.”

====================================================================
18. “¿QUÉ EXPLICA ESTE RESULTADO?”
====================================================================

Debe existir un bloque que resuma las cuatro ramas.

Ejemplo:

Educación y cultura
● ● ● ● ○

Salud
● ● ● ○ ○

Áreas verdes y espacio público
● ● ○ ○ ○

Comercio
● ● ● ● ○

Estos círculos NO son editables.

Representan qué tan fuerte es la señal de cada rama dentro del resultado de esa zona, después de aplicar:
- los filtros seleccionados;
- los pesos elegidos por el usuario.

Debe existir un “?” junto a cada rama.

Ejemplo:

“Educación y cultura: la disponibilidad de los servicios educativos seleccionados es relativamente baja frente a otras zonas comparables.”

Debajo NO debe generarse una frase automática.

En su lugar, mostrar de forma estructurada:
- valor o nivel de cada rama;
- peso asignado por el usuario;
- contribución de cada rama al resultado general, si ese valor ya está calculado;
- icono “?” para explicar cómo interpretar cada componente.

IMPORTANTE:
No confundir estos círculos con los círculos editables de prioridades.

CÍRCULOS DE PRIORIDADES
= lo que el usuario considera importante.

CÍRCULOS DE EXPLICACIÓN
= lo que los datos muestran en esa zona.

====================================================================
19. COMPARAR ALCALDÍAS
====================================================================

Debe existir una pestaña o función:

“Comparar”

El usuario selecciona:

Alcaldía A
VS
Alcaldía B

La comparación debe conservar exactamente:
- población;
- horizonte;
- búsqueda;
- pesos;
- filtros.

Debe comparar:

- oportunidad relativa;
- confianza;
- educación y cultura;
- salud;
- áreas verdes y espacio público;
- comercio;
- población objetivo;
- disponibilidad general.

La comparación debe mostrarse mediante indicadores equivalentes colocados lado a lado.

Ejemplo:

Educación y cultura     Alcaldía A: Media    Alcaldía B: Media
Salud                   Alcaldía A: Baja     Alcaldía B: Alta
Verde y espacio público Alcaldía A: Alta     Alcaldía B: Media
Comercio                Alcaldía A: Media    Alcaldía B: Media
Oportunidad relativa    Alcaldía A: Alta     Alcaldía B: Media
Confianza               Alcaldía A: Alta     Alcaldía B: Media

No debe generarse una frase automática ni declarar un ganador.

====================================================================
20. ICONOS “?” COMO SISTEMA DE AYUDA
====================================================================

Los “?” deben utilizarse para explicar conceptos sin llenar la pantalla de texto.

Cada ayuda debe responder:

1. ¿Qué es?
2. ¿Por qué importa?
3. ¿Cómo debo interpretarlo?

Conceptos que deben tener “?”:

- oportunidad relativa;
- demanda potencial;
- oferta;
- cobertura;
- confianza;
- incertidumbre;
- pesos;
- población objetivo;
- histórico/proyección;
- cada una de las cuatro ramas cuando sea necesario.

Las ayudas deben abrirse dentro de la misma vista.

====================================================================
21. DIFERENCIA ENTRE PESOS, FILTROS Y RESULTADO
====================================================================

Esta diferencia debe quedar clarísima.

PESOS
Responden:
“¿Qué es más importante para mí?”

Ejemplo:
salud = 5/5.

FILTROS
Responden:
“¿Qué quiero incluir dentro de esa rama?”

Ejemplo:
Salud:
solo hospitales y clínicas públicas.

RESULTADO
Responde:
“¿Qué muestran los datos con esas decisiones?”

Ejemplo:
la zona tiene baja disponibilidad relativa de hospitales y clínicas públicas.

PREDICCIÓN
No es modificada por los pesos ni por los filtros.

El usuario modifica la consulta y la prioridad, no los datos originales.

====================================================================
22. ACTUALIZACIÓN EN TIEMPO REAL
====================================================================

Cuando el usuario cambie:

Población
→ actualizar resultados relacionados.

Horizonte
→ actualizar proyección e incertidumbre.

Peso de una rama
→ actualizar índice compuesto y ranking.

Filtro de una rama
→ actualizar esa rama, índice compuesto, mapa y ranking.

Alcaldía
→ actualizar ficha.

Comparación
→ recalcular la comparación bajo el escenario activo.

No recargar la página.

====================================================================
23. ORDEN EN QUE SE PRESENTA LA INFORMACIÓN
====================================================================

La información debe seguir esta secuencia:

1. ¿Qué hace Habitancia?
2. ¿Qué quiero analizar?
3. ¿Qué es importante para mí?
4. ¿Qué filtros quiero aplicar?
5. ¿Dónde están las zonas relevantes?
6. ¿Qué zonas aparecen primero?
7. ¿Qué ocurre en la zona que seleccioné?
8. ¿Cómo ha cambiado?
9. ¿Qué podría pasar?
10. ¿Qué explica el resultado?
11. ¿Cómo se compara con otra alcaldía?

No empezar por gráficas.
No empezar por tablas.
No empezar por términos estadísticos.

====================================================================
24. CASO DE USO PARA LOS JUECES
====================================================================

Un juez debe poder realizar una consulta como:

“Quiero analizar servicios para niñas y niños de primaria dentro de tres años. Me interesa especialmente educación y salud, quiero considerar únicamente educación pública y hospitales o clínicas, .”

Flujo:

Población:
6–11 años.

Horizonte:
3 años.

Búsqueda:
Oportunidad de expansión.

Prioridades:
Educación y cultura: alta.
Salud: alta.
Verde: media.
Comercio: media.

Filtros:
Educación: Primaria + Público.
Salud: Hospitales y clínicas.
Comercio: Primera necesidad.
Verde: Áreas verdes recreativas.

Resultado:
mapa + ranking.

Selecciona una zona.

Habitancia explica:
- oportunidad relativa;
- confianza;
- comportamiento de la población;
- disponibilidad de servicios;
- qué ramas explican el resultado.

Después puede:
- abrir gráficas;
- modificar filtros;
- cambiar pesos;
- comparar dos alcaldías.

Todo sin recargar la página.

====================================================================
25. REGLA PRINCIPAL DE INTUITIVIDAD
====================================================================

Cada sección debe responder UNA pregunta.

INICIO
“¿Qué hace Habitancia?”

CONFIGURACIÓN
“¿Qué quiero analizar?”

PRIORIDADES
“¿Qué es más importante para mí?”

FILTROS
“¿Qué quiero incluir?”

MAPA
“¿Dónde ocurre?”

RANKING
“¿Qué zonas debería revisar primero?”

FICHA
“¿Qué ocurre aquí?”

GRÁFICAS
“¿Cómo ha cambiado y qué podría pasar?”

EXPLICACIÓN
“¿Por qué aparece con este resultado?”

COMPARACIÓN
“¿En qué se diferencian?”

No mostrar información únicamente porque existe en la base.

La prioridad es que cualquier persona pueda comprender:

“qué está pasando, dónde, qué factores intervienen, a qué plazo y qué tan confiable es la estimación.”

====================================================================
26. RESULTADO FUNCIONAL ESPERADO
====================================================================

Al finalizar esta fase, una persona que no conoce la Ciudad de México debe poder:

1. entender qué hace Habitancia;
2. encontrar una alcaldía;
3. seleccionar población objetivo;
4. seleccionar 1, 3 o 5 años;
5. elegir oportunidad de expansión o disponibilidad;
6. asignar pesos sencillos a las cuatro ramas;
7. aplicar filtros básicos y comprensibles dentro de cada rama;
8. consultar un mapa por AGEB;
9. consultar un ranking por AGEB;
10. abrir una zona;
11. comprender su oportunidad relativa;
12. revisar las gráficas disponibles;
13. entender qué ramas explican el resultado;
14. comparar dos alcaldías.

Todo debe funcionar sin exigir conocimientos de estadística, programación o divisiones territoriales técnicas.
