import json
from pathlib import Path

DEFAULT_STORY = "the_forgotten_house"
STORIES = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (Path(__file__).parent / "stories").glob("*.json")}

def get_story(story_id=DEFAULT_STORY):
    if story_id not in STORIES:
        raise ValueError("Unknown story.")
    return STORIES[story_id]
