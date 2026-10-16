"""Human-owned next steps; saving a plan never changes the scientific assessment."""
import sqlite3
from pathlib import Path
import streamlit as st
from review_service import prepare_review
from followup_service import history, prepare_followup, FollowupWorkflow
from ui_service import review_status
from ui_reviews import available


def start_re_review(workspace,run_id,assessment_id):
    try:
        preview=prepare_review(workspace,run_id,assessment_id)
        key='review_preview:'+str(Path(workspace).resolve())+':'+run_id+':'+assessment_id
        st.session_state[key]=preview
        st.session_state['review_report']='No agent report consulted'
        st.session_state['view']='Challenge & review'
        st.session_state['action_notice']='Re-review opened below under Record human review. Enter your updated rationale, check it, then record a new decision.'
    except (ValueError,OSError,KeyError,sqlite3.Error) as exc:
        st.session_state['re_review_error']=str(exc)


def followup_controls(workspace,run,brief):
    if not brief:return
    label,_,review=review_status(run,brief)
    records=history(workspace,run['state']['run_id'])
    matching=[r for r in records if review and r['review_id']==review['review_id']]
    if not matching and (not review or review['decision']!='DEFER') and not records:return
    st.subheader('What happens next')
    st.caption('Track the work needed to reconsider a deferred decision. Saving a plan does not approve progression or send a message to its owner.')
    latest=matching[-1] if matching else None
    if latest:
        with st.container(border=True):
            st.markdown('**Follow-up status:** '+latest['status'])
            st.markdown('**Required work**');st.write(latest['required_work'])
            st.markdown('**Owner:** '+latest['owner'])
            st.markdown('**Re-review condition**');st.write(latest['re_review_condition'])
            if latest['progress_note']:st.markdown('**Progress / evidence note**');st.write(latest['progress_note'])
            st.caption('Saved '+latest['recorded_at']+' · Review '+latest['review_id'])
        if latest['status']=='Ready for re-review':
            st.info('Ready for a human to reconsider. The decision remains deferred until a new review is recorded. An evidence note is not an imported scientific result.')
    elif review and review['decision']=='DEFER':st.info('No follow-up plan recorded for this deferred decision yet.')
    if records:
        with st.expander('Follow-up history'):
            for record in reversed(records):
                st.markdown('**'+record['status']+'** · '+record['assessment_id']+' · '+record['review_id'])
                st.write(record['required_work'])
                st.write('Owner: '+record['owner'])
                st.write('Re-review condition: '+record['re_review_condition'])
                if record['progress_note']:st.write(record['progress_note'])
                st.caption(record['recorded_at'])
    if label!='Deferred':
        st.caption('Earlier plans remain in history. A new plan requires a current deferred decision.')
        return
    if not available(workspace,run,brief):return
    if 're_review_error' in st.session_state:st.error(st.session_state.pop('re_review_error'))
    if latest and latest['status']=='Ready for re-review':
        st.button('Start re-review',key='start_re_review',on_click=start_re_review,
                  args=(workspace,run['state']['run_id'],brief['assessment_id']))
        st.caption('Opens a fresh decision form in Challenge & review below the saved report. Include how the follow-up addresses your earlier concern in the new rationale. The AI check receives your rationale and the current assessment; follow-up notes are not sent automatically.')
    key='followup_preview:'+str(workspace)+':'+review['review_id']
    if st.button('Update follow-up plan' if latest else 'Add follow-up plan',key='prepare_followup'):
        st.session_state[key]=prepare_followup(workspace,run['state']['run_id'],brief['assessment_id'])
    preview=st.session_state.get(key)
    if not preview:return
    with st.form('followup_'+preview['submission_id']):
        work=st.text_area('Required work',value=latest['required_work'] if latest else '')
        owner=st.text_input('Follow-up owner',value=latest['owner'] if latest else '')
        condition=st.text_area('Condition for re-review',value=latest['re_review_condition'] if latest else '')
        choices=['Planned','In progress','Ready for re-review']
        status=st.selectbox('Follow-up status',choices,index=choices.index(latest['status']) if latest else 0)
        note=st.text_area('Progress / evidence note',value=latest['progress_note'] if latest else '',help='Required when marking ready for re-review. This note does not import evidence into the assessment.')
        submitted=st.form_submit_button('Save follow-up plan')
    if submitted:
        app=None
        try:
            app=FollowupWorkflow(workspace)
            app.save_followup(preview,work,owner,condition,status,note)
            del st.session_state[key]
            st.session_state['action_notice']='Follow-up plan saved. The human decision remains deferred.'
            st.rerun()
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:st.error('Follow-up not saved: '+str(exc))
        finally:
            if app:app.close()
