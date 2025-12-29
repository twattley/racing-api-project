"""One-time script to reformat examples.csv with new separator format."""

import csv
from pathlib import Path

examples_path = Path(__file__).parent / "examples.csv"
labeled_path = Path(__file__).parent / "labeled.jsonl"


def reformat(old: str) -> str:
    """
    Transform old format to new format.

    Old: 'Position. Race: xxx.. horse_comment'
    New: 'Position | [RACE]: xxx | [HORSE]: horse_comment'
    """
    # Split on '. Race: ' to get position and rest
    if ". Race: " in old:
        pos_part, rest = old.split(". Race: ", 1)
        # Split rest on '.. ' to get race comment and horse comment
        if ".. " in rest:
            race_comment, horse_comment = rest.split(".. ", 1)
        else:
            race_comment = rest
            horse_comment = ""

        parts = [pos_part]
        if race_comment:
            parts.append(f"[RACE]: {race_comment}")
        if horse_comment:
            parts.append(f"[HORSE]: {horse_comment}")
        return " | ".join(parts)
    else:
        # No race comment - just position and horse comment
        # Format: 'Position. horse_comment'
        if ". " in old:
            pos_part, horse_comment = old.split(". ", 1)
            return f"{pos_part} | [HORSE]: {horse_comment}"
        return old


def main():
    # Read existing
    with open(examples_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} examples")

    # Reformat all
    new_rows = []
    for row in rows:
        new_formatted = reformat(row["formatted_input"])
        new_rows.append({"formatted_input": new_formatted})

    # Write back
    with open(examples_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["formatted_input"])
        writer.writeheader()
        writer.writerows(new_rows)

    print(f"Reformatted {len(new_rows)} examples")
    print(f"\nSample:\n{new_rows[0]['formatted_input'][:200]}...")

    # Clear labeled.jsonl since format changed
    if labeled_path.exists():
        labeled_path.unlink()
        print(f"\nCleared {labeled_path} (needs re-labeling with new format)")


if __name__ == "__main__":
    main()
