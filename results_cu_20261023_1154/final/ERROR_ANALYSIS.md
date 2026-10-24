# Phân tích lỗi của cảnh báo (XGB + p > p*, test, 3 seed)

Mức chu kỳ: **báo nhầm** = chu kỳ không thiếu tiền nhưng có ít nhất 1 cảnh báo; **bỏ sót** = chu kỳ thiếu tiền nhưng không có cảnh báo nào ở các điểm quyết định còn lại (điểm có số dư đã dưới θ bị loại theo SPEC mục 2). 'Suýt thiếu' = số dư cuối kỳ cao hơn θ chưa tới 1θ (chưa tới 1 ngày chi tiêu trung bình). Trung bình ± độ lệch chuẩn qua các seed.

## Tổng quan (so với B2)

|                                                              | XGB + p > p*   | B2 (TB cùng thứ)   |
|:-------------------------------------------------------------|:---------------|:-------------------|
| tỉ lệ chu kỳ bình thường bị báo nhầm                         | 0,442 ± 0,032  | 0,397 ± 0,058      |
| tỉ lệ chu kỳ thiếu tiền bị bỏ sót                            | 0,017 ± 0,008  | 0,033 ± 0,018      |
| trong số báo nhầm: tỉ lệ 'suýt thiếu' (cuối kỳ dư < 1θ)      | 0,167 ± 0,017  | 0,170 ± 0,015      |
| trong số chu kỳ bình thường không bị báo: tỉ lệ 'suýt thiếu' | 0,012 ± 0,003  | 0,021 ± 0,004      |
| trong số báo nhầm: trung vị ngày cảnh báo đầu tiên           | 1,0 ± 0,0      | 1,7 ± 0,6          |
| trong số báo nhầm: trung vị tỉ lệ ngày bị cảnh báo           | 0,289 ± 0,059  | 0,354 ± 0,062      |
| bỏ sót: trung vị (số dư cuối kỳ − θ)/θ                       | -1,36 ± 1,23   | -1,60 ± 0,83       |
| bắt được: trung vị (số dư cuối kỳ − θ)/θ                     | -3,44 ± 0,35   | -3,45 ± 0,33       |
| trung vị số điểm quyết định của chu kỳ bị bỏ sót             | 27,2 ± 0,3     | 27,2 ± 0,3         |
| trung vị số điểm quyết định của chu kỳ bắt được              | 26,3 ± 0,6     | 26,3 ± 0,6         |

## Theo kiểu chi tiêu và loại thu nhập (XGB + p > p*)

|                             | tỉ lệ thiếu tiền   | báo nhầm      | bỏ sót        |
|:----------------------------|:-------------------|:--------------|:--------------|
| income_type = allowance_1st | 0,296 ± 0,022      | 0,431 ± 0,029 | 0,022 ± 0,005 |
| income_type = salary_25     | 0,295 ± 0,017      | 0,455 ± 0,050 | 0,012 ± 0,012 |
| pattern = even              | 0,272 ± 0,013      | 0,304 ± 0,054 | 0,033 ± 0,006 |
| pattern = front             | 0,287 ± 0,043      | 0,408 ± 0,031 | 0,000 ± 0,000 |
| pattern = spike             | 0,344 ± 0,028      | 0,573 ± 0,117 | 0,024 ± 0,027 |
| pattern = weekend           | 0,278 ± 0,043      | 0,500 ± 0,033 | 0,007 ± 0,006 |

## Hai ví dụ điển hình (seed 1, p* = 0,30; hình `fig11_error_cases.png`, số liệu `error_cases.csv`)

- **Báo nhầm** - user 113, chu kỳ 21, kiểu front: cảnh báo đầu tiên ngày 1, p lớn nhất 0,52; số dư cuối kỳ thật 0,83 triệu so với θ = 0,15 triệu (cao hơn θ 4,39 lần θ).
- **Bỏ sót** - user 88, chu kỳ 22, kiểu even: p lớn nhất chỉ 0,19 (< p*); số điểm quyết định 27, ngày cạn thực tế 30; số dư cuối kỳ 0,12 triệu so với θ = 0,13 triệu.

## Nhận xét tính từ số liệu

- Báo nhầm: 0,442 ± 0,032 chu kỳ bình thường bị cảnh báo ít nhất một lần; trong các chu kỳ đó 0,167 ± 0,017 là 'suýt thiếu', so với 0,012 ± 0,003 ở các chu kỳ bình thường không bị cảnh báo. Trung vị ngày cảnh báo đầu tiên là ngày 1,0 ± 0,0; trung vị tỉ lệ ngày bị cảnh báo trong chu kỳ báo nhầm là 0,289 ± 0,059.
- Bỏ sót: 0,017 ± 0,008 chu kỳ thiếu tiền; p lớn nhất trung vị của các chu kỳ này là 0,26 ± 0,03; trung vị (số dư cuối kỳ − θ)/θ là -1,36 ± 1,23, so với -3,44 ± 0,35 ở chu kỳ bắt được; trung vị số điểm quyết định 27,2 ± 0,3 so với 26,3 ± 0,6.
- Kiểu chi tiêu báo nhầm nhiều nhất: spike; bỏ sót nhiều nhất: even.

Ví dụ chọn theo quy tắc cố định để tránh chọn ca có lợi; không phải ca tệ nhất. Dữ liệu mô phỏng.
