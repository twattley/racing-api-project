# Comment Labeler Architecture

## Purpose

Use Gemini to label horse racing comments with performance signals. Labels are stored in `public.comment_labels` and can be joined to `results_data` via `unique_id`.

## The 7 Signals

### Form Signals (boolean)

| Signal                | Meaning                                       | Example Triggers                                                          |
| --------------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| `in_form`             | Horse is thriving, ready to win               | "will remain of interest", "best effort of the season", "one to keep"     |
| `out_of_form`         | Horse is struggling or physically compromised | "folded tamely", "bled from nose", "atrial fibrillation", "gone off boil" |
| `better_than_show`    | Ran better than result suggests (unlucky)     | "denied clear run", "hampered", "nearest at finish", "lost lengths start" |
| `flattered_by_result` | Ran worse than result suggests (lucky)        | "flattered by proximity", "had run of race", "benefited from bias"        |

### Attitude Signals (boolean)

| Signal              | Meaning                     | Example Triggers                                                   |
| ------------------- | --------------------------- | ------------------------------------------------------------------ |
| `positive_attitude` | Showed grit and willingness | "battled", "rallied", "found for pressure", "dug deep", "straight" |
| `negative_attitude` | Showed quirks or no resolve | "flashing tail", "hanging badly", "downed tools", "idled"          |

### Race Quality Signal

| Value       | Meaning                                       |
| ----------- | --------------------------------------------- |
| `strong`    | Competitive field, reliable form, 20+ runners |
| `average`   | Typical race, nothing special                 |
| `weak`      | Low-grade, modest pace, unreliable form       |
| `no_signal` | No information about race strength            |

## Data Flow

```
public.results_data → [labeler.py] → Gemini API → public.comment_labels
                                                         ↓
                                              JOIN via unique_id
```

## Usage

```bash
# Label 500 comments in batches of 50
python apps/comment_labeler/labeler.py --total 500 --batch-size 50

# Use a specific model
python apps/comment_labeler/labeler.py --model gemini-2.5-pro

# Only label comments from 2024 onwards
python apps/comment_labeler/labeler.py --min-date 2024-01-01
```

## Database Schema

```sql
-- Created automatically by labeler.py
CREATE TABLE public.comment_labels (
    unique_id VARCHAR(132) PRIMARY KEY,
    in_form BOOLEAN DEFAULT FALSE,
    out_of_form BOOLEAN DEFAULT FALSE,
    better_than_show BOOLEAN DEFAULT FALSE,
    flattered_by_result BOOLEAN DEFAULT FALSE,
    positive_attitude BOOLEAN DEFAULT FALSE,
    negative_attitude BOOLEAN DEFAULT FALSE,
    race_strength VARCHAR(16) DEFAULT 'no_signal',
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Joining to Results

```sql
SELECT
    r.horse_name,
    r.race_date,
    r.finishing_position,
    cl.in_form,
    cl.better_than_show,
    cl.race_strength,
    cl.reasoning
FROM public.results_data r
JOIN public.comment_labels cl ON r.unique_id = cl.unique_id
WHERE cl.in_form = true
ORDER BY r.race_date DESC;
```

## Key Files

| File         | Purpose                              |
| ------------ | ------------------------------------ |
| `labeler.py` | Main pipeline: fetch → label → store |
| `models.py`  | Pydantic models (if needed)          |

## Environment

Requires `GEMINI_API_KEY` in:

```
libraries/api-helpers/src/api_helpers/.env
```

## Cost Estimate

- Gemini 2.5 Flash: ~$0.001 per comment
- 10,000 comments ≈ $10
