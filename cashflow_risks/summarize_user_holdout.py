"""Summarize the disjoint-user generalization diagnostic."""
import os

import pandas as pd


def mean_sd(df, cols):
    g = df.groupby("model")[cols].agg(["mean", "std"])
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    return g


def fmt(x, digits=3):
    if pd.isna(x):
        return "—"
    return f"{x:.{digits}f}".replace(".", ",")


def main(seeds=(1, 2, 3)):
    root = "results/user_holdout"
    q1 = pd.concat([pd.read_csv(f"{root}/q1_seed{s}.csv") for s in seeds], ignore_index=True)
    q2 = pd.concat([pd.read_csv(f"{root}/q2_seed{s}.csv") for s in seeds], ignore_index=True)
    prec = pd.concat([pd.read_csv(f"{root}/precision_seed{s}.csv") for s in seeds], ignore_index=True)
    sizes = pd.concat([pd.read_csv(f"{root}/split_sizes_seed{s}.csv") for s in seeds], ignore_index=True)
    q1m = mean_sd(q1, ["MAE_spend", "RMSE_spend", "MAE_balance", "RMSE_balance"])
    q2m = mean_sd(q2, ["precision", "recall", "f1", "cycle_recall", "cycle_false_alarm"])
    p = prec[(prec.muc == "B1") & prec.reachable.astype(bool)]
    pm = mean_sd(p, ["precision_target", "precision_val", "precision", "recall", "cycle_recall", "lead_mean_all"])
    q1m.to_csv(f"{root}/q1_mean.csv")
    q2m.to_csv(f"{root}/q2_mean.csv")
    pm.to_csv(f"{root}/precision_mean.csv")

    lines = [
        "# Đánh giá phụ trên người dùng giữ riêng",
        "",
        f"Kết quả trung bình ± độ lệch chuẩn qua {len(seeds)} seed. Đây là phép thử tổng quát hóa bổ sung; đánh giá chính theo thời gian vẫn nằm trong `results/final/RESULTS.md`.",
        "",
        "## Cách chia",
        "",
        "Mỗi người chỉ thuộc một vai trò. Nhóm train dùng chu kỳ train, nhóm calib dùng chu kỳ calib, nhóm val dùng chu kỳ val và nhóm test dùng chu kỳ test. Các vai trò người dùng không giao nhau; việc tạo đặc trưng cho một người vẫn dùng lịch sử giao dịch trước thời điểm dự báo của chính người đó.",
        "",
        "```",
        sizes.drop(columns="selected_risk_method").groupby("seed").mean(numeric_only=True).round(1).to_string(),
        "```",
        "",
        "## Sai số dự báo trên nhóm test chưa dùng ở các vai trò khác (VND)",
        "",
        "| Mô hình | MAE chi tiêu | RMSE chi tiêu | MAE số dư | RMSE số dư |",
        "|---|---:|---:|---:|---:|",
    ]
    for m, r in q1m.iterrows():
        lines.append(f"| {m} | {fmt(r.MAE_spend_mean, 0)} ± {fmt(r.MAE_spend_std, 0)} | {fmt(r.RMSE_spend_mean, 0)} ± {fmt(r.RMSE_spend_std, 0)} | {fmt(r.MAE_balance_mean, 0)} ± {fmt(r.MAE_balance_std, 0)} | {fmt(r.RMSE_balance_mean, 0)} ± {fmt(r.RMSE_balance_std, 0)} |")
    lines += ["", "## Chất lượng cảnh báo trên nhóm test giữ riêng", "", "| Mô hình | Precision | Recall | F1 | Cycle recall | False alarm theo chu kỳ |", "|---|---:|---:|---:|---:|---:|"]
    for m, r in q2m.iterrows():
        lines.append(f"| {m} | {fmt(r.precision_mean)} ± {fmt(r.precision_std)} | {fmt(r.recall_mean)} ± {fmt(r.recall_std)} | {fmt(r.f1_mean)} ± {fmt(r.f1_std)} | {fmt(r.cycle_recall_mean)} ± {fmt(r.cycle_recall_std)} | {fmt(r.cycle_false_alarm_mean)} ± {fmt(r.cycle_false_alarm_std)} |")
    lines += ["", "## So sánh ở Precision mục tiêu của B1", "", "Ngưỡng được chọn trên validation của nhóm người dùng riêng cho vai trò val, sau đó giữ nguyên trên nhóm test. Precision validation và test được báo riêng.", "", "| Mô hình | Precision mục tiêu | Precision val | Precision test | Recall test | Cycle recall test | Báo sớm (ngày, bỏ sót = 0) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for m, r in pm.iterrows():
        lines.append(f"| {m} | {fmt(r.precision_target_mean)} ± {fmt(r.precision_target_std)} | {fmt(r.precision_val_mean)} ± {fmt(r.precision_val_std)} | {fmt(r.precision_mean)} ± {fmt(r.precision_std)} | {fmt(r.recall_mean)} ± {fmt(r.recall_std)} | {fmt(r.cycle_recall_mean)} ± {fmt(r.cycle_recall_std)} | {fmt(r.lead_mean_all_mean, 1)} ± {fmt(r.lead_mean_all_std, 1)} |")
    lines += ["", "## Giới hạn", "", "Đây vẫn là dữ liệu mô phỏng. Phép thử giữ riêng người dùng chỉ cho biết khả năng chuyển sang người mô phỏng khác trong cùng simulator; nó không thay thế kiểm định với dữ liệu giao dịch thật. Chỉ có 60 người mô phỏng trong mỗi nhóm test seed, nên xem đây là đánh giá phụ và đọc cùng độ lệch giữa các seed.", ""]
    with open(f"{root}/USER_HOLDOUT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Đã lưu {root}/USER_HOLDOUT.md, q1_mean.csv, q2_mean.csv, precision_mean.csv")


if __name__ == "__main__":
    main()
