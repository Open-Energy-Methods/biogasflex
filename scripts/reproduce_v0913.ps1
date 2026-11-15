$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = (Join-Path (Get-Location) 'src') + [IO.Path]::PathSeparator + $env:PYTHONPATH
$steps = @(
    @('-m', 'unittest', 'discover', '-s', 'tests', '-q'),
    @('scripts/recompute_v09_against_frozen.py'),
    @('scripts/independent_v08_audit.py'),
    @('scripts/audit_v09_candidate.py'),
    @('scripts/verify_v0913_environment.py'),
    @('scripts/verify_v091_inherited_frozen.py'),
    @('scripts/certify_v092_dual_bounds.py'),
    @('scripts/run_v093_stress.py'),
    @('scripts/audit_v095_operational.py'),
    @('scripts/audit_v096_commitment.py'),
    @('scripts/audit_v097_hourly.py'),
    @('scripts/audit_v098_rolling.py'),
    @('scripts/audit_v0981_maintenance.py'),
    @('scripts/audit_v099_historical.py'),
    @('scripts/audit_v0910_market_boundary.py'),
    @('scripts/audit_v0911_hard_contract.py'),
    @('scripts/audit_v0912_external_chp.py'),
    @('scripts/audit_v0913_market_provenance.py'),
    @('scripts/verify_v09_manifest.py'),
    @('scripts/verify_v091_git_coverage.py')
)
foreach ($arguments in $steps) {
    & python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Reproduction gate failed: $($arguments -join ' ')" }
}
Write-Output 'v0.9.13 market provenance and inherited external annual CHP/optimization, exact duals, synthetic LP oracle, ramp model, binary on/off oracle and manifest PASS'
