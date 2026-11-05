$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot '..')
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Test suite failed' }
python -m biogasflex dispatch --config config/v06_oracle_two_period.json --prices data/synthetic/prices_2period_oracle.csv --output results/v0.6/oracle.json
if ($LASTEXITCODE -ne 0) { throw 'Toy oracle failed' }
python -m biogasflex sweep --config config/v06_oracle_two_period.json --prices data/synthetic/prices_2period_oracle.csv --output results/v0.6/oracle_sweep.json
if ($LASTEXITCODE -ne 0) { throw 'Toy sweep failed' }
python -m biogasflex dispatch --config config/v06_lovsta_counterfactual.json --prices data/observed/svk_se3_20200101_CC-BY-4.0.csv --output results/v0.6/lovsta_counterfactual.json
if ($LASTEXITCODE -ne 0) { throw 'Lövsta counterfactual failed' }
python -m biogasflex sweep --config config/v06_lovsta_counterfactual.json --prices data/observed/svk_se3_20200101_CC-BY-4.0.csv --output results/v0.6/lovsta_storage_sweep.json
if ($LASTEXITCODE -ne 0) { throw 'Lövsta storage sweep failed' }
python scripts/generate_v06_figures.py
if ($LASTEXITCODE -ne 0) { throw 'Plot regeneration failed' }
