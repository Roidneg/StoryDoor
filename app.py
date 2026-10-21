import streamlit as st

from narrator import NarrationError, narrate_transition
from story_config import MAX_DECISIONS, OPENING_TEXT, STORY_TITLE
from story_engine import StoryState, available_choices
from story_catalog import STORIES, get_story
from save_store import SaveError, load_game, save_game


st.set_page_config(
    page_title="StoryDoor",
    page_icon="🗝️",
    layout="centered",
)

selected_story = st.sidebar.selectbox("Choose a story", list(STORIES), format_func=lambda key: STORIES[key]["title"])
st.sidebar.caption("Select a story, then use Start selected story to begin it.")

def start_new(revision=0):
    story = get_story(selected_story)
    state = StoryState(story_id=selected_story)
    scenes = [{"title": story["title"], "text": story["opening"]}]
    try:
        revision = save_game(state, scenes, revision)
    except SaveError as exc:
        st.error(str(exc))
        return
    st.session_state.story_state = state
    st.session_state.scenes = scenes
    st.session_state.save_revision = revision
    st.rerun()


if "story_state" not in st.session_state:
    try:
        saved = load_game()
    except SaveError as exc:
        st.error(str(exc))
        st.info("Keep storydoor.db for recovery. Close the app and move it aside to start with a fresh save.")
        st.stop()
    if saved is not None:
        saved_state, saved_scenes, revision = saved
        st.title(get_story(saved_state.story_id)["title"])
        st.write(f"Saved journey: {saved_state.decisions} of {get_story(saved_state.story_id)['max_decisions']} decisions.")
        if st.button("Resume saved journey", type="primary"):
            st.session_state.story_state = saved_state
            st.session_state.scenes = saved_scenes
            st.session_state.save_revision = revision
            st.rerun()
        replace_save = st.checkbox("Replace my saved journey with a new one")
        if st.button("Start new journey", disabled=not replace_save):
            start_new(revision)
        st.stop()
    start_new()
    st.stop()


# Available throughout a journey, not only after the ending.
with st.sidebar:
    active = st.session_state.story_state
    st.caption(f"Current journey: {get_story(active.story_id)['title']}")
    st.write(f"Start: **{get_story(selected_story)['title']}**")
    st.caption("Starting replaces your current journey in the single save slot. Evaluation history is retained.")
    confirmed = st.checkbox(
        "Replace my current saved journey",
        key=f"replace_active_{selected_story}_{st.session_state.save_revision}",
    )
    if st.button("Start selected story", disabled=not confirmed, key="start_selected_story"):
        start_new(st.session_state.save_revision)


def take_action(choice_id: str) -> None:
    """Advance only after the narrator returns a validated scene."""
    current_state = st.session_state.story_state
    previous_scene = st.session_state.scenes[-1]["text"]

    try:
        with st.spinner("Your story continues…"):
            next_state, scene = narrate_transition(
                current_state,
                choice_id,
                previous_scene,
            )
    except NarrationError as exc:
        st.error(str(exc))
        st.info("Your current scene is unchanged. You can try again.")
        return

    next_scenes = st.session_state.scenes + [scene.model_dump()]
    try:
        revision = save_game(next_state, next_scenes, st.session_state.save_revision)
    except SaveError as exc:
        st.error(str(exc))
        st.info("Progress was not advanced. Your previous save is unchanged.")
        return
    st.session_state.save_revision = revision
    st.session_state.scenes = next_scenes
    st.session_state.story_state = next_state
    st.rerun()


story = get_story(st.session_state.story_state.story_id)
STORY_TITLE = story["title"]
MAX_DECISIONS = story["max_decisions"]
st.caption("STORYDOOR · EVERY CHOICE OPENS A NEW STORY")
st.title(STORY_TITLE)
st.write(story["tagline"])
st.caption("An interactive mystery with AI-generated narration.")

state = st.session_state.story_state
current_scene = st.session_state.scenes[-1]

st.progress(
    state.decisions / MAX_DECISIONS,
    text=f"{state.decisions} of {MAX_DECISIONS} decisions made",
)

st.divider()
st.subheader(current_scene["title"])

# Render model text as plain text, without interpreting HTML or Markdown.
for paragraph in current_scene["text"].split("\n\n"):
    st.text(paragraph)

st.divider()

if state.ending is None:
    st.subheader("What do you do?")

    # A form submits one selected action at a time.
    with st.form(f"decision_{state.decisions}"):
        choices = available_choices(state)

        selected = st.radio(
            "Choose your next action",
            options=list(choices),
            format_func=lambda choice_id: choices[choice_id],
        )

        submitted = st.form_submit_button(
            "Follow this path",
            type="primary",
        )

    if submitted:
        take_action(selected)

else:
    ending_labels = story["ending_labels"]

    st.success(ending_labels[state.ending])

    transcript = "\n\n".join(
        f"{scene['title']}\n\n{scene['text']}"
        for scene in st.session_state.scenes
    )

    st.download_button(
        "Download your story",
        data=f"{STORY_TITLE}\n\n{transcript}",
        file_name=f"{state.story_id}.txt",
        mime="text/plain",
    )

    replace_save = st.checkbox("Replace this completed journey with a new one")
    if st.button("Begin another journey", disabled=not replace_save):
        start_new(st.session_state.save_revision)

if len(st.session_state.scenes) > 1:
    with st.expander("Read earlier scenes"):
        for scene in st.session_state.scenes[:-1]:
            st.subheader(scene["title"])
            st.text(scene["text"])

st.caption(
    "Saved automatically after each decision on this computer. "
    "Refresh or reopen the app to resume. One shared local save slot."
)