"""
sensitivity.py - Phân tích độ nhạy theo tham số simulator (thay cho dữ liệu thật). Người 1.
Mỗi kịch bản đổi MỘT tham số (nhân 0,5 hoặc 1,5; riêng rho dịch ∓0,05), chạy lại cả pipeline (huấn luyện, B1/B2, xác suất p)
rồi kiểm tra 5 kết luận chính còn đứng vững không.
  python src/sensitivity.py --seed 1 --only base,weekend_lo,weekend_hi                 # chạy một nhóm kịch bản (mặc định 300 người như phần lõi)
  python src/sensitivity.py --seed 1 --report                                          # bảng tổng hợp + hình fig8
Kết quả từng kịch bản được GHI NỐI vào results/sensitivity_seed{S}.csv (chạy lại kịch bản nào thì thay hàng của kịch bản đó).
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import simulate
from labels import make_dp, prepare_df
from baselines import predict_spend_b1, predict_spend_b2, alert_by_margin, tune_margin
from evaluate import evaluate, forecast_metrics
from model_xgb import XGBForecaster
from risk import fit_predict, tune_pstar, coverage_eval
from prob_metrics import prob_metrics

RHO_LO, RHO_HI = 0.85, 1.05
SCENARIOS = {"base": ({}, 0.0)}
for k in ("weekend", "front", "noise", "spike", "shock"):
    SCENARIOS[f"{k}_lo"] = ({k: 0.5}, 0.0)
    SCENARIOS[f"{k}_hi"] = ({k: 1.5}, 0.0)
SCENARIOS["rho_lo"] = ({}, -0.05)
SCENARIOS["rho_hi"] = ({}, +0.05)


def run_one(name, seed, users):
    params, shift = SCENARIOS[name]
    raw, _ = simulate.simulate(users, seed, RHO_LO + shift, RHO_HI + shift, 0.10, params)
    df = prepare_df(raw)
    dp = make_dp(df)
    sp = dp.split.to_numpy()
    tr, calib, val, test = (dp[sp == s].reset_index(drop=True) for s in ("train", "calib", "val", "test"))
    fc = XGBForecaster(seed=seed).fit(df, tr, val)
    P = {"XGB": [fc.predict_spend(df, d) for d in (calib, val, test)],
         "B1": [predict_spend_b1(df, d) for d in (calib, val, test)],
         "B2": [predict_spend_b2(df, d) for d in (calib, val, test)]}
    row = {"scenario": name, "users": users, "seed": seed, "pos_rate_test": float(test.y.mean())}
    for m, (yc, yv, yt) in P.items():
        mg, _ = tune_margin(val, yv, evaluate)
        r = evaluate(test, alert_by_margin(test, yt, mg))
        row[f"f1_{m}"], row[f"fa_{m}"] = r["f1"], r["cycle_false_alarm"]
        row[f"mae_spend_{m}"] = forecast_metrics(df, test, yt)["MAE_spend"]
        row[f"mae_bal_{m}"] = forecast_metrics(df, test, yt)["MAE_balance"]
    yc, yv, yt = P["XGB"]
    p_val, p_test = fit_predict("cumb", calib, yc, [(val, yv), (test, yt)], df)
    ps, _ = tune_pstar(val, p_val, evaluate)
    r = evaluate(test, p_test > ps)
    pm = prob_metrics(p_test, test.y, calib.y.mean())
    cov = coverage_eval("cumb", calib, yc, test, yt, df)
    row.update({"f1_XGBrisk": r["f1"], "fa_XGBrisk": r["cycle_false_alarm"], "p_star": ps, "ece": pm["ece"],
                "brier": pm["brier"], "auroc": pm["auroc"], "cov80": float(cov[:, 1].mean())})
    # năm kết luận chính
    row["K1_XGB_MAE_thap_hon_B2"] = int(row["mae_spend_XGB"] < row["mae_spend_B2"])
    row["K2_XGBrisk_F1_cao_hon_B1_va_B2"] = int(row["f1_XGBrisk"] > max(row["f1_B1"], row["f1_B2"]))
    row["K3_ECE_duoi_0.03"] = int(row["ece"] < 0.03)
    row["K4_lop_xac_suat_khong_hon_nhieu"] = int(abs(row["f1_XGBrisk"] - row["f1_XGB"]) < 0.01)
    row["K5_cov80_trong_0.75_0.85"] = int(0.75 <= row["cov80"] <= 0.85)
    return row


def save_rows(rows, path):
    new = pd.DataFrame(rows)
    if os.path.exists(path):
        old = pd.read_csv(path)
        old = old[~old.scenario.isin(new.scenario)]
        new = pd.concat([old, new], ignore_index=True)
    new.to_csv(path, index=False)


def report(seed):
    path = f"results/sensitivity_seed{seed}.csv"
    d = pd.read_csv(path)
    order = [k for k in SCENARIOS if k in set(d.scenario)]
    d = d.set_index("scenario").loc[order]
    d["MAE XGB so với B2 (%)"] = 100 * (d.mae_spend_XGB / d.mae_spend_B2 - 1)
    d["F1 XGB+risk − B2"] = d.f1_XGBrisk - d.f1_B2
    d["F1 XGB+risk − B1"] = d.f1_XGBrisk - d.f1_B1
    show = d[["pos_rate_test", "MAE XGB so với B2 (%)", "F1 XGB+risk − B2", "F1 XGB+risk − B1", "ece", "cov80", "auroc"]]
    pd.set_option("display.width", 200)
    print(show.round(3).to_string())
    K = [c for c in d.columns if c.startswith("K")]
    print("\nKết luận còn đứng vững (1 = đúng):")
    print(d[K].to_string())
    print("\nSố kịch bản mà mỗi kết luận đúng:", d[K].sum().astype(int).to_dict(), "/", len(d))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    y = np.arange(len(d))
    ax[0].barh(y, d["MAE XGB so với B2 (%)"], color="#F58518"); ax[0].axvline(0, color="k", lw=0.8)
    ax[0].set_title("MAE chi tiêu của XGB so với B2 (%, âm = tốt hơn)")
    ax[1].barh(y, d["F1 XGB+risk − B2"], color="#E45756"); ax[1].axvline(0, color="k", lw=0.8)
    ax[1].set_title("F1 của XGB + p > p* trừ F1 của B2")
    ax[2].barh(y, d["ece"], color="#4C78A8"); ax[2].axvline(0.03, color="red", ls="--", lw=1)
    ax[2].set_title("ECE của p (đường đỏ = 0,03)")
    for a in ax:
        a.set_yticks(y); a.set_yticklabels(d.index, fontsize=8); a.invert_yaxis()
    fig.suptitle(f"Phân tích độ nhạy theo tham số simulator (seed {seed}, {int(d.users.iloc[0])} người)")
    fig.tight_layout()
    os.makedirs("results/final", exist_ok=True)
    fig.savefig("results/final/fig8_sensitivity.png", dpi=130)
    show.round(4).to_csv("results/final/sensitivity_table.csv", encoding="utf-8-sig")
    d[K].to_csv("results/final/sensitivity_conclusions.csv", encoding="utf-8-sig")
    print("\nĐã lưu results/final/fig8_sensitivity.png, sensitivity_table.csv, sensitivity_conclusions.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--users", type=int, default=300)
    ap.add_argument("--only", default="")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report(a.seed)
    else:
        names = [n for n in a.only.split(",") if n] or list(SCENARIOS)
        rows = []
        for n in names:
            t0 = time.time()
            rows.append(run_one(n, a.seed, a.users))
            print(f"{n:11s} xong sau {time.time() - t0:.0f}s | tỉ lệ dương test {rows[-1]['pos_rate_test']:.3f} | "
                  f"F1 B2 {rows[-1]['f1_B2']:.3f} XGB+risk {rows[-1]['f1_XGBrisk']:.3f} | ECE {rows[-1]['ece']:.3f}", flush=True)
        os.makedirs("results", exist_ok=True)
        save_rows(rows, f"results/sensitivity_seed{a.seed}.csv")
