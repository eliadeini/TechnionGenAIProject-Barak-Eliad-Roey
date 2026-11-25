"""The agent structure we learned: prompt + tools -> create_openai_tools_agent -> AgentExecutor."""
### in LangChain 1.x the agents that we learned are in langchain_classic
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.scheduling_advisor.config import CHAT_MODEL, check_api_key, load_prompt


def get_llm(max_tokens=400):
    """API parameters: temperature=0 - the most focused and deterministic answers, max_tokens - an SMS is short"""
    check_api_key()
    return ChatOpenAI(model=CHAT_MODEL, temperature=0, max_tokens=max_tokens, timeout=60)


def build_executor(llm, tools, prompt_name):
    ### the order of the messages matters: system -> history -> agent_scratchpad -> user
    prompt = ChatPromptTemplate.from_messages([
        ("system", load_prompt(prompt_name)),
        MessagesPlaceholder(variable_name="history", optional=True),   ### only the Main Agent has memory
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        ("user", "{input}")
    ])

    ### a wrong argument returns an error text, instead of stopping the program
    for t in tools:
        t.handle_validation_error = True

    ### build agent: every answer of the model must be a function call, exactly one at a time
    llm_with_calls = (llm or get_llm()).bind(tool_choice="required", parallel_tool_calls=False)
    agent = create_openai_tools_agent(llm_with_calls, tools, prompt)

    ### create an executor (to run the agent). verbose=True prints every step
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=5)


def run_agent(executor, inputs):
    """return_direct=True: the last function that the agent called ends the run, and its result (schemas.py) is the answer.
    A text (a wrong argument, too many steps) is not an answer"""
    output = executor.invoke(inputs)["output"]
    return output if isinstance(output, BaseModel) else None
