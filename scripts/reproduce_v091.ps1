$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = (Join-Path (Get-Location) 'src') + [IO.Path]::PathSeparator + $env:PYTHONPATH
python -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
python scripts/recompute_v09_against_frozen.py
if ($LASTEXITCODE -ne 0) { throw 'Scenario recomputation failed' }
python scripts/independent_v08_audit.py
if ($LASTEXITCODE -ne 0) { throw 'v0.8 audit failed' }
python scripts/audit_v09_candidate.py
if ($LASTEXITCODE -ne 0) { throw 'v0.9 audit failed' }
python scripts/verify_v091_environment.py
if ($LASTEXITCODE -ne 0) { throw 'v0.9.1 environment check failed' }
python scripts/verify_v091_inherited_frozen.py
if ($LASTEXITCODE -ne 0) { throw 'Inherited research freeze failed' }
python scripts/verify_v09_manifest.py
if ($LASTEXITCODE -ne 0) { throw 'Release SHA-256 manifest failed' }
python scripts/verify_v091_git_coverage.py
if ($LASTEXITCODE -ne 0) { throw 'Git coverage failed' }
Write-Output 'v0.9.1 all inherited scientific and release-engineering gates PASS'
