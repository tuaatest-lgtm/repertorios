# Asignación revisada de voces

`apply_reviewed_voice_assignments` conecta contexto de pentagrama y
excepciones por evento con los candidatos de evento musical. El contexto
`human_confirmed` de un pentagrama puede asignar soprano/alto/tenor/bajo;
un override por evento permite separar voces que comparten pentagrama.

Un override pendiente bloquea el fallback al pentagrama para no confundir
líneas simultáneas. La asignación no promueve a `ready_for_review` hasta que
altura y duración ya estén resueltas; los silencios pueden recibir voz sin
tener pitch. Aun cuando el evento queda listo para revisión, sigue siendo
candidato, no una transcripción musical confirmada.
