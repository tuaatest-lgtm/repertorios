# Manifiesto de revisión humana de alturas

El CLI acepta `--pitch-review-manifest archivo.json`. El manifiesto representa decisiones ya confirmadas por una persona, no predicciones del detector.

Cada página requiere `reviewer_confirmed: true` y una entrada por cada cabeza geométrica, en el mismo orden que las listas `notehead_candidates` (`filled`) y `hollow_notehead_candidates` (`hollow`) del análisis. `source_index` es el índice local dentro de su lista. Cada entrada debe incluir `measure_id` y `event_order` entero no negativo. Las cabezas del mismo ataque comparten `event_order` y `simultaneous_group_id`.

Ejemplo:
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
      "event_order": 0,
      "explicit_accidental": null,
      "simultaneous_group_id": "p1-s0-m1-e0"
    }]
  }]
}
```

`explicit_accidental` admite `natural`, `sharp`, `flat`, `double_sharp`, `double_flat` o `null`. Las cabezas simultáneas del mismo ataque deben compartir un `simultaneous_group_id`; si varias cabezas comparten `event_order` y no comparten grupo, el CLI rechaza la asignación. Las notas individuales pueden omitir el grupo.

El CLI ordena internamente por pentagrama, compás, `event_order` y posición horizontal para procesar el estado de alteraciones de izquierda a derecha. Después restaura el orden geométrico original y conserva `source_index`, de modo que la altura revisada siga enlazada con la cabeza y el timeline.

El manifiesto debe cubrir todas las cabezas detectadas exactamente una vez. Las asignaciones incompletas, duplicadas, incompatibles o fuera de orden se rechazan.

Las claves y armaduras siguen requiriendo confirmación y suministro independiente. Las alturas solo se resuelven cuando existe clave suministrada/confirmada. Sin este manifiesto, el comportamiento previo se conserva.