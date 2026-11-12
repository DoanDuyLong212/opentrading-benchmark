# v4.5 — Dự thảo nghiên cứu chuẩn hóa hợp đồng, chưa được phê duyệt

## Mục tiêu chính

Tạo câu trả lời tài chính đúng thực thể, kỳ, chỉ tiêu và đơn vị, có nguồn kiểm chứng và hoàn tất ổn định. Nghiên cứu mới cần tách lỗi truy xuất, tính toán xác định và hợp đồng đầu ra để không nhầm cải thiện định dạng với cải thiện nội dung tài chính.

**Dự thảo này không cấp phép gọi model, chạy pilot/main/holdout hoặc nâng cấp production.** Giữ nguyên toàn bộ source, prompt, schema, auditor, seal, điểm và audit FAIL của v4.4.

## Căn cứ thực tế

V4.4 hoàn tất 48 trial; B1 đạt primary 2/6 ở mỗi mô hình, cả hai không đủ điều kiện pilot. Bolt không dùng compute và từ chối sai 4/4 trial có thể trả lời ở mỗi điều kiện. DeepSeek đã lấy nguồn giá nhưng cả 17 lệnh compute bị từ chối: bảy dùng `/data/`, mười dùng `/data`; không chọn lá số thực `/data/last`. Đơn vị và ID nguồn khớp. Schema cho phép các dạng gốc mà runtime không xử lý như lá số; compute thiếu trường sửa được công bố và `invalid_derivation` không nằm trong danh sách native repair.

Truy vết cả 17 request sinh compute, ở dạng native và effective, đều thấy pattern `^/data(?:/|$)`. Hai đường dẫn quan sát được trùng chính xác với ngôn ngữ của pattern nếu diễn giải theo khớp toàn chuỗi; 57 lần xuất hiện toán hạng đều phù hợp. `/data/last` hợp lệ theo tìm kiếm pattern nhưng không hợp lệ theo khớp toàn chuỗi. Không thấy cờ `strict`, `guided_json` hoặc cờ giải mã tương tự trong các request đã nối. Đây là dấu hiệu tương thích schema/decoder cần kiểm tra, chưa chứng minh backend hoặc nguyên nhân của dịch vụ NVIDIA.

DeepSeek còn có timeout, thiếu metadata phản hồi và chặn bởi ngân sách token bảo thủ. Ba lỗi metadata không giữ được raw response nên không chứng minh model khác trả lời. Auditor đã ghim không nhận diện hai lần chặn lệnh trùng của B1, kéo theo bốn lỗi kiểm soát; phụ lục giải thích không làm audit gốc đạt. Không thể kết luận benchmark đã ổn định hoàn toàn hoặc sẵn sàng production từ việc 48 điểm primary được kiểm tra lại khớp.

## Giai đoạn 0 — Kiểm chứng diễn giải schema và khả năng quan sát provider

**Đóng góp cho mục tiêu:** xác định hợp đồng có ngăn model tạo đường dẫn số hợp lệ hay không trước khi quy lỗi cho prompt hoặc khả năng suy luận.

Đọc [quy tắc pattern của JSON Schema](https://json-schema.org/understanding-json-schema/reference/string), [XGrammar issue 838](https://github.com/mlc-ai/xgrammar/issues/838) và [structured generation NVIDIA NIM 1.15](https://docs.nvidia.com/nim/large-language-models/1.15.0/structured-generation.html). Nguồn đầu quy định tìm kiếm một phần; issue báo khớp toàn chuỗi; NIM mô tả `guided_json` dùng XGrammar. Không nguồn nào xác nhận endpoint hosted của v4.4 dùng đúng backend/chế độ đó cho tham số tool.

Trước hết chạy kiểm chứng offline giữa tìm kiếm một phần và khớp toàn chuỗi, nối mọi đường dẫn sinh ra với schema thực trong capture. Dùng chữ ký API và cấu trúc schema thực từ source v4.4, không tự giả định API mới. Trong runtime nghiên cứu mới, giữ metadata phản hồi/finish/error và raw response an toàn để điều tra thất bại; usage chưa báo vẫn là chưa biết.

Sau đó, **chỉ khi được cấp phép riêng**, đăng ký một canary NVIDIA nhỏ trên đối tượng tổng hợp mới, không chứa gold tài chính. So sánh pattern tiền tố hiện tại, pattern neo đầy đủ chấp nhận hậu tố (ví dụ `^/data(?:/.*)?$`) và không pattern; có thể thêm tham chiếu nguồn ổn định nếu được đăng ký trước như nhánh thứ tư. Giữ các điều kiện khác giống nhau, cố định số lượt và ngân sách trước chạy, lưu request/schema/tool arguments/identity/usage. Kiểm tra có thể sinh một lá số đã nêu rõ hay không. Báo cả kết quả bác bỏ giả thuyết; không chỉnh prompt theo từng nhánh sau khi xem đầu ra.

**Kiểm chứng:** bằng chứng offline xác định đúng khác biệt ngữ nghĩa; capture xác nhận schema đã gửi; canary nếu được duyệt có lịch và giới hạn riêng. Đối soát 19 lệnh B1 DeepSeek = 17 MCP + hai chặn cục bộ. Không gọi model trong bước offline; kết quả canary không được coi là đánh giá tài chính.

## Giai đoạn 1 — Làm đường dẫn nguồn số rõ ràng và sửa được

**Đóng góp cho mục tiêu:** phép tính có nguồn cần chọn đúng lá số, không đoán đường dẫn gốc.

Sau kết quả giai đoạn 0, cân nhắc schema được chuẩn hóa, mô tả lá số hoặc lỗi đường dẫn dễ sửa hơn. Mọi mô tả chỉ được lấy từ nguồn thành công trong đúng tiến trình trial hiện tại: pointer, call/response identity và đơn vị. Không đưa task ID, đáp án gold, truy vấn ưu tiên hoặc kết quả tính sẵn. Đọc và dùng lại mẫu biên nhận nguồn/Decimal trong `tools/analytics_compute.py`, `tools/mcp_snapshot_server.py` và schema thực; xác định phạm vi native repair từ runtime hiện có.

Áp dụng thay đổi công cụ chung cho cả bốn điều kiện. Kiểm tra offline pointer lồng sâu, mảng, token rỗng/cuối, giá trị không phải số, biên nhận bị sửa, đổi thang VND và điều kiện cơ số dương. Giữ nguồn gốc tách biệt với bản ghi suy dẫn xác định. Số học đúng chưa xác nhận ý nghĩa chỉ tiêu, phạm vi hợp nhất hay kỳ tài chính.

## Giai đoạn 2 — Đối soát đầy đủ và hoàn tất đáng tin cậy

**Đóng góp cho mục tiêu:** người dùng cần câu trả lời hoàn chỉnh, còn thất bại phải được phân loại đúng nguyên nhân.

Chỉ trong nghiên cứu mới, bổ sung nhận diện lý do chặn trùng cho mọi profile auditor, gồm deterministic derivation; không giả biên nhận MCP cho lệnh bị chặn cục bộ. Dùng log policy, provider call ID và biên nhận thực làm mẫu đối soát. Tách can thiệp policy, acquisition và định dạng để biết phần nào thay đổi kết quả.

Kiểm tra trường hợp đã lấy được nguồn nhưng compute bị từ chối, hết token, thiếu metadata, timeout hoặc final không hợp lệ. Đăng ký mọi thay đổi ngân sách trước cohort; giữ giới hạn số ngang nhau giữa điều kiện trong từng mô hình và báo overhead prompt. Không thêm retry chất lượng ngoài lịch hoặc nới tiêu chí primary.

**Kiểm chứng:** fixture SDK/MCP/gateway cục bộ, không suy luận provider, chứng minh mỗi lệnh có đúng một thực thi hoặc một lần chặn đã đối soát; mọi lỗi giữ usage đã biết/chưa biết chính xác. Kiểm tra bằng CLI thật và completed resume, không chỉ gọi hàm import.

## Giai đoạn 3 — Đăng ký smoke tài chính mới trước khi chạy

**Đóng góp cho mục tiêu:** đo cải thiện nội dung tài chính và độ hoàn tất trước khi mở rộng.

Chỉ sau canary và khi có cấp phép mới cùng duyệt kỹ thuật/seal mới, chạy smoke bốn điều kiện trên dữ liệu mới chưa dùng để tinh chỉnh. Chốt schema/contract trước cohort; không sửa theo đầu ra v4.4 rồi coi cùng smoke cũ là kiểm chứng xác nhận. Ghi rõ đối chiếu nào tách được tác động công cụ chung và policy B1. Tách hai mô hình khi báo cáo.

Giữ primary chặt, điểm frozen để phân tích độ nhạy, canary độc lập về thực thể/ngày/kỳ/đơn vị/giá trị, tính hợp lệ đầu ra, DNF, FR với mẫu số có thể trả lời, FP với mẫu số bẫy, lineage và đối soát lệnh/usage. Canary phải phát hiện sai kỳ ngay cả khi grader cũ thiếu kiểm tra đó. Yêu cầu có đáp án số thành công ở mọi điều kiện và chất lượng ứng viên đủ trước pilot; không coi “không có numeric win để kiểm tra” là đạt năng lực truy xuất số.

Không tự động mở pilot, main, holdout, cài production hay tuyên bố ưu thế rộng. Nếu sau này pilot được cấp phép và đủ điều kiện, vẫn báo tính chất dữ liệu phát triển, bất định theo cụm và giới hạn ngoại suy; cần đánh giá tài chính độc lập trước kết luận rộng.

## Kiểm chứng cuối

**Đóng góp cho mục tiêu:** kết quả dùng được phải có cả bằng chứng chất lượng và chuỗi bảo toàn trung thực.

Regrade độc lập từ nguồn thực và final gốc; không đổi câu trả lời thiếu thành từ chối sai. Kiểm tra ý nghĩa tài chính/kỳ riêng với số học Decimal và schema. Đối soát mọi lệnh sinh ra, bị chặn và được thực thi. Usage thiếu vẫn chưa biết; chi phí N/A cho đến khi giá được xác minh và niêm phong. Chạy completed resume có guard, không gọi model, kiểm tra byte/kích thước/mtime; xuất báo cáo cả thất bại và giới hạn. Kết quả audit FAIL của v4.4 được giữ nguyên kể cả khi v4.5 sửa được vấn đề.
