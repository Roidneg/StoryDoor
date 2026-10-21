from dataclasses import dataclass, replace
from story_catalog import DEFAULT_STORY, get_story

@dataclass(frozen=True)
class StoryState:
    decisions: int = 0
    clues: tuple[str, ...] = ()
    visited_rooms: tuple[str, ...] = ()
    history: tuple[str, ...] = ()
    ending: str | None = None
    story_id: str = DEFAULT_STORY

def available_choices(state):
    story = get_story(state.story_id)
    if state.ending is not None or state.decisions >= story["max_decisions"]:
        return {}
    if state.decisions == 0:
        return dict(story["opening_choices"])
    if state.decisions < story["max_decisions"] - 1:
        return {key: room["label"] for key, room in story["rooms"].items() if key not in state.visited_rooms}
    return {key: label for key, label in story["ending_choices"].items() if set(story["requirements"][key]).issubset(state.clues)}

def apply_choice(state, choice_id):
    if choice_id not in available_choices(state):
        raise ValueError(f"That choice is unavailable: {choice_id}")
    story = get_story(state.story_id)
    clues, visited, ending = state.clues, state.visited_rooms, None
    if state.decisions == 0:
        clue, outcome = story["opening_results"][choice_id]
        if clue not in clues: clues += (clue,)
    elif state.decisions < story["max_decisions"] - 1:
        room = story["rooms"][choice_id]
        outcome, clue = room["outcome"], room["clue"]
        visited += (choice_id,)
        if clue not in clues: clues += (clue,)
        for required_clue, extra in room.get("conditional_outcomes", {}).items():
            if required_clue in clues:
                outcome += " " + extra

    else:
        ending, outcome = choice_id, story["endings"][choice_id]
    return replace(state, decisions=state.decisions+1, clues=clues, visited_rooms=visited, ending=ending, history=state.history+(choice_id,)), outcome
