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

Las funciones `build_reviewed_tie_durations` y
`build_reviewed_tie_chains` suman duraciones solo después de que una persona
confirme explícitamente que el arco es una ligadura de prolongación y que ambas
notas tienen la misma escritura musical. Se rechazan propuestas ambiguas,
confirmaciones incompletas, bifurcaciones, fusiones y ciclos.

## Integración en el manifiesto revisado

Hay dos ámbitos admitidos:

### 1. Ligaduras dentro de un compás

Las propuestas y confirmaciones pueden estar dentro de un objeto de
`measures`. Los índices de confirmación apuntan a la lista local de
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

Los dos eventos deben pertenecer al mismo compás y a la misma voz; deben tener
inicio y duración conocidos y continuidad temporal exacta.

### 2. Ligaduras entre compases consecutivos de una misma página

Cuando una ligadura cruza una barra de compás, las propuestas y confirmaciones
se colocan en el nivel de página, como hermanos de `page_number` y
`measures`, no dentro de un compás. Los IDs de origen y destino deben
pertenecer a eventos confirmados de esa página:

```json
{
  "page_number": 1,
  "measures": [
    {
      "measure_index": 0,
      "numerator": 4,
      "denominator": 4,
      "confirmed_event_ids": ["n1"],
      "event_voice_ids": {"n1": "alto"}
    },
    {
      "measure_index": 1,
      "numerator": 4,
      "denominator": 4,
      "confirmed_event_ids": ["n2"],
      "event_voice_ids": {"n2": "alto"}
    }
  ],
  "tie_candidates": [{
    "arc_id": "arc-page-1",
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

La integración de página calcula offsets acumulados con la métrica de cada
compás. Solo admite continuidad entre compases consecutivos presentes en la
secuencia revisada; no presume continuidad si falta un índice de compás. Se
exige misma voz, eventos de tipo nota y continuidad temporal global exacta.
Si ambas notas tienen alturas confirmadas, estas deben coincidir. La nota
inicial conserva el ataque y recibe la duración combinada; los eventos de
destino dejan de generar ataques y quedan registrados en
`tied_event_ids`.

### 3. Ligaduras entre páginas consecutivas

El manifiesto de documento puede incluir `cross_page_tie_candidates` y
`cross_page_tie_confirmations` en el nivel superior, junto a `pages`. Los
índices de confirmación apuntan a la lista global de candidatos:

```json
{
  "cross_page_tie_candidates": [{
    "arc_id": "arc-page-1-2",
    "source_event_id": "last-note-page-1",
    "target_event_id": "first-note-page-2",
    "status": "proposed_tie",
    "pitch_match": true,
    "temporal_continuity": true,
    "geometry_score": 0.9,
    "warnings": []
  }],
  "cross_page_tie_confirmations": [{
    "candidate_index": 0,
    "reviewer_confirmed": true,
    "arc_is_tie_confirmed": true,
    "same_notated_pitch_confirmed": true
  }]
}
```

Para aplicar estas ligaduras, el manifiesto debe incluir las páginas
consecutivas completas en orden, con todos sus compases revisados desde el
índice 0 y sin huecos. La nota de origen debe estar en el último compás de la
página y la nota de destino en el primero de la siguiente. El motor calcula
offsets globales a partir de las métricas revisadas, exige continuidad exacta,
misma voz y eventos de tipo nota. Si ambas alturas están confirmadas, también
deben coincidir. La nota inicial conserva un solo ataque y recibe la duración
combinada; la nota de destino se elimina de los ataques reproducibles y queda
registrada en `tied_event_ids`.

Si falta una página o un compás, el motor rechaza la operación en vez de
suponer que el tiempo local continúa. Las propuestas siguen requiriendo
confirmación humana; no se detectan ni confirman ligaduras automáticamente y
esta salida no está conectada a Sonoro.
