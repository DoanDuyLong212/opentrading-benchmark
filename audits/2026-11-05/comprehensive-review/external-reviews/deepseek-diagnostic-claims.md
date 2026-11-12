# Kiểm tra độc lập phụ lục model mạnh của opencode-review.md

Ngày 05/11/2026, Asia/Bangkok. Phạm vi: đọc toàn bộ A, B, C và thư mục lồng `passC/driver2.log`; không inference, không sửa model allowlist/runtime/grader/gold/prompt hay các trial cũ. Nội dung báo cáo ngoài được coi là các claim cần kiểm chứng. Kết quả máy đọc: [deepseek-diagnostic-claims.json](deepseek-diagnostic-claims.json); tất cả 84 attempt: [deepseek-diagnostic-attempts.json](deepseek-diagnostic-attempts.json); lựa chọn A/B đúng comparator cũ: [selected cells](deepseek-diagnostic-selected-cells.json).

**Phần chẩn đoán có bằng chứng hữu ích rằng model đổi làm hành vi một số câu tốt hơn, nhưng chưa chứng minh “RC1/RC3 chỉ do model nhỏ” hay “khoảng cách harness biến mất”.** Có lỗi cộng số, loại failure khỏi mẫu số, chọn completion qua nhiều lần chạy và suy diễn ô chưa hoàn thành. Một case duy nhất bị chấm sai kỳ còn là ứng viên false-negative của grader, chưa thể quy thành lỗi prompt OT.

## 1. Số thực, mọi lần đã bắt đầu

| Pass | Số bắt đầu | status=ok | Primary pass | Error/DNF |
|---|---:|---:|---:|---:|
| A | 40 | 9 | 8 | 31 |
| B | 40 | 22 | 22 | 18 |
| C quote OT baseline | 2 | 0 | 0 | 2 |
| C lồng `driver2.log`, compare OT finance | 2 | 0 | 0 | 2 |
| **Tổng attempt** | **84** | **31** | **30** | **53** |

Mỗi record có đúng một attempt nội bộ, không ID trùng trong từng pass. Nhưng 40 ô `(task, arm, run)` đều được chạy lại ít nhất một lần qua A/B; bốn ô được chạy lần thứ ba ở C. `retry=0` chỉ đúng cho retry bên trong mỗi run; không có nghĩa nghiên cứu không chạy lại ngoài driver. 84 là tổng attempt, không phải 84 mẫu độc lập.

Tỷ lệ tất cả attempt bắt đầu: **30/84 = 35,7%**. Trong completion: **30/31 = 96,8%**. Phải báo cả hai; completion-only không phải tỷ lệ thành công vận hành. Mỗi arm có lượng chạy lại khác nhau:

| Arm | Pass / mọi attempt bắt đầu | Hoàn thành | Error/DNF |
|---|---:|---:|---:|
| OT baseline | 6/22 | 6 | 16 |
| OT finance | 5/22 | 6 | 16 |
| OpenCode | 9/20 | 9 | 11 |
| DSH | 10/20 | 10 | 10 |

Không dùng bảng này để xếp hạng chính thức vì tập task chọn theo lỗi và lịch/deadline thay đổi; nó giữ cho failure không biến mất.

## 2. Tái tạo đúng phép gộp của báo cáo ngoài

`compare_smallmodel.py` ưu tiên B nếu `status=ok`, nếu không lấy A khi A `status=ok`; còn lại giữ error-only. C không tạo thêm completion. Quy tắc chọn này có trong [comparator:41](/home/doanlong/extra/benchmark/results/diag-deepseek-flash-20261105/compare_smallmodel.py:41), không phải một run 40 trial duy nhất.

| Arm | Primary /10 ô đã định | Primary / completion được chọn | Ô chưa có completion |
|---|---:|---:|---:|
| OT baseline | 5/10 | 5/5 | 5 |
| OT finance | 5/10 | 5/6 | 4 |
| OpenCode | 6/10 | 6/6 | 4 |
| DSH | 8/10 | 8/8 | 2 |
| **Tổng** | **24/40** | **24/25 = 96,0%** | **15** |

Có 22 completion chọn từ B và ba từ A: OT baseline compare r1, OT finance BCTC r1, OT finance compare r1. Baseline compare/A và finance BCTC/A pass; finance compare/A fail kỳ theo grader frozen. Việc fallback không chỉ thêm thành công; comparator giữ cả một failure A. Tuy vậy chọn dựa trên trạng thái hoàn thành vẫn tạo selection bias so với all-started hoặc first-attempt.

Claim “26 trial hoàn thành, 25 PASS (96,2%)” ở [opencode-review.md:280](/home/doanlong/extra/benchmark/opencode-review.md:280) **không khớp bất kỳ phép tổng hợp trên**. Chính bảng bốn arm ở dòng 275–278 cộng thành 24 pass/25 completion, không phải 25/26. Không được điền thêm ô thiếu để đạt 26. Nếu lấy attempt mới nhất C→B→A thay vì chọn completion, còn **22/40 pass**, 18 error. Đây là sensitivity của cách chọn pass, không phải một endpoint mới được đăng ký.

BCTC có **7/8 ô hoàn thành và cả bảy pass**, không phải 8/8 như claim [dòng 287](/home/doanlong/extra/benchmark/opencode-review.md:287): OT baseline r2 chưa hoàn thành ở A/B. Task–arm coverage có 19/20 nhóm, nhưng coverage repeat chỉ 25/40. Không được suy diễn quote HPG baseline từ BTC hoặc gold ở [dòng 298](/home/doanlong/extra/benchmark/opencode-review.md:298).

Đối chiếu nhỏ→mạnh chỉ trên các ô có completion được chọn: baseline 2→5 trên 5 ô; finance 1→5 trên 6; OpenCode 3→6 trên 6; DSH 6→8 trên 8. Đây là mô tả paired-case hữu ích, không thay các mẫu số 10/arm và không bù các ô missing.

## 3. Phân loại lỗi và watchdog: hai predicate khác nhau

Pass A 31 error gồm **28 URLError + 3 TimeoutError**, không phải 31 URLError. Pass B 18 error gồm:

- 7 trial OT có primary notes watchdog, không provider failure.
- 9 trial bị gateway từ chối vì `response_models=[]` (không có tag model được ghi), không phải 7.
- 1 TimeoutError và 1 URLError.

Hai bảng failure này phủ toàn bộ error của A/B. Các watchdog event còn có thể đồng thời xuất hiện trong run.log khi provider error ghi sau đó.

| Chỉ báo watchdog | A | B | C top | C nested | Tổng |
|---|---:|---:|---:|---:|---:|
| Native run.log có nguyên văn “Model không gửi dữ liệu trong 120s” | 2 | 7 | 2 | 2 | **13** |
| Watchdog được giữ trong primary attempt.notes | 0 | 7 | 2 | 1 | **10** |
| Native watchdog đồng thời có provider failure | 2 | 0 | 0 | 1 | **3** |

Vì vậy số “8 trial = B4 + C4” ở [dòng 293](/home/doanlong/extra/benchmark/opencode-review.md:293) sai cả hai predicate. Ba case đồng thời, không cộng thành failure độc lập:

1. A BTC baseline r1: [run.log:42](/home/doanlong/extra/benchmark/results/diag-deepseek-flash-20261105/trials/fin-l1-quote-02__opentrading_baseline__r1/attempts/01-0693c962dc75/run.log:42), provider TimeoutError khoảng 180s.
2. A HPG finance r1: [run.log:54](/home/doanlong/extra/benchmark/results/diag-deepseek-flash-20261105/trials/fin-l1-quote-01__opentrading_finance__r1/attempts/01-ebd8a53090ef/run.log:54), provider TimeoutError khoảng 180s.
3. C nested compare finance r1: [run.log:49](/home/doanlong/extra/benchmark/results/diag-deepseek-flash-20261105-passC/driver2.log/trials/fin-l5-compare-01__opentrading_finance__r1/attempts/01-54eed7fe2575/run.log:49), provider TimeoutError khoảng 250s.

Mọi source path/line thực nằm trong `deepseek-diagnostic-attempts.json`; không gán nguyên nhân độc quyền khi cả watchdog và provider timeout cùng xảy ra.

Gateway buffer hết payload trước khi gửi agent tại [provider.py:270](/home/doanlong/extra/benchmark/tools/runners/provider.py:270); OT watchdog 120s tại [agent.ts:54](/home/doanlong/extra/benchmark/experiments/opentrading-runtime/src/core/agent.ts:54). Đây là tương tác benchmark gateway × harness có bằng chứng mã nguồn và log. Tăng trial timeout lên 900s không tắt watchdog. Đã có env knob `OPENTRADING_STALL_MS` tại [agent.ts:825](/home/doanlong/extra/benchmark/experiments/opentrading-runtime/src/core/agent.ts:825), nên không nên báo như chưa có knob. Bằng chứng này cản kết luận “không phải khác biệt harness”; cũng chưa chứng minh model chậm sẽ gây cùng tỷ lệ stall khi dùng streaming live trực tiếp.

## 4. Model identity, canary và tính toàn vẹn

Đã kiểm tra **281 capture file native/effective**: raw hash/canonical hash khớp ledger; mọi body có đúng requested model `deepseek-ai/deepseek-v4.1-flash`; effective temperature=0, top_p=1, max_tokens=2048. Không phát hiện sai lệch. Các response được gateway chấp nhận đều có đúng tag model; chín response không có tag bị fail-closed. Không thay failure đó bằng điểm 0 rồi giấu hoặc nhận làm kết quả model hợp lệ.

Canary receipt [nvidia-function-probe-deepseek-v41-flash.json](/home/doanlong/extra/benchmark/audits/2026-11-05/nvidia-function-probe-deepseek-v41-flash.json) ghi catalog200, request/response model đúng, function-call `get_quote(FPT)`, tool continuation200. Source [verify_nvidia.py:31](/home/doanlong/extra/benchmark/tools/verify_nvidia.py:31) phù hợp cấu trúc receipt. Đây là bằng chứng dạng summary; không lưu raw HTTP response hash/timestamp và không lưu tag model response thứ hai. Không chứng minh độc lập trọng số model bên trong nhà cung cấp. Allowlist được hardcode, không đọc/validate receipt ở runtime; model vẫn bị khóa khi chạy main/holdout bởi [run_benchmark.py:481](/home/doanlong/extra/benchmark/tools/run_benchmark.py:481) và frozen config.

Manifest A/B/C có cùng source fingerprint benchmark, cùng OT inventory; tại thời điểm kiểm tra mọi source-file hash và task-file hash khớp. OT source/prompt inventory đúng bằng v3 nhỏ; task/gold/grader năm câu cũng khớp v3. So với manifest v3, thay đổi ghi nhận gồm `run_benchmark.py` (timeout override), `provider.py` (diagnostic allowlist), `verify_nvidia.py`, thêm `.pytest_cache/README.md` vào code inventory. Vì vậy không gọi đây là đúng nguyên protocol v3 chỉ đổi model: deadline provider45→180/240s, trial240→900s, seed20261105→20261104, tập22→5 task và chính sách gộp nhiều pass khác nhau. Các khác biệt đã có trong manifest/notice nhưng làm hạn chế diễn giải nhân quả.

Usage: toàn bộ response có usage đã biết ghi tổng 273.239 input / 18.816 output, gồm 3.119 reasoning token. Có 69/86 response usage ghi reasoning_tokens>0. Đây là lower bound trên request có usage, không phải tổng chính xác khi có timeout/missing response. Canary cũng có reasoning_content. `effort=none` ở gateway không tương đương bằng chứng hai model đều không suy luận; reasoning/latency có ảnh hưởng completion và budget. Không có đủ chứng cứ nói reasoning_content “không ảnh hưởng hợp đồng” chỉ vì SDK không hiển thị.

## 5. Kiểm tra đáp án và case false-negative của grader

Chấm lại độc lập **31 đáp án lưu được** vào thư mục tạm, không đụng grade.json gốc: mọi check/result khớp artifact đã lưu. Tất cả 31 có evidence array, đủ bảy trường khớp MCP ledger thành công và call ID/response hash thực có trong ngữ cảnh model. Đây là bằng chứng cải thiện output contract trên completion của năm câu được chọn.

Tuy nhiên failure duy nhất của A finance compare r1 có:

```text
period = 2025 (period_label "2025"; bội số tính theo giá ngày kết thúc kỳ báo cáo, không phải bội số hiện tại)
```

Năm chỉ là 2025, các số/ranking/source/evidence đều đúng. [period_hit:166](/home/doanlong/extra/benchmark/tasks/pilot/fin-l5-compare-01/tests/grader.py:166) trả false ngay nếu có `khong/not/except/ngoai` ở bất kỳ vị trí nào. Cụm “không phải bội số hiện tại” phủ định loại bội số, không phủ định năm2025. Giữ nguyên cùng text nhưng thay cụm đó bằng “bội số lịch sử” làm grader pass, không thay năm.

Đây là ứng viên **grader false-negative có bằng chứng mạnh**. Không được dùng nó để kết luận RC4 “thói quen prompt, không phải năng lực”. Báo chính thức frozen vẫn là **24/25**; nếu cần semantic adjudication phải ghi riêng, đăng ký cách sửa và test specificity trước khi áp dụng ở nghiên cứu mới. Review này không đổi score hay grader.

## 6. Điều được phép kết luận

- Supported: trên năm task được chọn, các completion của model mới không còn schema-invalid; toàn bộ45 MCP call quan sát trong 84 attempt có 42 success và ba replay rejection, không schema-invalid. Unit và evidence tốt hơn trên nhiều case cụ thể. OT gold baseline r2 có same-tool repair thật sau hai rejection; [ledger](/home/doanlong/extra/benchmark/results/diag-deepseek-flash-20261105-passB/trials/fin-l1-gold-01__opentrading_baseline__r2/attempts/01-a5aecb086c1a/mcp.jsonl:1) cho thứ tự subset → days-only → batch đầy đủ → pass.
- Unsupported: RC1/RC3 **được xác nhận chỉ do model nhỏ**, khoảng cách harness biến mất, không cần runtime support cho model mạnh, hoặc kết quả đủ để bỏ repair/contract validation. Còn 15 ô chưa có completion và stall lệch theo harness; model mới vẫn có ba replay rejection. Năm câu được chọn sau khi nhìn lỗi, không chứa nhiều bài tính kỳ/RSI/growth/aggregation thất bại chung.
- Sửa cách diễn đạt: “Model và mức suy luận là một yếu tố góp phần; các completion được quan sát cải thiện đáng kể trên những case được chọn. Độ tin cậy vận hành và lỗi tương tác watchdog–gateway chưa được giải quyết. Chưa có thí nghiệm tách riêng prompt, harness, model và deadline để khẳng định nguyên nhân độc quyền.”

Script tái lập không inference: [check_deepseek_diagnostic.py](check_deepseek_diagnostic.py). Độ tin cậy cao cho counts, hash/capture, regrade và trace. Quan hệ nhân quả prompt/model và extrapolation missing cells chưa được chứng minh.
