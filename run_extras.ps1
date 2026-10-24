# run_extras.ps1 - Chay phan DO NHAY + MVP (sau khi da chay duoc phan loi bang run_all.ps1), roi tu kiem tra ket qua.
# Dung o thu muc du an (vi du D:\cashflow_risk), trong PowerShell:
#     .\run_extras.ps1                                   # do nhay (13 kich ban, 300 nguoi, ~15 phut) + tao demo.html
#     .\run_extras.ps1 -SkipSensitivity                  # chi tao demo.html (~1 phut)
#     .\run_extras.ps1 -Csv ".\cashflow_risks\data\example_user.csv" -Balance 0     # them demo tren file CSV (demo_csv.html)
#     .\run_extras.ps1 -BrowserTest                      # them kiem tra trang bang Node.js + jsdom (can cai san)
# Mac dinh tu tim thu muc ma: .\src (neu co) hoac .\cashflow_risks.
param([string]$Src = "", [switch]$SkipInstall, [switch]$SkipSensitivity, [string]$Csv = "", [double]$Balance = 0, [switch]$BrowserTest,
      [ValidateSet("error", "zero")][string]$MissingPolicy = "error",
      [ValidateSet("error", "ffill")][string]$BalancePolicy = "error")
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
if ($Src -eq "") { if (Test-Path ".\src") { $Src = ".\src" } else { $Src = ".\cashflow_risks" } }

$required = @("simulate","labels","baselines","evaluate","features","model_xgb","risk","prob_metrics",
              "sensitivity","import_real","make_demo","check_extras")
$missing = $required | Where-Object { -not (Test-Path (Join-Path $Src "$_.py")) }
if ($missing) { throw "Thieu file trong $Src : $($missing -join ', ').py" }
if (-not (Test-Path (Join-Path $Src "demo_template.html"))) { throw "Thieu file demo_template.html trong $Src (phai nam canh make_demo.py)" }

function Invoke-Py {
    param([string]$Script, [string[]]$ScriptArgs = @())
    $path = Join-Path $Src $Script
    Write-Host ">> python $path $($ScriptArgs -join ' ')" -ForegroundColor Cyan
    & python $path @ScriptArgs
    if ($LASTEXITCODE -ne 0) { throw "LOI: $Script $($ScriptArgs -join ' ') (ma thoat $LASTEXITCODE)" }
}

if (-not $SkipInstall) {
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Cai thu vien that bai" }
}

# 1) Phan tich do nhay: 13 kich ban, moi kich ban doi MOT tham so cua simulator
if (-not $SkipSensitivity) {
    $old = ".\results\sensitivity_seed1.csv"
    if (Test-Path $old) {
        $stamp = Get-Date -Format "yyyyMMdd_HHmm"
        Rename-Item $old "sensitivity_seed1_cu_$stamp.csv"
        Write-Host "Da doi ten ket qua do nhay cu" -ForegroundColor Yellow
    }
    Invoke-Py "sensitivity.py" @("--seed", "1", "--users", "300")
    Invoke-Py "sensitivity.py" @("--seed", "1", "--report")
}

# 2) MVP: tao demo.html tu nguoi dung mo phong (tap test)
Invoke-Py "make_demo.py" @("--out", "demo.html")
if ($Csv -ne "") {
    Invoke-Py "make_demo.py" @("--csv", $Csv, "--balance", "$Balance", "--missing-policy", $MissingPolicy, "--balance-policy", $BalancePolicy, "--out", "demo_csv.html")
}

# 3) Tu kiem tra
if ($SkipSensitivity) { Invoke-Py "check_extras.py" @("--skip-sens") } else { Invoke-Py "check_extras.py" }
if ($Csv -ne "") { Invoke-Py "check_extras.py" @("--demo", "demo_csv.html", "--skip-sens") }

# 4) Tuy chon: kiem tra trang bang trinh duyet gia lap (can Node.js va 'npm install jsdom' o thu muc du an)
if ($BrowserTest) {
    $js = Join-Path $Src "test_demo.js"
    if (-not (Test-Path $js)) { throw "Thieu $js" }
    node $js "demo.html"
    if ($LASTEXITCODE -ne 0) { throw "test_demo.js bao loi" }
}

$sw.Stop()
Write-Host ("HOAN TAT sau {0:N1} phut. Mo demo.html bang trinh duyet; bang va hinh do nhay nam trong results\final\." -f $sw.Elapsed.TotalMinutes) -ForegroundColor Green
