# Đánh giá nâng cấp — ngưỡng cố định từ validation

Đây là bằng chứng kỹ thuật bổ sung, không sửa báo cáo cuối kỳ. Các chính sách được
định trước (F1, FAR20, chi phí r=1/2/3/5/10/20, Bayes); không chọn chính sách tốt nhất theo test.
Test đã được xem trong phát triển dự án, nên đây là đánh giá bổ sung trên bộ chuẩn cũ,
không phải một tập kiểm chứng mới hoàn toàn chưa từng xem.

Chi phí tính trên 100 điểm quyết định, đơn vị một FP; không phải chi phí tiền thật.
FAR tính trên chu kỳ bình thường có ít nhất một điểm đủ điều kiện. Số ngày cảnh báo
cũng chỉ tính các điểm đủ điều kiện, không phải mọi ngày lịch. Cột thông báo một lần/
chu kỳ là phép đếm nếu chỉ gửi lần cảnh báo đầu; không chứng minh người dùng sẽ hành động.
FAR validation <=20% không bảo đảm FAR test <=20% khi phân phối thay đổi.

CI95% được báo riêng theo seed, bootstrap ghép cặp theo người, giữ cố định ngưỡng.
Không lấy trung bình cận CI thành CI95% chung; SD qua ba seed là mô tả độ biến thiên.
Phép bootstrap này không bao gồm bất định do huấn luyện/chọn ngưỡng. CI của chênh lệch
Precision/Recall tại mục tiêu Precision chung cũng được lưu riêng; không dùng việc CI
chứa 0 để kết luận tương đương, vì chưa định trước biên tương đương. Dòng FAR20 của
original_bootstrap_per_seed.csv vẫn là đường đánh đổi mô tả trên test cũ.

User-holdout giữ riêng người giữa các vai trò nhưng cho phép dùng lịch sử của chính
người đó để xây đặc trưng; không phải cold start và chưa đại diện dữ liệu thật.

## Chính sách cảnh báo (trung bình các seed)

| mode         | model    | policy      |   test_precision |   test_recall |   test_f1 |   test_cycle_recall |   test_cycle_false_alarm |   test_negative_alert_days_mean |   test_cost_per_100 |
|:-------------|:---------|:------------|-----------------:|--------------:|----------:|--------------------:|-------------------------:|--------------------------------:|--------------------:|
| time         | B1       | cost_r2_val |           0.5879 |        0.7454 |    0.6563 |              0.9887 |                   0.5701 |                          5.6228 |             28.9869 |
| time         | B1       | f1_val      |           0.5875 |        0.746  |    0.6563 |              0.9897 |                   0.5697 |                          5.6368 |            nan      |
| time         | B1       | far20_val   |           0.7305 |        0.2745 |    0.3988 |              0.7289 |                   0.1912 |                          1.074  |            nan      |
| time         | B2       | cost_r2_val |           0.6431 |        0.7258 |    0.6802 |              0.9673 |                   0.3888 |                          4.3601 |             26.7814 |
| time         | B2       | f1_val      |           0.6393 |        0.7288 |    0.679  |              0.9673 |                   0.3967 |                          4.4658 |            nan      |
| time         | B2       | far20_val   |           0.7943 |        0.4137 |    0.5436 |              0.8003 |                   0.1817 |                          1.139  |            nan      |
| time         | B2+risk  | bayes_r2    |           0.5846 |        0.7874 |    0.6707 |              0.9794 |                   0.5272 |                          5.979  |             27.5684 |
| time         | B2+risk  | cost_r2_val |           0.6331 |        0.74   |    0.6804 |              0.9719 |                   0.4251 |                          4.6579 |             26.7593 |
| time         | B2+risk  | f1_val      |           0.6372 |        0.735  |    0.6813 |              0.9709 |                   0.4156 |                          4.5171 |            nan      |
| time         | B2+risk  | far20_val   |           0.8015 |        0.5114 |    0.624  |              0.9145 |                   0.1794 |                          1.3564 |            nan      |
| time         | XGB      | cost_r2_val |           0.6522 |        0.746  |    0.6949 |              0.9813 |                   0.4057 |                          4.2787 |             25.442  |
| time         | XGB      | f1_val      |           0.6773 |        0.7252 |    0.6999 |              0.9776 |                   0.3724 |                          3.71   |            nan      |
| time         | XGB      | far20_val   |           0.8314 |        0.5426 |    0.6564 |              0.9284 |                   0.1893 |                          1.1774 |            nan      |
| time         | XGB+risk | bayes_r2    |           0.6741 |        0.7338 |    0.7024 |              0.9813 |                   0.4102 |                          3.7916 |             24.8337 |
| time         | XGB+risk | cost_r2_val |           0.6483 |        0.7635 |    0.701  |              0.9841 |                   0.4627 |                          4.4236 |             24.8254 |
| time         | XGB+risk | f1_val      |           0.6585 |        0.7517 |    0.7015 |              0.9832 |                   0.4425 |                          4.1753 |            nan      |
| time         | XGB+risk | far20_val   |           0.8211 |        0.5639 |    0.6685 |              0.9436 |                   0.1943 |                          1.3145 |            nan      |
| user_holdout | B1       | cost_r2_val |           0.5597 |        0.7851 |    0.6517 |              0.9951 |                   0.6189 |                          6.8611 |             29.9115 |
| user_holdout | B1       | f1_val      |           0.5448 |        0.7917 |    0.6452 |              0.9905 |                   0.6498 |                          7.1986 |            nan      |
| user_holdout | B1       | far20_val   |           0.7305 |        0.3073 |    0.4298 |              0.7825 |                   0.2098 |                          1.2351 |            nan      |
| user_holdout | B2       | cost_r2_val |           0.5726 |        0.7926 |    0.6601 |              0.9713 |                   0.511  |                          6.8426 |             29.3918 |
| user_holdout | B2       | f1_val      |           0.5373 |        0.81   |    0.6457 |              0.9815 |                   0.5802 |                          7.5601 |            nan      |
| user_holdout | B2       | far20_val   |           0.8122 |        0.4037 |    0.5341 |              0.7978 |                   0.1704 |                          1.0098 |            nan      |
| user_holdout | B2+risk  | bayes_r2    |           0.5917 |        0.7781 |    0.6718 |              0.9762 |                   0.5688 |                          5.8664 |             27.7971 |
| user_holdout | B2+risk  | cost_r2_val |           0.5539 |        0.8123 |    0.6575 |              0.9762 |                   0.6586 |                          7.2224 |             29.3474 |
| user_holdout | B2+risk  | f1_val      |           0.5687 |        0.7952 |    0.6622 |              0.9811 |                   0.6062 |                          6.6182 |            nan      |
| user_holdout | B2+risk  | far20_val   |           0.8075 |        0.5085 |    0.6225 |              0.9213 |                   0.1846 |                          1.3064 |            nan      |
| user_holdout | XGB      | cost_r2_val |           0.6083 |        0.7911 |    0.6804 |              0.9807 |                   0.5052 |                          6.0642 |             27.4065 |
| user_holdout | XGB      | f1_val      |           0.5703 |        0.8135 |    0.6695 |              0.9856 |                   0.5477 |                          6.77   |            nan      |
| user_holdout | XGB      | far20_val   |           0.8311 |        0.5536 |    0.664  |              0.9209 |                   0.2062 |                          1.2123 |            nan      |
| user_holdout | XGB+risk | bayes_r2    |           0.6621 |        0.745  |    0.7003 |              0.9717 |                   0.4634 |                          4.1509 |             25.2678 |
| user_holdout | XGB+risk | cost_r2_val |           0.6348 |        0.7784 |    0.6959 |              0.9668 |                   0.5189 |                          5.1303 |             25.7632 |
| user_holdout | XGB+risk | f1_val      |           0.5661 |        0.8163 |    0.6669 |              0.9864 |                   0.6758 |                          6.7844 |            nan      |
| user_holdout | XGB+risk | far20_val   |           0.8163 |        0.5611 |    0.6647 |              0.9394 |                   0.1943 |                          1.3768 |            nan      |

## Bỏ nhóm đặc trưng

| variant             |   MAE_spend |   MAE_balance |
|:--------------------|------------:|--------------:|
| full                |      108581 |        623752 |
| no_calendar_recent  |      120280 |        630617 |
| no_personal_history |      108578 |        637202 |

Hai ablation chỉ thay đầu vào mô hình, cùng chia tập/thuật toán/hyperparameter; mỗi mô hình early-stop trên validation. no_calendar_recent vẫn giữ h, D, số dư/ngưỡng, lịch sử chu kỳ và chuẩn hóa mean28; đây là bỏ một nhóm đặc trưng, không xóa mọi thông tin lịch/chi tiêu. So XGB với XGB+risk trong bảng chính sách là đối chứng có/không lớp xác suất trên cùng dự báo.
