"""Validate the v3 fixture package offline; not an agent or biological benchmark."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from target_discovery.workflow.contracts import (MODELS, DecisionBrief, GetPredictionRequest, GetPredictionResponse,
    Handoff, Manifest, Registry, SpecialistResponse, validate_handoff, validate_prediction_exchange)
from target_discovery.workflow.evaluate import assess

from target_discovery.paths import PROJECT_ROOT as ROOT


def read(path):
    return json.loads((ROOT/path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def current_input_hashes(brief):
    """Resolve package-relative references only; callers must use trusted snapshots."""
    hashes={}
    for relative in brief.versions.input_content_sha256:
        path=(ROOT/relative).resolve()
        if not path.is_relative_to((ROOT/'runtime').resolve()) or not path.is_file():
            raise ValueError('Input reference must resolve to a file under runtime/')
        hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def validate_package():
    index=read('fixture_index.json')
    for item in index['typed_files']:
        MODELS[item['model']].model_validate(read(item['path']))
    for path, expected_hash in index['preserved_base_files_sha256'].items():
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected_hash,
                f'Preserved baseline was altered: {path}')
    for name,model in MODELS.items():
        stored=read(f'schemas/{name}.schema.json')
        expected=model.model_json_schema()
        expected['$schema']='https://json-schema.org/draft/2020-12/schema'
        require(stored==expected, f'Stale exported schema: {name}')

    # Prove that heterogeneous views preserve the originals and evidence families.
    original={r['id']:r for r in read('runtime/initial_evidence.json')['records']}
    internal=read('runtime/sources/internal_evidence.json')
    cro=read('runtime/sources/cro_export.json')
    views=[r['record_payload'] for r in internal['items']] + [r['report'] for r in cro['rows']]
    require(len(views)==16 and {r['id']:r for r in views}==original, 'Source-view round trip changed evidence')
    result=read('examples/tools/search_evidence.response.json')['data']
    canonical={r['evidence_id']:r for r in result['records']}
    require(len(result['records'])==16 and set(canonical)==set(original), 'Search result drops or multiplies evidence')
    mappings={r['original_value']:r for r in read('runtime/metadata/alias_mappings.json')['mappings']}
    for eid,r in canonical.items():
        require(r['raw_record']==original[eid], f'Raw provenance changed: {eid}')
        require(r['evidence_family_id']==original[eid]['family'], f'Evidence family changed: {eid}')
        mapping=mappings.get(r['source']['original_target_label'])
        require(r['target_id']==(mapping['canonical_id'] if mapping else None), f'Unsupported entity mapping: {eid}')
        require(r['source']['mapping_id']==(mapping['mapping_id'] if mapping else None), f'Missing mapping provenance: {eid}')
        view=(internal['items'] if r['source']['source_id']=='SRC-INTERNAL' else cro['rows'])
        key='record_key' if r['source']['source_id']=='SRC-INTERNAL' else 'row_id'
        source_row=next((v for v in view if v[key]==r['source']['source_record_id']),None)
        require(source_row is not None, f'Unresolvable source locator: {eid}')
        require(r['units']==source_row['units' if key=='record_key' else 'unit_map'], f'Units changed in normalization: {eid}')
    require(canonical['E14']['raw_record']['duplicate_of']=='E01','Duplicate linkage lost')
    require(canonical['E16']['context_id'] is None,'Incomplete evidence context was fabricated')
    require(internal['analysis_request']['cell_state'] is None,'Metadata dependency disappeared')

    registry=Registry.model_validate(read('runtime/capability_registry.json'))
    manifest=Manifest.model_validate(read('runtime/metadata/study_manifest.json'))
    catalogue=read('runtime/metadata/context_catalog.json')
    expected_context=next(c for c in catalogue['contexts'] if c['context_id']==manifest.context.context_id)
    require(manifest.context.model_dump()==expected_context,'Manifest and canonical context attributes differ')
    require(manifest.snapshot_id==internal['analysis_request']['metadata_snapshot_id'],'Manifest lookup version mismatch')
    require(manifest.study_id==internal['analysis_request']['study_id'],'Manifest study mismatch')
    for path in sorted((ROOT/'examples/tools').glob('*.request.json')):
        req=read(str(path.relative_to(ROOT)))
        res=read(str(path.relative_to(ROOT)).replace('.request.json','.response.json'))
        require(req['request_id']==res['request_id'],'Tool response/request identity mismatch')
    for capability in registry.capabilities:
        require((ROOT/capability.input_schema).is_file() and (ROOT/capability.output_schema).is_file(),
                'Registry schema reference does not resolve')
    for name in ['get_prediction','get_prediction_unsupported','get_prediction_missing_metadata','get_prediction_transient_failure']:
        req=GetPredictionRequest.model_validate(read(f'examples/tools/{name}.request.json'))
        res=GetPredictionResponse.model_validate(read(f'examples/tools/{name}.response.json'))
        validate_prediction_exchange(req,res,registry,None if name.endswith('missing_metadata') else manifest)
    prediction=read('runtime/predictions/stimulated_signature.response.json')['data']
    require([p['signature_change'] for p in prediction['predictions']]==[-0.5,0,0.2],'Prediction values changed unexpectedly')
    require(original['E06']['measurements']['signature_change_standardized_units']==-0.65,'Historical prediction overwritten')

    policy=read('runtime/policy.json')
    expected=read('evaluation/expected.json')['cases']
    routes={r['experiment_id']:r for r in read('evaluation/operational_routes.json')['cases']}
    expected_routes={'X101':'READY_FOR_BIOLOGY_REVIEW','X102':'READY_FOR_BIOLOGY_REVIEW',
        'X103':'BIOLOGY_UNRESOLVED','X104':'BIOLOGY_UNRESOLVED','X105':'SCHEMA_OR_QC_REVIEW',
        'X106':'SCHEMA_OR_QC_REVIEW','X107':'BIOLOGY_UNRESOLVED','X108':'SCHEMA_OR_QC_REVIEW'}
    for path in sorted((ROOT/'runtime/experiments').glob('X*.json')):
        record=read(str(path.relative_to(ROOT)))
        calculated=assess(record,policy)
        require(calculated['proposed_action']==expected[path.stem]['action'],f'Scientific branch changed: {path.stem}')
        require(routes[path.stem]['workflow_status']==expected_routes[path.stem],f'Wrong operational route: {path.stem}')
        require(routes[path.stem]['failed_gates']==calculated['failed_gates'],f'Failure reasons lost: {path.stem}')
    valid_citations=set(original)|{'PRED-STIM-001'}
    for key in ['initial','X101','X102','X103']:
        brief=DecisionBrief.model_validate(read(f'evaluation/reference_briefs/{key}.json'))
        allowed=valid_citations | ({key} if key!='initial' else set())
        refs=brief.supporting_evidence_ids+brief.challenging_evidence_ids+list(brief.excluded_or_limited_evidence)
        refs+=brief.confidence.causal.evidence_ids+brief.confidence.intervention.evidence_ids
        require(set(refs)<=allowed,f'Unknown or future citation in reference brief: {key}')
        require(brief.confidence.causal.ordinal==1,'Causal grade changed without new causal evidence')
        require(brief.confidence.intervention.ordinal==expected[key]['intervention_support_ordinal'],'Inconsistent support rubric')
        require(brief.scientific_recommendation==expected[key]['action'],'Reference action disagrees with expected branch')
        require(current_input_hashes(brief)==brief.versions.input_content_sha256,'Reference brief has stale input content')
        if key!='initial':
            calculated=assess(read(f'runtime/experiments/{key}.json'),policy)
            require({a:s.model_dump() for a,s in brief.functional_effects.items()}==
                    {a:s['functional_reduction_pct'] for a,s in calculated['statistics'].items()},'Brief changes calculated effects')

    handoff=Handoff.model_validate(read('examples/handoff/antibody_handoff.json'))
    specialist=SpecialistResponse.model_validate(read('examples/handoff/antibody_response.json'))
    validate_handoff(handoff,specialist,current_input_hashes=current_input_hashes(handoff.assessment))
    # No answer-bearing path is registered as a runtime capability/data reference.
    for cap in registry.capabilities:
        require(not any('evaluation/' in x or 'examples/' in x for x in cap.required_data_references), 'Answer-key leakage in registry')
    return {'typed_json_files':len(index['typed_files']),'json_schemas':len(MODELS),
            'preserved_evidence_records':len(original),'experimental_cases':len(routes),
            'reference_briefs':4,'status':'PASS',
            'scope':'Structure, provenance, applicability, arithmetic, branching and review binding only. No LLM or biological evaluation.'}


if __name__=='__main__':
    print(json.dumps(validate_package(),indent=2))
