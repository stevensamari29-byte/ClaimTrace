# Independent Role 3 integration acceptance — 2026-10-24

Reviewer: native `/root/role3_integration_qa`, separate from the implementation author. Scope: the existing one-page React interface, compatibility and truthful presentation. Backend/agent/provider/shared-schema files are outside this reviewer's edit ownership. No cloud writes or model inference are permitted.

## Accepted branch dependencies

Read actual local diffs: `origin/main` (`84cc576`) to model contracts `aca07ec` changes nine contract/schema/test/documentation files; `aca07ec` to dispatcher/ownership `21464b4` changes ten dispatcher/gate/test/documentation files. The correct integration order is PR #7 contracts, then PR #8 dispatcher. Neither local diff changes the existing frontend, HTTP API, SEC/Zetaris readers, provider transport, controller, H-MEM adapter or vendored H-MEM source. Director verifies actual GitHub PR heads, bases and current teammate activity separately.

Read `work/model-contract-qa.md` and `work/dispatcher-qa.md` against the actual contracts/dispatcher implementation. Recorded independent results at those reviewed snapshots are 175 tests plus 58 subtests and 235 tests plus 58 subtests, respectively; they include repaired source-URL/provider-metadata findings and credential/provenance checks. No redundant full baseline has been rerun before frontend edits. No new blocking compatibility finding in these preparation-only diffs.

Danny's handoff: preserve the restricted schema/dispatcher, shared budgets and required review/unverified semantic mapping. Real structured Nightshift transport, supported authorized host, trusted disclosure ingestion, semantic validation and H-MEM model context remain outstanding. The current text-only adapter cannot be called genuine structured inference. The actual HTTP API currently exposes foundation evidence only; it does not provide dispatcher run traces or persisted review routes. Frontend availability cannot establish those capabilities.

## Frontend acceptance

Status: verified within the limited evidence-page/report-rendering scope; no blocking findings. Actual full-run HTTP integration and persisted review remain blocked on Alex/Danny/Amari's interface agreement. No backend review persistence or genuine model activity is claimed.

Independently read the actual `main.jsx` diff and new `investigation-api.js`. The existing route remains `/api/investigations`; only a fixed company/period/cutoff/backend request is sent. Returned scope must match the immutable submitted request. Form edits cannot relabel an earlier result. The page explicitly calls this evidence retrieval, explains absent controller activity, keeps review required and provides no fake approve/reject buttons. Backend/shared-schema/CSS paths remain unchanged.

Independent `frontend/tests/investigation-acceptance.test.mjs` has nine fixture/actual-source React server-rendering cases. Existing esbuild compiles actual JSX in memory; existing React server rendering inspects its actual output, with explicit test state injection. These tests do not exercise browser clicks or call a model. They cover visible original claim text, numerical/calculation/source/date/locator fields, rendered challenge activity only when returned, escaped untrusted text, retained submitted scope, honest cutoff-blocked/empty evidence, no fabricated trace or approval, malformed response rejection, unsafe URL schemes/credentials, no SQL/commands/provider settings sent, errors without fallback, labeled native form controls, disabled duplicate submission and accessible waiting announcements. Six separate implementation tests also run.

The first independent run had one failure while the Director changed source-link policy from SEC-only to any credential-free HTTPS primary-source link. The test was updated to the agreed policy: backend/host provenance determines authenticity, HTTPS alone does not. This was a concurrent contract adjustment, not an application security defect. All final tests pass.

Final commands and observed results:

- `node --test tests/*.test.mjs` in `frontend`: exit 0, **15 passed** (nine independent acceptance, six implementation).
- `npm run build` in `frontend`: exit 0, **24 modules transformed**.
- `.venv/Scripts/python.exe -m pytest backend/tests/test_foundation.py -q`: exit 0, **51 passed**, existing Starlette/httpx deprecation warning only.
- `.venv/Scripts/python.exe -m pytest backend/tests/test_repository_secrets.py -q`: exit 0, **1 passed**; this checks the actual existing Git index. Director must stage/review new frontend files and repeat the final index check before committing.
- `git diff --check`: exit 0; `git diff --name-only -- backend shared frontend/src/styles.css` returned no paths.

The historical 235 tests plus 58 subtests remain the dispatcher baseline; this frontend-only change does not justify rerunning unchanged agent/provider/H-MEM suites.

## Actual read-only service acceptance

Started the existing local FastAPI app on `127.0.0.1:8000` with the existing external secure configuration, existing `claimtrace.sec_financial_evidence` view and live SEC mode. Started existing Vite on `127.0.0.1:5173`. No secure configuration contents were emitted or changed; no cloud objects were written. Director performs separate browser verification against these running servers.

Executed the **actual new `requestEvidence` frontend helper**, with native fetch through the **Vite `/api` proxy**, to the actual API and existing Zetaris SQL reader. This is a genuine network request, not the fixture tests above. Sanitized observed receipt:

| Request | Actual result |
| --- | --- |
| ISRG fiscal 2026 Q2, cutoff 2026-10-23, Zetaris | `partial`; three `live_zetaris` evidence records; revenue 2,892,300,000 USD, diluted EPS 2.29 USD/shares, net income 818,100,000 USD; GAAP net margin 28.285448 percent |
| Same company/period/backend, cutoff 2026-07-20 | `blocked`; zero evidence and zero calculations |

All three returned facts cover 2026-04-01 through 2026-06-30 and cite [the actual SEC 10-Q](https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm), publication 2026-07-21, accession `0001035267-26-000058` and concept/date locators. Margin references the actual revenue and net-income evidence IDs. Both responses normalized to `isControllerReport:false`, zero trace events and `human_review_status:required`; no inference, persisted review or dispatcher activity was substituted. The existing endpoint accurately reports no autonomous investigation, no model inference and its source/normalization limitations.

Director separately reported actual browser verification of all three live Zetaris values, margin and publication/source links; editing the form name did not relabel the submitted result. Director retained a local ignored screenshot at `.local/frontend-live.png`. This browser observation is attributed to the Director; the independent reviewer's directly executed evidence is the helper/proxy/network request and actual-source render tests above.
