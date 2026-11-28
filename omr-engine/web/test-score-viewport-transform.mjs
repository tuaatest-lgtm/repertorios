import test from "node:test";
import assert from "node:assert/strict";
import { ScoreViewportTransform } from "./score-viewport-transform.mjs";

test("escala anclajes de análisis a CSS y aplica offsets/scroll", () => {
  const transform = new ScoreViewportTransform({
    source_width: 1000, source_height: 1400,
    rendered_width: 500, rendered_height: 700,
    offset_left: 30, offset_top: 20, scroll_left: 10, scroll_top: 5,
    page_index: 1,
  });
  assert.deepEqual(transform.mapRect({ x: 100, y: 200, width: 20, height: 10 }), {
    left: 70, top: 115, width: 10, height: 5,
  });
});

test("soporta escalas X/Y distintas si el host entrega dimensiones reales", () => {
  const transform = new ScoreViewportTransform({
    source_width: 1000, source_height: 1000,
    rendered_width: 500, rendered_height: 600, page_index: 0,
  });
  assert.deepEqual(transform.mapRect({ x: 100, y: 100, width: 40, height: 20 }), {
    left: 50, top: 60, width: 20, height: 12,
  });
});

test("solo expone resaltados de la página activa y oculta posiciones ambiguas", () => {
  const transform = new ScoreViewportTransform({
    source_width: 100, source_height: 100, rendered_width: 200, rendered_height: 200,
    page_index: 2,
  });
  const visual = {
    page_index: 2, ambiguous_location: false,
    highlights: [
      { event_id: "a", page_index: 2, x: 10, y: 15, width: 5, height: 5 },
      { event_id: "b", page_index: 1, x: 30, y: 15, width: 5, height: 5 },
    ],
  };
  const mapped = transform.mapVisualState(visual);
  assert.equal(mapped.visible, true);
  assert.equal(mapped.highlights.length, 1);
  assert.deepEqual(mapped.highlights[0].rect, { left: 20, top: 30, width: 10, height: 10 });
  assert.equal(transform.mapVisualState({ ...visual, ambiguous_location: true }).visible, false);
});

test("rechaza dimensiones, páginas y rectángulos no válidos", () => {
  assert.throws(() => new ScoreViewportTransform({ source_width: 0 }), /source_width/);
  assert.throws(() => new ScoreViewportTransform({
    source_width: 10, source_height: 10, rendered_width: 10, rendered_height: 10, page_index: -1,
  }), /page_index/);
  const transform = new ScoreViewportTransform({
    source_width: 10, source_height: 10, rendered_width: 10, rendered_height: 10, page_index: 0,
  });
  assert.throws(() => transform.mapRect({ x: 0, y: 0, width: 0, height: 1 }), /positivas/);
});
