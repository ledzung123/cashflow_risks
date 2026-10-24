"""
baselines.py - B1, B2 và quy tắc cảnh báo của baseline (SPEC v1.1 mục 5-6). Người 2.

  B1: chi tiêu mỗi ngày = trung bình 14 ngày gần nhất (tương ứng cách "số dư chia chi tiêu trung bình").
  B2: chi tiêu mỗi ngày = trung bình cùng thứ trong tuần của 28 ngày gần nhất.
Cả hai chỉ dùng dữ liệu <= ngày t (không rò rỉ tương lai).
"""
import numpy as np
import pandas as pd

from labels import HORIZON_MAX

B1_WINDOW = 14
B2_WINDOW = 28


def _mask_beyond_D(yhat, D):
    h = np.arange(1, HORIZON_MAX + 1)[None, :]
    yhat = yhat.copy()
    yhat[h > D[:, None]] = np.nan
    return yhat


def predict_spend_b1(df, dp):
    roll = df.groupby("user_id")["spend"].transform(lambda s: s.rolling(B1_WINDOW).mean()).to_numpy()
    base = roll[dp["row"].to_numpy()]
    yhat = np.repeat(base[:, None], HORIZON_MAX, axis=1)
    return _mask_beyond_D(yhat, dp["D"].to_numpy())


def predict_spend_b2(df, dp):
    spend = df["spend"].to_numpy(dtype=float)
    wd = df["wd"].to_numpy()
    rows = dp["row"].to_numpy()
    idx = rows[:, None] - np.arange(B2_WINDOW)[None, ::-1]          # (n, 28), kết thúc ở ngày t
    win, wdw = spend[idx], wd[idx]
    m7 = np.zeros((len(dp), 7))
    for w in range(7):
        mask = wdw == w
        m7[:, w] = (win * mask).sum(1) / mask.sum(1)
    wd_t = wd[rows]
    h = np.arange(1, HORIZON_MAX + 1)[None, :]
    target_wd = (wd_t[:, None] + h) % 7
    yhat = np.take_along_axis(m7, target_wd, axis=1)
    return _mask_beyond_D(yhat, dp["D"].to_numpy())


def projected_end_balance(dp, yhat):
    """Số dư dự kiến cuối chu kỳ = số dư hiện tại - tổng chi dự báo D ngày tới."""
    return dp["balance_t"].to_numpy() - np.nansum(yhat, axis=1)


def alert_by_margin(dp, yhat, m):
    """Cảnh báo khi số dư dự kiến cuối chu kỳ < theta_c * (1 + m). m tính theo đơn vị theta_c."""
    return projected_end_balance(dp, yhat) < dp["theta_c"].to_numpy() * (1.0 + m)


def margin_score(dp, yhat):
    """Điểm rủi ro liên tục của cảnh báo theo biên: (theta - số dư dự kiến cuối chu kỳ) / theta.
    Cảnh báo theo biên m  <=>  margin_score > -m, nên AUROC/AUPRC của điểm này là chỉ số KHÔNG phụ thuộc ngưỡng m."""
    theta = dp["theta_c"].to_numpy()
    return (theta - projected_end_balance(dp, yhat)) / theta


def tune_margin(dp_val, yhat_val, evaluate_fn, grid=None):
    """Chọn m trên tập val để tối đa F1 (cùng tiêu chí với p* của XGBoost)."""
    grid = np.arange(-3.0, 10.01, 0.25) if grid is None else grid
    best_m, best_f1 = None, -1.0
    for m in grid:
        f1 = evaluate_fn(dp_val, alert_by_margin(dp_val, yhat_val, m))["f1"]
        if f1 > best_f1:
            best_m, best_f1 = float(m), f1
    return best_m, best_f1
