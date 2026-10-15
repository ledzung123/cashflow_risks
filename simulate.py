import argparse
import os
import random
import numpy as np
import pandas as pd


def generate_cash_flow_data(n_users=300, months=18, start_date="2025-01-01", seed=42):
    rng = np.random.default_rng(seed)
    random.seed(seed)
    np.random.seed(seed)

    start_dt = pd.to_datetime(start_date)
    end_dt = start_dt + pd.DateOffset(months=months)
    date_range = pd.date_range(start=start_dt, end=end_dt, freq="D")

    all_data = []
    income_cycles = ["trợ cấp đầu tháng", "lương ngày 25"]
    spend_patterns = ["đều", "dồn đầu chu kỳ", "tăng cuối tuần", "bất thường"]

    # Chia đều 4 kiểu chi tiêu x 2 chu kỳ thu nhập (8 tổ hợp)
    combos = [(ic, sp) for ic in income_cycles for sp in spend_patterns]
    user_combos = [combos[(i - 1) % len(combos)] for i in range(1, n_users + 1)]
    rng.shuffle(user_combos)

    for i in range(1, n_users + 1):
        user_id = f"U{str(i).zfill(3)}"
        income_cycle, spend_pattern = user_combos[i - 1]

        # Thu nhập theo SPEC Mục 9
        if income_cycle == "trợ cấp đầu tháng":
            monthly_income = float(rng.uniform(3_000_000, 5_000_000))
            balance = 0
        else:
            monthly_income = float(rng.uniform(7_000_000, 15_000_000))
            # Ngày 01/01 đã qua 7 ngày của kỳ lương 25 trước đó
            balance = round(monthly_income * (24.0 / 31.0))

        # Tham số cá nhân theo SPEC Mục 9
        rho = float(rng.uniform(0.85, 1.05))
        sigma_daily = float(rng.uniform(0.35, 0.60))
        s_front = float(rng.uniform(1.2, 2.0))
        s_weekend = float(rng.uniform(1.8, 2.5))
        cycle_shock = float(rng.lognormal(mean=-0.5 * (0.07 ** 2), sigma=0.07))

        for idx_d, current_date in enumerate(date_range):
            day_of_month = current_date.day
            income = 0

            # Tính ngày lương và số ngày tới kỳ lương tiếp theo
            if income_cycle == "trợ cấp đầu tháng":
                if day_of_month == 1:
                    income = round(monthly_income)
                day_in_cycle = day_of_month
                next_payday_date = current_date.replace(day=1) + pd.DateOffset(months=1)
            else:  # lương ngày 25
                if day_of_month == 25:
                    income = round(monthly_income)
                if day_of_month >= 25:
                    day_in_cycle = day_of_month - 24
                    next_payday_date = current_date.replace(day=25) + pd.DateOffset(months=1)
                else:
                    prev_payday = current_date.replace(day=25) - pd.DateOffset(months=1)
                    day_in_cycle = (current_date - prev_payday).days + 1
                    next_payday_date = current_date.replace(day=25)

            days_to_next_income = (next_payday_date - current_date).days
            cycle_len = day_in_cycle + days_to_next_income - 1

            # Đầu chu kỳ mới: cập nhật cú sốc chu kỳ và kết chuyển số dư (tối đa 10% thu nhập)
            if day_in_cycle == 1 and idx_d > 0:
                cycle_shock = float(rng.lognormal(mean=-0.5 * (0.07 ** 2), sigma=0.07))
                balance = min(max(balance, 0), round(0.10 * monthly_income))

            base_daily_spend = (monthly_income * rho * cycle_shock) / cycle_len

            # Trọng số theo kiểu chi tiêu
            if spend_pattern == "đều":
                pattern_weight = 1.0
            elif spend_pattern == "dồn đầu chu kỳ":
                d_arr = np.arange(1, cycle_len + 1)
                w_all = 1.0 + s_front * np.exp(-d_arr / 8.0)
                pattern_weight = float((1.0 + s_front * np.exp(-day_in_cycle / 8.0)) / np.mean(w_all))
            elif spend_pattern == "tăng cuối tuần":
                mean_w = (5.0 * 0.7 + 2.0 * s_weekend) / 7.0
                raw_w = s_weekend if current_date.weekday() >= 5 else 0.7
                pattern_weight = float(raw_w / mean_w)
            else:  # bất thường
                pattern_weight = 0.75

            # Nhiễu log-normal hằng ngày (5% ngày không chi tiêu)
            if rng.random() < 0.05:
                noise = 0.0
            else:
                noise = float(rng.lognormal(mean=-0.5 * (sigma_daily ** 2), sigma=sigma_daily)) / 0.95

            daily_spend = base_daily_spend * pattern_weight * noise

            if spend_pattern == "bất thường":
                if rng.random() < (0.25 / 6.0):
                    daily_spend += base_daily_spend * float(rng.uniform(5.0, 7.0))

            daily_spend = int(round(daily_spend))
            income = int(round(income))
            balance = int(round(balance + income - daily_spend))

            all_data.append([
                user_id,
                current_date.strftime("%Y-%m-%d"),
                daily_spend,
                income,
                balance,
                days_to_next_income,
                day_in_cycle,
                spend_pattern,
            ])

    columns = [
        "user_id",
        "date",
        "spend",
        "income",
        "balance",
        "days_to_next_income",
        "day_in_cycle",
        "pattern",
    ]
    return pd.DataFrame(all_data, columns=columns)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinh dữ liệu dòng tiền cá nhân")
    parser.add_argument("--users", type=int, default=20, help="Số lượng người dùng (mặc định: 20)")
    parser.add_argument("--months", type=int, default=18, help="Số tháng mô phỏng (mặc định: 18)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (mặc định: 42)")
    parser.add_argument("--out", type=str, default="data/sample_v0.csv", help="File đầu ra (mặc định: data/sample_v0.csv)")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    print(f"Đang sinh dữ liệu ({args.users} người, {args.months} tháng, seed={args.seed})...")
    df_out = generate_cash_flow_data(n_users=args.users, months=args.months, seed=args.seed)
    df_out.to_csv(args.out, index=False)
    print(f"Đã lưu thành công tại: {args.out} ({len(df_out):,} dòng)")