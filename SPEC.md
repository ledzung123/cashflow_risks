# SPEC v2.9 – Nhóm 11 (nguồn: mục 3 và 4.2 báo cáo giữa kỳ)

v2.9: thêm đánh giá chính sách chi phí/FAR với ngưỡng chọn trên validation, CI từng seed, gánh nặng cảnh báo theo chu kỳ, ablation và chính sách nhập CSV tường minh. Kết quả bổ sung ở `results/upgrades/summary/`; quy trình ở `results/upgrades/PROTOCOL.md`. Báo cáo cuối kỳ DOCX chưa được sửa theo phiên bản này.

Thay đổi so với v1: thêm cột `split`, thêm file `*_users.csv`, chốt quy tắc mang số dư sang chu kỳ sau,
chốt tham số simulator (mục 9). v1.2: biên m tính theo đơn vị theta_c (mục 6), thêm chỉ số mức chu kỳ (mục 6),
thêm lệnh chạy baseline (mục 10). v1.3: chốt cách ước lượng xác suất ở bước 5 (mục 5, 6, 11). v1.4: bước 6 gộp kết quả (mục 12). v2.8: chọn ngưỡng cùng Precision trên val và đánh giá test độc lập (mục 6e), đánh giá phụ giữ riêng người dùng, ghi DATA_CARD.md (mục 18). v2.7: KS (mục 6c), so ở cùng Precision với B1 (mục 6e), kiểm tra CSV thật và lý do cảnh báo trong demo (mục 15), phân tích lỗi, SHAP, mất cân bằng lớp, công bằng theo thu nhập, ghim phiên bản thư viện (mục 18). v2.6: bổ sung kỹ thuật cho thang điểm cuối kỳ (mục 17). v2.5: chỉ số báo sớm ở cùng mức báo nhầm (mục 6d). v2.4: rà soát đồng bộ (mục 16). v2.3: chỉ số không phụ thuộc ngưỡng (mục 6c). v2.2: phân tích độ nhạy (mục 14), MVP demo.html (mục 15), nhập CSV thật (mục 15). v2.1: chỉ số cho p_t (mục 6b), kiểm chứng phần dư độc lập (mục 13), thêm cách chia nhóm "cumb" (mục 11). v2.0 (theo góp ý của thầy): 24 chu kỳ và 4 tập tách riêng train/calib/val/test (mục 4); p* và phân phối sai số không còn dùng chung một tập (mục 11). Mọi thay đổi tiếp theo phải báo cả nhóm.

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

## 4. Chia dữ liệu (theo thời gian, 24 chu kỳ) – SPEC v2.0
| Tập | `cycle_id` | Vai trò DUY NHẤT |
|---|---|---|
| train | 0–11 | Huấn luyện XGBoost |
| calib | 12–15 | Dựng phân phối sai số để tính p (chỉ dùng cho việc này) |
| val | 16–19 | Early stopping, tune biên m (baseline, XGB theo biên m), chọn p* |
| test | 20–23 | Chỉ đánh giá, chạy một lần |
Gán theo chu kỳ nên không có chu kỳ vắt qua ranh giới; thứ tự thời gian: train < calib < val < test.
Không tập nào được dùng cho hai vai trò khác nhau (đây là điểm thầy đã chỉ ra ở bản v1).

## 5. Giao diện (B1, B2, XGBoost dùng chung)
- `dp` = bảng điểm quyết định (user_id, cycle_id, t, balance_t, D, theta_c, y, dip_day) – Người 2
- `predict_spend(df, dp) -> mảng (n_dp, 31)`: chi tiêu dự báo ngày t+1..t+D, NaN phía sau
  - B1, B2: Người 2 | XGBoost: Người 3
- `risk.fit_predict(method, dp_calib, yhat_calib, [(dp_val, yhat_val), (dp_test, yhat_test)], df, K, seed) -> [p_val, p_test]` – Người 4
  - Vì số dư chỉ giảm: p = P(tổng chi D ngày > balance_t − theta_c)
  - method "cumb" (được chọn, Brier val thấp hơn ở cả 3 seed) hoặc "mc" (mô phỏng K quỹ đạo); phân phối dựng trên tập calib
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
- 300 người × 24 chu kỳ; 4 kiểu chi tiêu chia đều; 2 chu kỳ thu nhập (trợ cấp ngày 1: 3–5 triệu; lương ngày 25: 7–15 triệu).
- Tổng chi/thu nhập của mỗi người ρ ~ U(0.85, 1.05); nhiễu hằng ngày log-normal σ ~ U(0.35, 0.60);
  "cú sốc theo chu kỳ" log-normal σ = 0.07; 5% ngày không chi gì.
- front: hệ số `1 + s·exp(−d/8)`, s ~ U(1.2, 2.0). weekend: cuối tuần/ngày thường = s/0.7, s ~ U(1.8, 2.5).
  spike: 75% chi nền + khoản lớn (~6× chi tiêu ngày) theo Poisson, chiếm 25% tổng chi.
- Mang sang chu kỳ sau: `min(max(balance_cuối, 0), 10% thu nhập)`; thiếu hụt được xoay xở ngoài mô hình.
- Hiệu chỉnh duy nhất: chọn khoảng ρ để tỉ lệ chu kỳ thiếu tiền nằm trong 15–35%
  (seed 42, 24 chu kỳ: 29,0% chu kỳ thiếu tiền; train 28,8%, val 28,2%, test 31,8%). Không chỉnh theo kết quả mô hình.
- Hiệu ứng độ dài chu kỳ (phát hiện khi vẽ sanity_v1.png): chi tiêu mô phỏng tính theo ngày còn thu nhập tính theo chu kỳ, nên chu kỳ 28 ngày
  (tháng 2: cycle_id 1 và 13) thiếu tiền ít hơn rõ rệt (14,8%) so với chu kỳ 30 ngày (27,4%) và 31 ngày (31,7%). Giữ nguyên vì hợp lý
  (tháng dài khó hơn); ghi vào mục Thảo luận. Tập val có 1 chu kỳ 28 ngày nên tỉ lệ dương của val hơi thấp.
- Giả định cần ghi vào mục "Giới hạn" của báo cáo: người dùng không tự cắt chi khi số dư thấp; thu nhập đến đúng lịch.

## 10. Chạy
```
python src/simulate.py --users 300 --seed 42 --out data/daily.csv              # dữ liệu đầy đủ
python src/simulate.py --users 20  --seed 42 --out data/sample_v0.csv          # bản v0 nhỏ
python src/simulate.py --users 300 --seed 42 --check --fig results/sanity_v0.png  # thống kê + hình kiểm tra
python src/plot_sanity.py --csv data/daily.csv --out results/sanity_v1.png   # hình kiểm tra 6 ô từ file đã sinh
python src/test_pipeline.py                  # kiểm tra nhãn, oracle, rò rỉ tương lai, chỉ số
python src/run_baselines.py --seed 1         # B1/B2: tune m trên val, đánh giá trên test
```

## 11. Bước 5 (xác suất và cảnh báo p > p*)
- Phân phối sai số dựng trên **calib**; p* chọn trên **val** để tối đa F1; test chỉ đánh giá một lần.
- Hiệu chỉnh xác suất báo bằng Brier và ECE (10 khoảng); kèm biểu đồ `results/calibration_seed*.png`.
- Biến thể báo cáo thêm: `XGB+risk(k=2)` (chỉ cảnh báo khi p > p* hai ngày liên tiếp) và `B2+risk` (đối chứng: cùng cách tính p nhưng dùng dự báo của B2).
- Lệnh: `python src/test_risk.py`; `python src/run_risk.py --seed S`; `python src/aggregate_results.py --prefix risk --seeds 1 2 3`.

## 12. Bước 6 (gộp kết quả cho báo cáo)
- Đầu vào: kết quả 3 seed (1, 2, 3) của bước 3, 4, 5, gồm `results/risk_points_seed*.csv` (mỗi điểm test: p, nhãn, cảnh báo của từng mô hình).
  `run_risk.py` phải là bản mới (có lưu file này).
- Lệnh: `python src/make_report.py --seeds 1 2 3`. Đầu ra trong `results/final/`: `RESULTS.md` (bảng và kết luận tính từ số liệu),
  `Q1_table.csv`, `Q2_table.csv`, `by_pattern_Q2.csv`, `by_pattern_Q1_MAE_balance.csv`, `paired_diff.csv` và các hình. Toàn bộ bảng và hình
  `fig0`–`fig12` của dự án nằm trong `results/final/`, mô tả trong `RESULTS.md` và mục tương ứng của SPEC này.
- Mọi bảng là trung bình ± độ lệch chuẩn qua các seed; so sánh cặp theo seed ghi ở `paired_diff.csv`.
- Ví dụ minh họa (fig6) chọn theo quy tắc cố định (seed đầu, kiểu "front"), không phải ví dụ đại diện.

## 6b. Chỉ số cho p_t (bước 5, `prob_metrics.py`) – SPEC v2.1
- Độ chính xác xác suất: Brier, Brier skill, log loss, log loss skill (so với luôn đoán tỉ lệ nền của tập CALIB).
- Xếp hạng: AUROC, AUPRC. Hiệu chỉnh: ECE, MCE, độ dốc và hệ số chặn hiệu chỉnh (lý tưởng 1 và 0). Độ sắc: độ lệch chuẩn của p.
- Độ phủ khoảng dự báo 50%/80%/90% của tổng chi D ngày (kiểm tra trực tiếp phân phối sai số).
- Báo cáo tổng thể, theo 4 kiểu chi tiêu và theo 6 nhóm D. File: `results/pmetrics*_seed*.csv`, bảng `results/final/P_*.csv`.

## 13. Kiểm chứng phần dư độc lập theo ngày (`check_residuals.py`) – SPEC v2.1
- Đo tương quan phần dư chuẩn hóa giữa các ngày, tỉ số phương sai Var(tổng)/Tổng Var (độc lập = 1), và độ phủ 80% của "mc" (giả định độc lập)
  so với "cum"/"cumb" (không giả định). Phân phối dựng trên calib, đo trên test. File: `results/diagnostics_seed*.csv`.
- Cách chia nhóm "cumb": thêm nhóm theo tần suất chi CỰC lớn (số ngày chi > 5 lần mức TB 28 ngày, trên tối đa 84 ngày gần nhất, ngưỡng 0,5/28 ngày).
  Ngưỡng 3 lần không dùng được vì không phân biệt người "spike" với người chi nhiều cuối tuần.
- Phương pháp ước lượng p (cum, cumb, mc) được chọn theo Brier trên **val**.
- Lệnh: `python src/check_residuals.py --seed S` (cho S = 1, 2, 3) rồi `python src/make_report.py --seeds 1 2 3`.

## 14. Phân tích độ nhạy theo tham số simulator (`sensitivity.py`) – SPEC v2.2
- Thay cho dữ liệu thật: đổi MỘT tham số mỗi lần (hệ số cuối tuần, mức dồn đầu chu kỳ, độ nhiễu, tỉ lệ khoản chi lớn, cú sốc theo chu kỳ: nhân 0,5 và 1,5;
  tỉ lệ chi trên thu nhập: dịch ∓0,05), chạy lại cả pipeline và kiểm tra 5 kết luận (K1–K5) còn đúng không.
- Lệnh: `python src/sensitivity.py --seed 1` (mặc định 300 người, 13 kịch bản; có thể dùng `--only` để chia nhóm), rồi `--report`.
- `simulate.simulate(..., params={...})` nhận hệ số nhân; mặc định (không truyền params) cho kết quả giống hệt bản đã đóng băng.

## 15. MVP minh họa luồng hoạt động và nhập CSV thật – SPEC v2.2
- `python src/make_demo.py` tạo `demo.html` (một file, mở bằng trình duyệt): chọn người, chu kỳ, ngày; xem dải rủi ro theo ngày,
  luồng 4 bước (biết gì, dự báo chi tiêu, xác suất, quyết định), đường số dư dự báo và bảng so với B1/B2; có nút hiện kết quả thật.
- `python src/make_demo.py --csv file.csv --balance 1500000`: demo trên dữ liệu thật của một người. File cần cột date, spend, income
  (và tùy chọn balance); xem quy tắc ở `import_real.py`. Mô hình vẫn huấn luyện trên dữ liệu MÔ PHỎNG: demo chỉ để minh họa, chưa phải kiểm chứng.
- (v2.7) `import_real.py` kiểm tra chất lượng: ô trống hoặc không phải số, chi âm, ngày thiếu, ngày chi > nhiều lần trung vị, số dư thiếu.
  Cập nhật: mặc định từ chối ô lỗi/ngày thiếu/số dư thiếu. Chỉ điền 0 khi chọn `missing_policy='zero'`, chỉ điền số dư từ ngày trước khi chọn `balance_policy='ffill'`; nguồn không bị ghi đè. Chi âm và ngoại lai được giữ nguyên kèm cảnh báo. Chính sách và dấu vết biến đổi lưu ở `df.attrs["quality"]`.
- (v2.7) Mỗi ngày có dự báo, demo hiện dòng "Vì sao dự báo chi như vậy": 3 đặc trưng làm tăng và 2 đặc trưng làm giảm tổng chi dự báo D ngày
  nhiều nhất, theo SHAP (`explain.contributions`, mục 18), tính bằng nghìn đồng, bỏ đóng góp dưới 1 nghìn đồng.
- Kiểm tra: `node src/test_demo.js demo.html` (cần Node.js và gói jsdom: `npm install jsdom`), duyệt mọi ngày và chu kỳ, kiểm tra không lỗi và kết luận khớp dữ liệu.
- Mọi file demo cần `demo_template.html` nằm cùng thư mục với `make_demo.py`.

## 6c. Chỉ số không phụ thuộc ngưỡng (AUROC, AUPRC, KS) – SPEC v2.3, KS thêm ở v2.7
- Điểm số rủi ro liên tục cho mọi mô hình trên cùng tập test: B1, B2, XGB (theo biên m): `(theta - số dư dự kiến cuối chu kỳ) / theta`
  (cảnh báo theo biên m <=> điểm số > -m, nên không đổi gì về quy tắc cảnh báo); XGB + risk và B2 + risk: chính xác suất p.
- Lưu ở `results/rank_seed*.csv` (do `run_risk.py` ghi) và đưa vào bảng Q2 (`results/final/Q2_table.csv`).
- Lý do: F1 phụ thuộc ngưỡng chọn trên val nên dao động giữa các seed; AUROC/AUPRC so sánh các mô hình ổn định hơn.
- (v2.7) KS = max(TPR − FPR) trên đường ROC, tính trong `evaluate.rank_metrics`, có trong bảng Q2. Chỉ số quen thuộc khi đánh giá điểm rủi ro tài chính.

## 16. Rà soát đồng bộ – SPEC v2.4
- **Một quy ước kích thước dữ liệu cho mọi bước chính:** 300 người mô phỏng × 24 chu kỳ = 219.000 dòng (seed dữ liệu minh họa 42; seed kết quả 1, 2, 3).
  Áp dụng cho `run_baselines/run_xgb/run_risk/check_residuals` (qua `run_baselines.load`), `sensitivity.py` (mặc định 300) và `make_demo.py` (huấn luyện trên 300).
- `demo.html` **chỉ hiển thị** một tập con (mặc định 20 trong 300 người, ở tập test); hệ thống phía sau vẫn huấn luyện trên 300 người.
- Các bộ test (`test_*.py`) dùng ít người (8, 40, 60) chỉ để kiểm tra nhanh, không phải kết quả.
- Seed mặc định của mọi script chạy là 1; `run_all.ps1` truyền rõ 1, 2, 3.
- Trong gói zip, thư mục mã tên `cashflow_risks` (các lệnh `python src/...` trong tài liệu này đọc là `python cashflow_risks\...`).
- `check_conventions.py` tự kiểm tra các quy ước trên (chạy trước tiên trong `run_all.ps1`).

## 6d. Báo sớm ở cùng mức báo nhầm (`evaluate.lead_at_far`) – SPEC v2.5
- Lý do: `mean_days_early` không phân biệt được các mô hình vì cảnh báo thường bật ngay từ ngày đầu chu kỳ, và mỗi mô hình có mức báo nhầm khác nhau.
- Với mỗi mức báo nhầm mục tiêu (5% đến 50%, bước 5%; báo cáo 10%, 20%, 30%), đặt ngưỡng trên điểm số liên tục của từng mô hình (điểm biên cho B1/B2/XGB,
  p cho XGB + p và B2 + p) sao cho đúng tỉ lệ **chu kỳ bình thường có ít nhất một cảnh báo** như vậy; sau đó đo trên các chu kỳ thiếu tiền:
  `cycle_recall` (tỉ lệ bắt được), `lead_mean_all` (số ngày báo trước ngày cạn tiền, chu kỳ bỏ sót tính 0), `lead_median_caught` (chỉ chu kỳ bắt được).
- Ngưỡng đặt trực tiếp trên test để so sánh theo đường cong (giống AUROC), không phải ngưỡng vận hành; không dùng để chọn p* hay m.
- File: `results/lead_seed*.csv`, bảng `results/final/Lead_table.csv`, hình `fig9_lead_far.png`.

## 6e. Ở cùng mức Precision với B1 (`evaluate.lead_at_precision`) – SPEC v2.8
- Lý do: báo cáo giữa kỳ coi giải pháp có ích nếu "ở mức Precision tương đương, Recall cao hơn hoặc báo sớm hơn B1"; mục 6d so ở cùng mức báo nhầm,
  chưa đúng câu chữ này.
- Với mỗi mức Precision mục tiêu (Precision của B1 trên **val** sau khi tune biên m trên val, và 0,7), chọn ngưỡng trên điểm số liên tục của từng mô hình
  cho Recall **trên val** lớn nhất mà Precision trên val vẫn ≥ mục tiêu. Sau đó giữ nguyên ngưỡng và đo Precision, Recall, `cycle_recall`,
  `cycle_false_alarm`, `lead_mean_all`, `lead_median_caught` **một lần trên test**. Báo cáo riêng Precision validation để cho thấy việc chọn ngưỡng đạt mục tiêu ra sao;
  Precision test có thể khác mức mục tiêu.
- Test không tham gia chọn ngưỡng. Đây là đánh giá trên holdout, không phải so sánh đường cong ROC/PR; nếu muốn mô tả đường cong thì ghi riêng là phân tích thăm dò.
- File: `results/prec_seed*.csv` (do `run_risk.py` ghi), bảng `results/final/Prec_table.csv`, một mục trong `RESULTS.md`.

## 17. Bổ sung kỹ thuật cho thang điểm cuối kỳ (`model_alt.py`, `extra_analysis.py`, `summarize_extra.py`) – SPEC v2.6
- So XGBoost với B1, B2, Ridge, Random Forest, HistGradientBoosting trên CÙNG đặc trưng, mục tiêu và tập test (random forest dùng 40 cây, mỗi cây 8% mẫu để kịp thời gian).
- Chi phí sai: báo nhầm = 1, bỏ sót = r (r = 1, 2, 3, 5, 10, 20); chọn ngưỡng tối thiểu chi phí trên validation rồi đo chi phí test. So với Bayes 1/(1+r) cho XGB + p (không tune). Bảng cũ trước đợt nâng cấp là tối ưu trực tiếp trên test, chỉ có ý nghĩa tham chiếu hồi cứu.
- Khoảng tin cậy 95% bootstrap theo NGƯỜI (500 lần mặc định) cho hiệu XGB - B2 về AUROC, tỉ lệ bắt được ở báo nhầm 20%, F1, MAE. Công bố CI từng seed và trung bình/SD kết quả qua seed; không diễn giải trung bình cận CI là CI95% chung.
- Phân tích theo nhóm thu nhập và kiểu chi tiêu; độ trễ 1 yêu cầu và kích thước mô hình.
- Chạy: `python src/extra_analysis.py --seed S` (mỗi seed vài phút), rồi `python src/summarize_extra.py` -> `results/final/Extra_*.csv`, `EXTRA_RESULTS.md`, `fig10_extra.png`.


## 18. Phân tích lỗi, lý do cảnh báo, mất cân bằng lớp, công bằng, tái lập – SPEC v2.8
- **Phân tích lỗi** (`error_cases.py --seeds 1 2 3`): mức chu kỳ, XGB + p > p* so với B2 trên test. Báo nhầm = chu kỳ không thiếu tiền nhưng có
  ít nhất 1 cảnh báo; bỏ sót = chu kỳ thiếu tiền không có cảnh báo nào (giống `cycle_false_alarm`, `cycle_recall`). "Suýt thiếu" = số dư cuối kỳ
  cao hơn θ chưa tới 1θ. Thống kê theo kiểu chi tiêu và loại thu nhập. 2 ví dụ chọn theo quy tắc cố định (seed đầu; với mỗi loại lỗi, chu kỳ có
  p lớn nhất gần trung vị của loại đó nhất), không chọn tay. Đầu ra: `ERROR_ANALYSIS.md`, `error_*.csv`, `fig11_error_cases.png`.
- **Lý do cảnh báo** (`explain.py --seed 1`): TreeSHAP có sẵn trong XGBoost (`pred_contribs=True`), không cài thêm thư viện. Đóng góp (VND) =
  SHAP × mức chi TB 28 ngày, cộng qua h = 1..D, tức là đóng góp vào TỔNG CHI dự báo D ngày tới; tự kiểm tra tổng SHAP bằng dự báo.
  SHAP giải thích vì sao MÔ HÌNH dự báo như vậy, không giải thích nguyên nhân người dùng chi tiêu (phạm vi giữ như giữa kỳ).
  Đầu ra: `explain_alerts_seed1.csv`, `explain_global_seed1.csv`, `explain_cases.csv`, `fig12_explain.png`.
- **Mất cân bằng lớp** (`supplement.py --seeds 1 2 3`): mô hình chính hồi quy chi tiêu nên không dùng trọng số lớp hay lấy mẫu lại; mất cân bằng
  chỉ tác động ở bước đặt ngưỡng (p* chọn trên val theo F1, báo cáo thêm AUPRC). Báo cáo tỉ lệ thiếu tiền ở từng tập và cùng một p với 3 ngưỡng:
  p*, 0,5, tỉ lệ nền tập calib. Đầu ra: `class_balance.csv`, `imbalance_table.csv`, `SUPPLEMENT.md`.
- **Công bằng theo mức thu nhập** (`supplement.py`): chia 3 mức thu nhập bằng nhau TRONG từng loại thu nhập (6 nhóm), so bỏ sót, báo nhầm,
  Precision, Recall, AUROC, ECE, Brier. Simulator không cài khác biệt hành vi theo thu nhập, nên phép thử chỉ kiểm tra mô hình có tự tạo ra chênh
  lệch hay không. Đầu ra: `fairness_income.csv`, `SUPPLEMENT.md`.
- **Tái lập:** phiên bản thư viện ghim trong `requirements.txt` (Python 3.12.10); `run_all.ps1` và `run_extras.ps1` cài từ file này
  (bỏ qua bằng `-SkipInstall`). Khác phiên bản xgboost có thể làm số của các dòng XGB lệch nhẹ; B1/B2 không đổi.
- **Phạm vi dữ liệu:** `DATA_CARD.md` ghi nguồn sinh dữ liệu, quy mô, biến, giả định và giới hạn. `data/daily.csv` là dữ liệu mô phỏng, không phải dữ liệu giao dịch thật.
- Tách tập hiện tại là theo thời gian trên cùng 300 người mô phỏng. Nó đánh giá dự báo các chu kỳ sau của nhóm người đã có lịch sử, chưa đánh giá khả năng tổng quát hóa sang người dùng hoàn toàn mới.
- Không tuyên bố hiệu quả trên người thật cho tới khi có đánh giá riêng trên dữ liệu giao dịch thật có sự đồng ý phù hợp. User-holdout chỉ kiểm tra khả năng chuyển sang người mô phỏng khác trong cùng simulator.

## 19. Đánh giá phụ giữ riêng người dùng (`run_user_holdout.py`) – SPEC v2.8
- Phân vai người dùng một lần bằng seed chia nhóm cố định: 50% train, 15% calib, 15% val, 20% test. Không một `user_id` nào xuất hiện ở hơn một vai trò.
- Mỗi vai trò dùng đúng giai đoạn thời gian tương ứng: chu kỳ 0–11 cho train, 12–15 cho calib, 16–19 cho val, 20–23 cho test. Các đặc trưng của người dùng test vẫn được phép dùng lịch sử giao dịch trước thời điểm dự báo của chính người đó; nhãn test không tham gia fit, calibration hay chọn ngưỡng.
- Đây là phép đánh giá phụ về tổng quát hóa sang người mô phỏng khác, không thay thế đánh giá chính theo thời gian và không chứng minh hiệu quả trên người thật.
- `run_all.ps1` chạy `run_user_holdout.py --seeds 1 2 3`, sau đó `summarize_user_holdout.py` tạo `results/user_holdout/USER_HOLDOUT.md` và các bảng CSV.
