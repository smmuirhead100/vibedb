from anthropic import types as anthropic_types
from agents.chat_context import ChatMessage, ChatRole
from agents.tools import Tool, ToolCall


def chat_messages_to_anthropic_system_and_messages(messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
    system_prompt = next((m.content for m in messages if m.role == ChatRole.SYSTEM), None)
    if not system_prompt:
        raise ValueError("No system prompt found!")

    anthropic_messages = []
    for msg in messages:
        role = "assistant" if msg.role == ChatRole.ASSISTANT else "user"
        if isinstance(msg.content, str):
            anthropic_messages.append(anthropic_types.MessageParam(role=role, content=msg.content))
        elif isinstance(msg.content, ToolCall):
            tool_call = msg.content
            anthropic_messages.append(anthropic_types.ToolUseBlockParam(
                id=tool_call.id,
                input=tool_call.args,
                name=tool_call.tool.name,
            ))
            anthropic_messages.append(anthropic_types.ToolResultBlockParam(
                tool_use_id=tool_call.id,
                content=tool_call.response,
                is_error=False,
            ))
        else:
            raise ValueError(f"Unknown message type: {msg}")

    return system_prompt, anthropic_messages


def tool_to_anthropic_tool(tool: Tool) -> anthropic_types.ToolParam:
    return anthropic_types.ToolParam(
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema.model_json_schema(),
    )


def anthropic_chunk_to_str_or_tool_call(chunk: anthropic_types.RawMessageStreamEvent) -> str | ToolCall | None:
    if isinstance(chunk, anthropic_types.RawContentBlockDeltaEvent):
        return chunk.delta.text
    elif isinstance(chunk, anthropic_types.InputJSONDelta):
        return chunk.partial_json
    return None
