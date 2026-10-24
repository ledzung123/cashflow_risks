# Phân tích bổ sung (test, trung bình ± độ lệch chuẩn qua 3 seed)

## 1. Mất cân bằng lớp

Tỉ lệ thiếu tiền ở từng tập (điểm quyết định và chu kỳ):

| tập   | số điểm    | tỉ lệ điểm thiếu tiền   | số chu kỳ   | tỉ lệ chu kỳ thiếu tiền   |
|:------|:-----------|:------------------------|:------------|:--------------------------|
| train | 88469 ± 62 | 0,273 ± 0,008           | 3300 ± 0    | 0,286 ± 0,008             |
| calib | 31782 ± 99 | 0,259 ± 0,020           | 1200 ± 0    | 0,271 ± 0,020             |
| val   | 32516 ± 60 | 0,295 ± 0,012           | 1200 ± 0    | 0,311 ± 0,013             |
| test  | 32260 ± 45 | 0,280 ± 0,005           | 1200 ± 0    | 0,295 ± 0,006             |

Mô hình chính (XGBoost) dự báo **chi tiêu** (hồi quy), không phân loại trực tiếp, nên không dùng trọng số lớp hay lấy mẫu lại. Mất cân bằng chỉ tác động ở bước đặt ngưỡng cảnh báo trên xác suất p. Nhóm xử lý bằng cách chọn ngưỡng p* trên tập val để tối đa F1, và báo cáo thêm AUPRC (nhạy với lớp hiếm hơn AUROC). Bảng dưới so sánh cùng một p với các ngưỡng khác:

| ngưỡng                       | giá trị ngưỡng   | precision     | recall        | f1            | cycle_recall   | cycle_false_alarm   |
|:-----------------------------|:-----------------|:--------------|:--------------|:--------------|:---------------|:--------------------|
| p* chọn trên val (đang dùng) | 0,313 ± 0,012    | 0,658 ± 0,034 | 0,752 ± 0,010 | 0,702 ± 0,015 | 0,983 ± 0,008  | 0,442 ± 0,032       |
| 0,5 (mặc định)               | 0,500 ± 0,000    | 0,801 ± 0,030 | 0,589 ± 0,013 | 0,679 ± 0,013 | 0,951 ± 0,013  | 0,223 ± 0,029       |
| tỉ lệ nền tập calib          | 0,259 ± 0,020    | 0,612 ± 0,009 | 0,800 ± 0,012 | 0,694 ± 0,010 | 0,994 ± 0,005  | 0,535 ± 0,034       |

- Ngưỡng 0,5 mặc định: recall 0,589 so với 0,752 khi dùng p*, F1 0,679 so với 0,702.
- Đổi lại, ngưỡng 0,5 giảm tỉ lệ chu kỳ bình thường bị báo nhầm từ 0,442 xuống 0,223, trong khi tỉ lệ bắt được chu kỳ thiếu tiền chỉ giảm từ 0,983 xuống 0,951. p* tối đa F1 ở mức điểm quyết định nên ưu tiên bắt được nhiều ngày có nguy cơ; nếu muốn giảm mệt mỏi vì cảnh báo thì ngưỡng cao hơn hợp lý hơn (chọn theo chi phí bỏ sót / báo nhầm, xem `Extra_cost.csv`).

## 2. Công bằng theo mức thu nhập (XGB + p > p*)

Chia 3 mức thu nhập bằng nhau trong từng loại thu nhập (6 nhóm, mỗi nhóm khoảng 50 người).

| nhóm                 | số người   | tỉ lệ chu kỳ thiếu tiền   | bỏ sót (chu kỳ)   | báo nhầm (chu kỳ)   | precision     | recall        | AUROC         | ECE           | Brier         |
|:---------------------|:-----------|:--------------------------|:------------------|:--------------------|:--------------|:--------------|:--------------|:--------------|:--------------|
| allowance_1st / thấp | 53 ± 1     | 0,258 ± 0,036             | 0,019 ± 0,018     | 0,409 ± 0,066       | 0,628 ± 0,021 | 0,786 ± 0,006 | 0,906 ± 0,004 | 0,022 ± 0,011 | 0,100 ± 0,006 |
| allowance_1st / vừa  | 49 ± 3     | 0,292 ± 0,022             | 0,021 ± 0,023     | 0,430 ± 0,030       | 0,674 ± 0,037 | 0,756 ± 0,041 | 0,889 ± 0,020 | 0,024 ± 0,003 | 0,108 ± 0,011 |
| allowance_1st / cao  | 50 ± 2     | 0,340 ± 0,033             | 0,026 ± 0,024     | 0,463 ± 0,037       | 0,707 ± 0,048 | 0,762 ± 0,022 | 0,901 ± 0,016 | 0,033 ± 0,014 | 0,115 ± 0,001 |
| salary_25 / thấp     | 51 ± 1     | 0,325 ± 0,021             | 0,015 ± 0,016     | 0,456 ± 0,064       | 0,681 ± 0,062 | 0,736 ± 0,042 | 0,881 ± 0,014 | 0,036 ± 0,017 | 0,119 ± 0,010 |
| salary_25 / vừa      | 49 ± 2     | 0,255 ± 0,022             | 0,014 ± 0,024     | 0,447 ± 0,090       | 0,610 ± 0,100 | 0,717 ± 0,056 | 0,874 ± 0,051 | 0,033 ± 0,018 | 0,110 ± 0,029 |
| salary_25 / cao      | 48 ± 1     | 0,304 ± 0,048             | 0,007 ± 0,012     | 0,459 ± 0,059       | 0,640 ± 0,049 | 0,748 ± 0,058 | 0,875 ± 0,024 | 0,019 ± 0,007 | 0,119 ± 0,004 |

- Báo nhầm theo chu kỳ dao động từ 0,409 (allowance_1st / thấp) đến 0,463 (allowance_1st / cao); bỏ sót từ 0,007 (salary_25 / cao) đến 0,026 (allowance_1st / cao); AUROC từ 0,874 (salary_25 / vừa) đến 0,906 (allowance_1st / thấp).
- Lưu ý: simulator không cài khác biệt hành vi theo mức thu nhập (chi tiêu tỉ lệ với thu nhập qua ρ), nên phép thử này chỉ kiểm tra mô hình có tự tạo ra chênh lệch hay không; chưa phải bằng chứng về công bằng trên người dùng thật. Phân tích theo kiểu chi tiêu và loại thu nhập có ở `Extra_fairness.csv`.
