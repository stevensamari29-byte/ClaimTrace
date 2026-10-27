# Restricted model-to-tools dispatcher

`backend.investigation.dispatcher.RestrictedDispatcher` is a standalone execution
boundary over the existing controller contracts and financial tools. It does not
modify the API, website, readers, provider client or H-MEM workflow.

This remains an **incomplete agent implementation**. There is no authorized
Nightshift host and no live structured provider adapter. Tests use explicitly
labelled scripted protocol fixtures, actual deterministic verification, and mocked
reader returns. They do not establish AI reasoning or live sponsor inference.

## Host interface

Construct with the existing `InvestigationRequest`, at most three host-ingested
`TrustedDisclosure` objects (12,000 total characters), and optional initial facts.
Call `dispatch(json_text)` with exactly `{"tool": "name", "arguments": {...}}`.
Only the six schema-validated tools from `shared/model-tools.json` are allowed.
Unknown fields/tools, duplicate JSON keys, nonfinite numbers, malformed JSON and
responses above 64 KiB fail before effects. Failed attempts consume a call slot.
Do not construct disclosures, providers or retrievers from model-controlled URLs,
class names or configuration. Host ingestion must establish disclosure identity,
period and text authenticity before registration; exact quotation validation
alone cannot establish that upstream trust or semantic extraction accuracy.

The default retriever reuses the existing SEC/Zetaris process-isolated read tools.
It receives a defensive immutable-scope request and at most the remaining run
deadline (capped at 45 seconds). There is no SQL argument, command interface,
arbitrary URL fetch, cloud write, model memory write or human approval operation.
An additional investigation uses the existing SEC reader when starting in Zetaris;
the choice is explicit in code and not a model-supplied backend override.

The shared run allows eight attempted tools, ten transitions, 120 seconds and one
justified recheck, with zero automatic retries. One initial evidence query is permitted; another read must use the
justified additional-investigation tool, preventing repeated queries from bypassing
the recheck limit. Budgets cannot be increased above
these limits. Provider latency and retrieval latency share the original deadline.
Source batches are validated atomically for SEC issuer, dates, locator, document,
duration and optional SHA-256 format; 25 facts per batch, 100 total. Contrary
versions are preserved with stable hash-suffixed IDs. Updating evidence invalidates
old findings and reruns every claim's financial verification without resetting
limits. Fiscal-calendar identity is established by the existing scoped readers,
not independently derived from dates by the dispatcher.

All six quality checks must be selected for each claim before the host records a
challenge. Checks reuse the actual verifier (unit/period/GAAP/conflict/comparison)
and scoped ingestion (issuer/publication/provenance), retaining missing semantic
context and original float precision as explicit qualifications. Conclusions must
match host classifications and all comparable citations. The final report uses
canonical host findings and prose, not the unvalidated model briefing proposal.
Every report retains `human_review_status=required` and unverified semantic mapping.
Any provider/read/deadline/budget/validation failure is terminal: no supported final
conclusion is returned; previous findings are diagnostic only.

## Future Nightshift boundary

`run(provider)` expects a trusted adapter implementing the `StructuredProvider`
protocol: `propose(context=..., tools=..., deadline=absolute_monotonic_deadline)`
returns one bounded JSON tool proposal. The adapter must actually enforce that
deadline for the whole network operation, including response reads, and must not
leave background calls running after expiry. The dispatcher checks before and
after every call but cannot cancel an arbitrary dishonest Python callback; only
trusted, reviewed deadline-enforcing adapters may be installed. The production
retrieval adapter already enforces its wall deadline via a terminated subprocess.

The preserved `MeterlessClient.chat()` is text-only with its own fixed timeout;
it is deliberately rejected instead of guessed into structured compatibility.
Next work: implement genuine structured tool-call/response transport in that client
once supported authorized Runtime access exists, enforce bounded output and the
shared deadline, establish a real completion and underlying Nemotron receipt,
then independently test the complete model-directed workflow. Protocol declaration
is not proof of inference; reports retain `live_inference_verified=false`.

H-MEM sourced recall and reviewed corrections remain in the accepted standalone
controller. This dispatcher does not expose memory writes or weaken those reviews.
Connecting approved recalls into model context is a later scoped integration.

Tests: `python -m pytest backend/tests/test_dispatcher.py -q`. Fixtures are explicit
and no test here performs live inference, cloud writes or a fresh sponsor audit.
