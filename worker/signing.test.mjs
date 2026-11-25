// Roundtrip test for verified-report signing. 2026-11-25, additive.
//
// Generates an EPHEMERAL Ed25519 keypair (no secret needed, runs anywhere),
// signs a report through the same signReport() the Worker uses, then verifies
// through tools/verify_report.py -- the reference checker's pure-Python
// Ed25519 -- so JS signer and Python verifier are proven against each other.
// A tampered report must fail. Blast radius: a self-created temp dir.
import { generateKeyPairSync, createHash } from "node:crypto";
import { writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { signReport } from "./signing.mjs";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..");
const tmp = mkdtempSync(join(tmpdir(), "vlc-sign-"));
let failed = 0;
const ok = (cond, name) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) failed = 1; };

try {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const pkcs8 = privateKey.export({ type: "pkcs8", format: "der" }).toString("base64");
  const spki = publicKey.export({ type: "spki", format: "der" });
  const raw = spki.subarray(spki.length - 32);
  const keyId = createHash("sha256").update(raw).digest("hex").slice(0, 16);
  const pubFile = join(tmp, "pub.json");
  writeFileSync(pubFile, JSON.stringify({ alg: "Ed25519", key_id: keyId, public_key_raw_hex: raw.toString("hex") }));

  const report = {
    report: "VLC verified report", issued_at: "2026-11-25T00:00:00Z", key_id: keyId,
    verdict: "L1/L2 SUBSET PASS", records: 43, head: "788a438b",
    results: [{ check: "VLC-L1-1", ok: true, note: "chain verifies" }],
  };
  const sig = await signReport(report, pkcs8);
  ok(/^[0-9a-f]{128}$/.test(sig), "signature is 64 bytes of hex");

  const good = join(tmp, "good.json");
  writeFileSync(good, JSON.stringify({ report, signature: { alg: "Ed25519", key_id: keyId, sig_hex: sig } }));
  let out = execFileSync("python3", [join(repo, "tools/verify_report.py"), good, pubFile]).toString();
  ok(out.includes("VALID"), "python verifier accepts the JS signature");

  const bad = join(tmp, "bad.json");
  const tampered = { ...report, verdict: "FAIL" }; // flip the verdict, keep the signature
  writeFileSync(bad, JSON.stringify({ report: tampered, signature: { alg: "Ed25519", key_id: keyId, sig_hex: sig } }));
  let code = 0;
  try { execFileSync("python3", [join(repo, "tools/verify_report.py"), bad, pubFile], { stdio: "pipe" }); }
  catch (e) { code = e.status; }
  ok(code === 1, "python verifier rejects a tampered verdict (exit 1)");

  console.log(failed ? "SIGNING TEST FAIL" : "SIGNING TEST PASS");
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
process.exit(failed);
