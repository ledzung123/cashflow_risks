#!/usr/bin/env python3
"""
simulate.py - Sinh dữ liệu chi tiêu mô phỏng (Nhóm 11, SPEC v1 mục 3-4).

Chạy:
  python src/simulate.py --users 300 --seed 42 --out data/daily.csv      # đầy đủ
  python src/simulate.py --users 20  --seed 42 --out data/sample_v0.csv  # bản v0 nhỏ
  python src/simulate.py --users 300 --seed 42 --check                   # in thống kê + vẽ hình kiểm tra

Giả định của simulator (ghi vào mục "Giới hạn" của báo cáo):
  - Thu nhập đến đúng lịch, số tiền cố định theo từng người.
  - Người dùng KHÔNG tự cắt chi khi số dư thấp.
  - Khoản thiếu hụt (số dư < 0) được xoay xở bên ngoài; chu kỳ sau chỉ mang sang phần dư dương,
    tối đa --carry-cap x thu nhập (phần dư lớn hơn được chuyển sang tiết kiệm).
"""
import argparse
import os
from datetime import date

import numpy as np
import pandas as pd

PATTERNS = ["even", "front", "weekend", "spike"]
INCOME_TYPES = ["allowance_1st", "salary_25"]
N_CYCLES = 24                      # 24 chu kỳ ~ 24 tháng (SPEC v2.0)
START_YEAR, START_MONTH = 2025, 1
# train: huấn luyện XGBoost | calib: chỉ dựng phân phối sai số cho p | val: early stopping, tune m và p* | test: chỉ đánh giá
SPLIT_OF_CYCLE = {**{k: "train" for k in range(0, 12)},
                  **{k: "calib" for k in range(12, 16)},
                  **{k: "val" for k in range(16, 20)},
                  **{k: "test" for k in range(20, 24)}}

# Hệ số nhân cho phân tích độ nhạy (mặc định 1.0 = tham số đã đóng băng trong SPEC mục 9)
PARAMS = {"weekend": 1.0, "front": 1.0, "noise": 1.0, "spike": 1.0, "shock": 1.0}

DAYS_PER_CYCLE = 30.4
ZERO_DAY_PROB = 0.05               # xác suất một ngày không chi gì
SPIKE_SHARE = 0.25                 # kiểu "spike": 25% tổng chi nằm ở các khoản lớn bất thường
SPIKE_SIZE = 6.0                   # một khoản lớn ~ 6 lần chi tiêu trung bình ngày


def _spike_share():
    return min(SPIKE_SHARE * PARAMS["spike"], 0.9)


def cycle_bounds(income_type, k):
    """Ngày bắt đầu và độ dài (ngày) của chu kỳ thứ k."""
    def month(idx):
        return START_YEAR + (START_MONTH - 1 + idx) // 12, (START_MONTH - 1 + idx) % 12 + 1
    y, m = month(k)
    ny, nm = month(k + 1)
    day = 1 if income_type == "allowance_1st" else 25
    start, nxt = date(y, m, day), date(ny, nm, day)
    return start, (nxt - start).days


def lognormal_mean1(rng, sigma, size):
    """Nhiễu log-normal có kỳ vọng = 1."""
    return np.exp(rng.normal(0.0, sigma, size) - sigma ** 2 / 2)


def make_profile(pattern, dates, rng, strength):
    """Hệ số nhân theo ngày (trung bình = 1 trên cả chu kỳ) mô tả kiểu chi tiêu."""
    L = len(dates)
    if pattern == "front":                       # dồn vào đầu chu kỳ
        raw = 1.0 + strength * np.exp(-np.arange(L) / 8.0)
    elif pattern == "weekend":                   # tăng vào cuối tuần
        wd = np.array([d.weekday() for d in dates])
        raw = np.where(wd >= 5, strength, 0.7)
    elif pattern == "spike":                     # nền thấp hơn, phần còn lại là các khoản lớn
        raw = np.full(L, 1.0 - _spike_share())
        return raw
    else:                                        # even
        raw = np.ones(L)
    return raw / raw.mean()


def simulate_user(uid, pattern, income_type, rho_lo, rho_hi, seed, carry_cap):
    rng = np.random.default_rng([seed, uid])
    if income_type == "allowance_1st":
        income = np.round(rng.uniform(3.0e6, 5.0e6) / 1e5) * 1e5
    else:
        income = np.round(rng.uniform(7.0e6, 15.0e6) / 1e5) * 1e5
    rho = rng.uniform(rho_lo, rho_hi)            # tổng chi chu kỳ / thu nhập (kỳ vọng)
    mu = rho * income / DAYS_PER_CYCLE            # chi tiêu trung bình/ngày
    sigma = rng.uniform(0.35, 0.60) * PARAMS["noise"]   # độ nhiễu hằng ngày của người này
    if pattern == "front":
        strength = rng.uniform(1.2, 2.0) * PARAMS["front"]
    elif pattern == "weekend":
        strength = 1.0 + (rng.uniform(1.8, 2.5) - 1.0) * PARAMS["weekend"]
    else:
        strength = 0.0

    carry = np.round(rng.uniform(0.0, 0.3) * income / 1e5) * 1e5
    rows = []
    for k in range(N_CYCLES):
        start, L = cycle_bounds(income_type, k)
        dates = pd.date_range(start, periods=L)
        prof = make_profile(pattern, dates, rng, strength)
        cyc_shock = np.exp(rng.normal(0.0, 0.07 * PARAMS["shock"]))     # "tháng này tiêu nhiều/ít hơn"
        noise = lognormal_mean1(rng, sigma, L)
        spend = mu * cyc_shock * prof * noise
        spend = spend * (rng.random(L) > ZERO_DAY_PROB) / (1 - ZERO_DAY_PROB)
        if pattern == "spike":
            lam = L * _spike_share() / SPIKE_SIZE
            n = min(rng.poisson(lam), L)
            days = rng.choice(L, size=n, replace=False)
            spend[days] += mu * SPIKE_SIZE * lognormal_mean1(rng, 0.4, n)
        spend = np.round(spend / 1000.0) * 1000.0

        bal = carry
        for d in range(L):
            inc = income if d == 0 else 0.0
            bal = bal + inc - spend[d]
            rows.append((uid, dates[d].date().isoformat(), int(spend[d]), int(inc), int(bal),
                         k, d + 1, L - (d + 1), pattern, income_type, SPLIT_OF_CYCLE[k]))
        # thiếu hụt được xoay xở ngoài mô hình; phần dư lớn được chuyển sang tiết kiệm
        carry = min(max(bal, 0.0), carry_cap * income)
    meta = dict(user_id=uid, pattern=pattern, income_type=income_type,
                income=int(income), rho=round(rho, 3), sigma=round(sigma, 3),
                strength=round(strength, 3))
    return rows, meta


def simulate(n_users, seed, rho_lo, rho_hi, carry_cap, params=None):
    """params: dict hệ số nhân (weekend, front, noise, spike, shock) cho phân tích độ nhạy; None = mặc định đóng băng."""
    saved = dict(PARAMS)
    if params:
        PARAMS.update(params)
    try:
        return _simulate(n_users, seed, rho_lo, rho_hi, carry_cap)
    finally:
        PARAMS.clear(); PARAMS.update(saved)


def _simulate(n_users, seed, rho_lo, rho_hi, carry_cap):
    all_rows, metas = [], []
    for uid in range(n_users):
        pattern = PATTERNS[uid % 4]                      # 4 kiểu chi tiêu chia đều
        income_type = INCOME_TYPES[(uid // 4) % 2]       # 2 chu kỳ thu nhập xen kẽ
        rows, meta = simulate_user(uid, pattern, income_type, rho_lo, rho_hi, seed, carry_cap)
        all_rows += rows
        metas.append(meta)
    cols = ["user_id", "date", "spend", "income", "balance", "cycle_id", "day_in_cycle",
            "D", "pattern", "income_type", "split"]
    return pd.DataFrame(all_rows, columns=cols), pd.DataFrame(metas)


# ---------------------------------------------------------------- kiểm tra / thống kê
def quick_labels(df):
    """Bản rút gọn của SPEC mục 2 để ước lượng tỉ lệ thiếu tiền (KHÔNG thay labels.py của Người 2)."""
    out = []
    for uid, g in df.groupby("user_id"):
        g = g.reset_index(drop=True)
        for c in range(1, N_CYCLES):                     # chu kỳ 0 chưa đủ 14 ngày lịch sử
            cyc = g[g.cycle_id == c]
            prev14 = g[(g.cycle_id == c - 1)].spend.iloc[-14:]
            theta = prev14.mean()
            y = int(cyc.balance.iloc[-1] < theta)
            pts = cyc[(cyc.D >= 3) & (cyc.balance >= theta)]
            out.append(dict(user_id=uid, cycle_id=c, pattern=cyc.pattern.iloc[0],
                            split=cyc.split.iloc[0], y_cycle=y, n_points=len(pts)))
    return pd.DataFrame(out)


def check(df, meta, fig_path):
    lab = quick_labels(df)
    print(f"\nSố dòng: {len(df):,} | số người: {df.user_id.nunique()} | số chu kỳ/người: {N_CYCLES}")
    print("\nTỉ lệ chu kỳ thiếu tiền (balance cuối chu kỳ < theta):")
    print(f"  tổng: {lab.y_cycle.mean():.1%}")
    print(lab.groupby("pattern").y_cycle.mean().map("{:.1%}".format).to_string())
    print(lab.groupby("split").y_cycle.mean().map("{:.1%}".format).to_string())
    pts = lab.n_points
    print(f"\nTỉ lệ ĐIỂM QUYẾT ĐỊNH dương (đã loại điểm balance<theta, D<3): "
          f"{(lab.y_cycle * pts).sum() / pts.sum():.1%}")

    d = df.copy()
    d["rel"] = d.spend / d.groupby("user_id").spend.transform("mean")
    d["wd"] = pd.to_datetime(d.date).dt.weekday
    d["phase"] = pd.cut(d.day_in_cycle, [0, 7, 15, 40], labels=["ngày 1-7", "ngày 8-15", "ngày 16-hết"])
    t1 = d.pivot_table(index="pattern", columns="phase", values="rel", aggfunc="mean", observed=True)
    d["we"] = np.where(d.wd >= 5, "cuối tuần", "ngày thường")
    t2 = d.pivot_table(index="pattern", columns="we", values="rel", aggfunc="mean")
    print("\nChi tiêu tương đối (1.0 = trung bình của chính người đó) theo giai đoạn chu kỳ:")
    print(t1.round(2).to_string())
    print("\nTheo cuối tuần / ngày thường:")
    print(t2.round(2).to_string())
    print("\nTổng chi / thu nhập mỗi chu kỳ (trung bình):",
          round((df.groupby(["user_id", "cycle_id"]).spend.sum() /
                 df.groupby(["user_id", "cycle_id"]).income.sum()).mean(), 3))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    for p in PATTERNS:
        s = d[(d.pattern == p) & (d.day_in_cycle <= 28)].groupby("day_in_cycle").rel.mean()
        ax[0, 0].plot(s.index, s.values, label=p)
        w = d[d.pattern == p].groupby("wd").rel.mean()
        ax[0, 1].plot(["T2", "T3", "T4", "T5", "T6", "T7", "CN"], w.values, marker="o", label=p)
    ax[0, 0].set(title="Chi tiêu tương đối theo ngày trong chu kỳ", xlabel="day_in_cycle")
    ax[0, 1].set(title="Chi tiêu tương đối theo thứ trong tuần")
    ax[0, 0].legend(); ax[0, 1].legend()
    for p in PATTERNS:
        uid = int(meta[(meta.pattern == p) & (meta.income_type == "allowance_1st")].user_id.iloc[0])
        g = df[(df.user_id == uid) & (df.cycle_id.isin([6, 7, 8]))]
        ax[1, 0].plot(range(len(g)), g.balance.values / 1e6, label=f"{p} (user {uid})")
    ax[1, 0].axhline(0, color="k", lw=0.5)
    ax[1, 0].set(title="Số dư (triệu VND) qua 3 chu kỳ - 4 người mẫu", xlabel="ngày")
    ax[1, 0].legend()
    ratio = (df.groupby(["user_id", "cycle_id"]).spend.sum() /
             df.groupby(["user_id", "cycle_id"]).income.sum())
    ax[1, 1].hist(ratio, bins=40)
    ax[1, 1].axvline(1.0, color="r", ls="--")
    ax[1, 1].set(title="Tổng chi / thu nhập mỗi chu kỳ", xlabel="tỉ lệ")
    fig.tight_layout()
    os.makedirs(os.path.dirname(fig_path) or ".", exist_ok=True)
    fig.savefig(fig_path, dpi=110)
    print(f"\nĐã lưu hình kiểm tra: {fig_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rho-low", type=float, default=0.85)
    ap.add_argument("--rho-high", type=float, default=1.05)
    ap.add_argument("--carry-cap", type=float, default=0.10)
    ap.add_argument("--out", default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fig", default="results/sanity_v0.png")
    a = ap.parse_args()

    df, meta = simulate(a.users, a.seed, a.rho_low, a.rho_high, a.carry_cap)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        df.to_csv(a.out, index=False)
        meta.to_csv(os.path.splitext(a.out)[0] + "_users.csv", index=False)
        print(f"Đã ghi {a.out} ({len(df):,} dòng) và {os.path.splitext(a.out)[0] + '_users.csv'}")
    if a.check:
        check(df, meta, a.fig)
