# Conflicts format

The conflict-detection step (an LLM reading the transcript and the slides) returns JSON in the format below. The results page shows these conflicts under the minutes. No pipeline step produces them yet.

## Where conflicts are stored

**In the database** (the normal case, written by the pipeline):

| Format field | Table and column |
|---|---|
| (the check ran at all) | one `conflict_checks` row for the meeting, even when no conflicts were found |
| each conflict | a `conflicts` row; `sort_order` = its position in the list |
| `kind`, `severity`, `status`, `title`, `description`, `resolution` | same-named `conflicts` columns |
| each of `positions` | a `conflict_positions` row; `sort_order` = its position |
| `speaker`, `statement` | same-named `conflict_positions` columns |
| `segment_ids` | `conflict_positions.source_seqs`: the transcript **`seq`** numbers (1, 2, …) the model was shown, as in the minutes prompt |
| `slide_numbers` | `conflict_positions.slide_ids`: the matching `slides.id` values (slide numbers repeat across decks) |

Clear the old conflict rows before writing new ones; the pipeline's `_clear_previous_results()` already deletes `conflict_checks` and `conflicts` (positions go with their conflict).

**As a file**, for testing without the pipeline: `storage/meetings/<meeting_id>/conflicts.json`, next to the other JSON result files. There, `segment_ids` are the `id` values in that folder's `transcript.json`.

- `conflicts.schema.json` is the JSON Schema. You can pass it to the LLM as its structured-output format (for example Ollama's `format` parameter), so the model can only return valid JSON in this shape.
- `conflicts.example.json` is a filled-in example for the Sprint 14 test meeting in `tests/fixtures/sprint14/`.

## Shape

```json
{
  "conflicts": [
    {
      "kind": "speaker_disagreement | speech_vs_slide",
      "severity": "low | medium | high",
      "status": "resolved | unresolved",
      "title": "One line naming both sides",
      "description": "One or two sentences",
      "positions": [
        { "speaker": "Marcus", "statement": "…", "segment_ids": [3, 4], "slide_numbers": [] },
        { "speaker": null,     "statement": "…", "segment_ids": [],     "slide_numbers": [2] }
      ],
      "resolution": "How it was settled, or null"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `kind` | `speaker_disagreement`: people disagree with each other. `speech_vs_slide`: something said contradicts a slide. |
| `severity` | `high` affects dates, money, scope or a decision; `low` is a minor detail. |
| `status` | `resolved` only if the meeting clearly settled it. |
| `positions` | At least two sides. Each has who said it, what they said, and where it shows up. |
| `speaker` | The person's name as used in the meeting. `null` for a slide's side, or when the speaker isn't known. |
| `segment_ids` | `id` values of segments in `transcript.json` that show this side. |
| `slide_numbers` | `slide_number` values from `slides_text.json` that show this side. |
| `resolution` | What was agreed, or `null` when it's still open. |

## Rules

- **No conflicts is `{"conflicts": []}`.** That tells the page the meeting was checked and nothing conflicted. If the file is missing, the page says conflict detection hasn't run.
- **Use real ids.** Segment ids and slide numbers must come from the transcript and slides given to the model. The backend drops references that don't exist, so a made-up id becomes a missing source rather than a wrong one.
- **Names match the minutes.** Use the same spelling as `meeting_overview.participants` in `meeting_minutes.json`, so a person appears once on the page.
- **Leniency.** Since this is LLM output, the backend (`app/services/pipeline_adapter.py`) accepts any casing for `kind`/`severity`/`status`, treats an unknown severity as `medium` and an unknown status as `unresolved`, and skips (with a warning in the log) any conflict with an unknown `kind`, no `title` or fewer than two usable positions.
- **Transcript numbering.** In the database, transcript references are the `seq` numbers (starting at 1) that the pipeline puts in front of each transcript line in its prompts. In the JSON files, they're the `id` values in `transcript.json`, which start at 0.
