# Kết quả cuối cùng (test, trung bình ± độ lệch chuẩn qua 3 seed: 1, 2, 3)

## Q1 - Sai số dự báo (VND)

|                            | MAE_spend     | RMSE_spend    | MAE_balance    | RMSE_balance    | MAE_spend so với B2   | MAE_balance so với B2   |
|:---------------------------|:--------------|:--------------|:---------------|:----------------|:----------------------|:------------------------|
| B1 (TB 14 ngày)            | 131066 ± 2836 | 251495 ± 3900 | 969519 ± 12774 | 1619399 ± 50157 | +2,1%                 | +19,2%                  |
| B2 (TB cùng thứ)           | 128358 ± 2022 | 255063 ± 3157 | 813502 ± 17697 | 1317702 ± 74982 | +0,0%                 | +0,0%                   |
| XGB (cảnh báo theo biên m) | 108581 ± 2284 | 229512 ± 3425 | 623752 ± 12033 | 1031614 ± 55440 | -15,4%                | -23,3%                  |

## Q2 - Chất lượng cảnh báo

|                            | precision     | recall        | f1            | auroc         | auprc         | ks            | cycle_recall   | cycle_false_alarm   | mean_days_early   | brier_test    | ece_test      |
|:---------------------------|:--------------|:--------------|:--------------|:--------------|:--------------|:--------------|:---------------|:--------------------|:------------------|:--------------|:--------------|
| B1 (TB 14 ngày)            | 0,588 ± 0,042 | 0,746 ± 0,025 | 0,656 ± 0,018 | 0,825 ± 0,012 | 0,657 ± 0,028 | 0,545 ± 0,018 | 0,990 ± 0,002  | 0,570 ± 0,053       | 22,7 ± 0,2        | —             | —             |
| B2 (TB cùng thứ)           | 0,639 ± 0,056 | 0,729 ± 0,037 | 0,679 ± 0,015 | 0,847 ± 0,011 | 0,716 ± 0,027 | 0,575 ± 0,017 | 0,967 ± 0,018  | 0,397 ± 0,058       | 22,1 ± 0,3        | —             | —             |
| XGB (cảnh báo theo biên m) | 0,677 ± 0,038 | 0,725 ± 0,011 | 0,700 ± 0,016 | 0,872 ± 0,010 | 0,778 ± 0,019 | 0,594 ± 0,017 | 0,978 ± 0,010  | 0,372 ± 0,017       | 21,7 ± 0,1        | —             | —             |
| XGB + p > p*               | 0,658 ± 0,034 | 0,752 ± 0,010 | 0,702 ± 0,015 | 0,888 ± 0,008 | 0,802 ± 0,017 | 0,606 ± 0,015 | 0,983 ± 0,008  | 0,442 ± 0,032       | 23,0 ± 0,3        | 0,112 ± 0,005 | 0,013 ± 0,006 |
| XGB + p > p* (k=2)         | 0,662 ± 0,038 | 0,713 ± 0,017 | 0,686 ± 0,015 | —             | —             | —             | 0,972 ± 0,014  | 0,410 ± 0,048       | 21,9 ± 0,6        | 0,112 ± 0,005 | 0,013 ± 0,006 |
| B2 + p > p* (đối chứng)    | 0,637 ± 0,048 | 0,735 ± 0,024 | 0,681 ± 0,018 | 0,864 ± 0,010 | 0,764 ± 0,023 | 0,575 ± 0,016 | 0,971 ± 0,012  | 0,416 ± 0,051       | 22,2 ± 0,3        | 0,129 ± 0,007 | 0,062 ± 0,011 |

## Chỉ số cho p_t (test)

|                | XGB + p > p*   | B2 + p > p* (đối chứng)   |
|:---------------|:---------------|:--------------------------|
| brier          | 0,112 ± 0,005  | 0,129 ± 0,007             |
| brier_skill    | 0,447 ± 0,024  | 0,360 ± 0,044             |
| log_loss       | 0,359 ± 0,015  | 0,415 ± 0,021             |
| log_loss_skill | 0,397 ± 0,026  | 0,302 ± 0,041             |
| auroc          | 0,888 ± 0,008  | 0,864 ± 0,010             |
| auprc          | 0,802 ± 0,017  | 0,764 ± 0,023             |
| cal_slope      | 0,970 ± 0,070  | 0,717 ± 0,035             |
| cal_intercept  | 0,037 ± 0,116  | -0,536 ± 0,075            |
| ece            | 0,013 ± 0,006  | 0,062 ± 0,011             |
| mce            | 0,057 ± 0,025  | 0,188 ± 0,038             |
| sharpness      | 0,298 ± 0,000  | 0,330 ± 0,002             |
| cov50          | 0,501 ± 0,004  | 0,492 ± 0,007             |
| cov80          | 0,796 ± 0,001  | 0,798 ± 0,007             |
| cov90          | 0,895 ± 0,005  | 0,899 ± 0,008             |

## Chỉ số p_t theo kiểu chi tiêu (XGB + p > p*)

| pattern   | pos_rate      | brier         | auroc         | ece           | cal_slope     | cov80         |
|:----------|:--------------|:--------------|:--------------|:--------------|:--------------|:--------------|
| even      | 0,263 ± 0,013 | 0,093 ± 0,007 | 0,925 ± 0,014 | 0,034 ± 0,018 | 1,323 ± 0,159 | 0,830 ± 0,013 |
| front     | 0,272 ± 0,040 | 0,088 ± 0,002 | 0,936 ± 0,010 | 0,034 ± 0,003 | 1,306 ± 0,156 | 0,834 ± 0,005 |
| weekend   | 0,269 ± 0,041 | 0,108 ± 0,012 | 0,898 ± 0,009 | 0,020 ± 0,010 | 1,092 ± 0,049 | 0,822 ± 0,008 |
| spike     | 0,315 ± 0,027 | 0,159 ± 0,012 | 0,798 ± 0,018 | 0,062 ± 0,016 | 0,556 ± 0,084 | 0,697 ± 0,019 |

## Chỉ số p_t theo số ngày còn lại D (XGB + p > p*)

| D     | pos_rate      | brier         | auroc         | ece           | cal_slope     | cov80         |
|:------|:--------------|:--------------|:--------------|:--------------|:--------------|:--------------|
| 3-4   | 0,173 ± 0,008 | 0,047 ± 0,006 | 0,965 ± 0,014 | 0,013 ± 0,004 | 0,973 ± 0,189 | 0,789 ± 0,008 |
| 5-7   | 0,243 ± 0,000 | 0,062 ± 0,005 | 0,956 ± 0,006 | 0,013 ± 0,002 | 0,970 ± 0,059 | 0,792 ± 0,013 |
| 8-11  | 0,278 ± 0,005 | 0,079 ± 0,003 | 0,938 ± 0,004 | 0,014 ± 0,002 | 0,973 ± 0,040 | 0,800 ± 0,011 |
| 12-16 | 0,293 ± 0,006 | 0,101 ± 0,005 | 0,906 ± 0,007 | 0,017 ± 0,007 | 0,965 ± 0,062 | 0,801 ± 0,004 |
| 17-21 | 0,295 ± 0,006 | 0,123 ± 0,006 | 0,867 ± 0,011 | 0,020 ± 0,008 | 0,950 ± 0,077 | 0,790 ± 0,003 |
| 22-31 | 0,297 ± 0,005 | 0,155 ± 0,005 | 0,800 ± 0,015 | 0,024 ± 0,006 | 0,992 ± 0,090 | 0,799 ± 0,005 |

## Kiểm chứng giả định phần dư độc lập

| phép thử                                           | giá trị (TB ± std)   |
|:---------------------------------------------------|:---------------------|
| Tương quan phần dư cách 1 ngày                     | 0,010 ± 0,017        |
| Tương quan phần dư cách 2 ngày                     | 0,014 ± 0,011        |
| Tương quan phần dư cách 3 ngày                     | 0,013 ± 0,009        |
| Tương quan phần dư cách 7 ngày                     | 0,019 ± 0,021        |
| Tỉ số phương sai, D=5 (độc lập = 1)                | 1,014 ± 0,078        |
| Tỉ số phương sai, D=10                             | 1,096 ± 0,047        |
| Tỉ số phương sai, D=15                             | 1,134 ± 0,215        |
| Tỉ số phương sai, D=20                             | 1,161 ± 0,109        |
| Tỉ số phương sai, D=25                             | 1,235 ± 0,084        |
| Độ phủ khoảng 80%, mc, all (danh nghĩa 0,80)       | 0,752 ± 0,002        |
| Độ phủ khoảng 80%, mc, even (danh nghĩa 0,80)      | 0,769 ± 0,016        |
| Độ phủ khoảng 80%, mc, front (danh nghĩa 0,80)     | 0,827 ± 0,004        |
| Độ phủ khoảng 80%, mc, weekend (danh nghĩa 0,80)   | 0,837 ± 0,004        |
| Độ phủ khoảng 80%, mc, spike (danh nghĩa 0,80)     | 0,570 ± 0,016        |
| Độ phủ khoảng 80%, cum, all (danh nghĩa 0,80)      | 0,799 ± 0,009        |
| Độ phủ khoảng 80%, cum, even (danh nghĩa 0,80)     | 0,861 ± 0,007        |
| Độ phủ khoảng 80%, cum, front (danh nghĩa 0,80)    | 0,864 ± 0,011        |
| Độ phủ khoảng 80%, cum, weekend (danh nghĩa 0,80)  | 0,865 ± 0,010        |
| Độ phủ khoảng 80%, cum, spike (danh nghĩa 0,80)    | 0,600 ± 0,026        |
| Độ phủ khoảng 80%, cumb, all (danh nghĩa 0,80)     | 0,796 ± 0,001        |
| Độ phủ khoảng 80%, cumb, even (danh nghĩa 0,80)    | 0,830 ± 0,013        |
| Độ phủ khoảng 80%, cumb, front (danh nghĩa 0,80)   | 0,834 ± 0,005        |
| Độ phủ khoảng 80%, cumb, weekend (danh nghĩa 0,80) | 0,822 ± 0,008        |
| Độ phủ khoảng 80%, cumb, spike (danh nghĩa 0,80)   | 0,697 ± 0,019        |

## Báo sớm ở cùng mức báo nhầm

Mỗi mô hình được đặt ngưỡng sao cho đúng tỉ lệ chu kỳ bình thường bị cảnh báo như bảng, rồi so tỉ lệ bắt được chu kỳ thiếu tiền và số ngày báo trước ngày cạn tiền. Cách này không phụ thuộc ngưỡng đã tune, nên thay cho chỉ số `mean_days_early` (không phân biệt được các mô hình).

|                                       | tỉ lệ bắt được chu kỳ thiếu tiền   | số ngày báo trước (bỏ sót tính 0)   | trung vị số ngày báo trước (chỉ chu kỳ bắt được)   |
|:--------------------------------------|:-----------------------------------|:------------------------------------|:---------------------------------------------------|
| ('10%', 'B1 (TB 14 ngày)')            | 0,508 ± 0,033                      | 9,2 ± 0,7                           | 19,3 ± 0,6                                         |
| ('10%', 'B2 (TB cùng thứ)')           | 0,610 ± 0,040                      | 11,3 ± 1,3                          | 19,5 ± 1,3                                         |
| ('10%', 'XGB (cảnh báo theo biên m)') | 0,833 ± 0,030                      | 13,9 ± 1,0                          | 17,8 ± 0,8                                         |
| ('10%', 'XGB + p > p*')               | 0,902 ± 0,013                      | 13,9 ± 0,9                          | 16,0 ± 1,7                                         |
| ('10%', 'B2 + p > p* (đối chứng)')    | 0,860 ± 0,023                      | 13,0 ± 1,3                          | 16,3 ± 2,1                                         |
| ('20%', 'B1 (TB 14 ngày)')            | 0,743 ± 0,024                      | 14,5 ± 0,7                          | 20,7 ± 0,6                                         |
| ('20%', 'B2 (TB cùng thứ)')           | 0,827 ± 0,026                      | 16,6 ± 1,0                          | 21,3 ± 0,6                                         |
| ('20%', 'XGB (cảnh báo theo biên m)') | 0,935 ± 0,010                      | 18,0 ± 0,3                          | 21,0 ± 0,0                                         |
| ('20%', 'XGB + p > p*')               | 0,946 ± 0,008                      | 17,8 ± 0,4                          | 20,3 ± 0,6                                         |
| ('20%', 'B2 + p > p* (đối chứng)')    | 0,919 ± 0,002                      | 17,0 ± 1,0                          | 20,7 ± 1,2                                         |
| ('30%', 'B1 (TB 14 ngày)')            | 0,895 ± 0,025                      | 18,2 ± 0,8                          | 22,0 ± 0,0                                         |
| ('30%', 'B2 (TB cùng thứ)')           | 0,928 ± 0,008                      | 19,6 ± 0,6                          | 23,0 ± 0,0                                         |
| ('30%', 'XGB (cảnh báo theo biên m)') | 0,965 ± 0,006                      | 20,0 ± 0,2                          | 23,0 ± 0,0                                         |
| ('30%', 'XGB + p > p*')               | 0,963 ± 0,005                      | 20,1 ± 0,3                          | 23,0 ± 0,0                                         |
| ('30%', 'B2 + p > p* (đối chứng)')    | 0,945 ± 0,003                      | 19,5 ± 0,6                          | 22,7 ± 0,6                                         |

## Ở cùng mức Precision (đúng tiêu chí của báo cáo giữa kỳ)

Báo cáo giữa kỳ coi giải pháp là có ích nếu "ở mức Precision tương đương, Recall cao hơn hoặc báo sớm hơn B1". Với mỗi mô hình, ngưỡng thấp nhất còn đạt Precision mục tiêu được chọn trên validation; Precision validation được ghi riêng để kiểm tra quy tắc chọn ngưỡng. Ngưỡng được giữ nguyên khi đánh giá một lần trên test, nên Precision test có thể khác mục tiêu. Precision mục tiêu bằng Precision validation của B1 tại biên m đã tune, hoặc 0,7.

|                                                   | precision đạt được   | precision validation   | recall        | tỉ lệ bắt được chu kỳ thiếu tiền   | báo nhầm theo chu kỳ   | số ngày báo trước (bỏ sót tính 0)   | trung vị số ngày báo trước (chỉ chu kỳ bắt được)   |
|:--------------------------------------------------|:---------------------|:-----------------------|:--------------|:-----------------------------------|:-----------------------|:------------------------------------|:---------------------------------------------------|
| ('bằng B1 (0,592)', 'B1 (TB 14 ngày)')            | 0,587 ± 0,042        | 0,592 ± 0,012          | 0,746 ± 0,025 | 0,990 ± 0,002                      | 0,571 ± 0,054          | 22,4 ± 0,3                          | 24,0 ± 0,0                                         |
| ('bằng B1 (0,592)', 'B2 (TB cùng thứ)')           | 0,587 ± 0,049        | 0,593 ± 0,012          | 0,784 ± 0,022 | 0,983 ± 0,013                      | 0,481 ± 0,057          | 22,2 ± 0,4                          | 24,3 ± 0,6                                         |
| ('bằng B1 (0,592)', 'XGB (cảnh báo theo biên m)') | 0,578 ± 0,042        | 0,592 ± 0,012          | 0,809 ± 0,015 | 0,993 ± 0,004                      | 0,511 ± 0,042          | 22,9 ± 0,2                          | 25,0 ± 0,0                                         |
| ('bằng B1 (0,592)', 'XGB + p > p*')               | 0,580 ± 0,038        | 0,593 ± 0,012          | 0,833 ± 0,019 | 0,994 ± 0,005                      | 0,618 ± 0,051          | 24,3 ± 0,3                          | 26,0 ± 0,0                                         |
| ('bằng B1 (0,592)', 'B2 + p > p* (đối chứng)')    | 0,590 ± 0,048        | 0,593 ± 0,012          | 0,784 ± 0,026 | 0,980 ± 0,010                      | 0,522 ± 0,062          | 22,6 ± 0,5                          | 25,0 ± 0,0                                         |
| ('0,7', 'B1 (TB 14 ngày)')                        | 0,702 ± 0,017        | 0,700 ± 0,000          | 0,399 ± 0,062 | 0,851 ± 0,040                      | 0,270 ± 0,015          | 17,2 ± 1,1                          | 21,7 ± 0,6                                         |
| ('0,7', 'B2 (TB cùng thứ)')                       | 0,701 ± 0,028        | 0,700 ± 0,000          | 0,630 ± 0,021 | 0,932 ± 0,015                      | 0,310 ± 0,027          | 19,8 ± 0,4                          | 23,0 ± 0,0                                         |
| ('0,7', 'XGB (cảnh báo theo biên m)')             | 0,685 ± 0,034        | 0,700 ± 0,000          | 0,717 ± 0,010 | 0,977 ± 0,009                      | 0,365 ± 0,011          | 21,1 ± 0,0                          | 23,7 ± 0,6                                         |
| ('0,7', 'XGB + p > p*')                           | 0,690 ± 0,037        | 0,700 ± 0,000          | 0,718 ± 0,013 | 0,979 ± 0,006                      | 0,386 ± 0,017          | 21,8 ± 0,1                          | 24,0 ± 0,0                                         |
| ('0,7', 'B2 + p > p* (đối chứng)')                | 0,700 ± 0,034        | 0,700 ± 0,000          | 0,655 ± 0,020 | 0,950 ± 0,009                      | 0,317 ± 0,024          | 20,0 ± 0,4                          | 23,0 ± 0,0                                         |

## Theo 4 kiểu chi tiêu - MAE số dư cuối chu kỳ (VND)

|         | B1 (TB 14 ngày)   | B2 (TB cùng thứ)   | XGB (cảnh báo theo biên m)   |
|:--------|:------------------|:-------------------|:-----------------------------|
| even    | 605182 ± 13826    | 554919 ± 20854     | 488875 ± 3814                |
| front   | 1083162 ± 42295   | 781844 ± 29668     | 439318 ± 23671               |
| weekend | 734009 ± 18589    | 645527 ± 29642     | 530894 ± 15761               |
| spike   | 1471812 ± 33404   | 1285743 ± 6015     | 1047236 ± 10039              |

## Kiểm định cặp theo seed

| so_sánh        | chỉ_số            |     chênh_TB |        std | số_seed_tốt_hơn   |
|:---------------|:------------------|-------------:|-----------:|:------------------|
| XGB − B2       | f1                |       0,0209 |     0,006  | 3/3               |
| XGB − B2       | auroc             |       0,0248 |     0,003  | 3/3               |
| XGB − B2       | auprc             |       0,0618 |     0,0084 | 3/3               |
| XGB − B2       | MAE_spend         |  -19776,8    |   285,583  | 3/3               |
| XGB − B2       | MAE_balance       | -189749      |  6184,48   | 3/3               |
| XGB − B2       | cycle_false_alarm |      -0,0243 |     0,0422 | 2/3               |
| XGB − B1       | f1                |       0,0436 |     0,0086 | 3/3               |
| XGB − B1       | auroc             |       0,0477 |     0,0049 | 3/3               |
| XGB − B1       | auprc             |       0,1212 |     0,0145 | 3/3               |
| XGB − B1       | MAE_spend         |  -22485,4    |   615,84   | 3/3               |
| XGB − B1       | MAE_balance       | -345766      | 15195,5    | 3/3               |
| XGB − B1       | cycle_false_alarm |      -0,1973 |     0,0376 | 3/3               |
| XGB+risk − B2  | f1                |       0,0225 |     0,0044 | 3/3               |
| XGB+risk − B2  | auroc             |       0,0411 |     0,0083 | 3/3               |
| XGB+risk − B2  | auprc             |       0,0863 |     0,0111 | 3/3               |
| XGB+risk − B2  | cycle_false_alarm |       0,0458 |     0,0545 | 1/3               |
| XGB+risk − XGB | f1                |       0,0016 |     0,0016 | 2/3               |
| XGB+risk − XGB | auroc             |       0,0162 |     0,0053 | 3/3               |
| XGB+risk − XGB | auprc             |       0,0245 |     0,0027 | 3/3               |
| XGB+risk − XGB | cycle_false_alarm |       0,0701 |     0,0261 | 0/3               |
| B2+risk − B2   | f1                |       0,0023 |     0,0032 | 2/3               |
| B2+risk − B2   | auroc             |       0,0166 |     0,0015 | 3/3               |
| B2+risk − B2   | auprc             |       0,0482 |     0,0055 | 3/3               |
| B2+risk − B2   | cycle_false_alarm |       0,019  |     0,0085 | 0/3               |

## Kết luận tính từ số liệu

- Q1: MAE chi tiêu ngày của XGB thấp hơn B2 15,4% (tốt hơn ở 3/3 seed); MAE số dư thấp hơn 23,3% (tốt hơn ở 3/3 seed).
- Q2: F1 của XGB (biên m) hơn B2 ở 3/3 seed, chênh trung bình +0,021; XGB + p > p* hơn B2 ở 3/3 seed, chênh +0,023.
- XGB + p > p* so với XGB cảnh báo theo biên m: chênh F1 +0,002 (tốt hơn ở 2/3 seed) - chênh rất nhỏ (< 0,01), không có ý nghĩa thực tế; tỉ lệ chu kỳ bình thường vẫn bị cảnh báo 0,442 so với 0,372 (XGB + p > p* tốt hơn ở 0/3 seed, tức là cao hơn biên m).
- Không phụ thuộc ngưỡng (AUROC): XGB (điểm số theo biên) hơn B2 +0,025 (3/3 seed); XGB + p hơn B2 +0,041 (3/3 seed) và hơn XGB theo biên +0,016 (3/3 seed) - lớp xác suất cải thiện khả năng xếp hạng rủi ro dù F1 ở ngưỡng đã chọn gần như không đổi.
- Báo sớm ở cùng mức báo nhầm 20%: XGB bắt được nhiều chu kỳ thiếu tiền hơn B2 +10,8 điểm phần trăm (3/3 seed) và số ngày báo trước (chu kỳ bỏ sót tính 0) hơn +1,4 ngày (3/3 seed); XGB + p hơn B2 +11,9 điểm và +1,2 ngày (3/3, 3/3 seed). Trong các chu kỳ đã bắt được, trung vị số ngày báo trước gần như bằng nhau giữa các mô hình (chênh tối đa 1,0 ngày): lợi thế là bắt được nhiều chu kỳ hơn ở cùng mức báo nhầm, không phải bắt sớm hơn trong chu kỳ đã bắt được.
- Tiêu chí báo cáo giữa kỳ (ở Precision bằng B1, trung bình 0,592): XGB + p > p* so với B1 (TB 14 ngày): Recall +8,7 điểm phần trăm (3/3 seed), số ngày báo trước (bỏ sót tính 0) +1,9 ngày (3/3 seed), trung vị số ngày báo trước trong chu kỳ bắt được +2,0 ngày.
- Tiêu chí báo cáo giữa kỳ (ở Precision bằng B1, trung bình 0,592): XGB + p > p* so với B2 (TB cùng thứ): Recall +4,8 điểm phần trăm (3/3 seed), số ngày báo trước (bỏ sót tính 0) +2,1 ngày (3/3 seed), trung vị số ngày báo trước trong chu kỳ bắt được +1,7 ngày.
- Đối chứng B2 + p > p*: F1 chênh +0,002 và AUROC chênh +0,017 so với B2. Lớp xác suất giúp xếp hạng rủi ro tốt hơn, nhưng F1 ở ngưỡng chọn trên val gần như không đổi; phần chênh F1 giữa XGB và B2 đến từ mô hình dự báo.
- Điều kiện k=2 (cảnh báo khi p > p* hai ngày liên tiếp) chỉ là thử nghiệm: tỉ lệ báo nhầm 0,410 so với 0,442 khi k=1, F1 0,686 so với 0,702 - không dùng trong giải pháp cuối.
- Hiệu chỉnh xác suất (test, gộp seed): XGB + risk ECE = 0,007, Brier = 0,112; B2 + risk ECE = 0,062. (ECE gộp các seed nhỏ hơn trung bình ECE từng seed trong bảng Q2 vì ít nhiễu hơn.)
- Phần dư độc lập theo ngày: tương quan giữa các ngày chỉ +0,010 đến +0,019 (gần 0), nhưng tỉ số phương sai Var(tổng)/Tổng Var nằm trong 1,01-1,24 (độc lập = 1) nên có phụ thuộc dương nhẹ; khoảng 80% của cách giả định độc lập (mc) chỉ phủ 0,752, còn cum/cumb phủ 0,799/0,796.
- Kiểu spike vẫn bị phủ thiếu: độ phủ 80% là 0,600 (cum) và 0,697 (cumb, thêm nhóm theo tần suất chi cực lớn), so với danh nghĩa 0,80.
- Phương pháp ước lượng p được chọn theo Brier trên val: seed 1: cumb, seed 2: cumb, seed 3: cumb.
- Chỉ số p_t (XGB + p > p*, test): AUROC 0,888, Brier skill 0,447, độ dốc hiệu chỉnh 0,97 (1 = lý tưởng), ECE 0,013; đối chứng B2 + p > p*: AUROC 0,864, ECE 0,062.
- F1 theo kiểu chi tiêu, XGB so với B2:
  - even: F1 XGB − B2 = +0,011 (chưa rõ so với nhiễu giữa các seed).
  - front: F1 XGB − B2 = +0,065 (rõ: cả 3 seed cùng dấu và > 0,02).
  - weekend: F1 XGB − B2 = +0,007 (chưa rõ so với nhiễu giữa các seed).
  - spike: F1 XGB − B2 = -0,005 (chưa rõ so với nhiễu giữa các seed).

Lưu ý: dữ liệu mô phỏng nên kết quả chỉ cho thấy tính khả thi của cách đặt bài toán, chưa khẳng định hiệu quả với người dùng thật. `mean_days_early` chỉ dùng để so giữa các mô hình vì cảnh báo thường bật ngay từ đầu chu kỳ.

## Quy trình và môi trường của lần chạy này

So sánh ở cùng Precision chọn ngưỡng trên validation rồi giữ nguyên ngưỡng để đánh giá test một lần; Precision validation và test được báo riêng. Kết quả đánh giá phụ giữ riêng người dùng nằm ở `results/user_holdout/USER_HOLDOUT.md`.

Runtime: Python 3.12.14, NumPy 2.4.5, pandas 3.0.6, scikit-learn 1.9.1, XGBoost 3.4.1, Matplotlib 3.10.9.

Runtime này khác phiên bản ghim trong `requirements.txt`; xem `THAY_DOI.md`. Các số trong báo cáo này là lần chạy mới, còn `ket_qua_tham_chieu/` được giữ nguyên làm bản đối chiếu trước khi sửa quy trình chọn ngưỡng.
