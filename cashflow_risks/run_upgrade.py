"""Reproducible additional evaluation; preserves the previous final results and DOCX.

python cashflow_risks/run_upgrade.py --stage all
python cashflow_risks/run_upgrade.py --stage analysis   # cached scores only

Stage fit trains temporal/user-holdout models and two feature ablations on seeds
1,2,3. Checkpoints include source hashes and runtime versions. Stage analysis
selects all policies from validation, and reports every policy on test.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import time

import numpy as np
import pandas as pd
import sklearn
import xgboost

from baselines import margin_score, tune_margin
from evaluate import evaluate, forecast_metrics, rank_metrics, lead_at_precision
from features import FEATURES
from model_xgb import XGBForecaster
from policies import policy_table
from run_baselines import load
from run_risk import run, split_points
from labels import make_dp

ROOT = Path("results/upgrades")
SOURCE = Path(__file__).resolve().parent
MODES = ("time", "user_holdout")
ABLATIONS = {
    "no_personal_history": {"hist_dic_rel", "hist_smooth_rel", "n_prev"},
    "no_calendar_recent": {"tgt_wd", "tgt_weekend", "tgt_dic", "days_after", "dic_t",
                           "mean7_rel", "mean14_rel", "std14_rel", "max14_rel", "last1_rel",
                           "big28", "we_ratio", "b2_rel"},
}
TRAIN_SOURCES = ("run_risk.py", "run_baselines.py", "model_xgb.py", "features.py", "simulate.py",
                 "labels.py", "baselines.py", "risk.py", "prob_metrics.py", "evaluate.py", "policies.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signature(seed, mode, dropped=()):
    return {"seed": seed, "mode": mode, "dropped": sorted(dropped), "K": 500,
            "sources": {f: sha(SOURCE / f) for f in TRAIN_SOURCES},
            "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                        "pandas": pd.__version__, "xgboost": xgboost.__version__, "sklearn": sklearn.__version__}}


def ready(folder, expected):
    p = folder / "complete.json"
    if not p.exists():
        return False
    saved = json.loads(p.read_text(encoding="utf-8"))
    return saved["signature"] == expected and all(
        (folder / f).is_file() and sha(folder / f) == h for f, h in saved["artifacts"].items())


def finish(folder, expected):
    artifacts = {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != "complete.json"}
    (folder / "complete.json").write_text(json.dumps({"signature": expected, "artifacts": artifacts}, indent=2), encoding="utf-8")


def fit(seeds):
    for seed in seeds:
        for mode in MODES:
            folder = ROOT / mode / f"seed{seed}"
            expected = signature(seed, mode)
            if ready(folder, expected):
                print(f"REUSE {mode} seed{seed}: verified checkpoint", flush=True)
                continue
            print(f"FIT {mode} seed{seed}", flush=True)
            t0 = time.time()
            run(seed, split_mode=mode, evidence_dir=folder)
            finish(folder, expected)
            print(f"DONE {mode} seed{seed}: {time.time()-t0:.1f}s", flush=True)
        df = load(seed, None)
        S = split_points(make_dp(df))
        for variant, dropped in ABLATIONS.items():
            folder = ROOT / "ablation" / f"seed{seed}" / variant
            expected = signature(seed, "time", dropped)
            if ready(folder, expected):
                print(f"REUSE {variant} seed{seed}: verified checkpoint", flush=True)
                continue
            print(f"FIT {variant} seed{seed}", flush=True)
            t0 = time.time()
            folder.mkdir(parents=True, exist_ok=True)
            kept = [f for f in FEATURES if f not in dropped]
            model = XGBForecaster(seed=seed, feature_names=kept).fit(df, S["train"], S["val"])
            pred = {s: model.predict_spend(df, S[s]) for s in ("val", "test")}
            sv, st = (margin_score(S[s], pred[s]) for s in ("val", "test"))
            margin, _ = tune_margin(S["val"], pred["val"], evaluate)
            policy_table(S["val"], {variant: sv}, S["test"], {variant: st}, {variant: -margin}).to_csv(folder / "policies.csv", index=False)
            pd.DataFrame([{"variant": variant, "seed": seed, "n_features": len(kept),
                           "features": ",".join(kept), **forecast_metrics(df, S["test"], pred["test"]),
                           **rank_metrics(S["test"], st)}]).to_csv(folder / "forecast_metrics.csv", index=False)
            np.savez_compressed(folder / "forecasts.npz", **pred)
            model.model.save_model(folder / "model.ubj")
            finish(folder, expected)
            print(f"DONE {variant} seed{seed}: {time.time()-t0:.1f}s", flush=True)


def counts_by_user(dp, alert):
    y = dp.y.to_numpy(dtype=bool)
    c = dp.assign(tp=alert & y, fp=alert & ~y, fn=~alert & y, alert=alert)
    points = c.groupby("user_id")[["tp", "fp", "fn"]].sum()
    cycles = c.groupby(["user_id", "cycle_id"]).agg(y=("y", "max"), days=("alert", "sum"))
    z = cycles.assign(pos=cycles.y == 1, neg=cycles.y == 0,
                      caught=(cycles.y == 1) & (cycles.days > 0),
                      false=(cycles.y == 0) & (cycles.days > 0),
                      neg_days=cycles.days.where(cycles.y == 0, 0)).groupby("user_id").sum()
    return points.join(z[["pos", "neg", "caught", "false", "neg_days"]]).fillna(0)


def metrics_from_counts(x):
    tp, fp, fn, pos, neg, caught, false, days = x.T
    div = lambda a, b: np.divide(a, b, out=np.full_like(a, np.nan, dtype=float), where=b != 0)
    return {"precision": div(tp, tp + fp), "recall": div(tp, tp + fn),
            "f1": div(2 * tp, 2 * tp + fp + fn), "cycle_recall": div(caught, pos),
            "cycle_false_alarm": div(false, neg), "negative_alert_days_mean": div(days, neg)}


def bootstrap_policies(dp, table, seed, mode, B, policy_names=("f1_val", "far20_val", "cost_r2_val")):
    """Paired cluster bootstrap by user; frozen validation thresholds; per-seed CI."""
    users = np.sort(dp.user_id.unique())
    rng = np.random.default_rng(10000 + seed)
    weights = rng.multinomial(len(users), np.ones(len(users)) / len(users), size=B)
    rows = []
    for policy in policy_names:
        ms = {}
        for model in ("B1", "B2", "XGB", "XGB+risk"):
            threshold = table.loc[(table.model == model) & (table.policy == policy), "threshold"].item()
            counts = counts_by_user(dp, dp["score_" + model].to_numpy() > threshold).reindex(users).to_numpy(float)
            ms[model] = (metrics_from_counts(counts.sum(axis=0, keepdims=True)), metrics_from_counts(weights @ counts))
        for baseline in ("B1", "B2", "XGB"):
            for metric in ms[baseline][0]:
                d = ms["XGB+risk"][1][metric] - ms[baseline][1][metric]
                valid = d[np.isfinite(d)]
                low, high = np.quantile(valid, [0.025, 0.975]) if len(valid) else (np.nan, np.nan)
                rows.append({"mode": mode, "seed": seed, "policy": policy,
                             "comparison": "XGB+risk - " + baseline, "metric": metric,
                             "difference": float(ms["XGB+risk"][0][metric][0] - ms[baseline][0][metric][0]),
                             "ci95_low": low, "ci95_high": high, "B": B, "valid_resamples": len(valid),
                             "unit": "user", "threshold_source": "validation"})
    return pd.DataFrame(rows)


def analysis(seeds, B):
    tables, boot, q1, ablation, precision, precision_boot = [], [], [], [], [], []
    for seed in seeds:
        for mode in MODES:
            folder = ROOT / mode / f"seed{seed}"
            if not ready(folder, signature(seed, mode)):
                raise ValueError(f"Missing/stale checkpoint: {folder}; run --stage fit")
            val, test = (pd.read_csv(folder / f"{s}_scores.csv", float_precision="round_trip") for s in ("val", "test"))
            selected = json.loads((folder / "selection.json").read_text(encoding="utf-8"))
            names = list(selected["f1_thresholds"])
            sv, st = ({m: points["score_" + m].to_numpy() for m in names} for points in (val, test))
            table = policy_table(val, sv, test, st, selected["f1_thresholds"], ("XGB+risk", "B2+risk"))
            tables.append(table.assign(seed=seed, mode=mode))
            boot.append(bootstrap_policies(test, table, seed, mode, B))
            q1.append(pd.read_csv(folder / "q1.csv").assign(seed=seed, mode=mode))
            target = evaluate(val, sv["B1"] > selected["f1_thresholds"]["B1"])["precision"]
            matching = []
            for m in names:
                part = lead_at_precision(val, sv[m], test, st[m], [target]).assign(model=m, seed=seed, mode=mode)
                precision.append(part)
                if part.reachable.item():
                    # lead_at_precision uses >=; bootstrap policies use strict >.
                    matching.append({"model": m, "policy": "same_precision_val",
                                     "threshold": np.nextafter(part.threshold.item(), -np.inf)})
            if {"B1", "B2", "XGB", "XGB+risk"}.issubset({r["model"] for r in matching}):
                precision_boot.append(bootstrap_policies(test, pd.DataFrame(matching), seed, mode, B,
                                                         policy_names=("same_precision_val",)))
        full = pd.read_csv(ROOT / "time" / f"seed{seed}" / "q1.csv").query("model == 'XGB'").copy()
        full["variant"], full["seed"], full["n_features"] = "full", seed, len(FEATURES)
        ablation.append(full.drop(columns="model"))
        for variant, dropped in ABLATIONS.items():
            folder = ROOT / "ablation" / f"seed{seed}" / variant
            if not ready(folder, signature(seed, "time", dropped)):
                raise ValueError(f"Missing/stale ablation checkpoint: {folder}")
            ablation.append(pd.read_csv(folder / "forecast_metrics.csv"))
            tables.append(pd.read_csv(folder / "policies.csv").assign(seed=seed, mode="ablation"))
    out = ROOT / "summary"
    out.mkdir(parents=True, exist_ok=True)
    policies = pd.concat(tables, ignore_index=True)
    policies.to_csv(out / "policies_per_seed.csv", index=False)
    cols = [c for c in policies if c.startswith("test_")] + ["val_cycle_false_alarm", "val_cost_per_100"]
    means = policies.groupby(["mode", "model", "policy"])[cols].mean()
    means.to_csv(out / "policies_mean.csv")
    policies.groupby(["mode", "model", "policy"])[cols].std().to_csv(out / "policies_sd.csv")
    boots = pd.concat(boot, ignore_index=True)
    boots.to_csv(out / "bootstrap_per_seed.csv", index=False)
    boots.groupby(["mode", "policy", "comparison", "metric"]).agg(
        difference_mean=("difference", "mean"), difference_sd=("difference", "std"),
        seeds_ci_above_zero=("ci95_low", lambda v: int((v > 0).sum())),
        seeds_ci_below_zero=("ci95_high", lambda v: int((v < 0).sum()))).to_csv(out / "bootstrap_seed_summary.csv")
    original = []
    for seed in seeds:
        p = Path(f"results/boot_seed{seed}.csv")
        if p.exists():
            original.append(pd.read_csv(p).assign(seed=seed))
    if original:
        old = pd.concat(original, ignore_index=True)
        old.to_csv(out / "original_bootstrap_per_seed.csv", index=False)
        old.groupby(["so_sánh", "chỉ_số"]).agg(mean=("chênh_quan_sát", "mean"),
            sd=("chênh_quan_sát", "std")).to_csv(out / "original_bootstrap_seed_summary.csv")
    pd.concat(q1).to_csv(out / "q1_per_seed.csv", index=False)
    pd.concat(precision).to_csv(out / "same_precision_per_seed.csv", index=False)
    if precision_boot:
        pd.concat(precision_boot).to_csv(out / "same_precision_bootstrap_per_seed.csv", index=False)
    ab = pd.concat(ablation, ignore_index=True)
    ab.to_csv(out / "ablation_per_seed.csv", index=False)
    ab.groupby("variant")[["MAE_spend", "MAE_balance"]].agg(["mean", "std"]).to_csv(out / "ablation_summary.csv")
    selected_policies = means.reset_index().query("mode != 'ablation' and policy in ['f1_val','far20_val','cost_r2_val','bayes_r2']")
    display = selected_policies[["mode", "model", "policy", "test_precision", "test_recall", "test_f1",
        "test_cycle_recall", "test_cycle_false_alarm", "test_negative_alert_days_mean", "test_cost_per_100"]]
    note = """# Đánh giá nâng cấp — ngưỡng cố định từ validation

Đây là bằng chứng kỹ thuật bổ sung, không sửa báo cáo cuối kỳ. Các chính sách được
định trước (F1, FAR20, chi phí r=1/2/3/5/10/20, Bayes); không chọn chính sách tốt nhất theo test.
Test đã được xem trong phát triển dự án, nên đây là đánh giá bổ sung trên bộ chuẩn cũ,
không phải một tập kiểm chứng mới hoàn toàn chưa từng xem.

Chi phí tính trên 100 điểm quyết định, đơn vị một FP; không phải chi phí tiền thật.
FAR tính trên chu kỳ bình thường có ít nhất một điểm đủ điều kiện. Số ngày cảnh báo
cũng chỉ tính các điểm đủ điều kiện, không phải mọi ngày lịch. Cột thông báo một lần/
chu kỳ là phép đếm nếu chỉ gửi lần cảnh báo đầu; không chứng minh người dùng sẽ hành động.
FAR validation <=20% không bảo đảm FAR test <=20% khi phân phối thay đổi.

CI95% được báo riêng theo seed, bootstrap ghép cặp theo người, giữ cố định ngưỡng.
Không lấy trung bình cận CI thành CI95% chung; SD qua ba seed là mô tả độ biến thiên.
Phép bootstrap này không bao gồm bất định do huấn luyện/chọn ngưỡng. CI của chênh lệch
Precision/Recall tại mục tiêu Precision chung cũng được lưu riêng; không dùng việc CI
chứa 0 để kết luận tương đương, vì chưa định trước biên tương đương. Dòng FAR20 của
original_bootstrap_per_seed.csv vẫn là đường đánh đổi mô tả trên test cũ.

User-holdout giữ riêng người giữa các vai trò nhưng cho phép dùng lịch sử của chính
người đó để xây đặc trưng; không phải cold start và chưa đại diện dữ liệu thật.

## Chính sách cảnh báo (trung bình các seed)

"""
    note += display.round(4).to_markdown(index=False)
    note += "\n\n## Bỏ nhóm đặc trưng\n\n" + ab.groupby("variant")[["MAE_spend", "MAE_balance"]].mean().round(2).to_markdown()
    note += "\n\nHai ablation chỉ thay đầu vào mô hình, cùng chia tập/thuật toán/hyperparameter; mỗi mô hình early-stop trên validation. "
    note += "no_calendar_recent vẫn giữ h, D, số dư/ngưỡng, lịch sử chu kỳ và chuẩn hóa mean28; đây là bỏ một nhóm đặc trưng, không xóa mọi thông tin lịch/chi tiêu. "
    note += "So XGB với XGB+risk trong bảng chính sách là đối chứng có/không lớp xác suất trên cùng dự báo.\n"
    (out / "UPGRADE_RESULTS.md").write_text(note, encoding="utf-8")
    print(display.round(4).to_string(index=False), flush=True)
    print(f"Saved {out}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("fit", "analysis", "all"), default="all")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--B", type=int, default=500)
    a = ap.parse_args()
    if len(set(a.seeds)) != len(a.seeds) or a.B < 100:
        raise ValueError("Seeds must be unique; B must be >=100")
    ROOT.mkdir(parents=True, exist_ok=True)
    report = Path("Bao_cao_cuoi_ky_nhom_11.docx")
    before = sha(report) if report.exists() else None
    if a.stage in ("fit", "all"):
        fit(a.seeds)
    if a.stage in ("analysis", "all"):
        analysis(a.seeds, a.B)
    if before is not None and sha(report) != before:
        raise RuntimeError("Final report changed during execution")
    (ROOT / "run_manifest.json").write_text(json.dumps({"seeds": a.seeds, "bootstrap_replicates": a.B,
        "stage": a.stage, "report_sha256_unchanged": before,
        "analysis_sources": {f: sha(SOURCE / f) for f in ("run_upgrade.py", "policies.py")}}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
