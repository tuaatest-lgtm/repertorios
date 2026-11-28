import { WebAudioSink } from "./web-audio-playback.mjs";
import { LookaheadPlaybackController } from "./lookahead-playback-controller.mjs";
import { ScoreVisualCursor } from "./score-visual-cursor.mjs";
import { BrowserScorePlaybackSession } from "./score-playback-session.mjs";

/**
 * Cableado estándar del paquete OMR al audio y cursor del navegador.
 * El host crea AudioContext tras una interacción del usuario y suministra
 * el callback que navega el visor; no se accede al DOM ni a un visor concreto.
 */
export function createBrowserScorePlaybackSession(
  bundle,
  { audioContext, onPageChange = null, audioOptions = {}, lookaheadSeconds = 0.12 } = {},
) {
  if (!bundle || bundle.status !== "unconfirmed_score_playback_bundle" ||
      !bundle.command_stream || !bundle.visual_anchor_map ||
      !bundle.playback_projection) {
    throw new TypeError("Se requiere un paquete Palermo de reproducción provisional");
  }
  if (!Array.isArray(bundle.visual_anchor_map.anchors)) {
    throw new TypeError("El paquete no contiene anclajes visuales válidos");
  }
  const sink = new WebAudioSink({ audioContext, ...audioOptions });
  try {
    const player = new LookaheadPlaybackController(
      bundle.command_stream, sink, { lookaheadSeconds },
    );
    const cursor = new ScoreVisualCursor(
      bundle.playback_projection, bundle.visual_anchor_map.anchors,
    );
    const session = new BrowserScorePlaybackSession({
      player, visualCursor: cursor, onPageChange,
    });
    return {
      sink, player, cursor, session,
      dispose() {
        player.stop();
        sink.dispose();
      },
    };
  } catch (error) {
    sink.dispose();
    throw error;
  }
}
