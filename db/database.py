from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from config import DATABASE_URL
from typing import AsyncGenerator


engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()



async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Получение асинхронной сессии базы данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            print(f"Ошибка сессии SQLAlchemy: {e}")
            raise

async def init_models():
    """
    Инициализация моделей базы данных
    """
    try:
        async with engine.begin() as conn:
            # Для удаления таблиц перед созданием
            # print("Удаление старых таблиц...")
            # await conn.run_sync(Base.metadata.drop_all)
            # print("Старые таблицы удалены.")
            await conn.run_sync(Base.metadata.create_all)
            print("Создание таблиц успешно завершено")

    except SQLAlchemyError as e:
        print(f"Ошибка SQLAlchemy: {e}")
        raise
    except Exception as e:
        print(f"Общая ошибка: {e}")
        raise