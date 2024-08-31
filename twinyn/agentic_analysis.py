from twinyn.agents.prompts import *

import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from autogen import ConversableAgent, AssistantAgent
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.coding.func_with_reqs import with_requirements
load_dotenv()

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

@with_requirements(python_packages=["psycopg2"], global_imports=["psycopg2", "os"])
def execute_sql(query: str) -> list:
    """Execute SQL statement and return a list of results."""
    conn_url = os.getenv("CONNECTION_URL")
    conn = psycopg2.connect(conn_url)
    with conn.cursor() as cursor:
        cursor.execute(
            query
        )
        res = cursor.fetchall()
        return res

# TODO:
# - include multiple seed prompts
# - aggregate and manage results, analysis, and instructions from all the seed prompts
# - 2nd order analysis from these resultant artifacts
# - a nice API also maybe?

executor = LocalCommandLineCodeExecutor(work_dir=work_dir, functions=[execute_sql])
seed_prompt = "Peak traffic time in the past 5 hours bucketed in 30 minute intervals"

SQL_AGENT_SYSTEM_PROMPT += executor.format_functions_for_prompt()

# SQL agent who's sole purpose is to write SQL queries and write python code to execute it (using the `execute_sql` function).
sql_agent = ConversableAgent(
    name="sql_agent",
    system_message=SQL_AGENT_SYSTEM_PROMPT,
    # set "cache_seed" to None to NOT use cached responses to same queries
    llm_config={"config_list": [{"model": "gpt-4o-2024-08-06", "api_key": os.getenv("OPENAI_API_KEY"), "price": [2.5, 10.0]}], "cache_seed": None},
    code_execution_config=False,
    human_input_mode="NEVER"
)

# a code executor agent, as the name indicates. no LLM is configured for this agent.
code_executor_agent = ConversableAgent(
    name="code_executor_agent",
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"), # is not called further when TERMINATE is recieved
    llm_config=False,
    code_execution_config={
        "executor": executor,
    },
    human_input_mode="NEVER",
)

# an analyst agent that gives "Analysis" and "Further Instructions" based on the output from the `sql_agent`'s query output.
analyst_agent = AssistantAgent(
    name="analyst_agent",
    system_message=ANALYST_AGENT_SYSTEM_PROMPT,
    llm_config={"config_list": [{"model": "gpt-4o-mini", "api_key": os.getenv("OPENAI_API_KEY"), "price": [0.15, 0.60]}]},
)

# TODO:
# - evaluate if this functions works as expected. expectation: take both the execution output (given by `code_executor_agent`)
#   and the response to the output (which also contains TERMINATE) by `sql_agent` as carryover to the `analyst_agent`
def custom_message(sender: ConversableAgent, recipient: ConversableAgent, context: dict) -> str | dict:
    carryover = context.get("carryover", "")
    if isinstance(carryover, list):
        carryover = '\n'.join(carryover[-3:])
    final_msg = "What do you think of the results? Do you find any peculiarity or anything that require further querying?" + "\nContext: \n" + carryover
    print("FINAL_MESSAGE: ", final_msg)
    return final_msg

# kicks off execution with the `code_executor_agent` calling `sql_agent` with the seed_prompt
# more info: https://microsoft.github.io/autogen/docs/tutorial/conversation-patterns#sequential-chats
# api-ref: https://microsoft.github.io/autogen/docs/reference/agentchat/conversable_agent#initiate_chats and #initiate_chat
chat_result = code_executor_agent.initiate_chats(
    [
        {
            "recipient": sql_agent,
            "message": seed_prompt,
            "clear_history": True,
            "silent": False,
            "max_turns": None, # indicates to wait till "TERMINATE" is sent by this agent
            "summary_method": "last_msg"
        },
        {
            "recipient": analyst_agent,
            "message": custom_message,
            "max_turns": 1,
            "summary_method": "last_msg",
        }
    ]
)
