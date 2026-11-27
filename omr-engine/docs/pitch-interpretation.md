# Interpretación de altura — Palermo OMR

El módulo `pitch.py` convierte una posición diatónica relativa al pentagrama en una altura escrita y un número MIDI, siempre que la clave ya sea conocida.

Claves soportadas: sol (treble), fa (bass), do en alto (alto) y do en tenor (tenor). La línea inferior corresponde respectivamente a E4, G2, F3 y D3.

La armadura se suministra como alteraciones por letra (por ejemplo `{"F": 1, "B": -1}`). Las alteraciones explícitas admitidas son natural, sostenido, bemol, doble sostenido y doble bemol. `MeasureAccidentals` conserva alteraciones explícitas por letra y octava hasta que se llama a `reset()` al comenzar un nuevo compás.

**Límite:** este módulo no detecta claves ni armaduras en la imagen. Tampoco resuelve todavía reglas editoriales avanzadas de alteraciones, ligaduras entre compases o notas enharmónicas. Es una etapa de interpretación musical que consume datos ya reconocidos.


## Alteraciones en acordes simultáneos

`build_pitch_candidates` acepta `simultaneous_group_ids` junto con
`measure_ids`. Cada ID identifica un ataque/acorde ya agrupado y revisado
humanamente. El motor registra primero todas las alteraciones explícitas del
acorde y después resuelve las demás cabezas. Por eso, una alteración aplicada
a una nota también afecta a otra nota simultánea con la misma letra y octava,
aunque su cabeza aparezca antes en la lista.

Los miembros de un grupo deben ser contiguos, pertenecer al mismo pentagrama y
compás, y estar en orden de lectura. Dos alteraciones explícitas incompatibles
para la misma nota escrita dentro del mismo acorde se rechazan. El agrupamiento
no se infiere por proximidad horizontal en esta etapa: debe venir de una
asignación de ataque/acorde revisada. La persistencia sigue limitada a la misma
letra y octava durante el compás y se reinicia en el siguiente.
