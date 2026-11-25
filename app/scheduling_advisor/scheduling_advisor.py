"""Interview Scheduling Advisor.

Assists the Main Agent in determining whether it's the right time to schedule
an interview: checks conversation context, validates proposed times, and
interacts with recruiter calendars (the SQL `db_Tech.sql` availability table)
via function calling.

The model READS the conversation, the code KNOWS the date, and SQL DECIDES what is free:
1. The two options of the advisor (Sched / Don't Sched) are two functions, and the model must call one of them.
2. The model only translates what the candidate wants into the arguments. It never sees the calendar: the slots in the answer come only from SQL.
3. One SQL query both searches and validates: a free slot is the nearest slot to itself.
4. return_direct=True: the answer of SQL is the answer of the advisor, so one call to the model is enough.
"""
from datetime import datetime, timedelta
from typing import Literal

from langchain.tools import tool

from app.scheduling_advisor.agents import build_executor, run_agent
from app.scheduling_advisor.calendar_tools import ScheduleDB
from app.scheduling_advisor.conversations import conversation_time, format_history
from app.scheduling_advisor.schemas import SchedulingAdvisorResult


def list_dates(now, days=35):
    """The next five weeks as text, so the model looks a date up instead of calculating it"""
    sunday = now - timedelta(days=(now.weekday() + 1) % 7)   ### the first day of this week
    lines = []

    for i in range(days):
        day = now + timedelta(days=i)
        week = (day - sunday).days // 7
        note = ["this week", "next week"][week] if week < 2 else f"in {week} weeks"
        if i < 2:
            note = ["today", "tomorrow"][i] + ", " + note
        lines.append(f"{day:%A %Y-%m-%d} ({note})")

    return "\n".join(lines)


def slots_text(slots):
    """['2024-04-04 10:00', '2024-04-04 14:00'] -> 'Thursday, April 4 at 10 AM or 2 PM'"""
    days = {}
    for slot in sorted(slots):
        d = datetime.strptime(slot, "%Y-%m-%d %H:%M")
        days.setdefault(f"{d:%A, %B} {d.day}", []).append(f"{d:%I %p}".lstrip("0"))

    parts = []
    for day, hours in days.items():
        if len(hours) > 2:
            hours = [", ".join(hours[:-1]), hours[-1]]   ### 9 AM, 10 AM or 2 PM
        parts.append(f'{day} at {" or ".join(hours)}')

    return ", or ".join(parts)


class SchedulingAdvisor:
    """Proposes and validates interview slots based on the conversation so far."""

    def __init__(self, llm=None, db=None):
        self.llm = llm
        self.db = db or ScheduleDB()

    def make_tools(self, now, booked=None):
        """The time of the conversation and the booked slot come from the code, the model cannot change them"""

        @tool(return_direct=True)
        def sched(reason: str, agreed: bool, days: list[str] = [], hours: list[str] = [], refused: list[str] = []) -> SchedulingAdvisorResult:
            """This is the right time for an interview: search the calendar. Leave out what the candidate did not mention.
            reason - what the candidate wants, one short sentence.
            agreed - true only if the candidate accepted or suggested one exact day and one exact hour.
            days - one day that suits the candidate [YYYY-MM-DD], or a range [first day, last day].
            hours - one hour that suits the candidate [HH:MM], or a range [first hour, last hour].
            refused - the days (YYYY-MM-DD) and the times (YYYY-MM-DD HH:MM) that the candidate turned down."""
            return self.find_slots(now, days, hours, refused, agreed, reason, booked)

        @tool(return_direct=True)
        def dont_sched(reason: Literal["too early", "open question", "wants to stop"]) -> SchedulingAdvisorResult:
            """This is not the right time for an interview."""
            return SchedulingAdvisorResult(decision="Don't Sched", status=reason)

        return [sched, dont_sched]

    def propose_slots(self, conversation, booked=None):
        """The complete chat history -> the 3 nearest available interview slots, or the slot that was agreed.
        booked - the slot that this candidate already booked, if there is one"""
        now = conversation_time(conversation)
        executor = build_executor(self.llm, self.make_tools(now, booked), "scheduling_advisor")
        result = run_agent(executor, {
            "input": format_history(conversation),
            "now": f"{now:%A %Y-%m-%d %H:%M}",
            "dates": list_dates(now),
        })
        return result or SchedulingAdvisorResult()

    def find_slots(self, now, days=(), hours=(), refused=(), agreed=False, reason=None, booked=None):
        ### no wish = any day from tomorrow, at any hour. sorted: in "Tuesday or Thursday" the Thursday may come first
        days = sorted(days) or [f"{now + timedelta(days=1):%Y-%m-%d}", "9999-12-31"]
        hours = sorted([hour.zfill(5) for hour in hours]) or ["09:00", "17:00"]   ### 9:00 -> 09:00
        refused = [" ".join([part.zfill(5) for part in r.split()]) for r in refused]   ### 2024-04-04 9:00 -> 2024-04-04 09:00

        df = self.db.get_next_three_dates(f"{now:%Y-%m-%d %H:%M}", days, hours, refused, agreed, booked)
        status = df["status"][0] if len(df) else "no free slots"

        ### an agreed time is one slot, in every other status there are up to three options
        slots = df["slot"].tolist()
        if status == "agreed":
            slots = slots[:1]

        return SchedulingAdvisorResult(decision="Sched", status=status, reason=reason, proposed_slots=slots, reply_text=slots_text(slots))

    def book(self, slot):
        return self.db.book(slot)
