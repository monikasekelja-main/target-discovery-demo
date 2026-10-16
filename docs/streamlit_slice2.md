# Streamlit slice 2: human review and local specialist handoff

Updated with [pre-save rationale advice](rationale_review.md). The original slice 2
verification below is retained; the new advice gate now precedes saving a review.

Implemented 15 October 2026. Use the existing `.venv` and launch command:

```bash
.venv/bin/python -m streamlit run streamlit_app.py
```

Restart an already running server after installing this slice so imported service
modules are reloaded. Open the local URL and select your saved workspace.
Browsing, local checks and simulated handoff require no API key. Live rationale
advice requires `OPENAI_API_KEY` in the server environment.

## Review an assessment

In **Challenge & review**, inspect the saved report if relevant, then choose the
report consulted for this new review, or explicitly choose **No agent report
consulted**. Click **Prepare human review**. The preview displays the canonical
assessment, its full digest, and the separate report digest and status. A stale
report requires acknowledgement as historical advice. Reports from another
assessment or with another canonical digest are rejected.

Enter the reviewer name/role and rationale, choose **APPROVE**, **DEFER** or
**AMEND**, check the draft rationale, acknowledge the feedback and exact local scope, then
submit. Unresolved or unavailable advice requires an explicit override with a
written reason. See the rationale-advice guide above.
The default is DEFER. An amendment also requires a revised next action; it creates
a new canonical draft and selects it for a separate review. Calculations,
scientific recommendation and thresholds are not editable here.

The prepared preview remains fixed across form submissions. Changing the report
selection requires preparing a new preview. Concurrent changes to assessment
content (including reused IDs), inputs, the current review, report bytes or report
status cause rejection. The UI does not silently refresh the submitted digest.
Agent readiness and PASS checks never create human approval.

## Create a local handoff

In **Specialist handoff**, **Preview local handoff** is enabled only for a current
explicitly approved, supportive assessment with passed assay prerequisites.
Inspect the exact canonical assessment, review and consultation provenance, then
acknowledge and create the local simulation. The existing antibody simulation
returns a request for mechanism-equivalence evidence. No message, order or model
call is sent. Other platforms remain illustrative discussion questions.

The transaction rechecks the previewed assessment, approval and consultation
receipt. Repeated submissions reuse the existing handoff; a new review invalidates
its current authorization while retaining historical events and provenance.
The response remains bound to handoff identity/version, assessment digest and
platform. Saved consultation provenance is inspectable separately from the packet.

## Storage and compatibility

`target_discovery/review/review_service.py` layers the new commands over the unchanged reference workflow.
`target_discovery/ui/ui_reviews.py` supplies the preview/forms. The original workflow, store, compiler,
agent prompts, fixtures and version bindings are unchanged. The legacy CLI remains
available with its existing semantics; these additional preview/receipt guarantees
apply to the new UI service commands.

Explicit submissions create two additive SQLite tables as needed:

- `review_receipts`: append-only review-linked consultation records, including
  explicit no-report choices, exact report-byte digest, report binding/status,
  acknowledgement, local scope and service version. A submission ID and request
  digest make retries idempotent; changing consultation creates a new review.
- `handoff_receipts`: append-only handoff-linked provenance with its exact review
  receipt, kept outside canonical assessment content.

New receipts are also recorded in the event history, which the existing CLI trace
export preserves. Old reviews/handoffs are not rewritten or backfilled. An old
approval does not claim consultation of a newly viewed report. Bundled examples
are read-only. Browsing and preparing previews do not create tables or modify runs.

Database changes use an outer `BEGIN IMMEDIATE` transaction. Existing amendment
and handoff commands run in nested savepoints, so validation failures roll back
both canonical changes and receipts. Report files are read and checked again just
before commit; this is a local application, not a distributed file-locking or
identity-authentication system. Reviewer identity is self-entered. Approval is
limited to local simulation and conveys no real experimental authorization.

## Verification

123 automated tests passed across numerical, contract, workflow, agent, UI and
new review suites. New checks cover stale IDs/content/inputs/reviews, changed
reports (including during submission), separate digests, historical acknowledgement,
wrong-assessment rejection, explicit no-report review, defer/amend, duplicate
submissions, rollback, handoff gates/retries, changed approvals, and preservation
of legacy provenance. Streamlit AppTest also submits review/amend/handoff forms
and checks disabled states and stale previews.

Browser QA at 1366 × 768 used an isolated temporary workspace, with an explicitly
scripted report. Verified pending-approval gating, exact assessment/report preview,
review form submission, and the resulting simulated handoff and response.

- [Gated handoff](visual-qa/slice2-handoff-gated.png)
- [Review form](visual-qa/slice2-review-form.png)
- [Handoff preview](visual-qa/slice2-handoff-preview.png)
- [Saved handoff provenance](visual-qa/slice2-handoff-provenance.png)
- [Cell-loss gate](visual-qa/slice2-cell-loss-gated.png)
- [Initial review with no report](visual-qa/slice2-initial-no-report.png)
- [Machine-readable verification](visual-qa/slice2-verification.json)

All pre-existing files under `demo-runs` and `recorded_examples` matched their
before-build SHA-256 hashes. The original `demo-A002` live v2 report remains current
and advisory-ready. No paid calls or approvals on the user's saved runs were made.
Live correction-cycle verification remains outstanding because the earlier live
run requested no revision. External handoff delivery, identity authentication,
and agent execution controls are outside this slice.

## Programme context addition (15 October 2026)

The Decision view adds a compact, read-only plaque-psoriasis / fictional DEMO-R1 heading and a collapsed programme hypothesis card. Scientific results now precede the detailed review and follow-up sections; current review status remains beside the next action. See [programme-context-v1](programme_context.md) for copy ownership, evidence boundaries, the 173-test regression result, 1366 × 768 browser inspection and the supplied presentation's missing slide 1/A1 limitation. Existing agent, review and handoff behaviour is unchanged.
