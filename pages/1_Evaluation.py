import json
import sqlite3
import streamlit as st
from evaluation import read_attempts, review_attempt, summarize

st.set_page_config(page_title='StoryDoor | Evaluation', layout='wide')
st.title('Narration evaluation')
st.caption('Targeted checks flag known patterns. Accepted narration still needs human continuity review. Logs include CLI and browser attempts, even if saving game progress later fails.')
try:
    rows = read_attempts()
except sqlite3.Error:
    st.error('Could not read the local evaluation database.')
    st.stop()
if not rows:
    st.info('Play a decision to record your first narration attempt.')
    st.stop()
labels = sorted({(r['story_id'], r['model'], r['prompt_version'], r['prompt_sha256']) for r in rows})
st.subheader('Recorded groups')
comparison=[]
for story_id, model, version, fingerprint in labels:
    cohort=[r for r in rows if (r['story_id'],r['model'],r['prompt_version'],r['prompt_sha256'])==(story_id,model,version,fingerprint)]
    comparison.append(dict(story=story_id, model=model, prompt_version=version, prompt_hash=fingerprint, **summarize(cohort)))
st.dataframe(comparison, hide_index=True)
group = st.selectbox('Story / model / prompt version / prompt hash', labels)
filtered = [r for r in rows if (r['story_id'],r['model'],r['prompt_version'],r['prompt_sha256']) == group]
st.write(summarize(filtered))
st.caption('Fallback rate = fallback responses / all returned responses. API errors are shown separately. Different story paths are not controlled A/B comparisons.')
st.dataframe([{'id':r['id'],'decision':r['decision'],'action':r['action'],'status':r['status'],'issues':', '.join(r['issues']),'human_review':r['human_review']} for r in filtered], hide_index=True)
st.download_button('Export selected attempts (JSON)',json.dumps(filtered,indent=2,ensure_ascii=False),file_name='storydoor-evaluation.json',mime='application/json')
selected = st.selectbox('Inspect an attempt', [r['id'] for r in filtered])
r = next(r for r in filtered if r['id']==selected)
st.subheader('Required outcome')
st.text(r['context']['required_outcome'])
st.subheader('Original model response')
st.text(r['raw_response'] or '(No response)')
st.subheader('Displayed scene')
st.json(r['displayed_scene'])
with st.expander('Prompt and established facts'):
    st.text(r['system_prompt'])
    st.json(r['context'])
st.write('Review the original response: does it preserve causal order, avoid undiscovered facts, and include every consequence? A fallback does not make the original response pass.')
with st.form('review_'+selected):
    verdict=st.selectbox('Human review of original response',['pending','pass','fail'],index=['pending','pass','fail'].index(r['human_review']))
    notes=st.text_area('Review notes',value=r['human_notes'])
    if st.form_submit_button('Save review'):
        try:
            review_attempt(selected,verdict,notes)
            st.rerun()
        except (sqlite3.Error,ValueError):
            st.error('Review was not saved.')
