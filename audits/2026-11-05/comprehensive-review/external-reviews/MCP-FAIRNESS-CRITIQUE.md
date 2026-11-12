# Phản biện MCP/fairness cho opencode-review.md và agy-review.md

Ngày kiểm tra: 05/11/2026. Chỉ đọc tài liệu/log/source và ghi audit; không sửa source/runtime/config, không gọi model hay data provider. Phân biệt source hiện tại đã có thay đổi phục vụ diagnostic với trạng thái v3 lịch sử; kết luận dưới đây dùng captures frozen và audit source đã trích xuất ở lượt review trước.

## 1. Phần giữ lại được

`opencode-review.md` dùng đúng primary denominator44 cho cả4 condition; tách16 cuộc gọi sai kiểu của OT khỏi90 rejection có schema hợp lệ; chỉ ra không có same-tool repair thành công trong pilot nhỏ; ghi rõ metadata replay không phải production ở dòng 238. Các hướng local validator, bounded repair, output gate và typed MCP là hợp lý để đưa vào thí nghiệm, không phải kết luận đã đo mức tăng.

`agy-review.md` nhận diện đúng các ví dụ HPG wrong-type/no repair, đơn vị BCTC, evidence/namespace và period1D. Hướng sửa cần giữ, nhưng số liệu mẫu số, nhãn task và khái quát causal phải sửa trước khi dùng làm kế hoạch.

## 2. Các claim cần sửa

| Claim / vị trí | Kết quả đối chiếu | Cách viết chính xác |
|---|---|---|
| OpenCode review mở đầu: gateway/timeout/catalog/schema tương đương | Model/provider/caps/đầu vào server có kiểm soát; effective schemas **không byte-identical** | Server contract chung; native transforms là một phần harness, có khác biệt đã ghi. Không tuyên bố đã loại mọi yếu tố hạ tầng. |
| OpenCode review3.3 “mô tả tool giống” | Đúng cho description replay so sánh, không đúng nếu mở rộng sang toàn bộ function spec | OT tên`mcp__opentrading__...`, OC `opentrading_...`; OT root inputSchema mất`additionalProperties:false`, OC/DSH giữ. Wrong-type`columns` vẫn sai trên cả hai; root additionalProperties:false không giải thích trực tiếp lỗi đó. |
| OpenCode review3.1 “90/106 bình đẳng giữa arm” | Cùng rejection policy, nhưng số lượng khác15/23/27/25 và tác vụ/args khác | Chính sách replay chung, không phải tác động bằng nhau hay mọi request đều sai production. |
| OpenCode RC1 gọi thêmdays=1 là phát minh tham số ngoài contract | `days=1` hợp live schema/provider; chỉ ngoài recorded snapshot request | Tách wrong-type, wrong-domain, hợp production nhưng chưa recorded, thiếu entity/ambiguous. |
| OpenCode RC4 “prompt dài gây lỗi” / “model nhỏ đọc nhắc gì làm nấy” | Quan sát tương quan arm-level; prompt/content/runtime khác đồng thời | Giả thuyết cần ablation; không dùng bốn điểm arm để xác nhận attention hay model cause. |
| AGY “OpenCode/DSH giữ namespace nguyên bản” dòng 98 | Capturewire khác namespace cả ba; DSH cũng có prefix như OT | Việc finalanswer bỏ prefix đúng là hành vi model/contractmapping; không phải riêng OT được cấp tên có prefix. |
| AGY pilot168trial,18/39,14/43,12/43 | Loại8 DNF; manifest176,44 mỗi arm | Primary unconditional18/44,14/44,12/44,12/44; có thể báo thêm conditional answered nhưng phải gọi đúng tên và kèm DNF. |
| AGY tool errors là server Pydantic validation | Replay dùng jsonschema.validate; Pydantic dùng ở liveFastMCP | Ghi rõ lớp nào validate; errorquoted`not valid under any schemas` đến từ replayjsonschema. |
| AGY runtime_only trước là đã repair | Hai runtimefiles trước chỉ thêm trustedpromptDir/clockPolicy | Không tính hai file đã cài là validator/argument repair/evidence gate; đây là công việc tương lai. |

Bằng chứngwire trực tiếp: `../mcp/representative-wire-tool-definitions.json`. OT parametersroot không có additionalProperties, OC/DSH false; trườngcolumns đềuanyOfarray/null. `mcp/FINDINGS.md` đã có local deterministicrepro phân biệt live/replay.

## 3. Nhãn bài toán trong AGY cần sửa

| Task | AGY ghi | Instruction thực tế |
|---|---|---|
| fin-l1-quote-02 | Giá VNM | Giá Bitcoin BTCUSDT tại snapshot, unit USDT |
| fin-l1-gold-01 | Giá vàng SJC | Vàng thế giới XAUUSD phiên gần nhất, USD/oz |
| fin-l2-tech-01 | RSI SSI | RSI-14 VCB khung ngày 1D |
| fin-l3-tech-multi-01 | RSI đa khung thời gian | RSI-14 khung ngày thấp nhất trong HPG,HCM,VND,SSI,SHB; đa mã, cùng khung |
| fin-l5-valuation-01 | Định giá cơ bản | Truy xuấtprice/PER/PB của FPT; không kiểm định fair value range/DCF |

Nguồn từng dòng: `tasks/pilot/<id>/instruction.md` và `solution/gold.json`. Việc nhầm SJC/XAUUSD có hệ quả kỹ thuật: MCP `vn_msn_fx_gold` không phải retail SJC; cần entity/unit/marketplace từ task, không sửa tool bằng suy đoán.

## 4. Kiểm soát lời khuyên autorepair

1. **Local validator** kiểm input theo originalMCP schema; không chỉ theo provider-sanitizedschema. Model thấy reduced schema được phép nhưng guard phải theo contract thật, ghi chi tiết path/expectedtype/allowed values.
2. **Không tự castscalar→array như một bản sửa tổng quát.** `columns:"close"`→`["close"]` mới đúngtype nhưng live`vn_quote_history` có field`c`; `project_rows` vớiclose trả`[{}]`. Cần alias registry công bố hoặc reject+modelretry. Không dùng tên field ở tool khác làm căn cứ.
3. **Không tự chọn minimal recorded request bằng gold/task ID.** Snapshot-only repair được dùng model-visible `error.snapshot_requests`/schema hiện có, giữ cùng tool/entity/date/period yêu cầu; nếu nhiều pattern không xác định duy nhất thì dừng/nhờ model chọn. Nếu candidate bỏdays/columns làm thay đổi query, phải log original/new args + policy; không coi canonicalization vô nghĩa.
4. Productionkhông có snapshot_requests nên policy đúng là invalid_argument→allowedfields/correctformat; auth/timeout/not_found/no_data có nhánh riêng. Không tạo missing financial claim từinvalid request.
5. Evidence builder chỉ lấy provenance của call thành công thật trong context + ledger; không chèn tất cả evidence để cứu điểm, không tạo IDs/hash, không tự quyết financial claim bằng oracle. Canonical namespace phải dùng registry mapping đã biết, không strip bừa substring.
6. Mỗi repair có cap 1 lần/cause hoặc rõ tổng cap; tính vào request/token/time budget, công bố metric original attempt/final result. Không loop đến pass hay retry infra để lọc DNF.
7. `OPENTRADING_STALL_MS`/streaming/gateway buffer cần phối hợp: timeout chung không loại được watchdog native. Artifact của model diagnostic mới không được trộn với v3 Bolt hay cấp lại nhãn certified cho run lịch sử.

## 5. Thí nghiệm MCP nhỏ nhất hữu ích trong một tuần

Nên tách thay metadata MCP chung khỏi thay runtimeOT. Tránh một gói đồng thời “đổi model + rút prompt + sửa schema + repair + evidencebuilder” rồi kết luậndescription gâyrađiểm.

**MCP-C0**: strict replay v3 như historical, được đóng băng lại trong locator mới vì current runner đã thay cho diagnostic. **MCP-C1**: cùng types/defaults/required keys/query matching/payloads/error policy/provenance/gold/grader; chỉ giữ semantics docstring thật và thêm field-level description rõ (interval1D/1W/1M, days là số candle, columns raw`t/o/h/l/c/v`, source fetch vs observation date, financial period/unit). Append replay restriction/snapshot_requests riêng, không thay docstring bằng restriction. Không thêm projection/slicing/hợp thức hóa query trong phase này.

C1 là **gói metadata**, không gọi nó là phép đo riêng vềđộ dài/docstring. Enum/bounds enforcement và typedoutput là phase contract hardening kế tiếp vì sẽđổi queryvalidation/failuresemantics. Nếu quyết định gộp trongC1 thì phải gọi là contract package ablation và ghi chính xác mọi query mới bị accept/reject; không quy riêng hiệu quả cho“description”.

Giữ **3 native arms: OT baseline, OC, DSH**; chưa cần OT finance đã không đạt guard. Giữmột model mà function calling/preflight thực tế ổn định, một prompt variant OT fixed, một clock/budget policy đã đăng ký. Trước inference kiểm server metadata/diff actual wire và protected files; report native transforms còn khác, không force ba effective prompt byte-identical.

Dev subset 8 task × 2 repeats × 3 arms × 2 MCP conditions = **96 trial**, đủ nhỏ để test tính hiệu quả của metadata trong tuần. Subset cố định trước khi chạy, ví dụ:

- fin-l1-quote-01 (HPG scalar columns/period) vàfin-l1-gold-01 (subset batch XAUUSD);
- fin-l1-bctc-01 (units), fin-l2-growth-01 (quarter binding);
- fin-l2-tech-01 (interval vs observation day), fin-l3-agg-01 (multicall);
- fin-l5-compare-01 (metric arrays/evidence), fin-l5-valuation-01 (capability naming).

Đây là dev exploratory trên các pilot case đã xem; không được gọi holdout hay ước lượng generalization. Có thể thêm canary real-empty trap offline đểbảo đảm error/no_data không bị lẫn; nếu thêm inference phải công bố số trial mới trước chạy. Chỉ nếu96 trial cóusage/operationalcoverageđạtgate và giải được uncertainty thì mở 22 task × 2 repeats × 3 arms × 2 conditions = 264 trial; không chạy 264 mặc định nếu quota/time không cần. Nêu rõ264 là run mới, không trộn kết quả 96 để chọn max score.

**Metrics chính**: unconditional primary/DNF theo đúng started denominator; MCPfirstcallvalid/schemaInvalid/domainInvalid/not_recorded tách riêng; same-request-repaired vàfinal-primary-recovered; evidencevalidcomplete; unit/period correctness; measured tokens + repair calls + elapsed latency; false-refusal vàfalse-positive trên đúng cohort. So C1−C0 trong từng native arm, task-paired CI exploratory; không dùng small subset để chứng minh OT đánh bại mọi đối chứng.

**Không sửa corp/data/gold lịch sử:** tất cả snapshots/replay financial envelopes/oracle/grader/176 v3 trials giữ byte identities. Thử nghiệm mới dùng config/protocol/sourceinventory/outputfolder và state hash mới, temperature/effort/caps theo policy đăng ký; provider allowlist diagnostic đang đổi là thay đổiimplementation thật nên cần freeze với nguyên bản hiện tại. Không sửa v3 receipt để làm cho resume bỏ qua mismatch.

## 6. Scope production phù hợp với một tuần

Tuần này đủ cho các seam đầu tiên: fix metadata/export + typed input một số tool, reject unknown period/columns, errors isError, local validator/boundedrepair và output contract gate rõ ràng, regression offline, một ablation nhỏ. Không nên hứa chuẩn hóa chính xác toàn 174 provider hay hoàn thành DCF/fair value. Full 174 catalog được scan hình thức nhưng chưa được verify tài chính độc lập từng provider.
