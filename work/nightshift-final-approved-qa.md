# Independent QA — final separately approved Nightshift investigation

Reviewer: /root/sprint_independent_qa. Read-only actual artifact and code inspection; no credentials/environment read, network requests, model calls, retries or source edits.

## Verified actual outcome
- `.local/nightshift-final-approved-investigation.json` records2026-10-27T18:57:33.349015Z,8.878seconds,tested main d088bbb9474c46476bb3327002df677d516b4feb.
- Exactly one uncached provider receipt. It independently passes existing validate_nightshift_receipt. Requested,response,provider,routed model IDs all equal nvidia/nemotron-3.5-lightning-30b-a3b;provider nvidia;from_cachefalse. Receipt rcpt_req_jlykdkf6,decision req_jlykdkf6,response chatcmpl-3a439c4c-993e-4d27-b447-3e8864006eb5. Usage4586prompt+583completion=5169tokens.
- Host statusblocked,errorproposal_rejected. Diagnostictool propose_extracted_claims,phasegate,rulesource_binding_invalid,schema_issuesempty.
- This identifies the current run's tool and grouped gate rule. Canonical argument schema validation completed before the source-binding gate failed. It does NOT identify the exact failing field, retain raw arguments, or recover the earlier original proposal.
- Actual gate condition checks registered disclosure presence,exact sourceSHA256,start/end range,source substring equals quote,claim text equals quote,and exact registered period dates. One or more failed; evidence cannot distinguish which. Do not state a specific wrong hash/offset/period without further evidence.
- One host attemptedtool,zero registeredclaims,evidence,calculations,citations,traces,or acceptedconclusion;zero rechecks;humanreviewrequired. There was no Zetaris financial retrieval in this run.

## Safety and compatibility
- Inspected runner .local/nightshift_final_approved_acceptance.py requires main plus reviewedPR15ancestor and exclusive new .local/nightshift-final-approved-one-run.started marker; old diagnostic marker remains. Exactly one dispatcher.run,120second/8tool/1recheck/10transition/0automaticretry limits. Trusted disclosures, existingZetarisinterface and H-MEMadapter preserved.
- Main d088bbb tree independently equals reviewed ea61dc7 tree.
- Static Nightshift advertised schemas inline local refs and project const into equivalent enum; native decoding preserves tool/argument JSON before canonical gate. No proven schema/serialization compatibility bug established. Source-binding validation must remain intact.
- No additional model attempt or compatibility alteration justified by this evidence. Prior originalproposal remains unknown; earlier provider-unavailable attempt remains separate.

## Independent execution
- Local assertion script validating actual receipt,allmodelidentities,uncachedflag,exactdiagnostic,bounds,effectcounts,markers,singleinvocation and exactreviewedtree:exit0.
- Focused proposal-diagnostics and cloud-pin regression result supplied separately below after completion. Fixture tests do not establish a completed live investigation.

Conclusion: genuine Nightshift/NVIDIA native inference verified; financial workflow blocked at required source binding. No completed model-directed financial investigation, financial calculations or acceptedbriefing claimed. Owner submission/media/merge actions remain separately controlled.
` .venv\Scripts\python.exe -m pytest backend\tests\test_proposal_diagnostics.py backend\tests\test_nightshift_cloud_pin.py -q`: exit0,42passed,6.76seconds.
