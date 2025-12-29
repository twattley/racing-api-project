# Comment Labeler Architecture

## Purpose

Build gold-standard training data for fine-tuning a small language model to analyze horse racing comments. The goal is to extract actionable signals from race commentaries that indicate whether a horse is likely to perform well in future races.

## The 5 Signals

The system extracts these signals from race comments:

### Individual Performance Signals (boolean)

| Signal             | Meaning                                     | Example Triggers                                                |
| ------------------ | ------------------------------------------- | --------------------------------------------------------------- |
| `in_form`          | Horse is thriving, likely to run well again | "will remain of interest", "clearly thriving", "rallied gamely" |
| `out_of_form`      | Horse is regressing, unlikely to replicate  | "hard to fancy", "found nothing when asked", "hung badly"       |
| `better_than_show` | Performance masked by bad luck              | "denied clear run", "hampered", "ran on when too late"          |
| `worse_than_show`  | Performance flattered by circumstances      | "flattered by proximity", "got soft lead", "race fell apart"    |

### Race Quality Signal

| Value       | Meaning                                       |
| ----------- | --------------------------------------------- |
| `strong`    | Competitive field, strong pace, reliable form |
| `average`   | Typical race, nothing special                 |
| `weak`      | Slowly run, modest affair, unreliable form    |
| `no_signal` | No information about race strength            |

## Data Pipeline

```
comments.csv          →  examples.csv  →  labeled.jsonl  →  goldstandard.jsonl
(~130k raw comments)     (curated set)    (Gemini labels)   (human verified)
```

### Stage 1: Source Data

- **File**: `comments.csv`
- **Contents**: ~130k horse racing comments with context
- **Key columns**: `race_comment`, `main_race_comment`, `finishing_position`, `number_of_runners`, `total_distance_beaten`

### Stage 2: Example Curation (`examples.csv`)

Two methods to build the training set:

1. **Search** - Find specific phrases:

   ```bash
   python -m apps.comment_labeler.cli search "denied a clear run"
   python -m apps.comment_labeler.cli search "reluctant to go to the start"
   ```

2. **Diverse sampling** - Let Gemini pick interesting examples from random samples:
   ```bash
   python -m apps.comment_labeler.cli diverse --count 10 --iterations 5
   ```

### Stage 3: Gemini Labeling (`labeled.jsonl`)

```bash
python -m apps.comment_labeler.cli label
```

- Uses **Gemini 3 Pro** (`gemini-3-pro-preview`)
- Structured JSON output with all 5 signals + reasoning
- Cost: ~$5-15 for 1000 examples

### Stage 4: Human Review (`goldstandard.jsonl`)

```bash
.venv/bin/python apps/comment_labeler/dashboard.py
```

- Dash web app at `http://127.0.0.1:8050`
- Review Gemini's labels, correct errors, edit reasoning
- Checkpoint saves position between sessions

## Key Files

| File                  | Purpose                                           |
| --------------------- | ------------------------------------------------- |
| `models.py`           | Data models, `format_input()` function            |
| `extract_comments.py` | CSV loading, search, random sampling              |
| `diverse_sampler.py`  | Gemini-powered diverse example selection          |
| `gemini_labeler.py`   | Label comments with Gemini 3 Pro                  |
| `local_model.py`      | Ollama wrapper for local fine-tuned model         |
| `dashboard.py`        | Dash review UI (tabbed: Gemini + Predictions)     |
| `cli.py`              | Command-line interface                            |
| `reviewer.py`         | Terminal-based review (deprecated, use dashboard) |

## Input Format

The `format_input()` function creates a standardized string for the model:

```
Won | [RACE]: Strong race, good pace throughout | [HORSE]: Made all, kept on gamely
```

```
3rd of 12, involved in finish | [RACE]: Modest affair | [HORSE]: Denied clear run inside final furlong
```

Components:

- **Position context**: "Won", "3rd of 12, involved in finish", "10th of 16, well beaten"
- **Race comment** (optional): `[RACE]: ...` - overall race description
- **Horse comment**: `[HORSE]: ...` - individual performance notes

## Gemini Prompt Design

The `SYSTEM_PROMPT` in `gemini_labeler.py` is carefully crafted to teach the model racing domain knowledge:

1. **Signal definitions** with examples
2. **Pace interaction** - how pace affects form reliability
3. **Attitude signals** - "rallied gamely" vs "found nothing"
4. **Handicap mark context** - "well handicapped" alone isn't enough

Key instruction: _"Most comments will have all FALSE flags - only set TRUE when there's clear evidence"_

## Dashboard Features

- **Tabbed interface**: Gemini Review + Model Predictions tabs
- **Slider navigation** with prev/next buttons
- **Checkboxes** for boolean signals
- **Dropdown** for race strength
- **Reasoning textarea** for editing explanations
- **Live progress** showing reviewed count
- **Separate checkpoints** per tab (`.checkpoint-gemini`, `.checkpoint-predictions`)

## Commands Reference

```bash
# Search for patterns
python -m apps.comment_labeler.cli search "PATTERN" --count 5

# Diverse sampling
python -m apps.comment_labeler.cli diverse --count 10 --iterations 5

# Label with Gemini
python -m apps.comment_labeler.cli label

# Check stats
python -m apps.comment_labeler.cli stats

# Run local model predictions (for active learning)
python -m apps.comment_labeler.cli predict --count 20

# Export goldstandard for fine-tuning
python -m apps.comment_labeler.cli export

# Launch review dashboard
.venv/bin/python apps/comment_labeler/dashboard.py
```

## Environment Setup

Requires `GEMINI_API_KEY` environment variable. Currently loaded from:

```
libraries/api-helpers/src/api_helpers/.env
```

## Active Learning Loop

Once you have an initial fine-tuned model (`flat-hcap` in Ollama), use this iteration loop:

```
goldstandard.jsonl → [export] → Colab fine-tune → flat-hcap model
                                                        ↓
comments.csv → [predict] → predictions.jsonl → [dashboard] → goldstandard.jsonl
                                                        ↑
                                              human corrections
```

### Workflow

1. **Bootstrap**: Review Gemini-labeled examples in dashboard Tab 1, build initial ~200 examples in `goldstandard.jsonl`

2. **First training**: Export to Colab (`cli export`), fine-tune Gemma 3 27B, import as `flat-hcap` in Ollama

3. **Iterate**:
   - Run `predict --count 20` to get new predictions from local model
   - Review in dashboard Tab 2 (Model Predictions)
   - Correct mistakes, approve good ones → adds to goldstandard
   - Export and retrain when accuracy drops or coverage gaps appear

4. **Deploy**: Once satisfied, use `flat-hcap` in production pipeline

## Next Steps

1. Complete human review of Gemini-labeled examples
2. Export `goldstandard.jsonl` as training data
3. Fine-tune Gemma 3 27B model on the labeled data in Colab
4. Import as `flat-hcap` in Ollama
5. Iterate: predict → review → retrain
