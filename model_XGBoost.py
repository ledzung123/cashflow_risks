"""
Bước 4 — Mô hình dự báo
XGBoost dự báo trực tiếp chi tiêu ngày t+h.
"""
import numpy as np
import pandas as pd
import xgboost as xgb

SEED = 42
MIN_REMAINING_DAYS = 1
GLOBAL_MAX_H = 30        

df = pd.read_csv("data/sample_v0.csv", parse_dates=["date"])
df = df.sort_values(["user_id", "date"]).reset_index(drop=True)
new_cycle_mask = df.groupby("user_id")["day_in_cycle"].diff() < 0
df["cycle_id"] = new_cycle_mask.astype(int).groupby(df["user_id"]).cumsum()
df["D"] = df["day_in_cycle"] + df["days_to_next_income"] - 1
df = df.sort_values(["user_id", "cycle_id", "day_in_cycle"]).reset_index(drop=True)

# ============================================================
# Bước 3 (một phần, tính nội bộ — KHÔNG lưu trong daily.csv gốc):
# theta_t = trung bình chi tiêu 14 ngày gần nhất tại ngày t, chỉ dùng
# dữ liệu <= ngày t-1 (shift(1) trước khi rolling, tránh leak chính ngày t)
# ============================================================
g_user = df.sort_values(["user_id", "date"]).groupby("user_id")["spend"]
df = df.sort_values(["user_id", "date"]).reset_index(drop=True)
df["theta_t"] = g_user.transform(lambda s: s.shift(1).rolling(14, min_periods=5).mean())

# ============================================================
# Đặc trưng "backward-looking" — chỉ dùng spend đến trước ngày t
# ============================================================
g = df.groupby("user_id")["spend"]
df["avg7"]  = g.transform(lambda s: s.shift(1).rolling(7,  min_periods=3).mean())
df["avg14"] = g.transform(lambda s: s.shift(1).rolling(14, min_periods=5).mean())
df["avg28"] = g.transform(lambda s: s.shift(1).rolling(28, min_periods=10).mean())
df["std14"] = g.transform(lambda s: s.shift(1).rolling(14, min_periods=5).std())
df["sum7"]  = g.transform(lambda s: s.shift(1).rolling(7,  min_periods=3).sum())
df["balance_over_theta"] = df["balance"] / df["theta_t"].replace(0, np.nan)

BACKWARD_FEATS = ["avg7", "avg14", "avg28", "std14", "sum7", "balance_over_theta"]

# ============================================================
# Số ngày còn lại trong chu kỳ hiện tại (tính cả hôm nay) -> quyết định
# có tạo sample tại dòng này hay không, và horizon tối đa cho phép
# ============================================================
df["remaining_days"] = df["D"] - df["day_in_cycle"]
decision_rows = df[df["remaining_days"] >= MIN_REMAINING_DAYS].copy()
print(f"Số điểm quyết định (remaining_days >= {MIN_REMAINING_DAYS}): "
      f"{len(decision_rows):,} / {len(df):,} dòng gốc")

# ============================================================
# Sinh mẫu "direct multi-horizon": với mỗi h, lấy target bằng cách
# shift(-h) TRONG CÙNG (user_id, cycle_id) -> nếu h vượt quá chu kỳ,
# pandas tự trả NaN (không bị lẫn sang chu kỳ kế tiếp) -> dropna sau đó
# sẽ tự loại các h không hợp lệ, không cần tính max_h thủ công.
# ============================================================
cycle_sorted = df.sort_values(["user_id", "cycle_id", "day_in_cycle"])
cycle_group = cycle_sorted.groupby(["user_id", "cycle_id"])["spend"]

frames = []
for h in range(1, GLOBAL_MAX_H + 1):
    tmp = decision_rows.copy()
    tmp["h"] = h

    target_date = tmp["date"] + pd.to_timedelta(h, unit="D")
    tmp["target_date"] = target_date
    tmp["target_weekday"] = target_date.dt.weekday
    tmp["target_is_weekend"] = (tmp["target_weekday"] >= 5).astype(int)
    # vì h bị giới hạn trong cùng chu kỳ, ngày-trong-chu-kỳ của ngày đích
    # chỉ đơn giản là cộng dồn (không cần tra bảng)
    tmp["target_day_in_cycle"] = tmp["day_in_cycle"] + h

    # lấy target_spend bằng shift(-h) trong đúng nhóm (user_id, cycle_id)
    shifted = cycle_group.shift(-h)
    tmp["target_spend"] = shifted.reindex(tmp.index)

    frames.append(tmp)

samples = pd.concat(frames, ignore_index=True)
samples = samples.dropna(
    subset=["target_spend"] + BACKWARD_FEATS + ["target_weekday", "target_is_weekend"]
).reset_index(drop=True)

# ============================================================
# Đặc trưng dùng cho mô hình — TUYỆT ĐỐI KHÔNG CÓ "pattern"
# ============================================================
FEATURE_COLS = (
    ["h", "target_weekday", "target_is_weekend", "target_day_in_cycle",
     "day_in_cycle", "remaining_days"]
    + BACKWARD_FEATS
)
assert "pattern" not in FEATURE_COLS, "LỖI: pattern là nhãn thật, không được dùng làm đặc trưng!"
assert "pattern" not in samples[FEATURE_COLS].columns

# ============================================================
# Chia tập theo thời gian (walk-forward), xấp xỉ tỉ lệ 12/3/3 (rút gọn)
# ============================================================
TRAIN_END = pd.Timestamp("2025-09-01")
VAL_END   = pd.Timestamp("2025-11-01")

train = samples[samples["date"] < TRAIN_END]
val   = samples[(samples["date"] >= TRAIN_END) & (samples["date"] < VAL_END)]
test  = samples[samples["date"] >= VAL_END]

print(f"Train: {len(train):,} mẫu | Validation: {len(val):,} mẫu | Test: {len(test):,} mẫu")

# ============================================================
# Huấn luyện XGBoost (một model chung, h là một đặc trưng)
# ============================================================
dtrain = xgb.DMatrix(train[FEATURE_COLS], label=train["target_spend"])
dval = xgb.DMatrix(val[FEATURE_COLS], label=val["target_spend"])
dtest = xgb.DMatrix(test[FEATURE_COLS])

params = {
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": SEED,
    "eval_metric": "mae",
    "objective": "reg:squarederror"
}

model = xgb.train(
    params,
    dtrain,
    num_boost_round=400,
    evals=[(dtrain, "train"), (dval, "val")],
    early_stopping_rounds=30,
    verbose_eval=False
)
print(f"Số cây thực tế dùng (sau early stopping): {model.best_iteration}")

val = val.copy()
test = test.copy()
val["pred_spend"]  = model.predict(dval)
test["pred_spend"] = model.predict(dtest)

# ============================================================
# Xuất file — pattern CHỈ xuất hiện ở đây (để phân tích Bước 6),
# không hề có mặt trong FEATURE_COLS đã dùng để huấn luyện ở trên
# ============================================================
OUT_COLS = [
    "user_id", "date", "target_date", "cycle_id", "day_in_cycle", "D", "remaining_days", "h",
    "pattern",
    "balance", "theta_t", "balance_over_theta",
    "avg7", "avg14", "avg28", "std14", "sum7",
    "target_spend", "pred_spend",
]

import os
os.makedirs("outputs", exist_ok=True)
for split_name, split_df in [("validation", val), ("test", test)]:
    out = split_df[OUT_COLS].copy()
    out.to_csv(f"outputs/forecast_{split_name}.csv", index=False)

# ============================================================
# Sanity check: MAE so với baseline B1 (avg14), tách sơ bộ theo pattern
# (đánh giá đầy đủ thuộc Bước 6)
# ============================================================
def mae(y_true, y_pred):
    return np.mean(np.abs(y_true - y_pred))

for name, split in [("Validation", val), ("Test", test)]:
    mae_model = mae(split["target_spend"], split["pred_spend"])
    mae_b1 = mae(split["target_spend"], split["avg14"])
    print(f"\n[{name}] MAE XGBoost : {mae_model:,.0f} VND | MAE baseline B1: {mae_b1:,.0f} VND "
          f"| Cải thiện: {(1 - mae_model/mae_b1)*100:.1f}%")
    print(f"[{name}] MAE theo pattern:")
    print(split.assign(err=lambda d: (d.target_spend - d.pred_spend).abs())
                .groupby("pattern")["err"].mean().round(0))

print("\nĐã lưu: forecast_validation.csv, forecast_test.csv")

# ============================================================
# Tính toán Rủi ro dòng tiền (Aggregated Cashflow Risk)
# ============================================================
risk_frames = []
for split_name, split_df in [("validation", val), ("test", test)]:
    # Nhóm theo từng ngày t để dự phóng phần còn lại của chu kỳ
    agg = split_df.groupby(["user_id", "date", "cycle_id", "remaining_days"]).agg(
        current_balance=("balance", "first"),
        expected_total_spend=("pred_spend", "sum")
    ).reset_index()
    
    agg["projected_end_balance"] = agg["current_balance"] - agg["expected_total_spend"]
    agg["risk_flag"] = (agg["projected_end_balance"] < 0).astype(int)
    agg["split"] = split_name
    risk_frames.append(agg)

risk_df = pd.concat(risk_frames, ignore_index=True)
risk_df.to_csv("outputs/cashflow_risk_assessment.csv", index=False)

print("Đã lưu bảng tổng hợp rủi ro: outputs/cashflow_risk_assessment.csv")