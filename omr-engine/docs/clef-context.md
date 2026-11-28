# Contexto de clave por pentagrama

`build_staff_clef_candidates` construye un registro de clave para cada
pentagrama solicitado en una página. Separa cuatro estados:

- `human_confirmed`: una etiqueta humana confirma una clave.
- `pending_human_review`: existen glifos sin etiqueta; la clave no se asigna.
- `conflicting_human_labels`: hay etiquetas humanas incompatibles.
- `no_clef_evidence`: no hay evidencia; no se aplica una clave predeterminada.

El registro conserva los IDs de glifos confirmados y pendientes. Una etiqueta
de sostenido, bemol u otro símbolo no se interpreta como clave. La geometría
de un glifo tampoco confirma por sí sola su identidad.

Este módulo prepara un contexto explícito para `pitch_candidates`, pero no
modifica ni resuelve alturas MIDI. La integración con el flujo de partitura
debe respetar los estados y no usar candidatos pendientes o conflictivos.
