# Regiones rasterizadas candidatas a texto

`palermo_omr.text_regions` propone regiones geométricas que podrían contener texto impreso en el margen izquierdo y en una franja superior estrecha de una partitura.

## Flujo

1. Recibe una imagen binaria con tinta negra y fondo blanco.
2. Retira líneas horizontales largas para reducir la interferencia del pentagrama.
3. Examina una franja configurable del margen izquierdo.
4. Agrupa componentes pequeños cercanos horizontalmente.
5. Filtra por dimensiones relativas al espaciado del pentagrama.
6. Registra la caja y los pentagramas cercanos por proximidad vertical.

## Interpretación de resultados

- `nearby_staff_candidate`: la región queda más cerca de un pentagrama que de los demás dentro del umbral; no significa que sea una etiqueta de ese pentagrama.
- `ambiguous`: hay más de un pentagrama a distancia vertical similar.
- `location_hint`: `above_staff`, `beside_staff` o `below_staff` describe únicamente la posición geométrica.

## Límites

No reconoce letras, palabras, claves ni nombres de voces. Una región puede corresponder a una etiqueta, un número, una indicación editorial, un símbolo musical o ruido del escaneo. El detector se restringe al margen izquierdo y a una franja superior estrecha (7% de la página por defecto). Puede no encontrar etiquetas centradas encima de sistemas inferiores o impresas en otras zonas. La franja superior puede incluir títulos, letras de canciones u otras indicaciones editoriales: no debe tratarse como un detector de etiquetas específico. Las cajas requieren inspección visual y no se convierten en `StaffIdentityEvidence` hasta que exista una lectura verificable del contenido.

El módulo no está conectado al CLI, no modifica la estructura musical y no se integra con Sonoro.
