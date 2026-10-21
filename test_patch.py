import json
from pathlib import Path
import pytest
from narrator import Scene, narration_issues
from story_catalog import get_story

@pytest.mark.parametrize('clue',['Grid C-7','Grid C‐7','Grid C‑7','Grid C–7','Grid C—7','Grid C−7','Grid\u00a0C-7'])
def test_equivalent_clue_typography(clue):
    assert not narration_issues(Scene(title='Chart',text=f'The chart reads “{clue}”.'),"Read 'Grid C-7'.",'the_last_signal')

@pytest.mark.parametrize('clue',['Grid C-8','Grid C-70','Grid D-7','Use channel nineteen'])
def test_meaningful_clue_changes_rejected(clue):
    assert 'missing or altered quoted clue' in narration_issues(Scene(title='Chart',text=clue),"Read 'Grid C-7'.",'the_last_signal')

@pytest.mark.parametrize('clock,invalid',[('23:60',True),('24:01',True),('99:99',True),('23:59',False),('00:00',False)])
def test_clock_range(clock,invalid):
    issues=narration_issues(Scene(title='Clock',text=f'The clock reads {clock}.'),'A clock.','the_last_signal')
    assert ('invalid clock time' in issues)==invalid


def test_real_baseline_failures():
    rows=json.loads((Path(__file__).parent/'data/baselines/last-signal-v2.0.json').read_text(encoding='utf-8'))
    assert len(rows)==10
    for row in rows:
        scene=Scene.model_validate_json(row['raw_response'])
        issues=narration_issues(scene,row['context']['required_outcome'],row['story_id'])
        if row['action']=='chart':
            assert 'missing or altered quoted clue' not in issues
        if '23:60' in scene.text:
            assert 'invalid clock time' in issues
    # Baseline evidence is retained, not relabeled with candidate outcomes.
    assert sum(r['status']=='fallback' for r in rows)==2
    assert sum(r['human_review']=='fail' for r in rows)==1


def test_rescue_outcome_names_transfer_and_shutdown_order():
    story=get_story('the_last_signal')
    assert 'from the disabled Kestrel onto the rescue boat' in story['endings']['rescue']
    assert 'only after this confirmation' in story['endings']['rescue']
