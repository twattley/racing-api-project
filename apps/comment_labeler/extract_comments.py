"""
Extract and search comments from CSV file.

Expected CSV columns:
- race_comment: Individual horse comment
- main_race_comment: Overall race description
- finishing_position: Horse's finishing position
- number_of_runners: Total runners
- total_distance_beaten: Distance beaten in lengths
"""

import json
from pathlib import Path

import pandas as pd

from .models import format_input


REQUIRED_COLUMNS = [
    "race_comment",
    "main_race_comment",
    "finishing_position",
    "number_of_runners",
    "total_distance_beaten",
]


def load_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load comments CSV file and validate columns."""
    df = pd.read_csv(csv_path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Handle non-numeric finishing positions (PU, F, etc) -> 999
    df["finishing_position"] = (
        pd.to_numeric(df["finishing_position"], errors="coerce").fillna(999).astype(int)
    )

    # Handle non-numeric distance beaten -> 999
    df["total_distance_beaten"] = pd.to_numeric(
        df["total_distance_beaten"], errors="coerce"
    ).fillna(999)

    return df


def _has_context(row: pd.Series) -> bool:
    """Check if row has required context (non-null values)."""
    return (
        pd.notna(row["race_comment"])
        and len(str(row["race_comment"])) > 20
        and row["finishing_position"] < 999  # Skip PU/F etc
        and pd.notna(row["number_of_runners"])
    )


def _row_to_example(row: pd.Series) -> dict:
    """Convert a DataFrame row to a formatted example dict."""
    position = int(row["finishing_position"])
    runners = int(row["number_of_runners"])
    distance = (
        float(row["total_distance_beaten"])
        if row["total_distance_beaten"] < 999
        else None
    )
    main_comment = (
        row["main_race_comment"] if pd.notna(row["main_race_comment"]) else ""
    )
    race_comment = row["race_comment"]

    formatted = format_input(
        position=position,
        runners=runners,
        distance_beaten=distance,
        main_race_comment=main_comment,
        performance_comment=race_comment,
    )

    return {"formatted_input": formatted}


def search_comments(
    csv_path: str | Path,
    pattern: str,
    output_path: str | Path,
    count: int = 5,
) -> list[dict]:
    """
    Search CSV for comments matching a pattern and add to examples CSV.

    Args:
        csv_path: Path to the source CSV file
        pattern: Text pattern to search for (case-insensitive)
        output_path: Path to the output CSV file (appends)
        count: Number of matching examples to add

    Returns:
        List of examples that were added
    """
    df = load_csv(csv_path)

    # Filter to rows with context
    df = df[df.apply(_has_context, axis=1)]

    # Search for pattern (case-insensitive)
    mask = df["race_comment"].str.lower().str.contains(pattern.lower(), na=False)
    matches = df[mask]

    if len(matches) == 0:
        print(f"No matches found for: '{pattern}'")
        return []

    print(f"\nFound {len(matches)} matches for '{pattern}'")
    print(f"Showing up to {count} examples:\n")

    # Sample up to count examples
    if len(matches) > count:
        matches = matches.sample(n=count)

    # Load existing to avoid duplicates
    output_path = Path(output_path)
    existing = set()
    if output_path.exists():
        existing_df = pd.read_csv(output_path)
        existing = set(existing_df["formatted_input"].tolist())

    # Show examples and add new ones
    added = []
    for i, (_, row) in enumerate(matches.iterrows(), 1):
        example = _row_to_example(row)
        print(f"  {i}. {example['formatted_input'][:100]}...")

        if example["formatted_input"] not in existing:
            added.append(example)
            existing.add(example["formatted_input"])

    # Append to CSV
    if added:
        new_df = pd.DataFrame(added)
        if output_path.exists():
            new_df.to_csv(output_path, mode="a", header=False, index=False)
        else:
            new_df.to_csv(output_path, index=False)

    print(f"\nAdded {len(added)} new examples to {output_path}")

    for i, example in enumerate(added, 1):
        print(f"  {i}. {example['formatted_input'][:80]}...")

    return added


def load_examples(path: str | Path) -> list[dict]:
    """Load examples from JSONL file."""
    examples = []
    path = Path(path)
    if path.exists():
        with open(path) as f:
            for line in f:
                examples.append(json.loads(line))
    return examples


def random_sample(
    csv_path: str | Path,
    count: int = 100,
    seed: int = 42,
) -> list[dict]:
    """Get random sample of examples from CSV with full context."""
    df = load_csv(csv_path)

    # Filter to rows with context
    df = df[df.apply(_has_context, axis=1)]

    # Sample
    if len(df) > count:
        df = df.sample(n=count, random_state=seed)

    return [_row_to_example(row) for _, row in df.iterrows()]
