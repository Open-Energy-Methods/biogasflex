$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = (Join-Path (Get-Location) 'src') + [IO.Path]::PathSeparator + $env:PYTHONPATH
python -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python scripts/recompute_v09_against_frozen.py
if ($LASTEXITCODE -ne 0) { throw 'Clean scenario rerun failed' }
python scripts/independent_v08_audit.py
if ($LASTEXITCODE -ne 0) { throw 'v0.8 ledger audit failed' }
python scripts/audit_v09_candidate.py
if ($LASTEXITCODE -ne 0) { throw 'v0.9 source/assumption audit failed' }
python scripts/verify_v09_manifest.py
if ($LASTEXITCODE -ne 0) { throw 'Release manifest failed' }
Write-Output 'v0.9 reproducibility gates PASS'
