# Línea temporal rítmica por compás

El módulo `rhythmic_timeline.py` introduce una capa temporal explícita para eventos musicales que ya cuentan con una voz, un compás, un inicio y una duración candidatos.

## Principios

- Los inicios y las duraciones se expresan en unidades exactas de negra mediante `Fraction`.
- Cada evento conserva su propio inicio y su propia duración; una blanca puede continuar sonando mientras otra voz ejecuta dos negras.
- Los ataques con el mismo inicio se agrupan, incluso si pertenecen a voces SATB diferentes.
- Los eventos de piano de manos distintas también pueden coexistir y solaparse sin forzar una duración común.
- Los inicios o duraciones desconocidos permanecen explícitamente pendientes.
- Un evento que comienza fuera del compás o termina más allá de su extensión métrica se señala como `overfull`.

## Alcance y límites

Esta capa no detecta notas, voces, compases, barras, ligaduras ni inicios temporales en la imagen. Tampoco estima el inicio a partir de la coordenada horizontal: el espaciado musical no es necesariamente lineal. Recibe posiciones temporales ya establecidas por una etapa posterior o por revisión humana.

El estado `placed_events_only` significa que los eventos suministrados tienen posiciones y duraciones conocidas y caben en la extensión métrica; no demuestra que la partitura esté completa ni que no falten eventos. La capa no se conecta al CLI ni al motor Sonoro.

Las notas ligadas deben consolidarse antes de crear eventos de ataque, para no contar una continuación como un nuevo ataque.
