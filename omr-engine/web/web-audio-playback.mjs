/**
 * Adaptador Web Audio para el flujo polifónico Palermo.
 *
 * No se importa desde index.html: el host debe instanciarlo explícitamente.
 * Cada nota usa su propio oscilador y envolvente; cada voz tiene un bus de
 * ganancia independiente. El reloj maestro es AudioContext.currentTime.
 */
export class WebAudioSink {
  constructor({ audioContext, masterGain = 0.18, waveform = "triangle", releaseSeconds = 0.035 } = {}) {
    if (!audioContext || typeof audioContext.createOscillator !== "function" ||
        typeof audioContext.createGain !== "function" || !audioContext.destination) {
      throw new TypeError("Se requiere un AudioContext compatible con Web Audio");
    }
    if (!Number.isFinite(masterGain) || masterGain <= 0 || masterGain > 1) {
      throw new RangeError("masterGain debe estar entre 0 y 1");
    }
    if (!["sine", "triangle", "square", "sawtooth"].includes(waveform)) {
      throw new TypeError("Forma de onda no válida");
    }
    if (!Number.isFinite(releaseSeconds) || releaseSeconds <= 0 || releaseSeconds > 1) {
      throw new RangeError("releaseSeconds debe estar entre 0 y 1");
    }
    this.context = audioContext;
    this.waveform = waveform;
    this.releaseSeconds = releaseSeconds;
    this.master = audioContext.createGain();
    this.master.gain.value = masterGain;
    this.master.connect(audioContext.destination);
    this.voices = new Map();
    this.notes = new Map();
    this.disposed = false;
  }

  #assertLive() {
    if (this.disposed) throw new Error("El adaptador de audio ya fue cerrado");
  }

  #voiceBus(voiceId) {
    let bus = this.voices.get(voiceId);
    if (!bus) {
      bus = this.context.createGain();
      bus.gain.value = 1;
      bus.connect(this.master);
      this.voices.set(voiceId, bus);
    }
    return bus;
  }

  note_on(voiceId, midi, eventId) {
    this.#assertLive();
    if (typeof voiceId !== "string" || !voiceId || typeof eventId !== "string" || !eventId ||
        !Number.isInteger(midi) || midi < 0 || midi > 127) {
      throw new TypeError("note_on requiere voz, evento y MIDI válidos");
    }
    const key = this.#key(voiceId, eventId, midi);
    if (this.notes.has(key)) throw new Error("La nota ya está activa");
    const now = this.context.currentTime;
    const oscillator = this.context.createOscillator();
    const envelope = this.context.createGain();
    oscillator.type = this.waveform;
    oscillator.frequency.setValueAtTime(440 * (2 ** ((midi - 69) / 12)), now);
    envelope.gain.setValueAtTime(0.0001, now);
    const attackSeconds = 0.012;
    envelope.gain.exponentialRampToValueAtTime(0.7, now + attackSeconds);
    oscillator.connect(envelope);
    envelope.connect(this.#voiceBus(voiceId));
    oscillator.start(now);
    this.notes.set(key, { oscillator, envelope, voiceId, midi, eventId, startedAt: now, attackSeconds });
  }

  note_off(voiceId, midi, eventId) {
    this.#assertLive();
    const key = this.#key(voiceId, eventId, midi);
    const note = this.notes.get(key);
    if (!note) return;
    const now = this.context.currentTime;
    note.envelope.gain.cancelScheduledValues(now);
    const attackProgress = Math.max(0, Math.min(1, (now - note.startedAt) / note.attackSeconds));
    const heldGain = 0.0001 * (0.7 / 0.0001) ** attackProgress;
    note.envelope.gain.setValueAtTime(Math.max(heldGain, 0.0001), now);
    note.envelope.gain.exponentialRampToValueAtTime(0.0001, now + this.releaseSeconds);
    note.oscillator.stop(now + this.releaseSeconds + 0.005);
    this.notes.delete(key);
  }

  set_voice_muted(voiceId, muted) {
    this.#assertLive();
    if (typeof voiceId !== "string" || !voiceId || typeof muted !== "boolean") {
      throw new TypeError("Se requiere voiceId y muted booleano");
    }
    const bus = this.#voiceBus(voiceId);
    const now = this.context.currentTime;
    bus.gain.cancelScheduledValues(now);
    bus.gain.setTargetAtTime(muted ? 0 : 1, now, 0.008);
  }

  all_notes_off() {
    if (this.disposed) return;
    const now = this.context.currentTime;
    for (const note of this.notes.values()) {
      try {
        note.envelope.gain.cancelScheduledValues(now);
        note.envelope.gain.setValueAtTime(0.0001, now);
        note.oscillator.stop(now + 0.002);
      } catch { /* stop() may already have been requested */ }
    }
    this.notes.clear();
  }

  dispose() {
    if (this.disposed) return;
    this.all_notes_off();
    for (const bus of this.voices.values()) {
      try { bus.disconnect(); } catch { /* already disconnected */ }
    }
    this.voices.clear();
    this.master.disconnect();
    this.disposed = true;
  }

  #key(voiceId, eventId, midi) {
    return JSON.stringify([voiceId, eventId, midi]);
  }
}

/**
 * Scheduler liviano para el navegador. Llamar tick() desde requestAnimationFrame
 * o un timer de alta resolución; usar siempre audioContext.currentTime.
 * El motor no conoce páginas: la línea temporal es global a toda la partitura.
 */
export class BrowserPlaybackController {
  constructor(commandStream, sink) {
    if (!commandStream || commandStream.status !== "unconfirmed_synth_command_stream" ||
        !Array.isArray(commandStream.commands)) {
      throw new TypeError("Se requiere un flujo de comandos Palermo provisional");
    }
    for (const c of commandStream.commands) {
      if (!c || !["note_on", "note_off"].includes(c.command) ||
          !Number.isFinite(c.time_seconds) || c.time_seconds < 0 ||
          typeof c.voice_id !== "string" || !c.voice_id ||
          typeof c.event_id !== "string" || !c.event_id ||
          !Number.isInteger(c.midi) || c.midi < 0 || c.midi > 127) {
        throw new TypeError("Comando de audio inválido");
      }
    }
    if (!sink || !["note_on", "note_off", "all_notes_off"].every(k => typeof sink[k] === "function")) {
      throw new TypeError("El sink no implementa el contrato Palermo");
    }
    this.commands = [...commandStream.commands].sort((a, b) =>
      a.time_seconds - b.time_seconds ||
      (a.command === "note_off" ? 0 : 1) - (b.command === "note_off" ? 0 : 1) ||
      a.voice_id.localeCompare(b.voice_id) || a.midi - b.midi);
    this.sink = sink;
    this.index = 0;
    this.elapsed = 0;
    this.anchor = null;
    this.state = "stopped";
    this.muted = new Set();
    this.active = new Map();
  }

  async play() {
    this.sink.all_notes_off();
    this.index = 0;
    this.elapsed = 0;
    this.active.clear();
    if (this.sink.context?.state === "suspended") await this.sink.context.resume();
    this.anchor = this.sink.context.currentTime;
    this.state = "playing";
    return this.tick();
  }

  tick() {
    if (this.state !== "playing") return this.snapshot();
    const now = this.sink.context.currentTime;
    this.elapsed = Math.max(0, now - this.anchor);
    while (this.index < this.commands.length && this.commands[this.index].time_seconds <= this.elapsed) {
      const c = this.commands[this.index++];
      const key = JSON.stringify([c.voice_id, c.event_id, c.midi]);
      if (c.command === "note_on") {
        if (this.active.has(key)) throw new Error("note_on duplicado");
        this.active.set(key, c);
        if (!this.muted.has(c.voice_id)) this.sink.note_on(c.voice_id, c.midi, c.event_id);
      } else {
        if (!this.active.has(key)) throw new Error("note_off sin note_on");
        this.active.delete(key);
        if (!this.muted.has(c.voice_id)) this.sink.note_off(c.voice_id, c.midi, c.event_id);
      }
    }
    if (this.index === this.commands.length && this.active.size === 0) {
      this.state = "finished";
      this.anchor = null;
      this.sink.all_notes_off();
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
    return this.snapshot();
  }

  async resume() {
    if (this.state !== "paused") return this.snapshot();
    if (this.sink.context?.state === "suspended") await this.sink.context.resume();
    this.anchor = this.sink.context.currentTime - this.elapsed;
    this.state = "playing";
    for (const c of this.active.values()) {
      if (!this.muted.has(c.voice_id)) this.sink.note_on(c.voice_id, c.midi, c.event_id);
    }
    return this.snapshot();
  }

  stop() {
    this.sink.all_notes_off();
    this.index = 0;
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
    this.sink.set_voice_muted?.(voiceId, muted);
    if (this.state === "playing") {
      for (const c of this.active.values()) {
        if (c.voice_id !== voiceId) continue;
        if (muted) this.sink.note_off(c.voice_id, c.midi, c.event_id);
        else this.sink.note_on(c.voice_id, c.midi, c.event_id);
      }
    }
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
      processed_commands: this.index, total_commands: this.commands.length,
      active_notes: this.active.size, muted_voices: [...this.muted].sort(),
    };
  }
}
