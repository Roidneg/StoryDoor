import json
import sqlite3

import pytest

from save_store import SaveError, load_game, save_game
from story_engine import StoryState, apply_choice


def journey(*actions):
    state = StoryState()
    scenes = [{"title": "Opening", "text": "At the gate."}]
    for action in actions:
        state, outcome = apply_choice(state, action)
        scenes.append({"title": action, "text": outcome})
    return state, scenes


def test_missing_save(tmp_path):
    assert load_game(tmp_path / "save.db") is None


@pytest.mark.parametrize("ending", ["release", "keep", "leave"])
def test_round_trip_endings(tmp_path, ending):
    path = tmp_path / "save.db"
    state, scenes = journey("demolition_notice", "study", "conservatory", ending)
    revision = save_game(state, scenes, 0, path)
    assert load_game(path) == (state, scenes, revision)


def test_resume_and_continue(tmp_path):
    path = tmp_path / "save.db"
    state, scenes = journey("demolition_notice")
    save_game(state, scenes, 0, path)
    state, scenes, revision = load_game(path)
    state, outcome = apply_choice(state, "study")
    scenes.append({"title": "Study", "text": outcome})
    assert save_game(state, scenes, revision, path) == 2
    assert load_game(path) == (state, scenes, 2)


def test_stale_tab_cannot_overwrite(tmp_path):
    path = tmp_path / "save.db"
    state, scenes = journey("demolition_notice")
    save_game(state, scenes, 0, path)
    with pytest.raises(SaveError):
        save_game(*journey(), 0, path)
    assert load_game(path) == (state, scenes, 1)


def test_invalid_scene_count_preserves_save(tmp_path):
    path = tmp_path / "save.db"
    state, scenes = journey("demolition_notice")
    save_game(state, scenes, 0, path)
    with pytest.raises(SaveError):
        save_game(state, scenes[:-1], 1, path)
    assert load_game(path) == (state, scenes, 1)


def test_corrupt_history_rejected(tmp_path):
    path = tmp_path / "save.db"
    save_game(*journey(), 0, path)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE saved_game SET payload=?", (json.dumps({"version": 1, "history": ["release"], "scenes": []}),))
    with pytest.raises(SaveError):
        load_game(path)
