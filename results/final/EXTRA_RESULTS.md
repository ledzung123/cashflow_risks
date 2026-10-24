# Bổ sung cho tiêu chí Kỹ thuật và Kết quả (test, trung bình ± độ lệch chuẩn qua 3 seed)

## So XGBoost với mô hình khác (cùng đặc trưng)

|                      | MAE_spend     | MAE_balance    | f1            | auroc         | recall_at_far20   | lead_at_far20   | fit_seconds   | pred_ms_per_1k   |
|:---------------------|:--------------|:---------------|:--------------|:--------------|:------------------|:----------------|:--------------|:-----------------|
| B1                   | 131066 ± 2836 | 969519 ± 12774 | 0,656 ± 0,018 | 0,825 ± 0,012 | 0,743 ± 0,024     | 14,5 ± 0,7      | 0,0 ± 0,0     | 3 ± 2            |
| B2                   | 128358 ± 2022 | 813502 ± 17697 | 0,679 ± 0,015 | 0,847 ± 0,011 | 0,827 ± 0,026     | 16,6 ± 1,0      | 0,0 ± 0,0     | 4 ± 2            |
| Ridge (tuyến tính)   | 114936 ± 2306 | 638540 ± 12952 | 0,691 ± 0,013 | 0,867 ± 0,008 | 0,933 ± 0,009     | 17,4 ± 0,3      | 6,5 ± 1,1     | 46 ± 15          |
| Random Forest        | 108839 ± 2248 | 627242 ± 11847 | 0,700 ± 0,017 | 0,872 ± 0,011 | 0,915 ± 0,012     | 17,7 ± 0,4      | 16,2 ± 1,2    | 74 ± 26          |
| HistGradientBoosting | 108626 ± 2284 | 625234 ± 10331 | 0,700 ± 0,015 | 0,872 ± 0,010 | 0,939 ± 0,008     | 18,0 ± 0,3      | 10,0 ± 0,3    | 96 ± 34          |
| XGBoost              | 108581 ± 2284 | 623752 ± 12033 | 0,700 ± 0,016 | 0,872 ± 0,010 | 0,935 ± 0,010     | 18,0 ± 0,3      | 20,2 ± 5,0    | 57 ± 13          |

## Chi phí trên 100 điểm quyết định (báo nhầm = 1, bỏ sót = r)

|                                           |   r=1 |   r=2 |   r=3 |   r=5 |   r=10 |   r=20 |
|:------------------------------------------|------:|------:|------:|------:|-------:|-------:|
| B1                                        | 19.83 | 28.62 | 35.64 | 46.44 |  64.42 |  71.87 |
| B2                                        | 17.68 | 26.55 | 33.37 | 44.09 |  61.49 |  71.63 |
| XGB (điểm biên)                           | 15.55 | 24.98 | 32.02 | 42.12 |  56.31 |  68.17 |
| XGB + p                                   | 15.51 | 24.7  | 30.77 | 38.66 |  49.18 |  59.48 |
| XGB + p, ngưỡng Bayes 1/(1+r), không tune | 15.6  | 24.83 | 30.81 | 38.75 |  49.42 |  59.64 |

## Khoảng tin cậy bootstrap theo người (500 lần... xem boot_seed), trung bình 3 seed

|                                                                |    chênh_TB |   ci_thấp_TB |   ci_cao_TB |   số_seed_CI_trên_0 |   số_seed_CI_dưới_0 |
|:---------------------------------------------------------------|------------:|-------------:|------------:|--------------------:|--------------------:|
| ('XGB (điểm biên) - B2', 'AUROC')                              |      0.0248 |       0.0183 |      0.0315 |                   3 |                   0 |
| ('XGB (điểm biên) - B2', 'F1 (ngưỡng chọn trên val)')          |      0.0209 |       0.0081 |      0.0335 |                   3 |                   0 |
| ('XGB (điểm biên) - B2', 'MAE chi tiêu ngày')                  | -19776.8    |  -21907.8    | -17691.6    |                   0 |                   3 |
| ('XGB (điểm biên) - B2', 'tỉ lệ bắt được ở báo nhầm 20%')      |      0.1084 |       0.0621 |      0.1598 |                   3 |                   0 |
| ('XGB + p - B2', 'AUROC')                                      |      0.0411 |       0.0323 |      0.0503 |                   3 |                   0 |
| ('XGB + p - B2', 'F1 (ngưỡng chọn trên val)')                  |      0.0225 |       0.0101 |      0.0345 |                   3 |                   0 |
| ('XGB + p - B2', 'MAE chi tiêu ngày')                          | -19776.8    |  -21907.8    | -17691.6    |                   0 |                   3 |
| ('XGB + p - B2', 'tỉ lệ bắt được ở báo nhầm 20%')              |      0.1188 |       0.0673 |      0.1725 |                   3 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'AUROC')                         |      0.0162 |       0.0105 |      0.0227 |                   3 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'F1 (ngưỡng chọn trên val)')     |      0.0016 |      -0.0039 |      0.0069 |                   0 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'MAE chi tiêu ngày')             |      0      |       0      |      0      |                   0 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'tỉ lệ bắt được ở báo nhầm 20%') |      0.0104 |      -0.0085 |      0.0276 |                   0 |                   0 |

## Theo nhóm (XGB + p, trung bình 3 seed)

|                               |   tỉ_lệ_thiếu_tiền |   p_trung_bình |   precision |   recall |   fpr_điểm |   báo_nhầm_theo_chu_kỳ |   auroc |   ece |   seed |
|:------------------------------|-------------------:|---------------:|------------:|---------:|-----------:|-----------------------:|--------:|------:|-------:|
| ('kiểu chi tiêu', 'even')     |              0.263 |          0.241 |       0.746 |    0.76  |      0.096 |                  0.304 |   0.925 | 0.034 |      2 |
| ('kiểu chi tiêu', 'front')    |              0.272 |          0.293 |       0.671 |    0.853 |      0.155 |                  0.408 |   0.936 | 0.034 |      2 |
| ('kiểu chi tiêu', 'spike')    |              0.315 |          0.277 |       0.601 |    0.622 |      0.19  |                  0.573 |   0.798 | 0.062 |      2 |
| ('kiểu chi tiêu', 'weekend')  |              0.269 |          0.281 |       0.629 |    0.787 |      0.172 |                  0.5   |   0.898 | 0.02  |      2 |
| ('thu nhập', 'allowance_1st') |              0.279 |          0.273 |       0.671 |    0.767 |      0.146 |                  0.431 |   0.899 | 0.014 |      2 |
| ('thu nhập', 'salary_25')     |              0.28  |          0.273 |       0.646 |    0.736 |      0.159 |                  0.455 |   0.878 | 0.02  |      2 |

## Độ trễ và kích thước mô hình

| mục                                                         |   median |   max |
|:------------------------------------------------------------|---------:|------:|
| 1 yêu cầu: dựng đặc trưng + dự báo (ms, trung vị 40 lần)    |     20.9 |  25.3 |
| 1 yêu cầu: lần chậm nhất trong 40 lần (ms)                  |     33.7 | 135.5 |
| kích thước file mô hình (KB)                                |    940.2 | 992.5 |
| số cây XGBoost                                              |    107   | 113   |
| số dòng lịch sử của người dùng trong yêu cầu                |    730   | 730   |
| tính xác suất p từ dự báo của 1 điểm (ms, trung vị 100 lần) |      1.7 |   1.8 |

## Kết luận tính từ số liệu

- MAE chi tiêu ngày (nghìn VND): B2 128.4, Ridge 114.9, Random Forest 108.8, HGB 108.6, XGBoost 108.6. XGBoost thấp hơn Ridge 5.5% và gần như bằng Random Forest, HGB (chênh 0.0%, 0.2%).
- Bắt được chu kỳ thiếu tiền ở mức báo nhầm 20%: B2 0.827, Ridge 0.933, XGBoost 0.935. Phần lớn lợi thế so với B1/B2 đến từ ĐẶC TRƯNG (lịch sử cá nhân, chuẩn hóa theo người) chứ không riêng từ XGBoost: mô hình tuyến tính với cùng đặc trưng đã gần bằng.
- Chi phí: với r = 2, XGB + p tốn 24.7 so với B2 26.6 (trên 100 điểm quyết định); ngưỡng Bayes 1/(1+r) cho 24.8 mà không cần tune, nhờ xác suất đã hiệu chỉnh.
- Độ trễ: 1 yêu cầu (dựng đặc trưng + dự báo, một người, ~730 dòng lịch sử) trung vị 21 ms; mô hình 940 KB.
