# Tool input/output definitions — tools-v1

The demo uses four read-only tool names and a code-owned calculation/review/handoff path. No external service, production system, assay order or message is involved.

`contracts.py` is the executable definition; `schemas/*.schema.json` are generated from it. Strict Pydantic models reject extra fields and coerced numeric strings and check finite numeric measurements. JSON schemas communicate structure. Python validators and exchange checks also enforce cross-field and cross-record rules. Passing these checks does not validate a biological claim.

## Common envelope

Each request contains `contract_version: "tools-v1"`, `request_id` and `idempotency_key`. The controller supplies these fields. The tool-specific fields follow below.

Each response includes the same contract/request identity, `synthetic: true`, `status`, `source_snapshot_ids`, `data` and `error`.

| Condition | Response | Controller behaviour |
|---|---|---|
| Success | `OK`, typed data, no error | Check identities, versions and applicability. |
| Missing metadata | `NEEDS_METADATA`, no data, required fields and owner | Resolve the specific manifest or pause for the data owner. |
| Unsupported request | `MODEL_NOT_APPLICABLE`, no data, reason | Select an eligible alternative or abstain; no negative biological inference. |
| No record | `NOT_FOUND`, no data, source gap | Record retrieval absence, not absence of an effect. A missing manifest blocks prediction. |
| Invalid input | `INVALID_INPUT`, no data, requirement and owner | Ask the controller/data owner to repair input; do not silently coerce it. |
| Transient failure | `TECHNICAL_ERROR`, no data, `retryable: true` | Retry at most once with identical input, request ID and idempotency key; then preserve a blocked/partial run and owner. |

Errors contain `code`, `message`, `retryable`, `missing_fields` and `next_owner_role`. Only transient technical errors are retryable. Response schemas narrow the allowed statuses for each tool. Source content must not change tool authority.

Example request IDs are fixed for documentation. The local adapter returns the current request ID when serving a frozen scientific payload. Attempt number belongs in the event log; it must not change prediction inputs.

## 1. search_evidence

| Input | Meaning |
|---|---|
| `target_id` | Exact canonical ID: `DEMO-R1`. |
| `evidence_snapshot_id` | `EV-INITIAL-003`: evidence-v1 plus source views and mappings. |
| `query` | Bounded evidence question. |
| `evidence_ids` | Filter list; empty requests all records in scope. |
| `include_unresolved_candidates` | Include unresolved candidates for inspection, excluded from mapped target support. |

Output: evidence snapshot, records and notice. Each record includes evidence/family IDs, canonical target or null, entity status, claim/type, context/endpoint IDs or null, units, source provenance and original payload.

The raw claim remains available even when wrong: E13 is challenged, not silently corrected. E14 retains `duplicate_of: E01`. E01–E03, E13 and E14 retain family G01. E15 remains an unresolved candidate. Successful retrieval does not certify a claim.

Example: `examples/tools/search_evidence.request.json` and matching response.

## 2. get_study_manifest

Inputs: `study_id`, `snapshot_id`.

For `S-TARGET-001` / `META-001-v1`, output includes canonical target, full context attributes, input snapshot, data kind, metadata version, resolved fields, locator, owner and limitations.

This resolves **application input** cell state from the internal source's `analysis_request`. It does not revise the resting context in E05/E06 or invent context for E16. The specialist input is a reference to synthetic metadata and frozen outputs; no expression matrix exists in this package. Assay MFI is not a substitute model input.

The S-U02 example remains `NEEDS_METADATA`: cell context, endpoint and denominator are unknown. Dependent predictions must not proceed.

Examples: `get_study_manifest.*.json` and `get_study_manifest_unresolved.*.json` under `examples/tools/`.

## 3. get_prediction

| Input | Example / interpretation |
|---|---|
| `model_id`, `model_version` | `mock-signature-adapter`, `synthetic-model-v2`; exact registry match. |
| `target_id`, `context_id` | `DEMO-R1`, `CTX-CD4-STIM-TH17`; agree with manifest and required attributes. |
| `perturbation.kind` | `expression_change`. |
| `perturbation.expression_changes_pct` | `[-50, 0, 50]`; signed relative changes; zero means unchanged. Only registered levels supported. |
| `input_snapshot_id` | `SC-STIM-001-v1`; specialist input reference. |
| `metadata_snapshot_id` | `META-001-v1`; the manifest must actually be available, not merely named. |
| `endpoint_id` | `transcriptomic_inflammatory_signature`. |

The OK payload contains output/model/target/context/snapshot IDs, perturbation kind, endpoint, units, applicability, prediction points, uncalibrated uncertainty, null measured accuracy, provenance and limitations. The stimulated values are −0.50, 0 and +0.20 **standardized signature units**, not functional percentage changes.

`validate_prediction_exchange(request, response, registry, manifest)` checks dependency and request/output correspondence. A refused response has no numeric prediction. An unregistered −25% request is refused; no interpolation. Historical model v1 remains restricted to resting cells and is refused for the stimulated request.

Examples: `get_prediction`, `get_prediction_unsupported`, `get_prediction_missing_metadata` and `get_prediction_transient_failure` request/response pairs.

## 4. get_experiment_options

Inputs: `hypothesis_id`, `context_id`, `policy_version`, `unresolved_questions`, `option_snapshot_id`.

Output contains three study concepts: focused evidence review, relevant-context functional perturbation and a broader omics screen. Each specifies uncertainty addressed, readouts, decision consequences, owner, effort band, illustrative turnaround, relative cost and limitations. They require biology review and are not executable laboratory protocols.

The response returns options, not an optimal choice. The analyst justifies the proposal using the remaining uncertainty and how possible results would change the decision. The initial reference prefers a functional experiment after bounded review. No formal value-of-information optimum is claimed.

Example: `examples/tools/get_experiment_options.*.json`.

## Source mappings and canonical identity

| Canonical field | Internal view | CRO-style view |
|---|---|---|
| Source record ID | `record_key` | `row_id` |
| Original target | `target_label` | `analyte` |
| Study | `study_ref` | `study_code` |
| Units | `units` | `unit_map` |
| Original record | `record_payload` | `report` |
| Snapshot | top-level `snapshot_id` | top-level `export_version` |

The two views partition the original 16 records, not two independent confirmations. Canonical output retains family ID, locator, original target text, mapping ID and untouched payload. E16's percentage denominator remains unspecified.

Mappings are exact and versioned: `MAP-T001` preserves `DEMO-R1`; `MAP-T002` maps `DEMO_R1`. No mapping exists for `DEMO-RI`. Context matching requires both ID and required attributes; free-text similarity is insufficient.

The legacy calculator still checks its complete fixed `policy.context` to guard the numerical fixtures. Source/model interoperability uses canonical identifiers. `context_catalog.json` explicitly binds the assay to `CTX-CD4-STIM-TH17`; the implemented controller checks this binding before calculation.

## Code-owned calculation and decision brief

Validate a selected payload with `ExperimentRecord`, verify context binding, then call `evaluate.assess(record, policy)`. The calculator returns effect intervals, failed gates and action eligibility. It cannot authorize action or establish biological truth. Predictions cannot fill missing functional measurements.

`DecisionBrief` carries hypothesis/intervention/context, versions and input-content hashes, scientific recommendation, workflow status, scoped support grades, supporting/challenging/limited evidence IDs, functional estimates, prerequisites, uncertainties, next action and owner. Human review is always required.

Support grades are proposed ordinal categories. Unknown uses `ordinal: null, status: UNKNOWN`; zero describes an assessed, scoped unsupported claim. Mock predictions do not auto-increase grades; causal support remains 1/3 across reference branches. The two assay methods use the same donors.

Workflow status is separate from recommendation. X103/X104/X107 return `BIOLOGY_UNRESOLVED` for different reasons. Failed controls, insufficient intended perturbation and wrong context (X105/X106/X108) go to `SCHEMA_OR_QC_REVIEW`. Their scientific recommendations are inconclusive, but next actions differ.

## Reviewed handoff and specialist response

`Handoff` contains the complete assessment, review, recipient, requested action and next owner. `Review` binds assessment ID and SHA-256 of the entire brief, including input-content hashes. The example approval is a simulated human action with local-only scope.

`validate_handoff(handoff, response, current_input_hashes=...)` requires approval, exact assessment content, current input hashes and matching response identity. The controller obtains hashes from trusted current snapshots. Changes to evidence, metadata, policy, model output, prompts or assessment text require a new assessment and review. Hashes detect change; they are not authentication or proof of genuine human review.

`SpecialistResponse` returns `ACCEPTED_FOR_REVIEW`, `NEEDS_INFORMATION` or `DECLINED`, plus reason, missing information, next action and owner. Acceptance for review is not endorsement. A needs-information response must name the gap. The antibody example asks whether blockade reproduces the expression-reduction phenotype.

The runtime template omits fixed IDs/hashes. The controller binds its scientific response to the handoff actually generated. Concrete examples under `examples/handoff/` are for development, not agent retrieval.

Antibody specialists own modality/mechanism feasibility; small-molecule specialists own tractability and exposure; oligonucleotide specialists own transcript/isoform and delivery questions. DDS owns workflow integration, biology owns assay criteria and target decisions, and platform partners own shared deployment infrastructure.

## Verification and remaining implementation

`validate_contracts.py` checks schemas, source preservation, identity/context, prediction scope, numerical branches, citations and review binding. `verify_contracts.py` includes malformed inputs and stale reviews. Numerical tests remain in `verify.py`.

The package now implements local tool handlers, a deterministic controller, bounded immediate retries, durable events, CLI review capture and exports. See `cli_run_guide.md`. Live agents and UI are not included. The planned 28/56-trial LLM evaluation has not run; CLI integration checks do not replace it.

Implementation references: [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) and [JSON Schema generation](https://docs.pydantic.dev/latest/concepts/json_schema/), consulted 13 October 2026. Numerical assumptions and methodological sources are preserved in `numerical_reference.md`.

The CLI adds the explicit author mode `deterministic_reference` and reviewer mode `local_demo_operator`. Both remain local synthetic demonstration records; the original hand-authored and simulated-review fixtures remain valid.
