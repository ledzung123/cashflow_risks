"""Kiểm tra nhanh nhãn, baseline và chỉ số. Chạy: python src/test_pipeline.py"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import simulate
from labels import prepare_df, make_dp, future_actual, THETA_WINDOW
from baselines import predict_spend_b1, predict_spend_b2, projected_end_balance
from evaluate import evaluate

df, _ = simulate.simulate(8, 7, 0.85, 1.05, 0.10)
df = prepare_df(df)
dp = make_dp(df)
print(f"dp nhỏ: {len(dp):,} điểm")

# 1. Nhãn nhất quán
assert (dp.cycle_id >= 1).all() and (dp.D >= 3).all()
assert (dp.balance_t >= dp.theta_c).all(), "đã loại điểm balance<theta chưa?"
assert ((dp.y == 1) == dp.dip_day.notna()).all(), "y=1 <=> có ngày dip"
assert (dp.t < dp.dip_day.fillna(1e9)).all(), "mọi điểm quyết định phải trước dip_day"
r = dp.iloc[len(dp) // 2]
u, c = int(r.user_id), int(r.cycle_id)
prev = df[(df.user_id == u) & (df.cycle_id == c - 1)].spend.iloc[-THETA_WINDOW:].mean()
assert abs(prev - r.theta_c) < 1e-6, "theta_c = TB 14 ngày trước ngày nhận tiền"
print("OK nhãn")

# 2. Oracle: dự báo hoàn hảo => cảnh báo đúng nhãn (P = R = 1)
yhat = future_actual(df, dp)
assert np.allclose(projected_end_balance(dp, yhat), dp.end_balance)
res = evaluate(dp, projected_end_balance(dp, yhat) < dp.theta_c)
assert res["precision"] == 1 and res["recall"] == 1, res
print("OK oracle: P = R = 1")

# 3. Không rò rỉ tương lai: đổi toàn bộ chi tiêu SAU ngày t thì dự báo tại t không đổi
rng = np.random.default_rng(0)
for fn in (predict_spend_b1, predict_spend_b2):
    for i in rng.choice(len(dp), 40, replace=False):
        row, uid = int(dp.row[i]), int(dp.user_id[i])
        df2 = df.copy()
        mask = (df2.user_id == uid) & (df2.index > row)
        df2.loc[mask, "spend"] = rng.integers(0, 10**6, mask.sum())
        a = fn(df, dp.iloc[[i]].reset_index(drop=True))
        b = fn(df2, dp.iloc[[i]].reset_index(drop=True))
        assert np.allclose(a, b, equal_nan=True), f"{fn.__name__} dùng dữ liệu tương lai!"
print("OK không rò rỉ (B1, B2)")

# 4. Chỉ số trên ví dụ tay: 2 chu kỳ, 1 dương (dip ngày 10), 1 âm
import pandas as pd
toy = pd.DataFrame({
    "user_id": [0] * 4 + [1] * 3, "cycle_id": [1] * 4 + [1] * 3,
    "t": [1, 2, 3, 4, 1, 2, 3], "y": [1, 1, 1, 1, 0, 0, 0],
    "dip_day": [10] * 4 + [np.nan] * 3})
a = np.array([0, 0, 1, 1, 0, 1, 0], dtype=bool)
r = evaluate(toy, a)
assert abs(r["precision"] - 2 / 3) < 1e-9 and abs(r["recall"] - 2 / 4) < 1e-9
assert r["mean_days_early"] == 7 and r["cycle_recall"] == 1 and r["cycle_false_alarm"] == 1
print("OK chỉ số (ví dụ tay)")

# 5. Điểm số liên tục khớp với quy tắc cảnh báo theo biên, và AUROC/AUPRC hoạt động
from baselines import alert_by_margin, margin_score
from evaluate import rank_metrics
yb = predict_spend_b2(df, dp)
sc = margin_score(dp, yb)
for m in (-1.0, 0.0, 0.5, 2.0):
    mism = (alert_by_margin(dp, yb, m) != (sc > -m)).mean()
    assert mism < 1e-3, f"điểm số không khớp quy tắc biên m={m}: {mism}"
rm = rank_metrics(dp, dp["y"].to_numpy().astype(float))          # điểm số hoàn hảo
assert rm["auroc"] == 1.0 and abs(rm["auprc"] - 1.0) < 1e-9
rm0 = rank_metrics(dp, np.zeros(len(dp)))                         # điểm số vô nghĩa
assert abs(rm0["auroc"] - 0.5) < 1e-9
print("OK điểm số liên tục khớp quy tắc biên m; AUROC/AUPRC")

# 6. Báo sớm ở cùng mức báo nhầm: ví dụ tính tay (2 chu kỳ bình thường, 2 chu kỳ thiếu tiền, dip_day = 10)
from evaluate import lead_at_far
import pandas as pd
toy = pd.DataFrame({
    "user_id": [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3], "cycle_id": [1] * 12, "t": [1, 2, 3] * 4,
    "y": [0] * 6 + [1] * 6, "dip_day": [np.nan] * 6 + [10] * 6})
sc = [0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.5, 0.6, 0.7, 0.05, 0.4, 0.8]
r = lead_at_far(toy, sc, fars=(0.0, 0.5)).set_index("far_target")
assert r.loc[0.0, "far_actual"] == 0 and r.loc[0.0, "cycle_recall"] == 1 and r.loc[0.0, "lead_mean_all"] == 8.5   # ngưỡng 0,3: ngày 1 và ngày 2
assert r.loc[0.5, "far_actual"] == 0.5 and r.loc[0.5, "lead_mean_all"] == 8.5 and r.loc[0.5, "lead_median_caught"] == 8.5
r2 = lead_at_far(toy, [0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.5, 0.6, 0.7, 0.05, 0.1, 0.1], fars=(0.0,)).iloc[0]   # chu kỳ D không bao giờ vượt ngưỡng 0,3
assert r2.cycle_recall == 0.5 and r2.lead_mean_all == 4.5, r2          # bỏ sót tính 0 ngày: (9 + 0) / 2
print("OK báo sớm ở cùng mức báo nhầm (ví dụ tính tay)")

# 7. KS và báo sớm ở cùng Precision: chọn trên validation, áp nguyên ngưỡng sang test.
from evaluate import lead_at_precision
assert rm["ks"] == 1.0 and rm0["ks"] == 0.0                        # điểm số hoàn hảo / vô nghĩa
r3 = lead_at_precision(toy, sc, toy, sc, [1.0, 0.6, 0.99]).set_index("precision_target")
assert r3.loc[1.0, "threshold"] == 0.4 and r3.loc[1.0, "recall"] == 5 / 6 and r3.loc[1.0, "lead_mean_all"] == 8.5   # (9 + 8) / 2
assert r3.loc[0.6, "threshold"] == 0.2 and abs(r3.loc[0.6, "precision"] - 5 / 7) < 1e-12 and r3.loc[0.6, "cycle_false_alarm"] == 0.5
assert r3.loc[0.99, "threshold"] == 0.4                            # mục tiêu không đạt đúng -> lấy ngưỡng còn đạt precision >= mục tiêu
# Thay test scores/labels không được làm đổi ngưỡng đã chọn từ validation.
test_changed = toy.copy(); test_changed["y"] = 1 - test_changed["y"]
r3_changed = lead_at_precision(toy, sc, test_changed, sc[::-1], [1.0]).iloc[0]
assert r3_changed.threshold == r3.loc[1.0, "threshold"] and r3_changed.precision_val == r3.loc[1.0, "precision_val"]
print("OK ngưỡng cùng Precision chọn trên validation và giữ nguyên khi đánh giá test")

# 8. User-holdout roles are deterministic, disjoint, and cover every user exactly once.
from run_risk import user_roles
roles = user_roles(range(100))
assert {k: len(v) for k, v in roles.items()} == {"train": 50, "calib": 15, "val": 15, "test": 20}
assert sum(map(len, roles.values())) == 100
assert all(roles[a].isdisjoint(roles[b]) for a in roles for b in roles if a < b)
assert roles == user_roles(range(100))
print("OK phân chia user-holdout: không giao người dùng và tái lập")

# 9. Nhập CSV thật: điền dữ liệu chỉ khi chọn chính sách tường minh.
import os
import warnings
from import_real import load_user_csv
ex_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "example_user.csv")
ex = load_user_csv(ex_path)
raw = pd.read_csv(ex_path).astype({"spend": object})
raw.loc[5, "spend"], raw.loc[6, "spend"], raw.loc[20, "spend"] = "abc", -50000, 10 ** 9   # ô hỏng, chi âm, ngoại lai
raw = raw.drop(index=10)                                                                  # thiếu 1 ngày (kéo theo thiếu số dư)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    bad = load_user_csv(raw, missing_policy="zero", balance_policy="ffill")
q = bad.attrs["quality"]
assert (q["o_trong_hoac_loi"], q["dong_chi_am"], q["ngay_thieu"], q["so_du_thieu"]) == (1, 1, 1, 1) and q["ngay_ngoai_lai"] >= 1, q
assert len(w) == 6 and len(bad) == len(ex), (len(w), len(bad), len(ex))     # 5 cảnh báo chất lượng + 1 cảnh báo số dư tăng giữa kỳ (chi âm)
assert q["vi_pham_so_du_chi_giam"] and q["chi_am_sau_ngay_nhan_dau"] == 1
assert ex.attrs["quality"]["ngay_ngoai_lai"] == 0 and not ex.attrs["quality"]["dong_chi_am"]
assert not ex.attrs["quality"]["vi_pham_so_du_chi_giam"]
print("OK nhập CSV thật: cảnh báo và điền dữ liệu theo chính sách đã chọn")

# 10. CSV thật vi phạm giả định: chu kỳ ngắn (thiếu lịch sử 28 ngày) và tiền vào giữa chu kỳ
from labels import MIN_HISTORY
from baselines import B2_WINDOW
days = pd.date_range("2025-01-01", periods=120)
biweekly = pd.DataFrame({"date": days.strftime("%Y-%m-%d"), "spend": 100_000,
                         "income": np.where(np.arange(120) % 14 == 0, 2_000_000, 0)})
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    dfb = prepare_df(load_user_csv(biweekly))
    dpb = make_dp(dfb)
assert any("chưa đủ" in str(x.message) for x in w), "phải cảnh báo khi bỏ điểm thiếu lịch sử"
pos = dfb.groupby("user_id").cumcount().to_numpy()
assert (pos[dpb.row.to_numpy()] >= MIN_HISTORY - 1).all(), "mọi điểm quyết định phải có đủ 28 ngày lịch sử"
assert (dpb.row.to_numpy() - (B2_WINDOW - 1) >= 0).all(), "B2 không được đọc chỉ số âm"
inc = np.zeros(120); inc[[0, 31, 59, 90]] = 6_000_000; inc[[15, 45]] = 1_500_000
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    side = load_user_csv(pd.DataFrame({"date": days.strftime("%Y-%m-%d"), "spend": 150_000, "income": inc}))
assert side.attrs["quality"]["thu_nhap_giua_ky"] == 2 and side.attrs["quality"]["vi_pham_so_du_chi_giam"]
assert any("giữa chu kỳ" in str(x.message) for x in w)
print("OK CSV vi phạm giả định: bỏ điểm thiếu lịch sử, cảnh báo tiền vào giữa chu kỳ")
print("TẤT CẢ OK")
