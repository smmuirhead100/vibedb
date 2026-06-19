from pydantic import BaseModel
from typing import List
from sdk.client import Client


DB_URL = "postgresql://localhost/alcatraz"


class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str


async def run():
    # 1. Instantiate the client and send some data
    client = await Client.create(database_url=DB_URL)
    # await client.execute("Make sure no duplicate users are created from here on out.")
    users = await client.execute("Get last 3 users created in descending order by created_at", return_as=List[User])
    print(f"Users: {users}")
    
    # This one should be really fast because it is cached.
    users_again = await client.execute("Get last 1 users created in descending order by created_at", return_as=List[User])
    print(f"Users again: {users_again}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
