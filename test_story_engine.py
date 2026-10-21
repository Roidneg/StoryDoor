import pytest

from story_engine import StoryState, apply_choice, available_choices


def play(*actions):
    state = StoryState()
    for action in actions:
        state, _ = apply_choice(state, action)
    return state


def test_opening_has_three_choices():
    assert set(available_choices(StoryState())) == {
        "front_door",
        "upstairs_light",
        "demolition_notice",
    }


def test_choice_does_not_mutate_original_state():
    original = StoryState()
    updated, _ = apply_choice(original, "demolition_notice")

    assert original == StoryState()
    assert updated.decisions == 1
    assert "mara_name" in updated.clues


def test_visited_room_cannot_be_selected_again():
    state = play("front_door", "study")

    assert set(available_choices(state)) == {
        "nursery",
        "conservatory",
    }

    with pytest.raises(ValueError):
        apply_choice(state, "study")


def test_release_requires_both_clues():
    # These rooms reveal the words, but this path never learns her name.
    state = play("front_door", "study", "conservatory")

    assert set(available_choices(state)) == {"keep", "leave"}

    with pytest.raises(ValueError):
        apply_choice(state, "release")


def test_opening_clue_changes_available_endings():
    state = play("demolition_notice", "study", "conservatory")

    assert set(available_choices(state)) == {
        "release",
        "keep",
        "leave",
    }


def test_name_can_be_discovered_in_nursery():
    state = play("front_door", "nursery", "study")

    assert "release" in available_choices(state)


def test_learning_release_words_does_not_end_story():
    state = play("demolition_notice", "study")

    assert "release_words" in state.clues
    assert state.ending is None
    assert "release" not in available_choices(state)


@pytest.mark.parametrize("ending", ["release", "keep", "leave"])
def test_each_ending_finishes_on_fourth_decision(ending):
    state = play("demolition_notice", "study", "conservatory", ending)

    assert state.decisions == 4
    assert state.ending == ending
    assert available_choices(state) == {}

    with pytest.raises(ValueError):
        apply_choice(state, "study")


def test_repeated_clue_is_not_duplicated():
    state = play("demolition_notice", "study", "conservatory")

    assert state.clues.count("release_words") == 1


def test_unknown_choice_is_rejected():
    with pytest.raises(ValueError):
        apply_choice(StoryState(), "open_secret_tunnel")