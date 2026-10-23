// REST integration hooks. Every call is best-effort: the UI runs on local mock state
// and mirrors mutations to the backend when it is reachable (default http://localhost:8000).

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PREFIX = "/api/v1";

async function request(path, { method = "GET", body, timeoutMs = 1500 } = {}) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_URL}${PREFIX}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(t);
  }
}

/** Swallows network errors; returns { ok, data }. */
async function safe(path, opts) {
  try {
    return { ok: true, data: await request(path, opts) };
  } catch {
    return { ok: false, data: null };
  }
}

export const api = {
  ping: () => safe("/pricing/health"),
  getBatches: () => safe("/inventory/batches"),
  applyMarkdown: (batchIds, pct) => safe("/pricing/apply", { method: "POST", body: { batch_ids: batchIds, discount_pct: pct } }),
  dispatchSurplus: (payload) => safe("/routing/dispatch", { method: "POST", body: payload }),
  confirmRoute: (id) => safe(`/routing/confirm/${id}`, { method: "POST" }),
  createOrder: (payload) => safe("/customer/orders", { method: "POST", body: payload }),
};
