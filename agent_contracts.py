"""Strict advisory contracts. No write tools or approval fields exist."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Citation(Strict):
    source_id: str
    quote: str = Field(min_length=8, max_length=1000)

class Claim(Strict):
    claim_id: str
    kind: Literal['support', 'challenge', 'limitation']
    statement: str = Field(min_length=1, max_length=1500)
    citations: list[Citation] = Field(min_length=1, max_length=6)

class Retrieval(Strict):
    evidence_ids: list[str] = Field(min_length=1, max_length=4)
    question: str = Field(min_length=1, max_length=500)

Action = Literal['EXPERIMENT_TO_RESOLVE_UNCERTAINTY', 'ADVANCE_TO_REPLICATION',
                 'DEPRIORITIZE_TESTED_HYPOTHESIS', 'INCONCLUSIVE']

class EvidenceAssessment(Strict):
    status: Literal['UNTESTED', 'SUPPORTED_IN_THIS_EXPERIMENT', 'USEFUL_EFFECT_EXCLUDED', 'UNRESOLVED']
    summary: str = Field(min_length=1, max_length=1500)
    citations: list[Citation] = Field(min_length=1, max_length=6)

class AnalystOutput(Strict):
    hypothesis_under_test: str = Field(min_length=1, max_length=1500)
    current_evidence: EvidenceAssessment
    claims: list[Claim] = Field(min_length=1, max_length=16)
    proposed_action: Action
    experiment_option_id: str | None
    next_step: str = Field(min_length=1, max_length=1500)
    uncertainties: list[str] = Field(min_length=1, max_length=12)
    retrieval: Retrieval | None

class Finding(Strict):
    severity: Literal['blocking', 'caution']
    claim_id: str | None
    issue: str = Field(min_length=1, max_length=1500)
    required_change: str = Field(min_length=1, max_length=1500)
    citations: list[Citation] = Field(min_length=1, max_length=6)

class ConsistencyChecks(Strict):
    hypothesis_and_finding: Literal['PASS', 'FAIL']
    cell_loss_and_qc: Literal['PASS', 'FAIL']
    replication_independence: Literal['PASS', 'FAIL']
    modality_equivalence: Literal['PASS', 'FAIL']

class ChallengerOutput(Strict):
    checks: ConsistencyChecks
    verdict: Literal['READY_FOR_HUMAN_REVIEW', 'REVISE', 'ABSTAIN']
    findings: list[Finding] = Field(max_length=16)
    retrieval: Retrieval | None
    rationale: str = Field(min_length=1, max_length=1500)
