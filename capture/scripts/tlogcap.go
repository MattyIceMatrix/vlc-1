// tlogcap -- helper for capture/scripts/tessera.sh (built there in a temp module).
//
//	tlogcap genkey ORIGIN            prints "<skey>\n<vkey>\n" (golang.org/x/mod/sumdb/note)
//	tlogcap verify DIR VKEY OLDCKPT  verifies DIR/checkpoint with VKEY, every entry's
//	                                 inclusion proof against it, and a consistency proof
//	                                 from the checkpoint in OLDCKPT; writes one JSON line per
//	                                 check to stdout; exit 1 if any check fails.
//
// Proofs are built by Tessera's own client.ProofBuilder from the log's tiles and checked
// with github.com/transparency-dev/merkle/proof -- the code a tlog-tiles client runs.
// BLAST RADIUS: reads DIR and OLDCKPT only; writes nothing but stdout/stderr.
package main

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path"

	"github.com/transparency-dev/formats/log"
	"github.com/transparency-dev/merkle/proof"
	"github.com/transparency-dev/merkle/rfc6962"
	"github.com/transparency-dev/tessera/api"
	"github.com/transparency-dev/tessera/api/layout"
	"github.com/transparency-dev/tessera/client"
	"golang.org/x/mod/sumdb/note"
)

func die(f string, a ...any) { fmt.Fprintf(os.Stderr, f+"\n", a...); os.Exit(2) }

func emit(m map[string]any) {
	b, _ := json.Marshal(m)
	fmt.Println(string(b))
}

func b64s(bs [][]byte) []string {
	out := make([]string, len(bs))
	for i, b := range bs {
		out[i] = base64.StdEncoding.EncodeToString(b)
	}
	return out
}

func main() {
	if len(os.Args) < 3 {
		die("usage: tlogcap genkey ORIGIN | tlogcap verify DIR VKEY OLDCKPT")
	}
	switch os.Args[1] {
	case "genkey":
		skey, vkey, err := note.GenerateKey(rand.Reader, os.Args[2])
		if err != nil {
			die("genkey: %v", err)
		}
		fmt.Println(skey)
		fmt.Println(vkey)
	case "verify":
		if len(os.Args) < 5 {
			die("usage: tlogcap verify DIR VKEY OLDCKPT")
		}
		os.Exit(verify(os.Args[2], os.Args[3], os.Args[4]))
	default:
		die("unknown command %q", os.Args[1])
	}
}

func verify(dir, vkey, oldPath string) int {
	ctx := context.Background()
	v, err := note.NewVerifier(vkey)
	if err != nil {
		die("verifier: %v", err)
	}
	fail := 0
	check := func(m map[string]any, err error) {
		m["ok"] = err == nil
		if err != nil {
			m["error"] = err.Error()
			fail = 1
		}
		emit(m)
	}
	readTile := func(ctx context.Context, l, i uint64, p uint8) ([]byte, error) {
		return os.ReadFile(path.Join(dir, layout.TilePath(l, i, p)))
	}
	readBundle := func(ctx context.Context, i uint64, p uint8) ([]byte, error) {
		return os.ReadFile(path.Join(dir, layout.EntriesPath(i, p)))
	}

	raw, err := os.ReadFile(path.Join(dir, layout.CheckpointPath))
	if err != nil {
		die("checkpoint: %v", err)
	}
	cp, _, _, err := log.ParseCheckpoint(raw, v.Name(), v)
	check(map[string]any{"check": "checkpoint signature", "file": "checkpoint"}, err)
	if err != nil {
		return 1
	}
	emit(map[string]any{"check": "checkpoint body", "origin": cp.Origin, "size": cp.Size,
		"root": base64.StdEncoding.EncodeToString(cp.Hash)})

	oldRaw, err := os.ReadFile(oldPath)
	if err != nil {
		die("old checkpoint: %v", err)
	}
	old, _, _, err := log.ParseCheckpoint(oldRaw, v.Name(), v)
	check(map[string]any{"check": "old checkpoint signature", "file": oldPath}, err)
	if err != nil {
		return 1
	}

	pb, err := client.NewProofBuilder(ctx, cp.Size, readTile)
	if err != nil {
		die("proof builder: %v", err)
	}
	h := rfc6962.DefaultHasher
	for bi := uint64(0); bi*layout.EntryBundleWidth < cp.Size; bi++ {
		p := layout.PartialTileSize(0, bi, cp.Size)
		b, err := readBundle(ctx, bi, p)
		if err != nil {
			die("entry bundle %d: %v", bi, err)
		}
		var eb api.EntryBundle
		if err := eb.UnmarshalText(b); err != nil {
			die("entry bundle %d: %v", bi, err)
		}
		for j, e := range eb.Entries {
			idx := bi*layout.EntryBundleWidth + uint64(j)
			leaf := h.HashLeaf(e)
			ip, err := pb.InclusionProof(ctx, idx)
			if err == nil {
				err = proof.VerifyInclusion(h, idx, cp.Size, leaf, ip, cp.Hash)
			}
			check(map[string]any{"check": "inclusion", "index": idx, "tree_size": cp.Size,
				"leaf_hash": base64.StdEncoding.EncodeToString(leaf), "proof": b64s(ip)}, err)
		}
	}
	cpf, err := pb.ConsistencyProof(ctx, old.Size, cp.Size)
	if err == nil {
		err = proof.VerifyConsistency(h, old.Size, cp.Size, cpf, old.Hash, cp.Hash)
	}
	check(map[string]any{"check": "consistency", "from_size": old.Size, "to_size": cp.Size,
		"from_root": base64.StdEncoding.EncodeToString(old.Hash),
		"to_root":   base64.StdEncoding.EncodeToString(cp.Hash), "proof": b64s(cpf)}, err)
	return fail
}
