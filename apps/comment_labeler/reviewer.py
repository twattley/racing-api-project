"""
Human review interface for Gemini-labeled comments.

Interactive terminal UI for reviewing and correcting labels.
"""

import json
import os
import textwrap
from pathlib import Path

from .models import LabeledComment


def clear_screen():
    """Clear the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")


def wrap_text(text: str, width: int = 80, prefix: str = "") -> str:
    """Wrap text to specified width with optional prefix."""
    lines = textwrap.wrap(text, width=width - len(prefix))
    return "\n".join(prefix + line for line in lines)


def display_item(item: LabeledComment, index: int, total: int):
    """Display a single item for review."""
    clear_screen()

    print("=" * 80)
    print(f"  REVIEW [{index}/{total}]")
    print("=" * 80)

    # Parse formatted_input to show sections clearly
    parts = item.formatted_input.split(" | ")

    print("\n📊 RESULT:")
    print(f"   {parts[0]}")

    if len(parts) > 1:
        for part in parts[1:]:
            if part.startswith("[RACE]:"):
                print("\n📋 RACE COMMENT:")
                print(wrap_text(part[7:].strip(), 76, "   "))
            elif part.startswith("[HORSE]:"):
                print("\n🐴 HORSE COMMENT:")
                print(wrap_text(part[8:].strip(), 76, "   "))

    print("\n" + "-" * 80)
    print("🏷️  GEMINI'S LABELS:")
    print(f"   [1] in_form:          {'✅ YES' if item.in_form else '❌ no'}")
    print(f"   [2] out_of_form:      {'✅ YES' if item.out_of_form else '❌ no'}")
    print(f"   [3] better_than_show: {'✅ YES' if item.better_than_show else '❌ no'}")
    print(f"   [4] worse_than_show:  {'✅ YES' if item.worse_than_show else '❌ no'}")
    print(f"   [5] race_strength:    {item.race_strength.upper()}")

    print("\n💭 REASONING:")
    print(wrap_text(item.reasoning, 76, "   "))
    print("-" * 80)


def display_commands():
    """Display available commands."""
    print("\n📝 COMMANDS:")
    print("   ENTER     = Accept as-is")
    print("   1,2,3,4   = Toggle that flag (e.g., '1' toggles in_form)")
    print("   5s/5a/5w/5n = Set race_strength (strong/average/weak/no_signal)")
    print("   r         = Edit reasoning")
    print("   a         = Add to reasoning")
    print("   s         = Skip (exclude from output)")
    print("   b         = Go back one")
    print("   q         = Quit and save")
    print()


def apply_commands(cmd: str, item: LabeledComment) -> LabeledComment:
    """Apply command string to item and return modified item."""
    cmd = cmd.lower().strip()

    # Handle individual toggles
    if "1" in cmd:
        item.in_form = not item.in_form
    if "2" in cmd:
        item.out_of_form = not item.out_of_form
    if "3" in cmd:
        item.better_than_show = not item.better_than_show
    if "4" in cmd:
        item.worse_than_show = not item.worse_than_show

    # Handle race strength
    if "5s" in cmd:
        item.race_strength = "strong"
    elif "5a" in cmd:
        item.race_strength = "average"
    elif "5w" in cmd:
        item.race_strength = "weak"
    elif "5n" in cmd:
        item.race_strength = "no_signal"

    return item


def review_labels(
    input_path: str | Path,
    output_path: str | Path | None = None,
):
    """
    Interactive review of Gemini-labeled comments.

    Args:
        input_path: Path to Gemini-labeled JSONL file
        output_path: Path to save reviewed examples (defaults to reviewed.jsonl)
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.parent / "reviewed.jsonl"
    else:
        output_path = Path(output_path)

    # Load input
    with open(input_path) as f:
        data = [LabeledComment(**json.loads(line)) for line in f]

    # Load existing reviewed to skip
    reviewed = []
    reviewed_inputs = set()
    if output_path.exists():
        with open(output_path) as f:
            for line in f:
                item = LabeledComment(**json.loads(line))
                reviewed.append(item)
                reviewed_inputs.add(item.formatted_input)
        print(f"Loaded {len(reviewed)} already reviewed. Resuming...")

    # Filter to unreviewed items
    to_review = [item for item in data if item.formatted_input not in reviewed_inputs]

    if not to_review:
        print("All items already reviewed!")
        return reviewed

    stats = {"accepted": 0, "corrected": 0, "skipped": 0}
    current_idx = 0

    while current_idx < len(to_review):
        item = to_review[current_idx]
        total_reviewed = len(reviewed)

        display_item(item, total_reviewed + 1, len(data))
        display_commands()

        try:
            action = input(">>> ").strip()
        except (KeyboardInterrupt, EOFError):
            action = "q"

        if action.lower() == "q":
            print("\n💾 Saving and quitting...")
            break

        elif action.lower() == "s":
            stats["skipped"] += 1
            current_idx += 1
            continue

        elif action.lower() == "b":
            # Go back
            if reviewed:
                # Remove last from reviewed
                last = reviewed.pop()
                reviewed_inputs.remove(last.formatted_input)
                # Re-insert at current position
                to_review.insert(current_idx, last)
                print("⬅️  Going back one...")
            continue

        elif action.lower() == "r":
            # Replace reasoning
            print(f"\nCurrent: {item.reasoning}")
            new_reason = input("New reasoning: ").strip()
            if new_reason:
                item.reasoning = new_reason
            reviewed.append(item)
            reviewed_inputs.add(item.formatted_input)
            stats["corrected"] += 1
            current_idx += 1

        elif action.lower() == "a":
            # Add to reasoning
            print(f"\nCurrent: {item.reasoning}")
            addition = input("Add: ").strip()
            if addition:
                item.reasoning = item.reasoning + " " + addition
            reviewed.append(item)
            reviewed_inputs.add(item.formatted_input)
            stats["corrected"] += 1
            current_idx += 1

        elif action == "":
            # Accept as-is
            reviewed.append(item)
            reviewed_inputs.add(item.formatted_input)
            stats["accepted"] += 1
            current_idx += 1

        else:
            # Apply corrections
            item = apply_commands(action, item)
            reviewed.append(item)
            reviewed_inputs.add(item.formatted_input)
            stats["corrected"] += 1
            current_idx += 1

        # Save incrementally
        with open(output_path, "w") as f:
            for r in reviewed:
                f.write(r.model_dump_json() + "\n")

    # Final summary
    clear_screen()
    print("=" * 60)
    print("  REVIEW COMPLETE")
    print("=" * 60)
    print(f"  ✅ Accepted:  {stats['accepted']}")
    print(f"  ✏️  Corrected: {stats['corrected']}")
    print(f"  ⏭️  Skipped:   {stats['skipped']}")
    print(f"  📁 Total:     {len(reviewed)} saved to {output_path}")
    print("=" * 60)

    return reviewed
