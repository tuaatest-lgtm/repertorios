import test from "node:test";
import assert from "node:assert/strict";
import { WebAudioSink, BrowserPlaybackController } from "./web-audio-playback.mjs";
import { ScoreVisualCursor } from "./score-visual-cursor.mjs";
import { BrowserScorePlaybackSession } from "./score-playback-session.mjs";

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
const stream = { status: "unconfirmed_synth_command_stream", commands: [
  { command: "note_on", time_seconds: 0, voice_id: "soprano", event_id: "one", midi: 60 },
  { command: "note_off", time_seconds: 2, voice_id: "soprano", event_id: "one", midi: 60 },
  { command: "note_on", time_seconds: 2, voice_id: "soprano", event_id: "two", midi: 62 },
  { command: "note_off", time_seconds: 3, voice_id: "soprano", event_id: "two", midi: 62 },
] };
const projection = { status: "unconfirmed_playback_projection", events: [
  { event_id: "one", voice_id: "soprano", start_seconds: 0, duration_seconds: 2 },
  { event_id: "two", voice_id: "soprano", start_seconds: 2, duration_seconds: 1 },
] };
const anchors = [
  { event_id: "one", page_index: 0, system_index: 1, measure_index: 0, x: 80, y: 20, width: 10, height: 8 },
  { event_id: "two", page_index: 1, system_index: 0, measure_index: 4, x: 30, y: 20, width: 10, height: 8 },
];

function makeSession(onPageChange) {
  const context = new Context();
  const sink = new WebAudioSink({ audioContext: context });
  const player = new BrowserPlaybackController(stream, sink);
  const cursor = new ScoreVisualCursor(projection, anchors);
  return { context, session: new BrowserScorePlaybackSession({ player, visualCursor: cursor, onPageChange }) };
}

test("reloj de audio gobierna cursor y cambio de página", async () => {
  const changes = [];
  const { context, session } = makeSession(change => changes.push(change));
  const first = await session.play();
  assert.equal(first.visual.page_index, 0);
  assert.equal(first.visual.system_index, 1);
  context.currentTime = 2.1;
  const second = session.frame();
  assert.equal(second.playback.current_seconds, 2.1);
  assert.equal(second.visual.page_index, 1);
  assert.deepEqual(changes.map(c => c.page_index), [0, 1]);
});

test("pausa y reanudación preservan la página y la posición musical", async () => {
  const { context, session } = makeSession();
  await session.play();
  context.currentTime = 0.75;
  const paused = session.pause();
  assert.equal(paused.playback.state, "paused");
  assert.equal(paused.visual.page_index, 0);
  context.currentTime = 10;
  const stillPaused = session.frame();
  assert.equal(stillPaused.playback.current_seconds, 0.75);
  const resumed = await session.resume();
  assert.equal(resumed.playback.current_seconds, 0.75);
  assert.equal(resumed.visual.page_index, 0);
});

test("stop devuelve reloj y cursor al inicio", async () => {
  const { context, session } = makeSession();
  await session.play();
  context.currentTime = 2.5;
  session.frame();
  const stopped = session.stop();
  assert.equal(stopped.playback.state, "stopped");
  assert.equal(stopped.playback.current_seconds, 0);
  assert.equal(stopped.visual.page_index, 0);
});

test("no solicita cambio de página cuando el anclaje es ambiguo", async () => {
  const calls = [];
  const { context, session } = makeSession(value => calls.push(value));
  await session.play();
  assert.equal(calls.length, 1);
  // El cursor ya seleccionó página 0; se conserva sin saltos especulativos.
  context.currentTime = 1.5;
  session.frame();
  assert.equal(calls.length, 1);
});
