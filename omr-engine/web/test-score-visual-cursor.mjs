import test from "node:test";
import assert from "node:assert/strict";
import { ScoreVisualCursor } from "./score-visual-cursor.mjs";

const projection = { status: "unconfirmed_playback_projection", events: [
  { event_id: "s1", voice_id: "soprano", event_type: "note", start_seconds: 0, duration_seconds: 2 },
  { event_id: "a1", voice_id: "alto", event_type: "note", start_seconds: 0, duration_seconds: 1 },
  { event_id: "s2", voice_id: "soprano", event_type: "note", start_seconds: 2, duration_seconds: 1 },
  { event_id: "r1", voice_id: "tenor", event_type: "rest", start_seconds: 3, duration_seconds: 1 },
] };
const anchors = [
  { event_id: "s1", page_index: 0, system_index: 0, measure_index: 0, x: 100, y: 50, width: 12, height: 8 },
  { event_id: "a1", page_index: 0, system_index: 0, measure_index: 0, x: 100, y: 100, width: 12, height: 8 },
  { event_id: "s2", page_index: 1, system_index: 0, measure_index: 4, x: 35, y: 50, width: 12, height: 8 },
  { event_id: "r1", page_index: 1, system_index: 0, measure_index: 4, x: 60, y: 100, width: 10, height: 8 },
];

test("devuelve varias cabezas simultáneas y conserva la identidad de voz", () => {
  const cursor = new ScoreVisualCursor(projection, anchors);
  const state = cursor.positionAt(0.5);
  assert.equal(state.page_index, 0);
  assert.equal(state.system_index, 0);
  assert.deepEqual(state.active_event_ids, ["a1", "s1"]);
  assert.deepEqual(state.active_voices, ["alto", "soprano"]);
  assert.equal(state.highlights.length, 2);
});

test("salta de página según el anclaje temporal, sin reiniciar el reloj", () => {
  const cursor = new ScoreVisualCursor(projection, anchors);
  const before = cursor.positionAt(1.99);
  const after = cursor.positionAt(2.01);
  assert.equal(before.page_index, 0);
  assert.equal(after.page_index, 1);
  assert.equal(after.system_index, 0);
  assert.equal(after.focus_event_id, "s2");
});

test("mantiene una referencia visual durante un silencio", () => {
  const cursor = new ScoreVisualCursor(projection, anchors);
  const state = cursor.positionAt(3.5);
  assert.equal(state.page_index, 1);
  assert.deepEqual(state.active_event_ids, ["r1"]);
  assert.equal(state.highlights[0].event_type, "rest");
});

test("reporta eventos sin geometría en lugar de inventar posiciones", () => {
  const cursor = new ScoreVisualCursor(projection, anchors.slice(0, 2));
  assert.deepEqual(cursor.unresolved, [
    { event_id: "r1", reason: "missing_visual_anchor" },
    { event_id: "s2", reason: "missing_visual_anchor" },
  ]);
  assert.equal(cursor.positionAt(2.5).page_index, null);
  assert.equal(cursor.positionAt(2.5).unresolved_visual_events, 2);
});

test("expone el siguiente límite temporal y valida anclajes", () => {
  const cursor = new ScoreVisualCursor(projection, anchors);
  assert.equal(cursor.nextBoundaryAfter(0.2), 1);
  assert.equal(cursor.nextBoundaryAfter(4), null);
  assert.throws(() => cursor.positionAt(-1), /no negativo/);
  assert.throws(() => new ScoreVisualCursor(projection, [{ ...anchors[0], width: 0 }]), /dimensiones/);
});
