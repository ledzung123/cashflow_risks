# Cảnh báo sớm thiếu tiền trước kỳ nhận thu nhập - mã nguồn nhóm 11

## Quy ước dữ liệu (áp dụng cho mọi bước chính)
- Dữ liệu mô phỏng: **300 người × 24 chu kỳ = 219.000 dòng**. Chia theo chu kỳ: train 0-11, calib 12-15, val 16-19, test 20-23.
- Seed kết quả: 1, 2, 3. Seed dữ liệu minh họa/kiểm tra: 42.
- `demo.html` chỉ **hiển thị** 20 trong 300 người (ở tập test) cho dễ xem; hệ thống phía sau huấn luyện trên cả 300 người.
- Các file `test_*.py` dùng ít người (8, 40, 60) chỉ để kiểm tra nhanh.

## Cấu trúc thư mục sau khi giải nén
```
run_all.ps1          chạy phần lõi (bước 1-6) và đánh giá phụ user-holdout
run_extras.ps1       chạy phần độ nhạy + MVP
run_upgrade.ps1      đánh giá chính sách ngưỡng chọn trên validation, bootstrap từng seed, ablation (SPEC mục 20)
requirements.txt     phiên bản thư viện đã dùng để tạo bộ số chính thức (hai script trên tự cài từ file này)
demo.html            demo dựng sẵn (bấm đúp để mở)
SPEC.md              quy ước chi tiết
DATA_CARD.md         nguồn, nội dung, giả định và giới hạn của dữ liệu
ket_qua_tham_chieu\  bản sao bộ kết quả chốt hiện tại trong results\final\
ket_qua_tham_chieu_pre_val_precision_20261023\  bản tham chiếu cũ trước khi chọn ngưỡng Precision trên validation
results_pre_val_precision\   kết quả cũ chọn ngưỡng Precision trên test (chỉ để đối chiếu lịch sử)
cashflow_risks\      toàn bộ mã (35 file .py, demo_template.html, test_demo.js) và data\ (2 file CSV mẫu)
```

## Cách chạy (PowerShell, đứng ở thư mục chứa run_all.ps1)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_all.ps1          # phần lõi + đánh giá user-holdout, khoảng 20-40 phút tùy máy; dòng cuối phải là "TẤT CẢ ĐẠT"
.\run_extras.ps1       # độ nhạy + MVP, khoảng 15-20 phút; dòng cuối phải là "TAT CA DAT"
```
- Cả hai script cài thư viện từ `requirements.txt` trước khi chạy; thêm `-SkipInstall` để bỏ qua bước này.
- `run_extras.ps1 -SkipSensitivity` chỉ dựng lại demo (khoảng 1 phút).
- `run_extras.ps1 -BrowserTest` kiểm tra thêm `demo.html` bằng trình duyệt giả lập (cần Node.js và `npm install jsdom` ở thư mục này).

## Kết quả
- Kết quả nằm trong `results\`, bảng và hình cho báo cáo nằm trong `results\final\` (bắt đầu đọc từ `RESULTS.md`).
- Đánh giá phụ trên người dùng giữ riêng nằm trong `results\user_holdout\USER_HOLDOUT.md`; xem thêm giới hạn trong `DATA_CARD.md`.
- Mỗi lần chạy lại, `run_all.ps1` đổi tên `results\` cũ thành `results_cu_<ngày>_<giờ>` để không trộn số cũ và mới.
- `results\final\PUBLICATION.md` ghi nguồn của từng bảng: bảng lõi (Q1/Q2, mô hình thay thế, SHAP, hiệu chỉnh, độ nhạy) lấy từ lần chạy `run_all.ps1`; bảng chi phí, CI, chính sách và ablation lấy từ `run_upgrade.ps1`. Nhật ký chạy và runtime ghi trong `THAY_DOI.md`.
- `ket_qua_tham_chieu\` là bản sao SHA256 khớp với `results\final\`. Bộ tham chiếu cũ trước thay đổi ngưỡng được giữ trong `ket_qua_tham_chieu_pre_val_precision_20261023\`; kết quả chọn ngưỡng trên test cũ nằm trong `results_pre_val_precision\`.
- `results_cu_20261023_1154\` là bộ trung gian từ lần chạy Python 3.13 bị ngắt ở phân tích bổ sung; không dùng các số trong đó làm kết quả chốt.

## File CSV của một người (cho `make_demo.py --csv`)
Cột `date` (YYYY-MM-DD), `spend` (tổng chi trong ngày, VND), `income` (số tiền vào, 0 nếu không có); cột `balance` (số dư cuối ngày) tùy chọn.
Cần ít nhất 3 lần nhận thu nhập; nên có từ 3 tháng trở lên. Ví dụ: `cashflow_risks\data\example_user.csv`.
Mặc định chương trình từ chối ô trống/lỗi, ngày thiếu hoặc số dư thiếu; chi âm và chi bất thường được giữ nguyên kèm cảnh báo. Khoản tiền vào giữa chu kỳ và chi âm được cảnh báo riêng vì mô hình giả định số dư chỉ giảm giữa kỳ. Các ngày quyết định chưa đủ 28 ngày lịch sử bị bỏ. Chỉ điền chi tiêu/thu nhập bằng 0 khi chọn `--missing-policy zero`; chỉ điền số dư theo ngày trước khi chọn `--balance-policy ffill`. Không điền được số dư đầu chuỗi nếu chưa có giá trị trước đó. Các biến đổi được lưu trong metadata chất lượng dữ liệu; không ghi đè CSV nguồn.
Mô hình luôn huấn luyện trên dữ liệu mô phỏng, nên demo trên dữ liệu thật chỉ để minh họa.

Phạm vi và giới hạn của dữ liệu mô phỏng được ghi trong `DATA_CARD.md`. Có cả chia tập theo thời gian trên cùng người và đánh giá phụ giữ riêng người dùng; đánh giá phụ vẫn dùng lịch sử người đó để tạo đặc trưng, không phải cold start.

## Đánh giá nâng cấp: ngưỡng vận hành và độ tin cậy

```powershell
python cashflow_risks/run_upgrade.py --stage all
python cashflow_risks/run_upgrade.py --stage analysis  # chỉ tính từ dự báo đã lưu
.\run_upgrade.ps1 -Stage analysis  # tính bảng và dựng thêm hai hình so sánh
```

- `results/upgrades/summary/UPGRADE_RESULTS.md`: kết quả mới, kèm bảng CSV từng seed và trung bình/SD.
- Chi phí FP/FN và ngưỡng FAR20 được chọn trên validation, cố định trước khi tính test; báo riêng FAR thực tế trên test.
- So các chính sách F1, chi phí, FAR20 và Bayes trên cả temporal và user-holdout; báo số ngày cảnh báo lặp ở chu kỳ bình thường. Không chọn chính sách tốt nhất theo test.
- Bootstrap ghép cặp theo người, CI95% từng seed; không dùng trung bình cận khoảng tin cậy làm CI chung.
- Hai ablation trên ba seed bỏ lịch sử chu kỳ cá nhân hoặc nhóm lịch/thống kê gần đây. So XGB với XGB+risk là đối chứng riêng cho lớp xác suất.
- Lưu mô hình, dự báo, điểm validation/test và SHA256 mã nguồn/kết quả để tiếp tục từ checkpoint hợp lệ. Manifest ghi phiên bản runtime thực sự sử dụng.
- `results/final/` và `ket_qua_tham_chieu/` đã cập nhật bảng chi phí, CI, chính sách và ablation; xem PUBLICATION.md để phân biệt nguồn thí nghiệm. Chi phí tối thiểu trong bộ cũ được chọn trên test; FAR20 cũ là điểm trên đường đánh đổi mô tả. Không trộn với bảng chính sách mới. Báo cáo cuối kỳ (DOCX, nộp riêng, không đưa lên repo) dùng bộ công bố này.
- `extra_analysis.py` và `summarize_extra.py` cũng đã chuyển sang chi phí chọn ngưỡng trên validation; không tổng hợp lẫn CSV chi phí cũ và mới. `run_upgrade.py` là đường chạy bổ sung, không cần chạy lại toàn bộ `run_all.ps1`.

## Các file kiểm tra tự động
| File                                               | Việc                                                                                                                    |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `extra_analysis.py`, `summarize_extra.py`          | So mô hình, chi phí sai, khoảng tin cậy, phân tích theo nhóm, độ trễ (chạy trong `run_all.ps1`, thêm khoảng 12-20 phút) |
| `check_conventions.py`                             | Mã nguồn có đúng quy ước (300 người, 24 chu kỳ, 4 tập, seed, hằng số)                                                   |
| `test_pipeline.py`, `test_xgb.py`, `test_risk.py`  | Nhãn, không rò rỉ tương lai, xác suất, chỉ số                                                                           |
| `check_expected.py`                                | Kết quả phần lõi có nằm trong khoảng đúng (gồm cả chỉ số báo sớm ở cùng mức báo nhầm)                                   |
| `check_extras.py`                                  | Kết quả độ nhạy và demo.html có hợp lệ                                                                                  |
| `run_user_holdout.py`, `summarize_user_holdout.py` | Đánh giá phụ với user_id tách rời giữa train/calib/val/test -> `results/user_holdout/USER_HOLDOUT.md`                   |

## Phân tích bổ sung (chạy trong `run_all.ps1`, chi tiết ở SPEC mục 6e và 18)
| File                                               | Việc                                                                                                                                                                                        |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `error_cases.py`                                   | Báo nhầm / bỏ sót mức chu kỳ, theo kiểu chi tiêu và loại thu nhập, 2 ví dụ điển hình -> `ERROR_ANALYSIS.md`, `fig11_error_cases.png`                                                        |
| `explain.py`                                       | Lý do cảnh báo bằng SHAP (TreeSHAP có sẵn trong XGBoost) cho mọi cảnh báo trên test -> `explain_alerts_seed1.csv`, `fig12_explain.png`; `--plot-saved` chỉ dựng lại hình từ CSV SHAP đã lưu |
| `supplement.py`                                    | Mất cân bằng lớp (so các cách đặt ngưỡng) và công bằng theo mức thu nhập -> `SUPPLEMENT.md`                                                                                                 |
| `run_risk.py`, `make_report.py`                    | Thêm KS và so sánh ở cùng Precision với B1, ngưỡng chọn trên validation (đúng tiêu chí báo cáo giữa kỳ) -> `Prec_table.csv`, mục tương ứng trong `RESULTS.md`                               |
| `policies.py`, `run_upgrade.py`, `plot_upgrade.py` | Chính sách ngưỡng chọn trên validation, bootstrap ghép cặp từng seed, ablation (chạy bằng `run_upgrade.ps1`, SPEC mục 20) -> `results/upgrades/`                                            |


## Cập nhật kết quả ngày 23/10/2026

Số liệu và diễn giải hiện hành ghi ở **một nơi duy nhất**: `results/final/PUBLICATION.md` (nguồn từng bảng) và mục "Cập nhật kết quả ngày 23/10/2026" đầu `THAY_DOI.md`. Không chép lại số ở đây để tránh lệch khi cập nhật.
