$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& (Join-Path $PSScriptRoot 'reproduce_v0914.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Inherited v0.9.14-A reproduction failed' }
& python scripts/audit_v0914b_sensitivity.py
if ($LASTEXITCODE -ne 0) { throw 'Independent v0.9.14-B bounded sensitivity audit failed' }
Write-Output 'v0.9.14-B: 81 factorial cases + 9 OAT + 2 hypothetical continuous-box proofs and inherited science PASS'
