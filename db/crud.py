from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy import select, delete

from db.models import AdminPanel, User, Note
from db.utils import id_to_ref_code

from typing import Optional, List

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Получение пользователя по его user_id
    Возвращает объект User, если пользователь найден, иначе None.
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    if user:
        return user
    return None

async def add_user(db: AsyncSession, user_id: int, username: Optional[str] = None, first_name: str = None, last_name: Optional[str] = None) -> User:
    """
    Добавление нового пользователя в базу данных
    1. Проверяет, существует ли пользователь с данным user_id.
    2. Если существует, возвращает существующего пользователя.
    3. Если не существует, создает нового пользователя с предоставленными данными.
    Возвращает объект пользователя.
    """
    if await get_user_by_id(db, user_id):
        return await get_user_by_id(db, user_id)
    
    ref_code = id_to_ref_code(user_id)
    query = select(User).where(User.ref_code == ref_code)
    result = await db.execute(query)
    existing_user = result.scalars().first()
    while existing_user:
        # Если ref_code уже существует, генерируем новый, увеличивая user_id
        user_id += 1
        ref_code = id_to_ref_code(user_id)
        query = select(User).where(User.ref_code == ref_code)
        result = await db.execute(query)
        existing_user = result.scalars().first()

    new_user = User(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        ref_code=ref_code
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def create_or_update_user(db: AsyncSession, user_id: int, username: Optional[str] = None, first_name: str = None, last_name: Optional[str] = None) -> User:
    """
    Создание нового пользователя или обновление существующего
    1. Проверяет, существует ли пользователь с данным user_id.
    2. Если существует, обновляет его данные.
    3. Если не существует, создает нового пользователя с предоставленными данными.
    Возвращает объект пользователя.
    """
    user = await get_user_by_id(db, user_id)
    if user:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    else:
        return await add_user(db, user_id, username, first_name, last_name)

async def get_user_by_ref_code(db: AsyncSession, ref_code: str) -> Optional[User]:
    """
    Получение пользователя по его реферальному коду
    Возвращает объект User, если пользователь найден, иначе None.
    """
    result = await db.execute(select(User).where(User.ref_code == ref_code))
    user = result.scalars().first()
    if user:
        return user
    return None

async def create_new_ref_code(db: AsyncSession, user_id: int) -> str:
    """
    Обновляет реферальный код пользователя на новый случайный,
    используя функцию id_to_ref_code из utils.py.
    Возвращает новый реферальный код.
    """
    import random
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    while True:
        rand_id = user_id + random.randint(1, 5000) * random.choice([-1, 1])
        new_code = id_to_ref_code(rand_id)
        if not await get_user_by_ref_code(db, new_code):
            user.ref_code = new_code
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return new_code




async def create_note(db: AsyncSession, for_user_id: int, text: str, created_by_user_id: int) -> Note:
    """
    Создание новой заметки
    1. Создает новую заметку с предоставленным текстом для указанного пользователя.
    2. Устанавливает created_by_user_id для отслеживания, кто создал заметку.
    Возвращает объект созданной заметки.
    """
    note_id = await get_note_id(db, created_by_user_id, for_user_id)
    if note_id:
        await delete_note_by_id(db, note_id)

    new_note = Note(
        for_user_id=for_user_id,
        text=text,
        created_by_user_id=created_by_user_id
    )
    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)
    return new_note

async def get_note_id(db: AsyncSession, from_user_id: int, for_user_id: int) -> Optional[int]:
    """
    Получение ID заметки, созданной пользователем from_user_id для пользователя for_user_id
    Возвращает ID заметки, если она найдена, иначе None.
    """
    result = await db.execute(
        select(Note.id).where(
            Note.created_by_user_id == from_user_id,
            Note.for_user_id == for_user_id,
        ).order_by(Note.created_at.desc())
    )
    note_id = result.scalars().first()
    return note_id

async def get_note_by_id(db: AsyncSession, note_id: int) -> Optional[Note]:
    """
    Получение заметки по ее ID
    Возвращает объект Note, если заметка найдена, иначе None.
    """
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalars().first()
    if note:
        return note
    return None



async def get_note_by_user_id_and_creator_id(db: AsyncSession, for_user_id: int, created_by_user_id: int) -> Optional[Note]:
    """
    Получение заметки, созданной пользователем created_by_user_id для пользователя for_user_id
    Возвращает объект Note, если заметка найдена, иначе None.
    """
    
    result = await db.execute(
        select(Note).where(
            Note.for_user_id == for_user_id,
            Note.created_by_user_id == created_by_user_id
        ).order_by(Note.created_at.desc())
    )
    note = result.scalars().first()
    
    return note

async def update_note_text(db: AsyncSession, note_id: int, new_text: str) -> Optional[Note]:
    """
    Обновление текста заметки по ее ID
    1. Проверяет, существует ли заметка с данным ID.
    2. Если существует, обновляет ее текст на новый.
    Возвращает обновленный объект Note, если заметка была обновлена, иначе None.
    """
    note = await get_note_by_id(db, note_id)
    if note:
        note.text = new_text
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note
    return None



async def delete_note_by_id(db: AsyncSession, note_id: int) -> bool:
    """
    Удаление заметки по ее ID
    1. Проверяет, существует ли заметка с данным ID.
    2. Если существует, удаляет ее из базы данных.
    Возвращает True, если заметка была удалена, иначе False.
    """
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalars().first()
    if note:
        await db.delete(note)
        await db.commit()
        return True
    return False

async def set_note_as_read(db: AsyncSession, note_id: int) -> Optional[Note]:
    """
    Помечает заметку как прочитанную по ее ID
    """
    note = await get_note_by_id(db, note_id)
    if note:
        note.is_read = True
        note.fake_is_read = True
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note
    return None

async def set_note_as_unread(db: AsyncSession, note_id: int) -> Optional[Note]:
    """
    Помечает заметку как непрочитанную по ее ID
    """
    note = await get_note_by_id(db, note_id)
    if note:
        note.fake_is_read = False
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note
    return None



async def get_notes_by_user_id(db: AsyncSession, user_id: int) -> List[Note]:
    """
    Получение всех заметок, созданных для пользователя с данным user_id
    Возвращает список объектов Note.
    """
    result = await db.execute(select(Note).where(Note.created_by_user_id == user_id).order_by(Note.created_at.desc()))
    notes = result.scalars().all()
    return notes


async def initiate_creation_of_admin_panel(db: AsyncSession, admin_user_id: int, total_earnings: int = 0, total_read_cancels_sold: int = 0) -> None:
    """
    Инициализация панели администратора для пользователя с данным user_id
    """
    result = await db.execute(select(AdminPanel).where(AdminPanel.admin_user_id == admin_user_id))
    admin_panel = result.scalars().first()
    if not admin_panel:
        new_admin_panel = AdminPanel(
            admin_user_id=admin_user_id,
            total_earnings=total_earnings,
            total_read_cancels_sold=total_read_cancels_sold
        )
        db.add(new_admin_panel)
        await db.commit()
        await db.refresh(new_admin_panel)
    if admin_panel:
        admin_panel.last_restart = func.now()
        db.add(admin_panel)
        await db.commit()


async def get_admin_panel(db: AsyncSession) -> Optional[AdminPanel]:
    """
    Возвращает объект AdminPanel.
    """
    result = await db.execute(select(AdminPanel))
    admin_panel = result.scalars().first()
    if admin_panel:
        return admin_panel
    return None


async def update_user_balance(db: AsyncSession, user_id: int, additional_cancels: int) -> User:
    """
    Обновляет баланс отмен прочтения для пользователя
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with id {user_id} not found")
    
    user.count_read_cancel += additional_cancels
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def update_admin_panel(db: AsyncSession, additional_earnings: int, additional_cancels_sold: int) -> AdminPanel:
    """
    Обновляет статистику админ-панели
    """
    admin_panel = await get_admin_panel(db)
    if not admin_panel:
        raise ValueError("Admin panel not found")
    
    admin_panel.total_earnings += additional_earnings
    admin_panel.total_read_cancels_sold += additional_cancels_sold
    db.add(admin_panel)
    await db.commit()
    await db.refresh(admin_panel)
    return admin_panel

async def process_payment(db: AsyncSession, user_id: int, quantity: int, total_cost: int) -> tuple[User, AdminPanel]:
    """
    Обрабатывает успешный платеж: обновляет баланс пользователя и статистику админа
    Возвращает кортеж (обновленный пользователь, обновленная админ-панель)
    """
    user = await update_user_balance(db, user_id, quantity)
    
    admin_panel = await update_admin_panel(db, total_cost, quantity)
    
    return user, admin_panel