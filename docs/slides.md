# ClaimTrace six-slide review deck

Revised October 27, 2026 for the final organizer checklist. The editable review deck is `submission/claimtrace-slides.pptx`, with `submission/claimtrace-slides.pdf` as a rendered preview. Byte-identical local authoring copies/previews remain under ignored `.local/final-submission-deck`. The lead must review and upload/share approved assets with judges. This is an internal review draft, not a claim that the entry is complete or compliant.

## Slide content

1. **ClaimTrace — Earnings Brief Gatekeeper.** Quarterly financial claims, evidence and human review. Mandatory Nightshift provider integration remains unmet.
2. **Current investigation workflow.** The existing one-page app selects company, quarter, cutoff and an explicit analyst assertion; retrieves SEC evidence through SEC or approved Zetaris SQL; performs deterministic checks and bounded challenge/recheck; stores an immutable report and persistent human review. NVIDIA native proposals ran separately; no accepted completed model briefing is claimed.
3. **Three observed financial cases.** Actual HTTP outputs from the current application: EPS 2.29 is supported; EPS 9.99 is contradicted against 2.29, with difference −7.70; a July 20 cutoff excludes the July 21 filing and returns no eligible evidence. Actual source modes are `live_zetaris` and, during the contradicted-case recheck, `cached_sec`. These are explicitly deterministic controller results, not AI reasoning. The assertions are test inputs, not issuer quotations.
4. **Evidence and review safeguards.** Exact quarter, units and GAAP basis; calculation inputs; publication cutoff and citations; source fingerprints; approved/persistent/scoped H-MEM context which cannot override financial evidence. Human review is mandatory. Hash embeddings and synthetic financial correction-test inputs are disclosed.
5. **Sponsor functionality and gaps.** Zetaris financial SQL and the H-MEM engine function. NVIDIA hosted calls and partial native financial investigations are genuine, but a completed model briefing is not accepted. Nightshift1.2.7 has verified authenticated uncached NVIDIA Lightning inference and a native proposal. The financial proposal was rejected before evidence retrieval; no completed AI briefing is claimed. Cursor installation is preserved, but a qualifying human product contribution is not documented.
6. **Actions required before submission.** Resolve mandatory Nightshift provider use; confirm judge/repository access to the merged release; review the actual 1–4-minute video and deck; verify roster, pre-existing components, disclosures and final upload form. PRs #7–#13 are merged on main0a6f6fb. No deployment, public visibility change or submission is performed by this deck.

## Actual sample provenance

The deck reads `.local/submission/samples.json` and refuses to export if its supported and contradicted classifications are absent or its cutoff case contains evidence. The accepted actual runs supplied by the Director are:

- Supported: `10082dea-a551-4e0b-80ae-33dcc4decd87`.
- Contradicted: `05f2b9a6-e87b-4e4e-b62b-b80531a133ca`.
- Cutoff excluded: `1ad5e77e-d8e7-46ce-ac54-476278cbb3a3`.

Original assets remain preserved in ignored `.local/submission-originals-oct27`. Revised slides5/6 correct runtime startup and merge status; all six revised slides were rendered and visually checked, with independent inspection of5/6.

Source financial evidence cites [the SEC filing published July 21, 2026](https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm). Earlier failed sample attempts were not relabelled as success. The Director corrected only the existing local backend startup configuration and reran the actual HTTP requests before providing these outputs.

## Rendering and usage

The deck uses editable native tables and text, with primary-source and internal execution references in speaker notes. Six full-slide PNG previews are under `.local/final-submission-deck/deck-previews/`. Local authoring source is `.local/final-submission-deck/deck-source.mjs`, using the pre-existing bundled Artifact Tool; no package installation or external artifact publication is required.

PPTX structure/layout/font/import validation and visual inspection do not prove that the deck works in every PowerPoint/Google Slides version, satisfy sponsor eligibility, establish model accuracy, or complete a video. No final recorded video, upload or submission is asserted here.

Final local verification: six slides, three editable native tables, zero structure/layout/font findings, and successful first-party Artifact Tool re-import. All six full-size PNGs were visually inspected for clipping, overlap and factual disclosures. The delivered PPTX is byte-identical to the validated file, SHA-256 `4c79a0f1f823916e36111684e186516d191dcc2ec9fc01da9e3beb310fedda83`. It was not opened in PowerPoint or Google Slides.

`.local/final-submission-deck/claimtrace-slides.pdf` is a six-page **rendered preview PDF** assembled from the actual slide PNGs. Native Artifact Tool PDF export was unavailable because the bundled runtime lacks `#standard-fonts/Helvetica`; no package was installed or runtime modified. The editable deliverable remains the PPTX. Validation details stay private under `.local/final-submission-deck/deck-previews/`.
