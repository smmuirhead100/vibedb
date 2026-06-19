# vibedb

VibeDB lets you read and write to a database in plain English. You describe what you
want, an LLM agent inspects your live schema, writes and runs the SQL, and hands the
result back as a typed object.

Repeated requests are cached: after handling a query, the agent saves a reusable handler
keyed by a natural-language template, so the next matching request runs directly against
the database with no LLM call.

> ⚠️ Experimental. The agent generates and executes SQL and cached handlers run
> generated Python against your database with no sandboxing. Don't point it at
> anything you care about!

## Install

```bash
git clone https://github.com/<you>/vibedb.git
cd vibedb
uv sync
```

Requires Python 3.13+ and a running PostgreSQL database.

## Setup

Copy the example env file and fill it in:

```bash
cp .env.example .env
```

```dotenv
DATABASE_URL=postgresql://localhost/your_db
GEMINI_API_KEY=your_key_here
```

VibeDB uses Gemini by default, so a `GEMINI_API_KEY` is required.

## Usage

```python
from typing import List

from pydantic import BaseModel

from sdk.client import Client

DB_URL = "postgresql://localhost/your_db"


class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str


async def run():
    # Instantiate the client
    client = await Client.create(database_url=DB_URL)

    # Write data in plain English
    await client.execute(
        "New Event: new user signed up with first name 'Bob' and last name 'Test'. "
        "Phone number is 555-555-5555."
    )

    # Read it back, cast into your own model
    users = await client.execute(
        "Get last 3 users created in descending order by created_at",
        return_as=List[User],
    )
    print(f"Users: {users}")

    # Clean up
    await client.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

A runnable version of this lives in [`sdk/example.py`](sdk/example.py).

### How it works

- `Client.execute(query)` checks the query cache first. On a miss, it hands the request
  to an LLM agent.
- The agent sees an overview of your schema, writes SQL, runs it via an `execute_query`
  tool, and (when you pass `return_as`) casts the rows into your model.
- After a successful request the agent may cache a reusable handler keyed by a
  natural-language template (e.g. `Get user with id {id}`). Future messages that match the
  template skip the LLM and run the handler directly.

### TODO
- [x] Support Postgres
- [x] Agent-based query execution
- [x] Query caching
- [x] Schema casting (Pydantic models)
- [ ] Schema casting for Python built-ins
- [ ] Add CLI
- [ ] Support SQLite
- [ ] Schema updates automatically posted to pypi
- [ ] Automatic query optimization
- [ ] Support multiple databases under one client (e.g. route ILIKE-heavy workloads to a vector DB)
- [ ] CI / CD pipeline
- [ ] Poor Practice Detection (N+1s, etc.)
- [ ] Distribute the query cache to multiple clients
