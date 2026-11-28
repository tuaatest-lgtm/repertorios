# Exportación Standard MIDI

`midi_export.py` convierte un `unconfirmed_synth_command_stream` en un
archivo Standard MIDI File (SMF) tipo 1 usando únicamente la biblioteca
estándar de Python.

## Uso

```python
from pathlib import Path
from palermo_omr.midi_export import render_polyphonic_midi

midi_bytes = render_polyphonic_midi(
    command_stream,
    tempo_bpm=96,
    default_program=52,  # GM Choir Aahs
    time_signature=(4, 4),
    key_signature=(5, 0),  # cinco sostenidos, mayor
)
Path("partitura.mid").write_bytes(midi_bytes)
```

## Comportamiento

- Una pista y un canal MIDI independiente por voz; reserva el canal 10
  (índice 9) para percusión.
- Los acordes se expanden en notas simultáneas.
- Cada nota conserva su propio inicio y final; al mismo tick, note-off precede
  a un nuevo note-on de la misma altura.
- Incluye pista conductora con tempo, compás y armadura opcionales, además de PPQ configurable.
- `render_score_playback_bundle_midi(bundle, ...)` exporta directamente el flujo de comandos de un paquete de reproducción multipágina.
- Programa General MIDI predeterminado 52 (Choir Aahs), con opción de cambiar
  programa, canal y paneo por voz.
- Las voces soprano, alto, tenor y bajo tienen paneo predeterminado separado.
- Rechaza notas sin pareja, duraciones que colapsan a cero ticks y notas de la
  misma altura solapadas en un mismo canal/voz, porque SMF no puede emparejar
  esas notas por el ID de evento de origen.

El archivo no incorpora un sintetizador ni un soundfont. Para oír instrumentos
General MIDI se abre en un reproductor o sintetizador externo que disponga de
un banco de sonidos. El renderizador WAV interno continúa siendo una salida de
prueba con oscilador seno; este exportador ofrece una ruta distinta hacia
instrumentos GM externos.

## Estado musical

El exportador no cambia el estado de revisión de los eventos. Si la proyección
contiene candidatos no confirmados, el MIDI resultante también es provisional.
No se afirma que las notas exportadas sean una transcripción correcta del PDF.
