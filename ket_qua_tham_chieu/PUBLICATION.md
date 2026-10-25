# Bộ kết quả công bố ngày 23/10/2026

Đọc UPGRADE_RESULTS.md cho chính sách validation, user-holdout và ablation.
Extra_cost.csv dùng ngưỡng chi phí chọn trên validation từ checkpoint nâng cấp.
Extra_bootstrap.csv là mean/SD; CI95% từng seed nằm trong Extra_bootstrap_per_seed.csv.
policies_mean.csv và policies_sd.csv báo trung bình và SD riêng; bootstrap_per_seed.csv
là CI ghép cặp theo người ở ngưỡng cố định. Không có CI95% gộp bằng trung bình hai cận.

Các bảng Q1/Q2, mô hình thay thế, SHAP, hiệu chỉnh và độ nhạy giữ nguồn chạy lõi
trước đó. Các bảng policies/ablation có runtime nâng cấp riêng (upgrade_runtime_packages.json).
Đây là bộ bằng chứng có nhiều thí nghiệm được ghi nguồn, không phải một lần chạy duy nhất.
Không dùng FAR20 mô tả trong Lead_table/Extra_models/fig9 như ngưỡng vận hành:
chính sách vận hành là far20_val, với FAR thực tế trên test được báo riêng.
Test đã được xem trong phát triển; không gọi là bộ test mới chưa từng xem.

Tái tạo thí nghiệm: run_all.ps1 và run_upgrade.ps1. Lần công bố này đối chiếu
SHA256 của 12 checkpoint; bảng chi phí được lấy từ chính sách temporal đã lưu,
bảng CI được tổng hợp lại từ từng seed. Không huấn luyện lại hoặc đổi ngưỡng demo.
Bản trước cập nhật nằm trong publication_backups/20261023_224155.
