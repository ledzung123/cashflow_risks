# run_all.ps1 - Chay toan bo pipeline loi (buoc 1-6) tu dau den cuoi, roi tu kiem tra ket qua.
# Dung o thu muc du an (vi du D:\cashflow_risk), trong PowerShell:
#     .\run_all.ps1
# Mac dinh tu tim thu muc ma: .\src (neu co) hoac .\cashflow_risks. Co the chi ro:  .\run_all.ps1 -Src ".\cashflow_risks"
# Bo qua cai thu vien:  .\run_all.ps1 -SkipInstall
param([string]$Src = "", [switch]$SkipInstall)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
if ($Src -eq "") { if (Test-Path ".\src") { $Src = ".\src" } else { $Src = ".\cashflow_risks" } }

$required = @("simulate","labels","baselines","evaluate","features","model_xgb","risk","prob_metrics",
              "run_baselines","run_xgb","run_risk","check_residuals","aggregate_results","make_report",
              "test_pipeline","test_xgb","test_risk","check_expected","check_conventions","plot_sanity",
              "model_alt","extra_analysis","summarize_extra","error_cases","explain","supplement",
              "run_user_holdout","summarize_user_holdout")
$missing = $required | Where-Object { -not (Test-Path (Join-Path $Src "$_.py")) }
if ($missing) { throw "Thieu file trong $Src : $($missing -join ', ').py" }

function Invoke-Py {
    param([string]$Script, [string[]]$ScriptArgs = @())
    $path = Join-Path $Src $Script
    Write-Host ">> python $path $($ScriptArgs -join ' ')" -ForegroundColor Cyan
    & python $path @ScriptArgs
    if ($LASTEXITCODE -ne 0) { throw "LOI: $Script $($ScriptArgs -join ' ') (ma thoat $LASTEXITCODE)" }
}

if (-not $SkipInstall) {
    # Ghim dung phien ban da tao bo so lieu chinh thuc (xem requirements.txt, THAY_DOI.md)
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Cai thu vien that bai" }
}

# Giu ket qua cu, tranh tron voi ket qua moi
if (Test-Path ".\results") {
    $stamp = Get-Date -Format "yyyyMMdd_HHmm"
    Rename-Item ".\results" "results_cu_$stamp"
    Write-Host "Da doi ten results cu thanh results_cu_$stamp" -ForegroundColor Yellow
}

# 0) Ra soat quy uoc, sinh du lieu mo phong 300 nguoi x 24 chu ky (219.000 dong) va ve hinh kiem tra du lieu
Invoke-Py "check_conventions.py"
Invoke-Py "simulate.py" @("--users", "300", "--seed", "42", "--out", "data\daily.csv")
Invoke-Py "plot_sanity.py" @("--csv", "data\daily.csv", "--out", "results\final\fig0_sanity_du_lieu.png")

# 1) Kiem tra ma nguon
foreach ($t in @("test_pipeline","test_xgb","test_risk")) { Invoke-Py "$t.py" }

# 2) Chay 3 seed: B1/B2, XGBoost, xac suat p va chi so p_t, kiem chung phan du
foreach ($s in 1..3) {
    foreach ($r in @("run_baselines","run_xgb","run_risk","check_residuals","extra_analysis")) {
        Invoke-Py "$r.py" @("--seed", "$s")
    }
}

# Danh gia phu ve kha nang tong quat hoa sang nguoi dung khong tham gia cac vai tro train/calib/val.
Invoke-Py "run_user_holdout.py" @("--seeds", "1", "2", "3")
Invoke-Py "summarize_user_holdout.py"

# 3) Gop 3 seed, tao bang va hinh cho bao cao
foreach ($p in @("baselines","xgb","risk")) { Invoke-Py "aggregate_results.py" @("--prefix", $p, "--seeds", "1", "2", "3") }
Invoke-Py "make_report.py" @("--seeds", "1", "2", "3")
Invoke-Py "summarize_extra.py"
# Phan tich loi (bao nham / bo sot) va ly do canh bao (SHAP) - xem THAY_DOI.md
Invoke-Py "error_cases.py" @("--seeds", "1", "2", "3")
Invoke-Py "explain.py" @("--seed", "1")
# Mat can bang lop (so sanh nguong) va cong bang theo muc thu nhap - xem THAY_DOI.md
Invoke-Py "supplement.py" @("--seeds", "1", "2", "3")

# 4) Tu kiem tra ket qua dung/sai
Invoke-Py "check_expected.py"

$sw.Stop()
Write-Host ("HOAN TAT sau {0:N1} phut. Ket qua nam trong results\final\ (bat dau bang RESULTS.md)." -f $sw.Elapsed.TotalMinutes) -ForegroundColor Green
