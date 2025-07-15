from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


# Создаем движок базы данных
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Установить в True для отладки SQL запросов
    future=True
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_async_session() -> AsyncSession:
    """Получить асинхронную сессию базы данных"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_database():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        # Импортируем все модели для создания таблиц
        from app.database.models import User, Category, Dish, Order, OrderItem, Payment
        
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)


async def close_database():
    """Закрытие соединения с базой данных"""
    await engine.dispose()
