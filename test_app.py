from pathlib import Path
from streamlit.testing.v1 import AppTest
from narrator import Scene
from story_engine import apply_choice
import narrator
import save_store
import evaluation


def test_browser_save_resume_and_second_story(monkeypatch,tmp_path):
    path=tmp_path/'game.db'
    original_save,original_load=save_store.save_game,save_store.load_game
    monkeypatch.setattr(save_store,'save_game',lambda s,sc,r:original_save(s,sc,r,path))
    monkeypatch.setattr(save_store,'load_game',lambda:original_load(path))
    def fake_narrate(before,choice,previous):
        after,outcome=apply_choice(before,choice)
        return after,Scene(title='Test scene',text=outcome)
    monkeypatch.setattr(narrator,'narrate_transition',fake_narrate)
    app=AppTest.from_file(str(Path(__file__).parent/'app.py')).run()
    assert not app.exception
    app.button[0].click().run()
    assert app.session_state['story_state'].decisions==1
    refreshed=AppTest.from_file(str(Path(__file__).parent/'app.py')).run()
    refreshed.button[0].click().run()
    assert refreshed.session_state['story_state'].decisions==1
    # New session chooses the other story and explicitly replaces the save.
    new=AppTest.from_file(str(Path(__file__).parent/'app.py')).run()
    new.sidebar.selectbox[0].select('the_last_signal').run()
    new.checkbox[0].check().run()
    new.button[1].click().run()
    assert not new.exception
    assert new.session_state['story_state'].story_id=='the_last_signal'
    new.button[0].click().run()
    assert new.session_state['story_state'].decisions==1


def test_evaluation_page_review(monkeypatch,tmp_path):
    path=tmp_path/'eval.db'
    rid=evaluation.record_attempt({'story_id':'the_last_signal','model':'mock','prompt_sha256':'hash','action':'clock','decision':1,'status':'accepted','fallback':False,'issues':[],'raw_response':'raw','displayed_scene':{'title':'Scene','text':'text'},'context':{'required_outcome':'outcome'},'system_prompt':'prompt'},path)
    original_read,original_review=evaluation.read_attempts,evaluation.review_attempt
    monkeypatch.setattr(evaluation,'read_attempts',lambda:original_read(path))
    monkeypatch.setattr(evaluation,'review_attempt',lambda i,r,n:original_review(i,r,n,path))
    app=AppTest.from_file(str(Path(__file__).parent/'pages/1_Evaluation.py')).run()
    assert not app.exception
    app.selectbox[2].select('fail')
    app.text_area[0].set_value('Causal order incorrect')
    app.button[0].click().run()
    assert not app.exception
    assert original_read(path)[0]['human_review']=='fail'


def test_switch_mid_journey_requires_confirmation_and_persists(monkeypatch,tmp_path):
    path=tmp_path/'switch.db'
    original_save,original_load=save_store.save_game,save_store.load_game
    monkeypatch.setattr(save_store,'save_game',lambda s,sc,r:original_save(s,sc,r,path))
    monkeypatch.setattr(save_store,'load_game',lambda:original_load(path))
    def fake_narrate(before,choice,previous):
        after,outcome=apply_choice(before,choice)
        return after,Scene(title='Test scene',text=outcome)
    monkeypatch.setattr(narrator,'narrate_transition',fake_narrate)
    app=AppTest.from_file(str(Path(__file__).parent/'app.py')).run()
    next(b for b in app.button if b.label=='Follow this path').click().run()
    before=original_load(path)
    assert before[0].decisions==1
    app.sidebar.selectbox[0].select('the_last_signal').run()
    assert original_load(path)==before
    assert app.session_state['story_state']==before[0]
    assert app.sidebar.button(key='start_selected_story').disabled
    app.sidebar.checkbox[0].check().run()
    app.sidebar.button(key='start_selected_story').click().run()
    assert not app.exception
    after=original_load(path)
    assert after[0].story_id=='the_last_signal'
    assert after[0].decisions==0 and len(after[1])==1
    assert not app.sidebar.checkbox[0].value
    resumed=AppTest.from_file(str(Path(__file__).parent/'app.py')).run()
    next(b for b in resumed.button if b.label=='Resume saved journey').click().run()
    assert resumed.session_state['story_state']==after[0]


def test_failed_switch_keeps_active_journey(monkeypatch,tmp_path):
    path=tmp_path/'switch.db'
    original_save,original_load=save_store.save_game,save_store.load_game
    monkeypatch.setattr(save_store,'save_game',lambda s,sc,r:original_save(s,sc,r,path))
    monkeypatch.setattr(save_store,'load_game',lambda:original_load(path))
    app=AppTest.from_file(str(Path(__file__).parent/'app.py')).run()
    before=original_load(path)
    def failed_save(*args):
        raise save_store.SaveError('Could not save')
    monkeypatch.setattr(save_store,'save_game',failed_save)
    app.sidebar.selectbox[0].select('the_last_signal').run()
    app.sidebar.checkbox[0].check().run()
    app.sidebar.button(key='start_selected_story').click().run()
    assert not app.exception
    assert app.session_state['story_state']==before[0]
    assert original_load(path)==before
    assert app.error
