"""Figures for the validation-selected policy evaluation and feature ablations."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def main():
    root = Path("results/upgrades/summary")
    table = pd.read_csv(root / "policies_mean.csv")
    n_seeds = pd.read_csv(root / "policies_per_seed.csv").seed.nunique()
    colors = {"B1": "#777777", "B2": "#277DA1", "XGB": "#F8961E", "XGB+risk": "#C83E4D"}
    markers = {"f1_val": "o", "far20_val": "s", "cost_r2_val": "^"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7), sharey=True)
    for ax, mode in zip(axes, ("time", "user_holdout")):
        sub = table[table["mode"] == mode]
        for model, color in colors.items():
            for policy, marker in markers.items():
                row = sub[(sub.model == model) & (sub.policy == policy)].iloc[0]
                ax.scatter(100 * row.test_cycle_false_alarm, 100 * row.test_cycle_recall,
                           marker=marker, color=color, s=65)
        ax.axvline(20, color="#999999", linestyle="--", linewidth=1)
        ax.set(title={"time": "Theo thời gian", "user_holdout": "Giữ riêng người dùng"}[mode],
               xlabel="Chu kỳ bình thường bị cảnh báo nhầm trên test (%)", ylim=(0, 102))
        ax.grid(alpha=.18)
    axes[0].set_ylabel("Chu kỳ thiếu tiền bắt được trên test (%)")
    handles = [plt.Line2D([], [], color=c, marker="o", linestyle="", label=m) for m, c in colors.items()]
    handles += [plt.Line2D([], [], color="black", marker=marker, linestyle="", label=label)
                for (policy, marker), label in zip(markers.items(), ("Tối đa F1 val", "FAR20 val", "Chi phí r=2 val"))]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False)
    fig.suptitle(f"Ngưỡng chọn trên validation, giữ cố định khi đánh giá test — trung bình {n_seeds} seed", fontsize=11)
    fig.tight_layout(rect=(0, .15, 1, .94))
    fig.savefig(root / "fig_policy_tradeoff.png", dpi=160)
    plt.close(fig)

    ab = pd.read_csv(root / "ablation_per_seed.csv")
    order = ["full", "no_personal_history", "no_calendar_recent"]
    means = ab.groupby("variant")[["MAE_spend", "MAE_balance"]].mean().loc[order]
    sd = ab.groupby("variant")[["MAE_spend", "MAE_balance"]].std().loc[order]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.7))
    for ax, metric, title in zip(axes, means.columns, ("Chi tiêu ngày", "Số dư cuối chu kỳ")):
        ax.bar(range(3), means[metric] / 1000, yerr=sd[metric] / 1000, capsize=5,
               color=["#277DA1", "#F8961E", "#C83E4D"])
        ax.set_xticks(range(3), ["Đầy đủ", "Bỏ lịch sử\nchu kỳ cá nhân", "Bỏ lịch/thống kê\ngần đây"])
        ax.set(title=title, ylabel="MAE (nghìn VND)")
        ax.grid(axis="y", alpha=.18)
    fig.suptitle(f"Ablation trên cùng cách chia theo thời gian — trung bình ± SD của {n_seeds} seed", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(root / "fig_ablation.png", dpi=160)
    plt.close(fig)
    print("Saved fig_policy_tradeoff.png and fig_ablation.png")


if __name__ == "__main__":
    main()
