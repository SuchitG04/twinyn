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
        seed_prompt: str,
        sql_agent_sys_prompt: str | None = None,
        analyst_agent_sys_prompt: str | None = None,
    ):
        self.executor = executor
        self.llm_config_sqlagent = llm_config_sqlagent
        self.llm_config_analystagent = llm_config_analystagent
        self.seed_prompt = seed_prompt

        self.chat_result = None

        if sql_agent_sys_prompt is None:
            self.SQL_AGENT_SYSTEM_PROMPT = prompts.SQL_AGENT_SYSTEM_PROMPT
        else:
            self.SQL_AGENT_SYSTEM_PROMPT = sql_agent_sys_prompt

        if analyst_agent_sys_prompt is None:
            self.ANALYST_AGENT_SYSTEM_PROMPT = prompts.ANALYST_AGENT_SYSTEM_PROMPT
        else:
            self.ANALYST_AGENT_SYSTEM_PROMPT = analyst_agent_sys_prompt

        self.SQL_AGENT_SYSTEM_PROMPT += self.executor.format_functions_for_prompt()
        self.sql_agent = ConversableAgent(
            name="sql_agent",
            system_message=self.SQL_AGENT_SYSTEM_PROMPT,
            llm_config=self.llm_config_sqlagent,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        self.code_executor_agent = ConversableAgent(
            name="code_executor_agent",
            # is not called further when TERMINATE is recieved
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
            llm_config=False,
            code_execution_config={
                "executor": self.executor,
            },
            human_input_mode="NEVER",
        )
        self.analyst_agent = AssistantAgent(
            name="analyst_agent",
            system_message=self.ANALYST_AGENT_SYSTEM_PROMPT,
            llm_config=self.llm_config_analystagent,
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
        self.chat_result = self.code_executor_agent.initiate_chats(
            [
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
                }
            ]
        )


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

    def __exclude_terminate_word(self, msg: str):
        """Excludes any 'TERMINATE' signals included in the output by agents."""
        return '\n'.join(msg.strip().split('\n')[:-1])

    def __list_instructions(self, msg: str):
        """Takes an input string having numbered points and return the points without the numbers."""
        pattern = r'\d+\.\s+([^\n]+)'
        instructions = re.findall(pattern, msg, re.DOTALL)
        return [i.strip() for i in instructions]

    def _collect_msgs(self):
        """Collects relevant messages from the agents and store it in appropriate variables."""
        code_res = self.agent_output[0].chat_history[-2:]
        self.code_res_msg = code_res[0]['content'] + "\n" + code_res[1]['content']
        self.code_res_msg = self.code_res_msg.replace("TERMINATE", "")

        analysis_instr_msg = self.agent_output[1].chat_history[-1]['content']
        analysis_instr_msg = analysis_instr_msg.replace("TERMINATE", "").strip()
        analysis_instr_msg = json.loads(analysis_instr_msg)
        self.analysis_msg = analysis_instr_msg["analysis"]
        self.parsed_instructions = analysis_instr_msg["further_instructions"]

    def collect(self):
        """Wrapper function to collect the seed prompt, code execution message, analysis message and instructions."""
        self.seed_prompt = self.agent_output[0].chat_history[0]['content']
        self._collect_msgs()
