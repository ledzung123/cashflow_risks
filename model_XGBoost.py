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

# theta_t = trung bình chi tiêu 14 ngày gần nhất tại ngày t
g_user = df.sort_values(["user_id", "date"]).groupby("user_id")["spend"]
df = df.sort_values(["user_id", "date"]).reset_index(drop=True)
df["theta_t"] = g_user.transform(lambda s: s.shift(1).rolling(14, min_periods=5).mean())
g = df.groupby("user_id")["spend"]
df["avg7"]  = g.transform(lambda s: s.shift(1).rolling(7,  min_periods=3).mean())
df["avg14"] = g.transform(lambda s: s.shift(1).rolling(14, min_periods=5).mean())
df["avg28"] = g.transform(lambda s: s.shift(1).rolling(28, min_periods=10).mean())
df["std14"] = g.transform(lambda s: s.shift(1).rolling(14, min_periods=5).std())
df["sum7"]  = g.transform(lambda s: s.shift(1).rolling(7,  min_periods=3).sum())
df["balance_over_theta"] = df["balance"] / df["theta_t"].replace(0, np.nan)

for _col in ["avg7", "avg14", "avg28", "std14", "sum7"]:
    df[f"{_col}_rel"] = df[_col] / df["theta_t"].replace(0, np.nan)


BACKWARD_FEATS = ["avg7_rel", "avg14_rel", "avg28_rel", "std14_rel", "sum7_rel", "balance_over_theta",
                   "theta_t"]

# Số ngày còn lại trong chu kỳ hiện tại (tính cả hôm nay) -> quyết định
# có tạo sample tại dòng này hay không, và horizon tối đa cho phép
df["remaining_days"] = df["D"] - df["day_in_cycle"]
decision_rows = df[df["remaining_days"] >= MIN_REMAINING_DAYS].copy()
print(f"Số điểm quyết định (remaining_days >= {MIN_REMAINING_DAYS}): "
      f"{len(decision_rows):,} / {len(df):,} dòng gốc")

# Sinh mẫu direct multi-horizon: với mỗi h, lấy target bằng cách
# shift(-h) TRONG CÙNG (user_id, cycle_id) -> nếu h vượt quá chu kỳ,
# pandas tự trả NaN -> tự loại các h không hợp lệ
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
    tmp["target_day_in_cycle"] = tmp["day_in_cycle"] + h

    # lấy target_spend bằng shift(-h) trong đúng nhóm (user_id, cycle_id)
    shifted = cycle_group.shift(-h)
    tmp["target_spend"] = shifted.reindex(tmp.index)

    frames.append(tmp)

samples = pd.concat(frames, ignore_index=True)
samples = samples.dropna(
    subset=["target_spend"] + BACKWARD_FEATS + ["target_weekday", "target_is_weekend"]
).reset_index(drop=True)

# Đặc trưng dùng cho mô hình
FEATURE_COLS = (
    ["h", "target_weekday", "target_is_weekend", "target_day_in_cycle",
     "day_in_cycle", "remaining_days"]
    + BACKWARD_FEATS
)
assert "pattern" not in FEATURE_COLS, "LỖI: pattern là nhãn thật, không được dùng làm đặc trưng!"
assert "pattern" not in samples[FEATURE_COLS].columns

TRAIN_END = pd.Timestamp("2026-01-01")
CALIB_END = pd.Timestamp("2026-03-01")
VAL_END   = pd.Timestamp("2026-05-01")

BLOCKS = [
    ("train",       None,      TRAIN_END),
    ("calibration", TRAIN_END, CALIB_END),
    ("validation",  CALIB_END, VAL_END),
    ("test",        VAL_END,   None),
]
 
def take_block(df_, start, end):
    # Lấy mẫu có ngày quyết định t trong [start, end) VÀ ngày đích t+h < end
    m = pd.Series(True, index=df_.index)
    if start is not None:
        m &= df_["date"] >= start
    if end is not None:
        m &= (df_["date"] < end) & (df_["target_date"] < end)
    return df_[m]
 
train = take_block(samples, *BLOCKS[0][1:])
calib = take_block(samples, *BLOCKS[1][1:])
val   = take_block(samples, *BLOCKS[2][1:])
test  = take_block(samples, *BLOCKS[3][1:])
 
n_purged = len(samples) - sum(len(b) for b in (train, calib, val, test))
print(f"Đã purge {n_purged:,} mẫu có target_date vượt ranh giới khối.")
print(f"Train: {len(train):,} | Calibration: {len(calib):,} | "
      f"Validation: {len(val):,} | Test: {len(test):,} mẫu")
 
# Huấn luyện XGBoost
params = {
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": SEED,
    "eval_metric": "mae",
    "objective": "reg:squarederror"
}
 
INNER_START = TRAIN_END - pd.Timedelta(days=30)
fit_part = take_block(train, None, INNER_START)
es_part  = train[(train["date"] >= INNER_START)]
 
d_fit = xgb.DMatrix(fit_part[FEATURE_COLS], label=fit_part["target_spend"])
d_es  = xgb.DMatrix(es_part[FEATURE_COLS],  label=es_part["target_spend"])
probe = xgb.train(params, d_fit, num_boost_round=400,
                  evals=[(d_es, "inner_val")],
                  early_stopping_rounds=30, verbose_eval=False)
N_TREES = probe.best_iteration + 1
print(f"Số cây chọn bằng early stopping nội bộ trong Train: {N_TREES}")
 
dtrain = xgb.DMatrix(train[FEATURE_COLS], label=train["target_spend"])
model = xgb.train(params, dtrain, num_boost_round=N_TREES, verbose_eval=False)
 
# Dự báo + sai số 
out_blocks = {"calibration": calib.copy(), "validation": val.copy(), "test": test.copy()}
for name, blk in out_blocks.items():
    blk["pred_spend"] = model.predict(xgb.DMatrix(blk[FEATURE_COLS]))
    blk["error"] = blk["target_spend"] - blk["pred_spend"]
    blk["abs_error"] = blk["error"].abs()
    blk["split"] = name
 
# pattern CHỈ xuất hiện ở file xuất (phục vụ phân tích Bước 6),
# không có trong FEATURE_COLS đã dùng để huấn luyện.
OUT_COLS = [
    "split", "user_id", "date", "target_date", "h",
    "cycle_id", "day_in_cycle", "D", "remaining_days", "pattern",
    "balance", "theta_t", "balance_over_theta",
    "avg7", "avg14", "avg28", "std14", "sum7",
    "avg7_rel", "avg14_rel", "avg28_rel", "std14_rel", "sum7_rel",
    "target_spend", "pred_spend", "error", "abs_error",
]
 
import os
os.makedirs("outputs", exist_ok=True)
for name, blk in out_blocks.items():
    blk[OUT_COLS].to_csv(f"outputs/forecast_{name}.csv", index=False) 
 
# Sanity check: MAE so với baseline B1 (avg14) và theo h / pattern
def mae(y_true, y_pred):
    return np.mean(np.abs(y_true - y_pred))
 
for name, blk in out_blocks.items():
    mae_model = mae(blk["target_spend"], blk["pred_spend"])
    mae_b1 = mae(blk["target_spend"], blk["avg14"])
    print(f"\n[{name}] MAE XGBoost : {mae_model:,.0f} VND | MAE baseline B1: {mae_b1:,.0f} VND "
          f"| Cải thiện: {(1 - mae_model/mae_b1)*100:.1f}% | Bias TB e: {blk['error'].mean():,.0f}")
    print(f"[{name}] MAE theo pattern:")
    print(blk.groupby("pattern")["abs_error"].mean().round(0))
 
print("\nĐã lưu: forecast_calibration.csv, forecast_validation.csv, forecast_test.csv")
 
# Tính toán Rủi ro dòng tiền
risk_frames = []
SAFETY_MARGIN = 1.0
for split_name, split_df in out_blocks.items():
    # Nhóm theo từng ngày t 
    agg = split_df.groupby(["user_id", "date", "cycle_id", "remaining_days"]).agg(
        current_balance=("balance", "first"),
        theta_t=("theta_t", "first"),
        expected_total_spend=("pred_spend", "sum")
    ).reset_index()
 
    agg["projected_end_balance"] = agg["current_balance"] - agg["expected_total_spend"]
 
    # Ngưỡng rủi ro so với θ (đệm an toàn = SAFETY_MARGIN ngày chi tiêu trung
    # bình của chính user đó)
    agg["risk_threshold"] = SAFETY_MARGIN * agg["theta_t"].fillna(0)
    agg["risk_flag"] = (agg["projected_end_balance"] < agg["risk_threshold"]).astype(int)
    agg["split"] = split_name
    risk_frames.append(agg)
 
risk_df = pd.concat(risk_frames, ignore_index=True)
risk_df.to_csv("outputs/cashflow_risk_assessment.csv", index=False)
 
print("Đã lưu bảng tổng hợp rủi ro: outputs/cashflow_risk_assessment.csv")