# Structured provider: implemented transport, unverified runtime

The provider is prepared for the existing Meterless Nightshift client. No compatible authorized host is available as of October 25. No actual Nemotron reasoning, automatic claim extraction or generated briefing has been demonstrated. The current browser stays on the deterministic controller and requires human review.

## Interfaces and trust boundary

- `backend/providers/meterless_client.py`: preserves the existing text client and its tests; adds a native OpenAI-compatible structured request and strict JSON decoding.
- `backend/providers/structured.py` and `structured_worker.py`: fixed isolated Python worker, bounded input/output, sanitized errors and an absolute parent-controlled deadline. An expired/slow request kills and reaps its worker; no token appears in arguments or logs.
- `backend/providers/nightshift.py`: explicit configuration factory. Both `--live` and server enablement are required. No automatic discovery or direct NVIDIA fallback.
- `backend/investigation/model_run.py`: standalone dispatcher entry point, independent of React. Input is a local validated `InvestigationRequest`; optional disclosures must be trusted SEC disclosure records already accepted by the contracts.
- `backend/investigation/dispatcher.py`: existing host gates still validate each proposal, company/period scope, evidence identity, publication cutoff, citations, final classification, tool budget and required human review. Optional real H-MEM recall occurs after fresh evidence ingestion. Memory is reviewed context, never a financial override or model write capability.

The request contains only host-defined tools and bounded untrusted source/tool context. It requires exactly one native function call, disables parallel calls and streaming, and bounds completion tokens. Duplicate keys, nonfinite JSON numbers, multiple calls, free-text responses, refusals, truncated output and unknown tools fail closed. No SQL, shell, user-supplied URL or scope-changing tool is exposed. The existing dispatcher enforces at most eight tool actions, ten transitions, one recheck and 120 seconds for the workflow. Provider transport uses the remaining absolute deadline. Local HTTP fixtures verify the protocol and termination behavior; they are not a model.

## No-network default

From the repository root:

```powershell
.venv\Scripts\python.exe -m backend.investigation.model_run shared/example.request.json
```

Expected: exit 2, blocked provider status, `live_inference_verified: false`, and required human review. The CLI does not load `.env.local` provider fields. An invalid local input also returns an explicit sanitized blocked error.

## Authorized live acceptance, when access exists

The eligible account/host owner must privately configure these process variables, never frontend variables or tracked files:

```text
NIGHTSHIFT_INFERENCE_ENABLED=true
NIGHTSHIFT_BASE_URL=<authorized compatible host>
NIGHTSHIFT_RUNTIME_TOKEN=<real Runtime token>
NIGHTSHIFT_MODEL_ID=<routing ID actually returned by /v1/models>
```

Then run the same command with `--live`, optionally `--disclosures` pointing to a locally validated disclosure list. Review the JSON output; a routing ID or HTTP success alone does not establish Nemotron inference. Preserve a redacted receipt identifying runtime version, underlying model, actual native tool proposals, host-validated tool results, bounded finish, valid citations and human review. Repeat a conflicting/incomplete case and an unavailable-provider case. Do not run this acceptance until service access is authorized.

Official Meterless [provider documentation](https://raw.githubusercontent.com/Meterless/Meterless/main/docs/agent-ready/add-meterless-provider.md) describes authenticated `/v1` text chat, a stable `meterless-app` and `meterless-scope: user` for chat, and real `/v1/models` discovery. Its documented text path does not establish native tool support. This adapter's `tools` contract therefore remains explicitly unverified against a real Runtime. Unsupported native calls fail rather than silently becoming text reasoning.

NVIDIA's [official LLM API reference](https://docs.api.nvidia.com/nim/reference/llm-apis) documents hosted Nemotron endpoints. Public API documentation does not provide eligible account access or establish that direct NVIDIA calls satisfy the competition's Meterless requirement. No direct-provider substitution or account borrowing is implemented.

## Exact next access requirements

**Danny must provide:** a nonsecret authorized compatible host location/availability; eligible owner confirmation; privately configured token; actual discovered route and runtime version; proof of native tool support and underlying Nemotron selection. No compatible host is currently available. No further engineering assignment is required to unblock the adapter tests.

**Alex must provide only if broader Zetaris coverage is needed:** which existing approved view contains the second company's fiscal quarter; approved nonsecret column/type contract and source publication semantics; confirmation whether numeric values were converted through `DOUBLE`. The current approved ISRG view remains usable. New/modified cloud datasets still require explicit approval. Generic SEC retrieval already works across companies without a new cloud object.

Cursor can independently review the provider worker lifecycle, strict parser, host gates, H-MEM context and exact-value tests in this focused branch. Retain any genuine Cursor-assisted edit/diff and tests; opening the folder is insufficient sponsor evidence.
