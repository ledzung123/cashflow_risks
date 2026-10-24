"""
check_conventions.py - Ra soat nhanh: ma nguon co dung cac quy uoc da chot (SPEC) khong. In PASS/FAIL, thoat ma 1 neu co FAIL.
  python src/check_conventions.py          (chay duoc o bat ky thu muc nao; mat vai giay)
Muc dich: phat hien ngay khi co file bi lech (vi du dung 120 nguoi thay vi 300, seed mac dinh khac nhau, hang so bi doi).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(("PASS  " if cond else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


def src(name):
    return open(os.path.join(HERE, name), encoding="utf-8").read()


def default_of(name, flag):
    m = re.search(r'add_argument\("' + re.escape(flag) + r'",[^)]*?default=([0-9.]+)', src(name))
    return float(m.group(1)) if m else None


print("-- 1. File can co --")
need = ["simulate", "labels", "baselines", "evaluate", "features", "model_xgb", "risk", "prob_metrics", "run_baselines", "run_xgb", "run_risk",
        "check_residuals", "aggregate_results", "make_report", "plot_sanity", "check_expected", "check_conventions", "test_pipeline", "test_xgb",
        "test_risk", "sensitivity", "import_real", "make_demo", "check_extras", "model_alt", "extra_analysis", "summarize_extra"]
miss = [n for n in need if not os.path.exists(os.path.join(HERE, n + ".py"))]
check("du 27 file .py", not miss, "thieu: " + ", ".join(miss) if miss else "")
check("co demo_template.html canh make_demo.py", os.path.exists(os.path.join(HERE, "demo_template.html")))

print("\n-- 2. Quy uoc du lieu: 300 nguoi x 24 chu ky, 4 tap --")
import simulate
check("N_CYCLES = 24", simulate.N_CYCLES == 24, str(simulate.N_CYCLES))
sp = simulate.SPLIT_OF_CYCLE
exp = {**{k: "train" for k in range(0, 12)}, **{k: "calib" for k in range(12, 16)}, **{k: "val" for k in range(16, 20)}, **{k: "test" for k in range(20, 24)}}
check("chia tap theo chu ky: train 0-11, calib 12-15, val 16-19, test 20-23", sp == exp)
check("tham so simulator mac dinh (PARAMS) toan 1.0", all(v == 1.0 for v in simulate.PARAMS.values()))
check("simulate.py: --users mac dinh = 300", default_of("simulate.py", "--users") == 300)
check("run_baselines.py (load dung chung cho run_xgb, run_risk, check_residuals) sinh 300 nguoi",
      re.search(r"simulate\.simulate\(300,\s*seed,\s*0\.85,\s*1\.05,\s*0\.10\)", src("run_baselines.py")) is not None)
check("make_demo.py: --users mac dinh = 300", default_of("make_demo.py", "--users") == 300)
check("sensitivity.py: --users mac dinh = 300", default_of("sensitivity.py", "--users") == 300)
check("sensitivity.py dung rho 0,85-1,05 va carry 0,10",
      "RHO_LO, RHO_HI = 0.85, 1.05" in src("sensitivity.py") and "0.10, params" in src("sensitivity.py"))
check("make_demo.py dung rho 0,85-1,05 va carry 0,10", "simulate.simulate(users, seed, 0.85, 1.05, 0.10)" in src("make_demo.py"))

print("\n-- 3. Seed: seed cuoi la 1, 2, 3 --")
for n in ("run_baselines.py", "run_xgb.py", "run_risk.py", "check_residuals.py", "sensitivity.py", "make_demo.py"):
    check(f"{n}: --seed mac dinh = 1", default_of(n, "--seed") == 1, str(default_of(n, "--seed")))
ps = open(os.path.join(HERE, "..", "run_all.ps1"), encoding="utf-8").read() if os.path.exists(os.path.join(HERE, "..", "run_all.ps1")) else ""
if ps:
    check("run_all.ps1 chay seed 1..3", "foreach ($s in 1..3)" in ps)

print("\n-- 4. Hang so cua bai toan --")
import baselines, features, labels, risk
check("theta = trung binh 14 ngay truoc ngay nhan tien", labels.THETA_WINDOW == 14)
check("chi xet diem con >= 3 ngay den ky nhan tien", labels.MIN_D == 3)
check("B1 = trung binh 14 ngay, B2 = trung binh cung thu trong 28 ngay", baselines.B1_WINDOW == 14 and baselines.B2_WINDOW == 28)
check("lich su ca nhan dung toi da 6 chu ky truoc", features.K_PREV == 6)
check("horizon toi da 31 ngay", labels.HORIZON_MAX == 31)
check("nhom 'chi cuc lon' dung nguong 0,5 ngay / 28 ngay", risk.BIG_CUT == 0.5)

print("\n-- 5. Khong dung cot nhan that `pattern` lam dac trung --")
check("pattern khong nam trong FEATURES", "pattern" not in features.FEATURES and "income_type" not in features.FEATURES)
for n in ("features.py", "model_xgb.py", "risk.py"):
    code = "\n".join(l.split("#")[0] for l in src(n).splitlines())
    check(f"{n}: ma (bo comment) khong tham chieu cot pattern", re.search(r"\[\s*[\"']pattern[\"']\s*\]|\.pattern\b", code) is None)

print("\n-- 6. Du lieu mau sinh ra dung dinh dang --")
df, _ = simulate.simulate(12, 7, 0.85, 1.05, 0.10)
cols = ["user_id", "date", "spend", "income", "balance", "cycle_id", "day_in_cycle", "D", "pattern", "income_type", "split"]
check("cot dung SPEC (11 cot, dung thu tu)", list(df.columns) == cols)
check("12 nguoi x 24 chu ky", df.user_id.nunique() == 12 and df.groupby("user_id").cycle_id.nunique().eq(24).all())
L = df.groupby(["user_id", "cycle_id"]).day_in_cycle.transform("max")
check("D = do dai chu ky - day_in_cycle (D la so ngay CON LAI)", bool((df.D == L - df.day_in_cycle).all()))
inc = df[df.income > 0]
check("moi chu ky co dung 1 ngay nhan tien, vao ngay dau chu ky", len(inc) == 12 * 24 and bool((inc.day_in_cycle == 1).all()))
check("4 kieu chi tieu chia deu (12 nguoi -> moi kieu 3 nguoi)", df.groupby("pattern").user_id.nunique().eq(3).all())
check("trong chu ky, so du chi giam sau ngay dau", bool((df[df.day_in_cycle > 1].groupby(["user_id", "cycle_id"]).balance.apply(lambda s: s.is_monotonic_decreasing or (s.diff().dropna() <= 0).all())).all()))

print(f"\n{'TAT CA DAT' if fails == 0 else str(fails) + ' TIEU CHI KHONG DAT'}")
sys.exit(1 if fails else 0)
