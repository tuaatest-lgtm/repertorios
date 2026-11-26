# Inferencia de una duración faltante por balance del compás

El valor métrico del compás puede utilizarse como una ecuación de balance:

**duración esperada − suma de duraciones conocidas = duración restante.**

El módulo `duration_completion.py` calcula esa diferencia con fracciones exactas, sin redondeos decimales. Por ejemplo, en 4/4 el compás vale cuatro negras. Si tres eventos de la misma voz ya están identificados y suman tres negras, el único evento pendiente debe valer una negra.

## Cuándo se puede inferir

La función solo asigna el residuo a un evento cuando se cumplen todas estas condiciones:

- Los eventos pertenecen a la misma voz o línea rítmica independiente y al mismo compás.
- Se conoce el indicador de compás.
- Todos los demás eventos están contabilizados, incluidos silencios.
- Las duraciones conocidas ya incluyen puntillos, tresillos u otras subdivisiones, y las notas ligadas ya se han tratado como corresponda.
- Existe exactamente un evento sin duración conocida.
- La suma conocida no excede el valor del compás y queda un residuo positivo.

## Cuándo no se puede decidir

Si faltan dos o más duraciones, el residuo es solo la suma que deben completar entre ellas. Por ejemplo, dos negras restantes podrían corresponder a dos negras, una blanca, cuatro corcheas u otra combinación compatible. El módulo no inventa una asignación.

Tampoco se deben sumar entre sí voces simultáneas distintas: cada voz tiene su propio balance rítmico. En una partitura de piano, las dos manos pueden tener eventos simultáneos pero sus duraciones se verifican por flujo rítmico; en una partitura coral, soprano, alto, tenor y bajo se validan de forma independiente. Un silencio cuenta como evento y una ligadura de prolongación no crea un nuevo ataque.

El resultado es una inferencia de duración, no una identificación visual de la figura. Una duración restante de 3/2 negras, por ejemplo, podría expresarse como negra con puntillo, pero solo si el contexto y la notación lo permiten. La función conserva el valor exacto y no decide por sí sola la grafía.

## Estados

- `inferred_single_unknown`: residuo positivo asignado al único evento desconocido.
- `remainder_shared_by_multiple_unknowns`: residuo calculado, pero no asignado a un evento.
- `overfull`: las duraciones conocidas ya exceden el compás.
- `no_positive_remainder`: no queda duración positiva para el evento pendiente.
- `complete`: todos los eventos declarados conocidos suman exactamente el compás.
- `unaccounted_remainder`: no se declararon eventos desconocidos, pero queda tiempo sin explicar.

Este módulo es una herramienta de validación y no está conectado todavía al análisis de imágenes ni al reproductor Sonoro.
