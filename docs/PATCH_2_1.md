# StoryDoor 2.1: findings from a live evaluation

The preserved `data/baselines/last-signal-v2.0.json` contains ten real attempts across two paths: eight accepted, two fallbacks, one human-reviewed failure, and nine pending reviews. Original statuses, prompts, notes, and outputs remain unchanged.

## Changes

- Normalize curly quotes, Unicode hyphens/dashes, and whitespace for required-clue matching. Preserve case, words, and digits. Word boundaries reject coordinate prefixes such as `Grid C-70` when `Grid C-7` is required.
- Reject numeric clock notation with hours above 23 or minutes above 59. `00:00` remains valid for the future recording. This range check does not establish elapsed time, temporal ordering, or whether a departure occurs before midnight.
- Clarify the rescue specification: both technicians transfer from disabled Kestrel to a separate rescue boat; Kestrel remains disabled; dispatch confirms transfer before shutdown and midnight.
- Bump prompt and check versions to `storydoor-2.1` and `targeted-2.1`. New audit records carry these versions. Existing logs and saved scenes are not rewritten.

## Evidence and limitations

The regression tests replay the actual chart outputs and invalid-clock opening from the export. The two chart outputs no longer trigger the quoted-clue check; the opening containing `23:60` now triggers the clock check. This is an offline detector comparison on old text, not a new model run or evidence of improved generation quality. Those chart scenes may still have other continuity defects.

The rescue specification was ambiguous: it originally said only “both technicians safely aboard.” The revised text names the rescue boat. This is a prompt/specification fix, not an automatic semantic validator. The earlier Silence ending's after-midnight departure remains a human-review finding. The regression suite deliberately retains a semantic blind spot rather than claiming complete correctness.

## Install and check

Stop Streamlit and copy the contents of the packaged StoryDoor directory over the project. Keep `.env`, `.venv`, `storydoor.db`, and `evaluations.db`.

```powershell
python -m pytest -q
python evaluate_regressions.py
python -m streamlit run app.py --server.port 8502
```

Start a new Last Signal journey to generate candidate records. Use the same rescue route: clock, chart, relay, manifest, rescue. Review original responses and export the new group. Keep model and path fixed; a single new run is illustrative, not a statistically reliable comparison. Changing the prompt does not alter an already saved ending.
