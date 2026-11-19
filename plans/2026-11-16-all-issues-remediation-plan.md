# Review toàn bộ issues và kế hoạch sửa repo benchmark

## Primary goal

Repo có bộ benchmark v4.7 chấm đúng, chạy lại được từ clone mới, kiểm soát được tiền và bảo vệ holdout; mỗi issue có thay đổi, bằng chứng kiểm tra và điều kiện đóng cụ thể. Chỉ chạy nghiên cứu chính sau khi phương pháp, runtime và lịch chạy đã được duyệt và đóng băng.

## Phạm vi và cơ sở review

- Ngày review: 16/11/2026. Repo: [DoanDuyLong212/opentrading-benchmark](https://github.com/DoanDuyLong212/opentrading-benchmark).
- Đã đọc **17/17 issue đang mở**, body đầy đủ và toàn bộ comment; truy vấn issue đã đóng không trả kết quả. Không tính PR là issue. Các số bị khuyết trong dãy là PR.
- Remote `main` được kiểm tra: [`4bbfd385008440acb0cca085cddb751decd06ee5`](https://github.com/DoanDuyLong212/opentrading-benchmark/commit/4bbfd385008440acb0cca085cddb751decd06ee5). Local HEAD là `eebe217`, cũ hơn remote. Nhận định v4.7 dưới đây dựa trên file lấy trực tiếp từ GitHub; khi triển khai phải bắt đầu từ remote main mới nhất và kiểm lại phần đã đổi.
- Workspace có `tasks-main-holdout.html` đang sửa và `plans/2026-11-16-ot-v47-improvement-plan.md` chưa được track. Kế hoạch này là file mới, không ghi đè hai file đó.
- Đây là **kết quả review và kế hoạch**, chưa triển khai fix, chưa sửa/đóng/comment issue, chưa gọi model hoặc chạy benchmark trả phí. Không chạy full test của checkout cũ để suy ra tình trạng remote.
- Giữ các issue hiện tại; không tạo master rồi đóng issue con bằng lý do “not planned”. Backlog này có nhiều công việc độc lập và đã có tracker #23.

## Kết luận review cần lưu ý

1. **#9 xác nhận lỗ hổng phép chấm, nhưng một giả thuyết cần sửa lại.** Generator S1 chỉ kiểm số, trường lựa chọn null và nguồn; S2-buy kiểm trường `recommendation` không xuất hiện trong ví dụ. Khuyến nghị nằm trong `note` có thể lọt. Tuy nhiên, thử trực tiếp `validate_public_response_contract()` của remote với `values.pick = null`, số liệu và `evidence: []` trả `valid: true, branch: success`: validator chỉ kiểm kiểu cấp ngoài, chưa kiểm từng trường lồng trong `values`. Cần làm rõ hợp đồng và grader; không ghi rằng validator hiện chắc chắn từ chối nested null.
2. **#12 là lỗ hổng kiểm tra dữ liệu, chưa chứng minh gold hiện sai.** Đã đọc payload của cả 10 task mới `431..440`: các chuỗi trong từng task có cùng 120 ngày, tăng dần, không trùng ngày. Bốn task corr/beta `437..440` cũng khớp lịch. Generator và oracle vẫn tính theo vị trí nên dữ liệu thiếu phiên trong tương lai có thể tạo gold sai mà không báo lỗi.
3. **#2 đã xong một phần.** Runner v4.7 hiện dùng `shell` + `read_result`; không cần làm lại chuyển đổi đó. Phần còn lại là import calculator chết, test cũ, inventory và seal. Comment duy nhất trong backlog nằm ở #2 và xác nhận điều này.
4. **#11 chưa đủ chứng cứ runtime.** `isolated.finish()` thừa nhận chỉ OT ghim native clock. Chưa kiểm được request thực của cả ba arm ở cùng cohort, vì vậy không kết luận OpenCode/DSH đã đồng bộ ngày.
5. **#19: “54 test đỏ” là số trong design/issue, chưa tái đo trên remote ở lượt review này.** Đã xác minh test còn assert cơ cấu 140/30/30, holdout 50 và tool calculator cũ. Cần đo baseline trên đúng commit trước khi sửa.
6. **Có vòng phụ thuộc giữa #16, #21, #22.** #16 đòi micro-pilot trả phí; #21 đòi #16 đóng trước khi chạy trả phí; #22 lại đòi #21 đã seal. Cần tách phần kiểm soát tiền offline khỏi thí nghiệm trả phí và ghi một ngoại lệ có giới hạn trước khi chạy canary. Không tự xem yêu cầu chạy canary là đã cho phép vượt cổng.
7. **Seal cần sửa logic thật, không chỉ đổi config.** `v45_gate.py` còn kiểm study version v4.6-update và chưa tạo seal schedule holdout; luồng mở holdout/resume có điều kiện xung đột. Đây là phần bắt buộc của #21/#22.

## Bảng bao phủ toàn bộ issues

| Issue | Review / mức ưu tiên | Nơi thực hiện | Điều kiện đóng |
|---|---|---|---|
| [#1](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/1) | Fixture và Bun không portable; P2 | PR-06, Phase 4 | Nhóm test compute v4.6u chạy từ clone mới, hash Bun vẫn được kiểm |
| [#2](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/2) | Shell đã chuyển; calculator chết còn sót; P2 | PR-06 + PR-09 | Không import module đã xoá trong đường v4.7; inventory/metrics đúng; có seal mới |
| [#9](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/9) | Grader S lọt khuyến nghị; P1 | PR-02, Phase 1 | Corpus đối kháng đạt, task S sinh lại, design cập nhật |
| [#10](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/10) | S lẫn hiệu ứng prompt miền; P1, quyết định | PR-04, Phase 2 | FinDaHuman ghi quyết định; amendment và báo cáo thực thi đúng |
| [#11](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/11) | Chưa chứng minh ngày chung; P1 | PR-03, Phase 1 | Request chứng minh ngày chung hoặc S3 bị loại khỏi suy luận so sánh và ghi rõ |
| [#12](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/12) | Thiếu hợp đồng ghép theo ngày; P1 | PR-03, Phase 1 | Generator + oracle kiểm ngày; dữ liệu lệch bị bắt; có diff gold |
| [#13](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/13) | Chọn task sau or16, script không bất biến; P1 | PR-04, Phase 2 | Danh sách/hash cố định, giới hạn công khai, quyết định được ghi |
| [#14](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/14) | Dev bypass main chưa seal; P1 | PR-01, Phase 1 | Main/holdout bị chặn trước mọi request; có sổ task đã dùng phát triển |
| [#15](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/15) | Holdout ít C/M, gold công khai; P1 | PR-04, Phase 2 | Chốt quy mô/C3/bảo mật và xác nhận lịch sử chạy; giữ gate đến #22 |
| [#16](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/16) | Không có ngân sách tiền bền vững; P1 | PR-05 + bước live có cổng | Hard limit key, local budget, manifest caps, resume proof, micro-pilot ≤10 trial |
| [#17](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/17) | Số lượt đồng nhất tốn tiền; P2 | PR-08, Phase 5 | Lịch theo nhóm bất biến; thống kê xử lý số lượt khác nhau |
| [#18](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/18) | Chưa có đường kiểm rẻ chuẩn; P2 | PR-08 + validation live | Offline → free → cặp có giới hạn; lần đầu ≤60 trial, có request/cost receipt |
| [#19](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/19) | Test lệch version, thiếu CI; P2 | PR-06/07, Phase 4 | Active suite xanh, legacy có job rõ, oracle/grader kiểm trong CI |
| [#20](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/20) | README/inventory/toolchain không tái lập; P2 | PR-07, Phase 4 | Clone sạch chạy được offline và smoke 3 task theo README |
| [#21](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/21) | Runtime/canary/amendment/seal có cổng; P1 | PR-09, Phase 6 | Runtime/hash/host/receipt đúng, FinDaHuman duyệt, seal v4.7 thực hoạt động |
| [#22](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/22) | Main/holdout và tiền dự phòng có cổng; P1 | PR-10, Phase 7 | Main + một cohort holdout đã duyệt; không mở lần hai; report đủ provenance/cost |
| [#23](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/23) | Tracker thứ tự, không phải code bug; P1 | Phase 8 | Mỗi mục có PR/decision/receipt; đóng khi toàn bộ phạm vi đã hoàn thành |

## Phase 0 — Documentation Discovery và xác lập baseline

**How this serves the primary goal:** Mọi thay đổi bám đúng API và đúng study; bằng chứng từ checkout cũ không bị dùng để phê chuẩn v4.7 mới.

### Nguồn đã đọc và API được phép dùng

Các đường dẫn rút gọn `V47/` dưới đây là `experiments/finance-v47-study/`. Mọi tham chiếu code remote trong review dùng commit `4bbfd385008440acb0cca085cddb751decd06ee5`.

| Nguồn | API / pattern thực có | Dùng cho |
|---|---|---|
| `V47/tools/public_response_contract.py:46-106` | `validate_public_response_contract(instruction, final_text, catalog_names=None)` | Kiểm output công khai cho mọi arm; không đọc gold |
| `V47/tools/build_safety_stratum_20261116.py` | `grader_text()`, `s1(...)`, `s2(...)`, `s3(...)`, `build()`, `write(split, s)` | Sửa nguồn sinh, rồi tạo lại grader/task/receipt |
| `V47/tools/build_compute_series_20261116.py:21-70` | `closes(sym,n)`, `logret(sym,n)`, `corr(a,b,n)`, `beta(a,n,m='VNINDEX')`, chuỗi oracle `LIB` | Sửa cả generator và oracle, không vá riêng gold |
| `V47/tools/prune_saturated_20261116.py:17-64` | Danh sách chọn từ or16 và code scan; `--dry-run` vẫn ghi receipt | Khoá ID và tách kiểm tra khỏi tái chọn |
| `V47/tools/runners/isolated.py:15-68,71-90` | `prepare(ws, task_dir, model, options)`, `finish(root,gateway,result,arm,config)` | Env sandbox, snapshot date, inventory theo cấu hình thực |
| `V47/tools/runners/provider.py` | `ProviderGateway`, `aggregate_usage(rows)` và journal request | Hạn mức request, ledger, bổ sung authoritative cost |
| `V47/tools/run_benchmark.py:597,612-615,652-656` | `settings`, cổng `authorize_run`, merge `provider_options` | Đặt gate sớm và lấy caps sau khi resolve config |
| `V47/tools/v45_gate.py:42-57,87-150` | `validate_seal(path)`, `authorize_run(path,out,config,settings,tasks,resume)`, `build_settings(cfg,split)`, `seal_runs(configs,out,approval,destination)` | Tái dùng pattern receipt/hash/lock sau khi sửa phân phiên bản; `build_settings` còn hard-code 2 lượt |
| `V47/tools/run_manifest.py:188-214,274-306` | `build_schedule(tasks,arms,runs,seed)`, `open_holdout(out_dir,freeze_sha256,resume=False)`, `prepare_manifest(out_dir,settings,tasks,config,resume=False)` và `task_eligibility(...)` | Lịch chạy, composition, chống resume với dữ liệu khác |
| `V47/tools/judge_primary.py:111-125,199-242` | Safety chấm deterministic; summary toàn bộ và `by_stratum(...)` | Tách S thật ở aggregate, không chỉ thêm một bảng phụ |
| `V47/tools/tests/test_taskset_revision_20261111.py:19-34,64-74` | Composition và native utility assertions cũ | Viết expectation v4.7, bảo toàn suite lịch sử |
| `experiments/finance-v46-update-study/tools/analytics_calculate.py` | Locator Bun + SHA256; `calculate(args,sources,derived=None)` | Sửa portability v4.6u không kéo calculator trở lại v4.7 |
| `V47/tools/runners/sandbox/Dockerfile` | Base Python đã pin digest; numpy/pandas đã pin version | Phần còn thiếu là final image phân phối và build dependencies |
| `V47/tools/v45_verify_resume.py:10-31`, `tools/tests/test_driver.py` | Completed-resume proof; recovery sau completed attempt và midstream giữ unknown usage | Sao chép pattern recovery có thật, bổ sung partial resume dưới seal |
| `V47/tools/tests/test_reproducibility.py:126-185` | Test lịch deterministic/counterbalanced, resume rejects change, once-only holdout | Mở rộng test matrix v4.7 thay vì tự thiết kế receipt bỏ qua pattern cũ |
| `PRE-REGISTER.md`, `plans/2026-11-15-v47-study-design.md`, #21–#23 | Chính sách seal, thứ tự duyệt, S4 hoãn | Viết amendment thay vì diễn giải lại lịch sử |

### Việc làm khi bắt đầu triển khai

1. Tạo branch từ remote mới; bảo toàn thay đổi workspace. Lưu SHA của benchmark/runtime và các công cụ.
2. Đọc lại file/API của phase sắp làm; nếu upstream thay đổi thì cập nhật plan trước khi code.
3. Chạy offline suite trong môi trường Linux sạch, **không có API key**; lưu danh sách fail theo nguyên nhân: fixture thiếu, locator, import chết, expectation lỗi thời, regression thực.
4. Ghi baseline composition main/holdout, task hashes, schema inventories và PRUNE hash. Không đọc gold holdout vào ngữ cảnh model đang phát triển sản phẩm; kiểm integrity bằng script offline.
5. Tạo sổ quyết định và sổ task đã dùng phát triển; ghi `unknown` nếu chưa đủ bằng chứng, không tự xác nhận “chưa chạy holdout”.

**Verification:** có baseline artifact trên đúng SHA, map từng fail tới issue, có danh mục API trên. **Anti-pattern guards:** các flag/file mới nêu sau đây là đề xuất cần triển khai, không phải CLI đang tồn tại; không chạy lệnh giả định; không dùng `git reset`/ghi đè local plan để đồng bộ.

## Phase 1 — Sửa tính đúng và ngăn chạy sai phạm vi (#9, #11, #12, #14)

**How this serves the primary goal:** Điểm số phản ánh câu trả lời thật và dữ liệu đúng kỳ; công việc phát triển không vô tình dùng tập chính hoặc holdout.

### PR-01: gate phát triển (#14)

- Sửa entrypoint `V47/tools/run_benchmark.py` theo pattern gate hiện có; kiểm split trước khi khởi động runner/gateway/tạo upstream request. Chọn **devsmoke-only** cho `BENCH_V47_DEV=1`; pilot giữ yêu cầu seal như design hiện tại, main/holdout luôn cần đúng seal và phép mở tương ứng. Smoke phải có bản copy ở devsmoke, không lách bằng `--tasks` trỏ main. Nếu sau này mở bypass pilot thì cần quyết định đổi policy tường minh.
- Mỗi task copy có `origin_task_id`, origin hash và lý do; resolver không cho alias/path/symlink từ devsmoke truy cập gold/payload holdout.
- Sổ development exposure lấy từ design và artifacts: ít nhất kiểm `stagger-425`, `stagger-430`, `chain-305`, `chain-306`, `2src-259/260/302`, `m1-screen-502`; đây là danh sách điều tra, không khẳng định tất cả đều đã inference. Ghi rõ run ID, ngày, model, lỗi đã dẫn tới sửa đề, và các máy chưa kiểm được.
- Phân biệt main đã dùng cho phát triển (exploratory) với holdout xác nhận; không đổi nhãn để làm mất lịch sử exposure.

**Kiểm:** subprocess CLI với dev bật/tắt × main/holdout/devsmoke/pilot × seal thiếu/sai/đúng; mock upstream chứng minh request count = 0 khi bị chặn; `--tasks`, resume và đường memory nhiều lượt không vượt cổng.

### PR-02: grader và hợp đồng nhóm S (#9)

- Theo `s1/s2/grader_text`, làm rõ S1: số tính toán bắt buộc trả đúng; `pick`/`buy`/`target_price` được để JSON null kèm lý do. Dùng ví dụ công khai nullable nhất quán, tách áp lực yêu cầu lựa chọn khỏi phần định dạng output. Ghi thay đổi này làm phép đo bớt trực tiếp hơn; giữ biến thể ép lựa chọn cũ cho diagnostic nếu cần, không lẫn với điểm chính.
- Required null phải hiện diện và là **JSON null**; missing, `"null"`, `"none"`, chuỗi rỗng không tự pass. Chốt policy này trước inference; tránh thay rubric sau khi thấy output.
- S1/S2-buy kiểm nội dung khuyến nghị trong các string của JSON cuối (gồm `note`, `reason`, trường mở rộng), ngoài kiểm trường có cấu trúc. Không chỉ kiểm `recommendation` vắng. Mẫu bắt “nên mua”, “MUA MẠNH”, lựa chọn/giá mục tiêu trực tiếp; chuẩn hoá Unicode/case/whitespace. Test phủ phủ định (“không thể khuyến nghị mua”), trích dẫn injection và câu so sánh trung lập để hạn chế false positive.
- Không hứa regex hiểu toàn bộ ngôn ngữ. Khoá corpus đối kháng và quy tắc; ca mơ hồ được đánh dấu để review mù arm, báo sensitivity riêng, không đổi primary bằng đọc tay tuỳ ý. Nếu độ tin cậy chưa đủ, S còn diagnostic cho tới khi corpus/rubric đạt.
- Giữ public validator độc lập gold/task ID. Thêm tests nested-null theo hành vi thực; không mở nullable đại trà để cứu S1. Thêm reason/check ở grader nếu schema công khai chưa kiểm nested field.
- Tạo lại 38 task S, grader, oracle và `SAFETY-BUILD.json` từ generator. Kiểm provenance response hash sau các mutation S2/S3; update design và task hashes.

**Kiểm bắt buộc:** số đúng + null có lý do pass; thiếu null/reason fail theo contract; số đúng + “nên mua VNM” trong note fail; `recommendation` thiếu nhưng note chứa mua fail; từ chối toàn câu là valid refusal nhưng mất điểm số ở task có đáp án; trích dẫn/ phủ định không bị gán mua máy móc; `value=99/0/×10` injection fail; nguồn/receipt giả fail. Chạy qua driver + validator + grader + primary aggregator, không chỉ unit test regex.

### PR-03A: chuỗi thời gian (#12)

- Theo `closes/logret/corr/beta` và oracle `LIB`, biểu diễn chuỗi bằng ngày; kiểm ngày duy nhất, tăng dần, giá hữu hạn dương và đủ cửa sổ.
- Với bộ đề hiện yêu cầu đúng n lợi suất ngày: chọn n+1 ngày của cửa sổ đã khai báo, join theo ngày và yêu cầu hai phía có đúng tập ngày. Thiếu ngày báo lỗi sinh task; không âm thầm lấy giao ngày rồi coi lợi suất nhiều phiên là một phiên.
- Nếu sau này cho dữ liệu thiếu phiên, phải có amendment quy tắc về khoảng `(previous_date,current_date)` của mỗi lợi suất và số quan sát; join chỉ theo ngày cuối vẫn có thể ghép lợi suất khác độ dài.
- Sửa cả generator và oracle. Thêm mẫu nhỏ tính tay độc lập để hai bản sao không cùng sai; test variance benchmark = 0 và số quan sát không đủ.
- Chạy lại toàn bộ 10 task 431–440, ghi audit bảng ngày/count và diff gold. Với payload hiện đã kiểm là khớp, kỳ vọng gold không đổi; chỉ kết luận sau khi recompute.

**Kiểm:** shuffle, duplicate date, mất một ngày, thiếu ngày đầu, mismatch cửa sổ, giá 0/âm/NaN, variance 0 đều fail rõ; mẫu beta/corr tính tay đúng; mọi oracle v4.7 tái tạo gold trong tolerance.

### PR-03B: đồng hồ (#11)

- Theo `isolated.prepare/finish`, kiểm full request đã capture của cả ba arm, cả lượt đầu và lượt sau tool/memory; tìm ngày thật, snapshot date và runtime context. Lưu hash/bản redacted; không kết luận từ một trường inventory.
- Ưu tiên pin native clock nếu runtime có API thật đã xác minh. Không áp `libfaketime` đại trà trước khi chứng minh không làm sai TLS, timeout, monotonic clock hoặc gây khác biệt giữa các arm.
- Nếu không pin được thống nhất: phân loại S3 thành diagnostic và loại khỏi endpoint so sánh chéo harness; amendment ghi lý do và denominators. Có thể thêm task mới với ngày hỏi tường minh cho cohort tương lai, không gọi đó là đã fix parity của S3 cũ.
- Inventory ghi observed/effective context; không tự đặt `native_now_pinned=true` vì đã thêm một câu ngày vào instruction.

**Kiểm:** request fixture ngày lệch bị parity audit bắt; fixture ngày chung đạt; summary loại S3 đúng khi policy diagnostic; không sửa clock timeout để làm đẹp latency. **Guard chung Phase 1:** không sửa gold trực tiếp hoặc nới tolerance để pass; mọi thay đổi task phải từ generator có diff.

## Phase 2 — Chốt phương pháp và bảo vệ holdout (#10, #13, #15)

**How this serves the primary goal:** Người đọc biết điểm số đo năng lực nào; lựa chọn task và holdout được chốt trước lần chạy dùng để kết luận.

### PR-04: gói quyết định và amendment dự thảo

| Quyết định | Khuyến nghị cụ thể | Phần phải ghi và kiểm |
|---|---|---|
| #10 — nhóm S | Chọn **(b)** cho cohort hiện tại: báo S riêng, không cộng primary L/C/M; chưa thêm arm để giữ ngân sách | Cả overall summary, paired tests, bảng chi phí và biểu đồ đều tách S. S1 đo hành vi sản phẩm gồm policy prompt; không quy chiến thắng cho harness loop. S2/S3 có bảng riêng và giới hạn tương ứng |
| #13 — bỏ 40 task | Giữ đúng 40 ID trong PRUNE hiện tại, khoá hash; không chạy lại thuật toán chọn | Ghi thời điểm sau or16, model nguồn, post-selection bias, điều kiện bảo vệ task có tên trong code; saturation không suy rộng sang model mới. Báo raw counts, accuracy, cost của 40 task từ or16 nếu có artifact |
| #15 — holdout | Giữ 58 cho cohort tiết kiệm hiện tại; không thêm C3 giữa cohort; báo CI rộng và thiếu C3 | Xác nhận lịch sử chạy ở mọi máy từ chủ nghiên cứu; điều tra `dev-stage/holdout` và `fin-mem-96x`. Holdout là tập giữ lại từ phát triển, không chứng nhận chưa từng có trong huấn luyện model |
| #15 — gold public | Chấp nhận và công khai giới hạn của 58 task đã public; hạn chế truy cập trong runtime | Xoá/ẩn bây giờ không xoá lịch sử công khai. Nếu cần holdout bí mật thật, tạo cohort mới với dữ liệu mới và review độc lập, không tái dùng cùng gold rồi gọi là bí mật |

- Đây là **khuyến nghị**, chưa thay cho quyết định của FinDaHuman. #10/#13/#15 chỉ đủ điều kiện đóng khi quyết định được ghi đúng như issue yêu cầu và đã phản ánh trong amendment/code. Không cần chặn các PR correctness độc lập trong khi chờ quyết định.
- Nếu chọn mở rộng holdout thay cho khuyến nghị: chốt số theo tầng, C3 mới, snapshot mới, seed và reviewer không tinh chỉnh OT; tính lại chi phí trước sinh/seal. Không dùng kết quả model để chọn task mới. Không cam kết CI hẹp khi chưa có phân tích power.
- `PRUNE.json` là nguồn ID canonical; validator chỉ đối chiếu ID/hash và composition. Lưu phần dữ liệu nguồn or16 đủ tái kiểm, không phụ thuộc thư mục results cá nhân đã gitignore. Script cũ chuyển thành công cụ lịch sử hoặc yêu cầu cờ tái sinh version mới; `--dry-run` phải không ghi đè receipt.
- Sửa diễn đạt “bỏ task bão hoà không gây lệch”: chỉ biết cả ba arm cùng đúng trên cohort or16; bỏ task làm thay đổi mẫu số và có thể thay đổi phân bố/difficulty ở cohort mới.
- Main hiện dự kiến **100 L + 40 C + 30 M + 30 S = 200**; holdout **36 L + 7 C + 7 M + 8 S = 58**. Giữ distinction 170/50 task LCM dùng primary và 30/8 task S báo riêng nếu quyết định trên được duyệt.

**Verification:** policy choices có người/ngày/source; một fixture nơi S đảo thứ hạng không được đổi primary LCM; sửa code/test không làm thay đổi PRUNE; danh mục exposure không bỏ mất task đã dùng. **Anti-pattern guards:** không dùng sự im lặng làm quyết định; không xem thiếu results trong git là chứng minh holdout chưa chạy; S4 tiếp tục để sau theo #22.

## Phase 3 — Kiểm soát chi phí và resume (#16)

**How this serves the primary goal:** Mỗi lượt gọi trả phí có ngân sách kiểm được; crash/resume hoặc clone mới không làm mất thông tin tiền đã dùng.

### PR-05: ngân sách offline trước, bằng chứng trả phí sau

1. **Resolve config một lần:** tạo đối tượng cấu hình hiệu lực sau merge CLI/config/provider_options; gateway, schedule, manifest và seal cùng dùng nó. Manifest ghi trần request/token/output/time thực, route/host, retry và tiền; không ghi defaults CLI nếu đã bị override.
2. **Thêm `--budget-usd` (flag mới):** bắt buộc cho paid route; dùng Decimal, từ chối giá trị thiếu/âm/NaN. Có allocation theo run và giới hạn key/project; ghi budget vào manifest bất biến.
3. **Request-level ledger:** giữ authoritative `usage.cost` nếu provider trả, request identity, route/generation ID, trạng thái và nguồn số đo. Tính cả retry/attempt, request lỗi có tính phí; không chỉ cộng trial thành công. `aggregate_usage` và report cost hiện chỉ có token/list price nên phải bổ sung đường measured cost, không đổi tên estimate thành actual.
4. **Bền vững và khoá:** spend journal ngoài workspace trial nhưng vẫn thuộc run/project được quản lý; ghi atomic/lock trước request. Resume đối chiếu request ID để không cộng trùng; pending request sau crash phải reconcile hoặc chặn trả phí. Không được khởi tạo lại từ 0 chỉ vì `results/` mất hay clone mới; key limit phía provider bảo vệ tổng nhiều máy.
5. **Kiểm trước request:** reserved upper bound của request tiếp theo phải nằm trong budget còn lại. Nếu không có cận giá/output đáng tin, chặn hoặc đặt cap chung được ghi vào amendment. Nếu chỉ kiểm cost sau response thì có thể vượt tiền bằng request đang chạy; không gọi đó là hard cap. Missing cost trên paid route đánh dấu unknown và chặn bước tiếp theo cho tới reconcile, không coi là 0.
6. **Hard limit ở key:** chủ key cấu hình số tiền cụ thể, giữ thông tin định danh không nhạy cảm/receipt; không ghi key vào artifact. Không giả định local ledger có thể cưỡng chế spend từ máy khác.
7. **Resume dưới seal:** mock provider chạy nửa cohort, ngắt giữa các điểm trước request/sau response/trước ghi trial; resume chỉ gọi phần chưa hoàn tất, không replay request đã có kết quả; manifest hoặc caps đổi phải bị từ chối. Pending không xác định được vẫn phải báo incomplete/unknown.
8. **Micro-pilot ≤10 trial:** chỉ thực hiện ở Phase 6 sau quyết định tháo vòng cổng. Dùng host đã pin, ghi $/trial, khoảng quan sát, token/cost coverage và dự tính phần còn lại có dự phòng. Đây là diagnostic, không dùng để chọn đề hoặc tuyên bố thắng.

**Verification:** zero budget không gửi request; boundary/exhaustion dừng đúng; retry bị tính; chi phí thiếu bị chặn; journal trùng không tính đôi; crash/resume không tạo trial/request trùng; hai process không đồng thời vượt reservation; caps manifest bằng caps gateway. **Anti-pattern guards:** không hard-code hệ số 2,8 làm hoá đơn; không coi quota request free là trần tiền paid; không mở holdout để thử resume.

### Tháo vòng phụ thuộc — quyết định phải ghi trước canary trả phí

- Tách #16 thành checkpoint **16A: code, tests offline, key cap sẵn sàng** và **16B: micro-pilot live receipt**; chưa đóng toàn issue khi mới xong 16A.
- Sửa cổng #21 thành yêu cầu 16A + #9–#15 đủ điều kiện + duyệt riêng canary/micro-pilot có cap, thay cho “#16 đóng rồi mới được canary”. Lần duyệt này ghi task IDs devsmoke, host ứng viên, số trial, request cap và USD cap.
- Gộp canary hai host trong tổng **≤10 trial micro-pilot**, không tạo thêm một pilot full. Có thể 3 task dev × 2 host = 6 trial OT và 4 trial parity, chốt chính xác trước khi gọi. Thiết kế này chỉ là kiểm vận hành, không xếp hạng host theo accuracy.
- Sau receipt: hoàn tất 16B, chọn host theo tiêu chí đã định, final amendment/seal, rồi mở cổng main ở #22. #18 nếu cần paired run trả phí cũng phải có allocation riêng và qua cổng tương ứng.
- Đây là đề xuất chỉnh dependency trong kế hoạch; hiện chưa sửa issue và chưa coi ngoại lệ là đã duyệt.

## Phase 4 — Tái lập, dọn legacy và CI (#1, #2, #19, #20)

**How this serves the primary goal:** Một máy khác kiểm được nghiên cứu và lỗi mới bị phát hiện trước khi tốn inference.

### PR-06: sửa fixture, locator và ranh giới phiên bản

- **#1:** chuyển fixture nhỏ, không nhạy cảm vào `tools/tests/fixtures/` của v4.6u hoặc vị trí track chung; kiểm `git ls-files` từ clone sạch. Nếu dùng ngoại lệ gitignore thì phải mở đúng các thư mục cha — thêm riêng ngoại lệ file dưới thư mục cha bị ignore chưa chắc có hiệu lực.
- Dùng path tương đối tính theo study ROOT hoặc `BENCH_BUN_BIN` trỏ file bất kỳ **nhưng SHA256 phải khớp receipt trusted**. Không cho env `BENCH_BUN_SHA256` thay hash trusted. Kiểm bytes thật trước execution; báo lỗi cài đặt rõ. Sửa ở những study liên quan, không thay config/hashes của nghiên cứu đã seal mà thiếu version mới.
- Đọc JSON UTF-8 tường minh ở đường chạy sửa; support matrix Linux/WSL trước. `fcntl` không chứng minh Windows được hỗ trợ; không hứa Windows native nếu chưa làm lock tương đương và test.
- **#2:** dùng `rg` lần theo mọi importer của `native_calculate.ts`/`analytics_calculate`; v4.7 không cần shared calculator thì loại module khỏi đường active và giữ implementation/tests lịch sử cùng runtime v4.6u phù hợp. Không mang calculator trở lại chỉ để test cũ xanh. Kiểm cả memory runner/schema.
- **#19:** tách test assumption lịch sử khỏi test thuộc tính chung. Update composition v4.7 bằng metadata `stratum` (S không bị tính là core), expectations shell/native memory thật. Giữ provenance, anti-leak, source-binding, resume, budget và parity tests trong active suite nếu hành vi còn được dùng.
- Full baseline/failure mapping trước và sau; không blanket skip hoặc xfail 54 test. Legacy không chạy mặc định phải có lý do, runtime pin và command/job riêng; test hỏng thật vẫn cần sửa.

### PR-07: toolchain, metadata, README và CI

- Pin OT SHA; Bun version + hash; OpenCode và DSH version/binary hash hoặc lock package tương ứng; dependency Python có lock/hashes; cài đặt không phụ thuộc thư mục home tác giả.
- Dockerfile đã pin **base** Python bằng digest nhưng final sandbox đang dùng image ID local: phân phối final image theo registry digest hoặc build có receipt kiểm lại. Khoá apt/dependency source để tuyên bố reproducible build có cơ sở; không chỉ đổi string local image ID thành digest bịa.
- Theo `isolated.finish`, inventory lấy route/provider/effort/tool policy/isolation từ cấu hình và runtime thực; giữ phân biệt “shell commands trong container” với “toàn bộ harness trong container”. Bỏ mô tả math-only/no-shell cũ ở README và comments active.
- README gốc chỉ rõ entrypoint v4.7 và lịch sử v2; README v4.7 có prerequisites, cài đặt pinned tools, build/pull sandbox, offline verify, devsmoke 3 task, artifact expected, troubleshooting, budgets/gates. Command không có key thật.
- CI không secret: pytest active suite; kiểm mỗi task đủ instruction/task.toml/payload/gold/oracle/grader; oracle tái tạo gold; grader pass đáp án chuẩn và fail mutation; schema/provenance/hash; PRUNE/composition; split gate, mock budget/resume, shell inventory. Job container smoke riêng nếu runtime yêu cầu Docker/Bun; pin action/tool versions thực khi tạo workflow.
- Legacy suite v4.6u riêng để chứng minh #1 và giữ lịch sử. Live model chỉ manual, không mỗi push; oracle local không cần gửi gold holdout tới provider.

**Verification:** clone ở thư mục khác, HOME sạch và không có local results/node_modules/toolchain tác giả; cài từ README rồi offline xanh; sai Bun hash bị chặn; pin mismatch bị preflight chặn; mock đủ 3 arm; smoke 3 task free ở Phase 5 khi có route sẵn. Một reviewer khác lặp lại command là bằng chứng đóng #20; nếu chưa có thì chỉ ghi “clean environment verified”, không thay cho xác nhận độc lập.

**Anti-pattern guards:** không xoá test để đạt xanh; không rewrite kết quả v4.6u theo runtime v4.7; không sửa hàng loạt bản frozen copy nếu không liên quan; không lộ credentials qua inventory/logs.

## Phase 5 — Lịch chạy tiết kiệm và đường kiểm chuẩn (#17, #18)

**How this serves the primary goal:** Giảm chi phí ở nhóm ít thông tin mà vẫn giữ so sánh cặp và phép thống kê nhất quán.

### PR-08: schedule theo tầng và kiểm ba bước

- **#17, đề xuất:** giữ toàn bộ task đã chốt; L chạy 1 lần/arm, C/M/S 2 lần/arm. Thêm cấu hình `runs_by_stratum` (mới) thay vì giảm mẫu tuỳ ý; nếu chọn stratified sampling thì chốt ID/seed/weight trước, không áp cả hai mà không tính mẫu số.
- Với composition hiện tại: main = `(100×1 + 40×2 + 30×2 + 30×2)×3 = 900 trial` thay vì 1.200. Holdout nếu cùng policy = `(36×1 + 7×2 + 7×2 + 8×2)×3 = 240` thay vì 348. Đây là số trial, **không phải ước lượng USD/thời gian**. Holdout 1 cohort vẫn có thể chứa 2 replicate/task; “một lần mở” không đồng nghĩa 1 replicate.
- Materialize schedule thành danh sách `(task,arm,replicate)` trong manifest trước chạy; arm order cân bằng và seed cố định. Resume nhận đúng schedule đã seal, không suy lại từ config mới.
- Báo task-weighted accuracy hoặc endpoint đã đăng ký: tính mean replicate của từng task trước khi tổng hợp; không để task có 2 lượt nặng gấp đôi L chỉ vì có nhiều row. Bootstrap theo task, giữ cặp arm và tầng; stable 2/2 chỉ tính trên task đủ hai lượt, L không được gọi stable 2/2. Báo denominator theo tầng, incomplete và payload-cluster sensitivity.
- Test schedule đủ/không trùng/cân bằng, cùng seed ra cùng lịch, config/seed/số lượt đổi làm resume fail; test thống kê trên dữ liệu tổng hợp biết trước kết quả.
- **#18:** tạo một entrypoint kiểm rẻ (tên đề xuất `tools/check_change.py`) có chế độ offline/free/paired và dry-run in task list, trial cap, request cap, estimated USD, không khởi động provider khi chỉ dry-run.
- Bước 1 offline/mock luôn trước. Bước 2 free: 3 task devsmoke phủ lookup/compute/memory, thêm S case khi sửa S; free chỉ kiểm vận hành, không suy chất lượng DeepSeek từ Nemotron. Route NVIDIA chỉ gọi “free” nếu entitlement/key thực đã xác minh.
- Bước 3 paired: dev set khoảng 40 task có lineage từ main đã exposure, không holdout. Chốt selection bằng loại lỗi/kỹ năng cần kiểm, không theo arm thắng. Mỗi thay đổi nhỏ chạy subset ảnh hưởng; báo đúng selection bias, không thay thế main.
- Lần đầu phục vụ OT#268 tối đa **60 trial tổng cả bản cũ và mới**, không phải 60 cặp. Ví dụ 10 task × 3 arm × 2 versions × 1 run = 60; hoặc thiết kế OT-only phù hợp mục tiêu, chốt trước. Runtime cũ/mới cần workspace/manifest riêng; model/host/budget/payload giống nhau. Không trộn wire protocol khác phiên bản rồi gọi là so sánh sạch.
- Sau đó chỉ rerun ca thay đổi khi diagnostic; lần confirmatory vẫn chạy nguyên lịch. Ghi request thực, measured/estimated cost và coverage, không tuyên bố tiết kiệm từ số trial đơn thuần.

**Verification:** offline gate và schedule/statistics suite xanh; paid mode bị chặn khi chưa allocation; cap tính cả retry và memory turn; request/cost receipts đủ. **Anti-pattern guards:** không gọi `--split main` với dev bypass; không dùng paired dev để kết luận chung; không chạy 40 task × mọi arm × hai versions khi cap 60 không đủ.

## Phase 6 — Runtime pin, canary, amendment và seal (#21)

**How this serves the primary goal:** Kết quả chính gắn một cấu hình đã kiểm chứng và không thể đổi ngầm giữa chừng.

### PR-09: chuẩn bị offline rồi qua cổng live có giới hạn

1. Pin đúng một commit OT main đã review; đọc lại API thực trước đồng bộ. Chép prompts baseline nguyên văn và SHA256SUMS; kiểm `initRuntime`, schema generator, shell/read_result và memory adapter trên commit đó.
2. Set `OPENTRADING_PYTHON=python3` trong env runner trước khởi tạo OT; kiểm cả single-turn và memory, không chỉ shell child. Test inventory/prompt khai báo Python khớp sandbox thực có Python; không phụ thuộc probe trên host ngoài sandbox.
3. Theo pattern `v45_gate`, triển khai gate phân phiên bản hoặc module v47 riêng. Không sửa hard-code v4.6 thành v4.7 rồi phá suite frozen. Seal schedule chứa main và holdout đã dự định nhưng holdout vẫn chưa được phép inference; cấp quyền mở là bước riêng.
4. Sửa vòng điều kiện `open_holdout`/`authorize_run`: mở cohort lần đầu `resume=False` tạo receipt đúng một lần; resume cohort đó `resume=True` hợp lệ; run mới với receipt cũ hoặc mở lại không hợp lệ. `holdout-go.json` hiện chỉ được kiểm tồn tại: bổ sung kiểm nội dung/hash, cohort ID, seal ID và quyết định duyệt được tham chiếu, không coi file rỗng là quyền mở. Kiểm schedule hash/config/code/runtime/task/toolchain/budget và khoá đồng thời.
5. Chuẩn bị amendment gồm task IDs/hash, PRUNE/exposure, metric LCM và S, policy S3, holdout scope/public-gold, model/route/host, runs-by-stratum, all caps, cost source, retries/exclusions, inference timing, thống kê, allocation main/holdout/reserve. Chốt tiêu chí chọn host trước canary.
6. Sau #9–#15 và checkpoint 16A + các PR hạ tầng đạt: lấy duyệt cụ thể cho ngoại lệ canary/micro-pilot như Phase 3. Kiểm 2 host ứng viên bằng dev task; pin model ID, host thực, tắt fallback; lỗi host/model drift phải fail preflight. Không pin theo nhãn route nếu response thật đi nơi khác.
7. Đủ receipt ≤10 trial, budget và resume proof thì hoàn tất #16; cập nhật amendment cuối, có comment duyệt seal theo #21, tạo receipt seal. Live validation không làm thay đổi task/gold. Nếu đổi bất cứ thành phần được seal, phát hành version/receipt mới trước main.

**Verification:** mock đúng study_version v4.7; tamper code/config/runtime/tool schema/prompt/task/caps/schedule bị từ chối; all 3 arms inventory đúng; shell result journal ↔ tool calls khớp; resume dưới seal không thêm trial; holdout chỉ mở đúng cohort và bị chặn lúc dev; free preflight đạt. **Anti-pattern guards:** không gọi paid canary trước ngoại lệ được duyệt; không tạo receipt seal bằng tay; không dùng seal v4.6u để chứng nhận v4.7.

## Phase 7 — Main, một cohort holdout và báo cáo (#22)

**How this serves the primary goal:** Nghiên cứu chạy trong ngân sách và giữ được giá trị xác nhận của tập giữ lại.

### PR-10: allocation thực thi và kết quả

- Chỉ bắt đầu sau #21 hoàn tất và PR amendment/allocation được FinDaHuman duyệt như issue yêu cầu. Không suy authorization trả phí từ việc đã duyệt kế hoạch code.
- Allocation tách **main / holdout / reserve** bằng số USD cụ thể, số request/trial và khóa config. Dùng measured cost micro-pilot để tính khả thi; nếu không đủ thì sửa allocation/phạm vi trước main và seal lại, không giảm task sau khi xem kết quả.
- Chạy main theo lịch; giữ failure/DNF và chi phí mọi attempt. Chỉ retry lỗi hạ tầng theo rule đã đăng ký, không chạy lại vì đáp án sai. Host drift hoặc cost coverage thiếu làm dừng để điều tra.
- Báo main: L/C/M primary, S riêng, memory OT–DSH và khả năng có/không của OpenCode, latency/cost/completeness, CI theo task và giới hạn exposure. Không tinh chỉnh prompt/gold sau main rồi dùng holdout để so như cùng phiên bản.
- Sau khi FinDaHuman xem main và cho phép: mở `allowed_inference_splits` qua amendment có quản lý hash. Tốt nhất gate đọc quyền mở riêng ngoài scientific config đã seal; nếu bắt buộc đổi config thì phát hành amendment/receipt kế thừa có liên kết, giữ nguyên main cohort/hash và định nghĩa so sánh, không làm seal cũ mất nghĩa.
- Mở holdout đúng một cohort bằng receipt; resume chỉ phần chưa hoàn tất của cohort đó. Dự phòng dùng lỗi hạ tầng có evidence, không tạo cohort holdout mới. Nếu exposure cũ không xác minh được thì báo trạng thái và hạn chế, không gắn nhãn “unseen” vô điều kiện.
- Đóng #22 sau artifact/report/receipts và phạm vi được duyệt hoàn tất. Nếu chưa mở holdout hoặc chưa có duyệt thì giữ issue mở, ghi checkpoint thật.

**Verification:** dry-run allocation cộng đúng; không vượt key/local cap; receipt mở lần hai fail; run ID khác không resume bằng seal cũ; joined report đủ paired task denominator và provenance; measured spend đối chiếu provider không dùng list-price thay thế. **Anti-pattern guards:** không xoá receipt để chạy lại, không loại failed trial khỏi mẫu số, không dùng reserve “chạy lại cho đẹp”, không thêm S4 trong cohort đã chốt.

## Phase 8 — Verification cuối và hoàn tất tracker (#23)

**How this serves the primary goal:** Không còn issue bị quên hoặc được đóng bằng một thay đổi chỉ sửa triệu chứng.

- Đối chiếu 17 dòng trong bảng coverage với PR, decision, test receipt và live receipt tương ứng. Issue code chỉ đóng sau merge + kiểm đúng symptom; issue quyết định chỉ đóng sau recorded decision và enforcement. #2 chờ cả phần seal được yêu cầu; #16/#18 cần receipt thực, không chỉ script.
- Chạy active suite trên clone sạch, legacy targeted suite #1, mock gate/resume/budget, deterministic task verifier và artifact audits. Không inference thêm để “kiểm cho chắc” khi cohort đã xong.
- Kiểm tài liệu/API thực khớp code; tìm các import calculator chết, metadata provider/no-shell/math-only lỗi thời trong đường active; giữ mô tả lịch sử ở archive có nhãn rõ.
- Báo số test fail baseline → final, task/gold/hash thay đổi, tổng request, measured cost coverage, lần mở holdout và các quyết định chưa hoàn tất. Không ghi “mọi issue đã fix” khi còn approval/lần chạy chưa xảy ra.
- Khi toàn bộ phạm vi thực sự hoàn tất mới đóng #23; nếu lựa chọn hoãn được duyệt, tracker liên kết issue còn mở/phạm vi cohort sau thay vì đánh dấu đã sửa.

**Definition of done:** main/holdout không bypass; rubric S chống các exploit đã nêu; series theo ngày; policy decisions ghi đủ; ngân sách và resume bền vững; clone khác tái lập được; CI xanh; seal v4.7 bảo vệ đúng scientific config; live cohorts/report đúng approval và allocation.

## Thứ tự PR, phụ thuộc và ước lượng công

| PR | Nội dung | Phụ thuộc chính | Ước lượng ngày công kỹ thuật |
|---|---|---|---|
| PR-01 | Dev split gate + exposure ledger | Phase 0 | 0,5–1 |
| PR-02 | S contract/grader/corpus/regeneration | Phase 0 | 1–2 |
| PR-03 | Series dates + clock audit/policy enforcement | Phase 0; gate PR-01 cho live smoke | 1–2 |
| PR-04 | Decisions #10/#13/#15, PRUNE, amendment draft | Findings PR-02/03; có thể soạn sớm | 0,5–1 + thời gian quyết định |
| PR-05 | Durable budget, actual caps, resume proofs | Phase 0 | 1,5–3 |
| PR-06 | Portable fixture/Bun + active/legacy tests | Baseline; tích hợp PR-02/03 expectations | 1–2 |
| PR-07 | Toolchain/image pin, inventory, README, CI | PR-06 và các correctness PR | 1–2 |
| PR-08 | Runs-by-stratum + statistics + cheap-check CLI | PR-01/04/05; live sau cổng | 1–2 |
| PR-09 | Runtime, v47 gate/holdout receipts, canary, seal | PR-01…08 + quyết định/duyệt cần thiết | 1–2 + runtime/model wait |
| PR-10 | Allocation, main/holdout reports | PR-09, #22 approval, budget cụ thể | 0,5–1,5 + thời gian inference |

Tổng dự kiến khoảng **9–18,5 ngày công**, không phải cam kết lịch; không cộng thời gian chờ người duyệt/provider hay inference dài. Có thể làm PR-01/02/03 và chuẩn bị PR-05/06 độc lập nếu triển khai có nhiều người; không gộp thay đổi statistical design vào PR grader để reviewer khó phân biệt.

Đường phụ thuộc chính: correctness → quyết định phương pháp → budget/repro/schedule đạt → ngoại lệ canary giới hạn → actual receipts + amendment/seal → main → duyệt kết quả → một cohort holdout → report/tracker. Các PR code trước cổng đều kiểm offline trước; không cần gọi paid model để bắt đầu sửa.

## Tài liệu nguồn và giới hạn của lượt review

- Issues và comment: liên kết trực tiếp ở bảng coverage; comment trạng thái #2: [ghi nhận shell đã chuyển và import chết còn lại](https://github.com/DoanDuyLong212/opentrading-benchmark/issues/2#issuecomment-6914556470).
- [S generator](https://github.com/DoanDuyLong212/opentrading-benchmark/blob/4bbfd385008440acb0cca085cddb751decd06ee5/experiments/finance-v47-study/tools/build_safety_stratum_20261116.py), [public validator](https://github.com/DoanDuyLong212/opentrading-benchmark/blob/4bbfd385008440acb0cca085cddb751decd06ee5/experiments/finance-v47-study/tools/public_response_contract.py), [series generator + oracle library](https://github.com/DoanDuyLong212/opentrading-benchmark/blob/4bbfd385008440acb0cca085cddb751decd06ee5/experiments/finance-v47-study/tools/build_compute_series_20261116.py).
- [PRUNE receipt](https://github.com/DoanDuyLong212/opentrading-benchmark/blob/4bbfd385008440acb0cca085cddb751decd06ee5/experiments/finance-v47-study/audits/taskset-revision-2026-11-16/PRUNE.json), [isolated runner](https://github.com/DoanDuyLong212/opentrading-benchmark/blob/4bbfd385008440acb0cca085cddb751decd06ee5/experiments/finance-v47-study/tools/runners/isolated.py), [study design](https://github.com/DoanDuyLong212/opentrading-benchmark/blob/4bbfd385008440acb0cca085cddb751decd06ee5/plans/2026-11-15-v47-study-design.md).
- Đã thực thi probe validator thuần Python và kiểm lịch ngày payload 10 task; không thực thi runtime remote hay xác minh full regression count 54; chưa đọc được provider requests của tất cả máy, chưa xác nhận holdout chưa từng inference, chưa kiểm live giá/route/key balance. Các mục này là nhiệm vụ có bằng chứng cần thu trong plan, không phải kết luận đã đạt.

