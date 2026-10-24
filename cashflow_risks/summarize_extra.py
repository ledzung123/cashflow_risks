"""
summarize_extra.py - Gộp kết quả của extra_analysis.py (3 seed) thành bảng và hình cho báo cáo/slide.
  python src/summarize_extra.py        ->  results/final/Extra_*.csv, EXTRA_RESULTS.md, fig10_extra.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SEEDS = (1, 2, 3)
OUT = "results/final"
os.makedirs(OUT, exist_ok=True)
vn = lambda x, d=3: f"{x:.{d}f}".replace(".", ",")
ms = lambda m, s, d=3: f"{vn(m, d)} ± {vn(s, d)}"

M = pd.concat([pd.read_csv(f"results/models_seed{s}.csv").assign(seed=s) for s in SEEDS])
order = ["B1", "B2", "Ridge (tuyến tính)", "Random Forest", "HistGradientBoosting", "XGBoost"]
cols = [("MAE_spend", 0), ("MAE_balance", 0), ("f1", 3), ("auroc", 3), ("recall_at_far20", 3), ("lead_at_far20", 1), ("fit_seconds", 1), ("pred_ms_per_1k", 0)]
g = M.groupby("model")
mean, std = g.mean(numeric_only=True), g.std(numeric_only=True)
T = pd.DataFrame({c: [ms(mean.loc[m, c], std.loc[m, c], d) for m in order] for c, d in cols}, index=order)
T.to_csv(f"{OUT}/Extra_models.csv", encoding="utf-8-sig")

C = pd.concat([pd.read_csv(f"results/cost_seed{s}.csv").assign(seed=s) for s in SEEDS])
if "threshold_source" not in C or not C.threshold_source.eq("validation").all():
    raise ValueError("Legacy/test-tuned cost files: rerun extra_analysis analysis before summarizing")
cm = C.groupby(["model", "r"]).mean(numeric_only=True)
rs = sorted(C.r.unique())
cost = pd.DataFrame({f"r={r}": [cm.loc[(m, r), "cost_test_per_100"] for m in ["B1", "B2", "XGB (điểm biên)", "XGB + p"]] for r in rs},
                    index=["B1", "B2", "XGB (điểm biên)", "XGB + p"])
cost.loc["XGB + p, ngưỡng Bayes 1/(1+r), không tune"] = [cm.loc[("XGB + p", r), "cost_bayes_per_100"] for r in rs]
cost.round(2).to_csv(f"{OUT}/Extra_cost.csv", encoding="utf-8-sig")

B = pd.concat([pd.read_csv(f"results/boot_seed{s}.csv").assign(seed=s) for s in SEEDS])
bg = B.groupby(["so_sánh", "chỉ_số"])
BT = bg.agg(chênh_TB=("chênh_quan_sát", "mean"), độ_lệch_chuẩn_seed=("chênh_quan_sát", "std"),
            số_seed_CI_trên_0=("ci_thấp", lambda x: int(((x > 0)).sum())), số_seed_CI_dưới_0=("ci_cao", lambda x: int((x < 0).sum())))
BT.round(4).to_csv(f"{OUT}/Extra_bootstrap.csv", encoding="utf-8-sig")
B.to_csv(f"{OUT}/Extra_bootstrap_per_seed.csv", index=False, encoding="utf-8-sig")

F = pd.concat([pd.read_csv(f"results/fair_seed{s}.csv").assign(seed=s) for s in SEEDS])
FT = F.groupby(["nhóm_theo", "nhóm"]).mean(numeric_only=True).drop(columns=["n_điểm"]).round(3)
FT.to_csv(f"{OUT}/Extra_fairness.csv", encoding="utf-8-sig")

L = pd.concat([pd.read_csv(f"results/latency_seed{s}.csv").assign(seed=s) for s in SEEDS])
LT = L.groupby("mục")["giá trị"].agg(["median", "max"]).round(1)
LT.to_csv(f"{OUT}/Extra_latency.csv", encoding="utf-8-sig")

# hình: sai số dự báo theo mô hình, và chi phí theo tỉ lệ chi phí
fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
col = {"B1": "#9D9D9D", "B2": "#4C78A8", "Ridge (tuyến tính)": "#72B7B2", "Random Forest": "#B279A2", "HistGradientBoosting": "#54A24B", "XGBoost": "#F58518"}
ax[0].bar(range(6), [mean.loc[m, "MAE_spend"] / 1000 for m in order], yerr=[std.loc[m, "MAE_spend"] / 1000 for m in order],
          color=[col[m] for m in order], capsize=3)
ax[0].set_xticks(range(6)); ax[0].set_xticklabels(["B1", "B2", "Ridge", "RF", "HGB", "XGB"])
ax[0].set(title="MAE chi tiêu ngày (nghìn VND, test, 3 seed)", ylim=(90, 135))
for name, c, ls in [("B1", "#9D9D9D", "-"), ("B2", "#4C78A8", "-"), ("XGB (điểm biên)", "#F58518", "-"), ("XGB + p", "#E45756", "-")]:
    ax[1].plot(rs, [cm.loc[(name, r), "cost_test_per_100"] for r in rs], marker="o", color=c, ls=ls, label=name)
ax[1].plot(rs, [cm.loc[("XGB + p", r), "cost_bayes_per_100"] for r in rs], marker="s", ls="--", color="#E45756", label="XGB + p, ngưỡng Bayes (không tune)")
ax[1].set(xlabel="tỉ lệ chi phí bỏ sót / báo nhầm (r)", ylabel="chi phí trên 100 điểm quyết định (đơn vị = 1 báo nhầm)", title="Chi phí test, ngưỡng chọn trên validation")
ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/fig10_extra.png", dpi=130)

# kết luận tính từ số liệu
x, b2, rd, hg, rf = (mean.loc[k] for k in ["XGBoost", "B2", "Ridge (tuyến tính)", "HistGradientBoosting", "Random Forest"])
bs = BT.loc[("XGB + p - B2")]
lines = [
 f"- MAE chi tiêu ngày (nghìn VND): B2 {b2.MAE_spend/1000:.1f}, Ridge {rd.MAE_spend/1000:.1f}, Random Forest {rf.MAE_spend/1000:.1f}, HGB {hg.MAE_spend/1000:.1f}, XGBoost {x.MAE_spend/1000:.1f}. "
 f"XGBoost thấp hơn Ridge {100*(1-x.MAE_spend/rd.MAE_spend):.1f}% và gần như bằng Random Forest, HGB (chênh {100*abs(x.MAE_spend/hg.MAE_spend-1):.1f}%, {100*abs(x.MAE_spend/rf.MAE_spend-1):.1f}%).",
 f"- Bắt được chu kỳ thiếu tiền ở mức báo nhầm 20%: B2 {b2.recall_at_far20:.3f}, Ridge {rd.recall_at_far20:.3f}, XGBoost {x.recall_at_far20:.3f}. "
 f"Phần lớn lợi thế so với B1/B2 đến từ ĐẶC TRƯNG (lịch sử cá nhân, chuẩn hóa theo người) chứ không riêng từ XGBoost: mô hình tuyến tính với cùng đặc trưng đã gần bằng.",
 f"- Chi phí: với r = 2, XGB + p tốn {cost.loc['XGB + p','r=2']:.1f} so với B2 {cost.loc['B2','r=2']:.1f} (trên 100 điểm quyết định); ngưỡng Bayes 1/(1+r) cho {cost.loc['XGB + p, ngưỡng Bayes 1/(1+r), không tune','r=2']:.1f} "
 f"mà không cần tune, nhờ xác suất đã hiệu chỉnh.",
 f"- Độ trễ: 1 yêu cầu (dựng đặc trưng + dự báo, một người, ~730 dòng lịch sử) trung vị {LT.loc['1 yêu cầu: dựng đặc trưng + dự báo (ms, trung vị 40 lần)','median']:.0f} ms; "
 f"mô hình {LT.loc['kích thước file mô hình (KB)','median']:.0f} KB.",
]
with open(f"{OUT}/EXTRA_RESULTS.md", "w", encoding="utf-8") as f:
    f.write("# Bổ sung cho tiêu chí Kỹ thuật và Kết quả (test, trung bình ± độ lệch chuẩn qua 3 seed)\n\n## So XGBoost với mô hình khác (cùng đặc trưng)\n\n" + T.to_markdown() +
            "\n\n## Chi phí trên 100 điểm quyết định (báo nhầm = 1, bỏ sót = r)\n\n" + cost.round(2).to_markdown() +
            "\n\n## Bootstrap theo người: từng seed có CI95% riêng\n\nTrung bình và SD qua seed không phải CI95% gộp. Xem Extra_bootstrap_per_seed.csv.\n\n" + BT.round(4).to_markdown() +
            "\n\n## Theo nhóm (XGB + p, trung bình 3 seed)\n\n" + FT.to_markdown() + "\n\n## Độ trễ và kích thước mô hình\n\n" + LT.to_markdown() +
            "\n\n## Kết luận tính từ số liệu\n\n" + "\n".join(lines) + "\n")
print("\n".join(lines))
print("\nBOOTSTRAP (XGB + p - B2), trung bình 3 seed:"); print(bs.round(4).to_string())
print("\nTHEO NHÓM:"); print(FT[["tỉ_lệ_thiếu_tiền", "p_trung_bình", "precision", "recall", "báo_nhầm_theo_chu_kỳ", "auroc", "ece"]].to_string())
print("\nĐỘ TRỄ:"); print(LT.to_string())
print("\nBẢNG SO MÔ HÌNH:"); print(T.to_string())
