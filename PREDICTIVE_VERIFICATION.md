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
