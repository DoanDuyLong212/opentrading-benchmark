# Review benchmark OpenTrading × DeepSeek Harness × OpenCode

Ngày đánh giá: **04/11/2026**, múi giờ Asia/Bangkok. Trạng thái: **CHƯA ĐỦ ĐIỀU KIỆN chạy main để công bố xếp hạng harness**.

Thiết kế snapshot, oracle, grader bằng code, nhiều lần chạy và không gộp mọi tiêu chí thành một điểm là hướng đúng. Tuy nhiên, cài đặt hiện tại chưa thực hiện đầy đủ những bảo đảm được mô tả trong README/PRE-REGISTER. Điểm smoke 9/9 trước đây chỉ chứng minh một đường chạy đã hoàn tất, chưa chứng minh benchmark công bằng, không thể bị vượt qua, hoặc đo đúng năng lực phân tích tài chính Việt Nam.

## 1. Phạm vi và bằng chứng

- Kiểm tra cấu trúc đủ **200 main, 24 pilot, 3 smoke, 50 holdout**.
- Chạy lại **227 oracle** của main/pilot/smoke: tất cả pass. Không chạy model, oracle hoặc grader trên holdout trong vòng phát triển này; chỉ đếm và băm file holdout.
- Chạy **227 × 3** ca grader: đáp án tổng hợp đúng đều pass; đột biến cơ bản và đáp án rỗng đều fail. Leak scanner hiện có báo 0. Đây là kiểm tra nhất quán nội bộ, không phải xác nhận dữ liệu gốc đúng ngoài thực tế.
- Bộ test cũ: **38 passed**. Lần chạy sandbox bị vướng; kết quả đầy đủ được xác nhận khi chạy ngoài sandbox.
- Bổ sung kiểm định đối kháng bằng script, không sửa task/gold/runner/config gốc.
- Kiểm tra source OpenTrading đang cài ở commit `2af971e86cf8a548dce55d35ac27d68e36d95721`, DSH `0.2.1-rc.2`, profile DSH thực tế, runtime skills/tools và kết quả smoke cũ.
- Gọi API discovery Google/NVIDIA; chạy smoke mới bằng **Google Gemini 3.5 Flash Lite**, không gọi DeepSeek trả phí, Beam hoặc model lớn NVIDIA.

Bằng chứng máy đọc: [audit-evidence.json](audit-evidence.json), [supplemental-evidence.json](supplemental-evidence.json), [runtime-inventory.json](runtime-inventory.json), [provider-probe.json](provider-probe.json), [smoke-evidence.json](smoke-evidence.json), [smoke-diagnostics.json](smoke-diagnostics.json), [task-sha256.json](task-sha256.json).

## 2. Những lỗi cần sửa trước khi chạy chính thức

### P0 — Snapshot trả dữ liệu cho tham số sai

`tools/mcp_snapshot_server.py:42–59` chọn envelope có số tham số khớp nhiều nhất; nếu không khớp gì vẫn lấy envelope đầu tiên. **112/112** task được thử với symbol `AUDIT_DOES_NOT_EXIST_999` vẫn trả dữ liệu. Mọi param optional, `additionalProperties=true`; pilot còn không lưu params gốc, nên không thể xác nhận lời gọi đúng bằng dữ liệu hiện tại.

Hệ quả: gọi sai mã, sai kỳ, hoặc bỏ tham số có thể vẫn đạt đáp án. Benchmark không đo chính xác việc lập kế hoạch và sử dụng công cụ. Một test hiện có còn yêu cầu hành vi fallback này phải xảy ra.

**Nâng cấp:** schema lấy từ catalog MCP thật; phân biệt param định danh bắt buộc và defaults đã đăng ký; chỉ replay khi request tương đương một request đã ghi. Sai symbol/kỳ phải trả lỗi `not_in_snapshot` có cấu trúc; nhiều ứng viên không phân biệt được phải báo ambiguity. Chuẩn hóa defaults được phép, không dùng nearest-match để biến request sai thành đúng. Pilot phải bổ sung request gốc hoặc ghi rõ chỉ là kiểm tra adapter.

### P0 — Grader chấp nhận kỳ/nguồn sai và từ chối sai định dạng

| Kiểm định đối kháng trên main/pilot/smoke | Kết quả hiện tại |
|---|---:|
| Kỳ `Q1/1900; KHÔNG PHẢI <kỳ gold>` | **128/128 pass** |
| Nguồn `KHÔNG dùng <tool gold>; nguồn thực tế: invented` | **189/189 pass** |
| Refusal với `value: "12345 đồng"` | **26/26 pass** |
| Refusal với `value: {"amount":12345}` | **26/26 pass** |
| Một câu từ chối chung, không đọc tool | Pass cả **26 refusal task** |

`tokens_hit` so chuỗi con nên không hiểu phủ định hoặc mâu thuẫn. Refusal chỉ kiểm tra `parse_number(value)` có thành công không; “không parse được số” bị đồng nhất với JSON null. FP hiện chỉ bắt số ở đúng `value`, bỏ qua số bịa trong trường khác. Câu từ chối chung vượt các task refusal là baseline kiểm soát cần báo cáo, không phải một mình nó chứng minh grader sai; nhưng cho thấy **FP thấp phải được đọc cùng false-refusal và answer coverage**.

**Nâng cấp:** validate JSON schema trước; `value` của refusal bắt buộc tồn tại và bằng JSON null. Tách `requested_period`, `comparison_period`, `data_as_of`, `tool_sources` và evidence. So sánh kỳ đã parse thành cấu trúc; nguồn là danh sách canonical tool IDs, không chấm ngữ nghĩa nguồn bằng substring. Phần giải thích có mâu thuẫn thì fail hoặc đưa vào hàng đợi duyệt người. Kiểm định thiếu trường, phủ định, hai đáp án, sai năm, sai năm tài chính, object/string thay số, đáp án bịa ở `note` và payload prompt injection.

### P0 — Các harness chưa đồng bộ thực sự

| Trục | Bằng chứng hiện tại | Kết luận |
|---|---|---|
| Dữ liệu | Cùng server và envelope snapshot | Đúng ý tưởng, matcher cần sửa |
| Skills OpenTrading | `ot_headless.ts` gọi `loadSkills()`; runtime nạp **30 bundled skills** | Mô tả “không skills” sai; nạp catalog không đồng nghĩa mọi skill đã được dùng |
| Skills OpenCode | Smoke mới thực sự gọi skill **brainstorming** dù XDG đã tách | Vẫn kế thừa skills ngoài benchmark |
| DSH | Dùng profile `headless` của user, có `dsh-thinking-levels`, `dsh-pdf-reader`, hooks | Chưa phải profile tối giản, đóng băng và độc lập |
| Web OpenTrading | Runtime đăng ký `web_search`, `web_fetch`; cả hai `readOnly:true` | Chưa bị loại khỏi registry; headless permission không tự chặn read-only |
| Reasoning effort | DSH patch đặt NVIDIA `low`, Google `off`; OpenCode/OT không đặt tương đương | Chưa có cấu hình medium chung |
| Output | OC/DSH viết file; OT được nhắc thêm để in JSON; OC còn cứu object từ write-tool input bị lỗi | Có khác biệt adapter ảnh hưởng success |
| Budget | Có timeout chung theo task, chưa có cap request/token chung; retry ngoài làm mới timeout | Chưa chứng minh ngang ngân sách thực dùng |
| State | OC XDG riêng, OT home riêng; DSH dùng global profile; auth copy nhiều provider | Cần kiểm tra cấu hình hiệu lực và side calls |

Không cần ép mọi system prompt giống nhau: system prompt và cách lập kế hoạch là một phần harness. Nhưng phải chọn rõ **đánh giá sản phẩm mặc định** hay **đánh giá harness trong điều kiện kiểm soát**. Nếu giữ skill tài chính riêng cho OT, đó là lợi thế của sản phẩm được đánh giá, phải ghi rõ, không được gọi là không skills/cùng skills.

**Khuyến nghị cho tuần này:** một track chính có model/provider/effort/budget/data/output contract chung, không user skills, không user plugins, memory off, web off; native system prompt của từng harness được giữ và băm. Nếu muốn đo giá trị bộ skill, làm một ablation nhỏ sau track chính. Không nhân đôi toàn bộ workload để chạy cả hai track trong một tuần.

### P0 — Token, số tool call và cost chưa dùng để xếp hạng được

- OpenCode runner gán `tokens = tk` mỗi event, giữ **bước cuối**, thay vì cộng từng request. Smoke quote mới có **15 step-usage records, tổng input 71.977/output 545**, nhưng trial lưu input **3.529/output 16**. Smoke aggregate có 9 records, tổng input 41.239 nhưng lưu 3.012. Cache cần cộng và phân loại riêng.
- `count_mcp_calls` đếm regex trên mọi nội dung log. Smoke aggregate OT có **1 `tool-start` MCP** với call ID riêng, nhưng trial báo **9 MCP calls**; quote 1 nhưng báo 4. Chuỗi tool name có thể xuất hiện trong tool-search result, mô tả và log khác.
- Kết quả DSH cũ lưu shape `inputTokens/outputTokens/cacheReadTokens`; `norm_tokens` hiện không đọc shape đó. Coverage/cost lịch sử có thể mất dù usage đã tồn tại.
- `cost_of_trial` coi output thiếu là 0; bảng giá hiện tại dùng giá OpenCode Go nhưng model mặc định đi qua NVIDIA. Giá chuẩn hóa giả định có thể hữu ích, nhưng không phải chi phí NVIDIA thực trả.
- `build_summary` lấy model và giá từ config đang sống, không từ manifest của lần chạy. Phân tích lại dữ liệu cũ sau đổi config có thể gắn sai model/giá.
- Retry dùng lại workspace và ghi đè log; latency/tokens chỉ phản ánh attempt cuối. Tổng chi phí và thời gian bị mất. Có thể tái sử dụng answer cũ khi retry hoặc dùng lại `--out`.

**Nâng cấp:** telemetry server-side append-only `{trial_id, attempt_id, call_id, tool, normalized_args_hash, selected_payload_hash, status, started, ended}`; client-side per-request usage có request ID và cache semantics. Lưu tất cả attempts trong thư mục mới, fresh workspace/session, tổng hợp cả attempt thất bại và backoff. Khóa manifest model/provider/endpoint/effort/pricing. Tách **observed usage**, **estimated list-price cost**, **allowance consumption**, **cash subscription fee**.

Không mặc định trừ hoặc cộng cache giống nhau cho mọi provider: phải xác minh input token đã bao gồm cache hay chưa. Reasoning cũng có thể nằm trong output hoặc được báo riêng; tránh tính hai lần.

## 3. Metrics: giữ gì và đổi gì

Dashboard nhiều tiêu chí là hợp lý; không cần tạo điểm tổng tùy ý. Tuy nhiên, `metrics.py/analyze.py` **chưa triển khai** stable-correct, paired confidence interval, McNemar/Holm và dashboard FP/latency chính như kế hoạch mô tả. Driver chỉ in vài tổng cơ bản. Ghi trong PRE-REGISTER không tương đương đã có code phân tích.

| Metric | Định nghĩa nên đóng băng |
|---|---|
| Success primary | Đúng đáp án và những điều kiện provenance/schema bắt buộc, hoàn tất trong ngân sách; mẫu số là mọi trial đã bắt đầu |
| Answer correctness secondary | Chỉ chất lượng nội dung, để phân biệt sai adapter/format với sai tài chính |
| Stable-correct / pass^3 | Task đúng đủ 3 lần độc lập / task có đủ 3 lần theo lịch; thiếu run phải hiện incomplete, không tính 1/1 thành 3/3 |
| Hallucination on unanswerable | Số trial đưa ra khẳng định số không được hỗ trợ / số trial unanswerable; báo cả started và answered, kèm DNF |
| False-refusal on answerable | Từ chối ở trường thực sự có đáp án / trường hoặc task answerable; phân biệt null hợp lệ, schema thiếu, invalid format và set/ranking không có scalar value |
| Grounded correctness | Kết quả đúng và evidence nằm trong tool-call ledger của chính trial; tự ghi tên tool không đủ |
| Time | End-to-end p50/p90, time-to-valid-answer, timeout rate, tổng retry/backoff; thêm thành phần model/tool/harness nếu đo được |
| Cost | Tổng usage của mọi request và attempt; cost/success chỉ tính khi coverage đủ hoặc báo theo matched observed subset |
| Per-check score | Để chẩn đoán; L5 thêm completeness và lỗi trọng yếu, vẫn giữ all-pass |

**Stable-correct 3/3 không phải xác suất đúng khi dùng một lần.** Độ tin cậy một lần được ước lượng bằng success per trial; pass^3 đánh giá tính nhất quán qua ba lần. Không dùng pass@3 (“đúng ít nhất một lần”) thay pass^3.

Các lỗi metric đã tái hiện bằng counterexample trong JSON:

- `dnf_rate` dùng `answered = n - dnf`, coi `status=ok` nhưng không có answer là answered. Nó cộng mọi success vào tử số answered, kể cả success trên trial timeout/error; một input hợp lệ theo schema hiện tại cho **success_answered=200%**. Driver hiện vẫn chấm file khi process timeout, nên cần xử lý đúng trường hợp này.
- `false_refusal_rate` dùng không tìm thấy scalar value để suy ra từ chối; task chỉ có set/ranking/string dễ bị gắn nhầm. `task_is_partial` loại cả task khi một payload partial, dù trường được hỏi có thể đầy đủ.
- MAD% chia cho median có dấu: hai đáp án âm cho **MAD%=-9,091%**. Dùng `abs(median)` và xử lý gần 0; pass-only MAD vốn chỉ là metric phụ đã bị ràng buộc bởi tolerance, không thay stability.
- Error taxonomy ưu tiên `khong_tra_loi` từ grader có thể che nguyên nhân timeout/provider error. Lưu riêng execution_error, format_error, semantic_error.

**Thống kê:** unit phân tích là task, không phải 600 trial độc lập/arm. Với success ba lần, dùng paired bootstrap trên trung bình per-task; thêm sensitivity theo nhóm payload/family để thể hiện tương quan. Với stable-correct nhị phân đủ 3 runs, McNemar paired là phù hợp nếu nêu rõ endpoint; Holm cho các so sánh đã đăng ký. Ngưỡng chênh 7 điểm phần trăm là tiêu chí ý nghĩa thực tế, chưa chứng minh đủ power. Pilot cần ước lượng discordance/correlation trước khi hứa phát hiện 7 điểm.

Ví dụ sensitivity có giả định: với 200 cặp task nhị phân độc lập và tỷ lệ hai arm bất đồng khoảng 30%, xấp xỉ chuẩn cho sai số chênh là `sqrt(0.30/200) ≈ 3,9 điểm %`; khoảng 95% rộng xấp xỉ ±7,6 điểm trước hiệu chỉnh nhiều so sánh. Không phải power estimate đo từ repo. Main chỉ có 23 task refusal; dù không có FP ở cả ba lần, bằng chứng để khẳng định “rất hiếm bịa” vẫn yếu. Đừng coi 69 lần lặp là 69 tình huống độc lập hoặc kết luận FP thực tế bằng 0.

## 4. Chất lượng câu hỏi và độ bao phủ tài chính Việt Nam

**Những phần nên giữ:** đơn vị nghìn/đồng/tỷ, lợi nhuận công ty mẹ/hợp nhất, QoQ, CPI nhiều chuỗi, dữ liệu không khả dụng, đối chiếu hai nguồn và snapshot tái lập. Đây là các lỗi thực tế quan trọng.

**Những giới hạn đo được:**

- Main có **24 family labels**, **115 tập payload khác nhau**, **139 envelope khác nhau**. 200 thẻ không phải 200 tình huống dữ liệu độc lập.
- **27/50 file payload holdout trùng byte-for-byte với một file main**. Không đồng nghĩa model đã thấy gold, nhưng holdout hiện kiểm tra chuyển đổi câu hỏi trên dữ liệu quen thuộc nhiều hơn là tổng quát sang dữ liệu mới. Kiểm tra này chỉ so SHA256, không dùng câu hỏi/gold holdout để tinh chỉnh.
- **Toàn bộ 40 task L3 chỉ có một tên tool trong catalog task**; 25/40 L5 cũng vậy. Một tool vẫn có thể cần nhiều calls/entities, nhưng catalog đã chỉ sẵn đường đi; không thể suy rằng L3–L5 luôn đòi hỏi orchestration sâu.
- Ví dụ L2 ratio chỉ đọc P/E từ `valuation_run`; L2 technical đọc RSI đã tính; L5 valuation chỉ đọc price/P-E/P-B. Đây là extraction được gắn nhãn khó hơn, chưa đo lập mô hình định giá.
- **200/200 main không có check `as_of`**, **32/200 không có source check**. 88 task không có period-type check; 101 không có unit-type check. Hai số sau không tự động là lỗi vì units có thể nằm trong tên trường hoặc task chỉ hỏi ranking/verdict; cần audit theo output contract thay vì ép thêm trường vô nghĩa.
- `source` trong đề thường đã ghi sẵn tên tool. `provenance.source` thật lại là `vietstock`/`computed-local`… Đây là hai namespace khác nhau; kiểm tra source bằng tên tool không thực hiện được lời hứa đối chiếu provenance.
- Đề nhắc xem `task.toml → snapshot_date` nhưng workspace chỉ có `instruction.md`. Cần đưa metadata không chứa đáp án vào prompt hoặc manifest read-only.
- Oracle và gold do cùng family builder tạo, nhiều oracle chỉ kiểm tra `gold.solution`, grader lại chấm `gold.expects`. Pass oracle không thay xác minh công thức độc lập, consistency giữa solution/expects, hoặc đối chiếu báo cáo gốc.

**Ưu tiên chất lượng hơn tăng số câu:** chọn 20–30 task đại diện, kiểm tra bởi người hiểu tài chính hoặc reviewer độc lập, lưu tài liệu gốc/trang/dòng/công thức. Những số stale hoặc đơn vị chưa xác minh phải thành task phát hiện giới hạn hoặc bị loại khỏi câu khẳng định số đúng. Snapshot tái lập được vẫn có thể chứa số tài chính sai.

Một kiểm tra thực tế đáng lưu ý: CTD có Q4/2026 trong payload vào 01/11/2026 **không tự động là dữ liệu tương lai**. Báo cáo công bố của Coteccons ghi niên độ 01/07–30/06. Nên thêm `fiscal_year_end` và ngày bắt đầu/kết thúc kỳ, thay vì áp quý dương lịch cho mọi mã. [Báo cáo Coteccons](https://coteccons.vn/wp-content/uploads/2025/04/20250429-CTD-BCTC-Rieng-Quy-3.2025-Giai-trinh-trong-TM-ENG.pdf).

Đề xuất bổ sung/thay thế có chọn lọc trước freeze, không sửa holdout hiện có để tối ưu kết quả:

| Nhóm mới | Ví dụ câu hỏi/điểm phải chấm |
|---|---|
| Kỳ và kế toán | Tính Q3 riêng lẻ từ 9T trừ 6T; phân biệt kỳ tài chính/dương lịch, standalone/consolidated và số điều chỉnh hồi tố |
| Định giá thật | Tự tính EPS TTM, P/E, P/B với số cổ phiếu và ngày dữ liệu; giải thích tại sao P/E âm không hữu ích; cảnh báo mismatch đơn vị |
| Ngân hàng | NIM/NPL/coverage với định nghĩa và kỳ nhất quán; không ép gross margin doanh nghiệp thường vào ngân hàng |
| Corporate actions | Phân biệt giá điều chỉnh/không điều chỉnh khi trả cổ tức/chia tách; so lợi suất với cùng convention |
| Dữ liệu mâu thuẫn | Hai nguồn thật sự khác số hoặc khác as-of, đưa quyết định có bằng chứng thay vì luôn kết luận “khớp” |
| Recovery | Snapshot trả 429/partial/sai schema theo kịch bản cố định; agent phải recover hoặc giới hạn kết luận |
| Phân tích nhiều bước | 3–5 bước phụ thuộc dữ liệu, nguồn bổ sung chỉ xác định sau bước trước; không chỉ batch extraction nhiều mã |
| Báo cáo ngắn | Kết luận, số liệu hỗ trợ, rủi ro và giới hạn dữ liệu; rubric có dealbreakers, tránh chấm văn phong thay correctness |

Một đợt sau nên có holdout tách theo **thực thể + tài liệu/kỳ + snapshot**, còn template có thể chia sẻ có chủ đích. Không tự coi mọi template giống nhau là contamination. Nếu thêm settlement T+2, phải freeze lịch ngày làm việc và quy chế nguồn chính thức; VSDC có mô tả thay đổi thời gian thanh toán, phù hợp làm dữ liệu nguồn hơn lời nhắc chung của model. [VSDC](https://vsdc.vn/vi/ad/152750).

## 5. Đối chiếu benchmark đã công bố

| Benchmark | Cách làm đáng học | Áp dụng cho repo này |
|---|---|---|
| FinanceBench | Câu hỏi có human gold, justification, evidence document/page; bộ public là mẫu của bộ lớn hơn | Lưu evidence nguồn gốc, kiểm tra người; không chỉ tự sinh số từ MCP |
| FinQA | Có reasoning program và execution answer; private test không cung cấp intermediate gold | Lưu công thức/input references; test kín và baseline không đọc tool; chú ý FinQA từng sửa lỗi format gây label leakage |
| ConvFinQA | Đo chuỗi suy luận số qua hội thoại | Thêm một ít task follow-up có state, khi scope sản phẩm thực sự cần |
| Finance Agent v2.1 | Shared harness để so model; tool workflow, rubric partial credit có lỗi trọng yếu và all-pass riêng | Ta so harness nên giữ model cố định; mượn cách chấm completeness cho report, không bê nguyên thiết kế so model |
| τ-bench | Kiểm tra trạng thái cuối và pass^k qua nhiều trial | Kiểm tra artifact/evidence cuối và stability thật; không nhầm pass@k với pass^k |
| FinBen | Taxonomy phủ nhiều mặt tài chính | Dùng làm coverage checklist; chưa cần mở rộng sang trading/backtest nếu mục tiêu hiện tại là QA/analysis |

Nguồn chính: [FinanceBench repo](https://github.com/patronus-ai/financebench), [FinQA repo](https://github.com/czyssrs/FinQA), [ConvFinQA paper](https://arxiv.org/abs/2210.03849), [Finance Agent methodology](https://www.vals.ai/benchmarks/fabv2-1), [τ-bench paper](https://arxiv.org/abs/2406.12045), [FinBen paper](https://arxiv.org/abs/2402.12659).

Không cần mua/copy bộ benchmark của họ. Phần có giá trị nhất là evidence độc lập, endpoint đo rõ ràng, private split đúng nghĩa, kiểm định grader và theo dõi chi phí toàn pipeline.

## 6. Smoke mới và lựa chọn provider

Chỉ chạy Gemini 3.5 Flash Lite; timeout 90 giây/trial, không retry; dừng arm khi lỗi hạ tầng. Normalize key trong process chạy smoke vì key Google môi trường trả **401**, còn key trong auth OpenTrading hoạt động. Không thay key/config toàn máy.

| Arm | Quote | Aggregate | Refusal | Kết luận |
|---|---|---|---|---|
| OpenCode | PASS, 44,3s | PASS, 29,8s | ERROR 429, 14,6s | Có đường chạy thành công; lộ skill inheritance và thiếu điều tiết quota |
| DSH | ERROR 400, 37,2s | Không chạy | Không chạy | `Function call is missing a thought_signature`; route Google OpenAI-compatible chưa tương thích tool loop này |
| OpenTrading | PASS, 14,8s | PASS, 16,8s | PASS, 35,3s | Ba task hoạt động; vẫn cần sửa parity và telemetry |

Tổng **7 trial, 5 pass, 2 lỗi hạ tầng**. Không dùng bảng này để kết luận OT tốt hơn: chưa cùng điều kiện skills, effort, transport và quota; đây là kiểm tra adapter, không phải main evaluation. Không retry để biến lỗi đã quan sát thành kết quả “sạch”.

Provider discovery NVIDIA trả 200, có 85 model, gồm Granite 3B và một số model nhỏ. Chưa gọi inference NVIDIA vì Google đủ cho thử nghiệm có giới hạn. **Có tên trong `/models` không chứng minh hỗ trợ tools hoặc ổn định**; embedding/safety model nhỏ không dùng làm chat agent. Muốn fallback, chọn model chat có function-calling đã kiểm tra, chạy cùng một model đó ở cả ba arm và ghi tách kết quả. Không trộn model theo từng arm.

**Beam Free → DeepSeek V4.1 Flash medium:** đây là hai giai đoạn khác nhau, hợp lý cho tiết kiệm. Beam pass chỉ kiểm tra hạ tầng trên Beam; đổi sang DeepSeek vẫn phải canary đủ ba arm trước main. Medium phải được xác nhận trên request thực gửi, không chỉ trong file config. Provider OpenCode Go chưa được runner hiện tại wiring/verify đồng bộ cho cả ba arm.

Go công bố Beam miễn phí có giới hạn thời gian/địa bàn, quota DeepSeek theo tháng/tuần/5 giờ, và lỗi thiếu session metadata trên một số adapter DSH. Dùng User-Agent riêng, session ID ổn định. Tài khoản chưa mua nên chưa xác minh allowance. [Tài liệu OpenCode Go](https://opencode.ai/v2/docs/console/go/).

Go được mô tả cho coding-agent traffic; cần xác nhận nhà cung cấp hỗ trợ workload tài chính này.

## 7. Kế hoạch khả thi trong một tuần: 04–10/11/2026

Smoke NVIDIA lịch sử: mean **175,4 giây/trial**, median 168 giây. Với pause 15 giây:

- Main 200 × 3 arm × 3 runs = **1.800 trials ≈95,2 giờ**.
- Main + holdout 50 × 3 × 3 = **2.250 trials ≈119,0 giờ**, chưa pilot/A-A/retry/fix.
- Nếu chạy hết timeout cũ theo task, riêng main có trần khoảng **1.110 giờ**. Đây là worst case, không phải dự báo.

Các ước lượng trên suy từ **9 trial, 3 task**, provider khác Go và độ khó ít đại diện; chỉ dùng cảnh báo lịch, không hứa completion. Không thể lấy số request ước tính của nhà cung cấp thay thời gian/token đo trên workload thật.

| Ngày | Việc hoàn thành | Gate |
|---|---|---|
| 04/11 | Chốt estimand/track; vá matcher, schema/grader, chặn web và global skills | Tất cả counterexample sai phải bị chặn; đáp án hợp lệ vẫn pass |
| 05/11 | Chuẩn hóa runner/usage/attempts; smoke nhỏ; kiểm tra source 20–30 thẻ; pilot đại diện và A/A | DSH tool loop chạy được; không missing usage/manifest; không đọc ngoài/mạng ngoài |
| 06/11 | Canary DeepSeek medium qua Go nếu đã mua; freeze code/tasks/pricing/analysis và chọn full hay subset trước nhìn kết quả main | Ba arm cùng route/effort; dự báo giờ và allowance nằm trong budget |
| 06–09/11 | Chạy main theo lịch block hoán vị arm; theo dõi quota; mỗi block hoàn tất cả ba arm | Không chỉnh harness/đề theo kết quả; circuit breaker lỗi provider |
| 09–10/11 | Mở holdout sau freeze đúng quy chế; phân tích paired, spot-check bất đồng; viết kết luận | Báo coverage, missing trials, CI, failure modes và giới hạn |

**Quyết định quy mô:** giữ 200 main nếu runtime/quota sau pilot chứng minh còn đủ thời gian cộng ít nhất 20% dự phòng. Nếu không, freeze trước main một **subset 120 task** phân tầng domain/family và mức khó, 3 runs/arm; giữ kết quả tách với kế hoạch 200. Main120 + holdout50 đủ 3 runs là 1.530 trial, khoảng **80,9 giờ** theo tốc độ lịch sử; pilot/A-A vẫn tính riêng. Đây là sửa pre-register có công khai, không phải tùy ý dừng khi thấy arm yêu thích thắng. Subset không làm bộ đề tốt hơn tự động và làm CI rộng hơn.

**Vận hành bắt buộc:**

1. Rate limiter theo request/token/provider dùng chung mọi arm, tôn trọng Retry-After. Trial pause không kiểm soát được 15 request trong một agent loop.
2. Retry chỉ lỗi hạ tầng đã phân loại; mỗi attempt session/workspace mới. Không retry đáp án sai/format sai để chọn best-of.
3. Persistent schedule + resume idempotent + attempt ledger; `--out` đã tồn tại không được chạy đè. Khi dừng phải giữ đủ log.
4. Timeout/token/request cap freeze sau pilot. Report harness khác số request là kết quả cần đo, nhưng mọi arm phải có cùng cap chung đã nêu.
5. Freeze manifest: commit/dirty diff, binary/plugin versions, prompts, skills hashes, schema/catalog hash, snapshot hashes, model alias/resolved identity khi có, effort, endpoint, timestamps, price source.
6. Sandbox dùng allowlist tool thực, không chỉ prompt; gold/grader ở process/mount khác, credentials không vào workspace agent. Đo và báo residual isolation limits.
7. Holdout hiện chỉ được guard bằng flag; cần receipt/manifest để ngăn vô tình mở lại. Nếu thêm holdout mới, quản lý version và tách khỏi quá trình tuning.

**Budget Go:** mức DeepSeek công bố $100/tháng tương ứng $50/tuần, $20/5 giờ; xác minh dashboard trước chạy. Phí $10/tháng khác token allowance. Lưu allowance response, tính cache và peak/off-peak. Giá repo khớp off-peak Go; nhãn “Off-Peak NIM” sai căn cứ.

## 8. Checklist chấp nhận trước main

- [ ] Counterexample matcher/grader đều fail như mong đợi; semantic-valid variants pass; test quanh biên tolerance.
- [ ] Ba arm có inventory prompt/skills/plugins/tools/permissions được ghi; không kế thừa user state.
- [ ] Có request chứng minh cùng model/provider/medium; không side-model không được tính budget.
- [ ] Server ledger khớp call ID; tổng usage đối soát log/provider; missing là N/A.
- [ ] Retry không làm mất attempts; latency/cost có tổng, timeout không được tính success primary.
- [ ] Implement primary metrics, stable3/3 coverage, trap confusion matrix và paired analysis; model/price lấy từ frozen manifest.
- [ ] Duyệt nguồn độc lập cho mẫu task; sửa label khó, fiscal period, provenance namespace; không sửa holdout để tối ưu.
- [ ] Run plan còn đủ thời gian/quota; full/subset đã chọn trước main; canary ba arm pass.

Các ô trên **chưa được đánh dấu hoàn tất** bởi review này. Runners, graders, tasks/gold và cấu hình gốc vẫn giữ nguyên để người xây dựng xem được đầy đủ vấn đề và quyết định nâng cấp theo thứ tự; README có thêm liên kết đến review. Các script audit mới là công cụ tái hiện bằng chứng, không phải runner/grader v2 đã sửa.

## 9. Tái hiện

```bash
python3 -m pytest tools/tests/ -q
python3 tools/audit_benchmark.py --out audits/2026-11-04
```

Hai lệnh không gọi model. Script audit không chấm holdout, không regenerate task, chỉ ghi evidence trong thư mục output.

```bash
python3 tools/audit_provider_probe.py
python3 tools/audit_smoke.py --timeout 90 --out results/audit-gemini-new-run
```

Hai lệnh sau có gọi mạng/model theo giới hạn trong script. Smoke chỉ dùng Gemini 3.5 Flash Lite và ba task smoke; từ chối dùng lại output directory. Raw logs/config chứa auth copy được giữ trong `results/` vốn bị gitignore; không đưa chúng lên git. Artifacts trong `audits/` chỉ chứa metadata/diagnostics đã chọn, không chứa key.
