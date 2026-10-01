package aer1

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

var uuidRE = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
var rfcRE = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$`)
var hashRE = regexp.MustCompile(`^sha256:[0-9a-f]{64}$`)

func Verify(r map[string]interface{}) []string {
	f := []string{}
	core := []string{"id", "receipt_schema_version", "created_at", "tool", "provenance_class", "canonical_bytes", "output_hash", "verification_status"}
	for _, k := range core {
		if _, ok := r[k]; !ok {
			f = append(f, "missing required member: "+k)
		}
	}
	if len(f) > 0 {
		return f
	}
	if x, ok := r["id"].(string); !ok || !uuidRE.MatchString(x) || x[14:15] != "4" || !strings.Contains("89ab", x[19:20]) {
		f = append(f, "id is not a lowercase UUID")
	}
	if x, ok := r["receipt_schema_version"].(string); !ok || x != "0.3" {
		f = append(f, "receipt_schema_version is not 0.3")
	}
	if x, ok := r["created_at"].(string); !ok || !rfcRE.MatchString(x) {
		f = append(f, "created_at is not RFC 3339")
	} else {
		if _, e := time.Parse(time.RFC3339Nano, x); e != nil || (x[len(x)-1] != 'Z' && (x[len(x)-5] > '2' || (x[len(x)-5] == '2' && x[len(x)-4] > '3') || x[len(x)-2] > '5')) {
			f = append(f, "created_at is not a valid calendar date/time")
		}
	}
	t, ok := r["tool"].(map[string]interface{})
	if !ok {
		f = append(f, "tool is not an object with name/version/scope strings")
	} else {
		for _, k := range []string{"name", "version", "scope"} {
			x, ok := t[k].(string)
			if !ok || x == "" {
				f = append(f, "tool is not an object with name/version/scope strings")
			}
		}
	}
	p, ok := r["provenance_class"].(string)
	if !ok || !(p == "OBSERVED VIA GATEWAY" || p == "LOGGED BY AGENT" || strings.HasPrefix(p, "EXECUTED BY ") && len(p) > 12) {
		f = append(f, "provenance_class is not a known class")
	}
	var raw []byte
	if x, ok := r["canonical_bytes"].(string); !ok {
		f = append(f, "canonical_bytes is not valid base64")
	} else {
		var e error
		raw, e = base64.StdEncoding.Strict().DecodeString(x)
		if e != nil {
			f = append(f, "canonical_bytes is not valid base64")
		} else if !utf8.Valid(raw) {
			f = append(f, "canonical_bytes is not valid UTF-8")
		}
	}
	oh, ok := r["output_hash"].(string)
	if !ok || !hashRE.MatchString(oh) {
		f = append(f, "output_hash is not sha256: + lowercase hex digest")
	} else if raw != nil {
		h := sha256.Sum256(raw)
		if oh != "sha256:"+hex.EncodeToString(h[:]) {
			f = append(f, "output_hash does not match sha256(canonical_bytes)")
		}
	}
	if x, ok := r["verification_status"].(string); !ok || x != "verified" {
		f = append(f, "verification_status is not verified")
	}
	return f
}
func Profile(r map[string]interface{}) bool {
	b, ok := r["canonical_bytes"].(string)
	if !ok {
		return false
	}
	raw, e := base64.StdEncoding.Strict().DecodeString(b)
	if e != nil || !utf8.Valid(raw) {
		return false
	}
	var p map[string]interface{}
	if json.Unmarshal(raw, &p) != nil {
		return false
	}
	_, ok = p["inputs"]
	return ok
}
func Anchor(r map[string]interface{}) bool {
	a, ok := r["anchor"].(map[string]interface{})
	if !ok {
		return false
	}
	raw, e := base64.StdEncoding.Strict().DecodeString(r["canonical_bytes"].(string))
	if e != nil {
		return false
	}
	h := sha256.Sum256(raw)
	lh, _ := a["leaf_hash"].(string)
	at, _ := a["anchored_at"].(string)
	_, proof := a["proof"].(map[string]interface{})
	return lh == "sha256:"+hex.EncodeToString(h[:]) && rfcRE.MatchString(at) && func() bool { _, e := time.Parse(time.RFC3339Nano, at); return e == nil }() && proof
}
func Emit(id, created, tool, version, scope, prov string, payload []byte) map[string]interface{} {
	h := sha256.Sum256(payload)
	return map[string]interface{}{"id": id, "receipt_schema_version": "0.3", "created_at": created, "tool": map[string]string{"name": tool, "version": version, "scope": scope}, "provenance_class": prov, "canonical_bytes": base64.StdEncoding.EncodeToString(payload), "output_hash": "sha256:" + hex.EncodeToString(h[:]), "verification_status": "verified"}
}
func Load(p string) map[string]interface{} {
	b, _ := os.ReadFile(p)
	var r map[string]interface{}
	json.Unmarshal(b, &r)
	return r
}

var _ = fmt.Sprint

// intValue extracts an integer from a decoded JSON number (float64 from
// encoding/json, or a native Go int family value set programmatically).
func intValue(v interface{}) (int, bool) {
	switch n := v.(type) {
	case int:
		return n, true
	case int64:
		return int(n), true
	case float64:
		if n == float64(int(n)) {
			return int(n), true
		}
	case json.Number:
		if i, e := n.Int64(); e == nil {
			return int(i), true
		}
	}
	return 0, false
}

// VerifyWorkflow validates the Section 8.1 workflow: input is an object,
// steps is a non-empty list, each step has integer seq and string receipt_id,
// seq runs exactly 1..n in order (no gaps, no duplicate seq), no two steps
// share a receipt_id, and merkle_root equals the recomputed Section 8.1 root
// over the ordered receipt_id strings. Section 8.2 steps 1-2 (fetching each
// receipt over the network and re-verifying it) need network access and stay
// the caller's job; this checks structure and math only.
func VerifyWorkflow(w map[string]interface{}) []string {
	f := []string{}
	if w == nil {
		return append(f, "workflow is not an object")
	}
	steps, ok := w["steps"].([]interface{})
	if !ok || len(steps) == 0 {
		return append(f, "steps is not a non-empty list")
	}
	ids := make([]string, 0, len(steps))
	seen := map[string]bool{}
	for i, s := range steps {
		step, ok := s.(map[string]interface{})
		if !ok {
			f = append(f, fmt.Sprintf("step %d is not an object", i))
			continue
		}
		if seq, ok := intValue(step["seq"]); !ok || seq != i+1 {
			f = append(f, fmt.Sprintf("step %d seq is not %d", i, i+1))
		}
		rid, ok := step["receipt_id"].(string)
		if !ok || rid == "" {
			f = append(f, fmt.Sprintf("step %d receipt_id is not a non-empty string", i))
			continue
		}
		if seen[rid] {
			f = append(f, "duplicate receipt_id: "+rid)
		}
		seen[rid] = true
		ids = append(ids, rid)
	}
	root, ok := w["merkle_root"].(string)
	if !ok {
		f = append(f, "merkle_root is missing or not a string")
	} else if got := MerkleRoot(ids); got != root {
		f = append(f, "merkle_root does not match recomputed Section 8.1 root")
	}
	return f
}

// VerifyChain validates the pinned Section 7 hash-chain construction and
// nothing else. Entry digest = SHA-256 over the raw bytes of base64-decoded
// canonical_bytes (strict decode, fail closed). Entry 0 prev_digest must be
// exactly 64 zeros. Every later entry's prev_digest must equal the lowercase
// hex digest of the previous entry. The last entry must carry close: true
// (boolean). An empty timeline fails. Fetching or verifying the receipts the
// chain references is out of scope here; that is the caller's job.
func VerifyChain(timeline []interface{}) []string {
	f := []string{}
	if len(timeline) == 0 {
		return append(f, "timeline is empty")
	}
	digests := make([]string, 0, len(timeline))
	for i, e := range timeline {
		entry, ok := e.(map[string]interface{})
		if !ok {
			return append(f, fmt.Sprintf("entry %d is not an object", i))
		}
		cb, ok := entry["canonical_bytes"].(string)
		raw, derr := base64.StdEncoding.Strict().DecodeString(cb)
		if !ok || derr != nil {
			return append(f, fmt.Sprintf("entry %d canonical_bytes is not valid base64", i))
		}
		h := sha256.Sum256(raw)
		digests = append(digests, hex.EncodeToString(h[:]))
		pd, ok := entry["prev_digest"].(string)
		if !ok {
			return append(f, fmt.Sprintf("entry %d prev_digest is missing or not a string", i))
		}
		if i == 0 {
			if pd != strings.Repeat("0", 64) {
				f = append(f, "entry 0 prev_digest is not 64 zeros")
			}
		} else if pd != digests[i-1] {
			f = append(f, fmt.Sprintf("entry %d prev_digest does not match digest of entry %d", i, i-1))
		}
	}
	last, ok := timeline[len(timeline)-1].(map[string]interface{})
	if !ok {
		return append(f, "last entry is not an object")
	}
	if c, ok := last["close"].(bool); !ok || !c {
		f = append(f, "last entry close is not true")
	}
	return f
}

// MerkleRoot implements the recommended Section 8.1 tree over ordered receipt IDs.
func MerkleRoot(ids []string) string {
	if len(ids) == 0 {
		h := sha256.Sum256(nil)
		return hex.EncodeToString(h[:])
	}
	level := make([][]byte, len(ids))
	for i, id := range ids {
		h := sha256.Sum256([]byte(id))
		level[i] = h[:]
	}
	for len(level) > 1 {
		if len(level)%2 == 1 {
			level = append(level, append([]byte(nil), level[len(level)-1]...))
		}
		next := make([][]byte, 0, (len(level)+1)/2)
		for i := 0; i < len(level); i += 2 {
			b := append(append([]byte(nil), level[i]...), level[i+1]...)
			h := sha256.Sum256(b)
			next = append(next, h[:])
		}
		level = next
	}
	return hex.EncodeToString(level[0])
}
