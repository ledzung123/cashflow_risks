"""
run_baselines.py - Chạy B1/B2 end-to-end: nhãn -> dự báo -> tune m trên val -> đánh giá trên test.
  python src/run_baselines.py --seed 42            # seed dev (số liệu chỉ để kiểm tra pipeline)
  python src/run_baselines.py --seed 1 --csv data/daily.csv
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import simulate
from labels import prepare_df, make_dp
from baselines import predict_spend_b1, predict_spend_b2, alert_by_margin, tune_margin
from evaluate import evaluate, evaluate_by, forecast_metrics


def load(seed, csv):
    if csv and os.path.exists(csv):
        df = pd.read_csv(csv)
    else:
        df, _ = simulate.simulate(300, seed, 0.85, 1.05, 0.10)
    return prepare_df(df)


def run(seed, csv=None):
    df = load(seed, csv)
    dp = make_dp(df)
    out = {}
    for name, fn in [("B1", predict_spend_b1), ("B2", predict_spend_b2)]:
        yhat = fn(df, dp)
        val, test = (dp.split == "val").to_numpy(), (dp.split == "test").to_numpy()
        dp_val, dp_test = dp[val].reset_index(drop=True), dp[test].reset_index(drop=True)
        m, f1_val = tune_margin(dp_val, yhat[val], evaluate)
        a_test = alert_by_margin(dp_test, yhat[test], m)
        res = {"m": m, "f1_val": f1_val, **evaluate(dp_test, a_test),
               **forecast_metrics(df, dp_test, yhat[test])}
        out[name] = (res, evaluate_by(dp_test, a_test, df, yhat[test]))
    return dp, out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--save", default="results/baselines_seed{seed}.csv")
    a = ap.parse_args()
    dp, out = run(a.seed, a.csv)
    print(f"dp: {len(dp):,} điểm quyết định | dương: {dp.y.mean():.1%} | "
          f"train/val/test = {(dp.split=='train').sum():,}/{(dp.split=='val').sum():,}/{(dp.split=='test').sum():,}")
    pd.set_option("display.width", 200)
    rows = []
    for name, (res, by) in out.items():
        print(f"\n=== {name} (m tune trên val = {res['m']:+.2f} x theta, F1 val = {res['f1_val']:.3f}) -> TEST ===")
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in res.items() if k not in ('m', 'f1_val')})
        print(by[["precision", "recall", "f1", "mean_days_early", "cycle_false_alarm", "MAE_spend", "MAE_balance"]].round(3).to_string())
        rows.append({"model": name, **res})
    path = a.save.format(seed=a.seed)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"\nĐã lưu {path}")
