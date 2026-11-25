// The vlc-1 Worker: static spec site (assets) + the live checker endpoint.
// POST /api/check  body: the journal (JSONL)  query: ?adapter=generic-appjsonl
// 2026-11-25: added alongside the static page; the page itself is unchanged.
import { check } from "./core.mjs";
import { signReport } from "./signing.mjs";
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
    // 2026-11-25, additive: usage counters. COUNTS ONLY -- event type, day,
    // verdict family. No journal content, no emails, no IPs: the page's
    // "nothing you paste is stored" promise holds.
    this.sql.exec(`CREATE TABLE IF NOT EXISTS events (
      day TEXT NOT NULL, type TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (day, type))`);
    // 2026-11-25, additive: the report-signing key. Generated INSIDE this
    // Durable Object on first use and never exported -- no human ever sees
    // the private key, there is nothing to paste into a dashboard and
    // nothing to leak from a laptop or a transcript. Only the PUBLIC half
    // leaves (via /pubkey), to be committed to the spec repo.
    this.sql.exec(`CREATE TABLE IF NOT EXISTS signing_keys (
      key_id TEXT PRIMARY KEY, pkcs8_b64 TEXT NOT NULL, spki_b64 TEXT NOT NULL,
      raw_hex TEXT NOT NULL, created TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)`);
  }
  async _activeKey() {
    const rows = this.sql.exec("SELECT * FROM signing_keys WHERE active = 1 ORDER BY created DESC LIMIT 1").toArray();
    if (rows.length) return rows[0];
    const pair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", pair.privateKey));
    const spki = new Uint8Array(await crypto.subtle.exportKey("spki", pair.publicKey));
    const raw = spki.slice(spki.length - 32);
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", raw));
    const hex = (a) => Array.from(a).map(b => b.toString(16).padStart(2, "0")).join("");
    const b64 = (a) => btoa(String.fromCharCode(...a));
    const row = { key_id: hex(digest).slice(0, 16), pkcs8_b64: b64(pkcs8), spki_b64: b64(spki),
                  raw_hex: hex(raw), created: new Date().toISOString(), active: 1 };
    this.sql.exec("INSERT INTO signing_keys (key_id, pkcs8_b64, spki_b64, raw_hex, created, active) VALUES (?, ?, ?, ?, ?, 1)",
      row.key_id, row.pkcs8_b64, row.spki_b64, row.raw_hex, row.created);
    return row;
  }
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/event" && request.method === "POST") {
      const type = (url.searchParams.get("type") ?? "unknown").slice(0, 40);
      const day = new Date().toISOString().slice(0, 10);
      this.sql.exec(
        "INSERT INTO events (day, type, n) VALUES (?, ?, 1) ON CONFLICT(day, type) DO UPDATE SET n = n + 1",
        day, type);
      return Response.json({ ok: true });
    }
    if (url.pathname === "/pubkey" && request.method === "GET") {
      const k = await this._activeKey();
      return Response.json({ alg: "Ed25519", key_id: k.key_id, public_key_raw_hex: k.raw_hex,
                             public_key_spki_b64: k.spki_b64, created: k.created });
    }
    if (url.pathname === "/sign" && request.method === "POST") {
      const { report } = await request.json();
      const k = await this._activeKey();
      const sig = await signReport(report, k.pkcs8_b64);
      return Response.json({ sig_hex: sig, key_id: k.key_id });
    }
    if (url.pathname === "/stats" && request.method === "GET") {
      const rows = this.sql.exec("SELECT day, type, n FROM events ORDER BY day, type").toArray();
      const total = this.sql.exec("SELECT COUNT(*) AS n FROM signups").one().n;
      return Response.json({ signups_total: total, events: rows });
    }
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

// ---------------------------------------------------------------------------
// 2026-11-25, additive: per-IP token buckets. Per-isolate and in-memory, so
// they reset when the isolate recycles -- a first line against curl loops,
// not a hard quota (a hard quota would need the DO or a Cloudflare rate rule).
const BUCKETS = new Map(); // key -> { tokens, last }
function rateLimited(ip, route, perMs, burst) {
  const key = route + "|" + ip, now = Date.now();
  let b = BUCKETS.get(key);
  if (!b) { b = { tokens: burst, last: now }; BUCKETS.set(key, b); }
  b.tokens = Math.min(burst, b.tokens + (now - b.last) / perMs);
  b.last = now;
  if (BUCKETS.size > 10_000) BUCKETS.clear(); // bound memory
  if (b.tokens < 1) return Math.ceil(perMs * (1 - b.tokens) / 1000);
  b.tokens -= 1;
  return 0;
}
function tooMany(retryS) {
  return Response.json({ error: "rate limit; slow down" },
    { status: 429, headers: { ...CORS, "retry-after": String(retryS) } });
}

async function buildReport(request, url) {
  // Shared by /api/check and /api/verify: returns [errorResponse] or [null, report, adapterName].
  const name = url.searchParams.get("adapter") ?? "generic-appjsonl";
  const ad = ADAPTERS[name];
  if (!ad)
    return [Response.json({ error: `unknown adapter; this endpoint serves: ${Object.keys(ADAPTERS).join(", ")}. The full 25-adapter set needs the reference checker.` }, { status: 400, headers: CORS })];
  const body = await request.text();
  if (body.length > MAX_BYTES)
    return [Response.json({ error: `journal over ${MAX_BYTES} bytes; run the reference checker locally` }, { status: 413, headers: CORS })];
  const out = await check(body, ad);
  out.adapter = name;
  out.reference = "https://github.com/MattyIceMatrix/vlc-1 (conformance.py, MIT; spec CC0)";
  return [null, out, name];
}
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "POST, OPTIONS",
  "access-control-allow-headers": "content-type",
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const ip = request.headers.get("cf-connecting-ip") ?? "unknown";
    const bump = (type) => {
      // fire-and-forget counter; never blocks or fails the user's request
      try {
        const stub = env.SIGNUPS.get(env.SIGNUPS.idFromName("list"));
        ctx.waitUntil(stub.fetch("https://do/event?type=" + type, { method: "POST" }).catch(() => {}));
      } catch { /* counting must never break checking */ }
    };
    if (url.pathname === "/api/check") {
      if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
      if (request.method !== "POST")
        return Response.json({ error: "POST a JSONL journal as the request body" }, { status: 405, headers: CORS });
      const retry = rateLimited(ip, "check", 2_000, 30); // ~30 burst, 1 per 2s sustained
      if (retry) return tooMany(retry);
      try {
        const [err, out] = await buildReport(request, url);
        if (err) return err;
        bump("check_" + (String(out.verdict).includes("PASS") ? "pass" : "fail"));
        return Response.json(out, { headers: CORS });
      } catch (e) {
        return Response.json({ error: String(e?.message ?? e) }, { status: 422, headers: CORS });
      }
    }
    if (url.pathname === "/api/verify") {
      // 2026-11-25, additive: VERIFIED (signed) reports. Admin-gated: this is
      // the paid tier's instrument -- the operator runs the check and issues a
      // report signed with the key only this Worker holds. Anyone can verify
      // the signature offline against keys/vlc-report-signing.pub.json
      // (tools/verify_report.py), but only the operator can issue one.
      if (request.method !== "POST")
        return Response.json({ error: "POST a JSONL journal as the request body" }, { status: 405 });
      const key = request.headers.get("x-admin-key");
      if (!env.ADMIN_KEY || !key || key !== env.ADMIN_KEY)
        return Response.json({ error: "verified reports are issued by the operator; join the list on /checker.html for launch" }, { status: 403 });
      try {
        const [err, out] = await buildReport(request, url);
        if (err) return err;
        const stub = env.SIGNUPS.get(env.SIGNUPS.idFromName("list"));
        const pub = await (await stub.fetch("https://do/pubkey")).json();
        const report = {
          report: "VLC verified report",
          issued_at: new Date().toISOString(),
          issuer: "vlc-1.moorematthew131.workers.dev",
          checker: "vlc-1 live subset (VLC-L1-1, VLC-L1-3, VLC-L2-5; canonical-chain)",
          key_id: pub.key_id,
          spec: "https://github.com/MattyIceMatrix/vlc-1",
          ...out,
        };
        const signed = await (await stub.fetch("https://do/sign", {
          method: "POST", body: JSON.stringify({ report }) })).json();
        bump("verify_issued");
        return Response.json({
          report,
          signature: { alg: "Ed25519", key_id: signed.key_id, signed: "canonical JSON of .report (sorted keys, compact separators)", sig_hex: signed.sig_hex },
          verify_with: "tools/verify_report.py in the spec repo, against keys/vlc-report-signing.pub.json",
        });
      } catch (e) {
        return Response.json({ error: String(e?.message ?? e) }, { status: 422 });
      }
    }
    if (url.pathname === "/api/pubkey") {
      // public: the key anyone verifies reports against; also committed to
      // the spec repo (keys/vlc-report-signing.pub.json)
      const stub = env.SIGNUPS.get(env.SIGNUPS.idFromName("list"));
      return stub.fetch("https://do/pubkey");
    }
    if (url.pathname === "/api/stats") {
      const key = request.headers.get("x-admin-key");
      if (!env.ADMIN_KEY || !key || key !== env.ADMIN_KEY)
        return Response.json({ error: "admin only" }, { status: 403 });
      const stub = env.SIGNUPS.get(env.SIGNUPS.idFromName("list"));
      return stub.fetch("https://do/stats");
    }
    if (url.pathname === "/api/signup") {
      if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
      if (request.method !== "POST")
        return Response.json({ error: "POST {\"email\": ...}" }, { status: 405, headers: CORS });
      let body;
      try { body = await request.json(); } catch { body = {}; }
      const retry = rateLimited(ip, "signup", 720_000, 5); // 5 burst, ~5/hour sustained
      if (retry) return tooMany(retry);
      const email = String(body.email ?? "").trim().toLowerCase();
      if (!EMAIL_RE.test(email) || email.length > 254)
        return Response.json({ error: "that does not look like an email address" }, { status: 400, headers: CORS });
      const stub = env.SIGNUPS.get(env.SIGNUPS.idFromName("list"));
      const r = await stub.fetch("https://do/signup", {
        method: "POST",
        body: JSON.stringify({ email, source: String(body.source ?? "checker").slice(0, 40) }),
      });
      const out = await r.json();
      if (out.ok === true) bump("signup");
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
