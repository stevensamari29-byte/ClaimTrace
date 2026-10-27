# Final submission independent QA — October 26, 2026

Reviewer: native `/root/final_submission_qa`, separate from implementation and deck authors. Scope is the final organizer checklist and current `codex/live-nemotron` working snapshot. This reviewer changed only this evidence record; no production code, Git state, configuration, credentials, services, model calls, cloud data or account permissions were changed. No new package was installed.

## Final regression results

- `.venv/Scripts/python.exe -m pytest backend/tests -q`: **exit 0, 563 tests + 81 subtests passed**, 52.36 seconds. The only warning is the existing Starlette/httpx test-client deprecation. No optional package was installed to suppress it.
- From `frontend`, `node --test tests/*.test.mjs`: **exit 0, 47 passed**, 900.9 ms. This includes actual component rendering, returned trace/source handling, exact decimal representations, review binding, stale/replayed review failures, cutoff-empty reports, unavailable providers and bounded browser transport.
- From `frontend`, `npm run build`: **exit 0, 24 modules**, 1.56 seconds.

The full backend run includes the preserved controller/readers, actual vendored H-MEM worker tests, run/review persistence/concurrency checks, source/model gates, bounded transport and the new NVIDIA protocol/format/identity tests. Synthetic HTTP/model/financial fixtures remain fixtures; passing them is not live inference or sponsor compliance.

## Three genuine application examples

Inspected the Director's actual HTTP captures in `.local/submission/samples.json` and the three corresponding JSON files. This was an independent artifact inspection, not a fresh service request by this reviewer. Initial stale-server failures were not relabelled as success; the Director restarted only the verified owned existing API with existing authorized data pointers, then reran the requests. All final sample reports state `model_inference_performed: false` and required human review.

| Sample | Actual request and result | Verified details |
| --- | --- | --- |
| Supported | ISRG fiscal 2026 Q2, April 1–June 30, as-of October 25, GAAP diluted EPS `2.29 USD/shares`; run `10082dea-a551-4e0b-80ae-33dcc4decd87`; report partial, finding supported | Actual returned `live_zetaris`, three eligible facts, retrieval `ok: true`; actual EPS `2.29000000`, difference `0E-8`; real retrieve/recall/verify/challenge/conclude trace. |
| Contradicted | Same scope, assertion `9.99 USD/shares`; run `05f2b9a6-e87b-4e4e-b62b-b80531a133ca`; report partial, finding contradicted | Actual EPS `2.29000000`, difference `-7.70000000`; three initial `live_zetaris` facts and successful bounded cached-SEC recheck producing eight combined facts; both source labels remain explicit. |
| Cutoff excluded | Same quarter and EPS `2.29`, as-of July 20; run `1ad5e77e-d8e7-46ce-ac54-476278cbb3a3`; report blocked, finding incomplete | Both retrieval and recheck return `ok: true`, zero eligible facts, zero citations and no comparison. This is an honest cutoff result, not a retrieval-error fallback. |

Independently checked every returned evidence publication date is on/before its input cutoff and every report citation ID resolves to returned evidence. The permitted filing is the primary SEC ISRG 10-Q published July 21. The assertions are analyst test inputs, not invented issuer quotations. The recheck is not independent issuer corroboration; it is explicitly `cached_sec`.

The sample JSON captures review state when created. The Director separately demonstrated an explicitly labelled automated QA rejection and reload; that is not a human financial sign-off or memory correction approval. The existing store's automated persistence/digest/version/concurrency coverage passed in the full regression.

## Slide artifact inspection

Independently inspected the delivered PPTX ZIP structure: **six slides**, 38,579 bytes, SHA-256 `6a72cbbaf5ddafb33330ddec32b5f42300baa78830d37b682e105a3bc58a3537`, matching the deck author's validated file. Six PNG previews exist. Visually viewed slide 3 (actual sample table) and slide 5 (sponsor gaps); the content is readable without clipping in those inspected views.

Slide 3 accurately labels all examples as deterministic controller results and distinguishes live Zetaris from cached SEC. Slide 5 prominently marks Nightshift as a mandatory unmet gap, NVIDIA runs as genuine but partial with no accepted completed model briefing, H-MEM synthetic financial correction-test inputs/hash embeddings, and no documented qualifying Cursor contribution. The footer states internal review and Nightshift unmet. No submission-compliance claim is made.

The six-page PDF is a rendered preview assembled from actual slide PNGs, not an editable PDF export; the PPTX is editable. This reviewer did not open PowerPoint/Google Slides or independently re-render all six slides. The deck author's separate rendering/import/layout evidence is in `docs/slides.md` and ignored deck-preview artifacts.

## Sponsor and final-readiness limits

- **Nightshift remains a submission blocker.** The final bounded inspection record says installed official 1.2.7, status/discover exit 12 `E_UNREACHABLE`, no daemon/8088 listener, integrated Iris Xe/8 GB hardware below the advertised dedicated-GPU configuration, and no established supported cloud-only startup without local models. The app was not launched under an unverified prefetch configuration. This is not proof that the executable can never start. Direct NVIDIA and H-MEM do not satisfy the mandatory Nightshift-provider requirement.
- **NVIDIA calls are genuine but no complete accepted model briefing is established.** Current saved acceptance remains blocked with an unavailable-provider error and no accepted conclusion. Earlier genuine model-directed financial retrieval/calculation partials and safety failures must be preserved separately, not described as a successful end-to-end AI investigation. The explicitly configured public/internal Super requested/served pair retains identity-difference limitations; exact alias/weights/VL equivalence is not established.
- **H-MEM uses the real vendored engine** in source-backed review/persistence/recall tests and application recall. Correction-test financial data and hash embeddings are synthetic/deterministic. No semantic inference, actual financial sign-off or Nightshift inference follows from those tests. Financial evidence cannot be replaced by remembered text.
- **Zetaris remains functional** in the actual final sample captures, with real financial records, canonical issuer scope, publication dates/citations and correct cutoff behavior. No new cloud object is needed for these examples.
- **Cursor contribution remains undocumented.** Installation and a prepared review handoff are insufficient qualifying evidence.

The Director still must inspect the final Git index after staging for private configuration/credential artifacts; this reviewer's full run reads the existing index, which does not yet include every unstaged new file. Final README sample entries, public live-evidence summaries, video verification, repository/judge accessibility, current registered human roster, final PR-head review and actual submission/upload approval remain Director/human gates. A file name, local deck or passing test does not establish that a video was recorded, a judge can access the repository, or the entry is compliant. No merge, deployment, visibility change, external upload or submission was performed.

## Final documentation and retained-evidence recheck

After the Director completed the documentation/evidence pass, independently read README's three actual inputs/output excerpts, `docs/submission-readiness.md`, `docs/pre-existing-components.md`, `work/submission-samples.json` and `work/nvidia-live.json`. No new production code or tests changed, so the successful full regression was not repeated.

README now includes the exact common HTTP contract, the two input changes for each negative case, actual finding/report distinctions, source labels, arithmetic, original run IDs and response excerpts. It clearly states deterministic execution, analyst test assertions and required review. The excluded cutoff is qualified correctly: no eligible filing evidence, not a claim that no information existed anywhere earlier. Fresh clones must rerun inputs rather than assume this workstation's saved UUIDs exist remotely.

The committed candidate sample evidence contains three actual outputs; the contradicted case has persisted QA rejection version 1 with the explicit note that it is not human financial sign-off. Supported and cutoff cases still require review. This does not change their financial classifications or approve memory corrections.

The retained NVIDIA evidence contains the genuine Lightning `READY` receipt and **three blocked partial checkpoints**, with respectively **2, 1 and 8 actual provider receipts**. Every checkpoint is blocked; `accepted_completed_model_investigation` and `nightshift_provider_used` are false. Both requested and server-reported Super names remain visible with unresolved identity qualifications. The final `tool_choice: auto` transport is explicitly **not live-accepted after the organizer freeze**. A narrow read-only high-confidence key-pattern/personal-absolute-path check of this curated JSON found neither; this does not replace the Director's complete staged-index check.

The final readiness document correctly says **not ready to submit as compliant**, treats Nightshift as mandatory rather than optional, distinguishes real deterministic traces from NVIDIA partial calls, and identifies supported Runtime access, owner-approved merges/judge access, roster, asset review and actual uploads as remaining actions. Pre-existing-component disclosure separates private HQ infrastructure, prior foundation, existing sponsor connection, public pinned H-MEM, portable adapter, vendor software, new NVIDIA integration and new draft media. No qualifying Cursor edit, successful Nightshift inference, exact Super/VL equivalence, completed AI briefing or submission is fabricated.

No unresolved factual overclaim was found in these inspected documents. The video is still described as encoding/in-progress at this checkpoint; its final file, duration and playback have not yet been independently verified. Local media and repository access still require owner review and authorized sharing/upload.

## Finished video and submission copies: offline verification

The finished video is now present: `submission/claimtrace-review-demo.webm`, **4,222,765 bytes**, SHA-256 `0f1e518af2e0682948895b14792016f152e9791d18f50a295fcc8cb9af70e66d`. Independent offline parsing verified the EBML/WebM header, VP8 video (`V_VP8`) and Opus audio (`A_OPUS`), 3,925 blocks, and final block timestamp **181.109 seconds**. WebM contains no Duration metadata field; this is disclosed rather than inferred as a missing recording. The actual narration WAV has **181.183492 seconds** of PCM audio, agreeing with the browser receipt's **181.183479 seconds** (3:01.18), within the requested 1–4 minute range. The receipt records 1280×720, eight edited actual UI capture stages, local computer-generated narration, Nightshift unmet and no live-AI claim.

Byte comparisons verified that the final `submission/` video, PPTX, PDF and video receipt exactly match their generated `.local/submission/` originals. PPTX SHA-256 is `6a72cbbaf5ddafb33330ddec32b5f42300baa78830d37b682e105a3bc58a3537`; PDF SHA-256 is `908e88dd891e1ecf824e75824962b2135e7b15075be4d2c728176706dd47184e`. This is an edited demonstration artifact, not real-time screen recording or completed model inference. The Director observed the saved status and final blocked-Nightshift frame. Independent QA did **not** perform a complete audiovisual playback, assess every narration timing transition, or approve organizer format/accessibility requirements. Owner full playthrough and authorized sharing/upload remain necessary. The final staged-index secret scan remains Director-owned and pending at this checkpoint. No API, inference, browser operation, new dependency or production change was performed in this media check.
