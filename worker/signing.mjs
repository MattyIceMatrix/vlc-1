// Ed25519 signing for verified reports. 2026-11-25: new file, additive.
//
// The private key lives ONLY in the Worker secret SIGNING_KEY (base64 PKCS#8),
// set in the Cloudflare dashboard. The matching public key is committed at
// keys/vlc-report-signing.pub.json. The signature is computed over the
// CANONICAL JSON bytes of the report object -- same canon() the checker uses
// for record hashing (sorted keys, compact separators) -- so any Ed25519
// implementation can verify offline: tools/verify_report.py does it with the
// reference checker's own pure-Python ed25519_verify.
import { canon } from "./core.mjs";

function b64ToBytes(b64) {
  const bin = atob(b64.trim());
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

let cachedKey = null;
async function importSigningKey(secretB64) {
  if (cachedKey) return cachedKey;
  const pkcs8 = b64ToBytes(secretB64);
  // Workers runtime: standard "Ed25519"; older runtimes used "NODE-ED25519".
  for (const alg of [{ name: "Ed25519" }, { name: "NODE-ED25519", namedCurve: "NODE-ED25519" }]) {
    try {
      cachedKey = await crypto.subtle.importKey("pkcs8", pkcs8, alg, false, ["sign"]);
      cachedKey._alg = alg;
      return cachedKey;
    } catch { /* try next */ }
  }
  throw new Error("Ed25519 not supported by this runtime");
}

export async function signReport(report, secretB64) {
  const key = await importSigningKey(secretB64);
  const msg = new TextEncoder().encode(canon(report));
  const sig = new Uint8Array(await crypto.subtle.sign(key._alg, key, msg));
  return Array.from(sig).map(b => b.toString(16).padStart(2, "0")).join("");
}
