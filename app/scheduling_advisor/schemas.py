"""The answer of the Scheduling Advisor: AdvisorResult of the project, with the fields of this advisor."""
from typing import Optional

from app.schemas import AdvisorResult


class SchedulingAdvisorResult(AdvisorResult):
    """What SchedulingAdvisor.propose_slots() returns. reply_text = the proposed slots as text."""

    reply_text: str = ""
    decision: str = "No answer"          ### Sched / Don't Sched. "No answer" = the advisor failed
    status: Optional[str] = None         ### offer, not available, agreed, no free slots / too early, open question, wants to stop
    reason: Optional[str] = None
    proposed_slots: list[str] = []
