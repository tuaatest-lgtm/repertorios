import test from "node:test";
import assert from "node:assert/strict";
import { LookaheadPlaybackController } from "./lookahead-playback-controller.mjs";

class ScheduledSink {
  constructor() { this.context = { currentTime: 0, state: "running", resume: async () => {} }; this.calls = []; }
  note_on(voice, midi, event, when) { this.calls.push(["on", voice, midi, event, when]); }
  note_off(voice, midi, event, when) { this.calls.push(["off", voice, midi, event, when]); }
  all_notes_off() { this.calls.push(["panic"]); }
  set_voice_muted(voice, muted) { this.calls.push(["mute", voice, muted]); }
}
const stream = { status: "unconfirmed_synth_command_stream", commands: [
  { command: "note_on", time_seconds: 0, voice_id: "soprano", event_id: "s1", midi: 72 },
  { command: "note_on", time_seconds: 0.05, voice_id: "alto", event_id: "a1", midi: 60 },
  { command: "note_off", time_seconds: 0.4, voice_id: "alto", event_id: "a1", midi: 60 },
  { command: "note_off", time_seconds: 1, voice_id: "soprano", event_id: "s1", midi: 72 },
] };

test("programa eventos dentro de la ventana usando tiempos absolutos del dispositivo", async () => {
  const sink = new ScheduledSink();
  const player = new LookaheadPlaybackController(stream, sink, { lookaheadSeconds: 0.1 });
  await player.play();
  assert.deepEqual(sink.calls.filter(c => c[0] === "on").map(c => [c[1], c[4]]), [
    ["soprano", 0], ["alto", 0.05],
  ]);
  assert.equal(player.snapshot().active_notes, 1);
  assert.equal(player.snapshot().scheduled_commands, 2);
  sink.context.currentTime = 0.35;
  player.tick();
  assert.ok(sink.calls.some(c => c[0] === "off" && c[1] === "alto" && c[4] === 0.4));
  assert.equal(player.snapshot().active_notes, 1);
});

test("pausa cancela comandos futuros y reanuda notas sostenidas con el reloj congelado", async () => {
  const sink = new ScheduledSink();
  const player = new LookaheadPlaybackController(stream, sink, { lookaheadSeconds: 0.2 });
  await player.play();
  sink.context.currentTime = 0.2;
  player.pause();
  assert.equal(player.state, "paused");
  assert.equal(player.snapshot().active_notes, 2);
  assert.equal(sink.calls.at(-1)[0], "panic");
  sink.context.currentTime = 5;
  assert.equal(player.current_seconds, 0.2);
  await player.resume();
  assert.equal(player.state, "playing");
  assert.ok(sink.calls.some(c => c[0] === "on" && c[1] === "soprano" && c[4] === 5));
  assert.ok(sink.calls.some(c => c[0] === "on" && c[1] === "alto" && c[4] === 5));
  sink.context.currentTime = 5.2;
  player.tick();
  assert.ok(Math.abs(player.current_seconds - 0.4) < 1e-9);
});

test("mute por voz no altera el calendario ni las otras voces", async () => {
  const sink = new ScheduledSink();
  const player = new LookaheadPlaybackController(stream, sink);
  await player.play();
  const before = player.snapshot().scheduled_commands;
  player.set_voice_muted("alto", true);
  assert.equal(player.snapshot().scheduled_commands, before);
  assert.ok(sink.calls.some(c => c[0] === "mute" && c[1] === "alto" && c[2] === true));
});

test("detiene, reinicia y valida límites de anticipación", async () => {
  const sink = new ScheduledSink();
  assert.throws(() => new LookaheadPlaybackController(stream, sink, { lookaheadSeconds: 1 }), /lookaheadSeconds/);
  const player = new LookaheadPlaybackController(stream, sink);
  await player.play();
  player.stop();
  assert.equal(player.snapshot().state, "stopped");
  assert.equal(player.snapshot().processed_commands, 0);
  assert.equal(player.snapshot().scheduled_commands, 0);
});
