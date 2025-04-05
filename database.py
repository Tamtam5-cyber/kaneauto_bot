import motor.motor_asyncio

class Database:
    def __init__(self, uri, db_name):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.users = self.db.users
        self.userbots = self.db.userbots
        self.forwards = self.db.forwards

    async def add_userbot(self, user_id, session_string):
        if not await self.is_userbot_exist(user_id):
            await self.userbots.insert_one({"user_id": user_id, "session": session_string})

    async def is_userbot_exist(self, user_id):
        return bool(await self.userbots.find_one({"user_id": user_id}))

    async def get_userbots(self):
        return [bot async for bot in self.userbots.find({})]

    async def update_forward(self, user_id, details):
        await self.forwards.update_one({"user_id": user_id}, {"$set": {"details": details}}, upsert=True)

    async def get_forward_details(self, user_id):
        default = {"source_chats": [], "target_chats": [], "last_id": {}, "fetched": 0}
        user = await self.forwards.find_one({"user_id": user_id})
        return user.get("details", default) if user else default

    async def add_forward_config(self, user_id, source_chats, target_chats):
        details = await self.get_forward_details(user_id)
        details["source_chats"] = list(set(details["source_chats"] + source_chats))
        details["target_chats"] = list(set(details["target_chats"] + target_chats))
        await self.update_forward(user_id, details)
