# ClaimTrace
Help financial analysts check the accuracy, context, and supporting evidence behind corporate earnings claims before using them in research.

Application on the integrated `main` branch (PRs #7–#12 merged October 27, 2026): React/Vite → FastAPI → existing investigation controller → attributed financial evidence, challenge/recheck, H-MEM recall and durable local report review. The browser uses deterministic investigation rules. The separate opt-in NVIDIA CLI now makes genuine hosted model calls and model-directed financial tool proposals; completed-investigation status, failures and model-identity limitations are recorded in [NVIDIA activation](docs/nvidia-activation.md). Nightshift Runtime integration remains unverified. Every result requires human review. See [standalone controller usage](docs/investigation-controller.md); the existing one-page frontend is preserved.

Repository (currently private; judge access must be enabled separately): `https://github.com/stevensamari29-byte/ClaimTrace.git`. Python 3.11+ and Node 22.12+ are sufficient; the verified workstation uses Python 3.14 and Node 24. No Docker, new cloud services or model credentials are required to run this slice.

The browser run/review integration and subsequent model-provider work are now merged into `main` through PRs #7–#12. Clone `main` with access to this repository and run the commands below. Live sponsor access requires separate authorized private configuration; credentials are not bundled in the clone.

```powershell
git clone --branch main https://github.com/stevensamari29-byte/ClaimTrace.git
cd ClaimTrace
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In another terminal in the repository:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/` and select **Start investigation** with an explicit analyst assertion. On `main` the browser invokes the real controller; this does not imply model inference. Saved investigation links restore the original report and review after refresh or backend restart. On macOS/Linux use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. Vite forwards `/api` to the local backend; secrets stay server-side. These are local development servers, not a deployment.

```powershell
# Repository root
.venv\Scripts\python.exe -m pytest backend/tests -q
# frontend directory
npm run build
```

The default ISRG Q2 2026 response uses an **authentic cached SEC snapshot**, retrieved October 23, 2026, explicitly labeled `cached_sec`. Five current-quarter facts include revenue $2,892,300,000, GAAP net income $818,100,000 and diluted EPS $2.29. Exact units, period boundaries, inline-XBRL locators and original document hashes accompany each fact. This default request does not make a live SEC or Zetaris call. Other companies/periods use reusable live SEC retrieval when a real identifying `SEC_CONTACT_EMAIL` is configured. A failed live request is reported, never replaced silently with fabricated evidence.

Primary sources: [SEC 10-Q filed July 21, 2026](https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm), [original earnings release published July 16, 2026](https://isrg.gcs-web.com/news-releases/news-release-details/intuitive-announces-second-quarter-earnings-6). Quarterly and six-month values remain distinct. The initial API uses the 10-Q's publication date, conservatively excluding its facts before July 21 even though the issuer released some figures earlier. The issuer release was independently retrieved and checked, not represented as a completed issuer ingestion pipeline.

`shared/request.schema.json` and `shared/response.schema.json` define the machine-validatable contract; `shared/example.*.json` provide sanitized development examples. `POST /api/investigations` accepts company identifiers, fiscal year, period, cutoff and evidence backend. `GET /api/health` explicitly reports inference disabled. The integration branch adds create/read/review routes documented in [the run/review interface](docs/frontend-integration.md); the legacy evidence endpoint remains compatible. See [backend details](backend/README.md) for retrieval limits and current coverage.

Configuration names are documented in [.env.example](.env.example). Set environment variables in the backend process or an approved local launcher. `SEC_CONTACT_EMAIL` is also read from Git-ignored `.env.local`, with the process environment taking precedence. The backend constructs `ClaimTrace Hackathon Team <approved email>`; missing, placeholder and GitHub noreply contacts fail before network access. The existing Zetaris configuration can be referenced using `ZETARIS_CONFIG_PATH` outside this repository; do not copy it or commit private endpoints, keys or personal configuration. No cloud writes run on startup or investigation requests.

Live acceptance on October 23 succeeded after the owner privately configured the SEC contact. The existing Zetaris instance now has the approved CLAIMTRACE database, claimtrace container, three SEC REST registrations, and `claimtrace.sec_financial_evidence` view. The view contains five authentic facts: three current-quarter values and two prior-year comparisons. Actual backend SQL retrieves current-quarter revenue, diluted EPS and net income, labeled `live_zetaris`, and computes the margin; a cutoff before the filing excludes them. Live SEC retrieval independently returns five metrics, labeled `live_sec`. Evidence and independent checks are in [work/live-data.json](work/live-data.json) and [work/live-qa.md](work/live-qa.md).

For an authorized existing instance, set `CLAIMTRACE_ZETARIS_TABLE=claimtrace.sec_financial_evidence` alongside the external `ZETARIS_CONFIG_PATH` before starting the backend; select **Zetaris** in the interface. Set `CLAIMTRACE_SEC_MODE=live` to use actual SEC requests instead of the development snapshot. The verified live demo used both settings; configure the backend process for each local run. A fresh clone still defaults to the explicitly labeled authentic snapshot and has no private access. The SQL template records the approved setup; do not rerun its CREATE statements against existing objects.

Minimum live startup configuration, in the backend terminal before the existing uvicorn command:

```powershell
# Point to your already-authorized secure config, outside this checkout.
$env:ZETARIS_CONFIG_PATH = 'C:\path\to\your\existing-zetaris.env'
$env:CLAIMTRACE_ZETARIS_TABLE = 'claimtrace.sec_financial_evidence'
$env:CLAIMTRACE_SEC_MODE = 'live'
```

Privately create ignored `.env.local` with `SEC_CONTACT_EMAIL=` followed by your real approved monitored address. The loader reads that field only; other example variables need the backend process environment. Live Zetaris requires authorized access to the existing instance; a clone alone does not grant it. SEC-only live mode needs the contact but no Zetaris key. To use the development snapshot, omit `CLAIMTRACE_SEC_MODE=live`; its label stays `cached_sec`. For a read-only API check, submit [shared/example.request.json](shared/example.request.json) to `POST /api/investigations`, selecting `evidence_backend: "zetaris"` for the cloud path. Expect three `live_zetaris` records, one margin calculation and required human review; cutoff `2026-07-20` gives zero evidence. Do not recreate the verified cloud objects.

The four-role interface agreement and original agent plan are in [docs/agent-handoff.md](docs/agent-handoff.md). The October 25 autonomous sprint expands Amari + Codex responsibility to the complete stack, with Alex and Danny supporting specialized data/access questions. Human QA is unavailable; native independent verification is recorded in `work/`. Historical issue assignments preserve attribution and do not block the authorized sprint. See [current integration boundary](docs/frontend-integration.md).

Sponsor integration status:

| Existing component | Actual reuse / interface | Demonstrated and tested | Mocked, blocked or remaining |
|---|---|---|---|
| Hackathon HQ | Existing native implementation agents plus different independent QA; HQ remains separate | Existing 26 regression tests pass; product review evidence in `work/` | No HQ private files/configuration copied; no replacement orchestration |
| AWS-hosted Zetaris | `backend/zetaris.py`, original external secure configuration, approved SEC REST tables and normalized view; reused by standalone controller | Real financial SQL -> cited current-quarter financial records; source/date/cutoff checks | Initial view covers ISRG Q2 current/prior facts. Additional cloud data scope needs approval; no new cloud objects created by controller |
| Meterless H-MEM | Public pinned store/retrieval/trust-ledger services reused in `backend/investigation/vendor/hmem`, Python adapter and bounded Node worker | Actual source-backed approval/rejection, persisted recall, feedback and reviewed correction lineage; product tests run the real engine | Deterministic hash embeddings are mocks, not semantic inference. Local human actor labels are not shared authentication. Memory never overwrites financial facts; see `docs/hmem-integration.md` |
| Meterless client | Portable nonsecret `backend/providers/meterless_client.py` and its existing 13 tests reused; parser/worker reused by NVIDIA extension | Protocol tests cover strict native calls, auth, redirects, sanitized errors and deadline termination; original text interface preserved | The Nightshift path has no live Runtime completion. NVIDIA execution is separate and does not establish Nightshift usage |
| Nightshift Runtime — mandatory | Existing official Windows installation/CLI inspected; required AI provider under the final organizer checklist | Version 1.2.7 installer checksum verified; final bounded status/discover attempt returns unreachable | **Submission blocker:** laptop lacks advertised dedicated GPU; supported cloud-only startup, authorized Runtime and native calls remain unverified. No local model loaded; see `docs/nightshift-windows-activation.md`. Direct NVIDIA and H-MEM do not replace this requirement |
| NVIDIA hosted Nemotron | `backend/providers/nvidia.py`, standalone `nvidia_run.py`, original restricted dispatcher and financial tools | Actual authenticated completion, native source extraction, real Zetaris queries and host financial verification; failures and final acceptance are retained separately | Browser remains deterministic. Exact public/internal Super route equivalence, underlying weights and VL capability are not attested; direct NVIDIA does not prove Nightshift or track compliance. See `docs/nvidia-activation.md` |
| Cursor | Existing installation preserved | No ClaimTrace human development contribution claimed | Eligible teammate makes a meaningful product edit; retain attribution, actual diff, test and explanation |

Historical assigned team issues (not the current active roster): [Data & Backend](https://github.com/stevensamari29-byte/ClaimTrace/issues/1), [AI Agent & Reasoning](https://github.com/stevensamari29-byte/ClaimTrace/issues/2), [Frontend & UX](https://github.com/stevensamari29-byte/ClaimTrace/issues/3), [QA, Research & Submission](https://github.com/stevensamari29-byte/ClaimTrace/issues/4). Their confirmed owners and remaining responsibilities are recorded in the issues and AGENTS.md. Preserve separate branches and reviewed PRs; coordinate shared backend routes before editing. Current evidence, limitations and approvals are in [work/foundation.md](work/foundation.md).

## Integrated controller and local review

To reproduce the current integrated workflow, use `main` and the environment and startup commands above. No additional cloud dataset or service is required for the explicitly labeled cached SEC path. Do not switch a shared checkout while another contributor is editing; use a separate checkout if needed.

An editable ISRG Q2 EPS assertion is a starting input, not an extracted issuer quotation or predefined result. The backend validates explicit dates, metric, unit, basis and Decimal strings, calls the accepted controller, and persists its actual report. Canonical issuer identity comes from the reader. Scope changes clear the earlier assertion. Findings verify structured financial inputs; automatic text interpretation remains unavailable.

Reports and append-only review history are stored in Git-ignored `.local/investigations.sqlite3`. Approve/reject sends the exact report digest and current review revision; a fresh GET confirms saved state. Stale or cross-report decisions fail with 409 and are not automatically retried. Review does not certify financial accuracy or approve an H-MEM correction. The reviewer label is server-derived local development metadata, not shared-user authentication. Keep these servers bound to `127.0.0.1`; public deployment is not provided.

Use [the truthful browser demo](docs/demo-readiness.md), [independent integration QA](work/run-review-qa.md), [finite financial evaluation](work/financial-evaluation.json) and [current sponsor-access status](docs/sponsor-path-status.md). The opt-in hosted NVIDIA path has separate actual receipts and limitations; no Nightshift inference or competition-compliance guarantee is claimed.

## Structured provider and exact received numbers

The structured inference changes, merged through PR #11, add an opt-in native tool-call adapter, a separate model-dispatch CLI and read-only reviewed H-MEM context. Browser runs continue using the accepted deterministic controller. No new dependencies or cloud objects are required. See [provider acceptance and access requirements](docs/structured-provider.md) and [submission materials](docs/submission-pack.md).

Evidence may now include `value_decimal`, preserving numeric text received from SEC, its authentic cache, or the Zetaris gateway before conversion to the compatible legacy numeric `value`. Verification and the evidence display prefer this exact text. Legacy saved reports still render. This cannot recover rounding already introduced upstream (including a Zetaris `DOUBLE`) and does not prove original filing rounding precision. Margin division remains explicitly bounded/rounded. Changed exact evidence invalidates the matching memory fingerprint; legacy evidence without the field retains its previous fingerprint.

Run frontend tests with `node --test tests/*.test.mjs` in `frontend`. Run the standalone default-no-network acceptance with `.venv\Scripts\python.exe -m backend.investigation.model_run shared/example.request.json`: exit 2 and a blocked report are expected until a real authorized provider is enabled. This command does not run an AI model.

For a reproducible no-network safeguard comparison, run `.venv\Scripts\python.exe -m backend.investigation.evaluate`. [Saved results](work/guardrail-evaluation.json) compare eight deliberately selected authentic-cache cases with an explicitly weak value-only ablation. This finite diagnostic is not general accuracy or an external model benchmark.

## Hosted NVIDIA adapter and activation

The hosted NVIDIA adapter and honest partial-inference receipts were merged through PR #12. Follow [secure activation and live evidence](docs/nvidia-activation.md). Public SEC disclosure input and provenance are provided in `backend/data/isrg-q2-2026-disclosure*.json`; `shared/example.nvidia.request.json` selects the existing approved Zetaris financial view. A private authorized NVIDIA key and existing Zetaris configuration are still required. Never rerun cloud CREATE statements.

NVIDIA schemas advertise only actions whose host prerequisites are satisfied, bind references to known IDs, and suppress unchanged repeated calculations. The model chooses the source span, financial interpretation and permitted actions; the original host gate still decides financial classifications. Optional one-time model-generated format correction is separately disabled by default, visible in output and included in the global eight-request/120-second budget. Rejected arguments are never automatically repaired. No website inference switch or model-report review persistence is claimed by this increment; the existing browser and its durable review workflow remain intact.

## Final submission gate — October 26

**Not ready to submit as compliant:** the final organizer checklist requires Nightshift as the AI provider. Its installed Runtime is unreachable, and no genuine Nightshift investigation has executed. The existing deterministic application works; direct NVIDIA has genuine partial execution evidence, but no accepted completed model briefing. Optional model improvements are frozen. See [the final readiness checklist](docs/submission-readiness.md), [pre-existing component disclosures](docs/pre-existing-components.md) and [independent final QA](work/final-submission-qa.md). PRs #7–#12 were merged into `main` on October 27, 2026. No HackOS submission or public deployment has been confirmed; the repository still requires judge access.

## Three actual sample inputs and outputs

These were executed against the real local HTTP API on October 26, using the existing approved Zetaris connection. They are **deterministic controller runs, not model inference**. The assertions are analyst test inputs, not issuer quotations. Full actual requests, reports, citations, traces and review state are retained in [work/submission-samples.json](work/submission-samples.json).

Common request to `POST /api/investigation-runs` (the website sends this contract):

```json
{
  "request": {
    "company": {"name": "Intuitive Surgical, Inc.", "ticker": "ISRG", "cik": "0001035267"},
    "fiscal_year": 2026, "period": "Q2", "as_of": "2026-10-25", "evidence_backend": "zetaris"
  },
  "claim_inputs": [{
    "id": "analyst-eps", "text": "Analyst test assertion: quarterly GAAP diluted EPS was 2.29 USD/shares.",
    "metric": "diluted_eps", "expected_value_decimal": "2.29", "unit": "USD/shares",
    "accounting_basis": "GAAP", "period_start": "2026-04-01", "period_end": "2026-06-30",
    "tolerance_decimal": "0"
  }]
}
```

| Actual case | Input changes from above | Actual finding / report status | Actual evidence and calculation |
| --- | --- | --- | --- |
| Supported | None: claimed EPS `2.29`, cutoff `2026-10-25` | `supported` / `partial`; human review required | 3 `live_zetaris` facts; actual EPS `2.29000000`; difference `0E-8` |
| Contradicted | Claimed value and assertion text use `9.99` | `contradicted` / `partial` | 8 combined `live_zetaris` + explicitly labelled `cached_sec` facts after a bounded recheck; actual EPS `2.29000000`, difference `-7.70000000` |
| Cutoff excluded | Set `request.as_of` to `2026-07-20`; claim remains `2.29` | `incomplete` / `blocked`; no supported financial conclusion | Both readers successfully returned zero eligible facts. The July 21 filing is excluded; this is not a service-error fallback |

Actual response excerpts, in the same order:

```json
{"run_id":"10082dea-a551-4e0b-80ae-33dcc4decd87","report":{"status":"partial","findings":[{"claim_id":"analyst-eps","classification":"supported"}],"model_inference_performed":false,"human_review_status":"required"}}
```

```json
{"run_id":"05f2b9a6-e87b-4e4e-b62b-b80531a133ca","report":{"status":"partial","findings":[{"claim_id":"analyst-eps","classification":"contradicted"}],"model_inference_performed":false,"human_review_status":"required"}}
```

```json
{"run_id":"1ad5e77e-d8e7-46ce-ac54-476278cbb3a3","report":{"status":"blocked","findings":[{"claim_id":"analyst-eps","classification":"incomplete"}],"model_inference_performed":false,"human_review_status":"required"}}
```

The original [SEC 10-Q](https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm) was published July 21. An earlier issuer release would need separate verified ingestion; the excluded-cutoff case does not claim no information existed anywhere before July 21. Returned traces include actual retrieval, H-MEM recall when evidence exists, verification, challenge, recheck and conclusion events. Recheck of the same issuer is not independent corroboration.

Saved local links use `http://127.0.0.1:5173/?run=<run_id>` on this workstation; fresh clones must execute the inputs to create their own IDs. The contradicted sample also has an explicitly labelled **automated QA rejection**, version 1, which survived browser reload. That is a persistence demonstration, not financial sign-off or an H-MEM correction approval. Source-hash and precision limitations remain visible in the reports.
