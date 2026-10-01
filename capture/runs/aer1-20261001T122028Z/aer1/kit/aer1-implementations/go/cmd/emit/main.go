package main

import (
	"aer1"
	"encoding/json"
	"os"
)

func main() {
	r := aer1.Emit("b6c63ac5-f324-4fa7-ad58-c4bf83faa86a", "2026-09-27T09:00:00.000Z", "demo_tool", "1.0.0", "public", "EXECUTED BY GO", []byte(`{"inputs":{"x":1},"outputs":{"ok":true}}`))
	json.NewEncoder(os.Stdout).Encode(r)
}
