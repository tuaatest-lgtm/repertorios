# Adjunción de alteraciones a cabezas de nota

`attach_reviewed_accidentals` relaciona un glifo de alteración ya confirmado
visualmente con una cabeza candidata del mismo pentagrama y compás. Usa la
distancia horizontal desde el borde del glifo y la distancia vertical entre
centros, normalizadas por el espaciado del pentagrama.

No detecta sostenidos/bemoles desde píxeles ni decide qué nota debe alterarse.
Cuando hay dos destinos igualmente plausibles, contexto ausente o más de un
glifo apuntando a la misma cabeza, conserva el caso como unresolved.

La salida permanece `pending_human_attachment_review`. Solo después de que
una persona acepte los IDs de alteración, `build_accepted_explicit_accidentals`
genera la lista alineada que puede suministrarse a `build_pitch_candidates`.
Así se preserva la regla musical de alteraciones por compás sin promover una
asociación geométrica dudosa a altura MIDI.
