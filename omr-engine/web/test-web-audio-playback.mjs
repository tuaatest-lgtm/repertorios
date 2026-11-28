import test from "node:test";
import assert from "node:assert/strict";
import { WebAudioSink, BrowserPlaybackController } from "./web-audio-playback.mjs";

class Param {
  constructor(value = 0) { this.value = value; this.calls = []; }
  setValueAtTime(v, t) { this.value = v; this.calls.push(["set", v, t]); }
  exponentialRampToValueAtTime(v, t) { this.value = v; this.calls.push(["ramp", v, t]); }
  setTargetAtTime(v, t, c) { this.value = v; this.calls.push(["target", v, t, c]); }
  cancelScheduledValues(t) { this.calls.push(["cancel", t]); }
}
class Node {
  constructor() { this.gain = new Param(1); this.frequency = new Param(440); this.connections = []; this.stops = []; }
  connect(n) { this.connections.push(n); }
  disconnect() {}
  start(t) { this.started = t; }
  stop(t) { this.stops.push(t); }
}
class FakeAudioContext {
  constructor() { this.currentTime = 0; this.state = "running"; this.destination = {}; this.nodes = []; }
  createGain() { const n = new Node(); this.nodes.push(n); return n; }
  createOscillator() { const n = new Node(); this.nodes.push(n); return n; }
  async resume() { this.state = "running"; }
}
const stream = { status: "unconfirmed_synth_command_stream", commands: [
  { command: "note_on", time_seconds: 0, voice_id: "soprano", event_id: "a", midi: 69 },
  { command: "note_on", time_seconds: 0, voice_id: "alto", event_id: "b", midi: 60 },
  { command: "note_off", time_seconds: 1, voice_id: "soprano", event_id: "a", midi: 69 },
  { command: "note_off", time_seconds: 2, voice_id: "alto", event_id: "b", midi: 60 },
] };

test("WebAudioSink crea osciladores independientes y libera notas", () => {
  const context = new FakeAudioContext();
  const sink = new WebAudioSink({ audioContext: context });
  sink.note_on("soprano", 69, "a");
  sink.note_on("alto", 60, "b");
  assert.equal(sink.notes.size, 2);
  assert.equal(sink.voices.size, 2);
  sink.note_off("soprano", 69, "a");
  assert.equal(sink.notes.size, 1);
  assert.ok([...sink.notes.values()][0].oscillator.started === 0);
  sink.all_notes_off();
  assert.equal(sink.notes.size, 0);
  sink.dispose();
  assert.throws(() => sink.note_on("soprano", 69, "c"), /cerrado/);
});

test("scheduler mantiene dos voces simultáneas y finaliza tras duraciones independientes", async () => {
  const context = new FakeAudioContext();
  const sink = new WebAudioSink({ audioContext: context });
  const player = new BrowserPlaybackController(stream, sink);
  await player.play();
  assert.equal(player.snapshot().active_notes, 2);
  context.currentTime = 1;
  player.tick();
  assert.equal(player.snapshot().active_notes, 1);
  context.currentTime = 2;
  player.tick();
  assert.equal(player.state, "finished");
  assert.equal(sink.notes.size, 0);
});

test("pause congela la línea temporal y resume reenciende notas sostenidas", async () => {
  const context = new FakeAudioContext();
  const sink = new WebAudioSink({ audioContext: context });
  const player = new BrowserPlaybackController(stream, sink);
  await player.play();
  context.currentTime = 0.4;
  player.pause();
  assert.equal(player.state, "paused");
  assert.equal(sink.notes.size, 0);
  context.currentTime = 5;
  await player.resume();
  assert.equal(player.snapshot().current_seconds, 0.4);
  assert.equal(sink.notes.size, 2);
  context.currentTime = 5.6;
  player.tick();
  assert.equal(player.snapshot().active_notes, 1);
});

test("mute afecta una sola voz sin detener las demás", async () => {
  const context = new FakeAudioContext();
  const sink = new WebAudioSink({ audioContext: context });
  const player = new BrowserPlaybackController(stream, sink);
  await player.play();
  player.set_voice_muted("soprano", true);
  assert.equal(sink.voices.get("soprano").gain.value, 0);
  assert.equal(sink.voices.get("alto").gain.value, 1);
  assert.equal(player.snapshot().active_notes, 2);
});
