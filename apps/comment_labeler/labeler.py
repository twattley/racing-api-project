"""
Comment Labeler - Simple Gemini-based labeling pipeline.

Flow:
1. Pull unlabeled comments from database
2. Format and send to Gemini in batches
3. Store results in comment_labels table
"""

import json
import time
from dataclasses import dataclass

from google import genai
from google.genai import types
import pandas as pd

from api_helpers.clients import get_postgres_client


SYSTEM_PROMPT = """You are an expert horse racing analyst. Your task is to analyze race comments and position/distance data to extract performance signals.

For each comment, you must determine:

1. **in_form** (true/false): Is the horse currently thriving or "ready to win"? Or is the horse just in good shape running well and generally being competitive? 
   - TRUE: "will remain of interest", "back on track", "best effort of the season", "one to keep on side", "ought to be winning soon", "well handicapped and shaped well".
   - FALSE: If the horse "found little", "folded", "ran moderately", or is "struggling".

2. **out_of_form** (true/false): Is the horse explicitly struggling or physically compromised? 
   - TRUE: "folded tamely", "struggling", "gone off the boil", "ran no sort of race", "labouring", "In a lull", "out of sorts" "going through the motions", "Plodding on", "Weak light gains".
   - CRITICAL: Always set to TRUE if the horse "bled from the nose" or had "atrial fibrillation," regardless of other excuses we need to see physical ailments sorted before they can become of interest.

3. **better_than_show** (true/false): Did the horse run better than the result (unlucky/disadvantaged)?
   - TRUE: "denied clear run", "hampered", "shuffled back", "nearest at finish", "won the race on his side of the track" (if bias existed), "lost 10+ lengths at start", "rider dropped rein/whip".
   - PACE/BIAS: Upgrade if the horse was a "closer in a slow pace", If a horse sits closer to a really strong pace, we can upgrade that as better than shown. However, if they were the one setting the silly pace that was too strong, I don't want this to be marked as better than shown because it tends to be more an attitude thing, and they might probably do the same thing next time. So they will forever get marks better than shown, and that is not correct. It's more of an attitude problem, although not a negative attitude problem! 

4. **flattered_by_result** (true/false): Was the horse "flattered" by circumstances (lucky)?
   - TRUE: "flattered by proximity", "had the run of the race", "benefited from track bias", "advantaged by soft lead", "hit 1.06 in running and lost" (indicating they looked like a winner but didn't go through with it).
   - TRUE: "Benefited from getting things his own way on the rail."

5. **positive_attitude** (true/false): Did the horse show grit and willingness, does the horse respond well to the jockey's urgings? Does he stay on for pressure? Does he battle and rally and fight back when Another Horse Challenges Him 
   - TRUE: "battled", "rallied", "found for pressure", "dug deep", "stuck to task", "head down", "responded to urgings", "straight as a die".

6. **negative_attitude** (true/false): Did the horse show quirks or lack of resolve? Does he hang under pressure? Does he respond for pressure? Does he find for pressure? Does he stand a straight line and respond to the jockey's urgings? 
   - TRUE: "flashing tail", "carrying head awkwardly", "hanging badly", "not finding for pressure", "wayward", "on and off the bridle", "downed tools", "idled", "reared at start" "Very slowly away", "Detached".

7. **to_look_out_for** (true/false): Is this horse explicitly recommended for future races? Maybe he's an improver? Maybe he's ahead of his handicap mark? When this horse next runs, should we be with him? 
   - TRUE: "one to look out for", "keep on side", "remember for next time", "will win soon", "note for the future", "interesting prospect", "one to follow", "won't be long winning", "remain of interest", "compensation awaits".
   - CRITICAL: Requires explicit forward-looking recommendation. Good past performance alone is NOT enough.
   - FALSE if: Comment only describes what happened without future implication.

8. **to_oppose** (true/false): Is this horse explicitly flagged as unreliable or one to bet against? Is he generally inconsistent but has won a race? Was he flattered by the result, and generally opposable next time? When this horse next runs, do we want to be against it? 
   - TRUE: "hard to trust", "one to oppose", "take on next time", "unreliable", "can't be backed with confidence", "flattered", "regressive profile", "best watched not backed", "difficult to catch right".
   - CRITICAL: Requires explicit warning about future betting. Poor performance alone is NOT enough.
   - FALSE if: Horse simply ran badly without a warning about future unreliability.

9. **improver** (true/false): Does the horse have untapped potential the handicapper hasn't fully assessed? Should we forgive this run and give him more chances in the future because of his untapped potential? 
   - TRUE: "open to improvement", "unexposed", "lightly raced", "scope for better", "still learning", "more to come", "could rate higher", "yet to fulfil potential", "progressive", "on the upgrade", "could be ahead of the assessor", "breeding suggests more to come".
   - CONTEXT: Young horses (3yo in handicaps, any novice) are more likely improvers.
   - FALSE if: No explicit mention of potential improvement or being ahead of their mark.

10. **exposed** (true/false): Is the horse fully known to the handicapper with no hidden upside? 
   - TRUE: "exposed", "no secrets", "fully exposed", "well known to handicapper", "has had plenty of chances", "limited", "operating at his level", "this is as good as he is", "held by the assessor", "unlikely to be underestimated".
   - CONTEXT: Older horses (5yo+) with many runs at similar marks are more likely exposed.
   - FALSE if: No explicit mention of being exposed or limited.

LOGIC RULES FOR NEW SIGNALS:
- **Mutual Exclusivity**: A horse can be both `to_look_out_for` AND `to_oppose` if the comment says something like "talented but unreliable - one to watch but not to back."
- **Improver vs Exposed**: These are mutually exclusive. If both seem applicable, re-read the comment - one will be stronger.
- **Confidence Threshold**: Only set TRUE if you are confident the signal is present. When in doubt, default to FALSE.

11. **race_strength** (strong/average/weak/no_signal):
   - **STRONG**: "useful contest", "belting handicap", "solid form", "prestigious prize", "good timefigure". 
     *Note: Large fields (20+ runners) are almost always "strong" as the form is historically more reliable.*
   - **WEAK**: "low-grade", "basement-grade", "ordinary", "modest gallop", "muddling pace", "ropey form", "unreliable sort edging home".
   - **AVERAGE**: "fair handicap", "standard 3-y-o race", "typical race of its kind".

LOGIC RULES FROM HISTORICAL DATA:
- **The "Bled" Rule**: If a horse "bled from the nose," set out_of_form=true and in_form=false. This is a primary physical red flag.
- **The "Eye-Catcher" Rule**: If a horse was "slowly away/dwelt" and "ran on late" or "nearest at finish," set better_than_show=true. However, extreme slowness away is a sign of attitude. So be mindful of horses tardily away or very slowly away. This is attitude problems, not better than could show. 
- **The "Bias" Rule**: If a horse won its side of the track but finished mid-pack because of a track bias, set better_than_show=true and in_form=true.
- **Attitude Filter**: If a horse was unlucky (better_than_show) but also "flashed tail" or "hung," do NOT mark as in_form. They are "hostages to fortune."

Generally speaking, a horse wants to go fairly smoothly on the bridle for the jockey, and when the race hots up, we want to see the horse have a good attitude to the jockey's urgings. This is generally the long and short of it. We don't want to see a horse slowly away or quickly away and pulling hard mad or running too freely and having nothing left when the jockey asks it to race and compete in the finish. These are the general patterns we're looking out for in the comments and in the various categories. 

Respond in JSON:
{
    "in_form": true/false,
    "out_of_form": true/false,
    "better_than_show": true/false,
    "flattered_by_result": true/false,
    "positive_attitude": true/false,
    "negative_attitude": true/false,
    "to_look_out_for": true/false,
    "to_oppose": true/false,
    "improver": true/false,
    "exposed": true/false,
    "race_strength": "strong" | "average" | "weak" | "no_signal",
    "reasoning": "2-3 sentences max. Highlight the specific keywords from the text regarding form, pace, and attitude."
}
"""


# Map non-numeric positions to full words for the LLM
POSITION_MAP = {
    "PU": "Pulled Up",
    "F": "Fell",
    "UR": "Unseated Rider",
    "RO": "Ran Out",
    "BD": "Brought Down",
    "RR": "Refused to Race",
    "SU": "Slipped Up",
    "DSQ": "Disqualified",
}


def _ordinal(n: int) -> str:
    """Return ordinal suffix for a number (1st, 2nd, 3rd, etc)."""
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _distance_category(distance_beaten: float | None) -> str:
    """
    Categorize distance beaten into human-readable description.

    0-3L:  involved in finish
    3-5L:  competitive
    5-8L:  fairly beaten
    8L+:   well beaten
    """
    if distance_beaten is None:
        return ""
    if distance_beaten <= 3:
        return "involved in finish"
    elif distance_beaten <= 5:
        return "competitive"
    elif distance_beaten <= 8:
        return "fairly beaten"
    else:
        return "well beaten"


@dataclass
class CommentRow:
    """A single comment to label."""

    unique_id: str
    finishing_position: str | None
    number_of_runners: int | None
    distance_beaten: float | None
    tf_comment: str | None
    rp_comment: str | None
    main_race_comment: str | None

    def format_input(self) -> str:
        """
        Format for Gemini input with ordinals and distance categories.

        Examples:
        - "Won | [RACE]: strong handicap | [HORSE]: made all"
        - "3rd of 12, involved in finish | [HORSE]: kept on well"
        - "6th of 14, competitive | [HORSE]: one pace final furlong"
        - "10th of 16, fairly beaten | [HORSE]: never travelling"
        """
        parts = []

        # Position context with ordinals and distance category
        if self.finishing_position and self.number_of_runners:
            pos = str(self.finishing_position).strip().upper()

            # Handle special positions
            if pos in POSITION_MAP:
                parts.append(POSITION_MAP[pos])
            elif pos == "1":
                parts.append("Won")
            else:
                # Use ordinal and add distance category
                try:
                    pos_num = int(self.finishing_position)
                    pos_str = (
                        f"{pos_num}{_ordinal(pos_num)} of {self.number_of_runners}"
                    )

                    # Add distance category if available
                    dist_cat = _distance_category(self.distance_beaten)
                    if dist_cat:
                        parts.append(f"{pos_str}, {dist_cat}")
                    else:
                        parts.append(pos_str)
                except (ValueError, TypeError):
                    # Fallback for non-numeric positions
                    parts.append(
                        f"{self.finishing_position} of {self.number_of_runners}"
                    )

        # Race comment
        if self.main_race_comment:
            parts.append(f"[RACE]: {self.main_race_comment}")

        # Horse comment (prefer tf_comment, fallback to rp_comment)
        comment = self.tf_comment or self.rp_comment or ""
        if comment:
            parts.append(f"[HORSE]: {comment}")

        return " | ".join(parts)


def fetch_unlabeled_comments(
    db_client,
    limit: int = 100,
    min_date: str = "2020-01-01",
) -> list[CommentRow]:
    """Fetch comments that haven't been labeled yet."""
    query = f"""
    SELECT 
        r.unique_id,
        r.finishing_position,
        r.number_of_runners,
        r.total_distance_beaten as distance_beaten,
        r.tf_comment,
        r.rp_comment,
        r.main_race_comment
    FROM public.results_data r
    LEFT JOIN public.comment_labels cl ON r.unique_id = cl.unique_id
    WHERE cl.unique_id IS NULL
      AND r.race_date >= '{min_date}'
      AND (r.tf_comment IS NOT NULL OR r.rp_comment IS NOT NULL)
      AND number_of_runners IS NOT NULL
      AND race_date > '2025-01-01'
      and race_type = 'Flat'
      AND race_class >= 2
      AND hcap_range IS NOT NULL
    ORDER BY r.race_date DESC
    LIMIT {limit}
    """
    df = db_client.fetch_data(query)

    return [
        CommentRow(
            unique_id=row["unique_id"],
            finishing_position=row["finishing_position"],
            number_of_runners=row["number_of_runners"],
            distance_beaten=row["distance_beaten"],
            tf_comment=row["tf_comment"],
            rp_comment=row["rp_comment"],
            main_race_comment=row["main_race_comment"],
        )
        for _, row in df.iterrows()
    ]


class RateLimitError(Exception):
    """Raised when API rate limit is hit."""

    pass


def label_comment(
    formatted_input: str,
    client: genai.Client,
    model_name: str = "gemini-2.0-flash-exp",
) -> dict | None:
    """
    Label a single comment using Gemini.
    Args:
        formatted_input: The formatted context + comment string
        client: Gemini client
        model_name: Model to use
    Returns:
        Dict with label fields, or None if failed
    Raises:
        RateLimitError: If daily quota exceeded (caller should stop)
    """
    try:
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
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            raise RateLimitError(f"Rate limit exceeded: {e}")
        print(f"Error labeling: {e}")
        return None


def label_batch(
    comments: list[CommentRow],
    client: genai.Client,
    db_client,
    model_name: str = "gemini-2.0-flash-exp",
    delay: float = 7.0,  # 10 RPM limit = 6s minimum, use 7s for safety
) -> tuple[int, bool]:
    """Label a batch of comments, saving each to DB immediately.

    Returns:
        Tuple of (labeled_count, rate_limited)
    """
    labeled_count = 0

    for i, comment in enumerate(comments, 1):
        formatted = comment.format_input()
        print(f"[{i}/{len(comments)}] {formatted[:80]}...")

        try:
            labels = label_comment(formatted, client, model_name)
        except RateLimitError as e:
            print(f"\n⛔ {e}")
            print(f"Stopping - saved {labeled_count} labels this batch.")
            print("Progress saved. Run again later or upgrade your plan.")
            return labeled_count, True

        # Skip if not a valid dict response
        if not isinstance(labels, dict):
            print(f"  Skipping: got {type(labels).__name__} instead of dict")
            continue

        # Save immediately to DB
        row = {
            "unique_id": comment.unique_id,
            "in_form": labels.get("in_form", False),
            "out_of_form": labels.get("out_of_form", False),
            "better_than_show": labels.get("better_than_show", False),
            "flattered_by_result": labels.get("flattered_by_result", False),
            "positive_attitude": labels.get("positive_attitude", False),
            "negative_attitude": labels.get("negative_attitude", False),
            "to_look_out_for": labels.get("to_look_out_for", False),
            "to_oppose": labels.get("to_oppose", False),
            "improver": labels.get("improver", False),
            "exposed": labels.get("exposed", False),
            "race_strength": labels.get("race_strength", "no_signal"),
            "reasoning": labels.get("reasoning", ""),
        }

        df = pd.DataFrame([row])
        db_client.store_data(
            data=df,
            table="comment_labels",
            schema="public",
            created_at=True,
        )
        labeled_count += 1
        print(f"  Saved to DB")

        time.sleep(delay)

    return labeled_count, False


def save_labels(db_client, labels: list[dict]) -> None:
    """Save labels to database."""
    if not labels:
        print("No labels to save")
        return

    df = pd.DataFrame(labels)
    db_client.store_data(
        data=df,
        table="comment_labels",
        schema="public",
        created_at=True,
    )
    print(f"Saved {len(labels)} labels to public.comment_labels")


def run_labeling_pipeline(
    batch_size: int = 50,
    total_limit: int = 500,
    model_name: str = "gemini-2.0-flash-exp",
    min_date: str = "2020-01-01",
) -> None:
    """Run the full labeling pipeline."""
    import os
    from dotenv import load_dotenv

    load_dotenv(
        dotenv_path="/Users/tomwattley/App/racing-api-project/racing-api-project/libraries/api-helpers/src/api_helpers/.env"
    )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    db_client = get_postgres_client()
    gemini_client = genai.Client(api_key=api_key)

    # Process in batches
    total_labeled = 0
    while total_labeled < total_limit:
        # Fetch unlabeled
        comments = fetch_unlabeled_comments(
            db_client,
            limit=batch_size,
            min_date=min_date,
        )

        if not comments:
            print("No more unlabeled comments")
            break

        print(f"\nBatch: {len(comments)} comments")

        # Label and save each to DB immediately
        batch_labeled, rate_limited = label_batch(
            comments, gemini_client, db_client, model_name
        )

        total_labeled += batch_labeled
        print(f"Progress: {total_labeled}/{total_limit}")

        if rate_limited:
            print(f"\n⛔ Rate limit hit. Total labeled this session: {total_labeled}")
            break

    print(f"\nDone! Labeled {total_labeled} comments total")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Label comments with Gemini")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size")
    parser.add_argument("--total", type=int, default=500, help="Total to label")
    parser.add_argument("--model", default="gemini-2.0-flash-exp", help="Gemini model")
    parser.add_argument("--min-date", default="2020-01-01", help="Min race date")

    args = parser.parse_args()

    run_labeling_pipeline(
        batch_size=args.batch_size,
        total_limit=args.total,
        model_name=args.model,
        min_date=args.min_date,
    )
