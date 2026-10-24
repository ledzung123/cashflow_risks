"""
check_expected.py - Tự kiểm tra kết quả sau khi chạy xong run_all.ps1: in PASS/FAIL cho từng tiêu chí, thoát mã 1 nếu có FAIL.
  python src/check_expected.py            (chạy ở thư mục chứa results/)
Các khoảng chấp nhận được đặt rộng hơn sai khác thường thấy giữa hai máy (XGBoost trên máy khác cho kết quả lệch rất nhỏ).
Riêng B1 và B2 không dùng XGBoost nên phải trùng gần như tuyệt đối.
"""
import os
import sys

import numpy as np
import pandas as pd

SEEDS = (1, 2, 3)
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(("PASS  " if cond else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


def need(path):
    ok = os.path.exists(path)
    check(f"có file {path}", ok)
    return ok


def per_seed(prefix):
    return pd.concat([pd.read_csv(f"results/{prefix}_seed{s}.csv").assign(seed=s) for s in SEEDS])


files = (["data/daily.csv", "results/final/fig0_sanity_du_lieu.png"]
         + [f"results/{p}_seed{s}.csv" for p in ("baselines", "xgb", "risk", "rank", "pmetrics", "diagnostics", "risk_points") for s in SEEDS]
         + [f"results/final/{f}" for f in ("RESULTS.md", "Q1_table.csv", "Q2_table.csv", "P_table.csv", "diagnostics_table.csv",
                                             "fig1_Q1.png", "fig2_Q2.png", "fig3_by_pattern.png", "fig4_calibration.png",
                                             "fig5_importance.png", "fig6_case_study.png", "fig7_p_diagnostics.png", "fig9_lead_far.png", "Lead_table.csv")]
         + [f"results/lead_seed{s}.csv" for s in SEEDS])
files += ["results/user_holdout/user_assignments.csv", "results/user_holdout/USER_HOLDOUT.md",
          "results/user_holdout/q1_mean.csv", "results/user_holdout/q2_mean.csv",
          "results/user_holdout/precision_mean.csv"]
files += [f"results/user_holdout/{kind}_seed{s}.csv" for s in SEEDS for kind in ("q1", "q2", "precision", "split_sizes")]
if not all([need(f) for f in files]):
    print("\nThiếu file kết quả: chạy lại run_all.ps1 (hoặc từng bước bị thiếu) rồi kiểm tra lại.")
    sys.exit(1)

B, X, R, K = per_seed("baselines"), per_seed("xgb"), per_seed("risk"), per_seed("rank")
P = pd.concat([pd.read_csv(f"results/pmetrics_seed{s}.csv").assign(seed=s) for s in SEEDS])
P = P[P["set"] == "test"]
G = pd.concat([pd.read_csv(f"results/diagnostics_seed{s}.csv").assign(seed=s) for s in SEEDS]).groupby("metric").value.mean()
mean = lambda df, m, c: float(df[df.model == m][c].mean())
bys = lambda df, m, c: df[df.model == m].set_index("seed")[c]

print("\n-- 0. Du lieu mo phong: 300 nguoi x 24 chu ky --")
dd = pd.read_csv("data/daily.csv", usecols=["user_id", "cycle_id", "split"])
check("data/daily.csv co 300 nguoi", dd.user_id.nunique() == 300, str(dd.user_id.nunique()))
check("moi nguoi co 24 chu ky", bool(dd.groupby("user_id").cycle_id.nunique().eq(24).all()))
check("tong 219.000 dong (300 nguoi x 730 ngay)", len(dd) == 219000, f"{len(dd):,}")
check("so chu ky moi tap: train 12, calib 4, val 4, test 4", dd.groupby("split").cycle_id.nunique().to_dict() == {"calib": 4, "test": 4, "train": 12, "val": 4})

print("\n-- 1. Dữ liệu và baseline (không phụ thuộc XGBoost, phải trùng gần tuyệt đối) --")
n_test = [len(pd.read_csv(f"results/risk_points_seed{s}.csv")) for s in SEEDS]
check("số điểm test của 3 seed = 32290 / 32208 / 32283", n_test == [32290, 32208, 32283], str(n_test))
ref = {("B1", "f1"): 0.6563, ("B2", "f1"): 0.6790, ("B1", "MAE_spend"): 131066.0, ("B2", "MAE_spend"): 128358.0,
       ("B1", "MAE_balance"): 969519.0, ("B2", "MAE_balance"): 813502.0}
for (m, c), v in ref.items():
    got = mean(B, m, c)
    check(f"{m} {c} trung bình = {v:g}", abs(got - v) <= max(abs(v) * 1e-4, 5e-4), f"{got:.4f}")

print("\n-- 2. Q1: dự báo chi tiêu (XGBoost) --")
check("MAE chi tiêu ngày của XGB trong [106.000; 111.500]", 106000 <= mean(X, "XGB", "MAE_spend") <= 111500, f"{mean(X, 'XGB', 'MAE_spend'):.0f}")
check("MAE số dư của XGB trong [605.000; 640.000]", 605000 <= mean(X, "XGB", "MAE_balance") <= 640000, f"{mean(X, 'XGB', 'MAE_balance'):.0f}")
for c in ("MAE_spend", "MAE_balance"):
    d = bys(X, "XGB", c) - bys(B, "B2", c)
    check(f"XGB có {c} thấp hơn B2 ở cả 3 seed", bool((d < 0).all()), "chênh " + ", ".join(f"{v:+.0f}" for v in d))
red = 100 * (1 - mean(X, "XGB", "MAE_spend") / mean(B, "B2", "MAE_spend"))
check("XGB giảm MAE chi tiêu so với B2 từ 12% đến 19%", 12 <= red <= 19, f"{red:.1f}%")

print("\n-- 3. Q2: cảnh báo và xác suất --")
check("F1 của XGB (biên m) trong [0,685; 0,715]", 0.685 <= mean(X, "XGB", "f1") <= 0.715, f"{mean(X, 'XGB', 'f1'):.4f}")
check("F1 của XGB + p > p* trong [0,685; 0,715]", 0.685 <= mean(R, "XGB+risk", "f1") <= 0.715, f"{mean(R, 'XGB+risk', 'f1'):.4f}")
d = bys(X, "XGB", "f1") - bys(B, "B2", "f1")
check("F1 của XGB cao hơn B2 ở cả 3 seed", bool((d > 0).all()), "chênh " + ", ".join(f"{v:+.3f}" for v in d))
auc = {m: mean(K, m, "auroc") for m in ("B1", "B2", "XGB", "XGB+risk", "B2+risk")}
check("AUROC: B1 < B2 < XGB < XGB + p", auc["B1"] < auc["B2"] < auc["XGB"] < auc["XGB+risk"], ", ".join(f"{k} {v:.3f}" for k, v in auc.items()))
d = bys(K, "XGB", "auroc") - bys(K, "B2", "auroc")
check("AUROC của XGB cao hơn B2 ở cả 3 seed", bool((d > 0).all()), "chênh " + ", ".join(f"{v:+.3f}" for v in d))
ece_x, ece_b = mean(R, "XGB+risk", "ece_test"), mean(R, "B2+risk", "ece_test")
check("ECE của XGB + p dưới 0,03", ece_x < 0.03, f"{ece_x:.4f}")
check("ECE của B2 + p lớn hơn ECE của XGB + p (dự báo tốt hơn thì xác suất chuẩn hơn)", ece_b > ece_x, f"{ece_b:.4f} > {ece_x:.4f}")
check("Brier test của XGB + p thấp hơn B2 + p", mean(R, "XGB+risk", "brier_test") < mean(R, "B2+risk", "brier_test"))
meth = R[R.model == "XGB+risk"]["method"].tolist()
check("phương pháp ước lượng p được chọn là cum hoặc cumb (không phải mc)", all(m in ("cum", "cumb") for m in meth), str(meth))
px = P[P.model == "XGB+risk"]
check("độ dốc hiệu chỉnh của XGB + p trong [0,85; 1,10]", 0.85 <= px.cal_slope.mean() <= 1.10, f"{px.cal_slope.mean():.3f}")
check("AUROC của p (XGB + p) lớn hơn 0,86", px.auroc.mean() > 0.86, f"{px.auroc.mean():.3f}")
check("độ phủ khoảng dự báo 80% của XGB + p trong [0,76; 0,83]", 0.76 <= px.cov80.mean() <= 0.83, f"{px.cov80.mean():.3f}")

print("\n-- 3b. Báo sớm ở cùng mức báo nhầm --")
LD = pd.concat([pd.read_csv(f"results/lead_seed{s}.csv").assign(seed=s) for s in SEEDS])
for far in (0.1, 0.2, 0.3):
    sub = LD[np.isclose(LD.far_target, far)]
    check(f"mức báo nhầm thực tế bám sát mục tiêu {int(far * 100)}% (lệch dưới 2 điểm phần trăm)", bool((sub.far_actual - far).abs().max() < 0.02),
          f"lệch tối đa {(sub.far_actual - far).abs().max():.3f}")
L20 = LD[np.isclose(LD.far_target, 0.2)].pivot(index="seed", columns="model", values=["cycle_recall", "lead_mean_all", "lead_median_caught"])
rm = L20["cycle_recall"].mean()
check("ở cùng mức báo nhầm 20%: tỉ lệ bắt được B1 < B2 < XGB", rm["B1"] < rm["B2"] < rm["XGB"], ", ".join(f"{k} {rm[k]:.3f}" for k in ("B1", "B2", "XGB", "XGB+risk")))
check("XGB bắt được nhiều chu kỳ thiếu tiền hơn B2 ở cả 3 seed (mức báo nhầm 20%)", bool((L20["cycle_recall"]["XGB"] > L20["cycle_recall"]["B2"]).all()))
check("XGB báo trước nhiều ngày hơn B2 ở cả 3 seed (chu kỳ bỏ sót tính 0)", bool((L20["lead_mean_all"]["XGB"] > L20["lead_mean_all"]["B2"]).all()))
med = L20["lead_median_caught"].mean()[["B1", "B2", "XGB", "XGB+risk", "B2+risk"]]
check("trung vị số ngày báo trước (chỉ chu kỳ bắt được) gần bằng nhau giữa các mô hình (chênh dưới 4 ngày) - lợi thế là bắt được nhiều hơn, không phải sớm hơn",
      med.max() - med.min() < 4, f"{med.min():.1f} đến {med.max():.1f}")

print("\n-- 3c. Bổ sung kỹ thuật: so mô hình, chi phí, khoảng tin cậy --")
for f in ("Extra_models.csv", "Extra_cost.csv", "Extra_bootstrap.csv", "Extra_fairness.csv", "Extra_latency.csv", "EXTRA_RESULTS.md", "fig10_extra.png"):
    need(f"results/final/{f}")
MD = pd.concat([pd.read_csv(f"results/models_seed{s}.csv").assign(seed=s) for s in SEEDS]).pivot(index="seed", columns="key", values="MAE_spend")
check("XGBoost có MAE chi tiêu thấp hơn Ridge (tuyến tính) ở cả 3 seed", bool((MD["xgb"] < MD["ridge"]).all()))
check("XGBoost thấp hơn B2 ít nhất 10% MAE chi tiêu ở cả 3 seed", bool((MD["xgb"] < 0.9 * MD["b2"]).all()))
check("XGBoost, HGB, Random Forest xấp xỉ nhau (chênh MAE dưới 3%)", float((MD[["xgb", "hgb", "rf"]].max(axis=1) / MD[["xgb", "hgb", "rf"]].min(axis=1) - 1).max()) < 0.03)
CD = pd.concat([pd.read_csv(f"results/cost_seed{s}.csv").assign(seed=s) for s in SEEDS])
check("chi phí test dùng ngưỡng chọn trên validation", "threshold_source" in CD and bool(CD.threshold_source.eq("validation").all()))
if "cost_test_per_100" in CD:
    xp = CD[CD.model == "XGB + p"].groupby("r")[["cost_test_per_100", "cost_bayes_per_100"]].mean()
    gap = (xp.cost_bayes_per_100 / xp.cost_test_per_100 - 1).loc[[1, 2, 3, 5]]
    print("Chênh chi phí Bayes so với ngưỡng validation (mô tả, không phải tối ưu trên test):", ", ".join(f"r={r}: {v:+.1%}" for r, v in gap.items()))
BD = pd.concat([pd.read_csv(f"results/boot_seed{s}.csv").assign(seed=s) for s in SEEDS])
bx = BD[(BD["so_sánh"] == "XGB + p - B2") & BD["chỉ_số"].isin(["AUROC", "tỉ lệ bắt được ở báo nhầm 20%"])]
check("khoảng tin cậy 95% (bootstrap theo người) của hiệu XGB + p - B2 về AUROC và tỉ lệ bắt được không chứa 0, ở cả 3 seed", bool((bx.ci_thấp > 0).all()))
LD2 = pd.concat([pd.read_csv(f"results/latency_seed{s}.csv") for s in SEEDS])
lat = LD2[LD2["mục"].str.startswith("1 yêu cầu: dựng")]["giá trị"]
check("độ trễ 1 yêu cầu (dựng đặc trưng + dự báo) dưới 200 ms", float(lat.max()) < 200, f"tối đa {lat.max():.0f} ms")

print("\n-- 4. Kiểm chứng phần dư độc lập --")
lag = [G[f"lagcorr_k{k}_test"] for k in (1, 2, 3, 7)]
check("tương quan phần dư giữa các ngày gần 0 (|r| < 0,05)", max(abs(v) for v in lag) < 0.05, ", ".join(f"{v:+.3f}" for v in lag))
check("tỉ số phương sai > 1 và tăng theo D (phụ thuộc dương nhẹ)", 1.0 < G["VR_D5_test"] < G["VR_D25_test"] < 1.5,
      f"D=5: {G['VR_D5_test']:.2f}, D=25: {G['VR_D25_test']:.2f}")
check("cách giả định độc lập (mc) phủ thiếu hơn cách không giả định (cum)", G["cov80_mc_all"] < G["cov80_cum_all"],
      f"mc {G['cov80_mc_all']:.3f} < cum {G['cov80_cum_all']:.3f}")
check("kiểu spike vẫn phủ thiếu rõ (cumb < 0,78) - hạn chế đã biết", G["cov80_cumb_spike"] < 0.78, f"{G['cov80_cumb_spike']:.3f}")

print("\n-- 5. Tập đánh giá phụ giữ riêng người dùng --")
UA = pd.read_csv("results/user_holdout/user_assignments.csv")
role_sizes = UA.groupby("role").user_id.nunique().to_dict()
check("user-holdout phân vai đủ 300 người (train/calib/val/test = 150/45/45/60)",
      role_sizes == {"calib": 45, "test": 60, "train": 150, "val": 45}, str(role_sizes))
check("mỗi user_id chỉ xuất hiện trong một vai trò", UA.user_id.nunique() == len(UA) == 300)
UH = pd.concat([pd.read_csv(f"results/user_holdout/q2_seed{s}.csv").assign(seed=s) for s in SEEDS])
check("kết quả user-holdout có các mô hình chính", set(("B1", "B2", "XGB", "XGB+risk", "B2+risk")).issubset(set(UH.model)))
UP = pd.concat([pd.read_csv(f"results/user_holdout/precision_seed{s}.csv").assign(seed=s) for s in SEEDS])
check("báo cáo cùng Precision user-holdout lưu Precision validation và test riêng",
      {"precision_val", "precision", "threshold"}.issubset(UP.columns))

print(f"\n{'TẤT CẢ ĐẠT' if fails == 0 else str(fails) + ' TIÊU CHÍ KHÔNG ĐẠT'}")
sys.exit(1 if fails else 0)
