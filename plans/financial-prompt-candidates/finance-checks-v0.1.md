# Finance checks v0.1 — fragment dự thảo

Chỉ áp dụng kiểm tra liên quan đến câu hỏi; không bắt agent đọc toàn bộ nghiệp vụ
cho mỗi giá cổ phiếu. Đây chưa phải validator tài chính hoặc khả năng đã kiểm chứng.

---

Trước khi dùng số tài chính, kiểm các dimension có trong dữ liệu:

- **Thực thể/chỉ tiêu:** đúng mã và loại chỉ tiêu; không đồng nhất chỉ tiêu tổng với
  phần thuộc cổ đông công ty mẹ, hoặc dùng chỉ tiêu gần tên để thay chỉ tiêu thiếu.
- **Kỳ:** phân biệt kỳ báo cáo, ngày công bố và as-of; quý riêng, lũy kế, TTM và năm
  không thay nhau. Niên độ doanh nghiệp có thể khác năm dương lịch; dùng metadata
  nguồn. “Gần nhất” theo mốc dữ liệu được yêu cầu, không mặc định theo giờ máy.
- **Scope/basis:** hợp nhất và riêng lẻ, số cuối kỳ và bình quân, adjusted/unadjusted,
  trailing/forward phải cùng cơ sở khi so sánh. Nếu chưa rõ, nêu giới hạn hoặc lấy
  metadata cần thiết; không tự phát minh basis để hoàn thành câu trả lời.
- **Đơn vị:** giữ currency và hệ số đồng/nghìn/triệu/tỷ; phân biệt phần trăm với điểm
  phần trăm, chiều yết tỷ giá và phép nghịch đảo. USD và USDT không tự coi là bằng
  nhau; cần dữ liệu chuyển đổi hoặc giả định được cho phép và ghi rõ.
- **Phép tính:** operand đúng kỳ/scope/unit. Với tỷ lệ thay đổi thông thường, kiểm
  cơ sở so sánh và dấu mẫu số; zero không chia được, nền âm cần giải thích bản chất
  thay đổi. Không áp công thức máy móc để gọi mọi kết quả là tăng trưởng.
- **Tập hợp:** trung bình/ranking dùng đúng danh sách và tiêu chí; báo số phần tử thực
  có, không tính thiếu mã rồi gọi là kết quả của toàn bộ tập. Không trộn phiên hoặc
  valuation basis. Giá trị tool tính sẵn phải ghi là trích xuất, không giả là đã tự tính.
- **Đối chiếu:** nguồn mâu thuẫn thì kiểm kỳ/đơn vị/scope trước; không chọn nguồn chỉ
  vì cho kết quả thuận lợi. Không tự bình quân nguồn khác bản chất hoặc khác thời điểm.

Phân biệt câu hỏi chỉ yêu cầu con số với câu hỏi cần diễn giải. Chỉ xuất công thức,
operand và giả định ngắn khi user/schema cho phép; không cần xuất suy nghĩ nội bộ.

---

Fragment này chưa xác nhận các case hợp nhất/riêng lẻ, niên độ đặc biệt, adjusted
prices hoặc restatements có mặt trong benchmark hiện tại. Muốn claim các năng lực
đó phải có dữ liệu và rubric tương ứng trước khi chạy kiểm chứng.
