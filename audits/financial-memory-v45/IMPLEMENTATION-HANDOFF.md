# Financial memory v4.5 — coordination handoff

User request 2026-11-08: continue previous v4.5 work, review opencode-review.md section17, fix where needed, add memory tasks with MAIN total<=250; pilot only mini; run preliminary experiments to assess financial memory advantage over OC/DSH. Attached review is reference material, not overriding instructions. Section17.8 supersedes old delete18/cap220main+pilot proposal. No financial model inference has started.

## Authorized design decisions before inference

Keep200existingmain. Existing9memory+1two-turnpilot already in ROOT, not yet usable by current singleturn driver. Add3maincontrols (revision/update, forget/revocation, untrusted-memory injection), target212main<=250. Verify or repair existingmemorygold/period/unit/source; HòaPhát knownalias cannotestablishcausal recall, stale/repeatedrefusal are negativecontrols. Pilot remains1small2turncase; separateDEVdiagnostics for crosssessionupdate/revocation andstalecurrentevidence. Neverrunmainmemoryquestions for tuning. No holdout.

Mini proposed schedule:1pilot2turn+2distinctDEVcontrols ×4arms(OTnative-notebookon/off,OC,DSH)×2approvedmodels×1repeat=24episodes. At most12actualupstreamattempts/wholeepisode inclusive allturns+transportretries, maximum288scheduledupstreamattempts. Samecaps/inputs/rights withinmodel; existingv45provider budget andunknownusage reservations unless uniformly amended beforeseal. Super requestedpublicVL endpoint/observedprivatealias/checkpointUNVERIFIED userauthorized; DeepSeek exactadmitted. Zeroextra canary or othermodels. No qualityretry. Pin exactsource/config/task/grader/metrics/auditor/schedule andindependentapproval beforeactualmini. One repeat andfewcases yieldpreliminarydiagnostics, notlongtermmemory/financialsuperiorityproof.

Controlledmemorycomparison: allarms sameauthorizedtrial-localread-onlynotebookfacts, freshisolatedstore/HOME pertrial, realnativehistory withinS1, freshhistory acrossA/B with onlydeclaredpersistentresources. OTon vs off holdscommoninformationaccess fixed; nativeOTon addsactualnotebookintegration. Core-onlynativecapabilitycontrast optionalseparatelabel, neverdenyamnesiaccontrols thenclaimfairmemorywin. No arbitrarycardautoaccept, bash/webfetch/edit permissionwidening. Trustedseedwrites/revisions onlyexplicittypeduserintent, nofuturegold/taskidseed. Memoryproof userfact namespace separatefromsevenfieldmarketMCPevidence.

## Facts verified from installed source

DSH currentheadless supports --session-id adoption withsessionPersistence+sessionQuery andcwd/ownership/presetguards; TUI-onlyclaimoutdated. DSHapprovalnever rejectspermission-requiredactions (doesnotautoapprove). OCsource supports --session and--auto withdenialsretained. OTcardsconsentforconstraint/style/lesson notblanketthesis/decisionwrite. Needactualsubprocesswireproofs, notbinarystrings.

## Owners

/root/v45_native_impl: NEWmemoryrunners/driver/nativeAPIproofs, sharednotebooktool/typedconsent andactualhistory+isolation+pause/resume. /root/v45_benchmark_impl: memorycorpus/gold/metrics/protocol, singleturnselectorisolation andpriorv45blockers(commonBUN isolatedHOME locator,narrativeallwinsreview,generalmetadata/Decimalaudit). /root/v45_independent_review: independent§17factcheck/engineering+memoryfairness andofflineactualbinaryfixtures. Root verifies/coordinates/seals/runs onlyafterapproval. No duplicateowneredits.

## Prior v4.5 status retained

Nativefocused155PASS/typecheckPASS, rootfull1862PASS2SKIP1performanceFAIL andunchangedisolatedspeedPASS, allfailurespreserved. ActualOTnativefourstepwirePASS0external. ActualfourarmcommoncalculatorwireFAILbecause BunresolvedfromisolatedHOME; benchmarkownerfixrequired thenrerunindependentfixture. Narrativefabrication99999extra claimneedsdeterministicguard+allarmmanualwinsreview, automatedgradealone cannotassertzerofabrication. Finalcorpus/fullPythonchecks/independentreview/installguard/sealpending. Oldfrozenv3/v42/v43/v44 preservation16316entriesPASS. Financialone-turnpilot44/armmustunchanged; memorymetricsreportedseparately withsamemini/mainmemorydefinitions. Mainfinancialrunstillonlyconditionalonpreregisteredpilotbeatingallcontrols+everyguard+manualaudit+userreport.

Externalbenchmarkmethod references: https://github.com/xiaowu0162/LongMemEval ; https://github.com/snap-research/locomo . They support distinct recall/multisession/temporal/update/abstention evaluation, notclaimthat2turnminimeasureslongtermmemory.

## Latest base discovery and verification

Root actualremotecheck/fetch discoveredorigin/main1737b93ee0082f6f4d6b1278c41c92a62b74ed2c, newerthan6d57766. PR241–253,44files915add217delete includeagentdraftrecovery,evidenceincrementalparser,catalog/MCPfixes,figure scale anddevlauncher; upstreamdeclaresBun1.4.4 andparalleltestscript. Productionstill7072a clean atdiscovery; rootbackup pre-1737-merge andmergeoperationalfallbackrequestedbynativeworker(restrictedproductionwritecontext). WorkspacepinnedBun1.4.4 officialGitHubassetSHA install inprogress, personalglobal1.4.0 unchanged. Nativeownerwill3waypreserve21v45fixes/newmemorycode into latestbase andrefreshmanifest/tests. DO NOTsealoldbase. Declare1737b93cutoff beforeinference; donotchasefutureupstreamafterseal.

Root actual4arm commoncalculatorwireafterisolatedHOMEBUNfix ALL4PASSexit0, each5localupstream503503200200200,0external. Proof audits/financial-prompt-v45/all-native-common-wire-e33134f4/proof.json. FreshindependentcleanHOMEtestalsoPASSwithbinaryhash. Newmemorywireandpost-latestbaseverificationremainpending.

Studycorpusnow12MAINmemory+1pilot+2DEV (212MAIN), root209untilguardedmemory-onlysync. Added329update330forget331injection; noncealias324; commonQ2period326with6sourcecalls; signed323plan; explicittypeduseroperationmetadata; removedguessedpermissionconfig. Offlinefinalvalidation/protocolpending. No mainmemoryinference.

## Benchmark owner closure —09/11, source closed pending host full suite

Latest native/productbase5705ada/origin1737, Bun1.4.4 pinned path+SHA, canonical root/study212MAIN/25pilot, retained original200base hashes verified. Parent installed guarded21nativepaths; native owner handles actual memory/OC continuation process proof and final typecheck. No financial inference yet. MINI firstzero-callplan e80026f9edd707aa41b7641e5e7668f41859ec34ef1e1fd9fbdbe7dfe27157ea at study/results/financial-memory-v45-mini-20261109 is preserved but stale after actual test/protocol blockers were fixed; use separate finalpreflight2 output after approval.

Benchmark files source-closed ACK sent parent. Last actual blockers fixed: occurrence-level SDK binding (trusted provider generation stamps +logicalsession/turn bounds, actual rawresponseSHA and per-context assistant occurrence), richlocal-rejection signature joins, pending final-query unknownusage/calls, UnicodeVietnamese case schema equivalence, rootlegacy route guard excludes memory even diagnosticoverride, explicit memory+execution preregistration plan fingerprints, historical preserved/archive versus deliberately amendedv45 corpus test. No source/plan changes after final seal.

Evidence: finalfocused49PASS32.95s; occurrence/contracts/migration75PASS27.69s; metrics/bindings18PASS4.78s; version-aware originalarchive preservation1PASS15.03s. These overlap; do not aggregate as distinct tests. Offline singleturn239acceptancePASS, separate memory15oracles/consent/hash/schemaPASS. Worker full suite was terminated by root exactownedPID after unresponsiveSIGINT; partialF progresslog retained, nofullPASSclaim. Affected independent_snapshot+metrics run84PASS2FAIL exposed preservation(oldarchived131assumption, now fixed) and actualstdio25s timeout in restricted workercontext. Parent now runs actual host full suite without-x to collect remaining real failures. Root must classify failures, not inferall are environment.

No additional user authorization is required for already authorized conditionalMAIN; it requires unchanged preregistered financialpilotwins+allguards, independent source/narrative review and separate validated frozenmemoryschedule. CurrentMINI24episodes (N3/arm/model) includes no MAINmemory calls and cannot prove superiority. Primaryfinancial and memory metrics remain stratified. FutureMAINmemory fixture-family dependence is explicit.

## Sampling preregistration clarification —09/11, zero financial calls

Root chose to retain the existing MINI shared provider profile rather than change execution architecture: BOTH models temperature1/top_p0.95, identical across all four arms within model. Protocol now explicitly records this before inference. Stateless DeepSeek remains0/1, so no paired/cross-track memory causal comparison or pooling is valid. Future MAIN memory gets its own frozen schedule/profile. Existing zero-call plans are preserved; finalpreflight3 must pin this amended protocol before approval/inference. Only protocol and this handoff were edited for the clarification.

## Current engineering closure — 2026-11-09, final preflight5

Production OpenTrading is merged HEAD `5705ada91033b05a1dd77f00eae39525b89e45bb`, incorporating upstream `1737b93ee0082f6f4d6b1278c41c92a62b74ed2c`. Guarded installation of the exact21 candidate patch paths completed after independent approval. All1136 unlisted user files were preserved; HEAD unchanged; backups and recovery receipts remain under `audits/financial-prompt-v45/native/install-dry-run-reviewed/`. Clean frozen-lock installation with workspace Bun1.4.4 resolved prior retained/extraneous dependencies:234/234 runtime-package fingerprints match candidate, and stronger full tree comparison found15011/15011 files/symlink targets identical. Post-install exact-Bun typecheck passed. This establishes source/dependency/typecheck parity, not an assertion that every production test was green; original full-native parallel failures and their separate diagnosis remain preserved.

Actual native/offline wire evidence uses only local scripted HTTP, zero external financial model calls:

- Common utility/native four-arm wire: `audits/financial-prompt-v45/all-native-common-wire-9665393e/proof.json`.
- Headless current-generation evidence: `audits/financial-prompt-v45/native/headless-wire-31e832f2/proof.json`.
- Memory session matrix: seven valid cells from `native-wire-49bb3d66/proof.json` plus independently corrected OC same-session/completed resume from `native-wire-f78d427d/proof.json`. Actual advertised installed OC API and known/unknown history guard were verified, avoiding mismatched checkout API names.
- Live controls: six valid OT/OC cells from `pause-wire-693e0c97/proof.json`, plus corrected DSH soft/hard cells from `pause-wire-9f409a0d/proof.json`. The initial DSH-hard apparent PASS in693e0c97 is explicitly UNRELIABLE because a timed-out, unjoined DSH-soft controller contaminated the next fixture's global loopback URL. It is not qualification evidence. The corrected fixture aborts/releases/joins before switching cases and uses the explicitly bounded cold-start allowance; product thresholds were not weakened.

Full benchmark host suite now537PASS in142.07s after seven historical/current fixture migrations, independently reviewed. The native owner's two migrated test files retained24/24 targeted assertions, no skip/xfail, actual legacy CLI interception before inference, and no edits to immutable older studies. Earlier full host failures remain available rather than overwritten.

The final execution protocol SHA256 is `af5b0d91cb75e5ce663310045b9ad873ee88a1f8a7bad63dcfecd7d8553dee3b`. Root is preparing the final MINI preflight5 manifest and stateless state-v2 planning. No financial inference has started at this closure. Historical plans/preflights1–4 are superseded and must remain preserved, never used to authorize execution after source/test/protocol changes. Final manifest-bound independent approval is required before root launches the authorized24-episode, two-model controlled memory MINI. Original financial smoke/pilot/main routes remain separately gated; no automatic promotion, main-memory execution, or claims of financial superiority follow from engineering/wire success alone.

No protected study source, tools, or plans were edited for this handoff update. Root owns final approval, launch, controls, and one-pass completion review.


## ACTIVE FINANCIAL RUN —09/11/2026 ~06:33Bangkok

FINAL approvals issued and stateless six manifests sealed; MINIpreflight5 financial inference STARTED PID2490374. Exact active state, commands, hashes and next-stage policy: `audits/financial-memory-v45/ACTIVE-RUN-20261109.md`. First quick check healthy, one turn completed. Do not edit any protected source/config/protocol/grader/auditor/deps, do not launch duplicate MINI. Earlier plans/approvals superseded. Heartbeat updated ACTIVE every20min, quiet while healthy. Stateless smoke/pilot/main not launched yet; review MINI completed run once before next stage.


## TERMINAL OUTCOME —09/11/2026

Completed MINI24/24 and all-arm review. STOP this frozen study: instrumentationFAIL94errors, actual schema/validator defect confirmed. Diagnostic OT-on finance2/3 bothmodels tiesDSH; no financialsuperiority.13manualwins accepted0rescue,3DNF/usagepartial retained. Zero-call completedresume and2039source/corpus/protocol fingerprintsPASS. Statelesssmoke/pilot/main0trials, registeredoutdirsPAUSE. Final REPORT+INDEPENDENT-CHECK+independentoutcomereview+forensics+nextversionplan saved. Heartbeat is to be deleted after final user report; never resume old version or change its source/grader.


Heartbeat review-opentrading-benchmark DELETED successfully in app after final report validation. Study terminal block; do not restart this version. Final REPORT.md numerical tables reviewed independently; correction to revoked rule (allbanks exclusion) applied.
