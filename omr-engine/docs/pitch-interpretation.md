# Interpretación de altura — Palermo OMR

El módulo `pitch.py` convierte una posición diatónica relativa al pentagrama en una altura escrita y un número MIDI, siempre que la clave ya sea conocida.

Claves soportadas: sol (treble), fa (bass), do en alto (alto) y do en tenor (tenor). La línea inferior corresponde respectivamente a E4, G2, F3 y D3.

La armadura se suministra como alteraciones por letra (por ejemplo `{"F": 1, "B": -1}`). Las alteraciones explícitas admitidas son natural, sostenido, bemol, doble sostenido y doble bemol. `MeasureAccidentals` conserva alteraciones explícitas por letra y octava hasta que se llama a `reset()` al comenzar un nuevo compás.

**Límite:** este módulo no detecta claves ni armaduras en la imagen. Tampoco resuelve todavía reglas editoriales avanzadas de alteraciones, ligaduras entre compases o notas enharmónicas. Es una etapa de interpretación musical que consume datos ya reconocidos.
