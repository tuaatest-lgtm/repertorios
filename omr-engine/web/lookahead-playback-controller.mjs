/**
 * Scheduler Web Audio con ventana de anticipación. Separa el estado musical
 * actual (para cursor/pausa) de los comandos ya programados en AudioContext.
 */
export class LookaheadPlaybackController {
  constructor(commandStream, sink, { lookaheadSeconds = 0.12 } = {}) {
    if (!commandStream || commandStream.status !== "unconfirmed_synth_command_stream" ||
        !Array.isArray(commandStream.commands)) {
      throw new TypeError("Se requiere un flujo de comandos Palermo provisional");
    }
    if (!sink || !sink.context ||
        !["note_on", "note_off", "all_notes_off", "set_voice_muted"].every(k => typeof sink[k] === "function")) {
      throw new TypeError("El sink debe implementar el contrato Web Audio programable");
    }
    if (!Number.isFinite(lookaheadSeconds) || lookaheadSeconds < 0.02 || lookaheadSeconds > 0.5) {
      throw new RangeError("lookaheadSeconds debe estar entre 0.02 y 0.5");
    }
    this.commands = [...commandStream.commands].map(c => ({ ...c })).sort((a, b) =>
      a.time_seconds - b.time_seconds ||
      (a.command === "note_off" ? 0 : 1) - (b.command === "note_off" ? 0 : 1) ||
      a.voice_id.localeCompare(b.voice_id) || a.midi - b.midi);
    for (const c of this.commands) {
      if (!c || !["note_on", "note_off"].includes(c.command) ||
          !Number.isFinite(c.time_seconds) || c.time_seconds < 0 ||
          typeof c.voice_id !== "string" || !c.voice_id ||
          typeof c.event_id !== "string" || !c.event_id ||
          !Number.isInteger(c.midi) || c.midi < 0 || c.midi > 127) {
        throw new TypeError("Comando de audio inválido");
      }
    }
    this.sink = sink;
    this.lookaheadSeconds = lookaheadSeconds;
    this.index = 0;
    this.scheduledIndex = 0;
    this.elapsed = 0;
    this.anchor = null;
    this.state = "stopped";
    this.active = new Map();
    this.muted = new Set();
  }

  async play() {
    this.sink.all_notes_off();
    this.index = 0;
    this.scheduledIndex = 0;
    this.elapsed = 0;
    this.active.clear();
    if (this.sink.context.state === "suspended") await this.sink.context.resume();
    this.anchor = this.sink.context.currentTime;
    this.state = "playing";
    return this.tick();
  }

  tick() {
    if (this.state !== "playing") return this.snapshot();
    const now = this.sink.context.currentTime;
    this.elapsed = Math.max(0, now - this.anchor);

    // Estado lógico exacto al tiempo presente: lo usa el cursor, no el look-ahead.
    while (this.index < this.commands.length &&
           this.commands[this.index].time_seconds <= this.elapsed) {
      const c = this.commands[this.index++];
      const key = this.#key(c);
      if (c.command === "note_on") {
        if (this.active.has(key)) throw new Error("note_on duplicado");
        this.active.set(key, c);
      } else {
        if (!this.active.has(key)) throw new Error("note_off sin note_on");
        this.active.delete(key);
      }
    }

    // Audio se programa sobre el reloj del dispositivo, adelantado respecto al UI.
    const horizon = this.elapsed + this.lookaheadSeconds;
    while (this.scheduledIndex < this.commands.length &&
           this.commands[this.scheduledIndex].time_seconds <= horizon) {
      const c = this.commands[this.scheduledIndex++];
      const when = Math.max(now, this.anchor + c.time_seconds);
      if (c.command === "note_on") {
        this.sink.note_on(c.voice_id, c.midi, c.event_id, when);
      } else {
        this.sink.note_off(c.voice_id, c.midi, c.event_id, when);
      }
    }

    if (this.index === this.commands.length && this.active.size === 0) {
      this.state = "finished";
      this.anchor = null;
    }
    return this.snapshot();
  }

  pause() {
    if (this.state !== "playing") return this.snapshot();
    this.tick();
    if (this.state !== "playing") return this.snapshot();
    this.elapsed = Math.max(0, this.sink.context.currentTime - this.anchor);
    this.anchor = null;
    this.state = "paused";
    this.sink.all_notes_off();
    // Descarta comandos futuros cancelados por all_notes_off; el reloj lógico se conserva.
    this.scheduledIndex = this.index;
    return this.snapshot();
  }

  async resume() {
    if (this.state !== "paused") return this.snapshot();
    if (this.sink.context.state === "suspended") await this.sink.context.resume();
    this.anchor = this.sink.context.currentTime - this.elapsed;
    this.state = "playing";
    for (const c of this.active.values()) {
      this.sink.note_on(c.voice_id, c.midi, c.event_id, this.sink.context.currentTime);
    }
    this.scheduledIndex = this.index;
    return this.tick();
  }

  stop() {
    this.sink.all_notes_off();
    this.index = 0;
    this.scheduledIndex = 0;
    this.elapsed = 0;
    this.anchor = null;
    this.active.clear();
    this.state = "stopped";
    return this.snapshot();
  }

  set_voice_muted(voiceId, muted) {
    if (typeof voiceId !== "string" || !voiceId || typeof muted !== "boolean") {
      throw new TypeError("voiceId y muted inválidos");
    }
    if (muted) this.muted.add(voiceId);
    else this.muted.delete(voiceId);
    this.sink.set_voice_muted(voiceId, muted);
    return this.snapshot();
  }

  get current_seconds() {
    if (this.state === "playing" && this.anchor !== null) {
      return Math.max(0, this.sink.context.currentTime - this.anchor);
    }
    return this.elapsed;
  }

  snapshot() {
    return {
      state: this.state, current_seconds: this.current_seconds,
      processed_commands: this.index, scheduled_commands: this.scheduledIndex,
      total_commands: this.commands.length, active_notes: this.active.size,
      muted_voices: [...this.muted].sort(),
    };
  }

  #key(command) {
    return JSON.stringify([command.voice_id, command.event_id, command.midi]);
  }
}
