"""
labels.py - Nhãn và bảng điểm quyết định `dp` (SPEC v1.1 mục 2 và 5). Người 2.

Quy ước:
  - prepare_df(df): sắp xếp theo (user_id, date), reset index. MỌI hàm khác giả định df đã qua prepare_df.
  - dp.row = vị trí của ngày t trong df đã prepare (dùng để lấy lịch sử <= t và chi tiêu thật t+1..t+D).
"""
import warnings

import numpy as np
import pandas as pd

HORIZON_MAX = 31          # D tối đa (chu kỳ dài nhất = 31 ngày)
THETA_WINDOW = 14         # theta_c = chi tiêu TB/ngày của 14 ngày trước ngày nhận tiền
MIN_D = 3                 # chỉ xét điểm quyết định còn >= 3 ngày đến kỳ nhận tiền
MIN_HISTORY = 28          # cửa sổ dài nhất mà B2 và đặc trưng (scale = TB 28 ngày) đọc ngược từ ngày t


def prepare_df(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["user_id", "date"]).reset_index(drop=True)
    df["wd"] = df["date"].dt.weekday
    return df


def make_dp(df):
    """Bảng điểm quyết định. Mỗi dòng = (người, chu kỳ, ngày t) thỏa SPEC mục 2."""
    spend = df["spend"].to_numpy(dtype=float)
    hist_pos = df.groupby("user_id").cumcount().to_numpy()      # số ngày lịch sử của chính người đó trước dòng này
    grp = df.groupby(["user_id", "cycle_id"], sort=False)

    first_row = grp.cumcount() == 0
    start_rows = np.flatnonzero(first_row.to_numpy())
    keys = df.loc[start_rows, ["user_id", "cycle_id"]].reset_index(drop=True)

    # theta_c: trung bình 14 ngày ngay trước ngày nhận tiền (chu kỳ 0 không đủ lịch sử -> bỏ)
    theta = np.full(len(keys), np.nan)
    for i, r0 in enumerate(start_rows):
        if keys.cycle_id[i] >= 1 and hist_pos[r0] >= THETA_WINDOW:     # tránh đọc lẫn dữ liệu người khác
            theta[i] = spend[r0 - THETA_WINDOW:r0].mean()
    keys["theta_c"] = theta

    d = df.merge(keys, on=["user_id", "cycle_id"], how="left")
    d["row"] = np.arange(len(d))
    d = d[d.cycle_id >= 1].copy()

    below = d.balance < d.theta_c
    end_bal = d.groupby(["user_id", "cycle_id"]).balance.transform("last")
    d["end_balance"] = end_bal
    d["y"] = (end_bal < d.theta_c).astype(int)
    # dip_day: ngày (day_in_cycle) đầu tiên balance < theta_c; số dư chỉ giảm nên y=1 <=> có dip
    first_dip = d[below].groupby(["user_id", "cycle_id"]).day_in_cycle.min().rename("dip_day").reset_index()
    d = d.merge(first_dip, on=["user_id", "cycle_id"], how="left")

    keep = (d.D >= MIN_D) & (d.balance >= d.theta_c)
    # B2 và chuẩn hóa XGB (TB 28 ngày) cần đủ 28 ngày lịch sử của CHÍNH người đó, nếu không sẽ đọc lẫn dữ liệu khác
    # (chỉ xảy ra với CSV thật có chu kỳ ngắn; dữ liệu mô phỏng luôn đủ vì chu kỳ 0 dài >= 31 ngày).
    short = keep & (hist_pos[d["row"].to_numpy()] < MIN_HISTORY - 1)
    if short.any():
        warnings.warn(f"Bỏ {int(short.sum())} điểm quyết định chưa đủ {MIN_HISTORY} ngày lịch sử.", stacklevel=2)
        keep &= ~short
    if not keep.any():
        raise ValueError(f"Không còn điểm quyết định nào: cần ít nhất {MIN_HISTORY} ngày lịch sử trước điểm quyết định đầu tiên.")
    dp = d[keep].rename(columns={"day_in_cycle": "t", "balance": "balance_t"})
    dp = dp[["user_id", "cycle_id", "t", "row", "date", "balance_t", "D", "theta_c", "end_balance",
             "y", "dip_day", "split", "pattern", "income_type"]].reset_index(drop=True)
    return dp


def future_actual(df, dp):
    """Chi tiêu thật của ngày t+1..t+D, mảng (n_dp, 31), NaN phía sau D."""
    spend = df["spend"].to_numpy(dtype=float)
    h = np.arange(1, HORIZON_MAX + 1)[None, :]
    rows = dp["row"].to_numpy()[:, None] + h
    out = spend[np.minimum(rows, len(spend) - 1)]
    out[h > dp["D"].to_numpy()[:, None]] = np.nan
    return out
