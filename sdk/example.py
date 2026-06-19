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
    # 1. Instantiate the client
    client = await Client.create(database_url=DB_URL)
   
    # 2. Collect write some data
    await client.execute("New Event: new user signed up with first name 'Bob' and last name 'Test'. Phone number is 555-555-5555.")
    await client.execute("New Event: new user signed up with first name 'John' and last name 'Doe'. Phone number is 555-555-5556.")
    await client.execute("New Event: new user signed up with first name 'Jane' and last name 'Smith'. Phone number is 555-555-5557.")

    # 3. Query the data
    users = await client.execute("Get last 3 users created in descending order by created_at", return_as=List[User])
    print(f"Users: {users}")

    # 4. Query the data again (should be cached)
    users_again = await client.execute("Get last 1 users created in descending order by created_at", return_as=List[User])
    print(f"Users again: {users_again}")

    # 5. Dispose the client
    await client.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
