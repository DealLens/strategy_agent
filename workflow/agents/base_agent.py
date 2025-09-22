from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from typing import List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BaseAgent:
    def __init__(self, system_prompt: str, tools: List, verbose: bool = True):
        # Try Azure OpenAI first, fallback to OpenAI
        try:
            if os.getenv("AOAI_API_KEY") and os.getenv("AOAI_ENDPOINT"):
                self.llm = AzureChatOpenAI(
                    azure_endpoint=os.getenv("AOAI_ENDPOINT"),
                    azure_deployment=os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o"),
                    api_version=os.getenv("AOAI_API_VERSION", "2024-10-21"),
                    api_key=os.getenv("AOAI_API_KEY"),
                    temperature=0.7
                )
            else:
                # Fallback to OpenAI
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=os.getenv("OPENAI_API_KEY"),
                    temperature=0.7
                )
        except Exception as e:
            # If no API keys are available, use a mock LLM for development
            print(f"Warning: No valid API keys found. Using mock LLM. Error: {e}")
            self.llm = None

        self.tools = tools
        self.system_prompt = system_prompt

        if self.llm is not None:
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
        else:
            self.executor = None

    def run(self, user_input: str):
        if self.executor is not None:
            result = self.executor.invoke({"input": user_input})
            return result["output"]
        else:
            # Mock response for development
            return f"[Mock Response] {self.system_prompt}\n\nUser Input: {user_input}\n\nThis is a mock response. Please configure your API keys in the .env file to get real responses."
