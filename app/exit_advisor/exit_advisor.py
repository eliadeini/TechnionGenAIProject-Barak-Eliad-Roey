"""Conversation Exit Advisor.

Evaluates whether it is appropriate to end the conversation, so that
uninterested candidates (e.g. already found a job) are not unnecessarily
followed up with. Backed by a fine-tuned model trained to detect conversation
scenarios that are expected to conclude.
"""

# TODO: load the fine-tuned model id / client from app.config


class ExitAdvisor:
    """Confirms whether ending the conversation is the right call."""

    def __init__(self):
        # TODO: construct the (fine-tuned) LLM client used to classify
        # whether the candidate's last messages signal disinterest.
        pass

    def evaluate(self, conversation):
        """Decide whether ending the conversation is appropriate.

        TODO:
        - Pass `conversation` to the fine-tuned exit-detection model.
        - Return an AdvisorResult (see app.schemas, once it exists) saying
          whether to confirm ending, plus a closing reply if so.
        """
        raise NotImplementedError
