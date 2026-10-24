# Bổ sung cho tiêu chí Kỹ thuật và Kết quả (test, trung bình ± độ lệch chuẩn qua 3 seed)

## So XGBoost với mô hình khác (cùng đặc trưng)

|                      | MAE_spend     | MAE_balance    | f1            | auroc         | recall_at_far20   | lead_at_far20   | fit_seconds   | pred_ms_per_1k   |
|:---------------------|:--------------|:---------------|:--------------|:--------------|:------------------|:----------------|:--------------|:-----------------|
| B1                   | 131066 ± 2836 | 969519 ± 12774 | 0,656 ± 0,018 | 0,825 ± 0,012 | 0,743 ± 0,024     | 14,5 ± 0,7      | 0,0 ± 0,0     | 1 ± 0            |
| B2                   | 128358 ± 2022 | 813502 ± 17697 | 0,679 ± 0,015 | 0,847 ± 0,011 | 0,827 ± 0,026     | 16,6 ± 1,0      | 0,0 ± 0,0     | 2 ± 0            |
| Ridge (tuyến tính)   | 114936 ± 2306 | 638540 ± 12952 | 0,691 ± 0,013 | 0,867 ± 0,008 | 0,933 ± 0,009     | 17,4 ± 0,3      | 4,2 ± 1,0     | 28 ± 4           |
| Random Forest        | 108839 ± 2248 | 627242 ± 11847 | 0,700 ± 0,017 | 0,872 ± 0,011 | 0,915 ± 0,012     | 17,7 ± 0,4      | 9,6 ± 0,4     | 31 ± 1           |
| HistGradientBoosting | 108626 ± 2284 | 625234 ± 10331 | 0,700 ± 0,015 | 0,872 ± 0,010 | 0,939 ± 0,008     | 18,0 ± 0,3      | 7,7 ± 1,2     | 59 ± 6           |
| XGBoost              | 108537 ± 2281 | 623894 ± 11479 | 0,698 ± 0,016 | 0,872 ± 0,010 | 0,934 ± 0,005     | 17,9 ± 0,4      | 12,8 ± 1,1    | 29 ± 1           |

## Chi phí trên 100 điểm quyết định (báo nhầm = 1, bỏ sót = r)

|                                           |   r=1 |   r=2 |   r=3 |   r=5 |   r=10 |   r=20 |
|:------------------------------------------|------:|------:|------:|------:|-------:|-------:|
| B1                                        | 19.83 | 28.62 | 35.64 | 46.44 |  64.42 |  71.87 |
| B2                                        | 17.68 | 26.55 | 33.37 | 44.09 |  61.49 |  71.63 |
| XGB (điểm biên)                           | 15.53 | 25.01 | 32.04 | 42.15 |  56.21 |  68.24 |
| XGB + p                                   | 15.5  | 24.69 | 30.75 | 38.71 |  49.29 |  59.48 |
| XGB + p, ngưỡng Bayes 1/(1+r), không tune | 15.64 | 24.78 | 30.86 | 38.88 |  49.49 |  59.83 |

## Khoảng tin cậy bootstrap theo người (500 lần... xem boot_seed), trung bình 3 seed

|                                                                |    chênh_TB |   ci_thấp_TB |   ci_cao_TB |   số_seed_CI_trên_0 |   số_seed_CI_dưới_0 |
|:---------------------------------------------------------------|------------:|-------------:|------------:|--------------------:|--------------------:|
| ('XGB (điểm biên) - B2', 'AUROC')                              |      0.0247 |       0.018  |      0.0314 |                   3 |                   0 |
| ('XGB (điểm biên) - B2', 'F1 (ngưỡng chọn trên val)')          |      0.0188 |       0.0062 |      0.0317 |                   3 |                   0 |
| ('XGB (điểm biên) - B2', 'MAE chi tiêu ngày')                  | -19820.1    |  -21970      | -17727.5    |                   0 |                   3 |
| ('XGB (điểm biên) - B2', 'tỉ lệ bắt được ở báo nhầm 20%')      |      0.1075 |       0.0608 |      0.1579 |                   3 |                   0 |
| ('XGB + p - B2', 'AUROC')                                      |      0.0409 |       0.032  |      0.0502 |                   3 |                   0 |
| ('XGB + p - B2', 'F1 (ngưỡng chọn trên val)')                  |      0.024  |       0.0119 |      0.0362 |                   3 |                   0 |
| ('XGB + p - B2', 'MAE chi tiêu ngày')                          | -19820.1    |  -21970      | -17727.5    |                   0 |                   3 |
| ('XGB + p - B2', 'tỉ lệ bắt được ở báo nhầm 20%')              |      0.1197 |       0.0686 |      0.1703 |                   3 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'AUROC')                         |      0.0163 |       0.0105 |      0.0228 |                   3 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'F1 (ngưỡng chọn trên val)')     |      0.0052 |       0.0006 |      0.0098 |                   1 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'MAE chi tiêu ngày')             |      0      |       0      |      0      |                   0 |                   0 |
| ('XGB + p - XGB (điểm biên)', 'tỉ lệ bắt được ở báo nhầm 20%') |      0.0122 |      -0.0077 |      0.0295 |                   0 |                   0 |

## Theo nhóm (XGB + p, trung bình 3 seed)

|                               |   tỉ_lệ_thiếu_tiền |   p_trung_bình |   precision |   recall |   fpr_điểm |   báo_nhầm_theo_chu_kỳ |   auroc |   ece |   seed |
|:------------------------------|-------------------:|---------------:|------------:|---------:|-----------:|-----------------------:|--------:|------:|-------:|
| ('kiểu chi tiêu', 'even')     |              0.263 |          0.242 |       0.758 |    0.75  |      0.09  |                  0.29  |   0.925 | 0.034 |      2 |
| ('kiểu chi tiêu', 'front')    |              0.272 |          0.291 |       0.684 |    0.841 |      0.144 |                  0.385 |   0.936 | 0.033 |      2 |
| ('kiểu chi tiêu', 'spike')    |              0.315 |          0.277 |       0.612 |    0.608 |      0.178 |                  0.542 |   0.798 | 0.062 |      2 |
| ('kiểu chi tiêu', 'weekend')  |              0.269 |          0.28  |       0.643 |    0.775 |      0.16  |                  0.475 |   0.898 | 0.02  |      2 |
| ('thu nhập', 'allowance_1st') |              0.279 |          0.272 |       0.683 |    0.754 |      0.135 |                  0.412 |   0.899 | 0.014 |      2 |
| ('thu nhập', 'salary_25')     |              0.28  |          0.273 |       0.66  |    0.725 |      0.149 |                  0.429 |   0.877 | 0.02  |      2 |

## Độ trễ và kích thước mô hình

| mục                                                         |   median |    max |
|:------------------------------------------------------------|---------:|-------:|
| 1 yêu cầu: dựng đặc trưng + dự báo (ms, trung vị 40 lần)    |     13.8 |   14   |
| 1 yêu cầu: lần chậm nhất trong 40 lần (ms)                  |     21   |   28.7 |
| kích thước file mô hình (KB)                                |   1028   | 1056.4 |
| số cây XGBoost                                              |    120   |  128   |
| số dòng lịch sử của người dùng trong yêu cầu                |    730   |  730   |
| tính xác suất p từ dự báo của 1 điểm (ms, trung vị 100 lần) |      1.1 |    1.1 |

## Kết luận tính từ số liệu

- MAE chi tiêu ngày (nghìn VND): B2 128.4, Ridge 114.9, Random Forest 108.8, HGB 108.6, XGBoost 108.5. XGBoost thấp hơn Ridge 5.6% và gần như bằng Random Forest, HGB (chênh 0.1%, 0.3%).
- Bắt được chu kỳ thiếu tiền ở mức báo nhầm 20%: B2 0.827, Ridge 0.933, XGBoost 0.934. Phần lớn lợi thế so với B1/B2 đến từ ĐẶC TRƯNG (lịch sử cá nhân, chuẩn hóa theo người) chứ không riêng từ XGBoost: mô hình tuyến tính với cùng đặc trưng đã gần bằng.
- Chi phí: với r = 2, XGB + p tốn 24.7 so với B2 26.6 (trên 100 điểm quyết định); ngưỡng Bayes 1/(1+r) cho 24.8 mà không cần tune, nhờ xác suất đã hiệu chỉnh.
- Độ trễ: 1 yêu cầu (dựng đặc trưng + dự báo, một người, ~730 dòng lịch sử) trung vị 14 ms; mô hình 1028 KB.
