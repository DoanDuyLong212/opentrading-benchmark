# User-authorized requested-route admission amendment v2

2026-11-08, BEFORE financial inference. Root coordinator relayed the user's explicit approval to use the requested public NVIDIA Super endpoint while retaining its actual returned private identifier and marking checkpoint identity **UNVERIFIED**. This is a separate versioned contract, not a correction of the original exact-identity canary failure.

- Requested/wire model stays `nvidia/nemotron-3.5-super-vl-120b-a12b`.
- The only additional accepted response identifier is exactly `private/nvidia/nemotron-3.5-super-120b-a12b`.
- `checkpoint_unverified=true`; no claim that the private checkpoint is independently verified as VL or equivalent to another endpoint.
- The gateway never rewrites raw response model identity. Rows record requested model, accepted returned identifier, actual response identifiers, admission contract and checkpoint status. Raw request/response captures remain independently hashed.
- No fallback, broad private-prefix allowlist, new inference or canary retry is introduced. Every other response identity is rejected.
- Receipt `experiments/finance-v45-study/audits/model-admission/nvidia__nemotron-3.5-super-vl-120b-a12b-route-v2.json` binds the existing immutable canary SHA and six recorded successful function/continuation cases. The original exact-identity FAIL and all original artifacts remain unchanged.
- DeepSeek continues under original exact-identity-v1 admission. Report the two model cohorts separately, with Super labelled as the requested endpoint with unverified private checkpoint identity.

The gateway now admits both requested routes under these distinct contracts. Admission is operational permission to execute the registered benchmark; it does not establish financial quality, smoke/pilot success or superiority.
