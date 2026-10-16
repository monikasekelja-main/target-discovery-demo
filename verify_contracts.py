"""Boundary tests for integration risks; no model, agent or remote service calls."""
import copy
import json
from pathlib import Path
import unittest

from pydantic import ValidationError
from contracts import (DecisionBrief, ExperimentRecord, GetPredictionRequest, GetPredictionResponse,
    Handoff, Manifest, Registry, SpecialistResponse, SupportGrade,
    prediction_eligibility, validate_handoff, validate_prediction_exchange)
from validate_contracts import validate_package, current_input_hashes

ROOT=Path(__file__).parent


def read(path):
    return json.loads((ROOT/path).read_text())


def check_handoff(data, response=None):
    handoff=Handoff.model_validate(data)
    return validate_handoff(handoff,response,current_input_hashes=current_input_hashes(handoff.assessment))


class IntegrationContracts(unittest.TestCase):
    def setUp(self):
        self.request=GetPredictionRequest.model_validate(read('examples/tools/get_prediction.request.json'))
        self.response=GetPredictionResponse.model_validate(read('examples/tools/get_prediction.response.json'))
        self.registry=Registry.model_validate(read('runtime/capability_registry.json'))
        self.manifest=Manifest.model_validate(read('runtime/metadata/study_manifest.json'))

    def test_complete_package(self):
        self.assertEqual(validate_package()['status'],'PASS')

    def test_missing_manifest_blocks_otherwise_well_formed_request(self):
        self.assertEqual(prediction_eligibility(self.request,self.registry,None),'METADATA_REQUIRED')
        with self.assertRaises(ValueError):
            validate_prediction_exchange(self.request,self.response,self.registry,None)

    def test_eligibility_checks_context_version_target_and_data(self):
        variants={'model_version':'unregistered','target_id':'DEMO-RI','context_id':'CTX-CD4-REST',
                  'input_snapshot_id':'unknown-snapshot','metadata_snapshot_id':'META-001-v0'}
        for field,value in variants.items():
            with self.subTest(field=field):
                changed=self.request.model_dump();changed[field]=value
                self.assertIsNotNone(prediction_eligibility(GetPredictionRequest.model_validate(changed),self.registry,self.manifest))

    def test_matching_context_id_cannot_hide_wrong_attributes(self):
        data=self.manifest.model_dump();data['context']['cell_state']='resting'
        altered=Manifest.model_validate(data)
        self.assertEqual(prediction_eligibility(self.request,self.registry,altered),'CONTEXT_ATTRIBUTES_MISMATCH')

    def test_frozen_predictions_do_not_interpolate_unsupported_doses(self):
        data=self.request.model_dump();data['perturbation']['expression_changes_pct']=[-25]
        self.assertEqual(prediction_eligibility(GetPredictionRequest.model_validate(data),self.registry,self.manifest),
                         'PERTURBATION_LEVEL_NOT_SUPPORTED')

    def test_wrong_model_version_or_missing_curve_point_is_rejected(self):
        for field in ['model_version','predictions']:
            with self.subTest(field=field):
                data=self.response.model_dump()
                if field=='model_version': data['data'][field]='synthetic-model-v1'
                else: data['data'][field].pop()
                with self.assertRaises(ValueError):
                    validate_prediction_exchange(self.request,GetPredictionResponse.model_validate(data),self.registry,self.manifest)

    def test_signature_cannot_be_returned_as_functional_percent(self):
        data=self.response.model_dump();data['data']['units']='relative_percent_reduction'
        with self.assertRaises(ValidationError):GetPredictionResponse.model_validate(data)
        request=self.request.model_dump();request['endpoint_id']='IL17A_functional_reduction'
        with self.assertRaises(ValidationError):GetPredictionRequest.model_validate(request)

    def test_nonfinite_boolean_and_extra_numeric_inputs_are_rejected(self):
        for value in [float('nan'),float('inf'),True,'13.6']:
            with self.subTest(value=value):
                record=read('runtime/experiments/X101.json');record['assays']['KD-A'][0]['kd_il17_positive_pct']=value
                with self.assertRaises(ValidationError):ExperimentRecord.model_validate(record)
        request=self.request.model_dump();request['assay_mfi']=1000
        with self.assertRaises(ValidationError):GetPredictionRequest.model_validate(request)

    def test_refusal_cannot_include_a_prediction_or_be_retryable(self):
        source=read('examples/tools/get_prediction_unsupported.response.json')
        for variant in ['data','retry']:
            data=copy.deepcopy(source)
            if variant=='data':data['data']=self.response.data.model_dump()
            else:data['error']['retryable']=True
            with self.assertRaises(ValidationError):GetPredictionResponse.model_validate(data)

    def test_no_unsupported_refusal_reason(self):
        request=GetPredictionRequest.model_validate(read('examples/tools/get_prediction_unsupported.request.json'))
        data=read('examples/tools/get_prediction_unsupported.response.json');data['error']['code']='BIOLOGICALLY_INEFFECTIVE'
        with self.assertRaises(ValueError):
            validate_prediction_exchange(request,GetPredictionResponse.model_validate(data),self.registry,self.manifest)

    def test_unknown_confidence_is_not_zero(self):
        grade={'ordinal':None,'status':'UNKNOWN','scope':'unassessed claim','rationale':'No assessment','evidence_ids':[]}
        self.assertIsNone(SupportGrade.model_validate(grade).ordinal)
        grade['ordinal']=0
        with self.assertRaises(ValidationError):SupportGrade.model_validate(grade)

    def test_content_change_invalidates_review_even_with_same_id(self):
        for field in ['evidence_snapshot_id','metadata_snapshot_id','policy_version','registry_version','prompt_version']:
            with self.subTest(field=field):
                data=read('examples/handoff/antibody_handoff.json')
                data['assessment']['versions'][field]+='-changed'
                with self.assertRaises(ValueError):check_handoff(data)
        data=read('examples/handoff/antibody_handoff.json');data['assessment']['rationale']+=' Human edit.'
        with self.assertRaises(ValueError):check_handoff(data)

    def test_model_output_update_invalidates_prior_review(self):
        data=read('examples/handoff/antibody_handoff.json');data['assessment']['versions']['model_output_ids']=['PRED-NEW']
        with self.assertRaises(ValueError):check_handoff(data)

    def test_same_version_id_does_not_hide_changed_input_content(self):
        handoff=Handoff.model_validate(read('examples/handoff/antibody_handoff.json'))
        changed=current_input_hashes(handoff.assessment)
        changed['runtime/predictions/stimulated_signature.response.json']='0'*64
        with self.assertRaises(ValueError):validate_handoff(handoff,current_input_hashes=changed)

    def test_deferred_review_does_not_authorize_handoff(self):
        data=read('examples/handoff/antibody_handoff.json');data['review']['decision']='DEFER'
        with self.assertRaises(ValueError):check_handoff(data)

    def test_response_is_bound_to_exact_handoff(self):
        handoff=Handoff.model_validate(read('examples/handoff/antibody_handoff.json'))
        data=read('examples/handoff/antibody_response.json');data['handoff_id']='different-handoff'
        with self.assertRaises(ValueError):validate_handoff(handoff,SpecialistResponse.model_validate(data),
            current_input_hashes=current_input_hashes(handoff.assessment))

    def test_needs_information_requires_a_concrete_gap(self):
        data=read('examples/handoff/antibody_response.json');data['missing_information']=[]
        with self.assertRaises(ValidationError):SpecialistResponse.model_validate(data)


if __name__=='__main__':unittest.main(verbosity=2)
