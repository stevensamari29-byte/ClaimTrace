# Controller run and review integration

Implemented on `codex/run-review-integration`, stacked after PR #9; no automatic merge. The October 25 expanded directive authorized this bounded takeover after current branches and Issue #1 showed no published implementation. Controller, readers, dispatcher, contracts, provider client and H-MEM logic are reused unchanged.

## Actual local HTTP interface

| Endpoint | Behavior |
| --- | --- |
| `POST /api/investigation-runs` | Accept existing `InvestigationInput` (`request` and one to three typed `claim_inputs`), run the controller with real H-MEM recall, save the immutable report and return its envelope. |
| `GET /api/investigation-runs/{run_id}` | Read that report and persisted review without another investigation or changing its cutoff. |
| `POST /api/investigation-runs/{run_id}/review` | Accept `{report_digest, expected_review_version, decision: approved|rejected, comment}`. Atomically check identity, digest and review version, append history and increment version. Initial version is zero. Stale, replayed or cross-report requests fail with 409. Reload before any deliberate subsequent review. |

Envelope: `{schema_version: "claimtrace.run.v1", run_id, report_digest, report, review: {status, version, history}}`. The report is the actual `claimtrace.investigation.v1` output. Original claims, findings, calculations, trace, challenges, citations, rejected evidence, limitations and reviewed memory are preserved. The digest covers the immutable report including its run ID. Review history is separate and does not change that digest. Readback detects changed report content.

History entries have a version, decision, comment, server-derived `local-human` label and UTC timestamp. This is trusted local development, not authenticated shared-user identity. Report approval does not certify the original claim, financial accuracy, model inference or an H-MEM correction.

Input retains company/CIK, fiscal period, cutoff, source enum, assertion, metric, Decimal strings, units, basis, period dates and tolerance. Browser input cannot supply SQL, credentials, configuration paths, arbitrary fetch URLs, reviewer identity or controller limits. Checks apply to structured financial inputs; automatic text extraction and semantic mapping remain unavailable.

Errors: sanitized invalid input 422, absent run 404, conflicting review 409, non-JSON 415, oversized body 413, unexpected execution/storage failure 503. Genuine blocked/incomplete controller outcomes remain saved reports with actual limitations. Duplicate keys, invalid numeric constants and deeply nested JSON are rejected. Host/Origin/peer checks restrict the local interface; bind the server to `127.0.0.1`. No public deployment or multiuser authentication is provided.

## Persistence and reuse

SQLite state is ignored `.local/investigations.sqlite3`, surviving process restart without a new service or cloud dataset. Analyst text and reports remain private local state, excluded from Git and fresh clones. Existing startup commands and the legacy evidence endpoint remain compatible.

H-MEM uses the existing store and `local-cli` scope. Recall is bound to fresh evidence fingerprints, company, fiscal period and cutoff. A successful empty recall shows zero memories. Report review never calls memory proposal/approval methods; correction review remains a separate explicit workflow.

The dispatcher still has a different report shape (`scope`, `conclusion.findings`, `diagnostic_findings`). It is not exposed as a live provider. Danny can later supply a reviewed adapter; blocked diagnostics must not become final conclusions.

## Browser and acceptance

The page accepts an editable analyst assertion, runs the real controller, displays returned activity after completion, and saves `?run=` for reopening. Scope changes clear prior assertion inputs. Canonical issuer names are displayed while submitted scope stays recorded. Review sends the exact digest/version and performs GET confirmation. Ambiguous failures never become assumed approval; 409 refreshes without resubmitting.

See [independent QA](../work/run-review-qa.md), [financial evaluation](../work/financial-evaluation.json) and [demo readiness](demo-readiness.md). The actual browser test retrieved live Zetaris evidence, showed controller/H-MEM events, saved an explicitly labelled QA rejection, and restored it after a backend restart. That test decision is not human financial sign-off. Isaiah should independently rehearse the complete browser/restart/stale-review flow before final recording.
