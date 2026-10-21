"""Tạo dữ liệu theo chu kỳ thu nhập và nhãn thiếu tiền cho mô hình."""

import json

import numpy as np
import pandas as pd

from config import DATA_DIR, END_DATE, START_DATE


def build_cycle_dataset() -> pd.DataFrame:
    daily = pd.read_csv(DATA_DIR / "daily.csv", parse_dates=["date"])
    users = pd.read_csv(DATA_DIR / "users.csv")
    daily = daily.sort_values(["user_id", "date"]).reset_index(drop=True)
    profile_map = users.set_index("user_id").to_dict("index")
    first_date = pd.Timestamp(START_DATE)
    last_date = pd.Timestamp(END_DATE)
    output = []

    for user_id, user_days in daily.groupby("user_id", sort=False):
        user_days = user_days.reset_index(drop=True)
        dates = user_days["date"].to_numpy(dtype="datetime64[ns]")
        spends = user_days["spend"].to_numpy(dtype=float)
        balances = user_days["balance"].to_numpy(dtype=float)
        incomes = user_days["income"].to_numpy(dtype=float)
        pay_positions = np.flatnonzero(incomes > 0)
        if len(pay_positions) < 2:
            continue
        profile = profile_map[user_id]

        for i in range(len(pay_positions) - 1):
            start_pos = int(pay_positions[i])
            next_pos = int(pay_positions[i + 1])
            cycle_start = pd.Timestamp(dates[start_pos])
            next_payday = pd.Timestamp(dates[next_pos])

            # Bỏ chu kỳ đầu vì chưa đủ 30 ngày lịch sử; bỏ chu kỳ cuối chưa kết thúc.
            if cycle_start < first_date + pd.Timedelta(days=30):
                continue
            if next_payday > last_date:
                continue
            history_start_pos = start_pos - 30
            if history_start_pos < 0:
                continue

            history = user_days.iloc[history_start_pos:start_pos]
            cycle = user_days.iloc[start_pos:next_pos]
            if len(cycle) == 0 or len(history) != 30:
                continue

            if i > 0:
                previous_start_pos = int(pay_positions[i - 1])
                previous_spend_ratio = float(spends[previous_start_pos:start_pos].sum() / max(incomes[previous_start_pos], 1))
                previous_shortfall = int(np.any(balances[previous_start_pos:start_pos] < 0))
            else:
                previous_spend_ratio = np.nan
                previous_shortfall = 0

            history_spends = spends[history_start_pos:start_pos]
            avg_spend = float(history_spends.mean())
            std_spend = float(history_spends.std(ddof=0))
            total_spend_30d = float(history_spends.sum())
            history_dates = pd.to_datetime(dates[history_start_pos:start_pos])
            weekend_mask = np.asarray(history_dates.dayofweek >= 5)
            weekend_total = float(history_spends[weekend_mask].sum())
            weekend_share = weekend_total / max(total_spend_30d, 1.0)
            current_income = float(incomes[start_pos])
            start_balance = float(balances[start_pos] + spends[start_pos])
            cycle_days = int(next_pos - start_pos)
            shortfall = int(np.any(balances[start_pos:next_pos] < 0))

            output.append(
                {
                    "user_id": user_id,
                    "cycle_start_date": cycle_start.strftime("%Y-%m-%d"),
                    "cycle_end_date": (next_payday - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    "income_type": profile["income_type"],
                    "pattern": profile["pattern"],
                    "monthly_income_vnd": int(profile["monthly_income_vnd"]),
                    "current_income": current_income,
                    "cycle_start_balance": start_balance,
                    "start_balance_to_income": start_balance / max(current_income, 1.0),
                    "days_in_cycle": cycle_days,
                    "avg_daily_spend_30d": avg_spend,
                    "std_daily_spend_30d": std_spend,
                    "max_daily_spend_30d": float(history_spends.max()),
                    "total_spend_30d": total_spend_30d,
                    "weekend_spend_share_30d": weekend_share,
                    "spending_volatility_30d": std_spend / max(avg_spend, 1.0),
                    "previous_cycle_spend_ratio": previous_spend_ratio,
                    "previous_cycle_shortfall": previous_shortfall,
                    "projected_spend_to_start_balance": avg_spend * cycle_days / max(start_balance, 1.0),
                    "cycle_start_day_of_month": int(cycle_start.day),
                    "shortfall": shortfall,
                }
            )

    result = pd.DataFrame(output)
    if result.empty:
        raise RuntimeError("Không tạo được cycle_dataset.csv. Hãy kiểm tra ngày và lịch thu nhập.")

    result = result.sort_values(["user_id", "cycle_start_date"]).reset_index(drop=True)
    result.to_csv(DATA_DIR / "cycle_dataset.csv", index=False, encoding="utf-8-sig")
    summary = {
        "cycle_samples": int(len(result)),
        "unique_users": int(result["user_id"].nunique()),
        "shortfall_samples": int(result["shortfall"].sum()),
        "shortfall_rate": float(result["shortfall"].mean()),
        "non_shortfall_samples": int((result["shortfall"] == 0).sum()),
        "cycle_start_min": str(result["cycle_start_date"].min()),
        "cycle_start_max": str(result["cycle_start_date"].max()),
        "label_definition": "1 nếu balance âm ít nhất một ngày từ ngày nhận thu nhập đến ngày trước kỳ thu nhập kế tiếp; ngược lại là 0.",
    }
    (DATA_DIR / "cycle_dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Đã lưu: {DATA_DIR / 'cycle_dataset.csv'}")
    print(
        f"Mẫu chu kỳ: {len(result):,}; thiếu tiền: {result['shortfall'].sum():,} "
        f"({result['shortfall'].mean():.2%}); số người: {result['user_id'].nunique():,}"
    )
    return result


def main() -> None:
    build_cycle_dataset()


if __name__ == "__main__":
    main()
