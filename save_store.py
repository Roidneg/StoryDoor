"""One local save slot, with replay validation and stale-tab protection."""
import json
import sqlite3
from pathlib import Path

from story_engine import StoryState, apply_choice

DB_PATH = Path(__file__).resolve().parent / "storydoor.db"


class SaveError(RuntimeError):
    pass


def validate(history, scenes, story_id="the_forgotten_house"):
    if not isinstance(history, list) or not isinstance(scenes, list):
        raise ValueError("Invalid save structure.")
    state = StoryState(story_id=story_id)
    from story_catalog import get_story
    get_story(story_id)
    for action in history:
        if not isinstance(action, str):
            raise ValueError("Invalid action.")
        state, _ = apply_choice(state, action)
    if len(scenes) != state.decisions + 1:
        raise ValueError("Scene count does not match choices.")
    for scene in scenes:
        if not isinstance(scene, dict) or set(scene) != {"title", "text"}:
            raise ValueError("Invalid scene.")
        for key, limit in (("title", 100), ("text", 6000)):
            value = scene[key]
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError("Invalid scene text.")
    return state


def connect(path):
    conn = sqlite3.connect(path, timeout=5)
    conn.execute("CREATE TABLE IF NOT EXISTS saved_game (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)")
    return conn


def load_game(path=DB_PATH):
    """Return (state, scenes, revision), or None. Never call the narrator."""
    try:
        conn = connect(path)
        try:
            row = conn.execute("SELECT revision, payload FROM saved_game WHERE id=1").fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        payload = json.loads(row[1])
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("Unsupported save version.")
        state = validate(payload["history"], payload["scenes"], payload.get("story_id", "the_forgotten_house"))
        return state, payload["scenes"], row[0]
    except (sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        raise SaveError("Could not load the saved journey. The save has not been changed.") from exc


def save_game(state, scenes, expected_revision, path=DB_PATH):
    """Atomically save; reject writes from an outdated browser session."""
    try:
        if validate(list(state.history), scenes, state.story_id) != state:
            raise ValueError("State does not match history.")
        payload = json.dumps({"version": 1, "story_id": state.story_id, "history": list(state.history), "scenes": scenes})
        conn = connect(path)
        try:
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute("SELECT revision FROM saved_game WHERE id=1").fetchone()
                revision = row[0] if row else 0
                if revision != expected_revision:
                    raise SaveError("Another tab updated this save. Refresh to resume the latest journey.")
                conn.execute("INSERT OR REPLACE INTO saved_game VALUES (1, ?, ?)", (revision + 1, payload))
            return revision + 1
        finally:
            conn.close()
    except (sqlite3.Error, ValueError, TypeError) as exc:
        raise SaveError("Could not save this journey. Your previous save is unchanged.") from exc
