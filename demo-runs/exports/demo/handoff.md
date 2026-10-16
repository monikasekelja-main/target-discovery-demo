# Local synthetic antibody handoff

Assessment: demo-A002

Review mode: simulated_human; decision: APPROVE; current approval effective: True.

Requested action: Assess whether receptor blockade can reproduce the expression-reduction phenotype; identify the missing evidence.

Simulated response: **NEEDS_INFORMATION**. Expression reduction does not establish that receptor blockade gives the same functional result.

Next action: Agree a mechanism-equivalence study concept with biology and antibody specialists.

Next owner: biology assay lead with antibody specialists

No message or experiment order was sent. The full evidence and numerical assessment follow.

# demo-A002 — synthetic target decision

**All target-specific evidence is invented. This is a local demonstration.**

Proposal: **ADVANCE_TO_REPLICATION**

Workflow status: READY_FOR_BIOLOGY_REVIEW · Author: deterministic_reference

Partial expression reduction produces at least 20% relative reduction in the live-cell IL-17A-positive fraction while preserving cells in the specified stimulated context.

Both methods meet the predefined 20% useful functional-effect criterion with intact prerequisites. The methods use the same donors; this is not independent cohort replication.

Next action: Propose new-donor/batch replication and target-specificity work; open a conditional specialist feasibility discussion.

Owner: biology reviewer · Biology review required.

Support grades: causal 1/3; intervention 2/3. Ordinal categories, not probabilities.

| Method | Relative reduction | 95% interval | Donors |
|---|---|---|---|
| KD-A | 32.0% | 29.5–34.5% | 8 |
| KD-B | 29.0% | 27.0–31.0% | 8 |

Both methods use the same donors; not independent cohort replication.

Remaining uncertainty:

- Gene assignment and genetic direction remain unresolved.
- Systemic and tissue safety remain unassessed.
- Expression reduction is not established to be equivalent to receptor blockade.
- Relevant-cell delivery, isoform coverage and modality feasibility require specialist assessment.
- Independent replication and specificity remain unestablished.

Supporting source IDs: E01, E02, E03, E04, X101
Challenging source IDs: E07, E09, E10

Limited or excluded evidence:

- E06: Historical resting-cell signature prediction; not a stimulated functional-effect prediction.
- E13: Causal/inhibition-benefit overclaim is unsupported by the cited locus association.
- E14: Duplicate of E01; no independent support.
- E15: Unresolved entity; do not map automatically.
- E16: Cell context, endpoint and denominator remain unknown.
- PRED-STIM-001: Frozen signature response; no measured predictive accuracy or functional-benefit claim.

Versions:

```json
{
  "evidence_snapshot_id": "EV-INITIAL-003+evidence-v2-X101",
  "metadata_snapshot_id": "META-001-v1",
  "model_output_ids": [
    "PRED-STIM-001"
  ],
  "model_versions": {
    "historical_E06": "synthetic-model-v1",
    "mock-signature-adapter": "synthetic-model-v2"
  },
  "policy_version": "demo-policy-v1",
  "registry_version": "registry-v1",
  "alias_mapping_version": "aliases-v1",
  "prompt_version": "no-LLM-reference-cli-v1-44d83a09d54e",
  "contract_version": "tools-v1",
  "input_content_sha256": {
    "implementation/target_discovery/cli/demo.py": "4bda66c78d613fb2990debf9e99c368fbc3cfb4ed758c296cca7ba5418df442c",
    "implementation/target_discovery/paths.py": "e269994b0cdbbc5e4da9a037273e5f76a9549c2e968c40f8d57be8950fb0dcb5",
    "implementation/target_discovery/workflow/contracts.py": "1e622125fcee5990db4eaf134ca8b45e5abb2a5a49819bf059df1e9742a1c0f3",
    "implementation/target_discovery/workflow/decision_compiler.py": "bda93c181fcb81d9046b664564fd1e53efd87622902868312b04d8d93ae41246",
    "implementation/target_discovery/workflow/evaluate.py": "bc2ebe5cc30025cef49c93c22f4f7968d72b37c71a0a80d61d05c1c8be491b86",
    "implementation/target_discovery/workflow/local_tools.py": "a3d36b04472f553962c71d134f02fe87abc7d4f4bfd658547657e5e59e2250ad",
    "implementation/target_discovery/workflow/workflow.py": "2a93c52287693ee1e20e8b4e92a259c8caceb45936f678e7eec9ae45c5835b5d",
    "implementation/target_discovery/workflow/workflow_store.py": "5d5d01fef5b1a5515f1c9549cbb97235e8e6fda24c0b6be900af94680420c32b",
    "runtime/capability_registry.json": "9de92358b6bd5b081896ce101f23548443d526fb31ced17caf444a65cea83d23",
    "runtime/confidence_rubric.json": "8904b88d4f83af96ab3b399ec463a4ddf6a22930f03a55009228f88768aa04f1",
    "runtime/experiment_options.response.json": "c6027d25618e787a24035e90d7889c49560896fba8b57a44329282013df83fcf",
    "runtime/experiments/X101.json": "398ce07c9571caad7deb4954be9f4c9b5fda434c3a7239bcf6aeaaad40647af2",
    "runtime/handoffs/antibody_response_template.json": "b539db29810cc6f92fcad0a3fa77cc1c7d9248b36c6cf5c2153e0d8fca752e88",
    "runtime/initial_evidence.json": "1d78b76f9105e373405ecc061936e3e3321328d899fbedf766fe9465f95847a6",
    "runtime/metadata/alias_mappings.json": "9d15663c0d14f10286a6c05d40b2377f555bb314286a64440d57d26dd766ffa4",
    "runtime/metadata/context_catalog.json": "53983ca7e731f6bd183a41f8307ce3ba68040249054d6bcf99d3bafd5a88af60",
    "runtime/metadata/study_manifest.json": "00ac1850fd96641dfba51f9555d2c5674132cbb9b4ef87f3b0d0f8e90f274563",
    "runtime/policy.json": "1531dacf1982e73e90c3abcb0b9b37291283e7dfd859e6e0f33035810f614b23",
    "runtime/predictions/stimulated_signature.response.json": "56e68286639bb682fcb85b35fa3dea6330124891a4c93db8ef794442bb596c8f",
    "runtime/sources/cro_export.json": "cd4a685c3f79ea45626c52b2dd4f3eeb2d8ee506d41a649d5d61b38bfdf80de1",
    "runtime/sources/internal_evidence.json": "1b76edad6f1982c52b0f85ac8a543b077ae74ea69eae0ba2eba41964f1bfa1d2",
    "runtime/workflow_contract.json": "680c7c03de89a5ec9012667a60cf0174a3fa02b172e230711982fdfe9b6526c8"
  }
}
```
