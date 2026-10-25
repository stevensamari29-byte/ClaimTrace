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
