# Đánh giá phụ trên người dùng giữ riêng

Kết quả trung bình ± độ lệch chuẩn qua 3 seed. Đây là phép thử tổng quát hóa bổ sung; đánh giá chính theo thời gian vẫn nằm trong `results/final/RESULTS.md`.

## Cách chia

Mỗi người chỉ thuộc một vai trò. Nhóm train dùng chu kỳ train, nhóm calib dùng chu kỳ calib, nhóm val dùng chu kỳ val và nhóm test dùng chu kỳ test. Các vai trò người dùng không giao nhau; việc tạo đặc trưng cho một người vẫn dùng lịch sử giao dịch trước thời điểm dự báo của chính người đó.

```
      n_users_train  n_users_calib  n_users_val  n_users_test  n_points_train  n_points_calib  n_points_val  n_points_test
seed                                                                                                                      
1             150.0           45.0         45.0          60.0         44233.0          4803.0        4892.0         6452.0
2             150.0           45.0         45.0          60.0         44259.0          4711.0        4899.0         6434.0
3             150.0           45.0         45.0          60.0         44209.0          4752.0        4873.0         6452.0
```

## Sai số dự báo trên nhóm test chưa dùng ở các vai trò khác (VND)

| Mô hình | MAE chi tiêu | RMSE chi tiêu | MAE số dư | RMSE số dư |
|---|---:|---:|---:|---:|
| B1 | 129153 ± 3016 | 255727 ± 10175 | 1001085 ± 14450 | 1745193 ± 183458 |
| B2 | 129634 ± 1327 | 264171 ± 11712 | 840986 ± 29872 | 1446194 ± 232579 |
| XGB | 108818 ± 1707 | 237968 ± 11257 | 631766 ± 38007 | 1123762 ± 168444 |

## Chất lượng cảnh báo trên nhóm test giữ riêng

| Mô hình | Precision | Recall | F1 | Cycle recall | False alarm theo chu kỳ |
|---|---:|---:|---:|---:|---:|
| B1 | 0,545 ± 0,023 | 0,792 ± 0,013 | 0,645 ± 0,015 | 0,991 ± 0,008 | 0,650 ± 0,045 |
| B2 | 0,537 ± 0,026 | 0,810 ± 0,018 | 0,646 ± 0,017 | 0,981 ± 0,008 | 0,580 ± 0,080 |
| B2+risk | 0,569 ± 0,042 | 0,795 ± 0,019 | 0,662 ± 0,024 | 0,981 ± 0,016 | 0,606 ± 0,120 |
| XGB | 0,570 ± 0,049 | 0,813 ± 0,016 | 0,670 ± 0,030 | 0,986 ± 0,015 | 0,548 ± 0,120 |
| XGB+risk | 0,566 ± 0,038 | 0,816 ± 0,046 | 0,667 ± 0,012 | 0,986 ± 0,014 | 0,676 ± 0,115 |
| XGB+risk(k=2) | 0,552 ± 0,031 | 0,803 ± 0,030 | 0,653 ± 0,013 | 0,995 ± 0,008 | 0,655 ± 0,089 |

## So sánh ở Precision mục tiêu của B1

Ngưỡng được chọn trên validation của nhóm người dùng riêng cho vai trò val, sau đó giữ nguyên trên nhóm test. Precision validation và test được báo riêng.

| Mô hình | Precision mục tiêu | Precision val | Precision test | Recall test | Cycle recall test | Báo sớm (ngày, bỏ sót = 0) |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 0,597 ± 0,086 | 0,597 ± 0,086 | 0,544 ± 0,022 | 0,792 ± 0,012 | 0,991 ± 0,008 | 22,4 ± 0,6 |
| B2 | 0,597 ± 0,086 | 0,597 ± 0,086 | 0,551 ± 0,063 | 0,805 ± 0,021 | 0,976 ± 0,022 | 22,1 ± 0,4 |
| B2+risk | 0,597 ± 0,086 | 0,597 ± 0,086 | 0,558 ± 0,025 | 0,808 ± 0,022 | 0,981 ± 0,016 | 23,2 ± 0,5 |
| XGB | 0,597 ± 0,086 | 0,597 ± 0,086 | 0,547 ± 0,058 | 0,828 ± 0,019 | 0,986 ± 0,015 | 22,6 ± 0,6 |
| XGB+risk | 0,597 ± 0,086 | 0,598 ± 0,086 | 0,557 ± 0,041 | 0,832 ± 0,019 | 0,990 ± 0,017 | 23,5 ± 0,7 |

## Giới hạn

Đây vẫn là dữ liệu mô phỏng. Phép thử giữ riêng người dùng chỉ cho biết khả năng chuyển sang người mô phỏng khác trong cùng simulator; nó không thay thế kiểm định với dữ liệu giao dịch thật. Chỉ có 60 người mô phỏng trong mỗi nhóm test seed, nên xem đây là đánh giá phụ và đọc cùng độ lệch giữa các seed.
