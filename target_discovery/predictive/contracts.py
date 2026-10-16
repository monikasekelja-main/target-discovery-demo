"""Versioned contracts for an illustrative study; no real execution capability."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)

class Dataset(Record):
    source: str
    accession: str | None
    access_status: Literal['not_requested']
    tissue: str
    reference: str
    donor_ids: list[str]
    original_annotation: str
    approved_mapping: bool
    mapping_owner: str
    preprocessing_version: str

class Adaptation(Record):
    development_donors: list[str]
    evaluation_donors: list[str]
    status: Literal['proposed_not_run']
    plan: str
    split: str

class ModelPlan(Record):
    name: str
    version: str | None
    operation: str
    output: str
    intended_use: str
    validation: str
    baseline: str

class BiologicalTest(Record):
    interventions: list[str]
    timepoint: str
    readouts: list[str]
    criteria: str

class Study(Record):
    schema_version: Literal['predictive-study-v1']
    study_id: str
    evidence_status: Literal['illustrative_not_executed']
    indication: str
    target: str
    target_identity_status: Literal['fictional_placeholder']
    question: str
    dataset: Dataset
    adaptation: Adaptation
    model: ModelPlan
    boundaries: list[str]
    biological_test: BiologicalTest
    owners: dict[str, str]

class Observation(Record):
    evidence_id: str
    cell_state: str
    donor_shifts: dict[str, float]
    simple_baseline: float
    control_shift: float
    identity_preserved: bool

class Prerequisite(Record):
    name: str
    met: bool
    basis: str
    owner: str
    evidence_id: str

class Scenario(Record):
    id: str
    label: str
    data_status: Literal['ready','missing_annotation']
    model_status: Literal['supported','unvalidated','unsupported']
    conflict: bool
    timeout: bool
    summary: str
    observations: list[Observation]
    prerequisites: list[Prerequisite]
    independent_rationale: Prerequisite
    challenge: str
    request: str
    request_owner: str

class Event(Record):
    check: str
    finding: str
    action: str
    owner: str

class Nomination(Record):
    schema_version: Literal['nomination-v2'] = 'nomination-v2'
    study_id: str
    scenario_id: str
    evidence_status: Literal['illustrative_not_executed'] = 'illustrative_not_executed'
    status: Literal['supported_for_review','unresolved','exploratory','blocked']
    target: str
    intervention: str | None
    cell_state: str | None
    comparisons: list[dict]
    prerequisites: list[Prerequisite]
    independent_rationale: Prerequisite
    proposed_test: str | None
    next_action: str
    next_owner: str
    challenge: str
    request: str
    specialist: dict
    feedback_incorporated: bool
    reason: str
    limitations: list[str]
    events: list[Event]
    route: Literal['after_prediction','parallel']
    route_eligible: bool
    route_reason: str
    binding: str

class Review(Record):
    binding: str
    decision: Literal['APPROVE_SCOPED_TEST','DEFER']
    rationale: str = Field(min_length=12)
    actor_mode: Literal['session_rehearsal'] = 'session_rehearsal'
