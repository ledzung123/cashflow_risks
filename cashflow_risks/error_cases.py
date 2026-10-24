"""
error_cases.py - Phân tích lỗi mức chu kỳ (báo nhầm, bỏ sót) của XGB + p > p* trên test, kèm 2 ví dụ cụ thể.
  python src/error_cases.py --seeds 1 2 3
Đầu vào (có sau run_risk.py): results/risk_points_seed*.csv, results/risk_seed*.csv
Đầu ra (results/final/): error_summary.csv, error_by_group.csv, error_cases.csv, fig11_error_cases.png, ERROR_ANALYSIS.md

Định nghĩa mức chu kỳ (như evaluate.py): báo nhầm (FP) = chu kỳ KHÔNG thiếu tiền nhưng có >= 1 cảnh báo;
bỏ sót (FN) = chu kỳ thiếu tiền nhưng không có cảnh báo nào ở các điểm quyết định còn lại.
Ví dụ chọn theo quy tắc cố định (seed đầu): mỗi loại lỗi lấy chu kỳ có p lớn nhất gần trung vị của loại đó nhất
(ví dụ điển hình, không phải ca tệ nhất).
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from make_report import vn, ms, COLORS

OUT = "results/final"
MODELS = {"XGB+risk": "XGB + p > p*", "B2": "B2 (TB cùng thứ)"}
OUTCOME = {(1, 1): "TP", (1, 0): "FN", (0, 1): "FP", (0, 0): "TN"}


def cycles(pts, model):
    """Mỗi dòng = một chu kỳ test: nhãn, có cảnh báo không, ngày cảnh báo đầu, p lớn nhất, biên cuối kỳ."""
    a = pts[f"alert_{model}"].astype(int)
    g = pts.assign(a=a, ta=pts.t.where(a == 1)).groupby(["user_id", "cycle_id"])
    c = g.agg(y=("y", "first"), alerted=("a", "max"), n_alerts=("a", "sum"), first_alert=("ta", "min"), p_max=("p_xgb", "max"),
              dip_day=("dip_day", "first"), end_balance=("end_balance", "first"), theta_c=("theta_c", "first"),
              n_points=("t", "size"), last_t=("t", "max"), pattern=("pattern", "first"),
              income_type=("income_type", "first")).reset_index()
    c["outcome"] = [OUTCOME[(y, al)] for y, al in zip(c.y, c.alerted)]
    c["end_margin"] = (c.end_balance - c.theta_c) / c.theta_c       # số dư cuối kỳ cao hơn θ bao nhiêu lần θ
    return c


def summary_row(c):
    fp, fn, tp = c[c.outcome == "FP"], c[c.outcome == "FN"], c[c.outcome == "TP"]
    neg, pos = c[c.y == 0], c[c.y == 1]
    return {
        "n_cycles": len(c), "n_FP": len(fp), "n_FN": len(fn),
        "false_alarm_rate": len(fp) / max(len(neg), 1), "miss_rate": len(fn) / max(len(pos), 1),
        "FP_near_miss_share": float((fp.end_margin < 1).mean()) if len(fp) else np.nan,
        "TN_near_miss_share": float((c[c.outcome == "TN"].end_margin < 1).mean()),
        "FP_median_end_margin": float(fp.end_margin.median()) if len(fp) else np.nan,
        "FP_median_p_max": float(fp.p_max.median()) if len(fp) else np.nan,
        "FP_median_first_alert": float(fp.first_alert.median()) if len(fp) else np.nan,
        "FP_median_alert_share": float((fp.n_alerts / fp.n_points).median()) if len(fp) else np.nan,
        "FN_median_p_max": float(fn.p_max.median()) if len(fn) else np.nan,
        "FN_median_end_margin": float(fn.end_margin.median()) if len(fn) else np.nan,
        "TP_median_end_margin": float(tp.end_margin.median()) if len(tp) else np.nan,
        "FN_median_n_points": float(fn.n_points.median()) if len(fn) else np.nan,
        "TP_median_n_points": float(tp.n_points.median()) if len(tp) else np.nan,
    }


def pick(c, outcome):
    """Chu kỳ có p_max gần trung vị của nhóm lỗi nhất (hòa thì lấy theo thứ tự user, chu kỳ)."""
    e = c[c.outcome == outcome].sort_values(["user_id", "cycle_id"])
    return e.iloc[int(np.argmin(np.abs(e.p_max.to_numpy() - e.p_max.median())))]


def main(seeds):
    os.makedirs(OUT, exist_ok=True)
    rows, groups, cyc0 = [], [], None
    for s in seeds:
        pts = pd.read_csv(f"results/risk_points_seed{s}.csv")
        for m in MODELS:
            c = cycles(pts, m)
            rows.append({"seed": s, "model": m, **summary_row(c)})
            if m == "XGB+risk":
                if cyc0 is None:
                    cyc0, pts0 = c, pts
                for col in ("pattern", "income_type"):
                    for k, gg in c.groupby(col):
                        groups.append({"seed": s, "group": col, "value": k,
                                       "false_alarm_rate": (gg.outcome == "FP").sum() / max((gg.y == 0).sum(), 1),
                                       "miss_rate": (gg.outcome == "FN").sum() / max((gg.y == 1).sum(), 1),
                                       "pos_rate": gg.y.mean()})
    summ = pd.DataFrame(rows)
    num = [c for c in summ.columns if c not in ("seed", "model")]
    agg = summ.groupby("model", sort=False)[num].agg(["mean", "std"])
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    agg.round(4).to_csv(f"{OUT}/error_summary.csv")
    grp = pd.DataFrame(groups).groupby(["group", "value"])[["pos_rate", "false_alarm_rate", "miss_rate"]].agg(["mean", "std"])
    grp.columns = [f"{a}_{b}" for a, b in grp.columns]
    grp.round(4).to_csv(f"{OUT}/error_by_group.csv")

    # Hai ví dụ (seed đầu)
    s0 = seeds[0]
    pstar = float(pd.read_csv(f"results/risk_seed{s0}.csv").set_index("model").loc["XGB+risk", "p_star"])
    cases = {"FP": pick(cyc0, "FP"), "FN": pick(cyc0, "FN")}
    ex = []
    for kind, r in cases.items():
        g = pts0[(pts0.user_id == r.user_id) & (pts0.cycle_id == r.cycle_id)].sort_values("t")
        ex.append(g.assign(case=kind, seed=s0, p_star=pstar))
    ex = pd.concat(ex, ignore_index=True)
    ex.to_csv(f"{OUT}/error_cases.csv", index=False)

    fig, ax = plt.subplots(2, 2, figsize=(12, 6.5), sharex="col")
    titles = {"FP": "Báo nhầm: chu kỳ KHÔNG thiếu tiền nhưng bị cảnh báo",
              "FN": "Bỏ sót: chu kỳ thiếu tiền nhưng không có cảnh báo"}
    for j, kind in enumerate(("FP", "FN")):
        g, r = ex[ex.case == kind], cases[kind]
        ax[0, j].plot(g.t, g.p_xgb, "o-", color=COLORS["XGB+risk"], label="p (XGB + risk)")
        ax[0, j].axhline(pstar, color="k", ls="--", lw=1, label=f"p* = {pstar:.2f}")
        ta = g.t[g["alert_XGB+risk"] == 1]
        ax[0, j].scatter(ta, np.full(len(ta), 1.04), marker="|", s=90, color=COLORS["XGB+risk"], label="ngày cảnh báo")
        ax[0, j].set(ylim=(-0.03, 1.1), title=f"{titles[kind]}\nuser {r.user_id}, chu kỳ {r.cycle_id}, kiểu {r.pattern}")
        ax[1, j].plot(g.t, g.balance_t / 1e6, "o-", color="#4C78A8", label="số dư tại điểm quyết định")
        ax[1, j].axhline(r.theta_c / 1e6, color="gray", ls="--", label="θ")
        ax[1, j].scatter([g.t.max() + g.D.iloc[-1]], [r.end_balance / 1e6], marker="*", s=140, color="k",
                         label=f"số dư cuối kỳ thật ({vn(r.end_balance / 1e6, 2)} tr)")
        if not np.isnan(r.dip_day):
            for k in (0, 1):
                ax[k, j].axvline(r.dip_day, color="red", ls=":", label="ngày cạn thực tế" if k == 1 else None)
        ax[1, j].set(xlabel="ngày trong chu kỳ", ylabel="triệu VND")
        ax[1, j].legend(fontsize=8)
    ax[0, 0].set_ylabel("xác suất p"); ax[0, 0].legend(fontsize=8, loc="lower left")
    fig.suptitle(f"Ví dụ lỗi điển hình (seed {s0}; chọn theo quy tắc cố định: p lớn nhất gần trung vị của loại lỗi)")
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(f"{OUT}/fig11_error_cases.png", dpi=130); plt.close(fig)

    write_md(agg, grp, cases, pstar, s0, seeds)
    print(f"Đã lưu {OUT}/error_summary.csv, error_by_group.csv, error_cases.csv, fig11_error_cases.png, ERROR_ANALYSIS.md")


def write_md(agg, grp, cases, pstar, s0, seeds):
    x = agg.loc["XGB+risk"]
    M = lambda k, d=3: ms(x[f"{k}_mean"], x[f"{k}_std"], d)
    t1 = pd.DataFrame({
        MODELS[m]: {"tỉ lệ chu kỳ bình thường bị báo nhầm": ms(agg.loc[m, "false_alarm_rate_mean"], agg.loc[m, "false_alarm_rate_std"]),
                    "tỉ lệ chu kỳ thiếu tiền bị bỏ sót": ms(agg.loc[m, "miss_rate_mean"], agg.loc[m, "miss_rate_std"]),
                    "trong số báo nhầm: tỉ lệ 'suýt thiếu' (cuối kỳ dư < 1θ)": ms(agg.loc[m, "FP_near_miss_share_mean"], agg.loc[m, "FP_near_miss_share_std"]),
                    "trong số chu kỳ bình thường không bị báo: tỉ lệ 'suýt thiếu'": ms(agg.loc[m, "TN_near_miss_share_mean"], agg.loc[m, "TN_near_miss_share_std"]),
                    "trong số báo nhầm: trung vị ngày cảnh báo đầu tiên": ms(agg.loc[m, "FP_median_first_alert_mean"], agg.loc[m, "FP_median_first_alert_std"], 1),
                    "trong số báo nhầm: trung vị tỉ lệ ngày bị cảnh báo": ms(agg.loc[m, "FP_median_alert_share_mean"], agg.loc[m, "FP_median_alert_share_std"]),
                    "bỏ sót: trung vị (số dư cuối kỳ − θ)/θ": ms(agg.loc[m, "FN_median_end_margin_mean"], agg.loc[m, "FN_median_end_margin_std"], 2),
                    "bắt được: trung vị (số dư cuối kỳ − θ)/θ": ms(agg.loc[m, "TP_median_end_margin_mean"], agg.loc[m, "TP_median_end_margin_std"], 2),
                    "trung vị số điểm quyết định của chu kỳ bị bỏ sót": ms(agg.loc[m, "FN_median_n_points_mean"], agg.loc[m, "FN_median_n_points_std"], 1),
                    "trung vị số điểm quyết định của chu kỳ bắt được": ms(agg.loc[m, "TP_median_n_points_mean"], agg.loc[m, "TP_median_n_points_std"], 1)}
        for m in MODELS})
    gtab = grp.apply(lambda r: pd.Series({"tỉ lệ thiếu tiền": ms(r.pos_rate_mean, r.pos_rate_std),
                                          "báo nhầm": ms(r.false_alarm_rate_mean, r.false_alarm_rate_std),
                                          "bỏ sót": ms(r.miss_rate_mean, r.miss_rate_std)}), axis=1)
    gtab.index = [f"{a} = {b}" for a, b in gtab.index]
    fp, fn = cases["FP"], cases["FN"]
    worst_fa = grp.xs("pattern")["false_alarm_rate_mean"].idxmax()
    worst_miss = grp.xs("pattern")["miss_rate_mean"].idxmax()
    lines = [
        f"# Phân tích lỗi của cảnh báo (XGB + p > p*, test, {len(seeds)} seed)",
        "",
        "Mức chu kỳ: **báo nhầm** = chu kỳ không thiếu tiền nhưng có ít nhất 1 cảnh báo; **bỏ sót** = chu kỳ thiếu tiền nhưng "
        "không có cảnh báo nào ở các điểm quyết định còn lại (điểm có số dư đã dưới θ bị loại theo SPEC mục 2). "
        "'Suýt thiếu' = số dư cuối kỳ cao hơn θ chưa tới 1θ (chưa tới 1 ngày chi tiêu trung bình). Trung bình ± độ lệch chuẩn qua các seed.",
        "",
        "## Tổng quan (so với B2)",
        "", t1.to_markdown(), "",
        "## Theo kiểu chi tiêu và loại thu nhập (XGB + p > p*)",
        "", gtab.to_markdown(), "",
        f"## Hai ví dụ điển hình (seed {s0}, p* = {vn(pstar, 2)}; hình `fig11_error_cases.png`, số liệu `error_cases.csv`)",
        "",
        f"- **Báo nhầm** - user {fp.user_id}, chu kỳ {fp.cycle_id}, kiểu {fp.pattern}: cảnh báo đầu tiên ngày {int(fp.first_alert)}, "
        f"p lớn nhất {vn(fp.p_max, 2)}; số dư cuối kỳ thật {vn(fp.end_balance / 1e6, 2)} triệu so với θ = {vn(fp.theta_c / 1e6, 2)} triệu "
        f"(cao hơn θ {vn(fp.end_margin, 2)} lần θ).",
        f"- **Bỏ sót** - user {fn.user_id}, chu kỳ {fn.cycle_id}, kiểu {fn.pattern}: p lớn nhất chỉ {vn(fn.p_max, 2)} (< p*); "
        f"số điểm quyết định {int(fn.n_points)}, ngày cạn thực tế {int(fn.dip_day)}; số dư cuối kỳ {vn(fn.end_balance / 1e6, 2)} triệu "
        f"so với θ = {vn(fn.theta_c / 1e6, 2)} triệu.",
        "",
        "## Nhận xét tính từ số liệu",
        "",
        f"- Báo nhầm: {M('false_alarm_rate')} chu kỳ bình thường bị cảnh báo ít nhất một lần; trong các chu kỳ đó {M('FP_near_miss_share')} "
        f"là 'suýt thiếu', so với {M('TN_near_miss_share')} ở các chu kỳ bình thường không bị cảnh báo. "
        f"Trung vị ngày cảnh báo đầu tiên là ngày {M('FP_median_first_alert', 1)}; trung vị tỉ lệ ngày bị cảnh báo trong chu kỳ "
        f"báo nhầm là {M('FP_median_alert_share')}.",
        f"- Bỏ sót: {M('miss_rate')} chu kỳ thiếu tiền; p lớn nhất trung vị của các chu kỳ này là {M('FN_median_p_max', 2)}; "
        f"trung vị (số dư cuối kỳ − θ)/θ là {M('FN_median_end_margin', 2)}, so với {M('TP_median_end_margin', 2)} ở chu kỳ bắt được; "
        f"trung vị số điểm quyết định {M('FN_median_n_points', 1)} so với {M('TP_median_n_points', 1)}.",
        f"- Kiểu chi tiêu báo nhầm nhiều nhất: {worst_fa}; bỏ sót nhiều nhất: {worst_miss}.",
        "",
        "Ví dụ chọn theo quy tắc cố định để tránh chọn ca có lợi; không phải ca tệ nhất. Dữ liệu mô phỏng.",
    ]
    open(f"{OUT}/ERROR_ANALYSIS.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    main(ap.parse_args().seeds)
