# ClaimTrace
Help financial analysts check the accuracy, context, and supporting evidence behind corporate earnings claims before using them in research.

Foundation: React/Vite → FastAPI → attributed financial evidence, with a deterministic GAAP net-margin calculation. This is a working evidence foundation; the autonomous investigation controller and live model inference are still pending. Every result requires human review.

Use the existing private repository: `https://github.com/stevensamari29-byte/ClaimTrace.git`. Python 3.11+ and Node 22.12+ are sufficient; the verified workstation uses Python 3.14 and Node 24. No Docker, new cloud services or model credentials are required to run this slice.

After the foundation PR is merged, teammates can clone `main` using the commands below. **Until then, use `--branch codex/mvp-foundation` instead of `--branch main`: main currently contains only the initial README.** Existing collaborators need private-repository access; this handoff does not invite people or share credentials.

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

Open `http://127.0.0.1:5173/` and select **Trace financial evidence**. On macOS/Linux use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. Vite forwards `/api` to the local backend; secrets stay server-side. These are local development servers, not a deployment.

```powershell
# Repository root
.venv\Scripts\python.exe -m pytest backend/tests -q
# frontend directory
npm run build
```

The default ISRG Q2 2026 response uses an **authentic cached SEC snapshot**, retrieved October 23, 2026, explicitly labeled `cached_sec`. Five current-quarter facts include revenue $2,892,300,000, GAAP net income $818,100,000 and diluted EPS $2.29. Exact units, period boundaries, inline-XBRL locators and original document hashes accompany each fact. This default request does not make a live SEC or Zetaris call. Other companies/periods use reusable live SEC retrieval when a real identifying `SEC_CONTACT_EMAIL` is configured. A failed live request is reported, never replaced silently with fabricated evidence.

Primary sources: [SEC 10-Q filed July 21, 2026](https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm), [original earnings release published July 16, 2026](https://isrg.gcs-web.com/news-releases/news-release-details/intuitive-announces-second-quarter-earnings-6). Quarterly and six-month values remain distinct. The initial API uses the 10-Q's publication date, conservatively excluding its facts before July 21 even though the issuer released some figures earlier. The issuer release was independently retrieved and checked, not represented as a completed issuer ingestion pipeline.

`shared/request.schema.json` and `shared/response.schema.json` define the machine-validatable contract; `shared/example.*.json` provide sanitized development examples. `POST /api/investigations` accepts company identifiers, fiscal year, period, cutoff and evidence backend. `GET /api/health` explicitly reports inference disabled. See [backend details](backend/README.md) for retrieval limits and current coverage.

Configuration names are documented in [.env.example](.env.example). Set environment variables in the backend process or an approved local launcher. `SEC_CONTACT_EMAIL` is also read from Git-ignored `.env.local`, with the process environment taking precedence. The backend constructs `ClaimTrace Hackathon Team <approved email>`; missing, placeholder and GitHub noreply contacts fail before network access. The existing Zetaris configuration can be referenced using `ZETARIS_CONFIG_PATH` outside this repository; do not copy it or commit private endpoints, keys or personal configuration. No cloud writes run on startup or investigation requests.

Live acceptance on October 23 succeeded after the owner privately configured the SEC contact. The existing Zetaris instance now has the approved CLAIMTRACE database, claimtrace container, three SEC REST registrations, and `claimtrace.sec_financial_evidence` view. The view contains five authentic facts: three current-quarter values and two prior-year comparisons. Actual backend SQL retrieves current-quarter revenue, diluted EPS and net income, labeled `live_zetaris`, and computes the margin; a cutoff before the filing excludes them. Live SEC retrieval independently returns five metrics, labeled `live_sec`. Evidence and independent checks are in [work/live-data.json](work/live-data.json) and [work/live-qa.md](work/live-qa.md).

For an authorized existing instance, set `CLAIMTRACE_ZETARIS_TABLE=claimtrace.sec_financial_evidence` alongside the external `ZETARIS_CONFIG_PATH` before starting the backend; select **Zetaris** in the interface. Set `CLAIMTRACE_SEC_MODE=live` to use actual SEC requests instead of the development snapshot. The owner's running demo has both configured. A fresh clone still defaults to the explicitly labeled authentic snapshot and has no private access. The SQL template records the approved setup; do not rerun its CREATE statements against existing objects.

Minimum live startup configuration, in the backend terminal before the existing uvicorn command:

```powershell
# Point to your already-authorized secure config, outside this checkout.
$env:ZETARIS_CONFIG_PATH = 'C:\path\to\your\existing-zetaris.env'
$env:CLAIMTRACE_ZETARIS_TABLE = 'claimtrace.sec_financial_evidence'
$env:CLAIMTRACE_SEC_MODE = 'live'
```

Privately create ignored `.env.local` with `SEC_CONTACT_EMAIL=` followed by your real approved monitored address. The loader reads that field only; other example variables need the backend process environment. Live Zetaris requires authorized access to the existing instance; a clone alone does not grant it. SEC-only live mode needs the contact but no Zetaris key. To use the development snapshot, omit `CLAIMTRACE_SEC_MODE=live`; its label stays `cached_sec`. For a read-only API check, submit [shared/example.request.json](shared/example.request.json) to `POST /api/investigations`, selecting `evidence_backend: "zetaris"` for the cloud path. Expect three `live_zetaris` records, one margin calculation and required human review; cutoff `2026-07-20` gives zero evidence. Do not recreate the verified cloud objects.

The four-role interface agreement and smallest next agent plan are in [docs/agent-handoff.md](docs/agent-handoff.md). It separates existing contracts from proposed agent extensions and identifies deterministic work that can proceed before Nightshift is available. No remaining role is assigned yet.

Sponsor integration status:

| Existing component | Actual reuse / interface | Demonstrated and tested | Mocked, blocked or remaining |
|---|---|---|---|
| Hackathon HQ | Existing native implementation agents plus different independent QA; HQ remains separate | Existing 26 regression tests pass; product review evidence in `work/` | No HQ private files/configuration copied; no replacement orchestration |
| AWS-hosted Zetaris | `backend/zetaris.py`, original external secure configuration, approved SEC REST tables and normalized view | Real financial SQL -> three current-quarter API records and calculation; source/date/cutoff checks passed independently | Financial retrieval demonstrated; initial view covers ISRG Q2 current/prior facts. Additional data scope needs approval; full controller still pending |
| Meterless H-MEM | Existing pinned reference design informs `backend/providers/interfaces.py` reviewed-memory boundary | Interface prepared; prior reference conformance is historical evidence | Controller/persistence/corrections/recall not integrated. Reuse the reference during controller implementation and test provenance, approval, lineage, isolation and restart behavior; mock embeddings are not semantic inference |
| Meterless client | Portable nonsecret `backend/providers/meterless_client.py` and its existing 13 tests reused | Local HTTP/mock auth, normalization, redirect and error checks | No live Runtime or model completion. Connect a supported authorized host and retain actual discovery/response evidence |
| Nightshift + NVIDIA Nemotron | Intended primary Runtime; provider protocol and configuration prepared | No live inference performed | Supported host, permitted provider access, real routing ID and bounded model receipt still required; see backend README |
| Cursor | Existing installation preserved | No ClaimTrace human development contribution claimed | Eligible teammate makes a meaningful product edit; retain attribution, actual diff, test and explanation |

Four unassigned team issues: [Data & Backend](https://github.com/stevensamari29-byte/ClaimTrace/issues/1), [AI Agent & Reasoning](https://github.com/stevensamari29-byte/ClaimTrace/issues/2), [Frontend & UX](https://github.com/stevensamari29-byte/ClaimTrace/issues/3), [QA, Research & Submission](https://github.com/stevensamari29-byte/ClaimTrace/issues/4). Their ownership, dependencies, first tasks and acceptance criteria are ready for teammates to select. No invitations or assignments were made. Current evidence, limitations and approvals are in [work/foundation.md](work/foundation.md).
