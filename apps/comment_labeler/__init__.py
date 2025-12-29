"""
Comment Labeler - Tools for creating training data for horse racing comment analysis.

Workflow:
1. Search for specific phrases to curate examples
2. Use Gemini to pick diverse examples from random sample
3. Label with Gemini (4 signals: in_form, out_of_form, better_than_show, worse_than_show)
4. Human review with ability to edit reasoning
5. Export to database for training
"""

from .models import LabeledComment

__all__ = [
    "LabeledComment",
]
