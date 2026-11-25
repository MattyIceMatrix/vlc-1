// The vlc-1 Worker: static spec site (assets) + the live checker endpoint.
// POST /api/check  body: the journal (JSONL)  query: ?adapter=generic-appjsonl
// 2026-11-25: added alongside the static page; the page itself is unchanged.
import { check } from "./core.mjs";
import genericAdapter from "../adapters/generic-appjsonl.json";
import genericPolicyAdapter from "../adapters/generic-appjsonl-policy.json";

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
    return env.ASSETS.fetch(request);
  },
};
