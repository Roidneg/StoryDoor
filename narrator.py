import json
import os
import logging
import re
import sqlite3
import time
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from groq import APIError, Groq
from pydantic import BaseModel, ConfigDict, field_validator

from story_config import OPENING_TEXT
from story_catalog import get_story
from evaluation import record_attempt
from story_engine import StoryState, apply_choice, available_choices


class NarrationError(RuntimeError):
    """A scene could not be generated safely for display."""


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: str
    text: str

    @field_validator("title", "text")
    @classmethod
    def validate_text(cls, value: str, info):
        value = value.strip()
        limit = 100 if info.field_name == "title" else 6000

        if not value or len(value) > limit:
            raise ValueError(f"{info.field_name} is empty or too long.")

        return value



logger = logging.getLogger(__name__)


def normalize_clue_text(value: str) -> str:
    """Normalize presentation only; preserve words, case, and coordinate digits."""
    translations = str.maketrans({
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "‐": "-", "‑": "-", "–": "-", "—": "-", "−": "-",
    })
    return " ".join(value.translate(translations).split())


def narration_issues(scene: Scene, outcome: str, story_id="the_forgotten_house") -> list[str]:
    """Conservative text checks, not a semantic continuity guarantee."""
    text = " ".join((scene.title + " " + scene.text).casefold().split())
    issues = []
    if re.search(
        r"\b(?:required[_ ]outcome|established[_ ]facts|scene[_ ]constraints|"
        r"system prompt|json object|as instructed|as the instructions)\b", text
    ):
        issues.append("instruction leakage")

    # Match required clue text while allowing equivalent typography.
    normalized = normalize_clue_text(scene.text)
    for clue in re.findall(r"(?<!\w)'([^'\n]+)'(?!\w)", outcome):
        pattern = r"(?<!\w)" + re.escape(normalize_clue_text(clue)) + r"(?!\w)"
        if not re.search(pattern, normalized):
            issues.append("missing or altered quoted clue")
            break

    # Validate numeric HH:MM clock notation, not narrative time or chronology.
    for hour, minute in re.findall(r"(?<![\w:])(\d{1,2}):(\d{2})(?![\w:])", text):
        if int(hour) > 23 or int(minute) > 59:
            issues.append("invalid clock time")
            break

    # These catch specific observed failures; paraphrases can still escape.
    patterns = {
        "unestablished lighting": r"\b(?:candle\w*|green glow)\b",
        "wet ink": r"\bink\b[^.!?]{0,35}\b(?:wet|fresh)\b",
        "notice moved above door": r"\bnotice\b[^.!?]{0,65}\babove the door\b",
        "key temperature change": r"\bkey\b[^.!?]{0,35}\b(?:cold|cools|colder|warms|warmer)\b",
    }
    if story_id != "the_forgotten_house":
        patterns = {}
    for reason, pattern in patterns.items():
        if re.search(pattern, text):
            issues.append(reason)
    return issues


def fallback_scene(outcome: str, reason: str) -> Scene:
    """Display the engine's exact outcome; never another model attempt."""
    logger.warning("Using engine narration fallback: %s", reason)
    return Scene(title="The Story Continues — Backup Narration", text=outcome)

def narrate_transition(
    before: StoryState,
    choice_id: str,
    previous_scene: str,
) -> tuple[StoryState, Scene]:
    """Return validated narration or the authoritative engine fallback.

    previous_scene is retained for app compatibility, not used as truth.
    API/configuration failures still raise without advancing caller state.
    """
    after, outcome = apply_choice(before, choice_id)

    # Reconstruct established facts from the authoritative engine.
    story = get_story(before.story_id)
    replay = StoryState(story_id=before.story_id)
    established_facts = []

    for past_choice in before.history:
        replay, fact = apply_choice(replay, past_choice)
        established_facts.append(fact)

    if replay != before:
        raise ValueError("Story state does not match its choice history.")

    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise NarrationError("GROQ_API_KEY is missing from .env.")

    instructions = """
You narrate an interactive mystery in second person, present tense.
Return a short title and approximately 120–180 words of scene text.

Use established_facts and required_outcome as the authoritative record.
The story bible and scene_constraints constrain your writing; they
are not permission to reveal facts the reader has not discovered.

Describe the selected action and every consequence in required_outcome.
Preserve quoted clues exactly.
Do not add clues, objects, characters, supernatural effects, or
reader decisions beyond the supplied record.

You may add restrained sensory descriptions of established surroundings:
their texture, ordinary sounds, temperature, and smell.
Do not turn those descriptions into new events or magical rules.
Use concrete prose. Avoid repeatedly making the house breathe or sigh.

Do not generate choices; the application supplies them.
If ending is null, do not resolve the story or perform a final action.
If ending is supplied, conclude with every required consequence.
Never mention prompts, instructions, constraints, or required outcomes.
Use the story-specific constraints for timing, objects, and causal order.

Return only the requested JSON object.
"""

    context = {
        "opening": story["opening"],
        "established_facts": established_facts,
        "selected_action": available_choices(before)[choice_id],
        "required_outcome": outcome,
        "decision_number": after.decisions,
        "ending": after.ending,
        "scene_constraints": story["constraints"],
    }
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    system_prompt = instructions + "\n\n" + story["bible"]
    started = time.perf_counter()

    def finish(scene, issues, raw, status="accepted", finish_reason=None):
        fallback = status == "fallback"
        try:
            record_attempt({
                "story_id": before.story_id, "action": choice_id,
                "history": list(before.history), "decision": after.decisions,
                "model": model, "prompt_sha256": hashlib.sha256((system_prompt + json.dumps(story, sort_keys=True)).encode()).hexdigest(),
                "system_prompt": system_prompt, "context": context,
                "raw_response": raw, "displayed_scene": scene.model_dump() if scene else None,
                "issues": issues, "status": status, "fallback": fallback,
                "finish_reason": finish_reason, "latency_seconds": round(time.perf_counter()-started,3),
            })
        except (sqlite3.Error, OSError) as exc:
            raise NarrationError("Evaluation log could not be saved. Progress was not advanced.") from exc
        return after, scene


    try:
        with Groq(
            api_key=api_key,
            timeout=45.0,
            max_retries=0,
        ) as client:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(context),
                    },
                ],
                reasoning_effort="low",
                max_completion_tokens=1600,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "story_scene",
                        "strict": True,
                        "schema": Scene.model_json_schema(),
                    },
                },
            )
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        detail = f"HTTP {status}" if status else type(exc).__name__
        finish(None, [detail], None, "api_error")
        raise NarrationError(
            f"Groq request failed ({detail}). Progress was not advanced."
        ) from None

    if not response.choices:
        return finish(fallback_scene(outcome, "empty response"), ["empty response"], None, "fallback")

    result = response.choices[0]

    if result.finish_reason != "stop":
        return finish(fallback_scene(outcome, "incomplete response"), ["incomplete response"], result.message.content, "fallback", result.finish_reason)

    try:
        scene = Scene.model_validate_json(result.message.content or "")
    except ValueError:
        return finish(fallback_scene(outcome, "invalid scene JSON"), ["invalid scene JSON"], result.message.content, "fallback", result.finish_reason)

    issues = narration_issues(scene, outcome, before.story_id)
    if issues:
        return finish(fallback_scene(outcome, "; ".join(issues)), issues, result.message.content, "fallback", result.finish_reason)

    return finish(scene, [], result.message.content, finish_reason=result.finish_reason)


if __name__ == "__main__":
    state = StoryState()

    try:
        state, scene = narrate_transition(
            state,
            "demolition_notice",
            OPENING_TEXT,
        )
    except NarrationError as exc:
        raise SystemExit(str(exc))

    print(f"\n{scene.title}\n")
    print(scene.text)
    print(f"\nDecisions completed: {state.decisions}")
    print("Available choices:")

    for choice_id, label in available_choices(state).items():
        print(f"- {choice_id}: {label}")