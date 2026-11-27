/**
 * Cliente aislado para la API Palermo OMR v1.
 * Este módulo no se importa desde index.html hasta que el backend exista.
 */
export class PalermoOMRError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = "PalermoOMRError";
    this.status = status;
    this.details = details;
  }
}

export class PalermoOMRClient {
  constructor({ baseUrl = "/api/omr/v1", fetchImpl = globalThis.fetch, pollIntervalMs = 1500, maxPollIntervalMs = 8000 } = {}) {
    if (typeof fetchImpl !== "function") throw new TypeError("Se requiere una implementación fetch");
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetchImpl = fetchImpl;
    this.pollIntervalMs = pollIntervalMs;
    this.maxPollIntervalMs = maxPollIntervalMs;
  }

  async createJob(file, { dpi = 300, options, signal } = {}) {
    if (!file || typeof file.arrayBuffer !== "function" || !/\.pdf$/i.test(file.name || "")) {
      throw new TypeError("Selecciona un archivo PDF válido");
    }
    if (!Number.isInteger(dpi) || dpi < 150 || dpi > 400) throw new RangeError("dpi debe estar entre 150 y 400");
    const body = new FormData();
    body.append("file", file, file.name);
    body.append("dpi", String(dpi));
    if (options !== undefined) body.append("options", JSON.stringify(options));
    const data = await this.#request("/jobs", { method: "POST", body, signal }, 202);
    if (data.api_version !== "1" || typeof data.job_id !== "string" || !data.job_id) {
      throw new PalermoOMRError("Respuesta de creación de trabajo incompatible", 502, data);
    }
    return Object.freeze({ jobId: data.job_id, status: data.status, statusUrl: this.#jobPath(data.job_id), resultUrl: `${this.#jobPath(data.job_id)}/result` });
  }

  async getStatus(jobId, { signal } = {}) {
    const data = await this.#request(this.#jobPath(jobId), { method: "GET", signal });
    if (!["queued", "processing", "completed", "failed"].includes(data.status)) {
      throw new PalermoOMRError("Estado de trabajo desconocido", 502, data);
    }
    return data;
  }

  async getResult(jobId, { signal } = {}) {
    const data = await this.#request(`${this.#jobPath(jobId)}/result`, { method: "GET", signal });
    if (data.api_version !== "1" || data.job_id !== jobId || !Array.isArray(data.pages)) {
      throw new PalermoOMRError("Resultado OMR incompatible con el contrato v1", 502, data);
    }
    return data;
  }

  async waitForCompletion(jobId, { signal, onStatus } = {}) {
    let delay = this.pollIntervalMs;
    while (true) {
      if (signal?.aborted) throw new DOMException("Operación cancelada", "AbortError");
      const status = await this.getStatus(jobId, { signal });
      onStatus?.(status);
      if (status.status === "completed") return this.getResult(jobId, { signal });
      if (status.status === "failed") throw new PalermoOMRError(status.error?.message || "El análisis OMR falló", 422, status.error || status);
      await new Promise((resolve, reject) => {
        const timer = setTimeout(resolve, delay);
        signal?.addEventListener("abort", () => { clearTimeout(timer); reject(new DOMException("Operación cancelada", "AbortError")); }, { once: true });
      });
      delay = Math.min(Math.ceil(delay * 1.5), this.maxPollIntervalMs);
    }
  }

  #jobPath(jobId) {
    if (typeof jobId !== "string" || !/^[A-Za-z0-9_-]{8,160}$/.test(jobId)) throw new TypeError("Identificador de trabajo no válido");
    return `/jobs/${encodeURIComponent(jobId)}`;
  }

  async #request(path, init, expectedStatus = 200) {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, { credentials: "same-origin", ...init });
    let data;
    try { data = await response.json(); } catch { data = null; }
    if (response.status !== expectedStatus) {
      throw new PalermoOMRError(data?.error?.message || `Error HTTP ${response.status}`, response.status, data);
    }
    if (!data || typeof data !== "object") throw new PalermoOMRError("Respuesta JSON vacía o inválida", 502);
    return data;
  }
}
