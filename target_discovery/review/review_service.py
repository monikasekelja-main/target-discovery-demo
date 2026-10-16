"""Additive local review commands; the reference compiler and its bindings stay intact.

Previews are read-only. Only explicit submissions open the writable store. Outer
transactions guard the existing workflow commands, which run inside savepoints.
"""
from contextlib import contextmanager, closing
import hashlib
import json
import sqlite3
from pathlib import Path
import uuid

from target_discovery.agents.agent_layer import binding
from target_discovery.workflow.contracts import DecisionBrief, Review, content_fingerprint
from target_discovery.workflow.workflow import Workflow, WorkflowError, PACKAGE, checked_id
from target_discovery.workflow.workflow_store import Store, dump, now
from target_discovery.ui.ui_service import connect, load_run, review_status
from target_discovery.review.rationale_advisor import advisor_version, draft_fields, validate_advice, local_advice, PROMPT, RationaleAdvice


def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()


def service_version():
    return digest({'review_service':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'advisor':advisor_version()})


def report_receipt(workspace, state, brief, attempt_id):
    checked_id(attempt_id)
    parent=Path(workspace).resolve()/'agent-reports'/checked_id(state['run_id'])
    path=parent/attempt_id/'report.json'
    if path.is_symlink() or not path.resolve().is_relative_to(parent) or not parent.resolve().is_relative_to(Path(workspace).resolve()):
        raise WorkflowError('Report path is outside the saved run.')
    raw=path.read_bytes();report=json.loads(raw);bound=report['binding']
    canonical=content_fingerprint(DecisionBrief.model_validate(brief))
    if bound['run_id']!=state['run_id'] or bound['assessment_id']!=brief['assessment_id'] or bound['assessment_sha256']!=canonical:
        raise WorkflowError('Report belongs to a different assessment or canonical digest.')
    current=bound==binding(state,brief)
    return {'run_id':state['run_id'],'attempt_id':attempt_id,
            'report_sha256':hashlib.sha256(raw).hexdigest(),'assessment_sha256':canonical,
            'binding':bound,'effective_status':report['status'] if current else 'STALE',
            'mode':report.get('mode','unknown')}


def review_receipt(workspace,run_id,review_id):
    if review_id is None:return None
    with closing(connect(workspace)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='review_receipts'").fetchone():return None
        row=db.execute('SELECT receipt FROM review_receipts WHERE run_id=? AND review_id=?',(run_id,review_id)).fetchone()
    return json.loads(row[0]) if row else None


def handoff_receipt(workspace,run_id,handoff_id):
    with closing(connect(workspace)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='handoff_receipts'").fetchone():return None
        row=db.execute('SELECT receipt FROM handoff_receipts WHERE run_id=? AND handoff_id=?',(run_id,handoff_id)).fetchone()
    return json.loads(row[0]) if row else None


def prepare_review(workspace,run_id,assessment_id,attempt_id=None,root=PACKAGE):
    run=load_run(workspace,run_id,root);state=run['state']
    if not run['inputs_current'] or state['phase']=='BLOCKED':raise WorkflowError('Inputs are stale or blocked; resolve them before review.')
    if state['current_assessment_id']!=assessment_id:raise WorkflowError('Only the current assessment can be reviewed.')
    brief=next(b for b in run['assessments'] if b['assessment_id']==assessment_id)
    report=report_receipt(workspace,state,brief,attempt_id) if attempt_id else None
    return {'submission_id':uuid.uuid4().hex,'service_version':service_version(),
            'workspace':str(Path(workspace).resolve()),'run_id':run_id,'assessment_id':assessment_id,
            'assessment_sha256':content_fingerprint(DecisionBrief.model_validate(brief)),
            'brief':brief,'expected_review':state['review'],'consultation':report,
            'consultation_choice':'saved_report' if report else 'no_report'}


def prepare_handoff(workspace,run_id,assessment_id,root=PACKAGE):
    preview=prepare_review(workspace,run_id,assessment_id,root=root)
    run=load_run(workspace,run_id,root)
    if not review_status(run,preview['brief'])[1]:raise WorkflowError('Explicit current human approval is required.')
    brief=preview['brief']
    if brief['scientific_recommendation']!='ADVANCE_TO_REPLICATION' or not brief['prerequisites_passed']:
        raise WorkflowError('Handoff requires a supportive result with passed assay prerequisites.')
    review=preview['expected_review']
    if not review or review!=run['state']['review']:raise WorkflowError('Review changed while preparing; prepare again.')
    preview['review_receipt']=review_receipt(workspace,run_id,review['review_id'])
    preview['platform']='antibody'
    return preview


def advice_binding(preview,draft):
    return digest({'preview':preview,'draft':draft,'advisor_version':advisor_version()})


def load_rationale_check(workspace,check_id):
    with closing(connect(workspace)) as db:
        row=db.execute('SELECT request,result,result_sha256 FROM rationale_checks JOIN rationale_results USING(check_id) WHERE check_id=?',(check_id,)).fetchone()
    if not row:raise WorkflowError('No completed rationale check found.')
    request,result=json.loads(row[0]),json.loads(row[1])
    if digest(result)!=row[2]:raise WorkflowError('Rationale advice integrity check failed.')
    return {'request':request,'result':result,'result_sha256':row[2]}


class SubmissionStore(Store):
    @contextmanager
    def transaction(self):
        if not self.db.in_transaction:
            with super().transaction():yield
        else:
            self.db.execute('SAVEPOINT review_command')
            try:
                yield
                self.db.execute('RELEASE review_command')
            except BaseException:
                self.db.execute('ROLLBACK TO review_command')
                self.db.execute('RELEASE review_command')
                raise

    def advice_schema(self):
        self.db.execute('''CREATE TABLE IF NOT EXISTS rationale_checks(
            check_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, request TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(run_id))''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS rationale_results(
            check_id TEXT PRIMARY KEY, result TEXT NOT NULL, result_sha256 TEXT NOT NULL,
            FOREIGN KEY(check_id) REFERENCES rationale_checks(check_id))''')

    def receipts_schema(self):
        # Transactional and additive; never rewrite or backfill legacy records.
        self.db.execute('''CREATE TABLE IF NOT EXISTS review_receipts(
            run_id TEXT NOT NULL, review_id TEXT NOT NULL, submission_id TEXT NOT NULL,
            request_sha256 TEXT NOT NULL, receipt TEXT NOT NULL,
            PRIMARY KEY(run_id,review_id), UNIQUE(run_id,submission_id),
            FOREIGN KEY(run_id,review_id) REFERENCES reviews(run_id,review_id))''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS handoff_receipts(
            run_id TEXT NOT NULL, handoff_id TEXT NOT NULL, receipt TEXT NOT NULL,
            PRIMARY KEY(run_id,handoff_id), FOREIGN KEY(run_id) REFERENCES runs(run_id))''')


class ReviewWorkflow(Workflow):
    def __init__(self,workspace,fixture_root=PACKAGE):
        path=Path(workspace).resolve()
        if not (path/'workflow.sqlite3').is_file():raise WorkflowError('Existing saved workspace required.')
        if path.is_relative_to(PACKAGE/'recorded_examples'):
            raise WorkflowError('Bundled examples are read-only. Use your own saved workspace.')
        self.root=Path(fixture_root).resolve();self.store=SubmissionStore(path)

    def _check(self,preview):
        if preview['workspace']!=str(self.store.workspace) or preview['service_version']!=service_version():
            raise WorkflowError('Workspace or review service changed; prepare a new preview.')
        state=self.store.load(preview['run_id']);self._ensure_fresh(state)
        if state['phase']=='BLOCKED':raise WorkflowError('Resolve blocked inputs before submission.')
        brief=self._current_brief(state,preview['assessment_id'])
        if (content_fingerprint(brief)!=preview['assessment_sha256'] or
                content_fingerprint(DecisionBrief.model_validate(preview['brief']))!=preview['assessment_sha256']):
            raise WorkflowError('Assessment content changed; prepare a new preview.')
        if state['review']!=preview['expected_review']:
            raise WorkflowError('Human review changed; prepare a new preview.')
        return state,brief

    def _check_report(self,state,brief,receipt):
        if receipt is not None:
            actual=report_receipt(self.store.workspace,state,brief.model_dump(mode='json'),receipt['attempt_id'])
            if actual!=receipt:raise WorkflowError('Consulted report changed; prepare a new preview.')

    def check_rationale(self,preview,decision,reviewer,rationale,*,next_action='',historical_ack=False,
                        mode='live_llm',model='',provider=None):
        draft=draft_fields(decision,reviewer,rationale,next_action,historical_ack)
        if mode not in ('live_llm','local_checks'):raise WorkflowError('Unknown advice mode.')
        if mode=='local_checks' and provider is not None:raise WorkflowError('Local checks cannot call a provider.')
        check_id=uuid.uuid4().hex
        request={'check_id':check_id,'run_id':preview['run_id'],'assessment_id':preview['assessment_id'],
            'assessment_sha256':preview['assessment_sha256'],'draft':draft,
            'input_sha256':advice_binding(preview,draft),'advisor_version':advisor_version(),
            'service_version':preview['service_version'],'mode':mode,'requested_model':model if mode=='live_llm' else None,
            'created_at':now()}
        # Record intent before a possibly paid call; never hold the DB lock while waiting.
        with self.store.transaction():
            state,brief=self._check(preview);self._check_report(state,brief,preview['consultation'])
            self.store.advice_schema()
            self.store.db.execute('INSERT INTO rationale_checks VALUES(?,?,?)',(check_id,state['run_id'],dump(request)))
            self.store.event(state,'RATIONALE_CHECK_REQUESTED',request)
        result={'check_id':check_id,'input_sha256':request['input_sha256'],'mode':mode,
            'status':'COMPLETED','feedback':None,'error':None,'provider':None,'completed_at':None}
        try:
            if mode=='local_checks':value=local_advice(draft)
            else:
                from target_discovery.agents.agent_provider import OpenAIProvider
                if provider is None:provider=OpenAIProvider(model,max_output_tokens=3000)
                if provider.mode!='live_llm':raise WorkflowError('A live advice check requires a live provider.')
                # Reviewer identity is kept locally; only decision/reasoning and the
                # canonical evidence needed to critique it are sent to the provider.
                payload={'assessment':preview['brief'],
                    'draft':{k:v for k,v in draft.items() if k in ('decision','rationale','next_action')},
                    'scope':'Advisory reasoning review for a local synthetic workflow; no approval authority.'}
                value,meta=provider.complete('human_rationale_advisor',PROMPT,payload,RationaleAdvice.model_json_schema())
                result['provider']={k:meta.get(k) for k in ('response_id','resolved_model','usage')}
            result['feedback']=validate_advice(value,draft)
        except Exception as exc:
            from target_discovery.agents.agent_provider import ProviderError
            result['status']='FAILED'
            result['error']=str(exc) if isinstance(exc,ProviderError) else 'Advisory check failed or returned invalid output. No guidance was accepted.'
        with self.store.transaction():
            try:
                state,brief=self._check(preview);self._check_report(state,brief,preview['consultation'])
            except (ValueError,OSError,KeyError):
                result['status']='STALE';result['error']='Assessment, inputs, review or report changed during the check. Prepare again.'
            result['completed_at']=now()
            self.store.db.execute('INSERT INTO rationale_results VALUES(?,?,?)',(check_id,dump(result),digest(result)))
            self.store.event(self.store.load(preview['run_id']),'RATIONALE_CHECK_COMPLETED',result)
        return load_rationale_check(self.store.workspace,check_id)

    def _saved_check(self,check_id):
        if not check_id:raise WorkflowError('Check this draft rationale before saving the decision.')
        try:
            row=self.store.db.execute('SELECT request,result,result_sha256 FROM rationale_checks JOIN rationale_results USING(check_id) WHERE check_id=?',(check_id,)).fetchone()
        except sqlite3.OperationalError:
            raise WorkflowError('No saved rationale check exists. Check this draft first.') from None
        if not row:raise WorkflowError('No completed rationale check found.')
        request,result=json.loads(row[0]),json.loads(row[1])
        if digest(result)!=row[2] or request['input_sha256']!=result['input_sha256']:
            raise WorkflowError('Rationale advice integrity check failed.')
        return request,result,row[2]

    def _validate_check(self,preview,draft,check_id,acknowledged,override,reason):
        request,result,result_sha=self._saved_check(check_id)
        if request['run_id']!=preview['run_id'] or request['input_sha256']!=advice_binding(preview,draft):
            raise WorkflowError('Draft or assessment changed since the advice. Check the current draft again.')
        if result['status']=='STALE':raise WorkflowError('Advice is stale; prepare and check again.')
        if not acknowledged:raise WorkflowError('Read and acknowledge the advisory feedback before saving.')
        clear=result['status']=='COMPLETED' and result['mode']=='live_llm' and result['feedback']['outcome']=='NO_CONCERNS_IDENTIFIED'
        if not clear and not override:raise WorkflowError('Revise and recheck, or explicitly override the advice or unavailable AI check.')
        if override and (len(reason.strip())<20 or len(reason.split())<4):
            raise WorkflowError('Explain your override in a substantive sentence (at least 20 characters and four words).')
        return {'check_id':check_id,'input_sha256':request['input_sha256'],'result_sha256':result_sha,
            'request_sha256':digest(request),'mode':result['mode'],'status':result['status'],
            'outcome':result['feedback']['outcome'] if result['feedback'] else None,
            'feedback_acknowledged':True,'overridden':bool(override),'override_reason':reason if override else None}

    def _verify_saved_advice(self,advice):
        request,result,sha=self._saved_check(advice['check_id'])
        if sha!=advice['result_sha256'] or digest(request)!=advice['request_sha256']:
            raise WorkflowError('Saved rationale advice changed; handoff cannot use this review.')

    def submit_review(self,preview,decision,reviewer,rationale,*,acknowledged=False,historical_ack=False,next_action='',
                      check_id=None,advice_acknowledged=False,override=False,override_reason=''):
        if not acknowledged:raise WorkflowError('Explicit human acknowledgement is required.')
        if decision not in ('APPROVE','DEFER','AMEND'):raise WorkflowError('Unknown review decision.')
        if not reviewer.strip() or not rationale.strip():raise WorkflowError('Reviewer and rationale are required.')
        if decision=='AMEND' and not next_action.strip():raise WorkflowError('Amendment needs a proposed next action.')
        consulted=preview['consultation']
        if consulted and consulted['effective_status']=='STALE' and not historical_ack:
            raise WorkflowError('Explicit acknowledgement of historical advice is required.')
        request=digest({'preview':preview,'decision':decision,'reviewer':reviewer,'rationale':rationale,
                        'historical_ack':historical_ack,'next_action':next_action,'check_id':check_id,
                        'advice_acknowledged':advice_acknowledged,'override':override,'override_reason':override_reason})
        with self.store.transaction():
            self.store.receipts_schema()
            prior=self.store.db.execute('SELECT request_sha256,receipt FROM review_receipts WHERE run_id=? AND submission_id=?',
                (preview['run_id'],preview['submission_id'])).fetchone()
            if prior:
                if prior[0]!=request:raise WorkflowError('Submission already used with different content; prepare again.')
                return json.loads(prior[1])
            state,brief=self._check(preview);self._check_report(state,brief,consulted)
            advice=self._validate_check(preview,draft_fields(decision,reviewer,rationale,next_action,historical_ack),
                check_id,advice_acknowledged,override,override_reason)
            if decision=='AMEND':
                super().amend(state['run_id'],brief.assessment_id,reviewer,rationale,next_action)
                state=self.store.load(state['run_id'])
                review=self.store.reviews(state['run_id'])[-1]
            else:
                # A new explicit submission is a new review, even when only the
                # consulted report differs. Retries are deduplicated by submission ID.
                state['review_seq']+=1
                review=Review.model_validate({'synthetic':True,'review_id':f"{state['run_id']}-R{state['review_seq']:03}",
                    'assessment_id':brief.assessment_id,'reviewed_content_sha256':content_fingerprint(brief),
                    'reviewer_role':reviewer,'actor_mode':'local_demo_operator','decision':decision,
                    'rationale':rationale,'authorization_scope':'local_simulation_only'}).model_dump(mode='json')
                self.store.add_review(state,review);self.store.event(state,'REVIEW_RECORDED',review)
                if state['handoff']:
                    self.store.event(state,'HANDOFF_INVALIDATED',{'handoff_id':state['handoff']['handoff_id'],'reason':'Review changed.'})
                state.update(review=review,handoff=None,specialist_response=None,
                    phase='DEFERRED' if decision=='DEFER' else ('AWAITING_RESULT' if not state['selected_experiment'] else 'REVIEWED'),
                    workflow_status=brief.workflow_status)
                self.store.save(state)
            receipt={'run_id':state['run_id'],'review_id':review['review_id'],
                'assessment_id':brief.assessment_id,'assessment_sha256':content_fingerprint(brief),
                'consultation_choice':preview['consultation_choice'],'consultation':consulted,
                'rationale_advice':advice,
                'historical_acknowledged':bool(historical_ack),'actor_mode':'local_demo_operator',
                'authorization_scope':'local_simulation_only','recorded_at':now(),
                'service_version':preview['service_version'],'current_assessment_id':state['current_assessment_id']}
            self.store.db.execute('INSERT INTO review_receipts VALUES(?,?,?,?,?)',
                (state['run_id'],review['review_id'],preview['submission_id'],request,dump(receipt)))
            self.store.event(state,'REVIEW_CONSULTATION_RECORDED',receipt)
            # Recheck external report bytes immediately before committing.
            self._check_report(state,brief,consulted)
            self._ensure_fresh(state)
        return receipt

    def submit_handoff(self,preview,*,acknowledged=False):
        if not acknowledged:raise WorkflowError('Explicit local handoff acknowledgement is required.')
        if preview.get('platform')!='antibody':raise WorkflowError('Only the antibody simulation is implemented.')
        with self.store.transaction():
            self.store.receipts_schema();state,brief=self._check(preview)
            expected=preview['review_receipt']
            row=self.store.db.execute('SELECT receipt FROM review_receipts WHERE run_id=? AND review_id=?',
                (state['run_id'],state['review']['review_id'] if state['review'] else '')).fetchone()
            actual=json.loads(row[0]) if row else None
            if expected!=actual:raise WorkflowError('Review consultation receipt changed; prepare again.')
            self._check_report(state,brief,actual['consultation'] if actual else None)
            if actual and actual.get('rationale_advice'):self._verify_saved_advice(actual['rationale_advice'])
            existing=state['handoff']
            super().handoff(state['run_id'],brief.assessment_id)
            state=self.store.load(state['run_id']);handoff=state['handoff']
            if not existing:
                receipt={'handoff_id':handoff['handoff_id'],'review_id':state['review']['review_id'],
                    'assessment_sha256':content_fingerprint(brief),'platform':'antibody',
                    'review_receipt':actual,'consultation_provenance':'recorded' if actual else 'legacy_not_recorded',
                    'service_version':preview['service_version'],'recorded_at':now()}
                self.store.db.execute('INSERT INTO handoff_receipts VALUES(?,?,?)',
                    (state['run_id'],handoff['handoff_id'],dump(receipt)))
                self.store.event(state,'HANDOFF_PROVENANCE_RECORDED',receipt)
            self._check_report(state,brief,actual['consultation'] if actual else None)
            self._ensure_fresh(state)
        return handoff
