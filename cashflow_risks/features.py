"""
features.py - Đặc trưng cho dự báo TRỰC TIẾP chi tiêu ngày t+h (h = 1..D). Người 3.

Mỗi mẫu = (điểm quyết định, h). Mọi đặc trưng chỉ dùng dữ liệu <= ngày t:
  - thống kê trượt 7/14/28 ngày kết thúc ở ngày t;
  - lịch sử CÁ NHÂN: chi tiêu trung bình tại cùng "ngày-trong-chu-kỳ" của ngày đích ở các chu kỳ TRƯỚC
    (tối đa K_PREV chu kỳ gần nhất, cửa sổ làm mượt ±SMOOTH ngày). Đây là đặc trưng giúp mô hình chung
    nhận ra người dồn chi tiêu vào đầu chu kỳ mà không dùng cột `pattern`;
  - dự báo của B1/B2 (chuẩn hóa) làm đặc trưng.
Mục tiêu được chuẩn hóa: spend_{t+h} / scale_t, scale_t = chi tiêu TB 28 ngày gần nhất (để gộp người chi nhiều/ít).
"""
import numpy as np
import pandas as pd

from labels import HORIZON_MAX
from baselines import predict_spend_b2

K_PREV = 6        # số chu kỳ trước dùng cho lịch sử cá nhân
SMOOTH = 2        # làm mượt ±2 ngày quanh ngày-trong-chu-kỳ của ngày đích
DAY_AXIS = 33     # chỉ số day_in_cycle 1..31 (dư chỗ)

FEATURES = [
    "h", "tgt_wd", "tgt_weekend", "tgt_dic", "days_after", "dic_t", "D",
    "mean7_rel", "mean14_rel", "std14_rel", "max14_rel", "last1_rel", "big28", "we_ratio",
    "bal_rel", "theta_rel", "b2_rel", "hist_dic_rel", "hist_smooth_rel", "n_prev",
]


def _roll(df, col, w, fn="mean", min_periods=None):
    g = df.groupby("user_id")[col]
    if fn == "mean":
        return g.transform(lambda s: s.rolling(w, min_periods=min_periods).mean()).to_numpy()
    if fn == "std":
        return g.transform(lambda s: s.rolling(w).std()).to_numpy()
    if fn == "max":
        return g.transform(lambda s: s.rolling(w).max()).to_numpy()
    if fn == "sum":
        return g.transform(lambda s: s.rolling(w).sum()).to_numpy()
    raise ValueError(fn)


def row_features(df):
    """Thống kê trượt cho MỌI dòng của df (chỉ dùng dữ liệu <= dòng đó)."""
    d = pd.DataFrame({"user_id": df.user_id.to_numpy(), "spend": df.spend.to_numpy(float)})
    d["m28"] = _roll(d, "spend", 28)
    d["big"] = (d.spend > 3.0 * d.m28).astype(float)
    d["huge"] = (d.spend > 5.0 * d.m28).astype(float)
    we = (df.wd.to_numpy() >= 5)
    d["s_we"], d["n_we"] = d.spend * we, we.astype(float)
    d["s_wd"], d["n_wd"] = d.spend * ~we, (~we).astype(float)
    out = {
        "scale": d.m28.to_numpy(),
        "mean7": _roll(d, "spend", 7), "mean14": _roll(d, "spend", 14),
        "std14": _roll(d, "spend", 14, "std"), "max14": _roll(d, "spend", 14, "max"),
        "last1": d.spend.to_numpy(),
        "big28": _roll(d, "big", 28, "sum"),
        # tần suất chi CỰC lớn: số ngày chi > 5x mức TB / 28 ngày, trên tối đa 84 ngày gần nhất (dùng cho risk.py)
        "bigrate": _roll(d, "huge", 84, "mean", min_periods=28) * 28.0,
    }
    sw, nw = _roll(d, "s_we", 28, "sum"), _roll(d, "n_we", 28, "sum")
    sd, nd = _roll(d, "s_wd", 28, "sum"), _roll(d, "n_wd", 28, "sum")
    out["we_ratio"] = (sw / nw) / (sd / nd + 1e-9)
    return out


def _shift_sum(X, s):
    """Y[:, d] = X[:, d + s] (điền 0 ngoài biên)."""
    Y = np.zeros_like(X)
    if s > 0:
        Y[:, :-s] = X[:, s:]
    elif s < 0:
        Y[:, -s:] = X[:, :s]
    else:
        Y[:] = X
    return Y


def history_by_dic(df, dp):
    """Tổng và số lần quan sát chi tiêu theo ngày-trong-chu-kỳ ở các chu kỳ TRƯỚC (n_dp, DAY_AXIS)."""
    uniq, uidx_all = np.unique(df.user_id.to_numpy(), return_inverse=True)
    n_cyc = int(df.cycle_id.max()) + 1
    A = np.full((len(uniq), n_cyc, DAY_AXIS), np.nan)
    A[uidx_all, df.cycle_id.to_numpy(), df.day_in_cycle.to_numpy()] = df.spend.to_numpy(float)
    S, C = np.nan_to_num(A), (~np.isnan(A)).astype(float)
    ES = np.zeros((len(uniq), n_cyc + 1, DAY_AXIS)); EC = np.zeros_like(ES)
    ES[:, 1:], EC[:, 1:] = np.cumsum(S, axis=1), np.cumsum(C, axis=1)
    u = np.searchsorted(uniq, dp.user_id.to_numpy())
    c = dp.cycle_id.to_numpy()
    lo = np.maximum(c - K_PREV, 0)
    SW, CW = ES[u, c] - ES[u, lo], EC[u, c] - EC[u, lo]          # chỉ các chu kỳ < c
    SS = sum(_shift_sum(SW, s) for s in range(-SMOOTH, SMOOTH + 1))
    CS = sum(_shift_sum(CW, s) for s in range(-SMOOTH, SMOOTH + 1))
    return SW, CW, SS, CS


def build_matrix(df, dp, with_target=False):
    """Trả về X (m, F), meta (idx_dp, h, scale) và y_rel nếu with_target."""
    rf = row_features(df)
    rows = dp["row"].to_numpy()
    scale = rf["scale"][rows]
    rel = lambda a: a[rows] / scale
    t, D = dp["t"].to_numpy(), dp["D"].to_numpy()
    wd_t = df["wd"].to_numpy()[rows]
    SW, CW, SS, CS = history_by_dic(df, dp)
    b2 = predict_spend_b2(df, dp)                                 # (n, 31) VND
    spend = df["spend"].to_numpy(float)
    base = {
        "mean7_rel": rel(rf["mean7"]), "mean14_rel": rel(rf["mean14"]), "std14_rel": rel(rf["std14"]),
        "max14_rel": rel(rf["max14"]), "last1_rel": rel(rf["last1"]), "big28": rf["big28"][rows],
        "we_ratio": rf["we_ratio"][rows], "bal_rel": dp["balance_t"].to_numpy() / scale,
        "theta_rel": dp["theta_c"].to_numpy() / scale, "dic_t": t, "D": D,
    }
    Xs, idxs, hs, ys = [], [], [], []
    for h in range(1, HORIZON_MAX + 1):
        sel = np.flatnonzero(D >= h)
        if len(sel) == 0:
            continue
        td = t[sel] + h                                           # ngày-trong-chu-kỳ của ngày đích
        cols = {"h": np.full(len(sel), h), "tgt_wd": (wd_t[sel] + h) % 7,
                "tgt_dic": td, "days_after": D[sel] - h}
        cols["tgt_weekend"] = (cols["tgt_wd"] >= 5).astype(int)
        for k, v in base.items():
            cols[k] = v[sel]
        cols["b2_rel"] = b2[sel, h - 1] / scale[sel]
        with np.errstate(invalid="ignore", divide="ignore"):
            cols["hist_dic_rel"] = np.where(CW[sel, td] > 0, SW[sel, td] / CW[sel, td], np.nan) / scale[sel]
            cols["hist_smooth_rel"] = np.where(CS[sel, td] > 0, SS[sel, td] / CS[sel, td], np.nan) / scale[sel]
        cols["n_prev"] = CW[sel, td]
        Xs.append(np.column_stack([cols[f] for f in FEATURES]).astype(np.float32))
        idxs.append(sel); hs.append(np.full(len(sel), h))
        if with_target:
            ys.append(spend[rows[sel] + h] / scale[sel])
    X = np.vstack(Xs)
    meta = {"idx": np.concatenate(idxs), "h": np.concatenate(hs)}
    meta["scale"] = scale[meta["idx"]]
    return (X, meta, np.concatenate(ys).astype(np.float32)) if with_target else (X, meta)
