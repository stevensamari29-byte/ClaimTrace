# ClaimTrace H-MEM integration

This product uses the real Meterless H-MEM reference store, retrieval and trust-ledger services in a local Node worker. It performs actual add, hybrid query, persistence, restart, feedback and correction lineage operations. Its upstream embeddings are deterministic hash **mocks**, not learned semantic embeddings or model inference. This feature does not complete Nightshift/Nemotron integration.

Public source is pinned to [Meterless commit 1742dec56a66e58eef9dda2d2b865823758ca8cd](https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd/engines/hmem/reference/src). Five unchanged TypeScript modules live in `backend/investigation/vendor/hmem/` with the upstream Apache 2.0 license and source hash manifest. No private HQ configuration, memories, agent system or account information is included. The application reuses the existing tested public source and existing Node 24 runtime; no package install or new service is needed.

## Interface

`HMemMemory(root=None, scope_id="local-cli", actor="local-human", timeout=3)` in `backend/investigation/memory.py` is a versioned application adapter independent of the frontend. Default persistent data is in Git-ignored `.local/hmem/`. Choose the scope and actor in trusted local code, never directly from an unauthenticated remote request.

1. Retrieve current eligible financial evidence through the existing tool. `propose(request, text, evidence, correction_id, supersedes=None)` creates an immutable SHA-256 approval payload with source citations, publication dates and exact evidence snapshot hashes. It writes nothing.
2. Display the entire proposal to a local human. Call `review(proposal, approved_digest=proposal["digest"], approve=True)` only after that exact payload is explicitly approved. `approve=False` writes no memory or directory. A local actor label records the operator choice; it is not proof of remote user authentication.
3. On another invocation, `recall(request, fresh_evidence)` executes the real H-MEM query and then validates scope, source identity, snapshot hash and as-of cutoff. It returns reviewed interpretation pointers with citation links, reviewer and review timestamp. Missing/future/changed financial evidence cannot be replaced by memory.
4. A reviewed correction can name an existing `memory_id` as `supersedes`. Both `new.supersedes` and `old.supersededBy` are persisted. The old record remains available for audit but is excluded from active recall. The adapter disables the reference's heuristic supersession selection unless the exact reviewed proposal names that predecessor.
5. `feedback(request, memory_id, "helpful"|"not_helpful"|"wrong")` executes real reference feedback and records its ledger entry. `wrong` marks the record for review and excludes it from active recall; a separately approved replacement is required.

The isolation key combines a trusted local scope ID, canonical CIK, fiscal year/period and GAAP basis. Separate scope directories are necessary because the upstream `chatId` filter alone permits unscoped records. SEC filing URL issuer identifiers must match the requested CIK. Every source snapshot is hashed even when the upstream document hash is absent; the adapter labels this `evidence_snapshot_sha256`, never a document-content hash.

## Recovery and bounds

The Node worker serializes operations per scope with an exclusive PID-owned lock. Active owners cannot have their lock removed by a contender. A dead PID lock is reclaimed before startup recovery. A missing or malformed owner file fails closed and needs local inspection; it is never assumed stale merely because time elapsed.

Before a correction write the worker atomically records the approved operation in `operations.json`. Startup replays incomplete operations using the approval digest tag to avoid duplicate memories, repairs the backlink, and only then serves recall. State and journal replacements use temporary files and rename. The audit ledger is ordinary local JSONL, not cryptographically tamper proof. This is bounded local process-crash recovery, not a transactional distributed database or a power-loss durability guarantee.

Each worker invocation has a maximum three-second subprocess timeout; storage is capped at 100 approved correction IDs per scope. Each correction has at most 4000 characters and 25 source references. Worker output is capped at 2 MB. No sleep, dreaming, automatic mining, conflict resolution, model hook or network call is enabled. A timeout or corrupt store fails explicitly and cannot grant approval or fabricate recall.

## Reproducible verification

From the repository root run `.venv/Scripts/python -m pytest backend/tests/test_investigation_memory.py -q`. These product tests run the real vendored TypeScript services, not mocked memory calls. They cover rejected and exact approval, source fingerprints, process restart, actual ledger/feedback, duplicate approval, conflicting idempotency keys, changed sources, later publication, another issuer/session/quarter, both supersession links, pending-operation replay, live-owner lock protection and abandoned-owner recovery.

No approved correction changes SEC facts, numerical calculations or financial verdicts. The controller may expose reviewed context for human inspection and subsequent evidence-based rechecking. Model interpretation and reasoning remain incomplete pending authorized live Nightshift/Nemotron inference. No shared multi-user review endpoint or authentication system is supplied by this local adapter.
