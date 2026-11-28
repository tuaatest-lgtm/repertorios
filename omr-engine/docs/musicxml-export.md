# Exportación MusicXML

`musicxml_export.py` serializa líneas temporales revisadas en MusicXML 4.0
(partwise). Cada voz se convierte en una parte independiente; acordes,
silencios, duraciones exactas, puntillos, tupletos y ligaduras se conservan.

## Requisitos de entrada

Cada compás debe tener:

- `status = placed_events_only`, sin inicios/duraciones desconocidos,
  solapamientos ni desbordes;
- eventos con `voice_id`, `onset_quarters`, `duration_quarters` y
  `event_type`;
- alturas confirmadas en cada nota, con `step`, `octave` y `alteration`;
- un evento o silencio explícito para cada voz en cada compás.

El exportador rechaza compases incompletos y no inventa silencios, alturas,
figuras ni números de compás. Los eventos simultáneos de una voz se escriben
como acordes si comparten duración y tipo. Cada parte mantiene su propia
secuencia temporal, por lo que las voces pueden tener duraciones independientes.

## Python

```python
from pathlib import Path
from palermo_omr.musicxml_export import render_reviewed_timelines_musicxml

musicxml = render_reviewed_timelines_musicxml(
    reviewed_timelines,
    title="Clamaré a Dios",
    tempo_bpm=96,
    key_signature=(5, "major"),
)
Path("Clamare.musicxml").write_bytes(musicxml)
```

## Terminal

```bash
palermo-omr-musicxml reviewed-timelines.json salida.musicxml \
  --title "Clamaré a Dios" \
  --tempo-bpm 96 \
  --key-signature 5:major
```

La entrada puede ser una lista JSON de compases o un objeto con la propiedad
`timelines`. Para conservar numeración global de compases a través de páginas,
se puede proporcionar un JSON adicional con claves `"pagina:indice"`:

```bash
palermo-omr-musicxml reviewed-timelines.json salida.musicxml \
  --global-measure-numbers measure-map.json
```

MusicXML es una salida de notación editable; no es audio y no confirma que la
partitura original haya sido reconocida correctamente. La exportación solo
incluye los eventos que ya están revisados y completos.
