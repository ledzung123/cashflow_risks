"""
risk.py - Bước 5: từ dự báo chi tiêu -> xác suất thiếu tiền p -> cảnh báo p > p*. Người 4.

Sự kiện cần ước lượng (SPEC mục 2): chu kỳ thiếu tiền <=> số dư cuối chu kỳ < theta_c
  <=> tổng chi D ngày tới S_D > balance_t - theta_c      (số dư chỉ giảm giữa chu kỳ)
  => p_t = P(S_D > balance_t - theta_c | thông tin đến ngày t)

Hai cách ước lượng phân phối của S_D từ SAI SỐ DỰ BÁO trên tập val:
  "mc"  : mô phỏng K quỹ đạo chi D ngày = dự báo + sd_người × sai số chuẩn hóa lấy mẫu độc lập theo ngày
  "cum" : lấy thẳng phân phối thực nghiệm của tỉ lệ q = (tổng chi thật)/(tổng chi dự báo) trên val,
          chia nhóm theo D và theo độ biến động của người đó (cv); p = P(q > ngưỡng/tổng dự báo)
Phân phối sai số dựng trên tập CALIB; p* và early stopping dùng tập VAL; test chỉ đánh giá (SPEC v2.0: bốn tập tách riêng).
"""
import numpy as np
import pandas as pd

from labels import HORIZON_MAX, future_actual
from features import row_features

D_EDGES = [5, 8, 12, 17, 22]          # nhóm D: [3,4] [5,7] [8,11] [12,16] [17,21] [22,31]
MIN_BUCKET = 30
SD_FLOOR = 0.25                       # sd tối thiểu = 25% mức chi TB 28 ngày
BIG_CUT = 0.5                         # "hay có khoản chi cực lớn": >= 0,5 ngày chi > 5x mức TB / 28 ngày (trên tối đa 84 ngày)


def volatility(df, dp):
    """sd và cv của từng điểm quyết định, chỉ dùng dữ liệu <= ngày t."""
    rf = row_features(df)
    rows = dp["row"].to_numpy()
    sd = np.maximum(rf["std14"][rows], SD_FLOOR * rf["scale"][rows])
    cv = rf["std14"][rows] / rf["mean14"][rows]
    return sd, cv


def bigdays(df, dp):
    """Tần suất chi cực lớn (> 5 lần mức TB 28 ngày): số ngày / 28 ngày, tính trên tối đa 84 ngày gần nhất,
    chỉ dùng dữ liệu <= ngày t. (Ngưỡng 3 lần không phân biệt được người "spike" với người chi nhiều cuối tuần.)"""
    return row_features(df)["bigrate"][dp["row"].to_numpy()]


def _bucket(D, cv, cuts, big=None):
    b = np.digitize(D, D_EDGES) * 3 + np.digitize(cv, cuts)
    return b if big is None else b * 2 + (np.asarray(big) >= BIG_CUT).astype(int)


def cum_pool(dp, yhat, df, cv, big=None):
    s_hat = np.maximum(np.nansum(yhat, axis=1), 1.0)
    s_act = np.nansum(future_actual(df, dp), axis=1)
    return dict(q=s_act / s_hat, D=dp["D"].to_numpy(), cv=cv, big=big, cycle=dp["cycle_id"].to_numpy())


def _groups(pool, D, cv, big):
    """Gán mỗi điểm truy vấn vào nhóm (D, cv[, big]) và trả về các mẫu q của nhóm đó trong pool."""
    cuts = np.quantile(pool["cv"], [1 / 3, 2 / 3])
    use_big = pool.get("big") is not None
    b_pool = _bucket(pool["D"], pool["cv"], cuts, pool["big"] if use_big else None)
    d_pool = np.digitize(pool["D"], D_EDGES)
    b_q = _bucket(D, cv, cuts, big if use_big else None)
    div = 6 if use_big else 3
    out = {}
    for b in np.unique(b_q):
        qs = pool["q"][b_pool == b]
        if len(qs) < MIN_BUCKET:                                  # nhóm quá nhỏ -> chỉ chia theo D
            qs = pool["q"][d_pool == (b // div)]
        if len(qs) < MIN_BUCKET:                                  # vẫn quá nhỏ -> dùng toàn bộ phân phối
            qs = pool["q"]
        out[b] = np.sort(qs)
    return b_q, out


def cum_prob(pool, dp, yhat, cv, big=None):
    s_hat = np.maximum(np.nansum(yhat, axis=1), 1.0)
    z = (dp["balance_t"].to_numpy() - dp["theta_c"].to_numpy()) / s_hat
    b_q, groups = _groups(pool, dp["D"].to_numpy(), cv, big)
    p = np.empty(len(dp))
    for b, qs in groups.items():
        m = b_q == b
        p[m] = 1.0 - np.searchsorted(qs, z[m], side="right") / len(qs)
    return p


def cum_coverage(pool, dp, yhat, df, cv, big=None, levels=(0.5, 0.8, 0.9)):
    """Chỉ báo (n, len(levels)): tổng chi thật D ngày có nằm trong khoảng dự báo trung tâm mức `levels` không."""
    s_hat = np.maximum(np.nansum(yhat, axis=1), 1.0)
    q_act = np.nansum(future_actual(df, dp), axis=1) / s_hat
    b_q, groups = _groups(pool, dp["D"].to_numpy(), cv, big)
    inside = np.zeros((len(dp), len(levels)), dtype=bool)
    for b, qs in groups.items():
        m = b_q == b
        for k, lev in enumerate(levels):
            lo, hi = np.quantile(qs, [(1 - lev) / 2, 1 - (1 - lev) / 2])
            inside[m, k] = (q_act[m] >= lo) & (q_act[m] <= hi)
    return inside


def mc_pool(dp, yhat, df, sd):
    """Sai số chuẩn hóa (thật - dự báo)/sd, mảng (n, 31), NaN sau D."""
    return (future_actual(df, dp) - yhat) / sd[:, None]


def mc_prob(zmat_pool, dp, yhat, sd, K=500, seed=0, chunk=100, max_pool=300_000):
    rng = np.random.default_rng(seed)
    pool = zmat_pool[~np.isnan(zmat_pool)]
    if len(pool) > max_pool:
        pool = rng.choice(pool, max_pool, replace=False)
    thr = dp["balance_t"].to_numpy() - dp["theta_c"].to_numpy()
    valid = ~np.isnan(yhat)
    Y = np.nan_to_num(yhat)
    n, p = len(dp), np.empty(len(dp))
    for i0 in range(0, n, chunk):
        sl = slice(i0, min(i0 + chunk, n))
        z = pool[rng.integers(0, len(pool), size=(Y[sl].shape[0], K, HORIZON_MAX))]
        spend = np.maximum(0.0, Y[sl][:, None, :] + sd[sl][:, None, None] * z)
        total = (spend * valid[sl][:, None, :]).sum(axis=2)
        p[sl] = (total > thr[sl][:, None]).mean(axis=1)
    return p


def fit_predict(method, dp_calib, yhat_calib, targets, df, K=500, seed=0):
    """Dựng phân phối sai số trên tập CALIB, rồi tính p cho từng (dp, yhat) trong `targets` (val, test, ...).
    method: "cum" (chia nhóm theo D và cv), "cumb" (thêm nhóm theo số ngày chi lớn big28), "mc" (mô phỏng K quỹ đạo).
    Tập calib chỉ dùng cho việc này: không dùng để chọn p*, early stopping hay đánh giá."""
    sd_c, cv_c = volatility(df, dp_calib)
    if method in ("cum", "cumb"):
        big_c = bigdays(df, dp_calib) if method == "cumb" else None
        pool = cum_pool(dp_calib, yhat_calib, df, cv_c, big_c)
    else:
        pool = mc_pool(dp_calib, yhat_calib, df, sd_c)
    out = []
    for dp, yhat in targets:
        sd, cv = volatility(df, dp)
        if method in ("cum", "cumb"):
            out.append(cum_prob(pool, dp, yhat, cv, bigdays(df, dp) if method == "cumb" else None))
        else:
            out.append(mc_prob(pool, dp, yhat, sd, K, seed))
    return out


def tune_pstar(dp_val, p_val, evaluate_fn, alert_fn=None, grid=None):
    """Chọn p* trên val để tối đa F1 (cùng tiêu chí với biên m của baseline)."""
    grid = np.arange(0.05, 0.96, 0.01) if grid is None else grid
    best, best_f1 = None, -1.0
    for t in grid:
        a = p_val > t
        if alert_fn is not None:
            a = alert_fn(dp_val, a)
        f1 = evaluate_fn(dp_val, a)["f1"]
        if f1 > best_f1:
            best, best_f1 = float(t), f1
    return best, best_f1


def persist(dp, alert, k):
    """Chỉ cảnh báo khi điều kiện đúng k ngày liên tiếp trong cùng chu kỳ (giảm báo nhầm)."""
    if k <= 1:
        return np.asarray(alert, dtype=bool)
    s = pd.Series(np.asarray(alert, dtype=float))
    key = [dp["user_id"].to_numpy(), dp["cycle_id"].to_numpy()]
    r = s.groupby(key).transform(lambda x: x.rolling(k, min_periods=k).min()).fillna(0.0)
    return r.to_numpy().astype(bool)


def brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def ece(p, y, bins=10):
    p, y = np.asarray(p), np.asarray(y)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum((idx == b).mean() * abs(y[idx == b].mean() - p[idx == b].mean())
                     for b in range(bins) if (idx == b).any()))


def coverage_eval(method, dp_calib, yhat_calib, dp, yhat, df, levels=(0.5, 0.8, 0.9)):
    """Độ phủ khoảng dự báo của tổng chi D ngày (phân phối dựng trên calib). Trả về mảng (n, len(levels)) hoặc None với 'mc'."""
    if method not in ("cum", "cumb"):
        return None
    big_c = bigdays(df, dp_calib) if method == "cumb" else None
    pool = cum_pool(dp_calib, yhat_calib, df, volatility(df, dp_calib)[1], big_c)
    big = bigdays(df, dp) if method == "cumb" else None
    return cum_coverage(pool, dp, yhat, df, volatility(df, dp)[1], big, levels)
