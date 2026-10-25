# Quy trình đánh giá bổ sung

## Phạm vi

Giữ bài toán, simulator 300 người × 24 chu kỳ, seed 1/2/3, phân chia thời gian và user-holdout của dự án. Bộ test này đã được xem khi phát triển và rà soát dự án. Lần nâng cấp này sửa quy trình phân tích trên bộ chuẩn hiện có; không gọi nó là một bộ test mới chưa từng xem.

Không chỉnh file báo cáo cuối kỳ. Không cập nhật ngưỡng mặc định của demo bằng cách chọn kết quả tốt nhất trên test.

## Các lựa chọn cố định

- Mô hình đầy đủ: cùng tham số XGBoost đã có; early stopping dùng validation. Lớp xác suất được chọn giữa cum/cumb/mc bằng Brier validation; calib chỉ dùng ước lượng phân phối phần dư.
- F1: dùng ngưỡng tối đa F1 validation theo lưới cũ để so trực tiếp với kết quả trước.
- Chi phí: FP=1; FN=r với r ∈ {1,2,3,5,10,20}. Duyệt chính xác các ngưỡng có thể trên validation, bao gồm cảnh báo tất cả/không cảnh báo; hòa chi phí thì chọn ngưỡng cao hơn. Chi phí test tính sau khi khóa ngưỡng.
- FAR: chọn phân vị cao hơn của điểm lớn nhất trong từng chu kỳ âm validation, mục tiêu 20%; báo FAR và Recall đạt được trên test. Không ép FAR test bằng 20%.
- Bayes: p > 1/(1+r), cố định từ giả định chi phí. Chỉ áp dụng cho mô hình có xác suất.
- Báo đầy đủ từng chính sách; không công bố một cấu hình là thắng cuộc dựa vào bảng test.

## Ablation

Hai cấu hình được huấn luyện lại trên cùng ba seed, cùng hyperparameter, mỗi cấu hình early-stop trên validation:

1. Bỏ lịch sử chu kỳ cá nhân: hist_dic_rel, hist_smooth_rel, n_prev.
2. Bỏ nhóm lịch/thống kê gần đây: tgt_wd, tgt_weekend, tgt_dic, days_after, dic_t, mean7_rel, mean14_rel, std14_rel, max14_rel, last1_rel, big28, we_ratio, b2_rel.

Cấu hình thứ hai vẫn giữ h, D, bal_rel, theta_rel và lịch sử chu kỳ; phép chuẩn hóa bằng mean28 vẫn giữ nguyên. Không diễn giải nó thành loại hết thông tin lịch hoặc lịch sử chi tiêu.

So XGB dùng điểm biên với XGB+risk trên cùng dự báo là đối chứng có/không lớp xác suất. Đây là một đối chứng riêng với thí nghiệm bỏ đặc trưng.

## Độ tin cậy và giới hạn

- Bootstrap ghép cặp 500 lần theo người dùng cho chênh lệch chỉ số của các chính sách F1, FAR20 và chi phí r=2; một lượt lấy mẫu dùng chung người cho hai mô hình so sánh.
- Ngưỡng giữ nguyên trong bootstrap. CI95% điều kiện theo mô hình và ngưỡng đã huấn luyện/chọn, không chứa toàn bộ bất định huấn luyện/chọn ngưỡng.
- Công bố CI từng seed và trung bình/SD qua seed; không lấy trung bình cận CI làm khoảng tin cậy chung. Số resample hợp lệ được lưu khi Precision không xác định vì không có cảnh báo.
- Báo nhầm theo chu kỳ và số ngày cảnh báo được đo trên chu kỳ có ít nhất một điểm quyết định đủ điều kiện. Không đồng nhất với toàn bộ chu kỳ lịch.
- User-holdout là người giữ riêng nhưng đã có lịch sử quan sát. Không chứng minh cold start, dữ liệu thật hoặc hiệu quả can thiệp hành vi.

## Tái lập

`complete.json` của từng cấu hình ghi SHA256 nguồn, runtime và file kết quả. Chỉ tái sử dụng checkpoint khi các chữ ký còn khớp. `forecasts.npz`, `val_scores.csv`, `test_scores.csv` cho phép tái tính chính sách mà không huấn luyện lại. `runtime_packages.json` ghi phiên bản thực tế; không giả định môi trường hiện tại khớp toàn bộ môi trường tạo bộ số cũ.
