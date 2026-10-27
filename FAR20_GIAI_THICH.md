# Chính sách cảnh báo FAR20: là gì và vì sao nhóm chọn làm chính sách chính

Số liệu lấy từ test, trung bình 3 seed, file `results/final/policies_mean.csv` và `policies_per_seed.csv`.

## 1. Bối cảnh: mô hình cho ra một con số, nhưng cần một quy tắc để báo

Mỗi tối, mô hình tính **p** = xác suất cuối chu kỳ số dư xuống dưới mức an toàn θ.
p chỉ là một con số. Để biết **có gửi cảnh báo hay không**, cần thêm một ngưỡng: p vượt ngưỡng thì báo.
"Chính sách" chính là **cách chọn ngưỡng đó**. Ngưỡng cao thì ít báo, dễ bỏ sót. Ngưỡng thấp thì báo nhiều, dễ làm phiền.

## 2. FAR20 là gì

**FAR** = *False Alarm Rate*, tỉ lệ báo nhầm.
**FAR20** = chọn ngưỡng sao cho **không quá 20% chu kỳ bình thường bị báo nhầm**.

- Báo nhầm được tính **theo chu kỳ** (theo tháng lương), không tính theo từng ngày.
  Một chu kỳ bình thường, tức cuối kỳ không thiếu tiền, mà có **ít nhất một ngày** bị cảnh báo thì tính là 1 chu kỳ bị báo nhầm.
- Nói dễ hiểu: **trong 10 tháng không có chuyện gì, người dùng bị làm phiền vô ích tối đa 2 tháng.**

### Ngưỡng được chọn thế nào (`policies.py`, hàm `select_far_threshold`)

1. Trên tập **validation**, lấy các chu kỳ bình thường.
2. Với mỗi chu kỳ, lấy p **cao nhất** trong chu kỳ đó, tức lúc mô hình "lo" nhất.
3. Đặt ngưỡng ở mức **cao hơn 80%** các giá trị này (phân vị 80%). Như vậy chỉ khoảng 20% chu kỳ bình thường có lúc nào đó p vượt ngưỡng.
4. **Khoá** ngưỡng đó lại, rồi mới đo trên test. Test không được dùng để chọn ngưỡng.

`demo.html` dùng đúng quy tắc này cho cả XGB+risk lẫn B1/B2 (seed 1: τ = 0,527).

Ngưỡng thu được với XGB+risk là p ≈ 0,50–0,56 tuỳ seed. Báo nhầm trên test là 18,5–20,4%, sát mục tiêu 20%, nghĩa là ngưỡng chọn trên validation chuyển sang test tốt.

## 3. So với ngưỡng F1 đang dùng

Ngưỡng F1 (p* ≈ 0,31) là ngưỡng làm F1 **tính theo từng ngày** cao nhất trên validation. F1 là thước đo thống kê, không biết người dùng có bị làm phiền hay không.

| XGB+risk, test | Ngưỡng F1 | **FAR20** |
|---|---|---|
| Chu kỳ bình thường bị báo nhầm | 44,2% | **19,4%** |
| Số ngày bị báo nhầm trong một chu kỳ bình thường | 4,2 | **1,3** |
| Chu kỳ bình thường bị báo nhầm ≥ 5 ngày | 29,5% | **11,0%** |
| Chu kỳ thiếu tiền được bắt | 98,3% | 94,4% |
| Số ngày báo trước, trung bình | 22,6 | 17,7 |
| F1 theo ngày | 0,702 | 0,669 |

**Đổi lại:** cứ 100 chu kỳ thiếu tiền thì bỏ sót thêm khoảng 4, và cảnh báo đến muộn hơn khoảng 5 ngày nhưng vẫn sớm hơn 2 tuần. Bù lại, số lần làm phiền vô ích giảm hơn một nửa.

## 4. Vì sao chọn FAR20 làm chính sách chính

1. **Đúng với trải nghiệm thật của người dùng.** Một ứng dụng báo nhầm gần một nửa số tháng sẽ bị tắt thông báo, khi đó cả những cảnh báo đúng cũng mất tác dụng ("mệt mỏi vì cảnh báo"). Giới hạn báo nhầm là điều kiện để cảnh báo còn được tin.
2. **Dễ giải thích.** "Tối đa 2/10 tháng bình thường bị báo nhầm" dễ hiểu hơn "F1 = 0,702".
3. **So sánh công bằng giữa các mô hình.** Khi mọi mô hình bị giới hạn cùng mức báo nhầm, chỉ còn so ai **bắt được nhiều chu kỳ thiếu tiền hơn**:

   | Mô hình | Bắt được (báo nhầm ≈ 18–19%) |
   |---|---|
   | B1 | 72,9% |
   | B2 | 80,0% |
   | XGB | 92,8% |
   | **XGB+risk** | **94,4%** |

   Ở ngưỡng F1, mô hình nào cũng bắt được 97–99% nên khó thấy khác biệt. Ở FAR20, XGB+risk hơn B1 khoảng **21,5 điểm**, và lớp risk đứng đầu ở cả 3 seed.
4. **Ổn định khi gặp người mới.** Trên tập user-holdout (người không có trong tập huấn luyện), FAR20 vẫn cho bắt 93,9% và báo nhầm 19,4%.
5. **Không gian lận.** Ngưỡng chọn hoàn toàn trên validation, khoá lại rồi mới đo test.

## 5. Giới hạn cần nói rõ

- Con số **20% là quy ước của nhóm**, chưa tính từ chi phí thật của một lần báo nhầm so với một lần bỏ sót. Có thể đổi thành FAR10 hoặc FAR30. Muốn chọn theo chi phí thì xem các chính sách `cost_r*_val` và `bayes_r*` trong cùng bảng.
- **Ngưỡng F1 vẫn được giữ** trong bảng so sánh Q2, vì đó là thước đo chuẩn để so mô hình. FAR20 là chính sách **vận hành**, tức cách sản phẩm thực sự gửi cảnh báo.
- Ngưỡng được chọn trên dữ liệu **mô phỏng**. Trên MoneyData (dữ liệu thật), ngưỡng chuyển từ simulator sang vẫn báo nhầm 10/10 chu kỳ bình thường. Với dữ liệu thật, phải chọn lại ngưỡng trên validation của chính dữ liệu đó.

## 6. Câu nói gọn khi thuyết trình

> "Chúng tôi giới hạn báo nhầm ở 20% số tháng bình thường. Trong giới hạn đó, mô hình bắt được 94% số tháng sắp thiếu tiền, báo trước trung bình 18 ngày. Cách cũ B1 chỉ bắt được 73%."
