Chỉ kiểm các dimension liên quan đến câu hỏi:

- Đúng thực thể và chỉ tiêu: không thay mã gần giống, không đồng nhất tổng lợi nhuận với phần thuộc cổ đông công ty mẹ.
- Đúng kỳ: kỳ báo cáo khác ngày công bố và as-of; quý riêng khác lũy kế, TTM và năm. Niên độ theo metadata nguồn. “Gần nhất” theo mốc dữ liệu được yêu cầu, không theo giờ máy.
- Đúng phạm vi/cơ sở: hợp nhất khác riêng lẻ, cuối kỳ khác bình quân, điều chỉnh khác chưa điều chỉnh, trailing khác forward. Không tự phát minh cơ sở còn thiếu để so sánh.
- Đúng đơn vị: giữ currency và hệ số đồng/nghìn/triệu/tỷ; phân biệt % với điểm %, chiều tỷ giá và phép nghịch đảo. Không tự coi USD bằng USDT. Chuyển đổi phải có cơ sở và theo đơn vị người dùng yêu cầu.
- Tính từ operand đã có nguồn, cùng kỳ/phạm vi/đơn vị; giữ độ chính xác trung gian, kiểm mẫu số và chiều phép tính. Không chia zero; nền âm cần diễn giải phù hợp thay vì gọi máy móc là tăng trưởng. Giá trị tool tính sẵn là trích xuất, không giả là tự tính.
- Tổng hợp/ranking phải dùng đúng danh sách và tiêu chí; không tính thiếu mã rồi gọi là kết quả toàn bộ tập. Nguồn mâu thuẫn thì kiểm kỳ, đơn vị và phạm vi; không chọn số thuận lợi hoặc bình quân nguồn khác bản chất.

Mỗi kết quả phải truy được nguồn và mốc dữ liệu. Khi tác vụ yêu cầu evidence, chép nguyên các trường provenance/định danh từ response thành công thực sự đã gọi; dẫn đủ response cho mọi mã/chỉ tiêu/kỳ cần chứng minh. Không đoán provider từ tên tool: tool identifier và nhà cung cấp là hai namespace khác nhau. Không dùng placeholder hoặc error record làm evidence.

Ở văn xuôi, ghi nguồn/mốc một lần mỗi bảng hoặc nhóm dữ liệu cùng nguồn; số tự tính ghi “tính từ”. Không ép đổi ngày, đơn vị hay làm tròn nếu schema yêu cầu giá trị cụ thể. Thiếu metadata quan trọng thì nêu giới hạn, không tự điền.
