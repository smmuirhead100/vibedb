# AGENTS.md - VibeDB Claude Agents SDK

## Project Overview

This project is **VibeDB** - a magic database that runs an AI agent under the hood on top of a postgres DB. Users just give it any form of random data and it just works!

## Project Structure

```
vibedb/
├── agents/
│   ├── core/                    # Core agent framework
│   │   ├── agent_with_tools.py  # Base agent class with tool support
│   │   ├── chat_context.py     # Chat message and role definitions
│   │   └── tools.py             # Tool decorator and Tool/ToolCall models
│   ├── builtins/                # Pre-built agent implementations
│   │   ├── agent_with_sql_tools.py  # SQL database agent
│   │   └── agent_with_bash.py       # Bash command execution agent
│   └── main.py                  # Example usage entry point
├── llms/
│   ├── llm.py                   # Abstract LLM base class
│   └── anthropic/               # Anthropic Claude implementation
│       ├── llm.py               # LLM implementation using Anthropic API
│       ├── models.py            # Supported Claude model enum
│       └── utils.py             # Message/tool conversion utilities
├── pyproject.toml               # Poetry dependencies
└── README.md
```

## Core Concepts

### 1. Agent Architecture

The framework is built around the `AgentWithTools` base class (`agents/core/agent_with_tools.py`):

- **Tool Discovery**: Automatically discovers methods decorated with `@tool` and exposes them to the LLM
- **Streaming**: Supports async streaming of both text responses and tool calls
- **Parallel Tool Execution**: Executes multiple tool calls in parallel when the LLM requests them
- **Conversation Management**: Maintains chat history with system instructions, user messages, assistant responses, and tool results

### 2. Tool System

Tools are defined using the `@tool` decorator from `agents/core/tools.py`:

```python
from agents.core.tools import tool

class MyAgent(AgentWithTools):
    @tool
    async def my_tool(self, param1: str, param2: int) -> str:
        """
        Tool description that the LLM sees.
        """
        # Tool implementation
        return "result"
```

**Key Points:**
- Tool methods must be `async`
- Method signature (parameter types) is automatically converted to a JSON schema
- Docstrings become the tool description for the LLM
- Tools are discovered via introspection of decorated methods

### 3. LLM Abstraction

The project uses an abstract `LLM` base class (`llms/llm.py`) with a concrete Anthropic implementation:

- **Base Interface**: `astream(messages, tools)` returns an async generator of `str | ToolCall`
- **Anthropic Implementation**: Uses `AsyncAnthropic` client, handles streaming, tool use blocks, and message conversion
- **Model Support**: Currently supports `claude-sonnet-4-5` (defined in `llms/anthropic/models.py`)

### 4. Chat Context

Chat messages are represented by `ChatMessage` objects with:
- **Role**: `USER`, `ASSISTANT`, or `SYSTEM`
- **Content**: Either a `str` or a `ToolCall` object

The system automatically manages the conversation flow:
1. User message → LLM
2. LLM response (text + tool calls) → Execute tools in parallel
3. Tool results → Add to conversation history
4. Continue until LLM provides final text response

## Built-in Agents

### AgentWithSQLTools

Located in `agents/builtins/agent_with_sql_tools.py`, this agent provides database interaction capabilities:

**Tools:**
- `execute_query(query: str)`: Execute any SQL query (SELECT, INSERT, UPDATE, DELETE, DDL)
- `list_tables()`: List all tables in the database
- `describe_table(table_name: str)`: Get schema information for a table
- `list_schemas()`: List all schemas in the database

**Usage:**
```python
from agents.builtins.agent_with_sql_tools import AgentWithSQLTools
from llms.anthropic.llm import LLM
from llms.anthropic.models import AnthropicLLMModel

llm = LLM(model=AnthropicLLMModel.CLAUDE_4_5_SONNET.value)
agent = AgentWithSQLTools(
    database_url="postgresql://localhost/dbname",
    llm=llm,
    instructions="Your agent instructions here"
)
```

**System Instructions**: The agent is configured as "Bob, NaturalSQL's official Agent" - a database assistant that helps users interact with databases using natural language.

### AgentWithBash

Located in `agents/builtins/agent_with_bash.py`, this agent can execute bash commands:

**Tools:**
- `execute_bash_command(command: str)`: Execute a bash command in an isolated temporary directory

**Safety Features:**
- Commands run in isolated temporary directories
- 30-second timeout on command execution
- Captures both stdout and stderr

## Usage Pattern

The typical usage pattern is:

```python
async def run():
    # 1. Initialize LLM
    llm = LLM(model=AnthropicLLMModel.CLAUDE_4_5_SONNET.value)
    
    # 2. Create agent with tools
    agent = AgentWithSQLTools(
        database_url="postgresql://...",
        llm=llm,
        instructions="System instructions"
    )
    
    # 3. Stream responses
    message = ChatMessage(role=ChatRole.USER, content="User query")
    async for chunk in agent.astream(chat_message=message):
        if isinstance(chunk, ToolCall):
            print(f"Tool call: {chunk}")
        else:
            print(chunk, end="", flush=True)
```

## Key Implementation Details

### Tool Call Execution Flow

1. LLM generates tool calls during streaming
2. Tool calls are collected as they're yielded
3. After streaming completes, all tool calls are executed in parallel using `asyncio.gather()`
4. Tool results are added to conversation history
5. The conversation continues with tool results available to the LLM

### Message Conversion

The Anthropic API requires specific message formats:
- System prompts are extracted separately
- Tool calls are converted to `ToolUseBlock` and `ToolResultBlock` pairs
- Multiple tool calls are batched into single assistant/user message pairs
- See `llms/anthropic/utils.py` for conversion logic

### Streaming Behavior

The LLM streams both:
- **Text chunks**: Regular string tokens as they're generated
- **ToolCall objects**: Complete tool call objects (with id, name, args) when the LLM decides to use tools

The agent yields both types interleaved during streaming, allowing real-time feedback.

## Dependencies

- **anthropic**: Anthropic SDK for Claude API
- **pydantic**: Data validation and schema generation
- **sqlalchemy**: Database connectivity (for SQL agent)
- **psycopg2-binary**: PostgreSQL driver
- **python-dotenv**: Environment variable management

## Environment Setup

The project requires:
- `ANTHROPIC_API_KEY` environment variable (loaded via `dotenv`)
- Python 3.13+
- Poetry for dependency management

## Creating Custom Agents

To create a custom agent:

1. Inherit from `AgentWithTools`
2. Pass `llm` and `instructions` to `super().__init__()`
3. Add `@tool` decorated methods for your custom tools
4. Implement tool methods as `async` functions

Example:
```python
from agents.core.agent_with_tools import AgentWithTools
from agents.core.tools import tool

class MyCustomAgent(AgentWithTools):
    def __init__(self, llm, instructions, custom_param):
        super().__init__(llm=llm, instructions=instructions)
        self.custom_param = custom_param
    
    @tool
    async def my_custom_tool(self, input_param: str) -> str:
        """Description of what this tool does."""
        # Implementation
        return f"Processed: {input_param}"
```

## Important Notes for AI Coding Agents

1. **Tool Discovery**: Tools are automatically discovered via the `@tool` decorator. Don't manually register tools.

2. **Async Everything**: All tool methods must be `async`. The framework uses `asyncio` for parallel execution.

3. **Type Hints Required**: Tool parameters must have type hints - these become the JSON schema for the LLM.

4. **Docstrings Matter**: Tool docstrings are the descriptions the LLM sees. Write clear, concise descriptions.

5. **Error Handling**: Tool methods should handle errors gracefully and return error messages as strings rather than raising exceptions.

6. **Conversation State**: The agent maintains conversation history automatically. Don't manually manage `_messages` unless necessary.

7. **Streaming**: Always use `async for` when consuming agent responses. The agent yields both text chunks and `ToolCall` objects.

8. **Database Connections**: For SQL agents, remember to dispose of the engine when done (see `main.py` example).

9. **Model Selection**: Currently only `claude-sonnet-4-5` is supported. Check `llms/anthropic/models.py` for available models.

10. **VibeDB Context**: This SDK is specifically for the VibeDB product. When adding features or making changes, consider how they fit into VibeDB's use cases.

## Common Tasks

### Adding a New Tool to an Existing Agent

1. Add a new `@tool` decorated method to the agent class
2. Ensure it's `async` and has type hints
3. Add a descriptive docstring
4. The tool will be automatically available to the LLM

### Creating a New Agent Type

1. Create a new file in `agents/builtins/` or appropriate location
2. Inherit from `AgentWithTools`
3. Add your custom tools with `@tool` decorator
4. Initialize any required resources in `__init__`

### Adding Support for a New LLM Provider

1. Create a new implementation in `llms/{provider}/`
2. Implement the `LLM` abstract base class
3. Handle message/tool conversion for that provider's API
4. Update model enums if needed

## Testing

The main entry point (`agents/main.py`) provides an interactive chat interface for testing SQL agents. Modify the database URL and run:

```bash
python -m agents.main
```

## Future Considerations

- Support for additional LLM providers (OpenAI, etc.)
- More built-in agent types
- Tool result caching
- Conversation persistence
- Multi-turn tool execution with follow-up queries
