"""Sinh daily.csv cho hệ thống dự báo và cảnh báo dòng tiền cá nhân."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    BASE_SPEND_RATIO,
    DAILY_COLUMNS,
    DATA_DIR,
    END_DATE,
    INCOME_TYPES,
    N_USERS,
    PATTERNS,
    RANDOM_SEED,
    SIMULATION_START_DATE,
    START_DATE,
    TARGET_SHORTFALL_RATE,
)


def make_pay_dates(income_type: str) -> pd.DatetimeIndex:
    """Tạo ngày nhận tiền hàng tháng, có thêm ngày trước/sau giai đoạn dữ liệu."""
    if income_type == "trợ cấp đầu tháng":
        return pd.date_range("2024-11-01", "2026-07-01", freq="MS")

    months = pd.date_range("2024-10-01", "2026-07-01", freq="MS")
    return pd.DatetimeIndex([date.replace(day=25) for date in months])


def make_profiles(rng: np.random.Generator) -> pd.DataFrame:
    """Tạo hồ sơ giả lập, chia khá đều 8 tổ hợp kiểu chi tiêu × chu kỳ thu nhập."""
    combinations = [(pattern, income_type) for pattern in PATTERNS for income_type in INCOME_TYPES]
    assigned = []
    for pattern, income_type in combinations:
        assigned.extend([(pattern, income_type)] * (N_USERS // len(combinations)))
    for pattern, income_type in combinations[: N_USERS % len(combinations)]:
        assigned.append((pattern, income_type))
    rng.shuffle(assigned)

    rows = []
    for i, (pattern, income_type) in enumerate(assigned, start=1):
        monthly_income = int(rng.integers(10_000_000, 30_000_001))
        # Khác biệt mức chi giữa người dùng; trung bình gần 1.
        personal_spend_factor = float(rng.lognormal(mean=-0.5 * 0.12**2, sigma=0.12))
        # Số dư mang sang trước ngày bắt đầu mô phỏng, tương đương khoản còn lại từ kỳ trước.
        initial_balance = int(monthly_income * rng.uniform(0.05, 0.30))
        rows.append(
            {
                "user_id": f"U{i:03d}",
                "pattern": pattern,
                "income_type": income_type,
                "monthly_income": monthly_income,
                "personal_spend_factor": personal_spend_factor,
                "initial_balance": initial_balance,
            }
        )
    return pd.DataFrame(rows)


def pattern_weights(pattern: str, dates: pd.DatetimeIndex) -> np.ndarray:
    """Tạo hệ số chi tiêu theo kiểu; chuẩn hóa để trọng số nền có trung bình bằng 1."""
    n_days = len(dates)
    weights = np.ones(n_days, dtype=float)

    if pattern == "dồn đầu chu kỳ":
        early_days = max(1, int(np.ceil(n_days * 0.35)))
        weights[:early_days] = 1.65
        weights[early_days:] = 0.65
        weights = weights / weights.mean()
    elif pattern == "tăng cuối tuần":
        weekend = np.asarray(dates.dayofweek >= 5)
        weights[weekend] = 1.40
        weights[~weekend] = 0.84
        weights = weights / weights.mean()

    return weights


def create_base_daily(profiles: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Sinh chi tiêu nền và dòng tiền thu nhập trước khi hiệu chỉnh mức chi."""
    sim_start = pd.Timestamp(SIMULATION_START_DATE)
    end_date = pd.Timestamp(END_DATE)
    base_rows = []

    for profile in profiles.to_dict("records"):
        user_id = profile["user_id"]
        pattern = profile["pattern"]
        income_type = profile["income_type"]
        monthly_income = int(profile["monthly_income"])
        personal_factor = float(profile["personal_spend_factor"])
        pay_dates = make_pay_dates(income_type)

        spend_by_date = {}
        for index in range(len(pay_dates) - 1):
            cycle_start = pay_dates[index]
            next_payday = pay_dates[index + 1]
            full_cycle_dates = pd.date_range(cycle_start, next_payday - pd.Timedelta(days=1), freq="D")
            n_days = len(full_cycle_dates)

            weights = pattern_weights(pattern, full_cycle_dates)
            sigma = 0.28
            daily_noise = rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=n_days)
            factors = weights * daily_noise

            if pattern == "chi lớn bất thường":
                abnormal = rng.random(n_days) < 0.025
                abnormal_multiplier = rng.uniform(3.0, 7.0, size=n_days)
                factors = factors * np.where(abnormal, abnormal_multiplier, 1.0)

            # 0.90 là tỷ lệ chi tiêu nền ban đầu; spend_scale sẽ được hiệu chỉnh phía dưới.
            base_daily_amounts = (
                monthly_income * BASE_SPEND_RATIO / n_days * personal_factor * factors
            )
            for date, amount in zip(full_cycle_dates, base_daily_amounts):
                if sim_start <= date <= end_date:
                    spend_by_date[date] = float(amount)

        dates = pd.date_range(sim_start, end_date, freq="D")
        pay_dates_in_range = {date: monthly_income for date in pay_dates if sim_start <= date <= end_date}
        current_payday_indices = np.searchsorted(pay_dates.values, dates.values, side="right") - 1
        next_payday_indices = current_payday_indices + 1
        current_paydays = pay_dates.values[current_payday_indices]
        next_paydays = pay_dates.values[next_payday_indices]

        for j, date in enumerate(dates):
            base_rows.append(
                {
                    "user_id": user_id,
                    "date": date,
                    "base_spend": spend_by_date.get(date, 0.0),
                    "income": int(pay_dates_in_range.get(date, 0)),
                    "current_payday": pd.Timestamp(current_paydays[j]),
                    "next_payday": pd.Timestamp(next_paydays[j]),
                    "pattern": pattern,
                    "income_type": income_type,
                    "initial_balance": int(profile["initial_balance"]),
                }
            )

    result = pd.DataFrame(base_rows)
    result = result.sort_values(["user_id", "date"]).reset_index(drop=True)
    return result


def add_balances(base_daily: pd.DataFrame, spend_scale: float) -> pd.DataFrame:
    """Tính chi tiêu đã làm tròn và số dư cuối ngày cho một mức chi tiêu."""
    daily = base_daily.copy()
    daily["spend"] = np.rint(daily["base_spend"].to_numpy() * spend_scale).astype(np.int64)
    # Mỗi khi có thu nhập mới, nếu kỳ trước kết thúc với số dư âm thì đưa số dư về 0
    # trước khi cộng thu nhập. Trong mô phỏng này, phần âm biểu diễn nhu cầu chi chưa đủ tiền,
    # không phải khoản nợ/overdraft được mang nguyên sang các kỳ sau.
    daily["net_change"] = daily["income"].to_numpy(dtype=np.int64) - daily["spend"].to_numpy(dtype=np.int64)
    balances = np.zeros(len(daily), dtype=np.int64)
    all_income = daily["income"].to_numpy(dtype=np.int64)
    all_net = daily["net_change"].to_numpy(dtype=np.int64)
    all_initial = daily["initial_balance"].to_numpy(dtype=np.int64)
    # Xử lý theo từng chu kỳ thu nhập thay vì từng ngày: nhanh hơn đáng kể khi hiệu chỉnh.
    for positions in daily.groupby("user_id", sort=False).indices.values():
        positions = np.asarray(positions, dtype=int)
        group_income = all_income[positions]
        group_net = all_net[positions]
        pay_positions = np.flatnonzero(group_income > 0)
        boundaries = sorted(set([0, len(positions), *pay_positions.tolist()]))
        current_balance = int(all_initial[positions[0]])
        for start, end in zip(boundaries[:-1], boundaries[1:]):
            if start in pay_positions and current_balance < 0:
                current_balance = 0
            segment_balances = current_balance + np.cumsum(group_net[start:end], dtype=np.int64)
            balances[positions[start:end]] = segment_balances
            if len(segment_balances):
                current_balance = int(segment_balances[-1])
    daily["balance"] = balances
    daily["days_to_next_income"] = (daily["next_payday"] - daily["date"]).dt.days.astype(int)
    daily["day_in_cycle"] = (daily["date"] - daily["current_payday"]).dt.days.add(1).astype(int)
    return daily


def collect_complete_cycle_labels(daily: pd.DataFrame) -> pd.DataFrame:
    """Lấy nhãn ở các chu kỳ đủ dữ liệu và có ít nhất 30 ngày lịch sử trước chu kỳ."""
    start_date = pd.Timestamp(START_DATE)
    end_date = pd.Timestamp(END_DATE)
    rows = []

    for user_id, user_days in daily.groupby("user_id", sort=False):
        user_days = user_days.sort_values("date")
        dates = user_days["date"].to_numpy(dtype="datetime64[ns]")
        balances = user_days["balance"].to_numpy()
        pay_dates = user_days.loc[user_days["income"] > 0, "date"].to_numpy(dtype="datetime64[ns]")

        for i in range(len(pay_dates) - 1):
            cycle_start = pd.Timestamp(pay_dates[i])
            next_payday = pd.Timestamp(pay_dates[i + 1])
            if cycle_start < start_date + pd.Timedelta(days=30):
                continue
            if next_payday > end_date:
                continue
            left = int(np.searchsorted(dates, np.datetime64(cycle_start), side="left"))
            right = int(np.searchsorted(dates, np.datetime64(next_payday), side="left"))
            if right <= left:
                continue
            rows.append(
                {
                    "user_id": user_id,
                    "cycle_start_date": cycle_start,
                    "cycle_end_date": next_payday - pd.Timedelta(days=1),
                    "shortfall": int(np.any(balances[left:right] < 0)),
                }
            )
    return pd.DataFrame(rows)


def calibrate_spend_scale(base_daily: pd.DataFrame) -> tuple[float, pd.DataFrame, float]:
    """Tìm hệ số chi tiêu làm tỷ lệ chu kỳ thiếu tiền gần 25% nhất."""
    target = TARGET_SHORTFALL_RATE
    low, high = 0.20, 2.50
    candidates = []

    for _ in range(38):
        mid = (low + high) / 2
        daily = add_balances(base_daily, mid)
        labels = collect_complete_cycle_labels(daily)
        rate = float(labels["shortfall"].mean()) if not labels.empty else 0.0
        candidates.append((abs(rate - target), mid, rate))
        if rate < target:
            low = mid
        else:
            high = mid

    # Lấy hệ số có tỷ lệ gần mục tiêu nhất trong các lần thử.
    _, best_scale, _ = min(candidates, key=lambda item: item[0])
    final_daily = add_balances(base_daily, best_scale)
    final_labels = collect_complete_cycle_labels(final_daily)
    actual_rate = float(final_labels["shortfall"].mean()) if not final_labels.empty else 0.0
    return best_scale, final_daily, actual_rate


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)
    profiles = make_profiles(rng)
    base_daily = create_base_daily(profiles, rng)

    print("Đang hiệu chỉnh mức chi tiêu để tỷ lệ chu kỳ thiếu tiền gần 25%...")
    spend_scale, simulated_daily, actual_rate = calibrate_spend_scale(base_daily)

    visible_start = pd.Timestamp(START_DATE)
    visible_end = pd.Timestamp(END_DATE)
    visible = simulated_daily.loc[
        simulated_daily["date"].between(visible_start, visible_end)
    ].copy()

    visible["income"] = visible["income"].astype(np.int64)
    visible["spend"] = visible["spend"].astype(np.int64)
    visible["balance"] = visible["balance"].astype(np.int64)
    visible["date"] = visible["date"].dt.strftime("%Y-%m-%d")
    visible = visible[DAILY_COLUMNS].sort_values(["user_id", "date"]).reset_index(drop=True)
    visible.to_csv(DATA_DIR / "daily.csv", index=False, encoding="utf-8-sig")

    public_profiles = profiles[["user_id", "pattern", "income_type", "monthly_income"]].copy()
    public_profiles = public_profiles.rename(columns={"monthly_income": "monthly_income_vnd"})
    public_profiles.to_csv(DATA_DIR / "users.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "n_users": int(profiles["user_id"].nunique()),
        "daily_rows": int(len(visible)),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "days_per_user": int(visible["date"].nunique()),
        "target_shortfall_rate": TARGET_SHORTFALL_RATE,
        "actual_shortfall_rate_on_complete_cycles": actual_rate,
        "spend_scale": float(spend_scale),
        "random_seed": RANDOM_SEED,
        "note": "Dữ liệu giả lập; không phải giao dịch hay hồ sơ ngân hàng thực.",
    }
    (DATA_DIR / "generation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Đã lưu: {DATA_DIR / 'daily.csv'}")
    print(f"Số người: {metadata['n_users']:,}; số dòng ngày: {metadata['daily_rows']:,}")
    print(f"Hệ số chi tiêu: {spend_scale:.4f}; tỷ lệ thiếu tiền chu kỳ đầy đủ: {actual_rate:.2%}")


if __name__ == "__main__":
    main()
