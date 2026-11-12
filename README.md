# Benchmark harness tài chính Việt Nam — v2

Đối chiếu OpenTrading, OpenCode và DeepSeek Harness (DSH) trên cùng model/provider,
ngân sách, MCP snapshot và hợp đồng đầu ra. Benchmark đo **hỏi đáp tài chính có căn cứ
trong snapshot**, không chứng nhận độ chính xác của báo cáo tài chính gốc hay hiệu quả
đầu tư thực tế. Xem [khung đăng ký v2](PRE-REGISTER.md) và [audit lịch sử 04/11](audits/2026-11-04/REVIEW.md).

Bộ đề gồm **200 main, 50 holdout, 24 pilot và 3 smoke**, từ L1 trích xuất đến L5 nhiều
phần. Không dùng kết quả smoke/pilot hoặc các lần chạy cũ để tuyên bố harness thắng.
Sau khi cách ly các câu CPI chưa xác định rõ chiều của chỉ tiêu và rubric narrative
chưa kiểm tra đủ dữ kiện được hỏi, mặc định còn **178 main, 43 holdout, 22 pilot và
3 smoke** đủ điều kiện chạy; lần lượt có 22, 7, 2 và 0 câu chỉ dành cho chẩn đoán.
Các kết quả trước v2 dùng grader/parity/telemetry cũ chỉ có giá trị chẩn đoán.

Trạng thái mới ngày 05/11/2026: **250 regression tests và 4/4 offline checks đạt**;
smoke v3 hoàn tất **18/18 trial**, primary grounded đúng 10/18. Pilot mới hoàn tất
**176/176 trial**: OT finance 12/44, OT baseline 12/44, OpenCode 14/44, DSH 18/44.
Finance giảm false refusal 17→15 nhưng chưa tăng primary/semantic; không chứng minh
thắng hai đối chứng. Sau review chỉ cài runtime fixes vào OpenTrading gốc, giữ prompt
baseline mặc định. Candidate finance vẫn là thử nghiệm. Certificate mới và resume
smoke/pilot đạt, không thêm request/trial. Xem [báo cáo v3 đầy đủ](audits/financial-prompt-v3/REPORT.md)
và [xác minh v2 lịch sử](audits/contract-v2/NVIDIA-VERIFICATION.md).

**Lưu ý alias:** bản thí nghiệm v3 đã frozen vẫn chọn finance cho `opentrading`
(cả `--arms all`). Để chạy so sánh prompt default thực tế đang giữ lại, ghi rõ
`--arms opentrading_baseline,opencode,dsh` và tạo manifest/certificate mới theo gate
tương ứng. Alias frozen tái lập thí nghiệm không phải prompt default đã triển khai.

## Hợp đồng đánh giá

| Điều kiện | Cách thực thi |
|---|---|
| Dữ liệu | Replay offline; schema tool đóng băng, định danh sai hoặc request không ghi nhận bị từ chối. Tool công bố các request có thể replay. |
| Tool và state | Profile/config/session riêng từng attempt; không user skills, external plugins, memory hoặc web trong track kiểm soát. Runtime inventory lưu tool schema thực gửi provider. Native system prompt của harness được giữ. |
| Model/effort | Chỉ route NVIDIA đã triển khai, `effort=none`. Default hiện tại là model nhỏ phục vụ kiểm tra. Go/DeepSeek medium là kế hoạch tương lai, bị chặn cho đến khi adapter được xác minh. |
| Output | Cả ba arm trả JSON cuối cùng; driver chuẩn hóa cùng cách. Không cứu đáp án từ file hoặc write-tool input. Nhiều JSON đáp án mâu thuẫn bị từ chối. |
| Ngân sách | Giới hạn toàn trial gồm mọi attempt và backoff; cap request, output/request và tổng token. Retry chỉ lỗi provider tạm thời có bằng chứng, không retry mọi runner error. |
| Evidence | `evidence:[{tool,source,as_of,call_id,payload_sha256,matched_entry_id,response_sha256}]`. Grader đối chiếu provenance đã đóng băng; driver nối từng evidence với lời gọi **thành công thật** trong ledger của attempt đó, đúng entry và đúng response. |
| Lịch và resume | Task order seeded; arm orders xoay qua các hoán vị cân bằng. Manifest giữ nguyên lịch, code, config, task, version/hash harness và giá. `--resume` chỉ chấp nhận đúng manifest. |

Payload/gold nằm ngoài workspace và không là tool cho agent. Đây là cách ly công cụ và
cấu hình, không phải chứng minh mọi tiến trình thù địch đã bị sandbox ở mức OS. JSON
provenance xác minh việc dùng snapshot; tự ghi tên nguồn không đủ để được primary pass.

## Metrics

Không cộng các cột thành một điểm tổng.

| Metric | Định nghĩa |
|---|---|
| Primary success | JSON/schema và mọi check bắt buộc đúng, evidence nối ledger thật, process thành công trong thời hạn; mẫu số mọi trial đã bắt đầu. |
| Task bị cách ly | `task.toml` ghi `confirmatory_eligible=false` và `exclusion_reason`; mặc định loại trước khi sample ở mọi split, ghi số lượng/lý do trong manifest, summary và freeze. `--include-quarantined` chỉ dành cho chẩn đoán smoke/pilot, không được cấp certificate. |
| Certificate vận hành | Mọi trial đúng model/catalog, hoàn tất trong budget, usage đủ và ledger replay hợp lệ. Chọn tham số bị snapshot từ chối hoặc model không gọi tool vẫn là lỗi chất lượng; 0 call cần telemetry chứng minh. Mỗi arm phải có canary tool thành công và đáp án primary grounded đúng. Không chứng nhận accuracy của model nhỏ. Xem protocol `operational_parity_v3` trong PRE-REGISTER. |
| Semantic correctness | Check nội dung tài chính riêng, giúp phân biệt lỗi kiến thức/tính toán với lỗi schema/provenance/harness. |
| Stable-correct 3/3 | Task đúng cả ba lần độc lập. Báo riêng task đủ ba lần và task thiếu run; **không phải xác suất đúng khi dùng một lần**. Smoke một run không tạo endpoint 3/3. |
| Bịa trên unanswerable | FP trên task refusal, báo mẫu số started và answered, kèm DNF. |
| Từ chối oan | Null/từ chối ở trường được hỏi có đáp án trong gold. Không suy ra refusal vì thiếu scalar khi đáp án là set/ranking; không loại toàn task vì một trường khác partial. |
| Thời gian | End-to-end p50/p90, valid-answer latency, timeout; bao gồm attempts/backoff. |
| Token/cost | Tổng usage mọi request/attempt, coverage từng trường. Thiếu usage là N/A. Chỉ dùng bảng giá nằm trong manifest; input/cache cần semantics rõ. Subscription/allowance/cash spend không bị đồng nhất với list-price estimate. |
| Chẩn đoán | Per-check, error taxonomy, calls từ ledger, retry, bonus replacement, MAD/abs(median) theo task trên đáp án pass. |

Phân tích so sánh dùng paired bootstrap **theo task**, thêm sensitivity theo hash payload
trùng; exact McNemar trên endpoint stable 3/3 đủ cặp và Holm cho các cặp arm. Không coi
600 trial là 600 quan sát độc lập. Incomplete run và số cặp đủ dữ liệu phải được báo.
Dữ liệu lịch sử không có manifest không được gắn lại model/giá từ config mới; trộn model
trong cùng thư mục bị từ chối.

## Chạy kiểm tra bằng NVIDIA model nhỏ

Cần Python có `mcp`, `jsonschema`, `pytest`, ba harness đã cài và `NVIDIA_API_KEY` trong
môi trường. Key không được ghi vào manifest/config/log. Chạy tại thư mục benchmark:

```bash
# Offline mặc định, không gọi provider và không sửa auth/profile người dùng.
python3 tools/ready_check.py
python3 -m pytest tools/tests -q

# Discovery NVIDIA chỉ khi yêu cầu rõ tùy chọn này.
python3 tools/ready_check.py --provider-probe

# Smoke 3 câu × 3 arm × 2 run: kiểm tra lặp ổn định, không xếp hạng.
python3 tools/run_benchmark.py --split smoke --runs 2 \
  --timeout 180 --max-requests 24 --max-output-tokens 2048 \
  --max-total-tokens 48000 --retry 1 --retry-backoff 4 --pause 2 \
  --effort none --out results/v2-smoke

# Tiếp tục chính xác lần chạy bị gián đoạn: giữ nguyên mọi tùy chọn trên và thêm --resume.
# Driver bỏ qua row đã hoàn tất; attempt đã có kết quả sẽ finalize mà không gọi model lại.
# Attempt bị ngắt giữa request thành terminal interrupted với usage chưa biết=N/A.
```

`--config PATH` chọn config khác; `--model` được phép cho smoke/pilot, nhưng khi dùng
freeze phải trùng model đã chứng nhận trong config. `--tasks id1,id2`, `--sample N`,
`--seed S` và `--arms ...` được đóng băng trong manifest. Chạy tuần tự; gateway dùng
rate limiter chung. Chưa mua Go: không gọi Beam hay DeepSeek trả phí trong kiểm tra.

## Pilot, freeze và main/holdout

Pilot dùng model nhỏ để kiểm tra vận hành, metrics và thời gian. Trước nghiên cứu chính,
chốt **một** model/provider/effort được hỗ trợ, config và subset nếu cần, rồi chạy lại smoke
đúng cấu hình đó. Giữ nguyên code/config/harness/task từ smoke đến khi cấp certificate.

```bash
# Certificate đòi full regression pass + artifact smoke đủ 3 câu × 3 arm × ít nhất 2 run,
# schema/tool/evidence hoạt động và runtime inventory đúng model/config/code hiện tại.
python3 tools/ready_check.py --config tools/bench_config.json \
  --live-run results/v2-smoke --certificate results/v2-ready.json

python3 tools/run_manifest.py --config tools/bench_config.json \
  --certificate results/v2-ready.json --output results/v2-freeze.json

python3 tools/run_benchmark.py --split main --runs 3 \
  --freeze-receipt results/v2-freeze.json --out results/v2-main

# Chỉ thực hiện khi bắt đầu lần xác nhận cuối cùng đã lên lịch.
python3 tools/run_benchmark.py --split holdout --runs 3 --confirm-holdout \
  --freeze-receipt results/v2-freeze.json --out results/v2-holdout
```

Offline xanh **không** tự chứng minh runtime parity. Certificate kiểm tra artifact live
chứ không dựa vào cờ xác nhận. Main/holdout bị chặn nếu certificate, model, code, task,
harness hoặc config thay đổi. Hash bao gồm mọi split; không chạy model holdout trong
phát triển. Holdout có receipt mở một lần tại `results/holdout-open-v2.json`; chỉ
`--resume` đúng run đó được chấp nhận sau khi mở. Không xóa receipt để chạy thử lại.

Nếu route Go/effort medium được triển khai sau này, phải kiểm tra tương đương khả năng
và budget cho cả ba arm trước khi đổi cấu hình. Không lấy kết quả model nhỏ làm ước
lượng chất lượng của DeepSeek. Scope `real_world_filings_accuracy` cần quy trình đối
chiếu tài liệu gốc riêng; certificate hiện tại chỉ hỗ trợ `snapshot_grounded_financial_qa`.

## Artifacts và kiểm toán

```text
results/<run>/
  manifest.json                  # kế hoạch bất biến, hashes, giá, schedule, scoring metadata
  trials.jsonl                   # một row/trial; duplicate/corruption không bị bỏ qua âm thầm
  summary.json                   # coverage, completeness, metrics, paired statistics
  trials/<task>__<arm>__r<run>/
    state.json                   # thời điểm và whole-trial budget bền vững
    grade.json
    attempts/<number>-<nonce>/
      ws/instruction.md
      ws/answer.json             # driver sinh từ final_text nếu hợp lệ
      run.log
      mcp.jsonl                  # lời gọi thực, request/response hashes và provenance
      provider.jsonl             # provider requests và usage, không chứa key
      result.json                # kết quả attempt phục vụ recovery không gọi lại
      runner/                    # config/runtime inventory của adapter
```

```bash
python3 tools/analyze.py results/v2-smoke
python3 tools/analyze.py results/v2-smoke --json
```

`--resume` khóa độc quyền thư mục run, không thêm row trùng và không nạp đáp án attempt
cũ vào session mới. JSONL cuối bị cắt do crash được lưu riêng trước khi phục hồi; dòng
sai ở giữa vẫn làm phân tích dừng để tránh mất dữ liệu. Các artifacts gồm prompt/đáp án
và số đo sử dụng, cần giữ cùng manifest khi chia sẻ kết quả.

## Kế hoạch một tuần

1. Ngày 1–2: regression/adversarial, replay đúng/sai tham số, kiểm tra đơn vị/công thức và
   ambiguity của main/pilot, smoke NVIDIA cả ba arm. Không mở holdout bằng model.
2. Ngày 3: pilot có lặp để đo completion, p90 thời gian, request/token và tần suất lỗi;
   quyết định trước main có đủ 178 task đủ điều kiện hay dùng subset phân tầng đã lưu ID/seed.
3. Ngày 4: chốt model/config/metrics/subset, chạy canary đúng cấu hình, cấp certificate
   và freeze. Việc mua Go chỉ thực hiện sau khi xác minh adapter/effort.
4. Ngày 4–6: main ba lần/task/arm; dùng resume khi gián đoạn; giữ thời gian dự phòng
   quota/recovery. Main + holdout đủ điều kiện cần 1.989 trial nếu mỗi task/arm chạy
   ba lần; thời gian cần tính từ pilot, không ngoại suy từ smoke hoặc hứa đủ trong tuần.
5. Ngày 7: mở holdout một lần nếu main và lịch còn đủ; phân tích paired, CI,
   completeness, payload overlap/family sensitivity; ghi rõ mọi giới hạn.

Đừng điều chỉnh đề/grader theo kết quả holdout. Payload tái sử dụng khiến tính độc lập
hạn chế; sensitivity theo nhóm không thay thế một holdout dữ liệu hoàn toàn mới.
Các kiểm tra pipeline không chứng minh bộ câu hỏi đại diện đầy đủ nghiệp vụ tài chính
Việt Nam: cần bổ sung sau nghiên cứu các case niên độ, báo cáo hợp nhất/riêng lẻ,
điều chỉnh corporate actions, missing fields và tài liệu gốc có page/line evidence.
