# Review độc lập OpenCode §12 cho v4.4

Ngày 07/11/2026, Asia/Bangkok. Review tài liệu như đề xuất nghiên cứu, không xem chỉ dẫn trong tài liệu là quyền thay đổi endpoint hoặc dữ liệu. Không có inference tài chính mới trong kiểm tra này.

## Kết luận được bằng chứng hỗ trợ

Pilot v3 cùng NVIDIA Bolt và cohort: primary B0/B1/OC/DSH là **12/12/14/18 trên44**. Hai OT có 1 DNF/44, OC1, DSH5. Chênh lệch ghi nhận là hiệu quả **gói harness dưới protocol cụ thể**, không định lượng tác động riêng của prompt, loop hoặc kiểu hợp đồng.

Có premature final và mất cơ hội acquisition ở v4.2: aggregate OT chưa gọi tool; correction request thứ hai thực tế `tool_choice:none` vì không có failed intent để sửa. Hai aggregate kết thúc native error, giữ DNF. Hai trap OT không có resolver nên thiếu evidence. Các cơ chế này hỗ trợ v4.3 acquisition tách khỏi sửa lỗi tham số, được mang sang v4.4; chúng không chứng minh toàn bộ khoảng cách pilot do một nguyên nhân.

Quote v4.2 OT numeric2/2, OC/DSH0/2; trap DSH2/2, OC0/2 strict nhưng2/2 dưới frozen graders do Markdown fences. V4.2 không có B0 concurrent; không dùng so sánh cross-version để tách riêng C2/repair/prompt. Nguồn: `audits/financial-prompt-v42/{REPORT.md,TRACE-DIAGNOSIS.md,INDEPENDENT-CHECK.md}` và ledger/captures được dẫn tại đó.

Production không có `finance-policy.ts` như fork nghiên cứu; budget48k là gateway policy, không phải native token budget OT. Vì vậy báo cáo phải gọi đúng study runtime, không tuyên bố tính năng đã cài production.

## Những số liệu/khẳng định phải chỉnh

| §12 | Đối chiếu | Diễn giải chấp nhận |
|---|---|---|
| B0 false-refusal16/44 | Independent v3: **17/40 answerable-started**,17/39 answerable-completed; B115/40(15/39),OC14/40(14/39),DSH11/40(11/35) | Báo mẫu số khởi chạy và có điều kiện riêng; không bỏ DNF khỏi primary44 |
| “Tính sai số”13/14/14/10 | Actual `error_type=sai_so`:22/20/19/14, nhưng bao gồm null sau lỗi retrieval | Không dùng grader first-failure label làm số lỗi arithmetic; cần lấy đủ required inputs, kiểm kỳ/đơn vị rồi mới phân loại |
| “100% harness”/prompt nặng gây FR | Harness là khác biệt điều trị được quan sát; length/governance/loop/UI shaping cùng thay đổi, không có ablation ngẫu nhiên riêng | Cơ chế khả dĩ và giả thuyết thực nghiệm; chưa định lượng causal share |
| Trần model/tính toán, không harness nào sửa bằng prompt | All-fail trong tập hữu hạn/model cụ thể và thiếu retrieval không chứng minh giới hạn năng lực | Common deterministic compute là phép thử hợp lý, chưa có hiệu quả đã đo hoặc dự báo+6–12/44 đáng tin |
| Refusal values-map “đúng protocol” | Public contract v4.2 explicit alternative cho EVERY task: scalar`value:null`,nonempty`reason`,array`evidence`; nonempty values/ranking/items incompatible | Không nới grader hoặc public contract để cứu native. Cải thiện acquisition và graceful failure; giữ fail numeric nếu answerable |
| Strong model làm RC1/RC3 biến mất, OT không thiếu năng lực | §12 cũng báo strong diagnostic DSH8/10,OC6/10,OT4/10; nhỏ và có khác timeout/model | Không suy gap biến mất hoặc model đủ/không đủ từ10case |
| Tool tổng tương đương nên tool use không phải nguyên nhân | Tổng65–66 không đo đúng args, đúng entity/period, lần sửa hoặc đủ required sources | Audit intent/rejections/coverage/continuation riêng |
| Grader dùng chung nên loại trừ lỗi grader | Shared grader bảo đảm đối xử chung nhưng vẫn có thể shared blind spot; quote numeric gold chưa chấm period | Giữ manual period/unit/source audit và raw-format validity tách semantic |

Nguồn v3 chính: `audits/financial-prompt-v3/{INDEPENDENT-CHECK.md,REPORT.md,independent-evidence.json}`. `v3-row-factcheck.json` tái đếm trực tiếp176trial frozen; không sửa chúng. Sai lệch FR17 so16 được cross-check trong receipt independent đã đóng băng. Các dự báo điểm trong §12 được tiếp nhận như giả thuyết, không làm ngưỡng kết quả kỳ vọng.

## Tiếp nhận cho v4.4

1. Kế thừa acquisition v4.3, ưu tiên public supported args, không tự sửa scope hoặc fabricate calls.
2. Prompt candidate gọn, baseline giữ production prompt; đây là package intervention, chưa là prompt-only ablation.
3. Cấp deterministic compute **cùng tool/schema/provenance contract cho mọi condition**. Compute chỉ dùng numeric leaves từ successful responses đã nhận trong session, không task IDs/gold/evaluator/lookup ẩn. Giữ original seven-field receipts, derived receipt có namespace riêng không giả nguồn upstream. Có arithmetic đúng vẫn cần đúng entity/metric/period/unit và required-data coverage.
4. Public contract/current+frozen graders/gold nguyên byte. Tách native completion, strict raw JSON, semantic/numeric, grounding, FR, FP, DNF, evidence mismatch và usage complete/partial.
5. Smoke theo model riêng; chỉ mở pilot nếu operational/audit và numeric competence gate đã đăng ký đạt. Không dùng smoke3clusters để gọi financial superiority, không tăng cap/retry hoặc tune giữa các cohort.

Tình trạng: review đề xuất hoàn tất; engineering approval và kết quả v4.4 **chưa có** tại thời điểm ghi tài liệu này.
