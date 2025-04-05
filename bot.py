import asyncio
import logging
from os import environ
from typing import Union, Optional, AsyncGenerator
from flask import Flask
from pyrogram import Client, idle, types, filters
from database import Database

# Khởi tạo Flask app
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello from Forward Bot'

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Cấu hình bot
class Config:
    API_ID = int(environ.get("API_ID", "YOUR_API_ID"))  # Thay bằng API_ID của bạn
    API_HASH = environ.get("API_HASH", "YOUR_API_HASH")  # Thay bằng API_HASH
    BOT_TOKEN = environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")  # Thay bằng BOT_TOKEN
    BOT_SESSION = environ.get("BOT_SESSION", "AutoForwardBot")
    DATABASE_URI = environ.get("DATABASE_URI", "mongodb+srv://your_username:your_password@cluster0.mongodb.net/?retryWrites=true&w=majority")
    DATABASE_NAME = environ.get("DATABASE_NAME", "AutoForwardBotDB")
    BOT_OWNER = int(environ.get("BOT_OWNER", "YOUR_USER_ID"))  # Thay bằng ID Telegram của bạn

# Quản lý trạng thái tạm thời
class Temp:
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []

# Kết nối MongoDB
db = Database(Config.DATABASE_URI, Config.DATABASE_NAME)

# Khởi tạo bot
bot = Client(
    Config.BOT_SESSION,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    sleep_threshold=120
)

# Danh sách userbots
userbots = []

# Văn bản giao diện
class Script:
    START_TXT = """<b>ʜɪ {}
  
ɪ'ᴍ ᴀɴ ᴀᴅᴠᴀɴᴄᴇᴅ ꜰᴏʀᴡᴀʀᴅ ʙᴏᴛ
ɪ ᴄᴀɴ ꜰᴏʀᴡᴀʀᴅ ᴀʟʟ ᴍᴇssᴀɢᴇs ꜰʀᴏᴍ ᴍᴜʟᴛɪᴘʟᴇ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴍᴜʟᴛɪᴘʟᴇ ᴄʜᴀɴɴᴇʟs</b>

**ᴄʟɪᴄᴋ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴋɴᴏᴡ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ᴍᴇ**"""
    
    HELP_TXT = """<b><u>🔆 Help</b></u>

<u>**📚 Available commands:**</u>
<b>⏣ __/start - check I'm alive__ 
⏣ __/help - show this help__
⏣ __/forward - forward messages (usage: /forward [source_chats] [target_chats])__
⏣ __/adduserbot - add a userbot (usage: /adduserbot [user_id] [session_string])__
⏣ __/stop - stop forwarding__</b>

<b><u>💢 Features:</b></u>
<b>► __Forward messages from multiple sources to multiple targets__
► __Support multiple user accounts__
► __Auto-forward with configurable sources and targets__</b>"""

# Hàm hỗ trợ iter_messages
async def iter_messages(client, chat_id: Union[int, str], limit: int, offset: int = 0) -> Optional[AsyncGenerator[types.Message, None]]:
    current = offset
    while True:
        new_diff = min(200, limit - current)
        if new_diff <= 0:
            return
        messages = await client.get_messages(chat_id, list(range(current, current + new_diff + 1)))
        for message in messages:
            yield message
            current += 1

# Tự động forward tin nhắn từ nhiều nguồn đến nhiều đích
async def auto_forward(userbot, user_id):
    details = await db.get_forward_details(user_id)
    source_chats = details["source_chats"]
    target_chats = details["target_chats"]
    last_ids = details.get("last_id", {})

    if not source_chats or not target_chats:
        return

    for source in source_chats:
        async for message in iter_messages(userbot, source, limit=1000000, offset=last_ids.get(str(source), 0)):
            try:
                for target in target_chats:
                    await userbot.forward_messages(target, message)
                    logger.info(f"Forwarded message {message.id} from {source} to {target}")
                Temp.forwardings += 1
                last_ids[str(source)] = message.id
                await db.update_forward(userbot.session_name, {
                    "source_chats": source_chats,
                    "target_chats": target_chats,
                    "last_id": last_ids,
                    "fetched": Temp.forwardings
                })
                await asyncio.sleep(1)  # Tránh giới hạn Telegram
            except Exception as e:
                logger.error(f"Error forwarding message: {e}")

# Xử lý lệnh
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply(Script.START_TXT.format(message.from_user.first_name))

@bot.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    await message.reply(Script.HELP_TXT)

@bot.on_message(filters.command("forward") & filters.private & filters.user(Config.BOT_OWNER))
async def forward_command(client, message):
    if len(message.command) < 3:
        await message.reply("Usage: /forward [source_chat_ids] [target_chat_ids]\nExample: /forward -100123456789,-100123456790 -100987654321")
        return
    
    try:
        source_chats = [int(chat_id) for chat_id in message.command[1].split(",")]
        target_chats = [int(chat_id) for chat_id in message.command[2].split(",")]
        await db.add_forward_config(message.from_user.id, source_chats, target_chats)
        await message.reply(f"Forward configured: {source_chats} -> {target_chats}")
    except ValueError:
        await message.reply("Invalid chat IDs. Use format: /forward -100123456789,-100123456790 -100987654321")

@bot.on_message(filters.command("adduserbot") & filters.private & filters.user(Config.BOT_OWNER))
async def add_userbot_command(client, message):
    if len(message.command) < 3:
        await message.reply("Usage: /adduserbot [user_id] [session_string]\nExample: /adduserbot 123456789 1BVtsO...")
        return
    
    try:
        user_id = int(message.command[1])
        session_string = message.command[2]
        await db.add_userbot(user_id, session_string)
        await message.reply(f"Userbot {user_id} added successfully!")
        
        # Khởi động userbot ngay lập tức
        client = Client(f"session_{user_id}", session_string=session_string, api_id=Config.API_ID, api_hash=Config.API_HASH)
        await client.start()
        userbots.append(client)
        asyncio.create_task(auto_forward(client, user_id))
        logger.info(f"Userbot {user_id} started")
    except ValueError:
        await message.reply("Invalid user ID. Use format: /adduserbot 123456789 1BVtsO...")

@bot.on_message(filters.command("stop") & filters.private & filters.user(Config.BOT_OWNER))
async def stop_command(client, message):
    await db.update_forward(message.from_user.id, {"source_chats": [], "target_chats": [], "last_id": {}, "fetched": Temp.forwardings})
    await message.reply("Forwarding stopped.")

# Khởi động bot và userbots
async def main():
    # Khởi động bot chính
    await bot.start()
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")

    # Đăng nhập userbots từ DB
    async for ubot in db.get_userbots():
        client = Client(f"session_{ubot['user_id']}", session_string=ubot["session"], api_id=Config.API_ID, api_hash=Config.API_HASH)
        await client.start()
        userbots.append(client)
        logger.info(f"Userbot {ubot['user_id']} started")
        asyncio.create_task(auto_forward(client, ubot["user_id"]))

    # Giữ bot chạy
    await idle()

if __name__ == "__main__":
    # Chạy Flask trong thread riêng
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))).start()

    # Chạy bot
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
