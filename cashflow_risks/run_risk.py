"""
run_risk.py - Bước 5: xác suất thiếu tiền p và cảnh báo p > p*, so với cảnh báo theo biên m (bước 3-4).
  python src/run_risk.py --seed 1
Hàng kết quả: B1, B2, XGB (cảnh báo theo biên m) | XGB+risk (p > p*) | XGB+risk(k=2) | B2+risk (đối chứng: cùng cách tính p, dự báo của B2).
Phương pháp ước lượng phân phối ("cum", "cumb" thêm nhóm theo số ngày chi lớn, hoặc "mc") được chọn theo Brier trên val; test chỉ đánh giá một lần.
Lưu thêm chỉ số cho p_t (prob_metrics.py): results/pmetrics*_seed*.csv
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from labels import make_dp
from baselines import predict_spend_b1, predict_spend_b2, alert_by_margin, tune_margin, margin_score
from evaluate import evaluate, evaluate_by, forecast_metrics, rank_metrics, lead_at_far, lead_at_precision
from model_xgb import XGBForecaster
from risk import fit_predict, tune_pstar, persist, brier, ece, coverage_eval
from prob_metrics import prob_metrics, prob_metrics_by, d_bucket
from run_baselines import load

SHOW = ["p_star", "precision", "recall", "f1", "cycle_recall", "cycle_false_alarm", "brier_test", "ece_test"]
USER_SPLIT_SEED = 2026


def user_roles(user_ids):
    """Deterministic disjoint user groups for a secondary user-generalization evaluation."""
    ids = np.asarray(sorted(user_ids))
    shuffled = np.random.default_rng(USER_SPLIT_SEED).permutation(ids)
    n_train = int(round(0.50 * len(shuffled)))
    n_calib = int(round(0.15 * len(shuffled)))
    n_val = int(round(0.15 * len(shuffled)))
    return {
        "train": set(shuffled[:n_train].tolist()),
        "calib": set(shuffled[n_train:n_train + n_calib].tolist()),
        "val": set(shuffled[n_train + n_calib:n_train + n_calib + n_val].tolist()),
        "test": set(shuffled[n_train + n_calib + n_val:].tolist()),
    }


def split_points(dp, split_mode="time"):
    """Return train/calib/val/test decision points under temporal or disjoint-user roles."""
    if split_mode == "time":
        return {name: dp[dp.split == name].reset_index(drop=True)
                for name in ("train", "calib", "val", "test")}
    if split_mode != "user_holdout":
        raise ValueError(f"split_mode không hợp lệ: {split_mode}")

    roles = user_roles(dp.user_id.unique())
    out = {}
    for name, users in roles.items():
        part = dp[(dp.user_id.isin(users)) & (dp.split == name)].reset_index(drop=True)
        if part.empty:
            raise ValueError(f"Tập {name} rỗng trong user_holdout")
        out[name] = part
    return out


def risk_row(name, method, dp_val, p_val, dp_test, p_test, k=1):
    alert_fn = (lambda d, a: persist(d, a, k)) if k > 1 else None
    ps, f1v = tune_pstar(dp_val, p_val, evaluate, alert_fn)
    a_test = persist(dp_test, p_test > ps, k)
    yv, yt = dp_val["y"].to_numpy(), dp_test["y"].to_numpy()
    row = {"model": name, "method": method, "p_star": ps, "f1_val": f1v, **evaluate(dp_test, a_test),
           "brier_val": brier(p_val, yv), "ece_val": ece(p_val, yv),
           "brier_test": brier(p_test, yt), "ece_test": ece(p_test, yt)}
    return row, a_test


def run(seed, csv=None, K=500, split_mode="time", evidence_dir=None):
    df = load(seed, csv)
    dp = make_dp(df)
    splits = split_points(dp, split_mode)
    tr, calib, val, test = (splits[s] for s in ("train", "calib", "val", "test"))
    fc = XGBForecaster(seed=seed).fit(df, tr, val)
    P = {"XGB": [fc.predict_spend(df, d) for d in (calib, val, test)],
         "B1": [predict_spend_b1(df, d) for d in (calib, val, test)],
         "B2": [predict_spend_b2(df, d) for d in (calib, val, test)]}
    rows, alerts, margins = [], {}, {}
    for name, (yc, yv, yt) in P.items():                        # cảnh báo theo biên m (như bước 3-4)
        m, f1v = tune_margin(val, yv, evaluate)
        margins[name] = m
        a_m = alert_by_margin(test, yt, m)
        alerts[name] = a_m
        rows.append({"model": name, "method": "margin", "m": m, "f1_val": f1v, **evaluate(test, a_m)})
    methods, store = [], {}
    pat_t = test["pattern"].to_numpy()
    for method in ("cum", "cumb", "mc"):
        t0 = time.time()
        p_val, p_test = fit_predict(method, calib, P["XGB"][0], [(val, P["XGB"][1]), (test, P["XGB"][2])], df, K=K, seed=seed)
        row, a = risk_row(f"XGB+risk[{method}]", method, val, p_val, test, p_test)
        cov = coverage_eval(method, calib, P["XGB"][0], test, P["XGB"][2], df)
        for k, lev in enumerate(("cov50", "cov80", "cov90")):
            row[lev] = float(cov[:, k].mean()) if cov is not None else float("nan")
        row["cov80_spike"] = float(cov[pat_t == "spike", 1].mean()) if cov is not None else float("nan")
        row["secs"] = round(time.time() - t0, 1)
        methods.append(row); store[method] = (p_val, p_test, a)
    best = min(methods, key=lambda r: r["brier_val"])["method"]          # chọn theo Brier trên val
    p_val, p_test, a_best = store[best]
    r_best, alerts["XGB+risk"] = risk_row("XGB+risk", best, val, p_val, test, p_test)
    r_k2, alerts["XGB+risk(k=2)"] = risk_row("XGB+risk(k=2)", best, val, p_val, test, p_test, k=2)
    pv_b, pt_b = fit_predict("cum", calib, P["B2"][0], [(val, P["B2"][1]), (test, P["B2"][2])], df, K=K, seed=seed)
    r_b2, alerts["B2+risk"] = risk_row("B2+risk", "cum", val, pv_b, test, pt_b)
    risk_rows = [r_best, r_k2, r_b2]
    base_rate = float(calib["y"].mean())
    cov_x = coverage_eval(best, calib, P["XGB"][0], test, P["XGB"][2], df)
    cov_b = coverage_eval("cum", calib, P["B2"][0], test, P["B2"][2], df)
    pm = []
    for name, pv_, pt_, cv_ in [("XGB+risk", p_val, p_test, cov_x), ("B2+risk", pv_b, pt_b, cov_b)]:
        for sname, pp, dd in [("val", pv_, val), ("test", pt_, test)]:
            r = {"model": name, "set": sname, **prob_metrics(pp, dd["y"], base_rate)}
            if sname == "test" and cv_ is not None:
                r.update({"cov50": cv_[:, 0].mean(), "cov80": cv_[:, 1].mean(), "cov90": cv_[:, 2].mean()})
            pm.append(r)
    pm_pat = prob_metrics_by(p_test, test["y"], test["pattern"], base_rate, "pattern")
    pm_D = prob_metrics_by(p_test, test["y"], d_bucket(test["D"]), base_rate, "D")
    if cov_x is not None:
        for name, grp, tab in [("pattern", test["pattern"].to_numpy(), pm_pat), ("D", d_bucket(test["D"]), pm_D)]:
            cdf = pd.DataFrame(cov_x, columns=["cov50", "cov80", "cov90"]).groupby(grp).mean()
            tab[["cov50", "cov80", "cov90"]] = cdf.loc[tab.index]
    by = evaluate_by(test.assign(), a_best, None, None)
    pts = test[["user_id", "cycle_id", "t", "D", "balance_t", "theta_c", "end_balance", "y", "dip_day",
                "pattern", "income_type"]].copy()
    pts["p_xgb"], pts["p_b2"] = p_test, pt_b
    for k, v in alerts.items():
        pts["alert_" + k] = np.asarray(v).astype(int)
    rank = [{"model": name, **rank_metrics(test, margin_score(test, P[name][2]))} for name in ("B1", "B2", "XGB")]
    rank += [{"model": "XGB+risk", **rank_metrics(test, p_test)}, {"model": "B2+risk", **rank_metrics(test, pt_b)}]
    scores = {m: margin_score(test, P[m][2]) for m in ("B1", "B2", "XGB")}
    scores.update({"XGB+risk": p_test, "B2+risk": pt_b})
    scores_val = {m: margin_score(val, P[m][1]) for m in ("B1", "B2", "XGB")}
    scores_val.update({"XGB+risk": p_val, "B2+risk": pv_b})
    lead = pd.concat([lead_at_far(test, sc).assign(model=m) for m, sc in scores.items()], ignore_index=True)
    # Tiêu chí báo cáo giữa kỳ: Precision mục tiêu lấy từ B1 trên validation sau khi tune m.
    # Chọn mọi ngưỡng so sánh trên validation, giữ nguyên khi đánh giá test.
    p_b1_val = evaluate(val, alert_by_margin(val, P["B1"][1], margins["B1"]))["precision"]
    targets = [p_b1_val, 0.6, 0.7, 0.8]
    prec = pd.concat([lead_at_precision(val, scores_val[m], test, scores[m], targets).assign(
                          model=m, muc=["B1"] + [f"{t:.1f}" for t in targets[1:]])
                      for m in scores], ignore_index=True)
    q1 = pd.DataFrame([{"model": m, **forecast_metrics(df, test, P[m][2])} for m in ("B1", "B2", "XGB")])
    # Lưu validation và test để tái tính chính sách mà không huấn luyện lại.
    # Các kết quả cũ vẫn là đường đánh đổi mô tả; bảng policies là ngưỡng vận hành.
    from policies import policy_table
    from pathlib import Path
    import json
    out = Path(evidence_dir) if evidence_dir else Path("results/policies") / split_mode / f"seed{seed}"
    out.mkdir(parents=True, exist_ok=True)
    fc.model.save_model(out / "model.ubj")
    thresholds = {m: -margins[m] for m in margins}
    thresholds.update({"XGB+risk": r_best["p_star"], "B2+risk": r_b2["p_star"]})
    policy_table(val, scores_val, test, scores, thresholds, ("XGB+risk", "B2+risk")).to_csv(out / "policies.csv", index=False)
    for name, points, sc in (("val", val, scores_val), ("test", test, scores)):
        saved = points.copy()
        for model, score in sc.items():
            saved["score_" + model] = score
        saved.to_csv(out / f"{name}_scores.csv", index=False)
    np.savez_compressed(out / "forecasts.npz", **{f"{m}_{s}": values[i]
                        for m, values in P.items() for i, s in enumerate(("calib", "val", "test"))})
    q1.to_csv(out / "q1.csv", index=False)
    pd.DataFrame(methods).to_csv(out / "risk_methods.csv", index=False)
    (out / "selection.json").write_text(json.dumps({"seed": seed, "split_mode": split_mode,
        "risk_method": best, "f1_thresholds": thresholds, "cost_ratios": [1, 2, 3, 5, 10, 20],
        "far_target": 0.2, "threshold_source": "validation; Bayes fixed from cost ratio",
        "cycle_population": "eligible cycles with at least one decision point"}, indent=2), encoding="utf-8")
    return (pd.DataFrame(rows), pd.DataFrame(methods), pd.DataFrame(risk_rows), by, (test, p_test, best), pts,
            (pd.DataFrame(pm), pm_pat, pm_D, pd.DataFrame(rank), lead, prec), q1)


def calib_plot(test, p, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    y = test["y"].to_numpy()
    bins = np.linspace(0, 1, 11)
    idx = np.minimum(np.digitize(p, bins) - 1, 9)
    xs = [p[idx == b].mean() for b in range(10) if (idx == b).sum() >= 30]
    ys = [y[idx == b].mean() for b in range(10) if (idx == b).sum() >= 30]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot([0, 1], [0, 1], "k--", lw=1, label="lý tưởng")
    ax[0].plot(xs, ys, "o-", color="#E45756", label="XGB + risk (test)")
    ax[0].set(xlabel="xác suất dự đoán p", ylabel="tần suất thiếu tiền thực tế", title=title)
    ax[0].legend()
    ax[1].hist(p, bins=20, color="#4C78A8")
    ax[1].set(xlabel="p", ylabel="số điểm quyết định", title="Phân phối p trên test")
    fig.tight_layout()
    fig.savefig(path, dpi=110)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--K", type=int, default=500)
    a = ap.parse_args()
    t0 = time.time()
    base, methods, risk, by, (test, p_test, best), pts, (pm, pm_pat, pm_D, rank, lead, prec), q1 = run(a.seed, a.csv, a.K)
    pd.set_option("display.width", 230)
    print(f"tổng thời gian {time.time() - t0:.0f}s | phương pháp được chọn theo Brier val: {best}")
    print("\n=== Ba cách ước lượng p (Brier/ECE thấp hơn = hiệu chỉnh tốt hơn; cov80 danh nghĩa = 0,80) ===")
    print(methods[["model", "p_star", "f1_val", "brier_val", "ece_val", "brier_test", "ece_test", "f1", "cov80", "cov80_spike", "secs"]].round(3).to_string(index=False))
    show = pd.concat([base[["model", "m", "precision", "recall", "f1", "cycle_recall", "cycle_false_alarm"]],
                      risk[["model", "p_star", "precision", "recall", "f1", "cycle_recall", "cycle_false_alarm", "brier_test", "ece_test"]]])
    print("\n=== TEST ===")
    print(show.round(3).to_string(index=False))
    print("\n=== XGB+risk theo 4 kiểu chi tiêu ===")
    print(by[["precision", "recall", "f1", "cycle_false_alarm"]].round(3).to_string())
    print("\n=== Chỉ số cho p_t (test) ===")
    print(pm[pm.set == "test"].drop(columns=["set", "n"]).round(3).to_string(index=False))
    print("\n=== Chỉ số p_t theo kiểu chi tiêu (XGB+risk, test) ===")
    print(pm_pat[[c for c in ("pos_rate", "brier", "auroc", "ece", "cal_slope", "cov80") if c in pm_pat.columns]].round(3).to_string())
    os.makedirs("results", exist_ok=True)
    risk.to_csv(f"results/risk_seed{a.seed}.csv", index=False)
    pts.to_csv(f"results/risk_points_seed{a.seed}.csv", index=False)
    methods.to_csv(f"results/risk_methods_seed{a.seed}.csv", index=False)
    pm.to_csv(f"results/pmetrics_seed{a.seed}.csv", index=False)
    rank.to_csv(f"results/rank_seed{a.seed}.csv", index=False)
    lead.to_csv(f"results/lead_seed{a.seed}.csv", index=False)
    prec.to_csv(f"results/prec_seed{a.seed}.csv", index=False)
    print("\n=== Báo sớm ở cùng mức báo nhầm 20% (test) ===")
    print(lead[lead.far_target == 0.2][["model", "far_actual", "cycle_recall", "lead_mean_all", "lead_median_caught"]].round(3).to_string(index=False))
    print("\n=== AUROC / AUPRC (điểm số liên tục, không phụ thuộc ngưỡng; test) ===")
    print(rank.round(3).to_string(index=False))
    pm_pat.to_csv(f"results/pmetrics_by_pattern_seed{a.seed}.csv")
    pm_D.to_csv(f"results/pmetrics_by_D_seed{a.seed}.csv")
    calib_plot(test, p_test, f"results/calibration_seed{a.seed}.png", f"Hiệu chỉnh xác suất (seed {a.seed}, {best})")
    print(f"\nĐã lưu results/risk_seed{a.seed}.csv, risk_methods_seed{a.seed}.csv, calibration_seed{a.seed}.png")
