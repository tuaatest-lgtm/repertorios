# Reproducción polifónica en navegador

El módulo `web/web-audio-playback.mjs` implementa un sink Web Audio y un scheduler
para el contrato `unconfirmed_synth_command_stream`. Cada nota tiene oscilador y
envolvente propios; cada voz tiene un bus de ganancia independiente. El reloj maestro
es `AudioContext.currentTime`, no el reloj de una página, por lo que el cambio de
página no reinicia el tiempo musical.

## Uso explícito (sin conectar Sonoro)

```js
import { WebAudioSink, BrowserPlaybackController } from "./web-audio-playback.mjs";

const context = new AudioContext();
const sink = new WebAudioSink({ audioContext: context });
const player = new BrowserPlaybackController(commandStream, sink);
await player.play();
const frame = () => {
  player.tick();
  if (player.state === "playing") requestAnimationFrame(frame);
};
requestAnimationFrame(frame);
// player.pause(); await player.resume(); player.set_voice_muted("alto", true);
// player.stop(); sink.dispose();
```

El cursor visual puede consultar `player.current_seconds` para leer el reloj maestro directamente, incluso entre ticks de la interfaz. La aplicación debe crear el AudioContext como consecuencia de una acción del usuario
(por las políticas de autoplay), llamar `tick()` continuamente mientras reproduce y
cerrar el sink al desmontar el reproductor. Esta capa sintetiza tonos básicos; no es
todavía un instrumento GM ni está conectada a index.html/Sonoro. El scheduler usa
ticks de navegador y no anticipa eventos mediante look-ahead, por lo que bloqueos
prolongados del hilo principal pueden introducir retardo. Los eventos y alturas siguen
siendo provisionales hasta validar el reconocimiento OMR.
