# Contender Selections Feature

## Overview

The Contender Selections feature allows users to mark horses as either a **Contender** (C) or **Not Contender** (N) for each race. This provides a quick way to categorize horses during race analysis and track selection decisions over time.

## Purpose & Methodology

The goal is to create a **value identification system** by combining subjective race analysis with market prices.

### The Process

1. **Quick Assessment**: Mark which horses you believe have a realistic chance of winning (Contenders)

2. **Equal Contender Probability**: Each contender gets an equal share
   - Example: 5 runners, 3 marked as contenders
   - Each contender: `1/3 = 33.3%` chance

3. **Normalized Market Probability**: Take the Betfair SP of only the contenders and normalize to 100%
   - Contender A: Betfair SP 4.0 → probability `25%`
   - Contender B: Betfair SP 5.0 → probability `20%`
   - Contender C: Betfair SP 8.0 → probability `12.5%`
   - Total: `57.5%`
   - Normalized:
     - A: `25 / 57.5 = 43.5%`
     - B: `20 / 57.5 = 34.8%`
     - C: `12.5 / 57.5 = 21.7%`

4. **Blend the Two**: Average the equal contender % and normalized market %
   - Contender A: `(33.3 + 43.5) / 2 = 38.4%` → adjusted odds `2.60`
   - Contender B: `(33.3 + 34.8) / 2 = 34.1%` → adjusted odds `2.93`
   - Contender C: `(33.3 + 21.7) / 2 = 27.5%` → adjusted odds `3.64`

5. **Identify Value**: Compare adjusted odds to actual Betfair SP

### Backend Calculation (API Response)

The backend will return a **percentage difference** for each horse:

```
equal_prob = 1 / num_contenders
normalized_market_prob = (1 / betfair_sp) / sum_of_contender_probs
adjusted_prob = (equal_prob + normalized_market_prob) / 2
adjusted_odds = 1 / adjusted_prob
value_percentage = ((betfair_sp - adjusted_odds) / adjusted_odds) * 100
```

| Horse | Betfair SP | Equal % | Normalized Market % | Adjusted % | Adjusted Odds | Value % |
|-------|------------|---------|---------------------|------------|---------------|---------|
| A | 4.0 | 33.3% | 43.5% | 38.4% | 2.60 | +54% |
| B | 5.0 | 33.3% | 34.8% | 34.1% | 2.93 | +71% |
| C | 8.0 | 33.3% | 21.7% | 27.5% | 3.64 | +120% |

**Interpretation:**
- **Positive %**: Overpriced - potential back value (market odds higher than our adjusted odds)
- **Negative %**: Underpriced - avoid or consider lay
- **~0%**: Fair price

### Why This Works

- **Equal probability** represents your belief that all contenders have equal chance
- **Normalized market** brings in market wisdom about relative chances between contenders
- **Blending (÷2)** creates a compromise between your view and the market
- Horses with higher market odds relative to others get the biggest value boost

### Non-Contenders (Lay Value Calculation)

Horses marked as **Not Contender** (N) are evaluated for **lay value**:

**Logic:**
- The lay threshold = `num_contenders + 1` (decimal odds)
- If 3 contenders marked → threshold is **4.0** (3/1 in fractional)
- If non-contender price < threshold → **Value Lay** (market overrates them)
- If non-contender price ≥ threshold → **No Lay** (market correctly prices them as outsider)

**Formula:**
```
lay_threshold = num_contenders + 1
is_value_lay = betfair_sp < lay_threshold
lay_value_percentage = ((lay_threshold - betfair_sp) / betfair_sp) * 100
```

**Example:** 3 contenders marked
| Horse | Status | Betfair SP | Lay Threshold | Is Value Lay | Lay Value % |
|-------|--------|------------|---------------|--------------|-------------|
| D | not-contender | 2.5 | 4.0 | ✓ Yes | +60% |
| E | not-contender | 5.0 | 4.0 | ✗ No | - |
| F | not-contender | 3.8 | 4.0 | ✓ Yes | +5% |

**Interpretation:**
- **Value Lay (purple)**: Price < threshold → market overrates this horse, consider laying
- **No Lay (gray)**: Price ≥ threshold → market already treats them as outsider, no lay value

**Rationale:** If you believe only 3 horses can win, any horse not in that group should logically be at least 3/1 (4.0 decimal). If the market has them shorter, it's a potential lay.

## Data Model (API Response)

The horse race info endpoint returns these contender-related fields for each horse:

### Contender Fields (Back Value)
| Field | Type | Description |
|-------|------|-------------|
| `contender_status` | string | `'contender'`, `'not-contender'`, or `null` |
| `equal_prob` | decimal | Equal probability among contenders (%) |
| `normalized_market_prob` | decimal | Normalized market probability (%) |
| `adjusted_prob` | decimal | Blended probability (%) |
| `adjusted_odds` | decimal | Fair odds based on blended probability |
| `value_percentage` | decimal | Back value: `((SP - adjusted_odds) / adjusted_odds) * 100` |

### Not-Contender Fields (Lay Value)
| Field | Type | Description |
|-------|------|-------------|
| `lay_threshold` | decimal | Minimum price non-contender should be (`num_contenders + 1`) |
| `is_value_lay` | boolean | `true` if price < threshold (lay opportunity) |
| `lay_value_percentage` | decimal | Lay value: `((threshold - price) / price) * 100` |

## User Interface

In the `HorseDetails` component, two buttons are displayed for each horse:

| Button | Label | Color (Active) | Color (Inactive) | Action |
|--------|-------|----------------|------------------|--------|
| C | Contender | Green (`bg-green-600`) | Gray (`bg-gray-400`) | Mark horse as a contender |
| N | Not Contender | Red (`bg-red-600`) | Gray (`bg-gray-400`) | Mark horse as not a contender |

- Clicking an active button toggles it off (clears selection)
- Only one status can be active at a time per horse
- Selections are persisted to the database immediately

## Database Schema

```sql
-- Table: live_betting.contender_selections
CREATE TABLE live_betting.contender_selections (
    id SERIAL PRIMARY KEY,
    horse_id INTEGER NOT NULL,
    horse_name VARCHAR(255) NOT NULL,
    race_id INTEGER NOT NULL,
    race_date DATE NOT NULL,
    race_time VARCHAR(50),
    status VARCHAR(20) NOT NULL CHECK (status IN ('contender', 'not-contender')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(horse_id, race_id)
);

-- Indexes
CREATE INDEX idx_contender_selections_race_id ON live_betting.contender_selections(race_id);
CREATE INDEX idx_contender_selections_race_date ON live_betting.contender_selections(race_date);
```

## API Endpoints

### POST `/betting/contender_selections`

Store or update a contender selection.

**Request Body:**
```json
{
  "horse_id": 12345,
  "horse_name": "Example Horse",
  "race_id": 67890,
  "race_date": "2026-01-11",
  "race_time": "14:30",
  "status": "contender",
  "timestamp": "2026-01-11T14:25:00.000Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Stored contender selection for Example Horse"
}
```

### GET `/betting/contender_selections/{race_id}`

Retrieve all contender selections for a specific race.

**Response:**
```json
[
  {
    "horse_id": 12345,
    "horse_name": "Example Horse",
    "race_id": 67890,
    "race_date": "2026-01-11",
    "race_time": "14:30",
    "status": "contender",
    "created_at": "2026-01-11T14:25:00+00:00",
    "updated_at": "2026-01-11T14:25:00+00:00"
  }
]
```

### DELETE `/betting/contender_selections/{race_id}/{horse_id}`

Delete a contender selection for a specific horse in a race.

**Response:**
```json
{
  "success": true,
  "message": "Deleted selection for horse 12345 in race 67890"
}
```

### GET `/betting/contender_values/{race_id}`

Calculate and return value percentages for all contenders in a race.

**Response:**
```json
{
  "race_id": 67890,
  "contender_count": 3,
  "total_runners": 8,
  "values": [
    {
      "horse_id": 12345,
      "horse_name": "Example Horse A",
      "betfair_sp": 4.0,
      "equal_prob": 33.3,
      "normalized_market_prob": 43.5,
      "adjusted_prob": 38.4,
      "adjusted_odds": 2.6,
      "value_percentage": 54
    },
    {
      "horse_id": 12346,
      "horse_name": "Example Horse B",
      "betfair_sp": 5.0,
      "equal_prob": 33.3,
      "normalized_market_prob": 34.8,
      "adjusted_prob": 34.1,
      "adjusted_odds": 2.93,
      "value_percentage": 71
    }
  ]
}
```

**Value Calculation Formula:**
```
equal_prob = 1 / num_contenders
normalized_market_prob = (1 / betfair_sp) / sum_of_contender_probs
adjusted_prob = (equal_prob + normalized_market_prob) / 2
adjusted_odds = 1 / adjusted_prob
value_percentage = ((betfair_sp - adjusted_odds) / adjusted_odds) * 100
```

## Architecture

### Backend Files

| File | Purpose |
|------|---------|
| `models/contender_selection.py` | Pydantic models for request/response |
| `storage/query_generator/store_contender_selection.py` | SQL query generator |
| `repository/todays_repository.py` | Database operations |
| `services/todays_service.py` | Business logic |
| `controllers/betting_api.py` | API endpoint definitions |

### Frontend Files

| File | Purpose |
|------|---------|
| `api/hooks.js` | `usePostContenderSelection`, `useDeleteContenderSelection`, `useContenderSelections`, `useContenderValues` hooks |
| `components/HorseDetails.jsx` | UI buttons and click handlers |
| `components/RaceDetails.jsx` | Fetches selections and values from backend, passes to HorseDetails |

## Future Enhancements

- [x] Load existing selections when viewing a race (pre-populate button states)
- [x] Add ability to clear/delete selections

## Usage Example

1. Navigate to a race in the Today's or Feedback section
2. For each horse, click **C** if you consider them a contender
3. Click **N** if you want to explicitly mark them as not a contender
4. Selections are saved automatically
5. Click the same button again to clear the selection
