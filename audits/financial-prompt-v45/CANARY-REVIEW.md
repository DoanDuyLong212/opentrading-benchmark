# v4.5 synthetic NVIDIA canary: functional success differs from identity admission

Reviewed offline 2026-11-08. This review does not modify the original sealed canary script, manifest, results, or receipts.

The sealed schedule completed 12 cases, 24 chat requests and one catalog GET; every chat response has nonnegative measured prompt/completion usage. No financial task was queried. Each case has a function call and a continuation; synthetic 17 is visible in the original prompt and in the continuation instruction, so the continuation is a protocol test, **not proof of numerical reasoning or reliance on the tool**.

| Requested model | Prefix selector correct | Fully anchored selector correct | No-pattern selector correct | Reported response model | Original admission |
|---|---:|---:|---:|---|---|
| deepseek-ai/deepseek-v4.1-flash | 0/2 | 2/2 | 2/2 | deepseek-ai/deepseek-v4.1-flash | PASS |
| nvidia/nemotron-3.5-super-vl-120b-a12b | 2/2 | 2/2 | 2/2 | private/nvidia/nemotron-3.5-super-120b-a12b | **FAIL exact identity** |

DeepSeek's 0/2 versus 2/2 on the same synthetic object supports an effect of the prefix-pattern contract in this small controlled probe. It does not establish NVIDIA's backend implementation, nor prove the same effect explains every financial v4.4 failure. Corrected/no-pattern cases meet the preregistered identity/tool/continuation/usage admission checks; the old prefix control is reported without excluding its failures.

Super produces correct selectors in all six cases and expected continuation content in all six. All 12 responses report the private identifier rather than the requested public VL identifier. The exact-identity rule therefore fails and no Super admission receipt was created. A response alias alone neither proves a model substitution nor independently verifies model equivalence.

The captured catalog contains the public VL identifier, object type, created timestamp and owned_by=nvidia; it provides no private-name mapping. Official NVIDIA model card/API documents describe the public VL identifier. Searches for the exact private name in primary NVIDIA documentation did not establish an alias mapping. A customer forum report corroborates the observed private name but is not a provider attestation. No policy relaxation, extra canary request or financial call was made during this review.

Primary references reviewed:

- [NVIDIA Super API/model specification](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b).
- [NVIDIA Super model card](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b/modelcard).
- [NVIDIA DeepSeek model card](https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash/modelcard).
- [Customer's observed private-name report, not staff identity attestation](https://forums.developer.nvidia.com/t/nemotron-3-5-super-vl-on-integrate-api-nvidia-com-can-the-131-072-token-completion-cap-be-raised-and-what-does-reasoning-effort-max-do/387797).

Artifact: `experiments/finance-v45-study/audits/model-admission/canary-results.json`, with append-only `.attempts.jsonl` and `canary-manifest.json`. This canary contains no financial win, smoke/pilot result or justified financial-quality forecast.
