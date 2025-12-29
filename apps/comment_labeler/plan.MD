# Active Learning Pipeline Plan

## Goal

Train a local Llama 3.2 model (`flat-hcap`) to label horse racing comments with 5 signals. Use a simple human-in-the-loop workflow: predict → review → retrain → repeat.

## The Loop

```
goldstandard.jsonl → [export] → Colab fine-tune → flat-hcap model
                                                        ↓
comments.csv → [predict] → predictions.jsonl → [dashboard] → goldstandard.jsonl
                                                        ↑
                                              human corrections
```

## Implementation Steps

### 1. Create `local_model.py`

Simple Ollama wrapper for the `flat-hcap` model.

- Input: formatted comment string (same format as Gemini)
- Output: JSON with 5 signals + reasoning
- No system prompt needed (baked into fine-tuned weights)
- Parse JSON response, handle errors gracefully

```python
# Pseudocode
def predict(formatted_input: str) -> dict:
    response = ollama.chat(model="flat-hcap", messages=[...])
    return parse_json(response)
```

### 2. Add `predict` CLI command

In `cli.py`:

```bash
python -m apps.comment_labeler.cli predict --count 20
```

- Uses `random_sample()` from `extract_comments.py`
- Excludes items already in `goldstandard.jsonl` (dedupe by `formatted_input`)
- Runs each through `flat-hcap` model via Ollama
- Writes results to `predictions.jsonl`

### 3. Add tabs to dashboard

In `dashboard.py`:

- Wrap current layout in `dcc.Tabs`
- **Tab 1: "Gemini Review"** - existing functionality (loads `labeled.jsonl`)
- **Tab 2: "Model Predictions"** - new tab (loads `predictions.jsonl`)
- Both tabs save approved items to `goldstandard.jsonl`
- Separate checkpoints per tab (`.checkpoint-gemini`, `.checkpoint-predictions`)

### 4. Add `export` CLI command

In `cli.py`:

```bash
python -m apps.comment_labeler.cli export
```

- Reads `goldstandard.jsonl`
- Outputs `training_data.jsonl` in Colab-ready format
- Format: prompt/completion pairs for fine-tuning

```json
{
  "prompt": "Won | [RACE]: Strong race | [HORSE]: Made all, kept on well",
  "completion": "{\"in_form\": true, \"out_of_form\": false, ...}"
}
```

### 5. Update `architecture.MD`

Document the full workflow including the iteration loop.

## Files to Create/Modify

| File              | Action | Description                              |
| ----------------- | ------ | ---------------------------------------- |
| `local_model.py`  | Create | Ollama wrapper for `flat-hcap`           |
| `cli.py`          | Modify | Add `predict` and `export` commands      |
| `dashboard.py`    | Modify | Add tabs for Gemini + Predictions review |
| `architecture.MD` | Modify | Document iteration workflow              |

## Configuration

- **Model name**: `flat-hcap`
- **System prompt**: Not needed (fine-tuned weights handle it)
- **Prediction batch size**: 20 per iteration (configurable via `--count`)
- **Deduplication**: By `formatted_input` against `goldstandard.jsonl`

## Workflow

1. **Bootstrap**: Use existing Gemini-labeled data, review in dashboard Tab 1, build initial ~200 examples in `goldstandard.jsonl`

2. **First training**: Export to Colab, fine-tune Llama 3.2, import as `flat-hcap` in Ollama

3. **Iterate**:

   - Run `predict --count 20` to get new predictions
   - Review in dashboard Tab 2
   - Correct mistakes, approve good ones
   - Export and retrain when accuracy drops or coverage gaps appear

4. **Deploy**: Once satisfied, use `flat-hcap` in production pipeline

## Notes

- Keep it simple—you're the uncertainty detector
- Random sampling naturally surfaces diverse examples
- Retrain when you notice patterns the model gets wrong
- ~200 examples is a good starting point, can grow as needed
