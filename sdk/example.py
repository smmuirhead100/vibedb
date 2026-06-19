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

    # await client.execute("New Event: new user signed up with first name 'Bob' and last name 'Test'. Phone number is 555-555-5555.")
    # await client.execute("Sean Muirhead changed their phone number from 555-555-1234 to 555-555-5555")
    # await client.execute("Add these colors of shoes: red, green, blue")
    # await client.execute("New Event: new user signed up with first name 'Bob' and last name 'Test'. No phone number.")
    # await client.execute("New Event: Bob Test just added an email to their account: bob@bobby.com")

    # # 2. Create a new client and query the data
    # client_2 = Client()
    # users = await client_2.execute("Get all users who've signed up in the past day.")
    # print("Users: ", users)

    # colors = await client_2.execute("Get all colors of shoes.")
    # print("Colors: ", colors)

    # 3. Query and cast the data
    # client.execute("Get all users who've signed up in the past day", User)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
