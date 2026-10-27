# Minimal frontend integration

Status: proposed HTTP boundary, awaiting Alex and Danny agreement in [existing issue #1](https://github.com/stevensamari29-byte/ClaimTrace/issues/1#issuecomment-6393032438). This is not an implemented API contract.

Preserve the existing one-page design and `/api/investigations` evidence-only route. Role 3 owns frontend display, not backend or agent implementation. The current route cannot demonstrate a controller run, activity trace or persisted review.

## Smallest proposed server boundary

- `POST /api/investigation-runs`: accept the existing `InvestigationInput` (`request` and explicit `human_assertion` claim inputs). Call the accepted bounded controller. Return `{run_id, report_digest, report, review}`. A synchronous response is sufficient; display returned events after completion without pretending they streamed live.
- `GET /api/investigation-runs/{run_id}`: retrieve the persisted, immutable report and current review.
- `POST /api/investigation-runs/{run_id}/review`: accept `{report_digest, decision: approved|rejected, comment}`. The server derives the trusted local reviewer, verifies the report digest/version, persists the decision and rejects stale review. A following GET must confirm it. Local labels are not multiuser authentication; do not expose this development service publicly.

Alex confirms route/storage ownership; Danny confirms controller/report mapping and review semantics; Amari confirms the interface. Keep local state ignored; no new service or account. Report review must not automatically approve an H-MEM correction. Keep required human review and no-live-inference labels explicit. Scope/date/provenance/budgets remain enforced by the controller, never trusted from browser output.

Before implementing, owners should share their existing branches and file reservations. No unpublished teammate work is assumed absent. Do not edit their files just because this proposal exists.

## Acceptance after agreement

Real browser request must invoke the controller against the approved reader, return actual trace, original human claims, findings, calculations, publication dates and citations. Verify cutoff/unresolved failures and that later form edits cannot relabel an earlier result. Approve/reject a specific report, reload and restart the server, and verify the stored decision remains; stale digest fails. Independent QA must distinguish fixtures from live services.

Until those routes exist, the functional browser demonstration is financial evidence retrieval only. The standalone controller/H-MEM can be demonstrated separately. Nightshift/Nemotron remains blocked and no genuine model-directed reasoning is claimed.

## Owner handoff clarification — October 25

The existing Issue #1 comments already request this boundary; do not post duplicate requests. No owner agreement or implementation branch was visible at the latest check. These details remain proposals, not invented production endpoints.

| Operation | Proposed minimum fields and behavior |
| --- | --- |
| Create | Existing `InvestigationInput`: `request.company`, `fiscal_year`, `period`, `as_of`, `evidence_backend: sec|zetaris`; one to three existing typed `claim_inputs`. Keep Decimal inputs as strings, explicit period start/end, units, accounting basis and `input_kind: human_assertion`. Do not accept browser configuration paths, credentials, SQL or fetch URLs. |
| Run response/readback | Versioned envelope with `run_id`, immutable `report_digest`, `report`, and `review`. Use the existing `report.schema_version` to discriminate controller versus dispatcher. Retrieval must return the original saved scope and report, not recompute or relabel it. |
| Review | `{report_digest, expected_review_version, decision: approved|rejected, comment}`. Initial review version is zero. Server checks report identity/digest AND review version atomically, appends the decision with server-derived reviewer and timestamp, increments review version, and returns the persisted record. A stale version/digest or different report fails with a conflict; no silent overwrite. Owners must define safe repeat-request semantics. |
| Errors | Distinguish invalid input (422), absent run (404), stale review (409), unavailable reader/provider and exhausted deadline. Preserve blocked/incomplete report state and known evidence instead of fabricating success. Exact error envelope requires owner agreement. |

Controller `claimtrace.investigation.v1` already has `request`, `original_claims`, `findings`, `reviewed_memory`, `trace` and an ephemeral `run_id`. Dispatcher `claimtrace.dispatcher.v1` uses `scope`, `conclusion.findings` and `diagnostic_findings`; it does not expose original claims, memory recall or a run ID in its report. Alex's stored envelope needs stable identity; Danny must provide the truthful report mapping and supported input shape. Never display blocked dispatcher diagnostics as completed conclusions.

PR #9 currently accepts the controller report shape, not raw dispatcher reports or the proposed nested envelope. Once owners agree, Role 3 will explicitly unwrap and validate that version, add supported human claim inputs, send the actual run request, and connect review/readback using the server's digest and review version. No automatic claim extraction will be implied by manually entered assertions.

Isaiah's end-to-end gate after those routes exist: actual create/read, supported and contradicted assertions, unresolved/missing evidence, cutoff rejection, source dates/links, real returned challenge/recheck events, approve/reject followed by reload and server restart, cross-report and stale-review rejection, unavailable provider and no fallback fabrication. Fixture render tests do not satisfy this gate.
