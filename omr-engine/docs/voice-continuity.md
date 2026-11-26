# Candidatos de continuidad melódica

El módulo `palermo_omr.voice_continuity` propone enlaces entre eventos que
podrían pertenecer a una misma línea melódica. Recibe eventos con inicio,
duración y altura MIDI ya disponibles; no calcula tiempos a partir de píxeles
ni convierte por sí mismo una posición del pentagrama en altura.

## Evidencia utilizada

- Mismo pentagrama.
- Orden de inicio musical.
- Distancia de altura en semitonos.
- Separación temporal o solapamiento entre eventos.
- Coincidencia de dirección de plica como evidencia débil, nunca decisiva.

La versión actual solo enlaza eventos con una única altura MIDI. Los acordes
se omiten porque decidir qué nota del acorde continúa una línea requiere
información adicional. Los eventos simultáneos no se consideran sucesivos.

## Estados y cautelas

- `proposed_transition`: enlace geométrica y temporalmente plausible.
- `ambiguous_competing_successors`: existen varios sucesores con puntuaciones
  similares; ninguno se selecciona.

Las puntuaciones son heurísticas, no probabilidades calibradas. Un enlace no
confirma una voz ni debe convertirse automáticamente en asignación. La altura
MIDI debe proceder de una clave y alteraciones revisadas o confirmadas. Los
eventos solapados se señalan para revisión, no se descartan silenciosamente.

Este módulo tampoco distingue por sí solo soprano/alto/tenor/bajo ni mano
derecha/izquierda. La asignación humana por evento sigue siendo una compuerta
separada. Las alternativas ambiguas deben permanecer visibles.

## Entrada

Cada `VoiceEventObservation` incluye:
- `event_id`
- `staff_index`
- `onset_quarters` y `duration_quarters` como tiempo musical exacto
- `pitches_midi`
- `stem_direction` opcional

`build_melodic_transition_candidates` devuelve pares candidatos con intervalo
melódico, hueco temporal, solapamiento, coincidencia de plica, puntuación y
advertencias. No modifica eventos ni asigna voces.
