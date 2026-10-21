# Five-minute StoryDoor demo

1. Open the app and show the two stories in the sidebar. Explain that each uses the same engine but different settings, clues, decision counts, and ending requirements.
2. Start The Last Signal. Choose clock, chart, relay, manifest, then rescue. Each choice calls the configured Groq model and can incur provider usage. A fallback is an expected supported result, not a broken demo.
3. After the second decision, refresh and resume. Show the same scene and earlier-scene history. Do not switch stories unless you intend to replace this single save.
4. Finish the story, then open Evaluation. Inspect a recorded attempt's required outcome, original response, and displayed text. Explain why accepted does not mean semantically correct.
5. Save a human verdict with a specific note and export the selected group. Open the case study to show a real false alarm, a missed error, and a specification correction.

For a demo without an API key, run `python -m pytest -q` and `python evaluate_regressions.py`, then inspect the committed JSON exports. The interactive app itself still needs a key to generate new scenes.

Suggested repository description:

> Interactive fiction with AI narration, deterministic story rules, persistent saves, and human-reviewed evaluation traces.

Suggested topics: python, streamlit, generative-ai, llm-evaluation, interactive-fiction, pytest, sqlite.

Screenshot suggestions: the two-story selector, a completed ending, and an evaluation record showing original versus displayed narration. Use actual app screenshots; the repository does not currently include screenshot assets.
