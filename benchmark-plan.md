# BENCHMARK ĐÁNH GIÁ HARNESS TÀI CHÍNH — KẾ HOẠCH

> Văn bản xây **từng phần** — hiện có: **Phần 1** (tiêu chí đo) · **Phần 2** (môi trường) · **Phần 3** (bộ task) · **Phần 4** (mở rộng 400) · **Phần 5** (thiết kế chi tiết bộ 200 task, đối chiếu MCP thật).

---

# PHẦN 1 — TIÊU CHÍ ĐO

## 1.0. Nguyên tắc khung đo

| # | Nguyên tắc | Nội dung |
|---|---|---|
| 1 | **Không cộng điểm tổng** | 5 tiêu chí báo dạng **dashboard từng cột** — không cộng thành 1 điểm duy nhất (cộng điểm = tự chế trọng số, mất khả năng trả lời từng câu hỏi riêng) |
| 2 | **Log giàu, bảng nghèo** | Mọi dữ liệu thô (usage từng call, tool spans, timestamp) nằm trong log JSONL; bảng kết quả chỉ trình bày 5 cột chính. Khi nảy sinh câu hỏi mới → mở log trả lời, không cần benchmark lại |
| 3 | **Thiếu số đo → N/A, không ghi 0** | Harness nào không xuất telemetry (VD usage) → cột ghi N/A kèm tỷ lệ coverage |
| 4 | **So sánh trong cùng điều kiện** | Mọi đối chiếu giữa arm chỉ hợp lệ khi cùng mức độ khó (L), cùng snapshot dữ liệu, cùng model |
| 5 | **Một bảng giá duy nhất** | Chi phí định giá lại mọi arm bằng cùng 1 bảng giá, freeze lúc pre-register |

## 1.1. Năm tiêu chí chính

### ① Trả lời chính xác (Success)

| | |
|---|---|
| **Mô tả — đo để làm gì** | Tiêu chí cốt lõi: harness trả lời **đúng số, đúng đơn vị, đúng kỳ** so với đáp án chuẩn. Trả lời câu hỏi "arm nào cho kết quả đáng tin về mặt dữ liệu". Đây là lý do tồn tại của bộ câu hỏi: **mỗi task có gold answer sinh bằng script oracle, chấm hoàn toàn bằng code, không chấm tay** |
| **Cách tính** | Mỗi trial, harness phải trả `answer.json` theo schema bắt buộc `{value, unit, period, source}`. Grader đối chiếu với gold: `value` trong dung sai làm tròn (±0,5%) **VÀ** `unit` đúng **VÀ** `period` đúng → đúng. **Sai đơn vị hoặc sai kỳ = sai**, dù con số "trông đúng" (đặc thù tài chính: sai đơn vị/kỳ = ra quyết định sai tiền). Success = số trial đúng ÷ mọi trial đã bắt đầu. Báo kèm **theo từng mức độ sâu pipeline L1→L5** (định nghĩa từng mức ở phần thiết kế bộ task) |
| **Nguồn & chi phí** | Grader code tự động · cần bộ task + gold (xây ở phần sau) · chi phí đo = 0 |

### ② Stable-correct (đúng cả 3 runs)

| | |
|---|---|
| **Mô tả — đo để làm gì** | Đo **độ tin cậy khi dùng một lần**: % task mà cả 3 lượt chạy đều đúng. Khác Success (trung bình) — hai cột đặt cạnh nhau đọc ra "tính cách" arm: Success ≈ Stable-correct → arm ổn định; Success cao hơn hẳn Stable-correct → arm "hên xui" (đôi khi đúng đôi khi sai, không dùng được trong thực tế). Tham chiếu: SWE Atlas đo Pass^k, Aider đo pass@2 — đây là metric hiếm nhưng có tiền lệ |
| **Cách tính** | Với mỗi task chạy 3 runs độc lập (cùng snapshot, session sạch): cả 3 runs đều đạt theo grader ① → Stable-correct = 1; ngược lại = 0. Stable-correct = số task đạt-3/3 ÷ tổng task. Báo kèm theo mức L |
| **Nguồn & chi phí** | Miễn phí — tận dụng 3 runs bắt buộc của thiết kế. Lưu ý: 2 runs là mức tối thiểu của thiết kế (single-run dao động ±2,2–6,0 điểm theo nghiên cứu 60.000 trajectory); 3 runs cho phép tính Stable-correct |

### ③ Chống bịa (FP-rate — Hallucination)

| | |
|---|---|
| **Mô tả — đo để làm gì** | Tiêu chí **toàn vẹn/trung thực**: khi dữ liệu **không tồn tại** (kỳ chưa công bố, mã không niêm yết, số không có), harness có **bịa ra con số** không. FP = false positive = trình bày một con số như thật cho dữ liệu không có. Trong tài chính, bịa số = ra quyết định sai tiền — đây là lỗi nguy hiểm nhất và là tiêu chí **không benchmark harness nào đo trực tiếp** (ABC checklist phê bình chính điểm này). Kỳ vọng kiểm chứng: harness có nguyên tắc trung thực (OpenTrading) FP thấp hơn harness tổng quát |
| **Cách tính** | Bộ task chứa **task bẫy**: câu hỏi về dữ liệu không tồn tại. Grader code kiểm tra `answer.json`: (a) trường `value` có số, hoặc (b) văn bản khẳng định một con số cho dữ-kiệu-mất-tích → **FP = 1**. Trả lời từ chối có căn cứ ("chưa công bố", "không có mã này") → FP = 0. Task bẫy thường kèm **kỳ thay thế đúng** — trả lời kèm kỳ đúng được tính đúng luôn ở tiêu chí ①. FP-rate = số trial bịa ÷ tổng trial trên task bẫy. Trường hợp méo mó (vừa từ chối vừa "theo ước tính khoảng...") → đánh dấu ambiguous, spot-check người 10% |
| **Nguồn & chi phí** | Grader code tự động · cần task bẫy (L4 + field-trap rải trong task thường) · chi phí đo = 0 |

### ④ Tốc độ (Time p50/p90)

| | |
|---|---|
| **Mô tả — đo để làm gì** | Trả lời **"người dùng phải chờ bao lâu?"**. p50 (trung vị) cho tốc độ điển hình; **p90** bắt những lượt chậm bất thường. Chỉ nhìn p50 sẽ che mất "đôi khi rất chậm" — trong khi trải nghiệm thật phụ thuộc cả p90. Báo riêng theo mức L (task sâu tự nhiên lâu hơn — so arm phải trong cùng mức) |
| **Cách tính** | `Time = finished_at − started_at` (đồng hồ monotonic) tính từ lúc nhận prompt đến câu trả lời cuối. p50, p90 trên toàn bộ trial của arm; phân tách theo mức L. Lượt lỗi/timeout tính vào phân phối thời gian (không loại) — ghi rõ trạng thái |
| **Nguồn & chi phí** | Log trial · chi phí đo = 0. Không đo TTFT làm metric chính (bị provider chi phối, không phải thuộc tính harness) — vẫn ghi trong log để debug |

### ⑤ Chi phí (Cost/task)

| | |
|---|---|
| **Mô tả — đo để làm gì** | Quy mọi arm về **một con số tiền so sánh được**: "nếu mua API, mỗi câu hỏi tốn bao nhiêu". Tại sao không dùng Tokens là đủ: output token đắt hơn input ~4–5 lần, cached token rẻ hơn ~10 lần → hai arm cùng tổng token có thể hóa đơn chênh lớn. Cost/task là cột chuẩn của FrontierHarness / CursorBench / vals.ai |
| **Cách tính** | `Cost/trial = Σ mọi lần gọi model: (input × p_input + output × p_output + cached × p_cache)`. **Một bảng giá duy nhất** áp cho cả 3 arm (không dùng hóa đơn thật — mỗi provider một giá), freeze vào pre-register. `Cost/task` = trung bình Cost/trial; báo kèm per-mức L. Ghi kèm **tokens/trial** trong ngoặc để debug (không phải cột chính) |
| **Nguồn & chi phí** | Usage từ log + bảng giá freeze · chi phí đo = 0 |

## 1.3. Khảo sát key opencode-go (ngày khảo sát: 01/11/2026)

Model dự định cho benchmark: **DeepSeek V4.1 Flash** qua opencode-go.

| Hạng mục | Kết quả |
|---|---|
| **Key hiện tại trên máy** | ❌ **Đã hết hạn** (`api_key_expired`) — phải tạo key mới dạng `oc_sk_...` tại [Console → Account → Personal API keys](https://opencode.ai/v2/docs/console/harnesses/#get-an-api-key); đăng nhập lại **không** tự gia hạn key cũ |
| **Bản chất dịch vụ** | Trả phí: Go **$10/tháng** · Go Plus $40 · Go Teams $20/thành viên — [docs Go](https://opencode.ai/v2/docs/console/go/) |
| **Endpoint** | `https://opencode.ai/inference/go/openai/v1/chat/completions` (OpenAI-compatible; Console tự dịch giữa các API — [Base URLs](https://opencode.ai/v2/docs/console/harnesses/#base-urls)) |
| **Header bắt buộc** | `x-opencode-session: ses_...` ổn định mỗi conversation — thiếu → HTTP 400 `MissingSessionID` (probe thực tế 01/11); kèm UA tự định danh (VD `opentrading/0.1.0`) |
| **Hạn chế model free** | Beam Free / Iceman (unlimited) **chỉ chạy trong OpenCode** — harness khác nhận HTTP 403 dù có key ([Harnesses](https://opencode.ai/v2/docs/console/harnesses/)) |

**Model dự định: DeepSeek V4.1 Flash — thời lượng sử dụng:**

| Thông số | Giá trị |
|---|---|
| Limit Go plan | **$100/tháng** — 5 giờ = 20% (~$20) · tuần = 50% (~$50) |
| Giá Off-Peak | input $0,15 · output $0,60 · cached read $0,003 (per 1M token) |
| Giá Peak | input $0,30 · output $1,20 · cached read $0,006 |
| Khung giờ | Peak = 01:00–04:00 & 06:00–10:00 UTC (= 08:00–11:00 & 13:00–17:00 giờ VN, T2–T6) → **chạy benchmark đêm giờ VN = Off-Peak, giá thấp nhất** |
| Riêng tư | Không dùng để train · retention 0 ngày |
| Telemetry | Mỗi response trả `opencode.allowance` — track hạn mức thật (bổ sung cho Cost repriced ở 1.1-⑤) |
| **Thời lượng cho benchmark** | Go plan ước **~216.670 request/tháng** cho model này (pattern coding-agent chuẩn); benchmark 200-task cần ~46k request (3 arm dùng chung key) → **đủ chạy 1 đợt 200-task trong ~1 tuần quota, còn dư cho re-run và replication model-2** |

## 1.4. Setup OpenTrading và DSH dùng key opencode-go

### OpenTrading — dùng được, cần 2 chỉnh nhỏ

| Bước | Việc |
|---|---|
| 1 | Tạo key `oc_sk_...` mới từ [Console](https://opencode.ai/console) (workspace đã subscribe Go) |
| 2 | Lưu key vào auth file của OpenTrading (cùng format `auth.json` opencode — `src/core/auth.ts` có sẵn `setKey()`) hoặc env |
| 3 | Provider `opencode-go` **đã hỗ trợ sẵn** (có trong catalog + `LITE_SHORTLIST` của `src/core/subagents/model-pick.ts`); trỏ baseURL `https://opencode.ai/inference/go/openai/v1`, model `deepseek-v4.1-flash` |
| 4 | **Bắt buộc — sửa code ~5 dòng**: thêm header `x-opencode-session` (giá trị ổn định mỗi phiên) + UA `opentrading/0.1.0` vào fetch wrapper cho provider này (đã có sẵn pattern custom-fetch: `geminiFetch`) |
| 5 | Test: 1 task tra cứu chạy trọn — không dính HTTP 400 `MissingSessionID` |

### DSH — cấu hình được nhưng bị chặn một phần phía upstream

| Bước | Việc |
|---|---|
| 1 | Key `oc_sk_...` vào `~/.dsh/.env` (VD `OPENCODE_GO_API_KEY=oc_sk_...`) |
| 2 | Thêm provider route theo schema `llm-pi-ai.providers` (pattern có sẵn trong `settings.yaml.imported`): `opencode-go: {apiKeyEnv: OPENCODE_GO_API_KEY, api: openai-completions, baseURL: https://opencode.ai/inference/go/openai/v1, models: [deepseek-v4.1-flash, glm-5.3-flash]}` |
| 3 | ⚠️ **Hạn chế upstream**: DSH thuộc danh sách *"known problematic clients"* của doc Go — session header thiếu trên một số model path → path đó dính `MissingSessionID`; Go nhận native header của dsh trên path có gửi. Track tại [discussion #5495](https://github.com/deepseek-ai/deepseek-harness/discussions/5495). Schema provider dsh **không có tùy chọn custom-header** (đã grep source) → không vá qua config, phải chờ upstream |
| 4 | ⚠️ **Kiểm tra trước khi setup**: `~/.dsh/settings.yaml` hiện **không tồn tại** (chỉ còn `settings.yaml.imported`, 26/10 — nghi do dsh update migrate) → xác nhận trạng thái config dsh hiện tại, có thể phải khôi phục routes NVIDIA/Google |

### Tài liệu tham chiếu

| Tài liệu | Link |
|---|---|
| Trang Go chính thức (Where can I use it · Usage limits · Endpoints) | https://opencode.ai/v2/docs/console/go/ |
| Trang Harnesses (Get an API key · Base URLs · Sessions) | https://opencode.ai/v2/docs/console/harnesses/ |
| Console — tạo key | https://opencode.ai/console |
| Vấn đề DSH session-header | https://github.com/deepseek-ai/deepseek-harness/discussions/5495 |

---

# PHẦN 2 — XỬ LÝ MÔI TRƯỜNG BENCHMARK

## 2.0. Ba arm so sánh

| Arm | Vai trò | Pin |
|---|---|---|
| **OpenTrading** | Đối tượng đo (harness tài chính) | pin commit main tại lúc freeze |
| **OpenCode** | Đối chứng sản phẩm đầy đủ | pin version CLI |
| **DSH (DeepSeek Harness)** | Đối chứng thứ hai | pin version 0.1.x |

Cùng 1 model cho cả 3 arm: **DeepSeek V4.1 Flash qua opencode-go** (xem 1.3).

## 2.1. Kiến trúc môi trường

```
driver (orchestrator — nơi duy nhất 3 arm khác nhau là runner)
│
├── tasks/                    thẻ task chuẩn (đề + answer_schema + gold + oracle)
├── env/
│   ├── workspace-template/   thư mục sạch sao chép mỗi trial (cùng file, cùng quyền)
│   ├── mcp-snapshot/         MCP server replay dữ liệu GHI-RECORD — cùng dữ liệu cho cả 3 arm
│   └── skills-pack/          cùng nội dung skill, 3 kiểu đóng gói
├── runners/
│   ├── run-opencode.*        opencode run --format json
│   ├── run-dsh.*             dsh headless + go-header-proxy (xem 2.3)
│   └── run-opentrading.*     headless CLI + patch x-opencode-session
├── telemetry/                chuẩn hóa usage → 1 schema trial JSONL (xem 2.5)
├── grader/                   answer.json × gold → Success / FP / error-type
└── results/                  trials.jsonl + raw logs
```

## 2.2. Lớp runner — đặc tả từng arm (nơi duy nhất các arm khác nhau)

| Arm | Lệnh headless | Lấy answer | Lấy telemetry | Việc chuẩn bị |
|---|---|---|---|---|
| **OpenCode** | `opencode run --format json` (pin version) | parse JSON output | usage từ output/events | pin + test 1 task |
| **OpenTrading** | headless CLI (pin commit) | ghi `answer.json` | events/usage | **+ patch `x-opencode-session` & UA** (đã đặc tả ở 1.4) |
| **DSH** | `dsh --profile headless` (pin 0.1.x) | parse session log / output | session log (turn/step events) | **+ go-header-proxy** (2.3) + cấu hình provider route & MCP qua profile patch |

## 2.3. Rào cản DSH và giải pháp go-header-proxy

DSH thuộc *"known problematic clients"* của opencode-go: session header **thiếu trên một số model path** → path đó dính HTTP 400 `MissingSessionID`; schema provider dsh không có tùy chọn custom-header; upstream fix track tại discussion #5495.

**Giải pháp — chặn đầu bằng local proxy, không sửa code dsh:**

```
dsh ──(baseURL: http://127.0.0.1:PORT)──► go-header-proxy ──(thêm x-opencode-session + UA)──► opencode.ai/inference/go
```

- Proxy ~50 dòng (bun/node): inject `x-opencode-session` (driver cấp session id ổn định mỗi conversation) + UA, forward nguyên request/response
- dsh chỉ cần trỏ provider route `baseURL: http://127.0.0.1:PORT` — giữ nguyên pin version
- Tác dụng phụ có lợi: proxy là điểm log tập trung mọi request của arm DSH (kiểm chứng telemetry chéo)
- Điều kiện bắt buộc: proxy **trong suốt** — streaming SSE pass-through nguyên vẹn, không đụng body (kiểm ở gate G-E5)

## 2.4. Tám trục "cùng điều kiện" — khóa cứng cho 3 arm

| Trục | Cơ chế | Ghi chú riêng từng arm |
|---|---|---|
| **1. Model** | Cùng base URL `…/inference/go/openai/v1`, cùng key `oc_sk_`, cùng model `deepseek-v4.1-flash`, cùng temp/max_tokens; mỗi trial = 1 session mới → session header mới ổn định trong trial | OpenCode: gửi native ✅ · OpenTrading: patch (1.4) · DSH: qua proxy (2.3) |
| **2. Dữ liệu** | MCP snapshot replay + hash công bố; chặn mạng ngoài | OpenCode: MCP native · **DSH: MCP qua profile patch** (`mcp__<server>__tool`) · OpenTrading: native |
| **3. Kiến thức** | Skills cùng nội dung, 3 kiểu đóng gói; ma trận đóng gói ghi vào báo cáo | **DSH: skills qua patch profile (Definition/Provider/Consumer)** |
| **4. Workspace** | Fresh copy từ workspace-template mỗi trial; gold nằm NGOÀI workspace; cùng quyền ghi | — |
| **5. Ngân sách** | `time_limit_min` per task + token/step cap đặt đều nơi harness hỗ trợ | dsh có round cap/goal — đặt tương đương |
| **6. Quyền** | Full-auto cho cả 3 | opencode: yolo-mode · **dsh: danger-full-access/allow preset** · OpenTrading: full-auto |
| **7. Lịch chạy** | Xoay vòng thứ tự arm; không 2 arm chạy trùng khung giờ khi đo Time; cùng 1 máy | ghi concurrent-load lúc chạy |
| **8. Sạch** | Session mới mỗi trial · task chưa chạy trước eval (debug chỉ trên smoke set 3 task) · 1 attempt mỗi cell | — |

## 2.5. Telemetry schema chung (1 dòng JSONL/trial)

```json
{ "trial_id": "...", "arm": "opentrading", "model": "deepseek-v4.1-flash",
  "level": "L2", "task": "fin-lookup-03", "run": 2, "status": "ok|error|timeout",
  "tokens": {"input": 0, "output": 0, "cached": 0, "preamble_first_call": 0},
  "requests": 0, "wall_ms": 0, "answer_path": "...", "usage_coverage": 1.0,
  "session_id": "ses_...", "key_source": "opencode-go", "snapshot_hash": "...", "started_at": 0 }
```

## 2.6. Gates sẵn sàng (trước khi chạy pilot)

| Gate | Tiêu chí pass |
|---|---|
| **G-E1** | Cả 3 runner chạy trọn 1 task smoke, sinh answer + log đủ |
| **G-E2** | MCP snapshot replay **giống hệt** qua 3 arm (đối chiếu hash + payload) |
| **G-E3** | Telemetry trích được 3/3 arm (coverage 100% hoặc ghi N/A rõ) |
| **G-E4** | Session header có mặt **100% request** của cả 3 arm — với DSH phải xác nhận qua **mọi model path** (gate dễ fail nhất — đúng lỗi #5495) |
| **G-E5** | go-header-proxy trong suốt: streaming SSE nguyên vẹn, không đổi body |
| **G-E6** | Driver xoay vòng 3 arm không ôm lẫn session/workspace |

## 2.7. Thứ tự xây hạ tầng

1. **go-header-proxy + provider route DSH** (mở khóa arm DSH sớm — rủi ro lớn nhất)
2. MCP snapshot server (recording + replay)
3. 3 runner + driver
4. Workspace template + task format
5. Telemetry normalizer
6. Grader + results store

Ước tính: mỗi item 0,5–1 ngày → tổng ~3–5 ngày làm việc trước pilot.

## 2.8. Tài liệu tham chiếu Phần 2

| Tài liệu | Link |
|---|---|
| Harbor task format (task.toml / instruction / environment / solution / tests) | https://github.com/harbor-framework/terminal-bench |
| Golden checkpoint + fresh restore mỗi run | https://runta.com/blog/introducing-frontierharness-eval |
| Snapshot runtime (restore thay vì replay Dockerfile) | https://www.tensorlake.ai/blog/tensorlake-harbor-environment-runtime |
| Inspect AI — framework eval tái lập (UK AISI) | https://inspect.aisi.org.uk/ |
| Go sessions + session header bắt buộc | https://opencode.ai/v2/docs/console/go/#where-can-i-use-it |
| Vấn đề DSH session-header (upstream) | https://github.com/deepseek-ai/deepseek-harness/discussions/5495 |

---

# PHẦN 3 — BỘ TASK (200 TASK)

## 3.0. Nguồn task

| Quyết định | Nội dung |
|---|---|
| Viết tay có kiểm soát theo quy trình **FinanceBench** | Không dùng trực tiếp bộ có sẵn (FinanceBench/CFA/FinQA sai domain Mỹ/SEC, sai ngôn ngữ, sai format MCQ); không có bộ agentic tài chính VN |
| Minh bạch = quy trình kiểm định công bố + mở dataset + gold từ oracle | Precedent: Terminal-Bench 100% viết tay và là chuẩn ngành |

## 3.1. Taxonomy câu hỏi — 5 mức L1→L5

| Mức | Loại (FinanceBench) | Định nghĩa | Ghi chú |
|---|---|---|---|
| **L1** | Single-step extraction | 1 tool call, 0 suy ra | — |
| **L2** | Multi-step computation | 2–3 call phụ thuộc + 1 bước tính | — |
| **L3** | Comparative / aggregate | ≥4 call hoặc batch ≥5 mã | — |
| **L4** | **Unanswerable / verification** | Đối chiếu đa nguồn hoặc premise sai (bẫy) | ⭐ Kế thừa thiết kế *"unanswerable questions"* của FinanceBench — đo hallucination (tiêu chí FP-rate ở 1.1-③) |
| **L5** | Multi-part report | Báo cáo có provenance từng số | Mở rộng ngoài taxonomy FinanceBench |

## 3.2. Nhãn độ khó — SWE-bench Verified convention

- Độ khó = **thời gian ước tính người làm**: `<15 phút · 15–60 phút · >60 phút`
- Báo cáo Success/Stable-correct theo **nhóm L1→L5 × băng thời gian**; phân bố tự nhiên, không ép đường cong

## 3.3. Quy mô (chốt)

| Thành phần | Số lượng |
|---|---|
| **Pilot** | **24 task** (L1×5 · L2×6 · L3×6 · L4×4 · L5×3) |
| **Main** | **200 task** (40/mức) × 3 arm × **3 runs** = **1.800 trial** |
| Holdout kín | **60** (thực thể hoàn toàn mới, niêm phong) |
| A/A noise floor | 20 cặp (40 trial) |
| Mini-suite C7 + C8 | 36 + 36 trial mock |
| Thực thể | ≤2 task/thực thể, pool ~150; ~60% VN stock · 20% crypto · 10% vàng/FX · 10% macro |
| **Ngưỡng khẳng định** | **Gap ≥7 điểm** (d=13%, McNemar paired, Holm) |

> **Pilot là gì:** đợt chạy thử nghiệm 24 task đầu tiên trước khi chạy chính thức — ① kiểm tra hạ tầng end-to-end (3 arm, log, grader), ② đo tham số thật (discordance, pass-rate từng nhóm) để sửa bộ task **trước** khi tốn quota lớn, ③ 3 runs như main. Sau pilot, 24 task này nằm luôn trong bộ 200. Quy trình chuẩn mà mọi benchmark nghiêm túc đều có.

Khớp hạn mức: ~48k request ≈ 22% hạn mức tháng của DeepSeek V4.1 Flash (Go plan, xem 1.3); chi phí quy đổi ~$22; wall-time ~3–4 tuần với 2–3 workers.

## 3.4. Định dạng task — chuẩn Harbor

```
tasks/fin-lookup-03/
├── task.toml          # metadata: id, mức L1–L5, băng thời gian người, loại FinanceBench,
│                      #            snapshot_date, field-traps
├── instruction.md     # đề (ngắn, tự nhiên)
├── environment/       # workspace + cấu hình MCP snapshot cho task
├── solution/          # oracle script do người viết + gold answer
└── tests/             # grader: answer.json × gold → điểm + lý do trượt
```

Gold trong `solution/ + tests/`, **giữ ngoài workspace harness** khi chạy.

## 3.5. Quy trình kiểm định — 2 lớp

| Lớp | Nội dung |
|---|---|
| **A. 3 check Terminal-Bench** | Mỗi task: **giải-được** (oracle chạy ra gold) · **realistic** (đề như việc thật) · **well-specified** (gold duy nhất tồn tại) |
| **C. Duyệt 2 lượt độc lập** (bạn + 1 agent; any-flag → sửa/loại — SWE-bench Verified thu gọn) | Checklist 5 mục: ① realistic ② well-specified ③ gold đúng ④ **memory-check** — reviewer thử trả lời KHÔNG tool; task phải FAIL khi không tool (chống contamination nội bộ) ⑤ **ambiguity-check** thực địa (đề mơ hồ → loại) |

## 3.6. Freeze + pre-register

Mỗi wave: **freeze + hash task + gold → pre-register**; không sửa sau freeze; task loại vì hạ tầng ghi exclusion log.

## 3.7. Gates phần task

| Gate | Tiêu chí pass |
|---|---|
| **G-T1** | Pilot 24 qua cả 3 arm; pass-rate per nhóm ghi nhận trung thực |
| **G-T2** | Oracle/gold pass 100%; discordance đo được ≤25% |
| **G-T3** | Freeze + hash + pre-register hoàn tất trước main-run |

## 3.8. Tài liệu tham chiếu Phần 3

| Tài liệu | Link |
|---|---|
| FinanceBench (paper · 150-câu mẫu open · taxonomy + unanswerable) | https://arxiv.org/abs/2311.11944 · https://github.com/patronus-ai/financebench |
| Terminal-Bench (task format · 3 check · oracle) | https://github.com/harbor-framework/terminal-bench |
| SWE-bench Verified (nhãn thời gian người · lọc đa người) | https://openai.com/index/introducing-swe-bench-verified |
| SWE-rebench (heuristic lọc mơ hồ/tool-call) | https://arxiv.org/abs/2505.20411 |
| CFA sets (tham khảo — không dùng: license + format) | https://huggingface.co/datasets/TheFinAI/en-cfa |
| VNFinEval (tham khảo VN — macro only) | https://www.semanticscholar.org/paper/47a3de88b0aaa7a1f00351012e7e4d37b19a3757 |

---

# PHẦN 4 — KẾ HOẠCH MỞ RỘNG LÊN 400 TASKS

> Trạng thái: **dự bị** — chỉ khởi động sau khi 200-task hoàn tất và phân tích xong.

## 4.0. Điều kiện khởi động

| Gate | Điều kiện |
|---|---|
| **G4a** | 200-task xong, exclusion <5%, telemetry thiếu <3% |
| **G4b** | Holdout re-check khớp kết quả chính (hướng thứ hạng không đổi) |
| **G4c** | A/A ổn định qua 2 lần đo; discordance thật đo được ≤13% |

## 4.1. Ba nguyên tắc mở rộng

1. **Adaptive allocation**: wave mới dồn task vào vùng discordant cao (gần knee từng arm) — không dàn đều
2. **Wave-based**: mỗi wave 40–65 candidates qua đủ quy trình kiểm định 3.5; spot-audit 10%/wave
3. **Đa dạng**: pool thực thể nới ~150 → **~250** (+small-cap, +crypto, +FX/macro, +cặp đa-nguồn, +composite)

## 4.2. Waves

| Wave | Candidates → giữ | Phân bổ |
|---|---|---|
| W5–W6 | 130 → 90 | Adaptive theo knee |
| W7 | 65 → 45 | Bù cân đối 80/mức |
| W8–W9 | 130 → 90 (bù thất bát) | Chốt đủ **400** (80/mức) |
| Kiểm định cuối | — | Re-run holdout + 20 cặp A/A mới + re-run oracle toàn bộ |

Tổng thực viết thêm ~320 candidates → 200 task mới. **Ngưỡng khẳng định mới: ~5 điểm**; per-level 80 task/mức → kết luận per-level hợp lệ (CI ±11đ).

## 4.3. Chi phí với hạ tầng opencode-go

| Hạng mục | Con số |
|---|---|
| Trials | 400 × 3 arm × 3 runs ≈ 3.600 + A/A + holdout ≈ **3.800** |
| Requests | ~95k ≈ **44% hạn mức tháng** DeepSeek V4.1 Flash (Go plan) → ~1,5–2 tháng quota |
| Chi phí quy đổi | ~$44 (trivial — không cần ngân sách API riêng) |
| Wall-time | ~760 giờ serial → **~5–8 tuần** với 2–3 workers |

## 4.4. Nâng cấp hạ tầng trước Wave 5

1. **SQLite results DB** thay JSONL phẳng (schema theo 2.5)
2. **Scheduler quota-aware + auto-resume** (checkpoint mỗi trial)
3. **Gold-freshness CI**: re-run toàn bộ oracle mỗi wave
4. **Dashboard**: burn/pass-rate tạm theo arm × mức
5. **Re-nhãn độ khó** (thời gian người) mỗi wave

## 4.5. Rủi ro & đối sách

| Rủi ro | Đối sách |
|---|---|
| Pha loãng chất lượng task về cuối | Spot-audit 10%/wave; tỷ lệ giữ <55% → dừng sửa quy trình |
| Snapshot/schema drift làm oracle gãy | Gold-freshness CI mỗi wave; pin version |
| Provider đổi hạn mức giữa chừng | Scheduler xoay pool; ghi nguồn key |
| Kết quả 200-task đã phân giải rõ | Có thể KHÔNG cần 400 — gate G4c cho phép dừng |

---

# PHẦN 5 — THIẾT KẾ CHI TIẾT BỘ 200 TASK

> Đối chiếu năng lực MCP opentrading thật (175 tools, khảo sát 01/11/2026). Nguyên tắc: **task chỉ tồn tại ở vùng dữ liệu xác định** — né 9 điểm mù/vùng nguy hiểm đã xác định (5.1).

## 5.1. Bản đồ an toàn dữ liệu

### 🟢 Vùng XANH — dùng tự do (dữ liệu đóng băng, xác định)

| Dữ liệu | Tools MCP |
|---|---|
| BCTC đã công bố (mỗi kỳ, từng dòng) | `financial_statements` · `financial_detail` · `vs_financeinfo` · `financial_ratios` · `vn_fundamentals` |
| Giá đóng cửa/nến lịch sử 1D | `vn_quote_history` · `vn_equity_ohlcv` · `market_candles_batch` · `vn_index_ohlcv` |
| Crypto OHLCV lịch sử | `vn_crypto_ohlcv` · `crypto_spot` (từ snapshot) |
| Vàng/FX lịch sử | `vn_msn_fx_gold` · `vn_retail_gold` · `vn_forex_ohlcv` · `yf_commodities` |
| Macro đã phát hành | `vs_indicator_data` (CPI/GDP) · `macro_events_vn` (lịch GSO) · `sbv_rates` · `fred_series` |
| Cổ tức/tách cổ phiếu lịch sử | `dividends_splits` |
| Tham chiếu tĩnh | `exchange_calendar` (ATO/ATC/T+2) · `vs_financial_terms` (catalog kỳ) · `vn_reference`/`vn_listing` (universe) · `vs_financial_norms` |
| Chỉ báo tính từ nến local | `signals_technical` · `quant_factors` · `alert_check` (rsi14) — deterministic |

### 🟡 Vùng VÀNG — dùng có điều kiện ghi trong thẻ

| Điều kiện | Chi tiết |
|---|---|
| Screener ≤30 mã | `stock_screener` giới hạn metric tra tối đa 30 mã → task L3·A giới hạn universe ≤30 (cắt bằng `vn_reference` trước) |
| Đối chiếu 2 nguồn | Task L4·D **chỉ định rõ cặp nguồn** trong thẻ (`data_pairs`) — không để agent tự chọn |
| valuation_run / cycle_* | Chỉ dùng khi task nêu đúng giả định playbook; gold tính cùng tham số (L5·C/D) |
| Bảng snapshot stale | Bảng lưu-sẵn có `as_of` riêng (VD global tables as_of 10/10, stale 22 ngày) → gold ghi `as_of` của bảng; đề không hỏi "mới nhất" vượt snapshot_date |

### 🔴 Vùng ĐỎ — cấm trong 200 task

| Điểm mù/nguy hiểm | Lý do | Thay thế |
|---|---|---|
| Realtime WS/live board (`dnse_*` live, `vs_market_price` intraday, `vn_trades` tick) | Không tái lập khi replay; phụ thuộc phiên/giờ | Chỉ giá **đóng cửa** từ chuỗi lịch sử trong snapshot |
| `sentiment_score` (chấm bằng Groq — LLM ngoài) | Không xác định, phụ thuộc bên thứ 3 | Loại hoàn toàn |
| `web_search` / `web_fetch` | Chống gaming | **Allowlist MCP per arm** (gate G-E7) |
| Open interest futures | `futures_basis`: *"DNSE exposes no open-interest field"* | Không đặt task OI |
| IPO calendar | Tool doc: *"Calendar is often empty"* | Không đặt task |
| Số riêng công ty mẹ trong hợp nhất | Chưa chắc có trong `financial_detail` | L4·E cũ → trap niên độ tài chính (5.2-L4·E mới) |
| Adjusted-close có sẵn | Không có tool trực tiếp | L4·F cũ → tính điều chỉnh từ `dividends_splits` + giá raw (5.2-L4·F mới) |
| "Mới nhất/hôm nay" mơ hồ | Snapshot freeze → "gần nhất" = "gần nhất trong snapshot" | Vi phạm chính là trap L4·G mới |
| Deep-phase claims | `g_asset_phase` tự cảnh báo *"rest on few months"* | L5·D chỉ nhận xét có số kèm, không khẳng định giai đoạn trừu tượng |

## 5.2. Phân bổ 200 task — 5 mức × 40, quota tài sản mục tiêu ~65/15/10/10

### 🟢 L1 — Dữ liệu thô (40)

| Họ | SL | Tài sản | Ghi chú |
|---|---|---|---|
| L1·A Quote | 16 | VN7 · crypto6 · vàng/FX3 | — |
| L1·B BCTC chỉ số | 7 | VN | — |
| L1·C Quy đổi đơn vị | 5 | VN | ⭐ vật liệu bẫy xác nhận trong doc MCP: *"candles = nghìn đồng, bảng giá = đồng — convert trước khi ghép bảng"* |
| L1·D Macro 1 số | 6 | macro | — |
| L1·E Trạng thái phiên | 3 | VN | — |
| L1·F Bẫy thực thể | 3 | VN2 · crypto1 | verify `symbol_resolve` trả fail sạch (Phase-0) |

### 🟡 L2 — Chỉ số suy ra (40)

| Họ | SL | Tài sản |
|---|---|---|
| L2·A Tăng trưởng | 7 | VN |
| L2·B Biên | 5 | VN |
| L2·C Ratio | 5 | VN |
| L2·D Kỹ thuật | 6 | VN |
| L2·E Crypto suy ra | 8 | crypto |
| L2·F Vàng/FX | 5 | vàng/FX |
| L2·G Macro suy ra | 4 | macro |

### 🟠 L3 — Đa thực thể (40)

| Họ | SL | Tài sản | Điều kiện |
|---|---|---|---|
| L3·A Sàng lọc | 7 | VN | universe ≤30 |
| L3·B Top-N | 4 | VN | — |
| L3·C Aggregate nhóm | 7 | VN | — |
| L3·D Kỹ thuật đa mã | 5 | VN | — |
| L3·E Crypto batch | 7 | crypto | — |
| L3·F Đa phiên đa chuỗi | 5 | VN3 · vàng/FX2 | — |
| L3·G Macro aggregate (mới) | 5 | macro | CPI YTD, M2 change... |

### 🔴 L4 — Kiểm chứng & bẫy (40 — toàn bộ là bẫy)

| Họ | SL | Tài sản | Fix so với bản trước |
|---|---|---|---|
| L4·A Kỳ chưa công bố | 7 | VN5 · macro2 | dùng `vs_financial_terms` + `macro_events_vn` |
| L4·B Thực thể không có | 5 | VN3 · crypto2 | verify `symbol_resolve` fail sạch |
| L4·C Narrative sai | 7 | VN3 · crypto2 · vàng2 | — |
| L4·D Hai nguồn lệch | 6 | VN3 · vàng/FX3 | **cặp nguồn chỉ định trong thẻ** (`data_pairs`) |
| **L4·E (mới)** | 6 | VN | ❌ bỏ "hợp nhất vs mẹ" (điểm mù) → **trap niên độ/kỳ tài chính**: kỳ tài chính lệch dương lịch · nhầm Q4 vs cả năm · H1 vs 6 tháng — chấm được từ `vs_financial_terms` |
| **L4·F (mới)** | 6 | VN | ❌ bỏ "adjusted-close có sẵn" → **tính giá điều chỉnh từ `dividends_splits` + giá raw** — oracle tự tính, task sâu hơn |
| **L4·G (mới)** | 3 | trộn | **Trap vượt snapshot**: hỏi "hôm nay/live" → đúng = trả theo `as_of` snapshot + nêu `warnings`/`availability` |

### 🔵 L5 — Báo cáo có provenance (40)

| Họ | SL | Tài sản |
|---|---|---|
| L5·A Hồ sơ công ty | 11 | VN |
| L5·B So sánh nhóm | 8 | VN6 · crypto1 · vàng1 |
| L5·C Định giá playbook | 8 | VN (`valuation_run` + playbook dinh-gia) |
| L5·D Chu kỳ playbook | 5 | VN2 · crypto2 · vàng1 (né deep-phase) |
| L5·E Kiểm chứng nhận xét | 5 | VN3 · macro2 |
| L5·F Macro/cross-asset report (mới) | 3 | macro2 · vàng1 |

**Rollup 200: VN ≈ 128 (64%) · crypto ≈ 30 (15%) · vàng/FX ≈ 21 (10,5%) · macro ≈ 21 (10,5%)** — khớp băng mục tiêu; kiểm tra lại ở mỗi freeze.

## 5.3. Quy ước bắt buộc trong task.toml (mọi thẻ)

```toml
data_zone     = "green|yellow"    # red = không được phép tồn tại
data_pairs    = ["vn_quote_history", "vs_overview_trading"]  # bắt buộc với L4·D
snapshot_date = "2026-XX-XX"      # mọi đề đọc theo snapshot; "gần nhất" = trong snapshot
universe_cap  = 30                # bắt buộc với L3·A
banned_tools  = ["web_search", "web_fetch", "sentiment_score"]
gold_fields   = { value, unit, period, source, as_of }   # as_of bắt buộc — khớp envelope provenance của MCP
```

## 5.4. Gates bổ sung (kéo dài G-E ở 2.6)

| Gate mới | Tiêu chí |
|---|---|
| **G-E7** | Allowlist tool MCP: `web_search`/`web_fetch`/`sentiment_score` tắt trên **3/3 arm** (OpenTrading `activeTools` · opencode glob · DSH profile patch) |
| **G-E8** | Pipeline A1d chạy tự động: đối chiếu `source` khai trong answer × `provenance.source` thật từ envelope MCP (thử trên 3 task L1) |

## 5.5. Pilot 24 — danh sách ID chốt

| Mức | ID (thực thể) |
|---|---|
| L1 ×5 | `fin-l1-quote-01` (HPG) · `fin-l1-quote-02` (BTC) · `fin-l1-gold-01` (XAUUSD) · `fin-l1-bctc-01` (VCB, bẫy đơn vị nghìn↔đồng) · `fin-l1-macro-01` (CPI) |
| L2 ×6 | `fin-l2-growth-01` (VNM) · `fin-l2-margin-01` (MWG) · `fin-l2-ratio-01` (FPT P/E) · `fin-l2-tech-01` (RSI14 VCB) · `fin-l2-crypto-01` (biên độ BTC) · `fin-l2-gold-01` (SJC vs thế giới) |
| L3 ×6 | `fin-l3-screen-01` (universe 30) · `fin-l3-agg-01` (5 ngân hàng) · `fin-l3-top-01` · `fin-l3-tech-multi-01` · `fin-l3-crypto-01` · `fin-l3-index-01` |
| L4 ×4 | `fin-l4-future-01` (DGC Q4) · `fin-l4-nonexist-01` · `fin-l4-narrative-01` · `fin-l4-2nguon-01` (HPG) |
| L5 ×3 | `fin-l5-profile-01` (MWG) · `fin-l5-compare-01` (5 ngân hàng) · `fin-l5-valuation-01` (FPT playbook) |

## 5.6. Nguồn đối chiếu Phần 5

| Nguồn | Ghi chú |
|---|---|
| MCP opentrading — tools/list 175 tools (01/11/2026) | Catalog toàn bộ họ task đối chiếu |
| MCP server instructions — envelope `{data, provenance, warnings, availability}` + quy ước đơn vị (candles = nghìn đồng, board = đồng) | Căn cứ bẫy đơn vị + pipeline A1d |
| `g_asset_check` probe (01/11/2026) | Chứng minh bảng global stale 22 ngày (`as_of` 10/10) → bắt buộc snapshot freeze |

---

# PHẦN 6 — TRẠNG THÁI THI CÔNG BỘ TASK (01/11/2026)

## 6.1. Đã hoàn thành — 27 thẻ

Bộ task đã sinh tại `benchmark/tasks/` bằng `benchmark/tools/gen_tasks.py` (chạy lại được, idempotent):

| Nhóm | Số thẻ | Trạng thái |
|---|---|---|
| Smoke (không tính điểm) | 3 — `smoke-quote-01` (HPG) · `smoke-agg-01` (5 NH) · `smoke-trap-01` (XYZX) | ✅ payload thật + oracle + grader |
| L1 ×5 | quote-01 (HPG đơn vị) · quote-02 (BTC) · gold-01 (XAUUSD) · bctc-01 (VCB đơn vị + dòng mẹ/hợp nhất) · macro-01 (CPI nhiều chuỗi) | ✅ |
| L2 ×6 | growth-01 (VNM QoQ) · margin-01 (MWG) · ratio-01 (FPT P/E nguồn-pin) · tech-01 (VCB RSI) · crypto-01 (BTC→VND) · gold-01 (USDVND so phiên) | ✅ |
| L3 ×6 | screen-01 · agg-01 · top-01 · tech-multi-01 · crypto-01 · index-01 | ✅ |
| L4 ×4 | future-01 (DGC Q4) · nonexist-01 (XYZX) · narrative-01 (kiểm chứng nhận định) · 2nguon-01 (HPG 2 nguồn) | ✅ |
| L5 ×3 | profile-01 (MWG multi-part) · compare-01 (5 NH + xếp hạng ROE) · valuation-01 (FPT) | ✅ |

Kèm: `tasks/registry/entities.yaml` (pool 60 VN + 25 crypto + 12 vàng-FX + 10 macro + 8 composite + rule 65/15/10/10 + used_in_pilot) · `tasks/templates/task.toml` (mẫu 5.3) · `gold/README.md` (quy trình oracle) · `PRE-REGISTER.md` (skeleton).

**Mỗi thẻ** (chuẩn Harbor): `task.toml` · `instruction.md` · `environment/payloads.json` (envelope MCP thật đã ghi) · `solution/oracle.py` + `gold.json` · `tests/grader.py`.

**Kiểm chứng tự động** (mỗi lần chạy `tools/gen_tasks.py`):
- 27/27 oracle PASS — gold **tái tạo được từ payload** (không hardcode số);
- 9/9 self-test grader PASS — gồm bẫy đơn vị (`sai_don_vi`), bẫy dòng mẹ/hợp nhất (`sai_chi_tieu`), bịa số → FP=1 (`bia_so`), verdict reject chính xác (`sai_ket_qua`);
- 0 rò rỉ gold trong `instruction.md` (schema dùng placeholder `0`, tiêu đề trung tính).

## 6.2. Thay đổi so với 5.5 — do dữ liệu thật (probe MCP sống 01/11/2026)

| Thẻ | 5.5 dự kiến | Thực tế dữ liệu | Thi công |
|---|---|---|---|
| `fin-l3-screen-01` | `stock_screener` lọc ROE>15/P-E<15 universe 30 | Screener chỉ **enrich 5/30 symbols** → candidates rỗng, `availability: partial` | Đổi nguồn → `peer_compare` lọc ROE>20 & P/E<10 trên 5 NH (gold `{CTG, MBB}`); `universe_cap = 5` |
| `fin-l3-agg-01` | `vn_equity_quote_batch` 5 mã | Batch **`unavailable`** (vnstock fail 01/11) | Đổi → 5× `vn_quote_history` (gold mean 32.18 nghìn đồng) |
| `fin-l2-gold-01` | SJC vs vàng thế giới | `vn_retail_gold` **timeout** | Đổi đề → USDVND đóng cửa 30/10 + so phiên 29/10 (+3 đồng) |
| `fin-l2-crypto-01` | Biên độ phiên BTC | `crypto_spot` batch 10 mã → Binance **429**; high/low null | Đổi → quy BTC ra VND (78109 × 25802 = 2015.37 triệu đồng), 2 nguồn |
| `fin-l3-crypto-01` | Batch 10 coin | 429 khi batch | Đổi nguồn → `yf_commodities` 3 tài sản (GC/CL/BTC; winner CL=F +2.08%) |
| `fin-l2-ratio-01` | "P/E FPT" | 2 nguồn lệch nhau: `valuation_run` 8.75 vs `vn_fundamentals` 20.96 | Đề **chỉ định nguồn** `valuation_run` (nguồn khác = sai — đúng tinh thần A1d) |
| `fin-l5-valuation-01` | "playbook + vùng giá trị" | Tool không trả fair-value range (chỉ multiples) | Đề chỉ hỏi price/P-E/P-B (trung thực năng lực tool) |
| `fin-l4-future-01` | DGC Q4 (niên độ) | DGC đã có **Q3/2026** (LNST mẹ 478.16 tỷ) → Q4 vẫn là tương lai | Giữ đề; gold = từ chối + kỳ thay thế Q3/2026 (bonus) |

Phát hiện thêm (ghi để dùng cho 200): `vs_indicator_data("CPI")` trả **~17 chuỗi** (chỉ số gốc 105.08 vs % so T12 5.08 vs lạm phát cơ bản 4.45) → mọi task CPI/macro phải khóa tên chuỗi; `valuation_run` có trường `*_unit: "unverified"` (giữ nguyên trong payload — đó là chất liệu honesty check).

## 6.3. Định dạng bẫy đã hoạt động (đo được bằng grader)

| Bẫy | Thẻ | Cơ chế chấm |
|---|---|---|
| Đơn vị nghìn↔đồng | l1-quote-01, bctc-01, 2nguon-01, agg | `unit` check tách khỏi `value` (tolerance không "cứu" được) |
| Dòng chỉ tiêu gần nhau (mẹ 14542.28 vs hợp nhất 14550.96 — lệch 0.06%) | l1-bctc-01 | Field `line` bắt buộc + reject token "ngân hàng mẹ" |
| Kỳ chưa công bố | l4-future-01 | `scoring: refusal` — value có số → FP=1 |
| Mã không tồn tại | l4-nonexist-01 | `refusal_tokens` bắt buộc nêu lý do |
| Nhận định sai lệch | l4-narrative-01 | `verdict` reject **khớp toàn bộ** + evidence số thật |
| Nhiều nguồn lệch số | l2-ratio-01 | `source` pin chính xác tool |
| Nhiều chuỗi cùng tên | l1-macro-01 | value + period đủ phân biệt (5.08 vs 4.45 vs 105.08) |

## 6.4. Việc tiếp theo (chờ duyệt pilot)

1. **Duyệt pilot 24+3** (người): đọc `instruction.md` + `gold.json` từng thẻ; checklist 5 mục (G-T2) gồm memory-check + ambiguity-check; any-flag → sửa/loại.
2. Sau duyệt → **tạo 200 task chính** (40/mức, dùng registry + rules từ bộ này) + **holdout** (W3–W5) + kiểm định 2 lớp A/C.
3. Song song (hạ tầng, khi có key `oc_sk_` mới): snapshot-replay server (B2), go-header-proxy (2.3), 8 trục môi trường (2.6), pre-register freeze (bảng giá + commit hash).

*Sinh tự động bởi `tools/gen_tasks.py` — mọi số trong gold tái tạo được từ payload; xem log oracle/self-test khi chạy lại.*

---

# PHẦN 7 — THI CÔNG BỘ CHÍNH 200 + HOLDOUT 50 (02/11/2026)

## 7.1. Trạng thái

- **250 thẻ đã sinh xong** bằng `tools/build_main.py` (idempotent): `tasks/main/` ×200 + `tasks/holdout/` ×50; mỗi thẻ 6 file (task.toml · instruction.md · environment/payloads.json · solution/oracle.py + gold.json · tests/grader.py) — tổng ~1.500 file, + CTPF report `grade.ctrf.json` khi chạy grader.
- **Kiểm định tự động 6 nhóm — 0 lỗi**: 250/250 oracle (gold tái tạo từ payload) · 250 self-test "đúng→pass" · 250 "đột biến→fail" (kể cả task set/verdict) · 250 "rỗng→fail" · leak-scan 0 rò rỉ số vàng trong đề · `grade.ctrf.json` phát đủ 250. **Null-probe** (luôn trả value=3): 20/20 bị chặn.
- **Phân bổ main**: đúng 40 thẻ/mức L1–L5; thực thể **128 VN / 30 crypto / 21 vàng-FX / 21 macro** (≈64/15/10,5/10,5); 25 họ task phủ 30 họ đã thiết kế (5 họ gộp/biến thể).
- **Holdout 50**: 10 thẻ/mức, **niêm phong** — không dùng cho bất kỳ vòng lặp phát triển; chỉ mở **một lần sau freeze**, báo cáo tách riêng (xác nhận).
- Dữ liệu: **205 envelope MCP thật** đã ghi (`tools/recorded/batch_*.json`), từ ~250 lời gọi probe; snapshot cố định 01/11/2026.

## 7.2. Thay đổi so với Phần 4–6 vì dữ liệu thực tế (đã xử lý trong thiết kế)

| Hạng mục | Vấn đề thực tế | Xử lý |
|---|---|---|
| Crypto | binance 429 thường trực | Bỏ `crypto_spot`; dùng **yf** (BTC/ETH/SOL/BNB) + **vn_crypto_ohlcv** (BTC/ETH, VND); mỗi ticker ≤4 dùng với biến thể family/kind khác nhau |
| `movers` "hose" | Trả partial (missing 30 mã) | Bỏ universe hose; 6 task top dùng **vn30** với 6 biến thể đề |
| `vs_overview_trading` | Timeout hàng loạt | Thay bằng `vn_equity_quote_batch` cho task 2-nguồn (vẫn là bẫy đơn vị nghìn↔đồng) |
| LTG, VIS | BCTC stale 2023–2024 | Loại khỏi họ tài chính; VIS thay bằng HT1 trong quote + nhóm thép thay bằng POM |
| SBT | BCTC stale (hết 2025) | Chỉ dùng tech/narrative |
| HAH | `signals_technical` không khả dụng | Thay VGC ở l2-tech |
| POM | valuation partial (EPS âm — không tính P/E) | Task L5 "định giá dữ liệu một phần" (phải giải thích vì sao thiếu) |
| HDB | Trễ kỳ (mới nhất Q2/2026) | Dùng làm **bẫy future tự nhiên** (hỏi Q3/2026 — nơi mã khác đã có) |
| Registry | Sức chứa 60 mã VN < 130 task | Nâng pool **VN 90** (+HT1·90 mã), macro = CPI sub-series + GDP; luật đếm tinh chỉnh có ghi chú (rổ đếm riêng; crypto ≤4 theo biến thể; gf dùng chung pool 2 split) — xem `tasks/registry/entities.yaml` |

## 7.3. Cấu trúc công cụ (tái tạo được toàn bộ)

```
tools/
├── build_plan.py    # pools + phân bổ 250 (assert ≤2) + probe list
├── recorded/*.json  # 205 envelope MCP thật (batch_r0..r15)
├── fam_util.py      # helpers (units, kỳ, envelope, CPI/GDP…)
├── fam_a.py         # 12 họ L1–L2
├── fam_b.py         # 14 họ L3–L5
├── build_main.py    # sinh 250 task + 6 nhóm kiểm định tự động
└── gen_tasks.py     # (bộ pilot/smoke trước đó)
```

## 7.4. Quy chế holdout (bắt buộc giữ)

1. **Không chạy** holdout cho bất kỳ arm nào trước khi freeze phân tích chính (200).
2. Mở **đúng một lần** sau freeze; kết quả chỉ báo cáo dạng xác nhận (confirmatory), không tinh chỉnh ngược.
3. Mọi thay đổi thẻ sau freeze phải qua gate (G-T*), ghi changelog — **không sửa âm thầm**.

## 7.5. Việc tiếp theo (sau duyệt mẫu)

1. Duyệt mẫu ~30 thẻ (xem gợi ý trong PRE-REGISTER/changelog) → tinh chỉnh nếu cần.
2. Hạ tầng: snapshot-replay server phục vụ đúng envelope trong `payloads.json`; **runner contract: `environment/payloads.json` + `solution/` KHÔNG được đưa vào workspace agent** (chống bypass tool-use / đọc gold).
3. Key `oc_sk_` mới + chạy A/A 20 cặp → pilot freeze → chạy 200 (sau đó mới mở holdout).

*Sinh tự động bởi `tools/build_main.py` — 250/250 oracle OK; xem chi tiết khi chạy lại lệnh.*

---

# PHẦN 8 — VÁ 3 LEAK ĐÁP ÁN HỆ THỐNG + NÂNG CẤP KIỂM ĐỊNH (02/11/2026)

> Nguồn: review độc lập toàn bộ repo. Ba lỗi dưới đây đâm thẳng vào tiêu chí ① (sai kỳ = sai)
> và ③ FP-rate / giả thuyết H2 — đã vá xong trước pilot, bộ task rebuild lại 100%.

## 8.1. Ba leak đã vá

| # | Leak | Quy mô | Vá |
|---|---|---|---|
| 1 | Schema block của task bẫy hiển thị `"value": null` + trường `reason` → agent nhận biết task refusal chỉ qua format đề | 32/32 task refusal (main+holdout+pilot+smoke) | Đồng bộ schema: task bẫy dùng đúng schema value (`"value": 0` + unit); quy tắc "không có dữ liệu → null" nằm ở Ràng buộc chung của mọi task |
| 2 | Schema block chứa đúng token kỳ của gold (VD `"period": "Q3/2026 so với Q2/2026"`) → "sai kỳ = sai" vô hiệu | 113+ task (45%) | Placeholder trung tính `(kỳ được hỏi)` / `(kỳ dữ liệu tool)`; kỳ chỉ nêu ở thân câu hỏi khi là premise; growth/margin bỏ parenthetical "(Q3/2026)" (kỳ phải tự suy từ dữ liệu) |
| 3 | Narrative một chiều: claim luôn "tăng liên tục" (luôn SAI) + rule trong đề lộ hướng ("ít nhất 1 phiên giảm") | 11 task (9 main + 2 holdout + 1 pilot) | 2 chiều claim: "tăng liên tục" (SAI) ↔ "có ít nhất một phiên giảm" (ĐÚNG), chọn theo parity id → main 5 sai + 4 đúng, holdout 1+1; rule trung tính |

## 8.2. Nâng cấp đi kèm

- **`tools/check_leaks.py` (mới)** — quét 6 lớp leak trên 277 task: `fence_null` · `fence_period` ·
  `value_leak` · `evidence_leak` · `bonus_leak` · `narrative_leak`; exit 1 khi có leak.
  Leak-scan nội bộ của `build_main.py` dùng lại module này (thay scan cũ chỉ quét số ≥6).
- **Grader `verdict_hit` → longest-match-wins**: accept/reject đều so chuỗi con, token dài hơn thắng —
  "không đúng" (10) đánh bại "đúng" (4), còn "không lệch" (10) đánh bại reject "lệch" (4).
  Đóng lỗ hổng "không đúng vì..." bị tính là ĐÚNG — bắt buộc khi narrative có 2 hướng.
- **build_main.py**: sửa NameError tiềm ẩn `rep[mutate_fail]` (chỉ nổ đúng lúc bộ tự kiểm cần báo
  lỗi FP), bỏ khối no-op; **gen_tasks.py**: không còn ghi đè `registry/entities.yaml` (v2) và
  `PRE-REGISTER.md` khi chạy lại; self-test narrative đọc gold (gold-driven).
- **Period-accept mở rộng "gần nhất"** cho họ RSI (`l2-tech`, `l3-tech-multi`) và movers (`l3-top`):
  payload các tool này không chứa ngày → sau khi fence hết leak kỳ, agent không thể tự suy
  "30/10" → chấp nhận "phiên gần nhất/gần nhất" là hợp lệ (fairness, không phải nới lỏng bẫy).

## 8.2b. Round 2 — findings từ review độc lập (code-reviewer fresh-context)

| # | Finding | Mức | Vá |
|---|---|---|---|
| 1 | Fence `l3-screen` nội suy nguyên gold set vào schema (`"pass": ["ACB",...]`) — copy fence = pass; scanner cũ không quét set/list | Critical (10 task tính điểm) | Schema dùng placeholder `["MÃ1","MÃ2","..."]`; scanner thêm lớp **G `fence_set`** (chuỗi/list gold của expect set/list_order trong fence) |
| 2 | Tie-break verdict (hòa → reject) tước điểm câu trả lời đúng tự nhiên: "khớp, chênh lệch 0 đồng" bị FAIL vì "lệch" ⊂ "chênh lệch" | Important (l4-2src 6 task) | Grader mask cụm trung tính (`chênh lệch`, `sai khác`, `không có lệch`) trước khi so khớp; đồng bộ accept list l4-2src main/holdout với pilot (thêm "bằng nhau", "không chênh") |
| 3 | Rules bctc giao sẵn token gold `line` qua VD "(VD `Tổng LNST`)" | Minor→leak | Bỏ VD (2 pipeline); scanner thêm lớp **H `hint_token`** (token accepts ≥4 ký tự trong rules zone) |
| 4 | `%%` literal in thẳng vào đề (macro_calc ×3, macro_agg ×2) | Minor | Sửa thành `%` |
| 5 | Scanner: dead-call `num_in_text(re.escape(...))`; "6 lớp" → 8 lớp | Minor | Dọn |
| 6 | `build_main.py` import trong loop + docstring stale | Minor | Dồn lên đầu module, cập nhật docstring |
| 7 | smoke-trap title lộ bẫy ("mã không tồn tại") | Minor | Đổi title trung tính "Smoke — Giá mã XYZX" |

Findings được reviewer xác nhận đã xử lý đúng: parity narrative cả 3 split; gen_tasks
write-if-missing (dry-run sentinel nguyên vẹn, pilot+smoke rebuild byte-identical); không số
gold nào thay đổi trong diff tasks/ (trừ narrative verdict theo chủ đích + enrich accept 2src).

## 8.3. Kiểm định sau vá (độc lập)

- 277/277 oracle PASS (gold tái tạo từ payload); 277×3 grader self-test (đúng/đột biến/rỗng) 0 fail;
  `check_leaks` 277 task → **0 leak**; 12/12 case verdict thủ công (longest-match đúng cả 2 hướng).
- Bất biến: 200 main (đúng 40/mức) · 50 holdout · 24 pilot · 3 smoke; ID/level/entity không đổi;
  data payload không đổi (chỉ instruction/gold-narrative/grader thay đổi).
- Commit: `32f0ca4` (test) → `5292e8d` (fix tools) → `a79ae99` (rebuild 277 task) → `6f4c8d8` (docs) → round 2 (screen/verdict/scanner).

## 8.4. Hệ quả đo lường

- **FP-rate (H2) phải đo lại** trên bộ đã vá — số ước lượng trước đó (nếu có) từ bộ leak không dùng được.
- Cột "sai kỳ" của tiêu chí ① hoạt động trở lại trên toàn bộ 250 task main+holdout.

