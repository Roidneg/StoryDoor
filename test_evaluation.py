import json
from types import SimpleNamespace
import pytest
import narrator
from narrator import Scene, narration_issues
from evaluation import record_attempt, read_attempts, review_attempt, summarize
from story_engine import StoryState, apply_choice, available_choices
from save_store import save_game, load_game


def test_possessive_is_not_a_quote():
    assert narration_issues(Scene(title='Ending',text='Mara is free.'), "You speak Mara's name. The house's memory is freed.") == []


@pytest.mark.parametrize('text,issue',[
    ('as the required outcome dictates','instruction leakage'),
    ('the ink is still wet','wet ink'),
    ('the notice is nailed above the door','notice moved above door'),
    ('the key feels cold','key temperature change'),
])
def test_known_regressions(text, issue):
    assert issue in narration_issues(Scene(title='Scene',text=text),'A scene.')


def test_quoted_clue_required():
    assert 'missing or altered quoted clue' in narration_issues(Scene(title='Scene',text='Nothing here.'), "You read 'Use channel nine'.",'the_last_signal')


def test_house_checks_do_not_leak_into_second_story():
    assert not narration_issues(Scene(title='Scene',text='A green glow.'),'A scene.','the_last_signal')


def test_audit_and_review(tmp_path):
    path=tmp_path/'eval.db'
    rid=record_attempt({'status':'fallback','fallback':True,'raw_response':'bad original'},path)
    review_attempt(rid,'fail','Invented object',path)
    rows=read_attempts(path)
    assert rows[0]['raw_response']=='bad original'
    assert rows[0]['human_review']=='fail'
    assert summarize(rows)['fallback_rate']==1
    with pytest.raises(ValueError): review_attempt(rid,'unknown','',path)


def test_api_errors_excluded_from_fallback_denominator():
    assert summarize([{'status':'api_error','fallback':False,'human_review':'pending'}])['fallback_rate'] is None


def test_second_story_save_and_resume(tmp_path):
    state=StoryState(story_id='the_last_signal')
    scenes=[{'title':'Opening','text':'A signal.'}]
    for action in ['clock','chart','relay','manifest','rescue']:
        state,outcome=apply_choice(state,action)
        scenes.append({'title':action,'text':outcome})
    path=tmp_path/'save.db'
    revision=save_game(state,scenes,0,path)
    assert load_game(path)==(state,scenes,revision)
    assert state.ending=='rescue' and state.decisions==5


def test_rescue_locked_without_frequency():
    state=StoryState(story_id='the_last_signal')
    for action in ['power','chart','manifest','tape']:
        state,_=apply_choice(state,action)
    assert set(available_choices(state))=={'warn','silence'}


@pytest.mark.parametrize('raw,finish,expected',[
    (json.dumps({'title':'Gate','text':'A name is not a possession.'}),'stop','accepted'),
    (json.dumps({'title':'Gate','text':'as the required outcome dictates'}),'stop','fallback'),
    ('not json','stop','fallback'),
    ('unfinished','length','fallback'),
])
def test_narrator_records_raw_and_fallback(monkeypatch,raw,finish,expected):
    records=[]
    class Client:
        def __init__(self,**kwargs):
            self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def create(self,**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=raw))])
        def __enter__(self): return self
        def __exit__(self,*args): pass
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    monkeypatch.setattr(narrator,'Groq',Client)
    monkeypatch.setattr(narrator,'record_attempt',lambda r:records.append(r))
    after,scene=narrator.narrate_transition(StoryState(),'demolition_notice','')
    assert after.decisions==1
    assert records[0]['status']==expected
    assert records[0]['raw_response']==raw
    if expected=='fallback':
        assert scene.text==records[0]['context']['required_outcome']

@pytest.mark.parametrize('story_id',['the_forgotten_house','the_last_signal'])
def test_all_paths_finish_with_valid_endings(story_id):
    from story_catalog import get_story
    story=get_story(story_id)
    endings=set()
    def visit(state):
        choices=available_choices(state)
        if state.ending:
            assert not choices
            assert state.decisions==story['max_decisions']
            assert set(story['requirements'][state.ending]).issubset(state.clues)
            endings.add(state.ending)
            return
        assert choices
        for choice in choices:
            after,_=apply_choice(state,choice)
            visit(after)
    visit(StoryState(story_id=story_id))
    assert endings==set(story['endings'])


def test_old_house_save_loads(tmp_path):
    import sqlite3
    path=tmp_path/'old.db'
    scenes=[{'title':'Opening','text':'At the gate.'}]
    save_game(StoryState(),scenes,0,path)
    with sqlite3.connect(path) as conn:
        payload=json.loads(conn.execute('SELECT payload FROM saved_game').fetchone()[0])
        del payload['story_id']
        conn.execute('UPDATE saved_game SET payload=?',(json.dumps(payload),))
    assert load_game(path)[0]==StoryState()


def test_offline_regression_expectations():
    from evaluate_regressions import run
    report=run()
    assert report['detector_regressions']==0
    assert report['known_semantic_misses']==1
