from target_discovery.paths import PROJECT_ROOT
"""Presentation-only context. Never imported by workflow or agent code."""
import json
from pathlib import Path
import streamlit as st

ASSET = PROJECT_ROOT / 'ui_assets' / 'programme_context_v1.json'


def context_for(brief):
    """Bind to the selected brief, not the latest run's potentially different context."""
    context = json.loads(ASSET.read_text())
    if not brief or brief.get('target_id') != context['target_id']:
        return None
    return context


def programme_context(brief):
    context = context_for(brief)
    if context is None:
        return
    st.subheader(context['intended_indication'] + ' | ' + context['target_id'])
    st.caption(context['summary'] + ' Synthetic target; mechanism untested.')
    with st.expander('Programme hypothesis and scope', expanded=False):
        st.caption(context['version'] + ' · Presentation context, separate from the saved assessment')
        st.write(context['target_description'] + ' ' + context['programme_status'])
        for note in context['scope_notes']:
            st.write(note)
        if brief.get('context_id') != context['context_id']:
            st.warning('Context mismatch: this selected assessment does not match the programme assay context. Do not infer applicability from this programme description.')
        st.markdown('**Published disease background**')
        for reference in context['references']:
            st.markdown('[' + reference['citation'] + '](' + reference['url'] + ')')
            st.write('Supports: ' + reference['supports'])
            st.caption('Limits: ' + reference['limits'])
        st.markdown('**Synthetic target-specific evidence and frozen predictions**')
        st.write(context['experiment'])
        st.write(context['prediction_scope'])
        st.markdown('**Untested mechanistic and differentiation hypotheses**')
        st.write('Programme question: ' + context['programme_question'])
        st.write('Working mechanism: ' + context['mechanistic_hypothesis'])
        st.write('Immediate uncertainty: ' + context['immediate_uncertainty'])
        st.markdown('**Competing explanations for a lower readout**')
        for alternative in context['alternatives']:
            st.markdown('- ' + alternative)
        st.write('Potential differentiation: ' + context['differentiation_hypothesis'])
        st.markdown('**Questions for specialist teams**')
        for question in context['specialist_questions']:
            st.markdown('- ' + question)
        st.caption(context['specialist_scope'])
    if brief.get('context_id') != context['context_id']:
        st.warning('Programme assay context does not match the selected assessment; applicability is unestablished.')
