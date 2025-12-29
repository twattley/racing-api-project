"""
Use Gemini to select diverse/interesting examples from a random sample.

This helps build a training set with varied language patterns rather than
lots of repetitive "kept on" type comments.
"""

import json
from pathlib import Path

import pandas as pd
from google import genai
from google.genai import types


DIVERSE_PROMPT = """You are an expert horse racing analyst. I have a list of race examples with comments and context. I need you to select the most DIVERSE and INTERESTING examples for training a language model.

Select {count} examples that:
1. Use different/unusual phrasing (avoid repetitive "kept on", "stayed on" etc)
2. Contain clear signals about form, luck, race strength, or performance
3. Cover a variety of scenarios (good runs, bad runs, unlucky, flattered, strong races, weak races)
4. Include niche racing terminology and expressions
5. Are unambiguous in their meaning
6. Have interesting context (e.g., finishing close up in big field vs tailing off)

Here are the examples to choose from:

{examples}

Return a JSON array of the indices (0-based) of the {count} most diverse examples you selected.

Example format:
[0, 5, 12, 23, ...]
"""


def select_diverse_examples(
    examples: list[dict],
    output_path: str | Path,
    api_key: str,
    count: int = 10,
    model_name: str = "gemini-2.5-pro",
) -> list[dict]:
    """
    Use Gemini to select diverse examples from a list.

    Args:
        examples: List of example dicts with formatted_input
        output_path: Path to CSV file to append selected examples to
        api_key: Gemini API key
        count: Number of diverse examples to select
        model_name: Gemini model to use

    Returns:
        List of selected examples
    """
    client = genai.Client(api_key=api_key)

    # Format examples for the prompt - just show the formatted_input
    examples_text = "\n".join(
        f"{i}. {ex['formatted_input']}" for i, ex in enumerate(examples)
    )

    prompt = DIVERSE_PROMPT.format(count=count, examples=examples_text)

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        ),
    )

    selected_indices = json.loads(response.text)

    # Load existing to avoid duplicates
    output_path = Path(output_path)
    existing = set()
    if output_path.exists():
        existing_df = pd.read_csv(output_path)
        existing = set(existing_df["formatted_input"].tolist())

    # Add new examples
    added = []
    for idx in selected_indices:
        if idx < len(examples):
            example = examples[idx]
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

    print(f"Gemini selected {len(selected_indices)} diverse examples")
    print(f"Added {len(added)} new examples to {output_path}")

    for i, ex in enumerate(added, 1):
        print(f"  {i}. {ex['formatted_input'][:80]}...")

    return added
