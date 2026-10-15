"""
Bước 3 — Nhãn, Baseline (B1, B2) và Hàm đánh giá chỉ số (Q1, Q2).
Thống nhất giao diện theo SPEC.md (v1.2) và tương thích trực tiếp với sample_v0.csv / model_XGBoost.py.

Cách chạy:
  python src/run_baselines.py --seed 1
  python src/run_baselines.py --seed 2
  python src/run_baselines.py --seed 3
  python src/run_baselines.py --all-seeds
"""
import argparse
import os
import numpy as np
import pandas as pd


PATTERN_TO_VN = {
    "even": "đều",
    "front": "dồn đầu chu kỳ",
    "weekend": "tăng cuối tuần",
    "spike": "bất thường",
}


def load_and_prepare_data(
    csv_path: str = "data/sample_v0.csv",
    apply_spec_carryover: bool = True,
    shift_rolling: bool = True,
) -> pd.DataFrame:
    """
    Đọc dữ liệu từ sample_v0.csv hoặc daily.csv, chuẩn hóa đầy đủ các cột theo SPEC.md
    và model_XGBoost.py.
    """
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values(["user_id", "date"]).reset_index(drop=True)

    # Chuẩn hóa tên pattern sang tiếng Việt để đồng bộ với sample_v0.csv và model_XGBoost.py
    df["pattern_vn"] = df["pattern"].replace(PATTERN_TO_VN)

    # Xác định cycle_id nếu chưa có trong file
    if "cycle_id" not in df.columns:
        new_cycle_mask = df.groupby("user_id")["day_in_cycle"].diff() < 0
        df["cycle_id"] = new_cycle_mask.astype(int).groupby(df["user_id"]).cumsum()

    # Độ dài chu kỳ (cycle_len) và số ngày còn lại trong chu kỳ (D_rem)
    # Trong SPEC.md: D = độ dài chu kỳ - day_in_cycle (số ngày còn lại sau ngày t).
    # Trong model_XGBoost.py: df["D"] là độ dài chu kỳ, df["remaining_days"] = D - day_in_cycle.
    if "days_to_next_income" in df.columns:
        df["cycle_len"] = df["day_in_cycle"] + df["days_to_next_income"] - 1
        df["remaining_days"] = df["days_to_next_income"] - 1
    elif "D" in df.columns:
        df["remaining_days"] = df["D"]
        df["cycle_len"] = df["day_in_cycle"] + df["remaining_days"]
    else:
        raise ValueError("Dữ liệu thiếu cột days_to_next_income hoặc D.")

    df["D"] = df["remaining_days"]
    df["weekday"] = df["date"].dt.weekday

    # Chuyển số dư đầu chu kỳ (SPEC.md Mục 9):
    # Mang sang chu kỳ sau: min(max(balance_cuối, 0), 10% thu nhập)
    if apply_spec_carryover:
        for u, g in df.groupby("user_id"):
            bal = 0.0
            bals = []
            for _, row in g.iterrows():
                if row["day_in_cycle"] == 1 and row["cycle_id"] > 0:
                    carry = min(max(bal, 0.0), 0.10 * row["income"])
                    bal = carry + row["income"] - row["spend"]
                else:
                    bal = bal + row["income"] - row["spend"]
                bals.append(bal)
            df.loc[g.index, "balance"] = np.round(bals).astype(int)

    # Tính ngưỡng cá nhân theta:
    # - theta_t: TB chi tiêu 14 ngày gần nhất tại ngày t
    g_spend = df.groupby("user_id")["spend"]
    if shift_rolling:
        df["theta_t"] = g_spend.transform(lambda s: s.shift(1).rolling(14, min_periods=5).mean())
    else:
        df["theta_t"] = g_spend.transform(lambda s: s.rolling(14, min_periods=5).mean())

    theta_c_map = {}
    for u, g in df.groupby("user_id"):
        g_sorted = g.sort_values("date")
        spends = g_sorted["spend"].values
        cids = g_sorted["cycle_id"].values
        for cid in np.unique(cids):
            pos = np.where(cids == cid)[0][0]
            if pos < 5:
                theta_c_map[(u, cid)] = np.nan
            else:
                theta_c_map[(u, cid)] = float(spends[max(0, pos - 14) : pos].mean())
    df["theta_c"] = [theta_c_map[(u, c)] for u, c in zip(df["user_id"], df["cycle_id"])]

    # Gán nhãn chia tập (split) (SPEC.md Mục 4)
    if "split" not in df.columns:
        conds = [
            df["cycle_id"].between(0, 11),
            df["cycle_id"].between(12, 14),
            df["cycle_id"].between(15, 17),
        ]
        df["split"] = np.select(conds, ["train", "val", "test"], default="ignore")

    return df


def build_decision_points(
    df: pd.DataFrame,
    split_mode: str = "spec",
    theta_mode: str = "theta_c",
    min_remaining_days: int = 3,
    drop_already_below_theta: bool = True,
) -> pd.DataFrame:
    """
    Tạo bảng điểm quyết định dp theo SPEC.md Mục 5:
    (user_id, cycle_id, t, balance_t, D, theta_c, y, dip_day) kèm pattern, split, end_balance_true.
    """
    data = df.sort_values(["user_id", "date"]).reset_index(drop=True).copy()

    if split_mode == "xgb":
        conds = [
            data["date"] < pd.Timestamp("2025-09-01"),
            (data["date"] >= pd.Timestamp("2025-09-01")) & (data["date"] < pd.Timestamp("2025-11-01")),
            data["date"] >= pd.Timestamp("2025-11-01"),
        ]
        data["split"] = np.select(conds, ["train", "val", "test"], default="ignore")

    theta_col = "theta_c" if theta_mode == "theta_c" else "theta_t"
    data["theta"] = data[theta_col]

    # Số dư cuối chu kỳ thực tế
    data["end_balance_true"] = data.groupby(["user_id", "cycle_id"])["balance"].transform("last")

    # Nhãn y_t = 1 nếu số dư cuối chu kỳ < theta
    data["y"] = (data["end_balance_true"] < data["theta"]).astype(int)

    # Tìm dip_day = ngày đầu tiên trong chu kỳ có balance < theta
    dip_map = {}
    for (u, cid), cg in data.groupby(["user_id", "cycle_id"]):
        below = cg[cg["balance"] < cg["theta"]]
        dip_map[(u, cid)] = int(below["day_in_cycle"].iloc[0]) if len(below) > 0 else np.nan
    data["dip_day"] = [dip_map[(u, c)] for u, c in zip(data["user_id"], data["cycle_id"])]

    # Lọc điểm quyết định: D >= 3, bỏ chu kỳ 0, bỏ điểm đã thiếu tiền (balance_t < theta)
    mask = (
        (data["remaining_days"] >= min_remaining_days)
        & (data["cycle_id"] >= 1)
        & (data["theta"].notna())
        & (data["split"].isin(["train", "val", "test"]))
    )
    if drop_already_below_theta:
        mask = mask & (data["balance"] >= data["theta"])

    dp = data.loc[mask].copy().reset_index(drop=True)
    dp["t"] = dp["date"]
    dp["balance_t"] = dp["balance"]
    dp["D"] = dp["remaining_days"]
    return dp


def predict_spend(
    df: pd.DataFrame,
    dp: pd.DataFrame,
    method: str = "B1",
    b2_window: int = 28,
    shift_rolling: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Giao diện chung theo SPEC.md Mục 5:
    predict_spend(df, dp) -> mảng yhat (n_dp, 31) dự báo chi tiêu ngày t+1..t+D, NaN phía sau.
    Trả về thêm ytrue (n_dp, 31) là chi tiêu thực tế ngày t+1..t+D để tính MAE/RMSE.
    """
    n_dp = len(dp)
    max_h = 31
    yhat = np.full((n_dp, max_h), np.nan, dtype=float)
    ytrue = np.full((n_dp, max_h), np.nan, dtype=float)

    user_dfs = {u: g.sort_values("date").reset_index(drop=True) for u, g in df.groupby("user_id")}

    for i, row in dp.iterrows():
        u = row["user_id"]
        ug = user_dfs[u]
        t_idx = int(np.searchsorted(ug["date"].values, row["date"].to_numpy()))
        D = int(row["D"])

        # Cửa sổ lịch sử không vượt quá ngày t (nếu shift_rolling=True thì dùng đến t-1 giống model_XGBoost.py;
        # nếu shift_rolling=False thì dùng đến hết cuối ngày t theo SPEC.md Mục 1)
        end_pos = t_idx if shift_rolling else (t_idx + 1)
        hist_14 = ug["spend"].values[max(0, end_pos - 14) : end_pos]
        b1_val = float(np.mean(hist_14)) if len(hist_14) > 0 else 0.0

        if method.upper() == "B1":
            for h in range(1, D + 1):
                if t_idx + h < len(ug):
                    yhat[i, h - 1] = b1_val
                    ytrue[i, h - 1] = float(ug["spend"].values[t_idx + h])
        elif method.upper() == "B2":
            hist_start = max(0, end_pos - b2_window) if b2_window is not None else 0
            hist_spends = ug["spend"].values[hist_start:end_pos]
            hist_wdays = ug["weekday"].values[hist_start:end_pos]
            wday_means = {}
            for w in range(7):
                w_mask = hist_wdays == w
                wday_means[w] = float(np.mean(hist_spends[w_mask])) if np.any(w_mask) else b1_val
            for h in range(1, D + 1):
                if t_idx + h < len(ug):
                    target_w = int(ug["weekday"].values[t_idx + h])
                    yhat[i, h - 1] = wday_means[target_w]
                    ytrue[i, h - 1] = float(ug["spend"].values[t_idx + h])
        else:
            raise ValueError(f"Unknown method: {method}")

    return yhat, ytrue


def tune_margin_m(dp_val: pd.DataFrame, yhat_val: np.ndarray) -> tuple[float, float]:
    """
    Chọn biên m trên tập Validation theo SPEC.md Mục 6:
    Cảnh báo khi số dư dự kiến cuối chu kỳ < theta * (1 + m), m thuộc [-3..10] bước 0.25, tối đa hóa F1.
    """
    pred_total_spend = np.nansum(yhat_val, axis=1)
    pred_end_bal = dp_val["balance_t"].values - pred_total_spend
    theta = dp_val["theta"].values
    y_true = dp_val["y"].values

    m_grid = np.arange(-3.0, 10.0 + 1e-9, 0.25)
    best_m = 0.0
    best_f1 = -1.0

    for m in m_grid:
        alert = (pred_end_bal < theta * (1.0 + m)).astype(int)
        tp = np.sum((alert == 1) & (y_true == 1))
        fp = np.sum((alert == 1) & (y_true == 0))
        fn = np.sum((alert == 0) & (y_true == 1))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        if f1 > best_f1:
            best_f1 = float(f1)
            best_m = float(m)

    return best_m, best_f1


def evaluate(
    dp_sub: pd.DataFrame,
    yhat_sub: np.ndarray,
    ytrue_sub: np.ndarray,
    margin_m: float,
) -> dict:
    """
    Tính bộ chỉ số Q1 (MAE/RMSE chi tiêu ngày, MAE/RMSE số dư cuối kỳ)
    và Q2 (Precision, Recall, F1, số ngày báo sớm, cycle_recall, cycle_false_alarm).
    """
    valid_mask = ~np.isnan(ytrue_sub) & ~np.isnan(yhat_sub)
    diff_spend = yhat_sub[valid_mask] - ytrue_sub[valid_mask]
    mae_spend = float(np.mean(np.abs(diff_spend))) if np.any(valid_mask) else np.nan
    rmse_spend = float(np.sqrt(np.mean(diff_spend ** 2))) if np.any(valid_mask) else np.nan

    pred_total_spend = np.nansum(yhat_sub, axis=1)
    pred_end_bal = dp_sub["balance_t"].values - pred_total_spend
    true_end_bal = dp_sub["end_balance_true"].values
    diff_bal = pred_end_bal - true_end_bal
    mae_bal = float(np.mean(np.abs(diff_bal))) if len(diff_bal) > 0 else np.nan
    rmse_bal = float(np.sqrt(np.mean(diff_bal ** 2))) if len(diff_bal) > 0 else np.nan

    theta = dp_sub["theta"].values
    y_true = dp_sub["y"].values
    alert = (pred_end_bal < theta * (1.0 + margin_m)).astype(int)

    tp = int(np.sum((alert == 1) & (y_true == 1)))
    fp = int(np.sum((alert == 1) & (y_true == 0)))
    fn = int(np.sum((alert == 0) & (y_true == 1)))
    prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    dp_tmp = dp_sub.copy()
    dp_tmp["alert"] = alert
    days_early_list = []
    pos_cycles = 0
    caught_cycles = 0
    neg_cycles = 0
    fa_cycles = 0

    for (_, _), cg in dp_tmp.groupby(["user_id", "cycle_id"]):
        is_pos = cg["y"].iloc[0] == 1
        alerted = cg[cg["alert"] == 1]
        if is_pos:
            pos_cycles += 1
            if len(alerted) > 0 and pd.notna(cg["dip_day"].iloc[0]):
                caught_cycles += 1
                first_alert_day = int(alerted["day_in_cycle"].min())
                dip_d = int(cg["dip_day"].iloc[0])
                days_early_list.append(dip_d - first_alert_day)
        else:
            neg_cycles += 1
            if len(alerted) > 0:
                fa_cycles += 1

    mean_days_early = float(np.mean(days_early_list)) if len(days_early_list) > 0 else 0.0
    cycle_recall = float(caught_cycles / pos_cycles) if pos_cycles > 0 else 0.0
    cycle_fa = float(fa_cycles / neg_cycles) if neg_cycles > 0 else 0.0

    return {
        "Precision": round(prec, 4),
        "Recall": round(rec, 4),
        "F1": round(f1, 4),
        "MAE_spend": round(mae_spend, 2),
        "RMSE_spend": round(rmse_spend, 2),
        "MAE_balance": round(mae_bal, 2),
        "RMSE_balance": round(rmse_bal, 2),
        "mean_days_early": round(mean_days_early, 2),
        "cycle_recall": round(cycle_recall, 4),
        "cycle_false_alarm": round(cycle_fa, 4),
        "best_m": round(margin_m, 2),
    }


def run_for_seed(
    seed: int,
    data_path: str = "data/sample_v0.csv",
    split_mode: str = "spec",
    theta_mode: str = "theta_c",
    shift_rolling: bool = False,
    apply_spec_carryover: bool = True,
    out_dir: str = "results",
) -> pd.DataFrame:
    # Nếu có file riêng cho từng seed (vd data/daily_seed1.csv) thì ưu tiên đọc
    seed_specific_path = f"data/daily_seed{seed}.csv"
    actual_path = seed_specific_path if os.path.exists(seed_specific_path) else data_path

    df = load_and_prepare_data(
        actual_path,
        apply_spec_carryover=apply_spec_carryover,
        shift_rolling=shift_rolling,
    )
    dp = build_decision_points(
        df,
        split_mode=split_mode,
        theta_mode=theta_mode,
        min_remaining_days=3,
        drop_already_below_theta=True,
    )

    yhat_b1, ytrue = predict_spend(df, dp, method="B1", shift_rolling=shift_rolling)
    yhat_b2, _ = predict_spend(df, dp, method="B2", b2_window=28, shift_rolling=shift_rolling)

    val_mask = (dp["split"] == "val").values
    test_mask = (dp["split"] == "test").values

    m_b1, val_f1_b1 = tune_margin_m(dp.loc[val_mask], yhat_b1[val_mask])
    m_b2, val_f1_b2 = tune_margin_m(dp.loc[val_mask], yhat_b2[val_mask])

    res_b1 = evaluate(dp.loc[test_mask], yhat_b1[test_mask], ytrue[test_mask], m_b1)
    res_b2 = evaluate(dp.loc[test_mask], yhat_b2[test_mask], ytrue[test_mask], m_b2)

    overall_df = pd.DataFrame([
        {"model": "B1", **res_b1},
        {"model": "B2", **res_b2},
    ])

    # Bảng theo 4 kiểu chi tiêu
    pattern_rows = []
    for pat in sorted(dp["pattern_vn"].unique()):
        pat_mask = test_mask & (dp["pattern_vn"] == pat).values
        if np.any(pat_mask):
            r1 = evaluate(dp.loc[pat_mask], yhat_b1[pat_mask], ytrue[pat_mask], m_b1)
            r2 = evaluate(dp.loc[pat_mask], yhat_b2[pat_mask], ytrue[pat_mask], m_b2)
            pattern_rows.append({"pattern": pat, "model": "B1", **r1})
            pattern_rows.append({"pattern": pat, "model": "B2", **r2})
    pattern_df = pd.DataFrame(pattern_rows)

    print(f"\n==================== SEED {seed} (Nguồn: {actual_path}) ====================")
    print(f"[Val Tuning] B1: best_m = {m_b1:+.2f} (Val F1 = {val_f1_b1:.4f}) | "
          f"B2: best_m = {m_b2:+.2f} (Val F1 = {val_f1_b2:.4f})")
    print("\n--- Bảng Tổng hợp trên tập Test (B1, B2) ---")
    print(overall_df.to_string(index=False))
    print("\n--- Bảng Chi tiết theo 4 kiểu chi tiêu trên tập Test ---")
    print(pattern_df.to_string(index=False))

    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"baselines_seed{seed}.csv")
    overall_df.to_csv(out_file, index=False)
    print(f"\n-> Đã lưu: {out_file} ({len(overall_df)} dòng)")
    return overall_df


def aggregate_seeds(seeds=(1, 2, 3), out_dir="results") -> pd.DataFrame:
    dfs = []
    for s in seeds:
        path = os.path.join(out_dir, f"baselines_seed{s}.csv")
        if not os.path.exists(path):
            df_s = run_for_seed(s, out_dir=out_dir)
        else:
            df_s = pd.read_csv(path)
        df_s["seed"] = s
        dfs.append(df_s)

    combined = pd.concat(dfs, ignore_index=True)
    metric_cols = [
        "Precision", "Recall", "F1",
        "MAE_spend", "RMSE_spend", "MAE_balance", "RMSE_balance",
        "mean_days_early", "cycle_recall", "cycle_false_alarm", "best_m"
    ]

    mean_rows = []
    for model_name in ["B1", "B2"]:
        sub = combined[combined["model"] == model_name]
        row = {"model": model_name}
        for col in metric_cols:
            row[col] = round(float(sub[col].mean()), 4 if col in ["Precision", "Recall", "F1", "cycle_recall", "cycle_false_alarm"] else 2)
            row[f"{col}_std"] = round(float(sub[col].std(ddof=0)), 4 if col in ["Precision", "Recall", "F1", "cycle_recall", "cycle_false_alarm"] else 2)
        mean_rows.append(row)

    mean_df = pd.DataFrame(mean_rows)
    out_mean_path = os.path.join(out_dir, "baselines_mean_seeds123.csv")
    mean_df.to_csv(out_mean_path, index=False)
    print("\n==================== TRUNG BÌNH 3 SEED (1, 2, 3) ====================")
    print(mean_df[["model"] + metric_cols].to_string(index=False))
    print(f"\n-> Đã lưu: {out_mean_path} ({len(mean_df)} dòng)")
    return mean_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy Baseline B1, B2 cho Bước 3")
    parser.add_argument("--seed", type=int, default=1, help="Seed (1, 2, 3 hoặc 42)")
    parser.add_argument("--all-seeds", action="store_true", help="Chạy cả 3 seed (1, 2, 3) và xuất bảng trung bình")
    parser.add_argument("--data", type=str, default="data/sample_v0.csv", help="Đường dẫn file dữ liệu")
    parser.add_argument("--mode", type=str, choices=["spec", "xgb"], default="spec", help="Chế độ chia tập & tính theta")
    parser.add_argument("--raw-balance", action="store_true", help="Không áp dụng quy tắc kết chuyển số dư SPEC Mục 9")
    parser.add_argument("--out-dir", type=str, default="results", help="Thư mục lưu kết quả")
    args = parser.parse_args()

    split_mode = "spec" if args.mode == "spec" else "xgb"
    theta_mode = "theta_c" if args.mode == "spec" else "theta_t"
    shift_rolling = (args.mode == "xgb")
    apply_carry = not args.raw_balance

    if args.all_seeds:
        for s in (1, 2, 3):
            run_for_seed(
                seed=s,
                data_path=args.data,
                split_mode=split_mode,
                theta_mode=theta_mode,
                shift_rolling=shift_rolling,
                apply_spec_carryover=apply_carry,
                out_dir=args.out_dir,
            )
        aggregate_seeds(seeds=(1, 2, 3), out_dir=args.out_dir)
    else:
        run_for_seed(
            seed=args.seed,
            data_path=args.data,
            split_mode=split_mode,
            theta_mode=theta_mode,
            shift_rolling=shift_rolling,
            apply_spec_carryover=apply_carry,
            out_dir=args.out_dir,
        )