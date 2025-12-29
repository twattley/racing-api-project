"""
Pydantic models for comment labeling.

Individual Performance Signals (4):
- in_form: Horse is thriving, likely to run well again
- out_of_form: Horse is regressing, unlikely to replicate
- better_than_show: Performance was masked by bad luck
- worse_than_show: Performance was flattered by circumstances

Race Strength Signal:
- strong, average, weak, no_signal
"""

from typing import Literal

from pydantic import BaseModel, Field


RaceStrength = Literal["strong", "average", "weak", "no_signal"]


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


def format_input(
    position: int | None,
    runners: int | None,
    distance_beaten: float | None,
    main_race_comment: str,
    performance_comment: str,
) -> str:
    """
    Format all context into a single string for the model.

    Example outputs:
    - "Won. Strong race. made all, kept on well"
    - "3rd of 12, involved in finish. kept on well under pressure"
    - "6th of 14, competitive. one pace final furlong"
    - "10th of 16, fairly beaten. never travelling"
    """
    parts = []

    # Position description
    if position is not None and runners is not None:
        if position == 1:
            parts.append("Won")
        else:
            pos_str = f"{position}{_ordinal(position)} of {runners}"
            dist_cat = _distance_category(distance_beaten)
            if dist_cat:
                parts.append(f"{pos_str}, {dist_cat}")
            else:
                parts.append(pos_str)

    # Race comment (if present)
    if main_race_comment:
        parts.append(f"[RACE]: {main_race_comment}")

    # Performance comment
    if performance_comment:
        parts.append(f"[HORSE]: {performance_comment}")

    return " | ".join(parts)


class LabeledComment(BaseModel):
    """A comment with its extracted signals and metadata."""

    # Single formatted input for the model
    formatted_input: str = Field(
        description="Formatted context + comment string for model input"
    )

    # Race Strength Signal
    race_strength: RaceStrength = Field(
        default="no_signal",
        description="Strength of the race: strong, average, weak, or no_signal",
    )

    # Individual Performance Signals
    in_form: bool = Field(
        default=False, description="Horse is thriving, likely to run well again"
    )
    out_of_form: bool = Field(
        default=False, description="Horse is regressing, unlikely to replicate"
    )
    better_than_show: bool = Field(
        default=False,
        description="Performance masked by bad luck, interference, wrong tactics",
    )
    worse_than_show: bool = Field(
        default=False, description="Performance flattered by circumstances"
    )

    # Reasoning from Gemini (editable by human)
    reasoning: str = Field(
        default="", description="Explanation of why these signals were extracted"
    )

    # Metadata
    gemini_labeled: bool = False
    human_verified: bool = False
    human_corrected: bool = False
