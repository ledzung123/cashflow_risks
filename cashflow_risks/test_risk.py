"""Kiểm tra nhanh bước 5 (xác suất thiếu tiền). Chạy: python src/test_risk.py"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import simulate
from labels import prepare_df, make_dp, future_actual
from baselines import predict_spend_b2
from risk import (volatility, cum_pool, cum_prob, mc_pool, mc_prob, fit_predict, persist, brier, ece)
from evaluate import evaluate

df, _ = simulate.simulate(60, 3, 0.85, 1.05, 0.10)
df = prepare_df(df)
dp = make_dp(df)
calib = dp[dp.split == "calib"].reset_index(drop=True)
val = dp[dp.split == "val"].reset_index(drop=True)
test = dp[dp.split == "test"].reset_index(drop=True)
yc, yv, yt = (predict_spend_b2(df, d) for d in (calib, val, test))

# 1. p nằm trong [0, 1] và không NaN, cho cả hai phương pháp
for method in ("cum", "mc"):
    pv, pt = fit_predict(method, calib, yc, [(val, yv), (test, yt)], df, K=100)
    assert np.isfinite(pv).all() and np.isfinite(pt).all()
    assert (pv >= 0).all() and (pv <= 1).all() and (pt >= 0).all() and (pt <= 1).all()
print("OK p trong [0, 1] (cum, mc)")

# 2. Đơn điệu: cùng dự báo, số dư cao hơn thì p không tăng
sd, cv = volatility(df, test)
pool = cum_pool(calib, yc, df, volatility(df, calib)[1])
base = cum_prob(pool, test, yt, cv)
rich = test.copy(); rich["balance_t"] = rich["balance_t"] + 2_000_000
assert (cum_prob(pool, rich, yt, cv) <= base + 1e-12).all()
print("OK đơn điệu theo số dư")

# 3. Oracle: dự báo hoàn hảo + sai số = 0 => p chỉ nhận 0 hoặc 1 và khớp nhãn y
yo = future_actual(df, test)
pool0 = dict(q=np.ones(500), D=np.full(500, 10), cv=np.zeros(500), cycle=np.zeros(500))
p0 = cum_prob(pool0, test, yo, np.zeros(len(test)))
assert set(np.unique(p0)) <= {0.0, 1.0}
assert (p0.astype(int) == test.y.to_numpy()).all(), "oracle phải khớp nhãn"
print("OK oracle: p khớp nhãn y")

# 4. Không rò rỉ: p tại ngày t không đổi khi đổi chi tiêu SAU ngày t (phân phối calib cố định)
rng = np.random.default_rng(0)
for i in rng.choice(len(test), 20, replace=False):
    row, uid = int(test.row[i]), int(test.user_id[i])
    df2 = df.copy()
    m = (df2.user_id == uid) & (df2.index > row)
    df2.loc[m, "spend"] = rng.integers(0, 10**6, m.sum())
    one = test.iloc[[i]].reset_index(drop=True)
    a = cum_prob(pool, one, predict_spend_b2(df, one), volatility(df, one)[1])
    b = cum_prob(pool, one, predict_spend_b2(df2, one), volatility(df2, one)[1])
    assert np.allclose(a, b)
print("OK không rò rỉ tương lai")

# 4b. Bốn tập tách rời theo chu kỳ và theo thời gian
cyc = {k: set(dp[dp.split == k].cycle_id) for k in ("train", "calib", "val", "test")}
assert all(cyc[a].isdisjoint(cyc[b]) for a in cyc for b in cyc if a < b)
assert max(cyc["train"]) < min(cyc["calib"]) <= max(cyc["calib"]) < min(cyc["val"]) <= max(cyc["val"]) < min(cyc["test"])
print("OK bốn tập (train/calib/val/test) tách rời và theo thứ tự thời gian")

# 5. persist và chỉ số
a = np.array([1, 1, 0, 1, 1, 1], dtype=bool)
toy = type("T", (), {})
import pandas as pd
d = pd.DataFrame({"user_id": [0] * 6, "cycle_id": [1] * 6})
assert persist(d, a, 2).tolist() == [False, True, False, False, True, True]
assert abs(brier([0.5, 0.5], [1, 0]) - 0.25) < 1e-12 and ece([0.25] * 4, [0, 0, 0, 1]) < 1e-12
print("OK persist, Brier, ECE")

# 6. Chỉ số cho p_t và độ phủ khoảng dự báo
from prob_metrics import prob_metrics, prob_metrics_by, d_bucket
from risk import cum_pool, cum_coverage, bigdays, coverage_eval
yy = np.array([0, 0, 1, 1, 0, 1, 0, 1] * 50)
m = prob_metrics(yy.astype(float), yy)                       # p hoàn hảo
assert m["brier"] < 1e-9 and m["auroc"] == 1 and m["brier_skill"] > 0.99
m0 = prob_metrics(np.full(len(yy), yy.mean()), yy)             # luôn đoán tỉ lệ nền
assert abs(m0["brier_skill"]) < 1e-9 and abs(m0["auroc"] - 0.5) < 1e-9
rng2 = np.random.default_rng(1)
pr = rng2.uniform(0, 1, 20000); yr = (rng2.uniform(0, 1, 20000) < pr).astype(int)   # hiệu chỉnh hoàn hảo
mr = prob_metrics(pr, yr)
assert abs(mr["cal_slope"] - 1) < 0.1 and abs(mr["cal_intercept"]) < 0.1 and mr["ece"] < 0.03
assert set(d_bucket([3, 7, 10, 15, 20, 30])) == {"3-4", "5-7", "8-11", "12-16", "17-21", "22-31"}
bp = prob_metrics_by(pr, yr, np.where(pr < 0.5, "thấp", "cao"))
assert set(bp.index) == {"thấp", "cao"}
cv_c = volatility(df, calib)[1]
for big in (None, bigdays(df, calib)):                         # độ phủ trong mẫu ~ mức danh nghĩa
    pool_c = cum_pool(calib, yc, df, cv_c, big)
    cov = cum_coverage(pool_c, calib, yc, df, cv_c, big, (0.5, 0.8, 0.9)).mean(0)
    assert np.all(np.abs(cov - np.array([0.5, 0.8, 0.9])) < 0.06), cov
pv2, pt2 = fit_predict("cumb", calib, yc, [(val, yv), (test, yt)], df)
assert np.isfinite(pv2).all() and (pt2 >= 0).all() and (pt2 <= 1).all()
assert coverage_eval("mc", calib, yc, test, yt, df) is None
print("OK chỉ số p_t, độ phủ khoảng dự báo, nhóm big28")
print("TẤT CẢ OK")
