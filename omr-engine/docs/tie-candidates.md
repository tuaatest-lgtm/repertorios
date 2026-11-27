# Candidatos de ligadura de prolongación

El módulo `tie_candidates.py` combina tres fuentes que deben estar disponibles
antes de proponer una ligadura:

1. Eventos de nota con altura MIDI, voz revisada, pentagrama, tiempo global y
   caja de la cabeza de nota.
2. Candidatos geométricos de arco de `detect_tie_slur_shape_candidates`.
3. Continuidad temporal exacta entre el final de la nota de origen y el inicio
   de la nota siguiente de esa misma voz.

Solo propone pares consecutivos de la misma voz y pentagrama, con la misma
altura MIDI y un arco cuya caja cubre geométricamente el espacio entre las
cabezas. La comparación temporal usa unidades musicales exactas, no píxeles.
El tiempo debe ser global para poder representar ligaduras que cruzan barras
de compás.

## Estados y límites

- `proposed_tie`: se cumplen las condiciones necesarias, pero no confirma la
  ligadura.
- `ambiguous_tie_candidate`: un arco o un par admite varias correspondencias.

La igualdad MIDI no garantiza que ambas notas tengan la misma escritura
enarmónica. Una curva también puede ser una ligadura de expresión u otra marca.
Por tanto, todas las propuestas requieren revisión humana. No se clasifican
automáticamente los arcos que no cumplen las condiciones como slurs: pueden
ser arcos editoriales, errores geométricos o detecciones incompletas.

La función `build_reviewed_tie_durations` permite sumar las dos duraciones
solo después de que una persona confirme explícitamente que el arco es una
ligadura de prolongación y que ambas notas tienen la misma escritura musical.
Rechaza propuestas ambiguas o confirmaciones incompletas. La función `apply_reviewed_tie_chains_to_timeline` integra cadenas confirmadas
en la línea temporal revisada: conserva el primer ataque, suma la duración,
retira los ataques intermedios y registra `tied_event_ids` y
`reviewed_tie_chains` para trazabilidad. La integración se ejecuta desde
`build_reviewed_page_timelines` cuando el compás contiene `tie_candidates` y
`tie_confirmations` en el manifiesto `--reviewed-rhythm-manifest`. No está
conectada a Sonoro ni produce detección automática de ligaduras.

## Integración en el manifiesto de ritmo revisado

Dentro de cada objeto de `measures`, se pueden incluir las propuestas y las
confirmaciones. Los índices de confirmación apuntan a la lista local de
`tie_candidates` de ese compás:

```json
{
  "measure_index": 0,
  "numerator": 4,
  "denominator": 4,
  "confirmed_event_ids": ["n1", "n2"],
  "event_voice_ids": {"n1": "soprano", "n2": "soprano"},
  "tie_candidates": [{
    "arc_id": "arc-1",
    "source_event_id": "n1",
    "target_event_id": "n2",
    "status": "proposed_tie",
    "pitch_match": true,
    "temporal_continuity": true,
    "geometry_score": 0.9,
    "warnings": []
  }],
  "tie_confirmations": [{
    "candidate_index": 0,
    "reviewer_confirmed": true,
    "arc_is_tie_confirmed": true,
    "same_notated_pitch_confirmed": true
  }]
}
```

Los dos eventos deben estar incluidos en el mismo compás y pertenecer a la
misma voz; deben tener inicio y duración conocidos y continuidad temporal
exacta. Si hay alturas confirmadas en ambos eventos, deben coincidir. Los
cruces de compás o página se rechazan deliberadamente hasta que exista una
línea temporal global revisada que los pueda validar sin reiniciar el tiempo
local de cada compás. Las confirmaciones no se infieren de `geometry_score`.
