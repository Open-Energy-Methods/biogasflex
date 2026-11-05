$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests -v 2>&1 | Out-File -FilePath reports/v08_test_results.txt -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
python scripts/run_v07_study.py --plots
if ($LASTEXITCODE -ne 0) { throw 'v0.7 reproduction failed' }
python scripts/independent_v07_audit.py
if ($LASTEXITCODE -ne 0) { throw 'v0.7 independent ledger audit failed' }
python scripts/run_v08_study.py --plots
if ($LASTEXITCODE -ne 0) { throw 'v0.8 study failed' }
python scripts/independent_v08_audit.py | Out-File -FilePath reports/V08_INDEPENDENT_AUDIT.json -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'v0.8 independent ledger audit failed' }
Write-Host 'BiogasFlex v0.8: 216 scenarios, 5 emergency cases, full regression and ledgers PASS.'
