"""
check_residuals.py - Việc 3: kiểm chứng giả định "phần dư độc lập theo ngày" trên dữ liệu mô phỏng. Người 2.
  python src/check_residuals.py --seed 1
Đo: (1) tương quan phần dư chuẩn hóa giữa các ngày; (2) tỉ số phương sai Var(tổng)/Tổng Var (độc lập => 1);
    (3) độ phủ khoảng dự báo 80% của tổng chi D ngày: "mc" (giả định độc lập) so với "cum" và "cumb" (không giả định).
Phân phối dựng trên calib, đo trên test. Kết quả: results/diagnostics_seed{S}.csv
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from labels import make_dp, future_actual, HORIZON_MAX
from model_xgb import XGBForecaster
from run_baselines import load
from risk import volatility, mc_pool, coverage_eval

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--K", type=int, default=300)
a = ap.parse_args()

df = load(a.seed, None)
dp = make_dp(df)
sp = dp.split.to_numpy()
tr, calib, val, test = (dp[sp == s].reset_index(drop=True) for s in ("train", "calib", "val", "test"))
fc = XGBForecaster(seed=a.seed).fit(df, tr, val)
yc, yt = fc.predict_spend(df, calib), fc.predict_spend(df, test)
sd_c, _ = volatility(df, calib)
sd_t, _ = volatility(df, test)
rows = []

for name, d_, y_, sd_ in [("calib", calib, yc, sd_c), ("test", test, yt, sd_t)]:
    Z = mc_pool(d_, y_, df, sd_)
    for k in (1, 2, 3, 7):
        x, y = Z[:, :-k], Z[:, k:]
        m = ~np.isnan(x) & ~np.isnan(y)
        rows.append((f"lagcorr_k{k}_{name}", float(np.corrcoef(x[m], y[m])[0, 1])))
    D = d_.D.to_numpy()
    for d in (5, 10, 15, 20, 25):
        sel = D == d
        if sel.sum() >= 200:
            Zs = Z[sel][:, :d]
            rows.append((f"VR_D{d}_{name}", float(Zs.sum(1).var() / Zs.var(0).sum())))

# độ phủ 80% trên test
s_act = np.nansum(future_actual(df, test), axis=1)
pat = test.pattern.to_numpy()
rng = np.random.default_rng(a.seed)
zp = mc_pool(calib, yc, df, sd_c)
zp = zp[~np.isnan(zp)]
valid, Y = ~np.isnan(yt), np.nan_to_num(yt)
inside = np.zeros(len(test), dtype=bool)
for i0 in range(0, len(test), 100):
    sl = slice(i0, min(i0 + 100, len(test)))
    z = zp[rng.integers(0, len(zp), size=(Y[sl].shape[0], a.K, HORIZON_MAX))]
    tot = (np.maximum(0.0, Y[sl][:, None, :] + sd_t[sl][:, None, None] * z) * valid[sl][:, None, :]).sum(2)
    lo, hi = np.quantile(tot, [0.1, 0.9], axis=1)
    inside[sl] = (s_act[sl] >= lo) & (s_act[sl] <= hi)
cov = {"mc": inside}
for method in ("cum", "cumb"):
    cov[method] = coverage_eval(method, calib, yc, test, yt, df, levels=(0.8,))[:, 0]
for method, ins in cov.items():
    rows.append((f"cov80_{method}_all", float(ins.mean())))
    for p in ("even", "front", "weekend", "spike"):
        rows.append((f"cov80_{method}_{p}", float(ins[pat == p].mean())))
out = pd.DataFrame(rows, columns=["metric", "value"])
os.makedirs("results", exist_ok=True)
out.to_csv(f"results/diagnostics_seed{a.seed}.csv", index=False)
print(out.round(3).to_string(index=False))
