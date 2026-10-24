"""
supplement.py - Hai phân tích bổ sung cho thang điểm cuối kỳ (test, 3 seed):
  1. Mất cân bằng lớp: tỉ lệ thiếu tiền ở từng tập, và cảnh báo XGB + p với các cách đặt ngưỡng khác nhau
     (p* chọn trên val theo F1 = cách đang dùng; 0,5 = mặc định của bộ phân loại; tỉ lệ nền của tập calib).
     Mô hình chính là hồi quy chi tiêu nên không có "trọng số lớp"; mất cân bằng chỉ tác động ở bước đặt ngưỡng.
  2. Công bằng theo mức thu nhập: chia 3 mức (thấp / vừa / cao) TRONG từng loại thu nhập (trợ cấp 3-5 triệu, lương 7-15 triệu khác hẳn nhau),
     so tỉ lệ bỏ sót, báo nhầm, AUROC, ECE giữa 6 nhóm.
  python src/supplement.py --seeds 1 2 3
Đầu vào: results/risk_points_seed*.csv, results/risk_seed*.csv; mô phỏng lại dữ liệu (cùng seed) để lấy tỉ lệ nền và thu nhập từng người.
Đầu ra (results/final/): class_balance.csv, imbalance_table.csv, fairness_income.csv, SUPPLEMENT.md
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(__file__))
import simulate
from labels import prepare_df, make_dp
from evaluate import evaluate
from risk import ece, brier
from make_report import vn, ms

OUT = "results/final"
SPLITS = ["train", "calib", "val", "test"]
M_EVAL = ["precision", "recall", "f1", "cycle_recall", "cycle_false_alarm"]


def tbl(df):
    return df.to_markdown()


def main(seeds):
    os.makedirs(OUT, exist_ok=True)
    bal, imb, fair = [], [], []
    for s in seeds:
        df, users = simulate.simulate(300, s, 0.85, 1.05, 0.10)          # đúng như run_baselines.load
        dp = make_dp(prepare_df(df))
        for sp in SPLITS:
            d = dp[dp.split == sp]
            cyc = d.groupby(["user_id", "cycle_id"]).y.first()
            bal.append({"seed": s, "tập": sp, "số điểm": len(d), "tỉ lệ điểm thiếu tiền": d.y.mean(),
                        "số chu kỳ": len(cyc), "tỉ lệ chu kỳ thiếu tiền": cyc.mean()})
        pi = float(dp[dp.split == "calib"].y.mean())

        pts = pd.read_csv(f"results/risk_points_seed{s}.csv")
        pstar = float(pd.read_csv(f"results/risk_seed{s}.csv").set_index("model").loc["XGB+risk", "p_star"])
        p = pts.p_xgb.to_numpy()
        for name, thr in [("p* chọn trên val (đang dùng)", pstar), ("0,5 (mặc định)", 0.5), ("tỉ lệ nền tập calib", pi)]:
            r = evaluate(pts, p > thr)
            imb.append({"seed": s, "ngưỡng": name, "giá trị ngưỡng": thr, **{k: r[k] for k in M_EVAL}})

        # 3 mức thu nhập trong từng loại thu nhập
        u = users[["user_id", "income_type", "income"]].copy()
        u["mức"] = u.groupby("income_type").income.transform(lambda x: pd.qcut(x, 3, labels=["thấp", "vừa", "cao"]).astype(str))
        u["nhóm"] = u.income_type + " / " + u["mức"]
        pts = pts.merge(u[["user_id", "nhóm"]], on="user_id", how="left", validate="m:1")
        assert pts["nhóm"].notna().all()
        a = pts["alert_XGB+risk"].to_numpy().astype(bool)
        for g, idx in pts.groupby("nhóm").indices.items():
            sub = pts.iloc[idx].reset_index(drop=True)
            r = evaluate(sub, a[idx])
            yy, pp = sub.y.to_numpy(), sub.p_xgb.to_numpy()
            fair.append({"seed": s, "nhóm": g, "số người": sub.user_id.nunique(),
                         "tỉ lệ chu kỳ thiếu tiền": sub.groupby(["user_id", "cycle_id"]).y.first().mean(),
                         "bỏ sót (chu kỳ)": 1 - r["cycle_recall"], "báo nhầm (chu kỳ)": r["cycle_false_alarm"],
                         "precision": r["precision"], "recall": r["recall"],
                         "AUROC": roc_auc_score(yy, pp) if 0 < yy.mean() < 1 else np.nan, "ECE": ece(pp, yy), "Brier": brier(pp, yy)})

    def agg(rows, key, d=3):
        x = pd.DataFrame(rows)
        num = [c for c in x.columns if c not in ("seed", key)]
        g = x.groupby(key, sort=False)[num]
        m, sd = g.mean(), g.std()
        out = pd.DataFrame({c: [ms(m.loc[i, c], sd.loc[i, c], 0 if c in ("số điểm", "số chu kỳ", "số người") else d) for i in m.index]
                            for c in num}, index=m.index)
        return out, m

    t_bal, _ = agg(bal, "tập")
    t_imb, m_imb = agg(imb, "ngưỡng")
    t_fair, m_fair = agg(fair, "nhóm")
    order = [f"{t} / {lv}" for t in ("allowance_1st", "salary_25") for lv in ("thấp", "vừa", "cao")]
    t_fair, m_fair = t_fair.reindex(order), m_fair.reindex(order)
    t_bal.to_csv(f"{OUT}/class_balance.csv", encoding="utf-8-sig")
    t_imb.to_csv(f"{OUT}/imbalance_table.csv", encoding="utf-8-sig")
    t_fair.to_csv(f"{OUT}/fairness_income.csv", encoding="utf-8-sig")

    cur, half = m_imb.iloc[0], m_imb.loc["0,5 (mặc định)"]
    rng = lambda c: (m_fair[c].min(), m_fair[c].max(), m_fair[c].idxmin(), m_fair[c].idxmax())
    fa, miss, auc = rng("báo nhầm (chu kỳ)"), rng("bỏ sót (chu kỳ)"), rng("AUROC")
    lines = [
        f"# Phân tích bổ sung (test, trung bình ± độ lệch chuẩn qua {len(seeds)} seed)",
        "",
        "## 1. Mất cân bằng lớp",
        "",
        "Tỉ lệ thiếu tiền ở từng tập (điểm quyết định và chu kỳ):",
        "", tbl(t_bal), "",
        "Mô hình chính (XGBoost) dự báo **chi tiêu** (hồi quy), không phân loại trực tiếp, nên không dùng trọng số lớp hay lấy mẫu lại. "
        "Mất cân bằng chỉ tác động ở bước đặt ngưỡng cảnh báo trên xác suất p. Nhóm xử lý bằng cách chọn ngưỡng p* trên tập val để tối đa F1, "
        "và báo cáo thêm AUPRC (nhạy với lớp hiếm hơn AUROC). Bảng dưới so sánh cùng một p với các ngưỡng khác:",
        "", tbl(t_imb), "",
        f"- Ngưỡng 0,5 mặc định: recall {vn(half.recall)} so với {vn(cur.recall)} khi dùng p*, F1 {vn(half.f1)} so với {vn(cur.f1)}.",
        f"- Đổi lại, ngưỡng 0,5 giảm tỉ lệ chu kỳ bình thường bị báo nhầm từ {vn(cur.cycle_false_alarm)} xuống {vn(half.cycle_false_alarm)}, "
        f"trong khi tỉ lệ bắt được chu kỳ thiếu tiền chỉ giảm từ {vn(cur.cycle_recall)} xuống {vn(half.cycle_recall)}. "
        "p* tối đa F1 ở mức điểm quyết định nên ưu tiên bắt được nhiều ngày có nguy cơ; nếu muốn giảm mệt mỏi vì cảnh báo thì ngưỡng cao hơn hợp lý hơn "
        "(chọn theo chi phí bỏ sót / báo nhầm, xem `Extra_cost.csv`).",
        "",
        "## 2. Công bằng theo mức thu nhập (XGB + p > p*)",
        "",
        "Chia 3 mức thu nhập bằng nhau trong từng loại thu nhập (6 nhóm, mỗi nhóm khoảng 50 người).",
        "", tbl(t_fair), "",
        f"- Báo nhầm theo chu kỳ dao động từ {vn(fa[0])} ({fa[2]}) đến {vn(fa[1])} ({fa[3]}); "
        f"bỏ sót từ {vn(miss[0])} ({miss[2]}) đến {vn(miss[1])} ({miss[3]}); AUROC từ {vn(auc[0])} ({auc[2]}) đến {vn(auc[1])} ({auc[3]}).",
        "- Lưu ý: simulator không cài khác biệt hành vi theo mức thu nhập (chi tiêu tỉ lệ với thu nhập qua ρ), nên phép thử này chỉ kiểm tra "
        "mô hình có tự tạo ra chênh lệch hay không; chưa phải bằng chứng về công bằng trên người dùng thật. "
        "Phân tích theo kiểu chi tiêu và loại thu nhập có ở `Extra_fairness.csv`.",
    ]
    open(f"{OUT}/SUPPLEMENT.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    main(ap.parse_args().seeds)
