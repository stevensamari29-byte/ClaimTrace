# Independent live integration verification

Reviewer: native agent /root/qa; independent of implementation agent /root/backend. Follow-up scope: actual primary-source SEC and approved Zetaris financial slice. Reviewer may make bounded read-only source/API/SQL calls, but no cloud mutations, inference, Git staging/commits or private credential/contact export.

Current state: awaiting implementation agent setup/read readiness. User-approved isolated scope is one CLAIMTRACE Lightning database, one claimtrace container, three SEC REST registrations (revenue, diluted EPS, net income) and one normalized financial view. Real owner-approved SEC contact was supplied privately and silently validated by Director. Earlier missing-contact blocker has therefore changed; actual financial integration still requires measured queries.

Acceptance: real ClaimTrace backend retrieval using Zetaris SQL, three current-quarter facts (ISRG revenue2892300000USD, dilutedEPS2.29USD/shares, GAAP netincome818100000USD), view ledger with two comparative facts and three current facts; authentic SEC provenance, correct fiscal labels/date chronology, publication cutoff, and no cached/mock substitution. Expected source mode live_zetaris, with explicit AI/H-MEM/Nightshift limitations retained. A failed source/query remains failed or blocked, never simulated success.

Evidence pending. This file is a plan/evidence record, not a PASS. No cloud/source/model call by QA yet.


Independent live SEC evidence: product `.venv/Scripts/python.exe` script called `backend.sources.get_json` once for https://data.sec.gov/api/xbrl/companyfacts/CIK0001035267.json using its actual privately configured identity. Exit 0; live read passed. Asserted returned CIK, exact accession0001035267-26-000058, current Apr1-Jun30 dates, filed2026-07-21 and three amounts/units against expected authentic values. Retrieved raw Companyfacts SHA2563419d6820891488e2d57eb100dd14e3a3cd21f7eae1564b8307540b2c91f5953 matches the earlier authentic source snapshot. No private contact/header/config/error body was emitted. No retry performed. This proves actual primary-source retrieval, not yet Zetaris financial integration.


Independent actual Zetaris financial acceptance: PASS

Reviewer used the existing product backend.zetaris.query/result_rows functions and a server-process reference to the original external secure configuration (not copied or printed). Every SQL statement was SELECT with LIMIT25; no cloud mutation, fallback fixture or inference occurred. Read-only script using `.venv/Scripts/python.exe` exited0.

1. SELECT normalized public financial columns FROM claimtrace.sec_financial_evidence LIMIT25 returned exactly5 rows. Asserted all CIK0001035267/tickerISRG/fiscal-periodQ2, canonical source identity, source SEC accession0001035267-26-000058, source URL under that original10Q document, publication2026-07-21, and period/reporting-end equality. Three rows are FY2026 Apr1-Jun30; two are FY2025 Apr1-Jun30 comparatives, not mislabeled current facts.
2. Current amounts and units were asserted against independently retrieved authentic SEC data: revenue2892300000USD; dilutedEPS2.29USD/shares; GAAP netincome818100000USD.
3. Actual FastAPI TestClient POST /api/investigations with evidence_backend=zetaris made real cloud SQL requests. Result200/partial, exactly3live_zetaris facts, integration_status.zetaris=live_queries and one GAAP margin28.285448percent. Human review remains required; claims/findings remain empty. H-MEM and Nightshift are not connected by this operation.
4. Same actual handler request with as_of2026-07-20 returned200/blocked/zero evidence, proving real SQL publication filtering rather than cached local filtering. No evidence was substituted.
5. Second independent read-only script exited0. Its comparative-only SELECT (fiscal_year2025/fiscal_periodQ2/LIMIT25) verified exactly2authentic comparative values: revenue2440000000USD and dilutedEPS1.81USD/shares. These align with the original10Q independently reviewed in work/qa.md.
6. Independent HTTP POST to running http://127.0.0.1:8000/api/investigations also returned200 with3live_zetaris facts and1calculation. This exercised the running backend, in addition to the in-process actual-cloud handler test. Director owns separate frontend browser acceptance.

No implementation changes were needed during live acceptance; prior independent65tests+58subtests cover unchanged validation/error paths. No full regression repeat was required solely for server configuration/cloud-object state. Private SEC email, runtime headers, API key, organization ID, endpoint and raw error responses were never emitted by reviewer. Secret/index acceptance for new sanitized evidence is Director's next integration step.

Findings: none in this bounded actual financial slice. The required real SEC-derived Zetaris backend integration is now demonstrated, rather than inferred from sample-table discovery. The view is intentionally limited to the approved ISRG metrics/period pairs; generic API/configuration interfaces remain reusable. This does not establish complete product/competition compliance: autonomous controller, claim investigations, issuer ingestion, H-MEM application behavior, live Nightshift/Nemotron and genuine qualifying Cursor-edit evidence remain outstanding. QA created no cloud objects and performed no model call, Git stage/commit/push or external message. Reviewer writes complete.
