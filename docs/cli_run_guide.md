# Running the command-line reference workflow

**Implementation: reference CLI v1. Scientific specification: consolidated plan v3.**

The complete local workflow is implemented. The four tools read captured source fixtures, resolve metadata, validate and select a prediction, and return curated experiment concepts. Fixed code performs evidence checks and computes experimental decisions. SQLite saves runs, source snapshots, assessments, reviews and actual events.

All biology and predictive outputs are synthetic. No LLM, trained predictive model, external database, wet-lab system or messaging service is invoked. The rule-based compiler is deliberately labelled `deterministic_reference`; it must not be presented as an agent.

## Install and check

Unzip the package and open a terminal in `decision-fixtures/`. Use Python 3.10 or newer; development verification used Python 3.12.

```bash
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1` in Windows PowerShell. Then:

```bash
python -m pip install -r requirements.txt
python -m unittest -v verify verify_contracts verify_workflow
```

The only non-standard-library dependency is the pinned Pydantic version. Installing it may need internet access; the workflow itself operates offline.

## Walk through the supportive example

Each command completes independently. You can close the terminal between commands; `demo-runs/workflow.sqlite3` retains the state. `--workspace PATH` selects another state directory and must appear before the command name. `--json` emits structured output.

### 1. Assemble evidence and expose the metadata dependency

```bash
python demo.py start --run-id demo
```

The two differently shaped sources are normalized. The application target alias is resolved through the explicit mapping. The command stops at `NEEDS_METADATA`: no prediction has run. The source records E15 and E16 remain unresolved.

### 2. Resolve the dependency and create the initial proposal

```bash
python demo.py resume --run-id demo
python demo.py --json show --run-id demo
```

This performs the manifest lookup, checks context attributes, selects the eligible capability and obtains the frozen signature response. It runs fixed evidence checks, makes one targeted source follow-up, compares the three experiment concepts under an explicit reference rule, and creates `demo-A001`.

The proposal is `EXPERIMENT_TO_RESOLVE_UNCERTAINTY`. Causal and intervention support are both 1/3. A mock signature response does not increase these grades or establish a functional percentage effect. The workflow pauses for review.

### 3. Review the proposed experiment

Inspect the proposal before issuing this command. This is a local demonstration approval only.

```bash
python demo.py review --run-id demo --assessment demo-A001 --decision approve --reviewer "Demo reviewer" --rationale "The scoped experiment and proposed criteria are suitable for this synthetic demonstration."
```

Use `--decision defer` to stop. To revise the next-action text while preserving the computed action and measurements:

```bash
python demo.py amend --run-id demo --assessment demo-A001 --reviewer "Demo reviewer" --rationale "Make the donor-variability question explicit." --next-action "Discuss a prospective donor-variability plan with biology before the study."
```

An amendment creates a new assessment ID and requires its own review. Always use the current ID shown by `show`. The remaining example assumes no amendment, so the result assessment will be `demo-A002`.

### 4. Import one simulated experimental result

```bash
python demo.py import-result --run-id demo --experiment X101
```

This requires the initial approval. Only the selected result file enters the run. The calculator derives 32.0% and 29.0% functional reductions with the specified intervals and passing prerequisites. The proposal becomes `ADVANCE_TO_REPLICATION`, meaning new donors/batches and specificity work, plus a conditional specialist discussion.

The previous approval is no longer effective. A new assessment, `demo-A002`, is pending review. The two methods use the same eight donors; this is not independent replication.

### 5. Review the updated assessment and generate the handoff

```bash
python demo.py review --run-id demo --assessment demo-A002 --decision approve --reviewer "Demo reviewer" --rationale "The synthetic result supports replication and a conditional feasibility discussion; modality equivalence and systemic safety remain unresolved."
python demo.py handoff --run-id demo --assessment demo-A002
```

The handoff carries the full reviewed assessment, evidence, uncertainty and input versions. The local antibody-response template is bound to the actual handoff and assessment digest. It returns `NEEDS_INFORMATION`: does blockade reproduce the expression-reduction phenotype? Biology and antibody specialists own the next study concept.

No message, experiment order or programme advancement is issued. Approving an inconclusive proposal accepts the scoped inconclusive assessment; it cannot turn failed QC into support. The main antibody handoff is available only for the supportive, prerequisite-passing result.

### 6. Inspect the trace and export

```bash
python demo.py replay --run-id demo
python demo.py export --run-id demo
```

Exports appear under `demo-runs/exports/demo/`:

| File | Content |
|---|---|
| `run.json` | Current state, review status, effective approval and next step. |
| `brief.md`, `assessment.json` | Readable and structured current proposal, including when still unapproved. |
| `handoff.md`, `handoff.json`, `specialist_response.json` | Readable and structured local handoff, review status and simulated response, when created. |
| `recorded_trace.json` | Actual events, tool requests/results, assessments, reviews and all recorded input revisions. |
| `snapshot_manifest.json`, `snapshots/` | Input hashes and exact current captured source files. |
| `assessments/` | Previous immutable assessments. |

Replay reads captured events; it does not call tools or re-execute a model. Historical traces remain viewable when live inputs change, labelled with `live_inputs_match: false`. Such replay does not authorize new action.

## Other biological outcomes

Start a new run and repeat the review sequence, selecting a different experiment at import. Each run accepts one alternative outcome; duplicate import of that same unchanged outcome is a no-op. Different alternatives cannot be pooled into a run.

| Result | Behaviour |
|---|---|
| X102 | Excludes the predefined useful mean effect in this tested setting; propose scoped deprioritization. |
| X103 | Imprecise intervals; retain uncertainty and propose prospective follow-up. |
| X104 | Apparent benefit with cell loss; investigate the confound. |
| X105 | Positive assay control failed; biological negative conclusion is not justified. |
| X106 | Intended expression reduction not achieved; review perturbation adequacy. |
| X107 | Methods disagree; preserve the disagreement rather than average it away. |
| X108 | Wrong cell context; exclude from direct support for this hypothesis. |

## Operational failure demonstrations

Use a new run ID for each scenario:

```bash
python demo.py start --run-id missing --scenario metadata-unresolved
python demo.py resume --run-id missing
python demo.py start --run-id unsupported --scenario prediction-unsupported
python demo.py resume --run-id unsupported
python demo.py start --run-id retry --scenario transient-once
python demo.py resume --run-id retry
python demo.py start --run-id blocked --scenario transient-always
python demo.py resume --run-id blocked
```

| Scenario | Expected behaviour |
|---|---|
| `metadata-unresolved` | Metadata remains missing; no prediction call. |
| `prediction-unsupported` | Deliberately asks the resting model about the stimulated context; explicit refusal and no retry. |
| `transient-once` | One simulated timeout, one retry with identical inputs and idempotency key, then success. |
| `transient-always` | Two attempts in total, then a saved block assigned to the service owner. |

These are explicit controller fault simulations, not observed service outages. Repeated `resume` cannot restart an exhausted or non-retryable operation. Retry/follow-up bounds apply within a recorded revision. A deliberate correction uses a new revision:

```bash
python demo.py refresh --run-id missing --scenario standard
python demo.py resume --run-id missing
```

## Changed inputs and reviews

Reviews are bound to assessment content and hashes of evidence, metadata, model output, policy and implementation. Changing content under the same ID still makes an approval stale. `show` reports this; `review`, `import-result` and `handoff` refuse to act on it.

After an intentional source correction, run `refresh` and `resume`. A selected experimental outcome is re-assessed against the refreshed inputs; it is not silently combined with another outcome. A new assessment and review are required. Previous source revisions and decisions remain in the trace.

`--simulated` on a review labels it as a scripted reviewer action. The included recorded example uses this flag explicitly. Normal CLI review records a `local_demo_operator`; neither label asserts authenticated enterprise biology approval.

## Recorded example included in this package

`recorded_examples/supportive/` contains outputs captured from the implemented workflow. Its reviews are explicitly simulated. Inspect its readable brief or replay the included database:

```bash
python demo.py --workspace recorded_examples/state replay --run-id recorded-supportive
python demo.py --workspace recorded_examples/state show --run-id recorded-supportive
```

Use a fresh default workspace for your own runs. The captured example is not an answer source for runtime tools or future agents.

## Verification boundaries

Tests cover all eight numerical outcomes, source preservation, metadata and prediction scope, transient retries, review gates, stale content, amendment, duplicate commands, refresh, historical replay, exports and separate-process CLI execution. One test moves contrary measurements into the X101 file and checks that the recommendation follows measurements, not the filename. Workflow tests run with only a copied `runtime/` tree; no expected-answer or example files are available.

The fixed-code source-instruction test confirms that retrieved instructions are treated as data in this implementation. It is not a claim that future LLM agents resist prompt injection; that requires the planned agent evaluations.

SQLite transactions support this local demonstration. Production authorization, concurrent job scheduling, remote-service failure recovery and deployment on shared platforms remain outside this stage. A process failure inside a command can roll back that command; the local tools have no external side effects. No exactly-once remote execution guarantee is claimed.

Exit codes: `0` successful command or deliberate review/metadata pause; `2` rejected command or malformed input; `3` a persisted blocked workflow. Use `show` or JSON output for the specific cause.

Agents and Streamlit have not been added. The next stage can reuse these adapters, contracts and review boundaries without rewriting the numerical workflow.
