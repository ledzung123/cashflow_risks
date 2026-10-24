"""
evaluate.py - Chỉ số Q1 và Q2 (SPEC v1.1 mục 6). Người 2.

Q1: MAE, RMSE của chi tiêu ngày và của số dư cuối chu kỳ.
Q2: Precision, Recall, F1 (mức điểm quyết định); số ngày báo sớm (mức chu kỳ).
"""
import numpy as np
import pandas as pd

from labels import future_actual


def forecast_metrics(df, dp, yhat):
    y = future_actual(df, dp)
    err = (yhat - y)
    ok = ~np.isnan(err)
    proj_end = dp["balance_t"].to_numpy() - np.nansum(yhat, axis=1)
    e_bal = proj_end - dp["end_balance"].to_numpy()
    return {
        "MAE_spend": float(np.abs(err[ok]).mean()),
        "RMSE_spend": float(np.sqrt((err[ok] ** 2).mean())),
        "MAE_balance": float(np.abs(e_bal).mean()),
        "RMSE_balance": float(np.sqrt((e_bal ** 2).mean())),
    }


def evaluate(dp, alert):
    y = dp["y"].to_numpy().astype(bool)
    a = np.asarray(alert).astype(bool)
    tp, fp, fn = (a & y).sum(), (a & ~y).sum(), (~a & y).sum()
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    # mức chu kỳ
    c = dp[["user_id", "cycle_id", "t", "y", "dip_day"]].copy()
    c["a"] = a
    first_alert = c[c.a].groupby(["user_id", "cycle_id"]).t.min().rename("first_alert")
    cyc = c.groupby(["user_id", "cycle_id"]).agg(y=("y", "max"), dip_day=("dip_day", "first")).join(first_alert)
    pos, neg = cyc[cyc.y == 1], cyc[cyc.y == 0]
    caught = pos[pos.first_alert.notna()]
    days_early = (caught.dip_day - caught.first_alert)
    return {
        "precision": float(prec), "recall": float(rec), "f1": float(f1),
        "n_points": int(len(dp)), "pos_rate_points": float(y.mean()),
        "cycle_recall": float(len(caught) / len(pos)) if len(pos) else float("nan"),
        "cycle_false_alarm": float(neg.first_alert.notna().mean()) if len(neg) else float("nan"),
        "mean_days_early": float(days_early.mean()) if len(days_early) else float("nan"),
        "n_pos_cycles": int(len(pos)), "n_neg_cycles": int(len(neg)),
    }


def rank_metrics(dp, score):
    """AUROC, AUPRC và KS (= max(TPR - FPR)) của một điểm số rủi ro liên tục (điểm càng cao càng nguy cơ). Không phụ thuộc ngưỡng cảnh báo."""
    from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve
    y = dp["y"].to_numpy().astype(int)
    s = np.asarray(score, dtype=float)
    fpr, tpr, _ = roc_curve(y, s)
    return {"auroc": float(roc_auc_score(y, s)), "auprc": float(average_precision_score(y, s)),
            "ks": float(np.max(tpr - fpr)), "pos_rate": float(y.mean())}


FAR_GRID = tuple(round(x, 2) for x in np.arange(0.05, 0.501, 0.05))


def lead_at_far(dp, score, fars=FAR_GRID):
    """Đường đánh đổi MÔ TẢ trên tập được truyền vào, không phải ngưỡng vận hành độc lập.
    Với mỗi mức far (tỉ lệ chu kỳ bình thường có >= 1 cảnh báo), chọn ngưỡng trên chính tập đó,
    rồi đo trên các chu kỳ thiếu tiền: cycle_recall (tỉ lệ bắt được), lead_mean_all (số ngày báo trước ngày cạn tiền, chu kỳ bỏ sót tính 0 ngày),
    lead_median_caught (trung vị trên các chu kỳ bắt được). Không phụ thuộc ngưỡng đã tune, nên so sánh được giữa các mô hình."""
    c = dp[["user_id", "cycle_id", "t", "y", "dip_day"]].copy()
    c["s"] = np.asarray(score, dtype=float)
    key = ["user_id", "cycle_id"]
    cyc_y = c.groupby(key).y.first()
    neg_max = c.groupby(key).s.max()[cyc_y == 0].to_numpy()          # chu kỳ bình thường bị cảnh báo <=> max điểm > ngưỡng
    pos = c[c.y == 1]
    dip = pos.groupby(key).dip_day.first()
    rows = []
    for far in fars:
        thr = float(np.quantile(neg_max, 1.0 - far))
        first = pos[pos.s > thr].groupby(key).t.min()
        lead = dip.loc[first.index] - first
        rows.append({"far_target": far, "far_actual": float((neg_max > thr).mean()), "threshold": thr,
                     "cycle_recall": float(len(first) / len(dip)),
                     "lead_mean_all": float(lead.sum() / len(dip)),
                     "lead_median_caught": float(lead.median()) if len(lead) else float("nan")})
    return pd.DataFrame(rows)


def lead_at_precision(dp_val, score_val, dp_test, score_test, precisions):
    """Chọn ngưỡng trên validation để đạt Precision mục tiêu, rồi đánh giá một lần trên test.

    Với mỗi mức Precision, lấy ngưỡng thấp nhất trên validation còn đạt Precision mục tiêu
    (tức Recall validation cao nhất trong các ngưỡng đạt yêu cầu). Giữ nguyên ngưỡng đó khi
    tính Precision/Recall và chỉ số chu kỳ trên test. Test không tham gia chọn ngưỡng.
    """
    yv = dp_val["y"].to_numpy().astype(bool)
    sv = np.asarray(score_val, dtype=float)
    st = np.asarray(score_test, dtype=float)
    if len(dp_val) != len(sv) or len(dp_test) != len(st):
        raise ValueError("Số điểm của validation/test phải khớp với mảng score tương ứng")
    if not np.isfinite(sv).all() or not np.isfinite(st).all():
        raise ValueError("Score validation/test phải hữu hạn")

    order = np.argsort(-sv, kind="mergesort")
    ss, tp = sv[order], np.cumsum(yv[order])
    last = np.r_[ss[1:] != ss[:-1], True]                         # chỉ cắt ở ranh giới giữa các giá trị điểm khác nhau
    k = np.arange(1, len(sv) + 1)[last]
    precision_curve, thresholds = tp[last] / k, ss[last]
    rows = []
    for p_target in precisions:
        eligible = np.flatnonzero(precision_curve >= p_target)
        if len(eligible) == 0:
            rows.append({"precision_target": p_target, "reachable": False,
                         "threshold": np.nan, "precision_val": np.nan, "recall_val": np.nan})
            continue

        # Ngưỡng thấp nhất còn đạt Precision mục tiêu cho Recall lớn nhất trên validation.
        idx = eligible[-1]
        thr = float(thresholds[idx])
        val_metrics = evaluate(dp_val, sv >= thr)
        test_alert = st >= thr
        test_metrics = evaluate(dp_test, test_alert)

        key = ["user_id", "cycle_id"]
        c = dp_test[key + ["t", "y", "dip_day"]].assign(s=st)
        pos = c[c.y == 1]
        dip = pos.groupby(key).dip_day.first()
        first = pos[pos.s >= thr].groupby(key).t.min()
        lead = dip.loc[first.index] - first
        rows.append({"precision_target": p_target, "reachable": True, "threshold": thr,
                     "precision_val": val_metrics["precision"], "recall_val": val_metrics["recall"],
                     "precision": test_metrics["precision"], "recall": test_metrics["recall"],
                     "f1": test_metrics["f1"], "cycle_recall": test_metrics["cycle_recall"],
                     "cycle_false_alarm": test_metrics["cycle_false_alarm"],
                     "lead_mean_all": float(lead.sum() / len(dip)) if len(dip) else float("nan"),
                     "lead_median_caught": float(lead.median()) if len(lead) else float("nan")})
    return pd.DataFrame(rows)


def evaluate_by(dp, alert, df=None, yhat=None, by="pattern"):
    """Bảng chỉ số tách theo `by` (mặc định: 4 kiểu chi tiêu)."""
    rows = []
    alert = np.asarray(alert)
    for key, idx in dp.groupby(by).indices.items():
        sub = dp.iloc[idx].reset_index(drop=True)
        r = {by: key, **evaluate(sub, alert[idx])}
        if df is not None and yhat is not None:
            r.update(forecast_metrics(df, sub, yhat[idx]))
        rows.append(r)
    return pd.DataFrame(rows).set_index(by)
