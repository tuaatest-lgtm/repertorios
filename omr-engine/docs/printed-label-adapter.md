# Adaptador de etiquetas impresas a evidencia

`palermo_omr.printed_label_adapter` convierte candidatos reconocidos en la capa de texto PDF en objetos `StaffIdentityEvidence`.

## Regla de conversión

- Solo convierte candidatos con estado `associated_candidate` y un índice de pentagrama explícito.
- Omite candidatos ambiguos o no asignados; no elige por ellos.
- Comprueba que la página coincida con la estructura y que el índice detectado identifique un único pentagrama.
- Las etiquetas vocales se registran como `printed_voice_label`; las instrumentales como `printed_part_label`.
- Conserva la confianza del candidato como confianza de evidencia, no como probabilidad calibrada.

## Lo que deliberadamente no hace

El adaptador no crea `ScorePart`, `ScoreVoice`, `StaffIdentityProposal` ni `StaffAssignment`. Tampoco confirma que una etiqueta describa exclusivamente el pentagrama al que quedó asociada por proximidad. La evidencia se marca `source="visual_candidate"` y requiere revisión humana antes de cualquier identidad confirmada.

El adaptador no se conecta al CLI, al reproductor ni a Sonoro.
