"""Persistent deterministic reference workflow for the fictional DEMO-R1 case."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from contracts import (DecisionBrief, ExperimentRecord, Handoff, Manifest, Review, SpecialistResponse,
    GetPredictionRequest, content_fingerprint, prediction_eligibility, validate_handoff)
from decision_compiler import compile_brief, evidence_checks, render_brief
from evaluate import assess
from local_tools import LocalTools
from workflow_store import Store, now

PACKAGE=Path(__file__).parent.resolve()
SCENARIOS=('standard','metadata-unresolved','prediction-unsupported','transient-once','transient-always')
EXPERIMENT_IDS=frozenset(f'X{i}' for i in range(101,109))
BASE_INPUTS=(
    'runtime/initial_evidence.json','runtime/sources/internal_evidence.json','runtime/sources/cro_export.json',
    'runtime/metadata/alias_mappings.json','runtime/metadata/context_catalog.json','runtime/metadata/study_manifest.json',
    'runtime/capability_registry.json','runtime/predictions/stimulated_signature.response.json',
    'runtime/experiment_options.response.json','runtime/policy.json','runtime/confidence_rubric.json',
    'runtime/workflow_contract.json','runtime/handoffs/antibody_response_template.json')
IMPLEMENTATION_FILES=('contracts.py','evaluate.py','local_tools.py','decision_compiler.py','workflow.py','workflow_store.py','demo.py')


class WorkflowError(ValueError):
    pass


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def checked_id(run_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',run_id):
        raise WorkflowError('Run ID must be 1–64 letters/digits/underscores/hyphens, starting with a letter or digit')
    return run_id


class Workflow:
    def __init__(self,workspace,fixture_root=PACKAGE):
        self.root=Path(fixture_root).resolve()
        self.store=Store(workspace)

    def close(self):
        self.store.close()

    def _snapshot(self,relative):
        allowed=set(BASE_INPUTS)|{f'runtime/experiments/{eid}.json' for eid in EXPERIMENT_IDS}
        path=(self.root/relative).resolve()
        if relative not in allowed or not path.is_relative_to((self.root/'runtime').resolve()):
            raise WorkflowError('Only allowlisted runtime inputs may be loaded')
        try:
            text=path.read_text()
        except OSError as exc:
            raise WorkflowError(f'Missing runtime input: {relative}') from exc
        return {'sha256':sha(text),'text':text}

    def _implementation_hashes(self):
        return {'implementation/'+p:sha((PACKAGE/p).read_text()) for p in IMPLEMENTATION_FILES}

    def _capture(self):
        return {relative:self._snapshot(relative) for relative in BASE_INPUTS}

    @staticmethod
    def _reader(state):
        def read(relative):
            if relative not in state['snapshots']:
                raise WorkflowError('Input has not been captured for this run; alternative outcomes are not accessible')
            snapshot=state['snapshots'][relative]
            if sha(snapshot['text'])!=snapshot['sha256']:
                raise WorkflowError('Captured input content does not match its recorded digest')
            return json.loads(snapshot['text'])
        return read

    def _bound_hashes(self,state):
        return {**{p:s['sha256'] for p,s in state['snapshots'].items()},**state['implementation_sha256']}

    def _current_hashes(self,state):
        result={}
        for p in state['snapshots']:
            try: result[p]=self._snapshot(p)['sha256']
            except WorkflowError: result[p]='missing'
        return {**result,**self._implementation_hashes()}

    def _fresh(self,state):
        return self._bound_hashes(state)==self._current_hashes(state)

    def _ensure_fresh(self,state):
        if not self._fresh(state):
            raise WorkflowError('Inputs or implementation changed. Previous approval is stale; use refresh, then review the new assessment.')

    def _args(self,state,step,**fields):
        identity=f"{state['run_id']}-r{state['revision']}-{step}"
        return {'contract_version':'tools-v1','request_id':identity,'idempotency_key':'IDEMP-'+identity,**fields}

    def _call(self,state,step,tool,arguments,manifest=None):
        request_digest=sha(json.dumps(arguments,sort_keys=True,allow_nan=False))
        if step in state['calls']:
            saved=state['calls'][step]
            if saved['request_sha256']!=request_digest:
                raise WorkflowError('An idempotency step was reused with different arguments')
            return saved['response']
        tools=LocalTools(self._reader(state))
        attempts=[]
        for attempt in (1,2):
            fault=tool=='get_prediction' and (state['scenario']=='transient-always' or
                (state['scenario']=='transient-once' and attempt==1))
            self.store.event(state,'TOOL_REQUEST',{'revision':state['revision'],'step':step,'tool':tool,
                'attempt':attempt,'arguments':arguments,'request_sha256':request_digest,'fault_injected':fault})
            response=tools.call(tool,arguments,manifest=manifest,transient_failure=fault)
            attempts.append(response)
            self.store.event(state,'TOOL_RESULT',{'revision':state['revision'],'step':step,'tool':tool,
                'attempt':attempt,'response':response})
            retry=response['status']=='TECHNICAL_ERROR' and response['error']['retryable']
            if not retry or attempt==2: break
            state['workflow_status']='TECHNICAL_RETRY'
            self.store.event(state,'TECHNICAL_RETRY',{'step':step,'next_attempt':2,
                'reason':response['error']['code'],'same_input_and_idempotency_key':True})
        state['calls'][step]={'request_sha256':request_digest,'arguments':arguments,
            'response':response,'attempts':len(attempts)}
        return response

    def _block(self,state,status,reason,owner):
        state.update(phase='BLOCKED',workflow_status=status,block_reason=reason,next_owner_role=owner)
        self.store.event(state,'WORKFLOW_BLOCKED',{'status':status,'reason':reason,'owner':owner,
                                                'no_scientific_result_created':True})
        self.store.save(state)

    def _require_ok(self,state,response,tool):
        if response['status']=='OK': return True
        mapping={'NEEDS_METADATA':'NEEDS_METADATA','MODEL_NOT_APPLICABLE':'MODEL_NOT_APPLICABLE',
                 'TECHNICAL_ERROR':'TECHNICAL_RETRY','INVALID_INPUT':'SCHEMA_OR_QC_REVIEW'}
        status=mapping.get(response['status'],'NEEDS_METADATA' if tool=='get_study_manifest' else 'SCHEMA_OR_QC_REVIEW')
        self._block(state,status,response['error'],response['error']['next_owner_role'])
        return False

    def start(self,run_id,scenario='standard'):
        checked_id(run_id)
        if scenario not in SCENARIOS: raise WorkflowError('Unknown scenario')
        with self.store.transaction():
            if self.store.exists(run_id): raise WorkflowError('Run already exists; use show/resume or choose a new run ID')
            state={'run_id':run_id,'created_at':now(),'revision':1,'scenario':scenario,
                'execution_mode':'deterministic_reference_no_agents','phase':'EVIDENCE','workflow_status':'NEEDS_METADATA',
                'snapshots':self._capture(),'implementation_sha256':self._implementation_hashes(),
                'calls':{},'assessment_seq':0,'review_seq':0,'handoff_seq':0,
                'current_assessment_id':None,'review':None,'selected_experiment':None,'handoff':None,
                'specialist_response':None,'block_reason':None,'next_owner_role':'DDS workflow lead'}
            self.store.save(state)
            self.store.add_snapshots(state)
            self.store.event(state,'RUN_STARTED',{'scenario':scenario,'synthetic':True,
                'execution_mode':state['execution_mode'],'input_hashes':self._bound_hashes(state)})
            self._advance(state,pause_after_evidence=True)
        return self.show(run_id)

    def resume(self,run_id):
        with self.store.transaction():
            state=self.store.load(run_id)
            self._ensure_fresh(state)
            if state['phase'] in ('EVIDENCE','METADATA','PREDICTION','CHECKS','OPTIONS','ASSESS'):
                self._advance(state)
        return self.show(run_id)

    def _advance(self,state,pause_after_evidence=False):
        read=self._reader(state)
        tools=LocalTools(read)
        try:
            if state['phase']=='EVIDENCE':
                seed=read('runtime/sources/internal_evidence.json')['analysis_request']
                aliases=read('runtime/metadata/alias_mappings.json')['mappings']
                mapped=[m for m in aliases if m['original_value']==seed['target_label']]
                if len(mapped)!=1: raise WorkflowError('Application target alias has no unique authoritative mapping')
                state['target_id']=mapped[0]['canonical_id']
                state['seed']=seed
                caps=[c for c in tools.registry.capabilities if c.tool_name=='search_evidence']
                snapshot=caps[0].required_data_references[0]
                req=self._args(state,'evidence',target_id=state['target_id'],evidence_snapshot_id=snapshot,
                    query='Assemble source evidence and limitations for the target hypothesis.',evidence_ids=[],include_unresolved_candidates=True)
                response=self._call(state,'evidence','search_evidence',req)
                if not self._require_ok(state,response,'search_evidence'): return
                state['evidence']=response['data']
                state['phase']='METADATA';state['workflow_status']='NEEDS_METADATA'
                self.store.event(state,'DEPENDENCY_BLOCKED',{'required_fields':['cell_state','context_id'],
                    'dependent_tool':'get_prediction','next_action':'Read the exact study manifest; no prediction has run.'})
                self.store.save(state)
                if pause_after_evidence:return
            if state['phase']=='METADATA':
                seed=state['seed']
                unresolved=state['scenario']=='metadata-unresolved'
                req=self._args(state,'metadata',study_id='S-U02' if unresolved else seed['study_id'],
                    snapshot_id='META-U02-v1' if unresolved else seed['metadata_snapshot_id'])
                response=self._call(state,'metadata','get_study_manifest',req)
                if not self._require_ok(state,response,'get_study_manifest'):return
                state['manifest']=response['data']
                manifest=Manifest.model_validate(state['manifest'])
                catalog=read('runtime/metadata/context_catalog.json')
                context=next((c for c in catalog['contexts'] if c['context_id']==manifest.context.context_id),None)
                if context!=manifest.context.model_dump():raise WorkflowError('Manifest and canonical context attributes disagree')
                if manifest.target_id!=state['target_id'] or manifest.input_snapshot_id!=seed['input_snapshot_id']:
                    raise WorkflowError('Manifest target/input does not match the application request')
                self.store.event(state,'METADATA_RESOLVED',{'snapshot_id':manifest.snapshot_id,'context':context,
                    'does_not_resolve':['E16'],'historical_resting_evidence_preserved':True})
                candidates=[]
                for cap in tools.registry.capabilities:
                    if cap.tool_name!='get_prediction':continue
                    req=self._args(state,'prediction',model_id=cap.model_id,model_version=cap.model_version,
                        target_id=state['target_id'],context_id=manifest.context.context_id,
                        perturbation={'kind':'expression_change','expression_changes_pct':[-50,0,50]},
                        input_snapshot_id=manifest.input_snapshot_id,metadata_snapshot_id=manifest.snapshot_id,
                        endpoint_id='transcriptomic_inflammatory_signature')
                    reason=prediction_eligibility(GetPredictionRequest.model_validate(req),tools.registry,manifest)
                    candidates.append({'capability_id':cap.capability_id,'reason':reason,'request':req})
                eligible=[c for c in candidates if c['reason'] is None]
                self.store.event(state,'CAPABILITY_SELECTION',{'candidates':candidates,
                    'selection_rule':'Unique exact match of model context, attributes, input reference and requested levels.'})
                if state['scenario']=='prediction-unsupported':
                    refused=next(c for c in candidates if c['request']['model_version']=='synthetic-model-v1')
                    state['prediction_request']=refused['request']
                    state['prediction_request']['perturbation']['expression_changes_pct']=[-50]
                    self.store.event(state,'FAULT_SCENARIO',{'purpose':'Exercise explicit not-applicable response; a resting model is deliberately requested.'})
                elif len(eligible)==1:state['prediction_request']=eligible[0]['request']
                else:
                    self._block(state,'MODEL_NOT_APPLICABLE','No unique eligible registered prediction capability.','specialist predictive-model team')
                    return
                state['phase']='PREDICTION'
            if state['phase']=='PREDICTION':
                response=self._call(state,'prediction','get_prediction',state['prediction_request'],
                                    manifest=Manifest.model_validate(state['manifest']))
                if not self._require_ok(state,response,'get_prediction'):return
                state['prediction']=response['data'];state['phase']='CHECKS'
            if state['phase']=='CHECKS':
                checks=evidence_checks(state['evidence']['records'])
                state['evidence_checks']=checks
                self.store.event(state,'REFERENCE_CHECKS',checks)
                available={r['evidence_id'] for r in state['evidence']['records']}
                followup=[eid for eid in ['E03','E07','E09','E16'] if eid in available]
                req=self._args(state,'followup',target_id=state['target_id'],
                    evidence_snapshot_id=state['evidence']['evidence_snapshot_id'],
                    query='Reinspect genetic direction, cell-loss evidence and the incomplete record after the reference checks.',
                    evidence_ids=followup,include_unresolved_candidates=True)
                response=self._call(state,'followup','search_evidence',req)
                if not self._require_ok(state,response,'search_evidence'):return
                state['phase']='OPTIONS'
            if state['phase']=='OPTIONS':
                policy=read('runtime/policy.json')
                options=read('runtime/experiment_options.response.json')['data']
                req=self._args(state,'options',hypothesis_id='HYP-DEMO-R1-001',
                    context_id=state['manifest']['context']['context_id'],policy_version=policy['policy_version'],
                    unresolved_questions=['functional direction','cell-loss confound','gene assignment'],
                    option_snapshot_id=options['option_snapshot_id'])
                response=self._call(state,'options','get_experiment_options',req)
                if not self._require_ok(state,response,'get_experiment_options'):return
                state['options']=response['data']
                if not any(o['option_id']=='OPT-FUNCTION' for o in state['options']['options']):
                    raise WorkflowError('The reference policy has no matching functional-study concept; abstain')
                self.store.event(state,'NEXT_ACTION_PROPOSED',{'selected_option':'OPT-FUNCTION',
                    'mode':'explicit_scientist_authored_reference_rule',
                    'rationale':'Directly resolves the useful functional-effect and cell-loss uncertainty; review alone or broad signatures cannot establish that endpoint.',
                    'formal_optimality_claimed':False})
                state['phase']='ASSESS'
            if state['phase']=='ASSESS':self._assess(state)
            self.store.save(state)
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            self._block(state,'SCHEMA_OR_QC_REVIEW',str(exc),'data owner / biology assay lead')

    def _assess(self,state):
        read=self._reader(state)
        policy=read('runtime/policy.json')
        binding=read('runtime/metadata/context_catalog.json')['assay_context_binding']
        if binding['legacy_context']!=policy['context'] or binding['required_attributes']!=state['manifest']['context']:
            raise WorkflowError('Canonical assay context, metadata and calculation policy are not aligned')
        result=experiment=None
        if state['selected_experiment']:
            experiment=read(f"runtime/experiments/{state['selected_experiment']}.json")
            ExperimentRecord.model_validate(experiment)
            if experiment['experiment_id']!=state['selected_experiment']:
                raise WorkflowError('Selected experiment ID does not match the imported record')
            result=assess(experiment,policy)
            self.store.event(state,'CALCULATION',{'mode':'fixed_code','result':result,
                'note':'Effect estimates are diagnostic if prerequisites fail.'})
        state['assessment_seq']+=1
        assessment_id=f"{state['run_id']}-A{state['assessment_seq']:03}"
        compiler_digest=sha(json.dumps(state['implementation_sha256'],sort_keys=True))[:12]
        brief=compile_brief(assessment_id=assessment_id,evidence=state['evidence'],manifest=state['manifest'],
            prediction=state['prediction'],policy=policy,registry_version=read('runtime/capability_registry.json')['registry_version'],
            alias_version=read('runtime/metadata/alias_mappings.json')['mapping_version'],input_hashes=self._bound_hashes(state),
            implementation_version='no-LLM-reference-cli-v1-'+compiler_digest,result=result,experiment=experiment)
        state['current_assessment_id']=brief.assessment_id;state['review']=None
        state['handoff']=None;state['specialist_response']=None
        state['phase']='AWAITING_REVIEW';state['workflow_status']=brief.workflow_status
        state['next_owner_role']=brief.next_owner_role;state['block_reason']=None
        self.store.add_assessment(state,brief.model_dump(mode='json'))
        self.store.event(state,'ASSESSMENT_CREATED',{'assessment_id':brief.assessment_id,
            'content_sha256':content_fingerprint(brief),'proposed_action':brief.scientific_recommendation,
            'workflow_status':brief.workflow_status,'review_required':True})

    def _current_brief(self,state,assessment_id=None):
        current=state['current_assessment_id']
        if current is None:raise WorkflowError('No complete assessment is available')
        if assessment_id is not None and assessment_id!=current:
            raise WorkflowError('Assessment is not current; inspect the new assessment before reviewing or handing off')
        return DecisionBrief.model_validate(self.store.assessment(state['run_id'],current))

    def _approval(self,state,brief):
        review=state['review']
        return bool(review and review['decision']=='APPROVE' and review['assessment_id']==brief.assessment_id
                    and review['reviewed_content_sha256']==content_fingerprint(brief) and self._fresh(state))

    def review(self,run_id,assessment_id,decision,reviewer,rationale,simulated=False):
        if decision not in ('APPROVE','DEFER'):raise WorkflowError('Use approve/defer, or the amend command to create a revised draft')
        if not reviewer.strip() or not rationale.strip():raise WorkflowError('Reviewer and rationale are required')
        with self.store.transaction():
            state=self.store.load(run_id);self._ensure_fresh(state)
            if state['phase']=='BLOCKED':raise WorkflowError('Resolve the blocked inputs before review')
            brief=self._current_brief(state,assessment_id)
            mode='simulated_human' if simulated else 'local_demo_operator'
            last=state['review']
            if last and all(last[k]==v for k,v in {'assessment_id':assessment_id,'decision':decision,
                'reviewer_role':reviewer,'rationale':rationale,'actor_mode':mode}.items()):
                return self.show(run_id)
            state['review_seq']+=1
            review=Review.model_validate({'synthetic':True,'review_id':f"{run_id}-R{state['review_seq']:03}",
                'assessment_id':assessment_id,'reviewed_content_sha256':content_fingerprint(brief),
                'reviewer_role':reviewer,'actor_mode':mode,'decision':decision,'rationale':rationale,
                'authorization_scope':'local_simulation_only'}).model_dump(mode='json')
            self.store.add_review(state,review);self.store.event(state,'REVIEW_RECORDED',review)
            state['review']=review
            if state['handoff']:
                self.store.event(state,'HANDOFF_INVALIDATED',{'handoff_id':state['handoff']['handoff_id'],'reason':'Review changed.'})
                state['handoff']=state['specialist_response']=None
            state['phase']='DEFERRED' if decision=='DEFER' else ('AWAITING_RESULT' if not state['selected_experiment'] else 'REVIEWED')
            state['workflow_status']=brief.workflow_status
            self.store.save(state)
        return self.show(run_id)

    def amend(self,run_id,assessment_id,reviewer,rationale,next_action):
        if not all(x.strip() for x in [reviewer,rationale,next_action]):raise WorkflowError('Reviewer, rationale and next action are required')
        with self.store.transaction():
            state=self.store.load(run_id);self._ensure_fresh(state)
            if state['phase']=='BLOCKED':raise WorkflowError('Resolve the blocked inputs before amendment')
            old=self._current_brief(state,assessment_id)
            state['review_seq']+=1
            review=Review.model_validate({'synthetic':True,'review_id':f"{run_id}-R{state['review_seq']:03}",
                'assessment_id':assessment_id,'reviewed_content_sha256':content_fingerprint(old),'reviewer_role':reviewer,
                'actor_mode':'local_demo_operator','decision':'AMEND','rationale':rationale,
                'authorization_scope':'local_simulation_only'}).model_dump(mode='json')
            self.store.add_review(state,review);self.store.event(state,'REVIEW_RECORDED',review)
            state['assessment_seq']+=1
            draft=old.model_dump(mode='json');draft.update(assessment_id=f"{run_id}-A{state['assessment_seq']:03}",
                author_mode='human_amended',next_action=next_action,rationale=old.rationale+' Human review amendment: '+rationale)
            changed=DecisionBrief.model_validate(draft)
            self.store.add_assessment(state,changed.model_dump(mode='json'))
            state.update(current_assessment_id=changed.assessment_id,review=None,handoff=None,specialist_response=None,
                         phase='AWAITING_REVIEW',workflow_status=changed.workflow_status)
            self.store.event(state,'HUMAN_AMENDMENT',{'previous_assessment_id':assessment_id,'new_assessment_id':changed.assessment_id,
                'edited_fields':['next_action','rationale'],'scientific_action_and_calculated_values_unchanged':True,'review_required':True})
            self.store.save(state)
        return self.show(run_id)

    def import_result(self,run_id,experiment_id):
        if experiment_id not in EXPERIMENT_IDS:raise WorkflowError('Select an allowlisted experiment ID X101–X108')
        with self.store.transaction():
            state=self.store.load(run_id);self._ensure_fresh(state)
            if state['selected_experiment']:
                if state['selected_experiment']==experiment_id:return self.show(run_id)
                raise WorkflowError('This run already contains an outcome. Use a new run for an alternative; outcomes must not be pooled.')
            brief=self._current_brief(state)
            if state['phase']!='AWAITING_RESULT' or not self._approval(state,brief):
                raise WorkflowError('Approve the current initial assessment before importing a simulated result')
            path=f'runtime/experiments/{experiment_id}.json'
            state['snapshots'][path]=self._snapshot(path)
            state['selected_experiment']=experiment_id
            self.store.add_snapshots(state)
            self.store.event(state,'RESULT_IMPORTED',{'experiment_id':experiment_id,'snapshot_sha256':state['snapshots'][path]['sha256'],
                'simulated':True,'prior_assessment_id':brief.assessment_id,'prior_approval_invalidated':True})
            state.update(current_assessment_id=None,review=None,handoff=None,specialist_response=None,phase='ASSESS')
            self._advance(state)
        return self.show(run_id)

    def refresh(self,run_id,scenario=None):
        if scenario is not None and scenario not in SCENARIOS:raise WorkflowError('Unknown scenario')
        with self.store.transaction():
            old=self.store.load(run_id)
            state=copy.deepcopy(old)
            new_snapshots=self._capture()
            if state['selected_experiment']:
                p=f"runtime/experiments/{state['selected_experiment']}.json";new_snapshots[p]=self._snapshot(p)
            state.update(revision=state['revision']+1,scenario=scenario or state['scenario'],snapshots=new_snapshots,
                implementation_sha256=self._implementation_hashes(),calls={},phase='EVIDENCE',workflow_status='NEEDS_METADATA',
                current_assessment_id=None,review=None,handoff=None,specialist_response=None,block_reason=None)
            for field in ['evidence','manifest','prediction','prediction_request','evidence_checks','options']:
                state.pop(field,None)
            self.store.event(state,'ASSESSMENT_INVALIDATED',{'previous_assessment_id':old['current_assessment_id'],
                'previous_revision':old['revision'],'new_revision':state['revision'],
                'reason':'Explicit refresh of source/implementation snapshots; new review is required.',
                'input_hashes':self._bound_hashes(state)})
            self.store.save(state);self.store.add_snapshots(state);self._advance(state,pause_after_evidence=True)
        return self.show(run_id)

    def handoff(self,run_id,assessment_id):
        with self.store.transaction():
            state=self.store.load(run_id);self._ensure_fresh(state)
            brief=self._current_brief(state,assessment_id)
            if not state['selected_experiment'] or brief.scientific_recommendation!='ADVANCE_TO_REPLICATION' or not brief.prerequisites_passed:
                raise WorkflowError('The main antibody handoff requires a supportive, prerequisite-passing result. Other briefs can be exported for review.')
            if not self._approval(state,brief):raise WorkflowError('A current post-result approval is required for handoff')
            if state['handoff']:
                validate_handoff(Handoff.model_validate(state['handoff']),SpecialistResponse.model_validate(state['specialist_response']),
                    current_input_hashes=self._current_hashes(state))
                return self.show(run_id)
            state['handoff_seq']+=1
            h=Handoff.model_validate({'synthetic':True,'handoff_id':f"{run_id}-H{state['handoff_seq']:03}",
                'handoff_version':'handoff-v1','delivery_mode':'local_simulation','assessment':brief.model_dump(mode='json'),
                'review':state['review'],'recipient_platform':'antibody',
                'requested_action':'Assess whether receptor blockade can reproduce the expression-reduction phenotype; identify the missing evidence.',
                'requested_by_role':'DDS workflow lead','next_owner_role':'antibody specialists'})
            template=self._reader(state)('runtime/handoffs/antibody_response_template.json')
            response=SpecialistResponse.model_validate({**template,'response_id':h.handoff_id+'-response',
                'handoff_id':h.handoff_id,'handoff_version':h.handoff_version,'assessment_id':brief.assessment_id,
                'reviewed_content_sha256':content_fingerprint(brief)})
            validate_handoff(h,response,current_input_hashes=self._current_hashes(state))
            state['handoff']=h.model_dump(mode='json');state['specialist_response']=response.model_dump(mode='json')
            state['phase']='HANDOFF_'+response.status
            if response.status=='NEEDS_INFORMATION':state['workflow_status']='HANDOFF_NEEDS_INFORMATION'
            state['next_owner_role']=response.next_owner_role
            self.store.event(state,'HANDOFF_CREATED',state['handoff'])
            self.store.event(state,'SIMULATED_SPECIALIST_RESPONSE',state['specialist_response'])
            self.store.save(state)
        return self.show(run_id)

    def show(self,run_id):
        state=self.store.load(run_id)
        fresh=self._fresh(state)
        brief=self._current_brief(state) if state['current_assessment_id'] else None
        review=state['review']
        return {'run_id':run_id,'synthetic':True,'execution_mode':state['execution_mode'],'revision':state['revision'],
            'scenario':state['scenario'],'phase':state['phase'],'workflow_status':state['workflow_status'],
            'inputs_current':fresh,'approval_effective':bool(brief and self._approval(state,brief)),
            'review_status':'STALE' if not fresh else (review['decision'] if review else 'PENDING'),
            'assessment':brief.model_dump(mode='json') if brief else None,'review':review,
            'selected_experiment':state['selected_experiment'],'next_owner_role':state['next_owner_role'],
            'block_reason':state['block_reason'],'specialist_response':state['specialist_response'],
            'next_command':self._next_command(state,fresh),
            'tool_attempts':{k:v['attempts'] for k,v in state['calls'].items()}}

    @staticmethod
    def _next_command(state,fresh):
        rid=state['run_id'];aid=state['current_assessment_id']
        if not fresh:return f'refresh --run-id {rid}'
        if state['phase']=='BLOCKED':return f'Inspect the blocker. After an explicit correction: refresh --run-id {rid}'
        if state['phase']=='METADATA':return f'resume --run-id {rid}'
        if state['phase'] in ['AWAITING_REVIEW','DEFERRED']:
            return f'review --run-id {rid} --assessment {aid} --decision approve --reviewer YOUR_NAME --rationale YOUR_REASON'
        if state['phase']=='AWAITING_RESULT':return f'import-result --run-id {rid} --experiment X101'
        if state['phase']=='REVIEWED':return f'Inspect the proposal; export --run-id {rid}. A supportive result also permits the antibody handoff.'
        return f'export --run-id {rid}'

    def replay(self,run_id):
        state=self.store.load(run_id)
        events=self.store.events(run_id)
        if not events:raise WorkflowError('No captured trace is available')
        recorded_inputs=self.store.snapshots(run_id)
        if not recorded_inputs:raise WorkflowError('No captured input snapshots are available; replay unavailable')
        for snapshot in recorded_inputs:
            if sha(snapshot['source_text'])!=snapshot['sha256']:raise WorkflowError('Captured snapshot is corrupt; replay unavailable')
        return {'run_id':run_id,'capture_mode':'actual_deterministic_cli_execution_no_agents',
            'replay_mode':'read_only_historical_trace_no_tools_executed','recorded_revision':state['revision'],
            'input_hashes':self._bound_hashes(state),'live_inputs_match':self._fresh(state),
            'events':events,'recorded_inputs':recorded_inputs,
            'assessments':self.store.assessments(run_id),'reviews':self.store.reviews(run_id)}

    def export(self,run_id,destination=None):
        state=self.store.load(run_id)
        out=Path(destination).resolve() if destination else self.store.workspace/'exports'/run_id
        for protected in ['runtime','evaluation','examples','schemas']:
            if out.is_relative_to((self.root/protected).resolve()):raise WorkflowError('Export cannot overwrite fixture or evaluation directories')
        if out.exists() and any(out.iterdir()):
            marker=out/'run.json'
            if not marker.exists() or json.loads(marker.read_text()).get('run_id')!=run_id:
                raise WorkflowError('Export directory is nonempty and does not belong to this run')
        out.mkdir(parents=True,exist_ok=True)
        def write(name,data):
            path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
            payload=data if isinstance(data,str) else json.dumps(data,indent=2,allow_nan=False)+'\n'
            temporary=path.with_name(path.name+'.tmp');temporary.write_text(payload);temporary.replace(path)
        summary=self.show(run_id)
        write('run.json',summary)
        write('recorded_trace.json',self.replay(run_id))
        write('snapshot_manifest.json',{'input_hashes':self._bound_hashes(state),'synthetic':True})
        for path,snapshot in state['snapshots'].items():write('snapshots/'+path,snapshot['text'])
        for brief in self.store.assessments(run_id):
            write(f"assessments/{brief['assessment_id']}.json",brief)
        if summary['assessment']:
            write('assessment.json',summary['assessment'])
            review_notice=(f"Current export review status: **{summary['review_status']}**. "
                f"Local approval effective: **{summary['approval_effective']}**. "
                f"Review mode: **{summary['review']['actor_mode'] if summary['review'] else 'not reviewed'}**.\n\n")
            write('brief.md',review_notice+render_brief(summary['assessment']))
        if state['handoff']:
            write('handoff.json',state['handoff']);write('specialist_response.json',state['specialist_response'])
            response=state['specialist_response']
            write('handoff.md','# Local synthetic antibody handoff\n\n'+
                f"Assessment: {state['handoff']['assessment']['assessment_id']}\n\n"+
                f"Review mode: {state['review']['actor_mode']}; decision: {state['review']['decision']}; current approval effective: {summary['approval_effective']}.\n\n"+
                f"Requested action: {state['handoff']['requested_action']}\n\n"+
                f"Simulated response: **{response['status']}**. {response['reason']}\n\n"+
                f"Next action: {response['next_action']}\n\nNext owner: {response['next_owner_role']}\n\n"+
                'No message or experiment order was sent. The full evidence and numerical assessment follow.\n\n'+render_brief(summary['assessment']))
        # Clear stale current-view files from an earlier export of this same run.
        for name,present in [('assessment.json',summary['assessment']),('brief.md',summary['assessment']),
                             ('handoff.json',state['handoff']),('handoff.md',state['handoff']),('specialist_response.json',state['specialist_response'])]:
            if not present:(out/name).unlink(missing_ok=True)
        write('README.md', '# Recorded synthetic CLI run\n\n'+
            'These files were exported from actual fixed-code execution; no LLM or real predictive model ran. '+
            'Reviews labelled simulated_human are scripted demonstrations, not real biology approvals.\n\n'+
            'Read run.json for current review/approval status. brief.md is a proposal, including when it has not been approved. '+
            'recorded_trace.json preserves the actual requests, outputs, review events and versioned assessments. '+
            'snapshots/ contains the exact captured runtime inputs. Historical trace replay does not authorize new action.\n')
        return {'run_id':run_id,'export_directory':str(out),'inputs_current':summary['inputs_current'],
                'approval_effective':summary['approval_effective'],'synthetic':True}
