from telebot.async_telebot import AsyncTeleBot 
from db.database import get_async_db
from db import crud

from config import ADMIN_ID, COST

from sqlalchemy.ext.asyncio import AsyncSession
from telebot import types

from bot.utils import escape_html, create_user_link, db_handler, create_state_filter, update_data, get_data

from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_handler_backends import State, StatesGroup

class NoteStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_note_text = State()
    waiting_for_update_note_text = State()
    waiting_for_unread_quantity = State()

def check_state(state: State):
    pass

async def debug_state(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    state = await bot.get_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, f"Ваше текущее состояние: {state}")


async def start_note_creation(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    user = await crud.create_or_update_user(
        db,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    await bot.set_state(message.from_user.id, NoteStates.waiting_for_user_id, message.chat.id)
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    request_user_button = types.KeyboardButton(
        text="Отправить пользователя",
        request_user=types.KeyboardButtonRequestUser(request_id=1, user_is_bot=False),
    )
    keyboard.add(request_user_button)

    await bot.send_message(message.chat.id, "👤 Отправьте пользователя кнопкой ниже или введите его ID вручную:", reply_markup=keyboard)


async def process_user_id(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    print(f"process_user_id вызван! user_id={message.from_user.id}, chat_id={message.chat.id}, text={message.text}")
    state = await bot.get_state(message.from_user.id, message.chat.id)
    print(f"Текущее состояние пользователя: {state}")
    user_id_text = message.text.strip()
    if not user_id_text.isdigit():
        await bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректный числовой ID пользователя.")
        return
    await bot.set_state(message.from_user.id, NoteStates.waiting_for_note_text, message.chat.id)
    await bot.send_message(message.chat.id, "Теперь введите текст послания:", reply_markup=types.ReplyKeyboardRemove())
    await update_data(bot, message.from_user.id, message.chat.id, user_id=int(user_id_text))


async def process_note_text(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as state_data:
        for_user_id = state_data.get("user_id")

    note_text = message.text.strip()
    note = await crud.create_note(
        db,
        for_user_id=for_user_id,
        text=note_text,
        created_by_user_id=message.from_user.id
    )

    await bot.send_message(message.chat.id, f"Послание для пользователя {for_user_id} успешно сохранено!")
    await bot.delete_state(message.from_user.id, message.chat.id)


async def handle_start(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    message_parts = message.text.split()        
    user = await crud.create_or_update_user(
            db,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    if len(message_parts) == 1:
        await bot.send_message(message.chat.id, f"Привет, {escape_html(user.first_name)}! Здесь вы можете оставить своё послание любому пользователю.")
        return
    
    if len(message_parts) == 2:
        ref_code = message_parts[1]
        ref_user = await crud.get_user_by_ref_code(db, ref_code)
        print(user.user_id, ref_user.user_id)
        if ref_user:
            if ref_user.user_id == user.user_id:
                await bot.send_message(message.chat.id, "Вы не можете оставить послание самому себе.")
                return
            creator_user = await crud.get_user_by_ref_code(db, ref_code)
            note = await crud.get_note_by_user_id_and_creator_id(db, user.user_id, creator_user.user_id)
            if note is None:
                await bot.send_message(message.chat.id,  "📭 Тебе пока ничего не написали...\n\nНо ты можешь написать своё послание друзьям командой /note")
                return
            message_text = f"Вам письмо от {creator_user.first_name}:\n\n"\
                           f"{escape_html(note.text)}"
            await bot.send_message(message.chat.id, message_text)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button = types.KeyboardButton()


async def get_my_ref_link(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    user = await crud.create_or_update_user(
            db,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    if not user.ref_code:
        ref_code = await crud.generate_unique_ref_code(db, user)
        user.ref_code = ref_code
        db.add(user)
        await db.commit()
        await db.refresh(user)
    ref_link = f"https://t.me/ToUserBot?start={user.ref_code}"
    await bot.send_message(message.chat.id, f"Ваша реферальная ссылка:\n{ref_link}")


async def handle_user_shared(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    if not message.user_shared:
        await bot.send_message(message.chat.id, "❌ Не удалось получить пользователя.")
        return

    for_user_id = message.user_shared.users[0].user_id
    
    await bot.set_state(message.from_user.id, NoteStates.waiting_for_note_text, message.chat.id)
    await bot.send_message(message.chat.id, "✨ Теперь введите текст послания:", reply_markup=types.ReplyKeyboardRemove())
    await update_data(bot, message.from_user.id, message.chat.id, user_id=int(for_user_id))


async def handle_get_my_notes(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    user_id = message.from_user.id
    notes = await crud.get_notes_by_user_id(db, user_id)
    if not notes:
        await bot.send_message(message.chat.id, "Вы ещё никому не оставляли посланий. Используйте команду /note чтобы создать новое послание")
        return
    
    top_message = f"Вы оставили {len(notes)} послание(ий):\n\n"

    markup = types.InlineKeyboardMarkup()

    for note in notes:
        for_who = await crud.get_user_by_id(db, note.for_user_id)
        if for_who:
            for_who = escape_html(for_who.first_name)
        else:
            for_who = str(note.for_user_id)
        top_message += f"- Для `{for_who}` в {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        button = types.InlineKeyboardButton(
            text=f"Послание для {for_who}",
            callback_data=f"view_note_{note.id}"
        )
        markup.add(button)
    
    await bot.send_message(message.chat.id, top_message, reply_markup=markup, parse_mode='Markdown')


async def handle_buy_unread(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    chat_id = message.chat.id
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(
        text="Отменить покупку",
        callback_data="cancel_purchase"
    )
    markup.add(button)
    await bot.send_message(chat_id, f"Одна отмена прочтения стоит {COST} звёзд. Отправьте количество отмен, которое хотите купить:", reply_markup=markup)
    await bot.set_state(user_id, NoteStates.waiting_for_unread_quantity, chat_id)


async def handle_cancel_purchase_callback(call: types.CallbackQuery, bot: AsyncTeleBot, db: AsyncSession):
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    await bot.delete_state(user_id, chat_id)
    await bot.edit_message_text("Покупка отменена.", chat_id, message_id)


async def handle_unread_quantity(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    chat_id = message.chat.id
    user_id = message.from_user.id
    state = await bot.get_state(user_id, chat_id)
    
    quantity_text = message.text.strip()
    if not quantity_text.isdigit() or int(quantity_text) <= 0:
        await bot.send_message(chat_id, "Пожалуйста, введите корректное число")
        return

    quantity = int(quantity_text)
    total_cost = quantity * COST


    await bot.delete_state(user_id, chat_id)
    await bot.send_invoice(
        chat_id,
        title="Отмена прочтения",
        description=f"Покупка {quantity} отмен прочтения за {total_cost} звёзд",
        provider_token=None,
        currency="XTR",
        invoice_payload=f"buy_unread_{user_id}_{quantity}",
        prices=[types.LabeledPrice(label=f"{quantity} отмен прочтения", amount=total_cost)]
        )



async def handle_view_note_callback(call: types.CallbackQuery, bot: AsyncTeleBot, db: AsyncSession):
    data = call.data
    message_id = call.message.message_id
    chat_id = call.message.chat.id

    if not data.startswith("view_note_"):
        return
    note_id = int(data.split("_")[-1])

    note = await crud.get_note_by_id(db, note_id)
    if not note:
        await bot.answer_callback_query(call.id, "Послание не найдено.")
        return
    if note.created_by_user_id != call.from_user.id:
        await bot.answer_callback_query(call.id, "Вы не можете просматривать это послание.")
        return
    
    for_who = await crud.get_user_by_id(db, note.for_user_id)
    if for_who:
        for_who = escape_html(for_who.first_name)
    else:
        for_who = str(note.for_user_id)

    top_message = f"Послание для {for_who}:\n\n"
    top_message += note.text

    markup = types.InlineKeyboardMarkup()
    button_edit = types.InlineKeyboardButton(
        text="Редактировать",
        callback_data=f"edit_note_{note.id}"
    )
    button_delete = types.InlineKeyboardButton(
        text="Удалить",
        callback_data=f"delete_note_{note.id}"
    )
    button_back = types.InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_notes"
    )
    markup.add(button_edit)
    markup.add(button_delete)
    markup.add(button_back)

    await bot.edit_message_text(top_message, chat_id, message_id, parse_mode='HTML', reply_markup=markup)


async def handle_edit_note_callback(call: types.CallbackQuery, bot: AsyncTeleBot, db: AsyncSession):
    data = call.data
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if not data.startswith("edit_note_"):
        return
    
    note_id = int(data.split("_")[-1])
    note = await crud.get_note_by_id(db, note_id)
    if not note:
        await bot.answer_callback_query(call.id, "Послание не найдено")
        return
    
    if note.created_by_user_id != call.from_user.id:
        await bot.answer_callback_query(call.id, "Кого-то по рукам отшлёпать?")
        return

    top_message = f"Отправьте новый текст посания:"

    await bot.set_state(user_id, NoteStates.waiting_for_update_note_text, chat_id)
    await update_data(bot, user_id, chat_id, note_id=note_id)
    await bot.edit_message_text(top_message, chat_id, message_id)

async def handle_update_note_text(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    user_id = message.from_user.id
    chat_id = message.chat.id
    state = await bot.get_state(user_id, chat_id)
    
    note_id: str = await get_data(bot, user_id, chat_id, "note_id")

    note_text = message.text.strip()
    new_note = await crud.update_note_text(db, note_id, note_text)
    if not new_note:
        await bot.send_message(chat_id, "Этого послания не существует. Вы можете отправить новое командой /note")
        return 
    
    markup = types.InlineKeyboardMarkup()
    button_back = types.InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_notes"
    )
    markup.add(button_back)

    await bot.send_message(chat_id, "Послание успешно обновлено!", reply_markup=markup)
    await bot.delete_state(user_id, chat_id)
    
async def handle_delete_note_callback(call: types.CallbackQuery, bot: AsyncTeleBot, db: AsyncSession):
    data = call.data
    message_id = call.message.message_id
    chat_id = call.message.chat.id

    if not data.startswith("delete_note_"):
        return
    note_id = int(data.split("_")[-1])

    note = await crud.get_note_by_id(db, note_id)
    if not note:
        await bot.answer_callback_query(call.id, "Послание не найдено.")
        return
    if note.created_by_user_id != call.from_user.id:
        await bot.answer_callback_query(call.id, "Вы не можете удалять это послание.")
        return
    
    markup = types.InlineKeyboardMarkup()
    button_back = types.InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_notes"
    )
    markup.add(button_back)

    success = await crud.delete_note_by_id(db, note_id)
    if success:
        await bot.edit_message_text("Послание удалено.", chat_id, message_id, reply_markup=markup)
    else:
        await bot.answer_callback_query(call.id, "Не удалось удалить послание.")
    

async def handle_back_to_notes_callback(call: types.CallbackQuery, bot: AsyncTeleBot, db: AsyncSession):
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    await bot.delete_state(user_id, chat_id)
    notes = await crud.get_notes_by_user_id(db, user_id)
    if not notes:
        await bot.send_message(chat_id, "Вы ещё никому не оставляли посланий. Используйте команду /note чтобы создать новое послание")
        return
    
    top_message = f"Вы оставили {len(notes)} послание(ий):\n\n"

    markup = types.InlineKeyboardMarkup()

    for note in notes:
        for_who = await crud.get_user_by_id(db, note.for_user_id)
        if for_who:
            for_who = escape_html(for_who.first_name)
        else:
            for_who = str(note.for_user_id)
        top_message += f"- Для `{for_who}` в {note.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        button = types.InlineKeyboardButton(
            text=f"Послание для {for_who}",
            callback_data=f"view_note_{note.id}"
        )
        markup.add(button)
    
    await bot.edit_message_text(top_message, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')


async def handle_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery, bot: AsyncTeleBot, db: AsyncSession):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)




async def handle_successful_payment(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    
    payload_parts = payment_info.invoice_payload.split('_')
    quantity = int(payload_parts[-1])  
    
    user, admin_panel = await crud.process_payment(
        db, 
        user_id=user_id,
        quantity=quantity,
        total_cost=payment_info.total_amount
    )
    
    await bot.send_message(
        message.chat.id, 
        f"✅ Куплено {quantity} отмен прочтения!\n"
        f"💰 Ваш текущий баланс: {user.count_read_cancel} отмен"
    )


async def handle_admin(message: types.Message, bot: AsyncTeleBot, db: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    admin_panel = await crud.get_admin_panel(db)
    if not admin_panel:
        await bot.send_message(message.chat.id, "Чето пошло не так, перезапусти бота, по идее должно было создаться")
        return
    top_message = f"Привет, {message.from_user.first_name}! Текущая статистика бота:\n\n"
    top_message += f"💰 Общая прибыль: {admin_panel.total_earnings} звёзд\n"
    top_message += f"📖 Куплено отмен прочтения: {admin_panel.total_read_cancels_sold}\n"
    top_message += f"👤 ID Администратора: {admin_panel.admin_user_id}\n\n"
    top_message += f"Бот работает с {admin_panel.last_restart.strftime('%Y-%m-%d %H:%M:%S')} (МСК)\n"

    await bot.send_message(message.chat.id, top_message)



def register_handlers(bot: AsyncTeleBot):   
    bot.register_message_handler(db_handler(handle_user_shared), content_types=["users_shared"], pass_bot=True)       
    bot.register_message_handler(db_handler(debug_state), commands=["debugstate"], pass_bot=True)
    bot.register_message_handler(db_handler(handle_start), commands=["start"], pass_bot=True)
    bot.register_message_handler(db_handler(start_note_creation), commands=["note"], pass_bot=True)
    bot.register_message_handler(db_handler(get_my_ref_link), commands=["myref"], pass_bot=True)
    bot.register_message_handler(db_handler(handle_get_my_notes), commands=["mynotes"], pass_bot=True)

    bot.register_pre_checkout_query_handler(db_handler(handle_pre_checkout_query), func=lambda query: True, pass_bot=True)
    bot.register_message_handler(db_handler(handle_successful_payment), content_types=['successful_payment'], pass_bot=True)
    bot.register_message_handler(db_handler(handle_buy_unread), commands=["buy_unread"], pass_bot=True)
    bot.register_message_handler(db_handler(handle_unread_quantity), func=create_state_filter(NoteStates.waiting_for_unread_quantity, bot), pass_bot=True, content_types=['text'])

    bot.register_message_handler(db_handler(handle_admin), commands=["admin"], pass_bot=True)

    bot.register_callback_query_handler(callback=db_handler(handle_view_note_callback), func=lambda call: call.data and call.data.startswith("view_note_"), pass_bot=True)
    bot.register_callback_query_handler(callback=db_handler(handle_edit_note_callback), func=lambda call: call.data and call.data.startswith("edit_note_"), pass_bot=True)
    bot.register_callback_query_handler(callback=db_handler(handle_delete_note_callback), func=lambda call: call.data and call.data.startswith("delete_note_"), pass_bot=True)
    bot.register_callback_query_handler(callback=db_handler(handle_back_to_notes_callback), func=lambda call: call.data == "back_to_notes", pass_bot=True)

    bot.register_message_handler(db_handler(process_user_id), func=create_state_filter(NoteStates.waiting_for_user_id, bot), pass_bot=True, content_types=['text'])
    bot.register_message_handler(db_handler(process_note_text), func=create_state_filter(NoteStates.waiting_for_note_text, bot), pass_bot=True, content_types=['text'])
    bot.register_message_handler(db_handler(handle_update_note_text), func=create_state_filter(NoteStates.waiting_for_update_note_text, bot), pass_bot=True, content_types=['text'])
