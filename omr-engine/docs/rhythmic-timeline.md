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

## Detección de solapamientos incompatibles

La línea temporal informa `overlapping_event_ids` cuando dos eventos con duración e inicio conocidos pertenecen a la misma voz, comienzan en instantes distintos y el segundo ataque ocurre antes de que termine el primero. Los ataques simultáneos no se marcan: pueden representar notas de un acorde. Tampoco se marcan solapamientos entre voces distintas, porque la polifonía exige que sus duraciones sean independientes.

Esta comprobación detecta contradicciones en los datos temporales ya asignados; no decide automáticamente qué nota, duración o voz está equivocada. Los eventos con inicio o duración desconocidos quedan fuera de esta comprobación.


## Puntillos confirmados en la conversión a eventos

La conversión de grupos de notas revisados a eventos temporales acepta `event_dot_counts`, un mapa explícito de `event_id` a cantidad de puntillos (0–4). La duración se calcula con fracciones exactas: un puntillo aplica 3/2, dos 7/4, tres 15/8 y cuatro 31/16. Los candidatos geométricos de puntillo no se aplican automáticamente: la cantidad debe ser confirmada por revisión. El mismo mecanismo funciona cuando dos voces independientes comparten un pentagrama.


## Puntillos visuales revisados

La detección entrega una lista ordenada de `DotCandidate`. Para que un
puntillo visual afecte la duración, el manifiesto debe enlazar explícitamente
el índice del candidato con el evento confirmado:

```json
{
  "confirmed_event_ids": ["note-17"],
  "event_voice_ids": {"note-17": "soprano"},
  "event_dot_candidate_indices": {"note-17": [2]}
}
```

La llamada a `build_reviewed_page_timelines` debe recibir la misma lista de
candidatos mediante `dot_candidates`. El índice se resuelve contra esa lista,
y el candidato solo se acepta si su cabeza asociada pertenece al grupo de
cabezas del evento confirmado. Un candidato no puede reutilizarse en otro
evento. La cantidad de candidatos enlazados determina el número de puntillos
y la aritmética exacta de duración.

El conteo manual `event_dot_counts` sigue disponible como revisión explícita
alternativa, pero no se puede mezclar con enlaces visuales para el mismo
evento. La detección por sí sola nunca cambia el timeline.
