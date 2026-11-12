# Đồng bộ OT và căn cứ lập v4.5 — 08/11/2026

**Đã fetch và merge main mới vào OT local; chưa có inference v4.5 và chưa chứng nhận sẵn sàng benchmark main.**

## Repo sản phẩm

| Mốc | Commit |
|---|---|
| Local trước pull | `e5ce4e1a75a6c430ff8464b867032da18814cee3` |
| Remote main được fetch | `0a65fa04d0e60ee3d1822de365f2a88dc92eaf2f` |
| Local sau giải conflict và merge commit | `b4b4b848541986239cfd477715b6d3819cbc443c` |

Repo `/home/doanlong/OpenTrading`, branch main. Remote main là ancestor của merge; working tree tracked sạch, không unmerged entry; ahead3 là hai commit local cũ và merge mới. Không push GitHub. PR #229,235,236,237,238,222–227,239 đều được xác minh merged qua GitHub plugin; metadata và mô tả lưu trong `upstream-merged-prs.json`.

Một conflict tại imports `src/core/agent.ts`: upstream bỏ `loadProfile` để dùng memory binding/constraints/redaction/cards; local thêm `validatePromptDir`. Giữ toàn bộ imports/cơ chế memory mới và `validatePromptDir`, bỏ import `loadProfile` lỗi thời. `src/core/prompt/assemble.ts` auto-merge sạch. Diff cuối so remote chỉ hai file này, giữ trusted prompt directory validation và snapshot-clock caller option; không thay prompt sản phẩm hay native calculator bằng bản cũ.

Backup trước pull: `ot-before-pull.tar.gz`, `ot-before-pull.json`, patch. Có999file, trong đó441file chưa được Git theo dõi; các file cá nhân đều được kiểm tra hash không đổi. Dependency cài đúng `bun install --frozen-lockfile` mới (AI SDK7.0.162 và các dependency upstream). Backup có tài liệu/research cá nhân: chỉ giữ local để rollback, không publish hoặc commit lên remote.

## Các kiểm tra sau merge

| Kiểm tra | Kết quả thực tế |
|---|---|
| `bun run typecheck` | PASS |
| Full `bun test` | **1839 pass,2skip,2fail**,1843test/148file,343.32s |
| Recall performance chạy riêng với cùng ngưỡng50ms | PASS; ba lần55.9/36.8/53.7ms; full lần trước99.8/79.4/78.7ms |
| Test TUI lọc riêng theo tên | FAIL vì thiếu prerequisite connect/config do các test trước thiết lập; không dùng kết quả này để suy product regression |
| Toàn bộ `test/tui.test.tsx` chạy riêng đúng thứ tự | **114pass,0fail**,38.55s |
| `verify-merged-hooks.ts` | PASS; promptDir/symlink guard, snapshot/live clock, memory policy/index tier, constraints và invalid clock;0modelcall |

Giữ nguyên tất cả log và kết quả FAIL. Hai lỗi full suite là recall timing và TUI frame deadline; chạy riêng đúng context đều đạt. Chưa chứng minh dứt khoát nguồn biến thiên hoặc một lượt full-suite hoàn toàn xanh. Không sửa source/test threshold để làm xanh; clean full-suite kiểm chứng tiếp nằm trong gate v4.5. Test hook ban đầu có một assertion sai về channel constraints; sửa fixture theo source thực (constraints ở system, memory index ở context), không đổi code sản phẩm.

## Giữ v4.4 sao cho hợp lý

V4.4 candidate không được production-promote vì trượt gate; production trước pull chỉ có hook benchmark cũ. Không kích hoạt hồi tố prompt/policy thất bại. Những phần cần giữ được bảo toàn theo hai lớp:

1. Hook thực đã cài trong sản phẩm (`promptDir`, validation, snapshot clock) được merge vào agent/prompt assembly mới, có kiểm tra phối hợp memory.
2. Toàn bộ candidate v4.4 vẫn nguyên vẹn để port chọn lọc trong v4.5: validation, same-intent bounded repair, replay guard, raw invalid final, telemetry/evidence và cancellation. Không copy nguyên `agent.ts` cũ vì sẽ xóa memory tích hợp mới. `v44-native-delta-inventory.json` và `v44-native-reference.patch` liệt kê14file khác baseb6e354e; benchmark-side compute/grader/auditor/adapter riêng được chỉ dẫn trong kế hoạch.

Xác minh đọc-only sau pull (`post-pull-v44-preservation.json`):1795entry code/task/test/protocol trong study v4.4 cùng213source native và25runtimepackage giữ hash; **8132entry kết quả/trial/capture/ledger/pilotmanifest giữ hash/kích thước/mtime** so completed-resume proof; pinned auditor vẫn SHA743045848cd17165ddaec9c54530cdc487f44fcbf9ce8fd3c0e40a7089a78bde. Không regrade, không inference, không khởi chạy supervisor/resume v4.4 ở lượt này.

Đã tạo base source mới **chỉ705file Git-tracked** tại `/home/doanlong/extra/benchmark/experiments/finance-v45-base/opentrading-runtime`, pin mergeHEAD trên. Không copy research cá nhân/auth/profile/memory.db/.git/node_modules. `v45-base-source-manifest.json` lưu từng hash. Đây là snapshot **trước triển khai v4.5**, chưa có policyport hoặc approval/seal v4.5; không coi nó là study đã sẵn sàng chạy.

Legacy root `experiments/opentrading-runtime/node_modules` liên kết tới dependencies sản phẩm; đường legacy hiện không tương đương dependency pin của v3 (ai7.0.137 vs target7.0.162). Không dùng đường này hoặc approval cũ cho run mới. V4.4 có node_modules riêng và25package đã đối chiếu khớp seal; v4.5 snapshot cũng phải cài dependency riêng trước chạy. Không chỉnh manifest lịch sử để che drift.

## Review §14–16 và corpus cập nhật

Báo cáo discovery được giữ độc lập, phản ánh source lúc merge còn đang chờ commit; HEAD cuối ở báo cáo này và manifest là nguồn provenance hiện hành.

- `OPENCODE-SECTIONS14-16-FACTCHECK.md`: kiểm chứng FULL review. Sửa attribution “403storm”, acquisition count, tuyệt đối hóa fabrication, dự báo chi phí/điểm và giả thuyết ngôn ngữ/decoder.
- `MEMORY-COMPUTE-DISCOVERY.md`: APIs memory/refs/calculate/compute/headless thực; native ref chưa thay thế biên nhận7trường; scalar/units/scope/persistence cần kiểm tra.
- `CORPUS-DISCOVERY.md`: main200/183eligible,10task mới10/10fixture nội bộ, nhưng audit227exit1 và lỗi202/214/graders/refusal/corpusoverlap. Các bằng chứng offline lưu `corpus-offline-checks/` và `corpus-offline-audit/`. Không sửa tasks/golds/graders hoặc chạy main trong lượt review.

## Model/retry và quyết định

Kế hoạch mới dùng NVIDIA Super VL120B-A12B thay E4B và NVIDIA DeepSeekV4.1Flash; không đổi archived configs/model identities. `plans/v45-execution-profile.draft.json` có policy initial+2transportretry, cùngmọiarm, khôngqualityretry/resetbudget, wholetrialretry0. Đây là **draft chưa executable**: Super chưa admission, caps/thinking/wire chưa xác minh, customnativeOTretry chưa có knobtắt nên phải xử lý retryowner trước launch. Không cam kết mọi câu đều có đáp án bằng retry.

Kế hoạch chính: [2026-11-08-v45-finalization-plan.md](/home/doanlong/extra/benchmark/plans/2026-11-08-v45-finalization-plan.md). Tiêu chí product/main freeze, smoke/pilot, phần thực nghiệm và giới hạn dự tính nằm trong đó. Bản hiện tại là nền đúng hơn để hoàn thiện OT, **chưa có bằng chứng vượt OpenCode/DSH hoặc sẵn sàng main**. Không có call model nào trong lượt đồng bộ/lập kế hoạch này. Heartbeat cũ vẫn đã xóa; không tạo lại automation.
