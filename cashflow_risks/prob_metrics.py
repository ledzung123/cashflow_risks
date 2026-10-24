"""
prob_metrics.py - Chỉ số đánh giá chất lượng xác suất p_t (SPEC v2.1). Người 2.

  Độ chính xác xác suất : Brier, Brier skill (so với luôn đoán tỉ lệ nền), log loss, log loss skill
  Khả năng xếp hạng     : AUROC, AUPRC (so với tỉ lệ nền)
  Hiệu chỉnh            : ECE, MCE, độ dốc và hệ số chặn hiệu chỉnh (lý tưởng: 1 và 0)
  Độ sắc                : độ lệch chuẩn của p
Tỉ lệ nền để tính "skill" lấy từ tập CALIB (không lấy từ test).
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from risk import D_EDGES, brier, ece

D_LABELS = ["3-4", "5-7", "8-11", "12-16", "17-21", "22-31"]
EPS = 1e-6


def _logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def mce(p, y, bins=10, min_n=50):
    idx = np.minimum((p * bins).astype(int), bins - 1)
    gaps = [abs(y[idx == b].mean() - p[idx == b].mean()) for b in range(bins) if (idx == b).sum() >= min_n]
    return float(max(gaps)) if gaps else float("nan")


def prob_metrics(p, y, base_rate=None):
    p, y = np.asarray(p, dtype=float), np.asarray(y, dtype=int)
    base = float(y.mean()) if base_rate is None else float(base_rate)
    base = min(max(base, EPS), 1 - EPS)
    pc = np.clip(p, EPS, 1 - EPS)
    b, b_ref = brier(p, y), float(np.mean((base - y) ** 2))
    ll = float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc)))
    ll_ref = float(-np.mean(y * np.log(base) + (1 - y) * np.log(1 - base)))
    two = len(np.unique(y)) > 1
    if two:
        lr = LogisticRegression(C=1e6, max_iter=1000).fit(_logit(p)[:, None], y)
        slope, intercept = float(lr.coef_[0, 0]), float(lr.intercept_[0])
    else:
        slope = intercept = float("nan")
    return {"n": int(len(y)), "pos_rate": float(y.mean()), "brier": b, "brier_skill": 1 - b / b_ref,
            "log_loss": ll, "log_loss_skill": 1 - ll / ll_ref,
            "auroc": float(roc_auc_score(y, p)) if two else float("nan"),
            "auprc": float(average_precision_score(y, p)) if two else float("nan"),
            "cal_slope": slope, "cal_intercept": intercept,
            "ece": ece(p, y), "mce": mce(p, y), "sharpness": float(p.std())}


def prob_metrics_by(p, y, groups, base_rate=None, name="group"):
    p, y, groups = np.asarray(p), np.asarray(y), np.asarray(groups)
    rows = [{name: g, **prob_metrics(p[groups == g], y[groups == g], base_rate)} for g in pd.unique(groups)]
    return pd.DataFrame(rows).set_index(name).sort_index()


def d_bucket(D):
    return np.array(D_LABELS)[np.digitize(np.asarray(D), D_EDGES)]
