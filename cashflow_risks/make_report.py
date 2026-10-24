"""
make_report.py - Bước 6: gộp kết quả 3 seed thành bảng Q1/Q2, bảng theo 4 kiểu chi tiêu, kiểm định cặp, biểu đồ cho báo cáo.
  python src/make_report.py --seeds 1 2 3
Đầu vào (đã có sau bước 3-5): results/{baselines,xgb,risk}_seed*.csv, xgb_by_pattern_seed*.csv, xgb_importance_seed*.csv, risk_points_seed*.csv
Đầu ra: results/final/ (CSV, RESULTS.md, fig1..fig6). Mọi câu kết luận trong RESULTS.md được tính từ số liệu, không viết tay.
"""
import argparse
import os
import platform
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import xgboost

sys.path.insert(0, os.path.dirname(__file__))
from evaluate import evaluate
from risk import ece, brier

NAMES = {"B1": "B1 (TB 14 ngày)", "B2": "B2 (TB cùng thứ)", "XGB": "XGB (cảnh báo theo biên m)",
         "XGB+risk": "XGB + p > p*", "XGB+risk(k=2)": "XGB + p > p* (k=2)", "B2+risk": "B2 + p > p* (đối chứng)"}
ORDER = ["B1", "B2", "XGB", "XGB+risk", "XGB+risk(k=2)", "B2+risk"]
COLORS = {"B1": "#9D9D9D", "B2": "#4C78A8", "XGB": "#F58518", "XGB+risk": "#E45756",
          "XGB+risk(k=2)": "#B279A2", "B2+risk": "#72B7B2"}
PATTERNS = ["even", "front", "weekend", "spike"]
Q1 = ["MAE_spend", "RMSE_spend", "MAE_balance", "RMSE_balance"]
Q2 = ["precision", "recall", "f1", "auroc", "auprc", "ks", "cycle_recall", "cycle_false_alarm", "mean_days_early"]
OUT = "results/final"


def vn(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")


def ms(m, s, d=3):
    if pd.isna(m):
        return "—"
    return f"{vn(m, d)} ± {vn(s, d)}"


def load(seeds):
    rows = []
    for s in seeds:
        parts = [pd.read_csv(f"results/baselines_seed{s}.csv"), pd.read_csv(f"results/xgb_seed{s}.csv"),
                 pd.read_csv(f"results/risk_seed{s}.csv")]
        for d in parts:
            d["seed"] = s
            rows.append(d)
    R = pd.concat(rows, ignore_index=True)
    RK = pd.concat([pd.read_csv(f"results/rank_seed{s}.csv").assign(seed=s) for s in seeds])[["model", "seed", "auroc", "auprc", "ks"]]
    return R.merge(RK, on=["model", "seed"], how="left")           # AUROC/AUPRC/KS của điểm số liên tục (không phụ thuộc ngưỡng)


def per_seed_by_pattern(seeds):
    out = []
    for s in seeds:
        pts = pd.read_csv(f"results/risk_points_seed{s}.csv")
        for model in ORDER:
            a = pts[f"alert_{model}"].to_numpy()
            for pat in PATTERNS:
                m = (pts.pattern == pat).to_numpy()
                r = evaluate(pts[m].reset_index(drop=True), a[m])
                out.append({"seed": s, "model": model, "pattern": pat, **r})
    return pd.DataFrame(out)


def main(seeds):
    env_line = (f"Runtime: Python {platform.python_version()}, NumPy {np.__version__}, pandas {pd.__version__}, "
                f"scikit-learn {sklearn.__version__}, XGBoost {xgboost.__version__}, Matplotlib {matplotlib.__version__}.")
    os.makedirs(OUT, exist_ok=True)
    R = load(seeds)
    n = len(seeds)
    g = R.groupby("model")
    mean, std = g.mean(numeric_only=True), g.std(numeric_only=True)
    lines = []

    # ---------------- Q1
    q1 = pd.DataFrame(index=["B1", "B2", "XGB"])
    for c in Q1:
        q1[c] = [ms(mean.loc[m, c], std.loc[m, c], 0) for m in q1.index]
    q1["MAE_spend so với B2"] = [f"{100 * (mean.loc[m, 'MAE_spend'] / mean.loc['B2', 'MAE_spend'] - 1):+.1f}%".replace(".", ",") for m in q1.index]
    q1["MAE_balance so với B2"] = [f"{100 * (mean.loc[m, 'MAE_balance'] / mean.loc['B2', 'MAE_balance'] - 1):+.1f}%".replace(".", ",") for m in q1.index]
    q1.index = [NAMES[i] for i in q1.index]
    q1.to_csv(f"{OUT}/Q1_table.csv", encoding="utf-8-sig")

    # ---------------- Q2
    q2 = pd.DataFrame(index=ORDER)
    for c in Q2:
        d = 1 if c == "mean_days_early" else 3
        q2[c] = [ms(mean.loc[m, c], std.loc[m, c], d) for m in ORDER]
    q2["brier_test"] = [ms(mean.loc[m, "brier_test"], std.loc[m, "brier_test"]) if m.endswith("risk") or "risk" in m else "—" for m in ORDER]
    q2["ece_test"] = [ms(mean.loc[m, "ece_test"], std.loc[m, "ece_test"]) if "risk" in m else "—" for m in ORDER]
    q2.index = [NAMES[i] for i in q2.index]
    q2.to_csv(f"{OUT}/Q2_table.csv", encoding="utf-8-sig")

    # ---------------- theo kiểu chi tiêu
    P = per_seed_by_pattern(seeds)
    pg = P.groupby(["model", "pattern"])
    pm, ps = pg[["precision", "recall", "f1", "cycle_false_alarm"]].mean(), pg[["precision", "recall", "f1", "cycle_false_alarm"]].std()
    rows = []
    for m in ORDER:
        for pat in PATTERNS:
            rows.append({"model": NAMES[m], "pattern": pat,
                         **{c: ms(pm.loc[(m, pat), c], ps.loc[(m, pat), c]) for c in pm.columns}})
    pd.DataFrame(rows).to_csv(f"{OUT}/by_pattern_Q2.csv", index=False, encoding="utf-8-sig")
    bp = pd.concat([pd.read_csv(f"results/xgb_by_pattern_seed{s}.csv", index_col=0).assign(seed=s) for s in seeds])
    bpg = bp.groupby(level=0)
    bpm, bps = bpg.mean(numeric_only=True), bpg.std(numeric_only=True)
    q1p = pd.DataFrame({NAMES[m]: [ms(bpm.loc[p, f"MAEbal_{m}"], bps.loc[p, f"MAEbal_{m}"], 0) for p in PATTERNS]
                        for m in ("B1", "B2", "XGB")}, index=PATTERNS)
    q1p.to_csv(f"{OUT}/by_pattern_Q1_MAE_balance.csv", encoding="utf-8-sig")

    # tự kiểm tra: F1 theo kiểu tính từ điểm == F1 trong file run_xgb
    chk = max(abs(pm.loc[("XGB", p), "f1"] - bpm.loc[p, "F1_XGB"]) for p in PATTERNS)
    assert chk < 1e-9, f"F1 theo kiểu không khớp run_xgb ({chk})"

    # ---------------- kiểm định cặp (theo seed)
    wide = R.pivot_table(index="seed", columns="model", values=["f1", "auroc", "auprc", "MAE_spend", "MAE_balance", "cycle_false_alarm"])
    pair = []
    for a, b in [("XGB", "B2"), ("XGB", "B1"), ("XGB+risk", "B2"), ("XGB+risk", "XGB"), ("B2+risk", "B2")]:
        for c in ["f1", "auroc", "auprc", "MAE_spend", "MAE_balance", "cycle_false_alarm"]:
            if a not in wide[c].columns or b not in wide[c].columns or wide[c][[a, b]].isna().any().any():
                continue                                   # chỉ số này không có cho mô hình đó
            d = wide[c][a] - wide[c][b]
            better = (d > 0) if c in ("f1", "auroc", "auprc") else (d < 0)
            pair.append({"so_sánh": f"{a} − {b}", "chỉ_số": c, "chênh_TB": d.mean(), "std": d.std(),
                         "số_seed_tốt_hơn": f"{int(better.sum())}/{n}"})
    pair = pd.DataFrame(pair)
    pair.to_csv(f"{OUT}/paired_diff.csv", index=False, encoding="utf-8-sig")

    def won(a, b, c):
        return pair[(pair["so_sánh"] == f"{a} − {b}") & (pair["chỉ_số"] == c)].iloc[0]

    # ---------------- chỉ số cho p_t (việc 2) và kiểm chứng phần dư (việc 3)
    PM = pd.concat([pd.read_csv(f"results/pmetrics_seed{s}.csv").assign(seed=s) for s in seeds])
    PM = PM[PM["set"] == "test"]
    pcols = ["brier", "brier_skill", "log_loss", "log_loss_skill", "auroc", "auprc", "cal_slope", "cal_intercept",
             "ece", "mce", "sharpness", "cov50", "cov80", "cov90"]
    pgm = PM.groupby("model")[pcols]
    pmm, pms = pgm.mean(), pgm.std()
    pnames = {"XGB+risk": "XGB + p > p*", "B2+risk": "B2 + p > p* (đối chứng)"}
    ptab = pd.DataFrame({c: [ms(pmm.loc[m, c], pms.loc[m, c]) for m in pnames] for c in pcols}, index=list(pnames.values()))
    ptab.to_csv(f"{OUT}/P_table.csv", encoding="utf-8-sig")
    def by_tab(prefix, key, order, cols):
        d = pd.concat([pd.read_csv(f"results/pmetrics_by_{prefix}_seed{s}.csv", index_col=0).assign(seed=s) for s in seeds])
        g = d.groupby(level=0)[cols]
        mm, ss = g.mean(), g.std()
        tab = pd.DataFrame({c: [ms(mm.loc[k, c], ss.loc[k, c]) for k in order] for c in cols}, index=order)
        tab.index.name = key
        return tab, mm
    bcols = ["pos_rate", "brier", "auroc", "ece", "cal_slope", "cov80"]
    ptab_pat, pat_mean = by_tab("pattern", "pattern", PATTERNS, bcols)
    D_ORDER = ["3-4", "5-7", "8-11", "12-16", "17-21", "22-31"]
    ptab_D, D_mean = by_tab("D", "D", D_ORDER, bcols)
    ptab_pat.to_csv(f"{OUT}/P_by_pattern.csv", encoding="utf-8-sig")
    ptab_D.to_csv(f"{OUT}/P_by_D.csv", encoding="utf-8-sig")
    DG = pd.concat([pd.read_csv(f"results/diagnostics_seed{s}.csv").assign(seed=s) for s in seeds])
    dgm = DG.groupby("metric").value.agg(["mean", "std"])
    dnames = [("lagcorr_k1_test", "Tương quan phần dư cách 1 ngày"), ("lagcorr_k2_test", "Tương quan phần dư cách 2 ngày"),
              ("lagcorr_k3_test", "Tương quan phần dư cách 3 ngày"), ("lagcorr_k7_test", "Tương quan phần dư cách 7 ngày"),
              ("VR_D5_test", "Tỉ số phương sai, D=5 (độc lập = 1)"), ("VR_D10_test", "Tỉ số phương sai, D=10"),
              ("VR_D15_test", "Tỉ số phương sai, D=15"), ("VR_D20_test", "Tỉ số phương sai, D=20"),
              ("VR_D25_test", "Tỉ số phương sai, D=25")]
    for meth in ("mc", "cum", "cumb"):
        for sub in ("all", "even", "front", "weekend", "spike"):
            dnames.append((f"cov80_{meth}_{sub}", f"Độ phủ khoảng 80%, {meth}, {sub} (danh nghĩa 0,80)"))
    dtab = pd.DataFrame({"giá trị (TB ± std)": [ms(dgm.loc[k, "mean"], dgm.loc[k, "std"]) for k, _ in dnames]},
                        index=[n for _, n in dnames])
    dtab.index.name = "phép thử"
    dtab.to_csv(f"{OUT}/diagnostics_table.csv", encoding="utf-8-sig")

    # ---------------- báo sớm ở cùng mức báo nhầm
    LD = pd.concat([pd.read_csv(f"results/lead_seed{s}.csv").assign(seed=s) for s in seeds])
    LM = ["B1", "B2", "XGB", "XGB+risk", "B2+risk"]
    lrows = []
    for far in (0.1, 0.2, 0.3):
        g = LD[np.isclose(LD.far_target, far)].groupby("model")[["cycle_recall", "lead_mean_all", "lead_median_caught"]]
        gm, gs = g.mean(), g.std()
        for m in LM:
            lrows.append({"mức báo nhầm": f"{int(round(far * 100))}%", "mô hình": NAMES[m],
                          "tỉ lệ bắt được chu kỳ thiếu tiền": ms(gm.loc[m, "cycle_recall"], gs.loc[m, "cycle_recall"]),
                          "số ngày báo trước (bỏ sót tính 0)": ms(gm.loc[m, "lead_mean_all"], gs.loc[m, "lead_mean_all"], 1),
                          "trung vị số ngày báo trước (chỉ chu kỳ bắt được)": ms(gm.loc[m, "lead_median_caught"], gs.loc[m, "lead_median_caught"], 1)})
    ltab = pd.DataFrame(lrows).set_index(["mức báo nhầm", "mô hình"])
    ltab.to_csv(f"{OUT}/Lead_table.csv", encoding="utf-8-sig")
    L20 = LD[np.isclose(LD.far_target, 0.2)].pivot(index="seed", columns="model", values=["cycle_recall", "lead_mean_all", "lead_median_caught"])

    # ---------------- ở cùng Precision (đúng tiêu chí báo cáo giữa kỳ: "ở mức Precision tương đương, Recall cao hơn hoặc báo sớm hơn B1")
    PR = pd.concat([pd.read_csv(f"results/prec_seed{s}.csv").assign(seed=s) for s in seeds])
    PR = PR[PR.reachable.astype(bool)].assign(muc=lambda d: d.muc.astype(str))
    prows = []
    for muc in ("B1", "0.7"):
        g = PR[PR.muc == muc].groupby("model")
        gm, gs = g.mean(numeric_only=True), g.std(numeric_only=True)
        for m in LM:
            if m not in gm.index:
                continue
            prows.append({"mức precision": f"bằng B1 ({vn(gm.precision_target.mean())})" if muc == "B1" else vn(float(muc), 1),
                          "mô hình": NAMES[m], "precision đạt được": ms(gm.loc[m, "precision"], gs.loc[m, "precision"]),
                          "precision validation": ms(gm.loc[m, "precision_val"], gs.loc[m, "precision_val"]),
                          "recall": ms(gm.loc[m, "recall"], gs.loc[m, "recall"]),
                          "tỉ lệ bắt được chu kỳ thiếu tiền": ms(gm.loc[m, "cycle_recall"], gs.loc[m, "cycle_recall"]),
                          "báo nhầm theo chu kỳ": ms(gm.loc[m, "cycle_false_alarm"], gs.loc[m, "cycle_false_alarm"]),
                          "số ngày báo trước (bỏ sót tính 0)": ms(gm.loc[m, "lead_mean_all"], gs.loc[m, "lead_mean_all"], 1),
                          "trung vị số ngày báo trước (chỉ chu kỳ bắt được)": ms(gm.loc[m, "lead_median_caught"], gs.loc[m, "lead_median_caught"], 1)})
    ptab_prec = pd.DataFrame(prows).set_index(["mức precision", "mô hình"])
    ptab_prec.to_csv(f"{OUT}/Prec_table.csv", encoding="utf-8-sig")
    PB1 = PR[PR.muc == "B1"].pivot(index="seed", columns="model", values=["recall", "lead_mean_all", "lead_median_caught", "precision_target"])

    # ---------------- biểu đồ
    plt.rcParams.update({"font.size": 10})
    # fig1: Q1
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for a, c, t in [(ax[0], "MAE_spend", "MAE chi tiêu ngày (VND)"), (ax[1], "MAE_balance", "MAE số dư cuối chu kỳ (VND)")]:
        ms_ = ["B1", "B2", "XGB"]
        a.bar([NAMES[m].split(" (")[0] for m in ms_], [mean.loc[m, c] for m in ms_], yerr=[std.loc[m, c] for m in ms_],
              color=[COLORS[m] for m in ms_], capsize=4)
        a.set_title(t)
        for i, m in enumerate(ms_):
            a.text(i, mean.loc[m, c] * 1.01, f"{mean.loc[m, c] / 1000:,.0f}k", ha="center", va="bottom", fontsize=9)
    fig.suptitle(f"Q1 - Sai số dự báo trên test (trung bình ± độ lệch chuẩn, {n} seed)")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig1_Q1.png", dpi=130); plt.close(fig)

    # fig2: Q2
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), gridspec_kw={"width_ratios": [3, 1.4]})
    w = 0.13
    for i, m in enumerate(ORDER):
        ax[0].bar(np.arange(3) + (i - 2.5) * w, [mean.loc[m, c] for c in ("precision", "recall", "f1")],
                  w, yerr=[std.loc[m, c] for c in ("precision", "recall", "f1")], color=COLORS[m], capsize=2, label=NAMES[m])
    ax[0].set_xticks(range(3)); ax[0].set_xticklabels(["Precision", "Recall", "F1"]); ax[0].set_ylim(0.4, 0.85)
    ax[0].legend(fontsize=7.5, loc="upper left", ncol=2); ax[0].set_title("Chất lượng cảnh báo (mức điểm quyết định; trục y bắt đầu từ 0,4)")
    ax[1].bar(range(len(ORDER)), [mean.loc[m, "cycle_false_alarm"] for m in ORDER],
              yerr=[std.loc[m, "cycle_false_alarm"] for m in ORDER], color=[COLORS[m] for m in ORDER], capsize=3)
    ax[1].set_xticks(range(len(ORDER))); ax[1].set_xticklabels(["B1", "B2", "XGB\nm", "XGB\np*", "XGB\nk=2", "B2\np*"], fontsize=8)
    ax[1].set_title("Chu kỳ bình thường\nvẫn bị cảnh báo"); ax[1].set_ylim(0, 0.75)
    fig.suptitle(f"Q2 - Cảnh báo trên test ({n} seed)")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig2_Q2.png", dpi=130); plt.close(fig)

    # fig3: theo kiểu chi tiêu
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    show = ["B1", "B2", "XGB", "XGB+risk"]
    w = 0.2
    for i, m in enumerate(show):
        ax[0].bar(np.arange(4) + (i - 1.5) * w, [pm.loc[(m, p), "f1"] for p in PATTERNS], w,
                  yerr=[ps.loc[(m, p), "f1"] for p in PATTERNS], color=COLORS[m], capsize=2, label=NAMES[m])
    ax[0].set_xticks(range(4)); ax[0].set_xticklabels(PATTERNS); ax[0].set_ylim(0.4, 0.85)
    ax[0].set_title("F1 theo kiểu chi tiêu (trục y từ 0,4)"); ax[0].legend(fontsize=8)
    for i, m in enumerate(["B1", "B2", "XGB"]):
        ax[1].bar(np.arange(4) + (i - 1) * 0.26, [bpm.loc[p, f"MAEbal_{m}"] / 1e3 for p in PATTERNS], 0.26,
                  yerr=[bps.loc[p, f"MAEbal_{m}"] / 1e3 for p in PATTERNS], color=COLORS[m], capsize=2, label=NAMES[m].split(" (")[0])
    ax[1].set_xticks(range(4)); ax[1].set_xticklabels(PATTERNS); ax[1].set_title("MAE số dư cuối chu kỳ theo kiểu (nghìn VND)"); ax[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig3_by_pattern.png", dpi=130); plt.close(fig)

    # fig4: hiệu chỉnh gộp các seed
    pts = pd.concat([pd.read_csv(f"results/risk_points_seed{s}.csv") for s in seeds])
    fig, ax = plt.subplots(figsize=(5.4, 5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="lý tưởng")
    calib = {}
    for col, lab, c in [("p_xgb", "XGB + risk", COLORS["XGB+risk"]), ("p_b2", "B2 + risk", COLORS["B2+risk"])]:
        p, y = pts[col].to_numpy(), pts["y"].to_numpy()
        idx = np.minimum((p * 10).astype(int), 9)
        xs = [p[idx == b].mean() for b in range(10) if (idx == b).sum() >= 50]
        ys = [y[idx == b].mean() for b in range(10) if (idx == b).sum() >= 50]
        calib[lab] = (ece(p, y), brier(p, y))
        ax.plot(xs, ys, "o-", color=c, label=f"{lab} (ECE {ece(p, y):.3f})")
    ax.set(xlabel="xác suất dự đoán p", ylabel="tần suất thiếu tiền thực tế", title=f"Hiệu chỉnh xác suất (test, gộp {n} seed)")
    ax.legend(); fig.tight_layout(); fig.savefig(f"{OUT}/fig4_calibration.png", dpi=130); plt.close(fig)

    # fig5: độ quan trọng đặc trưng
    imp = pd.concat([pd.read_csv(f"results/xgb_importance_seed{s}.csv", index_col=0).iloc[:, 0].rename(s) for s in seeds], axis=1).fillna(0)
    im, isd = imp.mean(axis=1).sort_values(ascending=False), imp.std(axis=1)
    top = im.head(10)[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(top.index, top.values * 100, xerr=isd[top.index].values * 100, color="#F58518", capsize=2)
    ax.set(xlabel="% gain (trung bình các seed)", title="Độ quan trọng đặc trưng của XGBoost (top 10)")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig5_importance.png", dpi=130); plt.close(fig)

    # fig6: hai ví dụ minh họa (quy tắc chọn cố định: seed đầu, kiểu "front")
    s0 = seeds[0]
    pt = pd.read_csv(f"results/risk_points_seed{s0}.csv")
    pstar = float(pd.read_csv(f"results/risk_seed{s0}.csv").set_index("model").loc["XGB+risk", "p_star"])
    pt["key"] = pt.user_id.astype(str) + "-" + pt.cycle_id.astype(str)
    fr = pt[pt.pattern == "front"]
    first = lambda g, c: g.loc[g[c] == 1, "t"].min()
    summ = fr.groupby("key").apply(lambda g: pd.Series({"y": g.y.iloc[0], "x": first(g, "alert_XGB+risk"),
                                                       "b1": first(g, "alert_B1"), "b2": first(g, "alert_B2")}), include_groups=False)
    case_pos = summ[(summ.y == 1) & summ.x.notna()].index[0]
    neg = summ[(summ.y == 0) & summ.x.isna() & (summ.b1.notna() | summ.b2.notna())]
    case_neg = (neg.index[0] if len(neg) else summ[summ.y == 0].index[0])
    fig, ax = plt.subplots(2, 2, figsize=(12, 6.5), sharex="col")
    for j, (key, title) in enumerate([(case_pos, "Chu kỳ thiếu tiền (cảnh báo đúng)"), (case_neg, "Chu kỳ bình thường (tránh báo nhầm)")]):
        g = fr[fr.key == key].sort_values("t")
        ax[0, j].plot(g.t, g.p_xgb, "o-", color=COLORS["XGB+risk"], label="p (XGB + risk)")
        ax[0, j].axhline(pstar, color="k", ls="--", lw=1, label=f"p* = {pstar:.2f}")
        for col, m, yv in [("alert_B1", "B1", 1.08), ("alert_B2", "B2", 1.14), ("alert_XGB+risk", "XGB+risk", 1.02)]:
            ts = g.t[g[col] == 1]
            ax[0, j].scatter(ts, np.full(len(ts), yv), marker="|", s=90, color=COLORS[m], label=f"ngày cảnh báo {NAMES[m].split(' (')[0].split(' +')[0] if m != 'XGB+risk' else 'XGB+risk'}")
        ax[0, j].set(ylim=(-0.03, 1.22), title=title + f" - user {key.split('-')[0]}, chu kỳ {key.split('-')[1]}")
        ax[1, j].plot(g.t, g.balance_t / 1e6, "o-", color="#4C78A8", label="số dư")
        ax[1, j].plot(g.t, g.theta_c / 1e6, color="gray", ls="--", label="θ")
        ax[1, j].set(xlabel="ngày trong chu kỳ", ylabel="triệu VND")
        dd = g.dip_day.iloc[0]
        if not np.isnan(dd):
            for r in (0, 1):
                ax[r, j].axvline(dd, color="red", ls=":", label="ngày cạn thực tế" if r == 0 else None)
        ax[1, j].legend(fontsize=8)
    ax[0, 0].set_ylabel("xác suất p")
    h_, l_ = ax[0, 0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="lower center", ncol=6, fontsize=8)
    fig.suptitle(f"Ví dụ minh họa (seed {s0}; chọn theo quy tắc cố định, không phải ví dụ đại diện)")
    fig.tight_layout(rect=[0, 0.05, 1, 0.96]); fig.savefig(f"{OUT}/fig6_case_study.png", dpi=130); plt.close(fig)

    # fig7: hiệu chỉnh xác suất theo kiểu chi tiêu / theo D + độ phủ khoảng 80% của ba cách ước lượng
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    w = 0.26
    for i, (meth, col) in enumerate([("mc", "#9D9D9D"), ("cum", "#4C78A8"), ("cumb", "#E45756")]):
        ax[0].bar(np.arange(4) + (i - 1) * w, [dgm.loc[f"cov80_{meth}_{p}", "mean"] for p in PATTERNS], w, color=col,
                  yerr=[dgm.loc[f"cov80_{meth}_{p}", "std"] for p in PATTERNS], capsize=2,
                  label={"mc": "mc (phần dư độc lập)", "cum": "cum", "cumb": "cumb (thêm nhóm chi cực lớn)"}[meth])
    ax[0].axhline(0.8, color="k", ls="--", lw=1)
    ax[0].set_xticks(range(4)); ax[0].set_xticklabels(PATTERNS); ax[0].set_ylim(0.4, 1.0)
    ax[0].set_title("Độ phủ khoảng dự báo 80% (trục y từ 0,4)"); ax[0].legend(fontsize=7.5, loc="upper right")
    ax[1].bar(range(4), [pat_mean.loc[p, "ece"] for p in PATTERNS], color="#E45756")
    ax[1].set_xticks(range(4)); ax[1].set_xticklabels(PATTERNS); ax[1].set_title("ECE của XGB + p > p* theo kiểu chi tiêu")
    ax[2].bar(range(6), [D_mean.loc[k, "ece"] for k in D_ORDER], color="#E45756")
    ax[2].set_xticks(range(6)); ax[2].set_xticklabels(D_ORDER); ax[2].set_xlabel("số ngày còn lại D")
    ax[2].set_title("ECE theo số ngày còn lại")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig7_p_diagnostics.png", dpi=130); plt.close(fig)

    # fig9: báo sớm ở cùng mức báo nhầm
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    for m in LM:
        g = LD[LD.model == m].groupby("far_target")[["cycle_recall", "lead_mean_all"]].mean()
        ax[0].plot(g.index * 100, g.cycle_recall, marker="o", ms=4, color=COLORS[m], label=NAMES[m])
        ax[1].plot(g.index * 100, g.lead_mean_all, marker="o", ms=4, color=COLORS[m], label=NAMES[m])
    ax[0].set(xlabel="tỉ lệ chu kỳ bình thường bị cảnh báo (%)", ylabel="tỉ lệ bắt được chu kỳ thiếu tiền", title="Bắt được bao nhiêu chu kỳ thiếu tiền")
    ax[1].set(xlabel="tỉ lệ chu kỳ bình thường bị cảnh báo (%)", ylabel="số ngày báo trước ngày cạn tiền", title="Số ngày báo trước (chu kỳ bỏ sót tính 0)")
    ax[0].legend(fontsize=8, loc="lower right")
    fig.suptitle(f"So sánh ở CÙNG mức báo nhầm (test, trung bình {n} seed)")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig9_lead_far.png", dpi=130); plt.close(fig)

    # ---------------- RESULTS.md (câu kết luận tính từ số liệu)
    try:
        import tabulate  # noqa: F401
        tbl = lambda df: df.to_markdown()
    except Exception:
        tbl = lambda df: "```\n" + df.to_string() + "\n```"
    f_x, f_r = won("XGB", "B2", "f1"), won("XGB+risk", "B2", "f1")
    s_msg = []
    s_msg.append(f"- Q1: MAE chi tiêu ngày của XGB thấp hơn B2 {abs(100 * (mean.loc['XGB','MAE_spend'] / mean.loc['B2','MAE_spend'] - 1)):.1f}% "
                 f"(tốt hơn ở {won('XGB','B2','MAE_spend')['số_seed_tốt_hơn']} seed); MAE số dư thấp hơn "
                 f"{abs(100 * (mean.loc['XGB','MAE_balance'] / mean.loc['B2','MAE_balance'] - 1)):.1f}% (tốt hơn ở {won('XGB','B2','MAE_balance')['số_seed_tốt_hơn']} seed).")
    s_msg.append(f"- Q2: F1 của XGB (biên m) hơn B2 ở {f_x['số_seed_tốt_hơn']} seed, chênh trung bình {f_x['chênh_TB']:+.3f}; "
                 f"XGB + p > p* hơn B2 ở {f_r['số_seed_tốt_hơn']} seed, chênh {f_r['chênh_TB']:+.3f}.")
    d_rx, d_fa = won("XGB+risk", "XGB", "f1"), won("XGB+risk", "XGB", "cycle_false_alarm")
    s_msg.append(f"- XGB + p > p* so với XGB cảnh báo theo biên m: chênh F1 {d_rx['chênh_TB']:+.3f} (tốt hơn ở {d_rx['số_seed_tốt_hơn']} seed) - "
                 f"{'chênh rất nhỏ (< 0,01), không có ý nghĩa thực tế' if abs(d_rx['chênh_TB']) < 0.01 else 'khác biệt đáng kể'}; "
                 f"tỉ lệ chu kỳ bình thường vẫn bị cảnh báo {mean.loc['XGB+risk','cycle_false_alarm']:.3f} so với {mean.loc['XGB','cycle_false_alarm']:.3f} "
                 f"(XGB + p > p* tốt hơn ở {d_fa['số_seed_tốt_hơn']} seed, tức là {'cao hơn' if d_fa['chênh_TB'] > 0 else 'thấp hơn'} biên m).")
    a_x, a_r, a_l = won("XGB", "B2", "auroc"), won("XGB+risk", "B2", "auroc"), won("XGB+risk", "XGB", "auroc")
    s_msg.append(f"- Không phụ thuộc ngưỡng (AUROC): XGB (điểm số theo biên) hơn B2 {a_x['chênh_TB']:+.3f} ({a_x['số_seed_tốt_hơn']} seed); "
                 f"XGB + p hơn B2 {a_r['chênh_TB']:+.3f} ({a_r['số_seed_tốt_hơn']} seed) và hơn XGB theo biên {a_l['chênh_TB']:+.3f} "
                 f"({a_l['số_seed_tốt_hơn']} seed) - lớp xác suất cải thiện khả năng xếp hạng rủi ro dù F1 ở ngưỡng đã chọn gần như không đổi.")
    d20 = lambda c, a, b: ((L20[c][a] - L20[c][b]).mean(), int(((L20[c][a] - L20[c][b]) > 0).sum()))
    (rx, nrx), (lx, nlx) = d20("cycle_recall", "XGB", "B2"), d20("lead_mean_all", "XGB", "B2")
    (rr, nrr), (lr_, nlr) = d20("cycle_recall", "XGB+risk", "B2"), d20("lead_mean_all", "XGB+risk", "B2")
    med = L20["lead_median_caught"].mean()[LM]
    s_msg.append(f"- Báo sớm ở cùng mức báo nhầm 20%: XGB bắt được nhiều chu kỳ thiếu tiền hơn B2 {rx * 100:+.1f} điểm phần trăm ({nrx}/{n} seed) và số ngày báo trước "
                 f"(chu kỳ bỏ sót tính 0) hơn {lx:+.1f} ngày ({nlx}/{n} seed); XGB + p hơn B2 {rr * 100:+.1f} điểm và {lr_:+.1f} ngày ({nrr}/{n}, {nlr}/{n} seed). "
                 f"Trong các chu kỳ đã bắt được, trung vị số ngày báo trước gần như bằng nhau giữa các mô hình (chênh tối đa {med.max() - med.min():.1f} ngày): "
                 f"lợi thế là bắt được nhiều chu kỳ hơn ở cùng mức báo nhầm, không phải bắt sớm hơn trong chu kỳ đã bắt được.")
    dP = lambda c, a, b: ((PB1[c][a] - PB1[c][b]).mean(), int(((PB1[c][a] - PB1[c][b]) > 0).sum()))
    for a_, b_ in (("XGB+risk", "B1"), ("XGB+risk", "B2")):
        (pr_, npr), (pl_, npl), (pm_, _) = dP("recall", a_, b_), dP("lead_mean_all", a_, b_), dP("lead_median_caught", a_, b_)
        s_msg.append(f"- Tiêu chí báo cáo giữa kỳ (ở Precision bằng B1, trung bình {PB1['precision_target']['B1'].mean():.3f}): "
                     f"{NAMES[a_]} so với {NAMES[b_]}: Recall {pr_ * 100:+.1f} điểm phần trăm ({npr}/{n} seed), số ngày báo trước (bỏ sót tính 0) "
                     f"{pl_:+.1f} ngày ({npl}/{n} seed), trung vị số ngày báo trước trong chu kỳ bắt được {pm_:+.1f} ngày.")
    d_b, d_ba = won("B2+risk", "B2", "f1"), won("B2+risk", "B2", "auroc")
    s_msg.append(f"- Đối chứng B2 + p > p*: F1 chênh {d_b['chênh_TB']:+.3f} và AUROC chênh {d_ba['chênh_TB']:+.3f} so với B2. Lớp xác suất giúp xếp hạng rủi ro tốt hơn, "
                 f"nhưng F1 ở ngưỡng chọn trên val gần như không đổi; phần chênh F1 giữa XGB và B2 đến từ mô hình dự báo.")
    k2 = won("XGB+risk", "XGB", "cycle_false_alarm")
    s_msg.append(f"- Điều kiện k=2 (cảnh báo khi p > p* hai ngày liên tiếp) chỉ là thử nghiệm: tỉ lệ báo nhầm {mean.loc['XGB+risk(k=2)','cycle_false_alarm']:.3f} "
                 f"so với {mean.loc['XGB+risk','cycle_false_alarm']:.3f} khi k=1, F1 {mean.loc['XGB+risk(k=2)','f1']:.3f} so với {mean.loc['XGB+risk','f1']:.3f} - không dùng trong giải pháp cuối.")
    s_msg.append(f"- Hiệu chỉnh xác suất (test, gộp seed): XGB + risk ECE = {calib['XGB + risk'][0]:.3f}, Brier = {calib['XGB + risk'][1]:.3f}; "
                 f"B2 + risk ECE = {calib['B2 + risk'][0]:.3f}. (ECE gộp các seed nhỏ hơn trung bình ECE từng seed trong bảng Q2 vì ít nhiễu hơn.)")
    chosen = [pd.read_csv(f"results/risk_seed{s}.csv").set_index("model").loc["XGB+risk", "method"] for s in seeds]
    lag = [dgm.loc[k, "mean"] for k in ("lagcorr_k1_test", "lagcorr_k2_test", "lagcorr_k3_test", "lagcorr_k7_test")]
    vr = [dgm.loc[f"VR_D{d}_test", "mean"] for d in (5, 10, 15, 20, 25)]
    s_msg.append(f"- Phần dư độc lập theo ngày: tương quan giữa các ngày chỉ {min(lag):+.3f} đến {max(lag):+.3f} (gần 0), nhưng tỉ số phương sai "
                 f"Var(tổng)/Tổng Var nằm trong {min(vr):.2f}-{max(vr):.2f} (độc lập = 1) nên có phụ thuộc dương nhẹ; "
                 f"khoảng 80% của cách giả định độc lập (mc) chỉ phủ {dgm.loc['cov80_mc_all','mean']:.3f}, còn cum/cumb phủ "
                 f"{dgm.loc['cov80_cum_all','mean']:.3f}/{dgm.loc['cov80_cumb_all','mean']:.3f}.")
    s_msg.append(f"- Kiểu spike vẫn bị phủ thiếu: độ phủ 80% là {dgm.loc['cov80_cum_spike','mean']:.3f} (cum) và {dgm.loc['cov80_cumb_spike','mean']:.3f} "
                 f"(cumb, thêm nhóm theo tần suất chi cực lớn), so với danh nghĩa 0,80.")
    s_msg.append(f"- Phương pháp ước lượng p được chọn theo Brier trên val: {', '.join(f'seed {s}: {c}' for s, c in zip(seeds, chosen))}.")
    s_msg.append(f"- Chỉ số p_t (XGB + p > p*, test): AUROC {pmm.loc['XGB+risk','auroc']:.3f}, Brier skill {pmm.loc['XGB+risk','brier_skill']:.3f}, "
                 f"độ dốc hiệu chỉnh {pmm.loc['XGB+risk','cal_slope']:.2f} (1 = lý tưởng), ECE {pmm.loc['XGB+risk','ece']:.3f}; "
                 f"đối chứng B2 + p > p*: AUROC {pmm.loc['B2+risk','auroc']:.3f}, ECE {pmm.loc['B2+risk','ece']:.3f}.")
    pat_msg = []
    for p in PATTERNS:
        d = (P[(P.model == "XGB") & (P.pattern == p)].set_index("seed").f1 - P[(P.model == "B2") & (P.pattern == p)].set_index("seed").f1)
        clear = (d > 0).all() and d.mean() > 0.02
        pat_msg.append(f"  - {p}: F1 XGB − B2 = {d.mean():+.3f} ({'rõ: cả ' + str(n) + ' seed cùng dấu và > 0,02' if clear else 'chưa rõ so với nhiễu giữa các seed'}).")
    with open(f"{OUT}/RESULTS.md", "w", encoding="utf-8") as f:
        f.write(f"# Kết quả cuối cùng (test, trung bình ± độ lệch chuẩn qua {n} seed: {', '.join(map(str, seeds))})\n\n")
        f.write("## Q1 - Sai số dự báo (VND)\n\n" + tbl(q1) + "\n\n## Q2 - Chất lượng cảnh báo\n\n" + tbl(q2) + "\n\n")
        f.write("## Chỉ số cho p_t (test)\n\n" + tbl(ptab.T) + "\n\n## Chỉ số p_t theo kiểu chi tiêu (XGB + p > p*)\n\n" + tbl(ptab_pat)
                + "\n\n## Chỉ số p_t theo số ngày còn lại D (XGB + p > p*)\n\n" + tbl(ptab_D)
                + "\n\n## Kiểm chứng giả định phần dư độc lập\n\n" + tbl(dtab) + "\n\n")
        f.write("## Báo sớm ở cùng mức báo nhầm\n\nMỗi mô hình được đặt ngưỡng sao cho đúng tỉ lệ chu kỳ bình thường bị cảnh báo như bảng, rồi so tỉ lệ bắt được chu kỳ thiếu tiền "
                "và số ngày báo trước ngày cạn tiền. Cách này không phụ thuộc ngưỡng đã tune, nên thay cho chỉ số `mean_days_early` (không phân biệt được các mô hình).\n\n" + tbl(ltab) + "\n\n")
        f.write("## Ở cùng mức Precision (đúng tiêu chí của báo cáo giữa kỳ)\n\nBáo cáo giữa kỳ coi giải pháp là có ích nếu \"ở mức Precision tương đương, "
                "Recall cao hơn hoặc báo sớm hơn B1\". Với mỗi mô hình, ngưỡng thấp nhất còn đạt Precision mục tiêu được chọn trên validation; "
                "Precision validation được ghi riêng để kiểm tra quy tắc chọn ngưỡng. Ngưỡng được giữ nguyên khi đánh giá một lần trên test, "
                "nên Precision test có thể khác mục tiêu. Precision mục tiêu bằng Precision validation của B1 tại biên m đã tune, hoặc 0,7.\n\n"
                + tbl(ptab_prec) + "\n\n")
        f.write("## Theo 4 kiểu chi tiêu - MAE số dư cuối chu kỳ (VND)\n\n" + tbl(q1p) + "\n\n")
        f.write("## Kiểm định cặp theo seed\n\n" + tbl(pair.round(4).set_index("so_sánh")) + "\n\n")
        f.write("## Kết luận tính từ số liệu\n\n" + "\n".join(s_msg) + "\n- F1 theo kiểu chi tiêu, XGB so với B2:\n" + "\n".join(pat_msg) + "\n\n")
        f.write("Lưu ý: dữ liệu mô phỏng nên kết quả chỉ cho thấy tính khả thi của cách đặt bài toán, chưa khẳng định hiệu quả với người dùng thật. "
                "`mean_days_early` chỉ dùng để so giữa các mô hình vì cảnh báo thường bật ngay từ đầu chu kỳ.\n")
        f.write("\n## Quy trình và môi trường của lần chạy này\n\n"
                "So sánh ở cùng Precision chọn ngưỡng trên validation rồi giữ nguyên ngưỡng để đánh giá test một lần; Precision validation và test được báo riêng. "
                "Kết quả đánh giá phụ giữ riêng người dùng nằm ở `results/user_holdout/USER_HOLDOUT.md`.\n\n"
                f"{env_line}\n\n"
                "Runtime này khác phiên bản ghim trong `requirements.txt`; xem `THAY_DOI.md`. Các số trong báo cáo này là lần chạy mới, "
                "còn `ket_qua_tham_chieu/` được giữ nguyên làm bản đối chiếu trước khi sửa quy trình chọn ngưỡng.\n")
    import re
    txt = open(f"{OUT}/RESULTS.md", encoding="utf-8").read()
    txt = re.sub(r"(\d)\.(\d)", r"\1,\2", txt)                 # dấu phẩy thập phân cho báo cáo tiếng Việt
    txt = re.sub(r"(?m)^Runtime:.*$", env_line, txt)                 # version dùng dấu chấm, không phải số thập phân
    open(f"{OUT}/RESULTS.md", "w", encoding="utf-8").write(txt)
    print(txt)
    print("Đã lưu vào", OUT, ":", ", ".join(sorted(os.listdir(OUT))))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    main(ap.parse_args().seeds)
