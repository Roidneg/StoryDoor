"""Compatibility exports for scripts using the original house constants."""
from story_catalog import get_story
_story = get_story()
STORY_ID = _story['id']
STORY_TITLE = _story['title']
MAX_DECISIONS = _story['max_decisions']
STORY_BIBLE = _story['bible']
OPENING_TEXT = _story['opening']
OPENING_CHOICES = _story['opening_choices']
