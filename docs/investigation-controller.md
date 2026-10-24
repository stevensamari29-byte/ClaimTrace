# Standalone investigation controller

This is an **incomplete agent implementation**. It runs real evidence tools and deterministic verification, challenge/recheck and source-backed memory. It does not run model inference, extract assertions from prose, choose tools through model reasoning, or generate an AI-written briefing. `execution_mode` is always `incomplete_no_live_model`; human review is always required. The accepted frontend and `/api/investigations` remain compatible and unchanged.

From the repository root, with the existing dependencies:

```powershell
.venv\Scripts\python.exe -m backend.investigation shared/example.investigation-input.json --output .local/report.json
```

Create the ignored `.local` output directory first if needed. The example contains an explicitly human-entered test assertion, not an issuer quotation. Its default SEC path uses the authentic labeled ISRG cache. For actual Zetaris retrieval, set `request.evidence_backend` to `zetaris` in a local input and configure the already approved external connection and `CLAIMTRACE_ZETARIS_TABLE=claimtrace.sec_financial_evidence`. Never rerun the dataset CREATE template. Set `CLAIMTRACE_SEC_MODE=live` for live SEC retrieval/recheck; the approved real contact belongs only in ignored `.env.local`.

The Python interface is `from backend.investigation import InvestigationInput, run_investigation`; pass the JSON object or validated input. All company, fiscal period and cutoff inputs use the accepted request contract. The structured `claim_inputs` contract is implemented in `backend/investigation/models.py`. Each assertion supplies the exact dates, metric, decimal string, unit and accounting basis. Unsupported prose stays unresolved. Supported metrics are GAAP revenue, diluted EPS, net income and net margin; unknown/non-GAAP assertions require a reconciliation that this slice cannot provide.

Rules select the financial comparison or net-margin tool from the declared metric. Retrieval calls only the existing SEC/Zetaris readers in a process with a wall timeout. Checks reject future publications, inappropriate durations and unverified issuer document URLs, and require exact claim periods and compatible units. Conflicting eligible values stay unresolved. The challenger records qualifications and requests at most one additional retrieval when a finding is missing or contrary; Zetaris rechecks use SEC explicitly. A refresh of the same SEC source is not independent corroboration. Retrieval failure preserves earlier evidence but prevents an unqualified conclusion. Limits are shared across all claims: three claims, eight tool calls, ten trace transitions, 120 seconds, one recheck, no automatic retry.

Reports retain original assertions, evidence and publication dates, citations/locators, calculations, initial and final findings, challenge results, rejected evidence, tool trace, limitations and required review. Decimal calculations operate on the accepted reader's float representations; they cannot restore original filing precision or infer rounding tolerances. Declare any justified tolerance explicitly. These reports are deterministic checks for human review, not financial advice or completed AI reasoning.

Optional real H-MEM recall:

```powershell
.venv\Scripts\python.exe -m backend.investigation shared/example.investigation-input.json --memory-dir .local/hmem --memory-scope local-cli --output .local/report.json
```

See [H-MEM integration](hmem-integration.md) for exact-payload local review, sourced corrections, restart, lineage and isolation. Reviewed memory is context, never authority to replace a financial fact. Node 24 is required for the reused TypeScript services; state stays ignored and private. Local actor selection is not shared-user authentication.

Nightshift remains the intended primary runtime. The existing Meterless client and opt-in factory are preserved. Supported authorized host/access, actual discovery, a bounded live completion and a receipt establishing underlying NVIDIA Nemotron execution remain outstanding. Neither a mock transport nor H-MEM's deterministic hash embeddings fills this gap. The next model task is schema-validated extraction/tool proposals through that runtime, with every proposal checked by these same restricted tools and budgets.
