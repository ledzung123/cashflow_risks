"""Đánh giá dữ liệu/mô hình và tạo hình dùng trong báo cáo."""

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, roc_curve

from config import DATA_DIR, END_DATE, FIGURES_DIR, RESULTS_DIR, START_DATE


def save_label_distribution(cycles: pd.DataFrame) -> None:
    counts = cycles["shortfall"].value_counts().reindex([0, 1], fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(["Không thiếu tiền", "Thiếu tiền"], counts.values)
    ax.set_title("Phân bố nhãn thiếu tiền theo chu kỳ")
    ax.set_ylabel("Số chu kỳ")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:,}\n({value / counts.sum():.1%})", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "01_label_distribution.png", dpi=180)
    plt.close(fig)


def save_shortfall_by_category(cycles: pd.DataFrame) -> None:
    pattern_order = ["đều", "dồn đầu chu kỳ", "tăng cuối tuần", "chi lớn bất thường"]
    by_pattern = cycles.groupby("pattern", observed=False)["shortfall"].mean().reindex(pattern_order)
    fig, ax = plt.subplots(figsize=(8.5, 4.7))
    bars = ax.bar(by_pattern.index, by_pattern.values * 100)
    ax.set_title("Tỷ lệ chu kỳ thiếu tiền theo kiểu chi tiêu")
    ax.set_ylabel("Chu kỳ thiếu tiền (%)")
    ax.set_ylim(0, max(40, float(by_pattern.max() * 115)))
    ax.tick_params(axis="x", rotation=10)
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, by_pattern.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.1%}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "02_shortfall_by_pattern.png", dpi=180)
    plt.close(fig)

    income_order = ["trợ cấp đầu tháng", "lương ngày 25"]
    by_income = cycles.groupby("income_type", observed=False)["shortfall"].mean().reindex(income_order)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bars = ax.bar(by_income.index, by_income.values * 100)
    ax.set_title("Tỷ lệ chu kỳ thiếu tiền theo chu kỳ thu nhập")
    ax.set_ylabel("Chu kỳ thiếu tiền (%)")
    ax.set_ylim(0, max(40, float(by_income.max() * 115)))
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, by_income.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.1%}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "03_shortfall_by_income_type.png", dpi=180)
    plt.close(fig)


def save_model_comparison(metrics: pd.DataFrame) -> None:
    selected = metrics.set_index("model")[["f1", "recall", "roc_auc"]]
    ax = selected.plot(kind="bar", figsize=(10, 5.2), ylim=(0, 1), rot=12)
    ax.set_title("So sánh mô hình trên tập test")
    ax.set_ylabel("Điểm số (0–1)")
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(["F1", "Recall", "ROC-AUC"], loc="lower right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "04_model_comparison.png", dpi=180)
    plt.close()


def save_roc_curve(predictions: pd.DataFrame, summary: dict) -> None:
    from sklearn.metrics import roc_auc_score

    y_true = predictions["y_true"].astype(int).to_numpy()
    score_columns = [
        ("B1 - Quy tắc chi tiêu", "score_B1_rule"),
        ("B2 - Logistic Regression", "prob_B2_logistic"),
        (f"Mô hình chính - {summary['model_family']}", "prob_main_model"),
    ]
    fig, ax = plt.subplots(figsize=(7, 6))
    for label, column in score_columns:
        scores = predictions[column].astype(float).to_numpy()
        fpr, tpr, _ = roc_curve(y_true, scores)
        auc = roc_auc_score(y_true, scores)
        ax.plot(fpr, tpr, label=f"{label} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1, label="Ngẫu nhiên (AUC=0.5)")
    ax.set_title("Đường ROC trên tập test")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "05_roc_curve.png", dpi=180)
    plt.close(fig)


def save_feature_importance() -> None:
    importance = pd.read_csv(RESULTS_DIR / "feature_importance.csv").head(12).sort_values("importance")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(importance["feature"], importance["importance"])
    ax.set_title("12 đặc trưng quan trọng nhất của mô hình chính")
    ax.set_xlabel("Mức độ quan trọng")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "06_feature_importance.png", dpi=180)
    plt.close(fig)


def save_confusion_matrix(predictions: pd.DataFrame, summary: dict) -> None:
    y_true = predictions["y_true"].astype(int).to_numpy()
    y_pred = predictions["pred_main_model"].astype(int).to_numpy()
    fig, ax = plt.subplots(figsize=(5.5, 4.8))
    ConfusionMatrixDisplay.from_predictions(
        y_true, y_pred,
        labels=[0, 1],
        display_labels=["Không thiếu", "Thiếu tiền"],
        cmap="Blues",
        values_format="d",
        ax=ax,
        colorbar=False,
    )
    ax.set_title(f"Ma trận nhầm lẫn: {summary['model_family']}")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "07_confusion_matrix.png", dpi=180)
    plt.close(fig)


def save_balance_examples(daily: pd.DataFrame, users: pd.DataFrame) -> None:
    pattern_order = ["đều", "dồn đầu chu kỳ", "tăng cuối tuần", "chi lớn bất thường"]
    sample_users = []
    for pattern in pattern_order:
        candidates = users.loc[users["pattern"] == pattern, "user_id"]
        if len(candidates):
            sample_users.append((pattern, candidates.iloc[0]))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for pattern, user_id in sample_users:
        one_user = daily.loc[daily["user_id"] == user_id].copy()
        ax.plot(one_user["date"], one_user["balance"] / 1_000_000, label=f"{pattern} ({user_id})", linewidth=1.2)
    ax.axhline(0, color="black", linewidth=1, linestyle="--")
    ax.set_title("Ví dụ diễn biến số dư của 4 hồ sơ giả lập")
    ax.set_ylabel("Số dư cuối ngày (triệu đồng)")
    ax.set_xlabel("Ngày")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "08_balance_examples.png", dpi=180)
    plt.close(fig)


def save_monthly_summary(daily: pd.DataFrame) -> pd.DataFrame:
    monthly = daily.copy()
    monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
    summary = monthly.groupby("month").agg(
        total_spend_vnd=("spend", "sum"),
        total_income_vnd=("income", "sum"),
        average_end_balance_vnd=("balance", "mean"),
        share_negative_balance=("balance", lambda s: float((s < 0).mean())),
    ).reset_index()
    summary.to_csv(RESULTS_DIR / "monthly_summary.csv", index=False, encoding="utf-8-sig")

    plot_data = summary.melt(
        id_vars="month",
        value_vars=["total_spend_vnd", "total_income_vnd"],
        var_name="cashflow_type",
        value_name="amount_vnd",
    )
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for label, group in plot_data.groupby("cashflow_type"):
        pretty = "Tổng chi" if label == "total_spend_vnd" else "Tổng thu"
        ax.plot(group["month"], group["amount_vnd"] / 1_000_000_000, marker="o", markersize=3, label=pretty)
    ax.set_title("Tổng thu nhập và chi tiêu theo tháng")
    ax.set_ylabel("Tỷ đồng")
    ax.set_xlabel("Tháng")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "09_monthly_income_spend.png", dpi=180)
    plt.close(fig)
    return summary


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cycles = pd.read_csv(DATA_DIR / "cycle_dataset.csv", parse_dates=["cycle_start_date", "cycle_end_date"])
    daily = pd.read_csv(DATA_DIR / "daily.csv", parse_dates=["date"])
    users = pd.read_csv(DATA_DIR / "users.csv")
    metrics = pd.read_csv(RESULTS_DIR / "metrics.csv")
    predictions = pd.read_csv(RESULTS_DIR / "test_predictions.csv")
    model_summary = json.loads((RESULTS_DIR / "model_summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((DATA_DIR / "generation_metadata.json").read_text(encoding="utf-8"))

    save_label_distribution(cycles)
    save_shortfall_by_category(cycles)
    save_model_comparison(metrics)
    save_roc_curve(predictions, model_summary)
    save_feature_importance()
    save_confusion_matrix(predictions, model_summary)
    save_balance_examples(daily, users)
    monthly_summary = save_monthly_summary(daily)

    data_summary = {
        "n_users": int(users["user_id"].nunique()),
        "daily_rows": int(len(daily)),
        "daily_dates": int(daily["date"].nunique()),
        "daily_start": str(daily["date"].min().date()),
        "daily_end": str(daily["date"].max().date()),
        "cycle_samples": int(len(cycles)),
        "cycle_users": int(cycles["user_id"].nunique()),
        "cycle_shortfall_count": int(cycles["shortfall"].sum()),
        "cycle_shortfall_rate": float(cycles["shortfall"].mean()),
        "daily_missing_values": int(daily.isna().sum().sum()),
        "daily_negative_spend_count": int((daily["spend"] < 0).sum()),
        "income_event_count": int((daily["income"] > 0).sum()),
        "target_shortfall_rate": float(metadata["target_shortfall_rate"]),
        "spend_scale": float(metadata["spend_scale"]),
        "test_predictions": int(len(predictions)),
        "monthly_rows": int(len(monthly_summary)),
        "start_date_config": START_DATE,
        "end_date_config": END_DATE,
        "synthetic_data": True,
    }
    (RESULTS_DIR / "data_summary.json").write_text(
        json.dumps(data_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Đã tạo {len(list(FIGURES_DIR.glob('*.png')))} hình trong {FIGURES_DIR}")
    print(f"Tỷ lệ nhãn thiếu tiền của cycle_dataset.csv: {cycles['shortfall'].mean():.2%}")


if __name__ == "__main__":
    main()
