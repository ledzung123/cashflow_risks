"""
aggregate_results.py - Gộp kết quả nhiều seed thành bảng trung bình ± độ lệch chuẩn.
  python src/aggregate_results.py --prefix baselines --seeds 1 2 3
Đầu vào: results/<prefix>_seed<S>.csv (mỗi file: 1 dòng/mô hình).  Đầu ra: results/<prefix>_mean_seeds<...>.csv
"""
import argparse

import pandas as pd

COLS = ["m", "p_star", "precision", "recall", "f1", "cycle_recall", "cycle_false_alarm", "mean_days_early",
        "MAE_spend", "RMSE_spend", "MAE_balance", "RMSE_balance", "brier_test", "ece_test"]

ap = argparse.ArgumentParser()
ap.add_argument("--prefix", default="baselines")
ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
a = ap.parse_args()

d = pd.concat([pd.read_csv(f"results/{a.prefix}_seed{s}.csv").assign(seed=s) for s in a.seeds])
cols = [c for c in COLS if c in d.columns]
g = d.groupby("model")[cols]
mean, std = g.mean(), g.std()
print("TRUNG BÌNH:\n", mean.round(3).to_string(), "\n\nĐỘ LỆCH CHUẨN:\n", std.round(3).to_string())
out = f"results/{a.prefix}_mean_seeds{''.join(map(str, a.seeds))}.csv"
mean.round(4).to_csv(out)
print("\nĐã lưu", out)
