"""Shared data contracts between the Main Agent and the three Advisors.

Defining these upfront means every component (MainAgent, ExitAdvisor,
SchedulingAdvisor, InfoAdvisor) can return a well-typed object instead of
free text -- which is what makes it possible to score the bot's decisions
against the labeled actions in sms_conversations.json (Accuracy / Confusion
Matrix) without brittle text parsing.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Action(str, Enum):
    """The three actions the Main Agent can take on any turn."""

    CONTINUE = "continue"
    END = "end"
    SCHEDULE = "schedule"


class AgentDecision(BaseModel):
    """What MainAgent.handle_turn() returns -- the final result of one turn."""

    action: Action
    reply_text: str
    reasoning: Optional[str] = None


class AdvisorResult(BaseModel):
    """Base result returned by every Advisor's method.

    TODO: decide whether this single shared shape (plus the field below) is
    enough, or whether each Advisor needs its own subclass, e.g.:
        class ExitAdvisorResult(AdvisorResult):
            confirmed: bool
        class SchedulingAdvisorResult(AdvisorResult):
            proposed_slots: list[str]
        class InfoAdvisorResult(AdvisorResult):
            ...
    """

    reply_text: str
    # TODO: add whatever fields MainAgent.handle_turn() needs to combine this
    # result into the final AgentDecision (e.g. a confirmation flag for
    # ExitAdvisor, a list of slots for SchedulingAdvisor).
