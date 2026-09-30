# zenodo-finish-1.4.3.ps1
# Resumes the open 1.4.3-draft Zenodo draft (id 23063984): sets the metadata and
# publishes on an explicit yes. The file was already uploaded by the first run.
# Fix over the first script: Content-Type is exactly 'application/json'.

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Draft   = 'https://zenodo.org/api/deposit/depositions/23063984'
$Version = '1.4.3-draft'
$Title   = 'VLC-1: Verifiable Completeness for AI System Logs 1.4.3-draft'
$PubDate = '2026-09-30'

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

$sec = Read-Host 'Zenodo token (hidden)' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try   { $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
$H = @{ Authorization = "Bearer $Token" }

$d = Invoke-RestMethod -Uri $Draft -Headers $H
if ($d.submitted) { Write-Host "Draft $($d.id) is already published: DOI $($d.doi)"; exit 0 }

# Files: expect exactly the 1.4.3 zip. Show its checksum against the local copy.
$files = @(Invoke-RestMethod -Uri "$Draft/files" -Headers $H)
if ($files.Count -ne 1 -or $files[0].filename -notlike '*1.4.3-draft*.zip') {
    Write-Host "Unexpected files on the draft: $(($files | ForEach-Object { $_.filename }) -join ', ')"
    Write-Host "Stopping without changes. Send this output to Claude."; exit 1
}
$local = Get-ChildItem "$env:TEMP\vlc143-*\vlc-1-1.4.3-draft.zip" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
$remoteMd5 = $files[0].checksum
if ($local) {
    $localMd5 = (Get-FileHash $local.FullName -Algorithm MD5).Hash.ToLower()
    if ($localMd5 -ne $remoteMd5) { Write-Host "Checksum mismatch: local $localMd5, Zenodo $remoteMd5. Stopping."; exit 1 }
    Write-Host "File on Zenodo matches the downloaded archive (md5 $remoteMd5)"
} else {
    Write-Host "File on Zenodo: $($files[0].filename)  md5 $remoteMd5  (local copy not found to compare)"
}

# Metadata: change only version, title, date, description.
$m = $d.metadata
foreach ($p in 'doi','prereserve_doi') { $m.PSObject.Properties.Remove($p) }
$set = @{ version = $Version; title = $Title; publication_date = $PubDate; description = $Desc }
foreach ($k in $set.Keys) { $m | Add-Member -NotePropertyName $k -NotePropertyValue $set[$k] -Force }
$body = @{ metadata = $m } | ConvertTo-Json -Depth 30
$d = Invoke-RestMethod -Method Put -Uri $Draft -Headers $H `
     -Body ([Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json'

Write-Host ""
Write-Host "Draft ready -- check before publishing:"
Write-Host "  title    $($d.metadata.title)"
Write-Host "  version  $($d.metadata.version)"
Write-Host "  date     $($d.metadata.publication_date)"
Write-Host "  file     $($files[0].filename)"
Write-Host "  DOI to be minted: $($d.metadata.prereserve_doi.doi)"
Write-Host "  preview  $($d.links.html)"
Write-Host ""

$ok = Read-Host "Publish now? This is permanent. Type PUBLISH to confirm"
if ($ok -ne 'PUBLISH') { Write-Host "Not published. The draft stays open at the preview link."; exit 0 }
$pub = Invoke-RestMethod -Method Post -Uri "$Draft/actions/publish" -Headers $H
Write-Host ""
Write-Host "Published."
Write-Host "  Version DOI: $($pub.doi)"
Write-Host "  Record:      $($pub.links.html)"
Write-Host "Send the Version DOI line back to Claude."
