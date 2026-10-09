from datetime import datetime
import os
import random
import numpy as np
import pandas as pd

# Cố định seed để dữ liệu đồng nhất mỗi lần chạy
np.random.seed(42)
random.seed(42)


def generate_cash_flow_data(n_users=20, months=18, start_date="2025-01-01"):
  start_dt = pd.to_datetime(start_date)
  end_dt = start_dt + pd.DateOffset(months=months)
  date_range = pd.date_range(start=start_dt, end=end_dt, freq="D")

  all_data = []
  income_cycles = ["trợ cấp đầu tháng", "lương ngày 25"]
  spend_patterns = ["đều", "dồn đầu chu kỳ", "tăng cuối tuần", "bất thường"]

  for i in range(1, n_users + 1):
    user_id = f"U{str(i).zfill(3)}"
    income_cycle = random.choice(income_cycles)
    spend_pattern = random.choice(spend_patterns)

    monthly_income = np.random.uniform(10_000_000, 30_000_000)
    # Tỷ lệ 25% user bị thiếu tiền (thỏa mãn yêu cầu đề bài 15-35%)
    is_struggling = random.random() < 0.25
    spend_ratio = (
        np.random.uniform(0.95, 1.1)
        if is_struggling
        else np.random.uniform(0.6, 0.8)
    )
    base_daily_spend = (monthly_income * spend_ratio) / 30

    balance = 0

    for current_date in date_range:
      day_of_month = current_date.day
      income = 0

      # Tính ngày lương và số ngày tới kỳ lương tiếp theo
      if income_cycle == "trợ cấp đầu tháng":
        if day_of_month == 1:
          income = monthly_income
        day_in_cycle = day_of_month
        next_payday_date = current_date.replace(day=1) + pd.DateOffset(
            months=1
        )
      else:  # lương ngày 25
        if day_of_month == 25:
          income = monthly_income
        if day_of_month >= 25:
          day_in_cycle = day_of_month - 24
          next_payday_date = current_date.replace(day=25) + pd.DateOffset(
              months=1
          )
        else:
          prev_payday = current_date.replace(day=25) - pd.DateOffset(months=1)
          day_in_cycle = (current_date - prev_payday).days + 1
          next_payday_date = current_date.replace(day=25)

      days_to_next_income = (next_payday_date - current_date).days

      # Nhiễu log-normal
      noise = np.random.lognormal(mean=0, sigma=0.4)
      daily_spend = base_daily_spend * noise

      if spend_pattern == "dồn đầu chu kỳ":
        daily_spend *= max(0.2, 1.5 - (day_in_cycle * 0.04))
      elif spend_pattern == "tăng cuối tuần":
        daily_spend *= 2.5 if current_date.weekday() >= 5 else 0.7
      elif spend_pattern == "bất thường":
        if random.random() < 0.02:
          daily_spend *= np.random.uniform(5, 10)

      daily_spend = round(daily_spend)
      income = round(income)
      balance += income - daily_spend

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
  # Đảm bảo thư mục data/ tồn tại
  os.makedirs("data", exist_ok=True)

  # 1. Sinh bản v0 (20 người)
  print("Đang sinh dữ liệu bản v0 (20 người)...")
  df_v0 = generate_cash_flow_data(n_users=20, months=18)

  # Lưu vào folder data/
  output_path = "data/sample_v0.csv"
  df_v0.to_csv(output_path, index=False)
  print(f"Đã lưu thành công tại: {output_path}")