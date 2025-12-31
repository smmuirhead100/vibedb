import asyncio
from agents.builtins.agent_with_sql_tools import AgentWithSQLTools, INSTRUCTIONS
from agents.core.chat_context import ChatMessage, ChatRole
from agents.core.tools import ToolCall
from llms.gemini.models import GeminiLLMModel
from llms.gemini.llm import LLM as GeminiLLM


async def run():
    llm = GeminiLLM(model=GeminiLLMModel.GEMINI_3_FLASH_PREVIEW)
    # Update this connection string to match your local PostgreSQL instance
    database_url = "postgresql://localhost/alcatraz"
    agent = AgentWithSQLTools(
        database_url=database_url,
        llm=llm,
        instructions=INSTRUCTIONS
    )

    print("Chat with the SQL agent! Type 'exit' or 'quit' to end the conversation.\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break

            message = ChatMessage(role=ChatRole.USER, content=user_input)

            print("Agent: ", end="", flush=True)
            assistant_content_parts: list[str] = []
            tool_calls: list[ToolCall] = []
            async for chunk in agent.astream(chat_message=message):
                if isinstance(chunk, ToolCall):
                    tool_calls.append(chunk)
                    print(f"Tool call: {chunk}")
                else:
                    print(chunk, end="", flush=True)
                    assistant_content_parts.append(chunk)
            print()
    finally:
        # Close database connections
        if hasattr(agent, 'engine'):
            agent.engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
