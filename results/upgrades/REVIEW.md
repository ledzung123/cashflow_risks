# Tổng kết nâng cấp và đánh giá lại tiêu chí

Các thực nghiệm chạy ngày 23/10/2026; hoàn tất đối chiếu và tổng kết ngày 24/10/2026. Đây là ghi chú kỹ thuật và ước lượng điểm của ChatGPT/Codex, không phải báo cáo cuối kỳ hay điểm chính thức.

## 1. Các ưu tiên đã hoàn tất

1. **Ngưỡng chi phí:** chọn ngưỡng tối thiểu hóa FP + r×FN trên validation, khóa ngưỡng rồi tính test. Có r=1/2/3/5/10/20 và đối chứng ngưỡng Bayes.
2. **Ngưỡng FAR20:** chọn ngưỡng từ chu kỳ âm validation; công bố báo nhầm và Recall thực tế trên test. Đường cong FAR cũ vẫn là phân tích mô tả, không được dùng làm ngưỡng vận hành độc lập.
3. **Người dùng mới:** so các chính sách trên user-holdout, đo thêm số ngày cảnh báo và tỉ lệ chu kỳ âm bị cảnh báo từ 5 ngày trở lên.
4. **Bootstrap:** ghép cặp theo người, 500 lần, giữ cố định ngưỡng; CI95% riêng từng seed. Không lấy trung bình cận CI thành CI95% chung. Có thêm CI chênh lệch ở cùng mục tiêu Precision validation với B1.
5. **Dữ liệu thiếu:** mặc định từ chối ô lỗi, ngày thiếu và số dư thiếu. Chỉ điền khi chọn rõ chính sách zero/ffill; lưu dấu vết theo ngày và trường dữ liệu, không ghi đè nguồn.
6. **Ablation:** bỏ lịch sử chu kỳ cá nhân hoặc nhóm lịch/thống kê gần đây, cùng thuật toán, cách chia tập và siêu tham số; early stopping riêng trên validation.

Đã chạy 12 cấu hình: 3 seed × (temporal đầy đủ, user-holdout đầy đủ, 2 ablation). Có 360 dòng kết quả chính sách theo cấu hình/seed, mô hình và dự báo trung gian đã lưu, cùng hai hình tổng hợp.

## 2. Kết quả chính

Trung bình ba seed, riêng XGB+risk. Các chỉ số chu kỳ chỉ tính chu kỳ có ít nhất một điểm quyết định đủ điều kiện.

| Phép chia | Chính sách | Chu kỳ bình thường bị báo nhầm | Chu kỳ thiếu tiền bắt được | Ngày cảnh báo/chu kỳ bình thường |
|---|---|---:|---:|---:|
| Theo thời gian | Tối đa F1 validation, như bộ cũ | 44,25% | 98,32% | 4,18 |
| Theo thời gian | FAR20 validation | 19,43% | 94,36% | 1,31 |
| Giữ riêng người dùng | Tối đa F1 validation, như bộ cũ | 67,58% | 98,64% | 6,78 |
| Giữ riêng người dùng | FAR20 validation | 19,43% | 93,94% | 1,38 |

Đổi chính sách làm giảm báo nhầm và cảnh báo lặp, đồng thời giảm Recall chu kỳ. FAR validation không bảo đảm FAR test bằng đúng 20%. Chưa thay ngưỡng mặc định của demo bằng một chính sách chọn sau khi xem test.

Với r=2, chi phí test trên 100 điểm quyết định, ngưỡng tối ưu trên validation:

| Phép chia | B2 | XGB+risk |
|---|---:|---:|
| Theo thời gian | 26,7814 | 24,8254 |
| Giữ riêng người dùng | 29,3918 | 25,7632 |

Đơn vị chi phí quy ước: FP=1, FN=2. Đây không phải số tiền tiết kiệm thực tế. Các số 26,55/24,70 trong bộ chốt cũ là tối ưu trực tiếp trên test và không được dùng thay bảng mới.

## 3. Ablation và những kết luận cần giữ đúng

| Cấu hình | MAE chi tiêu (VND) | MAE số dư (VND) |
|---|---:|---:|
| Đầy đủ | 108.580,77 | 623.752,49 |
| Bỏ lịch sử chu kỳ cá nhân | 108.578,06 | 637.201,76 |
| Bỏ nhóm lịch/thống kê gần đây | 120.279,85 | 630.616,57 |

- Bỏ lịch sử chu kỳ cá nhân gần như không thay MAE chi tiêu (-0,0025%), nhưng MAE số dư tăng 2,16%.
- Bỏ nhóm lịch/thống kê gần đây làm MAE chi tiêu tăng 10,77%, MAE số dư tăng 1,10%. Cấu hình này vẫn giữ h, D, chuẩn hóa mean28 và đặc trưng lịch sử chu kỳ; không diễn giải thành bỏ mọi thông tin lịch/chi tiêu.
- Chênh lệch F1 giữa XGB+risk và XGB dùng điểm biên, tại ngưỡng F1 validation, có CI95% chứa 0 ở cả ba seed. Chưa có bằng chứng lớp risk tăng F1 rõ ràng.
- Ở cùng mục tiêu Precision validation với B1, chênh Recall của XGB+risk có CI95% dương ở cả ba seed; chênh Precision có CI chứa 0. Chưa thể khẳng định tương đương Precision vì chưa định trước biên tương đương.
- Bootstrap giữ ngưỡng cố định, chưa bao gồm toàn bộ bất định do huấn luyện/chọn ngưỡng. Mean/SD qua ba seed là thống kê mô tả.
- Dữ liệu vẫn mô phỏng; test đã từng được xem trong phát triển dự án. Đây là đánh giá bổ sung trên bộ chuẩn hiện có, không phải một bộ kiểm chứng mới hoàn toàn chưa từng sử dụng. User-holdout có lịch sử người dùng để tạo đặc trưng, chưa phải cold start.

## 4. Đối chiếu hoàn tất

- Ngày 24/10 đã đọc lại 12 checkpoint: SHA256 của nguồn và các file kết quả đều khớp, không có file sai chữ ký.
- 168 giá trị MAE/chỉ số cảnh báo tại chính sách cũ đối chiếu với kết quả trước nâng cấp có chênh lệch bằng 0: `baseline_reproduction.csv`.
- Tính lại bảng chính sách từ điểm CSV đã lưu cho sáu cấu hình temporal/user-holdout không làm đổi chỉ số: `cache_reload_consistency.csv`. CSV điểm được đọc theo round-trip để bảo toàn so sánh tại ngưỡng như 1/3.
- Đã phân tích cú pháp các file Python và nhập CSV mẫu bằng chế độ mặc định nghiêm ngặt; mẫu không cần điền ô/ngày thiếu. Metadata nằm trong `data_quality.json`.
- Đã dựng và xem hai hình `fig_policy_tradeoff.png`, `fig_ablation.png`.
- Chưa chạy lại toàn bộ bộ kiểm thử tự động hoặc pipeline phụ độ nhạy/SHAP/demo; không nhận các phần này là đã được chạy lại trong đợt nâng cấp.
- Runtime thực tế: Python 3.13.9, XGBoost 3.4.1; các gói khác xem `runtime_packages.json`. Môi trường khác một số phiên bản của bộ chốt cũ; 168 chỉ số đối chiếu nêu trên vẫn tái lập đúng.
- Báo cáo cuối kỳ không bị sửa. SHA256 trước/sau: `74774693b8843de692d30812df7938d6f41d74337c8b1d7b11f7db98335dde03`.

## 5. Ước lượng điểm theo bằng chứng dự án

| Tiêu chí | Trước | Sau | Căn cứ |
|---|---:|---:|---|
| Bài toán | 13/15 | 13/15 | Phạm vi và cam kết giữa kỳ giữ nguyên |
| Kỹ thuật | 17/20 | 19/20 | Ngưỡng chọn trên validation, đối chứng chính sách và ablation |
| Dữ liệu | 13/15 | 14/15 | Chính sách thiếu dữ liệu rõ, có dấu vết và hồ sơ nhất quán |
| Kết quả | 17/20 | 18/20 | CI từng seed, đo ngưỡng vận hành, phân tích đánh đổi và giới hạn |
| Áp dụng | 8/10 | 8/10 | Bằng chứng vận hành tốt hơn, chưa có đánh giá sử dụng thực tế |
| AI/tự làm | 8/10 | 8/10 | Đã ghi AI trong nhật ký; phần tự làm/hiểu bài cần minh chứng của nhóm |
| Coreach | 0/5 theo hồ sơ | 0/5 theo hồ sơ | Không có minh chứng mới |
| Trình bày/Q&A | Chưa chấm /5 | Chưa chấm /5 | Cần đánh giá buổi trình bày |

**Kỹ thuật + dữ liệu + kết quả: khoảng 47/55 → 51/55. Tổng phần đánh giá từ hồ sơ: khoảng 76/95 → 80/95.** Đây là ước lượng chủ quan; báo cáo DOCX chưa được bổ sung bằng chứng mới, nên không tự coi đây là điểm bản nộp hiện tại.

## 6. File dùng khi cập nhật báo cáo sau

- `summary/UPGRADE_RESULTS.md`: bảng chính sách và phương pháp.
- `summary/policies_per_seed.csv`, `policies_mean.csv`, `policies_sd.csv`: kết quả từng seed và tổng hợp.
- `summary/bootstrap_per_seed.csv`, `bootstrap_seed_summary.csv`: bootstrap ngưỡng cố định.
- `summary/same_precision_per_seed.csv`, `same_precision_bootstrap_per_seed.csv`: phép so theo tiêu chí giữa kỳ.
- `summary/original_bootstrap_per_seed.csv`: CI từng seed của phân tích cũ; FAR trong bảng này vẫn là đường cong mô tả.
- `summary/ablation_per_seed.csv`, `ablation_summary.csv`: thí nghiệm bỏ nhóm đặc trưng.
- `summary/fig_policy_tradeoff.png`, `fig_ablation.png`: hai hình bổ sung.
- `PROTOCOL.md`, `run_manifest.json`, từng `complete.json`: quy trình và thông tin tái lập.

Khi sửa báo cáo sau, cần cập nhật số chi phí, cách diễn giải FAR/CI, kết quả ablation và khai báo AI cho các module mới. Các phần Coreach và đóng góp thật của thành viên không được suy diễn từ mã nguồn.
