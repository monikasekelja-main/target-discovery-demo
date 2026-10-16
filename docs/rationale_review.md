# Pre-save rationale advice

Implemented 15 October 2026. The review UI now follows **draft → check → revise or
explicitly override → save**. Existing reviews, including earlier inadequate
rationales, are retained. Submit a new review to supersede one; history is never
silently rewritten.

## Use it

1. In **Challenge & review**, select the consulted report (or no report) and prepare
   the exact assessment preview.
2. Enter your reviewer name/role, decision, rationale and any amendment.
3. Select **AI advisory check**, confirm the model, and click **Check rationale with
   AI (one paid call)**. The agent checks relevance, evidence consistency and whether
   the reasoning explains the chosen action. It can ask questions but cannot save,
   approve, rewrite your rationale or issue a handoff.
4. Read the feedback. Revise and check again, or explicitly override with a written
   explanation. Then acknowledge the feedback and record your human decision.

Changing the draft decision, reviewer, rationale, amendment, historical-report
acknowledgement or assessment preview invalidates the previous check. The backend
also rechecks current inputs, assessment, prior review and consulted-report bytes
at submission. A stale check cannot be overridden.

“No concerns identified” is limited advisory feedback, not scientific validation
or human approval. Unresolved concerns, inability to assess, local-only checking
and failed AI calls all require an explicit override and explanation before saving.
The explanation's minimum length is a completeness check, not proof of its quality.
The human remains accountable for the final decision.

## Live AI configuration

Start or restart Streamlit from a terminal where `OPENAI_API_KEY` is already set.
Do not enter the key in the UI or paste it into chat. The model is editable in the
UI; `TARGET_REVIEW_MODEL` can set its default. Without that setting the UI retains
`gpt-6-astra`, the model used in the preceding saved live run.

```bash
.venv/bin/python -m streamlit run streamlit_app.py
```

The explicit check button can make one paid request through the existing provider.
There are no automatic retries, background calls or silent model fallbacks. The
payload contains the canonical assessment and draft decision/rationale/amendment;
reviewer identity is omitted. The prompt treats all draft and assessment text as
untrusted data. The response must match a strict schema and quote actual draft
text. These constraints do not guarantee model accuracy or injection resistance.

**Local checks only — no AI** is an explicit alternative. It uses limited text
rules to flag a rationale lacking a relevant evidence or constraint reference.
For example, “this was not acceptable because of the cherries” receives a request
to name the relevant finding or constraint. This mode never grants semantic
clearance: even a rationale that passes those text rules requires an explicit
override of the missing AI review before saving.

## Audit and compatibility

`rationale_advisor.py` defines the advisory prompt, strict output schema and limited
local checks. `review_service.py` persists check requests before calling a model,
then stores completed, failed or stale results separately. The network call runs
outside the database transaction. Interrupted requests remain recorded without an
accepted result and cannot authorize a save.

Two additive tables, `rationale_checks` and `rationale_results`, hold the draft,
assessment/binding digest, model metadata, status and feedback. Review receipts
link to exact request/result digests plus acknowledgement and override provenance.
Handoff revalidates those records. Checks and results are also captured in the
existing event history. They never alter canonical assessment prose.

Current review provenance shows the saved advice, or labels older reviews as
predating rationale checking. No old record is backfilled. The original reference
CLI retains its earlier review semantics; the new mandatory pre-save gate applies
to the UI review service. Scientific calculations, thresholds, original agent
prompts and saved live-report bindings are unchanged.

## Verification and limits

138 automated tests passed across the numerical, contract, workflow, agent, review,
UI and rationale-advisor suites. The new tests cover missing checks, irrelevant
rationales, independent final acknowledgement, explicit overrides, edits that
invalidate advice, concurrent reviews, failed/malformed provider responses,
quotation validation, preservation of history and handoff provenance integrity.
The live-provider path was tested with a mock transport; no paid calls were made.

Browser QA at 1366 × 768 used an isolated temporary workspace. It confirmed the
local “cherries” feedback, rejection of saving without override, and disabled
saving after editing the checked rationale. No final review was saved in this
browser QA flow.

- [Irrelevant rationale feedback](visual-qa/rationale-cherries-feedback.png)
- [Edited draft requires a new check](visual-qa/rationale-stale-draft.png)
- [Preservation and test record](visual-qa/rationale-verification.json)

Live semantic quality remains unverified in this build because no API key was
available in the test server. A real AI check on a draft is the next acceptance
step; it does not itself finalize a decision.
