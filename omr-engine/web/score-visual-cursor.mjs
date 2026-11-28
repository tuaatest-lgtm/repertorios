/**
 * Mapa temporal entre eventos de reproducción y geometría visual de la partitura.
 * No calcula coordenadas: exige anclajes explícitos producidos por el análisis
 * de página y conserva como unresolved los eventos sin correspondencia visual.
 */
export class ScoreVisualCursor {
  constructor(playbackProjection, visualAnchors) {
    if (!playbackProjection || playbackProjection.status !== "unconfirmed_playback_projection" ||
        !Array.isArray(playbackProjection.events)) {
      throw new TypeError("Se requiere una proyección temporal Palermo provisional");
    }
    if (!Array.isArray(visualAnchors)) {
      throw new TypeError("visualAnchors debe ser una lista de anclajes geométricos");
    }
    const anchors = new Map();
    for (const a of visualAnchors) {
      if (!a || typeof a.event_id !== "string" || !a.event_id ||
          anchors.has(a.event_id)) throw new TypeError("Cada anclaje requiere event_id único");
      for (const field of ["page_index", "system_index", "measure_index", "x", "y", "width", "height"]) {
        if (!Number.isFinite(a[field])) throw new TypeError("Anclaje inválido: " + field);
      }
      if (a.page_index < 0 || a.system_index < 0 || a.measure_index < 0 ||
          a.width <= 0 || a.height <= 0) throw new RangeError("Índices o dimensiones de anclaje inválidos");
      anchors.set(a.event_id, Object.freeze({ ...a }));
    }

    this.events = [];
    this.unresolved = [];
    this.unresolvedTimeline = [];
    const seen = new Set();
    for (const event of playbackProjection.events) {
      if (!event || typeof event.event_id !== "string" || !event.event_id ||
          seen.has(event.event_id)) throw new TypeError("Los eventos temporales deben tener ID único");
      seen.add(event.event_id);
      const start = event.start_seconds;
      const duration = event.duration_seconds;
      if (!Number.isFinite(start) || start < 0 || !Number.isFinite(duration) || duration <= 0) {
        throw new TypeError("El evento requiere inicio y duración válidos");
      }
      const anchor = anchors.get(event.event_id);
      if (!anchor) {
        this.unresolved.push({ event_id: event.event_id, reason: "missing_visual_anchor" });
        this.unresolvedTimeline.push({ event_id: event.event_id, start_seconds: start, end_seconds: start + duration });
        continue;
      }
      this.events.push(Object.freeze({
        event_id: event.event_id, voice_id: event.voice_id ?? null,
        event_type: event.event_type ?? "note",
        start_seconds: start, end_seconds: start + duration, anchor,
      }));
    }
    this.events.sort((a, b) => a.start_seconds - b.start_seconds ||
      a.anchor.page_index - b.anchor.page_index ||
      a.anchor.system_index - b.anchor.system_index || a.event_id.localeCompare(b.event_id));
    this.unresolved.sort((a, b) => a.event_id.localeCompare(b.event_id));
    this.duration_seconds = this.events.reduce((end, e) => Math.max(end, e.end_seconds), 0);
  }

  positionAt(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) {
      throw new RangeError("La posición temporal debe ser un número no negativo");
    }
    const started = this.events.filter(e => e.start_seconds <= seconds);
    const active = started.filter(e => seconds < e.end_seconds);
    const unresolvedActive = this.unresolvedTimeline.filter(e => e.start_seconds <= seconds && seconds < e.end_seconds);
    const focus = active.length ? active : (unresolvedActive.length ? [] : started.slice(-1));
    const pages = [...new Set(focus.map(e => e.anchor.page_index))].sort((a, b) => a - b);
    const systems = [...new Set(focus.map(e =>
      JSON.stringify([e.anchor.page_index, e.anchor.system_index])))].sort();
    const latest = [...focus].sort((a, b) => b.start_seconds - a.start_seconds)[0] ?? null;
    return {
      current_seconds: seconds,
      page_index: pages.length === 1 ? pages[0] : null,
      system_index: systems.length === 1 ? JSON.parse(systems[0])[1] : null,
      ambiguous_location: pages.length > 1 || systems.length > 1 || unresolvedActive.length > 0,
      active_event_ids: active.map(e => e.event_id),
      unresolved_active_event_ids: unresolvedActive.map(e => e.event_id),
      active_voices: [...new Set(active.map(e => e.voice_id).filter(Boolean))].sort(),
      highlights: active.map(e => ({
        event_id: e.event_id, voice_id: e.voice_id, event_type: e.event_type,
        page_index: e.anchor.page_index, system_index: e.anchor.system_index,
        measure_index: e.anchor.measure_index,
        x: e.anchor.x, y: e.anchor.y, width: e.anchor.width, height: e.anchor.height,
      })),
      focus_event_id: latest?.event_id ?? null,
      unresolved_visual_events: this.unresolved.length,
    };
  }

  nextBoundaryAfter(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) {
      throw new RangeError("La posición temporal debe ser un número no negativo");
    }
    const boundaries = this.events.flatMap(e => [e.start_seconds, e.end_seconds])
      .filter(value => value > seconds).sort((a, b) => a - b);
    return boundaries[0] ?? null;
  }
}
