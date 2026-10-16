# Next slice preparation: exact human review and specialist handoff

Status: implemented on 15 October 2026. See [slice 2 usage and verification](streamlit_slice2.md).
The contracts below are the original preparation; the completion notes describe
the earlier read-only verification. Original saved runs and agent files are unchanged.

## Supportive v2 run — verified

Code: `<project-directory>`.
Data: the same directory's `demo-runs`. Run `demo`, current assessment `demo-A002`,
new attempt `live-v2-20261015-01`. Previous live model: `gpt-6-astra`.
Pre-run binding and file hashes are in
`visual-qa/live-v2-20261015-01-baseline.json`.

The CLI takes a run ID, not an assessment ID. Before the paid command, compare
`agent_layer.binding(*agent_layer.read_state(workspace, 'demo'))` with the baseline
and confirm the attempt directory is absent. Abort on any mismatch. Do not refresh,
amend, regenerate, retry or substitute an offline report automatically.

After the user executes the run:

1. Use `load_report` / CLI `show` to recompute currentness. Require the exact
   baseline binding, `demo-A002`, `agent-report-v2`, live mode and v2 prompt version.
   Distinguish currentness from readiness; a current failed report is still failed.
2. Compare database, all pre-existing reports/exports, canonical assessment digest
   and review digest with the baseline. Only new-attempt artifacts are expected.
3. Inspect the hypothesis question separately from `current_evidence`; confirm
   support is scoped to this experiment, with the same eight donors, unestablished
   independent replication and unestablished blockade equivalence/safety.
4. Validate each accepted call's citations against its captured source packet and
   inspect scientific interpretation. Exact quote membership is not entailment.
5. Select My saved runs / demo / demo-A002 / the new attempt in Streamlit. Inspect
   origin, status, hypothesis/finding, claim citation expanders, challenger checks,
   findings and citations, and the actual call history in rendered screenshots.
6. Inspect every challenger call for `REVISE` and subsequent analyst feedback/recheck.
   If none requested revision, record exactly: **Correction cycle remains untested
   in this live run; no revision was requested.** Do not invent a correction.
   If requested but not completed, report that distinct failure explicitly.

## Human review contract

Reuse the canonical `content_fingerprint(DecisionBrief)` as the assessment digest.
The review must identify run, assessment ID, full canonical digest, reviewer,
decision, rationale, actor mode and local-simulation scope. The UI must submit the
digest that the person actually saw; the backend must compare it with the current
assessment and fresh inputs inside the same transaction before committing. Matching
IDs alone are insufficient. Reject stale tabs even if the ID was reused.

Record consulted reports separately from canonical content: an append-only
consultation receipt linked to the review ID, containing run ID, attempt ID,
SHA-256 of the exact saved `report.json` bytes, its assessment digest, binding and
effective status at consultation. Re-read and verify those bytes at submission;
reject changed reports. Do not insert agent prose or its digest into the canonical
brief merely because it was viewed. Preserve existing review/schema compatibility
through an additive receipt store rather than rewriting old records.

A stale report may be retained as explicitly historical consultation with the
reviewer's acknowledgement; it cannot be represented as current advice. A report
for another assessment must not be attached as consultation for this review.
Consulting no report is permitted and must be explicit. A new review cannot be
deduplicated solely by canonical decision/rationale if its consultation differs.

Agent readiness, PASS checks, and successful execution never create human approval.
Existing approval of demo-A002 does not imply consultation or adoption of this new
report. Do not retrospectively attach it to an old approval. Require an explicit
human action for any new review. Amendments create a new canonical version and
require a new review; no silent adoption of agent wording.

## Specialist handoff contract

Keep existing supportive-result, assay-prerequisite, fresh-input and exact-human-
approval gates. Preview the exact canonical assessment and review used by handoff.
Carry any consultation receipts separately as advisory provenance, with their
report digests; never substitute an agent verdict for the review receipt.

At execution, transactionally recheck the previewed assessment digest, review ID,
approval decision, input freshness and report receipts. Bind the simulated response
to handoff ID/version, assessment digest and platform. Preserve current idempotency
and historical handoffs; changed review invalidates current handoff authorization.
No external messages, experiment orders or model calls are part of this slice.

## Acceptance checks before enabling controls

- Reject missing human approval despite an agent-ready report.
- Reject assessment/input changes between display and submission, including same-ID
  content changes; reject report replacement after consultation.
- Keep exact report digest separate from canonical digest and verify receipt links.
- Preserve prior assessments, approvals, reports and handoffs without backfilling.
- Test explicit no-report review, historical consultation and wrong-assessment rejection.
- Test changed consultation on repeated review, duplicate submissions, defer/amend,
  stale approval, and handoff retry without duplicate effects.
- Verify UI wording and disabled states in the browser, including local simulation
  labels and clear separation of canonical approval from advisory readiness.

Original preparation gap (now covered by the additive `ReviewWorkflow` service): `Workflow.review` computes the canonical digest at
commit but accepts no client-expected digest or report-consultation receipt. The
handoff likewise has no separate report provenance. The new service supplies these checks and receipts without altering the
reference implementation hashes. See the slice 2 document for implemented controls.


## Completed verification

`live-v2-20261015-01` is current, exactly matches the pre-run v2 binding to
`demo-A002`, and is ADVISORY_READY_FOR_REVIEW. There were two validated calls
(analyst, challenger), no retrieval and no revision. All 28 quotations were
revalidated against the captured source strings. The six claims preserve shared-
donor, replication, target-specificity, genetic-causality, modality and safety limits.

**Correction cycle remains untested in this live run; no revision was requested.**

All pre-existing workspace files, including the database, assessments, approval
records and earlier reports, match their pre-run hashes. Only the new attempt's
three output files were added. The UI was inspected at 1366 × 768, including
expanded analyst and challenger citations. A display-only omission was fixed:
current-evidence citations now appear beneath the summary as source labels and
plain text. No new controls, agent prompt changes or report changes were made.
All 16 UI tests passed, including a check for the summary quotation rendering.

Machine-readable verification and the separate report/assessment digests are in
[verification record](visual-qa/live-v2-20261015-01-verification.json). This is QA
evidence, not a human approval or consultation receipt for an existing review.
The next slice remains the exact-digest human-review and specialist-handoff design
above; no write controls or new authorization were introduced.

After resuming from the usage interruption, currentness and all pre-existing file
hashes were checked again and still match. The final 1366 × 768 screenshot is
[current v2 report](visual-qa/v2-current-report.png). The browser confirms the live
origin, advisory-only readiness, and separate hypothesis and evidence sections.
