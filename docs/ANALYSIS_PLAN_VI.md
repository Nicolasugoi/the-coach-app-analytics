# Kế hoạch phân tích The Coach

## Câu hỏi trung tâm

Sau lần kích hoạt Pro đầu tiên, người dùng tích lũy thời gian học như thế nào, mức độ đạt mục tiêu 20 giờ trong 30 ngày ra sao, và sự suy giảm nằm ở khả năng quay lại, tần suất học hay thời lượng mỗi ngày học?

Phạm vi gồm phân tích hành vi và mức độ đạt mục tiêu. Chưa đề xuất tính năng, thử nghiệm sản phẩm hay kế hoạch tiếp thị.

## Trình tự ra quyết định

1. **Hiểu phép đo.** Xác định đơn vị và grain trước khi nối bảng. Mỗi người dùng nối với nhiều bản ghi ngày. Thời gian app gồm hoạt động ngoài học; thời gian module gồm năm cột, kể cả `other`. Tổng module là chỉ số đại diện cho thời gian học được ghi nhận, chưa chứng minh các bộ đếm không chồng lấn.
2. **Kiểm tra khả năng sử dụng dữ liệu.** Kiểm tra khóa trùng, khóa không khớp, ngày không hợp lệ, giá trị thiếu/âm, thành phần vượt tổng và thời lượng cực lớn. Giữ dữ liệu gốc, ghi cờ bất thường; không mặc định cắt phân vị 99.
3. **Thiết lập phạm vi quan sát.** Ngày kích hoạt là ngày 0. Tháng đầu gồm ngày 0–29; cửa sổ dài gồm 120 và 150 ngày. Chỉ đánh giá mục tiêu khi toàn bộ cửa sổ nằm trong phạm vi log. Các cửa sổ dài là quy ước số ngày, không phải phép cộng tháng lịch.
4. **Đo mức nền.** Báo cáo tỷ lệ đạt mục tiêu, trung vị, trung bình và phân bố giờ học. Đối chiếu thời gian app với thời gian module để lượng hóa ảnh hưởng của lựa chọn chỉ số.
5. **Phân rã diễn biến.** Tách tỷ lệ có học, số ngày học trên người còn học và phút trên ngày học. Dùng một nhóm cố định đủ 91 ngày để so diễn biến tuần 0–12; dùng mẫu số đủ điều kiện riêng cho mỗi tuần trong bảng cohort.
6. **Tìm khác biệt có ý nghĩa.** So cohort và gói trong cùng cửa sổ; giữ nhóm động lực Khác. Với module, phân biệt từng dùng, dùng lại ít nhất hai ngày và mức sử dụng. Không suy số phiên từ dữ liệu ngày.
7. **Kiểm tra độ vững.** Đối chiếu SQL với phép tính pandas độc lập. So kết quả gốc với việc bỏ ngày trên 8 giờ, ngày tổng module vượt tổng app, và người dùng có ngày không hợp lý. Ngưỡng 8 giờ là kịch bản kiểm tra, không phải kết luận mọi bản ghi đó sai.
8. **Diễn giải có giới hạn.** Hành vi tuần đầu và việc quay lại sau này chỉ là liên hệ quan sát. Không suy nguyên nhân tâm lý, hiệu quả học tiếng Anh hoặc tác động nhân quả từ log.

## Các giới hạn cần giữ trong báo cáo

- `active_at` là lần kích hoạt đầu tiên; lịch sử mua lại và quyền truy cập từng thời điểm chưa được cung cấp.
- Coi ngày không có log là không hoạt động chỉ hợp lý với giả định hệ thống ghi nhận đầy đủ. Khoảng ngày có dữ liệu không tự chứng minh giả định đó.
- `total_complete_lesson` chỉ bao gồm bài giao tiếp; chưa dùng như số bài hoàn thành của cả app.
- Mốc 100 giờ sau 120 và 150 ngày có mẫu đủ điều kiện khác nhau. Muốn nói về tiến triển cần so trên cùng nhóm đủ 150 ngày.
- Không có dữ liệu referral để đo mục tiêu giới thiệu người dùng; không có toàn bộ người miễn phí để tính chuyển đổi sang trả phí.

## Phân công công cụ

Hai nhánh chạy độc lập từ cùng dữ liệu gốc. Nhánh SQL tự nhập nguồn, chuẩn hóa, kiểm tra chất lượng, tạo cửa sổ quan sát, cohort, tổng hợp và chuỗi ngày học, rồi xuất CSV cho Power BI. Power BI dùng Power Query, quan hệ giữa bảng và DAX để khám phá kết quả theo cohort/gói/cửa sổ. Nhánh Python tự đọc nguồn, khám phá, tính chỉ số, phân tích độ nhạy và vẽ biểu đồ; không đọc kết quả SQL hay tạo file Power BI. Đối chiếu kết quả giữa hai nhánh là bước kiểm chứng, không phải điều kiện chạy.

Đầu ra công khai chỉ gồm dữ liệu tổng hợp. Dữ liệu gốc được giữ ở bản làm việc cục bộ và loại khỏi ZIP công khai; `.gitignore` không theo dõi thư mục raw. PBIX/PBIT trong portfolio là báo cáo hiện tại dùng dữ liệu tổng hợp, không phải file thi gốc.
