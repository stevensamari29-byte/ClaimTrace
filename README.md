# ClaimTrace
Help financial analysts check the accuracy, context, and supporting evidence behind corporate earnings claims before using them in research.

Foundation: React/Vite → FastAPI → attributed financial evidence, with a deterministic GAAP net-margin calculation. This is a working evidence foundation; the autonomous investigation controller and live model inference are still pending. Every result requires human review.

Use the existing private repository: `https://github.com/stevensamari29-byte/ClaimTrace.git`. Python 3.11+ and Node 22.12+ are sufficient; the verified workstation uses Python 3.14 and Node 24. No Docker, new cloud services or model credentials are required to run this slice.

```powershell
git clone --branch codex/mvp-foundation https://github.com/stevensamari29-byte/ClaimTrace.git
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

Configuration names are documented in [.env.example](.env.example). Set environment variables in the backend process or an approved local launcher. `SEC_CONTACT_EMAIL` is also read from Git-ignored `.env.local`, with the process environment taking precedence. The backend constructs `ClaimTrace Hackathon Team <approved email>`; missing, placeholder and GitHub noreply contacts fail before network access. The existing Zetaris configuration can be referenced using `ZETARIS_CONFIG_PATH` outside this repository; do not copy it or commit private endpoints, keys or personal configuration. Switching the dropdown to Zetaris currently shows blocked financial integration until the isolated dataset/view is created and verified. Its scoped creation is approved; the real SEC contact is still missing. No cloud writes run on startup or investigation requests.

Sponsor integration status:

| Existing component | Actual reuse / interface | Demonstrated and tested | Mocked, blocked or remaining |
|---|---|---|---|
| Hackathon HQ | Existing native implementation agents plus different independent QA; HQ remains separate | Existing 26 regression tests pass; product review evidence in `work/` | No HQ private files/configuration copied; no replacement orchestration |
| AWS-hosted Zetaris | `backend/zetaris.py`, existing external secure configuration and official SQL proxy | Actual product-module read-only inventory succeeded | No financial dataset exists. Cloud scope approved; real SEC contact still required. Execute the SEC REST table/view proposal using existing privileges, then prove real backend financial SQL and errors |
| Meterless H-MEM | Existing pinned reference design informs `backend/providers/interfaces.py` reviewed-memory boundary | Interface prepared; prior reference conformance is historical evidence | Controller/persistence/corrections/recall not integrated. Reuse the reference during controller implementation and test provenance, approval, lineage, isolation and restart behavior; mock embeddings are not semantic inference |
| Meterless client | Portable nonsecret `backend/providers/meterless_client.py` and its existing 13 tests reused | Local HTTP/mock auth, normalization, redirect and error checks | No live Runtime or model completion. Connect a supported authorized host and retain actual discovery/response evidence |
| Nightshift + NVIDIA Nemotron | Intended primary Runtime; provider protocol and configuration prepared | No live inference performed | Supported host, permitted provider access, real routing ID and bounded model receipt still required; see backend README |
| Cursor | Existing installation preserved | No ClaimTrace human development contribution claimed | Eligible teammate makes a meaningful product edit; retain attribution, actual diff, test and explanation |

Four unassigned team issues: [Data & Backend](https://github.com/stevensamari29-byte/ClaimTrace/issues/1), [AI Agent & Reasoning](https://github.com/stevensamari29-byte/ClaimTrace/issues/2), [Frontend & UX](https://github.com/stevensamari29-byte/ClaimTrace/issues/3), [QA, Research & Submission](https://github.com/stevensamari29-byte/ClaimTrace/issues/4). Their ownership, dependencies, first tasks and acceptance criteria are ready for teammates to select. No invitations or assignments were made. Current evidence, limitations and approvals are in [work/foundation.md](work/foundation.md).
