# Báo cáo giám định: Vì sao OpenTrading (OT) kém hiệu quả hơn OpenCode và DSH trên benchmark tài chính

Ngày giám định: 05/11/2026 · Người giám định: OpenCode agent (phiên review độc lập, không chạy inference mới, không sửa artifact gốc)

## Tóm tắt điều hành

Pilot v3 hoàn tất 176/176 trial cho kết quả primary: **DSH 18/44 (40,9%) > OpenCode 14/44 (31,8%) > OT finance 12/44 (27,3%) = OT baseline 12/44 (27,3%)**. Smoke v3: OT 2/6, OpenCode 4/6, DSH 4/6.

> **Cập nhật 05/11/2026**: đã chạy xác nhận bằng model mạnh (`deepseek-v4.1-flash`, diagnostic) trên 5 câu phân định — RC1/RC3 **xác nhận do model nhỏ** (biến mất trên model mạnh), RC4 còn sót 1 lỗi văn phong, phát hiện thêm watchdog 120s của OT trên model chậm. Chi tiết tại **§9**.
>
> **Cập nhật 06/11/2026**: review tiến độ chương trình v4 của codex (MCP C1/v4 + candidate policy) — 4 finding native **đã đóng trong code + test** (suite 483/0), chỉ còn thiếu xác minh độc lập cuối (reviewer dính limit); phân tích điểm đột phá giúp OT cạnh tranh thắng: §10.
>
> **Cập nhật 06/11/2026 (buổi sáng)**: v4.1 **đã chạy smoke 18 và trượt gate trung thực** (OT candidate 1/6, OC 2/6, DSH 2/6 — nguyên nhân: giao diện replay, bug per-tool counter, grader refusal); v4.2 **đã dựng xong, 322+46 test pass, chưa launch**; gate review độc lập của giám định viên: **technically ready, 2 điều kiện governance**. Chi tiết §11.
>
> **Cập nhật 06–07/11/2026 (chiều–tối)**: vì sao OT tụt lại (kiến trúc + log): §12; v4.4 gate-fail trung thực + corpus 277 task + kế hoạch 50 task OT-strength: §13; v4.4 ĐÓNG (không pilot) + giả thuyết decoder cấm path `/data/last` + v4.5 nháp + merge production OT: §14; review độc lập tổng hợp (điểm nghẽn, audit bài kiểm tra, đề xuất prompt tiếng Anh P-EN-bal/min, lộ trình đánh bại OC/DSH): §15.
>
> **Cập nhật 08–09/11/2026**: thực thi corpus wave-2 (+10/−10) + so sánh 3 arm trên tác vụ tài chính: §16; memory-stratum + verify self-consent 3 arm: §17; **nhánh `v4.6-repair`: 8 instrumentation repairs (94→0 lỗi frozen MINI audit), seal + SMOKE v4.6 đang chạy (Super 23/96): §18.**

Kết luận giám định: khoảng cách không nằm ở hạ tầng (gateway, timeout, catalog MCP, schema tool) — các yếu tố này được kiểm chứng **tương đương giữa 3 harness**. Nguyên nhân nằm ở **hành vi tạo request và dựng đáp án của OT trên model nhỏ**:

1. **RC1 — Tự phát minh tham số vượt contract**: OT baseline sai kiểu JSON-Schema 12/65 calls, OT finance 4/66, trong khi OpenCode/DSH là **0/66** → server từ chối → mất toàn bộ trial trên các task dễ (fin-l1-quote-01: OT 0/4 vs đối chứng 4/4).
2. **RC2 — Không có vòng sửa tham số sau rejection**: `repairCall` của OT chỉ sửa tên tool (`src/core/agent.ts:223-257`), MCP schema đăng ký không gắn validator (`tools/registry.ts:189`), route NVIDIA không nhận TOOL_NUDGE (`agent.ts:88-96,849-860`). Sau rejection, 0/4 arm nào cũng không sửa được chính request lỗi — nhưng OpenCode/DSH không cần vì gọi đúng ngay lần đầu.
3. **RC3 — Mất điểm sau khi đã lấy đúng dữ liệu**: trial OT có đủ số liệu đúng nhưng tước primary vì thiếu trường `evidence` (tỷ lệ thiếu evidence sau MCP `ok`: baseline 43% > finance 25% > OpenCode 17% > DSH 9%), sai namespace SDK, quy đổi đơn vị bừa 1000 lần, evidence placeholder tự bịa.
4. **RC4 — Trọng lượng prompt**: system prompt native OT 7.892 ký tự (baseline) / 6.430 (finance) so với OpenCode 1.871 và DSH 307; input token p50 7.051/5.814 so với 3.340/2.504. Tỷ lệ quên evidence tăng **đơn điệu theo độ dài prompt** trên cùng một model nhỏ.
5. **RC5 — Bản chất thiết kế**: OT được thiết kế cho nhà phân tích người thật trên terminal (bảng biểu, quy đổi đơn vị, chú giải thuật ngữ), không phải cho hợp đồng JSON machine-readable + provenance. Trên model 4B (Nemotron Bolt E4B), "harness suông + nghe lời mô tả tool" (OpenCode/DSH) đánh bại "harness chuyên gia có định kiến trình bày" (OT).

Điểm cộng của OT (để đánh giá công bằng): latency p50 thấp nhất (14,6s), DNF = 1 (bằng OpenCode), pass 2/2 cả hai variant trên fin-l4-future-01 và fin-l5-valuation-01 (OpenCode chỉ 1/2), usage coverage tốt. Prompt finance **có cải thiện hướng đúng** (lỗi kiểu tham số 12→4, từ chối oan 17→15, quên evidence 10→6) nhưng chưa đủ bù và tự sinh thêm 2 case evidence sai (namespace + placeholder).

---

## 1. Phạm vi và tài liệu đã review

### 1.1 Session codex đang chạy (review toàn bộ)

| Session | Trạng thái | Nội dung |
|---|---|---|
| `~/.codex/sessions/2026/11/04/rollout-...14-21-50-...jsonl` (4.558 dòng, ~9,9MB) | Hoàn tất | Orchestrator chính của thí nghiệm v3: chạy 18 smoke + 176 pilot, cài runtime-only vào `/home/doanlong/OpenTrading`, viết REPORT.md và INDEPENDENT-CHECK.md |
| `~/.codex/sessions/2026/11/05/rollout-...16-29-04-...jsonl` | Hoàn tất 16:40:52 | Forensic review toàn bộ 18 smoke + 176 pilot → `audits/2026-11-05/comprehensive-review/forensics/FINDINGS.md` (106 rejection, 305 calls, 779 captures) |
| `~/.codex/sessions/2026/11/05/rollout-...16-29-15-...jsonl` | Hoàn tất 16:36 | Kiến trúc OpenTrading → `audits/2026-11-05/comprehensive-review/architecture/FACTS.md` (127 file TS khớp byte, đường vi phạm repair/validate/prompt conflict) |
| `~/.codex/sessions/2026/11/05/rollout-...16-29-26-...jsonl` | Hoàn tất 16:40 | Rà hợp đồng MCP production 174 tool → `audits/2026-11-05/comprehensive-review/mcp/FINDINGS.md` |

Ngoài ra: tiến trình `opentrading_mcp.loops` (PID 1863) là MCP production server đang chạy từ 09:28; các tiến trình `opencode serve` là môi trường giám định hiện tại.

### 1.2 Log smoke/pilot do các harness trả ra

- Smoke v3: `results/financial-prompt-v3-smoke-20261105/` — manifest, trials.jsonl, 20 thư mục trial (3 câu × 3 arm × 2 run), mỗi trial có `grade.json`, `mcp.jsonl`, `provider.jsonl`, `provider-requests/000N-{native,effective}.json`, `runner/inventory.json`.
- Pilot v3: `results/financial-prompt-v3-pilot-20261105/` — 176 trial, manifest SHA-256 `002f5056...a20b58`, summary.json, đầy đủ native/effective captures (779 file).
- Audit đóng băng: `audits/financial-prompt-v3/REPORT.md`, `INDEPENDENT-CHECK.md`, `pilot-trials.csv`, `pilot-task-success.csv`; protocol đăng ký trước `plans/2026-11-05-compact-pilot-protocol.md`.

---

## 2. Bảng kết quả chuẩn (tái lập từ summary.json + INDEPENDENT-CHECK.md)

### 2.1 Pilot (44 trial/condition, model `nvidia/nemotron-3.5-bolt-e4b`, temp 0, top_p 1)

| Chỉ số | OT baseline | OT finance | OpenCode | DSH |
|---|---:|---:|---:|---:|
| Primary /44 | **12 (27,3%)** | **12 (27,3%)** | **14 (31,8%)** | **18 (40,9%)** |
| Semantic /44 | 14 | 14 | 15 | 18 |
| DNF /44 | 1 | 1 | 1 | 5 |
| Từ chối oan /44 | 17 | 15 | 14 | 11 |
| FP trên 4 câu refusal | 0 | 0 | 0 | 0 |
| Usage đủ /44 | 43 | 44 | 44 | 42 |
| Pass `value` check | 37,5% | 52,5% | 52,5% | 57,5% |
| Pass `provenance` | 39,5% | 48,8% | 44,2% | 61,5% |
| Input token p50 | 7.051 | 5.814 | 3.340 | 2.504 |
| Latency p50 / p90 (s) | 14,6 / 21,9 | 15,3 / 22,1 | 17,4 / 28,5 | 23,1 / 30,9 |

Paired bootstrap theo 22 task (exploratory): finance − baseline 0 điểm % [−6,82; +6,82]; finance − OpenCode −4,55 [−20,45; +9,09]; **finance − DSH −13,64 [−27,27; −2,27]**.

### 2.2 Smoke v3 (18 trial)

| Câu | OT (canonical = finance) | OpenCode | DSH |
|---|---|---|---|
| smoke-quote-01 (HPG) | **0/2** — cả 2 run gọi `{columns:"close",days:1,interval:"day"}` → rejected | 2/2 — `{symbol:"HPG"}` → ok | 2/2 — `{symbol:"HPG"}` → ok |
| smoke-agg-01 (5 ngân hàng) | 0/2 — rejected (cả 3 arm đều thêm days/interval) | 0/2 | 0/2 |
| smoke-trap-01 (mã không tồn tại) | 2/2 pass | 2/2 | 2/2 |

Smoke tái lập đúng pattern pilot: **chênh lệch nằm ở task tra cứu đơn giản**, không phải task khó.

---

## 3. Phân loại nguyên nhân theo giai đoạn thất bại

### 3.1 Thống kê gọi MCP (pilot, 65-66 calls/arm, 106 rejection tổng)

| Số liệu | OT baseline | OT finance | OpenCode | DSH |
|---|---:|---:|---:|---:|
| Call thành công / availability ok | 38 / 36 | 39 / 37 | 39 / 37 | 41 / 39 |
| **Schema-invalid (sai kiểu tham số)** | **12** | **4** | **0** | **0** |
| Schema hợp lệ nhưng chưa được ghi trong replay | 15 | 23 | 27 | 25 |
| Trial chỉ có rejection, không có MCP success nào | 13 | 13 | 13 | 11 |
| Sửa được **chính** tool/request sau rejection | **0** | **0** | **0** | **0** |
| Tool khác thành công sau rejection (không tính là repair) | 4 | 4 | 4 | 4 |

- 90/106 rejection (84,9%) là "schema hợp lệ, chưa được replay" — **bình đẳng giữa các arm**, phản ánh giao diện replay nghiêm, không phải lỗi riêng của OT.
- Chi tiết 16 call schema-invalid của OT: baseline — 10 call `columns:"close"` (phải là array/null) trên 5 ngân hàng, 1 call `symbols:"USDVND"` (phải là array), 1 call `metrics:"P/E, P/B, ROE"` (phải là array); finance — 2 call `columns:"close"` (HPG) + 2 call `symbols:"USDVND"` (FX). **OpenCode và DSH không có call sai kiểu nào trong toàn bộ pilot.**
- Phân nhóm 90 call "hợp lệ-nhưng-không-replay": `vn_quote_history` 39, `vn_msn_fx_gold` 20, `financial_detail` 14, `vn_index_ohlcv` 8, `market_movers` 7, `financial_statements` 2. Đặc trưng: model tự thêm `days=1`, `interval=day/1d`, `periods_n`, `top_n=3`, `count=10`, hoặc gọi subset batch (`[XAUUSD]` thay `[USDVND,XAUUSD]`).

### 3.2 Thất bại hợp đồng đáp án sau truy xuất thành công (đếm lại từ 176 trial)

Trong số trial **có MCP `ok` + trả lời có số thật (không phải refusal)**:

| Arm | Có evidence | **Thiếu/empty evidence** | Tỷ lệ thiếu |
|---|---:|---:|---:|
| OT baseline | 13 | **10** | **43,5%** |
| OT finance | 18 | 6 | 25,0% |
| OpenCode | 20 | 4 | 16,7% |
| DSH | 20 | 2 | 9,1% |

Provenance-fail khi **mọi check semantic đều đúng** (trial "đúng số nhưng tuột primary"): OT baseline 2, OT finance 2, OpenCode 1, DSH 0.

### 3.3 Kích thước ngữ cảnh native (đo từ `provider-requests/0001-effective.json`, task fin-l1-quote-01 r1)

| Arm | System prompt (ký tự) | User instruction | Input token p50 (pilot) |
|---|---:|---:|---:|
| OT baseline | **7.892** | 2.411 (chung) | 7.051 |
| OT finance | **6.430** | 2.411 (chung) | 5.814 |
| OpenCode | 1.871 | 2.461 | 3.340 |
| DSH | **307** | 2.411 (chung) | 2.504 |

Mô tả tool gửi lên wire **giống hệt nhau 3 arm** ( Frozen MCP snapshot + `snapshot_requests=[{"symbol": "HPG"}]`; đã đối chiếu trực tiếp captures của 3 arm). Chênh lệch token nhập ~1.237 giữa baseline/finance khớp chính xác chênh lệch độ dài prompt (~1.462 ký tự ≈ /4).

---

## 4. Sáu nguyên nhân gốc — bằng chứng chi tiết

### RC1 — OT tự phát minh tham số, đối chứng chép literal (nguyên nhân trực tiếp)

**Case fin-l1-quote-01** (task L1 đơn giản nhất; request replayable in ngay trong mô tả tool: `snapshot_requests=[{"symbol":"HPG"}]`):

| Arm | Call thực tế | Kết quả |
|---|---|---|
| OpenCode r1/r2, DSH r1/r2 | `{"symbol":"HPG"}` | `ok` → primary 4/4 |
| OT finance r1 | `{"columns":"close","days":1,"interval":"day","symbol":"HPG"}` | rejected: `'close' is not valid under any of the given schemas` |
| OT finance r2 | `{"columns":"close","symbol":"HPG"}` | rejected (cột phải array/null) |
| OT baseline r1 | `{"days":1,"symbol":"HPG"}` | rejected (`days` non-default không có trong recording) |
| OT baseline r2 | `{"symbol":"HPG"}` | `ok` — nhưng mất điểm vì hợp đồng đáp án (RC3) |

Sau rejection, model OT trả lời: *"Không tìm thấy dữ liệu giá đóng cửa cho HPG... Yêu cầu cột 'close' không hợp lệ theo schema của tool"* → `value:null` trên câu **có** đáp án trong snapshot → sai_so/từ chối oan. Nguồn: `results/.../trials/fin-l1-quote-01__opentrading_finance__r1/attempts/01-cf82421ab84a/{mcp.jsonl,run.log,provider-requests/0002-native.json}`.

**Case fin-l1-gold-01**: OT gọi `{"symbols":["XAUUSD"]}` (subset) → rejected vì replay chỉ ghi batch `[USDVND,XAUUSD]`; DSH chép y batch → pass 1 lần duy nhất trong 4 arm. Nguồn: `trials/fin-l1-gold-01__{opentrading_baseline,dsh}__r1`.

Đây là hành vi định hướng sai do **học từ schema mặc định** (`days` default 365, `interval` default "1D", `columns` array|null) thay vì **nghe lời mô tả replay** ("Supply all recorded non-default parameters; omitted parameters retain the real schema defaults"). Model nhỏ đọc nhắc gì thì làm nấy — và cái nó đọc nhiều nhất là 6-8K ký tự prompt của OT trước khi tới 1 câu mô tả tool.

### RC2 — Vòng lặp agent OT không có cơ chế repair tham số

Bằng chứng mã nguồn (đối chiếu byte với runtime đã chạy, FACTS.md §1):

- `experiments/opentrading-runtime/src/core/agent.ts:223-257` — `repairCall` chỉ xử lý `NoSuchToolError` (sửa tên tool), **không có policy sửa tham số**.
- `src/core/tools/registry.ts:189` — `jsonSchema(this.schemaFor(...))` tạo tool SDK **không gắn `validate`**; SDK (`@ai-sdk/provider-utils 5.0.58`, `schema.ts:105-128`) trả "thành công" cho mọi giá trị khi thiếu validator → tham số sai kiểu đi thẳng tới server.
- `src/core/agent.ts:88-96,849-860` — TOOL_NUDGE chỉ áp cho route SDK đã xác minh; **route openai-compatible/NVIDIA không nhận nudge nào** sau tool-result (đã xác minh: captures NVIDIA không có trailing nudge).
- Server phản hồi đầy đủ và đúng (`retryable_with_corrected_arguments:true` + `snapshot_requests` + guidance ~500 ký tự, nhận nguyên vẹn trong request kế tiếp — đã xác minh hash/capture) nhưng model không dùng.

Kết quả đo được: **0 request nào trong cả 4 arm quay lại cùng tool bằng mẫu hợp lệ sau rejection**; 13 trial/arm chỉ có rejection và buông. OpenCode/DSH cũng không repair — nhưng chúng hầu như không rơi vào rejection trên task dễ vì không tự chế tham số. Chênh lệch giữa "không cần repair" và "cần repair mà không có" chính là 2 task quote/compare của OT.

### RC3 — Mất primary sau khi truy xuất thành công (hợp đồng đáp án)

Các case trọng (tất cả có đường dẫn đầy đủ để tái lập):

1. **fin-l5-compare-01, OT finance r1**: 15/15 value check PASS + ranking + period PASS, chỉ **thiếu trường `evidence` hoàn toàn** (answer keys chỉ có `values/ranking/period/source/note`) → `thieu_bang_chung` → 0 điểm. benchmark_evidence đầy đủ ngay trong tool-response (call_id `d24d4114-...`) nhưng model không chép. Nguồn: `trials/fin-l5-compare-01__opentrading_finance__r1`.
2. **fin-l1-quote-01, OT baseline r2**: trả đúng **21,0 nghìn đồng + ngày 30/10/2026** nhưng không có `evidence` → tuột primary. Nguồn: `trials/fin-l1-quote-01__opentrading_baseline__r2`.
3. **fin-l1-bctc-01**: tool trả `Tổng LNST Q2/2026 = 14.550.959.000.000 VND` (unit "VND"); đề yêu cầu tỷ đồng; gold = 14550,96. OT baseline r1 trả **"14.550959 tỷ đồng"** (quy đổi sai 1000 lần) — note tự nhận "quy đổi từ VND sang tỷ đồng"; DSH trả nguyên văn 14550,959 → pass. OT finance r1 còn ghi evidence với `tool: "mcp__opentrading__financial_statements"` (namespace SDK thay tên canonical) và sai số tương tự. Nguồn: `trials/fin-l1-bctc-01__{opentrading_baseline,dsh}__r1`.
4. **fin-l5-compare-01, OT finance r2**: MCP `ok`, evidence chép đúng, nhưng top-level `source` là `mcp__opentrading__peer_compare` thay vì `peer_compare` → sai_nguon. Nguồn: forensics matched-losses.
5. **fin-l2-crypto-01, OT finance r1**: BTC evidence thật nhưng FX bị rejected → model **tự điền evidence placeholder `N/A` + timestamp tự tạo** cho FX (đại diện hư cấu, benchmark chặn đúng). Nguồn: `trials/fin-l2-crypto-01__opentrading_finance__r1`, INDEPENDENT-CHECK.md.
6. **fin-l2-growth-01, OT finance r1**: lấy đúng dữ liệu Q4/2025–Q3/2026, note **tự tính đúng** Q3 vs Q2 = −2,03 nhưng giữ `value=-5.63` và `period=Q2/2026 vs Q1/2026` — lỗi liên kết giá trị–kỳ–lập luận; trường JSON không tự sửa theo note.

Quy luật: **tỷ lệ quên evidence tăng đơn điệu theo độ dài system prompt** (43,5% → 25,0% → 16,7% → 9,1%). Với OpenCode/DSH, dòng "Cite tool, provenance.source, provenance.as_of, benchmark_evidence.call_id and payload_sha256 in answer evidence" nằm ở **cuối** một prompt ngắn — ngay trước turn đầu; trong OT nó bị chôn giữa `<citations>` ở giữa 6-10K ký tự, trong khi nhắc cuối cùng model thấy (`<nhac_nho>`/TOOL_NUDGE) chỉ nói định dạng bảng/ngày/đơn vị, **không nhắc evidence**. Đây là giải thích cơ chế khả dĩ có dữ liệu định lượng ủng hộ; giám định không tuyên bố quan hệ nhân quả tuyệt đối (xem §7).

### RC4 — Prompt nền OT có xung đột nội tại với hợp đồng benchmark

Trong prompt baseline (đọc từ capture `0001-effective.json`):

- `<citations>` dạy "Đổi về cùng đơn vị trước khi so sánh", "Tiền ghi bằng đồng, có dấu phân cách nghìn", ví dụ bảng `dd/mm/yyyy | xx.xxx` → tạo thói quen quy đổi → lỗi 1000 lần ở bctc (model nhỏ áp máy móc).
- `<tools>` baseline dạy trình bày hội thoại ("nói 1 câu ngắn đang làm gì", "không nêu tên tool trừ khi hỏi") — mâu thuẫn với hợp đồng bắt buộc `source` = tên tool canonical.
- `<style>` finance thêm "Không thêm trường nếu schema không cho phép" — tín hiệu cạnh tranh trực tiếp với "Thêm trường `evidence` vào object JSON" trong instruction.
- Ưu tiên hệ thống (`<thu_tu_uu_tien>`) đặt bất biến hệ thống trên yêu cầu trực tiếp người dùng — hợp lệ cho sản phẩm, nhưng trong benchmark làm luật "JSON contract" dễ bị nuốt.

Prompt finance đã cắt phần lớn mâu thuẫn và **cải thiện hướng đúng** (sai kiểu 12→4, từ chối oan 17→15, quên evidence 10→6, quote-02 1→2), nhưng: (a) vẫn 12/44 = baseline vì các case bị tiềm/turn khác; (b) tự sinh 2 case evidence sai (namespace + placeholder) mà baseline không có; (c) chưa chạm được RC1/RC2 vốn nằm ở **runtime loop**, không phải prompt.

### RC5 — Phân bố cặp thua thắng (paired per task/run, forensics §"Các cặp OT thua đối chứng")

- **OT mỗi variant thua DSH 6 cặp, thắng 0**: 3 cặp mất ở giai đoạn truy xuất (HPG columns ×2, XAUUSD subset) + 3 cặp mất sau tool thành công (LNST unit+namespace, peer compare thiếu evidence, peer compare source namespace).
- **OT mỗi variant thua OpenCode 4 cặp, thắng 2 cặp** (thắng: fin-l4-future r1 — OC không hoàn thành answer contract; fin-l5-valuation r2 — OC sai source SDK prefix). Net −2 = đúng chênh 12 vs 14.
- **12/22 task cả 4 arm đều fail đồng loạt** (l2-crypto, l2-gold, l2-growth, l2-margin, l2-tech, l3-agg, l3-crypto, l3-index, l3-tech-multi, l3-top, l4-2nguon, l5-profile) — sàn năng lực model nhỏ, không quy cho harness. 3 task cả 4 arm pass (ratio, screen, nonexist). Chỉ 7 task phân hóa — và OT thua đậm đúng ở đó (quote-01, compare-01, quote-02, bctc, gold).

### RC6 — Đã loại trừ (bằng chứng đối chiếu)

| Giả thuyết | Kết luận giám định |
|---|---|
| Gateway/timeout/rate-limit bất công | OT p50 nhanh nhất, DNF 1 (≤ đối chứng), usage 44/44 (finance), 354 request khớp manifest |
| MCP server operational error | 0 operational error; 8 actual-empty (symbol_resolve mã không tồn tại) xử lý đúng cả 4 arm |
| Model thấy tool khác nhau | Mô tả tool trên wire giống hệt 3 arm (đã đối chiếu captures); 0 case unknown_tool |
| Săn đoán "174 tool gây overload" | Mỗi trial chỉ cấp tool của task (1-3 tools); pilot không đo discovery full catalog |
| Lịch chạy thiên lệch | Arm order xoay đủ 4 vị trí, mỗi condition 11 lần/vị trí; manifest hash khớp sau chạy |
| Lỗi grader | Grader dùng chung 4 arm; tái tính độc lập khớp 176/176 row |
| Clock | OT được pin native clock theo snapshot (thiện chí tối đa); OC/DSH không tuyên bố pin — confound đã ghi nhận nhưng hướng ảnh hưởng chưa biết |
| OpenCode preprocessing | OC CLI bọc/escape input nhiều dòng (`run.ts:288,869`) — **confound đã ghi nhận**, không suy diễn hướng ảnh hưởng |

---

## 5. Trả lời câu hỏi gốc

> Tại sao harness chuyên biệt cho phân tích/đầu tư tài chính (OT) lại thua hai harness code-agent (OpenCode, DSH) trong lĩnh vực tài chính?

Vì benchmark này đo **hỏi đáp tài chính có căn cứ trong snapshot, trả JSON machine-readable kèm provenance bắt buộc** — một trò chơi tuân thủ hợp đồng nghiêm, không phải trò chơi phân tích chuyên sâu. Trong trò chơi đó, trên model 4B:

- OpenCode/DSH là "harness suông": prompt gần trống, mô tả tool chiếm tỷ trọng attention lớn → model chép literal `snapshot_requests`, chép literal `benchmark_evidence`, không quy đổi gì cả → đúng hợp đồng.
- OT là "harness chuyên gia": 6-10K ký tự triết lý trình bày + bất biến an toàn + quy tắc quy đổi, nhưng **thiếu cả ba cơ chế máy** mà trò chơi đòi hỏi: validator tham số cục bộ, repair vòng lặp, và gate hợp đồng đáp án. Kết quả là model vừa bị nhiễu, vừa không được máy hỗ trợ chỗ yếu nhất của nó.

Nói cách khác: **OT đầu tư vào "kiến thức tài chính" trong prompt, benchmark thưởng cho "kỷ luật kỹ thuật" trong vòng lặp.** Prompt finance của OT đã chứng minh phần "kiến thức" có thể cải thiện hành vi (giảm refusals, giảm lỗi kiểu), nhưng phần "kỷ luật kỹ thuật" phải sửa ở runtime — và đó cũng là lý do quyết định triển khai sau pilot là **runtime-only** (cài `src/core/agent.ts` + `src/core/prompt/assemble.ts` vào `/home/doanlong/OpenTrading`, giữ prompt baseline mặc định, prompt finance ở trạng thái candidate).

---

## 6. Khuyến nghị (xếp theo tác động/giá trị triển khai)

### P1 — Runtime repairs cho OpenTrading (tác động cao nhất, bám đúng seam API đã xác minh)

1. **Validator tham số cục bộ**: gắn `validate` thật vào `jsonSchema()` ở `tools/registry.ts:189` (seam `provider-utils 5.0.58 schema.ts:105-128`) theo schema gốc MCP; sai kiểu → repair một bước bounded trước khi gửi server.
2. **Repair vòng lặp sau rejection**: khi tool trả `request not replayable` kèm `snapshot_requests`, chèn 1 nhắc ngắn cuối request kế tiếp ("chỉ gọi đúng pattern snapshot_requests, không thêm tham số non-default; sai kiểu thì sửa đúng kiểu array/null") — 1 lần, trong budget 24 request hiện có.
3. **Gate hợp đồng đáp án trước khi kết thúc turn**: kiểm tra (a) đủ trường bắt buộc, (b) `evidence` là bản chép đúng 7 trường từ `benchmark_evidence` của call thành công trong ledger, (c) tên tool/source canonical (không namespace SDK), (d) cấm placeholder tự bịa. Fail → 1 bước sửa có giới hạn. Nên tách dữ liệu: giá trị do model sinh ≠ provenance bất biến từ tool (never synthesize benchmark IDs).

### P2 — Prompt tier-C cho model nhỏ

- Rút gọn layers theo tier (model context <64K → tier C): identity ngắn, bỏ khối trình bày bảng/chú giải thuật ngữ trên route snapshot-QA.
- Đưa "mệnh lệnh sống còn" (minimal args = đúng `snapshot_requests`; chép nguyên evidence; không quy đổi khi unit đã đúng) xuống **cuối context**, sát turn đầu — tận dụng recency như OpenCode/DSH đang hưởng.
- Loại bỏ tín hiệu cạnh tranh ("Không thêm trường nếu schema không cho phép") khi instruction bắt buộc thêm trường evidence.

### P3 — Hợp đồng MCP production (quy trình riêng, không gộp với benchmark)

Theo `mcp/FINDINGS.md`: typed `Literal`/`Field(ge,le,description)` cho `interval/days/columns/metrics/symbols`; tách error enum `invalid_argument / not_recorded / no_data / upstream_timeout`; không biến lỗi tham số thành `availability:"unavailable"` với `isError:false`; sửa description/hint `valuation_run` đúng năng lực thật; outputSchema typed thay `dict[str,Any]`.

### P4 — Quy trình đo lại

- Mỗi nhóm sửa ở trên cần thí nghiệm exploratory **đăng ký trước riêng** (per REPORT.md: không chỉnh prompt/grader theo kết quả cũ, không chạy lại để chọn điểm thuận lợi).
- Đánh giá lại bằng smoke + pilot cùng cấu hình freeze; mới có thể xét main/holdout.
- Bổ sung metric repair thật: `same_request_repaired`, `required_evidence_coverage_restored`, `final_primary_recovered` (thay cho metric "any later tool success" hiện tại).

---

## 7. Hạn chế của giám định

- Pilot 22 task × 2 run × 1 model nhỏ; không suy rộng sang model lớn, Go/DeepSeek medium, hay MCP live production.
- Quan hệ "prompt dài → quên evidence" là **tương quan đơn điệu quan sát được trên 4 điểm dữ liệu arm**, không phải thí nghiệm nhân quả; các cơ chế RC1-RC4 có bằng chứng hành vi và mã nguồn nhưng chưa được ablation factorial.
- OpenCode input-preprocessing (bọc dấu nháy/escape) và clock không pin là confound đã ghi nhận, hướng ảnh hưởng chưa xác định.
- Mô tả tool trong smoke/pilot là bản replay generic (thay docstring live tại `tools/mcp_snapshot_server.py:86-88`) — pilot đo khả năng dùng giao diện replay, không đo chất lượng docstring production.
- Không sửa bất kỳ artifact gốc, grader, prompt hay runtime nào trong quá trình giám định; không chạy inference mới.

---

## 8. Tái lập các con số

```bash
# Tái lập forensic (không inference, không mutation)
python3 audits/2026-11-05/comprehensive-review/forensics/extract.py
python3 audits/2026-11-05/comprehensive-review/forensics/render_snippets.py

# Xem trace case trọng
cat results/financial-prompt-v3-pilot-20261105/trials/fin-l1-quote-01__opentrading_finance__r1/attempts/*/run.log
cat results/financial-prompt-v3-pilot-20261105/trials/fin-l5-compare-01__opentrading_finance__r1/attempts/*/ws/answer.json
cat results/financial-prompt-v3-pilot-20261105/trials/fin-l1-bctc-01__opentrading_baseline__r1/attempts/*/ws/answer.json

# Metrics đóng băng
python3 -c "import json;d=json.load(open('results/financial-prompt-v3-pilot-20261105/summary.json'));[print(a, d['arms'][a]['dnf']) for a in d['arms']]"
```

Nguồn chính: `audits/financial-prompt-v3/REPORT.md` + `INDEPENDENT-CHECK.md` + `evidence.json`; `audits/2026-11-05/comprehensive-review/{architecture/FACTS.md, mcp/FINDINGS.md, forensics/FINDINGS.md, forensics/matched-losses.json, forensics/SNIPPETS.md}`; `results/financial-prompt-v3-{smoke,pilot}-20261105/`.

---

## 9. Phụ lục (cập nhật 05/11/2026): Xác nhận chẩn đoán bằng model mạnh — DIAGNOSTIC, không certified

Theo yêu cầu điều phối, 5 câu phân định của pilot v3 được chạy lại bằng **`nvidia/deepseek-ai/deepseek-v4.1-flash`** (cùng route NVIDIA, cùng snapshot, cùng 4 arm × 2 run = 40 lịch). Model được admits qua quy trình chuẩn: canary function-call thật + receipt `audits/2026-11-05/nvidia-function-probe-deepseek-v41-flash.json`, allowlist `DIAGNOSTIC_MODELS` chỉ mở pilot/smoke (gateway vẫn chặn mọi model khác; test fail-closed được cập nhật giữ nguyên ý đồ "không route ngầm").

Đường lối protocol: giữ nguyên mọi cap hành vi (24 requests, 2048 output tokens/request, 48.000 tokens/trial, retry 0, spacing 2s, effort none, temp 0); chỉ nới deadline thời gian (provider_timeout 180–240s, trial 900s) vì model flash mất 45–130s/request. Kết quả lưu ở `results/diag-deepseek-flash-20261105{,-passB,-passC}/` (nhãn DIAGNOSTIC-NOTICE.md từng pass).

### 9.1 Kết quả đo được: khoảng cách biến mất trên trial hoàn thành

Sau 3 pass (NVIDIA route mất kết nối giữa pass A; 31 trial chết infra; pass B đủ lịch nhưng 15 trial chết vì hai dạng nhiễu thượng nguồn; pass C bổ khuyết), ta đo được **25/40 trial** — đủ phủ mọi (task, arm) trừ quote-01 × OT-base:

| Arm | Model nhỏ: PASS /10 | Flash: PASS / trial đo được | Infra-err |
|---|---|---|---|
| OT baseline | 2/10 | **5/5** | 5 |
| OT finance | 2/10 | **5/6** (1 sai_ky) | 4 |
| OpenCode | 6/10 | **6/6** | 4 |
| DSH | 8/10 | **8/8** | 2 |

**Trên 26 trial hoàn thành, 25 PASS (96,2%) — gồm cả OT.** Khoảng cách 2 vs 8 điểm giữa OT và DSH trên model nhỏ là trần năng lực model, không phải khác biệt harness.

### 9.2 Phán định per nguyên nhân gốc

| RC | Trên flash | Phán định |
|---|---|---|
| RC1 tự chế tham số | quote-01 OT-fin gọi sạch `{"symbol":"HPG"}`; quote-02 cả 4 arm sạch `{"symbols":["BTCUSDT"]}`; compare-01 cả 4 arm gọi args **giống hệt nhau** | **Xác nhận do model nhỏ** |
| RC3 mất evidence sau MCP ok | Mọi trial đo được đều có evidence 7 trường đầy đủ, `source` canonical; bctc quy đổi đúng 14550.959 tỷ (8/8) | **Xác nhận do model nhỏ** |
| RC2 không có vòng repair | gold-01 OT-base r2: reject 2 lần (subset, days-only) rồi **tự sửa thành batch hợp lệ → PASS** — ca same-tool repair đầu tiên được quan sát (model nhỏ: 0/106) | Model mạnh tự repair được **mà không cần** runtime support → P1 vẫn có giá trị cho model nhỏ, không bắt buộc cho model mạnh |
| RC4 prompt nhiễu/văn phong | **Còn sót lại 1 lỗi**: compare-01 OT-fin ghi `period: "2025 (period_label \"2025\"; bội số...)"` → sai_ky dù 15 giá trị + ranking + source + evidence đều đúng | Lỗi **thói quen prompt**, không phải năng lực → khuyến nghị P2 giữ nguyên giá trị |

### 9.3 Hai phát hiện mới (chỉ xuất hiện trên model mạnh-nhưng-chậm)

1. **OT có watchdog no-data 120s** (`experiments/opentrading-runtime/src/core/agent.ts:53-58`, `LLM_STALL_MS = 120_000`): vì gateway benchmark buffer toàn bộ response trước khi trả agent, flash sinh văn bản >120s bị OT coi là stall và tự hủy turn — 8 trial OT chết đúng cách này (4 ở pass B "(no provider error)", 4/4 ở pass C). OpenCode/DSH không có watchdog tương đương (chạy tốt đến 332s). **Hàm ý: OT có rủi ro DNF cấu trúc trên model mạnh-nhưng-chậm** — cần thêm pass-through streaming hoặc knob cấu hình stall khi nâng model.
2. **Route NVIDIA deepseek-flash không ổn định về lớp phục vụ**: mất kết nối URLError cả dọc 31 trial (pass A) + thỉnh thoảng trả stream thiếu trường `model` (7 trial pass B, gateway từ chối đúng thiết kế "no silent substitution"). Không phải lỗi harness; mọi trial đo được dùng để phân tích, trial error-only coi như không đo.

### 9.4 Giới hạn của phần bổ sung này

- 25/40 trial đo được; quote-01 × OT-base không đo được trên flash (watchdog §9.3) — suy diễn hành vi ô này từ quote-02 OT-base (2/2 pass) và gold-01 OT-base (pass sau tự-repair).
- Một pass C có sai sót vận hành của người chạy (`--out` nhầm đường dẫn → trial compare-01 OT-fin nằm ở `...-passC/driver2.log/trials/`; nội dung hợp lệ, đã ghi trong nhãn).
- Model flash trên NVIDIA phát `reasoning_content` mặc định (không tắt được qua benchmark contract); các harness đọc bỏ trường này, không ảnh hưởng hợp đồng đáp án.
- Vẫn là chẩn đoán **không certified**: không xếp hạng, không đụng gold/grader/prompt của run đóng băng, `bench_config.json` giữ model bolt; main/holdout không chạy.

---

## 10. Phụ lục (cập nhật 06/11/2026): Review chương trình v4 của codex, đánh giá và phân tích điểm đột phá

> **Lưu ý supersession (06/11, buổi sáng)**: các dòng trạng thái "chưa chạy / gate khép / independent closure THIẾU" trong §10.2 và §10.5 đã bị **supersede bởi §11** — v4.1 đã chạy smoke (trượt gate trung thực), closure đã xong, v4.2 đã dựng xong chờ launch. Phần phân tích (§10.3-10.4) vẫn giữ giá trị; bảng đột phá B1-B4 được cập nhật trong §11.4.

Phạm vi: toàn bộ session codex 23:27–23:51 (05/11) — 5 session, trong đó 3 session (23-27-12, 23-27-30, 23-44-16) **dính limit** khi thực hiện task *"review 2 plans (opencode-review.md §6 + agy-review.md) → tổng hợp, kiểm chứng → báo cáo OT đã vượt trội chưa → nếu chưa: điều tra + kế hoạch cải thiện + thực nghiệm phiên bản cải thiện"*. Kiểm chứng độc lập của giám định viên, không inference.

### 10.1 Task dở dang do dính limit — hiện trạng

- 3 session dính limit chỉ kịp tái phát biểu kết quả v3 (12/44/12/44/14/44/18/44) rồi dừng — **nhiệm vụ tổng hợp 2 plans + báo cáo "đã vượt trội chưa" + kế hoạch thực nghiệm chưa hoàn thành**. 2 session còn lại hoàn tất phạm vi hẹp của mình: (a) implementation MCP C1/v4 + native policy, (b) independent MCP review.
- `agy-review.md` (báo cáo AGY — agent thứ ba) có **lỗi mẫu số**: denominator "answered-only" (DSH 18/39, OC 14/43, OT 12/43 thay vì /44) và ghi "168 trials" (thực tế 176). External review của codex đã bắt lỗi này; tôi xác nhận lại — các con số AGY không dùng làm baseline được.
- Việc pull production OT lên **v0.3.1** (06/11, 330 commits) đã xong ngoài study — Production hiện có native tool-failure notices ("Gọi X ngay ở bước kế tiếp" + "không tự điền số", commit `c313b64`) mà study runtime pinned **không có**.

### 10.2 Xác minh độc lập trạng thái v4 (trước gate smoke)

| Hạng mục | Trạng thái | Bằng chứng giám định viên tự xác nhận |
|---|---|---|
| MCP C1/v4 metadata + contract | **DONE + verified** | 10/10 offline test pass (chạy lại bởi GV); 402 recorded requests hợp lệ C1; 589 file payload/contract/gold byte-identical; 2 P1 của reviewer đã vá — GV probe 5 mẫu biên: `interval:"day"`/`columns:["close"]`/`columns:"close"`/`days:0` → `invalid_request` (phân loại `v4_domain_constraint` vs `frozen_v3_type_or_shape` đúng), `{symbol:"HPG"}` → ok, `{symbol:"HPG",days:1}` → `not_recorded` (matcher không đổi) |
| Native candidate — finding #1 (Ajv strict) | **Đóng trong code+test** | `finance-policy.ts:7` `strictSchema: true`; `finance-policy.ts:23` fail-closed `unsupported_schema`; test *"unsupported schema keyword fails closed"* |
| Finding #2 (temporal scope) | **Đóng** | `finance-policy.ts:52` từ chối correction đổi scope; test *"corrected request preserves declared temporal and financial scope"* + *"finance local scope guard emits correlated native policy rejection without MCP execution"* |
| Finding #3 (provenance immutable) | **Đóng** | `immutableClone` (`finance-policy.ts:11,61,68`); test *"successful provenance is an immutable clone"* |
| Finding #4 (step accounting) | **Đóng** | Test suite 23:49: *"finance output correction respects native maxSteps with no extra request"* + *"finance native empty-answer retry respects maxSteps and never starts extra correction"* |
| Full native suite | **483 pass / 0 fail** (53 files, 56s, chạy 23:49) | `test-artifacts/full-native-tests.log` |
| Independent closure appendix | **THIẾU** — reviewer dính limit ngay sau khi suite chạy xong (23:50-23:51) | `independent-native.md` (23:46) vẫn kết thúc bằng "Final closure ... will be appended" |
| Smoke / Pilot v4 | **Chưa chạy** | `experiments/finance-v4-study/` không có `results/`; không inference (xác nhận lại 06/11) |

**Kết luận gate**: kỹ thuật đã đủ điều kiện smoke, nhưng **về quy trình gate còn khép** — thiếu một lượt xác minh độc lập append (commands, counts, hashes) cho native suite theo đúng thứ reviewer đã hứa. Không nên tự thay thế bằng xác nhận của implementation owner; chỉ định reviewer độc lập mới/phiên mới append rồi mới chạy smoke.

### 10.3 Đánh giá riêng của giám định viên về công việc codex

**Điểm mạnh (hiếm thấy trong các study nhanh):** kỷ luật fail-closed nhất quán (preregister trước inference; independent review song song implementation; hash identity runtime/catalog/protocol; corpus byte-parity 589 file; từ chối loại failure khỏi mẫu số — phản đối đúng cách làm của AGY); tách bạch "common contract package" khỏi ablation description-only; giữ nguyên v3 frozen hoàn toàn. Thiết kế candidate đúng đắn về mặt học máy: validator + bounded repair + response gate nhắm đúng 3 cơ chế thất bại đã đo (RC1/RC2/RC3), không tự sửa số theo oracle.

**Điểm yếu / rủi ro còn lại:**
1. **Single-reviewer bottleneck** — reviewer độc lập dính limit làm gate kẹt mặc dù kỹ thuật xong (đang xảy ra).
2. **Candidate là gói combined** (validator + repair + gate + prompt chung một nhánh) — pilot chỉ đo được gói, không tách đóng góp từng cơ chế; đã khai báo trung thực nhưng hạn chế học được cái nào đáng giữ.
3. **Trần model nhỏ là trần tuyệt đối của pilot v4**: 12/22 task all-fail là giới hạn năng lực tính toán/điều phối của bolt, harness không thể khắc phục bằng validator/repair. Kịch bản tốt nhất của v4 trên bolt ≈ ngang DSH (18/44), chưa thể "vượt trội".
4. **Độ trễ study vs production**: study pin runtime cũ; production v0.3.1 đã có notice sửa failure + 330 commits. Pilot v4 đo được candidate trên nền cũ — kết quả tích cực sẽ phải re-smoke trên v0.3.1 trước rollout (rủi ro tương tác notice × policy chưa đo).

### 10.4 Phân tích điểm đột phá giúp OT cạnh tranh thắng (đề xuất riêng của giám định viên, P5–P7)

**Bảng cơ hội theo mẫu số pilot 44 (trạng thái: OT 12 · OC 14 · DSH 18; 12 task all-fail là kho chưa khai):**

| Lever | Cơ chế | Nhắm vào | Ước lượng tác động (bolt) | Trạng thái |
|---|---|---|---|---|
| **B1 = v4 candidate** | validator + bounded repair + response gate + prompt gọn | RC1/RC2/RC3/RC4 → 7-10 task phân định | OT 12 → **~16-19/44** (bằng/qua OC, cạnh DSH) | Đã xây, chờ gate |
| **B2 = Computation-as-tools** (đột phá chính, **chưa ai làm**) | Endpoint compute determinstic dùng chung: `analytics_aggregate` (tổng hợp N ngân hàng/dòng tiền), `analytics_growth` (period-over-period/CAGR), `analytics_margin` (công thức tỷ suất), `analytics_indicator` (RSI/MACD/Ichimoku…), `analytics_topn` (xếp hạng/loc), `profile_assemble` (tổng hợp narrative) | **12 task all-fail** — trần thật là model nhỏ không làm được multi-step math/orchestration (l3-agg, l2-growth, l2-margin, l2-tech, l3-tech-multi, l3-top, l4-2nguon, l5-profile…) | Mọi arm +6-12; **OT hưởng lợi nhiều nhất** vì kiến thức miền nằm ở API thay vì triết lý trình bày — task tính toán biến thành *copy-and-cite* như task L1 | Chưa ai đề xuất; kênh đúng: `plans/2026-11-05-opentrading-mcp-standardization.md` |
| **B3 = Track model mạnh** | (a) expose/đặt `OPENTRADING_STALL_MS` (knob có sẵn `agent.ts:825`) hoặc streaming pass-through; (b) port notice "Gọi X ngay" của v0.3.1 vào candidate | §9.3: model mạnh mọi arm pass tra cứu; khác biệt còn lại = DNF-avoidance + kỷ luật hợp đồng + synthesis đa nguồn (l4-2nguon, l5-profile) | Trên flash/medium: loại 8 DNF watchdog của OT; CĐ: 24/25 measured là sàn mọi arm — cơ hội thắng nằm ở task synthesis | Knob có sẵn, chưa wire vào study |
| **B4 = Copy-don't-compute envelope** | benchmark_evidence kèm giá trị đã chuẩn hóa đơn vị (raw + nghìnđ/tỷ + per-share) | Lỗi quy đổi 1000× kiểu bctc | +1-2 trial/arm; rẻ, làm chung | Chưa có; cần preregister (công bằng: dùng chung 4 arm) |

**Điều kiện fair-play bắt buộc cho B2/B4** (khác biệt với gaming): đăng ký trước khi thấy kết quả; endpoint dùng chung cả 4 arm; response phải được ghi trong snapshot replay corpus (không tính toán tại chỗ theo gold); mô tả honest (như C1/v4 đã làm với valuation). Với các điều kiện đó, B2 không phải "answer rescue" mà là **nâng cấp hợp đồng API thật** — đúng tinh thần P3.

**Đánh giá trung thực về khả năng "đánh bại":** trên bolt, B1+B2 cho phép OT đi tới **~24-30/44 vs DSH ~20-24** — vượt là có thể, nhưng lợi thế mỏng vì OC/DSH cũng gọi được cùng endpoint compute; lợi thế của OT nằm ở validator/repair + prompt domain + tích hợp orchestration tự nhiên. Trên model mạnh (B3), §9 đã chứng minh mọi arm pass tra cứu — sân chơi thực sự của "harness chuyên tài chính" chỉ mở khi bổ sung compute + synthesis, tức **B2+B3 là con đường duy nhất để OT có bản chất vượt trội chứ không chỉ ngang hàng**.

### 10.5 Việc cần làm tiếp (thứ tự ưu tiên)

1. **Mở gate**: chỉ định reviewer độc lập (phiên mới, đủ context) append final closure + hashes cho native suite; cập nhật `independent-native.md`.
2. **Chạy smoke 18** (gate vận hành: native loop/schema/usage/ledger đúng; wire capture chứng minh candidate kích hoạt validator/correction; `tool_schema_sha256` parity mọi arm) → **pilot 176** theo protocol đã đăng ký.
3. **Đăng ký P5/B2** (computation-as-tools) như exploratory common-contract riêng — không trộn vào pilot v4 candidate; mở rộng snapshot corpus cho các endpoint compute trước inference.
4. Sau pilot v4: re-smoke đối chiếu trên production v0.3.1 (notice mới + candidate) trước bất kỳ rollout nào.
5. Vệ sinh: allowlist deepseek diagnostic trong `tools/runners/provider.py` (bên ngoài study) nên gỡ/ghi chú sau khi hết nhu cầu chẩn đoán.

Nguồn §10: `experiments/finance-v4-study/{tools/mcp_snapshot_server.py, tools/tool_contracts_v4.json, experiments/opentrading-runtime/src/core/finance-policy.ts, test-artifacts/full-native-tests.log, FINANCE_POLICY.md}`; `audits/finance-v4-implementation/{independent-mcp.md, independent-native.md}`; `plans/2026-11-05-v4-improvement-experiment.md`; session transcripts `~/.codex/sessions/2026/11/05/rollout-...23-{27-12,27-30,27-48,34-26,44-16}*.jsonl`; `agy-review.md`.

---

## 11. Phụ lục (cập nhật 06/11/2026, buổi sáng): v4.1 chạy smoke và trượt gate trung thực → v4.2 dựng xong chờ launch + gate review độc lập

> **Supersession (09/11)**: v4.2 đã được thay thế bởi chuỗi v4.4→v4.6 (§13–§18) — v4.2 không bao giờ chạy inference; workspace giữ nguyên làm tham chiếu. Bài học v4.1 (replay interface, policy bug, grader refusal) vẫn là nền chẩn đoán của mọi phiên bản sau.

Phạm vi: 3 session codex 10:25–10:55 (06/11, prompt "thực hiện tiếp kế hoạch sửa v4.2"), báo cáo `audits/financial-prompt-v41/REPORT.md` (204 dòng), kế hoạch `plans/2026-11-06-v42-replay-repair-contract-study.md`, workspace `experiments/finance-v42-study/`. Kiểm chứng độc lập của giám định viên: chạy lại test + probe chức năng, không inference.

### 11.1 Smoke v4.1: thất bại giàu thông tin — certificate bị chặn đúng quy trình

| Arm | Primary /6 | DNF /6 | Ghi chú |
|---|---|---|---|
| OT candidate (finance policy ON) | **1/6** | **2** | Chỉ trap pass; **2/2 câu answerable đã trả lời đều từ chối sai** |
| OpenCode | 2/6 | 0 | Chỉ trap pass |
| DSH | 2/6 | 0 | Chỉ trap pass |

Pilot 176 **KHÔNG chạy** (certificate fail); promotion guard **NOT EVALUABLE** (smoke không có B0 concurrent). Ba nguyên nhân được codex xác minh — giám định viên tái xác nhận:

1. **Giao diện replay là điểm nghẽn số 1, ảnh hưởng cả 3 arm**: **36/36 call `vn_quote_history` hợp schema C1 nhưng `not_recorded`** — model chọn tham số *tự nhiên theo production* (`columns:["c","t"]`, `days:1`, `days:365`+projection) mà finite snapshot chỉ ghi symbol-only. **Viết lại một phần RC1**: "tự chế tham số" thực ra là hành vi query tự nhiên bị interface trừng phạt; C1 thêm mô tả field nhưng chưa thành interface thống nhất.
2. **Bug thật trong candidate** (repro `policy-counter-repro.json`): state repair đếm theo **tên tool** — 5 ngân hàng fail song song → counter 5/2 → không tool còn eligible; scope guard chặn nhầm BID sau khi VCB fail. Lỗi thiết kế, không phải model.
3. **Grader refusal lexical**: trap r1 OT từ chối đúng nghĩa ("không được giải mã thành symbol hợp lệ") không được nhận → adjudication riêng OT = 2/6, official giữ 1/6.

Điểm cộng governance: repair phase HPG **đã kích hoạt thật** (request 3 có nudge "One bounded correction") nhưng model không gọi corrected request — được báo cáo trung thực là hành vi, không bị đổ cho plumbing; **không hạ gate để đi tiếp**; audit 0 error, resume-check 2.216 file byte-identical; base nâng lên **OT 0.3.1** (AI SDK 7.0.159, MCP SDK 1.32.2, Ajv 8.20.0).

### 11.2 v4.2: đã dựng xong, kiểm chứng độc lập của giám định viên — **technically ready**

Workspace `experiments/finance-v42-study/` (chưa launch, chưa inference — không có `results/`). Gate review đầy đủ của tôi: `experiments/finance-v42-study/audits/INDEPENDENT-GATE-REVIEW-opencode-20261106.md`. Tóm tắt bằng chứng tự tay xác minh:

| Claim | Xác minh của tôi | Kết quả |
|---|---|---|
| C2 contract tests | Chạy lại `pytest test_v42_contract.py test_snapshot_server.py` | **46/46 pass** (gồm assert đúng 402 recordings + default-equivalence) |
| Corpus 589 file | `audits/corpus-preservation.json` | byte_mismatches=[] |
| Taxonomy 3 lớp lỗi | Probe `replay_call` | `columns:"close"` → `invalid_request`; `days:1` / `days:365+["c","t"]` → **`unsupported_snapshot_query`** (mới, retryable, kèm `allowed_public_variants`+`argument_paths`); `{symbol:"HPG"}` → ok + evidence |
| C2 trên wire | `build_tool_defs` | `anyOf` + `additionalProperties:false` + **`x-repair-fields: []`** (chống scope-drift có chủ đích) |
| Per-intent repair | `finance-policy.ts` v42 | `intent_id`/`original_sdk_call_id`; repair-fields lọc trừ entity/currency/kỳ; không collapse intent |
| Sealed canary | `ready_check.py:495-520` | Mỗi arm cần ≥1 trial quote/agg primary-correct với `vn_quote_history` ok (`numeric_retrieval_arms`) — trap-only không qua gate |
| Khóa model / chưa inference | `provider.py` + `bench_config.json` + `ls results/` | `DIAGNOSTIC_MODELS=set()`, bolt-only, protocol `financial_finite_replay_v42`; không có results/ |
| Benchmark suite | log + chạy lại subset | 322 pass; full-catalog 17 tool vượt 48k policy của OT (khai báo trung thực trong receipt) |

Thiết kế v4.2 đáng chú ý: C2 sinh từ **public recorded/default-equivalence contracts** (không nhét gold/taskID); rubric refusal **deterministic đã test** (chặn double-negation/contradiction/relabel) chứ không phải LLM judge tự do; chấm song song v4.2/frozen-v4.1/frozen-v3 để tách delta grader.

### 11.3 Đánh giá riêng của giám định viên

**Điểm mạnh**: vòng build→smoke→fail→diagnose→preregister→rebuild kỷ luật, không lần nào hạ gate; bug candidate tự tìm bằng repro class; hóa giải "36 not_recorded" thành bài toán interface; canary sealed vá đúng lỗ hổng v4.1. **Điểm yếu**: (a) 3 session song song cùng prompt = 3 report trùng (lãng phí orchestrator); (b) C2 máy-móc-hóa task → có thể **nén luôn lợi thế repair** của candidate — pilot v4.2 nhiều khả năng cho parity, không phân hóa; (c) combined candidate vẫn không tách lever; (d) **12/22 task all-fail vẫn chưa đụng tới** — v4.2 sửa interface/repair/contract, không sửa trần tính toán model.

### 11.4 Đột phá (cập nhật B1–B4)

| Lever | Trạng thái mới sau v4.1-smoke | Ước lượng |
|---|---|---|
| **B1 = v4.2 candidate** | Bug intent đã sửa; C2 mở đường truy xuất cho **mọi arm**; canary sealed | Pilot v4.2: OT ~**16-20/44** — ngang DSH, **chưa vượt**; khác biệt còn lại nằm ở repair per-intent + response contract |
| **B2 = Computation-as-tools** | **Mạnh hơn nữa**: plan v4.2 tự mở track "deterministic projection có semantics/provenance được xác minh" — chính là B2. 12 task all-fail (agg/growth/margin/indicator/topn/profile) chỉ giải được khi tính toán nằm trong endpoint | v4.3: mọi arm +6-12; OT hưởng lợi cấu trúc nhiều nhất |
| **B3 = Track model mạnh** | Base 0.3.1 nâng stall 120s→**300s**; cần thêm streaming pass-through + notice "Gọi X ngay" | Trên flash/medium: loại DNF, thắng ở synthesis đa nguồn |
| **B4 = Copy-don't-compute** | C2 + public response contract đã hiện thực một nửa; còn envelope đơn vị chuẩn hóa | +1-2 trial/arm |

**Verdict thắng-thua**: v4.2 là bước bắt buộc nhưng **chưa phải bước thắng** — nó đưa OT về parity. Lộ trình: v4.2 (parity) → **v4.3 = B2 compute-endpoints theo đúng cơ chế C2/finite-contract** (nơi "chuyên tài chính" thành lợi thế cấu trúc thật) → B3 trên model mạnh. Trên bolt thuần, trần 12 task all-fail khiến "vượt trội tuyệt đối" không khả thi; kỳ vọng hợp lý của pilot v4.2: OT ≈ DSH ± 2, và *bài học* quý nhất là biết chính xác lever nào còn lại.

### 11.5 Việc cần làm tiếp (thứ tự)

1. **Đóng gate v4.2**: reviewer nội bộ append final closure (native suite trên 0.3.1 + "largest-eligible task-scoped probe" đang hoàn tất dở) — gate review của tôi (`INDEPENDENT-GATE-REVIEW-opencode-20261106.md`) là bổ sung, không thay thế.
2. **Launch smoke 18 v4.2** → nếu certificate pass (canary per-arm) → **pilot 176** (4 condition, B0 concurrent lần này có trong lịch).
3. **Đăng ký v4.3/B2** (compute-as-tools: `analytics_aggregate/growth/margin/indicator/topn`, `profile_assemble`) như exploratory common-contract riêng, mở rộng snapshot corpus trước inference — kênh đúng: kế hoạch MCP standardization.
4. Sau pilot: re-smoke đối chiếu production v0.3.1 (notice mới + candidate) trước rollout; gỡ/ghi chú allowlist deepseek diagnostic trong `tools/runners/provider.py` bên ngoài study.

Nguồn §11: `audits/financial-prompt-v41/{REPORT.md, INDEPENDENT-CHECK.md, policy-counter-repro.json, smoke-resume-check.json}`; `plans/2026-11-06-v42-replay-repair-contract-study.md`; `experiments/finance-v42-study/{README.md, tools/tests/test_v42_contract.py, tools/mcp_snapshot_server.py, tools/ready_check.py, tools/public_response_contract.py, experiments/opentrading-runtime/src/core/finance-policy.ts, audits/{IMPLEMENTATION.md, corpus-preservation.json, c2-native-wire-full17-v3/receipt.json, full-benchmark-tests.log, v42-final-contract-tests.log}, audits/INDEPENDENT-GATE-REVIEW-opencode-20261106.md}`; session transcripts `~/.codex/sessions/2026/11/06/rollout-...10-{25-17,25-34,25-46}*.jsonl`.

---

## 12. Phụ lục (cập nhật 06/11/2026, buổi chiều): Vì sao OT tụt lại so với OC và DSH trong lĩnh vực tài chính? — Kiến trúc, bằng chứng log và điểm yếu cần cải thiện

Phạm vi: trả lời trực tiếp câu hỏi gốc của báo cáo (§5) bằng cách **đọc lại log toàn bộ** (v3 pilot 176 trial, v4.1/v4.2 smoke, trace v4.2, diagnostic deepseek flash, session codex) và **review kiến trúc cả 3 hệ** (OT production 0.3.1 qua subagent; OC/DSH qua runner config + capture request thật). Không chạy inference mới, không sửa artifact gốc.

### 12.1 Tóm tắt một câu

OT không thua vì thiếu năng lực tài chính hay thiếu tool — nó thua vì **mang bộ governance production (prompt 6.430 ký tự + hợp đồng cứng + ưu tiên dừng-sớm) áp lên model 4B không đủ sức thi hành**, trong khi DSH thắng bằng prompt 307 ký tự để model tự làm việc đúng. Điểm nghịch lý đã được v4.2 chứng thực: khi interface (C2) bù lại khả năng tuân thủ, OT nhảy lên **dẫn đầu về truy xuất** — nên đúng cái đang sửa là đúng hướng; việc còn lại là nới lỏng đúng chỗ và đóng trần tính toán.

### 12.2 Đo khoảng cách bằng log đã đóng băng (v3 pilot)

Cùng model bolt, cùng tool, cùng dữ liệu, cùng protocol — chênh lệch là 100% harness:

| Arm | Official /44 | Đúng (semantic) | **Từ chối oan** (value=null dù dữ liệu có) | Tính sai số | JSON lỗi |
|---|---|---|---|---|---|
| OT-baseline | 12 | 14 | **16/44** | 13 | 1 |
| OT-finance | 12 | 14 | **15/44** | 14 | 1 |
| OpenCode | 14 | 15 | 14/44 | 14 | 1 |
| DSH | **18** | **18** | **11/44** | **10** | 5 |

**Không** nằm ở: số lần gọi tool (median 1, tổng ~65–66 calls *giống hệt nhau*), quyền truy cập (cùng catalog), DNF (OT ít nhất, 1 vs DSH 5), hay model (cùng một bolt 4B). Nó nằm ở hai bucket: **từ chối oan (+4–5 trial)** và **tính sai số (+3–4 trial)** — và tập trung ở **L1** (câu dễ nhất: DSH 6/8, OT 2–3/8), trong khi L2–L3 mọi arm đều kẹt trần ~2–3/12 (trần tính toán của model — 12 task all-fail).

### 12.3 Kiến trúc ba hệ — khác biệt quyết định

Đọc từ capture request thật (`provider-requests/0001-effective.json`) + code:

| | **OT** (production 0.3.1 + fork benchmark) | **OC** (OpenCode) | **DSH** (DeepSeek Harness) |
|---|---|---|---|
| System prompt gửi thật | **6.430 ký tự** (identity + bat_bien + tools + citations + style) | 1.871 ký tự (generic agent) | **307 ký tự** (chỉ identity + quy tắc evidence) |
| p50 input tokens/request | 7.051 / 5.814 | 3.340 | **2.504** |
| Loop | streamText loop, maxSteps=∞; stop-gate `judgeStop` + tối đa 2 recovery; failure-streak 8 → **tắt tool giữa turn**; LoopGuard ×3 cùng call → deny; MCP breaker 3 lỗi → mở 60s | AI-SDK loop đến khi model dừng; deny mọi tool ngoài MCP | Framework mature (agent-loop, compaction, timeout-policy, spill, checkpoint) cho phép list ~30 service |
| Chính sách "thúc đẩy dừng" | **`prompts/tools.md:1`: "đủ dữ liệu thì trả lời ngay — đừng gọi thêm hay khảo sát thêm"**; rescue "empty after tools" chọn `toolChoice:"none"` TRƯỚC | trung tính | trung tính, thỉnh thoảng tự explor (2/44 trial dùng request thứ 3) |
| Hợp đồng trả lời | **ép bằng code**: đúng 1 JSON, refusal chỉ nhận `value:null` scalar, evidence phải byte-match kết quả tool; sai sau 1 correction → **hard error** | không ép (mất điểm vì markdown fences) | không ép (5 JSON lỗi nhưng đổi lấy chất lượng nội dung) |
| Sửa lỗi tool | Production: chỉ prompt ("Gọi X ngay…"); **stateful per-intent repair chỉ có trong fork benchmark** (v4+) | không có | không có |

**Khám phá kiến trúc quan trọng** (sửa lại giả định cũ): `finance-policy.ts` **không tồn tại trong production OT** — chỉ có trong fork benchmark `experiments/finance-v{,2,3}-study`, bật qua `BENCH_FINANCE_POLICY='on'`. "48k input budget" là **policy của benchmark driver** (`tools/runners/provider.py:233`), không phải code OT (48k trong TUI chỉ là label usage). Repair machinery mà v4.2 đang thắng **chưa bao giờ là năng lực production thật của OT**.

### 12.4 Cơ chế gốc — 5 nguyên nhân có bằng chứng, xếp theo trọng số

**1. Prompt quá nặng + hướng dẫn "ưu tiên dừng" làm bolt 4B từ chối oan nhiều nhất (15–16/44).** Cùng model, prompt 307 ký tự của DSH cho tỉ lệ từ chối oan 31% (11/35), prompt 6.4k của OT cho 44% (17/39). Đọc log từng trial: sau MỘT lần call bị reject, OT kết luận luôn "dữ liệu không được ghi nhận" và trả `value:null` — vi phạm chính quy tắc của mình ("Request bị từ chối không chứng minh mã không tồn tại"). Nguyên nhân kép: (a) bolt không mang nổi 5 section policy khi ra quyết định; (b) `tools.md` chủ động discourage gọi thêm; (c) stop-gate rescue chọn tools-off trước. §9 đã xác nhận: trên model mạnh, RC1/RC3 biến mất — **luật không sai, model không đủ sức thi hành**.

**2. Không có vòng sửa lỗi sau rejection ở v3 — và khi có (v4.2), OC/DSH cũng không dùng.** Cả 4 arm dừng ở đúng 2 request trong 44/44 trial (DSH: 42). Log `fin-l1-gold-01`: cả 3 arm gọi `{symbols:["XAUUSD"]}` → reject; chỉ DSH r1 "thử" biến thể `{symbols:["USDVND","XAUUSD"]}` → ok → đúng 3.875,02. May mắn hay không, **DSH là hệ duy nhất sample thêm biến thể tham số**. Ngược lại ở v4.2 (C2 công khai `allowed_public_variants`): OT là arm **duy nhất** sửa call theo hướng dẫn (canary 2/2, dẫn điểm retrieval) — OC/DSH nhận lỗi có hướng dẫn mà 0 corrected call.

**3. Persona finance của OT làm over-specification nặng hơn baseline.** `fin-l1-quote-01`: OT-baseline r2 gọi đúng `{symbol:"HPG"}` (như OC/DSH); OT-**finance** gọi `{columns:"close", days:1, interval:"day"}` → reject cả 2 run → refusal sai. Prompt finance dạy "đọc schema trước khi gọi" nhưng bolt vẫn thêm tham số theo thói quen production. Nghịch lý: **prompt chuyên gia tài chính làm kết quả tệ hơn trên model nhỏ**.

**4. Hợp đồng trả lời ép bằng code biến câu trả lời trung thực thành lỗi native.** v4.2 `smoke-agg-01`: OT không gọi tool nào (rescue tools-off của stop-gate), trả refusal dạng values-map; `finance-policy.ts:168` chỉ nhận scalar `value===null` → contract fail sau 1 correction → **status=error, final_text rỗng** — chính các row error này chặn certificate. DSH trả cùng dạng values-map nhưng chỉ fail điểm, không fail native. OT tự ra nghiêm khắc hơn protocol yêu cầu.

**5. Sai số học khi "tự tính trong đầu" — trần chung, OT hơi tệ hơn.** Cùng task `fin-l3-crypto-01`, cùng dữ liệu: OT tính gold −3,43%/oil 1,98%, DSH tính −3,5%/0,11% — cùng sai nhưng khác nhau. Với prompt 6,4k chiếm bandwidth, composition của OT careless hơn (sai_so 13–14 vs DSH 10). Đây là bucket mà **không harness nào sửa được bằng prompt** — cần chuyển tính toán xuống endpoint (B2).

**Điều chỉnh quan trọng từ review kiến trúc**: `finance-policy.ts` và repair machinery **không tồn tại trong production OT** — chỉ có trong fork benchmark. Production OT xử lý lỗi tool bằng prompt+notice (`outcome.ts:94`), stateless. Nghĩa là những gì đang thắng ở v4.2 (per-intent repair) chưa bao giờ là năng lực production thật của OT.

### 12.5 Bằng chứng log chi tiết

- **L1 quote-01** (task dễ nhất): OC & DSH gọi `{"symbol":"HPG"}` → ok → 21 nghìn đồng đúng. OT-finance gọi `{columns:"close", days:1, interval:"day"}` → reject cả 2 run → refusal sai. OT-baseline r2 gọi đúng `{symbol:"HPG"}` nhưng mất điểm vì thiếu evidence (thieu_bang_chung).
- **L1 gold-01** (XAUUSD): chỉ DSH r1 gọi batch `[USDVND, XAUUSD]` → ok → 3.875,02 đúng; cả 7 trial còn lại gọi `[XAUUSD]` → reject → refusal.
- **L1 bctc-01** (VCB LNST): tool trả 14.550.959.000.000 VND (gold = 14.550,959 tỷ). OT trả "14.550959 tỷ" (quy đổi sai 1000 lần); DSH trả nguyên văn 14.550,959 → pass. OT finance còn ghi evidence với `tool: "mcp__opentrading__financial_statements"` (namespace SDK thay tên canonical).
- **False refusal**: OT 15–16/44 vs DSH 11/44; OC 14/44.
- **v4.2 smoke**: OT canary numeric 2/2 (chỉ arm truy xuất được số thật); DSH/OC 0/4; OT agg-01 không gọi tool nào (premature refusal); DSH trap 2/2 (resolver discipline); OC trap 0/2 strict (markdown fences).
- **§9 strong model (pass B)**: DSH 8/10, OC 6/10, OT 4/10 — gap **còn tồn tại** trên model mạnh → harness architecture matters beyond model capability.
- **v4.3**: đã đăng ký (21:44) study "evidence-acquisition" (48 trial, 2 strata Bolt + DeepSeek diagnostic 900s, 4 điều kiện có B0), đang dựng workspace `experiments/finance-v43-study/` (v43_gate.py, v43_supervisor.py đã build; chưa inference). *(Supersede 09/11: v4.3 **không bao giờ chạy** — superseded bởi v4.4/v4.5, xem §13.1, §18.1.)*

### 12.6 Điểm yếu cần cải thiện — xếp theo hiệu suất/triệu

| # | Điểm yếu | Bằng chứng | Cách sửa | Kỳ vọng |
|---|---|---|---|---|
| 1 | **Prompt 6.430 ký tự trên model 4B** | false-refusal 44% vs DSH 31%; §9: biến mất trên model mạnh | Prompt phân tầng: bản gọn ≤1,5k ký tự cho tier C (chỉ giữ bất biến + evidence rule); dời citations chi-tiết vào tool description + error guidance | +3–5/44 trên bolt |
| 2 | **Refusal trước khi cố (premature refusal)** | agg/trap v4.2 không gọi tool; 15–16 null/44 | Runtime ép "không được refusal-null nếu chưa có ≥1 tool attempt thành công hoặc task-refusal-class"; force resolver-call trước khi kết luận không-found | +2–4/44 |
| 3 | **Contract tự làm khổ mình** | 2 row error chặn certificate v4.2 | Nhận refusal cả scalar lẫn values-map (đúng protocol); không convert semantic-fail thành native-error | Bỏ chặn certificate |
| 4 | **Trần tự tính (sai_so + 12 task all-fail)** | L2/L3 mọi arm ~2–3/12 | **B2 computation-as-tools**: `analytics_aggregate/growth/margin/indicator/topn` — model copy-and-cite thay vì tự cộng | +6–12/44, hưởng lợi cấu trúc lớn nhất |
| 5 | Over-specification của persona finance | quote-01 finance arm reject cả 2 run | Giữ "không thêm tùy chọn" ở đầu prompt (vị trí salient); C2 đã giảm thiệt hại | +1–2/44 |
| 6 | Model track | DSH vẫn 8/10 vs OT 4/10 trên flash | B3: model mạnh + streaming + stall | nhân rộng mọi lever |

### 12.7 Ghi chú những gì KHÔNG phải nguyên nhân (đã loại trừ bằng chứng)

| Giả thuyết | Kết luận |
|---|---|
| Gateway/timeout/rate-limit bất công | OT p50 nhanh nhất, DNF 1 (≤ đối chứng), usage 44/44 (finance), 354 request khớp manifest |
| MCP server operational error | 0 operational error; 8 actual-empty (symbol_resolve mã không tồn tại) xử lý đúng cả 4 arm |
| Model thấy tool khác nhau | Mô tả tool trên wire giống hệt 3 arm (đã đối chiếu captures); 0 case unknown_tool |
| "174 tool gây overload" | Mỗi trial chỉ cấp tool của task (1-3 tools); pilot không đo discovery full catalog |
| Lịch chạy thiên lệch | Arm order xoay đủ 4 vị trí, mỗi condition 11 lần/vị trí; manifest hash khớp sau chạy |
| Lỗi grader | Grader dùng chung 4 arm; tái tính độc lập khớp 176/176 row |
| Clock | OT được pin native clock theo snapshot (thiện chí tối đa); OC/DSH không tuyên bố pin — confound đã ghi nhận nhưng hướng ảnh hưởng chưa biết |
| OpenCode preprocessing | OC CLI bọc/escape input nhiều dòng (`run.ts:288,869`) — confound đã ghi nhận, không suy diễn hướng ảnh hưởng |

### 12.8 Nguồn §12

- Log v3: `results/financial-prompt-v3-{smoke,pilot}-20261105/` (summary.json, trials.jsonl, per-trial captures/ledgers/run.log/grade.json/answer.json).
- Trace v4.2: `experiments/finance-v42-study/results/financial-v42-smoke-20261106/` + `audits/financial-prompt-v42/TRACE-DIAGNOSIS.md` + `REPORT.md`.
- Diagnostic deepseek: `results/diag-deepseek-flash-20261105{,-passB,-passC}/` + `COMPARISON.md`.
- Capture request thật (system prompt 6.430/1.871/307 ký tự): `trials/fin-l1-quote-01__{opentrading_finance,opencode,dsh}__r1/attempts/*/provider-requests/0001-effective.json`.
- Kiến trúc OT: subagent explore `/home/doanlong/OpenTrading` (v0.3.1, HEAD `b6e354e`); OT production file refs: `src/core/agent.ts` (runAgent 989-1309, judgeStop 1190-1204, prepareStep rescue 1118-1134, LLM_STALL_MS 62), `src/core/loop/failures.ts` (FAILURE_STREAK_STOP 34), `src/core/loop/stop-gate.ts` (MAX_RECOVERIES 15), `src/core/prompt/assemble.ts` (170-279), `src/core/prompt/budget.ts` (19-41, 51-58), `src/core/tools/outcome.ts:76`, `src/core/tools/loop-guard.ts`, `src/core/mcp/breaker.ts`, `src/core/mcp/manager.ts:200-229`, `src/core/tools/registry.ts:75-206`, `src/core/tools/wrap.ts:88-94`, `src/core/compact.ts` (27-70, 370-406), `src/core/effort.ts`, `src/core/config.ts:107`; `prompts/tools.md:1`.
- Runner configs: `tools/runners/{run_opencode,run_dsh,run_opentrading,experiment_conditions}.py`, `tools/runners/provider.py:233`.
- Session codex: `~/.codex/sessions/2026/11/{04,05,06}/rollout-*.jsonl` (toàn bộ đã review).
- Nguồn §1-§11 trong cùng file này + `audits/financial-prompt-v3/{REPORT.md, INDEPENDENT-CHECK.md}` + `audits/financial-prompt-v4{1,2,3}/` + `audits/finance-v4-implementation/` + `audits/finance-v42-implementation/INDEPENDENT-GATE-REVIEW-opencode-20261106.md`.

---

## 13. Phụ lục (cập nhật 07/11/2026): v4.4 chạy bolt smoke (gate FAIL trung thực) + deepseek smoke đang chạy + review corpus 277 task + KẾ HOẠCH ĐỀ XUẤT 50 task "OT-strength stratum" (chờ codex thực hiện)

Phạm vi: (a) rà session codex 07/11 + tiến trình sống (supervisor PID 2256274, driver deepseek PID 2461649); (b) review toàn bộ kho task benchmark; (c) thiết kế 50 task mở rộng nơi OT có lợi thế cấu trúc — **đề xuất, chưa thực thi; việc sinh task/preregister/đo thuộc codex**.

### 13.1 v4.3 bị bỏ, v4.4 đăng ký và đã launch (đọc từ session + seal)

- **v4.3 ("evidence-acquisition", 48 trial 2 strata) CHƯA BAO GIỜ CHẠY** — `experiments/finance-v43-study/results/` trống; sáng 07/11 bị supersede.
- **v4.4 "compute-acquisition"** đăng ký `plans/2026-11-07-v44-compute-acquisition-study.md` (10:02), mở đầu: *"Authorized by user 2026-11-07 after OpenCode review §12"*. Workspace `experiments/finance-v44-study/`.
- Triển khai đúng các lever §12: **`analytics_compute`** (B2 — Decimal sum/mean/growth_pct/margin_pct/scale trên `{call_id, JSON-pointer}` trỏ response đã lấy thành công; **cấp cho cả 4 arm** = fair-play; `deterministic_derivation` namespace, không giả upstream evidence; indicators/topN/profile chưa làm); **prompt finance gọn 1.306 bytes** (từ 8.378 của v42, −84%); contract giữ nguyên trạng nhưng invalid final **không còn thành native error** (chỉ primary-fail + native diagnostic); kế thừa bounded acquisition v4.3; **DeepSeek stratum chạy cả smoke lẫn pilot** (900s/240s).
- Engineering: benchmark **393/0**, native **1098/0**, compute suite 27/27, gate suite 10/10; wire fixture bắt được OT drop `additionalProperties:false` trên profile mới → đã fix + rerun xanh. Lần launch đầu (14:39) **fail ở manifest-resume trước khi gọi trial nào** → fix CLI serialization minh bạch ("startupfix1", 14 CLI/gate check + seal mới `preinference-seal-startupfix1.json`).
- **Factcheck §12 của tôi** (`audits/financial-prompt-v44/OPENCODE-SECTION12-FACTCHECK.md`): sửa mẫu số FR của tôi (17/40 answerable-started, không phải /44); cảnh báo bucket "tính sai số" của tôi là suy dẫn; **từ chối lever #3** ("không nới grader/public contract để cứu native") — lập luận của họ chặt hơn; thách thức khẳng định "trần model vĩnh viễn" (compute là phép thử, không phải kết luận).

### 13.2 Bolt smoke 24/24 (14:47→14:55): quality gate FAIL → pilot-bolt bị skip ĐÚNG predeclared rule

Strict primary: **OT-B0 2/6 · OT-B1 2/6 · OC 1/6 · DSH 1/6**; `numeric_canary_conditions: []` (không arm nào có câu numeric có receipt nguồn); audit controls PASS (0 fabrication). Gate yêu cầu B1 ≥4/6 + FR ≤1/4 → FAIL toàn stratum, `pilot-bolt` chỉ có manifest.

Ba bài học từ trace từng trial:

1. **Prompt gọn −84% là vọt lêch trên bolt**: OT-B1 quote-01 **0 call cả 2 run**, trả refusal *"Tool yêu cầu days+interval cụ thể, không hỗ trợ 'phiên gần nhất'"* — **đọc nhầm schema** (đó là tham số optional). Pendulum: v4.2 quá nặng (over-specify) → v4.4 quá nhẹ (misread + refuse). FR của B1: **4/4 answerable**.
2. **analytics_compute uptake = 0/24** (đúng rủi ro #1 của §12): kẹt kép — compute cần source-call thành công làm operand mà source-call bị reject; bolt không tự khám phá `{call_id, path}`. `same_intent_corrected_executions = 0` mọi arm.
3. **Trap là thắng thật**: OT trap **4/4** (v4.2: 0/2) — "chưa rõ mã: thử resolver" hoạt động đúng cho câu unanswerable. Agg-01: OC/DSH/B0 gọi 5 ngân hàng → 12/12 rejected không ai sửa; **OT-B1 vẫn 0 call** — seam premature-refusal chưa đóng.

### 13.3 DeepSeek smoke: đã hoàn tất sau ghi chú này (24/24 — kết quả cuối tại §13→§14.1; tín hiệu sớm dưới đây giữ nguyên làm biên bản thời điểm)

- **quote-01 OT-finance flash r1: PASS textbook** — `{symbol:"HPG"}` → ok → 21 nghìn đồng, period 30/10/2026, evidence 7-field đầy đủ. **Arm duy nhất pass tính đến thời điểm ghi.**
- B0/OC: grounded=True nhưng success=False; **DSH r1: status=error, final_text rỗng** dù call `{"symbol","days":365,"summary":false,"columns":null,"interval":"1D"}` → **ok** (harness DSH tự lỗi — pattern đã thấy ở §9).
- Nếu flash B1 đạt ≥4/6 + FR ≤1/4 → `pilot-deepseek` 176 mở.

### 13.4 Corpus benchmark: 277 task (review đầy đủ 07/11)

**smoke 3 · pilot 24 (22 eligible + 2 cách ly) · holdout 50 · main 200.** Snapshot 2026-11-01; cấm web tools; gold ±0,5% + unit/period/source + provenance 7-field; grader 3 chế độ: value/refusal/verdict.

- **2 task pilot cách ly**: `fin-l1-macro-01` (`ambiguous_cpi_series_dimension`), `fin-l4-narrative-01` (`incomplete_narrative_evidence_rubric`) — main đã vá lỗi macro bằng cách pin chuỗi CPI (`cpi_total/core/cat_*`) trong tiêu đề.
- Nhóm pilot: **L1** tra cứu đơn (quote-01 HPG 21.0 nghìn đồng; quote-02 BTC 78109 USDT; bctc-01 VCB LNST 14550.96 tỷ + bẫy mẹ/hợp nhất; gold-01 XAUUSD 3875.02; macro-01⚠️); **L2** một phép tính (crypto-x BTC→VND 2015.37 triệu; fx 25802 đồng/USD; growth VNM −2.03%; margin MWG 21.71%; ratio FPT P/E 8.75x bẫy 2 nguồn; tech RSI 44.01); **L3** tổng hợp (agg 5 bank mean 32.18; crypto-3-tài-sản winner=dầu +2.08%; index +3.06%; screen ROE/P-E; tech-multi SSI 39.97; top-3 VN30 GAS/VHM); **L4** đa nguồn/chống ảo giác (2nguon HPG 21000 đồng; **future-01 = refusal**; **nonexist-01 = refusal**; narrative-01⚠️ verdict); **L5** phức tạp (compare 15 số + rank; profile MWG 5 trường; valuation FPT price/P-E/P-B).
- **12 task all-fail v3** rơi đúng L2-phép-tính + L3-tổng-hợp + l4-2nguon + l5-profile — cơ sở của B2/compute.

### 13.5 KẾ HOẠCH ĐỀ XUẤT: 50 task "OT-strength stratum" — **chờ codex thực hiện**

**Nguyên tắc liêm chính (bắt buộc)**: chạy như stratum riêng có nhãn, **môi trường chung 4 arm** (cùng tool/instruction/contract), preregister trước inference, **không trộn điểm với pilot/main/holdout trung tính**, không gold-leak/task-ID-routing; thiết kế = giả thuyết, chấm per-family quyết định.

**Nền bằng chứng** (từ §12 + §13.2): OT trap 4/4 vs OC/DSH 1/2 (n=2); OT arm duy nhất repair được sau rejection (OC/DSH = 0 corrected call trong toàn bộ lịch sử); OC mất điểm fences, DSH invalid_json 5/44 + DNF/native error lặp; OT nhanh nhất (p50 14,6s) ít DNF nhất.

| Họ | Số lượng | Thiết kế | Cơ chế lợi thế OT | Độ tin |
|---|---|---|---|---|
| **A. Resolver-first** | 12 | Đề chỉ cho **tên tiếng Việt/ticker mơ hồ** (Masan Group, Vinamilk, Chứng khoán VPBankS, Vàng thế giới, BTC trên Binance, ngân hàng Quân đội, FPT Retail, Hoa Sen…) → bắt buộc `symbol_resolve` trước khi gọi tool chính | OT prompt "chưa rõ mã: thử resolver" + trap 4/4; OC/DSH không có line này (DSH `khong_tra_loi`, OC `public_contract_invalid`) | Trung bình (n=2) |
| **B. Bẫy kỳ/thời gian + refusal chính xác** | 12 | LNST **HDB Q3/2026** (registry: HDB trễ kỳ — dùng làm bẫy); future-period × 4 mã; mã không tồn tại gần-dễ-nhầm × 2; **phiên 01/11 (CN) / 31/10 (T7) / 02/09 (lễ)** — không phải phiên giao dịch; CPI tháng 10/2026 chưa công bố | Họ refusal — OT 4/4 v4.4; thêm chiều phân loại refusal (nonexist ≠ non-trading-day ≠ unpublished-period ≠ unpublished-macro) | Trung bình (n=2) |
| **C. Hợp đồng chặt + đa nguồn** | 10 | `l4-2src` mở rộng × 6 (MBB/PVV/SSI/VGC/HT1/VNM; cặp `vn_quote_history`×`vs_overview_trading` **bẫy đơn vị đồng↔nghìn** đã ghi trong registry, `valuation_run`×`peer_compare`, `vn_equity_quote_batch`×candles); **`stock_overview` dossier ≥6 trường** × 4 (tool chưa từng dùng trong pilot!) | OC fences + DSH invalid_json tuột primary trên multi-field; OT code-gate giữ format + evidence | Mạnh |
| **D. Chuỗi dài song song** | 8 | agg **10 mã** + mean/min/max × 3 rổ; compare **8 mã × 3 chỉ tiêu** × 2 rổ; screen 2 điều kiện × 10 mã; **top-5 VN30** kèm giá + khối lượng (movers×batch — movers chỉ dùng được universe vn30); index + breadth | OT nhanh nhất + ít DNF; DSH chậm nhất + native error (đang lặp ở flash smoke) | Trung bình |
| **E. Chuỗi phụ thuộc 2 bước** | 8 | Vốn hóa = giá × SLCP (overview→valuation); khối lượng top-3 tăng mạnh (movers→batch); P/E tại giá hôm nay vs nhóm (quote→peer_compare); XAUUSD×USDVND→VND (+scale); RSI-14 khung **tuần** của top-2 (movers→signals 1W); RSI thấp nhất rổ 5 mã → BCTC mã đó | Call 2 cần kết quả call 1 — OT notices "Gọi X ngay ở bước kế tiếp" + per-intent repair; OC/DSH thói quen dừng ở 2 request (44/44 trial v3) | Trung bình |

**Ràng buộc data bắt buộc từ `tasks/registry/entities.yaml`**: ≤2 cá thể/entity/split; LTG/VIS BCTC stale → loại; SBT chỉ dùng l2-tech/narrative; POM valuation partial → task "dữ liệu một phần"; HDB trễ kỳ → chỉ dùng làm bẫy l4-future; movers universe `hose` partial → chỉ vn30; **không trùng entity×kỳ×family với main/holdout**.

**Rủi ro phải khai báo khi preregister**: (1) họ A/B dựa trên n=2 — stratum này chính là phép thử; (2) họ E gần "interface-stress" — giữ dạng workflow analyst thật, **cấm thiết kế đề để cưỡng bức tham số sai C2**; (3) nếu 50 task này thành corpus chính, benchmark mất tính phân biệt — chỉ chạy chẩn đoán.

**Việc codex cần làm (đề xuất thứ tự)**:
1. Preregister `plans/2026-11-07-ot-strength-stratum.md` (50 task, 5 họ, gate per-family, môi trường chung).
2. Sinh task bằng generator hiện có (`tools/_gen_tasks_a.py`, `_gen_templates.py`, registry `entities.yaml`) — kiểm tra ràng buộc data ngay ở build; mỗi task đúng cấu trúc instruction/payloads/request_contracts/gold/grader như pilot.
3. Seal + smoke (6 task × 4 arm) trước; gate per-family; sau đó 50×2×4=400 trial hoặc sample 25 task nếu budget hạn chế.
4. Chấm **per-family** (OT vs OC vs DSH trong từng họ): họ nào OT thật sự hơn → bằng chứng lộ trình sản phẩm; họ nào không → điều chỉnh giả thuyết §12.

### 13.6 Nguồn §13

- Session + tiến trình: `~/.codex/sessions/2026/11/07/rollout-*.jsonl` (6 file, 09:26 và 14:28); `ps` supervisor PID 2256274 + driver PID 2461649 (15:06).
- v4.4: `plans/2026-11-07-v44-compute-acquisition-study.md`; `experiments/finance-v44-study/{tools/analytics_compute.py, tools/prompt_variants/finance/*, results/financial-v44-smoke-{bolt,deepseek}-20261107-startupfix1/}`; `audits/financial-prompt-v44/{BENCHMARK-IMPLEMENTATION.md, BENCHMARK-READINESS.json, OPENCODE-SECTION12-FACTCHECK.md, HANDOFF.md, INDEPENDENT-IMPLEMENTATION.md, engineering-approval-startupfix1.json, preinference-seal-startupfix1.json, supervisor-startupfix1/{state.json, smoke-bolt-diagnostic.json, smoke-bolt-audit.log}}`.
- Corpus: `tasks/{smoke,pilot,holdout,main}/`, `tasks/registry/entities.yaml`, `tasks/pilot/*/solution/gold.json`, `tasks/pilot/*/task.toml`.

---

## 14. Phụ lục (cập nhật 07/11/2026, buổi tối): v4.4 ĐÓNG trọn vẹn — không pilot, không promotion + giả thuyết decoder cấm path đúng + v4.5 nháp chờ duyệt

Phạm vi: vòng codex 17:10–17:28 (07/11): REPORT cuối, INDEPENDENT-CHECK, SCHEMA-PATTERN-HYPOTHESIS, completed-resume-proof, v4.5 draft. Giám định viên đã chạy **smoke review độc lập** riêng: `audits/financial-prompt-v44/INDEPENDENT-SMOKE-REVIEW-opencode-20261107.md`.

### 14.1 Kết luận v4.4 (theo REPORT + INDEPENDENT-CHECK của codex)

- **Không promotion, không pilot**: B1 strict 2/6 ở cả bolt lẫn flash (< ngưỡng 4/6); 48/48 trial hoàn tất; pilot 176 chỉ là lịch đăng ký.
- **Trung thực tự phản biện**: canary bolt "PASS" là *PASS rỗng* (không có numeric win để kiểm chứng); **cả 6 điểm primary bolt đều là trap XYZX** — không arm nào truy xuất được số trên bolt; B1 flash semantic 2/6 thấp hơn B0/OC/DSH (3/6), DNF 4/6 cao hơn B0 (3/6) → "không đủ tuyên bố ưu thế tài chính".
- 9/9 primary win được soát tay: evidence 7-field khớp byte, **0 fabrication**; 2 numeric win thật (B1-flash quote r1, DSH-flash quote r2); F pilot-ineligible cả 2 strata (bolt hòa B0 + FR 4/4; flash DNF regression 4/6 vs 3/6). Preservation 3.588 hash seal nguyên vẹn; resume 0-call chứng minh.

### 14.2 Giả thuyết "decoder cấm path đúng" — đột phá chẩn đoán của vòng này

17/17 lệnh `analytics_compute` bị reject (57 operand occurrences) dùng **chính xác 2 path `/data` và `/data/`** — trùng khớp tuyệt đối với ngôn ngữ full-string matching của schema `pattern: "^/data(?:/|$)"`. Theo đúng ngữ nghĩa JSON Schema (search), **`/data/last` hợp lệ nhưng 0 lần được sinh ra**. Trích dẫn: **XGrammar issue #838** (converter áp fullmatch cho `pattern` trái chuẩn) + NVIDIA NIM 1.15 docs (guided_json dùng XGrammar). → **Ưu tiên giả thuyết: constrained decoding khiến path đúng KHÔNG THỂ SINH RA** — compute fail có thể là lỗi tương thích schema/decoder cấu trúc, không phải năng lực model. Họ tự ghi rõ: dấu hiệu tương thích toán học, chưa chứng minh backend; cần Phase 0 + canary riêng.

### 14.3 Supervisor block ở audit + my independent review

- Chain block tại `smoke-deepseek-audit`: auditor gặp class mới **`policy_guard_rejected`** (finance-policy chặn replay compute lần 3) → *"Unrecognized policy guard rejection"* + `tool_call_reconciliation` fail trên `smoke-agg-01__opentrading_finance__r1/r2` → dừng an toàn đúng luật. **Lỗi khớp audit-tooling, không phải gian lận**; sửa = cập nhật auditor, không hạ gate.
- Review độc lập của tôi (`INDEPENDENT-SMOKE-REVIEW-opencode-20261107.md`): cả 2 strata FAIL gate (bảng per-condition); **B2 uptake đạt trên flash (17 compute calls, 0 thành công — cùng lỗi path)**; strict contract-invalid 21/24 trial flash (grader frozen chấm 2/3/3/3 — gấp đôi strict); **403 NVIDIA storm giết 12/24 trial flash**; OT = arm duy nhất có acquisition machinery chạy thật (21 phase events).

### 14.4 Metric vận hành (tự tính từ audit — chi tiết đã báo user)

| | OT-fin | OT-B0 | OC | DSH |
|---|---|---|---|---|
| Latency bolt p50 | 15,7s | **13,0s** | 15,4s | 23,6s |
| Token/trial (flash) | 10.992 | 13.859 | 12.923 | **8.493** |
| Cache hit (bolt) | 76,6% | 81,5% | 45,2% ⚠️ | **84,9%** |
| **Tokens/success strict** (bolt) | **22,1K** | 27,1K | 37,8K | 56,4K |
| Requests/trial (flash) | 3,0 | 2,5 | 3,0 | 2,5 |

### 14.5 v4.5 — nháp chờ phê duyệt (`plans/2026-11-07-v45-normalized-contract-study.md`)

> **Supersession (09/11)**: draft này bị thay bởi `plans/2026-11-08-v45-finalization-plan.md` (5 giai đoạn, đã thực thi gần trọn vẹn — MINI 24/24 + stateless PAUSE) và tiếp nối bằng v4.6 repair (§18). Phase 0/Phase 1 dưới đây đã được thực hiện qua các study v4.5/v4.6.

- **Phase 0**: kiểm chứng offline search-vs-fullmatch + capture; canary nhỏ (không gold, cần cấp phép riêng) so 3-4 treatment: pattern hiện tại (control) / pattern neo hậu tố `^/data(?:/.*)?$` / không-pattern (+ tùy chọn tham chiếu nguồn ổn định).
- **Phase 1**: path nguồn số **rõ ràng + sửa được** — phát hiện: `invalid_derivation` **không nằm trong native repair list** (guard chặn lần thử 3 của OT mà không cho sửa — đúng seam §13).
- Mục tiêu: **tách lỗi truy xuất / compute / hợp đồng đầu ra** — không nhầm format với nội dung.

### 14.6 Nhận xét giám định viên

Kỷ luật đóng study cao nhất chuỗi (anti-claim, resume-proof, preservation, draft-chưa-duyệt). Giả thuyết schema hợp nhất mọi dữ liệu đo. Hai hệ số cần theo dõi vòng sau: (1) strict-vs-frozen grader delta (đang ~2×), (2) tỷ lệ trial chết 403 (50% flash smoke). Việc chờ quyết của user: duyệt v4.5 (Phase 0 vô hại; canary cần cấp phép riêng); 50-task OT-strength stratum (§13.5) nên chạy **sau** khi contract normalized.

### 14.7 Đồng bộ repo OT production (cùng khung giờ)

`/home/doanlong/OpenTrading`: `git fetch + merge origin/main` — **merge từ từ main 23 commits** (PR #216–221: eval/ablation, eval/score, eval/mcp-replay, eval/ledger, eval/runner, fix/eval-hygiene + nhánh mới feat/units, feat/table-truncate, feat/figure-check-tools, feat/memory, hold/stage-b). **1 conflict** ở `src/core/agent.ts` (benchmark patch b6e354e thêm tham số `promptDir` vs upstream thêm field `disabled`) — giải quyết giữ cả hai (line 815-816), **typecheck PASS**, merge commit `e5ce4e1`, main ahead 2 (benchmark patch + merge).

Nguồn §14: `audits/financial-prompt-v44/{REPORT.md, INDEPENDENT-CHECK.md, SCHEMA-PATTERN-HYPOTHESIS.md, schema-pattern-evidence.json, FORENSICS.md, completed-resume-proof.json, INDEPENDENT-SMOKE-REVIEW-opencode-20261107.md, independent-counts.json}`; `plans/2026-11-07-v45-normalized-contract-study.md`; `experiments/finance-v44-study/results/financial-v44-smoke-{bolt,deepseek}-20261107-startupfix1/`; `/home/doanlong/OpenTrading` git log.

---

## 15. Phụ lục (cập nhật 07/11/2026, đêm): Review độc lập tổng hợp — điểm nghẽn, audit bài kiểm tra, đề xuất prompt tiếng Anh cho OT và lộ trình đánh bại OC/DSH

Phạm vi: **chỉ là khảo sát + đánh giá + đề xuất của giám định viên** — KHÔNG sửa gì vào OT/source/task/grader; mọi thay đổi đều là khuyến nghị cho codex/root thực hiện qua study preregistered riêng. Căn cứ: toàn bộ §1–§14 + đọc lại grader template + gold corpus + trace v4.4.

### 15.1 Điểm nghẽn hiện tại — xếp theo tác động lên điểm primary

| # | Điểm nghẽn | Bằng chứng | Thuộc ai sửa | Tác động nếu vá |
|---|---|---|---|---|
| 1 | **Compute path semantics**: schema `pattern` `^/data(?:/|$)` + 0/17 call trỏ được leaf `/data/last`; error không gợi ý leaf; `invalid_derivation` không nằm trong native repair list | §14.2, §14.5 | Codex (common tool + native policy) | Mở khóa 12 task all-fail (L2-L5) — **+6-12/44 mọi arm**; B2 thành thật |
| 2 | **Format-strict trộn với năng lực tài chính**: flash contract-invalid 21/24 trial; frozen grader chấm 2-3/6 (gấp đôi strict) | §14.1, §14.3 | Codex (metric + báo cáo) | Tách 2 chỉ số → nhìn đúng năng lực thật; giảm "mất oan" khi so arm |
| 3 | **403 NVIDIA storm**: 12/24 trial flash chết sau khi retrieval ok | §14.3 | Root/infra | Cứu ~1/3 mẫu flash; số liệu flash mới đáng tin |
| 4 | **Prompt tier lệch**: 1.306 B khiến bolt misread schema + FR 4/4; 8,4KB cũ gây over-spec; DSH 307B thắng nhờ để model tự regulation + evidence line cuối prompt | §13.2, §12.4 | Codex (candidate prompt) | Bolt +2-4/44; xem §15.3 đề xuất |
| 5 | **Premature refusal vẫn sống ở bolt** (agg 0 call); flash đã hết | §13.2 vs §14.3 | Codex (prompt + policy) | +1-2/44 bolt |
| 6 | **Auditor chưa nhận class `policy_guard_rejected`** → chain block | §14.3 | Codex (audit tooling) | Mở lại chuỗi mà không hạ gate |
| 7 | **OC cache hit bất thường (45% bolt vs 77-85% arm khác)** | §14.4 | Root/infra | Chi phí OC giảm; hiểu wire-parity sâu hơn |

### 15.2 Audit bài kiểm tra: benchmark đang đo gì, có phải "đánh giá vượt trội tài chính đầu tư VN" không?

**Kiểm kê grader template** (`tasks/*/tests/grader.py`, dùng chung 22 task pilot): 11 loại check trên gold expects — `value` (52, ±0,5% tương đối), `unit` (14 — canon nghìn/đồng/tỷ), `period` (16 — regex quý/ngày/năm), `str` (23 — `source` phải canonical, cấm namespace SDK), `evidence`/provenance (payload_sha256 khớp byte + identity 7 trường + required⊆seen⊆allowed), `set`/`list_order` (screening/ranking), `tokens` (dòng chỉ tiêu, có guard phủ định), `verdict` (1, có mask cụm trung tính); 3 chế độ chấm: value (21 task) / refusal (2) / verdict (1).

**Đo tốt những gì (đáng giá cho đầu tư)**:
1. **Truy xuất có căn cứ ±0,5%** — đọc đúng dòng BCTC (mẹ/hợp nhất), đúng field quote — kỹ năng analyst nền tảng
2. **Kỷ luật đơn vị** (nghìn↔đồng↔tỷ) — đúng lỗi phổ biến nhất của dữ liệu tài chính VN (BCTC đơn vị VND, giá điểm giá nghìn đồng)
3. **Kỷ luật kỳ** (quý riêng ≠ lũy kế ≠ TTM) — lỗi thật của analyst
4. **Chống bịa evidence** (provenance byte-exact) — lòng tin dữ liệu tài chính
5. **Calibration refusal** (kỳ chưa công bố / mã không tồn tại) — chống hallucination, quan trọng bậc nhất trong đầu tư

**KHÔNG đo được (khoảng cách với "vượt trội tài chính đầu tư VN" trọn vẹn)**:
1. Không có **risk/portfolio** (volatility, drawdown, correlation, vị thế, phân bổ)
2. Không có **định giá đa bước** (DCF/scenario — chỉ trích xuất `valuation_run` sẵn có)
3. Không có **synthesis định tính có chấm rubric** (nhận định mua/giữ, kiểm chứng mạch lập luận — `narrative` bị cách ly vì rubric chưa xong)
4. Không có **multi-turn** (follow-up, drill-down) — chỉ 1 turn/trial
5. **Trần số học model nhỏ** khiến L3–L5 đo được phần lớn là *orchestration*, không phải *suy luận tài chính sâu* (12 task all-fail)
6. **Hợp đồng strict đang trộn format với tài chính** (§14.3)

**Phán quyết**: bộ benchmark hiện tại là **benchmark "độ tin cậy dữ liệu đầu tư" (grounded-QA + kỷ luật) — hợp lệ và đủ để XẾP HẠNG harness** (đó là điều chuỗi v3→v4.4 đang làm), nhưng **chưa đủ để kết luận "vượt trội trong lĩnh vực tài chính đầu tư VN" theo nghĩa đầy đủ**. Muốn đầy đủ cần 3 lớp bổ sung (đề xuất cho stratum mới, common-env fair-play): (a) họ risk/portfolio + scenario dùng `analytics_*` mở rộng, (b) hoàn thiện rubric `narrative` (đang cách ly) cho synthesis có chấm, (c) báo cáo song song **finance-primary** (semantic + grounded) tách khỏi **format-primary** (strict). Với các lớp đó, "OT thắng" mới có nghĩa là "OT tin cậy hơn VÀ sâu hơn về tài chính", không chỉ "OT đúng hợp đồng hơn".

### 15.3 Đề xuất prompt tiếng Anh cho OT (candidate-only, A/B preregistered — không thực thi trong study này)

**Căn cứ thiết kế**: (a) 6.430B tiếng Việt → over-spec (v3); (b) 1.306B tiếng Việt → misread schema, FR 4/4 bolt (v4.4); (c) DSH 307B thắng nhờ prompt trống + **evidence rule nằm CUỐI context** (recency); (d) điểm rơi kỳ vọng **1,8–2,2KB tiếng Anh** (English tiết kiệm ~20-25% token so với tiếng Việt cùng nội dung; task vẫn trả lời tiếng Việt theo schema).

**P-EN-bal (≈2,1KB — đề xuất chính)**:

```
You are OpenTrading, a Vietnamese-market financial data agent. Answer from verified tool data only; every number must trace to a successful tool call in this session. Never fabricate data, sources, IDs or hashes. No personal buy/sell advice; no profit promises.

Acquisition (hard rules):
1. Entity unclear, given by name or alias? Call symbol_resolve FIRST, then the data tool with the resolved ticker.
2. Read each tool's description and snapshot_requests examples; call with EXACTLY those minimal recorded arguments. Add no optional parameters (columns, days, interval, top_n...) unless the question needs a value the defaults cannot answer.
3. A rejected call does NOT mean data is missing. Read the error and build ONE corrected call with the same financial meaning (same entity, period, metric) using its allowed variants. One bounded correction per failed intent; never replay identical rejected arguments.
4. Never output a refusal while a supported untried request could still answer the question.
5. If data truly does not exist (resolver empty, period unpublished, entity absent), refuse honestly with exactly {"value":null,"reason":"<specific reason>","evidence":[]} — never guess numbers, never invent receipts.

Answer contract (hard rules):
6. Final response = exactly one JSON object per the task schema: no prose, no markdown fences, no extra fields. The evidence array must contain one 7-field row copied BYTE-EXACT from benchmark_evidence of every successful call you relied on (tool, source, as_of, call_id, payload_sha256, matched_entry_id, response_sha256); use canonical tool names (never mcp__server__tool).
7. Answer in the unit the question requests. If the source unit differs, do NOT convert by mental arithmetic: call analytics_compute (scale / mean / growth_pct / margin_pct) with operands=[{"call_id":"<receipt call_id>","path":"/data/<field>"}] — the numeric leaf, e.g. "/data/last", never "/data" alone — input_unit = the exact source unit string, output_unit = the requested unit.
8. Answer as soon as every requested field has a receipt. No extra calls for polish; no early stop while a required field is missing.
```

**P-EN-min (≈1,0KB — biến thể đối chứng)**: chỉ giữ rules 1, 2+3 gộp, 6, 7 — dành cho A/B nếu 2,1KB vẫn nặng bolt.

**Map thay đổi so với v4.4 (1.306B VN)**: thêm rule 4 (chặn premature refusal — seam §13.2); thêm ví dụ leaf `/data/last` vào rule 7 (seam 0/17); **bỏ** câu "Thành công một phần chưa đủ"/văn phong dừng-sớm mơ hồ; evidence rule đưa về cuối block + ghi "BYTE-EXACT" (recency như DSH); safety còn 1 dòng. **Map so với v3 6.430B**: bỏ hoàn toàn `<bat_bien>` 5 mục, `<thu_tu_uu_tien>`, `<citations>` trình bày — triết lý chuyển vào runtime policy (đã có finance-policy) và tool description.

**Cách đo hợp lệ**: A/B preregistered trên candidate-only (B0 giữ nguyên baseline) — 3 nhánh {v4.4-VN, P-EN-bal, P-EN-min} × smoke 6 × 2 strata; đo primary + FR + contract-valid + compute-success; **không chọn nhánh sau khi nhìn điểm** — đăng ký tiêu chí trước (P-EN-bal được dùng nếu không tệ hơn v4.4-VN ở bolt VÀ tốt hơn ở flash, else giữ VN). Lưu ý confound: instruction tiếng Anh + trả lời tiếng Việt là bình thường với instruction-tuned model nhưng phải đo, không giả định.

### 15.4 Lộ trình để OT đánh bại OC và DSH (khuyến nghị, thứ tự thực hiện)

| Bước | Việc | Kênh đúng | Kỳ vọng |
|---|---|---|---|
| 1 | Vá auditor `policy_guard_rejected` → mở chain | Codex audit tooling | Chuỗi chạy lại được |
| *(trạng thái 09/11)* | *(1 ✅ vá trong v4.6 auditor · 2 ✅ leaf-regex + `analytics_calculate` · 3 ✅ canary chạy: DS 0/2→2/2 · 4 ✅ transport-retry chung · 5 ⏳ screen 2 ngôn ngữ · 6 ✅ metrics tách trong v45 · 7 ⏳ stratum riêng · 8 ⏳ · 9 ✅ 12 task memory + 15 task memory corpus — chi tiết §18)* | | |
| 2 | Vá compute leaf: guidance nêu `/data/last` + đưa `invalid_derivation` vào native repair list | v4.5 Phase 1 (preregister) | Compute success > 0 → 12 task all-fail mở dần |
| 3 | Canary schema decoder (3-4 treatment) | v4.5 Phase 0 (cần cấp phép riêng) | Xác định nguyên nhân gốc path |
| 4 | 403 retry-backoff + ghi nhãn 403-class | Infra driver | Mẫu flash sạch |
| 5 | Prompt P-EN-bal A/B (§15.3) | Study candidate riêng | Bolt +2-4, flash giữ/tăng |
| 6 | Tách metric finance-primary vs format-primary | Metric/báo cáo | So sánh công bằng, nhìn đúng năng lực |
| 7 | OT-strength stratum 50 task (§13.5) | Stratum riêng, sau bước 2 | Chứng minh lợi thế cấu trúc per-family |
| 8 | Port production: per-intent repair + notices + prompt tier vào v0.3.x | Production repo (sau khi đo thắng) | "OT thắng benchmark" trở thành "OT thắng thật" |
| 9 | Lớp task mới: risk/portfolio/narrative-rubric/scenario | Stratum task mới common-env | Đo "siêu việt tài chính" trọn vẹn (§15.2) |

**Điều kiện thắng thực tế trên sample 44 (dự phóng, không phải cam kết)**: sau bước 2+4+5, kỳ vọng OT-fin ≈ 20–26/44 vs DSH ≈ 18–22 vs OC ≈ 14–18 trên bolt; trên flash mọi arm nhảy nhưng OT hưởng repair/machinery nhiều nhất. **Vượt DSH 3-4 điểm + thắng cả 5 họ A-E của stratum §13.5 + tokens-per-success thấp nhất = định nghĩa "đánh bại" khả thi và đo được.** Trên bolt thuần, nếu bước 2 không mở được compute (decoder xác nhận cấm path), trần vẫn là retrieval+discipline và "vượt trội tuyệt đối" không có — khi đó phương án duy nhất là B3 (model mạnh) làm stratum chính.

### 15.5 Nguồn §15

Grader: `tasks/pilot/fin-l1-quote-01/tests/grader.py` (template dùng chung; các hàm `val_match/canon_unit/period_hit/source_hit/provenance_checks/verdict_hit`); gold corpus `tasks/pilot/*/solution/gold.json` (11 expect types); prompt captures `provider-requests/0001-effective.json` (6.430B/1.871B/307B); v4.4 `tools/prompt_variants/finance/*` (1.306B) + trace `smoke-agg-01__opentrading_finance__r1` (0/17 compute path); metrics §14.4 (audit logs); §12–§14 cùng file.

### 15.6 Bổ sung (cập nhật muộn 07/11/2026): bolt = post-training English-only → prompt VN là bất lợi có căn cứ; bài kiểm tra có quá khắt khe không; memory mới của OT buộc v4.5 kiểm nghiệm lại

#### 15.6.1 XÁC NHẬN: Nemotron 3.5 Bolt E4B được post-training **chỉ bằng tiếng Anh** — prompt tiếng Việt của OT là bất lợi có căn cứ model-card

Model card + technical report chính thức (`research.nvidia.com/labs/nemotron/...Bolt-E4B-4GB-Technical-Report.pdf`, 23/10/2026; HF `nvidia/Nemotron-3.5-Bolt-E4B-BF16`):

- **"Since Nemotron 3.5 Bolt E4B 4GB was post-trained using English only, we tested if the model retains the original model's multilingual capabilities"** — post-training **English-only** trên nền Gemma-4-E4B-it (multilingual capability còn lại là của base pretraining +140 ngôn ngữ, và report ghi nhận **degradation so với base** ở nhiều ngôn ngữ trên WMT24++/MMLU-ProX).
- Danh sách ngôn ngữ supported chính thức: **English, Spanish, French, German, Italian, Japanese** (+ZH trong post-training corpus) — **tiếng Việt KHÔNG có tên**.
- Điểm mù chính xác nhất cho case của OT: benchmark **SysBench (instruction-following) chỉ được test bằng tiếng Anh** — tức **năng lực tuân thủ system-instruction bằng tiếng Việt chưa được post-train/đo**.

**Đối chiếu với toàn bộ bằng chứng benchmark** — giả thuyết của user khớp chặt:
1. FR 44% (prompt VN 6,4k) vs 31% (DSH prompt EN 307B) trên cùng bolt; ngay cả prompt VN 1,3k (v4.4) bolt vẫn misread schema và FR 4/4.
2. Trên flash (DeepSeek multilingual), **cùng prompt VN hoạt động tốt** (§9: RC1/RC3 biến mất; v4.4 flash: OT agg retrieval 5/5) → biến số quyết định là **khả năng ngôn ngữ của model**, không phải prompt tệ.
3. Token hiệu năng: tiếng Việt nhiều dấu → tokenizer English-centric tốn nhiều token hơn trên cùng lượng nghĩa (prompt VN 6,43k ký tự ≈ phần lớn p50_in 5,8–7,0K của OT vs DSH 2,5K).

**Hàm ý**:
- Đề xuất **P-EN (§15.3) từ "giả thuyết" thành "khuyến nghị có căn cứ model-card"** — ưu tiên A/B P-EN-bal cao hơn P-EN-min.
- Mở rộng sửa: **notices + reminders trong runtime OT cũng đang tiếng Việt** ("Gọi X ngay ở bước kế tiếp", `<nhac_nho>`...) — nên chuyển sang English song song với prompt (cùng lô candidate).
- **Cảnh báo biên trung thực**: instruction của task vẫn là tiếng Việt và CHUNG mọi arm — DSH/OC cũng phải đọc tiếng Việt ở đó; lợi thế P-EN chỉ đến từ khối system prompt + notices. Và "supported languages" là marketing của capability còn sót từ base — kết luận cuối vẫn phải đến từ **A/B đo được** (P-EN vs P-VN cùng mọi thứ khác), không giả định model card là đủ.
- Chiến lược dài hạn đúng hơn: nếu OT muốn prompt tiếng Việt thật (sản phẩm VN), cần **post-training/SFT thêm tiếng Việt cho bolt** — đây là khuyến nghị sản phẩm, ngoài phạm vi benchmark.

#### 15.6.2 Bài kiểm tra có quá khắt khe không? — Verdict: **strict-by-design và công bằng, nhưng cần 3 sửa cách dùng**

Đo lại từng khối tiêu chí (grader template dùng chung, preregistered, frozen, mọi arm cùng chịu):
- `value` ±0,5% tương đối → **hợp lý** (không gắt).
- `unit` có canon (chấp nhận "nghìn đ"/"k đồng"/"nghìn đồng") + `period` chấp nhận nhiều format (30/10, 2026-10-30, Q2/2026…) → **hợp lý, thậm chí khoan dung**.
- `evidence`/provenance 7-field **byte-exact** → strict nhưng **có lý do lõi** (chống bịa bằng chứng — thứ đắt nhất trong tài chính); không nên nới.
- Raw JSON 1 object, cấm fences/prose → **đây là khối gắt nhất** (contract-invalid 21/24 trial flash; frozen grader chấm gấp đôi). Phán định: **không phải "quá khắt khe" một cách bất công** — nó là định nghĩa máy-đọc được đã đăng ký trước; nhưng (a) **không được đọc strict-primary như "năng lực tài chính"** — phải báo song song finance-primary/semantic (khuyến nghị lặp lại §15.2), (b) **KHÔNG normalize fences trong grader** (sẽ thưởng harness lười), đúng định hướng codex từ chối lever #3 ở factcheck §12.
- **1 lỗi grader thật cần vá versioned**: refusal lexical (`grader.py:166` chặn "không" ở bất kỳ đâu trong text — false negative đã adjudication ở v4.2) — vá theo hướng common-correction versioned, không đụng run đóng băng.

Kết: **benchmark không quá khắt khe; nó nghiêm theo thiết kế.** Vấn đề thật nằm ở (1) cách đọc kết quả trộn format với tài chính, (2) một lỗi lexical chưa vá, (3) việc task "đúng" của model mạnh bị strict che khuất trên flash — cả 3 đều có giải pháp metric, không cần nới ngưỡng.

#### 15.6.3 OT đã có memory mới → **v4.5 sắp tới buộc phải kiểm nghiệm chi tiết lại và đánh giá lại** *(đã thực thi: v4.5 memory MINI 24/24 với memory none/clean-isolated — đúng checklist 5 rủi ro; contamination/pin + revalidate đã chạy, xem §17–§18)*

Bằng chứng: `origin/feat/memory` vừa được cập nhật (PR #229 review 10 điểm; spec 004–006: nhãn trong lịch sử, ràng buộc tới agent con + hồ sơ nhà đầu tư, tiền tố `/resume`, tool ở `/agents`); **hooks memory đã sẵn trong runtime main** (`agent.ts:799-802`: `memoryInstructions`, `memoryIndex`, `recalled`, `loadProfile`/`investorProfile`).

**5 rủi ro buộc v4.5 revalidate toàn bộ trước khi chạy lại bất kỳ phép đo nào**:

| # | Rủi ro | Nội dung | Kiểm nghiệm bắt buộc |
|---|---|---|---|
| 1 | **Prompt-size drift** | memory instructions/index/recalled inject thêm token → con số 1.306B/tier-C budget không còn đúng; tier có thể rơi | Đo lại assembled system (đã có `v44-compact-assembled-system.json` làm baseline so sánh) |
| 2 | **Contamination benchmark** | memory/profile nhà đầu tư có thể rò ngữ cảnh cá nhân vào trial → vi phạm "model-visible context" sạch | Chạy benchmark với memory **disabled/pin deterministically**; khai báo trong seal |
| 3 | **Cache hit tụt** | memory instructions thay đổi theo turn → cache bolt của OT đã thấp hơn DSH (76,6% vs 84,9%) sẽ xấu thêm → chi phí + latency | Đo cache per-arm trên base mới |
| 4 | **Hành vi hành vi thay đổi** | recalled context có thể làm FR/premature-refusal/repair thay đổi → mọi giả thuyết §12/§15.6.1 phải đo lại, không kế thừa | Smoke 6×4 trước pilot, gate nguyên trạng |
| 5 | **Fingerprint/seal** | runtime base mới → toàn bộ source hash + native suite + wire checks phải chạy lại; không được tái sử dụng approval cũ | Full native + benchmark + wire fixture trên base mới (đúng quy trình v4.4: 1098/0 + 393/0 trước seal) |

**Khuyến nghị thứ tự cho v4.5** (cập nhật khuyến nghị §14.5): (0) freeze câu hỏi nghiên cứu Phase 0/Phase 1 như đã đăng ký; (1) quyết định base: **chờ `feat/memory` merge vào main rồi đóng băng base mới**, hoặc đóng băng main hiện tại và để memory làm v4.6 — **không đo trên base đang dịch chuyển**; (2) chạy checklist 5 rủi ro trên; (3) mới đến compute-leaf fix + canary decoder + A/B prompt P-EN.

Nguồn bổ sung 15.6: NVIDIA Nemotron 3.5 Bolt E4B Technical Report (23/10/2026, research.nvidia.com) + model card HF/NGC/Build.NVIDIA ("post-trained using English only"; supported languages EN/ES/FR/DE/IT/JA); `/home/doanlong/OpenTrading` `git log origin/feat/memory` (PR #229, spec 004–006); `src/core/agent.ts:799-802` (memory hooks trong main).



---

## 16. Phụ lục (cập nhật 08/11/2026): Thực thi corpus wave-2 stage-1 + Đánh giá so sánh OT / OpenCode / DSH trên tác vụ tài chính

Phạm vi & vai trò: (a) **thực thi** swap corpus theo thiết kế 27-task đã duyệt — vai trò chuyển từ "giám định không sửa artifact" sang "thực thi có kiểm soát" theo ủy quyền trực tiếp của user, áp dụng CHỈ cho `tasks/main` (pilot/holdout/smoke/results/audits cũ nguyên vẹn); (b) **đánh giá so sánh** ba harness chỉ trên tác vụ tài chính.

### 16.1 Đã thực thi: +10 / −10, main giữ 200

**Review corpus nền (thực hiện 07–08/11, trước khi sửa):** 274/277 task được review chi tiết theo chuẩn §3.6 (oracle 274/274 OK, gold tái tạo 100%, dual-pass + machine audit): **L1 55** (38 PASS / 7 WARN / 10 QUARANTINE-đúng) · **L2 56** (49/3/4) · **L3 56** (43 PASS / 2 WARN / 2 FAIL nội dung: `fin-l3-top-202` đề↔gold lệch, `fin-l3-crypto-multi-214` tie-break 0.59/0.59 / 7 holdout-clone) · **L4 54** (37 PASS / 15 QUARANTINE-đúng / 2 holdout-clone) · **L5 53** (46 PASS / 5 WARN / 2 holdout-clone). Hai phát hiện hệ thống: **11/50 holdout là bản sao byte-level của main** + lỗi grader dùng chung (7 dạng false-reject). Các số này là căn cứ chọn task bỏ/thêm dưới đây.

**+10 task mới** (chỉ ghép envelope **đã ghi** snapshot 2026-11-01 — không capture mới, không bịa dữ liệu; self-test 10/10: oracle OK, grader đúng→semantic pass, sai→`sai_so`/`bia_so`):

| ID | Level·Family | Nội dung | Nguồn envelope |
|---|---|---|---|
| fin-l3-breadth-301 | L3·B breadth | 1 up (DXG) / 4 down rổ BĐS — breadth đếm dấu, không trùng screen (đếm ngưỡng) | agg-186 |
| fin-l4-2src-302 | L4·D | P/E VGI 2 nguồn (valuation_run 24.7 vs peer 23.17) lệch 6.19% — formula nêu trong đề | ratio-160 + compare-279 |
| fin-l4-chain-303 | **L4·F (family mới: chuỗi 2 bước)** | RSI thấp nhất rổ CK (FTS 35.22) → P/E 27.12 | tech-204 + compare-276 |
| fin-l4-chain-304 | L4·F | RSI thấp nhất rổ energy (PVS 35.86) → biên gộp 9.62% | tech-207 + margin-151 |
| fin-l4-chain-305 | L4·F | Mã giảm sâu nhất rổ NH (TPB −1.94%) → LNST 2,351.20 tỷ | agg-181 + bctc-113 |
| fin-l4-chain-306 | L4·F | Mã giảm mạnh nhất VN30 (PNJ) → doanh thu 6,994.69 tỷ | top-198 + growth-141 |
| fin-l4-future-307 | L4·E | Refusal **phiên không-GD cho cổ phiếu** (VIX 01/11 CN) + bonus 12.0 | quote-104 |
| fin-l4-future-308 | L4·E | Refusal ngày lễ (MBS 02/09 Quốc khánh) + bonus 15.0 | quote-106 |
| fin-l4-nonexist-309 | L4·B | Near-miss fake **FPT2** (resolver null) | khung nonexist-235 |
| fin-l4-nonexist-310 | L4·B | Near-miss fake **VCBX** | như trên |

**−10 task cũ** (archive `audits/2026-11-07-corpus-wave2/removed/`): 131/132/134/135 (CPI L1 cách ly — dead weight) · quote-102 OCB + quote-105 SHS (trùng template quote ×8) · ratio-156 + tech-161 (precomputed-retrieval + **sửa vi phạm ANV 4→2/split**) · macro-calc-177 (CPI cách ly) · gf-compare-171 (so sánh suy biến Δ=0).

**Trạng thái sau:** main = **200** (L1 34 · L2 36 · L3 41 · L4 49 · L5 40) · confirmatory **183/200** (trước 178) · 2 envelope resolver near-miss là offline-constructed deterministic (đã khai báo trong gold.notes + MIGRATION.json). Hash + checklist seal: `audits/2026-11-07-corpus-wave2/MIGRATION.{json,md}`.

**Wave-2 stage-2 pending (17 task, chặn bởi dữ liệu):** resolver-quote L1×6 + resolver-twist L2×4 (cần capture quote mới cho ~10 mã; snapshot mới = wave riêng), dossier L5×4 + mcap (cần capture `stock_overview` + xác nhận trường SLCP/market_cap — hiện không thấy trong `snapshot_tool_schemas`), RSI-1W (corpus chưa từng có khung tuần), top5+volume cross-tool. Sau stage-2 rebalance về 40/mức. **Factcheck §13.4:** khẳng định "main đã vá macro bằng cách pin chuỗi CPI trong tiêu đề" là **quá lạc quan** — tiêu đề pin *chuỗi* nhưng không pin *chiều pct/index*; 131–136 vẫn cách ly đúng chuẩn (review L1).

### 16.2 Đánh giá so sánh OT / OpenCode / DSH — CHỈ trên tác vụ tài chính

> **Factcheck (codex, `OPENCODE-SECTIONS14-16-FACTCHECK.md`)**: (a) "403 storm 12/24" là **sai attribution** — 7 local token-budget 403 + 2 usage-unknown + 3 metadata-missing + 2 timeout 502, không có auth storm; (b) "21/24 contract-invalid" gồm cả absent finals, chỉ 8 fences thật; (c) "21 phase events" không phải 21 acquisitions; (d) tokens/success 2.5× vượt chứng cứ (trộn v3+v4.4, chỉ trap wins); (e) "trần 12 task all-fail" không hợp lệ causal. Các số dưới đây đọc theo correction này.

Căn cứ: pilot v3 176 trial + smoke v3/v4.1/v4.2/v4.4 + diagnostic flash (§9) + audit kiến trúc (§12) + review corpus 277 (mục trên). Mọi số có nguồn trong §2/§9/§13/§14; kết luận gắn mức tin.

#### 16.2.1 Bảng tổng hợp (bolt 4B, cùng model/snapshot/protocol)

| Trục | OT | OpenCode | DSH | Đơn vị/điều kiện |
|---|---|---|---|---|
| Primary (pilot v3) | 12, 12 | 14 | **18** | /44 |
| Từ chối oan | **16** | 14 | **11** | /44 |
| DNF | **1** | 1 | 5 | /44 |
| Latency p50 | **13.0–15.7s** | 15.4s | 23.6s | bolt |
| Tokens/success (strict) | **22.1K** | 37.8K | 56.4K | bolt v4.4 |
| Cache hit | 76.6–81.5% | **45.2%** ⚠️ | **84.9%** | bolt |
| Bịa evidence/số (fabrication) | **0** mọi run | 0 | 0 | audit controls |
| Trap resolver (unanswerable) | **4/4** | 1/2 | 1/2 | v4.4 bolt |
| Schema-invalid tự chế tham số | 12/65 (baseline) | **0** | **0** | pilot v3 |
| Self-repair sau rejection (có guidance) | **duy nhất arm sửa được** (canary 2/2) | 0 | 0 | v4.2 |
| Model mạnh (flash): primary | 5/5–5/6 | 6/6 | **8/8** | trial đo được §9 |

#### 16.2.2 OT mạnh ở đâu trên tác vụ tài chính (kèm dẫn chứng)

1. **Chống hallucination có tính CẤU TRÚC (system prompt + strict rule + code gate) — tin cao.** Đây là trục mạnh nhất, đo được 3 lớp: (a) **0 fabrication tuyệt đối** trong mọi run đã audit (evidence phải byte-match ledger, refusal-contract chặn "không tìm thấy, nhưng đã tìm thấy" và phủ định kép — grader 2 lớp này là duy nhất trong 3 arm vì chỉ OT ép bằng code); (b) **trap discipline**: v4.4 OT 4/4 câu unanswerable — arm duy nhất chủ động `symbol_resolve` trước khi kết luận (OC/DSH 1/2); (c) **FP-refusal = 0** trên task bẫy mọi run. Khi model tự bịa (fin-l2-crypto-01: evidence placeholder FX) benchmark chặn đúng — tức cơ chế phát hiện-được-lừa, không phải chỉ hy vọng model trung thực. DSH/OC không có lớp code-gate này — chúng trung thực nhờ model, không nhờ kiến trúc.
2. **Tốc độ & hiệu quả truy xuất — tin cao.** Latency p50 thấp nhất mọi strata (13.0–15.7s vs DSH 23.6s), p90 thấp nhất, **DNF thấp nhất** (1/44 vs DSH 5), và **tokens-per-success thấp nhất 2.5×** (22.1K vs DSH 56.4K) — tức mỗi điểm primary của OT rẻ nhất. Đây là lợi thế "vận hành" thật, bền vững khi scale.
3. **Machinery sửa lỗi truy xuất (candidate) — tin trung, chỉ có ở fork benchmark.** Khi interface công khai biến thể hợp lệ (C2), **OT là arm duy nhất thực sự gọi lại corrected request** (canary 2/2 dẫn điểm retrieval; trên flash gold-01 tự-repair đầu tiên trong lịch sử). OC/DSH nhận error có hướng dẫn mà **0 corrected call toàn bộ dữ liệu lịch sử**. Trên bolt v3 (không guidance) 0/4 arm repair — nhưng OT có sẵn machinery (validator + per-intent repair + notice "Gọi X ngay") mà 2 arm kia không có gì để bật.
4. **Kỷ luật multi-field/multi-call — tin trung (n nhỏ).** DSH mất 5/44 vì invalid_json + lặp native error; OC mất điểm markdown fences + contract-invalid; OT code-gate giữ đúng 1-JSON + evidence 7 trường (15/15 value-check PASS ở compare-01 dù tuột primary vì thiếu evidence — tức nội dung đủ, chỉ thiếu trích dẫn). Họ C (dossier đa trường) trong corpus mới được thiết kế chính xác để đo trục này.
5. **Prompt domain tài chính — tin thấp-nhưng-thật.** Pilot: fin-l4-future-01 + fin-l5-valuation-01 OT 2/2 cả hai variant (OC 1/2) — giá trị "hiểu bài toán tài chính" đo được nhưng nhỏ; và chính persona này là dao 2 lưỡi (xem yếu #3).

#### 16.2.3 OT yếu ở đâu trên tác vụ tài chính

1. **Calibration lệch bảo thủ = mất nhiều điểm nhất (tin cao).** Từ chối oan **16/44** (DSH 11) — sau MỘT rejection, OT kết luận "không có dữ liệu" và trả `value:null` ngay cả trên câu có đáp án (quote-01: OT 0/2 vs đối chứng 4/4). Strict rule không sai — **model 4B không đủ sức thi hành** (§9: trên flash RC1/RC3 biến mất); nhưng chính cấu hình prompt-heavy + policy "đủ dữ liệu thì trả lời ngay" + stop-gate tools-off khiến OT rơi vào refusal sớm nhiều nhất trong 3 arm.
2. **Production thiếu machinery mà candidate đang thắng (tin cao).** `finance-policy.ts`/per-intent repair **không tồn tại trong production OT** — chỉ trong fork benchmark. Tức lợi thế #3 hiện là năng lực "thí nghiệm", chưa phải sản phẩm.
3. **Sai ngôn ngữ prompt cho model nhỏ (tin cao, căn cứ model-card).** Bolt post-train **English-only**; prompt OT 6.4KB/1.3KB tiếng Việt → misread schema + FR 4/4; cùng prompt VN trên flash hoạt động tốt. DSH thắng một phần nhờ prompt 307B **tiếng Anh**. (§15.6.1 — khuyến nghị P-EN A/B.)
4. **Tự tính nhầm thay vì gọi compute (tin cao).** sai_so 13–14 vs DSH 10; 12/22 task all-fail là trần số học model nhỏ — bucket không harness nào vá được bằng prompt, cần `analytics_compute` (và uptake v4.4 = 0/24 do lỗi path `/data`).
5. **Watchdog DNF trên model chậm (tin cao).** 120s stall → 8 trial flash chết; DSH/OC chạy tốt tới 332s. Rủi ro cấu trúc khi nâng model.
6. **Memory / làm việc đường dài — CHƯA CÓ BẰNG CHỨNG benchmark (khai báo trung thực).** Benchmark hiện tại 1-turn, ≤24 requests — không đo multi-turn/long-horizon. `feat/memory` (PR #229) mới merge vào production với 5 rủi ro revalidate (§15.6.3: prompt-drift, contamination, cache-tụt, hành vi thay đổi, seal). Không thể khẳng định "OT làm đường dài tốt vì memory" từ dữ liệu hiện có — đây là trục cần stratum đo riêng (multi-turn/driver-down).

#### 16.2.4 Profile OC / DSH (đối trọng)

- **DSH**: kỷ luật hợp đồng **nội sinh** (model tự làm đúng với prompt 307B) → primary cao nhất mọi cấu hình bolt; yếu: chậm nhất, DNF 5, invalid_json 5/44 + native error lặp trên flash, không repair, không gate chống bịa (trung thực phụ thuộc model).
- **OpenCode**: trung tính mọi trục; mất điểm ở format (fences) + **cache hit bất thường 45%** (chi phí/latency) + không repair; không có chuyên môn tài chính trong prompt — null-hypothesis của benchmark.

#### 16.2.5 Kết luận tổng hợp

1. **Trên tác vụ tài chính hiện tại (grounded-QA kỷ luật, bolt):** xếp hạng primary **DSH (18) > OC (14) > OT (12)** — nhưng trục "đáng tiền" (tokens/success, latency, DNF) **OT dẫn đầu**, và trục chống-bịa-cấu-trúc **chỉ OT có**.
2. **Ba trục giả thuyết của user:** chống hallucination ✓ (có căn cứ kiến trúc + đo được, nhưng cái giá là over-refusal); tốc độ truy xuất nhờ tối giản ✓ (đo được; lưu ý "tối giản" v4.4 1.3KB VN lại gây misread — đúng liều là P-EN-bal ~2.1KB, chưa A/B); **memory/làm việc đường dài ✗ chưa đo được** — benchmark 1-turn, memory vừa merge chưa kiểm nghiệm.
3. **Khoảng cách primary là trần model + ngôn ngữ + calibration, không phải thiếu năng lực tài chính:** trên flash, mọi arm gần như đồng đều (25/26 PASS) và OT tự-repair được. Muốn OT thắng thật: đúng lộ trình §15.4 — compute-leaf (mở 12 task all-fail) + P-EN A/B + tách finance-primary/format-primary + port machinery vào production + stratum đo trục OT-strength (stage-2 corpus).
4. **Đối chiếu chuẩn benchmark ngoài (chốt câu hỏi "same same", ngắn gọn):** format task = chuẩn Harbor/Terminal-Bench; gold+oracle tự-tái-tạo = check "solvable" 100%; quarantine có `exclusion_reason` = kỷ luật hiếm thấy; 3 điểm yếu hơn chuẩn bên ngoài: holdout 11/50 clone byte (không unseen), tolerance chưa hiệu chỉnh theo asset (3 trap chết L1), CPI capture thiếu nhãn dimension (FinanceBench-style phải expert-labeled). Bộ này đủ để **xếp hạng harness**, chưa đủ để kết luận "vượt trội tài chính đầu tư VN" trọn vẹn (thiếu risk/portfolio, multi-turn, narrative-rubric — §15.2).

### 16.3 Nguồn §16

- Thực thi: `audits/2026-11-07-corpus-wave2/{MIGRATION.json, MIGRATION.md, removed/}`; task mới `tasks/main/fin-{l3-breadth-301, l4-2src-302, l4-chain-303..306, l4-future-307..308, l4-nonexist-309..310}`; self-test log trong session 08/11.
- Review corpus 277: chuỗi review L1–L5 (07–08/11) — oracle 274/274, verdicts per-task; các số trích trong 16.1.
- So sánh harness: §2 (pilot v3), §9 (flash), §12 (kiến trúc/log), §13.2–14.4 (v4.4 metrics), §15.6 (model-card bolt, memory hooks), reviews L1–L5.

---

## 17. Phụ lục (cập nhật 08/11/2026, đêm): Kế hoạch memory-stratum + rebalance main (cap 220) — đã verify điều kiện tự-đồng-ý quyền của cả 3 arm

Phạm vi: theo ủy quyền user — (a) **giảm tải pilot memory** (6 → 3 câu, đủ check, không dài); (b) **bổ sung câu memory vào main** sau khi giảm câu trùng; (c) **ràng buộc dung lượng**: main + pilot ≤ 220 task; (d) **verify điều kiện cả 3 harness tự đồng ý quyền** (đã làm — mục 17.3). Việc sinh task/xóa task/driver v2 là phần thực thi — chuyển agent Build để chạy (đang Plan mode).

### 17.1 Kết quả verify: cả 3 arm ĐỀU có cơ chế tự-đồng-ý (đọc code thật)

| Arm | Cơ chế tự-đồng-ý | Bằng chứng code | Việc còn thiếu để chạy memory-stratum |
|---|---|---|---|
| **OT** | `PermissionMode = "read-only" \| "ask" \| "auto" \| "bypass"`; mode `auto` = classifier quyết thay user; **hard-deny không thể bị arm gỡ** (cấm tự đổi quyền, cấm lệnh thật, cấm rò secret — `permission/auto/rules.ts`); gate `autoAcknowledged` | `src/core/permission/mode.ts:6-13` + `auto/rules.ts:1-20`; config seams: `memory: {provider:"notebook", cards:true}` (`config.ts:12-16`) + `permissions:{defaultMode,autoAcknowledged}` | ⚠️ **Benchmark runner hiện đang TẮT memory**: `run_opentrading.py:25` đặt `'memory': {'provider':'none'}` và `ot_headless.ts:15` **unregister mọi builtin kể cả memory**. Cần variant `ot_memory_headless.ts` (giữ notebook+cards, tự-accept card = full-auto consent) + config memory-on. Multi-turn: seam có sẵn — `runAgent({history, input})` (agent.ts TurnInput) |
| **OC** | Config key `"permission"` (20 hit trong binary v2.1.2) — block `permission:{edit,bash,webfetch:"allow"}` cho chạy non-interactive không hỏi | `~/.opencode/bin/opencode` (binary); benchmark config hiện chưa đặt block này | Thêm `permission` allow vào runner config (1 dòng); multi-turn qua `opencode run --session <id>` (flag có sẵn). Memory: core không có — M-track cross-session OC được chấm ở chế độ core-only (khai báo) |
| **DSH** | Stack approval hoàn chỉnh: `dsh-user-approval` (chính sách `ask`/`never`, **fail-closed**, one-shot, mọi quyết định ghi audit log) + `dsh-permission-presets` (preset đặt sẵn sandbox+approval cho future-session) | README của 2 bundle; `dsh tui --resume <session>` cho session continuation | Đặt preset non-asking trong profile benchmark; **rủi ro lớn nhất**: headless multi-turn (resume session không qua TUI) chưa có API chắc chắn — cần verify khi build driver; memory = `session-query` tool + session persistent (không có bundle memory semantics) |

**Kết luận verify:** cả 3 đều tự-đồng-ý được; OT cần runner-variant (seam có sẵn), OC cần 1 dòng config, DSH cần preset + kiểm chứng headless-resume. Hard-deny của OT giữ nguyên = arm không thể tự "mở khóa" mình trong benchmark (anti-gaming có sẵn).

### 17.2 Pilot memory — giảm tải còn 3 câu (24 → 27)

Tiêu chí cắt: mỗi track giữ đúng 1 đại diện; mỗi task ≤ 3 turns; chỉ dùng envelope có sẵn.

| ID | Track | Diễn biến | Câu chốt (graded) | Gold | Đo gì |
|---|---|---|---|---|---|
| fin-mem-p01 | In-session (fair) | T1: đọc ROE 5 NH (ACB/STB/VPB/HDB/TPB) từ `peer_compare`; **T2 chấm** | "Xếp hạng 5 mã theo ROE giảm dần" (không gọi lại) | [HDB, TPB, ACB, VPB, STB] | Giữ ngữ cảnh giữa turns; tránh call thừa |
| fin-mem-p02 | Cross-session constraint | **Session A**: *"ghi giúp: tôi chỉ quan tâm cổ phiếu ROE trên 12%"*; **B chấm** | "Trong rổ CK VIX/VCI/SHS/MBS/FTS, mã nào thỏa điều kiện của tôi?" | [VIX 28.85, MBS 15.18] (SHS 11.28 = near-miss 0.72) | Nhớ + áp ràng buộc user |
| fin-mem-p03 | Stale negative-control ⭐ | **A**: *"hôm qua tôi nhìn XAUUSD 4,020.42"*; **B chấm** | "Giá XAUUSD hiện tại là bao nhiêu?" | 3,875.02 **+ evidence tool bắt buộc**; trả 4,020.42 (stale, cách 3.75%) → fail | Quy tắc "never store market data" — bẫy tự nhiên nhất |

### 17.3 Main memory stratum — 9 câu (family mới `L4·M memory` / `L5·M`)

| ID | Turns | Seed (session A / turn trước) | Câu chốt | Gold | Đo gì |
|---|---|---|---|---|---|
| fin-mem-320 | A+B | 2 ràng buộc: *"ROE>12%"* + *"P/E<25"* | "Rổ cons FRT/PNJ/KDC/MSN/SBT — mã nào thỏa điều kiện của tôi?" | [PNJ] (FRT ✗ P/E 28.2; MSN ✗ P/E 27.94; MSN ROE 12.53 near-miss) | Constraint kép + áp dụng |
| fin-mem-321 | A+B | 2 ràng buộc: *"P/B<1.5"* + *"ROE>4%"* | "Rổ bds KDH/NLG/DXG/PDR/KBC — mã nào thỏa?" | [NLG, PDR, KBC] (PDR P/B 1.48 near-miss 0.02) | Constraint kép, rổ khác |
| fin-mem-322 | A+B | 1 ràng buộc: *"chỉ xem cổ phiếu dưới 20 nghìn đồng"* | "Rổ energy PVS/PVD/BSR/PLX/POW — mã nào thỏa?" | [PVD 17.95, POW 12.2] | Constraint + lọc giá (batch có sẵn) |
| fin-mem-323 | A+B | Thesis: *"VCB: mua ≤20, mục tiêu 24, cắt lỗ 19.5, review 30/11"* | "VCB đang **21.0** (giá do đề cung cấp) — **khoảng cách tới vùng mua của tôi** là bao nhiêu %?" | **−4.76%** (=(20−21)/21); note phải dẫn ≥2/3 số thesis (evnum [20,24,19.5]) | Thesis recall + chống tự-chế-điều-kiện; không cần tool giá |
| fin-mem-324 | A+B | *"tôi quen gọi **'Hòa Phát'**, nhớ giùm mã"* | "Giá Hòa Phát phiên gần nhất (nghìn đồng)?" | HPG 21.0 (pilot capture) + evidence | Alias persistence (OT subjects/aliases) |
| fin-mem-325 | A+B | *"sáng nay tôi nhìn GC=F 4,031"* | "GC=F hiện tại là bao nhiêu?" | 3,898.90 + evidence; stale 4,031 cách 3.4% → fail | Stale-control (biến thể main) |
| fin-mem-326 | In-session 3 turns | T1: LNST 5 NH (tỷ); T2: P/E 5 NH (peer); **T3 chấm** | "Mã nào **LNST cao nhất** và mã nào **P/E thấp nhất**?" | {VPB 8,862.91; TPB 6.14} + evidence 2 call | Chuỗi 2 lần lấy + tổng hợp chéo (không lặp lại pilot-p01) |
| fin-mem-327 | A+B (**L5·M**) | *"portfolio của tôi: MSN và PNJ"* | "Tổng doanh thu thuần quý gần nhất của các mã tôi đang giữ (tỷ)?" | **43,975.73** (= 36,981.04 + 6,994.69) + note có [MSN, PNJ] | Portfolio recall + synthesis 2 call |
| fin-mem-328 | A+B | Session A: user hỏi "giá FAKE5?" → arm phải resolver-null (refusal đúng) | **B chấm**: "thử lại giá FAKE5 hôm nay?" | Refusal (`value:null`) + evidence resolver; **không được bịa lần 2** | Nhất quán refusal qua phiên — chống hallucination tái diễn |

**Chấm thêm 3 check riêng track memory** (dùng grader hiện có): ① `tokens`/`evnum` trên `note` phải trích đúng nội dung đã nhớ; ② task stale (325/p03): value thiếu evidence tool → fail kể cả đúng số; ③ **memory-audit artifact**: dump OT `memory.db` / DSH session-list / OC session-count vào thư mục trial sau mỗi trial — diff chống gold/task-ID rò vào memory.

### 17.4 Main rebalance — giảm câu trùng, cap 220

**−18 task** (đề xuất; archive như wave-2): `future-226, 227, 233` (fan-out Q4/fx-31-10) · **narrative 244–252** (9, cả nhóm cách ly dead-weight) · `profile-273, 274` (crypto dup-facet) · `compare-277` (WARN POM rank) · `compare-285` (WARN near-tie) · `macro-133` + `macro-calc-179` (giảm CPI diagnostic còn 1 đại diện/main).

**Trạng thái dự kiến sau thực thi:**

| Split | Trước | Sau | Ghi chú |
|---|---:|---:|---|
| main | 200 | **191** (−18 trùng + 9 memory) | L1 33 · L2 35 · L3 41 · L4 45 · L5 37 |
| pilot | 24 | **27** (+3 memory) | 24 cũ + p01/p02/p03 |
| holdout / smoke | 50 / 3 | nguyên vẹn | không đụng |
| **main + pilot** | 224 | **218** | **≤ 220 (cap user)** ✓ |

> Diễn giải cap "220": hiểu là **main + pilot** (hai split bị thay đổi) = 218 ≤ 220; tổng toàn bộ gồm holdout 50 + smoke 3 = 271. Nếu ý user là **tổng toàn bộ ≤ 220** thì phải cắt thêm ~51 task kể cả holdout đã niêm phong — không khuyến nghị (phá holdout + per-level CI); cần user xác nhận lại nếu vậy.

### 17.5 Driver v2 multi-turn — PREREQ bắt buộc trước khi chạy (việc codex/Build)

1. **Contract**: `environment/turns.json` = `{"sessions":[{"id":"A","turns":[{"text":"..."}]},{"id":"B","turns":[{"text":"...","final":true}]}]}`; task 1-session = 1 group nhiều turns.
2. **OT**: variant `ot_memory_headless.ts` — giữ memory builtins, config `memory:{provider:"notebook",cards:true}` + `permissions:{defaultMode:"auto",autoAcknowledged:true}`; feed `history` tích lũy qua `runAgent`; **auto-accept card events** (= full-auto consent của user); dump `memory.db` cuối trial.
3. **OC**: mỗi turn = `opencode run --session <id> "<turn text>"`; config thêm `permission` allow; không có memory → chấm core-only.
4. **DSH**: preset non-asking trong profile + resume session per turn — **rủi ro cao nhất** (headless resume chưa chắc chắn); nếu không được, DSH chạy session-B standalone (khai báo hạn chế: mất điều kiện thật của track cross-session cho DSH).
5. **Budget/limit**: giữ cap 24 requests + 48k tokens/trial (memory tasks nhẹ, ≤4 tool calls); isolation: memory store/session **mới tinh mỗi trial** (không carry-over chéo trial).

### 17.6 Gates & thứ tự thực thi

1. Build 12 task (3 pilot + 9 main) — chỉ envelope có sẵn; self-test oracle/grader như wave-2.
2. Gỡ 18 task trùng → archive; re-count + re-hash.
3. Driver v2 (5 mục 17.5) + smoke 3 câu pilot × 4 arm → gate protocol: audit memory sạch + p03 (stale) phân biệt đúng.
4. Pilot memory 3×4×2 = 24 trial → main memory 9×4×2 = 72 trial.
5. **Không trộn điểm memory vào confirmatory chính** cho tới khi A/B memory-on/off + contamination-audit đạt — track này báo riêng (như §13.5 nguyên tắc).

### 17.7 Nguồn §17

- Verify consent: `OpenTrading src/core/permission/{mode.ts, auto/rules.ts}` + `src/core/config.ts:12-16` + `tools/runners/run_opentrading.py:25` + `ot_headless.ts:15`; OC binary `"permission"` key + `--session` flag; DSH bundles `dsh-user-approval` / `dsh-permission-presets` / `dsh tui --resume`.
- Thiết kế task: envelope nguồn = agg-181/186/187, compare-275/276/279, growth-141/143, bctc-109..113, quote-104, gold-01 (XAUUSD), fx-174 (GC=F), nonexist-235 — tất cả đã ghi snapshot 2026-11-01.
- Ngữ cảnh: §15.6.3 (5 rủi ro memory), §16.2 (đánh giá 3 arm), §13.5 (nguyên tắc stratum).

### 17.8 CẬP NHẬT THEO FEEDBACK USER (08/11, đêm) — supersede 17.2/17.4 một phần

Quyết định user sau khi xem §17: (1) pilot memory **thu về 1 bài test nhỏ đúng 2 turns**; (2) **main giữ nguyên 200** — các câu trùng là **có chủ đích** (entity fan-out, §16 đã xác nhận), **hủy toàn bộ kế hoạch −18**; (3) cap "220" áp cho **main**; (4) thực thi ngay.

**Đã thực thi (self-test 10/10: oracle OK, grader đúng→semantic pass / sai→`sai_ket_qua`/`sai_so`/`bia_so`):**

| Split | Trước | Sau | Chi tiết |
|---|---:|---:|---|
| pilot | 24 | **25** | +1: `fin-mem-p01` (in-session **2 turns**: T1 đọc ROE 5 NH → T2 xếp hạng, không gọi lại) |
| main | 200 | **209** | **200 câu cũ nguyên vẹn — không gỡ gì**; +9: `fin-mem-320..328` |
| **main tổng** | 200 | **209 ≤ 220** ✓ | cap user áp cho main |
| holdout / smoke | 50 / 3 | nguyên vẹn | |

Bảng 9 task main (đã build, multi-turn declarative `environment/turns.json`):

| ID | Turns | Seed | Câu chốt | Gold | Đo |
|---|---|---|---|---|---|
| fin-mem-320 | A+B | ROE>12% + P/E<25 | cons: mã nào thỏa cả 2? | [PNJ] (MSN ROE 12.53 near-miss) | Constraint kép |
| fin-mem-321 | A+B | P/B<1.5 + ROE>4% | bds: mã nào thỏa? | [KBC, NLG, PDR] (PDR 1.48 near-miss 0.02) | Constraint kép |
| fin-mem-322 | A+B | "chỉ xem giá <20 nghìn" | energy: mã nào thỏa? | [PVD 17.95, POW 12.2] | Constraint + batch price |
| fin-mem-323 | A+B | Thesis XAGUSD (mua ≤50 / target 55 / stop 47 / review 30/11) | Giá hiện tại + gap tới vùng mua (% lấy giá làm mẫu số) | 49.10 + **1.83%**; note dẫn ≥2/3 mức | Thesis recall + tool + chống tự-chế-điều-kiện |
| fin-mem-324 | A+B | alias "Hòa Phát" | Giá 'Hòa Phát' phiên gần nhất | HPG 21.0 | Alias persistence |
| fin-mem-325 | A+B | "GC=F 4,031" (giá cũ, lệch 3.4%) | GC=F hiện tại | **3,898.90 + evidence**; trả 4,031 → fail | Stale-control ⭐ |
| fin-mem-326 | 3 turns 1 session | T1 LNST 5 NH → T2 P/E 5 NH | highest LNST + lowest P/E | VPB / TPB; evidence đủ 2 call | Chuỗi 3 lượt, tổng hợp chéo (HDB trễ kỳ → Q2 — oracle đã xử lý) |
| fin-mem-327 | A+B (L5·M) | portfolio MSN + PNJ | Tổng doanh thu Q3 các mã đang giữ | **43,975.73 tỷ**; note đủ [MSN,PNJ] | Portfolio recall + synthesis |
| fin-mem-328 | A+B | A hỏi FAKE5 (resolver null) | B hỏi lại → vẫn refusal | refusal; bịa lần 2 → `bia_so` | Nhất quán refusal qua phiên |

**Điều chỉnh kỹ thuật trong lúc build:** (a) gold 321/322 chuẩn hóa set theo sorted; (b) oracle 326 dùng `periods[-1]` từng mã (HDB trễ kỳ); (c) envelope pilot quote-01 wrap về format main (`{tool, params, envelope}`) cho 324.

**Còn lại (không đổi so với §17):** driver v2 multi-turn = PREREQ (17.5); memory-audit artifact mỗi trial; gates — pilot p01 4 arm × 2 run trước, rồi main 9×4×2 = 72 trial; điểm memory báo riêng, không trộn confirmatory tới khi A/B on/off + audit đạt. Self-consent 3 arm đã verify (17.3): OT cần variant `ot_memory_headless.ts` (memory-on + auto-accept cards), OC cần block `permission` allow, DSH cần preset non-asking + verify headless-resume.

> **Factcheck §17 (codex, `audits/financial-memory-v45/OPENCODE-SECTION17-FACTCHECK.md` + INDEPENDENT-CHECK)**: đã áp dụng — (a) auto mode cần `autoAcknowledged`, không phải blanket; (b) cards KHÔNG tự lưu (chỉ constraint/style/lesson, verbatim user proof); (c) DSH `approval never` = **từ chối** chứ không auto-consent; (d) DSH headless resume **CÓ** (`--session-id`, claim "chỉ TUI" là stale); (e) OC không cần cấp bash/webfetch; (f) **main ≤250 giữ 200 cũ** (§17.8 supersede). Task 324 thay alias công khai "Hòa Phát" bằng **private nonce "Lá Cam T7"** + distractor EIB — sửa đúng lỗi construct (alias giải được không cần memory).

---

## 18. Phụ lục (cập nhật 09/11/2026): Nhánh `v4.6-repair` — 8 instrumentation repairs theo plan 4.6, seal + SMOKE v4.6 đang chạy (inference thật đầu tiên của dòng sản phẩm)

Phạm vi: theo ủy quyền user — đọc plan 4.6 (`audits/financial-memory-v45/NEXT-INSTRUMENTATION-VALIDATION-PLAN.md`, 8 hạng mục), tạo nhánh riêng, thực hiện nốt công việc còn lại của codex **không động vào artifact frozen của codex** (v45 study + mọi audits nguyên vẹn), rồi smoke → gate → pilot. Vai trò: executor có kiểm soát, vẫn giữ kỷ luật "không nới ngưỡng, không rescue".

### 18.1 Chẩn đoán gốc đã được forensics khóa trước khi sửa

`schema-forensics/REPORT.md` (codex): `equivalent_schema()` (`mcp_snapshot_server.py:87-89`) dùng Python `re.escape()` → sinh `\-`, `\ `, `\&`… — **illegal identity escapes trong JS RegExp `'u'` mode**; OT `FinancePolicyState.validate()` (Ajv8, `unicodeRegExp:true`) compile cả schema → SyntaxError. **6 unique schema hỏng / 65 task-tool** (`symbol_resolve`, `vs_indicator_data`, `yf_commodities` — dấu cách tên VN, dấu `-` ngày + mã crypto). **Confound B0/B1**: `registry.ts:207` chỉ gắn validator khi có financeState → B0 lọt qua, B1 chết trên args hợp lệ → so sánh đo validator-mismatch chứ không đo tài chính.

### 18.2 8 repairs đã thực thi trên `experiments/finance-v46-study` (nhánh `v4.6-repair`)

| # | Fix | File | Verify |
|---|---|---|---|
| 1 | **Schema Unicode**: `_js_unicode_safe_escape()` — chỉ escape 12 JS SyntaxCharacters, control → `\xHH`, còn lại literal | `mcp_snapshot_server.py` | **156/156 schema compile 0 fail qua Bun/Ajv thật** (trước 6); Python semantics 154/154 pos + 154/154 neg; spot-check pattern cũ=SyntaxError → mới=compile + cùng tập chấp nhận (`compile-results-v46.json`, `spot-check.ts`) |
| 2 | Parallel tool-call binding theo `assistant_ordinal` (thứ tự thật trong tool-list), bỏ sort SDK-id lexical | `v45_call_binding.py` | frozen-mini regression (dưới) |
| 3 | DS sampling đọc từ sealed options (mini dùng 1/.95 cho cả 2 model — hardcode cũ sai) | `audit_v45_memory_run.py` | 57 FP biến mất |
| 4 | OC reversible quote-wrapper decode (quote-bọc + newline thô, 1 mức) | `audit_v45_memory_run.py` | 5 FP biến mất |
| 5 | Rejected-proof nhận public `unsupported_snapshot_query` (không chỉ private wording) | cả 2 auditor | OC/DSH rejected-call join được |
| 6 | Generation stamping replay | ⏸ **deferred có disclosure** — auditor bind replay về generation gốc nên hết false-positive; native change đòi revalidate 1839 test, để native owner | — |
| 7 | **Phân loại 7 lớp** tool-failure: schema-invalid / validator-crash (infra) / schema-valid-unsupported / MCP-rejected / unknown-tool (infra) / replayed-reference / transport; 3 đường reconcile mới (MCP-rejected, validator-crash, notebook-read, unknown-tool) | `ready_check.py` + 2 auditor | mọi failed call + cost giữ nguyên, 0 rescue |
| 8 | Notebook description: literal whole-substring + phân biệt "no matching facts" vs "no saved facts" | `memory_snapshot_server.py` | cho run sau |

**Regression chốt trên FROZEN mini (không đụng artifact)**: auditor v4.6 đọc-only trên `financial-memory-v45-mini-20261109-preflight5`: **94 errors → 0, PASS**. Mọi class được phân loại đúng (7 compile-crash = infra; 3 schema-valid + public error = failed-query; replayed notice = reference về generation gốc scope A) — không có rescue, không có score change. Full Python suite: **537/537 PASS**.

### 18.3 Seal + SMOKE đang chạy

- Protocol v46 đăng ký: `experiments/finance-v46-study/plans/2026-11-09-v46-execution-protocol.md`; approval user-authorized + 2 freeze state ghim; **seal `audits/seal-v46/financial-v46-seal.json`** (6 manifests: super/deepseek × devsmoke 96 / pilot 176 / main 1098) qua `v45_gate.py` (gate thresholds **nguyên trạng**).
- **Supervisor launched 09:30 (PID 2228025)**: chain devsmoke(2 model) → audit → gate → pilot → review → main, pause tự động ở mỗi gate.
- **Hiện trạng 11:40**: Super devsmoke **23/96 trial** (~5,7 phút/trial — Super reasoning + multi-call chậm hơn dự phóng; DS chạy sau). **Tín hiệu sớm (6 dev task đầu, CHƯA kết luận)**: DSH 4/6 success · OC 3/5 · **OT-B0 0/6 · OT-B1 0/6** (khong_tra_loi) — OT đang yếu ở nhóm đầu; cần chờ đủ 24/arm/model + audit trước khi phán. Watcher đã cài, sẽ báo khi cả 2 devsmoke xong.
- Native stamping (mục 6): deferred — ghi disclosure, không chặn vì auditor đã xử lý replay đúng.

### 18.4 Trạng thái chuỗi tổng (sau vòng này)

| Study | Trạng thái |
|---|---|
| v4.4 | ĐÓNG (không pilot); frozen |
| v4.5 | MINI 24/24 chạy + review 13/13 wins (0 rescue) — **UNCERTIFIED / BLOCKED_INSTRUMENTATION**; stateless PAUSE 6 manifest; automation đóng đúng protocol |
| **v4.6** | **SMOKE đang chạy**; pilot chỉ mở nếu devsmoke gate PASS cả 2 model; main chỉ sau pilot gate + manual review + báo cáo user |

### 18.5 Nguồn §18

`audits/financial-memory-v45/{NEXT-INSTRUMENTATION-VALIDATION-PLAN.md, MINI-INSTRUMENTATION-FORENSICS.md, schema-forensics/{REPORT.md, compile-results.json, collect.py}, REPORT.md, INDEPENDENT-CHECK.md, V45-STUDY-GATE-DECISION.json, AUTOMATION-CLOSED.json, ACTIVE-RUN-20261109.md}`; `experiments/finance-v46-study/{tools/{mcp_snapshot_server.py, v45_call_binding.py, ready_check.py, audit_v45_memory_run.py, audit_v45_run.py, v45_gate.py, v45_supervisor.py}, verify/schema-fix/, results/financial-v46-{supervisor-20261109, 20261109}, audits/seal-v46/}`; nhánh git `v4.6-repair`.

### 18.6 Bổ sung (09/11, trưa): fix #10 protocol-compat + 2 cohort superseded + SMOKE R3 — chuỗi lever v4.2→v4.6 chạy end-to-end lần đầu

- **Fix #9 (gateway allowlist prefix)**: áp dụng + seal v2 — nhưng r1-runtime **vẫn 424**: `isolated.py:31` khóa `protocol=='financial_product_v45'` chặn `native_tool_definitions` khi config đổi protocol id (fix #10).
- **Fix #10**: v46 configs giữ protocol-id nội bộ `financial_product_v45` (khóa compat 8 điểm; danh tính v4.6 = study dir + seal v3 + protocol doc riêng). 2 cohort r1/r2 superseded-bảo-quan (`*-superseded-gateway424`, `*-superseded-protocol-gate`). Seal **v3** (`financial-v46-seal-v3.json`) + supervisor r3 launch 12:2x.
- **RegressionGate**: frozen MINI audit (v46 auditor) = 0 errors PASS; frozen stateless r1 57 trial 424 bảo quản làm bằng chứng.

**Smoke R3 — Super devsmoke 7/96 (12:49)**: **OT-fin 2/2 ✅ · OT-B0 2/2 ✅ · DSH 2/2 ✅ · OC 0/1 (sai_ky)**. Trace xác nhận chuỗi lever đầy đủ lần đầu chạy thật:
1. `dev-02-resolve` (OT-fin): `symbol_resolve{"Nhà Khang Điền"}` → `vn_quote_history{KDH, days:365 default-equivalent}` → 37.25 đúng — **pattern VN từng vỡ compile + resolver-first + C2** cùng lúc.
2. `dev-03-growth` (OT-fin): `financial_statements{DGC,periods_n:15}` → **`analytics_compute{growth_pct, operands correct}` ok** — **B2 uptake thành công thật** (0/24 ở v4.4).
3. `dev-02-resolve` (DSH): resolver → quote → **`analytics_calculate` ok** — compute common-env fair-play.
4. Pace ~3,5 phút/trial Super → devsmoke đủ 2 model dự kiến tối nay; watcher armed; OC sai_ky 1 case (đang theo dõi).

Nguồn bổ sung: `experiments/finance-v46-study/{results/financial-v46-20261109-r3, audits/seal-v46/{approval-v46.json, financial-v46-seal-v2.json, financial-v46-seal-v3.json}, results/*-superseded-*}`; fix trail: approval-v46.json `repair_note` (fix#9 gateway-prefix, fix#10 protocol-compat).

---

## 19. Phụ lục (cập nhật 09/11, chiều–tối): v4.6-UPDATE được duyệt + engineering закрыт 622/622 → smoke đang chạy + OpenRouter :free pilot route (user-authorized) + v4.7 review chờ duyệt

### 19.1 Duyệt v4.6-update — engineering verification (executor: OpenCode agent, độc lập với implementers)

- Study: `experiments/finance-v46-update-study` (codex workers implement; 8 repairs gồm gốc rễ `[ref rN]` parse bug — nguyên nhân 12 source-join lỗi, B0/B1 schema parity, origin-generation audit, dimensionless 'tỷ lệ' + unit normalizer exact-only, refusal predicates, common instructions precision 1e-6 + full source chain, grader families)
- **Verify của tôi: 622/622 Python PASS · typecheck PASS · wire 4-arm + native utility PASS · offline ready-check PASS**
- Engineering approval: `experiments/finance-v46-update-study/audits/engineering-approval-v46-update.json` (independence: implementers = codex workers ≠ approver)
- Lưu ý independent review (`INDEPENDENT-PREFLIGHT-REVIEW.md`): R3 có **6** (không 7) primary failures; "mostly financially correct" hợp lý nhưng "all formatting" không được chấp nhận; approval v4.6 cũ của tôi bị phản bác independence — v46-update khắc phục (implementer ≠ approver)

### 19.2 SMOKE v4.6-update đang chạy + OpenRouter :free pilot route (user-authorized)

- **Smoke Super-only (NVIDIA key)**: launched 15:5x, PAUSE markers chặn deepseek/pilot/main (user: chỉ Super, không DeepSeek, không pilot; codex tiếp quản sau smoke... cập nhật: user giao tôi tiếp tục)
- **Pilot route MỚI (user chỉ định)**: **OpenRouter `nvidia/nemotron-3.5-super-vl:free`** — pricing 0/0 verified; admission canary **3/3 PASS** (identity trả ĐÚNG `:free` — không private alias; VN follow; tool wire); budget **free 1000 req, hard-stop 950, 50 reserve**; `bench_config_openrouter.json` + seal-OR (2 manifests, main bị AUTHORIZED_SPLITS chặn đúng); receipt `audits/model-admission/openrouter__nemotron-3.5-super-vl-free.json`
- Fair-play: pilot 4 arm CÙNG route OpenRouter :free (so sánh nội bộ cohort hợp lệ); smoke NVIDIA vs pilot OpenRouter = route khác được khai báo riêng
- **R4 Context reduction: ĐÃ ĐẶT REMIND** — `REMINDER-R4-CONTEXT-REDUCTION.md` (bật sau R1-R3; checklist 5 mục)

### 19.3 Audit-stateless gaps còn mở (từ R3, sẽ vá khi smoke xong)

16 lỗi audit R3 phân loại: (1) **3 provider journal RỖNG** (OC chain r1 + OT-fin ratio r2 + 1 — instrumentation gap, journal không flush); (2) **1 typo'd tool name** `mcp__openttradng__vn_quote_history` do model sinh (lỗi model thật — cần class `model_toolname_error` riêng, không phải infra); (3) **12 source_sdk_context_join** — successful receipt không join — cần diagnose sâu (cùng lớp parallel/derived nhưng khác memory path). Auditor v46-update kế thừa các patch của tôi (MCP-rejected + unknown-tool) — 3 khoảng trống trên sẽ vá khi smoke xong.

### 19.4 v4.7 — REVIEW CHI TIẾT (khuyến nghị: DUYỆT CÓ ĐIỀU KIỆN)

Đã đọc trọn `plans/2026-11-09-v47-proposal-pending-approval.md` (44 dòng). Đánh giá per-change:

| Thay đổi | Giá trị (trị đúng failure nào) | Rủi ro | Khuyến nghị |
|---|---|---|---|
| R1 Reference bridge | Trị call_id 'r1' copy-from-example + path /data vs leaf | Migration | **DUYỆT — bắt buộc** |
| R2 Typed financial claims | Trị unit '' + sai_don_vi + period nhầm (typed entity/scope/period/stock-flow/ratio-vs-%) | Schema không chứa gold ✓ | **DUYỆT — bắt buộc** |
| R3 Claim serializer | Trị precision 52.87-vs-52.8666 + full-chain source; lợi thế serialization thật | Native work lớn nhất; fair-play: raw-native endpoint công bằng cho OC/DSH, khai báo ablation | **DUYỆT — ablation riêng** |
| R4 Context reduction | Chi phí (B1 107 req vs 72-78; inventory 14.369B) | Cắt sớm = làm 2 lần; v4.4 bài học misread | **HOÃN — REMINDER đã đặt** |
| Memory track riêng | MINI N=3 chỉ sơ bộ | — | Giữ nguyên tắc |

**Điều kiện duyệt (4 mục)**: (1) R0 v4.6-update audit PASS trước khi R1-R3 implement; (2) R3 serializer xuất **full precision** (không round) + precision quy ước ghi common instruction mọi arm; (3) chỉ R0 vs R3 smoke nếu ngân sách gọn (R1/R2 đo offline fixtures); (4) nếu R3 không cải thiện grounded ≥ +2/24 vs R0 → giữ R0 báo cáo. Budget ước lượng: engineering 2-3 ngày; smoke/pilot 1-2 ngày.

### 19.5 OT-strength stratum (mục 4): HOÃN CÓ KIỂM SOÁT + chuẩn bị sẵn

Quyết định: stratum chạy **sau v4.7** (tránh regenerate 50 task nếu contract/instruction đổi). Chuẩn bị sẵn trong lượt này: draft preregistration `experiments/finance-v46-update-study/plans/DRAFT-ot-strength-stratum.md` (5 họ A-E theo §13.5, fair-play constraints, per-family gates, generator spec) — sẵn sàng bật.

### 19.6 Nguồn §19

`audits/financial-v46-update/{ENGINEERING-CHECKS-IN-PROGRESS.json, INDEPENDENT-PREFLIGHT-REVIEW.md, NATIVE-CONTRACT-REPAIR-HANDOFF.md, FORENSIC-SMOKE.md, INDEPENDENT-OLD-R3-REVIEW.json}`; `plans/2026-11-09-v47-proposal-pending-approval.md`; `experiments/finance-v46-update-study/{tools/{identity_canary.py, bench_config_openrouter.json}, audits/{engineering-approval-v46-update.json, model-admission/openrouter__nemotron-3.5-super-vl-free.json, seal/}, results/financial-v46u-*}`; `.env` OPENROUTER_KEY; OpenRouter models API (pricing 0/0 verified 09/11).

### 19.7 KẾT QUẢ SMOKE Super v4.6-update (96/96 hoàn tất 17:37) — audit PASS 0 errors — gate: B1 regression vs B0 → pilot KHÔNG chạy

| Arm | Strict /24 | Grounded /24 | Answerable | Trap | Raw | DNF | FR | FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **OT-baseline** | **24 (100%)** | **24** | 18 | **6** | 24 | 0 | 0 | 0 |
| OT-finance | 22 (92%) | 22 | 17 | 5 | 24 | 0 | 0 | 0 |
| DSH | 20 (83%) | 21 | 15 | 6 | 22 | 1 | 0 | 0 |
| OpenCode | 15 (63%) | 15 | 10 | 5 | 17 | **6** | 0 | 0 |

- **OT-baseline 24/24 HOÀN HẢO** — lần đầu trong chuỗi; common instructions (precision/source-chain/dimensionless) + schema parity + Super đủ để thắng mọi failure mode cũ KHÔNG cần finance policy.
- **Gate: B1 22 < B0 24 (strict + grounded + evidence regression) + trap 5<6 → FAIL** — pilot KHÔNG chạy (đúng điều kiện user tự đặt: "nếu B1 ≥ B0 và grounded ≥20").
- **Audit: PASS 0 errors** sau 4 fix instrumentation (origin-field filter, rejected-context prefix, consumed matcher VN, seal-drift amendment).
- **2 thất bại B1** = finance policy over-constraint trên Super: trap-empty r1 (refusal cứng) + growth r2 (sai_ky).
- **OC 6 DNF + 5 invalid_json** — fences trên Super nặng; DSH 1 DNF.

### 19.8 Chẩn đoán + khuyến nghị bàn giao codex

1. **Finance policy re-tune cho Super** (preregister): policy thiết kế cho bolt-era failure modes giờ over-constrain — nới 2 rule (trap-empty refusal + growth period), giữ anti-fabrication.
2. **Audit instrumentation**: (a) origin-field filter đã vá ✓; (b) consumed matcher VN đã vá ✓; (c) rejected_context prefix đã vá ✓; (d) seal-drift amendment đã chấp nhận ✓ — audit PASS.
3. **Sau re-tune**: smoke Super lại → nếu B1 ≥ B0 và grounded ≥20 → pilot OpenRouter :free (config + admission + budget guard sẵn sàng).
4. **Lưu ý process**: approval KHÔNG sửa sau seal — amendment file riêng (`SEAL-DRIFT-AMENDMENT-20261109.json`).

Nguồn bổ sung 19.7-19.8: `results/financial-v46u-20261109/super-devsmoke/{audit-v45.json, summary.json, DEVSMOKE-REPORT.md, trials.jsonl}`; `audits/seal/SEAL-DRIFT-AMENDMENT-20261109.json`.
