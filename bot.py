import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient, events
import config

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot)

# Khởi tạo danh sách tài khoản người dùng Telethon
clients = []

async def start_clients():
    for user in config.USER_ACCOUNTS:
        client = TelegramClient(user["session"], config.API_ID, config.API_HASH)
        await client.start(phone=user["phone"])
        clients.append(client)
        print(f"✅ Đã đăng nhập: {user['phone']}")

# Xử lý nút menu
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🚀 Boost Performance", callback_data="boost"),
        InlineKeyboardButton("🔔 Alert: Chat Access Error", callback_data="alert"),
        InlineKeyboardButton("🌍 Language", callback_data="language"),
        InlineKeyboardButton("🔄 Restart BOT", callback_data="restart"),
        InlineKeyboardButton("❌ Disconnect", callback_data="disconnect"),
    )
    await message.reply("🔹 **Bot Forwarding System** 🔹\nChọn tính năng bên dưới:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "restart")
async def restart_bot(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("🔄 Bot đang khởi động lại...")
    await asyncio.sleep(2)
    await send_welcome(callback_query.message)

# Xử lý chuyển tiếp tin nhắn từ kênh nguồn đến mục tiêu
async def forward_messages(client):
    @client.on(events.NewMessage(chats=config.SOURCE_CHAT_IDS))
    async def handler(event):
        for target in config.TARGET_CHAT_IDS:
            await client.send_message(target, event.message)

# Chạy bot
async def main():
    await start_clients()
    for client in clients:
        client.loop.create_task(forward_messages(client))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
