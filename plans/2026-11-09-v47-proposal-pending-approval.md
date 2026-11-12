# Đề xuất v4.7 — chờ người dùng duyệt, chưa triển khai

Bản nháp phục vụ review v4.6-update. Kết quả smoke/pilot mới chưa có; không coi dự kiến là kết quả. Sau khi hoàn tất thí nghiệm, cập nhật quyết định ưu tiên bằng kết quả đã audit. Không chỉnh v4.7 trước khi người dùng duyệt.

## Vấn đề đã có bằng chứng

Super R3 v4.6: B1 strict18/24 và grounded18/24, bằng B0/DSH về grounded; OC13/24 strict,14/24 grounded. Audit chưa đạt nên đây là diagnostic, chưa chứng nhận vượt trội. Sáu B1 primary failures gồm2precision,1missing-period refusal lexical,1unit-label/canonicalizer,1source-chain serialization,1DNF. Không quy toàn bộ thành lỗi format. 21/24 trial có native contract rejection, trong đó20receipt-rejection;16primarywins vẫn được raw grader chấp nhận. B1107request so với B0/DSH78,OC72. B1 hệ thống ngắn2641ký tự nhưng toolinventory14369ký tự/6tools so với OC/DSH~7930/3tools; các con số này chỉ là sample growthr1, không đại diện mọi task. Mục tiêu là giảm sai hợp đồng và chi phí do lỗi có thể quan sát, không thêm prompt để đoán đáp án.

Các sửa instrumentation/contract tối thiểu đang thuộc v4.6-update, không tính chúng là tính năng v4.7. Mọi claim về tác dụng chờ thí nghiệm mới; không retroactively cứu điểm R3.

## Phạm vi sản phẩm đề xuất

1. **Một giao diện tham chiếu và trạng thái tính toán rõ ràng.** Chọn một namespace public cho source call và derived call; bridge typed nội bộ sang notebook/localref không để model tự đoán. Schema/description ghi rõ input nào là sourceUUID, JSONPointer hay localref. Replay giữ origin generation/session/turn bất biến. Không autocorrect tool typo hay tạo receipt khi lỗi.
2. **Kiểu dữ liệu tài chính và phép toán.** Typed claim gồm entity,scope,period/as-of,value,unit,source receipts và derivation. Phân biệt stock/flow, reporting period/date, %,ratio,percentage point,money/share; conversion có dimension/scale rõ. Không cho phép thay unit gốc bằng nhãn gần giống; tính conversion từ nguồn và ghi derivation. Schema chỉ mang cấu trúc không chứa gold/expected numerical answer.
3. **Tạo đáp án từ claim đã kiểm tra.** Cân nhắc native finalization API nhận claim có evidence; serializer xuất JSON/nguồn/kỳ/precision thống nhất, deterministic từ dữ liệu model đã chọn và tính. Nếu thiếu hoặc mâu thuẫn thì báo lỗi cụ thể một lần; không đoán/rescue nội dung. Đây là thay đổi sản phẩm có thể tạo lợi thế serialization: báo rõ, ablate riêng và giữ raw-native endpoint công bằng; không bí mật postprocess OC/DSH.
4. **Context gọn theo trạng thái, giữ khả năng truy hồi.** Tách hướng dẫn chọn nguồn, tính và kết luận; chỉ giữ tool/task facts cần thiết, cho read_result lấy lại dữ liệu đầy đủ khi cần. Không drop provenance/failedcalls/period hay user-memory conflicts. So sánh inventory động với inventory đầy đủ, kiểm không tool mất khả dụng. Trước tiên bỏ lặp và schema verbosity, không cắt bừa context.
5. **Một chính sách sửa lỗi có giới hạn.** Phân biệt schema/finance-policy/provider failures. Repair chỉ cung cấp trường lỗi, expected type và reference thật, không hint đáp án. Không retry output vì điểm kém, không tự nâng cap. Provider retries chỉ eligibletransport trong caps đã đăng ký; DNF và usageunknown giữ nguyên.
6. **Memory riêng và có thể kiểm chứng.** Không suy rộng stateless tài chính sang memory. Đề xuất retrieval/update/delete/conflict/temporal counterfactual tests, old-user-state isolation, new-session recall, financialfacts expiry, nguồn private/user vs market-source phân biệt. Canonical MAIN vẫn212case=200financial+12memory (<=250), không thêm task tùy tiện. MINI chỉ sơ bộ; xác thực schedule memory riêng trước inference.

## Học từ OC/DSH có kiểm soát

Ở oldR3, OC/DSH thường serialize resolver+quote sourcechain đầy đủ hơn; DSH scale2/2 trong khi OT-fin1/2DNF. OT mạnh hơn ở growthperiod alignment: B1/B02/2,OC0/2,DSH1/2. Aggregate cả8trial đều failprecision nên không có bằng chứng OC/DSH tính tốt hơn. Học cách hạn chế publicsurface và kết thúc sạch; giữ thế mạnh period/entity/source checks. Không chép prompt thiếu provenance hay bỏ validator để tăng completion. Xem actual native/effective captures, không dùng tên harness như lời giải thích.

## Thiết kế thực nghiệm sau duyệt

- Đóng engineering v4.6-update và giữ nguyên toàn bộ manifest/source/grades trước khi tạo candidate mới. Xem failure taxonomy mới để quyết định phần nào còn đáng làm.
- Mỗi thay đổi độc lập: R0=v4.6-update; R1=reference bridge; R2=typed financial computation; R3=claim serializer; R4=context reduction; memory là track riêng. Nếu nguồn lực hạn chế dùng staged ablation, không dồn thay đổi rồi không biết tác dụng.
- Dùng hai NVIDIA routes đã được phép; report riêng Super(private returned alias checkpointUNVERIFIED) và DeepSeek. Không pool model. Model/sampling/clock/payload/caps/calculator/isolation giống nhau trong từng so sánh; OC/DSH native behavior có thể khác nhưng capabilitydisclosure đầy đủ.
- Engineering adversarial suite: forged/duplicate receipt, wrong-generation replay, identical parallel calls, schema-invalid/unknown tools, missing period vs query unsupported, source mismatch, conflicting numbers, reversed growth/ratio, money/share ambiguity, partial SSE, truncated usage, stop/resume. Actual native SDK/MCP/wire, không chỉ Python mock.
- DEV smoke trước; dùng pilot mới hợp lệ nếu đã xem sâu pilot cũ để tránh gọi nó là dữ liệu chưa nhìn. MAIN/holdout không dùng tune; không tự chạy theo proposal này. Khi được phê duyệt lịch mới, đăng ký family/split/source snapshots và tiến hành blind final comparison.
- Co-primary strict grounded và grounded financial cùng định nghĩa MAIN; rawformat/nativeaccepted/numerical diagnostics tách riêng. Secondary: family/stable2/2,DNF,FR,FP,evidence/requireddata,requests,latencyallattempts,input/outputknownlowerbounds+unknownusage,repair counts. Manual all-armwins chỉ remove, không rescue; frozen graders báo riêng.
- Giữ qualityguard hiện có, zero accepted fabrication và không regress DNF/FR/FP/evidence. Superiority cần vượt từng B0/OC/DSH ở cả hai co-primary trong cohort phù hợp; pilot+3/44 là qualification, không tự chứng minh thống kê/main tổng quát. Báo paired task-cluster uncertainty/multiplicity, tác vụ chung snapshot không coi độc lập hoàn toàn.

## Thứ tự thực hiện và tiêu chí dừng

A. Review kết quả v4.6-update, xác định lỗi còn lại bằng trace và nguồn; hoàn tất threat/measurement review.
B. Thiết kế reference/claim interfaces, backwardcompatibility và migration; người dùng duyệt scope trước implementation.
C. Implement từng repair, meaningful negative tests, độc lập actualwire/pins approval.
D. Freeze prospectively; chạy smoke theo lịch, giữ mọi trial/DNF; lỗi instrumentation thì dừng không patch cùng run.
E. Diagnostic pilot và all-arm review; so với R0/OC/DSH bằng endpoint thực.
F. Nếu không cải thiện nội dung hoặc tốn request/latency đáng kể, giữ bản tốt hơn và giải thích ablation; không tự promote.
G. Báo cáo và xin quyết định MAIN/memory schedule riêng khi cần. Không hứa thắng100%, không production install tự động.

Ước lượng: engineering2–3ngày, validations0.5–1ngày, smoke/pilot1–2ngày tùy provider. Đây là ước lượng chưa đo throughput mới. Ưu tiên measurement integrity và fix reference/completion trước, không tối ưu nhiều nhánh đồng thời trong hạn1tuần.
