# Independent investigation acceptance — 2026-10-24

Reviewer: native `/root/agent_acceptance`, distinct from both implementers.

Actual live reads and real H-MEM engine operation receipts: [agent-live.json](agent-live.json). No fixture retriever was supplied for the four live financial cases. H-MEM controller recall uses replayed already-retrieved live rows, explicitly labeled. No model calls or cloud writes occurred.

Independent adversarial fixtures are in `backend/tests/test_investigation_acceptance.py`; injected source labels in that test file do not establish live service execution.

Initial independent run: 13 passed, 7 failed. Findings returned to controller engineer: duplicate citation IDs after conflicting-row recheck and unbounded Decimal input. Lock owner cleanup and crash recovery findings returned to memory engineer. Repairs and final retest recorded below.

## Final independent verification

- `.venv/Scripts/python.exe -m pytest backend/tests -q` — exit 0: **116 passed, 58 subtests passed** in 15.96s. Existing Starlette/httpx TestClient deprecation warning remains; no dependency change was needed. This includes unchanged foundation tests, 20 independent adversarial cases, controller tests and real H-MEM worker tests.
- Independent acceptance checks: incorrect comparison, unsupported units/basis/period/prose, missing/future/foreign/YTD source rows, conflicting same-ID versions, margin/zero denominator, shared tool budget and oversized Decimal representations. Fixtures are explicitly identified in the test module. All report citations resolve; no inference is represented.
- Memory test runs genuine Node reference services: reject without approval, exact-digest approval, idempotence, process restart, both correction lineage links, source snapshot/hash revalidation, isolated scope and feedback. Engineering recovery tests independently executed as part of the full suite.
- Actual financial reads: ISRG Q2 Zetaris revenue 2,892,300,000 USD supported; false revenue 1 USD challenged and rechecked through live SEC (eight retained facts across both modes), then contradicted. Before publication there were zero eligible facts and an incomplete finding, not fabricated verification. MSFT FY2026 Q3 reused the same controller/reader and returned five live SEC facts, including revenue 82,886,000,000 USD. Second-company evidence is SEC, not an expansion of the approved Zetaris dataset.
- Genuine H-MEM live-source receipt: local rejection → approval → worker restart → recall → explicitly reviewed superseding correction → one active recall; controller invoked real H-MEM recall with already-retrieved live source rows. That injected financial replay is labeled and is not a second network demonstration.
- Read `docs/investigation-controller.md` against implementation: accurately describes deterministic rules, restrictions, additional SEC retrieval, float-boundary precision, no prose extraction, local-only review identity and outstanding live Nightshift/Nemotron.

Resolved findings: conflicting-row recheck no longer duplicates citation IDs; oversized Decimal inputs fail validation before arithmetic. Memory worker now preserves live owner locks and recovers abandoned PID locks; a killed-before-owner-file-written lock remains fail-closed and may require manual local cleanup. This is a local-state availability limitation, not permission to discard a live lock.

Not established: genuine model reasoning, semantic embeddings, authenticated multi-user human review, original-source decimal precision, independent issuer-release ingestion, arbitrary prose/quote extraction, an independent second fiscal-calendar mapping, live Nightshift/Nemotron, Cursor qualifying human edit. The controller is explicitly incomplete and every report requires human review.

## Final staged review

After two real CLI cases were added, the final full suite ran again: `.venv/Scripts/python.exe -m pytest backend/tests -q` — **118 passed, 58 subtests passed**, exit 0, 16.07s, same existing warning. Actual killed-Node-owner lock recovery and owner-preserving contention tests ran in this final suite.

`git diff --cached --check` — exit 0. Actual 61 Git-index blobs scanned in memory for configured private endpoint/key/contact strings: zero matches. Private values were never printed. Existing external secure configuration SHA-256 matches the preserved baseline. Sixteen accepted API/frontend/provider code/schema files are byte-identical to main fb0bfdb; provider provenance documentation is intentionally updated. The new input schema exactly equals `InvestigationInput.model_json_schema()` and its example validates through both JSON Schema and Pydantic. All five vendored H-MEM modules match both the pinned manifest SHA-256 values and the previously verified public reference source byte-for-byte.

One documentation finding was returned to Director: the first paragraphs of provider provenance retained stale 'no H-MEM application memory has run' / 'until controller implementation' wording despite the new integrated feature. This requires replacing stale current-tense claims with historical context. No new application-code blockers remained in final independent tests.

Director repaired the stale provider provenance wording. Independent focused reread confirms current application memory and five public vendored modules are described accurately; final staged whitespace check exits 0. Documentation finding resolved; no blocking findings remain within the tested scope.
