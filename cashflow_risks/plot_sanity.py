"""
plot_sanity.py - Vẽ hình kiểm tra (sanity) TỪ FILE DỮ LIỆU ĐÃ SINH (data/daily.csv). Người 1.
  python src/plot_sanity.py --csv data/daily.csv --out results/sanity_v1.png
Sáu ô: (1) dồn đầu chu kỳ, (2) cuối tuần, (3) đuôi dài của khoản chi lớn, (4) mức chi VND theo loại thu nhập,
       (5) tỉ lệ chu kỳ thiếu tiền theo chu kỳ (kiểm tra trôi dạt giữa train/val/test), (6) số dư/thu nhập theo ngày.
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
import simulate

COL = {"even": "#4C78A8", "front": "#F58518", "weekend": "#54A24B", "spike": "#E45756"}
PATTERNS = ["even", "front", "weekend", "spike"]


def main(csv, out):
    df = pd.read_csv(csv)
    df["wd"] = pd.to_datetime(df.date).dt.weekday
    df["rel"] = df.spend / df.groupby("user_id").spend.transform("mean")
    lab = simulate.quick_labels(df)
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))

    for p in PATTERNS:
        g = df[df.pattern == p]
        s = g[g.day_in_cycle <= 28].groupby("day_in_cycle").rel.mean()
        ax[0, 0].plot(s.index, s.values, color=COL[p], label=p, lw=2)
        w = g.groupby("wd").rel.mean()
        ax[0, 1].plot(["T2", "T3", "T4", "T5", "T6", "T7", "CN"], w.values, color=COL[p], marker="o", label=p, lw=2)
        h, edges = np.histogram(g.rel[g.rel > 0], bins=np.linspace(0, 8, 41))
        ax[0, 2].step(edges[:-1], h / h.sum(), where="post", color=COL[p], label=p, lw=1.8)
    ax[0, 0].set(title="(1) Chi tiêu tương đối theo ngày trong chu kỳ", xlabel="day_in_cycle", ylabel="1.0 = TB của người đó")
    ax[0, 1].set(title="(2) Chi tiêu tương đối theo thứ trong tuần")
    ax[0, 2].set(title="(3) Phân phối chi tiêu ngày / TB người đó (trục y log)", xlabel="spend / TB", yscale="log")
    for a in (ax[0, 0], ax[0, 1], ax[0, 2]):
        a.legend()

    for it, c in [("allowance_1st", "#72B7B2"), ("salary_25", "#B279A2")]:
        v = df.spend[(df.income_type == it) & (df.spend > 0)]
        ax[1, 0].hist(np.log10(v), bins=60, alpha=0.6, color=c,
                      label=f"{it} (trung vị {int(v.median()/1000)}k)")
    ax[1, 0].set(title="(4) Chi tiêu ngày (VND, log10) theo loại thu nhập", xlabel="log10(VND/ngày)")
    ax[1, 0].set_xticks([4, 4.5, 5, 5.5, 6]); ax[1, 0].set_xticklabels(["10k", "32k", "100k", "316k", "1M"])
    ax[1, 0].legend()

    r = lab.groupby("cycle_id").y_cycle.agg(["mean", "size"])
    se = np.sqrt(r["mean"] * (1 - r["mean"]) / r["size"])
    ax[1, 1].axhspan(0.15, 0.35, color="#DDDDDD", alpha=0.6, label="mục tiêu 15–35%")
    ax[1, 1].errorbar(r.index, r["mean"], yerr=1.96 * se, fmt="o-", color="k", capsize=3, label="tất cả (±95%)")
    for lo, hi, name in [(0.5, 11.5, "train"), (11.5, 15.5, "calib"), (15.5, 19.5, "val"), (19.5, 23.5, "test")]:
        ax[1, 1].text((lo + hi) / 2, 0.02, name, ha="center", color="gray")
        ax[1, 1].axvline(hi, color="gray", ls=":")
    ax[1, 1].set(title="(5) Tỉ lệ chu kỳ thiếu tiền theo chu kỳ", xlabel="cycle_id", ylim=(0, 0.6))
    ax[1, 1].legend(loc="upper right")

    df["bal_rel"] = df.balance / df.groupby(["user_id", "cycle_id"]).income.transform("max")
    for p in PATTERNS:
        g = df[(df.pattern == p) & (df.day_in_cycle <= 28) & (df.cycle_id >= 1)]
        s = g.groupby("day_in_cycle").bal_rel.mean()
        ax[1, 2].plot(s.index, s.values, color=COL[p], label=p, lw=2)
    ax[1, 2].axhline(0, color="k", lw=0.6)
    ax[1, 2].set(title="(6) Số dư / thu nhập theo ngày (TB, từ chu kỳ 1)", xlabel="day_in_cycle")
    ax[1, 2].legend()

    fig.suptitle(f"Kiểm tra dữ liệu mô phỏng: {df.user_id.nunique()} người × {df.cycle_id.nunique()} chu kỳ, {len(df):,} dòng", y=1.0)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig.savefig(out, dpi=110, bbox_inches="tight")

    print("Tỉ lệ chu kỳ thiếu tiền: tổng %.1f%% | train %.1f%% | val %.1f%% | test %.1f%%" % (
        100 * lab.y_cycle.mean(), *[100 * lab[lab.split == s].y_cycle.mean() for s in ("train", "val", "test")]))
    print("Theo kiểu:", lab.groupby("pattern").y_cycle.mean().round(3).to_dict())
    print("Chi tiêu ngày trung vị (VND):", df.groupby("income_type").spend.median().astype(int).to_dict())
    print("Đã lưu", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/daily.csv")
    ap.add_argument("--out", default="results/sanity_v1.png")
    a = ap.parse_args()
    main(a.csv, a.out)
