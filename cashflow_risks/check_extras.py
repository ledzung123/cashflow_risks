"""
check_extras.py - Tu kiem tra phan do nhay + MVP sau khi chay run_extras.ps1: in PASS/FAIL, thoat ma 1 neu co FAIL.
  python src/check_extras.py [--demo demo.html] [--sens results/sensitivity_seed1.csv]
"""
import argparse
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(("PASS  " if cond else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


ap = argparse.ArgumentParser()
ap.add_argument("--demo", default="demo.html")
ap.add_argument("--sens", default="results/sensitivity_seed1.csv")
ap.add_argument("--skip-sens", action="store_true", help="bo qua phan 2 (do nhay), vi du khi chi kiem tra mot file demo")
a = ap.parse_args()

print("-- 1. Simulator: tham so mac dinh khong doi --")
import simulate
check("PARAMS mac dinh toan 1.0", all(v == 1.0 for v in simulate.PARAMS.values()), str(simulate.PARAMS))
sample = next((p for p in ("data/sample_v0.csv", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_v0.csv"))
               if os.path.exists(p)), "")
if sample:
    raw, _ = simulate.simulate(20, 42, 0.85, 1.05, 0.10)
    ref = pd.read_csv(sample)
    same = raw.reset_index(drop=True).equals(ref) or (raw.shape == ref.shape and (raw.astype(str).values == ref.astype(str).values).all())
    check("simulate mac dinh (20 nguoi, seed 42) giong het data/sample_v0.csv", same)
else:
    print("SKIP  khong co data/sample_v0.csv de so sanh ket qua mac dinh")
w = simulate.simulate(30, 3, 0.85, 1.05, 0.10, params={"weekend": 1.5})[0]
b = simulate.simulate(30, 3, 0.85, 1.05, 0.10)[0]
check("doi tham so (weekend x1.5) thi du lieu khac, va PARAMS tu khoi phuc", (not w.equals(b)) and all(v == 1.0 for v in simulate.PARAMS.values()))

print("\n-- 2. Phan tich do nhay --")
if a.skip_sens:
    print("SKIP  bo qua phan do nhay theo yeu cau")
elif os.path.exists(a.sens):
    d = pd.read_csv(a.sens).set_index("scenario")
    want = ["base"] + [f"{k}_{s}" for k in ("weekend", "front", "noise", "spike", "shock", "rho") for s in ("lo", "hi")]
    check("du 13 kich ban", set(want) == set(d.index), f"{len(d)} kich ban")
    red = 100 * (1 - d.mae_spend_XGB / d.mae_spend_B2)
    check("K1: XGB co MAE chi tieu thap hon B2 o moi kich ban, giam it nhat 10%", bool((red >= 10).all()), f"giam {red.min():.1f}% den {red.max():.1f}%")
    diff = d.f1_XGBrisk - d.f1_B2
    n2 = int((d.f1_XGBrisk > d[["f1_B1", "f1_B2"]].max(axis=1)).sum())
    check("K2: F1 cua XGB + p cao hon ca B1 va B2 o it nhat 11/13 kich ban", n2 >= 11, f"{n2}/13, hon B2 {diff.min():+.3f} den {diff.max():+.3f}")
    check("K3: ECE cua p duoi 0,04 o moi kich ban va trung binh duoi 0,02", bool((d.ece < 0.04).all()) and d.ece.mean() < 0.02,
          f"ECE {d.ece.min():.3f} den {d.ece.max():.3f}, TB {d.ece.mean():.3f}")
    check("K5: do phu khoang 80% trong [0,74; 0,86] o moi kich ban", bool(d.cov80.between(0.74, 0.86).all()), f"{d.cov80.min():.3f} den {d.cov80.max():.3f}")
    n4 = int((abs(d.f1_XGBrisk - d.f1_XGB) < 0.01).sum())
    check("K4 (thong tin): lop xac suat khong doi F1 nhieu o it nhat 9/13 kich ban", n4 >= 9, f"{n4}/13")
    non_rho = d.drop(index=["rho_lo", "rho_hi"], errors="ignore")
    check("ti le thieu tien tren test nam trong [0,2; 0,4] o cac kich ban khong doi ti le chi/thu nhap", bool(non_rho.pos_rate_test.between(0.2, 0.4).all()),
          f"{non_rho.pos_rate_test.min():.3f} den {non_rho.pos_rate_test.max():.3f}")
    check("rho_lo < base < rho_hi ve ti le thieu tien (kich ban doi ti le chi/thu nhap lam dung huong)",
          d.loc["rho_lo", "pos_rate_test"] < d.loc["base", "pos_rate_test"] < d.loc["rho_hi", "pos_rate_test"],
          f"{d.loc['rho_lo','pos_rate_test']:.3f} < {d.loc['base','pos_rate_test']:.3f} < {d.loc['rho_hi','pos_rate_test']:.3f}")
    for f in ("results/final/fig8_sensitivity.png", "results/final/sensitivity_table.csv", "results/final/sensitivity_conclusions.csv"):
        check(f"co file {f}", os.path.exists(f))
else:
    check(f"co file {a.sens}", False, "chua chay sensitivity.py")

print("\n-- 3. MVP demo.html --")
if os.path.exists(a.demo):
    h = open(a.demo, encoding="utf-8").read()
    check("khong con placeholder __DATA__", "__DATA__" not in h)
    m = re.search(r"const DATA = (.*?);\n", h, re.S)
    ok = m is not None
    check("tim thay du lieu nhung trong trang", ok)
    if ok:
        data = json.loads(m.group(1))
        U = data["users"]
        nc = sum(len(u["cycles"]) for u in U)
        check("co it nhat 1 nguoi va 1 chu ky", len(U) >= 1 and nc >= 1, f"{len(U)} nguoi, {nc} chu ky")
        tau = data["meta"]["tau"]
        check("nguong tau trong (0,05; 0,70)", 0.05 < tau < 0.70, f"{tau}")
        bad = 0
        n_pred = 0
        for u in U:
            for c in u["cycles"]:
                check_len = len(c["days"]) == c["L"]
                bad += 0 if check_len else 1
                for dday in c["days"]:
                    if dday["st"] == "p":
                        n_pred += 1
                        ok_p = 0 <= dday["p"] <= 1 and bool(dday["al"]) == (dday["p"] > tau) and len(dday["y"]) == c["L"] - dday["t"]
                        bad += 0 if ok_p else 1
        check("moi ngay du bao co p trong [0,1], canh bao khop tau, du bao du so ngay con lai", bad == 0, f"{n_pred} ngay du bao, {bad} loi")
        check("trang ghi ro la du lieu mo phong / minh hoa", "mô phỏng" in h or "mo phong" in h)
    check("kich thuoc trang duoi 3 MB", os.path.getsize(a.demo) < 3 * 1024 * 1024, f"{os.path.getsize(a.demo) / 1024:.0f} KB")
else:
    check(f"co file {a.demo}", False, "chua chay make_demo.py")

print(f"\n{'TAT CA DAT' if fails == 0 else str(fails) + ' TIEU CHI KHONG DAT'}")
sys.exit(1 if fails else 0)
