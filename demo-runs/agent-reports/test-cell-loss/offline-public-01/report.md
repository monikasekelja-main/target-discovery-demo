# Evidence analyst and challenger — synthetic demo

Mode: **scripted_offline_test** · Status: **ADVISORY_READY_FOR_REVIEW**

Bound to test-cell-loss-A002 · Human review required · No approval granted.

This is an advisory companion. It does not modify the reference decision brief.

## Analyst

### Hypothesis under test

Does partial DEMO-R1 expression reduction produce a useful functional effect while preserving cells in the specified stimulated context?

### Current evidence assessment

**UNRESOLVED**

Prerequisites failed; functional estimates are diagnostic only.

- COMPUTED: {"eligible_action": "INCONCLUSIVE", "failed_gates": ["G4:KD-A/D01: cell-loss/viability requirement failed", "G4:KD-A/D02: cell-loss/viability requirement failed

Proposal: INCONCLUSIVE

Ask biology to review the fixed calculation and select the appropriate replication, scoped deprioritization or unresolved/QC follow-up.

- C1 (support): The locus evidence motivates investigation; it does not settle gene assignment.
  - E01: {"claim": "Disease-associated locus; not gene-level causality.", "context_id": null, "endpoint_id": null, "entity_status": "RESOLVED", "evidence_family_id": "G0
- C2 (limitation): Frozen signature outputs are not measured functional benefit.
  - PREDICTION: {"applicability": "ELIGIBLE_UNDER_MOCK_CONTRACT", "context_id": "CTX-CD4-STIM-TH17", "endpoint_id": "transcriptomic_inflammatory_signature", "input_snapshot_id"
- C3 (challenge): Retain the historical cell-loss concern and inspect functional-study controls.
  - E09: {"claim": "Investigate cell loss and whether it is on-target, off-target, or delivery-related.", "context_id": null, "endpoint_id": null, "entity_status": "RESO
- C4 (limitation): Fixed calculated eligibility constrains the next decision; assay failures cannot establish benefit.
  - COMPUTED: {"eligible_action": "INCONCLUSIVE", "failed_gates": ["G4:KD-A/D01: cell-loss/viability requirement failed", "G4:KD-A/D02: cell-loss/viability requirement failed

Uncertainties:

- Gene assignment and genetic direction remain unresolved.
- Antibody blockade equivalence and systemic safety remain unassessed.

## Challenger

READY_FOR_HUMAN_REVIEW

SCRIPTED TEST ONLY: exercises report plumbing; no scientific correctness verdict.

Consistency checks (PASS means no identified overclaim, not established biology):

- hypothesis_and_finding: PASS
- cell_loss_and_qc: PASS
- replication_independence: PASS
- modality_equivalence: PASS

- caution: Scripted harness has not performed independent scientific evaluation. Required: A human must inspect sources and claims; live-model evaluation is still required.

## Limits

- Citation checks establish source membership and exact quotation, not entailment.
- Shared-model challenger is not independent biological validation.
- Fixed numerical eligibility is supplied, so agreement is not a discovery-accuracy metric.
- Report is advisory and is not incorporated into the reference assessment or approval.
