# zenodo-new-version-1.4.3.ps1
# Run AFTER the v1.4.3-draft GitHub release is published.
# Adds VLC-1 1.4.3-draft as a NEW VERSION of the existing Zenodo record, so it
# keeps the concept DOI 10.5281/zenodo.22728393 (same as 1.0 .. 1.4.2).
#
# Needs a Zenodo personal access token with scopes deposit:write and
# deposit:actions  (zenodo.org -> Applications -> Personal access tokens -> New).
# The token is typed at a hidden prompt; it is never written to disk.
#
# Run from PowerShell:   powershell -ExecutionPolicy Bypass -File .\zenodo-new-version-1.4.3.ps1
# It stops and asks before publishing, because a published version is permanent.

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Api      = 'https://zenodo.org/api'
$Prev     = 23028240                     # the 1.4.2-draft record
$Tag      = 'v1.4.3-draft'
$Version  = '1.4.3-draft'
$Title    = 'VLC-1: Verifiable Completeness for AI System Logs 1.4.3-draft'
$PubDate  = '2026-09-30'
$ZipUrl   = "https://github.com/MattyIceMatrix/vlc-1/archive/refs/tags/$Tag.zip"
$ZipName  = "vlc-1-$Version.zip"

$Desc = @'
<p>VLC-1: Verifiable Completeness for AI System Logs 1.4.3-draft.</p>
<p>A vendor-neutral specification and conformance scheme for demonstrating the completeness of logs produced by AI systems. Defines six cumulative levels, L0 to L5 &mdash; tamper-evident, loss-accounted, coverage-declared, policy-bound and independently witnessed &mdash; with a machine-checked proof that the levels are strictly ordered and that each admits an attack the next refuses. Includes an adapter-driven conformance checker, worked example logs at every level, and a reconciler for checking an agent's self-reported transcript against an independent record.</p>
<p>Changes in 1.4.3-draft (full account in CORRIGENDUM-2026-09-30-07.md):</p>
<ul>
<li>EXT-026: new integrity mechanism merkle-tlog. The checker now recomputes an RFC 6962 Merkle tree with a C2SP signed checkpoint (Ed25519). The live Trillian Tessera capture moves from L0 to structural and attested L1; the copy with one entry removed stays L0 with VLC-L1-1 failed. No published result for any other log changes.</li>
<li>Third parties: the invinoveritas verdict ledger scored from public data at its operator's invitation. 230 chained entries recompute with zero breaks and the newest signed Nostr head matches; it scores L0 because the checker has no mechanism for its chain yet.</li>
</ul>
<p>selftest.sh and CI pass.</p>
<p>Licensing: the specification text is CC0-1.0; the reference implementation and code in this archive are MIT. Zenodo records a single licence field, so the repository is authoritative on the split.</p>
'@

# --- token, hidden ---------------------------------------------------------
$sec = Read-Host 'Zenodo token (hidden)' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try   { $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
$H = @{ Authorization = "Bearer $Token" }

# --- 1. download the release archive under a unique name -------------------
$Tmp = Join-Path $env:TEMP ("vlc143-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $Tmp | Out-Null
$ZipPath = Join-Path $Tmp $ZipName
Write-Host "Downloading $ZipUrl"
Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing
$sha = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()
Write-Host "  $ZipName  $((Get-Item $ZipPath).Length) bytes  sha256 $sha"

# --- 2. new version of the 1.4.2 record (returns the existing draft if one is open)
Write-Host "Opening new version of record $Prev"
$nv    = Invoke-RestMethod -Method Post -Uri "$Api/deposit/depositions/$Prev/actions/newversion" -Headers $H
$Draft = $nv.links.latest_draft
$d     = Invoke-RestMethod -Uri $Draft -Headers $H
Write-Host "  draft id $($d.id)"

# --- 3. drop the files copied over from 1.4.2, upload the 1.4.3 archive --------
foreach ($f in (Invoke-RestMethod -Uri "$Draft/files" -Headers $H)) {
    Write-Host "  removing carried-over file $($f.filename)"
    Invoke-RestMethod -Method Delete -Uri $f.links.self -Headers $H | Out-Null
}
Write-Host "  uploading $ZipName"
Invoke-RestMethod -Method Put -Uri "$($d.links.bucket)/$ZipName" -Headers $H `
    -InFile $ZipPath -ContentType 'application/octet-stream' | Out-Null

# --- 4. metadata: change only version, title, date, description ------------
$m = $d.metadata
foreach ($p in 'doi','prereserve_doi') { $m.PSObject.Properties.Remove($p) }
$set = @{ version = $Version; title = $Title; publication_date = $PubDate; description = $Desc }
foreach ($k in $set.Keys) { $m | Add-Member -NotePropertyName $k -NotePropertyValue $set[$k] -Force }
$body = @{ metadata = $m } | ConvertTo-Json -Depth 30
$d = Invoke-RestMethod -Method Put -Uri $Draft -Headers $H -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
    -ContentType 'application/json; charset=utf-8'

$files = Invoke-RestMethod -Uri "$Draft/files" -Headers $H
Write-Host ""
Write-Host "Draft ready -- check before publishing:"
Write-Host "  title    $($d.metadata.title)"
Write-Host "  version  $($d.metadata.version)"
Write-Host "  date     $($d.metadata.publication_date)"
Write-Host "  files    $(($files | ForEach-Object { $_.filename }) -join ', ')"
Write-Host "  DOI to be minted: $($d.metadata.prereserve_doi.doi)"
Write-Host "  preview  $($d.links.html)"
Write-Host ""

# --- 5. publish, only on an explicit yes ------------------------------------
$ok = Read-Host "Publish now? This is permanent. Type PUBLISH to confirm"
if ($ok -ne 'PUBLISH') { Write-Host "Not published. The draft stays open at the preview link."; exit 0 }
$pub = Invoke-RestMethod -Method Post -Uri "$Draft/actions/publish" -Headers $H
Write-Host ""
Write-Host "Published."
Write-Host "  Version DOI: $($pub.doi)"
Write-Host "  Record:      $($pub.links.html)"
Write-Host "Send the Version DOI line back to Claude."
