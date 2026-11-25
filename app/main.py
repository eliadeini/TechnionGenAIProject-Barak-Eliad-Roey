"""Composition root for the SMS recruiting chatbot.

Wires together config, the per-session memory store, the three Advisors,
and the MainAgent, and exposes a single entry point -- `handle_message` --
that both the Streamlit UI and tests call into. This file should stay thin:
no prompts, no LLM client construction, no routing logic -- that all lives
in app.main_agent / app.advisors.
"""

# TODO: from app.config import ...
# TODO: from app.memory import ...
# TODO: from app.advisors.exit_advisor import ExitAdvisor
# TODO: from app.advisors.scheduling_advisor import SchedulingAdvisor
# TODO: from app.advisors.info_advisor import InfoAdvisor
# TODO: from app.main_agent.main_agent import MainAgent


def handle_message(session_id: str, text: str):
    """Handle one turn of the conversation for `session_id`.

    Returns an AgentDecision (see app.schemas) with the chosen action
    (continue / end / schedule) and the reply text to send back.
    """
    # TODO: construct the advisors + MainAgent (or receive them via
    # dependency injection) and delegate to MainAgent's classify-then-route
    # flow, passing it the message history for this session_id.
    raise NotImplementedError


def main():
    """Simple terminal loop for manual testing before Streamlit exists."""
    # TODO: read input() in a loop, call handle_message(), print the reply.
    pass


if __name__ == "__main__":
    main()
