"""Append-only follow-up plans bound to an exact deferred human review."""
from contextlib import closing
import json
import uuid
from target_discovery.review.review_service import ReviewWorkflow, prepare_review, digest
from target_discovery.ui.ui_service import connect
from target_discovery.workflow.workflow import WorkflowError
from target_discovery.workflow.workflow_store import dump, now


def history(workspace,run_id,review_id=None):
    with closing(connect(workspace)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='review_followups'").fetchone():return []
        rows=db.execute('SELECT record FROM review_followups WHERE run_id=? ORDER BY rowid',(run_id,))
        records=[json.loads(r[0]) for r in rows]
    return [r for r in records if review_id is None or r['review_id']==review_id]


def prepare_followup(workspace,run_id,assessment_id):
    preview=prepare_review(workspace,run_id,assessment_id)
    if not preview['expected_review'] or preview['expected_review']['decision']!='DEFER':
        raise WorkflowError('A current deferred human decision is required.')
    records=history(workspace,run_id,preview['expected_review']['review_id'])
    preview['previous_followup_id']=records[-1]['followup_id'] if records else None
    return preview


class FollowupWorkflow(ReviewWorkflow):
    def save_followup(self,preview,required_work,owner,re_review_condition,status='Planned',progress_note=''):
        values={k:v.strip() for k,v in dict(required_work=required_work,owner=owner,
            re_review_condition=re_review_condition,progress_note=progress_note).items()}
        for name in ('required_work','owner','re_review_condition'):
            if not values[name]:raise WorkflowError('Required work, owner and re-review condition are all required.')
        if any(len(v)>8000 for v in values.values()):raise WorkflowError('Each field must be at most 8,000 characters.')
        if status not in ('Planned','In progress','Ready for re-review'):raise WorkflowError('Unknown follow-up status.')
        if status=='Ready for re-review' and not values['progress_note']:
            raise WorkflowError('Describe the completed work or evidence to support re-review.')
        request=digest({'preview':preview,'values':values,'status':status})
        with self.store.transaction():
            self.store.db.execute('''CREATE TABLE IF NOT EXISTS review_followups(
                followup_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, review_id TEXT NOT NULL,
                submission_id TEXT UNIQUE NOT NULL, request_sha256 TEXT NOT NULL, record TEXT NOT NULL,
                FOREIGN KEY(run_id,review_id) REFERENCES reviews(run_id,review_id))''')
            prior=self.store.db.execute('SELECT request_sha256,record FROM review_followups WHERE submission_id=?',
                (preview['submission_id'],)).fetchone()
            if prior:
                if prior[0]!=request:raise WorkflowError('Submission already saved with different content. Prepare again.')
                return json.loads(prior[1])
            state,brief=self._check(preview)
            review=state['review']
            if not review or review['decision']!='DEFER':raise WorkflowError('A current deferred human decision is required.')
            last=self.store.db.execute('SELECT followup_id FROM review_followups WHERE run_id=? AND review_id=? ORDER BY rowid DESC LIMIT 1',
                (state['run_id'],review['review_id'])).fetchone()
            if (last[0] if last else None)!=preview['previous_followup_id']:
                raise WorkflowError('Follow-up changed in another session. Prepare again.')
            record={'followup_id':uuid.uuid4().hex,'run_id':state['run_id'],'review_id':review['review_id'],
                'assessment_id':brief.assessment_id,'assessment_sha256':preview['assessment_sha256'],
                'previous_followup_id':preview['previous_followup_id'],'recorded_at':now(),'status':status,**values}
            self.store.db.execute('INSERT INTO review_followups VALUES(?,?,?,?,?,?)',
                (record['followup_id'],state['run_id'],review['review_id'],preview['submission_id'],request,dump(record)))
            self.store.event(state,'REVIEW_FOLLOWUP_SAVED',record)
        return record
