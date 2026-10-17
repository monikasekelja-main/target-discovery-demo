"""Opt-in live proposal chat; session memory only; no automatic API calls."""
import os
import streamlit as st
from target_discovery.predictive.live_chat import context,ask
from target_discovery.agents.agent_provider import ProviderError

def render(study,nomination,review):
    ctx=context(study,nomination,review)
    # Discard old conversation when the scientific/review context changes.
    if st.session_state.get('proposal_live_binding')!=ctx['binding']:
        st.session_state['proposal_live_binding']=ctx['binding']
        st.session_state['proposal_live_history']=[]
    history=st.session_state.get('proposal_live_history',[])
    st.caption('LIVE AI · read-only advice about this proposal. Synthetic study results remain synthetic.')
    st.caption('One paid request per submission, up to 2,400 output tokens and a 45-second request timeout. No search, tools or automatic retries. Sends this study, proposal, matching review and up to three recent exchanges to OpenAI. Session-only history; store=false.')
    st.caption('Source checks confirm exact excerpts, not scientific correctness. AI advice cannot change evidence or approvals.')
    for record in history:
        with st.chat_message('user'):st.write(record['question'])
        with st.chat_message('assistant'):
            st.write(record['answer']['answer'])
            st.caption('What this does not establish: '+record['answer']['limitations'])
            with st.expander('Source excerpts and context'):
                for c in record['answer']['citations']:
                    st.write('**'+{'boundary':'Demo boundaries','study':'Study plan','proposal':'Current proposal','review':'Human review'}.get(c['source_id'],c['source_id'])+'**');st.text(c['excerpt'])
                st.caption('Model: '+str(record['model']))
                st.code(record['binding'],language=None)
    configured=bool(os.environ.get('OPENAI_API_KEY'))
    if not configured:st.warning('OPENAI_API_KEY is not available in this Streamlit server environment. Set it locally and restart the server; never paste it here or commit it.')
    with st.form('proposal_live_form'):
        model=st.text_input('Proposal chat model',value=os.environ.get('TARGET_PROPOSAL_MODEL',os.environ.get('TARGET_REVIEW_MODEL','gpt-6-astra')),key='proposal_live_model')
        question=st.text_area('Your question about this proposal',max_chars=4000,key='proposal_live_question_'+ctx['binding'])
        submitted=st.form_submit_button('Send to live assistant',disabled=not configured)
    if submitted:
        try:
            with st.spinner('Reading this proposal…'):
                record=ask(ctx,question,model,history)
            st.session_state['proposal_live_history']=(history+[record])[-6:]
            st.rerun()
        except (ValueError,ProviderError) as exc:st.error(str(exc))
        except Exception:st.error('Live request failed. No answer accepted and no automatic retry. Check your server configuration.')
    if history and st.button('Clear live conversation',key='proposal_live_clear'):
        st.session_state['proposal_live_history']=[];st.rerun()
