"""
run_xgb.py - Bước 4: huấn luyện XGBoost dự báo chi tiêu ngày, so với B1/B2 trên cùng dữ liệu và cùng tập test.
  python src/run_xgb.py --seed 1
  python src/run_xgb.py --seed 1 --csv data/daily.csv     # CSV phải được sinh bằng đúng seed này
  python src/run_xgb.py --seed 1 --stride 2               # dùng 1/2 số ngày quyết định để huấn luyện (nhanh hơn)
Cảnh báo của XGBoost ở bước này vẫn theo biên m (tune trên val, F1) để tách riêng phần "dự báo tốt hơn";
phần xác suất p > p* là bước 5.
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from labels import make_dp
from baselines import predict_spend_b1, predict_spend_b2, alert_by_margin, tune_margin
from evaluate import evaluate, evaluate_by, forecast_metrics
from model_xgb import XGBForecaster
from run_baselines import load

SHOW = ["precision", "recall", "f1", "cycle_false_alarm", "MAE_spend", "RMSE_spend", "MAE_balance", "RMSE_balance"]


def run(seed, csv=None, stride=1):
    df = load(seed, csv)
    dp = make_dp(df)
    sp = dp.split.to_numpy()
    tr = dp[sp == "train"].iloc[::stride].reset_index(drop=True)
    val = dp[sp == "val"].reset_index(drop=True)
    test = dp[sp == "test"].reset_index(drop=True)

    t0 = time.time()
    fc = XGBForecaster(seed=seed).fit(df, tr, val)
    fit_s = time.time() - t0
    preds = {"XGB": (fc.predict_spend(df, val), fc.predict_spend(df, test)),
             "B1": (predict_spend_b1(df, val), predict_spend_b1(df, test)),
             "B2": (predict_spend_b2(df, val), predict_spend_b2(df, test))}
    rows, by = [], {}
    for name, (yv, yt) in preds.items():
        m, f1v = tune_margin(val, yv, evaluate)
        a = alert_by_margin(test, yt, m)
        rows.append({"model": name, "m": m, "f1_val": f1v, **evaluate(test, a), **forecast_metrics(df, test, yt)})
        by[name] = evaluate_by(test, a, df, yt)
    res = pd.DataFrame(rows).set_index("model")
    res["n_trees"] = [fc.best_iteration, np.nan, np.nan]
    return res, by, fc, dict(n_train=len(tr), n_val=len(val), n_test=len(test), fit_s=fit_s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--stride", type=int, default=1)
    a = ap.parse_args()
    res, by, fc, info = run(a.seed, a.csv, a.stride)
    pd.set_option("display.width", 220)
    print(f"điểm quyết định train/val/test = {info['n_train']:,}/{info['n_val']:,}/{info['n_test']:,} | "
          f"số cây (early stopping) = {fc.best_iteration} | thời gian huấn luyện = {info['fit_s']:.0f}s")
    print("\n=== TEST (m của từng mô hình tune trên val) ===")
    print(res[SHOW].round(3).to_string())
    for k in ("MAE_spend", "MAE_balance", "RMSE_balance"):
        print(f"  XGB so với B2, {k}: {100 * (res.loc['XGB', k] / res.loc['B2', k] - 1):+.1f}%")
    print("\n=== Theo 4 kiểu chi tiêu: XGB so với B2 (F1 | MAE_balance) ===")
    t = pd.DataFrame({"F1_XGB": by["XGB"].f1, "F1_B2": by["B2"].f1, "F1_B1": by["B1"].f1,
                      "MAEbal_XGB": by["XGB"].MAE_balance, "MAEbal_B2": by["B2"].MAE_balance,
                      "MAEbal_B1": by["B1"].MAE_balance})
    print(t.round(3).to_string())
    imp = fc.importance()
    print("\n=== Độ quan trọng đặc trưng (gain), top 8 ===")
    for k, v in list(imp.items())[:8]:
        print(f"  {k:18s} {v:6.1%}")
    os.makedirs("results", exist_ok=True)
    res.loc[["XGB"]].to_csv(f"results/xgb_seed{a.seed}.csv")
    res.loc[["B1", "B2"]].to_csv(f"results/baselines_samedata_seed{a.seed}.csv")
    t.to_csv(f"results/xgb_by_pattern_seed{a.seed}.csv")
    pd.Series(imp, name="gain_share").to_csv(f"results/xgb_importance_seed{a.seed}.csv")
    print(f"\nĐã lưu results/xgb_seed{a.seed}.csv (+ importance, by_pattern, baselines_samedata)")
