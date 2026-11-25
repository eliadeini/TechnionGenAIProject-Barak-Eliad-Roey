"""Interview Scheduling Advisor.

Assists the Main Agent in determining whether it's the right time to schedule
an interview: checks conversation context, validates proposed times, and
interacts with recruiter calendars (the SQL `db_Tech.sql` availability table)
via function calling.
"""

# TODO: from app.tools.calendar_tools import get_next_three_dates


class SchedulingAdvisor:
    """Proposes and validates interview slots based on the conversation so far."""

    def __init__(self):
        # TODO: construct the LLM client / prompt used to extract a preferred
        # date from the conversation (e.g. "next Friday") and bind the
        # get_next_three_dates tool for function calling.
        pass

    def propose_slots(self, conversation):
        """Suggest the 3 nearest available interview slots.

        TODO:
        - Infer the current date from when the conversation took place.
        - Extract any candidate-preferred date/time from `conversation`.
        - Query recruiter availability (db_Tech.sql) via get_next_three_dates.
        - Return an AdvisorResult (see app.schemas, once it exists) with the
          3 proposed slots.
        """
        raise NotImplementedError
