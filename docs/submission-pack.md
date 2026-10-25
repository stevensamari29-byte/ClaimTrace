# ClaimTrace submission materials for human review

Prepared October 25, 2026. This is editable slide/script/metadata content, not a submitted entry, recorded video or rendered slide deck. Main remains separate from the reviewed feature branches until the lead approves merges. Do not describe the product as a functioning model-directed AI agent while inference is unavailable.

## Short description

ClaimTrace checks quarterly earnings assertions against attributed SEC financial evidence, challenges incomplete checks, and keeps an immutable report with a persistent human review decision. Its restricted model interface is implemented and tested independently of the website; authorized Nightshift/Nemotron execution remains outstanding.

Intended users are analysts preparing earnings briefs. A wrong quarter, accounting basis or cutoff can make a plausible number misleading. The demonstrated value is visible evidence, reproducible checks and review history. User adoption, time saved and general accuracy have not been measured.

## Three-minute demonstration script

| Time | Show | Say |
| --- | --- | --- |
| 0:00–0:25 | Existing one-page company/quarter/assertion form | “We check an earnings assertion before it goes into a brief. This build uses real evidence and deterministic investigation rules; live model reasoning remains unavailable.” |
| 0:25–1:15 | ISRG fiscal 2026 Q2, April 1–June 30, as-of October 25, GAAP diluted EPS assertion 9.99 USD/shares; select configured Zetaris | “This is a deliberately false analyst test assertion, not an issuer quote. The existing remote financial view supplies SEC-attributed evidence. The controller challenges the mismatch and requests an additional SEC check.” |
| 1:15–1:50 | Actual returned trace, EPS 2.29, difference -7.70, SEC document link and July 21 filing date | “These are actual tool results. The source date, exact quarter and units are checked. A second read of the same issuer is not independent corroboration.” |
| 1:50–2:15 | Human review, saved link, reload/restart | “A human can reject the report with a note. The backend binds the decision to this report digest and revision. It persists after restart. This demo action is a test, not financial sign-off.” |
| 2:15–2:40 | July 20 cutoff run, no eligible filing evidence | “This 10-Q is not eligible before its filing date. The honest result is insufficient evidence; an earlier earnings release would need its own verified ingestion.” |
| 2:40–3:00 | Sponsor/status and architecture content | “Zetaris and the H-MEM engine operate for real. The structured provider is tested against protocol fixtures; a supported authorized Nightshift host and actual Nemotron tool execution are the remaining AI blocker.” |

Rehearse with the actual local servers and source configuration. If live data is unavailable, use the clearly labelled authentic cached SEC snapshot and disclose that switch. Do not replay a recording as current execution. Preserve a screenshot of an actual result, readable original citation, genuine trace and persisted review. Never show local credentials or contact configuration.

## Six-slide content

1. **An earnings number needs context.** Quarterly versus year-to-date, GAAP versus adjusted and publication date can change what a figure supports. ClaimTrace is designed for the analyst's final evidence check.
2. **One assertion, a traceable investigation.** Company + quarter + cutoff → restricted evidence tools → deterministic calculations → challenge/recheck → cited report → human decision. Model extraction and tool selection remain an unverified extension until a real provider runs.
3. **A wrong EPS claim triggers a real check.** Show the actual ISRG test assertion 9.99, SEC EPS 2.29, calculated difference -7.70 and the original filing link. Label the assertion as a test; show the current real trace rather than invented reasoning.
4. **Checks that survive a plausible answer.** Exact units/period/basis, source cutoff, conflicting evidence, source-backed memory, immutable reports and versioned reviews. Reference the finite regression cases and independent QA. No general accuracy or measured productivity claim.
5. **What the sponsors actually do.** Zetaris: real scoped financial SQL. H-MEM: actual store/recall/reviewed correction engine; deterministic hash embeddings. Nightshift/Nemotron: prepared restricted transport, real inference blocked. Cursor: only claim an attributed qualifying human edit when its diff/tests are retained.
6. **Next proof: a model that uses the guarded tools.** Obtain an authorized compatible host, verify native calls and Nemotron identity, run the complete bounded investigation and record an honest unresolved case. Human review stays mandatory. End with the actual private repository/demo access status, not an unapproved public URL.

Use actual screenshots from the running accepted branch after approval. This content has not been rendered into a deck or checked for final video timing.

## Reproducible guardrail comparison

Run `.venv\Scripts\python.exe -m backend.investigation.evaluate` from the repository root. The committed output is `work/guardrail-evaluation.json`. Eight deliberately selected diagnostic assertions use authentic cached SEC facts: correct EPS, false EPS, non-GAAP, wrong quarter, wrong unit, unsupported causal claim, pre-publication cutoff and false margin. The guarded verifier matched 8/8 declared outcomes. An intentionally weak value-only ablation matched 4/8 because it deliberately ignored cutoff, unit, period and accounting basis. This shows the effect of those selected safeguards, not superiority to a real analyst, external product or AI baseline. The cases were not randomly sampled; no generalized accuracy, speed or analyst productivity claim follows. The evaluation makes no live network or model requests.

## HackOS technical metadata draft

| Field/content | Prepared value or outstanding item |
| --- | --- |
| Project | ClaimTrace: Earnings Brief Gatekeeper |
| Repository | Existing private `stevensamari29-byte/ClaimTrace`; judge access/publication decision pending. Do not create another repository. |
| Stack | React/Vite; Python/FastAPI; SQLite immutable run/review storage; bounded Node worker for existing H-MEM; remote Zetaris SQL; SEC primary data. |
| AI status | Incomplete model-directed agent. Restricted proposals, dispatcher and provider transport prepared; genuine Nightshift/Nemotron execution not demonstrated. |
| Sponsor evidence | README matrix, `docs/sponsor-path-status.md`, `docs/structured-provider.md`, `work/run-review-qa.md`, `work/autonomous-sprint-qa.md`, `work/live-data.json` and `work/financial-evaluation.json`. Tests/fixtures are identified separately. |
| Pre-existing work | Hackathon HQ development infrastructure remains private and separate. Reused nonsecret Meterless adapter; public pinned H-MEM source/license retained under its vendor directory. Existing sponsor connection reused. Do not claim these were all written during the event. |
| Cursor evidence | A genuine attributable product contribution and its tests remain to be supplied/verified. Installation alone is not evidence. |
| Deployment/video/slides | Local app demonstrated; no approved deployment, uploaded final video or rendered final deck is claimed. This file supplies the script and slide content. |
| Team/eligibility | Lead must confirm current registered human roster, eligibility and final submission ownership after withdrawals. Historical GitHub assignments are not proof of eligibility or participation. |
| Rules | See official source links and unresolved track details in `docs/sponsor-path-status.md`. Full binding terms and direct-provider substitution remain unconfirmed; no compliance guarantee. |
| Deadline | October 27, 2026 23:45 UTC / 7:45 p.m. Eastern, per retained event evidence. Plan feature freeze October 26 evening. |

HackOS field labels, exact asset limits and required declarations must be checked against the actual submission form by the eligible owner. These draft fields are not represented as a completed form. No secrets, local configuration, personal files or private HQ contents belong in any uploaded artifact.

## Submission blockers and human decisions

- Approve reviewed PRs in dependency order 7 → 8 → 9 → 10 → this sprint; recheck each head/diff and retarget after approved merges. Nothing merges automatically.
- Provide legitimate compatible Nightshift/Nemotron access or disclose incomplete inference. Missing required sponsor functionality could disqualify an entry or prevent track eligibility; exact consequences require final binding rules. Passing fixtures cannot resolve it.
- Confirm a qualifying Cursor contribution and any mandatory sponsor evidence. Verify required development window, pre-existing-source disclosure and licenses against binding terms.
- Confirm current registered roster and eligible account ownership; no borrowed credentials or invented contributor claims.
- Rehearse and record the actual demonstration; render/review final slides; check audio, source readability and duration. Give judges approved artifact/repository access.
- Lead reviews final HackOS content and authorizes any publication/deployment/submission separately. No such action is performed by this draft.

## Freeze and maintenance handoff

Keep the stable run/review branch available while reviewing this opt-in adapter increment. No local LLM, Docker migration, new cloud dataset or account is needed. Startup and tests remain in README. Alex supplies only missing remote schema/coverage facts; Danny supplies only legitimate provider/runtime access facts. Codex can maintain the remaining code and independent tests. Preserve contributor attribution and request a branch link before overwriting overlapping work.
