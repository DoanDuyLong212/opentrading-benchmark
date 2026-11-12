# Đánh giá OpenTrading, MCP và thực nghiệm tài chính v4.1

Ngày 06/11/2026, Asia/Bangkok. **Chưa có bằng chứng OpenTrading vượt OpenCode và DSH trong các tác vụ tài chính đã đo.** Pilot v3 đầy đủ đạt OT baseline 12/44, OT finance 12/44, OpenCode 14/44 và DSH 18/44. Phiên bản cải tiến v4.1 đã hoàn tất smoke18: OT candidate1/6, OpenCode2/6, DSH2/6. **Certificate bị chặn vì hai lượt OT kết thúc native failed; pilot176 chưa được chạy. Candidate chưa sẵn sàng qua gate hiện tại.** Không có concurrent OT baseline trong smoke để đánh giá nhân quả cải tiến hoặc promotion guard.

Báo cáo tổng hợp hai review người dùng cung cấp, điều tra source/MCP và artifact v3, cùng việc chuẩn bị thí nghiệm trên OpenTrading hiện tại. Hai tài liệu ngoài được coi là các lập luận cần kiểm chứng. Không lấy dự báo điểm hoặc chỉ dẫn chạy model trong tài liệu làm kết quả hay quyền thay đổi protocol.

## 1. Kết quả chắc chắn từ v3

Primary yêu cầu đáp án đúng toàn bộ, hợp đồng JSON và evidence đúng, nối được ledger thực, thực thi đúng hạn và status thành công. Mỗi condition bắt đầu 44 trial; mọi timeout/DNF giữ trong mẫu số này.

| Condition v3 | Primary /44 bắt đầu | Semantic /44 | DNF /44 | Từ chối oan /44 | FP trên 4 câu refusal |
|---|---:|---:|---:|---:|---:|
| OT baseline | 12 — 27,3% | 14 | 1 | 17 | 0/4 |
| OT finance | 12 — 27,3% | 14 | 1 | 15 | 0/4 |
| OpenCode | 14 — 31,8% | 15 | 1 | 14 | 0/4 |
| DSH | 18 — 40,9% | 18 | 5 | 11 | 0/4 |

Các tỷ lệ answered-only 12/43, 14/43 hay 18/39 chỉ là chẩn đoán phụ. Pilot có 176 trial bắt đầu; 168 không phải cỡ cohort primary. FP=0 trên bốn câu refusal không đồng nghĩa không có evidence bịa/sai ở các câu khác.

Prompt finance v3 giảm hai lượt từ chối oan, nhưng primary và semantic không tăng. Hai trial finance có evidence không khớp ledger, trong đó một trường hợp dùng placeholder. Guard v3 đã đăng ký **đạt** vì cho phép primary hòa baseline khi false refusal giảm và các chỉ số guard không regress. Quyết định triển khai bổ sung vẫn giữ prompt baseline: primary chưa tăng và có regression về evidence. Không viết lại guard v3 thành “fail”; guard v4.1 mới có điều kiện chặt hơn và được đăng ký trước inference.

Nguồn: [báo cáo v3](/home/doanlong/extra/benchmark/audits/financial-prompt-v3/REPORT.md), [kiểm chứng độc lập v3](/home/doanlong/extra/benchmark/audits/financial-prompt-v3/INDEPENDENT-CHECK.md).

## 2. Vì sao OT mất điểm: truy xuất và xử lý sau truy xuất

Đối chiếu đúng từng cặp task/run với DSH cho thấy **mỗi biến thể OT thua sáu cặp, không có cặp thắng**: ba cặp mất ở truy xuất, ba cặp mất sau tool thành công. Đây là phạm vi đã quan sát, không phải khẳng định mọi tác vụ OT đều có cùng cơ chế lỗi.

| Giai đoạn | Bằng chứng v3 | Hướng sửa có cơ sở |
|---|---|---|
| Tham số đầu vào | OT dùng `columns` dạng string; tự thêm window hoặc thu hẹp batch khác request được replay | Schema có nghĩa rõ, validation thật, tách lỗi kiểu/domain/replay |
| Sửa request | Sau rejection, model có thể kết thúc bằng null dù đã nhận hướng dẫn sửa; không có same-tool repair thành công trong pilot nhỏ | Bounded correction theo cùng intent, giới hạn budget và chống lặp |
| Phép tính/đơn vị/kỳ | Lấy đúng dữ liệu nhưng quy đổi VND→tỷ sai; chọn sai hai quý; dùng `1D` thay ngày/kỳ quan sát | Observation contract và phép tính deterministic có lineage; kiểm field số gắn với kỳ/đơn vị |
| Xuất đáp án | Đúng số nhưng thiếu evidence hoặc dùng SDK namespace thay canonical tool name; có placeholder | Machine-output contract, provenance bất biến và kiểm chứng evidence thật |
| Prompt/native loop | Quy tắc prose/style/unit có thể xung đột yêu cầu JSON; các harness có preprocessing và guards khác nhau | Prompt có machine mode, giữ safety; thử nghiệm đối chứng trên cùng native runtime |

Ví dụ finance thua DSH: HPG hai repeat sai kiểu/no repair; XAUUSD một repeat gọi subset không được replay; VCB LNST một repeat sai scale sau tool thành công; peer comparison một repeat thiếu evidence, một repeat sai source namespace. Baseline có ba retrieval loss và ba post-tool loss riêng; HPG baseline r2 đúng số, đơn vị, ngày nhưng thiếu evidence. Không quy trường hợp đó thành sai phép tính.

V3 ghi “4 recovered trials” mỗi arm theo nghĩa có tool khác thành công sau rejection. Cả bốn vẫn trượt primary và không sửa được request của chính tool bị từ chối. Nghiên cứu mới cần tách: sửa cùng intent, phục hồi đủ dữ liệu yêu cầu, rồi phục hồi primary cuối cùng.

Log xác nhận error đã tới model: cả 138 rejection smoke+pilot xuất hiện trong request kế tiếp. Không có bằng chứng ở v3 rằng MCP error bị giấu hoàn toàn hoặc ngân sách 24 request ngăn OT thử sửa. Giả thuyết “prompt dài gây mất evidence” có thể kiểm nghiệm, nhưng trace hiện có chưa cô lập được nhân quả; prompt ngắn hơn v3 cũng không tăng primary.

Nguồn: [forensic findings](/home/doanlong/extra/benchmark/audits/2026-11-05/comprehensive-review/forensics/FINDINGS.md), [matched losses](/home/doanlong/extra/benchmark/audits/2026-11-05/comprehensive-review/forensics/matched-losses.json), [source/architecture](/home/doanlong/extra/benchmark/audits/2026-11-05/comprehensive-review/architecture/FACTS.md).

## 3. MCP mô tả có đúng không, và bao nhiêu lời gọi thực sự sai schema?

Pilot v3 có 263 MCP call, 106 rejection: **16 sai schema kiểu/shape, 90 hợp schema nhưng không khớp replay**. Tỷ lệ 90/106 = 84,9%; không gọi cả 106 là lỗi schema hay lỗi backend live.

| Pilot v3 | OT baseline | OT finance | OpenCode | DSH |
|---|---:|---:|---:|---:|
| MCP calls | 65 | 66 | 66 | 66 |
| Schema invalid thật | 12 | 4 | 0 | 0 |
| Schema-valid nhưng not_recorded | 15 | 23 | 27 | 25 |
| Same-tool repair thành công | 0 | 0 | 0 | 0 |

`columns:"close"` sai kiểu thật; `interval:"day"` sai domain của provider dù schema v3 chưa mô tả enum. `{"symbol":"HPG","days":1}` có nghĩa hợp lệ ở production nhưng replay chỉ ghi symbol-only/default365 nên bị `not_recorded`. Một request schema-valid khác vẫn có thể sai domain; không suy toàn bộ 90 call là hợp lệ production. Giữ exact matching; không bỏ args hoặc trả payload khác kỳ/window để làm đẹp điểm.

Audit source đăng ký **174 tool, 331 property tham số**: không có field descriptions/enum/bounds trong generated input schema được kiểm tra; output schema của 174 tool là object tổng quát. Với 17 tool dùng trong study, có 52 property, cũng thiếu mô tả field. Exporter v3 còn làm mất tool-level docstrings, search metadata và output schema; mô tả trên wire là mẫu replay generic. Đây là hai lớp vấn đề: chất lượng source contract và mất thông tin khi export.

Các vấn đề production đã tái lập bằng stub gồm: interval sai có thể bị gói như `availability:unavailable`; period khác `quarter` có thể rơi sang dữ liệu năm; `valuation_run`/search hint gợi năng lực valuation rộng hơn phép tính thực; cột không được nhận diện có nguy cơ trả projection rỗng. Đây là căn cứ chuẩn hóa API, không phải bằng chứng tất cả bug đó gây ra từng lỗi pilot.

**C1 v4.1 chỉ bao phủ 17 tool của study**: khôi phục mô tả và metadata, bổ sung field semantics/domain guards đã xác minh, dùng cùng schema authoritative cho mọi condition. 402/402 recorded requests vẫn valid và chọn đúng envelope; 589 file tài chính giữ byte-identical. Output schema vẫn là generic object của source. C1 chưa chuẩn hóa typed financial outputs cho 174 tool và chưa triển khai các sửa production MCP sâu.

Production có 174 tool nhưng pilot chỉ lộ catalog nhỏ theo task. Chưa thể gọi “174 tool gây context overload” là nguyên nhân đã quan sát. Full-catalog discovery cần benchmark riêng.

Nguồn: [MCP findings](/home/doanlong/extra/benchmark/audits/2026-11-05/comprehensive-review/mcp/FINDINGS.md), [independent C1/current benchmark review](/home/doanlong/extra/benchmark/audits/finance-v4-current-implementation/independent-mcp.md).

## 4. Đối chiếu OpenCode review và AGY review

### OpenCode: tiếp nhận cơ chế, hiệu chỉnh kết luận

Các ưu tiên có cơ sở: registry validation, bounded repair, JSON/provenance gate, input/error/output contract có nghĩa tài chính, cùng thí nghiệm đối chứng. Prototype v4.1 đã triển khai một gói combined để kiểm các cơ chế này; pilot không tách riêng tác dụng validator, prompt và repair.

Những claim cần điều chỉnh:

- “Model mạnh xác nhận mọi lỗi do model nhỏ” chưa được chứng minh. Diagnostic chọn năm task, nhiều pass, deadline khác và missingness lệch theo arm. Có cả tương tác gateway buffering × watchdog OT; không kết luận khoảng cách harness biến mất.
- Diagnostic thực có **84 attempt, 31 completion, 30 pass và 53 error/DNF**. Phép chọn completion B trước rồi fallback A cho 40 ô có **24/40 pass, 25 completion**, nên completion-only là 24/25 = 96,0%, không phải 25/26 = 96,2%. Không thay failure bằng suy diễn ô chưa đo.
- Case `period="2025 (...không phải bội số hiện tại)"` có bằng chứng grader false-negative: phủ định loại bội số không phủ định năm. V4 sửa phạm vi negation trên bản sao, có adversarial test và frozen-v3 sensitivity; điểm lịch sử giữ nguyên.
- Suy token trực tiếp từ chênh ký tự không giải thích causal token usage. Ví dụ 1462/4 = 365,5, không phải 1237; lịch sử và lượt gọi cũng ảnh hưởng input tokens.

### OpenCode §10: cập nhật production là điểm quan trọng

§10 chỉ ra đúng độ trễ giữa study cũ và production0.3.1, cùng thiếu final independent closure của prototype cũ. Vì người dùng đã nâng source, v4.1 được tạo mới trên HEAD hiện tại; không dùng suite483pass hay certificate cũ để chứng nhận bản mới.

Các dự báo như “v4 sẽ đạt16–19/44”, “B1+B2 đạt24–30/44” và “model nhỏ có trần tuyệt đối” vẫn là giả thuyết. 12 task cùng trượt không chứng minh trần bất biến, hay chỉ có một con đường cải thiện. Compute-as-tools là hướng thử nghiệm đáng làm; mức hưởng lợi tương đối của OT so với hai harness phải đo khi cả ba cùng có API đó.

### AGY: sửa mẫu số và nhận diện task

Giữ cohort176 trial, 44/condition; answered-only là phụ. Các nhận diện BTCUSDT/VCB/XAUUSD và multi-symbol cần đúng theo task thực. Sai kỳ, scale và evidence có bằng chứng; namespace lỗi cũng xuất hiện ở OC/DSH. Không dùng smoke khác version/model/protocol hoặc nhóm case thuận lợi để tuyên bố OT đã ổn định/vượt trội.

Nguồn kiểm chứng chi tiết: [external review synthesis](/home/doanlong/extra/benchmark/audits/2026-11-05/comprehensive-review/EXTERNAL-REVIEWS-SYNTHESIS.md), [diagnostic fact-check](/home/doanlong/extra/benchmark/audits/2026-11-05/comprehensive-review/external-reviews/deepseek-diagnostic-claims.md), [OpenCode review §10](/home/doanlong/extra/benchmark/opencode-review.md), [AGY review](/home/doanlong/extra/benchmark/agy-review.md).

## 5. Bản v4.1 đã sửa gì và kiểm chứng đến đâu?

Study mới: `/home/doanlong/extra/benchmark/experiments/finance-v4-current-study`, trên OpenTrading0.3.1 HEAD `b6e354e76894887e31c33b1f13b44eadc02fad7e`. Baseline lấy sáu prompt production hiện tại. B0 và B1 dùng cùng current native loop/own dependencies; B0 policyOFF, B1 policyON và finance prompt. Các stop-gate/recovery, circuit breaker, accounting, cancellation và source guards upstream được giữ ở cả hai.

| Hạng mục | Đã triển khai/kiểm chứng |
|---|---|
| Native input/repair/output | Validation raw schema không coercion/default mutation; fail-closed schema không hỗ trợ; bounded read-only correction giữ entity/period/scope; immutable provenance; machine-output checks theo contract công khai |
| Catalog khi repair | Giữ full catalog; before-execution guard giới hạn tool được sửa. Không nới gateway để chấp nhận tool ngoài snapshot |
| Adapter B0/B1 | Lấy đúng final assistant text của completed native turn; không nối fragment đã bị stop-gate loại. Failed/aborted/missing completion không thành statusok; giữ partial output, unanswered và recoveries |
| Đối chiếu local rejection | Call ID/args/schema hoặc intent/phase, actual next-wire error và ledger proof; same-batch duplicate có bằng chứng MCP execution tương ứng |
| Grader | Sửa temporal-negation chung mọi arm; chấm cùng đáp án với frozen-v3 grader để tách hiệu ứng sửa grader |
| Identity | Pin TS/TSX/JSON, source/prompt/calendar, config/protocol/catalog/tasks, binaries và actual installed dependency files |
| Model/budget | Driver và gateway chỉ nhận Bolt; effortnone, temp0/top_p1,24request,2048output/request,48000policytokens, provider45s/trial240s. Native stall300s như current source, cùng hai OT condition |

Package production khai báo mới nhưng dependency cài ban đầu còn cũ. Study đã cài dependency tree riêng, không ghi qua symlink production. Source và dependency installation của original production được giữ nguyên; các sửa candidate/C1 và locked SDK mới trong study chưa được cài vào production. Actual versions gồm AI SDK7.0.159, MCP SDK1.32.2, compatible3.0.82, provider-utils5.0.72, zod4.6.7, Ajv8.20.0. Catalog/schema trên server chung; SDK wire có thể khác và được capture. Chỉ clock native OT được pin; không tuyên bố clock hoặc preprocessing OC/DSH byte-identical. Native failure nudge cũng không được giả định xuất hiện trên mọi provider route; đối chiếu actual wire quyết định.

Kiểm chứng trước inference:

- Full benchmark **297 pass**; offline preflight **4/4 PASS**.
- Native owner **151 focused pass**, typecheck pass; independent reviewer **27 focused pass**. Các lượt có overlap, không cộng thành178 test độc lập.
- Full native **1069 pass,2 skip,1 fail TUI timing**; cả file TUI rerun trên cùng source/deps **113/113 pass**. Giữ failure và logs. Reviewer chấp thuận **qualified operational PASS cho headless smoke**, không gọi full native suite hoàn toàn xanh hoặc kết luận đã chứng minh upstream flake.
- Actual current-SDK/NVIDIA-compatible captures qua gateway stub kiểm full catalog và các sampling/cap rewrite; đây là wire mock, chưa là financial-quality result.
- Original source/tasks, global diagnostic changes, archived v3/v4 được bảo toàn; 589 file tài chính byte-identical. Pre-inference engineering identity: `210b41a912b43d99b2db882a1c237e9d36072a30b3b9c217cefa5ae2562e4442`.

Nguồn: [implementation](/home/doanlong/extra/benchmark/experiments/finance-v4-current-study/audits/IMPLEMENTATION.md), [independent native closure](/home/doanlong/extra/benchmark/audits/finance-v4-current-implementation/independent-native.md), [independent MCP/benchmark closure](/home/doanlong/extra/benchmark/audits/finance-v4-current-implementation/independent-mcp.md), [source preservation](/home/doanlong/extra/benchmark/experiments/finance-v4-current-study/audits/original-after.json).

## 6. Kết quả smoke v4.1 và nguyên nhân dừng pilot

Smoke đã hoàn tất đúng18 trial =3 task×2 run×3canonicalarm. Canonical OT là candidate finance policyON; **không có B0 trong smoke**. Supervisor dừng tại bước certificate; pilot176 chưa bắt đầu. Nghiên cứu giữ nguyên source/prompt/grader, mọi trial và gate đã đăng ký.

| Condition smoke | Primary /6 | Frozen-v3 /6 | Semantic /6 | DNF /6 | Từ chối oan /4 answerable-started | FP /2 refusal | Usage đầy đủ |
|---|---:|---:|---:|---:|---:|---:|---:|
| OT candidate | 1/6 | 1/6 | 1/6 | 2/6 | 2/4 | 0/2 | 6/6 |
| OpenCode | 2/6 | 2/6 | 2/6 | 0/6 | 4/4 | 0/2 | 6/6 |
| DSH | 2/6 | 2/6 | 2/6 | 0/6 | 4/4 | 0/2 | 6/6 |

OT chỉ còn hai câu answerable đã trả lời, và cả hai từ chối sai: **2/2 answered-answerable**, khác 2/4 answerable-started. Hai câu answerable còn lại là DNF; số false refusal thấp hơn hai đối chứng không chứng minh chất lượng tốt hơn. Không dùng /6 làm mẫu số rủi ro false refusal; /6 chỉ có thể là cohort-normalized diagnostic được ghi rõ.

Cả ba arm đều trượt cả bốn lượt hỏi giá/tổng hợp; các primary đúng đến từ trap mã không tồn tại. Có40 upstream request HTTP200,42 MCP call và80 native/effective captures. Usage đầy đủ18/18:91.199input và7.639output token. OT dùng16 request; OpenCode/DSH mỗi bên12.

| Condition | Upstream request đủ usage | Input token | Output token |
|---|---:|---:|---:|
| OT candidate | 16/16 | 47.257 | 2.320 |
| OpenCode | 12/12 | 24.700 | 2.597 |
| DSH | 12/12 | 19.242 | 2.722 |

Không quy token thành USD vì chưa đóng băng pricing/entitlement được xác minh. Không có gateway rejection, provider error hay timeout giải thích thất bại này. Có5 trial placeholder/evidence mismatch ở OC2/DSH3 và tất cả bị primary chặn; accepted fabricated evidence=0. Không được mô tả các đáp án từ chối của đối chứng đều sạch evidence chỉ vì statusok.

### 6.1 Interface replay vẫn làm mọi arm mất dữ liệu

**Toàn bộ36 call `vn_quote_history` đều hợp schema C1 nhưng `not_recorded`; không có schema-invalid trong smoke.** Mỗi arm có12 rejection: hai HPG và mười bank calls. Sáu MCP success còn lại là symbol resolution của trap, không phải truy xuất giá thành công.

Model chọn các tham số có nghĩa tự nhiên theo API: `columns:["c","t"]`, HPG thêm `days:1`; bài ngân hàng dùng `days:365` kèm projected columns. Recorded requests chỉ có symbol/default-equivalent không projection. Vì `columns` khác default và không có recording tương ứng, replay từ chối đúng hợp đồng. Không được gọi nhóm này là “36 lỗi schema” hoặc tự kết luận backend tài chính không có dữ liệu.

C1 đã bổ sung mô tả field và domain guards đã xác minh, nhưng broad production-like input schema và tập request finite chưa trở thành một interface thống nhất đủ để model tuân thủ. Tất cả arm cùng gặp điểm nghẽn này. Chưa thể từ smoke ba task tách ảnh hưởng C1, native base, model hay prompt, hoặc suy rằng production không hỗ trợ truy vấn đó.

### 6.2 Repair HPG thực sự kích hoạt nhưng không tạo corrected call

Hai HPG OT đều có request thứ ba với `tool_choice:auto` và nudge `One bounded correction`, yêu cầu sửa tham số theo error/public schema. Model đã thấy `snapshot_requests:[{"symbol":"HPG"}]` và cảnh báo rejection không chứng minh thiếu dữ liệu. Tuy nhiên model tiếp tục xuất null, không gọi tool mới.

Đây là **repair phase đã chạy nhưng hành vi sửa request không xảy ra**, không phải bằng chứng hook bị mất hay tool error bị giấu. Có thêm request/token nhưng không có retrieval hoặc primary recovery.

### 6.3 Aggregation bộc lộ giới hạn counter theo tool, không theo intent

OT gọi năm ngân hàng song song; cả năm request đầu tiên bị replay reject. `FinancePolicyState.failures` đang key theo `def.name`, `failed()` cộng `attempts` cho từng failure và `correctionTools()` chỉ chọn state có `attempts<2`. Năm lỗi của năm entity khác nhau cùng tăng một counter lên5, nên không còn tool eligible trong bounded correction. Đây là vấn đề thiết kế **per-tool counter gộp nhiều intent ban đầu**, không phải model đã dùng hết năm lượt sửa cùng một intent.

Actual request thứ ba của hai aggregation trial có `tool_choice:none`, chỉ sửa output. Model vẫn không đáp ứng contract evidence sau correction; native phát `Machine-response contract failed after bounded correction` rồi `done.outcome:failed`. Wrapper ghi đúng error/DNF và giữ logs, không biến partial hoặc buffered draft thành đáp án thành công. Thất bại này cho thấy mock/unit coverage chưa bao phủ đầy đủ chuỗi năm parallel replay errors → per-intent correction → final public contract.

Repro deterministic qua actual policy class đã xác nhận thêm: sau một VCB failure, `before(BID)` bị chặn vì đổi entity dù BID là một intent truy xuất mới và chưa ở correction phase. Đây là bug candidate thực tế: state theo tool làm scope guard áp vào mọi call tương lai cùng tool. Cần **P0 tách state theo intent và chỉ áp repair-scope guards cho call đã được nhận diện là correction**, không cấm một entity khác hợp lệ trong nhiệm vụ nhiều mã. Bằng chứng: [policy-counter-repro.json](/home/doanlong/extra/benchmark/audits/financial-prompt-v41/policy-counter-repro.json).

Không hạ gate để đi tiếp pilot. Cần sửa theo phiên bản mới sau preregistration, giữ các lượt này làm kết quả thất bại của v4.1.

### 6.4 Một trap có ứng viên false-negative của refusal grader

OT trap r1 trả null với lý do **“không được giải mã thành symbol hợp lệ”**, phù hợp nghĩa mã không phân giải được; lexical gold không nhận paraphrase này. Official v4 và frozen-v3 đều giữ trial trượt. Review semantic chấp nhận đây là honest refusal, tương ứng2/6OT nếu adjudicate riêng; không sửa answer/grader/điểm đã chạy. Dù adjudication chấp nhận trường hợp này, hai DNF aggregation vẫn tồn tại và gate hiện tại vẫn không đạt.

### 6.5 Audit và resume

Coordinator chạy prepared independent verifier một lần; auditor độc lập xem kết quả và chốt manual findings. Verifier chấm lại18đáp án/kết quả bằng cả v4 và frozen-v3, đối chiếu42 MCP call,40 upstream request,80capture, usage và evidence; **0 audit error**. Kiểm exact completed-run resume exit0: toàn bộ2216 file manifest/trial được đối chiếu giữ byte-identical, không thêm request/capture/trial. Xem [resume receipt](/home/doanlong/extra/benchmark/audits/financial-prompt-v41/smoke-resume-check.json). Audit tính toàn vẹn đạt PASS, còn readiness đạt FAIL như đã nêu; kết luận độc lập nằm tại [INDEPENDENT-CHECK.md](/home/doanlong/extra/benchmark/audits/financial-prompt-v41/INDEPENDENT-CHECK.md).

**Pilot: NOT STARTED. Guard v4.1: NOT EVALUABLE.** Không có44 trial/condition hoặc B0 concurrent; không điền0/44, không tính CI hoặc delta candidate−baseline cho dữ liệu chưa chạy. Smoke chỉ đủ kết luận candidate/interface hiện tại chưa qua gate và xác định các cơ chế cần sửa.

Protocol giữ nguyên: [v4](/home/doanlong/extra/benchmark/plans/2026-11-05-v4-improvement-experiment.md), [current-runtime amendment](/home/doanlong/extra/benchmark/plans/2026-11-06-v4-current-runtime-amendment.md). Development set đã được xem; smoke không chứng minh generalization, stable3/3, main+7điểm%/CI97,5% hay kết quả Go/DeepSeek/medium.

## 7. Checklist nghiệm thu giữ lại cho thí nghiệm kế tiếp

1. **Lịch/cohort:** đúng176 trial unique theo manifest, đủ44/condition, không bỏ/thay trial timeout/DNF; source/config/protocol/dependency fingerprints còn khớp. Smoke18 và certificate thuộc đúng v4.1.
2. **Chấm độc lập:** regrade tất cả đáp án lưu được vào thư mục tạm; giữ mọi invalid JSON/missing answer/statusfail. Chấm song song v4 và frozen-v3, báo từng delta do grader; không sửa grade/answer lịch sử.
3. **Evidence:** nối đủ bảy field với successful ledger của final attempt; xác minh receipt thực sự có trong ngữ cảnh model. Giữ placeholder/fabrication/namespace mismatch; không cấp evidence cho rejected call.
4. **Tool path:** generated calls = actual MCP executions + proved local rejections. Tách v3-type/shape, C1-domain, not_recorded, legitimate empty/no-data, provider/transport errors. Same-intent repair cần corrected call và required-data completion; báo thêm có phục hồi primary hay không.
5. **Native/wire:** đối chiếu actual native/effective request hashes, model, catalog, sampling, caps, clocks/preprocessing; native completed/failed/aborted/unanswered/recoveries và policy activation. Không coi full catalog là bằng chứng đã gọi đúng tool hoặc cùng tool success là đủ toàn bộ evidence.
6. **Usage/DNF:** giữ mọi request/attempt, kể cả correction/recovery; phân biệt gateway rejection và upstream call. Usage thiếu giữN/A/partial/lower bound có coverage, không gán0 hay suy chi phí tiết kiệm. Báo latency và tokens cùng denominators, không loại failures khỏi primary.
7. **Thống kê/guard:** primary /44, semantic/unit/period riêng; false refusal trên40answerable-started và answered-only; FP trên4refusal cùng cohort-normalized guard. Task-paired exploratory CI95 và payload-family sensitivity; không đổi endpoint sau thấy điểm.
8. **Resume:** completed smoke/pilot chạy lại đúng args+`--resume`; trial IDs và manifest/trials/provider-ledger hashes không đổi,0 request mới/0 duplicate.
9. **Kết luận đầy đủ:** báo cả22task và mọi condition, không chọn subgroup thắng; ghi rõ candidate thắng/hòa/thua concurrent baseline và từng đối chứng, hạn chế statistical/generalization.
10. **Rollout:** guard mới yêu cầu primary candidate **cao hơn** baseline, không regress DNF/false refusal/FP, không accepted fabricated evidence và không tăng claimed evidence-mismatch trials. Với v4.1 dừng sau smoke, guard **NOT EVALUABLE**; checklist này chỉ áp dụng khi một nghiên cứu mới thực sự hoàn tất pilot đã đăng ký. Không tự promote hoặc cài vào original; mọi triển khai sau này cần review cụ thể, hash guard/backup và authorization phù hợp.

## 8. Hướng nâng cấp tiếp theo sau study này

Ưu tiên sản phẩm gồm input/error/output contracts typed cho17tool trước rồi mở rộng174, financial observation có unit/period/basis/lineage rõ, và deterministic calculations nhận operands thật từ tool. Compute endpoints cho aggregate/growth/margin/indicator/ranking cùng chuẩn hóa đơn vị là bước thực nghiệm hợp lý.

Các endpoint mới cần cùng khả năng cho OT/OC/DSH, có công thức/precision/missingness kiểm chứng, snapshot corpus và gold version mới, preregister trước inference. Không tự map hidden task/gold vào runtime hoặc chỉ bổ sung calculator cho OT trong track parity hiện tại. Ước lượng lợi ích và lợi thế tương đối là **PENDING**, vì hai đối chứng cũng hưởng lợi từ công cụ tốt hơn.

Model mạnh/streaming là track riêng: kiểm actual reasoning options, gateway buffering, provider timeouts và native stall trước khi chạy. Diagnostic cũ đã chỉ ra tương tác vận hành nhưng chưa chứng minh một nguyên nhân độc quyền. Không bổ sung compute, nới cap hay retune candidate rồi gắn kết quả mới vào run v4.1 đã thất bại. Pilot v4.1 chưa chạy; phiên bản sau phải có source/interface/protocol identity mới.

Kế hoạch sản phẩm chi tiết: [OT/MCP standardization](/home/doanlong/extra/benchmark/plans/2026-11-05-opentrading-mcp-standardization.md). Phạm vi kết luận hiện tại vẫn là snapshot-grounded financial QA; chưa chứng nhận tính đúng của filings gốc hoặc toàn bộ thị trường tài chính Việt Nam.


## 9. Bước tiếp theo sau smoke thất bại

Đề xuất một study mới với ba nhóm thay đổi được đăng ký trước inference: interface finite-replay nói rõ accepted request constraints cho mọi arm; repair state theo tool+intent và xử lý parallel batch; public success/refusal answer contract cùng semantic refusal grading có adversarial guards. Không thực hiện sửa hoặc inference trong v4.1 đã đóng băng. Kế hoạch cụ thể: [v4.2 replay/repair/contract](/home/doanlong/extra/benchmark/plans/2026-11-06-v42-replay-repair-contract-study.md).

Compute-as-tools vẫn là một track common-MCP riêng sau đó. Nó không thay thế việc sửa interface finite-replay, counter per-intent và grader được phát hiện ở smoke này. Chưa dự báo điểm hoặc cam kết OT sẽ vượt hai harness khi các thay đổi chưa được đo.
