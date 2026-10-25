# ClaimTrace
Help financial analysts check the accuracy, context, and supporting evidence behind corporate earnings claims before using them in research.

Application on the run/review integration branch: React/Vite → FastAPI → existing investigation controller → attributed financial evidence, challenge/recheck, H-MEM recall and durable local report review. The standalone controller remains reusable without the frontend. It is an **incomplete agent implementation**: live model extraction, reasoning and generation remain unavailable. Every result requires human review. See [standalone controller usage](docs/investigation-controller.md); the existing one-page frontend is preserved.

Use the existing private repository: `https://github.com/stevensamari29-byte/ClaimTrace.git`. Python 3.11+ and Node 22.12+ are sufficient; the verified workstation uses Python 3.14 and Node 24. No Docker, new cloud services or model credentials are required to run this slice.

The browser run/review integration is a separate reviewed branch/PR until explicitly merged; `main` does not automatically contain it. The verified foundation is merged into `main` through [PR #5](https://github.com/stevensamari29-byte/ClaimTrace/pull/5). Teammates with access to this private repository can clone and run it using the commands below. Live sponsor access requires separate authorized private configuration; credentials are not bundled in the clone.

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

Open `http://127.0.0.1:5173/` and select **Start investigation** with an explicit analyst assertion. On this integration branch the browser invokes the real controller; this does not imply model inference. Saved investigation links restore the original report and review after refresh or backend restart. On macOS/Linux use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. Vite forwards `/api` to the local backend; secrets stay server-side. These are local development servers, not a deployment.

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
| Meterless client | Portable nonsecret `backend/providers/meterless_client.py` and its existing 13 tests reused; structured extension behind a fixed worker | Local protocol tests cover strict native calls, auth, normalization, redirects, sanitized errors and deadline termination; original text interface preserved | No live Runtime or model completion. Connect a supported authorized host and retain actual discovery/response evidence |
| Nightshift + NVIDIA Nemotron | Intended primary Runtime; opt-in standalone structured-provider/dispatcher integration prepared | Default unavailable path demonstrated; protocol fixtures are explicitly not inference | Supported host, permitted access, actual native-tool compatibility, underlying Nemotron identity and bounded live receipt still required; see `docs/structured-provider.md` |
| Cursor | Existing installation preserved | No ClaimTrace human development contribution claimed | Eligible teammate makes a meaningful product edit; retain attribution, actual diff, test and explanation |

Four assigned team issues: [Data & Backend](https://github.com/stevensamari29-byte/ClaimTrace/issues/1), [AI Agent & Reasoning](https://github.com/stevensamari29-byte/ClaimTrace/issues/2), [Frontend & UX](https://github.com/stevensamari29-byte/ClaimTrace/issues/3), [QA, Research & Submission](https://github.com/stevensamari29-byte/ClaimTrace/issues/4). Their confirmed owners and remaining responsibilities are recorded in the issues and AGENTS.md. Preserve separate branches and reviewed PRs; coordinate shared backend routes before editing. Current evidence, limitations and approvals are in [work/foundation.md](work/foundation.md).

## Current integration branch and local review

To reproduce the new workflow before its approved merge, check out `codex/run-review-integration` in the existing clone, then use the same environment and startup commands above. No additional package, cloud dataset or service is required. Do not switch a shared checkout while another contributor is editing; use a separate checkout if needed.

An editable ISRG Q2 EPS assertion is a starting input, not an extracted issuer quotation or predefined result. The backend validates explicit dates, metric, unit, basis and Decimal strings, calls the accepted controller, and persists its actual report. Canonical issuer identity comes from the reader. Scope changes clear the earlier assertion. Findings verify structured financial inputs; automatic text interpretation remains unavailable.

Reports and append-only review history are stored in Git-ignored `.local/investigations.sqlite3`. Approve/reject sends the exact report digest and current review revision; a fresh GET confirms saved state. Stale or cross-report decisions fail with 409 and are not automatically retried. Review does not certify financial accuracy or approve an H-MEM correction. The reviewer label is server-derived local development metadata, not shared-user authentication. Keep these servers bound to `127.0.0.1`; public deployment is not provided.

Use [the truthful demo sequence](docs/demo-readiness.md), [independent integration QA](work/run-review-qa.md), [finite financial evaluation](work/financial-evaluation.json) and [current sponsor-access status](docs/sponsor-path-status.md). No live model reasoning or completed Nemotron/Nightshift integration is claimed.

## Structured provider and exact received numbers

`codex/structured-inference` builds on the unmerged run/review branch. It adds an opt-in native tool-call adapter, a separate model-dispatch CLI and read-only reviewed H-MEM context. Browser runs continue using the accepted deterministic controller. No new dependencies or cloud objects are required. See [provider acceptance and access requirements](docs/structured-provider.md) and [submission materials](docs/submission-pack.md).

Evidence may now include `value_decimal`, preserving numeric text received from SEC, its authentic cache, or the Zetaris gateway before conversion to the compatible legacy numeric `value`. Verification and the evidence display prefer this exact text. Legacy saved reports still render. This cannot recover rounding already introduced upstream (including a Zetaris `DOUBLE`) and does not prove original filing rounding precision. Margin division remains explicitly bounded/rounded. Changed exact evidence invalidates the matching memory fingerprint; legacy evidence without the field retains its previous fingerprint.

Run frontend tests with `node --test tests/*.test.mjs` in `frontend`. Run the standalone default-no-network acceptance with `.venv\Scripts\python.exe -m backend.investigation.model_run shared/example.request.json`: exit 2 and a blocked report are expected until a real authorized provider is enabled. This command does not run an AI model.

For a reproducible no-network safeguard comparison, run `.venv\Scripts\python.exe -m backend.investigation.evaluate`. [Saved results](work/guardrail-evaluation.json) compare eight deliberately selected authentic-cache cases with an explicitly weak value-only ablation. This finite diagnostic is not general accuracy or an external model benchmark.
