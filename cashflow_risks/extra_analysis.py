"""
extra_analysis.py - Bổ sung cho tiêu chí "Kỹ thuật" và "Kết quả" (thang điểm cuối kỳ). Người 2.
  (a) so XGBoost với mô hình khác (B1, B2, Ridge, Random Forest, HistGradientBoosting) trên cùng đặc trưng và cùng tập test
  (b) chi phí báo nhầm và bỏ sót: chọn ngưỡng theo tỉ lệ chi phí, và quy tắc Bayes dùng được vì xác suất đã được hiệu chỉnh
  (c) độ trễ và kích thước mô hình
  (d) khoảng tin cậy bootstrap theo NGƯỜI (resample người dùng) cho hiệu XGB - B2
  (f) phân tích theo nhóm (thu nhập, kiểu chi tiêu): có đối xử đều giữa các nhóm không
  python src/extra_analysis.py --seed 1                       # chạy tất cả (vài phút)
  python src/extra_analysis.py --seed 1 --stage train --models xgb,b1,b2     # chỉ huấn luyện/dự báo các mô hình rồi lưu cache
  python src/extra_analysis.py --seed 1 --stage analysis                      # đọc cache, tính bảng và khoảng tin cậy
Kết quả: results/models_seed*.csv, cost_seed*.csv, boot_seed*.csv, fair_seed*.csv, latency_seed*.csv
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(__file__))
from labels import make_dp, future_actual
from baselines import predict_spend_b1, predict_spend_b2, alert_by_margin, tune_margin, margin_score
from evaluate import evaluate, forecast_metrics, rank_metrics, lead_at_far
from model_xgb import XGBForecaster
from model_alt import SkForecaster
from risk import fit_predict, tune_pstar, volatility, bigdays, cum_pool, cum_prob
from prob_metrics import ece
from run_baselines import load
from policies import select_cost_threshold, cost_per_100

ALL_MODELS = ["b1", "b2", "ridge", "hgb", "rf", "xgb"]
NAME = {"b1": "B1", "b2": "B2", "ridge": "Ridge (tuyến tính)", "hgb": "HistGradientBoosting", "rf": "Random Forest", "xgb": "XGBoost"}
CACHE = "results/cache"
COST_RATIOS = (1, 2, 3, 5, 10, 20)


def split_dp(dp):
    sp = dp.split.to_numpy()
    return {k: dp[sp == k].reset_index(drop=True) for k in ("train", "calib", "val", "test")}


def train_stage(seed, models):
    df = load(seed, None)
    S = split_dp(make_dp(df))
    os.makedirs(CACHE, exist_ok=True)
    for name in models:
        t0 = time.time()
        fit_s = 0.0
        if name == "b1":
            f = predict_spend_b1
        elif name == "b2":
            f = predict_spend_b2
        elif name == "xgb":
            fc = XGBForecaster(seed=seed).fit(df, S["train"], S["val"])
            f, fit_s = fc.predict_spend, time.time() - t0
        else:
            fc = SkForecaster(name, seed).fit(df, S["train"])
            f, fit_s = fc.predict_spend, fc.fit_seconds
        t1 = time.time()
        out = {k: f(df, S[k]) for k in ("calib", "val", "test")} if name in ("xgb", "b2") else {k: f(df, S[k]) for k in ("val", "test")}
        t_pred_all = time.time() - t1
        t2 = time.time(); f(df, S["test"]); t_test = time.time() - t2
        np.savez_compressed(f"{CACHE}/seed{seed}_{name}.npz", fit_seconds=fit_s, pred_ms_per_1k=1000 * t_test / (len(S["test"]) / 1000.0), **out)
        print(f"{name:6s} xong: huấn luyện {fit_s:5.1f}s, dự báo test {t_test:4.1f}s ({1000 * t_test / (len(S['test']) / 1000):.0f} ms/1000 điểm)", flush=True)
        if name == "xgb":
            latency_xgb(seed, df, fc)


def latency_xgb(seed, df, fc):
    """Độ trễ của MỘT yêu cầu (dựng đặc trưng từ lịch sử của một người, dự báo chi tiêu các ngày còn lại) và kích thước mô hình."""
    import tempfile
    uid = int(df.user_id.iloc[0])
    u = df[df.user_id == uid].reset_index(drop=True)
    dpu = make_dp(u)
    one = dpu[dpu.split == "test"].iloc[[len(dpu[dpu.split == "test"]) // 2]].reset_index(drop=True)
    fc.predict_spend(u, one)                                           # khởi động
    ts = []
    for _ in range(40):
        t0 = time.perf_counter(); fc.predict_spend(u, one); ts.append(1000 * (time.perf_counter() - t0))
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m.json"); fc.model.save_model(path); size_kb = os.path.getsize(path) / 1024
    rows = [("1 yêu cầu: dựng đặc trưng + dự báo (ms, trung vị 40 lần)", float(np.median(ts))),
            ("1 yêu cầu: lần chậm nhất trong 40 lần (ms)", float(np.max(ts))),
            ("số cây XGBoost", float(fc.best_iteration)), ("kích thước file mô hình (KB)", float(size_kb)),
            ("số dòng lịch sử của người dùng trong yêu cầu", float(len(u)))]
    pd.DataFrame(rows, columns=["mục", "giá trị"]).to_csv(f"results/latency_seed{seed}.csv", index=False)
    print(f"độ trễ 1 yêu cầu (trung vị): {np.median(ts):.1f} ms | mô hình {size_kb:.0f} KB", flush=True)


def per_user_counts(users, alert, y):
    d = pd.DataFrame({"u": users, "tp": alert & (y == 1), "fp": alert & (y == 0), "fn": ~alert & (y == 1)})
    return d.groupby("u")[["tp", "fp", "fn"]].sum()


def analysis_stage(seed, B=500):
    df = load(seed, None)
    dp = make_dp(df)
    S = split_dp(dp)
    cal, val, test = S["calib"], S["val"], S["test"]
    y = test.y.to_numpy().astype(int)
    P = {m: np.load(f"{CACHE}/seed{seed}_{m}.npz") for m in ALL_MODELS if os.path.exists(f"{CACHE}/seed{seed}_{m}.npz")}
    miss = [m for m in ALL_MODELS if m not in P]
    if miss:
        raise SystemExit(f"Thiếu cache của: {miss}. Chạy --stage train --models {','.join(miss)} trước.")

    # (a) bảng so sánh mô hình
    rows, scores, alerts, abs_err, scores_val = [], {}, {}, {}, {}
    for m in ALL_MODELS:
        yv, yt = P[m]["val"], P[m]["test"]
        mg, _ = tune_margin(val, yv, evaluate)
        a = alert_by_margin(test, yt, mg)
        sc = margin_score(test, yt)
        ev, fm, rk = evaluate(test, a), forecast_metrics(df, test, yt), rank_metrics(test, sc)
        ld = lead_at_far(test, sc, fars=(0.2,)).iloc[0]
        rows.append({"model": NAME[m], "key": m, "MAE_spend": fm["MAE_spend"], "MAE_balance": fm["MAE_balance"], "f1": ev["f1"], "precision": ev["precision"],
                     "recall": ev["recall"], "auroc": rk["auroc"], "auprc": rk["auprc"], "recall_at_far20": ld.cycle_recall,
                     "lead_at_far20": ld.lead_mean_all, "fit_seconds": float(P[m]["fit_seconds"]), "pred_ms_per_1k": float(P[m]["pred_ms_per_1k"])})
        scores[m], alerts[m] = sc, a
        scores_val[m] = margin_score(val, yv)
        e = np.abs(future_actual(df, test) - yt)
        abs_err[m] = np.nan_to_num(e).sum(axis=1), (~np.isnan(e)).sum(axis=1)
    pd.DataFrame(rows).to_csv(f"results/models_seed{seed}.csv", index=False)
    print(pd.DataFrame(rows).set_index("model")[["MAE_spend", "f1", "auroc", "recall_at_far20", "fit_seconds", "pred_ms_per_1k"]].round(3).to_string(), flush=True)

    # xác suất p của XGBoost (cumb), p* chọn trên val
    yc, yv, yt = P["xgb"]["calib"], P["xgb"]["val"], P["xgb"]["test"]
    p_val, p_test = fit_predict("cumb", cal, yc, [(val, yv), (test, yt)], df)
    ps, _ = tune_pstar(val, p_val, evaluate)
    scores["xgbp"], alerts["xgbp"] = p_test, p_test > ps
    scores_val["xgbp"] = p_val
    pool = cum_pool(cal, yc, df, volatility(df, cal)[1], bigdays(df, cal))
    one = test.iloc[[len(test) // 2]].reset_index(drop=True)
    cv1, bg1 = volatility(df, one)[1], bigdays(df, one)
    ts = []
    for _ in range(100):
        t0 = time.perf_counter(); cum_prob(pool, one, yt[[len(test) // 2]], cv1, bg1); ts.append(1000 * (time.perf_counter() - t0))
    lat = pd.read_csv(f"results/latency_seed{seed}.csv")
    lat.loc[len(lat)] = ["tính xác suất p từ dự báo của 1 điểm (ms, trung vị 100 lần)", float(np.median(ts))]
    lat.to_csv(f"results/latency_seed{seed}.csv", index=False)

    # (b) chi phí: báo nhầm (FP) tốn 1, bỏ sót (FN) tốn r
    N, crow = len(y), []
    for r in COST_RATIOS:
        for key, label in (("b1", "B1"), ("b2", "B2"), ("xgb", "XGB (điểm biên)"), ("xgbp", "XGB + p")):
            s = scores[key]
            threshold = select_cost_threshold(val, scores_val[key], r)
            row = {"r": r, "model": label,
                   "cost_test_per_100": cost_per_100(y, s, threshold, r),
                   "cost_val_per_100": cost_per_100(val.y, scores_val[key], threshold, r),
                   "tau_val": threshold, "threshold_source": "validation",
                   "cost_bayes_per_100": np.nan, "tau_bayes": np.nan}
            if key == "xgbp":
                tb = 1.0 / (1.0 + r)
                row["cost_bayes_per_100"] = 100.0 * (((s > tb) & (y == 0)).sum() + r * ((s <= tb) & (y == 1)).sum()) / N
                row["tau_bayes"] = tb
            crow.append(row)
    pd.DataFrame(crow).to_csv(f"results/cost_seed{seed}.csv", index=False)

    # (d) bootstrap theo người
    users = test.user_id.to_numpy()
    uniq = np.unique(users)
    pts_by_u = {u: np.flatnonzero(users == u) for u in uniq}
    cyc = test[["user_id", "cycle_id", "y"]].copy()
    for k in ("b2", "xgb", "xgbp"):
        cyc[k] = scores[k]
    cg = cyc.groupby(["user_id", "cycle_id"]).agg(y=("y", "first"), b2=("b2", "max"), xgb=("xgb", "max"), xgbp=("xgbp", "max")).reset_index()
    cyc_by_u = {u: np.flatnonzero(cg.user_id.to_numpy() == u) for u in uniq}
    counts = {k: per_user_counts(users, alerts[k], y).reindex(uniq, fill_value=0) for k in ("b2", "xgb", "xgbp")}
    err = {k: (pd.Series(abs_err[k][0]).groupby(users).sum().reindex(uniq).to_numpy(), pd.Series(abs_err[k][1]).groupby(users).sum().reindex(uniq).to_numpy())
           for k in ("b2", "xgb")}
    ucol = {u: i for i, u in enumerate(uniq)}
    rng = np.random.default_rng(seed)

    def metrics(idx_users):
        pidx = np.concatenate([pts_by_u[u] for u in idx_users]); cidx = np.concatenate([cyc_by_u[u] for u in idx_users])
        out = {}
        yy = y[pidx]
        for k in ("b2", "xgb", "xgbp"):
            out[f"AUROC|{k}"] = roc_auc_score(yy, scores[k][pidx])
            c = cg.iloc[cidx]; neg = c[c.y == 0][k].to_numpy(); pos = c[c.y == 1][k].to_numpy()
            out[f"recall@FAR20|{k}"] = float((pos > np.quantile(neg, 0.8)).mean())
            ct = counts[k].loc[idx_users].sum(); out[f"F1|{k}"] = 2 * ct.tp / (2 * ct.tp + ct.fp + ct.fn)
        for k in ("b2", "xgb"):
            ii = [ucol[u] for u in idx_users]; out[f"MAE|{k}"] = err[k][0][ii].sum() / err[k][1][ii].sum()
        out["MAE|xgbp"] = out["MAE|xgb"]
        return out

    obs = metrics(list(uniq))
    boots = [metrics(list(rng.choice(uniq, len(uniq), replace=True))) for _ in range(B)]
    brow = []
    for comp, a, b in (("XGB (điểm biên) - B2", "xgb", "b2"), ("XGB + p - B2", "xgbp", "b2"), ("XGB + p - XGB (điểm biên)", "xgbp", "xgb")):
        for met, lab in (("AUROC", "AUROC"), ("recall@FAR20", "tỉ lệ bắt được ở báo nhầm 20%"), ("F1", "F1 (ngưỡng chọn trên val)"), ("MAE", "MAE chi tiêu ngày")):
            d = np.array([bt[f"{met}|{a}"] - bt[f"{met}|{b}"] for bt in boots])
            brow.append({"so_sánh": comp, "chỉ_số": lab, "chênh_quan_sát": obs[f"{met}|{a}"] - obs[f"{met}|{b}"],
                         "ci_thấp": float(np.percentile(d, 2.5)), "ci_cao": float(np.percentile(d, 97.5)), "tỉ_lệ_resample_có_lợi": float((d < 0).mean() if met == "MAE" else (d > 0).mean())})
    pd.DataFrame(brow).to_csv(f"results/boot_seed{seed}.csv", index=False)

    # (f) theo nhóm
    frow = []
    p, al = scores["xgbp"], alerts["xgbp"]
    for gname, col in (("thu nhập", "income_type"), ("kiểu chi tiêu", "pattern")):
        for g, idx in test.groupby(col).indices.items():
            sub, yy, pp, aa = test.iloc[idx].reset_index(drop=True), y[idx], p[idx], al[idx]
            ev = evaluate(sub, aa)
            frow.append({"nhóm_theo": gname, "nhóm": g, "n_điểm": len(idx), "tỉ_lệ_thiếu_tiền": yy.mean(), "p_trung_bình": pp.mean(), "precision": ev["precision"],
                         "recall": ev["recall"], "fpr_điểm": float((aa & (yy == 0)).sum() / max((yy == 0).sum(), 1)), "báo_nhầm_theo_chu_kỳ": ev["cycle_false_alarm"],
                         "auroc": roc_auc_score(yy, pp), "ece": ece(pp, yy)})
    pd.DataFrame(frow).to_csv(f"results/fair_seed{seed}.csv", index=False)
    print("đã lưu models, cost, boot, fair, latency cho seed", seed, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--stage", choices=["all", "train", "analysis"], default="all")
    ap.add_argument("--models", default=",".join(ALL_MODELS))
    ap.add_argument("--B", type=int, default=500, help="số lần resample bootstrap theo người")
    a = ap.parse_args()
    os.makedirs("results", exist_ok=True)
    if a.stage in ("all", "train"):
        train_stage(a.seed, [m for m in a.models.split(",") if m])
    if a.stage in ("all", "analysis"):
        analysis_stage(a.seed, a.B)
    if a.stage == "all":                                   # chạy một lệnh thì dọn cache; chạy theo giai đoạn thì giữ lại
        for m in ALL_MODELS:
            p = f"{CACHE}/seed{a.seed}_{m}.npz"
            if os.path.exists(p):
                os.remove(p)
