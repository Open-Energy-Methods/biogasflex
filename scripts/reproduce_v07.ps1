$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
function Run-Checked([string[]]$ArgsToRun) {
    & python @ArgsToRun
    if ($LASTEXITCODE -ne 0) { throw "Python command failed: $($ArgsToRun -join ' ')" }
}
Run-Checked -ArgsToRun @('-m','unittest','discover','-s','tests','-v')
Run-Checked -ArgsToRun @('scripts/run_v07_study.py','--plots')
Run-Checked -ArgsToRun @('scripts/independent_v07_audit.py')
Run-Checked -ArgsToRun @('-m','biogasflex','dispatch','--config','config/v06_oracle_two_period.json','--prices','data/synthetic/prices_2period_oracle.csv','--output','results/v0.6/oracle.json')
Run-Checked -ArgsToRun @('-m','biogasflex','heat-dispatch','--config','config/v07_oracle_two_period_heat.json','--prices','data/synthetic/prices_2period_oracle.csv','--output','results/v0.7/synthetic_oracle_heat_cost80.json')
Write-Host 'BiogasFlex v0.7 reproduction completed.'
