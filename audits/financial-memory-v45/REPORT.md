# Kết quả v4.5: MINI memory hoàn tất, chưa đủ điều kiện chạy tài chính tiếp

Ngày 09/11/2026, Asia/Bangkok. **OT chưa chứng minh vượt OpenCode và DSH về chất lượng tài chính.** MINI đã hoàn tất24/24 episode, được review độc lập toàn bộ13 automatic wins, nhưng instrumentation audit FAIL. Kết quả dưới đây là chẩn đoán đã đối chiếu nội dung, **chưa được chứng nhận để promotion hoặc suy ra thắng benchmark**. Không mở financial smoke96/model, pilot176/model hay MAIN. Các manifest đó được giữ nguyên và đặt PAUSE sau quyết định gate.

## Bản OT và phạm vi đã hoàn thành

Product `/home/doanlong/OpenTrading` ở merged HEAD5705ada91033b05a1dd77f00eae39525b89e45bb, bao gồm upstream1737b93ee0082f6f4d6b1278c41c92a62b74ed2c.21 patch được cài qua installer đã review với backup/hash guard;1136 file ngoài phạm vi giữ nguyên.234 package và15011 file dependency khớp candidate, Bun1.4.4 dùng binary/SHA riêng, global giữ nguyên. Typecheck PASS. Full Python host cuối537/537 PASS; kết quả này không thay thế kiểm chứng mọi schema thực tế.

Phạm vi qualification là headless benchmark. Broad native giữ1881PASS/2SKIP/6FAIL/1ERROR; TUI candidate113PASS/1FAIL so stock108PASS/6FAIL, có lỗi chung. Không gọi đây là bản sản phẩm100%không lỗi hay toàn suite xanh. Original v3 dùng symlink dependency product nên môi trường chạy lại đã đổi; kết quả/capture cũ giữ nguyên. Isolated v42/v44 giữ dependency đã seal. Chi tiết merge/preservation trong các handoff và receipts.

Canonical MAIN212 task danh nghĩa=200financial cũ+12memory, dưới trần250; financial MAIN183eligible,17quarantine. Financial pilot22eligible×2repeat×4arm=176/model, mẫu số44/arm, **chưa chạy**. MINI chỉ1task memory pilot+2DEV, mỗi task một lần×4arm×2model=24 episode, **mẫu số3/arm/model**. Không chạy bất kỳ câu MAIN memory nào trong MINI.

## Metrics chính: chẩn đoán đã review, N=3 mỗi arm/model

`Strict` yêu cầu đáp án tài chính/nguồn/state đúng và raw public JSON hợp lệ. `Financial` yêu cầu đúng nội dung tài chính và nguồn, chấp nhận một JSON object hoặc sole JSON fence; không cứu prose. `Memory-state` là co-primary kết hợp financial correctness với đúng trạng thái người dùng/provenance/native persistence. Nó không phải điểm lưu bộ nhớ thuần túy. DNF được giữ trong mẫu số.

### NVIDIA Super endpoint đã được người dùng chấp nhận

| Arm | Strict | Financial | Memory-state | Raw-format | DNF |
|---|---:|---:|---:|---:|---:|
| OT memory bật | 2/3 | 2/3 | 2/3 | 3/3 | 0/3 |
| OT memory tắt | 1/3 | 1/3 | 1/3 | 2/3 | 0/3 |
| OpenCode | 1/3 | 1/3 | 1/3 | 1/3 | 1/3 |
| DSH | 1/3 | 2/3 | 2/3 | 1/3 | 0/3 |

### NVIDIA DeepSeek v4.1 Flash

| Arm | Strict | Financial | Memory-state | Raw-format | DNF |
|---|---:|---:|---:|---:|---:|
| OT memory bật | 1/3 | 2/3 | 2/3 | 1/3 | 0/3 |
| OT memory tắt | 1/3 | 1/3 | 1/3 | 1/3 | 2/3 |
| OpenCode | 0/3 | 2/3 | 2/3 | 0/3 | 0/3 |
| DSH | 0/3 | 2/3 | 2/3 | 1/3 | 0/3 |

OT memory bật đạt Financial2/3 với cả hai model; **hòa DSH ở cả hai**, và với DeepSeek cũng hòa OpenCode. Lợi thế strict/raw-format không phải lợi thế tài chính. Chênh lệch2so1 ở vài cell N3 có DNF và lỗi hạ tầng không chứng minh superiority hay quan hệ nhân quả của memory.

Super gọi endpoint công khaiVL theo yêu cầu nhưng trả private/nvidia/nemotron-3.5-super-120b-a12b; checkpoint/VL tương đương chưa xác minh, original identityFAIL và user-authorized route-v2 giữ nguyên. Không đổi tên response để coi là cùng checkpoint. MINI cả hai model dùng temperature1/top_p.95; stateless DeepSeek đã đăng ký0/1. Không so sánh ghép cặp hoặc pooling hai track/model.

## Metrics phụ và usage

Tổng trong bảng là **cả3 episode gồm seed+query**, không phải latency của một đáp án. Tokens là observed, không bù usage thiếu bằng0; phần reasoning đã nằm trong output, không cộng lần nữa. Tỷ lệ usage complete là theo episode.

| Model | Arm | Calls mọi turn/query | Input observed | Output observed | Thời gian active tổng(s) | Usage complete |
|---|---|---:|---:|---:|---:|---:|
| Super | OT memory bật | 22/14 | 200,858 | 16,689 | 229.8 | 3/3 |
| Super | OT memory tắt | 18/11 | 116,911 | 11,326 | 154.6 | 3/3 |
| Super | OpenCode | 12/4 | 59,077 | 5,636 | 332.8 | 2/3 |
| Super | DSH | 17/9 | 87,774 | 6,417 | 134.6 | 3/3 |
| DeepSeek | OT memory bật | 18/11 | 162,149 | 11,739 | 783.4 | 3/3 |
| DeepSeek | OT memory tắt | 13/7 | 86,266 | 8,091 | 774.6 | 1/3 |
| DeepSeek | OpenCode | 13/5 | 64,510 | 5,226 | 422.4 | 3/3 |
| DeepSeek | DSH | 13/5 | 60,327 | 5,151 | 390.1 | 3/3 |

Tổng operational126 upstream attempts trong trần288, không có transport retry thực tế trong cohort.123 attempt có usage quan sát,3 attempt usage thiếu dẫn đến3 episode partial. Observed837872input+70275output tokens; không phải tổng usage thực đầy đủ. Reservation3170304tokens của3 attempt unknown là bookkeeping bảo thủ, **không phải token đã đo/chi phí**. Không báo dollar cost vì không có giá/entitlement được xác nhận. Các response còn quan sát reasoning tokens dù effort none; không giả backend thinking đã tắt.

Ba DNF: Super/OpenCode update-revoke; DeepSeek/OT-memory-off update-revoke và stale-current. Gateway ghi provider_finish_reason_missing, trong đó hai attempt kéo dài khoảng240s; response không đủ finish/usage được giữ failed, không retry chất lượng. Controller21 completed không đồng nghĩa21 đáp án đúng. Query chưa bắt đầu do DNF ở seed được tách khỏi query đã dispatch nhưng thiếu usage.

Frozen metrics ghi0unauthorized writes,0stale-value reuse. Đây không chứng nhận injection resistance: MINI không chạy injection case; injection MAIN chỉ offline validation. Thuật toán metrics chưa có bằng chứng vượt dài hạn qua compaction/many-session/adversarial memory. Thao tác ghi/đổi/xóa seed được controller thực hiện theo typed user consent, không phải chứng minh model tự học và tự ghi memory. Traces không khai receipt vẫn có thể hợp lệ một cách rỗng; positive memory uptake cần exposure/native-context riêng.

## Điều tra từng construct

1. **Context cùng phiên:** cả8arm/model cells đọc/xếp ROE đúng: HDB25.41 >TPB18.53 >ACB17.56 >VPB15.49 >STB10.34, cùng nguồn peer_compare/kỳ2025. Replay/context nhận diện đúng user/assistant history; không phải câu hỏi memory dài hạn.
2. **Update/revoke qua phiên mới:** rule ROE>20% hiệu lực và thu hồi điều kiện cũ loại toàn bộ ngân hàng cho kết quả chỉ HDB. OT-on đúng ở cả hai model; các đối chứng có cả đúng và DNF. SuperOT-off lưu rule hiện hành đúng nhưng query notebook nguyên chuỗi tiếngAnh không phải substring của fact tiếngViệt nên nhận facts[]. Đây là hành vi query/filter đã công bố, không phải database mất dữ liệu; cần cải thiện giao diện retrieval và đo exposure tách persistence. Với các win, reviewer kiểm actual native SQLite ID/version/text và nguồn user turn.
3. **Stale/current:** cả8 episode giữ FAIL. BốnOC/DSH lấy đúng giá3898.89990234375(hoặc làm tròn3898.9) nhưng trả period2026-11-01 là snapshot date thay vì source trading date2026-10-30. Không sửa gold hoặc cứu đáp án chỉ vì numeric đúng. BốnOT-on/off bị lỗi compile schema trước thực thi yf_commodities; có refusal/DSML text/DNF thay đáp án tài chính hợp lệ. Không dùng giá spot hay giá nhớ thay futuresGC=F.

## P0: lỗi schema benchmark làm OT bị bất lợi thực

Generator equivalent_schema dùng Python re.escape tạo\- cho ticker/date và\ khoảng trắng cho tên doanh nghiệp. Python regex nhận chúng, nhưng AJV của financial policy OT dùng JavaScript RegExp với cờUnicode và báoSyntaxError. Ví dụ captured patternBTC\-USD nằm ở nhánh khác của schema yf_commodities. Validator compile toàn schema nên **ngay cả callGC=F hợp lệ cũng bị chặn** trước MCP; đổi prompt hoặc bảo model sửa arguments không giải quyết malformed sibling schema.

Actual Bun1.4.4/SDK reproduction tái hiện cùngAI_TypeValidationError, trong khi nguyên arguments captured vượt Python validator.4 episodeOT stale-current có16 distinct local regex failures,0thực thiMCP yf_commodities;30 upstream attempts cả turn vẫn giữ nguyên. Đây là bug hợp đồng benchmark/schema/validator, **chưa phải bằng chứng mô tả MCP gốc sai hay mô hình kém tài chính**.

Quét offline254 task / 818 task-tool / 156 schema unique phát hiện6 schema không compile, xuất hiện ở65 task:60 MAIN,2 pilot,2 devsmoke,1 memory DEV; gồm symbol_resolve,vs_indicator_data,yf_commodities. Đây là sốtask **chứa tool schema hỏng**, không phải dự báo65 task chắc chắn fail: phụ thuộc đường gọi tool thực tế. Nghiêm trọng hơn, B1 gắn custom AJV validator còn B0 có đường JSONSchema pass-through khác; cùng arguments hợp lệ có thể quaB0 nhưng bịB1 chặn. Không thể tiếp tục phép so sánh đó rồi gọi chênh lệch là chất lượng tài chính.

## Auditor và tracing cũng chưa đủ tin cậy

Frozen audit cuối FAIL với94 errors / 20 episode:57 sampling,5 public-prompt binding,9 source-context,12 generated-call reconciliation,5 user-read-context,4 rejection proofs,1 rejection occurrence,1 native-execution binding. **Không diễn giải94 lỗi này thành94lần bịa nguồn.** Forensics xác định nhiều false positive:

- Auditor hardcodeDeepSeek0/1 trong khi MINI manifest đúng1/.95 cho mọi arm;57capture mismatches là lỗi verifier profile.
- CallBindings sortSDK IDs theo lexical thay vì actual parallel tool ordinal; đổi thứ tự haiUUID làm mất join mặc dù nguồn/context có thật.
- OpenCode JSON-quote user prompt làm newline escaped; so chuỗi nguyên văn bỏ qua wrapper grammar hợp lệ.
- Rejected MCP rows bị xử lý như source receipt; wrapped unsupported_snapshot_query không khớp nhãn lỗi cũ.

Đồng thời có **tracing defect thật**: history re-emits rejection notice nhưng stamp bằng provider index hiện tại thay vì generation gốc. Không được chỉ nới auditor để bỏ qua lỗi này. Các call peer_compare(metrics:['roe']) bị replay từ chối cũng phải phân biệt finite-capture coverage với sai tool hoặc query tài chính vô nghĩa.

Initial audit95 errors được giữ nguyên riêng; một lỗi proofmissing do audit chạy trước khi completed-resume proof được tạo. Sau khi có proof, chạy lại **cùng frozen auditor, không sửa code**, còn94. Final auditSHA72ae5a65... là bản manual review bind. Không sửa grader/source để làm cohort pass.

## Bảo toàn và quyết định gate

13 automatic wins được independent reviewer kiểm10 nhóm user facts/current rule/source/entity/period/unit/scope/math/narrative/native persistence:13 accept,0 remove,0 rescue; zero accepted fabrication trong các win đã review. Review chỉ đối chiếu nội dung, không biến instrumentationFAIL thành chứng nhận. Các failed answers và3 DNF giữ nguyên trong mẫu số3/arm/model.

Exact completed driver resume với constructor interceptor tạo0 model/gateway/episode calls; SHA/size/mtime mọi episode/capture không đổi. Sau khi gắn manual review, chạy lại exact completed CLI vẫn0calls, cùng proofSHA và review binding, summary được tính lại từ immutable rows.2039 protected source/config/task/protocol/grader fingerprints khớp manifest; stateless seal giữ nguyên, financial stateless trials0. Stored legacy results giữ nguyên; caveat dependency symlinkv3 đã nêu.

Gate decision: **BLOCKED_INSTRUMENTATION**. Sáu registered stateless run dirs đặtPAUSE với reasonpost-mini, không phải userpause bị tự gỡ. Không có scorepilot44/arm hay financialMAIN; không suy kết quả chưa chạy. Không tune, retry chất lượng, mở thêm model, holdout hoặc promote production. Đã hoàn tất review cohort và đã xóa heartbeat `review-opentrading-benchmark` theo yêu cầu.

## Kế hoạch phiên bản kế tiếp, trước khi có inference mới

Ưu tiênP0: sửa portable literal regex trong một version mới, giữ finite matching/rejection semantics. Toàn156 schema unique phải compile qua actual pinned validators; kiểm positive/negative tương đương Python/native với tickerhyphen,datehyphen,tên Việt cóspaces và Unicode. Không disableUnicode hay bỏ constraint để lấyPASS. Phân loại schema compilation là lỗi admission/hạ tầng, không gợi model sửa arguments.

P1: bind sampling theo exact manifest/track; giữ parallel tool ordinal/request/session identity; bind raw+decoded prompt bằng grammar hữu hạn; phân biệt rejected-source/read/native namespaces; ghi immutable event-origin generation ngay lúc tạo và không tái đóng dấu history replay. Fixtures phải có UUID reversed order, mixed parallel source/read/reject, reusedSDK IDs giữa sessions và native-generated error thực.

P2: làm rõ tool description/feedback notebook literal query, matching_count/total_current_count và ví dụquery ngắn; kiểm exposure/current-revoked facts riêng với persistence. Chỉ thêm semantic/token search nếu đăng ký cùng semantics cho mọi arm, không tăng quyền/seed cho OT. Ràng buộc output date vào data_time/last_t thực, snapshot as_of tách riêng. Provider incomplete stream được phân loại và giữ usagepartial; không hứa100%answers hoặc retry semantic failures.

P3: preflight actual4native arms trên toàn catalog/các schema đặc biệt, cả sampling profiles, rejection/error variants, parallel/resume/partial usage. Sinh completion proof trước final audit và chỉ seal khi independent instrumentationPASS. Giữ nguyên cohort hiện tại và manifest1–5; inference mới cần study/version/preregistration hợp lệ, không hồi tố sửa điểm. Những sửa này kỳ vọng loại bỏ failure hạ tầng đã tái hiện; **không có cơ sở dự báo phần trăm thắng hay hứa OT đánh bại OC/DSH**. Financial pilot/main giữ guard gốc và conditional user authorization; memory MINI N3 không tự promote.

## Bằng chứng để kiểm tra

- [Rollup metrics/usage](/home/doanlong/extra/benchmark/audits/financial-memory-v45/MINI-RESULTS-ROLLUP.json), [independent outcome review](/home/doanlong/extra/benchmark/audits/financial-memory-v45/INDEPENDENT-MINI-OUTCOME-REVIEW.md), [13-win review notes](/home/doanlong/extra/benchmark/audits/financial-memory-v45/MINI-MANUAL-REVIEW-NOTES.json).
- [Schema root cause và SDK reproduction](/home/doanlong/extra/benchmark/audits/financial-memory-v45/schema-forensics/REPORT.md), [inventory/repro summary](/home/doanlong/extra/benchmark/audits/financial-memory-v45/schema-forensics/FORENSIC-SUMMARY.json).
- [Auditor/tracing forensics](/home/doanlong/extra/benchmark/audits/financial-memory-v45/MINI-INSTRUMENTATION-FORENSICS.md), [next-version validation plan](/home/doanlong/extra/benchmark/audits/financial-memory-v45/NEXT-INSTRUMENTATION-VALIDATION-PLAN.md).
- [Gate decision](/home/doanlong/extra/benchmark/audits/financial-memory-v45/V45-STUDY-GATE-DECISION.json), [post-MINI preservation](/home/doanlong/extra/benchmark/audits/financial-memory-v45/POST-MINI-PRESERVATION.json), [reviewed-summary zero-call proof](/home/doanlong/extra/benchmark/audits/financial-memory-v45/reviewed-summary-zero-call-proof.json).
- Run đầy đủ: `/home/doanlong/extra/benchmark/experiments/finance-v45-study/results/financial-memory-v45-mini-20261109-preflight5` gồmmanifest,summary,memory-audit,memory-financial-review,completed-resume-proof và mọi episode/capture.
