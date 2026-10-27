# Independent run/review integration acceptance — October 25, 2026

Reviewer: native `/root/run_review_qa`, separate from `/root/run_api_build` and `/root/run_frontend_build`. Edit ownership is limited to the two independent acceptance-test files, this evidence record and `work/financial-evaluation.json`. No implementation, credential/configuration, Git, cloud dataset or model-inference mutation was performed.

**Final status: verified within the deterministic local run/report/review scope; no remaining blocking findings. Backend286 tests plus58 subtests, frontend46 tests and production build passed. No live model inference is claimed.**

## Initial review and repaired finding

Backend/store acceptance passed. One frontend decimal-representation compatibility issue was initially reproduced and has now been repaired/retested: the actual updated client sends valid `expected_value_decimal: "+2.29"`; the backend's Pydantic Decimal serializes it as `"2.29"`, retrieves actual Zetaris evidence and saves a supported report, but the client rejects the report as a substituted assertion because it compares the two spellings literally. Reproduced through the actual frontend helper, Vite proxy and API; saved run `15a20a87-0a30-42a3-a85c-9afd77fcbc33`. No fake result or review approval was displayed. The finding was sent to the Director and frontend engineer for a bounded repair without floating-point precision loss. Final repair and retest evidence appears below; no blocking finding remains.

## Directly inspected and executed

`backend/tests/test_run_review_acceptance.py` adds 27 independent API/store/evaluation cases. These use the actual accepted controller and the authentic checked-in SEC snapshot, with a temporary SQLite store and explicitly injected cache reader. Other dependency injections are test seams, not live service or inference evidence. Covered cases: immutable report and digest, fresh app/store readback, review history, stale/replay/cross-report rejection, concurrent compare-and-set from separate store objects, tampered report/history rejection, local-origin/host and JSON boundaries, forbidden browser actor/SQL/provider/path settings, sanitized runtime/validation errors, nested JSON, actual isolated H-MEM worker recall (empty, successful), and ineligible locator/issuer citation rejection. Automated review transitions are isolated tests, not actual human financial acceptance.

The eight deliberately selected cached-evidence financial cases are supported EPS2.29; contradicted EPS9.99; non-GAAP incomplete; wrong claim period incomplete; EUR units incomplete; unsupported causal claim unresolved; pre-publication cutoff blocked/incomplete; and incorrect50% margin contradicted. All eight matched their declared expected classification and retained citation/cutoff checks. This is a finite regression result, not general accuracy or AI reasoning performance. Inputs are human assertions/challenges; no primary source figures were fabricated. Full case results are in `work/financial-evaluation.json`.

Executed commands:

- `.venv/Scripts/python.exe -m pytest backend/tests/test_run_review_acceptance.py -q --tb=short`: exit0, **27 passed**, 1.49seconds; existing Starlette/httpx deprecation warning only.
- `.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short`: exit0, **286 passed plus58 subtests**, 22.22seconds; existing deprecation warning only.
- `node --test tests/*.test.mjs` in frontend before final compatibility/UX repairs: exit0, **36 passed**.
- `node --test tests/run-review-acceptance.test.mjs`: exit0, **4 passed**. These compile the actual JSX with existing esbuild and use actual React SSR to verify saved review versus contradicted findings, waiting controls, unconfirmed-review recovery, escaped notes and rejection of raw dispatcher/substituted identities. First-run test fixtures omitted the controller's required `rejected_evidence` array; fixing that test fixture resolved three errors. No application defect was attributed to those fixture errors.

## Actual HTTP financial investigations

Reused the Director-owned already-configured local API on127.0.0.1:8000. Four actual create requests called the accepted controller and existing readers, then GET readback matched the returned envelope exactly:

| Case | Actual output |
| --- | --- |
| ISRG2026Q2, Zetaris, EPS2.29 | Supported;3 `live_zetaris` facts; actual H-MEM recall event successful/count0; six real controller events; 3,052ms |
| ISRG2026Q2, Zetaris, deliberately false EPS9.99 | Contradicted; real challenge/recheck to SEC;8 retained combined `live_zetaris`/`live_sec` facts; eight real events;5,211ms |
| ISRG2026Q2, cutoff2026-07-20 | Blocked;0 evidence; incomplete finding and genuine bounded recheck;4,596ms |
| MicrosoftFY2026Q3, SEC, EPS4.27 | Supported;5 `live_sec` facts; same code, no company-specific modification; H-MEM recall successful/count0;1,945ms |

All cited dates meet their run cutoff and finding evidence IDs resolve. Source citations, calculations, report digests, exact scope, trace states and execution labels are retained in the JSON receipt. These are actual service calls, distinct from cached cases and protocol/SSR fixtures. Every report says `incomplete_no_live_model` and `model_inference_performed:false`.

## Actual review persistence and restart

Director reported performing a browser rejection with the explicit note `QA persistence test by Codex; not a human financial sign-off.` on run `e0095184-ba46-430a-be8a-caa1f630dd2b`, then stopping owned API process24212 and starting process33880 before reloading the same saved URL. That browser/restart observation is attributed to the Director.

After the new process was running, the independent reviewer directly GET-read the same run: `rejected`, review version1, one saved history record and report digest `6aea38608d92a37fc57c83fbe271deb1bbd0c559467bce3898dbfa0aa50a0054`. The report's immutable `human_review_status` remains `required`; report review did not approve H-MEM corrections. Actual stale-version0 and cross-report-digest POST attempts both returned409. Following GET still showed rejected/version1/history1, proving no silent overwrite. This proves persistence of the automated QA decision, not a human financial sign-off.

No live Nightshift/Nemotron execution, model-directed reasoning or semantic embeddings are claimed. H-MEM recall calls the actual preserved engine; its existing hash embeddings remain deterministic mocks. Existing full-suite memory-scope and restricted-model-proposal cases passed as tests, not live inference. Final staged-index/private-configuration checks remain Director-owned.

The complete 27-case independent backend file (including both ineligible-citation cases) was already included in the286-test run. A Director-requested final recount had begun before the no-repeat clarification arrived; it completed again with **286 passed plus58 subtests**, exit0,21.81seconds. No backend implementation/test changes occurred between those runs. Reproduce only the selected authentic cached classification cases with `.venv/Scripts/python.exe -m pytest backend/tests/test_run_review_acceptance.py -k authentic_cached_financial_evaluation -vv`; the full suite above already executed all eight.

## Final frontend repair verification

The frontend engineer repaired the decimal-identity finding with bounded exact coefficient/exponent normalization using BigInt exponents, without floating-point value comparison. The independent test adds equivalent plus-sign, leading-zero, scientific, signed-zero and34-digit representations, and rejects a one-unit change in the34-digit coefficient. The exact analyst decimal spelling remains in the request; the saved canonical report spelling may differ while retaining the same value. This is comparison of assertion representations, not recovery of source precision.

Final current `node --test tests/*.test.mjs`: exit0, **46 passed**, including five independent run/review/decimal UI cases. `npm run build`: exit0, **24 modules**,2.48seconds. This final run follows the engineer's canonical issuer label validation and report-detail UX repairs; no later implementation writes were reported. Canonical CIK-matched source labels remain separate from the submitted analyst labels. Findings and calculation scalars remain visible; nested auxiliary data has accessible details controls.

A real-helper retest of `+2.29` was attempted after the execution interruption, but both previously running local servers (8000 health and5173 page) were unavailable. The helper returned its explicit backend-unavailable error and no substituted result. This is an environment outage, not a repeated decimal failure. Director was notified and asked to restore only the previously authorized local servers; the independent reviewer did not access configuration or start replacement services. At that point live repair verification was pending the restart; the final successful receipt below supersedes that temporary outage.


## Final live repair acceptance

After the Director restored the same authorized local API/Vite servers, the independent reviewer executed exactly one real `startInvestigation` helper call through Vite/API with `expected_value_decimal: "+2.29"`, then `readInvestigation` GET. It completed successfully against live Zetaris, returned saved canonical `"2.29"`, supported classification and `model_inference_performed:false`. Run `70c5266f-18e0-4184-8ce3-c7344e06c8d5`, report digest `ba3b0111b778233c025b24a2c2dc7c21f36553a9bd9c93858c066a9ca20a2c0f`; saved GET digest matched. This independently closes the earlier real compatibility finding. Updated JSON receipt preserves both initial failure and successful repair.

All independent reviewer writes are complete. Final accepted commands/counts are backend286 plus58 subtests (no backend change after that run), frontend46 and production build24modules. No further broad reruns are needed absent new implementation changes. The Director retains final staging, Git-index secret/configuration checks, commit, push and PR authority. No application merge, deployment, paid access, cloud write, production memory approval or genuine model inference was performed by this review.
