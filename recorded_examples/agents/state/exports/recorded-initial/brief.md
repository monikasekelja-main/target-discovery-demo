Current export review status: **PENDING**. Local approval effective: **False**. Review mode: **not reviewed**.

# recorded-initial-A001 — synthetic target decision

**All target-specific evidence is invented. This is a local demonstration.**

Proposal: **EXPERIMENT_TO_RESOLVE_UNCERTAINTY**

Workflow status: READY_FOR_BIOLOGY_REVIEW · Author: deterministic_reference

Partial expression reduction produces at least 20% relative reduction in the live-cell IL-17A-positive fraction while preserving cells in the specified stimulated context.

Application context metadata is resolved. The eligible frozen signature response suggests a functional test; it does not establish functional benefit. Gene assignment, genetic direction and the earlier cell-loss confound remain unresolved.

Next action: Propose OPT-FUNCTION after bounded evidence review; agree feasibility and assay policy with biology.

Owner: biology reviewer · Biology review required.

Support grades: causal 1/3; intervention 1/3. Ordinal categories, not probabilities.


Remaining uncertainty:

- Gene assignment and genetic direction remain unresolved.
- Systemic and tissue safety remain unassessed.
- Expression reduction is not established to be equivalent to receptor blockade.
- Relevant-cell delivery, isoform coverage and modality feasibility require specialist assessment.

Supporting source IDs: E01, E02, E03, E04, PRED-STIM-001
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
  "evidence_snapshot_id": "EV-INITIAL-003",
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
  "prompt_version": "no-LLM-reference-cli-v1-b2d84e5fb927",
  "contract_version": "tools-v1",
  "input_content_sha256": {
    "implementation/contracts.py": "01348d479b95ca3344f3c5cbded16fb2114435c7ee67c473bd90db6b48bde768",
    "implementation/decision_compiler.py": "d59f6a9c9a737d5fc918d9e94bfa808ca7ae25515f072941532123436d633b75",
    "implementation/demo.py": "680f0eaa85c14f96ba0b40d647d6a6e12a3fdb2037721f5d955f6bc1b60f91a5",
    "implementation/evaluate.py": "3725ee519acc89a770dfa14d0ae72430455387f78a7568d97e1f88b27bfd21bb",
    "implementation/local_tools.py": "e67644a3a7299f84700c01212d3b525dde5421c4cd1b9a9967741b03c1463dd6",
    "implementation/workflow.py": "90e5505e75a79cb890aa416e56076ef538d0b4a6c053e44ae66a88c093212e7a",
    "implementation/workflow_store.py": "5d5d01fef5b1a5515f1c9549cbb97235e8e6fda24c0b6be900af94680420c32b",
    "runtime/capability_registry.json": "9de92358b6bd5b081896ce101f23548443d526fb31ced17caf444a65cea83d23",
    "runtime/confidence_rubric.json": "8904b88d4f83af96ab3b399ec463a4ddf6a22930f03a55009228f88768aa04f1",
    "runtime/experiment_options.response.json": "c6027d25618e787a24035e90d7889c49560896fba8b57a44329282013df83fcf",
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
