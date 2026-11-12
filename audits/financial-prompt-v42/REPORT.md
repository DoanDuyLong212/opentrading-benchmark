# Báo cáo đóng nghiên cứu tài chính v4.2

Ngày 06/11/2026, Asia/Bangkok. **Smoke18 hoàn tất; certificate thất bại tại live parity; pilot176 NOT STARTED. Không promote/install và chưa chứng minh OpenTrading vượt trội.** Đây là kết quả của study đã đóng băng, không phải dự báo trong OpenCode review §11.

## 1. Phạm vi và trạng thái quyết định

Study riêng `experiments/finance-v42-study` dùng OT0.3.1 native base, common finite-query C2, per-intent repair candidate và public success/refusal contract. Smoke có 3 task × 2 repeat × 3 arm =18 trial; không có B0 concurrent. Model duy nhất là NVIDIA `nvidia/nvidia/nemotron-3.5-bolt-e4b`, effort none, temperature0/top_p1; seed20261105; timeout240s/provider45s; request24, output2048/request, policy48000tokens, retry0, pause2s; native stall300s.

[Đăng ký v4.2](/home/doanlong/extra/benchmark/plans/2026-11-06-v42-replay-repair-contract-study.md) và source/grader/protocol cũ được giữ nguyên. [Đối chiếu review §11](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/OPENCODE-UPDATE-FACTCHECK.md) phân biệt các dự báo parity/16–20 trên44, compute-tools và trần model với kết quả đo. Báo cáo này không sửa tài liệu review của người dùng.

Supervisor dừng ở certificate: regression354 pass, sau đó live parity fail. Numeric retrieval canary cũng không được mọi arm đáp ứng: chỉ OT có successful numeric retrieval; OC/DSH chỉ có trap đúng theo semantics. Không có certificate pass để mở pilot. Pilot176 là **NOT STARTED**, không ghi 0/44 ở bất kỳ condition nào. Promotion guard B1>B0 là **NOT EVALUABLE**, vì thiếu B0 concurrent và pilot chưa chạy.

## 2. Kết quả smoke đã kiểm độc lập

| Endpoint | OpenTrading | OpenCode | DSH |
|---|---:|---:|---:|
| Primary strict / started | 2/6 | 0/6 | 2/6 |
| Frozen-v4.1 / frozen-v3 primary | 2/6 / 2/6 | 2/6 / 2/6 | 2/6 / 2/6 |
| HPG numeric /2 | 2/2 | 0/2 | 0/2 |
| Trap primary /2 | 0/2 | 0/2 | 2/2 |
| Bank aggregate primary /2 | 0/2 | 0/2 | 0/2 |
| DNF / started | 2/6 | 0/6 | 0/6 |
| False refusal / answerable-started | 0/4 | 4/4 | 4/4 |
| FP / unanswerable-started | 0/2 | 0/2 | 0/2 |
| Raw public contract valid | 4/6 | 2/6 | 4/6 |
| Required retrieval complete | 2/6 | 2/6 | 2/6 |

Nguồn: [kiểm độc lập](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/INDEPENDENT-CHECK.md), [fresh grades và thống kê](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/independent-evidence.json), [run summary](/home/doanlong/extra/benchmark/experiments/finance-v42-study/results/financial-v42-smoke-20261106/summary.json).

OT false-refusal0/4 gồm hai answerable trial DNF và chỉ hai answerable completion đúng; không thể gọi đây là thành công trên bốn câu. Hai trap OT không gọi resolver, evidence rỗng và chỉ yêu cầu xác định mã trước nên không đạt honest-refusal endpoint. FP0/2 không làm những refusal không có bằng chứng này thành đúng.

Hai trap OpenCode có resolver thật và refusal đúng nghĩa, nhưng bọc JSON trong Markdown fences. Vì vậy frozen graders chấm2/6, còn strict raw one-object contract chấm0/6. Đây là format penalty đã đăng ký, không phải hai lỗi tài chính hay fabricated evidence. DSH aggregate cũng fenced và dùng all-null `values`; chúng vốn đã fail retrieval/numeric. Extracted-answer schema valid không đồng nghĩa raw final contract valid.

## 3. Bằng chứng cơ chế: acquisition và contract control

OT chỉ phát sinh2 tool call, đều HPG thành công; aggregate và trap không gọi tool ở cả hai repeat. OC/DSH mỗi arm14 call, gồm2 resolver thành công và12 `unsupported_snapshot_query`. Tổng24 query bị từ chối là ngoài finite-snapshot support; không phải production schema errors và không chứng minh dữ liệu tài chính không tồn tại. Sau query thất bại, chưa quan sát sửa query thành công.

Trong OT aggregate, initial turn không tạo call nên không có failed intent. Output correction chỉ cho `toolChoice = correctionTools.length ? "auto" : "none"`; actual effective request thứ hai là `tool_choice:none` ở cả hai repeat. Do đó output repair không thể thực hiện acquisition còn thiếu. Model lặp all-null `values`, không dùng scalar refusal branch; cuối cùng fatal `Machine-response contract failed after bounded correction: Non-null answer requires actual successful tool evidence.` Final rỗng/status error được giữ DNF. Trap null/refusal hợp public shape có thể kết thúc trước resolver. Đây là seam acquisition/contract đã quan sát; smoke chưa exercise native five-failed-bank-intent recovery.

C2 machine constraints tồn tại; không có bằng chứng schema bị mất/corrupt. Actual OC HPG description vẫn có production prose về days mặc định365/projection rồi mới đến frozen-replay restriction symbol-only. Khả năng cue cạnh tranh là giả thuyết cải tiến interface, chưa là kết luận nhân quả. Không được tự strip args hay đổi matcher để cứu output. OT system prompt giống nhau ở ba task không tự chứng minh conflict trong prompt.

Taxonomy `sai_don_vi` ở HPG OC/DSH là check unit:null thất bại sau retrieval rejection; `sai_so` ở aggregate phản ánh không có số. Chúng không chứng minh model thử đổi đơn vị hoặc tính toán sai. Failure stage phù hợp là `required_retrieval_incomplete`. Chưa có run aggregate đủ dữ liệu để kiểm định trần số học. Chi tiết actual requests/state và kiểm tay tại [TRACE-DIAGNOSIS](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/TRACE-DIAGNOSIS.md).

## 4. Kiểm tài chính, provenance và accounting

Hai HPG OT trả21/21.0 nghìn đồng, ngày30/10/2026; payload thực tế có `last=21`, `last_t=2026-10-30`, đơn vị nghìn đồng/cổ phiếu. Value/unit đúng và actual receipt khớp. Gold quote không có expected period nên date correctness ở đây là kiểm tay, không phải coverage tự động của period grader. Kiểm tay5bank cùng ngày2026-10-30: VCB56.3+BID33.4+CTG30.3+TCB21.6+MBB19.3=160.9; trung bình160.9/5=32.18nghìn đồng, khớp gold. Không model nào lấy đủ5payload rồi thực hiện phép tính này; mọi bank failure đều trước số học.

Sáu nonempty evidence claims (OT2quote, OC2trap, DSH2trap) đều nối đủ7field tới đúng một successful ledger record và có trong model-visible context: zero mismatched claims, zero observed fabricated receipts, zero accepted fabricated evidence. Empty evidence có thể khiến câu trả lời fail nhưng không được đếm là fabricated receipt. [Receipt kiểm tay](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/independent-manual-receipts.json) và [kiểm độc lập](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/INDEPENDENT-CHECK.md) ghi đầy đủ reconciliation.

| Accounting | OT | OC | DSH | Tổng |
|---|---:|---:|---:|---:|
| Provider request / usage complete | 10/10 | 12/12 | 12/12 | 34/34 |
| Native/effective captures | 20 | 24 | 24 | 68 |
| Generated / MCP calls | 2/2 | 14/14 | 14/14 | 30/30 |
| Successful / rejected MCP | 2/0 | 2/12 | 2/12 | 6/24 |
| Input tokens | 30,663 | 28,744 | 23,047 | 82,454 |
| Output tokens | 1,637 | 1,646 | 1,906 | 5,189 |

Tất cả34 upstream HTTP200; usage input/output đủ, không đổi missing thành0. Reasoning usage không có thì giữ null/absent, cost không có nguồn tính thì N/A. Zero call-ID duplicates và zero local-rejection remainder. Prepared auditor exit0, errors=[]; model/sampling/caps, capture hashes/binding, condition/prompt/clock và replay integrity đều qua kiểm tra. Audit pass khác với product gate fail.

## 5. Preflight, live scope và bảo toàn

Native final suite **1,092 pass /2 skip /0 fail**, typecheck pass; final benchmark **354 pass**. Failed logs trước đó được giữ. [Root final gate](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/root-final-gate.json) xác nhận final source343files không drift và log hashes đúng. Receipt này là gate trước inference; trường `no_inference_run_directories:true` mô tả thời điểm tạo, không mô tả trạng thái sau smoke.

Full17 C2 wire là preflight capability coverage. Full17 tổng hợp bị OT policy48k chặn trước upstream; largest eligible task catalog hoàn tất stub ở bốn condition. **Mọi34 live request trong smoke chỉ có task-specific1tool catalog**. Không suy live full17 compliance hoặc chuỗi nhiều bước luôn nằm dưới budget từ preflight này.

[Completed resume](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/smoke-resume-check.json) exit0, zero new model calls/captures/duplicates,2,220 manifest/trial artifacts byte-identical, không thêm file. Summary timestamp được regenerate và được loại khỏi byte-preservation scope có chủ đích.

[Post-run preservation](/home/doanlong/extra/benchmark/audits/financial-prompt-v42/post-run-preservation.json) PASS: freeze hash `eb1471507c9f314d2ada983f40f183fab7839ec85ddd2c91e73776e19dddbd69`; original production HEAD `b6e354e76894887e31c33b1f13b44eadc02fad7e`;978original OT files,75tools,1,698tasks và2,216v4.1result files không đổi, cùng archived scopes được liệt kê. Đây là inherited Nov6 stored-path inventory; không khẳng định một start inventory mới hoặc quyền sở hữu các file người dùng mới không liên quan.

## 6. Giới hạn và hướng tiếp theo

Chỉ3task clusters,2repeat/task, trên development smoke và một model nhỏ. Task-cluster bootstrap CI95 là exploratory: OT−DSH0 điểm phần trăm, CI[-100,+100]; OT−OC+33.3điểm, CI[0,+100] (đảo dấu từ comparison OC−OT đã lưu). Payload-family sensitivity tương ứng cũng chỉ3clusters; không phải bằng chứng superiority. Stable McNemar không available vì đòi3scheduled repeats. Không có B0 concurrent để tách candidate package, còn v4.1→v4.2 chứa common C2/grader changes.

Ưu tiên kế tiếp là generic acquisition/action obligation trước final, refusal branch đồng nhất nhưng answerable null vẫn fail, và finite-support-first cues dùng chung mọi arm. Compute tools/normalize units chỉ xem xét sau retrieval coverage, với identity và contract riêng. Không đi thẳng từ những failure chưa lấy đủ dữ liệu tới kết luận phải tăng model hoặc chuyển toàn bộ tính toán vào endpoint.

[Kế hoạch v4.3 riêng](/home/doanlong/extra/benchmark/plans/2026-11-06-v43-evidence-acquisition-study.md) đăng ký giả thuyết, deterministic provider-stub probes, independent cases, actual-wire checks và gate trước một NVIDIA smoke nhỏ sau review. Kế hoạch không tự cấp quyền launch, main/holdout, model mạnh hoặc cài production; không nới certificate v4.2.

**Quyết định cuối: đóng v4.2 ở smoke thất bại gate; không promote/install, không gọi OT vượt trội; chỉ chuyển sang review kế hoạch nghiên cứu riêng.**
