# Independent ClaimTrace foundation verification

Reviewer: native agent /root/qa, different from /root/backend and /root/frontend. Scope: actual product code, shared schemas, authentic public snapshot, local API, bounded error cases, source/secret review. No implementation edits, cloud writes, model inference, Git staging or commits performed.

Initial independent commands:
- `.venv/Scripts/python.exe -m pytest backend/tests -q` — exit 0, 34 passed, 58 subtests passed; one upstream FastAPI/Starlette TestClient deprecation warning.
- `npm run build` in frontend — exit 0, Vite production build succeeded (23 modules).
- HTTP POSTs to http://127.0.0.1:8000: default SEC 200 partial with 5 cached_sec records; cutoff 2026-07-20 gives 200 blocked with 0; unconfigured financial Zetaris gives 200 blocked with 0; malformed period gives 422; health gives 200 and inference_enabled false.
- Initial proxy HTTP attempt to :5173 failed connection refused (exit 1); Director owns browser/live frontend verification and restart.

Primary source independently opened: https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm . Its three-month June 30, 2026 income statement supports the five selected snapshot facts: revenue 2,892.3 million USD; net income attributable to Intuitive Surgical 818.1 million USD; diluted EPS 2.29 USD/share; operating income 971.9 million USD; gross profit 1,960.4 million USD. These are quarter values, not six-month/YTD. Snapshot retains 20 comparative/current quarter/YTD records; API selects the five current-quarter records. The initial five-row import draft was replaced during implementation by backend/data/zetaris-proposal.sql: a proposed isolated REST-backed view, with three metrics/current records and two comparisons (five total); it remains unexecuted. No quarterly cash-flow claim is emitted. Source publication/filing 2026-07-21 is conservatively later than issuer release; cutoff test excludes all prior to filing. Hashes/fragment locators are present; independently fetching via web verifies amounts, not raw-byte hash equivalence.

Findings sent to implementer for cycle 1:
1. P1: live SEC companyfacts fy/fp describe filing; prior-year-only comparative was returned as requested current quarter. Reproduction FY2026/Q2 with only Apr–Jun2025 fact returned 2025 evidence. Repair requires validated filing reportDate anchor and regression.
2. P2: arbitrary request company name/ticker with ISRG CIK was echoed beside ISRG financial evidence. Repair requires source-backed identity or rejection, retaining CIK attribution.
3. P2: malformed Companyfacts shapes (list payload; facts list; units USD None) with valid submissions yielded HTTP500. Repair requires sanitized source failure.
4. P2: malformed mocked Zetaris row with javascript source URL and reversed dates yielded200 partial/live_queries. Repair requires provenance/date/period validation before evidence.

Initial source review: no private credentials/config copied into implementation. Environment/config values remain server-side. Source-pattern scan found only a historical HQ provenance reference in adapter tests, not a secret. Existing tracked README had no diff at inspection. Git ignores .env, .venv, caches, node_modules, dist, local private files. Pattern scanning is evidence, not a proof against every possible secret encoding. Meterless tests are explicitly local HTTP/mock tests; H-MEM is a protocol boundary only. Default API never calls inference. Zetaris DDL/import remain unexecuted proposals; discovery/sample tables do not demonstrate financial integration. Sponsor compliance is not established.

Focused independent repair retest (exit 0): malformed Companyfacts shapes now all503 with sanitized detail; wrong supplied name/ticker canonicalizes to Intuitive Surgical/ISRG; malformed Zetaris source URL/reversed dates now blocked. SEC selector now requires filing accession reportDate and removes older-only comparative; actual source inspection plus regression confirms the fix. Final stable generic Zetaris implementation independently inspected and retested: SELECT projects cik/company_name/ticker/fiscal_year/fiscal_period/reporting_period_end; every row must match request identifiers/labels and reporting-period end; identity is canonicalized from consistent source metadata. Date chronology, duration, URL and finite-number validation precede evidence output. No company-specific rewrite is present in generic retrieval. The isolated proposed view supplies source-backed ISRG metadata.

Final independent `.venv/Scripts/python.exe -m pytest backend/tests -q` - exit 0, 42 passed, 58 subtests passed in 8.22 seconds, one upstream deprecation warning. Frontend `npm run build` remained passed, no frontend source changes since its independent build.

Additional reviewer-written ephemeral TestClient checks (exit 0; no implementation files modified): valid mocked Zetaris row returns partial; wrong CIK, fiscal year, fiscal period, report end, future publication, javascript URL, Infinity, and YTD start each block with no evidence. A second issuer/noncalendar Q1 mock (AAPL) also passes the generic interface; this is test-only invented data used to verify routing/schema, never an authentic financial claim or live integration. Missing external config path returns blocked without exposing private path text.

Restarted actual backend :8000 HTTP checks - exit 0: default200 partial five ISRG facts; incorrect input labels resolve to ISRG; prefiling cutoff200 blocked0; unconfigured Zetaris200 blocked0. No live financial Zetaris query was claimed. Four findings are resolved in this bounded foundation. Autonomous controller, H-MEM behavior, live Nightshift/Nemotron and financial Zetaris acceptance remain incomplete/blocked as disclosed.

Nightshift factory and provenance reviewed: explicit opt-in environment gate, no network on construction, no use by startup/API. Adapter caps planned chat at128 output tokens/12000 input characters; live acceptance is a future single-request test blocked on supported host/hardware, real authorized runtime token, discovered Nemotron routing ID and inference authorization. No such request ran. H-MEM remains interface only.

Final result: independently verified local deterministic evidence foundation, with explicit sponsor integration limitations. Browser behavior/responsive inspection remains Director evidence. This is not acceptance of complete AI investigation or competition readiness.


Final Git-index acceptance after Director staging (33 candidate files):
- Independently read `backend/tests/test_repository_secrets.py`: it enumerates actual indexed paths with `git ls-files -z` and reads staged bytes using `git show :path`, rather than examining a replacement worktree or fixtures. It rejects private environment/keys/dependency environments and high-confidence credential patterns without printing their values.
- `.venv/Scripts/python.exe -m pytest backend/tests/test_repository_secrets.py -q`: exit 0; 1 passed in 1.50 seconds against the actual staged candidate.
- `.venv/Scripts/python.exe -m pytest backend/tests -q`: exit 0; 43 passed, 58 subtests passed in 7.52 seconds; same upstream TestClient deprecation warning.
- `git diff --cached --check`: exit 0; no whitespace errors.
- Reviewer independently read all 33 staged blobs through Git and scanned private workstation path/config/token patterns: exit 0, zero findings. Staged list consists only of ClaimTrace app/schema/public evidence/docs/tests, reusable portable nonsecret adapter and its tests; no unrelated project, private HQ configuration or credential files included. Existing README was extended with setup/status while preserving its original project statement.
- Director supplied separate actual browser evidence: frontend-to-API returned five cached SEC records and margin; July20 cutoff blocked with zero; Zetaris blocked with zero. This QA did not independently drive that browser session.

Final acceptance is for the local deterministic foundation and staged secret review only. Financial Zetaris integration remains awaiting concrete cloud-write approval/creation/read acceptance; H-MEM/controller/live Nightshift/Nemotron and competition compliance remain incomplete. This evidence update is Director-owned staging/integration next action; reviewer performed no stage, commit or push.


Final scoped acceptance after additional contract and SEC-contact changes:
- Independently inspected actual Claim/Finding models, regenerated response schema and tests. Findings now have required claim ID, evidence ID list, explanation and one of supported/contradicted/incomplete/unresolved. Tests exercise all four classifications, invalid enum/citation types and missing citation field. Actual API still emits empty claims/findings; schema examples are explicitly test fixtures, not completed investigation behavior.
- Independently inspected SEC identity loader. It loads only SEC_USER_AGENT from ignored product .env.local; process environment takes precedence and skips local-file reads entirely. Missing/reserved/placeholder contacts are rejected before any network call with sanitized descriptive error. Test-local files isolate this behavior; actual private contact/config was not created, read or output by QA. No retry loop was introduced.
- `.venv/Scripts/python.exe -m pytest backend/tests -q`: exit 0, 60 passed and 58 subtests passed in 9.53 seconds; one existing upstream TestClient deprecation warning.
- `.venv/Scripts/python.exe -m pytest backend/tests/test_repository_secrets.py -q`: exit 0, 1 passed in 1.72 seconds against the final actual staged blobs.
- `git diff --cached --check`: exit 0, no output. `git diff --name-only` before this evidence update: exit 0, empty, confirming implementation/docs at test time match the staged candidate.
- Current permission/blocker state supersedes earlier historical notes: owner APPROVED the specific isolated Zetaris cloud scope. Real authorized SEC contact remains absent, so cloud creation and financial SQL acceptance have not run. Approval alone is not working integration. Do not claim live SEC/sponsor/model completion.

No new findings in these scoped changes. Reviewer is finished writing; Director must restage this final evidence update before branch/commit. QA performed no Git mutation, cloud write, live SEC call or inference.


FINAL email-only configuration acceptance (supersedes earlier SEC_USER_AGENT setup history):
- Actual implementation now accepts bare SEC_CONTACT_EMAIL from ignored .env.local or process environment, constructs the fixed organization identity ClaimTrace Hackathon Team, and ignores raw SEC_USER_AGENT. Fullmatch/placeholder/reserved-domain/GitHub-noreply checks happen before network. Environment precedence skips local-file reading. Reviewer inspected these code and mocked/temp-file tests; no actual .env.local/private values were inspected or output.
- Full independent `.venv/Scripts/python.exe -m pytest backend/tests -q`: exit 0, 65 passed and 58 subtests passed in 22.32 seconds, same upstream TestClient deprecation warning.
- Independent `.venv/Scripts/python.exe -m pytest backend/tests/test_repository_secrets.py -q` against actual final staged blobs: exit 0, 1 passed in 9.51 seconds.
- `git diff --cached --check`: exit 0, empty output. Implementation working files matched staged candidate before this evidence-only update.
- No new findings. Real contact remains absent; scoped cloud approval persists, with no cloud creation, financial SQL acceptance or live SEC/model request performed. Director must stage this last evidence update. QA is done and will make no further writes.
