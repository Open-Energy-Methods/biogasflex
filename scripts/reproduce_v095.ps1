$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = (Join-Path (Get-Location) 'src') + [IO.Path]::PathSeparator + $env:PYTHONPATH
$steps = @(
    @('-m', 'unittest', 'discover', '-s', 'tests', '-q'),
    @('scripts/recompute_v09_against_frozen.py'),
    @('scripts/independent_v08_audit.py'),
    @('scripts/audit_v09_candidate.py'),
    @('scripts/verify_v095_environment.py'),
    @('scripts/verify_v091_inherited_frozen.py'),
    @('scripts/certify_v092_dual_bounds.py'),
    @('scripts/run_v093_stress.py'),
    @('scripts/audit_v095_operational.py'),
    @('scripts/verify_v09_manifest.py'),
    @('scripts/verify_v091_git_coverage.py')
)
foreach ($arguments in $steps) {
    & python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Reproduction gate failed: $($arguments -join ' ')" }
}
Write-Output 'v0.9.5 research-frozen, dual, solver-free, experimental-operating and integrity gates PASS'
