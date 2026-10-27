# NVIDIA activation and remaining Nightshift boundary

**Final organizer override, October 26:** Nightshift is mandatory, not an optional provider improvement. Optional model experiments have stopped. Genuine NVIDIA calls and partial financial actions are retained in `work/nvidia-live.json`, but no accepted completed model briefing is established, and direct NVIDIA cannot satisfy the mandatory Nightshift requirement. See `submission-readiness.md` for the final gate. The final `tool_choice: auto` transport probe has fixture coverage only, not a claimed successful live acceptance.

The owner supplied an existing NVIDIA API key privately on October 25, 2026. ClaimTrace reads only named NVIDIA settings from Git-ignored `.env.local` or the backend process. No key was requested in chat, printed, placed in command arguments or committed. No account, billing, paid infrastructure or local model was created.

## Secure local setup

Keep the real key only in `.env.local` as `NVIDIA_API_KEY=...` or the backend process environment. Do not put it in frontend/VITE variables. `.env.example` contains names and disabled defaults only. The local loader does not execute shell text or expand unrelated variables; process settings take precedence. The production endpoint is fixed to `https://integrate.api.nvidia.com/v1`, uses TLS and bearer authentication, and does not forward credentials through redirects or environment proxies.

The discovered and actually smoke-tested model is `nvidia/nemotron-3.5-lightning-30b-a3b`. NVIDIA's [official model page](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b) documents that identifier and a free hosted API endpoint. No paid billing was enabled. A catalog entry alone is not proof of availability: the older requested Super model appeared in `/v1/models` but its completion failed. A separate Super VL smoke request was rejected because the returned model did not exactly match the requested identifier; no verified receipt was credited.

From the repository root, using the existing virtual environment:

```powershell
# Explicit, temporary backend-process enablement; no key in this command.
$env:NVIDIA_INFERENCE_ENABLED='true'
$env:NVIDIA_MODEL_ID='nvidia/nemotron-3.5-lightning-30b-a3b'
.venv\Scripts\python.exe -m backend.investigation.nvidia_run --live --discover
.venv\Scripts\python.exe -m backend.investigation.nvidia_run --live --smoke
```

Without `--live`, the CLI fails before reading private configuration or making a request. Stored example enablement remains false. Neither application startup nor the existing deterministic browser action automatically invokes NVIDIA. Provider failures remain explicit; there is no automatic direct-NVIDIA/Nightshift fallback.

## Model and host responsibilities

The NVIDIA adapter reuses the existing fixed isolated worker and strict native-call decoder. The parent enforces the shared absolute deadline, kills/reaps a late worker, bounds request/response sizes and keeps secrets on stdin rather than arguments. Native responses must identify the selected model; receipts contain only public endpoint, server-reported model/response ID, bounded token counts, elapsed time and accepted tool identity. Provider bodies and hidden reasoning are not logged.

`propose_claim_from_span` is an explicit model-facing tool. The model selects a registered source span and proposes its metric, value, unit and accounting basis. The host supplies only that selected span's immutable quote, source hash, positions and period, then validates the original canonical extraction proposal. This avoids asking a language model to calculate character positions. It does not repair an invalid raw proposal, select a financial answer or make semantic interpretation trustworthy. Financial meanings and conclusions still require independent host checks and human review.

The original restricted dispatcher remains authoritative over issuer/scope, publication dates, evidence identity, deterministic calculations, challenges, rechecks and final classifications. A native completion is not proof that the financial investigation completed. Model-proposed prose never replaces host-verified findings or grants approval. Direct NVIDIA execution does not establish Meterless Nightshift usage or competition qualification.

## Actual acceptance and limits

A real Lightning smoke request returned `READY`, with matching requested/server-reported model, 24 prompt tokens and 3 completion tokens. Actual native tool proposals were also received. Initial investigation attempts failed closed: invalid quote offsets, a quarterly/year-to-date interpretation error, and selecting checks before a claim existed. These are meaningful observed failures, not successful investigations. Source indexing and an explicit span-selection contract preserve the original source and verification gates. Final complete-investigation status is recorded separately in `work/nvidia-live.json` once executed and independently checked.

The acceptance excerpt came from an actual bounded retrieval of the ISRG July 21 SEC filing. Public reproducible input and provenance are retained as `backend/data/isrg-q2-2026-disclosure.json` and `.provenance.json`; the receipt records source-document and excerpt SHA-256 values plus HTML-text normalization. No issuer claim or model result was authored in advance. The input is an authentic cache, not a new SEC request in every run. Live financial queries reuse the approved existing Zetaris configuration and table. No new cloud dataset is created.

The existing H-MEM store/worker genuinely persists and recalls reviewed corrections; independent tests label synthetic financial inputs and deterministic embeddings. Memory remains source/scope-bound context and cannot replace authoritative SEC values. The browser's persisted report review is separate from memory correction approval.

## Nightshift and Cursor

See `nightshift-windows-activation.md`: the official installed Nightshift software was identified and checksum-verified, but status/discover report unreachable. This laptop does not meet the published dedicated-GPU requirement for the Windows local-model edition. A supported cloud-only startup remains unverified; no local model or unverified cloud endpoint was substituted. A supported cloud-only configuration or an authorized compatible host, private provider-key setup and real Runtime model/tool receipts are still required.

Cursor can independently review this focused branch's provider, span binding, worker termination, host guards and tests. Retain a real human Cursor-assisted contribution and test evidence. No qualifying contribution follows from installation, a file listing or this handoff alone.
