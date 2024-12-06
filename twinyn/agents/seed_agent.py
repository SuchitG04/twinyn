import re
import json
import textwrap
from typing import Callable
from textwrap import dedent

import agents.prompts as prompts

from autogen import AssistantAgent, ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor
from autogen import ChatResult

class SeedTask:
    """
    SeedTask configures the SQL and Analyst agents, and initiates the conversation between them given a seed prompt.

    Attributes:
        executor (LocalCommandLineCodeExecutor): An executor configured to execute code in the directory of your choice.
        llm_config_sqlagent (dict): LLM configuration for the SQL agent.
        llm_config_analystagent (dict): LLM configuration for the Analyst agent.
        seed_prompt (str): The seed prompt that kicks of the conversation.
        sql_agent_sys_prompt (str, optional): The system prompt for the SQL agent. Prompt from `twinyn.agents.prompts`
        is used if not provided.
        analyst_agent_sys_prompt (str, optional): The system prompt for the Analyst agent. Prompt from `twinyn.agents.prompts`
        is used if not provided.
    """

    def __init__(
        self,
        executor: LocalCommandLineCodeExecutor,
        llm_config_sqlagent: dict,
        llm_config_analystagent: dict,
        llm_config_instructionsagent: dict,
        seed_prompt: str,
        branching_factor: int,
    ):
        self.executor = executor
        self.llm_config_sqlagent = llm_config_sqlagent
        self.llm_config_analystagent = llm_config_analystagent
        self.llm_config_instructionsagent = llm_config_instructionsagent
        self.seed_prompt = seed_prompt
        self.branching_factor = branching_factor

        self.chat_result = None

        self.sql_agent = ConversableAgent(
            name="sql_agent",
            system_message=prompts.SQL_AGENT_SYSTEM_PROMPT + self.executor.format_functions_for_prompt(),
            is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", ""), # x.get("content", "").rstrip().endswith("TERMINATE"),
            llm_config=self.llm_config_sqlagent,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        self.code_executor_agent = ConversableAgent(
            name="code_executor_agent",
            is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", ""), # x.get("content", "").rstrip().endswith("TERMINATE"),
            llm_config=False,
            code_execution_config={
                "executor": self.executor,
            },
            human_input_mode="NEVER",
        )
        self.analyst_agent = ConversableAgent(
            name="analyst_agent",
            system_message=prompts.ANALYST_AGENT_SYSTEM_PROMPT,
            llm_config=self.llm_config_analystagent,
            code_execution_config=False,
            human_input_mode="NEVER",
        )
        self.instructions_agent = ConversableAgent(
            name="instructions_agent",
            system_message=prompts.INSTRUCTIONS_AGENT_SYSTEM_PROMPT.format(branching_factor=self.branching_factor),
            llm_config=self.llm_config_instructionsagent,
            code_execution_config=False,
            human_input_mode="NEVER",
        )

    def _build_analyst_prompt(self, sender: ConversableAgent, recipient: ConversableAgent, context: dict) -> str:
        """Builds a custom prompt for the analyst agent using the seed prompt and the execution result."""
        query = self.seed_prompt
        result = context.get("carryover", "")
        prompt = f"""\
            Query:
            {query}
            
            Result:
            {result}
        """
        return textwrap.dedent(prompt)

    def kickoff(self):
        """Kicks off the conversation between the agents."""
        chat_queue = [
                {
                    "recipient": self.sql_agent,
                    "message": self.seed_prompt,
                    "clear_history": True,
                    "silent": False,
                    "max_turns": None,  # indicates to wait till "TERMINATE" is sent by this agent
                    "summary_method": "last_msg"
                },
                {
                    "recipient": self.analyst_agent,
                    "message": self._build_analyst_prompt,
                    "max_turns": 1,
                    "summary_method": "last_msg",
                },
        ]
        if self.branching_factor > 0:
            chat_queue.append(
                {
                    "recipient": self.instructions_agent,
                    "max_turns": 1,
                    "summary_method": "last_msg",
                }
            )
        try:
            self.chat_result = self.code_executor_agent.initiate_chats(chat_queue)
        except Exception as e:
            print("Exception: ", e)
            print(chat_queue)
            raise


class SeedOutput:
    """
    SeedOutput holds the agent's output, collects relevant parts of the conversation into class variables.

    Attributes:
        agent_output (list[ChatResult]): A list of `ChatResult` objects having conversation history of one agentic conversation.
        seed_prompt (str): The seed prompt used to start the conversation.
        code_res_msg (str): The execution results of the SQL query.
        analysis_msg (str): The analysis generated based on the execution results of the SQL query.
        parsed_instructions (list[str]): A list of further instructions to be sent to the SQL agent.
    """

    def __init__(self, agent_output: list[ChatResult]):
        self.agent_output = agent_output
        self.seed_prompt: str = None
        self.code_res_msg: str = None
        self.analysis_msg: str = None
        self.parsed_instructions: list[str] = None

    def _collect_msgs(self):
        """Collects relevant messages from the agents and store it in appropriate variables."""
        code_res = self.agent_output[0].chat_history[-2:]
        self.code_res_msg = code_res[0]['content'] + "\n" + code_res[1]['content']
        self.code_res_msg = self.code_res_msg.replace("TERMINATE", "")

        self.analysis_msg = self.agent_output[1].chat_history[-1]['content']

        self.parsed_instructions = self.agent_output[2].chat_history[-1]['content']
        self.parsed_instructions = json.loads(self.parsed_instructions)["instructions"]

    def collect(self):
        """Wrapper function to collect the seed prompt, code execution message, analysis message and instructions."""
        self.seed_prompt = self.agent_output[0].chat_history[0]['content']
        self._collect_msgs()
