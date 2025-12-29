#!/usr/bin/env python
"""
Comment Labeler CLI

Workflow:
    # 1. Search for specific phrases to curate examples
    python -m apps.comment_labeler.cli search "reluctant to go to the start"
    python -m apps.comment_labeler.cli search "denied a clear run"

    # 2. Let Gemini pick diverse examples from random sample
    python -m apps.comment_labeler.cli diverse --count 10

    # 3. Label all examples with Gemini
    python -m apps.comment_labeler.cli label

    # 4. Human review - accept, correct flags, edit reasoning
    python -m apps.comment_labeler.cli review

    # 5. Check stats
    python -m apps.comment_labeler.cli stats
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(
    dotenv_path="/Users/tomwattley/App/racing-api-project/racing-api-project/libraries/api-helpers/src/api_helpers/.env"
)


# Default paths
DEFAULT_CSV = "apps/comment_labeler/comments.csv"
DEFAULT_EXAMPLES = "apps/comment_labeler/examples.csv"
DEFAULT_LABELED = "apps/comment_labeler/labeled.jsonl"
DEFAULT_REVIEWED = "apps/comment_labeler/reviewed.jsonl"


def cmd_search(args):
    """Search CSV for pattern and add matching examples."""
    from .extract_comments import search_comments

    search_comments(
        csv_path=args.csv,
        pattern=args.pattern,
        output_path=args.output,
        count=args.count,
    )


def cmd_diverse(args):
    """Use Gemini to select diverse examples from random sample."""
    import time
    from .extract_comments import random_sample
    from .diverse_sampler import select_diverse_examples

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Provide --api-key or set GEMINI_API_KEY")
        return

    total_added = 0
    for i in range(args.iterations):
        print(f"\n{'='*50}")
        print(f"Iteration {i+1}/{args.iterations}")
        print(f"{'='*50}")

        # Get random sample (returns list of dicts with full context)
        # Use different seed each iteration for variety
        examples = random_sample(args.csv, count=args.sample_size, seed=42 + i)
        print(f"Got {len(examples)} random examples from {args.csv}")

        # Let Gemini pick diverse ones
        added = select_diverse_examples(
            examples=examples,
            output_path=args.output,
            api_key=api_key,
            count=args.count,
        )
        total_added += len(added)

        print(f"Running total: {total_added} examples added")

        # Small delay between iterations to avoid rate limits
        if i < args.iterations - 1:
            time.sleep(1)

    print(f"\n{'='*50}")
    print(f"COMPLETE: Added {total_added} examples across {args.iterations} iterations")
    print(f"{'='*50}")


def cmd_label(args):
    """Label all examples with Gemini."""
    from .gemini_labeler import label_examples

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Provide --api-key or set GEMINI_API_KEY")
        return

    label_examples(
        input_path=args.input,
        output_path=args.output,
        api_key=api_key,
        model_name=args.model,
    )


def cmd_review(args):
    """Human review of labeled examples."""
    from .reviewer import review_labels

    review_labels(
        input_path=args.input,
        output_path=args.output,
        start_from=args.start_from,
    )


def cmd_stats(args):
    """Show statistics on labeled data."""
    import json
    from .models import LabeledComment

    path = Path(args.input)
    if not path.exists():
        print(f"File not found: {path}")
        return

    data = []
    with open(path) as f:
        for line in f:
            data.append(LabeledComment(**json.loads(line)))

    print(f"\n{'='*50}")
    print(f"Stats for {path}")
    print(f"{'='*50}")
    print(f"Total examples: {len(data)}")
    print(f"")
    print(f"Race Strength:")
    print(f"  strong:     {sum(1 for d in data if d.race_strength == 'strong')}")
    print(f"  average:    {sum(1 for d in data if d.race_strength == 'average')}")
    print(f"  weak:       {sum(1 for d in data if d.race_strength == 'weak')}")
    print(f"  no_signal:  {sum(1 for d in data if d.race_strength == 'no_signal')}")
    print(f"")
    print(f"Performance Flags:")
    print(f"  in_form:          {sum(1 for d in data if d.in_form)}")
    print(f"  out_of_form:      {sum(1 for d in data if d.out_of_form)}")
    print(f"  better_than_show: {sum(1 for d in data if d.better_than_show)}")
    print(f"  worse_than_show:  {sum(1 for d in data if d.worse_than_show)}")
    print(
        f"  (no flags):       {sum(1 for d in data if not any([d.in_form, d.out_of_form, d.better_than_show, d.worse_than_show]))}"
    )
    print(f"")
    print(f"Status:")
    print(f"  Gemini labeled:   {sum(1 for d in data if d.gemini_labeled)}")
    print(f"  Human verified:   {sum(1 for d in data if d.human_verified)}")
    print(f"  Human corrected:  {sum(1 for d in data if d.human_corrected)}")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Comment Labeler - Create training data for horse racing comment analysis"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Search command
    p_search = subparsers.add_parser(
        "search", help="Search CSV for pattern and add examples"
    )
    p_search.add_argument("pattern", help="Text pattern to search for")
    p_search.add_argument("--csv", "-c", default=DEFAULT_CSV, help="Source CSV file")
    p_search.add_argument(
        "--output", "-o", default=DEFAULT_EXAMPLES, help="Output JSONL file"
    )
    p_search.add_argument(
        "--count", "-n", type=int, default=2, help="Number of examples to add"
    )
    p_search.set_defaults(func=cmd_search)

    # Diverse command
    p_diverse = subparsers.add_parser(
        "diverse", help="Gemini picks diverse examples from random sample"
    )
    p_diverse.add_argument("--csv", "-c", default=DEFAULT_CSV, help="Source CSV file")
    p_diverse.add_argument(
        "--output", "-o", default=DEFAULT_EXAMPLES, help="Output JSONL file"
    )
    p_diverse.add_argument(
        "--count", "-n", type=int, default=10, help="Number of diverse examples"
    )
    p_diverse.add_argument(
        "--sample-size", "-s", type=int, default=100, help="Random sample size"
    )
    p_diverse.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=1,
        help="Number of iterations (for building large dataset)",
    )
    p_diverse.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY)")
    p_diverse.set_defaults(func=cmd_diverse)

    # Label command
    p_label = subparsers.add_parser("label", help="Label examples with Gemini")
    p_label.add_argument(
        "--input", "-i", default=DEFAULT_EXAMPLES, help="Input JSONL file"
    )
    p_label.add_argument(
        "--output", "-o", default=DEFAULT_LABELED, help="Output JSONL file"
    )
    p_label.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY)")
    p_label.add_argument("--model", default="gemini-2.5-pro", help="Gemini model")
    p_label.add_argument(
        "--delay", type=float, default=0.5, help="Delay between API calls"
    )
    p_label.set_defaults(func=cmd_label)

    # Review command
    p_review = subparsers.add_parser("review", help="Human review of labeled examples")
    p_review.add_argument(
        "--input", "-i", default=DEFAULT_LABELED, help="Input JSONL file"
    )
    p_review.add_argument(
        "--output", "-o", default=DEFAULT_REVIEWED, help="Output JSONL file"
    )
    p_review.add_argument("--start-from", type=int, default=0, help="Start from index")
    p_review.set_defaults(func=cmd_review)

    # Stats command
    p_stats = subparsers.add_parser("stats", help="Show label statistics")
    p_stats.add_argument(
        "--input", "-i", default=DEFAULT_REVIEWED, help="Input JSONL file"
    )
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
