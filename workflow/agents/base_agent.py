from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from typing import List

class BaseAgent:
    def __init__(self, system_prompt: str, tools: List, verbose: bool = True):
        AOAI_ENDPOINT = "https://YOUR_AZURE_OPENAI_ENDPOINT"
        AOAI_DEPLOY_GPT4O_MINI = "YOUR_DEPLOYMENT_NAME"
        AOAI_API_KEY = "YOUR_API_KEY"

        self.llm = AzureChatOpenAI(
            azure_endpoint=AOAI_ENDPOINT,
            azure_deployment=AOAI_DEPLOY_GPT4O_MINI,
            api_version="2024-10-21",
            api_key=AOAI_API_KEY
        )

        self.tools = tools

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ]
        )

        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)

        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=verbose,
            max_iterations=10,
            max_execution_time=10,
            handle_parsing_errors=True,
        )

    def run(self, user_input: str):
        result = self.executor.invoke({"input": user_input})
        return result["output"]
