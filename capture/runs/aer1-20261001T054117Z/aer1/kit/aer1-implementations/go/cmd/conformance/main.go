package main

import (
	"aer1"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	b, _ := os.ReadFile("../vectors/index.json")
	var idx struct {
		Vectors []struct {
			ID          string `json:"id"`
			Fixture     string `json:"fixture"`
			VectorGroup string `json:"vector_group"`
			Expected    bool   `json:"expected_verdict"`
		} `json:"vectors"`
	}
	json.Unmarshal(b, &idx)
	pass := 0
	for _, v := range idx.Vectors {
		r := aer1.Load(filepath.Join("..", "vectors", v.Fixture))
		got := len(aer1.Verify(r)) == 0
		if v.ID == "missing-inputs" {
			got = got && aer1.Profile(r)
		}
		if v.VectorGroup == "anchored" {
			got = got && aer1.Anchor(r)
		}
		if got == v.Expected {
			pass++
			fmt.Println("PASS", v.ID)
		} else {
			fmt.Println("FAIL", v.ID)
		}
	}
	fmt.Printf("CONFORMANCE: %d/%d\n", pass, len(idx.Vectors))
	aerDir := filepath.Join("..", "..", "aer-1")
	cp, ct := gateChain(aerDir)
	mp, mt := gateMerkle(aerDir)
	fmt.Printf("CHAIN: %d/%d\n", cp, ct)
	fmt.Printf("MERKLE-VERDICT: %d/%d\n", mp, mt)
	if pass != len(idx.Vectors) || cp != ct || mp != mt {
		os.Exit(1)
	}
}

type chainVector struct {
	Name            string        `json:"name"`
	Timeline        []interface{} `json:"timeline"`
	ExpectedVerdict string        `json:"expected_verdict"`
}

func gateChain(dir string) (int, int) {
	path := filepath.Join(dir, "chain-vectors.json")
	b, err := os.ReadFile(path)
	if err != nil {
		fmt.Println("FAIL chain-vectors.json missing:", path)
		return 0, 1
	}
	var cf struct {
		Vectors []chainVector `json:"vectors"`
	}
	if json.Unmarshal(b, &cf) != nil || len(cf.Vectors) == 0 {
		fmt.Println("FAIL chain-vectors.json unreadable or empty")
		return 0, 1
	}
	pass := 0
	for _, v := range cf.Vectors {
		if v.ExpectedVerdict != "valid" && v.ExpectedVerdict != "invalid" {
			fmt.Println("FAIL chain", v.Name, "bad expected_verdict")
			continue
		}
		fails := aer1.VerifyChain(v.Timeline)
		if (len(fails) == 0) == (v.ExpectedVerdict == "valid") {
			pass++
			fmt.Println("PASS chain", v.Name)
		} else {
			fmt.Println("FAIL chain", v.Name, fails)
		}
	}
	return pass, len(cf.Vectors)
}

type merkleVector struct {
	Name                    string   `json:"name"`
	ReceiptIDs              []string `json:"receipt_ids"`
	ExpectedRoot            string   `json:"expected_root"`
	ExpectedWorkflowVerdict string   `json:"expected_workflow_verdict"`
	RejectedBy              string   `json:"rejected_by"`
}

func gateMerkle(dir string) (int, int) {
	path := filepath.Join(dir, "merkle-vectors.json")
	b, err := os.ReadFile(path)
	if err != nil {
		fmt.Println("FAIL merkle-vectors.json missing:", path)
		return 0, 1
	}
	var mf struct {
		Vectors []merkleVector `json:"vectors"`
	}
	if json.Unmarshal(b, &mf) != nil || len(mf.Vectors) == 0 {
		fmt.Println("FAIL merkle-vectors.json unreadable or empty")
		return 0, 1
	}
	var checked, passed int
	for i := range mf.Vectors {
		v := &mf.Vectors[i]
		if v.ExpectedWorkflowVerdict == "" {
			continue
		}
		checked++
		if v.ExpectedWorkflowVerdict != "valid" && v.ExpectedWorkflowVerdict != "invalid" {
			fmt.Println("FAIL merkle", v.Name, "bad expected_workflow_verdict")
			continue
		}
		steps := make([]interface{}, len(v.ReceiptIDs))
		for i, rid := range v.ReceiptIDs {
			steps[i] = map[string]interface{}{"seq": i + 1, "receipt_id": rid}
		}
		w := map[string]interface{}{"steps": steps, "merkle_root": v.ExpectedRoot}
		fails := aer1.VerifyWorkflow(w)
		want := v.ExpectedWorkflowVerdict == "valid"
		ok := (len(fails) == 0) == want
		if !want {
			mentioned := v.RejectedBy == ""
			for _, fs := range fails {
				if v.RejectedBy != "" && strings.Contains(fs, v.RejectedBy) {
					mentioned = true
				}
			}
			ok = ok && mentioned
		}
		if ok {
			fmt.Println("PASS merkle", v.Name)
			passed++
		} else {
			fmt.Println("FAIL merkle", v.Name, fails)
		}
	}
	if checked == 0 {
		fmt.Println("FAIL merkle-vectors.json has no workflow-verdict vectors")
		return 0, 1
	}
	return passed, checked
}
