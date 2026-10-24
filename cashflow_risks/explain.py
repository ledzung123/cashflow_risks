"""
explain.py - "Lý do cảnh báo" cho từng điểm quyết định: đóng góp SHAP của từng đặc trưng vào TỔNG CHI dự báo D ngày tới.
  python src/explain.py --seed 1
Dùng TreeSHAP có sẵn trong XGBoost (pred_contribs=True), không cần thư viện shap.
  - Mô hình dự báo chi tiêu ngày t+h đã chuẩn hóa (chia cho mức chi TB 28 ngày, `scale`), nên đóng góp (VND) = SHAP × scale,
    cộng qua h = 1..D. Mốc so sánh ("base") = hệ số chặn của mô hình × scale × D; tổng dự báo = base + tổng các đóng góp
    (trước khi chặn dự báo âm về 0).
  - p của XGB + risk tăng khi tổng chi dự báo tăng so với phần số dư còn trên θ (balance_t − θ), nên đặc trưng làm tăng dự báo chi
    là lý do đẩy rủi ro lên. Lớp xác suất (risk.py) chỉ thêm độ bất định theo nhóm D / độ biến động, không đổi thứ tự lý do.
Huấn luyện lại XGBoost đúng như run_risk.py (cùng seed, cùng dữ liệu). Cảnh báo lấy từ results/risk_points_seed{S}.csv.
Đầu ra (results/final/): explain_alerts_seed{S}.csv (mọi điểm test có cảnh báo), explain_global_seed{S}.csv,
explain_cases.csv (2 ví dụ trong error_cases.csv), fig12_explain.png.
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, os.path.dirname(__file__))
from labels import make_dp
from features import build_matrix, FEATURES
from model_xgb import XGBForecaster
from run_baselines import load
from make_report import vn

OUT = "results/final"
LABEL = {
    "h": "số ngày tính từ hôm nay đến ngày dự báo", "tgt_wd": "thứ trong tuần của ngày dự báo",
    "tgt_weekend": "ngày dự báo rơi vào cuối tuần", "tgt_dic": "vị trí ngày dự báo trong chu kỳ",
    "days_after": "số ngày còn lại sau ngày dự báo", "dic_t": "hôm nay là ngày thứ mấy của chu kỳ",
    "D": "số ngày còn lại đến kỳ nhận tiền", "mean7_rel": "chi TB 7 ngày gần nhất", "mean14_rel": "chi TB 14 ngày gần nhất",
    "std14_rel": "độ dao động chi 14 ngày", "max14_rel": "khoản chi lớn nhất 14 ngày", "last1_rel": "chi hôm nay",
    "big28": "số ngày chi lớn trong 28 ngày", "we_ratio": "chi cuối tuần so với ngày thường", "bal_rel": "số dư hiện tại",
    "theta_rel": "ngưỡng θ", "b2_rel": "dự báo B2 (TB cùng thứ)", "hist_dic_rel": "chi cùng ngày-trong-chu-kỳ ở các chu kỳ trước",
    "hist_smooth_rel": "chi quanh ngày-trong-chu-kỳ đó ở các chu kỳ trước", "n_prev": "số chu kỳ lịch sử",
}


def contributions(fc, df, dp):
    """(n_dp, F) đóng góp VND vào tổng chi dự báo D ngày, (n_dp,) mốc base, (n_dp,) tổng dự báo (đã chặn >= 0)."""
    X, meta = build_matrix(df, dp)
    C = fc.model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True, iteration_range=(0, fc.best_iteration))
    pred = fc.model.predict(X)
    assert np.allclose(C.sum(1), pred, rtol=1e-3, atol=1e-3), "SHAP phải cộng lại đúng bằng dự báo"
    Cv = C * meta["scale"][:, None]
    T = np.zeros((len(dp), C.shape[1]))
    np.add.at(T, meta["idx"], Cv)
    s_hat = np.nansum(fc.predict_spend(df, dp), axis=1)
    return T[:, :-1], T[:, -1], s_hat


def reason(row, contrib, k=3):
    up = [(f, v) for f, v in sorted(zip(FEATURES, contrib), key=lambda x: -x[1]) if v > 0][:k]
    txt = ", ".join(f"{LABEL[f]} (+{vn(v / 1e6, 2)} tr)" for f, v in up) or "không có"
    return (f"Dự báo chi {int(row.D)} ngày tới {vn(row.s_hat / 1e6, 2)} tr; số dư còn trên θ {vn(row.headroom / 1e6, 2)} tr. "
            f"Yếu tố làm tăng dự báo chi nhiều nhất: {txt}.")


def plot_saved(seed=1):
    """Rebuild fig12 from saved SHAP tables without refitting or recomputing contributions."""
    glob = pd.read_csv(f"{OUT}/explain_global_seed{seed}.csv").sort_values("mean_abs_vnd", ascending=False)
    cases = pd.read_csv(f"{OUT}/explain_cases.csv")
    if cases.empty:
        raise ValueError("explain_cases.csv chưa có ca để vẽ")
    cases = cases.sort_values("case", key=lambda col: col.map({"FP": 0, "FN": 1}).fillna(2))
    fig, ax = plt.subplots(1 + len(cases), 1, figsize=(10, 3.4 * (1 + len(cases))))
    ax = np.atleast_1d(ax)
    top = glob.head(10).iloc[::-1]
    ax[0].barh(top.mo_ta, top.mean_abs_vnd / 1e6, color="#F58518")
    ax[0].set(xlabel="trung bình |đóng góp| vào tổng chi dự báo (triệu VND)", title=f"Toàn cục, tập test (seed {seed})")
    names = {"FP": "Báo nhầm", "FN": "Bỏ sót"}
    feature_cols = [f"c_{feature}" for feature in FEATURES]
    for a, (_, row) in zip(ax[1:], cases.iterrows()):
        vals = pd.Series(row[feature_cols].to_numpy(dtype=float), index=FEATURES)
        vals = vals.reindex(vals.abs().sort_values(ascending=False).index[:6])[::-1]
        labels = [LABEL[f] for f in vals.index]
        a.barh(labels, vals.values / 1e6, color=np.where(vals.values > 0, "#E45756", "#4C78A8"))
        a.axvline(0, color="k", lw=0.8)
        a.set(xlabel="đóng góp vào tổng chi dự báo (triệu VND; đỏ = tăng rủi ro)",
              title=f"{names.get(row['case'], row['case'])}: user {int(row.user_id)}, chu kỳ {int(row.cycle_id)}, ngày {int(row.t)}\n"
                    f"p = {vn(row.p_xgb, 2)}; dự báo chi {vn(row.s_hat / 1e6, 2)} tr / còn trên θ {vn(row.headroom / 1e6, 2)} tr")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig12_explain.png", dpi=130)
    plt.close(fig)
    print(f"Đã dựng lại {OUT}/fig12_explain.png từ SHAP CSV đã lưu")


def main(seed):
    os.makedirs(OUT, exist_ok=True)
    df = load(seed, None)
    dp = make_dp(df)
    sp = dp.split.to_numpy()
    tr, val, test = (dp[sp == s].reset_index(drop=True) for s in ("train", "val", "test"))
    fc = XGBForecaster(seed=seed).fit(df, tr, val)
    T, base, s_hat = contributions(fc, df, test)

    pts = pd.read_csv(f"results/risk_points_seed{seed}.csv")
    key = ["user_id", "cycle_id", "t"]
    info = test[key + ["D", "balance_t", "theta_c", "y", "pattern"]].copy()
    info = info.merge(pts[key + ["p_xgb", "alert_XGB+risk"]], on=key, how="left", validate="1:1")
    assert info["p_xgb"].notna().all(), "risk_points phải khớp tập test (chạy run_risk.py cùng seed trước)"
    info["s_hat"], info["base"], info["headroom"] = s_hat, base, info.balance_t - info.theta_c
    contrib = pd.DataFrame(T, columns=[f"c_{f}" for f in FEATURES])

    # Toàn cục: trung bình |đóng góp| trên mọi điểm test
    glob = pd.DataFrame({"feature": FEATURES, "mo_ta": [LABEL[f] for f in FEATURES],
                         "mean_abs_vnd": np.abs(T).mean(0), "mean_vnd_khi_canh_bao": T[info["alert_XGB+risk"].to_numpy() == 1].mean(0)})
    glob = glob.sort_values("mean_abs_vnd", ascending=False)
    glob.round(0).to_csv(f"{OUT}/explain_global_seed{seed}.csv", index=False)

    al = info["alert_XGB+risk"].to_numpy() == 1
    rows = info[al].reset_index(drop=True)
    rows["ly_do"] = [reason(r, c) for r, c in zip(rows.itertuples(), T[al])]
    pd.concat([rows, contrib[al].reset_index(drop=True).round(0)], axis=1).to_csv(
        f"{OUT}/explain_alerts_seed{seed}.csv", index=False)

    # Hai ví dụ của error_cases.py: báo nhầm tại ngày cảnh báo đầu tiên, bỏ sót tại ngày p lớn nhất
    cases = []                                                   # (loại lỗi, chỉ số dòng trong info)
    ec_path = f"{OUT}/error_cases.csv"
    if os.path.exists(ec_path):
        ec = pd.read_csv(ec_path)
        ec = ec[ec.seed == seed]
        for kind, g in ec.groupby("case"):
            g = g.sort_values("t")
            t = g.loc[g["alert_XGB+risk"] == 1, "t"].min() if kind == "FP" else g.loc[g.p_xgb.idxmax(), "t"]
            i = info.index[(info.user_id == g.user_id.iloc[0]) & (info.cycle_id == g.cycle_id.iloc[0]) & (info.t == t)][0]
            cases.append((kind, i))
        out = pd.concat([info.loc[[i]].assign(case=k, ly_do=reason(info.loc[i], T[i])) for k, i in cases])
        pd.concat([out.reset_index(drop=True), contrib.loc[[i for _, i in cases]].reset_index(drop=True).round(0)],
                  axis=1).to_csv(f"{OUT}/explain_cases.csv", index=False)

    cases.sort(key=lambda c: c[0] != "FP")                       # báo nhầm trước, bỏ sót sau (như fig11)
    fig, ax = plt.subplots(1 + len(cases), 1, figsize=(10, 3.4 * (1 + len(cases))))
    ax = np.atleast_1d(ax)
    top = glob.head(10)[::-1]
    ax[0].barh([LABEL[f] for f in top.feature], top.mean_abs_vnd / 1e6, color="#F58518")
    ax[0].set(xlabel="trung bình |đóng góp| vào tổng chi dự báo (triệu VND)", title=f"Toàn cục, tập test (seed {seed})")
    names = {"FP": "Báo nhầm", "FN": "Bỏ sót"}
    for a, (kind, i) in zip(ax[1:], cases):
        c = pd.Series(T[i], index=FEATURES)
        c = c.reindex(c.abs().sort_values(ascending=False).index[:6])[::-1]
        a.barh([LABEL[f] for f in c.index], c.values / 1e6, color=np.where(c.values > 0, "#E45756", "#4C78A8"))
        a.axvline(0, color="k", lw=0.8)
        r = info.loc[i]
        a.set(xlabel="đóng góp vào tổng chi dự báo (triệu VND; đỏ = tăng rủi ro)",
              title=f"{names[kind]}: user {r.user_id}, chu kỳ {r.cycle_id}, ngày {r.t}\n"
                    f"p = {vn(r.p_xgb, 2)}; dự báo chi {vn(r.s_hat / 1e6, 2)} tr / còn trên θ {vn(r.headroom / 1e6, 2)} tr")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig12_explain.png", dpi=130); plt.close(fig)
    print(f"Đã lưu {OUT}/explain_alerts_seed{seed}.csv ({al.sum():,} cảnh báo), explain_global_seed{seed}.csv, "
          f"explain_cases.csv, fig12_explain.png")
    print(glob.head(8)[["feature", "mean_abs_vnd"]].round(0).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--plot-saved", action="store_true", help="chỉ dựng lại fig12 từ CSV SHAP, không huấn luyện lại")
    a = ap.parse_args()
    if a.plot_saved:
        plot_saved(a.seed)
    else:
        main(a.seed)
