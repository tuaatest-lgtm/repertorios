import test from "node:test";
import assert from "node:assert/strict";
import { PalermoOMRClient, PalermoOMRError } from "./omr-client.mjs";

test("rechaza archivos que no sean PDF antes de llamar a la API", async () => {
  let called = false;
  const client = new PalermoOMRClient({ fetchImpl: async () => { called = true; } });
  await assert.rejects(client.createJob({ name: "score.png", arrayBuffer: async () => new ArrayBuffer(0) }), /PDF válido/);
  assert.equal(called, false);
});

test("crea trabajos usando multipart y DPI permitido", async () => {
  let request;
  const client = new PalermoOMRClient({ fetchImpl: async (url, init) => { request = { url, init }; return new Response(JSON.stringify({ api_version: "1", job_id: "job_12345678", status: "queued" }), { status: 202, headers: { "content-type": "application/json" } }); } });
  const file = new Blob(["%PDF-1.7"], { type: "application/pdf" });
  Object.defineProperty(file, "name", { value: "score.pdf" });
  const job = await client.createJob(file, { dpi: 240 });
  assert.equal(request.url, "/api/omr/v1/jobs");
  assert.equal(request.init.credentials, "same-origin");
  assert.equal(request.init.body.get("dpi"), "240");
  assert.equal(job.jobId, "job_12345678");
});

test("espera hasta completed y después obtiene el resultado", async () => {
  let calls = 0;
  const client = new PalermoOMRClient({ pollIntervalMs: 0, maxPollIntervalMs: 0, fetchImpl: async (url) => {
    calls += 1;
    if (url.endsWith("/result")) return new Response(JSON.stringify({ api_version: "1", job_id: "job_12345678", pages: [] }), { status: 200 });
    const status = calls === 1 ? "processing" : "completed";
    return new Response(JSON.stringify({ status }), { status: 200 });
  } });
  const result = await client.waitForCompletion("job_12345678");
  assert.deepEqual(result.pages, []);
  assert.equal(calls, 3);
});

test("rechaza respuestas HTTP de error con mensaje del servidor", async () => {
  const client = new PalermoOMRClient({ fetchImpl: async () => new Response(JSON.stringify({ error: { message: "No autorizado" } }), { status: 401 }) });
  await assert.rejects(client.getStatus("job_12345678"), (error) => error instanceof PalermoOMRError && error.status === 401 && /No autorizado/.test(error.message));
});
