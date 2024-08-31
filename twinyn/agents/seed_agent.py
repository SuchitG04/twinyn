import re
from typing import Callable

import twinyn.agents.prompts as prompts

from autogen import AssistantAgent, ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor
from autogen import ChatResult

class SeedTask:
    def __init__(
        self,
        executor: LocalCommandLineCodeExecutor,
        llm_config_sqlagent: dict,
        llm_config_analystagent: dict,
        custom_msg_fn: Callable[[any, any, dict], str | dict],
        seed_prompt: str,
        sql_agent_sys_prompt: str | None = None,
        analyst_agent_sys_prompt: str | None = None,
    ):
        self.executor = executor
        self.llm_config_sqlagent = llm_config_sqlagent
        self.llm_config_analystagent = llm_config_analystagent
        self.custom_msg_fn = custom_msg_fn
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

    def kickoff(self):
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
                    "message": self.custom_msg_fn,
                    "max_turns": 1,
                    "summary_method": "last_msg",
                }
            ]
        )


class SeedOutput:
    def __init__(self, agent_output: list[ChatResult]):
        self.agent_output = agent_output
        self.seed_prompt: str = None
        self.code_res_msg: str = None
        self.analysis_msg: str = None
        self.parsed_instructions: list[str] = None

    def __exclude_terminate_word(self, msg: str):
        return '\n'.join(msg.strip().split('\n')[:-1])

    def _collect_msgs(self):
        code_res = self.agent_output[0].chat_history[-2:]
        self.code_res_msg = code_res[0]['content'] + "\n" + code_res[1]['content']
        self.code_res_msg = self.__exclude_terminate_word(self.code_res_msg)

        analysis = self.agent_output[1].chat_history[-1]['content']
        self.analysis_msg = self.__exclude_terminate_word(analysis)

    def _parse_instructions(self):
        pattern = r'\d+\.\s+([^\n]+(?:\n(?!\d+\.).*)*)'
        instructions = re.findall(pattern, self.analysis_msg, re.DOTALL)
        self.parsed_instructions = [instr.strip() for instr in instructions]

    def collect(self):
        self.seed_prompt = self.agent_output[0].chat_history[0]['content']
        self._collect_msgs()
        self._parse_instructions()
