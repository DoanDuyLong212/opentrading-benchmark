# Study v4.7: thiết kế runner (2026-11-15)

Trạng thái: **chưa seal**. Chỉ chạy dev smoke (`BENCH_V47_DEV=1`). Pilot, main và holdout cần seal mới.

Thư mục: `experiments/finance-v47-study/`. Chép `tools/` và `tasks/` từ v4.6u, không chép kết quả. Không sửa gì trong v4.6u (or16).

## Runtime OpenTrading
- Ghim commit `baa6743` (nhánh `feat/278-defer-local` = `main` 45ac4ff + #288 + PR hoãn nạp). Chép bằng `git archive` vào `experiments/opentrading-runtime/`, chạy `bun install --frozen-lockfile` ngay tại đó (không symlink).
- Prompt của OT (`tools/prompt_variants/baseline/`) là bản chép nguyên văn `prompts/` của commit đã ghim. Hash ghi trong `baseline.SHA256SUMS`.
- Runner chỉ giữ tool MCP snapshot, `shell` và `read_result`. Mọi tool hoãn nạp được đều bị gỡ, nên #288 và PR hoãn nạp không đổi request benchmark. Chỉ prompt và shell đổi.

## Quyết định của người dùng
| Mục | Quyết định | Cách làm |
|---|---|---|
| Công cụ tính | A: shell thật của từng harness, chỉ cho phép phép tính, một bộ lọc chung | `tools/runners/mathshell/`: `bin/bash` và `bin/sh` đứng đầu PATH, `$SHELL` trỏ vào đó. `filter.ts` dùng grammar `mathOnlyCommand` của runtime đã ghim. Lệnh không phải phép tính bị từ chối với cùng một câu cho mọi arm. Mỗi lệnh ghi vào `runner/shell.jsonl` |
| Trần request | Giữ trần an toàn ở gateway, không đặt trần trong harness | Gateway 24 request/trial. OT không truyền `maxSteps`, OpenCode không đặt `steps` |
| Trần tổng token | Giữ trần an toàn ở gateway | 4,6M/trial. Nâng từ 3,6M vì mỗi request giờ phải dự trữ đủ output tối đa của model, nên giữ khoảng dùng thực tế gần như or16 (~2,6M) |
| Trần output | Không giới hạn | Gateway không ép và không chèn `max_tokens`; harness gửi gì thì chuyển nguyên (smoke: OpenCode xin 256 000, DSH 32 768, OT không đặt). Phần dự trữ ngân sách thì giống nhau cho mọi arm (mức tối đa của model), để trần tổng token dừng mọi arm ở cùng một chỗ. OpenCode bắt buộc có `limit.output` nên đặt bằng mức tối đa của model (943 718, OpenRouter). DSH không đặt `maxTokens` |
| OT hỏi người dùng | Tự duyệt | Gate của OT được đặt là tương tác; mọi câu hỏi duyệt được trả lời "once". Đã kiểm (15/11): lệnh `python3 -c` nhận gợi ý viết lại của #289 và không chạy; awk đúng dạng chạy; `ls /` được tự duyệt rồi bị bộ lọc chung chặn |

## Cân bằng giữa các arm (thêm theo đề xuất)
- **OpenCode**: bật plugin `opencode.tool.shell` (thiếu plugin này thì treo) và quyền `shell`. Quyền `doom_loop` đặt allow vì không ai trả lời được câu hỏi này, cho khớp với OT tự duyệt. Workspace được `git init`, vì không có repo git thì tool shell treo trước request đầu (thử với mock ngày 15/11).
- **DSH**: bật `tool-bash` và các dịch vụ nó cần. Bật lại `repeat-tool-reminder` (mặc định của DSH, ngưỡng 3/5/8), vốn bị tắt ở or16 do không có trong danh sách cho phép.
- Kiểm bằng mock: cả 3 harness đều gọi `bash -c <lệnh>` qua PATH, nên bộ lọc chung bắt được hết.
- OT thêm `LC_ALL=C` và `-v OFMT=%.15g -v CONVFMT=%.15g` vào lệnh awk trước khi gọi bash. Bộ lọc bỏ đúng hai dạng này trước khi kiểm. Lợi thế 15 chữ số của `print` là tính năng thật của OT, được giữ nguyên.

## Tool mỗi arm thấy
| | OT | OpenCode | DSH |
|---|---|---|---|
| MCP snapshot | có | có | có |
| Shell (qua bộ lọc) | `shell` | `shell` | `bash` |
| Khác | `read_result` (đọc output dài OT đã cất) | không | không |

## System prompt
OpenCode và DSH ghép system prompt theo các tool đang bật, nên khi chỉ còn MCP và shell, prompt của chúng ngắn lại (OpenCode 617 token, DSH 98). Đó là hành vi thật của hai harness với bộ tool này. Prompt của OT là tĩnh (2 558 token), không co lại khi bị gỡ tool.

## Bộ lọc là khung dựng của benchmark
Câu từ chối của bộ lọc kèm `mathHint` của OT. Vì vậy OpenCode và DSH biết grammar của OT sau lần bị từ chối đầu tiên; đây là phần do benchmark thêm, không phải hành vi gốc của hai harness.

## Việc còn lại trước khi seal
- Ledger `native_derived` và các audit tính toán vẫn đọc dạng `calculate`. Cần chuyển sang đọc `shell.jsonl`.
- Nối `--profile machine` và trần request của OT khi OT có hai cờ này (không dùng trong benchmark vì OC và DSH không có cơ chế tương đương).
- Dev smoke đủ 3 arm, rồi pilot mới.
