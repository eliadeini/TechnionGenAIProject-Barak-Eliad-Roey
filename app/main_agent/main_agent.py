"""Main Agent.

Orchestrates the conversation with the candidate. On each turn it decides
among Continue / Schedule / End by first getting a tentative action from the
LLM, then routing to the one matching Advisor (Exit, Scheduling, or Info) to
confirm/execute it ("classify-then-route").
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# TODO: from app.config import ...


class MainAgent:
    """Decides the next action each turn and delegates to the matching Advisor."""

    def __init__(self, exit_advisor, scheduling_advisor, info_advisor):
        self.exit_advisor = exit_advisor
        self.scheduling_advisor = scheduling_advisor
        self.info_advisor = info_advisor

        # LLM used for the tentative classify step.
        # TODO: pull model name / temperature from app.config instead of hardcoding.
        self.llm = ChatOpenAI(model="gpt-4o-2024-11-20", temperature=0)

        # TODO: replace this generic prompt with one that produces a structured
        # tentative action (continue / end / schedule) -- see app.schemas once
        # it exists -- instead of free text.
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an assistant in a company. If the user wants to schedule an appointment, respond: "
             "'I will check available slots for you.' Otherwise, answer normally."),
            MessagesPlaceholder(variable_name="history"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
            ("user", "{input}"),
        ])

        agent = create_openai_tools_agent(self.llm, tools=[], prompt=self.prompt)
        executor = AgentExecutor(agent=agent, tools=[], verbose=False)

        # Per-session chat history store, keyed by session_id.
        # TODO: extract this into app.memory once that module exists, so
        # Streamlit / tests can share the same session store directly.
        self._history_store = {}
        self.executor_with_memory = RunnableWithMessageHistory(
            executor,
            get_session_history=self._get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def _get_history(self, session_id):
        if session_id not in self._history_store:
            self._history_store[session_id] = ChatMessageHistory()
        return self._history_store[session_id]

    def handle_turn(self, session_id, text):
        """Handle one turn of the conversation for `session_id`.

        TODO:
        - Call self.executor_with_memory (or a dedicated classify prompt) to
          get a tentative action, as structured output (see app.schemas).
        - Route based on the tentative action:
            * "end"      -> self.exit_advisor.evaluate(conversation)
            * "schedule" -> self.scheduling_advisor.propose_slots(conversation)
            * "continue" -> self.info_advisor.answer(conversation)
        - Combine the Advisor's result with the tentative action into the
          final AgentDecision (action, reply_text, reasoning) and return it.
        """
        raise NotImplementedError
