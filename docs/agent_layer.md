# Evidence analyst and evidence challenger

**Agent layer v2 · 14 October 2026 · Python 3.10+ (tested on 3.12)**

This implements two bounded roles as an additive CLI companion to the version 3 reference workflow. The original calculator, fixtures, controller and approvals are unchanged. There is no UI.

## Design and implementation plan

1. Bind a review to one complete reference assessment and its captured input hashes. Refuse incomplete, blocked or stale input. Read the reference SQLite database in read-only mode.
2. Give the analyst captured evidence, exact source metadata, frozen predictive output, curated experiment concepts, the policy, confidence rubric and computed eligibility facts. Do not provide the reference narrative, hand-authored briefs, evaluation answers or alternative experimental outcomes.
3. Ask for a source-linked hypothesis, explicit uncertainties, an experiment/next-step rationale, and optionally one focused evidence reinspection. Execute only the validated local read-only search tool, using controller-owned target and snapshot IDs. Re-run the analyst once if it requested that reinspection.
4. Give the challenger the sources and analyst proposal. Ask for material defects and retained limitations, distinguishing blocking findings from cautions. Permit one targeted reinspection and one analyst revision. Recheck the revised proposal with the challenger once. Preserve unresolved disagreement.
5. Validate schemas, exact quotations, source and claim IDs, option IDs, retrieval scope, and agreement with numerical eligibility. Save an advisory report and full trace. A human reads it before deciding whether to keep, defer or amend the reference brief.

Maximum: **five model calls, two local retrieval calls, one challenge/revision cycle**. Each live request has a 120-second timeout and 4,000 output-token cap. Input sources are capped at 200 KB. These limits bound requests, not an exact dollar cost or total wall-clock time. There is no automatic network retry, model substitution or offline fallback. A refusal, malformed response, fabricated citation or budget violation produces a visible failed report. An interrupted attempt remains RUNNING and is never automatically repeated.

Only two logical roles exist. The controller, calculator and validator are ordinary code. Model selection and prediction applicability remain with the existing deterministic controller and specialist capability registry. No agent swarm, vector database or orchestration framework is required for this example.

## Install on your Mac

Keep your existing `demo-runs/` directory. Copy the new `agent_*.py` files and `verify_agents.py` from this package into your existing `decision-fixtures` directory, alongside `demo.py`. These additions require no new dependency. The original runtime files and baseline Python implementation have not changed, so existing approvals are not invalidated by adding these files.

If starting fresh, extract the whole package, then:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python demo.py start --run-id agent-case
python demo.py resume --run-id agent-case
```

If the virtual environment already exists, just activate it. The new CLI gives a clear version error on Python 3.9.

## Offline smoke test — no LLM

For your existing `demo` run:

```bash
python agent_demo.py run --run-id demo --attempt-id offline-01 --provider offline
python agent_demo.py show --run-id demo --attempt-id offline-01
```

Offline mode uses scripted responses and tests orchestration, citations, retrieval, reporting and immutability. It does **not** show live agent reasoning or establish scientific quality. Its labels and reports say `scripted_offline_test` and `model: none`.

If `demo` is already at the handoff stage, this reviews its current post-result assessment. To see the initial experiment recommendation, create a separate reference run with `start` and `resume`, as above, and use that run ID.

## Live analyst and challenger

The live adapter uses the OpenAI Responses API with strict structured outputs. Both roles use the model you explicitly select; the API response's resolved model ID and token usage are recorded. A separate API key and model access are needed. Set `OPENAI_API_KEY` in your local environment without placing it in source code or reports, and set `OPENAI_MODEL` to a Structured Outputs compatible model ID available to your account.

```bash
python agent_demo.py run --run-id demo --attempt-id live-01 \
  --provider openai --model "$OPENAI_MODEL"
python agent_demo.py show --run-id demo --attempt-id live-01
```

Live mode sends the current synthetic source packet and role prompts to the API; `store` is false. It enables no hosted tools, shell, browsing or arbitrary endpoints. Keys are read from the environment and are not written into traces. **Live API execution and biological reasoning quality were not verified in this build.** The HTTP request/response handling is tested with mocked responses; offline tests are not substitutes for a real provider smoke test.

Each attempt ID is unique. Reusing one is rejected before any model call. Use `show` to inspect it, or choose a new ID for an intentional new call. The report retains the final proposal, every intermediate output, tool request/response, prompt, schema, source text, hashes and usage metadata. It does not request or store private chain-of-thought.

## Read the result

Outputs live at `demo-runs/agent-reports/<run-id>/<attempt-id>/`:

- `report.md`: readable hypothesis, claims, critique, next step, limitations.
- `report.json`: complete execution trace and final status.
- `input.json`: exact supplied sources and assessment binding.

`agent_demo.py show` rechecks current hashes and assessment identity. A saved static report is historical: use `show` before acting on it.

| Status | Meaning |
|---|---|
| ADVISORY_READY_FOR_REVIEW | Structural checks pass, no unresolved challenger block and action agrees with fixed eligibility. Still requires human review. |
| NEEDS_EXPERT_REVIEW | Persistent critique, abstention or numerical-policy disagreement; no approval granted. |
| FAILED | Invalid output, provider refusal/failure or operational error. Partial trace preserved. |
| STALE | Bound assessment, inputs, prompts or implementation changed. Generate a new attempt against current inputs. |
| RUNNING | Attempt started; may be in progress or interrupted. Inspect trace before intentionally rerunning under a new ID. |

Exit codes: 0 = advisory ready, 2 = command/preflight rejection, 3 = failed, stale or expert-review report.

## Human decision integration

An agent report is a **companion to**, not a replacement for, the canonical reference brief. Neither role can approve, import an outcome, hand off, change a threshold or overwrite a decision. The existing `demo.py review`, `amend` and `handoff` commands remain the only workflow actions. If you adopt a suggested next-step wording, use `demo.py amend` with your own review rationale, then approve the new assessment. The old report becomes stale because it is bound to the prior assessment. Re-run the role layer if a new report is needed.

Agent report completion is not an additional enforced gate in the original workflow: the deterministic fallback remains usable by itself. Existing approvals do not approve the agent report. Do not present the agent text as part of a previously approved brief. Integration of accepted agent narrative into a separately versioned, review-bound canonical brief can be a later UI stage.

## What is validated, and what is not

The checker verifies that quotations are verbatim substrings of supplied source JSON and that IDs, schemas and controlled actions are valid. **A correct quote can still be misinterpreted.** Scientific entailment, omissions, relevance and the proposed next experiment need challenger and human assessment. The same model in two roles can share errors; this is not independent biological validation.

Numeric eligibility is supplied as a fixed fact. Matching that action is a constraint check, not an independent target-discovery benchmark. The value to evaluate is accurate interpretation of evidence, useful uncertainty handling and a better justified next step.

These targets and measurements are synthetic. No biology foundation model is executed. No confidence probabilities are generated. No result establishes efficacy, systemic safety or modality feasibility. Additional targeted retrieval reopens frozen records; it cannot discover new literature or resolve absent data.

## Verification and next evaluation

```bash
python -m unittest -v verify verify_contracts verify_workflow verify_agents
```

The new suite exercises all eight outcome branches, both role paths, one bounded revision, persistent disagreement, abstention, invalid citations, invalid claims, authority escalation, retrieval abuse, provider refusal, malformed/incomplete responses, stale bindings, duplicate-attempt protection, command-line operation and read-only baseline preservation. Faults are injected with test providers; this does not prove LLM resistance to prompt injection.

Before presenting live outputs:

1. Run one initial and one supportive case with your chosen model. Inspect every claim against the source and confirm the full report labels live mode.
2. Run contrary, imprecise, cell-loss, QC and method-disagreement cases using separate reference runs. The selected outcome alone enters each prompt.
3. Use `evaluation/agent_review_rubric.md` to score evidence interpretation, uncertainty and next-step quality. Review analyst-first and final challenged outputs separately to measure whether the challenger helped. Log model/version, prompts, latency, tokens, defects and human edits.
4. Only then expand to the planned 16 scenarios / 28 trials per configuration in `evaluation/workflow_scenarios.json`. The 56-trial two-configuration comparison is still a plan, not an executed result. Some operational cases are upstream controller checks, not distinct agent reasoning tasks; report those categories separately.

## Deferred appendix

Automatic report adoption into canonical briefs; semantic entailment classifiers; calibrated support probabilities; multi-target ranking; real expression matrices and foundation-model services; live literature retrieval; external tool adapters; cloud deployment; enterprise identity; automatic lab execution; formal value of information; an alternative-model challenger; UI. None is necessary to demonstrate the two bounded roles, and none is implied to be implemented.

## API reference

Implementation follows the official [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses). Strict JSON structure does not establish factual correctness. Model support and access must be checked for the explicitly selected model.


## Version 2 upgrade: hypothesis versus finding

Copy all `agent_*.py` files, `challenger_probe.py` and `verify_agents.py` into your
existing project. Keep `demo-runs/` and `.venv/`. No baseline workflow Python file,
fixture, calculation or approval rule changed. Default API timeout is now 120 seconds,
preserving the adjustment that worked on your Mac.

The analyst now returns `hypothesis_under_test` as a question and a separate cited
`current_evidence` status and summary. The renderer displays both under explicit headings.
Status is checked against fixed experimental eligibility. This does not prove that the
summary prose is correct: that remains a challenger and human-review responsibility.

The challenger reports four required consistency checks. `PASS` means no identified
unsupported assertion in that dimension, not proof of efficacy, assay success, independent
replication or modality equivalence. Any `FAIL` requires a blocking finding and cannot be
accepted as READY_FOR_HUMAN_REVIEW. Contradictions in the opening, finding or next step are
material even when the action label and caveats elsewhere are correct. The one-revision
limit is unchanged; persistent issues remain visible for expert review.

Earlier agent reports remain historical files. `show` flags them stale after this code/prompt
change and can still render the old schema; it does not rewrite them. Your reference
assessments and approvals remain valid. Use a new attempt ID for a revised live run:

```bash
python agent_demo.py run --run-id test-initial --attempt-id live-v2 \
  --provider openai --model "$OPENAI_MODEL"
```

### Small targeted challenger test

After installing the update, this command runs FOUR live challenger-only calls: a sound
supportive control, a cell-loss overclaim, a false independent-replication claim, and an
unsupported antibody-blockade equivalence claim. It uses your existing supportive `demo`
and cell-loss `test-cell-loss` assessments. Calls incur normal API usage.

```bash
python challenger_probe.py --supportive-run demo --cell-loss-run test-cell-loss \
  --attempt-id challenger-v2 --model "$OPENAI_MODEL"
```

The evaluator authors the proposals and deliberately changes one substantive assertion
in each flawed case. It leaves the fixed action/status unchanged so the challenger must
check the prose, not just match an action label. Expected answers and case names are not
sent to the model. Evidence and exact citations are preserved. The control uses a short
scientifically scoped, authored proposal; it is not passed off as a live analyst output.

The script never writes to the reference database or production agent reports. Outputs
are in `demo-runs/challenger-probes/challenger-v2/`. Each case JSON includes the exact
proposal, sources, prompt, response, binding and automated detection check; `summary.json`
lists the results. Review findings yourself: a correct label alone does not establish
correct reasoning. The test performs no automatic correction cycle, to isolate detection.
A provider/validation failure stops the remaining calls; a missed error is recorded and
testing continues. Attempt IDs cannot be reused. There are no retries or fallback models.

The v2 code has been verified with scripted/fault-injected providers, not live model calls
in this environment. The four user-supplied v1 reports demonstrated live execution but
not the v2 fix. This focused probe set is a diagnostic, not a reliability benchmark.

## Four additional challenging cases: executable advanced suite

Upgrade only `challenger_probe.py` from the newest package; the live role prompts,
agent schemas and reference workflow are unchanged. This avoids teaching the model
these exact new answers before testing them. The basic suite remains the default.

From your existing project with `.venv` activated, create the missing imprecise
reference case (the other runs already exist from the earlier tests):

```bash
python demo.py start --run-id test-imprecise
python demo.py resume --run-id test-imprecise
python demo.py review --run-id test-imprecise --assessment test-imprecise-A001 \
  --decision approve --reviewer "Demo reviewer — simulated test" \
  --rationale "Approve solely to import the synthetic imprecise outcome." --simulated
python demo.py import-result --run-id test-imprecise --experiment X103
```

Then execute the four new challenger-only tests:

```bash
python challenger_probe.py --suite advanced \
  --supportive-run demo \
  --disagreement-run test-disagreement \
  --imprecise-run test-imprecise \
  --attempt-id challenger-advanced-01 \
  --model "$OPENAI_MODEL"
```

This makes four live calls (normal API usage). No new live analyst calls are needed.
The script creates the deliberately flawed proposals for you, retaining valid citations,
fixed action labels and evidence-status labels. You do not edit evidence or invent JSON.
It checks all run inputs before calling the model. Required selected mock outcomes are
X101, X107 and X103 respectively. No data from the alternative outcomes are pooled.

Cases: `genetic_causality_overclaim`, `favourable_method_selection`,
`imprecision_as_exclusion`, `direct_mechanism_overclaim`. Each adds exactly one flawed
claim (C7) to an otherwise unchanged authored proposal. Case names and expected answers
are not sent to the model. The existing sound control remains in the basic suite; these
four additional cases are all flawed, so all should receive blocking revision requests.

Inspect `demo-runs/challenger-probes/challenger-advanced-01/summary.json` and the four
case JSON files. The automated check requires a blocking finding on C7, REVISE or ABSTAIN,
and at least one failed consistency check. It does not require a particular checklist
category for these cross-cutting inference errors. A flag without correct explanation
is insufficient: human review must inspect the evidence and proposed correction.
The script validates plumbing only in build tests; these advanced cases have not yet
been tested against a live model here. Reuse of the attempt ID is rejected to prevent
accidental paid repeats; use a new ID only when intentionally repeating the test.
