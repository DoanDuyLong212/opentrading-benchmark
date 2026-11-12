# Output contract v0.1 — fragment dự thảo

Thiết kế để thay quy tắc trình bày đối lập, không append rồi giữ nguyên lệnh cấm JSON
ở layer khác. Không chứa đáp án hoặc định danh task.

---

Các quy tắc văn xuôi, bảng, chú giải thuật ngữ và đơn vị hiển thị là mặc định cho hội
thoại thường. Khi user hoặc hợp đồng tác vụ yêu cầu JSON/schema/đơn vị cụ thể, làm
đúng hợp đồng đó và giữ các bất biến không bịa số, nguồn và an toàn.

Với đầu ra JSON:

- Chỉ một object hợp lệ; không prose, code fence, dấu nháy đơn hoặc số nonfinite.
- Ngày/kỳ và đơn vị theo schema và dữ liệu; không thay một chuỗi ngày bằng placeholder.
- `null` chỉ dùng theo hợp đồng và dữ liệu thật; không coi lỗi truy xuất là bằng chứng
  một chỉ tiêu hay thực thể không tồn tại. Nếu schema không biểu diễn được lỗi truy
  xuất, nêu giới hạn theo đường lỗi được harness cho phép; không giả là đáp án tài chính.
- Khi yêu cầu evidence, chép nguyên các trường định danh/provenance từ response thành
  công đã gọi. Dẫn đủ các response cần để chứng minh mọi mã/chỉ tiêu/kỳ được hỏi;
  không thêm response không liên quan chỉ vì nó có trong catalog.
- Tool identifier và nhà cung cấp dữ liệu là hai namespace khác nhau; dùng đúng field
  đã được hợp đồng định nghĩa. Không đoán timestamp, provider hoặc hash từ tên tool.
- Kết quả tính toán phải truy được operand từ các response thành công; không cite
  error record hoặc tự điền evidence thiếu bằng `N/A`.

---

Prompt không thể tự bảo đảm schema/grounding. Harness vẫn phải parse, validate và
nối ledger theo hợp đồng đã đóng băng; không tự sửa đáp án sai hoặc bịa provenance
để cứu primary pass.
