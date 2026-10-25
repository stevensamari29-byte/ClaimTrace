# Independent dispatcher acceptance â€” 2026-10-24

Reviewer: native `/root/merge_dispatch_qa`, distinct from implementation engineer. Tests below concern the restricted host execution boundary with fixtures/protocol stubs, never genuine model inference.

## Accepted controller merge gate

Before merge, independently checked accepted head `40042f0e045348b33e5445683ec7831a4bcf2f65` against main `fb0bfdb214de62db28ba687382141b48e2db0c13`: unchanged 29 files, 3,359 additions and 8 deletions, clean worktree. Actual 61 committed blobs scanned in memory against configured private SEC contact and Zetaris endpoint/key values: zero matches; private values were never emitted. External private configuration hash matched its preserved baseline. Five public H-MEM source hashes matched the pinned provenance manifest. `.venv/Scripts/python.exe -m pytest backend/tests/test_repository_secrets.py -q`: exit 0, 1 passed in 6.90 seconds. Existing complete source/provenance/security review read; no new blocking findings. Director separately verified remote PR state and performed the approved merge.

## Dispatcher

Status: verified within the restricted deterministic host-boundary scope; no blocking findings remain after one repair cycle. No independent live service request, cloud write or model inference is authorized/performed by this review.


Independent `backend/tests/test_dispatcher_acceptance.py` adds 38 fixture/protocol cases: strict JSON/duplicate keys/output bound/nonfinite handling; forbidden SQL, arbitrary commands, host hooks, scope and budget changes; reader scope mutation; atomic batch validation including unselected metrics; later-published/foreign/undated/unlocated/invalid-duration source rejection; conflicting versions retained; source updates reverify without resetting budget; one recheck with the explicit Zetaris-to-SEC read; failed readers cannot conclude earlier support; shared call/deadline/transition limits; late provider/retrieval responses rejected; canonical source citations/publication dates; fabricated approval or semantic promotion rejected; untrusted briefing prose excluded; defensive report copies; actual preserved Meterless text client rejected without discovery/completion; unavailable provider explicit and sanitized; false semantic mapping remains unverified and requires human review.

One concrete independent blocking finding was reproduced: an invalid provider's unrecognized `execution_kind` was echoed into report metadata, allowing private adapter metadata to escape. Engineer allowlisted report kinds; the regression now passes. A transient test expectation was corrected after host challenge events were moved into existing transition metadata; this was a test-contract adjustment, not an application defect. Windows pytest parameter IDs for the oversized fixture were bounded explicitly to avoid generated filename errors.

Final independent commands:

- `.venv/Scripts/python.exe -m pytest backend/tests/test_dispatcher_acceptance.py -q --tb=short`: exit 0, 38 passed in 0.62 seconds.
- `.venv/Scripts/python.exe -m pytest backend/tests/test_dispatcher.py backend/tests/test_dispatcher_acceptance.py backend/tests/test_model_contracts.py backend/tests/test_model_contract_acceptance.py -q`: exit 0, 117 passed in 0.73 seconds after final one-query and post-challenge deadline hardening.
- `.venv/Scripts/python.exe -m pytest backend/tests -q`: exit 0, **235 tests plus 58 subtests passed**, 20.27 seconds, one existing Starlette/httpx TestClient deprecation warning.

Full stable-suite verification includes unchanged legacy API, provider tests, actual H-MEM process/store tests, accepted investigation controller, contracts and dispatcher. Fifteen accepted API/source-reader/frontend/provider/controller/H-MEM paths show zero Git-normalized content changes against `aca07ec`. Worktree raw bytes can differ in CRLF checkout endings, so compatibility verification used Git's normalized diff rather than asserting raw byte equality. All 74 tracked plus nonignored new worktree paths were scanned in memory against configured private contact/endpoints/key: zero matches; the external secure configuration hash remains unchanged. Director must also stage/review the final index scan before committing.

This review performs no fresh SEC/Zetaris service request, cloud dataset write or genuine inference. Default retrieval reuses the accepted process-isolated reader; custom trusted Python provider/reader callbacks must honor their declared deadline contract. Late callback output fails closed, but arbitrary Python callbacks are not forcibly preempted. The preserved Meterless client still lacks genuine structured tool-call/deadline support and is deliberately unavailable here. H-MEM behavior remains accepted in the existing controller; recalled memories are not yet added to dispatcher model context. Trusted disclosure ingestion, semantic extraction validation, original decimal precision and live Nightshift/Nemotron execution remain outstanding. No unsupported competition qualification or live model capability is asserted.

Final actual Git-index verification after Director staged all nine files: 74 staged blobs scanned in memory against configured private contact/endpoints/key, zero matches; external secure configuration hash preserved. `.venv/Scripts/python.exe -m pytest backend/tests/test_repository_secrets.py -q`: exit 0, 1 passed in 3.09 seconds. `git diff --cached --check`: exit 0. No remaining blocking findings in this scope. Director retains staging/commit authority.
