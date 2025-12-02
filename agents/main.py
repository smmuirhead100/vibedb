import asyncio
from agents.core.agent_with_tools import AgentWithTools, AgentWithToolsOptions
from agents.core.chat_context import ChatMessage, ChatRole
from agents.core.tools import ToolCall
from llms.anthropic.models import AnthropicLLMModel
from llms.anthropic.llm import LLM


async def run():
    llm = LLM(model=AnthropicLLMModel.CLAUDE_4_5_SONNET.value)
    options = AgentWithToolsOptions(llm=llm, tools=[])
    agent = AgentWithTools(options=options)

    # Initialize messages with system message
    messages: list[ChatMessage] = [ChatMessage(role=ChatRole.SYSTEM, content="Testing")]

    print("Chat with the agent! Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # Add user message to history
        messages.append(ChatMessage(role=ChatRole.USER, content=user_input))

        # Stream agent response
        print("Agent: ", end="", flush=True)
        assistant_content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        async for chunk in agent.astream(messages=messages):
            if isinstance(chunk, ToolCall):
                tool_calls.append(chunk)
            else:
                print(chunk, end="", flush=True)
                assistant_content_parts.append(chunk)
        print()

        # Add assistant response to history
        assistant_content = "".join(assistant_content_parts)
        assistant_message = ChatMessage(role=ChatRole.ASSISTANT, content=assistant_content)
        messages.append(assistant_message)


if __name__ == "__main__":
    asyncio.run(run())
