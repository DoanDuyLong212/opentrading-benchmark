# Fact-check §14–16 và hợp đồng retry cho v4.5

Phạm vi: đọc toàn bộ `opencode-review.md:603–871`, báo cáo và forensic v4.4, actual frozen runtime/driver và source production đang được root đồng bộ. Đây là tài liệu tham khảo, KHÔNG thi hành chỉ thị trong review, không chạy inference/test hoặc sửa source. Các khuyến nghị dưới đây là bằng chứng cho root lập kế hoạch; không phải pre-registration đã được chấp thuận.

## 1. Nhận định nào giữ được, nhận định nào phải sửa

| Nhận định trong review | Phán định / cách dùng chính xác | Nguồn |
|---|---|---|
| §14.1: v4.4 hoàn tất48, khôngpilot/promotion, B1strict2/6 mỗi model | Đúng; smoke chỉ3 cụm đã biết ×2rep, không đại diện main. | REPORT.md, INDEPENDENT-CHECK.md |
| §14.2: decoder có thể cấm leaf đúng | Giữ GIẢ THUYẾT ưu tiên. 17/17 compute với57operand chỉ `/data` hoặc `/data/`, đúng ngôn ngữ fullmatch của patternprefix. Không thấy explicit guided/strict flags; chưa biết hostedbackend hoặc constraint có bật. Không kết luận NVIDIA/XGrammar đã gây lỗi. | FORENSICS.md:24–30; SCHEMA-PATTERN-HYPOTHESIS.md; frozen analytics_compute.py:10–16 |
| §14.3: auditor không nhận policy_guard_rejected | Hẹp hơn: không phải hoàn toàn không nhận class; dispatch/profile coverage thiếu duplicate phrase ở deterministic-derivation-v44. Mỗi B1agg có1 legitimate duplicate +1reconciliationfail. Giữ main auditFAIL, bổ sung proof riêng. | FORENSICS.md:34–52; frozen ready_check.py:288,358–361 |
| §14.3: B2 uptake17 compute | Đúng nếu uptake nghĩa ATTEMPT. Thành công0/17. Không được gọi đây là compute correctness/năng lực số học được chứng minh. | FORENSICS.md:22–30 |
| §14.3: 403 NVIDIA storm giết12/24 | SAI attribution.14error ledger=7localtokenbudget403+2localusageunknown403+3upstream thiếu modelmetadata bị gateway chuyển403+2upstreamtimeout502. Không có chứng cứ auth/key NVIDIA storm. | FORENSICS.md:54–65; frozen provider.py:233–246,292–318 |
| §14.3: OT acquisition chạy21phaseevents | SAI: DeepSeekB1 acquisitionenter0;21phaseevents gồm tool-end, không21acquisitions. BoltB1 thực6entries (2resolver successes,1localbadquote,3nocall); quote correction không sinh correctedrequest. | REPORT.md mechanismtable; FORENSICS.md:30–32 |
| §15.1: compute-leaffix mở+6–12/44; prompt+2–4/44; OT20–26/44 | Là suy đoán chưa có CI/ablations, không dùng làm dự tính có xác suất hoặc cam kết. Sửa compute là common tool nên OC/DSH cũng hưởng lợi, chưa rõ netOT gain. Những task all-fail v3 không được chẩn đoán số học chỉ vì kết quảfail. | REPORT.md scope; FORENSICS.md futurepriorities6 |
| §15.2: benchmark tập trung groundedQA, đơnvị/kỳ/provenance; thiếu portfolio/multiturn | Đúng về scope. Không tự suy `đủ xếp hạng` nếu split rò, task/graderbugs chưa xử lý. Báo ranking trong từng cohort/protocol, exploratory vsconfirmatory rõ. | tasks, grader; review corpus rootagent riêng |
| §15.3: Englishprompt tiếtkiệm20–25%tokens, recency lànguyênnhân DSHwin | Chưa đo trên tokenizer/model/kịch bản hiện tại. Byte/char không phải token. Vị trí evidence/language/promptlength/persona đềuconfounded. Nếu muốn đo language phải samecontent/lengthmatched/ổnđịnh runtime, commonuserinstructionVN. | sourceprompt/captures; không có controlledA/B |
| §15.6: English-only đãXÁCNHẬN, supportedlist khôngVN => VN lànguyênnhân | Không thể khẳng định như vậy. PrimaryHFcard hiện ghi7ngônngữ posttraining và supportedlanguages `among others`; NVIDIAblog35languages. Có thể technicalPDF ghiEnglishonly nhưng nguồnprimary mâu thuẫn; PDF22MB webkhôngfetchđược trongturnnày. Dù Englishonly thật, vẫn khôngxáclập causallanguageeffect ởOT. UserđổiBolt→Super nên khôngngoạisuy causalBolt quaSuper. | Primarylinks ở mục5 |
| §15.6: memory mới phải freeze/đo assembledprompt/contamination | Đồngý. Maincomparative singleturn cần clean/pinnedempty memory/profile mọiarm; integration memorytest riêng đánhgiá mới chứngminh lợiíchmemory. Không thêmOTprivileged tài chínhmemory riêng rồi gọifaircomparison. | frozen run_opentrading.py memorynone; ot_headless historyempty, builtinremoved; production memoryhooks |
| §16: anti-fabrication0 tuyệtđối và chỉOT có codegate | SAI phạmvi. Common grader/provenance/ledger guard chạy mọiarm.9primarywins đãkhớp7field receipts; khôngchứngminh mọiattempt khôngbịa. OTfinancepolicy có pre-final guard bổsung riêng nhưng ledger/evidence correctness common. Codecógate khôngtựđộng chứngminh lợithế anti-fabrication sođốichứng. | frozen public_response_contract.py:46–51; run_benchmark.py grounded_answer; grader.py:228,381 |
| §16: trapOT4/4 vsOC/DSH1/2 | Denominator khôngđồngnhất: OT4/4pool2variantsB0+B1, mỗiarm2/2; OC1/2,DSH1/2 trongBoltsmoke. HaiOTvariants khôngphải4independent taskclusters. | INDEPENDENT-CHECK.md |
| §16: DSH/OC khôngrepair, OTduynhất | Những canary cụ thể support quan sát đó; khôngkếtluận mọihistorical/general runtimekhôngrepair. §9chínhreview ghi OTbaseline mạnh tựrepair khôngcầnnewmachinery. Sharedguidance phải same. | opencode-review.md:§9.2 và§12; v44forensics |
| §16: vận hành OT bềnvững/costthấp2.5× | Vượtquá chứngcứ. Bảngtrộn v3pilot vàv44smoke; v44tokens/success chỉ2trapwinsB1vs1DSH,0numericBoltwin. Flashusagechỉ12/24complete,knowncostlowerbounds; pricesN/A. Cachehit observedkhác khôngphảibug nếucontextprefix/tokenizer/timingkhác. | REPORT.md request/usage; FORENSICS.md:18,54–65 |
| §16: modelceiling12allfail, Flash25/26 =>khôngphảiharness | Khônghợp lệ causal. Diagnostic3passes thaytimeouts/cófailuresexcluded, finalcompletecases chọnsubset khác, khôngcertified. V44DeepSeek retrievalthànhcông7aggsnhưng pathfailtrướcarithmetic. Khôngthể kếtluận ceilinghoặcchỉlanguage. | review§9limits; FORENSICS.md |
| §16: OTwatchdog120s hiệnlàđiểmnghẽn | Historicalv3diagnostic đúng; v44headless truyềnstallMs300000, productionsource hiện LLM_STALL_MS300000. Phải đo currentrequest/trialtimeouts và bufferedstreamstall interplay. | frozen ot_headless.ts:24–26; productionagent.ts LLM_STALL_MS |

## 2. Số thực nghiệm dùng được (KHÔNG gom model/cohort)

Mỗiarm6trial/model (4answerable+2traps). Bolt primary B0/B1/OC/DSH=2/2/1/1, semantic2/2/2/1, DNF0/0/0/0, FR4/4mọiarm. Tấtcả6primarywinsBolt làemptyresolvertrap;0numericwins. DeepSeekprimary0/2/0/1, semantic3/2/3/3, DNF3/4/3/3, FR0nhưngnhiềuDNF. RawvalidDeepSeek0/2/0/1, nên21/24invalidđúng bao gồm cả absentfinals; khôngphải21format-onlyloss. Có8fencedfinals, khôngphải21. HaiquoteprimaryB1r1vàDSHr2 đúngHPG21nghìn đồng2026-10-30. Aggwins0mọiarm.17compute bịrejecttrướcphéptính, khôngtestarithmeticmodel.

UsageBolt24/24trialsđủ; DeepSeek12/24đủ. Gatewayrequest125, actualupstream116;9localdeny khôngtính thành9upstreamfinancialmodelcalls.9primaryreceiptjoinsđượcchứngminh, khôngkếtluận externalfinancialsnapshot authentic từhashnội bộ.

FR cần hai mẫu số: `tools/metrics.py:false_refusal_rate` báo denominatoranswered vàdenominator_started. FR0cóDNFkhôngđược trìnhbày như hoànthiệncalibration. Stable/fullscope và pairedper-task phải đi kèm sốcluster, khôngpseudo-replication.

## 3. Allowed APIs / current seams (copy from actual source, không tưởng tượng API)

Rootbenchmark hiệnkhác frozenv44study: rootkhôngcó analytics_compute/finance-policy mới, khôngđược tưởngrootđãbao gồmv44. Dùng pathđúng và pinSHA.

- `tools/run_benchmark.py:228` `transient_failure(result, log_text)`: nếu parseablefinal thìfalse; ưu tiên statusdòngcuối providerledger429/500/502/503/504; fallbackregex loại400/401/403/404. Frozen equivalent232. Hiệnkhôngphânbiệt localvsupstreamstatus/responsepartial.
- `execute_trial(item, task_dir, out_dir, model, timeout_s, retries=0, backoff_s=0, options=None)` root258, frozen262: **wholetrialretry**, mỗiattemptworkspace/Homefresh, giữtấtcảattempts; request/time/tokensharecap. Unknownbillingbreak. Khi recovering cóattemptdir thìkhôngnewcall. CLI `--retry` default1, `--retry-backoff` floatdefault4, `--timeout` wholetrialbudget; frozenv44manifestretry0.
- `tools/runners/provider.py:102` `ProviderGateway(model, ledger, options=None)`, `handle(handler)`: parentownedNVIDIAcreds; exactrequest/effectivecaptures; `provider_timeout_s`, `max_requests`, `max_output_tokens`, `max_total_tokens`. NVIDIA_URL `/v1`; actualroute `/chat/completions`. Defaultprovider45s; nohiddenupstreamretry; allnative SDKthroughsamegateway. Currentnormalize_model rejectsnewSuperuntilmodeladmissioncanary.
- Frozen `provider.py:233–246`: cap24; anypriorunknownupstreamusage deniescontinuation; conservativetokencheck actualknownusage+nextinputUTF8bytes+maxoutput. MappinganyValueError→403 line318isrootmislabel, notupstream403. HTTPError branchusesactualstatus, RetryAfteronly429 globalratelock; doesnotretryitself.
- `aggregate_usage(rows)` root72/frozen77 considersALLgatewayrows, so localnonupstreamdenial makescompletefalse evenifallactualupstreamusageknown. Futurev45 needseparateupstreambillingcoverage vs allrequesttelemetrycoverage withoutchangingfrozenruns.
- Frozen `analytics_compute.py:105` `compute(args, sources)`, `traverse(env,path)` line30, `unit_for`65,`scope_for`86: sessionboundreceipts, numericfiniteleaf, ordered/currentprevious, units/periods/entities, Decimal. Noarbitrarynumericoperands. Commonallarms.
- Frozen `finance-policy.ts:29` `correctionEligible(def: ToolDef,error:unknown)` no`invalid_derivation`; scope61removes only public`x-repair-fields`, protectsentity/date/metric. DoNOTjustset`x-repair-fields:[operands]`: thatwoulddropcallid/entity/date/metric aswellaspath, allow financialscopeescape. Need semanticimmutable sourceidentityand narrowfixablepath proof.
- Frozen `mcp_snapshot_server.py:293` `replay_compute(arguments,sources,payload_sha256,ledger_path=None)` returnsstructured `invalid_derivation` withretryabletrue andgenericguidance, ownderivedledger namespace. Publicvalidleafexamples canbelistedfromactualsource, neverselectedfromgold.
- Frozen `public_response_contract.py:46` `validate_public_response_contract(instruction,final_text,catalog_names=None)` purecommonshapecheck; nofinancialgoldorledger. Reportfinancecorrectness/grounded/rawformatseparately; donotloosenfrozenprimary.
- **Productionnativeupstreamretriesalreadyexist** `/home/doanlong/OpenTrading/src/core/retry.ts`: `RetryOptions` line48has`onRetry`, `requestTokens`, `sleep`, `random`, **NOmaxRetries/disableknob**. `RETRIES=4`, `RATE_RETRIES=2`, `MAX_WAIT_MS=60000`; `classifyFailure(error)`74, `withRetries<T>(call:()=>PromiseLike<T>,signal:AbortSignal|undefined,opts:RetryOptions={})`183; `retryMiddleware(opts:RetryOptions={})`209wrapGenerate/wrapStream. Itretriesprestreamrequests, notexecutedtoolsteps. `classifyFailure`retriesall5xxandstatusisRetryable; 403fatalusually. Daily429neverretry. SDKblindretryoffbutcustomOTmiddlewareON.
- Currentproduction`agent.ts` requestFor calls `wrapLanguageModel(...retryMiddleware(retry))`, `runAgent`usesRetryNotices.options. MerelyCLI`--retry0` DOESNOT disablethisnativerequestretry. Need explicitbenchmarkseamanduniformownerorcreditasnativefeature/documentasymmetricattempts. Existing`OPENTRADING_RETRY_SCALE=0` zeroessleep ONLY, DOESNOT disable retries; usingitasoffwouldcauseburst.
- Productionfilelinesmaymovewhilerootmerges/pulls; retryAPI/sourcewasreadfullthisturn butrootmustpinafterintegrationSHAandrefreshlinereferences.

## 4. Retry khuyến nghị để sơbộ cócâutrảlờinhiềuhơn, khôngchọnđápán

Khôngthểbảođảm100%mọicâu cócorrect/parseableanswer bằngtransportretry. Lỗi schema/format/calibration/compute phải xửlý gốc; serviceharderror/capsvẫnDNF. Usermuốnavoidempty là mục tiêu availability, khôngphải phép chọnsampleđẹpsaugrading.

**Policyproposal cho root lựa chọn đăngký trước:** common gatewayrequest-level owner; driverwholetrialretry0; nativeOT/OC/DSH providerretrydisabled/explicitlyproved; cùng DeepSeekpolicy cho4arms (Superpolicy cũngpintrước, cóthểcùngowner). Perlogicalrequest tốiđa3upstreamattempts (initial+2retry), chỉpre-exposuretransportfailure; waits4s,8s (RetryAftercao hơnđượcrespectđếntrần60s vàtrongremainingdeadline), providerdeadline240s/thửlàkhởitạonháp cần canaryverify; maxupstreamrequests24 vàtotaltrial900s làkhungv44thamkhảo, taskmultistep/capsphảidimensionbằngcanarytrướcfreeze, khôngnớimidthrough.

Eligibility bằng machineerrorclass+origin+bytesseen, khôngbằnggrade/value:

1. Retryactualupstream429per-minutewithRetryAfter;502/503/504/500 vàconnectreset/timeout đượcchứngminh; khôngdailyquota/auth400/401/403/404, modelmismatchnonempty, unsupportedfeature, localschema, request/tokenbudgetdeny, usageunknowncontinuationdeny.
2. **Missingmodelmetadata khôngtựđộng retry**: nếuactualbodyemptyzerochoices vànoexposedassistant/tooloutput cóthểclassify`empty_transport_response` riêng; nonemptyidentitymissing/partial/malformedtoolcall làprotocolfail cầninvestigate, khôngrelaxmodelproof. Giữredactedrawbody/streamchunks/requestIDs/header/finishreasons/bytesreceived/toolcallids/usage before deciding. Khônginventmodelname tocontinue.
3. Khiupstreamusageunknown, giữnguyênpartialtelemetry. Chỉcho phép retry nếu đãpreregistered conservativeupperreservation chofailedrequest bao gồminput+maxoutput thực đượcvalidate, tínhreservevàonumericalcap; khôngassumezero hoặc resetcap. Nếukhôngcóboundđángtin thìfailclosed nhưv44. Cóthểnguồnmodel/tokenizerexactreceiptboundđểgiảmbudgetbyteoverreserve; khônggáncharacters/4 làhardbound.
4. Retry cùng native/effectivepayloadhash vàcontext, khôngthêmfeedbackvềgold/format, khôngchạytoolstepslại; chỉpublishfirsttransport-success response vàdừng. Lưu mọiattemptkểcảpartial cóusageN/A, sharedrequest/time/tokenbudgets, deterministicattempt/backoffmetadata. Khôngcứthửđếnkhiđúng.
5. Nếumodelđãsinhđápánprose/fences/saisố/refusal, KHÔNGtransportretry. Genericboundedfinal-contractrepairnếuđăngký lànativeharnessmechanismtốnrequest vàphảibáoriêng, khôngẩntrongretrylayer. Nếuuser muốn answer-completiondiagnostic lại trênDNF, studyriêngđộc lập, giữoriginaldenominator/results vàkhônghợppoolchọnbestanswer.
6. Báofirst-attemptvsrecovered-with-transportretry; primarytínhmọitrialđãlênlịch; modelcall/latency/costsumallattempts; retryexhaustion, unknownusage, partialstreams riêng. Preapprovedaborttrêncohortproviderfailurethreshold, khôngđổiquestion/armchỉvìfail.
7. Testsmeaningfultừexistingfixtures mục6: 429→success,503→success,401/403/authfatal, localbudgetneverretried, metadataactualmismatchneverretry, partialassistantoutputneverretry, missingusagefailclosed/reserved, repeatedsamehash, nocallafterdeadline/cancel/exhaustedbudgets, completedresume0newcalls, native×gatewaymultiplicationprevented.

Policy nàyphùhợpđánhgiásơbộ nhưngkhôngcamkếtprovideravailability. NếuexistingnativeAPIkhôngcho disable, rootcầnthiếtkếknobthậtvàtest, khôngviết giả`maxRetries:0` trongRetryOptionschưahỗtrợ.

## 5. Primary externaldocs đã đọc (08/11/2026)

- [NVIDIA Super VL model card](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b/modelcard): modelIDnvidia/nemotron-3.5-super-vl-120b-a12b;120Btotal12Bactive;NVFP4;up1Mcontext;reasoningviachattemplate`enable_thinking`; recommendedtexttemperature1.0/top_p.95. Đây làkhảnăngmodel, khôngchứngminhhostedAPIchấpnhậnmọikhóa. V44gatewayepstemperature0/top_p1 làsettingcầnđăngkýminhbạch, khôngtựcoicả3modelsameeffectiveeffort. Khôngsuy SuperwinuplifttrênOTtừgeneralbenchmarks.
- [NVIDIA officialusagecookbook](https://raw.githubusercontent.com/NVIDIA-NeMo/Nemotron/main/usage-cookbook/Nemotron-3.5-Super-VL/README.md): hostedID,120B/12B,text/image/videocapability; financeLoRArecipe tồn tại, khôngdùnglàmchứngminhdomainbenchmarkready.
- [Bolt HF primarycard](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB/raw/main/README.md) lines595,799–801explicit7posttraininglanguages;lines248nonexhaustivesupportedlist;343thinkingdefaultonintemplatedeployment;336temp1/top_p.95recommended. TechnicalreportPDFopenfailedbecausecontent~22MB, nênkhôngbổsungtríchdẫnPDFchưaverified. ReviewassertionEnglishonly cóthểtríchPDFđúngnhưngkhôngđượcbỏmâuthuẫnprimary.
- [NVIDIA Bolt blog](https://research.nvidia.com/labs/nemotron/Nemotron-3.5-Bolt-E4B-4GB/) model/features35languages, agenticmultiturnsupport. KhônglàexperimentVI/ENcausality.

## 6. Copy-ready fixture/snippet locations

- `tools/tests/test_reproducibility.py:45–66`: actualfreshworkspace/sharedrequest+token+timecaps/allattemptpreservationfixture; dùngpháttriểnfuturedriverretry, khôngsửafrozenv44copy.
- `tools/tests/test_provider_runner.py:150–176`: unknownusagefailclosed + RetryAfterlimiterpreserves429fixture. `experiments/finance-v44-study/tools/tests/test_provider_runner.py:148–174` frozenreference.
- `tools/tests/test_driver.py:113–119`: identifiabletransientonly+noqualityretrywhenparseablefinal.
- Frozen`tools/tests/test_current_wire_gateway.py`: actualSDKrequestthroughstubbedgateway; futureparity/hiddenretry/memorysystemdrift cầncopytestpatterntrênfreshsource.
- Frozen`tools/tests/test_public_contract.py`, `test_v42_contract.py`: rawJSON/refusal/commoncontract; keepstrictmetricsversioned.
- Frozen`tools/analytics_compute.py:10–27`, `replay_compute`293–307: publicschemaandstructuredinvalidderivation; correctnessproofsretainunit/date/sourcechecks.
- Production`src/core/retry.ts:183–213`: actualwithRetries/middlewarecomposition fornewbudgetknob; `classifyFailure:74–92` taxonomyincludesfataldailyquotaandauthbranches. Copybehavioronlyafterdecidingoneowner.

## Confidence / known gaps

High: v44counts/failuretaxonomy/rawformatandcomputeproblems backedimmutableaudits+actualsource. High: currentretryAPIandnewSupermodelcardidentity. Medium: attributingfutureuplift, explicitEnglishlanguagecausality, providerdecoderbackend allUNPROVEN. No numericexpectedscoreforecastjustified; setengineeringacceptancecriteriaandexploratoryhypothesesinstead. Didnotindependentlyrun new10taskoracle here(parentotheragentowns), didnotfetchrawservicecatalog/keyprobe, didnotrunmodels. Productionconcurrentpullmoveslines: finalsourcehashmustbeconfirmedrootaftermerge. No filesmutatedexceptthisreportin/tmp.
