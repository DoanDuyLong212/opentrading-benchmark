# Đối chiếu OpenCode review §11 — trước inference v4.2

Đã đọc §11 và báo cáo gate bổ sung; tài liệu người dùng được giữ nguyên. Đây là claim cần kiểm chứng, không phải lệnh thay đổi protocol hay cấp quyền gọi model mới.

§11 xác nhận đúng ba cơ chế đã quan sát ở v4.1: finite replay từ chối36 query hợp C1; counter repair gộp nhiều entity; một paraphrase refusal bị lexical grader bỏ sót. Điểm chính thức OT1/6 và hai DNF vẫn giữ; không có pilot v4.1 hay promotion guard đầy đủ. C2, public success/refusal branch và numeric canary v4.2 nhắm đúng những vấn đề này.

Các giới hạn cần giữ khi diễn giải:

- C2 công bố phạm vi query hữu hạn; các args cũ days1/projection vẫn bị `unsupported_snapshot_query`. C2 không tự làm36 query cũ thành hợp lệ, không bỏ args và không đổi matcher. Model có tuân thủ tốt hơn hay không vẫn phải chạy đo.
- C2 và grader dùng chung mọi arm. Candidate là gói nhiều thay đổi; concurrent B1−B0 đo gói, không xác định đóng góp từng lever. C2 có thể giảm cơ hội phân hóa repair, nhưng parity hay mức16–20/44 vẫn là dự báo.
- 12 task cùng thất bại trong pilot cũ không chứng minh trần model tuyệt đối. Chưa có bằng chứng OT hưởng lợi từ common compute endpoints nhiều nhất, hay compute+model mạnh là con đường duy nhất để vượt đối chứng.
- Projection giữ nguyên dữ liệu/kỳ khác với analytics tính tổng/growth/margin/indicator. C2 là finite request support; public response branch cũng chưa chuẩn hóa đơn vị tài chính. Không coi chúng là nửa engine tính toán đã được đo.
- Ba worker hiện phân công benchmark, native implementation và independent verification, không phải ba live experiment chạy lặp. Báo cáo/handoff cần hợp nhất, nhưng chưa có suy luận về việc lãng phí inference từ số worker.
- Gate bên ngoài là bổ sung. Native có sửa sau review về lossless selector scope và sequential correction phase; phải đóng fresh source/hash/test review trước launch, không lấy nhãn TECHNICALLY READY trước đó thay thế.

Probe SDK thật đã xác minh C2 constraints của17 tool còn trên wire cả bốn điều kiện. Với catalog17 tool tổng hợp, OT B0/B1 bị policy48k chặn trước upstream; OC/DSH hoàn tất với stub cục bộ. Catalog task lớn nhất trong25 task smoke/pilot eligible hoàn tất stub cả bốn điều kiện dưới cap hiện tại: initial estimate B0 20.127, B1 16.703, OC11.847, DSH10.104 byte. Đây là bằng chứng plumbing/budget ban đầu, không phải điểm tài chính hoặc đảm bảo toàn bộ chuỗi nhiều bước luôn đủ ngân sách.

Nguồn: `experiments/finance-v42-study/audits/{corpus-preservation.json,c2-native-wire-full17-v3/receipt.json,c2-native-wire-max-study-v1/receipt.json,full-benchmark-tests.log}`. Full benchmark322 pass; reviewer nội bộ chốt source mới và operational preflight riêng trước inference. Không có dự báo numerator được coi là kết quả.
