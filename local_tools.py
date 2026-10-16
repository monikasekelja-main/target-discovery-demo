"""Four local, read-only adapters. Only captured runtime inputs are accessible.

No evaluation/example files, network calls, arbitrary paths, model training or
LLM inference. Queries record purpose; structured IDs filter this small pack.
"""
from __future__ import annotations

import json
from typing import Callable

from pydantic import ValidationError
from contracts import (SearchEvidenceRequest, SearchEvidenceResponse, GetStudyManifestRequest,
    GetStudyManifestResponse, GetPredictionRequest, GetPredictionResponse,
    GetExperimentOptionsRequest, GetExperimentOptionsResponse, Manifest, Registry,
    prediction_eligibility, validate_prediction_exchange)

TOOL_MODELS = {
    'search_evidence': (SearchEvidenceRequest, SearchEvidenceResponse),
    'get_study_manifest': (GetStudyManifestRequest, GetStudyManifestResponse),
    'get_prediction': (GetPredictionRequest, GetPredictionResponse),
    'get_experiment_options': (GetExperimentOptionsRequest, GetExperimentOptionsResponse),
}


def envelope(request_id, data=None, *, status='OK', code=None, message=None,
             owner='DDS workflow lead', missing=None, retryable=False, snapshots=None):
    return {'synthetic': True, 'contract_version': 'tools-v1', 'request_id': request_id,
            'status': status, 'source_snapshot_ids': snapshots or [], 'data': data,
            'error': None if status == 'OK' else {'code': code, 'message': message,
                'retryable': retryable, 'missing_fields': missing or [], 'next_owner_role': owner}}


class LocalTools:
    def __init__(self, read: Callable[[str], dict]):
        self.read = read

    @property
    def registry(self):
        return Registry.model_validate(self.read('runtime/capability_registry.json'))

    def call(self, tool, arguments, *, manifest=None, transient_failure=False):
        if tool not in TOOL_MODELS:
            raise ValueError('Unknown tool; only the four registered read-only tools are allowed')
        request_model, response_model = TOOL_MODELS[tool]
        request_id = arguments.get('request_id', 'INVALID-REQUEST')
        try:
            req = request_model.model_validate(arguments)
            permitted = [c for c in self.registry.capabilities if c.tool_name == tool and c.permitted_side_effects == 'none']
            if not permitted:
                raise ValueError('Tool has no permitted capability in the registry')
            if transient_failure:
                result = envelope(req.request_id, status='TECHNICAL_ERROR', code='SERVICE_TIMEOUT',
                    message='Deliberately simulated transient adapter timeout.', retryable=True,
                    owner='specialist service owner', snapshots=[self.registry.registry_version])
            else:
                result = getattr(self, tool)(req, manifest=manifest)
            validated = response_model.model_validate(result)
            if tool == 'get_prediction':
                validate_prediction_exchange(req, validated, self.registry, manifest)
            return validated.model_dump(mode='json')
        except (ValidationError, ValueError, KeyError, TypeError) as exc:
            # Keep malformed source input distinct from absence of a biological effect.
            result = envelope(request_id, status='INVALID_INPUT', code='CONTRACT_VIOLATION',
                message=str(exc), owner='data owner / DDS workflow lead')
            return response_model.model_validate(result).model_dump(mode='json')

    def search_evidence(self, req, **_):
        caps = [c for c in self.registry.capabilities if c.tool_name == 'search_evidence']
        if not any(req.evidence_snapshot_id in c.required_data_references for c in caps):
            return envelope(req.request_id,status='NOT_FOUND',code='SNAPSHOT_NOT_FOUND',
                message='Evidence snapshot is not registered.',owner='evidence data owner')
        aliases = self.read('runtime/metadata/alias_mappings.json')
        mappings = {x['original_value']:x for x in aliases['mappings']}
        known = {x['canonical_id'] for x in mappings.values()}
        if req.target_id not in known:
            return envelope(req.request_id,status='NOT_FOUND',code='TARGET_NOT_RESOLVED',
                message='An exact canonical target ID is required.',owner='entity data owner')
        internal = self.read('runtime/sources/internal_evidence.json')
        cro = self.read('runtime/sources/cro_export.json')
        records=[]
        for source, rows, key, target, study, units, raw, snapshot in [
            (internal,internal['items'],'record_key','target_label','study_ref','units','record_payload',internal['snapshot_id']),
            (cro,cro['rows'],'row_id','analyte','study_code','unit_map','report',cro['export_version'])]:
            for item in rows:
                original=item[raw]
                mapping=mappings.get(item[target])
                canonical=mapping['canonical_id'] if mapping else None
                if canonical != req.target_id and not (canonical is None and req.include_unresolved_candidates):
                    continue
                if req.evidence_ids and original['id'] not in req.evidence_ids:
                    continue
                # Mapping rules use the raw source context, not an outcome label.
                raw_context=original.get('context',original.get('supported_prediction_context',''))
                context_id='CTX-CD4-REST' if isinstance(raw_context,str) and 'resting' in raw_context.lower() else None
                endpoint_id='transcriptomic_inflammatory_signature' if original.get('endpoint')=='transcriptomic inflammatory-signature score' else None
                records.append({'synthetic':True,'evidence_id':original['id'],'evidence_family_id':original['family'],
                    'target_id':canonical,'entity_status':'RESOLVED' if canonical else 'UNRESOLVED',
                    'record_type':original['type'],'claim':original['claim'],'context_id':context_id,'endpoint_id':endpoint_id,
                    'units':item[units], 'source':{'source_id':source['source_id'],'source_record_id':item[key],
                        'study_id':item[study],'snapshot_id':snapshot,
                        'locator':f"fixture://{source['source_id']}/{snapshot}/{item[key]}",
                        'original_target_label':item[target],'mapping_id':mapping['mapping_id'] if mapping else None},
                    'raw_record':original})
        records.sort(key=lambda r:r['evidence_id'])
        ids=[r['evidence_id'] for r in records]
        if len(ids)!=len(set(ids)):
            raise ValueError('Duplicate canonical evidence IDs; source reconciliation is required')
        if req.evidence_ids and set(req.evidence_ids)-set(ids):
            return envelope(req.request_id,status='NOT_FOUND',code='EVIDENCE_IDS_NOT_FOUND',
                message='Requested evidence IDs are absent from this target/snapshot scope.',owner='evidence data owner')
        return envelope(req.request_id, {'evidence_snapshot_id':req.evidence_snapshot_id,'records':records,
            'notice':'Synthetic untrusted source content. Query records purpose; target and evidence IDs define the deterministic filter. Retrieval does not certify a claim.'},
            snapshots=['evidence-v1',internal['snapshot_id'],cro['export_version'],aliases['mapping_version']])

    def get_study_manifest(self, req, **_):
        manifest = Manifest.model_validate(self.read('runtime/metadata/study_manifest.json'))
        if (req.study_id,req.snapshot_id)==(manifest.study_id,manifest.snapshot_id):
            return envelope(req.request_id,manifest.model_dump(mode='json'),snapshots=[manifest.snapshot_id])
        cro=self.read('runtime/sources/cro_export.json')
        if any(r['study_code']==req.study_id and r['report']['type']=='incomplete_record' for r in cro['rows']):
            return envelope(req.request_id,status='NEEDS_METADATA',code='INCOMPLETE_SOURCE_METADATA',
                message='Cell context, endpoint and denominator remain unresolved; another study manifest cannot supply them.',
                missing=['cell_context','endpoint','denominator'],owner='CRO data owner',snapshots=[cro['export_version']])
        return envelope(req.request_id,status='NOT_FOUND',code='MANIFEST_NOT_FOUND',
            message='No exact study/snapshot manifest is available.',owner='single-cell data owner')

    def get_prediction(self, req, *, manifest=None):
        reason=prediction_eligibility(req,self.registry,manifest)
        if reason:
            return envelope(req.request_id,status='NEEDS_METADATA' if reason=='METADATA_REQUIRED' else 'MODEL_NOT_APPLICABLE',
                code=reason,message=f'No prediction returned: {reason}. This is not evidence of biological ineffectiveness.',
                owner='single-cell data owner' if reason=='METADATA_REQUIRED' else 'specialist predictive-model team',
                missing=['verified_study_manifest'] if reason=='METADATA_REQUIRED' else [],
                snapshots=[self.registry.registry_version])
        frozen=GetPredictionResponse.model_validate(self.read('runtime/predictions/stimulated_signature.response.json'))
        output=frozen.data.model_dump(mode='json')
        for field in ['model_id','model_version','target_id','context_id','input_snapshot_id','metadata_snapshot_id','endpoint_id']:
            if output[field]!=getattr(req,field):
                return envelope(req.request_id,status='TECHNICAL_ERROR',code='FROZEN_OUTPUT_UNAVAILABLE',
                    message='Request is contract-eligible but no matching frozen output is installed. No result fabricated.',
                    owner='specialist service owner',retryable=False)
        levels=set(req.perturbation.expression_changes_pct)
        output['predictions']=[p for p in output['predictions'] if p['expression_change_pct'] in levels]
        return envelope(req.request_id,output,snapshots=frozen.source_snapshot_ids)

    def get_experiment_options(self, req, **_):
        result=GetExperimentOptionsResponse.model_validate(self.read('runtime/experiment_options.response.json'))
        policy=self.read('runtime/policy.json')
        caps=[c for c in self.registry.capabilities if c.tool_name=='get_experiment_options']
        if req.hypothesis_id!='HYP-DEMO-R1-001' or req.context_id not in {v for c in caps for v in c.supported_context_ids}:
            return envelope(req.request_id,status='NOT_FOUND',code='NO_OPTIONS_FOR_CONTEXT',
                message='No curated experiment concepts match this hypothesis/context.',owner='biology assay lead')
        if req.policy_version!=policy['policy_version'] or req.option_snapshot_id!=result.data.option_snapshot_id:
            return envelope(req.request_id,status='INVALID_INPUT',code='OPTIONS_VERSION_MISMATCH',
                message='Policy or option snapshot does not match the loaded concepts.',owner='biology assay lead')
        return envelope(req.request_id,result.data.model_dump(mode='json'),snapshots=result.source_snapshot_ids)
