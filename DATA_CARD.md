# Hồ sơ dữ liệu của dự án

## Dữ liệu dùng để phát triển và đánh giá

`data/daily.csv` và `data/daily_users.csv` do `cashflow_risks/simulate.py` sinh ra. Bộ dữ liệu minh họa chuẩn có 300 người mô phỏng, 24 chu kỳ/người và 219.000 dòng ngày. Seed dữ liệu chuẩn là 42; file này dùng cho hình kiểm tra dữ liệu. Các kết quả mô hình chính chạy với seed 1, 2 và 3, và **mỗi seed tự sinh lại một bộ dữ liệu 300 người** (`run_baselines.load`), không đọc `data/daily.csv`. Vì vậy độ lệch chuẩn qua seed gộp cả dao động dữ liệu lẫn dao động mô hình.

Không có dữ liệu giao dịch thật của khách hàng trong bộ kết quả này. Vì vậy các chỉ số phản ánh hiệu quả trên quy luật đã cài trong simulator; chúng chưa phải bằng chứng hiệu quả ngoài đời.

## Nội dung

| Biến | Ý nghĩa |
|---|---|
| `user_id`, `date`, `cycle_id`, `day_in_cycle`, `D` | Người mô phỏng, ngày, chu kỳ, ngày trong chu kỳ và số ngày còn lại |
| `spend`, `income`, `balance` | Chi tiêu, thu nhập và số dư cuối ngày, đơn vị VND |
| `pattern`, `income_type` | Nhãn kiểu chi tiêu và lịch nhận thu nhập do simulator đặt |
| `split` | Tập theo thời gian: train, calib, val hoặc test |

`pattern` và tham số người dùng trong `daily_users.csv` chỉ dùng để phân tích kết quả; không được đưa vào đặc trưng mô hình. Quy tắc chia theo chu kỳ là train 0–11, calib 12–15, val 16–19, test 20–23.

## Giả định và giới hạn

- Simulator có bốn kiểu chi tiêu (đều, dồn đầu chu kỳ, tăng cuối tuần, có khoản chi lớn) và hai lịch nhận thu nhập (ngày 1 hoặc ngày 25).
- Thu nhập đến đúng lịch; simulator không mô hình hóa việc người dùng thay đổi hành vi khi số dư thấp. Số dư dương được mang sang chu kỳ sau có giới hạn.
- Các tập temporal chứa các chu kỳ khác nhau của cùng 300 người. Đánh giá phụ user-holdout giữ riêng 150/45/45/60 người cho train/calib/val/test, vẫn lấy giai đoạn thời gian tương ứng. Nhãn người dùng test không dùng huấn luyện/chọn ngưỡng; lịch sử đã quan sát của chính người đó được dùng làm đặc trưng. Đây chưa phải cold start hoặc đánh giá ngoài simulator.
- Simulator không chủ đích tạo khác biệt hành vi theo nhóm thu nhập. Phân tích nhóm thu nhập vì thế không chứng minh công bằng trên dân số thật.
- Dữ liệu mô phỏng được tạo có cấu trúc và không đại diện đầy đủ cho lỗi ghi nhận thực tế, giao dịch bị thiếu, thay đổi lịch nhận tiền hay hoàn tiền.
- Khi nhập CSV thật (SPEC mục 15): điểm quyết định chưa đủ 28 ngày lịch sử bị bỏ kèm cảnh báo (ví dụ thu nhập 2 tuần/lần sẽ mất các điểm đầu). Khoản tiền vào giữa chu kỳ hoặc chi âm làm số dư tăng giữa chu kỳ, trái giả định "số dư chỉ giảm": chương trình **chỉ phát hiện và cảnh báo**, nhãn và xác suất của những chu kỳ đó vẫn có thể sai.

## Kiểm tra CSV người dùng

`cashflow_risks/import_real.py` mặc định từ chối ô thiếu/không phải số/không hữu hạn, ngày bị thiếu và số dư thiếu. Không coi dữ liệu chưa biết là không chi tiêu.

Chỉ khi chọn rõ `missing_policy='zero'`, ô spend/income lỗi và ngày thiếu mới được điền 0; chỉ khi chọn `balance_policy='ffill'`, số dư thiếu mới được điền theo giá trị trước đó. Thiếu số dư đầu chuỗi vẫn bị từ chối. Đây là các giả định nhập liệu, không phải khôi phục giao dịch thực tế. Chi âm/ngoại lai được giữ nguyên và cảnh báo. Metadata `df.attrs['quality']` ghi chính sách, số lỗi và danh sách ngày/trường bị tác động; demo lưu metadata này và hiển thị lưu ý khi có điền dữ liệu. CSV nguồn không bị ghi đè.

Việc demo với CSV chỉ minh họa luồng xử lý; mô hình vẫn được huấn luyện trên dữ liệu mô phỏng.

## Bước cần có trước khi khẳng định hiệu quả thực tế

Đã có user-holdout trong mô phỏng. Bước tiếp theo là đánh giá trên dữ liệu thật được cung cấp có đồng ý và xử lý phù hợp hoặc kịch bản dịch chuyển ngoài giả định simulator. Báo cáo rõ nguồn, cách thu thập, chất lượng dữ liệu, sai lệch đại diện và kết quả theo từng nhóm. Không dùng kết quả mô phỏng để suy ra lợi ích tài chính thực tế.


## Cập nhật kết quả ngày 23/10/2026

Số liệu và diễn giải hiện hành ghi ở **một nơi duy nhất**: `results/final/PUBLICATION.md` (nguồn từng bảng) và mục "Cập nhật kết quả ngày 23/10/2026" đầu `THAY_DOI.md`. Không chép lại số ở đây để tránh lệch khi cập nhật.
