"""
Local model inference using Ollama.

Wraps the fine-tuned flat-hcap model for labeling comments.
"""

import json

import ollama


MODEL_NAME = "flat-hcap"

# Minimal prompt - the fine-tuned model should understand the task
SYSTEM_PROMPT = """Analyze this horse racing comment and return JSON with these fields:
- in_form (bool): Horse is thriving, likely to run well again
- out_of_form (bool): Horse is regressing, unlikely to replicate
- better_than_show (bool): Performance masked by bad luck
- worse_than_show (bool): Performance flattered by circumstances
- race_strength: "strong", "average", "weak", or "no_signal"
- reasoning: Brief explanation (1-2 sentences)

Respond with valid JSON only."""


def predict(formatted_input: str, model_name: str = MODEL_NAME) -> dict:
    """
    Label a single comment using the local model.

    Args:
        formatted_input: The formatted context + comment string
        model_name: Ollama model name (default: flat-hcap)

    Returns:
        Dict with label fields, or None if parsing fails
    """
    response = ollama.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": formatted_input},
        ],
        format="json",
    )

    try:
        result = json.loads(response["message"]["content"])
        # Normalize and validate fields
        return {
            "in_form": bool(result.get("in_form", False)),
            "out_of_form": bool(result.get("out_of_form", False)),
            "better_than_show": bool(result.get("better_than_show", False)),
            "worse_than_show": bool(result.get("worse_than_show", False)),
            "race_strength": result.get("race_strength", "no_signal"),
            "reasoning": result.get("reasoning", ""),
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Failed to parse model response: {e}")
        return None


def predict_batch(
    formatted_inputs: list[str],
    model_name: str = MODEL_NAME,
) -> list[dict]:
    """
    Label multiple comments.

    Args:
        formatted_inputs: List of formatted context + comment strings
        model_name: Ollama model name

    Returns:
        List of dicts with label fields (None for failed predictions)
    """
    results = []
    for i, formatted_input in enumerate(formatted_inputs, 1):
        print(f"[{i}/{len(formatted_inputs)}] Predicting...")
        result = predict(formatted_input, model_name)
        results.append(result)
    return results
