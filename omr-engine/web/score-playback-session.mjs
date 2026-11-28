import { ScoreVisualCursor } from "./score-visual-cursor.mjs";

/**
 * Une el reloj de reproducción con la posición visual de la partitura.
 * El host entrega onPageChange para cambiar la página renderizada; esta capa
 * no depende de un visor PDF concreto ni modifica la interfaz existente.
 */
export class BrowserScorePlaybackSession {
  constructor({ player, visualCursor, onPageChange = null }) {
    if (!player || typeof player.tick !== "function" ||
        typeof player.play !== "function" || typeof player.pause !== "function" ||
        typeof player.resume !== "function" || typeof player.stop !== "function" ||
        typeof player.snapshot !== "function" ||
        !(visualCursor instanceof ScoreVisualCursor)) {
      throw new TypeError("Se requiere reproductor y cursor visual Palermo");
    }
    if (onPageChange !== null && typeof onPageChange !== "function") {
      throw new TypeError("onPageChange debe ser una función");
    }
    this.player = player;
    this.visualCursor = visualCursor;
    this.onPageChange = onPageChange;
    this.lastPage = null;
  }

  async play() {
    await this.player.play();
    this.lastPage = null;
    return this.frame();
  }

  pause() {
    this.player.pause();
    return this.frame();
  }

  async resume() {
    await this.player.resume();
    return this.frame();
  }

  stop() {
    this.player.stop();
    this.lastPage = null;
    return this.frame();
  }

  frame() {
    this.player.tick();
    const playback = this.player.snapshot();
    const visual = this.visualCursor.positionAt(playback.current_seconds);
    if (!visual.ambiguous_location && visual.page_index !== null &&
        visual.page_index !== this.lastPage) {
      this.lastPage = visual.page_index;
      this.onPageChange?.({
        page_index: visual.page_index,
        system_index: visual.system_index,
        current_seconds: playback.current_seconds,
      });
    }
    return { playback, visual };
  }
}
