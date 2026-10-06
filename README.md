# cashflow_risks

# 1. DÒNG THỜI GIAN
- Ngày nhận tiền là ngày 1 của chu kỳ (day_in_cycle = 1); thu nhập cộng vào đầu ngày.
- Quyết định đưa ra cuối ngày t, khi đã biết spend_t và balance_t.
- D = độ dài chu kỳ − day_in_cycle. Chỉ xét điểm có D >= 3.
- Giữa chu kỳ không có thu nhập, nên số dư chỉ giảm.

# 2. ĐỊNH NGHĨA
- theta_c = chi tiêu TB/ngày của 14 ngày trước ngày nhận tiền; cố định suốt chu kỳ.
- Chu kỳ thiếu tiền <=> balance cuối chu kỳ < theta_c.
- y_t = 1 nếu chu kỳ chứa t là chu kỳ thiếu tiền.
- Bỏ điểm quyết định có balance_t < theta_c (đã thiếu rồi) và 28 ngày đầu của mỗi người.
- dip_day = ngày đầu tiên balance < theta_c.
  Số ngày báo sớm = dip_day − ngày có cảnh báo đầu tiên.

# 3. DỮ LIỆU: data/daily.csv (VND, số nguyên)
user_id, date, spend, income (0 nếu không phải ngày nhận), balance (cuối ngày),
cycle_id, day_in_cycle, D, pattern {even, front, weekend, spike},
income_type {allowance_1st, salary_25}
- Mô hình KHÔNG được dùng cột pattern (đó là nhãn thật của simulator).

# 4. CHIA DỮ LIỆU (theo thời gian, 18 tháng)
train tháng 1–12, val 13–15, test 16–18. Gán theo ngày bắt đầu chu kỳ;
chu kỳ vắt qua ranh giới thì bỏ.

# 5. GIAO DIỆN (B1, B2, XGBoost dùng chung)
- dp = bảng điểm quyết định (user_id, cycle_id, t, balance_t, D, theta_c, y, dip_day) – Người 2
- predict_spend(df, dp) -> mảng (n_dp, 31): chi tiêu dự báo ngày t+1..t+D, NaN phía sau
  B1, B2: Người 2 | XGBoost: Người 3
- risk_prob(yhat, dp, residuals, K=500, seed) -> p (n_dp,) – Người 4
  Vì số dư chỉ giảm: p = P(tổng chi D ngày > balance_t − theta_c)
- evaluate(dp, alert) -> dict chỉ số – Người 2

# 6. CHỈ SỐ VÀ CÁCH TUNE
- Q1: MAE, RMSE của chi tiêu ngày và của số dư cuối chu kỳ.
- Q2: Precision, Recall, F1 (mức điểm quyết định); số ngày báo sớm (mức chu kỳ).
- p* (XGBoost) và biên m (B1, B2: cảnh báo khi số dư dự kiến cuối chu kỳ < theta_c + m)
  chọn trên val để tối đa F1. Test chỉ chạy 1 lần.

# 7. SEED: dev dùng 42; chạy cuối dùng 1, 2, 3 (seed điều khiển cả sinh dữ liệu và mô hình).
   Báo cáo trung bình ± độ lệch chuẩn.
