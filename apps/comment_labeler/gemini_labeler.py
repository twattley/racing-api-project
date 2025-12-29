"""
Use Gemini to label horse racing comments with form signals.
"""

import json
import csv
from pathlib import Path

from google import genai
from google.genai import types


SYSTEM_PROMPT = """You are an expert horse racing analyst. Your task is to analyze race comments and extract signals about the horse's performance.

For each comment, you must determine:

1. **in_form** (true/false): Is the horse currently in good form?
   - TRUE: "will remain of interest", "bounce back to form", "sure to go well again", "clearly thriving"
   - FALSE only if explicitly struggling, not just a bad run

2. **out_of_form** (true/false): Is the horse currently OUT of form?
   - TRUE: "uncertain to reproduce", "wouldn't be obvious to follow up", "hard to fancy", "continues out of sorts"
   - FALSE if just had one bad run or nothing negative said

3. **better_than_show** (true/false): Did the horse run BETTER than the result suggests? (unlucky)
   - TRUE: "denied clear run", "hampered", "would have gone close", "ran on when too late", "not get a clear run"
   - TRUE: Poor ride, wrong tactics, trouble in running
   - FALSE if the result reflects true performance

4. **worse_than_show** (true/false): Did the horse run WORSE than the result suggests? (flattered)
   - TRUE: "flattered by proximity", "got soft lead", "race fell apart", "others underperformed"
   - TRUE: Benefited from circumstances beyond their ability
   - FALSE if the result reflects true performance

5. **race_strength** (strong/average/weak/no_signal): How strong was the race?
   - "strong": "strong gallop", "good depth", "competitive field", "several of these look progressive"
   - "weak": "slowly run", "modest affair", "little strength in depth", "weak event"
   - "average": typical race, nothing special mentioned
   - "no_signal": no information about race strength

PACE AND RACE STRENGTH INTERACTION:
- **Weak/slow pace downgrades race strength**: A slowly run race tends to produce misleading form. Horses that finish well in a weak pace often don't replicate - the form is unreliable. If the comment mentions "slowly run", "steady pace", "no pace", consider setting race_strength to "weak" and be skeptical of in_form signals.
- **Strong/fast pace upgrades race quality**: A genuinely run race (strong gallop, good pace throughout) produces reliable form. Horses that perform well in a strong pace have demonstrated genuine ability - this is a positive signal. If the comment mentions "strong gallop", "good pace", "truly run", this supports in_form signals.
- **Pace context affects worse_than_show**: A horse that "came from off the pace" in a slowly run race may have been flattered - the closers got a free ride. Consider worse_than_show=true in these scenarios.
- **Pace context affects better_than_show**: A horse that "made the running" or "led" in a strong pace did the hard work and may have run better than the result suggests if caught late. Also, a horse "unsuited by the pace" or that "ran on when pace lifted" in a weak pace may have run better than the result - they couldn't show their best.

ATTITUDE AND WILLINGNESS SIGNALS:
These are CRITICAL indicators of a horse's current form and future prospects.

**POSITIVE attitude signals (strong in_form indicators):**
- "rallied", "rallied gamely", "rallied well" - horse responded to pressure and fought back, excellent sign
- "battled", "battled gamely", "battled on" - shows determination and willingness to compete
- "stayed on gamely", "kept on gamely" - the word "gamely" indicates genuine effort and desire to win
- "found extra", "found for pressure" - had reserves and responded when asked
- "ran straight", "stayed straight" - a horse that runs straight is putting in honest effort
- "genuine", "game", "willing" - explicitly positive attitude descriptors

**NEGATIVE attitude signals (strong out_of_form indicators - treat as BIG negatives):**
- "hung left", "hung right", "hung badly" - horse not running straight indicates they're not trying or have issues
- "carried head awkwardly", "carried head high", "head carriage" - BAD SIGN, indicates unwillingness or discomfort
- "found nil", "found nothing", "found little" - no response when asked, very negative
- "outbattled", "out-battled" - lost the fight when challenged, concerning
- "idle", "idled", "not putting it all in" - lack of effort
- "reluctant", "ungenerous" - unwilling attitude
- "wandered", "wandered under pressure" - not focused, not trying

**Finding for pressure is KEY**: A horse that "finds for pressure" or "responds to pressure" is showing positive attitude. A horse that "finds nothing" or is "outbattled" is showing the opposite.

HANDICAP MARK SIGNALS:
Comments often reference where a horse sits in the handicap. This is important context but must be read carefully.

**"Well handicapped" + positive signs = in_form:**
- "becoming well handicapped and looks ready to strike" - POSITIVE, they're dropping to a good mark AND showing signs of form
- "well handicapped, should go well from this mark" - POSITIVE
- "below his last winning mark and shaped with promise" - POSITIVE
- "sliding down the weights and showed more here" - POSITIVE

**"Well handicapped" alone or + negative signs = NOT in_form:**
- "becoming well handicapped but showing no signs of taking advantage" - NEGATIVE, the handicap drop isn't helping
- "well handicapped but continues to disappoint" - NEGATIVE
- "well below his best mark but not interested" - NEGATIVE, attitude issue despite good mark
- "slipping to an attractive mark but hard to trust" - NEGATIVE

**The key question**: Is the horse READY to take advantage of their mark? Look for:
- Signs of returning form (shaped well, ran on, showed more)
- Positive attitude (battled, found for pressure, stayed on gamely)
- Trainer/horse "in form" or "going through a good spell"

Without these positive indicators, "well handicapped" alone is not an in_form signal - many horses drop down the weights while remaining out of form.

IMPORTANT GUIDELINES:
- Most comments will have all FALSE flags - only set TRUE when there's clear evidence
- A single bad run doesn't mean out_of_form - look for patterns or explicit statements
- Context matters: "kept on well" finishing 2nd of 12 beaten 1L is different from same phrase finishing 10th beaten 20L
- The formatted_input includes position and distance beaten - use this context
- Be conservative - when in doubt, leave as FALSE/no_signal
- Attitude signals are particularly important - a horse showing poor attitude is a strong out_of_form signal

Provide reasoning that explains your analysis, including how pace, attitude, and handicap context affected your assessment.

Respond in JSON format:
{
    "in_form": true/false,
    "out_of_form": true/false,
    "better_than_show": true/false,
    "worse_than_show": true/false,
    "race_strength": "strong" | "average" | "weak" | "no_signal",
    "reasoning": "Brief explanation of your analysis make it 2 or 3 sentences max highlighting key parts of the text that you judged it on"
}
"""


def label_comment(
    formatted_input: str,
    client: genai.Client,
    model_name: str = "gemini-3-pro-preview",
) -> dict:
    """
    Label a single comment using Gemini.

    Args:
        formatted_input: The formatted context + comment string
        client: Gemini client
        model_name: Model to use

    Returns:
        Dict with label fields
    """
    response = client.models.generate_content(
        model=model_name,
        contents=f"Analyze this race comment:\n\n{formatted_input}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=1.0,  # Gemini 3 recommends keeping at 1.0
        ),
    )

    return json.loads(response.text)


def label_examples(
    input_path: str | Path,
    output_path: str | Path,
    api_key: str,
    model_name: str = "gemini-3-pro-preview",
) -> None:
    """
    Label all examples in input CSV and write to output JSONL.

    Args:
        input_path: Path to examples.csv
        output_path: Path to write labeled.jsonl
        api_key: Gemini API key
        model_name: Gemini model to use
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    client = genai.Client(api_key=api_key)

    # Read input examples from CSV
    examples = []
    with open(input_path, newline="") as f:
        reader = csv.DictReader(f)
        examples = list(reader)

    # Load already labeled to skip
    already_labeled = set()
    if output_path.exists():
        with open(output_path) as f:
            for line in f:
                row = json.loads(line)
                already_labeled.add(row["formatted_input"])

    total = len(examples)
    labeled_count = len(already_labeled)

    print(f"Found {total} examples, {labeled_count} already labeled")
    print(f"Labeling {total - labeled_count} remaining examples...")

    with open(output_path, "a") as f:
        for i, example in enumerate(examples, 1):
            formatted_input = example["formatted_input"]

            if formatted_input in already_labeled:
                continue

            try:
                labels = label_comment(formatted_input, client, model_name)

                row = {
                    "formatted_input": formatted_input,
                    "in_form": labels.get("in_form", False),
                    "out_of_form": labels.get("out_of_form", False),
                    "better_than_show": labels.get("better_than_show", False),
                    "worse_than_show": labels.get("worse_than_show", False),
                    "race_strength": labels.get("race_strength", "no_signal"),
                    "reasoning": labels.get("reasoning", ""),
                }

                f.write(json.dumps(row) + "\n")
                f.flush()  # Write immediately in case of crash

                labeled_count += 1
                print(f"[{labeled_count}/{total}] {formatted_input[:60]}...")

            except Exception as e:
                print(f"Error labeling example {i}: {e}")
                continue

    print(f"\nDone! Labeled {labeled_count} examples saved to {output_path}")
