param([ValidateSet("all", "fit", "analysis")][string]$Stage = "all", [string]$Python = "python")
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Push-Location $PSScriptRoot
try {
    & $Python cashflow_risks/run_upgrade.py --stage $Stage
    if ($LASTEXITCODE -ne 0) { throw "Upgrade evaluation failed; checkpoints remain available." }
    if ($Stage -ne "fit") {
        & $Python cashflow_risks/plot_upgrade.py
        if ($LASTEXITCODE -ne 0) { throw "Upgrade figures failed." }
    }
} finally {
    Pop-Location
}
