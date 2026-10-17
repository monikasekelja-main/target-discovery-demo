# Separate-copy verification — 16 October 2026

## Result

Stages A and B implemented as an offline patient-study rehearsal. The original guided source copy and GitHub repository were not changed. Local preview: http://127.0.0.1:8507/ .

## Checks completed

- Full unittest suite: **196 tests passed** (180 original, 16 patient-study tests). After final wording/deferral-display adjustments, all 23 targeted patient-study and original-guided tests passed again.
- New UI coverage: nine scenarios × two routes × four steps, with socket connections, retrieval and model calls blocked. Navigation, session review, input/route binding, approval eligibility and deferral checked. Nine audit regressions additionally verify evidence-derived nomination, blocked-state suppression, each shared approval prerequisite, independent parallel rationale, donor sensitivity/conflicts, split leakage/identity loss, specialist-scope invalidation and persistence across screens.
- Original replay verifier: four original guided steps and nine saved runs across three workspaces, four technical views per run; existing review, report, follow-up and handoff bindings valid. No saved-record mutation or external calls.
- Preservation: all **411 original packaged files** retain their pre-task hashes. **316 protected files** (saved data, original runtime, agent prompts, contracts, scientific workflow, review services and programme assets) match byte-for-byte in the new copy.
- Rendered browser inspection at **1366 × 768**: all four new screens inspected; Next and Start again navigation exercised. Longer review/action screens require a short vertical scroll; controls and content remain readable. Temporary viewport override reset afterward.
- Updated evidence screenshot saved beside the copy as `predictive-v2-evidence.jpg`.

## Changed files

Added:
- `target_discovery/predictive/__init__.py`
- `target_discovery/predictive/contracts.py`
- `target_discovery/predictive/replay.py`
- `target_discovery/ui/predictive_demo.py`
- `predictive_examples/study.json`
- `predictive_examples/scenarios.json`
- `tests/test_predictive_demo.py`
- `tests/test_predictive_decisions.py`
- `PREDICTIVE_DEMO.md`
- `PREDICTIVE_VERIFICATION.md`

Updated in this copy only:
- `target_discovery/ui/app.py`: new default experience; original experiences retained.
- `tests/test_guided_demo.py`: explicitly select the preserved original guide.
- `README.md`, `REPLAY_DEMO.md`, `GUIDED_DEMO_NOTES.md`: distinguish the new proposed study from the independent assay example.
- `SOURCE_MANIFEST.json`: refreshed package inventory and hashes.

## Limits

No patient data were accessed, model trained, perturbation executed, API called or experiment commissioned. Scenario outcomes and agent commentary are deterministic illustrations, not scientific performance evidence. Human decisions are session-only rehearsals, with no AI rationale checking. Existing full-workbench optional AI functionality is preserved and remains explicitly initiated by the user. Real execution is stage C and requires an approved dataset, real target identifier, compatible model, intended-use evaluation and operational ownership.


## Presentation audit closure

- Slide 4: inspectable invented donor/state comparisons now drive nomination; no positive label is accepted as proof. The simple demonstration rule and arbitrary units are explicitly marked unvalidated.
- Slides 5–6: missing annotation, service failure and unsupported operations return no nomination. Donor dependence, conflicting observations and unvalidated intended use retain uncertainty, scenario-specific follow-up and owner.
- Slide 7: both routes check independent prerequisite records; a supportive prediction with missing assay readiness or resources cannot be approved. Parallel biology has a separate fictional rationale and lab context, without claiming inferred patient subtype.
- Slide 8: linked scripted specialist request/reply states owner and effort limitation. Including the reply revises scope and invalidates the earlier review binding.
- Review clarity: rationale semantics are explicitly unchecked, with a scripted guidance example; DEFER is consistently a warning and its concern is the immediate next action.
- Navigation: selected scenario/route remain visible; the old guide is labelled Optional assay example.
- Limits remain deliberate: no real model evaluation, patient analysis, semantic rationale checking, durable new reviews or external handoff. The demonstration supports the narrative, not scientific validation claims.


## Final wording and navigation verification

- Full suite: **197 tests passed**, including a new plain-language/pending-review/navigation regression.
- Original replay verifier passed: nine saved runs, original guided path and existing review/report/handoff bindings; no external calls or saved-record changes.
- Browser: simplified screens inspected in the narrow application panel and at 1366 × 768. Next from the page bottom, Back and direct step navigation returned the main scroll position to zero. Start again is covered by the automated navigation test.
- New screenshot: `../predictive-final-preview.jpg`.
- Changes are limited to the separate copy's presentation module, UI regression test, documentation and manifest. The scientific evaluator, contracts, original saved cases, agents and calculations are unchanged by this polish.
- GitHub was not updated. The guided path remains entirely offline.


## Offline agentic-workflow explanation addition

- **200 tests passed**; original saved-replay verification also passed.
- New tests cover all five answers across nine scenarios and both routes with network/model/retrieval calls blocked; matching context bindings, blocked nominations, changed-scope review invalidation, unsupported-question rejection and UI answer refresh are checked.
- Added `target_discovery/predictive/explainer.py` and `tests/test_proposal_explainer.py`; updated the new guided UI and these documentation files. Original scientific evaluator, legacy agent implementation and saved records are unchanged.
- Step 3 panel and offline question panel inspected in the rendered browser. Answers are explicitly scripted, read-only examples, not live AI.
- GitHub remains unchanged.

## Optional live proposal chat — 17 October 2026

- Full regression suite: 206 tests passed. Six new tests cover single-request behavior, context binding, invalid citations, missing-key UI, mocked successful submission, context isolation and protected-record preservation.
- Saved public replay passed: four guided steps and nine saved runs across three workspaces, including review/report/follow-up/handoff bindings; no calls or saved-record mutations.
- Offline remains the initial mode. Live answers have no tools or persistent writes; context changes discard prior conversation.
- No real API call was made: OPENAI_API_KEY was absent from the server-launch environment. Mocked integration tests do not establish account access, selected-model availability or live answer quality.
- GitHub was not updated.

Rendered browser inspection confirmed the initial offline selection, optional live form, disclosure and disabled submission without credentials. All 411 original guided-copy files match their saved baseline. Existing manifest comparison shows only the intended UI and documentation edits; saved evidence, calculations, prompts and records are unchanged.

### Live checks and citation refinement — 17 October 2026

Two browser submissions with gpt-6-astra returned accepted live answers: a supportive-proposal explanation and a request to override the read-only boundary. The explanation retained synthetic-evidence limits and no recorded review; the override request was refused without approval, edits or messaging. Source excerpts were inspected. Switching to the inconclusive scenario cleared the previous conversation.

The first inconclusive-scenario answer was rejected by format/source checks. Its exact rejection cause was not retained. Inspection found that instructions specified excerpt length but omitted the cumulative 25-word-per-source constraint enforced by validation. The proposal-chat-v2 instructions now state that constraint explicitly, and sanitized validation errors identify structure, source, exact-excerpt or quotation-budget failures. This preserves fail-closed behavior and makes no automatic retry.

After this refinement, all 207 regression tests and the saved public replay passed. The original guided copy matches all 411 baseline files. Saved records remain unchanged. The user reports a successful HTTP 200 authentication check; the follow-up browser check could not proceed because port 8507 had no listening server. Acceptance of a live inconclusive-scenario answer remains pending. GitHub has not been updated.

### Completed live inconclusive check — 17 October 2026

After the keyed server restarted, the same inconclusive question was manually submitted once with proposal-chat-v2 and gpt-6-astra. The response passed schema/exact-excerpt/quotation-budget checks. It correctly identified unresolved status, no cell-state nomination, no intervention or proposed test, an ineligible predictive route and no matching human review. Its comparisons matched the proposal: 0.095 versus 0.10 and 1/4 donors for Th17-like cells; 0.035 versus 0.06 and 0/4 for other memory CD4 cells. It assigned comparison of an informative alternative to the Analysis lead and kept an independent parallel rationale separate from predictive support. Source excerpts and rendered output were inspected.

All manifest-listed files matched their pre-request hashes after this live check. No scientific records were modified. Combined live smoke coverage now includes supportive explanation, read-only refusal and an accepted inconclusive explanation, plus conversation clearing on scenario change. These samples are integration checks, not an estimate of model reliability across all questions. The earlier rejected response remains documented above; no automatic retries were introduced. The 207-test regression and saved replay passed after the code refinement. GitHub remains unchanged for user review.
