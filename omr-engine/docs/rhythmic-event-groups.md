# Agrupación de eventos rítmicos candidatos

El módulo `palermo_omr.rhythmic_event_groups` reúne cabezas de nota del mismo
pentagrama que podrían representar un único ataque (por ejemplo, un acorde).
La coordenada horizontal se utiliza únicamente como evidencia geométrica para
proponer agrupaciones; no se convierte en duración ni en tiempo musical.

## Criterios

- Agrupa cabezas cercanas en x usando el espaciado entre líneas del pentagrama
  como escala, sin comparar píxeles absolutos entre partituras.
- Mantiene separados los pentagramas.
- Exige coherencia de dirección de plica para proponer un acorde.
- Si encuentra plicas opuestas, ausencia de dirección suficiente o duraciones
  candidatas incompatibles, marca el conjunto como `ambiguous`.
- Las duraciones solo se conservan como candidatas y se expresan en negras
  mediante `Fraction`; un grupo ambiguo no recibe duración utilizable.
- Una asignación de voz solo se conserva si el llamador la proporciona
  explícitamente en `staff_voice_ids`. El módulo no decide si el pentagrama es
  soprano, alto, tenor, bajo, mano derecha o mano izquierda.

## Estados

- `single_note_candidate`: una cabeza aislada, todavía no confirmada.
- `proposed_chord`: varias cabezas alineadas y con dirección de plica
  compatible; requiere revisión visual.
- `ambiguous`: evidencia contradictoria o insuficiente para establecer un
  ataque conjunto.

Todos los resultados son propuestas geométricas. Ni siquiera
`proposed_chord` es un acorde musical confirmado. Los grupos no se convierten
automáticamente en `OrderedVoiceEvent` ni en eventos de la línea temporal.

## Límites actuales

La alineación horizontal puede confundir notas simultáneas de voces distintas
con un acorde, especialmente cuando las voces comparten dirección de plica.
También puede no reunir cabezas de un acorde con desplazamientos horizontales
inusuales. La tolerancia es un parámetro configurable, no una calibración
universal. No se reconocen todavía voces independientes dentro de un mismo
pentagrama, silencios, puntillos ni ligaduras. Las figuras rítmicas de entrada
siguen siendo hipótesis de los detectores anteriores.

Por seguridad musical, los próximos módulos deben mantener los casos dudosos
sin resolver en lugar de forzar una secuencia temporal.
