# Amendment trước inference: v4.1 trên OpenTrading hiện tại

Ngày06/11/2026, Asia/Bangkok. Bổ sung cho [protocol v4](2026-11-05-v4-improvement-experiment.md). **Chưa có inference v4/v4.1 tại thời điểm đăng ký.** Điều chỉnh do người dùng cập nhật production từ GitHub và giải quyết conflict, không do xem kết quả candidate.

## Primary goal

Đánh giá candidate validation/repair/JSON-provenance trên nền OpenTrading hiện tại, giữ các cải tiến upstream, so với baseline hiện tại và hai harness đối chứng bằng model nhỏ, dữ liệu và ngân sách chung.

## Những gì đã thay đổi từ lúc lập protocol v4

- Production `/home/doanlong/OpenTrading` hiện version0.3.1, HEAD `b6e354e76894887e31c33b1f13b44eadc02fad7e`,212fileTS/TSX. Tracked tree sạch; Git không có unmerged entries và không thấy conflict markers trong source/prompts/tests khi kiểm tra đầu lượt này.
- Upstream đã có stop-gate/recovery notices, guard số liệu chưa truy xuất, circuit breaker, context pruning, effort/provider options và accounting mới. Không loại các tính năng này để làm candidate dễ thắng. Clock/prompt hooks đã được merge vào bản mới.
- Package khai báo SDK mới nhưng node_modules production ban đầu vẫn cũ. Prototype phải có dependency tree **riêng**, cài đúng locked versions; pin actual resolved versions/hash. Không cài qua symlink vào node_modules production và không suy installed version từ package.json.
- Prototype v4 cũ, log test483pass và các review pending được giữ làm lịch sử. Các số đó không chứng nhận codebase0.3.1 mới.

## Workspace và điều kiện mới

Workspace: `experiments/finance-v4-current-study/`. Giữ nguyên `experiments/finance-v4-study/`, v3 và các diagnostic results. Không sửa original OT/MCP-server hoặc thay kết quả cũ.

| Condition | Runtime/prompt |
|---|---|
| `opentrading_baseline` | Bản sao production0.3.1 + cùng optional policy implementation nhưng policyOFF; sáu prompt baseline lấy từ production hiện tại |
| `opentrading_finance` | Cùng runtime, financePolicyON và candidate prompt machine-output; không bỏ safety/upstream guards |
| `opencode` | Native binary/config/session riêng, cùng MCP C1 và ngân sách |
| `dsh` | Native binary/config/session riêng, cùng MCP C1 và ngân sách |

Canonical `opentrading` chọn candidate chỉ trong workspace thử nghiệm này. Không gọi đó là prompt mặc định production. Candidate là gói combined; không dùng thí nghiệm này tách nhân quả validator/prompt/repair riêng lẻ.

## Phải kiểm chứng trước smoke

1. So diff theo chức năng khi port policy, không ghi đè agent/registry mới bằng toàn file từ bản cũ. BaselineOFF giữ hành vi upstream; candidate integration giữ native stop-gate/recovery/accounting/cancellation/circuit breaker.
2. Candidate correction tối đa một attempt bổ sung theo policy v4, nằm trong turn budget và native step accounting. Recovery vốn có của upstream vẫn tồn tại ở cả baseline/candidate và phải được công khai; không coi mọi request thêm là candidate-only hoặc successful repair.
3. Dùng default stall của native hiện tại (300giây theo source/opts hiện tại), provider timeout45giây và trial240giây cho mọi arm; không lén tăng cap cho OT. Knob/streaming cần nghiên cứu riêng trước dùng model mạnh; không gọi model mạnh ở study này.
4. Pin actual dependency tree/binary/runtime source/prompt/calendar/config/C1catalog/protocol/task/grader. Kiểm raw/effective wire schema và tool errors; không đòi wire hash byte-identical nếu SDK biến đổi khác nhau đã công bố. Common server C1/validation/data vẫn giống nhau.
5. Kiểm MCP C1 authoritative schema=model-visible source catalog; strict Bolt admission cả CLI và gateway; native local rejection có callID/args/error/next-wire proof, không giả là MCP execution.
6. Fresh native focused+typecheck+full suite trên code/deps mới; full benchmark regression và offline preflight tuần tự khi cần socket/MCP subprocess. Reviewer độc lập phải đóng các finding thực tế; không chỉ thay dòng trạng thái pending từ kết quả người triển khai.
7. Hash original source/tasks ở đầu và cuối để phân biệt thay đổi của người dùng với thay đổi nghiên cứu. Không reset tracked/untracked files hoặc dependency tree production.

## Lịch và endpoint giữ nguyên, tên artifact đổi ngày

- Chỉ `nvidia/nvidia/nemotron-3.5-bolt-e4b`, effortnone,temp0,top_p1. Không DeepSeek/Go/Google, không inference main/holdout.
- Seed20261105, timeout240, provider_timeout45,24request,2048output/request,48000policytokens,retry0,pause2s.
- Smoke18:3task×2run×canonical3arms; khi gate vận hành pass mới pilot176:22eligiblepilot×2run×4condition,44/condition, cân bằng lịch.
- Artifacts nằm trong `experiments/finance-v4-current-study/results/financial-v41-{smoke,pilot}-20261106`; receipt/certificate riêng, không dùng receipt v3/v4 cũ.
- Primary grader v4 đã sửa broad-negation, evidence nối actual ledger, mẫu số mọi trial bắt đầu. Frozen-v3 grader sensitivity chấm song song mọi đáp án mới; không sửa điểm lịch sử.
- Development set đã được đọc để thiết kế. Báo CI95 exploratory, lỗi/usage/DNF đầy đủ; không gọi điểm cao hơn trên pilot là vượt trội toàn lĩnh vực. Chưa thực hiện criterion main+7pp/CI97,5%.
- Guard v4 giữ nguyên: primary phải cao hơn concurrentbaseline, không regress DNF/false refusal/FP/evidence mismatches; không tự promote. Không thêm compute endpoints, đổi corpus/gold hay retune candidate sau inference trong cùng study.
- Khi pilot chạy, để job chạy độc lập; review một lượt khi hoàn tất theo yêu cầu tiết kiệm quota. Heartbeat chỉ kiểm nhanh trạng thái, không phân tích lại từng trial; khi hoàn tất review/report xong thì tắt.

## Các đề xuất mới trong OpenCode §10

Compute-as-tools và chuẩn hóa đơn vị là hướng phát triển có cơ sở, đã có trong Phase4 kế hoạch chuẩn hóa; cần thí nghiệm common-tool riêng nếu triển khai. Các con số dự báo16–19/44 hoặc24–30/44 chưa có dữ liệu thực nghiệm.12task cùng fail không chứng minh trần bất biến hay con đường cải thiện duy nhất. Không bổ sung các endpoint/normalization mới vào study v4.1 sau khi đã đăng ký để săn điểm.
