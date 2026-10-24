# Phân tích lỗi của cảnh báo (XGB + p > p*, test, 3 seed)

Mức chu kỳ: **báo nhầm** = chu kỳ không thiếu tiền nhưng có ít nhất 1 cảnh báo; **bỏ sót** = chu kỳ thiếu tiền nhưng không có cảnh báo nào ở các điểm quyết định còn lại (điểm có số dư đã dưới θ bị loại theo SPEC mục 2). 'Suýt thiếu' = số dư cuối kỳ cao hơn θ chưa tới 1θ (chưa tới 1 ngày chi tiêu trung bình). Trung bình ± độ lệch chuẩn qua các seed.

## Tổng quan (so với B2)

|                                                              | XGB + p > p*   | B2 (TB cùng thứ)   |
|:-------------------------------------------------------------|:---------------|:-------------------|
| tỉ lệ chu kỳ bình thường bị báo nhầm                         | 0,420 ± 0,031  | 0,397 ± 0,058      |
| tỉ lệ chu kỳ thiếu tiền bị bỏ sót                            | 0,019 ± 0,011  | 0,033 ± 0,018      |
| trong số báo nhầm: tỉ lệ 'suýt thiếu' (cuối kỳ dư < 1θ)      | 0,170 ± 0,013  | 0,170 ± 0,015      |
| trong số chu kỳ bình thường không bị báo: tỉ lệ 'suýt thiếu' | 0,016 ± 0,005  | 0,021 ± 0,004      |
| trong số báo nhầm: trung vị ngày cảnh báo đầu tiên           | 1,0 ± 0,0      | 1,7 ± 0,6          |
| trong số báo nhầm: trung vị tỉ lệ ngày bị cảnh báo           | 0,285 ± 0,043  | 0,354 ± 0,062      |
| bỏ sót: trung vị (số dư cuối kỳ − θ)/θ                       | -1,69 ± 1,26   | -1,60 ± 0,83       |
| bắt được: trung vị (số dư cuối kỳ − θ)/θ                     | -3,43 ± 0,36   | -3,45 ± 0,33       |
| trung vị số điểm quyết định của chu kỳ bị bỏ sót             | 27,3 ± 0,6     | 27,2 ± 0,3         |
| trung vị số điểm quyết định của chu kỳ bắt được              | 26,3 ± 0,6     | 26,3 ± 0,6         |

## Theo kiểu chi tiêu và loại thu nhập (XGB + p > p*)

|                             | tỉ lệ thiếu tiền   | báo nhầm      | bỏ sót        |
|:----------------------------|:-------------------|:--------------|:--------------|
| income_type = allowance_1st | 0,296 ± 0,022      | 0,412 ± 0,008 | 0,022 ± 0,008 |
| income_type = salary_25     | 0,295 ± 0,017      | 0,429 ± 0,057 | 0,015 ± 0,015 |
| pattern = even              | 0,272 ± 0,013      | 0,290 ± 0,065 | 0,033 ± 0,006 |
| pattern = front             | 0,287 ± 0,043      | 0,385 ± 0,018 | 0,000 ± 0,000 |
| pattern = spike             | 0,344 ± 0,028      | 0,542 ± 0,102 | 0,034 ± 0,036 |
| pattern = weekend           | 0,278 ± 0,043      | 0,475 ± 0,047 | 0,004 ± 0,007 |

## Hai ví dụ điển hình (seed 1, p* = 0,30; hình `fig11_error_cases.png`, số liệu `error_cases.csv`)

- **Báo nhầm** - user 91, chu kỳ 22, kiểu spike: cảnh báo đầu tiên ngày 1, p lớn nhất 0,52; số dư cuối kỳ thật 0,91 triệu so với θ = 0,34 triệu (cao hơn θ 1,70 lần θ).
- **Bỏ sót** - user 88, chu kỳ 22, kiểu even: p lớn nhất chỉ 0,20 (< p*); số điểm quyết định 27, ngày cạn thực tế 30; số dư cuối kỳ 0,12 triệu so với θ = 0,13 triệu.

## Nhận xét tính từ số liệu

- Báo nhầm: 0,420 ± 0,031 chu kỳ bình thường bị cảnh báo ít nhất một lần; trong các chu kỳ đó 0,170 ± 0,013 là 'suýt thiếu', so với 0,016 ± 0,005 ở các chu kỳ bình thường không bị cảnh báo. Trung vị ngày cảnh báo đầu tiên là ngày 1,0 ± 0,0; trung vị tỉ lệ ngày bị cảnh báo trong chu kỳ báo nhầm là 0,285 ± 0,043.
- Bỏ sót: 0,019 ± 0,011 chu kỳ thiếu tiền; p lớn nhất trung vị của các chu kỳ này là 0,27 ± 0,03; trung vị (số dư cuối kỳ − θ)/θ là -1,69 ± 1,26, so với -3,43 ± 0,36 ở chu kỳ bắt được; trung vị số điểm quyết định 27,3 ± 0,6 so với 26,3 ± 0,6.
- Kiểu chi tiêu báo nhầm nhiều nhất: spike; bỏ sót nhiều nhất: spike.

Ví dụ chọn theo quy tắc cố định để tránh chọn ca có lợi; không phải ca tệ nhất. Dữ liệu mô phỏng.
