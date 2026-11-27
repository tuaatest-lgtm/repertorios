# Manifiesto de revisión humana de alturas

El CLI acepta `--pitch-review-manifest archivo.json`. El manifiesto representa decisiones ya confirmadas por una persona, no predicciones del detector.

Cada página requiere `reviewer_confirmed: true` y una entrada por cada cabeza geométrica, en el mismo orden que las listas `notehead_candidates` (filled) y `hollow_notehead_candidates` (hollow) del análisis. `source_index` es el índice local dentro de su lista. El orden se conserva para que los índices sigan enlazados con el timeline revisado; las cabezas deben estar en orden horizontal dentro de cada pentagrama y compás.

```json
{
  "schema_version": "1",
  "pages": [{
    "page_number": 1,
    "reviewer_confirmed": true,
    "heads": [{
      "source_kind": "filled",
      "source_index": 0,
      "measure_id": "p1-staff0-m1",
      "explicit_accidental": null,
      "simultaneous_group_id": "p1-s0-m1-chord1"
    }]
  }]
}
```

`explicit_accidental` admite `natural`, `sharp`, `flat`, `double_sharp`, `double_flat` o `null`. Las cabezas simultáneas del mismo acorde comparten `simultaneous_group_id`; las notas individuales pueden omitirlo. Las asignaciones incompletas, incompatibles o fuera de orden se rechazan.

Las claves y armaduras siguen requiriendo confirmación y suministro independiente. Las alturas solo se resuelven cuando existe clave suministrada/confirmada. Sin este manifiesto, el comportamiento previo se conserva.