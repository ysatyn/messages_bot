import html
from typing import List

from db.database import get_async_db

from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_handler_backends import State

def escape_html(text: str) -> str:
    escaped_text = html.escape(text, quote=True)
    escaped_text_for_telegram = escaped_text.replace('|', '&#124;')
    return escaped_text_for_telegram


def create_user_link(user_id: int, user_name: str, username: str | None = None) -> str:
    user_name = escape_html(user_name)
    link_html = f"<a href='tg://user?id={user_id}'>{user_name}</a>"

    return link_html
    

def db_handler(handler_func):
    async def wrapper(*args, **kwargs):
        session = await anext(get_async_db())
        try:
            return await handler_func(*args, db=session, **kwargs)
        finally:
            await session.close()
    return wrapper


def create_state_filter(required_state: State, bot_instance: AsyncTeleBot):
    async def state_checker(message: types.Message):
        current_state = await bot_instance.get_state(message.from_user.id, message.chat.id)
        return current_state == required_state.name
    return state_checker


async def update_data(bot: AsyncTeleBot, tg_user_id: int, tg_chat_id: int, **kwargs):
    async with bot.retrieve_data(tg_user_id, tg_chat_id) as data:
        data.update(kwargs)

async def get_data(bot: AsyncTeleBot, tg_user_id: int, tg_chat_id: int, key: str) -> object:
    async with bot.retrieve_data(tg_user_id, tg_chat_id) as data:
        return data.get(key)
