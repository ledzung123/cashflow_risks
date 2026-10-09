# SPEC v1.2 – Nhóm 11 (nguồn: mục 3 và 4.2 báo cáo giữa kỳ)

## 1. Dòng thời gian
- Ngày nhận tiền là ngày 1 của chu kỳ (`day_in_cycle = 1`); thu nhập cộng vào đầu ngày.
- Quyết định đưa ra cuối ngày t, khi đã biết `spend_t` và `balance_t`.
- `D` = độ dài chu kỳ − `day_in_cycle`. Chỉ xét điểm có D >= 3.
- Giữa chu kỳ không có thu nhập, nên số dư chỉ giảm.

## 2. Định nghĩa
- `theta_c` = chi tiêu TB/ngày của 14 ngày trước ngày nhận tiền; cố định suốt chu kỳ.
- Chu kỳ thiếu tiền <=> `balance` cuối chu kỳ < `theta_c`.
- `y_t` = 1 nếu chu kỳ chứa t là chu kỳ thiếu tiền.
- Bỏ điểm quyết định có `balance_t < theta_c` (đã thiếu rồi) và chu kỳ 0 (chưa đủ lịch sử).
- `dip_day` = ngày đầu tiên `balance < theta_c`. Số ngày báo sớm = `dip_day` − ngày có cảnh báo đầu tiên.

## 3. Dữ liệu: `data/daily.csv` (VND, số nguyên), sinh bởi `src/simulate.py`
`user_id, date, spend, income, balance, cycle_id, day_in_cycle, D, pattern, income_type, split`
- `income` = 0 nếu không phải ngày nhận tiền; `balance` là số dư cuối ngày (có thể âm).
- `pattern` ∈ {even, front, weekend, spike}, `income_type` ∈ {allowance_1st, salary_25}.
- **Mô hình KHÔNG được dùng cột `pattern`** (đó là nhãn thật của simulator, chỉ để phân tích kết quả).
- `daily_users.csv` ghi tham số thật của từng người (chỉ để phân tích).

## 4. Chia dữ liệu (theo thời gian, 18 chu kỳ)
`cycle_id` 0–11 = train, 12–14 = val, 15–17 = test (cột `split`). Gán theo chu kỳ nên không có chu kỳ vắt qua ranh giới.

## 5. Giao diện (B1, B2, XGBoost dùng chung)
- `dp` = bảng điểm quyết định (user_id, cycle_id, t, balance_t, D, theta_c, y, dip_day) – Người 2
- `predict_spend(df, dp) -> mảng (n_dp, 31)`: chi tiêu dự báo ngày t+1..t+D, NaN phía sau
  - B1, B2: Người 2 | XGBoost: Người 3
- `risk_prob(yhat, dp, residuals, K=500, seed) -> p (n_dp,)` – Người 4
  - Vì số dư chỉ giảm: p = P(tổng chi D ngày > balance_t − theta_c)
- `evaluate(dp, alert) -> dict chỉ số` – Người 2

## 6. Chỉ số và cách tune
- Q1: MAE, RMSE của chi tiêu ngày và của số dư cuối chu kỳ.
- Q2: Precision, Recall, F1 (mức điểm quyết định); số ngày báo sớm (mức chu kỳ).
- p* (XGBoost) và biên m (B1, B2: cảnh báo khi số dư dự kiến cuối chu kỳ < theta_c × (1 + m); m tính theo đơn vị theta_c,
  lưới −3..10 bước 0,25) chọn trên val để tối đa F1. Test chỉ chạy 1 lần.
- Mức chu kỳ (báo cáo thêm): `cycle_recall` = tỉ lệ chu kỳ thiếu tiền có ít nhất 1 cảnh báo;
  `cycle_false_alarm` = tỉ lệ chu kỳ KHÔNG thiếu tiền nhưng vẫn bị cảnh báo ít nhất 1 lần;
  `mean_days_early` = trung bình (dip_day − ngày cảnh báo đầu tiên) trên các chu kỳ thiếu tiền đã bắt được.

## 7. Seed
Dev dùng 42; chạy cuối dùng 1, 2, 3 (seed điều khiển cả sinh dữ liệu và mô hình). Báo cáo trung bình ± độ lệch chuẩn.

## 8. Quy tắc làm việc
Mỗi người sửa file của mình; PR vào main; không commit `data/` (chỉ commit `sample_v0.csv`).

## 9. Tham số simulator đã chốt (đóng băng, KHÔNG chỉnh sau khi đã xem kết quả mô hình)
- 300 người × 18 chu kỳ; 4 kiểu chi tiêu chia đều; 2 chu kỳ thu nhập (trợ cấp ngày 1: 3–5 triệu; lương ngày 25: 7–15 triệu).
- Tổng chi/thu nhập của mỗi người ρ ~ U(0.85, 1.05); nhiễu hằng ngày log-normal σ ~ U(0.35, 0.60);
  "cú sốc theo chu kỳ" log-normal σ = 0.07; 5% ngày không chi gì.
- front: hệ số `1 + s·exp(−d/8)`, s ~ U(1.2, 2.0). weekend: cuối tuần/ngày thường = s/0.7, s ~ U(1.8, 2.5).
  spike: 75% chi nền + khoản lớn (~6× chi tiêu ngày) theo Poisson, chiếm 25% tổng chi.
- Mang sang chu kỳ sau: `min(max(balance_cuối, 0), 10% thu nhập)`; thiếu hụt được xoay xở ngoài mô hình.
- Hiệu chỉnh duy nhất: chọn khoảng ρ để tỉ lệ chu kỳ thiếu tiền nằm trong 15–35%
  (kết quả: 28.2% chu kỳ, 26.9% điểm quyết định; train/val/test = 28.8/27.6/26.6%). Không chỉnh theo kết quả mô hình.
- Giả định cần ghi vào mục "Giới hạn" của báo cáo: người dùng không tự cắt chi khi số dư thấp; thu nhập đến đúng lịch.

## 10. Chạy
```
python src/simulate.py --users 300 --seed 42 --out data/daily.csv              # dữ liệu đầy đủ
python src/simulate.py --users 20  --seed 42 --out data/sample_v0.csv          # bản v0 nhỏ
python src/simulate.py --users 300 --seed 42 --check --fig results/sanity_v0.png  # thống kê + hình kiểm tra
python src/test_pipeline.py                  # kiểm tra nhãn, oracle, rò rỉ tương lai, chỉ số
python src/run_baselines.py --seed 1         # B1/B2: tune m trên val, đánh giá trên test
```
