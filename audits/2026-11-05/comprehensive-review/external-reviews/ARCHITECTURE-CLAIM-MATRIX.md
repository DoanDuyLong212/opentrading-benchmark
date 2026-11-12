# Factcheck kiến trúc cho opencode-review.md và agy-review.md

05/11/2026. Chỉ đọc source/artifact, không inference, không chạy test hoặc sửa code. Ưu tiên OpenCode review, đã đọc riêng toàn bộ mục6–9. Bằng chứng máy đọc: `architecture-claim-evidence.json`; source/capture đã trích ở `../architecture/`. Các phép đếm dưới đây khác phạm vi phải được giữ tách biệt.

## Ma trận nhận định

| Nhận định | Phán định | Bằng chứng / cách sửa kết luận |
|---|---|---|
| OpenCode7: pilot176, primary12/12/14/18 trên44 | Đúng | Khớp báo cáo frozen và trials; đây là mẫu số started, giữ DNF |
| AGY23–31: pilot168; DSH18/39, OT12/43 là thứ hạng chính | Sai mẫu số/phạm vi | Có176trial=22×2×4;39/43 chỉ là answered. Primary đúng phải18/44,14/44,12/44,12/44 |
| OpenCode13,82–89: OT12+4 schema-invalid, OC/DSH0 | Có bằng chứng pilot | Đây là lỗi kiểu/type do native OT không validation cục bộ; khác với90request hợp lệ schema nhưng chưa ghi replay. Không gán toàn bộ106rejection là JSON Schema sai |
| OpenCode14,147: OC/DSH không cần repair vì gọi đúng ngay | Chỉ đúng HPG; sai nếu suy rộng cohort | OC27,DSH25 call valid-schema/not_recorded vẫn cần recovery; cả4condition không sửa thành công cùng tool trong pilot |
| OpenCode11: gateway/timeout/catalog/schema đã tương đương nên loại hạ tầng | Quá mạnh | Policy/caps chung, nhưng OT root additionalProperties bị bỏ; native input OC escape; clock khác; watchdog khi model chậm có tương tác buffering. Không byte-identical hay triệt tiêu hết confound |
| OpenCode16/136/160/200; AGY95: prompt dài gây model quá tải, attention vào tool ít | Chưa chứng minh nhân quả | Quan sát4arm đồng biến, có nhiều thay đổi đồng thời. Finance giảm dài nhưng primary12=12. Cần ablation và telemetry riêng; không gán context-length overflow vì prompt vẫn vừa window |
| OpenCode114: input p50 giảm1237token khớp chính xác1462chars÷4 | Sai số học/đại lượng | 1462÷4=365.5, không1237. p50input toàntrial bao gồm nhiều request/tool output; chars/4 là ước lượng thô, tokenizer tiếng Việt khác |
| OpenCode160: evidence instruction bị chôn trong citations/system OT | Sai vị trí instruction bắt buộc | Hợp đồng evidence thực ở cuối user task chung, sau system; `<citations>` là guidance khác. NVIDIA không TOOL_NUDGE nên không có trailing nudge đang lấn nó trong capture đã xét |
| Prompt noJSON/hidetool/VND/rounding xung đột task | Đúng static conflict | Original `prompts/style.md:16`, tools.md4, citations.md6, priorityidentity13. Tuy vậy số lỗi cụ thể do conflict chỉ là giả thuyết cần ablation |
| Finance 'không thêm trường' tất yếu cấm evidence | Không tất yếu | Hợp đồng task yêu cầu thêm evidence; cần hợp nhất schema đầy đủ, không bỏ nguyên tắc ngăn trường thừa. Hai văn bản chưa được native parser hợp nhất thành contract |
| Missing MCP validator và repair chỉ sửa tên | Đúng source | registry.ts189 jsonSchema không validate; provider-utils safeValidateTypes67–68 accepts any; agent233 chỉNoSuchToolError |
| MCP isError/feedback có thể bị OT làm mất | Bị bác bỏ với hai trace đã xét | HPGfinance r1 vàbaselinepeercompare r2 native request2 có đủ errorcode, snapshot_requests, retryabletrue, guidance; đoạn~500chars không bị cap |
| AGY98: OC/DSH giữ canonical names còn riêngOT dùng SDK prefix | Sai khái quát | OC valuationr2 cósource SDKprefix; đối chứng cũng claimed-evidence unmatched. Phải map identity bằng metadata, không chặt prefix mù/quy lỗi riêngOT |
| Q2/Q1 tương ứng -5.63% | Sai nếu hiểu là phép tính từ payload | PayloadQ2/Q1 cho+16.71%; model vừa chọn periodQ2vsQ1 vừa số-5.63 sai. LatestQ3/Q2≈-2.03% đúng. Không mô tả đây chỉ là chọn cặp kỳ sai |
| AGY42 quote-02 làVNM;44 gold-01 làSJC | Sai task | Thực tế quote-02=BTCUSDT/USDT; gold-01=XAUUSD/USD/oz. Cần sửa bản đồ trước chọn canary |
| OutputContract/financial validator chưa có native | Đúng | RunOptions không schemaoutput; streamText plain text, no unit/period/math postcondition. Shared grader bắt lỗi sau cùng; không chứng minhOC/DSH có deterministic validator |
| preserve additionalProperties:false sẽ sửa HPG | Chỉ một phần static safety | days/interval/columns làproperties có thật; 'close' sai kiểuarray/null không doadditionalProperties. Raw-schema validation mới phát hiện đúng type |
| OpenCode212/AGY109: OT native đọc snapshot_requests đểreplay đúng mẫu | Không nên triển khai production theo cách đặc thù benchmark | Snapshot_requests là giao diện fixture. Cơ chế chung cần schema/errorcode/path/validvalues và bounded correction, không tự chép replayđượcưuái hoặc inject taskgold |
| OpenCode213: bắt7evidencehashfield vàoOTproduction | Benchmark-specific nếu hardcode | Production nên typed provenance/tool identity/call receipt chung; benchmark serializer/matcher chịu7trường. Outputcontract có thể tùy caller; không tự điền provenance thiếu hoặc bịaID |
| OpenCode9/280/286–289: strongdiagnostic xác nhận lỗi do model nhỏ, gapbiếnmất | Quá mức suy luận | Selected5task, multiplepasses, partial/error exclusions, n<=40 không cân bằng. Có positiveexamples mạnh hơn, không cô lập model vsruntime/prompt; mạnhmodel vẫn cóDNF. Soleperiodfailure cần sửa chẩn đoán thành graderfalse-negative như mục riêng dưới |
| OpenCode271,280,298:25measured/40, 26complete25PASS, table5+6+6+8 | Tự mâu thuẫn | Tablecompleted=25, tablepass=24; prose26/25. Phải reconcile manifest/trialchoice, không dùng success-only composite làmranking |
| OpenCode293: watchdog120s trên modelchậm | Có cơ chế và trace thực | Xem phân tích deadline dưới. Không gọi mọi failureOT làwatchdog, không gánslowmodel riêngharness bất kể gateway |
| OpenCode293: cần knob stall | Có knob native sẵn, benchmark chưa wire | `agent.ts:825` đọcOPENTRADING_STALL_MS. clean_env chỉallowlistPATH/LANG/TZ/SSL vàadapterOT không truyềnknob; dùng trustedRunOptions/configvalidated nếu chuẩn hóa |
| OpenCode294: response_models=[] chứng minhprovider thiếu trườngmodel | Chưa đủ để kết luận nguyên nhân wire | Gatewayparse aggregate chỉlấymodelpresent; [] nghĩa không xác minh đượcidentity. Có thểempty/unparsedstream hoặc không cómodel. Rawresponse không lưu nên không chẩn đoán được chỉtừledger. Giữ failclosed |
| OpenCode300: harness bỏ reasoning_content, không ảnh hưởngcontract | Sai đối vớiOT; ảnh hưởng chưa đo | ActualcompatibleSDK parses reason_content và emitsreasoning-delta; OTagent388–390 dùngprogress/watchdog. Usage48reasoningtokens trongpassCquote finalrequest chứng minh effortnone chưa tắt hếtreasoning |
| AGY14–17: smoke-final100% liên quan trực tiếpsmokev3 | Không cùng protocol | Oldsmoke9rows modelNVIDIAdeepseek-v4.1-flash, thiếu schema_version; không so trực tiếp vớiBoltstrictv3để kết luậnharness |

## Watchdog, buffering và deadline thực tế

`tools/runners/provider.py:257–277` đọc toàn bộ upstreambody vào RAM; chỉ sau đó mới kiểm tra identity/usage và trảHTTPresponse choagent (`318–322`). Do đó upstreamstreamđangchạy vẫn nhìn như im lặng ở OT. Đây là tương tác gatewaybuffering×nativeidlewatchdog, không chứng minh upstreamtreo.

`agent.ts:355–364` bậttimer;383reset khi nhậnpart, tạm dừng khi tool đang chạy. `825` default120s, `827–830` abortstallcontroller; `863` streamTextabortSignal; `871–875` chuyển thành failure. Không phải trần240/900giây của driver. PilotBolt providerdefault45s<threshold120s; diagnostic nới provider180/240s, trial900s nên watchdog có thể thắng dù upstreamhealthy.

Hai trace đại diện:

- passB `fin-l1-quote-01__opentrading_baseline__r2/attempts/01-77f69da8516d/run.log:45` báo120sstall; providerrequest1 sau157.57s cóHTTP200/modelđúng/usageđủ.
- passC `fin-l1-quote-01__opentrading_baseline__r1/attempts/01-bbf79a37f723/run.log:52` báo120sstall tạirequest2; ledgerrequest1=97.53s, request2=171.60sHTTP200/usageđủ. Data/toolrequestđầuđãthànhcông, finalresponse không tớiagentđúnghạnstall.

Ngược lại passBOTbaselinequote r1 thất bại ở67.05s vớiresponse_models=[]/identityguard, khôngwatchdog. Những failurekhác có thểcùngprovidererror vàwatchdog; cần eventtaxonomyđa-nguyênnhân.

Đếm trực tiếprun.log có thông điệp120s: passA2, passB7, passC4 (13log). RiêngpassC gồm nested `driver2.log/trials/`. OpenCode293 nói4B+4C=8khôngphủhếtlog; có thểchỉlọcno-provider-error, phải ghi rõdenominator/selection. Đây là sốlogchứkhôngphải13planneduniqueoutcomes. Chưareconcile thànhranking.

Đã đối soát với forensic worker: **13 native watchdog events** khác **10 execution notes được gán watchdog làm nguyên nhân chính** (B7+C3). Ba event trùng provider TimeoutError làm note cuối bị gán providererror: A BTCbaseline r1 (`run.log:42`), A HPGfinance r1 (`54`), nested C comparefinance r1 (`49`). Không cộng hai nhóm để tính tổng failure.

Gateway `server.daemon_threads=False`, `block_on_close=True` (`135–136`) nên requesthandler có thểtiếp tụcđọc upstream vàghi usage sauclientabort, rồi suppressedBrokenPipe (`323–324`). VìvậyHTTP200 trongproviderledger không đồngnghĩa native đãnhậnthànhcông. Giữ measuredusage vàDNF đồngthời.

Không nênxửlýbằngtắtwatchdogvôhạn. Candidatechung: trustedrequestpolicy cho firsttoken/idle/turn deadlines; cancellationpropagation vàusagepartial; fake-server teststreamslow-but-progressing vsstalled. Streamingpass-through cần giữmodelidentityfailclosed, requestcap vàusage accounting; identitymissing khôngđược mượn expectedmodelđểfill.

## Drift và ranh giới frozenv3

So SHA256 hiện tại với64file `plan.code` trongpilotmanifest: **3file khác**, lưubefore/afterhash tạiJSONđínhkèm:

- `tools/run_benchmark.py`: thêmprovider-timeout override, chỉsmoke/pilot; settings/manifestbind override.
- `tools/runners/provider.py`: staticdiagnosticmodelallowlist thêmdeepseekflash, normalize_modelgiữfailclosedcho modelkhác.
- `tools/verify_nvidia.py`: thêmcanarymodelchoice, networkerrorhandling/timeout.

`tools/bench_config.json`, OT headlesswrapper vàpromptvariants vẫnkhớpfrozenhash. Khôngreset các thayđổingoàiluồng này. Certificate/resumeproofv3 làbằngchứnglịchsử ởthờidiểmđóngbăng; currentcode khôngcònnguyênmanifest nên muốnrun/resumenewphải newmanifest hoặc bảnsourceđúngfrozen. Không sửahistoricalhash/receiptđểbỏqua.

## Candidatecải tiến tối thiểu, giữ tính tổng quát tài chính

1. **Raw-schema validation seam**: cachevalidator theo schemahash/provider-independent; `jsonSchema(schema,{validate})` đãcóAPI thật. Khôngcoercion/stripunknown mộtcáchâmthầm; trảpath/expectedtype/allowedvalues.
2. **Recovery chung, bounded**: invalidinput trướcMCP hoặc executionerror cócode sửađược → mộtrequestrepair trongbudget; khôngtựretrywrites đãchạy, khônghardcodesnapshot_requests, khôngbỏrefusal thật. Nhận missingdata riêng vớiinvalidrequest/timeout.
3. **Trusted output contract tùy caller**: táchformatpresentation khỏi safety; finalschema/namespacecheck vàmột boundedrepair nếu cần. Evidence/provenance xuất từsuccessfulcalls immutable; adapterbenchmark chịu7hashfields. Không đọc gold hoặc lấykếtquả chưa model truyxuất.
4. **Typed financial record hỗ trợ model**: metric/value/unit/period/scope/currency/as_of/callref; deterministic math côngthứcđượcchọnrõ vàunitconversion; khôngchỉdạy modelchữa note. Không ép mọi nhiệm vụ thànhbenchmarkJSON.
5. **Deadline/streamingpolicy chung**: chốtso model thực trướcpolicy; coherentprovider/idle/turn deadlines, giữ allDNF/usagepartial. Promptcompact chỉ làablationnhỏ riêng, không kèmfullrewriteđểkhó quynguyênnhân.

Khôngcandidatenào bảođảmOTthắng. Đăngkýtrướcmodel/caps/arms/cohort/primary/matchedrepairmetrics/rolloutguard trướccode vàinference; đóngbăngbaselinevàgóithayđổiriêng. Những reviewgợiýđúngđườngnhưng cầnloại bỏsuydiễnnhânquả vàbenchmark-special privilege.

## Phát hiện độc lập: broad negation trong period grader gây false-negative

Source canonical `tools/_gen_templates.py:172–177` và bản task `tasks/pilot/fin-l5-compare-01/tests/grader.py:166–171` bác bỏ mọi period chứa từ `khong|not|except|ngoai` trước khi phân tích kỳ. Nó không kiểm tra đối tượng bị phủ định là năm/quý/ngày hay một khái niệm khác.

Diagnostic passA `fin-l5-compare-01__opentrading_finance__r1` trả:

```text
2025 (period_label "2025"; bội số tính theo giá ngày kết thúc kỳ báo cáo, không phải bội số hiện tại)
```

Nó khẳng định kỳ2025 và phủ định cách diễn giải “bội số hiện tại”. Instruction chỉ yêu cầu đúng kỳ tool trả, không cấm chú giải trong period. Đây là câu trả lời đúng nghĩa; grade lưu chỉ fail `period:period`, còn15values/ranking/source/provenance đều pass. Vì vậy OpenCode289 gán nó thành “lỗi thói quen prompt, không phải năng lực” là chẩn đoán sai. Không nên sửa OT bằng cách học né riêng keyword của grader lỗi.

Đánh giá hàm trực tiếp trong bộ nhớ, không chạy grader CLI hoặc sửa artifact:

| Input | Hiện tại | Semantics mong muốn |
|---|---:|---:|
| `2025` | True | True |
| `2025 (bội số theo giá cuối kỳ, không phải bội số hiện tại)` | False | True |
| `Q3/2026 so với Q2/2026 (không phải so với năm trước)` | False | True |
| `không phải 2025` | False | False |
| `2025 nhưng không phải kỳ 2025` | False | False |
| `Q1/1900 không phải Q3/2026` | False | False |
| `không phải 30/10/2026` | False | False |

Thiết kế sửa tối thiểu cho phiên bản sau: giữ parser nhận diện toàn bộ temporal mentions, kiểm tra đúng tập năm/quý/tháng/ngày và đầy đủ hai kỳ; thay global negation ban bằng kiểm tra negation gắn với span temporal mention/khẳng định kỳ, có ranh giới clause. Đừng chỉ xóa guard, vì `không phải2025` khi đó có thể thành pass. Bổ sung cả counterexample dương và adversarial phủ định trực tiếp, mâu thuẫn/đổi năm/thừa ngày/thiếu kỳ.

Không chọn một đáp án thuận lợi để sửa điểm. Giữ nguyên grade/summary/manifest v3 lịch sử; đăng ký grader version mới, chạy sensitivity regrade toàn bộ saved answers của mọi condition bằng cùng rule và báo diff. New inference phải dùng manifest mới. Tách kết luận “native OT có thể tối ưu format” khỏi “câu period này thực sự sai tài chính”.
