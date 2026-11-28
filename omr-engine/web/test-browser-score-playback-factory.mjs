import test from "node:test";
import assert from "node:assert/strict";
import { createBrowserScorePlaybackSession } from "./browser-score-playback-factory.mjs";

class Param {
  constructor(value = 0) { this.value = value; }
  setValueAtTime(v) { this.value = v; }
  exponentialRampToValueAtTime(v) { this.value = v; }
  setTargetAtTime(v) { this.value = v; }
  cancelScheduledValues() {}
}
class Node {
  constructor() { this.gain = new Param(1); this.frequency = new Param(440); }
  connect() {}
  disconnect() {}
  start() {}
  stop() {}
}
class Context {
  constructor() { this.currentTime = 0; this.state = "running"; this.destination = {}; }
  createGain() { return new Node(); }
  createOscillator() { return new Node(); }
  async resume() {}
}
const bundle = {
  status: "unconfirmed_score_playback_bundle",
  command_stream: { status: "unconfirmed_synth_command_stream", commands: [
    { command: "note_on", time_seconds: 0, voice_id: "soprano", event_id: "n1", midi: 60 },
    { command: "note_off", time_seconds: 1, voice_id: "soprano", event_id: "n1", midi: 60 },
    { command: "note_on", time_seconds: 1, voice_id: "soprano", event_id: "n2", midi: 62 },
    { command: "note_off", time_seconds: 2, voice_id: "soprano", event_id: "n2", midi: 62 },
  ] },
  playback_projection: { status: "unconfirmed_playback_projection", events: [
    { event_id: "n1", voice_id: "soprano", start_seconds: 0, duration_seconds: 1 },
    { event_id: "n2", voice_id: "soprano", start_seconds: 1, duration_seconds: 1 },
  ] },
  visual_anchor_map: { status: "unconfirmed_visual_anchor_map", anchors: [
    { event_id: "n1", page_index: 0, system_index: 0, measure_index: 0, x: 20, y: 20, width: 10, height: 8 },
    { event_id: "n2", page_index: 1, system_index: 0, measure_index: 1, x: 30, y: 20, width: 10, height: 8 },
  ] },
};

test("factory conecta paquete, reloj de audio y cursor multipágina", async () => {
  const context = new Context();
  const changes = [];
  const app = createBrowserScorePlaybackSession(bundle, {
    audioContext: context, onPageChange: page => changes.push(page),
    lookaheadSeconds: 0.15,
  });
  const first = await app.session.play();
  assert.equal(first.visual.page_index, 0);
  context.currentTime = 1.2;
  const next = app.session.frame();
  assert.equal(next.visual.page_index, 1);
  assert.equal(next.playback.current_seconds, 1.2);
  assert.deepEqual(changes.map(item => item.page_index), [0, 1]);
  app.dispose();
  assert.equal(app.player.state, "stopped");
  assert.equal(app.sink.disposed, true);
});

test("factory rechaza paquetes incompletos y libera recursos si falla la creación", () => {
  assert.throws(() => createBrowserScorePlaybackSession({}, { audioContext: new Context() }), /paquete Palermo/);
  assert.throws(() => createBrowserScorePlaybackSession(bundle, {
    audioContext: new Context(), lookaheadSeconds: 2,
  }), /lookaheadSeconds/);
});
