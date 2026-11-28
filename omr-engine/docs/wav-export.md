# Exportación WAV

El renderizador WAV produce PCM16 estéreo desde un flujo polifónico de
`note_on`/`note_off`. Cada voz conserva su paneo y las duraciones de las notas
son independientes. El instrumento es un oscilador seno de prueba, no un banco
de sonidos General MIDI.

## Python

```python
from pathlib import Path
from palermo_omr.wav_renderer import render_score_playback_bundle_wav

audio = render_score_playback_bundle_wav(
    score_playback_bundle,
    sample_rate=22050,
    gain=0.22,
)
Path("preview.wav").write_bytes(audio)
```

## Terminal

```bash
palermo-omr-wav reviewed-score-bundle.json preview.wav \
  --sample-rate 22050 \
  --gain 0.22 \
  --voice-pan soprano:-0.8
```

La entrada puede ser un objeto `unconfirmed_score_playback_bundle` o un
`unconfirmed_synth_command_stream`. El comando crea el directorio de salida y
escribe el WAV de forma atómica. La salida sigue siendo provisional si los
eventos de origen no han sido confirmados musicalmente.

Para instrumentos General MIDI externos, usa el exportador MIDI; el WAV interno
es una salida de verificación y no pretende sonar como un coro real.
