#!/usr/bin/env bash
# aer1_fetch.sh -- fetch the AER-1 draft, its test vectors and the public receipt dataset.
# BLAST RADIUS: GitHub-hosted runner only; GET requests only; writes only under $OUT/aer1.
set -u
O="$OUT/aer1"; mkdir -p "$O"
note(){ echo "$*" | tee -a "$O/steps.txt"; }
get(){ # url file
  code=$(curl -sSL -A "vlc-1-capture (github.com/MattyIceMatrix/vlc-1)" -o "$O/$2" -w '%{http_code}' "$1"); note "GET $1 -> $code ($(stat -c %s "$O/$2" 2>/dev/null) bytes)"
  [ "$code" = 200 ] || rm -f "$O/$2"; }
get https://www.ietf.org/archive/id/draft-zambo-aer1-06.txt draft-zambo-aer1-06.txt
get https://zambo.dev/aer1/test-vectors/index.json tv-index.json
git clone -q --depth 1 https://gitlab.com/rambozambodotdev/zambo.git /tmp/zk 2>&1 | tail -2
echo "kit commit $(git -C /tmp/zk rev-parse HEAD 2>/dev/null)" >> "$O/steps.txt"
mkdir -p "$O/kit" && (cd /tmp/zk && tar cf - --exclude=.git --exclude=node_modules $(ls -d aer1* test-vectors* vectors* conformance* spec* 2>/dev/null)) | tar xf - -C "$O/kit" 2>/dev/null
(cd /tmp/zk && find . -maxdepth 3 -not -path "./.git*" | head -200) > "$O/kit-tree.txt"
get https://datatracker.ietf.org/doc/draft-zambo-aer1/ datatracker.html
get "https://datatracker.ietf.org/api/v1/doc/document/draft-zambo-aer1/?format=json" datatracker.json
for u in https://zambo.dev/aer1/test-vectors/ https://zambo.dev/aer1/test-vectors https://zambo.dev/aer-1/test-vectors/ https://zambo.dev/aer-1/test-vectors https://zambo.dev/aer1/test-vectors.json https://zambo.dev/aer-1/test-vectors.json; do
  f="tv-$(echo "$u" | sed 's#https://##; s#[/.]#_#g').html"; get "$u" "$f"; done
get https://zambo.dev/aer-1 spec-page.html
# every URL the draft and spec page mention, for the record
cat "$O"/*.txt "$O"/*.html 2>/dev/null | grep -oE 'https?://[A-Za-z0-9./_%?=&#~+-]+' | sort -u > "$O/urls-mentioned.txt"
# follow any test-vector / json / github links found
grep -iE 'test-?vector|vectors|\.json|github\.com/[^/]+/[^/]*aer' "$O/urls-mentioned.txt" | head -20 | while read -r u; do
  f="linked-$(echo "$u" | sed 's#https\?://##; s#[/.?=&#]#_#g' | cut -c1-120)"; get "$u" "$f"; done
# Hugging Face dataset: card, file list, then the files if small
get https://huggingface.co/api/datasets/zambodotdev/agent-execution-receipts hf-api.json
get https://huggingface.co/datasets/zambodotdev/agent-execution-receipts/raw/main/README.md hf-README.md
python3 - "$O" <<'PY'
import json,sys,os,urllib.request
O=sys.argv[1]
try: d=json.load(open(f"{O}/hf-api.json"))
except Exception as e: print("no hf api", e); sys.exit()
files=[s["rfilename"] for s in d.get("siblings",[])]
json.dump({"license":(d.get("cardData") or {}).get("license"),"files":files,"lastModified":d.get("lastModified"),"downloads":d.get("downloads")},open(f"{O}/hf-summary.json","w"),indent=2)
os.makedirs(f"{O}/hf",exist_ok=True)
for fn in files:
    if fn.endswith((".jsonl",".json",".csv",".md",".txt")):
        u=f"https://huggingface.co/datasets/zambodotdev/agent-execution-receipts/resolve/main/{fn}"
        try:
            b=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"vlc-1-capture"}),timeout=60).read()
            if len(b)<4_000_000:
                p=f"{O}/hf/{fn}"; os.makedirs(os.path.dirname(p),exist_ok=True); open(p,"wb").write(b)
            print("hf", fn, len(b))
        except Exception as e: print("hf fail", fn, e)
PY
note "done $(date -u +%FT%TZ)"
