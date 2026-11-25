// The vlc-1 Worker: static spec site (assets) + the live checker endpoint.
// POST /api/check  body: the journal (JSONL)  query: ?adapter=generic-appjsonl
// 2026-11-25: added alongside the static page; the page itself is unchanged.
import { check } from "./core.mjs";
import genericAdapter from "../adapters/generic-appjsonl.json";
import genericPolicyAdapter from "../adapters/generic-appjsonl-policy.json";

// ---------------------------------------------------------------------------
// Signups: a mailing list for future advanced services (conformance marks,
// verified runs). One Durable Object with SQLite storage -- created by the
// deploy itself, no dashboard setup. An email is stored once, with a
// timestamp and the page it came from, and used only for launch
// notifications. Reading the list back requires the ADMIN_KEY secret, set in
// the Cloudflare dashboard (Workers -> vlc-1 -> Settings -> Variables);
// until it is set, the export endpoint refuses everyone, including us.
export class Signups {
  constructor(state) {
    this.sql = state.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS signups (
      email TEXT PRIMARY KEY, ts TEXT NOT NULL, source TEXT NOT NULL)`);
  }
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "POST") {
      const { email, source } = await request.json();
      this.sql.exec(
        "INSERT INTO signups (email, ts, source) VALUES (?, ?, ?) ON CONFLICT(email) DO NOTHING",
        email, new Date().toISOString(), source ?? "checker");
      const n = this.sql.exec("SELECT COUNT(*) AS n FROM signups").one().n;
      return Response.json({ ok: true, total: n });
    }
    if (request.method === "GET") {
      const rows = this.sql.exec("SELECT email, ts, source FROM signups ORDER BY ts").toArray();
      return Response.json({ count: rows.length, signups: rows });
    }
    return new Response("method", { status: 405 });
  }
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const ADAPTERS = {
  "generic-appjsonl": genericAdapter,
  "generic-appjsonl-policy": genericPolicyAdapter,
};
const MAX_BYTES = 2_000_000;
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "POST, OPTIONS",
  "access-control-allow-headers": "content-type",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/check") {
      if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
      if (request.method !== "POST")
        return Response.json({ error: "POST a JSONL journal as the request body" }, { status: 405, headers: CORS });
      const name = url.searchParams.get("adapter") ?? "generic-appjsonl";
      const ad = ADAPTERS[name];
      if (!ad)
        return Response.json({ error: `unknown adapter; this endpoint serves: ${Object.keys(ADAPTERS).join(", ")}. The full 25-adapter set needs the reference checker.` }, { status: 400, headers: CORS });
      const body = await request.text();
      if (body.length > MAX_BYTES)
        return Response.json({ error: `journal over ${MAX_BYTES} bytes; run the reference checker locally` }, { status: 413, headers: CORS });
      try {
        const out = await check(body, ad);
        out.adapter = name;
        out.reference = "https://github.com/MattyIceMatrix/vlc-1 (conformance.py, MIT; spec CC0)";
        return Response.json(out, { headers: CORS });
      } catch (e) {
        return Response.json({ error: String(e?.message ?? e) }, { status: 422, headers: CORS });
      }
    }
    if (url.pathname === "/api/signup") {
      if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
      if (request.method !== "POST")
        return Response.json({ error: "POST {\"email\": ...}" }, { status: 405, headers: CORS });
      let body;
      try { body = await request.json(); } catch { body = {}; }
      const email = String(body.email ?? "").trim().toLowerCase();
      if (!EMAIL_RE.test(email) || email.length > 254)
        return Response.json({ error: "that does not look like an email address" }, { status: 400, headers: CORS });
      const stub = env.SIGNUPS.get(env.SIGNUPS.idFromName("list"));
      const r = await stub.fetch("https://do/signup", {
        method: "POST",
        body: JSON.stringify({ email, source: String(body.source ?? "checker").slice(0, 40) }),
      });
      const out = await r.json();
      return Response.json({ ok: out.ok === true }, { headers: CORS });
    }
    if (url.pathname === "/api/signups") {
      const key = request.headers.get("x-admin-key");
      if (!env.ADMIN_KEY || !key || key !== env.ADMIN_KEY)
        return Response.json({ error: "admin only; set ADMIN_KEY in the Worker's variables and send it as x-admin-key" }, { status: 403 });
      const stub = env.SIGNUPS.get(env.SIGNUPS.idFromName("list"));
      return stub.fetch("https://do/export");
    }
    return env.ASSETS.fetch(request);
  },
};
