"""Kiểm tra nhanh bước 4 (đặc trưng + XGBoost). Chạy: python src/test_xgb.py"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import simulate
from labels import prepare_df, make_dp
from model_xgb import XGBForecaster

df, _ = simulate.simulate(40, 5, 0.85, 1.05, 0.10)
df = prepare_df(df)
dp = make_dp(df)
tr = dp[dp.split == "train"].iloc[::3].reset_index(drop=True)
va = dp[dp.split == "val"].iloc[::3].reset_index(drop=True)
te = dp[dp.split == "test"].reset_index(drop=True)
fc = XGBForecaster(seed=0, n_estimators=40, early_stopping_rounds=10).fit(df, tr, va)
print(f"đã huấn luyện mô hình nhỏ ({fc.best_iteration} cây) trên {len(tr):,} điểm")

# 1. Hình dạng dự báo: hữu hạn và >= 0 với h <= D, NaN với h > D
yhat = fc.predict_spend(df, te)
h = np.arange(1, 32)[None, :]
inside = h <= te.D.to_numpy()[:, None]
assert yhat.shape == (len(te), 31)
assert np.isfinite(yhat[inside]).all() and (yhat[inside] >= 0).all()
assert np.isnan(yhat[~inside]).all()
print("OK hình dạng dự báo (>= 0, NaN sau D)")

# 2. Không rò rỉ tương lai: đổi toàn bộ chi tiêu SAU ngày t thì dự báo tại t không đổi
rng = np.random.default_rng(0)
for i in rng.choice(len(te), 25, replace=False):
    row, uid = int(te.row[i]), int(te.user_id[i])
    df2 = df.copy()
    mask = (df2.user_id == uid) & (df2.index > row)
    df2.loc[mask, "spend"] = rng.integers(0, 10**6, mask.sum())
    one = te.iloc[[i]].reset_index(drop=True)
    a, b = fc.predict_spend(df, one), fc.predict_spend(df2, one)
    assert np.allclose(a, b, equal_nan=True), "XGBoost đang dùng dữ liệu tương lai!"
print("OK không rò rỉ tương lai (XGBoost)")

# 3. Không dùng cột nhãn thật `pattern`
from features import FEATURES
assert "pattern" not in FEATURES and "income_type" not in FEATURES
print("OK không dùng cột pattern")

imp = fc.importance()
assert abs(sum(imp.values()) - 1) < 1e-6
print("TẤT CẢ OK")
