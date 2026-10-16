# Target-discovery demo: command-line reference workflow

**Reference CLI v1 + bounded agent layer v2 · 14 October 2026 · scientific plan and fixtures v3.**

This package now includes a runnable command-line workflow, four local tool adapters, SQLite checkpoints, explicit review gates and a simulated specialist handoff. It implements the reference path for the planned one-target, two-agent demo; the two bounded advisory roles are now implemented; a Streamlit workbench now supports explicit local human review and simulated handoff.

**DEMO-R1 and every target-specific measurement, prediction, source and response are invented.** No live LLM or biology model has been run during build verification. Live analyst/challenger execution is available through the separate agent CLI. The decision thresholds are illustrative assumptions for biology review, not organisational standards or clinically validated criteria.

**Public synthetic replay:** start with [REPLAY_DEMO.md](../REPLAY_DEMO.md). Included reviews, follow-ups, reports and replies were created offline for this public example. They are not original operator records or live-model evaluations. See [PUBLIC_RELEASE.md](../PUBLIC_RELEASE.md).

## Start here

1. Follow `docs/cli_run_guide.md` to run the complete workflow.
2. Inspect `recorded_examples/supportive/brief.md` and its recorded trace for an executed example with explicitly simulated reviews.
3. Read `docs/tool_contracts.md` for the interfaces and `evaluation/reference_briefs/README.md` for the hand-authored reference briefs.

The command-line workflow is implemented and verified. SQLite persists runs, source revisions, decisions, reviews and events. `examples/` contains authored interface illustrations; `recorded_examples/` contains actual CLI execution captures. The separate agent CLI adds an evidence analyst and challenger in live or explicitly scripted offline mode. The Streamlit UI supports saved evidence inspection and explicit local review/handoff controls.

## Components in this package

| Addition | What it demonstrates |
|---|---|
| Internal and CRO-style source views | Different formats resolve to the same 16 evidence records, preserving originals and shared evidence families. |
| Alias mappings and a study manifest | Map `DEMO_R1` through an explicit mock registry and recover missing application cell-state metadata. Leave `DEMO-RI` and E16 unresolved. |
| Small capability registry | Select a prediction capability by context, input snapshot, perturbation and version. |
| Eligible, refused, metadata-blocked and technical-failure responses | Separate applicable prediction from unsupported biology and operational problems. |
| Three experiment concepts | Compare decision relevance, limitations and explicitly illustrative effort. |
| Confidence rubric and four reference briefs | Keep causal support, intervention support, modality feasibility and safety separate. |
| Handoff and specialist-response contracts | Carry a reviewed hypothesis forward; identify missing blockade-equivalence evidence and its owner. |
| Python definitions and exported JSON schemas | Check fields, versions, units, applicability and review binding before connecting agents. |
| Command-line workflow and SQLite history | Run and resume the complete path; prevent stale approvals, repeated imports and unreviewed handoffs. |

The original 16 evidence records, eight experimental files, assay policy and numerical calculator are preserved. The new initial narrative in `evaluation/reference_briefs/` supersedes the initial narrative in the earlier decision-brief PDF. Experimental estimates and criteria are unchanged.

## The example in one minute

The question is whether partial reduction of a fictional surface receptor's expression reduces the **fraction of live CD4 T cells that are IL-17A positive by at least 20%**, while preserving live-cell recovery, in the specified stimulated, Th17-enriched context.

The application initially lacks cell-state metadata. A versioned manifest resolves this, permitting a frozen mock signature response: **−50% expression → −0.50 signature units; unchanged → 0; +50% expression → +0.20 units**. This suggests a functional experiment; it is not a predicted 20% functional benefit. The original resting-cell prediction remains separate.

| Result | KD-A reduction, 95% CI | KD-B reduction, 95% CI | Proposed action |
|---|---|---|---|
| X101 | 32.0% [29.5, 34.5] | 29.0% [27.0, 31.0] | Independent replication and specificity work; conditional specialist discussion. |
| X102 | 3.0% [0.8, 5.2] | 2.0% [0.1, 3.9] | Deprioritize this useful-benefit hypothesis in this tested setting. |
| X103 | 23.0% [5.2, 40.8] | 24.0% [8.1, 39.9] | Investigate variability and plan a prospective follow-up. |

Each method uses the **same eight paired donors**. The methods are not independent cohort replication. X101–X108 are alternative outcomes, not successive studies. A simulated antibody response requests evidence that blockade reproduces expression reduction; no molecule-design task or actual message is issued.

## Files and runtime boundaries

| Location | Role and permitted use |
|---|---|
| `runtime/initial_evidence.json` | Original evidence-v1; 16 records, not 16 independent studies. |
| `runtime/sources/` | Two differently shaped source views, with untouched raw payloads. |
| `runtime/metadata/` | Canonical contexts, exact alias mappings and the application study manifest. |
| `runtime/capability_registry.json` | Four tool names, with resting and stimulated prediction capabilities. |
| `runtime/predictions/` | Frozen synthetic response; no model weights or expression matrix. |
| `runtime/experiment_options.response.json` | Three study concepts. Cost numbers are invented relative estimates, not quotes. |
| `runtime/policy.json` | Original action criteria and measurement definitions. |
| `runtime/confidence_rubric.json` | Ordinal definitions; unknown is null, not zero. |
| `runtime/experiments/` | Controller exposes **one** selected outcome to the workflow. |
| `runtime/workflow_contract.json` | States, ownership, retry bounds and review invalidation requirements. |
| `runtime/handoffs/` | Simulated response template; code must insert the current handoff identity and assessment digest. |
| `target_discovery/workflow/contracts.py`, `schemas/` | Executable Pydantic definitions and generated JSON schemas. |
| `examples/` | Developer examples. **Never retrieve these as evidence or agent answers.** |
| `evaluation/` | Expected actions, hand-authored briefs, scenario specification and numerical audit outputs. **Never put these in runtime prompts or retrieval.** |
| `fixture_index.json` | Validation manifest and preserved baseline hashes; developer use only. |
| `target_discovery/workflow/evaluate.py` | Existing deterministic arithmetic and action-eligibility rules. |
| `target_discovery/cli/demo.py`, `target_discovery/workflow/workflow.py`, `target_discovery/workflow/workflow_store.py` | CLI, persistent controller and transactional history. |
| `target_discovery/workflow/local_tools.py`, `target_discovery/workflow/decision_compiler.py` | Read-only adapters and explicitly labelled fixed scientific reference rules. |
| `recorded_examples/` | Captured outputs and SQLite state; developer/presentation inspection only, never runtime retrieval. |

The runtime adapters read only captured, allowlisted inputs. Requests accept IDs, not caller-supplied paths. Only the selected experimental outcome enters a run. Source text is untrusted content, including E13's deliberately unsupported claim. Schema validity does not establish that a claim is supported.

## Run

Python 3.10+; tested with Python 3.12 and Pydantic 2.13.5. From this directory:

```bash
python -m pip install -r requirements.txt
python -m scripts.validate_contracts
python -m unittest -v verify verify_contracts verify_workflow
python -m target_discovery.workflow.evaluate runtime/experiments/X101.json
```

The calculator and its original nine checks use only the standard library. Contract validation requires the pinned dependency. These checks establish numerical and interface consistency, not biological validity, agent accuracy, confidence calibration or production readiness.

Regenerate additive fixtures and schemas after an intentional specification edit:

```bash
python -m scripts.build_contract_fixtures
python -m scripts.validate_contracts
```

The builder authors synthetic interface examples and reference briefs. It does not change baseline experimental data or thresholds. Hand-authored briefs must not be presented as agent outputs. The 28/56-trial LLM comparison in `evaluation/workflow_scenarios.json` is specified, not executed.

## Implemented sequence

The controller executes: load source views → resolve metadata → validate/select prediction → compare next actions → pause for biology review → import one simulated experiment → calculate and create a new assessment → require a new review → export the handoff and bind the simulated specialist response.

Input/output models and cross-record constraints are checked. Handoffs require current snapshot hashes; reusing an ID cannot conceal changed content. Retries are bounded and checkpoints survive separate CLI invocations. Historical snapshots and approvals remain inspectable.

Read `docs/agent_layer.md` for the implemented analyst/challenger design, installation, live execution, limits and human review. Live-model evaluation remains separate from the Streamlit review UI. Offline source-instruction tests establish controller boundaries, not LLM robustness.

## Quick start

```bash
python -m target_discovery.cli.demo start --run-id demo
python -m target_discovery.cli.demo resume --run-id demo
```

This stops at the first review gate. Follow `docs/cli_run_guide.md` for approval, importing X101, fresh review and handoff. Commands never approve automatically.

## Agent layer quick start

Activate your Python 3.12 virtual environment. For an existing complete run:

```bash
python -m target_discovery.cli.agent_demo run --run-id demo --attempt-id offline-01 --provider offline
python -m target_discovery.cli.agent_demo show --run-id demo --attempt-id offline-01
```

This is a scripted smoke test, not live reasoning. See `docs/agent_layer.md` for live mode with an explicit model and local API key. Original reference Python files and runtime fixtures are byte-for-byte unchanged.

Version 2 separates the hypothesis question from current evidence, requires four challenger consistency checks, and includes `target_discovery/agents/challenger_probe.py` for a four-case live diagnostic. See the upgrade section in `docs/agent_layer.md`.

## Streamlit workbench (slice 2)

```bash
python -m pip install -r requirements-ui.txt
python -m streamlit run streamlit_app.py
```

Read `docs/streamlit_slice2.md` for the current review and handoff controls. Browsing remains read-only; explicit submissions record exact-assessment reviews and local simulated handoffs. Rationale advice can make one paid model call only when explicitly requested; no external handoff messages are sent. See `docs/rationale_review.md` for the required pre-save check and configuration. `docs/streamlit_slice1.md` retains the earlier inspection-only scope and QA history.

The **Ask the evidence assistant** view adds read-only grounded chat, verified effect/QC figure exports, and PubMed/Crossref abstract retrieval. External findings remain candidate evidence. See [assistant usage, boundaries and rehearsal checklist](docs/evidence_assistant.md). It uses the existing server API key; optional official web search requires a separate Brave Search key. Matplotlib is included in `requirements-ui.txt`. Live assistant semantic evaluation remains a rehearsal requirement; automated tests use model doubles.

The Decision view includes [programme-context-v1](docs/programme_context.md): read-only plaque-psoriasis / fictional DEMO-R1 framing, kept separate from saved evidence, agents and approvals. Expand **Programme hypothesis and scope** for competing explanations, specialist questions and disease-background references.
