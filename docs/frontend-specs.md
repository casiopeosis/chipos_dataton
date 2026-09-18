# Frontend Specs — Mapa de Demanda por Alcaldía (CDMX)

## 0. Antes de escribir código

Abre `docs/view.png` y úsalo como referencia visual principal. Es más importante clonar la *sensación* de esa imagen (limpieza, espacio en blanco, jerarquía visual) que cualquier detalle técnico descrito abajo. Si algo en este doc contradice lo que se ve en `view.png`, gana la imagen.

## 1. Qué estamos construyendo

Un frontend tipo **pitch/demo**, no una herramienta de análisis. Es la diferencia entre el tablero de un avión (para el piloto, que sabe qué hace cada botón) y la pantalla de un simulador de vuelo en un museo (para que cualquiera entienda la idea en 10 segundos sin instrucciones). Vamos por la segunda.

Pieza central: un mapa outline de la Ciudad de México sobre fondo blanco/simple, con las 16 alcaldías coloreadas según una proyección de cambio en demanda (de qué — envejecimiento poblacional, demanda de servicios, etc. — lo define el dataset). Cada alcaldía es clickable. Al hacer click se despliega un panel con texto informativo generado dinámicamente, tipo:

> "La población de adultos mayores en [alcaldía] cambiará en +X% para [año], lo que implica una mayor demanda de [servicio] de aproximadamente Y."

## 2. Lo que NO queremos (y por qué importa decirlo)

El primer intento en Streamlit se sentía "AI-generated" porque tenía el olor característico de un dashboard genérico: sidebar a la izquierda llena de sliders/parámetros que el usuario no sabe interpretar, sin curaduría de qué es relevante mostrar. Eso comunica "aquí hay una API con perillas", no "aquí hay un insight".

Evita explícitamente:
- Cualquier sidebar con inputs/parámetros libres.
- Widgets default de Streamlit, Gradio, o cualquier librería que se note "de fábrica" (fuentes default, spacing por defecto, cards con sombra genérica).
- Controles que impliquen que el usuario debe "operar" el modelo o entender la mecánica de la predicción.

## 3. Lo que SÍ queremos

- Fondo blanco o casi blanco, minimalista.
- El mapa como protagonista absoluto — nada de compartir espacio con paneles de control.
- Colores del mapa con significado claro (ver sección 5, escala de color).
- Interacción mínima y obvia: hover = feedback sutil (leve highlight/elevación), click = despliega el panel informativo con una transición suave (no un modal brusco que tape todo).
- El texto informativo debe sentirse "escrito para humano", no una tabla de números. Los números importan pero van envueltos en una oración con contexto.
- Transiciones suaves en todo: aparición del panel, cambio de color al hacer hover, aparición/desaparición de texto. Piensa "Apple keynote slide", no "formulario de gobierno".

## 4. Interacción detallada

1. Estado inicial: mapa completo visible, todas las alcaldías coloreadas según su proyección, sin panel abierto (o con un panel de "bienvenida"/instrucción muy breve, tipo "Haz click en una alcaldía para ver el detalle").
2. Hover sobre una alcaldía: cambio visual sutil (opacidad, borde, o un tooltip mínimo con el nombre y el número clave) — sin abrir el panel completo todavía.
3. Click: el panel se despliega (lateral, o como overlay flotante cerca de la alcaldía — decide con base en `view.png`) con:
   - Nombre de la alcaldía.
   - El texto dinámico de la proyección.
   - Idealmente 1 visual de apoyo (mini gráfico de tendencia, no una tabla).
4. Click en otra alcaldía: el panel se actualiza con una transición (no un salto brusco), y el mapa puede des-resaltar la anterior y resaltar la nueva.
5. Click fuera / botón cerrar: el panel se cierra suavemente.

## 5. Datos y escala de color — cosas que probablemente no habías pensado pero sí importan

- **Necesitas un GeoJSON/TopoJSON de los límites de las 16 alcaldías de CDMX.** Si no lo tienes ya, es lo primero que hay que resolver (INEGI o Datos Abiertos CDMX lo publican). Sin esto no hay mapa, así que vale la pena confirmarlo antes de que Claude Code empiece a construir UI sobre datos que no existen.
- **Define si tu variable es secuencial o divergente.** Si "cambio en demanda" puede ser negativo en algunas alcaldías y positivo en otras, necesitas una escala divergente (ej. azul→blanco→rojo), no una secuencial de un solo color — si no, alcaldías con caída de demanda se verán "igual de calientes" que las que suben. Esto cambia la lectura completa del mapa.
- **Une la leyenda al mapa.** Un mapa de calor sin leyenda es una decoración, no información — el usuario en un pitch necesita saber qué significa el color en 1 segundo, sin preguntarte.
- **Formato del dato de entrada:** define ya un JSON/CSV simple (alcaldía → valor(es) → texto o template de texto) que el frontend consuma, para que no dependa de que el modelo corra en vivo. Para un pitch, tener los números pre-calculados y servidos como datos estáticos es más confiable que llamar al modelo en tiempo real (menos puntos de falla el día de la presentación).

## 6. Cosas adicionales a considerar (que no mencionaste pero sí te van a doler si las ignoras)

- **¿Dónde y cómo se va a mostrar esto el día del pitch?** ¿Proyector, laptop, compartiendo pantalla? Si es para presentar en vivo, prioriza que se vea bien en una resolución de laptop/proyector estándar, no necesariamente que sea responsive a celular (a menos que también planees mandar el link a alguien para que lo abra en su teléfono — en ese caso sí hay que pensar en mobile).
- **Estado de "nada seleccionado" y estado de carga.** ¿Qué se ve mientras cargan los datos o límites del mapa? Un mapa en blanco por 2 segundos en medio de un pitch se siente como un error.
- **Fuente tipográfica y paleta de marca.** Si tienes colores o tipografía institucional (de la organización o el proyecto), este es el momento de definirlos, aunque sea de forma mínima (1 tipografía para títulos, 1 para cuerpo, 2-3 colores de acento).
- **Deploy/compartir.** ¿Esto se va a poder mandar como link (Vercel/Netlify/GitHub Pages) para que alguien lo vea sin que tú lo tengas prendido en tu laptop? Vale la pena resolverlo desde el principio si es parte del "pitch" (mandar el link antes o después de la reunión).
- **Créditos/fuente de datos.** En un pitch, tener una nota discreta de la fuente de los datos (INEGI, CONAPO, etc.) da credibilidad — no hace falta que sea prominente, pero su ausencia se nota si alguien pregunta "¿de dónde sale esto?".
- **Accesibilidad de color.** Si usas rojo/verde para la escala divergente, considera que puede ser ilegible para daltónicos — hay paletas divergentes (ej. azul/naranja) que resuelven esto sin sacrificar impacto visual.

## 7. Stack técnico sugerido

No es religioso, pero para lograr "chic + transiciones suaves" sin reinventar la rueda:

- **React + Vite** como base (rápido de iterar, fácil de deployar como estático).
- **Mapa:** SVG del outline de CDMX con las alcaldías como `<path>` individuales (vía `d3-geo`/`topojson` para proyectar el GeoJSON a SVG), en vez de un mapa tipo Google Maps/Leaflet con tiles — para este caso un SVG plano da más control sobre el estilo "ilustración limpia" que se ve en `view.png`, y es más fácil de animar.
- **Animaciones/transiciones:** `framer-motion` — hace que el panel, el hover y las transiciones de color se sientan pulidas con poco código.
- **Estilos:** Tailwind CSS para mantener consistencia y evitar el look "default" de cualquier librería de componentes pesada (Bootstrap, Material UI de fábrica, etc.).
- Alternativa más simple si se prefiere cero build step: HTML/CSS/JS vanilla con D3 para el mapa y CSS transitions — funciona igual de bien para un pitch de una sola página.

## 8. Checklist de aceptación (para que Claude Code se autoevalúe al terminar)

- [ ] Fondo blanco/simple, sin sidebar de controles.
- [ ] Las 16 alcaldías visibles, clickables, con colores según la escala definida (y su leyenda visible).
- [ ] Click despliega panel con texto dinámico coherente con el dataset real (no lorem ipsum).
- [ ] Transiciones suaves en hover, click, y cambio de panel (nada de saltos bruscos).
- [ ] No hay ningún input/slider/parámetro libre visible para el usuario.
- [ ] Se ve bien en resolución de laptop estándar (1440x900 o similar) sin scroll raro.
- [ ] Existe un estado de carga y un estado inicial (antes del primer click) que no se sienta vacío o roto.
- [ ] La estética general se parece, en espíritu, a `docs/view.png`.