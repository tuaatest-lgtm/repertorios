# Integración del contexto de notación con alturas

`build_pitch_candidates_with_notation_context` conecta tres etapas sin
confundir candidatos con hechos:

1. Obtiene las claves por pentagrama desde el manifiesto de glifos.
2. Solo usa claves con estado `human_confirmed`.
3. Calcula candidatos de armadura por posición y secuencia, pero solo aplica
   una armadura si el pentagrama aparece explícitamente en
   `accepted_key_signature_staff_indices`.
4. Envía el contexto confirmado a `build_pitch_candidates`.

Los candidatos de armadura no aceptados permanecen en el resultado para
auditoría y no alteran MIDI. Los pentagramas sin clave confirmada mantienen
sus alturas como `unresolved_clef`. El resultado incluye las evidencias,
candidatos de armadura, armaduras aplicadas y alturas resultantes.

Esta integración no afirma reconocer automáticamente claves ni alteraciones
desde una imagen; consume las etiquetas y geometrías disponibles.
