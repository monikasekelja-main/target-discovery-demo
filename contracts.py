"""Versioned contracts for the synthetic demo; no agents or remote calls.

Pydantic validation checks structure. Exchange checks below also enforce selected
cross-record constraints. Neither establishes scientific truth or authorization.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Text = Annotated[str, Field(min_length=1)]
Number = Annotated[float, Field(allow_inf_nan=False)]
Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Status = Literal['OK', 'NEEDS_METADATA', 'MODEL_NOT_APPLICABLE', 'NOT_FOUND',
                 'TECHNICAL_ERROR', 'INVALID_INPUT']
WorkflowStatus = Literal['NEEDS_METADATA', 'MODEL_NOT_APPLICABLE', 'TECHNICAL_RETRY',
    'SCHEMA_OR_QC_REVIEW', 'BIOLOGY_UNRESOLVED', 'READY_FOR_BIOLOGY_REVIEW',
    'HANDOFF_NEEDS_INFORMATION']
Action = Literal['EXPERIMENT_TO_RESOLVE_UNCERTAINTY', 'ADVANCE_TO_REPLICATION',
                 'DEPRIORITIZE_TESTED_HYPOTHESIS', 'INCONCLUSIVE']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Synthetic(StrictModel):
    synthetic: Literal[True]


class Context(StrictModel):
    context_id: Text
    species: Literal['human']
    cell_type: Text
    cell_state: Text
    disease_context_id: Text


class AssayContext(StrictModel):
    target: Text
    disease_context: Text
    cell_context: Text
    intervention: Text
    endpoint: Text
    endpoint_time_hours: Annotated[int, Field(gt=0)]
    assay_protocol_version: Text


class Request(StrictModel):
    contract_version: Literal['tools-v1']
    request_id: Text
    idempotency_key: Text


class ToolError(StrictModel):
    code: Text
    message: Text
    retryable: bool
    missing_fields: list[str]
    next_owner_role: Text


T = TypeVar('T')


class Response(Synthetic, Generic[T]):
    contract_version: Literal['tools-v1']
    request_id: Text
    status: Status
    source_snapshot_ids: list[str]
    data: T | None
    error: ToolError | None

    @model_validator(mode='after')
    def coherent_status(self):
        if self.status == 'OK':
            if self.data is None or self.error is not None:
                raise ValueError('OK requires data and no error')
        elif self.data is not None or self.error is None:
            raise ValueError('Non-OK responses require an error and no scientific result')
        if self.error and self.error.retryable and self.status != 'TECHNICAL_ERROR':
            raise ValueError('Only transient technical errors may be retried')
        return self


class SourceRef(StrictModel):
    source_id: Text
    source_record_id: Text
    study_id: Text
    snapshot_id: Text
    locator: Text
    original_target_label: Text
    mapping_id: Text | None


class EvidenceRecord(Synthetic):
    evidence_id: Text
    evidence_family_id: Text
    target_id: Text | None
    entity_status: Literal['RESOLVED', 'UNRESOLVED']
    record_type: Text
    claim: Text
    context_id: Text | None
    endpoint_id: Text | None
    units: dict[str, str]
    source: SourceRef
    raw_record: dict[str, JsonValue]

    @model_validator(mode='after')
    def entity_consistency(self):
        if (self.entity_status == 'RESOLVED') != (self.target_id is not None):
            raise ValueError('Unresolved entity cannot acquire a canonical target ID')
        return self


class SearchEvidenceRequest(Request):
    target_id: Text
    evidence_snapshot_id: Text
    query: Text
    evidence_ids: list[str]
    include_unresolved_candidates: bool


class EvidenceSearchResult(StrictModel):
    evidence_snapshot_id: Text
    records: list[EvidenceRecord]
    notice: Text


class SearchEvidenceResponse(Response[EvidenceSearchResult]):
    status: Literal['OK', 'NOT_FOUND', 'TECHNICAL_ERROR', 'INVALID_INPUT']


class Manifest(Synthetic):
    study_id: Text
    snapshot_id: Text
    manifest_version: Text
    target_id: Text
    context: Context
    input_snapshot_id: Text
    input_data_kind: Literal['specialist_prepared_single_cell_reference']
    data_availability: Literal['metadata_and_frozen_outputs_only']
    source_locator: Text
    resolved_fields: list[str]
    owner_role: Text
    limitation: Text


class GetStudyManifestRequest(Request):
    study_id: Text
    snapshot_id: Text


class GetStudyManifestResponse(Response[Manifest]):
    status: Literal['OK', 'NEEDS_METADATA', 'NOT_FOUND', 'TECHNICAL_ERROR', 'INVALID_INPUT']


class Perturbation(StrictModel):
    kind: Literal['expression_change']
    expression_changes_pct: Annotated[list[Number], Field(min_length=1, max_length=3)]

    @model_validator(mode='after')
    def unique_levels(self):
        if len(set(self.expression_changes_pct)) != len(self.expression_changes_pct):
            raise ValueError('Duplicate perturbation levels')
        return self


class GetPredictionRequest(Request):
    model_id: Text
    model_version: Text
    target_id: Text
    context_id: Text
    perturbation: Perturbation
    input_snapshot_id: Text
    metadata_snapshot_id: Text
    endpoint_id: Literal['transcriptomic_inflammatory_signature']


class PredictionPoint(StrictModel):
    expression_change_pct: Number
    signature_change: Number


class PredictionResult(Synthetic):
    output_id: Text
    model_id: Text
    model_version: Text
    target_id: Text
    context_id: Text
    input_snapshot_id: Text
    metadata_snapshot_id: Text
    perturbation_kind: Literal['expression_change']
    endpoint_id: Literal['transcriptomic_inflammatory_signature']
    units: Literal['standardized_signature_units']
    applicability: Literal['ELIGIBLE_UNDER_MOCK_CONTRACT']
    predictions: Annotated[list[PredictionPoint], Field(min_length=1, max_length=3)]
    uncertainty: Literal['not_calibrated']
    measured_predictive_accuracy: None
    source_locator: Text
    limitations: Annotated[list[str], Field(min_length=1)]


class GetPredictionResponse(Response[PredictionResult]):
    status: Literal['OK', 'NEEDS_METADATA', 'MODEL_NOT_APPLICABLE', 'TECHNICAL_ERROR', 'INVALID_INPUT']


class ExperimentOption(Synthetic):
    option_id: Text
    title: Text
    uncertainty_addressed: list[str]
    readouts: list[str]
    decision_consequences: dict[str, str]
    effort_band: Literal['low', 'medium', 'high']
    illustrative_turnaround_weeks: Annotated[list[Number], Field(min_length=2, max_length=2)]
    relative_cost_units: Positive
    limitations: list[str]
    owner_role: Text
    scientific_review_status: Literal['illustrative_concept_requires_biology_review']
    executable_lab_protocol: Literal[False]


class GetExperimentOptionsRequest(Request):
    hypothesis_id: Text
    context_id: Text
    policy_version: Text
    unresolved_questions: Annotated[list[str], Field(min_length=1)]
    option_snapshot_id: Text


class ExperimentOptionsResult(StrictModel):
    option_snapshot_id: Text
    options: Annotated[list[ExperimentOption], Field(min_length=1)]
    selection_method: Literal['qualitative_decision_relevance_no_formal_optimality']


class GetExperimentOptionsResponse(Response[ExperimentOptionsResult]):
    status: Literal['OK', 'NOT_FOUND', 'TECHNICAL_ERROR', 'INVALID_INPUT']


class Capability(StrictModel):
    capability_id: Text
    tool_name: Literal['search_evidence', 'get_study_manifest', 'get_prediction', 'get_experiment_options']
    owner_role: Text
    input_schema: Text
    output_schema: Text
    schema_version: Literal['tools-v1']
    supported_context_ids: list[str]
    required_context_attributes: dict[str, str]
    supported_perturbations: list[str]
    allowed_expression_changes_pct: list[Number]
    required_data_references: list[str]
    model_id: Text | None
    model_version: Text | None
    permitted_side_effects: Literal['none']
    max_transient_retries: Literal[1]
    retry_requires_identical_input_and_idempotency_key: Literal[True]
    limitations: list[str]


class Registry(Synthetic):
    registry_version: Text
    capabilities: list[Capability]


class Measurement(StrictModel):
    measurement_id: Text
    donor_id: Text
    technical_replicates: Annotated[int, Field(gt=0)]
    min_live_cd4_events_per_well: Annotated[int, Field(ge=0)]
    ntc_il17_positive_pct: Percent
    kd_il17_positive_pct: Percent
    unstim_il17_positive_pct: Percent
    positive_control_il17_positive_pct: Percent
    ntc_live_fraction_pct: Percent
    kd_live_fraction_pct: Percent
    positive_control_live_fraction_pct: Percent
    positive_control_live_recovery_pct: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    ntc_live_cells: Annotated[int, Field(ge=0)]
    kd_live_cells: Annotated[int, Field(ge=0)]
    ntc_target_mfi: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    kd_target_mfi: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    max_technical_cv_pct: Annotated[float, Field(ge=0, allow_inf_nan=False)]


class ExperimentRecord(Synthetic):
    experiment_id: Text
    evidence_version: Text
    policy_version: Text
    context: AssayContext
    measurement_status: Text
    design: Text
    assays: dict[Literal['KD-A', 'KD-B'], list[Measurement]]


class Versions(StrictModel):
    evidence_snapshot_id: Text
    metadata_snapshot_id: Text
    model_output_ids: list[str]
    model_versions: dict[str, str]
    policy_version: Text
    registry_version: Text
    alias_mapping_version: Text
    prompt_version: Text
    contract_version: Literal['tools-v1']
    input_content_sha256: dict[Text, Annotated[str, Field(pattern='^[a-f0-9]{64}$')]]


class SupportGrade(StrictModel):
    ordinal: Annotated[int, Field(ge=0, le=3)] | None
    status: Literal['ASSESSED', 'UNKNOWN']
    scope: Text
    rationale: Text
    evidence_ids: list[str]

    @model_validator(mode='after')
    def unknown_is_not_zero(self):
        if (self.status == 'UNKNOWN') != (self.ordinal is None):
            raise ValueError('Unknown must use null, not zero')
        return self


class ConfidenceProfile(StrictModel):
    rubric_version: Literal['ordinal-rubric-v1']
    interpretation: Literal['proposed_ordinal_support_not_probability']
    causal: SupportGrade
    intervention: SupportGrade
    modality_feasibility: dict[Literal['antibody', 'small_molecule', 'oligonucleotide'], Literal['conditional', 'unknown']]
    systemic_safety: Literal['unassessed']


class EffectInterval(StrictModel):
    mean: Number
    lower_95: Number
    upper_95: Number
    n_donors: Annotated[int, Field(gt=1)]

    @model_validator(mode='after')
    def ordered(self):
        if not self.lower_95 <= self.mean <= self.upper_95:
            raise ValueError('Interval must contain its mean')
        return self


class DecisionBrief(Synthetic):
    assessment_id: Text
    author_mode: Literal['hand_authored_reference', 'deterministic_reference', 'agent_proposed', 'human_amended']
    hypothesis_id: Text
    target_id: Text
    context_id: Text
    hypothesis: Text
    intervention: Text
    versions: Versions
    workflow_status: WorkflowStatus
    scientific_recommendation: Action
    rationale: Text
    supporting_evidence_ids: list[str]
    challenging_evidence_ids: list[str]
    excluded_or_limited_evidence: dict[str, str]
    functional_effects: dict[str, EffectInterval]
    functional_effect_units: Literal['relative_percent_reduction']
    prerequisites_passed: bool | None
    failed_gates: list[str]
    confidence: ConfidenceProfile
    remaining_uncertainties: Annotated[list[str], Field(min_length=1)]
    next_action: Text
    next_owner_role: Text
    human_review_required: Literal[True]


class Review(Synthetic):
    review_id: Text
    assessment_id: Text
    reviewed_content_sha256: Annotated[str, Field(pattern='^[a-f0-9]{64}$')]
    reviewer_role: Text
    actor_mode: Literal['simulated_human', 'local_demo_operator']
    decision: Literal['APPROVE', 'AMEND', 'DEFER']
    rationale: Text
    authorization_scope: Literal['local_simulation_only']


class Handoff(Synthetic):
    handoff_id: Text
    handoff_version: Literal['handoff-v1']
    delivery_mode: Literal['local_simulation']
    assessment: DecisionBrief
    review: Review
    recipient_platform: Literal['antibody', 'small_molecule', 'oligonucleotide']
    requested_action: Text
    requested_by_role: Text
    next_owner_role: Text


class SpecialistResponseTemplate(Synthetic):
    platform: Literal['antibody', 'small_molecule', 'oligonucleotide']
    status: Literal['ACCEPTED_FOR_REVIEW', 'NEEDS_INFORMATION', 'DECLINED']
    reason: Text
    missing_information: list[str]
    next_action: Text
    next_owner_role: Text
    delivery_mode: Literal['local_simulation']

    @model_validator(mode='after')
    def information_request(self):
        if self.status == 'NEEDS_INFORMATION' and not self.missing_information:
            raise ValueError('Needs-information response must specify the missing item')
        return self


class SpecialistResponse(SpecialistResponseTemplate):
    response_id: Text
    handoff_id: Text
    handoff_version: Literal['handoff-v1']
    assessment_id: Text
    reviewed_content_sha256: Annotated[str, Field(pattern='^[a-f0-9]{64}$')]


def content_fingerprint(brief: DecisionBrief) -> str:
    """Bind a review to complete content, including the exact version bundle."""
    payload = json.dumps(brief.model_dump(mode='json'), sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def prediction_eligibility(request: GetPredictionRequest, registry: Registry, manifest: Manifest | None) -> str | None:
    """Return a refusal code, or None for eligibility under the MOCK contract."""
    if manifest is None:
        return 'METADATA_REQUIRED'
    if request.metadata_snapshot_id != manifest.snapshot_id:
        return 'METADATA_VERSION_MISMATCH'
    if request.target_id != manifest.target_id or request.context_id != manifest.context.context_id:
        return 'CONTEXT_OR_TARGET_MISMATCH'
    if request.input_snapshot_id != manifest.input_snapshot_id:
        return 'INPUT_SNAPSHOT_MISMATCH'
    matches = [c for c in registry.capabilities if c.tool_name == 'get_prediction'
               and (c.model_id, c.model_version) == (request.model_id, request.model_version)]
    if len(matches) != 1:
        return 'MODEL_VERSION_NOT_REGISTERED'
    capability = matches[0]
    if request.context_id not in capability.supported_context_ids:
        return 'CONTEXT_NOT_SUPPORTED'
    if any(getattr(manifest.context, key, None) != value
           for key, value in capability.required_context_attributes.items()):
        return 'CONTEXT_ATTRIBUTES_MISMATCH'
    if request.input_snapshot_id not in capability.required_data_references:
        return 'MODEL_INPUT_SNAPSHOT_NOT_SUPPORTED'
    if request.perturbation.kind not in capability.supported_perturbations:
        return 'PERTURBATION_NOT_SUPPORTED'
    if not set(request.perturbation.expression_changes_pct) <= set(capability.allowed_expression_changes_pct):
        return 'PERTURBATION_LEVEL_NOT_SUPPORTED'
    return None


def validate_prediction_exchange(request: GetPredictionRequest, response: GetPredictionResponse,
                                registry: Registry, manifest: Manifest | None) -> None:
    if request.request_id != response.request_id:
        raise ValueError('Response/request ID mismatch')
    reason = prediction_eligibility(request, registry, manifest)
    if response.status == 'OK':
        if reason:
            raise ValueError(f'Unsupported prediction was returned: {reason}')
        output = response.data
        for name in ['model_id', 'model_version', 'target_id', 'context_id', 'input_snapshot_id',
                     'metadata_snapshot_id', 'endpoint_id']:
            if getattr(output, name) != getattr(request, name):
                raise ValueError(f'Prediction output mismatch: {name}')
        levels = [p.expression_change_pct for p in output.predictions]
        if len(levels) != len(set(levels)) or set(levels) != set(request.perturbation.expression_changes_pct):
            raise ValueError('Returned perturbation levels must match requested levels')
    elif response.status in ['MODEL_NOT_APPLICABLE', 'NEEDS_METADATA']:
        if response.error.code != reason:
            raise ValueError('Refusal does not match the checked applicability reason')
        expected_status = 'NEEDS_METADATA' if reason == 'METADATA_REQUIRED' else 'MODEL_NOT_APPLICABLE'
        if response.status != expected_status:
            raise ValueError('Refusal routed to wrong status')


def validate_handoff(handoff: Handoff, response: SpecialistResponse | None = None,
                     *, current_input_hashes: dict[str, str]) -> None:
    brief, review = handoff.assessment, handoff.review
    if review.decision != 'APPROVE':
        raise ValueError('Handoff requires an explicit approval for the local demonstration')
    if review.assessment_id != brief.assessment_id or review.reviewed_content_sha256 != content_fingerprint(brief):
        raise ValueError('Review is stale or belongs to different assessment content')
    if not brief.versions.input_content_sha256 or current_input_hashes != brief.versions.input_content_sha256:
        raise ValueError('Inputs changed since the reviewed assessment, even if IDs were reused')
    if response is not None:
        if (response.handoff_id, response.handoff_version, response.assessment_id,
            response.reviewed_content_sha256, response.platform) != (
            handoff.handoff_id, handoff.handoff_version, brief.assessment_id,
            review.reviewed_content_sha256, handoff.recipient_platform):
            raise ValueError('Specialist response does not match the reviewed handoff')


MODELS = {cls.__name__: cls for cls in [SearchEvidenceRequest, SearchEvidenceResponse,
    GetStudyManifestRequest, GetStudyManifestResponse, GetPredictionRequest, GetPredictionResponse,
    GetExperimentOptionsRequest, GetExperimentOptionsResponse, Registry, Manifest,
    ExperimentRecord, DecisionBrief, Review, Handoff, SpecialistResponse, SpecialistResponseTemplate]}


def export_schemas(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name, model in MODELS.items():
        schema = model.model_json_schema()
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        (destination / f'{name}.schema.json').write_text(json.dumps(schema, indent=2) + '\n')


if __name__ == '__main__':
    export_schemas(Path(__file__).parent / 'schemas')
    print(f'Exported {len(MODELS)} schemas. Python exchange checks remain required.')
