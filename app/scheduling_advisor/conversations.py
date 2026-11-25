"""One text format for every agent that reads a conversation, and the time of a conversation."""
from datetime import datetime


def format_history(turns):
    """Turns (in the format of sms_conversations.json) -> text"""
    return "\n".join([f'{t["speaker"].capitalize()}: {t["text"]}' for t in turns])


def conversation_time(conversation):
    """The time of the last message. The Scheduling Advisor finds "next Friday" from it"""
    return datetime.fromisoformat(conversation[-1]["timestamp_utc"].rstrip("Z"))
