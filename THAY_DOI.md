# Nhật ký thay đổi
## Đồng bộ demo FAR20 và form tự nhập (28/10/2026)

- Cập nhật `make_demo.py` chọn τ của XGB+risk và biên B1/B2 bằng `select_far_threshold` trên validation. Dùng dữ liệu nhúng FAR20 seed 1 từ bản dự án mới (τ = 0,527; 20 người, 80 chu kỳ), thay giao diện có nút **Xem kết quả** và chú giải từng trường. Dữ liệu dự báo nhúng không huấn luyện lại trong lượt này.
- Phần nhập thử chỉ tính số dư từ các số người xem nhập; không áp dụng FAR20 hoặc tạo xác suất cho người mới. Mục chu kỳ có sẵn hiển thị rõ FAR20 và nói tỷ lệ báo nhầm test có thể khác 20%. Bỏ footer dài.

## Demo tự nhập tình huống thu chi (27/10/2026)

- Theo góp ý giao diện: giải thích từng trường, chỉ tính khi bấm **Xem kết quả**, ẩn kết quả cũ khi sửa dữ liệu và bỏ đoạn footer dài.
- Giữ nguyên các chu kỳ mô phỏng đã tính trước. Thêm phần tự nhập thu/chi tính số dư ngay trên trình duyệt; phần này không tạo xác suất XGBoost cho người mới.
- Ở bản 27/10, demo dùng p* tối đa F1. Bản 28/10 chuyển phần chu kỳ có sẵn sang FAR20; phép kiểm Q2 vẫn dùng ngưỡng F1 riêng. Câu giới hạn MoneyData nêu kết quả cảnh báo gần như mọi chu kỳ trên tài khoản thật.

## Đợt 7 — sửa các lỗi đã xác nhận (23/10/2026)

**Không đổi bộ số chính thức** (`results/final/`, `ket_qua_tham_chieu/` giữ nguyên).

| #   | Lỗi (đã tái hiện trước khi sửa)                                                                                                                                                                                                | Sửa                                                                                                                                                                                 | File                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| R-1 | CSV thu nhập 2 tuần/lần: điểm quyết định đầu tiên thiếu lịch sử 28 ngày, B2 đọc chỉ số âm (lấy vòng xuống cuối mảng), `scale` = NaN, XGB ra tổng chi 0 nên p = 0 và báo "an toàn" sai. Cùng lỗi ở θ khi trước chu kỳ < 14 ngày | `make_dp` bỏ điểm có < `MIN_HISTORY` = 28 ngày lịch sử của chính người đó, không tính θ khi < 14 ngày; cảnh báo, báo lỗi nếu không còn điểm                                         | `labels.py`                          |
| R-2 | Tiền vào giữa chu kỳ / chi âm làm số dư tăng, trái giả định "số dư chỉ giảm": ví dụ số dư thủng θ ngày 23 nhưng y = 0                                                                                                          | Cách nhanh: phát hiện, cảnh báo, ghi `thu_nhap_giua_ky`, `chi_am_sau_ngay_nhan_dau`, `vi_pham_so_du_chi_giam` vào `attrs["quality"]`; demo CSV hiện lưu ý. Chưa đổi định nghĩa nhãn | `import_real.py`, `make_demo.py`     |
| R-3 | Demo báo "Có nguy cơ" nhưng đường dự báo trung bình không chạm θ, không giải thích (269/2.129 ngày)                                                                                                                            | Thêm câu giải thích trong kết luận; `test_demo.js` kiểm tra độc lập từ dữ liệu ở mọi ngày                                                                                           | `demo_template.html`, `test_demo.js` |
| R-4 | Docstring `risk.py` ghi phân phối dựng "trên val" và cumb dùng "big28"                                                                                                                                                         | Sửa thành calib và `bigrate` (5×, 84 ngày)                                                                                                                                          | `risk.py`                            |

**Kiểm chứng:**
- `dp` giống hệt trước khi sửa ở seed 1, 2, 3 (SHA256 trên bảng `dp`: 185.161 / 185.070 / 184.851 điểm), nên mọi bước sau và bộ số chính thức không đổi.
- `test_pipeline.py` thêm mục 10 (CSV chu kỳ ngắn và tiền vào giữa kỳ); mục 9 nay kỳ vọng 6 cảnh báo thay vì 5 (thêm cảnh báo số dư tăng do dòng chi âm trong dữ liệu test). Cả 3 bộ test: `TẤT CẢ OK`. `check_conventions`: `TAT CA DAT`. `check_extras --skip-sens`: `TAT CA DAT`. `test_demo.js`: `TẤT CẢ OK`.
- `demo.html`: dựng lại trên máy này cho dự báo XGB khác bản công bố ở một số ngày (36 ngày đổi trạng thái cảnh báo) do khác môi trường chạy (Python 3.12.10 so với 3.12.14, CPU khác); dựng hai lần trên cùng máy cho kết quả giống hệt. Để demo khớp bộ công bố, **giữ nguyên dữ liệu nhúng của bản công bố**, chỉ thay template mới.

## Đợt 6 — đồng nhất tài liệu (23/10/2026)

Chỉ sửa tài liệu, không sửa mã nguồn hoặc kết quả. Thực hiện bằng Claude Code theo yêu cầu người dùng.

- Khối "Cập nhật kết quả ngày 23/10/2026" trước đây được chép y nguyên vào README, SPEC, DATA_CARD và file này. Nay chỉ giữ ở file này; ba file kia trỏ về đây và `results/final/PUBLICATION.md`, để lần sau đổi số không sót chỗ.
- `SPEC.md`: thêm mục 20 cho `policies.py`/`run_upgrade.py` (v2.9 trước đây chỉ có ở dòng đầu); mục 5 liệt kê đủ cum/cumb/mc; mục 11 sửa mô tả B2+risk (code luôn dùng "cum", không cùng phương pháp với XGB); mục 12 thêm các bảng mới trong `results/final/`; mục 15 ghi hai giới hạn đã biết của đường nhập CSV; mục 18 ghi đúng runtime.
- `README.md`: thêm `run_upgrade.ps1`, `results_pre_val_precision\`, `publication_backups\` vào cấu trúc thư mục; số file .py 32 → 35; thay đoạn ghi chú chạy lại (TEMP, runtime) bằng một dòng trỏ `PUBLICATION.md`; thêm dòng `policies.py`/`run_upgrade.py` vào bảng.
- `DATA_CARD.md`: ghi rõ mỗi seed tự sinh lại dữ liệu, `data/daily.csv` chỉ dùng cho hình kiểm tra; thêm hai giới hạn của đường nhập CSV.
- `requirements.txt`: dòng chú thích ghi đúng hai runtime Python.

## Đợt 5 — đồng bộ kết quả và tài liệu ngày 23/10/2026

Đã kiểm tra SHA256 nguồn và artifact của 12 checkpoint nâng cấp; công bố lại bảng chi phí/CI, bổ sung bảng chính sách và ablation vào results/final, đồng bộ bản tham chiếu. Không huấn luyện lại, không sửa mô hình hoặc ngưỡng demo. Bản cũ được giữ ở publication_backups/20261023_224155. Kiểm tra sau cập nhật: check_expected.py TẤT CẢ ĐẠT; bản tham chiếu khớp SHA256. Script Python phụ dùng một lần đã được xóa theo phản hồi người dùng; không thêm mã chức năng. Các mục đợt 1–4 bên dưới là lịch sử, không mô tả trạng thái hiện hành. ChatGPT/Codex hỗ trợ cập nhật tài liệu và báo cáo.

## Cập nhật kết quả ngày 23/10/2026

Nguồn hiện hành: `results/final/PUBLICATION.md`, `UPGRADE_RESULTS.md`, `policies_mean.csv`, `policies_sd.csv` và các bảng từng seed. Bản tham chiếu được đồng bộ với bộ công bố. Bảng lõi và thí nghiệm nâng cấp có runtime riêng được ghi rõ; không coi chúng là một lần chạy duy nhất.

- Chi phí FP=1, FN=2: ngưỡng chọn trên validation cho chi phí test XGB+risk **24,83**, B2 **26,78** trên 100 điểm quyết định. Bayes 1/3 cho **24,83** (hai số trùng sau làm tròn, không bằng nhau tuyệt đối). Không gọi đây là chi phí tối ưu trên test.
- FAR20 chọn trên validation: XGB+risk đạt FAR test **19,4%**, Recall chu kỳ **94,4%**; B2 đạt **18,2% / 80,0%**, B1 **19,1% / 72,9%**. Không ép FAR test bằng 20%.
- CI95% bootstrap ghép cặp theo người được báo từng seed, giữ mô hình/ngưỡng cố định. Mean/SD qua ba seed không phải CI95% chung. F1 của risk so với XGB biên chỉ tăng khoảng 0,0016; CI từng seed chứa 0, chưa chứng minh cải thiện F1 rõ rệt.
- User-holdout có lịch sử: XGB+risk ở ngưỡng F1 có F1 **0,667**, FAR **67,6%**, **6,78** ngày cảnh báo/chu kỳ bình thường. Với chi phí r=2 chọn trên val: **0,696 / 51,9% / 5,13 ngày**; Bayes r=2: **0,700 / 46,3% / 4,15 ngày**; FAR20-val: **0,665 / 19,4% / 1,38 ngày**, Recall chu kỳ **93,9%**. Đây là các chính sách định trước, không chọn người thắng trên test.
- Ablation ba seed: MAE chi tiêu đầy đủ **108.581 VND**, bỏ lịch sử cá nhân **108.578 VND**, bỏ nhóm lịch/thống kê gần đây **120.280 VND** (+10,8%). Bỏ lịch sử cá nhân tăng MAE số dư khoảng 2,2%. SHAP cao không chứng minh nhóm đặc trưng là không thể thay thế; chưa xác định đặc trưng nào thay thế nó.
- CSV mặc định từ chối ô lỗi/ngày thiếu/số dư thiếu. Chỉ điền khi chọn `missing_policy=zero` hoặc `balance_policy=ffill`; lưu dấu vết trong `attrs["quality"]` và metadata demo. Điền dữ liệu là giả định, không phải phục hồi giao dịch thực.
- Test đã được xem khi phát triển. Các kết quả này chưa chứng minh cold start không có lịch sử, hiệu quả ngoài simulator hay tác động hành vi người dùng.


## Đợt 4 — nâng cấp đánh giá và chất lượng dữ liệu (23/10/2026)

Các thay đổi mã nguồn và phân tích của đợt này được ChatGPT/Codex thực hiện theo yêu cầu người dùng. Nhật ký này là bằng chứng sử dụng AI cho lần nâng cấp; phần khai báo trong báo cáo cuối kỳ chưa được cập nhật.

- Thêm `policies.py`: tối ưu chi phí chỉ trên validation, chọn ngưỡng FAR20 theo chu kỳ âm validation, giữ nguyên khi đo test; đo thêm số ngày cảnh báo và tỉ lệ chu kỳ âm bị cảnh báo ít nhất 5 ngày.
- `extra_analysis.py` chuyển từ tối ưu chi phí trên test sang chọn trên validation. Tên cột mới `cost_test_per_100`, `cost_val_per_100`, `tau_val`, `threshold_source`; bộ CSV cũ được giữ làm lịch sử, không trộn vào bộ mới. `check_expected.py` được cập nhật theo schema này.
- `summarize_extra.py` xuất CI bootstrap riêng từng seed và mean/SD; bỏ trung bình cận CI. Từ chối tổng hợp các file chi phí cũ chọn ngưỡng trên test.
- `run_risk.py` lưu mô hình, dự báo calib/val/test, điểm validation/test, ngưỡng và bảng chính sách. Chỉ số FAR cũ vẫn là đường đánh đổi mô tả; bảng chính sách mới là kết quả ngưỡng chọn trên validation.
- Thêm `run_upgrade.py`/`run_upgrade.ps1`: chạy temporal và user-holdout, hai ablation trên seed 1/2/3, lưu checkpoint có SHA256; phân tích lại được từ cache. Thêm bootstrap ghép cặp theo người ở ngưỡng cố định và CI chênh lệch tại mục tiêu Precision chung. Không kết luận tương đương Precision khi chưa có biên tương đương định trước.
- `model_xgb.py` hỗ trợ chọn tập con đặc trưng cho ablation; mặc định vẫn dùng toàn bộ đặc trưng và tham số cũ. Bỏ nhóm lịch sử cá nhân hoặc nhóm lịch/thống kê gần đây theo danh sách đã ghi trong `results/upgrades/PROTOCOL.md`.
- `import_real.py` mặc định từ chối ô lỗi/ngày thiếu/số dư thiếu; chỉ điền khi chọn rõ `zero`/`ffill`. Lưu chính sách và dấu vết biến đổi theo ngày/trường; không ghi đè nguồn. `make_demo.py` và `run_extras.ps1` nhận lựa chọn này, demo lưu metadata và hiện lưu ý nếu có điền dữ liệu. Điều chỉnh lời gọi trong bài kiểm tra nhập liệu sẵn có cho chính sách mới.
- Đồng bộ README, DATA_CARD và SPEC v2.9. Thêm `plot_upgrade.py` để tạo hai hình chính sách và ablation từ số liệu mới.
- Kết quả nâng cấp nằm riêng trong `results/upgrades/`; bộ `results/final/` và `ket_qua_tham_chieu/` vẫn là kết quả chốt trước đợt này. File báo cáo cuối kỳ DOCX không được chỉnh sửa.
- Runtime lần nâng cấp được ghi bằng phiên bản thực trong `results/upgrades/runtime_packages.json` và từng `complete.json`; không giả định khớp toàn bộ phiên bản cũ.

**Mục lục các đợt** (mới nhất ở trên):
- **Đợt 8 (24/10/2026):** sửa khai báo AI trong DOCX; bài tự làm cho Người 2 trong `docs/`. Xem đầu file.
- **Đợt 7 (23/10/2026):** sửa R-1 đến R-4 (thiếu lịch sử, số dư tăng giữa kỳ, giải thích trong demo, docstring). Xem đầu file.
- **Đợt 6 (23/10/2026):** đồng nhất tài liệu. Xem đầu file.
- **Đợt 5 (23/10/2026):** công bố lại bảng chi phí, CI, chính sách, ablation vào `results/final/`. Xem đầu file.
- **Đợt 4 (23/10/2026):** chính sách ngưỡng chọn trên validation, CI từng seed, ablation, chính sách nhập CSV tường minh. Xem đầu file.
- **Đợt 3 (23/10/2026):** chọn ngưỡng so sánh cùng Precision trên validation và chỉ đo trên test; thêm đánh giá phụ giữ riêng người dùng; ghi rõ giới hạn dữ liệu mô phỏng. Xem mục dưới.
- **Đợt 2 (22–23/10/2026):** ghim phiên bản thư viện, thêm KS, so sánh ở cùng Precision, ngưỡng và mất cân bằng lớp, công bằng theo thu nhập, kiểm tra CSV thật, lý do cảnh báo trong demo. Xem sau Đợt 3.
- **Đợt 1 (22/10/2026):** phân tích lỗi và lý do cảnh báo (SHAP). Xem phần "Đợt 1" ở cuối file.

---

# Đợt 3 (23/10/2026)

Công cụ: ChatGPT/Codex hỗ trợ theo yêu cầu người dùng (ghi nhận theo báo cáo cuối kỳ §6; bản gốc của mục này không ghi công cụ).

## 1. Sửa quy trình chọn ngưỡng cùng Precision

Trước đây `lead_at_precision` tìm ngưỡng trên chính tập test rồi báo Recall/lead time của test. Đây là lựa chọn ngưỡng dựa vào test, làm kết quả lạc quan và không còn là đánh giá holdout độc lập.

Đã sửa như sau:

- Precision mục tiêu bằng B1 được tính trên validation sau khi tune biên `m` của B1 trên validation.
- Với mỗi mô hình, chọn ngưỡng thấp nhất còn đạt Precision mục tiêu trên validation (Recall validation cao nhất trong các ngưỡng đạt điều kiện).
- Giữ ngưỡng đó và áp dụng lên test một lần. Báo cáo Precision validation và Precision test riêng; hai giá trị có thể khác nhau.
- Thêm kiểm tra tính chất: thay đổi nhãn/điểm số test không được làm thay đổi ngưỡng hoặc Precision validation đã chọn.

Các file thay đổi: `cashflow_risks/evaluate.py`, `cashflow_risks/run_risk.py`, `cashflow_risks/make_report.py`, `cashflow_risks/test_pipeline.py`, `cashflow_risks/run_user_holdout.py`, `cashflow_risks/summarize_user_holdout.py`, `cashflow_risks/check_expected.py`, `cashflow_risks/explain.py`, `run_all.ps1`, `SPEC.md`, `DATA_CARD.md`, `README.md`, `SLIDE_NHAP.md`.

## 2. Giới hạn dữ liệu được ghi rõ

Thêm `DATA_CARD.md` và cập nhật `README.md` để nói rõ bộ 300 người × 24 chu kỳ là mô phỏng, các tập thời gian đang dùng cùng nhóm người, CSV thật chưa được dùng để huấn luyện/đánh giá, và kiểm tra CSV chỉ cảnh báo chứ không tự sửa. Không tạo hoặc suy diễn dữ liệu người dùng thật.

Thêm `run_user_holdout.py` và `summarize_user_holdout.py`: nhóm người dùng train/calib/val/test không trùng nhau, nhưng từng vai trò vẫn lấy giai đoạn chu kỳ tương ứng. Kết quả tách riêng trong `results/user_holdout/`, không trộn với bảng đánh giá thời gian chính.

## 3. Chạy chốt và xác minh (23/10/2026)

- Pipeline lõi theo đúng thứ tự của `run_all.ps1` đã hoàn tất đủ ba seed, user-holdout, tổng hợp báo cáo, phân tích lỗi, SHAP và supplement. Lần đầu XGBoost không ghi được file đo độ trễ vào thư mục TEMP bị giới hạn của Windows; các bước còn lại được tiếp tục từ `extra_analysis.py` seed 1 với `TEMP/TMP` trỏ vào `.pipeline_tmp` trong workspace. Không sửa mã nguồn.
- `test_pipeline.py`, `test_xgb.py`, `test_risk.py` đều báo `TẤT CẢ OK`; `check_expected.py` báo **`TẤT CẢ ĐẠT`**, gồm cả kiểm tra user-holdout.
- `run_extras.ps1 -SkipInstall` đã chạy đủ 13 kịch bản độ nhạy và dựng lại demo. `check_extras.py` báo **`TAT CA DAT`**; cả 5 kết luận độ nhạy giữ ở 13/13 kịch bản (65/65); demo có 20 người, 80 chu kỳ và 0 lỗi dự báo.
- Runtime: Python 3.12.14; NumPy 2.4.5, pandas 3.0.6, SciPy 1.17.1, scikit-learn 1.9.1, XGBoost 3.4.1, Matplotlib 3.10.9, tabulate 0.10.0. Các gói khớp `requirements.txt`; bản Python lệch patch so với 3.12.10 ghi trong nhật ký cũ.
- Bộ chốt nằm trong `results/final/`; `ket_qua_tham_chieu/` là bản sao đối chiếu SHA256 giống hệt. Bản tham chiếu trước thay đổi phương pháp được giữ trong `ket_qua_tham_chieu_pre_val_precision_20261023/`; `results_cu_20261023_1154/` là lần chạy trung gian không đầy đủ và không dùng để trích số.

Ở cùng Precision: mục tiêu validation của B1 là 0,592; XGB+risk đạt 0,593 trên validation và 0,580 trên test, Recall test 0,833, báo trước 24,3 ngày. So với B1, Recall tăng 8,7 điểm phần trăm và báo trước 1,9 ngày; cả hai chênh lệch cùng chiều ở 3/3 seed. Không diễn giải Precision test là bằng B1.

User-holdout: nhóm test gồm 60 người mô phỏng, tách khỏi train/calib/val; XGB giảm MAE chi tiêu 16,1% và MAE số dư 24,9% so với B2; XGB+risk F1 0,667 so với B2 0,646, nhưng báo nhầm theo chu kỳ 0,676. Đây vẫn là phép thử trong cùng simulator, không xác nhận hiệu quả với người thật.

---

# Đợt 2 (22–23/10/2026)

Công cụ: Claude (Claude Code) thực hiện theo yêu cầu người dùng.

Mục đích: lấp các chỗ hở về code mà thang điểm cuối kỳ và báo cáo giữa kỳ đòi hỏi, rồi chạy lại toàn bộ để có **một bộ số chính thức duy nhất**. Logic mô hình, nhãn và cách chia tập không đổi, chỉ thêm chỉ số, bảng và kiểm tra.

## 1. Đổi gì và vì sao

| #   | Việc                                                                                                                                                                                                             | File                                                      | Vì sao                                                                                                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| a   | Ghim phiên bản thư viện; `run_all.ps1`, `run_extras.ps1` cài bằng `pip install -r requirements.txt`                                                                                                              | `requirements.txt` (mới), `run_all.ps1`, `run_extras.ps1` | Đợt 1 phát hiện các dòng XGB lệch nhẹ khi chạy với phiên bản xgboost khác (F1 0,702 → 0,703). Ghim phiên bản thì ai chạy lại cũng ra đúng bộ số trên slide.                                                                         |
| b   | Thêm **KS** (= max(TPR − FPR)) vào `rank_metrics`; KS có trong bảng Q2                                                                                                                                           | `evaluate.py`, `run_risk.py`, `make_report.py`            | KS là chỉ số quen thuộc khi đánh giá điểm rủi ro tài chính. Hội đồng có thể hỏi, và có thêm cũng không mất gì.                                                                                                                      |
| c   | **So sánh ở cùng Precision với B1** (hàm `lead_at_precision`): đặt ngưỡng của từng mô hình sao cho Precision bằng B1, rồi so Recall và số ngày báo trước. Đầu ra: `Prec_table.csv` và một mục trong `RESULTS.md` | `evaluate.py`, `run_risk.py`, `make_report.py`            | Báo cáo giữa kỳ cam kết tiêu chí "ở mức Precision tương đương, Recall cao hơn hoặc báo sớm hơn B1". Trước đây code chỉ so ở cùng mức báo nhầm, chưa đúng câu chữ đó. Thang điểm trừ điểm nếu lệch giữa kỳ mà không giải thích.      |
| d   | **Mất cân bằng lớp:** tỉ lệ thiếu tiền ở từng tập, và cùng một p với 3 cách đặt ngưỡng (p* chọn trên val, 0,5, tỉ lệ nền)                                                                                        | `supplement.py` (mới)                                     | Thang điểm hỏi cách xử lý mất cân bằng lớp. Mô hình chính là hồi quy chi tiêu nên không có trọng số lớp; mất cân bằng chỉ tác động ở bước đặt ngưỡng. Bảng này chứng minh điều đó và trả lời luôn câu hỏi về "mệt mỏi vì cảnh báo". |
| e   | **Công bằng theo mức thu nhập:** chia 3 mức thu nhập trong từng loại thu nhập (6 nhóm), so bỏ sót, báo nhầm, AUROC, ECE                                                                                          | `supplement.py`                                           | Thang điểm cộng điểm cho phân tích công bằng. Trước đây chỉ có phân tích theo kiểu chi tiêu và loại thu nhập. Chia mức trong từng loại vì trợ cấp (3–5 triệu) và lương (7–15 triệu) khác nhau hẳn.                                  |
| f   | **Kiểm tra chất lượng CSV thật:** phát hiện ô trống hoặc lỗi, chi âm, ngày thiếu, ngày chi bất thường, số dư thiếu. **Chỉ cảnh báo, không tự sửa**; kết quả lưu trong `df.attrs["quality"]`                      | `import_real.py`, `test_pipeline.py`                      | Tiêu chí dữ liệu hỏi về làm sạch, dữ liệu thiếu và ngoại lai. Dữ liệu tài chính của người dùng không nên bị sửa ngầm (ví dụ chi âm có thể là hoàn tiền), nên chỉ báo để người dùng tự xem lại.                                      |
| g   | **Demo có dòng "Vì sao dự báo chi như vậy"**: 3 yếu tố làm tăng và 2 yếu tố làm giảm tổng chi dự báo nhiều nhất, theo SHAP, tính bằng nghìn đồng                                                                 | `make_demo.py`, `demo_template.html`, `test_demo.js`      | Đợt 1 mới có SHAP trong file kết quả, người dùng demo chưa thấy được. Báo cáo giữa kỳ hứa đầu ra dễ hiểu cho người dùng.                                                                                                            |
| —   | Thêm `supplement.py` vào `run_all.ps1`                                                                                                                                                                           | `run_all.ps1`                                             | Để một lệnh chạy ra đủ mọi bảng.                                                                                                                                                                                                    |

Logic của simulator, nhãn, mô hình, lớp xác suất giữ nguyên.

**Tài liệu (sau khi chạy xong):**

| File                  | Sửa gì                                                                                                                                                                                                                                                                      | Vì sao                                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `SPEC.md` → v2.7      | Mục 5 đổi "cum" thành "cumb" (nhóm tự sửa). Thêm KS vào mục 6c. Thêm mục 6e (so ở cùng Precision). Thêm kiểm tra CSV và dòng "Vì sao" vào mục 15. Thêm mục 18 (phân tích lỗi, SHAP, mất cân bằng lớp, công bằng, `requirements.txt`). Mục 12 hết liệt kê cứng `fig1..fig6`. | SPEC quy định mọi thay đổi phải báo cả nhóm. Dòng "cum" sai so với kết quả chạy chính thức.               |
| `README.md`           | Thêm `requirements.txt`, cờ `-SkipInstall` và `-BrowserTest`, mục "Kết quả" (`results\final\`, cách đổi tên `results_cu_*`). Thêm `supplement.py` và `Prec_table.csv`. Sửa số file `.py` từ 24 thành 30, thời gian chạy thành 15–35 phút tùy máy.                           | Người nhận gói zip cần biết số chính thức nằm ở đâu và cách chạy ra đúng số đó.                           |
| `ket_qua_tham_chieu\` | Thay bằng bản sao `results\final\` của lần chạy chính thức (44 file). Bản cũ đổi tên thành `ket_qua_tham_chieu_goc\`.                                                                                                                                                       | Có `requirements.txt` rồi thì bản đối chiếu nên khớp từng số với slide. Không script nào đọc thư mục này. |

## 2. Đã kiểm tra

- `test_pipeline.py` có thêm 2 ví dụ tính tay:
  - KS và so sánh ở cùng Precision;
  - nhập CSV lỗi: phải phát hiện đủ ô hỏng, chi âm, ngày thiếu, ngày bất thường, và không sửa dữ liệu.
- `test_demo.js` (Node.js + jsdom) chạy qua toàn bộ 2.440 ngày-chu kỳ của demo. Với mỗi ngày, test kiểm tra dòng "Vì sao" có xuất hiện đúng khi có dự báo và có nêu đúng yếu tố đứng đầu.
- Lần chạy chính thức (`run_all.ps1`, 23:44 ngày 22/10, 16,2 phút):
  - `check_conventions`: "TAT CA DAT";
  - `test_pipeline`, `test_xgb`, `test_risk`: "TẤT CẢ OK";
  - `check_expected`: **"TẤT CẢ ĐẠT"**.
- `run_extras.ps1 -SkipInstall -BrowserTest` (độ nhạy + demo + test trình duyệt, 16,2 phút):
  - `check_extras`: "TAT CA DAT";
  - độ nhạy: 64/65 kết luận giữ nguyên qua 13 kịch bản (chỉ kết luận thông tin K4 hỏng ở rho_lo);
  - `test_demo.js`: "TẤT CẢ OK", duyệt 2.440 ngày-chu kỳ không có lỗi.
- Nháp slide dùng bộ số này: `SLIDE_NHAP.md`.

## 3. Bộ số chính thức

**Bộ số chính thức là `results\` của lần chạy trên, với phiên bản trong `requirements.txt`. Slide và báo cáo chỉ lấy số từ đây.**

- `results_cu_20261022_2344\` là kết quả đợt 1, chỉ để đối chiếu.
- `ket_qua_tham_chieu\` bây giờ là bản sao của bộ số chính thức. Bản gốc nằm ở `ket_qua_tham_chieu_goc\`. Phần "Đợt 1" bên dưới viết `ket_qua_tham_chieu\` là để chỉ bản gốc này.
- Không dùng số trong `plan.pdf`.

Các dòng B1/B2 trùng hoàn toàn với đợt 1. Các dòng XGB cũng trùng (F1 0,703; tỉ lệ báo nhầm theo chu kỳ 0,420), vì cùng phiên bản thư viện.

Phương pháp tính p được chọn là **"cumb" ở cả 3 seed** (theo Brier trên val). "cumb" là "cum" có thêm nhóm theo tần suất chi lớn. `SPEC.md` mục 5 trước đây ghi "cum", nay đã sửa thành "cumb". Slide cũng dùng "cumb".

## 4. Kết quả mới đáng dùng

- **Đúng tiêu chí giữa kỳ (Precision bằng B1, 0,588):**
  - XGB + p > p* có Recall 0,826, so với 0,746 của B1 (+8,0 điểm phần trăm, 3/3 seed).
  - Số ngày báo trước (chu kỳ bỏ sót tính 0) là 24,3, so với 22,4 của B1 (+1,8 ngày, 3/3 seed).
- **Mệt mỏi vì cảnh báo:** cùng một p, dùng ngưỡng 0,5 thay cho p* (0,33) thì:
  - tỉ lệ chu kỳ bình thường bị báo nhầm giảm gần một nửa, từ 0,420 xuống 0,224;
  - tỉ lệ bắt được chu kỳ thiếu tiền chỉ giảm từ 0,981 xuống 0,952;
  - F1 giảm từ 0,703 xuống 0,678.
- **Công bằng theo thu nhập:** 6 nhóm có báo nhầm 0,39–0,44, bỏ sót 0,01–0,03, AUROC 0,87–0,91, không có nhóm nào lệch hẳn. Lưu ý: simulator không cài khác biệt hành vi theo thu nhập, nên đây chỉ chứng minh mô hình không tự tạo ra chênh lệch.
- **KS** (test): XGB + p 0,605; B2 0,575; B1 0,545.

---

# Đợt 1 (22/10/2026): phân tích lỗi và lý do cảnh báo

Mục đích: làm 2 việc cần code trong `plan.pdf`:
- **mục 6:** ví dụ ca báo nhầm và bỏ sót;
- **mục 5:** SHAP / "lý do cảnh báo" cho từng ca.

Không sửa logic của file nào đã có. Bản sao lưu trước khi sửa: `C:\Users\TIENTUONG\Downloads\cashflow_risk_backup`.

## 1. File thêm mới

| File                            | Việc                                                                                                                                                                                                            | Đầu ra (trong `results\final\`)                                                                            |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `cashflow_risks\error_cases.py` | Phân tích lỗi ở mức chu kỳ của XGB + p > p* (so với B2) trên test, 3 seed. Thống kê theo kiểu chi tiêu và loại thu nhập. Chọn 2 ví dụ theo quy tắc cố định.                                                     | `ERROR_ANALYSIS.md`, `error_summary.csv`, `error_by_group.csv`, `error_cases.csv`, `fig11_error_cases.png` |
| `cashflow_risks\explain.py`     | Lý do cảnh báo bằng SHAP. Dùng TreeSHAP có sẵn trong XGBoost (`pred_contribs=True`), **không cài thêm thư viện**. Viết một câu lý do cho mọi điểm test có cảnh báo, và giải thích 2 ví dụ của `error_cases.py`. | `explain_alerts_seed1.csv`, `explain_global_seed1.csv`, `explain_cases.csv`, `fig12_explain.png`           |
| `THAY_DOI.md`                   | File này                                                                                                                                                                                                        |                                                                                                            |

## 2. File sửa

| File          | Sửa gì                                                                                                                                                         |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `run_all.ps1` | Thêm `error_cases` và `explain` vào danh sách file bắt buộc. Thêm 2 lệnh chạy ngay sau `summarize_extra.py` (sau `make_report.py`, trước `check_expected.py`). |
| `README.md`   | Thêm bảng "Phân tích lỗi và lý do cảnh báo".                                                                                                                   |

Các file `.py` cũ, SPEC.md, `ket_qua_tham_chieu\` và `demo.html` giữ nguyên.

## 3. Định nghĩa và quy tắc

- **Báo nhầm (FP):** chu kỳ không thiếu tiền nhưng có ít nhất 1 cảnh báo.
- **Bỏ sót (FN):** chu kỳ thiếu tiền nhưng không có cảnh báo nào ở các điểm quyết định còn lại. Định nghĩa này giống `cycle_false_alarm` và `cycle_recall` trong `evaluate.py`.
- **"Suýt thiếu":** số dư cuối kỳ cao hơn θ nhưng chưa tới 1θ.
- **Chọn ví dụ:** lấy seed đầu (1). Với mỗi loại lỗi, chọn chu kỳ có p lớn nhất gần trung vị của loại lỗi đó nhất. Đây là ví dụ điển hình, không phải ca tệ nhất, và không chọn tay.
- **SHAP:**
  - Mô hình dự báo chi tiêu ngày đã chuẩn hóa. Đóng góp tính bằng VND = SHAP × mức chi TB 28 ngày, cộng qua h = 1..D. Kết quả là đóng góp của từng đặc trưng vào **tổng chi dự báo D ngày tới**.
  - Đặc trưng làm tăng tổng chi dự báo cũng làm tăng p.
  - Lớp xác suất (`risk.py`) chỉ thêm độ bất định theo nhóm, không có SHAP riêng.
- **Huấn luyện lại:** `explain.py` huấn luyện lại XGBoost giống hệt `run_risk.py` (cùng seed, cùng dữ liệu). Cảnh báo lấy từ `results\risk_points_seed1.csv`.

## 4. Đã kiểm tra

- `run_all.ps1` chạy hết trong 12,2 phút. Kết quả các bước kiểm tra:
  - `check_conventions`: "TAT CA DAT";
  - `test_pipeline`, `test_xgb`, `test_risk`: "TẤT CẢ OK";
  - `check_expected`: "TẤT CẢ ĐẠT".
- `explain.py` tự kiểm tra (`assert`): tổng SHAP của mỗi dòng bằng đúng dự báo của mô hình.
- Đã mở xem `fig11` và `fig12`, cả hai đọc được.
- Phiên bản thư viện khi chạy:

  | Thư viện     | Phiên bản |
  | ------------ | --------- |
  | Python       | 3.12.10   |
  | xgboost      | 3.4.1     |
  | pandas       | 3.0.6     |
  | numpy        | 2.4.5     |
  | scikit-learn | 1.9.1     |

## 5. Lưu ý về số liệu

**Kết quả chạy lại không trùng hoàn toàn với `ket_qua_tham_chieu\`:**
- Các dòng B1 và B2 giống hệt.
- Các dòng XGB lệch nhẹ (nhiều khả năng do khác phiên bản xgboost):

  | Chỉ số                                 | Tham chiếu | Chạy lại |
  | -------------------------------------- | ---------- | -------- |
  | XGB + p > p*, F1                       | 0,702      | 0,703    |
  | XGB + p > p*, tỉ lệ chu kỳ bị báo nhầm | 0,423      | 0,420    |
  | XGB theo biên m, F1                    | 0,701      | 0,698    |
  | XGB + p > p* (k=2), F1                 | 0,683      | 0,687    |

- `plan.pdf` lại trích một bộ số thứ ba (0,442; 0,66; 0,686).

→ Nhóm cần **chọn một bộ duy nhất** cho slide và báo cáo. Ghi kèm phiên bản thư viện, và không trộn số giữa các bộ.

## 6. Kết quả chính (test, trung bình ± độ lệch chuẩn 3 seed, xem `results\final\ERROR_ANALYSIS.md`)

**Lỗi gần như toàn là báo nhầm**

| Chỉ số                               | XGB + p > p*  | B2            |
| ------------------------------------ | ------------- | ------------- |
| Tỉ lệ chu kỳ bình thường bị báo nhầm | 0,420 ± 0,031 | 0,397 ± 0,058 |
| Tỉ lệ chu kỳ thiếu tiền bị bỏ sót    | 0,019 ± 0,011 | 0,033 ± 0,018 |

**Báo nhầm có cấu trúc rõ**
- 17% chu kỳ bị báo nhầm là "suýt thiếu". Ở các chu kỳ bình thường không bị cảnh báo, tỉ lệ này chỉ 1,6%.
- Cảnh báo nhầm thường bật ngay ngày 1 (trung vị).
- Trung vị chỉ khoảng 29% số ngày trong chu kỳ bị cảnh báo.
- → Có thể dùng các điểm này để trả lời câu hỏi về "mệt mỏi vì cảnh báo".

**Bỏ sót là các chu kỳ thiếu ít**
- Số dư cuối kỳ trung vị thấp hơn θ 1,69θ. Ở chu kỳ bắt được, mức này là 3,43θ.
- Bỏ sót không phải do chu kỳ có ít điểm quyết định.

**Theo kiểu chi tiêu**
- Kiểu `spike` vừa báo nhầm nhiều nhất (0,542) vừa bỏ sót nhiều nhất (0,034).
- Kiểu `front` không bỏ sót chu kỳ nào ở cả 3 seed.

**Lý do cảnh báo (SHAP, seed 1)**
- Đặc trưng ảnh hưởng nhiều nhất đến tổng chi dự báo là **số dư hiện tại**.
- Tiếp theo là chi tiêu quanh cùng ngày-trong-chu-kỳ ở các chu kỳ trước, và vị trí của hôm nay trong chu kỳ.
- Điều này khác với bảng độ quan trọng theo gain (`fig5`, trong đó `tgt_weekend` dẫn đầu). Gain đo mức đặc trưng được dùng để chia cây; SHAP đo mức nó làm thay đổi dự báo. Khi trình bày cần nói rõ đang dùng thước đo nào.
- Việc số dư hiện tại ảnh hưởng mạnh đến dự báo chi tiêu có thể phản ánh cách simulator tạo dữ liệu (chi tiêu tỉ lệ với thu nhập). Nên đưa vào phần "tính vòng tròn của dữ liệu mô phỏng".

## 7. Chưa làm (còn lại trong `plan.pdf`)

| Mục | Việc                                                                                    |
| --- | --------------------------------------------------------------------------------------- |
| 1   | Slide khả năng áp dụng                                                                  |
| 2   | Khai báo AI (cần ghi rằng hai script này do Claude viết theo yêu cầu, nhóm đã kiểm tra) |
| 3   | Dẫn chiếu Coreach                                                                       |
| 4   | Slide giới hạn dữ liệu                                                                  |
| 5   | Câu về mất cân bằng lớp, giải thích vì sao chọn XGB thay vì Ridge                       |
| 7   | Slide bài toán                                                                          |
| 8   | Phân vai, chuẩn bị phản biện                                                            |

## 8. Ghi chú khác

- `run_all_log.txt` ở thư mục gốc là log của lần chạy trên. Xóa được.
- `results\` là kết quả mới chạy. `ket_qua_tham_chieu\` vẫn là bản cũ, để đối chiếu.
- Chạy riêng phần mới (từ thư mục gốc, khi đã có `results\` của 3 seed):

  ```
  python cashflow_risks\error_cases.py --seeds 1 2 3
  python cashflow_risks\explain.py --seed 1        # khoảng 1 phút, huấn luyện lại XGBoost
  ```
