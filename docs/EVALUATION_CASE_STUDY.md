# StoryDoor: evaluating a narrator that can get the story wrong

StoryDoor combines a deterministic story engine with model-generated scene text. The engineering question was whether a playable story could preserve clue rules and ending eligibility while still producing varied narration—and make its failures inspectable.

The first story, The Forgotten House, exposed invented objects, relocated clues, and a reversed rescue memory. A second story, The Last Signal, tested the same engine in a radio station with equipment, timing, and coordinate clues. Those failures shaped the evaluation feature rather than being removed from the record.

## What the system controls

Python decides which choices are available, records discovered clues, and determines the ending. The model receives an authoritative outcome and supplies a title and prose. Structured-output validation checks response shape; targeted text checks detect selected patterns. Rejected narration is replaced with the engine's exact outcome.

An audit record retains the original response even when the reader sees a fallback. It records model, prompt version, story-inclusive prompt hash, context, issues, latency, and displayed scene. Human review remains separate from automated acceptance. Loading an existing journey restores saved text without generating it again.

## Evidence

The following exports are preserved unchanged:

- [Version 2.0 baseline](../data/baselines/last-signal-v2.0.json): ten attempts from two five-decision paths.
- [Version 2.1 candidate](../data/candidates/last-signal-v2.1.json): five attempts from one rescue path.

Both exports use `openai/gpt-oss-120b`. The table reports stored labels, not retrospective judgments made while writing this document.

| Measure | Baseline 2.0 | Candidate 2.1 |
| --- | ---: | ---: |
| Returned responses | 10 | 5 |
| Automated accepted | 8 | 5 |
| Fallback responses | 2 | 0 |
| Observed fallback rate | 20% | 0% |
| API errors | 0 | 0 |
| Stored human passes | 0 | 0 |
| Stored human failures | 1 | 0 |
| Stored human reviews pending | 9 | 5 |

**These are descriptive observations, not a controlled A/B result or a correctness rate.** The baseline includes a Silence path and a rescue path. Its rescue path visits chart before relay; the candidate visits relay before chart. The sample is small, human labeling is incomplete, and both the checks and the prompt/specification changed.

## Three findings and their fixes

### A checker can reject correct typography

Both baseline chart outputs contained `Grid C‑7` using a nonbreaking hyphen. The exact text check expected `Grid C-7` and replaced both scenes. This was a detector defect, not evidence that the coordinate was semantically wrong.

Version 2.1 normalizes equivalent typography and whitespace while preserving clue words, case, and digits. Boundary checks prevent `Grid C-70` from satisfying `Grid C-7`. Regression tests replay the original chart responses and confirm that this specific false alarm is removed. Other narrative defects in those responses are still possible.

### Passing checks can miss an impossible clock

One accepted baseline opening reported `23:60`. Version 2.1 rejects numeric clock notation with an hour above 23 or a minute above 59. The candidate opening correctly uses 23:40 and a future timestamp of 00:00.

The check verifies numeric range only. It does not calculate chronology. The baseline Silence ending's after-midnight departure remains an example requiring semantic review.

### A model failure can reveal an unclear specification

The baseline rescue scene placed both technicians safely aboard Kestrel, the disabled boat. Jorge marked that response as a human-review failure. The original required outcome said only “both technicians safely aboard,” leaving the vessel implicit.

Version 2.1 explicitly requires transfer from Kestrel onto a separate rescue boat, leaves Kestrel disabled, and requires dispatch confirmation before shutdown and midnight. In the candidate response, dispatch confirms the transfer at 23:55 and the operator shuts down at 23:58. This addresses the observed transfer error in that response; it is not proof that future narration will always follow the specification.

## Remaining defects are part of the result

The candidate manifest invents technician names, job roles, and a specific return time. Its ending adds wet ink and does not explicitly state that Kestrel remains disabled. The saved human reviews are still pending; this document's observations do not silently overwrite those labels.

The offline fixtures deliberately retain a reversed rescue meaning that the current detector misses. A zero detector-regression count means expected detector behavior held, not that every scene is valid. There is no general semantic validator or automated LLM judge in this release.

## Testing and collaboration

The packaged suite contains 61 tests covering both stories' available paths, ending requirements, immutable state transitions, persistence and old-save compatibility, stale-tab protection, narration validation, evaluation storage, and Streamlit UI behavior. UI/model tests use mocked responses and make no paid API calls. The maintainer also ran local tests and live playthroughs, checked save/resume and review persistence, and reported that switching stories required finishing the current journey. That report led to an explicit sidebar control for replacing the current save mid-story.

Jorge set the product direction, exercised the application, supplied failure examples, and made the recorded review judgment. ChatGPT/Codex assisted with code, tests, analysis, and documentation. The portfolio evidence is the combination of a working application, inspectable failures, bounded checks, and decisions backed by those failures.

## Next measurement

A follow-up evaluation should hold model, story, choice order, and generation settings fixed, use multiple samples per path, and complete a common human-review rubric. Compare detector performance separately from narration quality. The current exports support that next step without claiming it has already happened.
