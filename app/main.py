"""
Главный файл приложения - запуск бота
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database import init_database, close_database
from app.handlers import register_all_handlers
from app.middlewares import register_all_middlewares


async def on_startup():
    """Действия при запуске бота"""
    logging.info("Инициализация базы данных...")
    await init_database()
    logging.info("База данных инициализирована")


async def on_shutdown():
    """Действия при остановке бота"""
    logging.info("Закрытие соединения с базой данных...")
    await close_database()
    logging.info("Соединение с базой данных закрыто")


async def main():
    """Основная функция запуска бота"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logging.info("Запуск бота...")
    
    # Создание бота и диспетчера
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware и обработчиков
    register_all_middlewares(dp)
    register_all_handlers(dp)
    
    # Действия при запуске
    await on_startup()
    
    try:
        # Запуск бота
        logging.info("Бот запущен и готов к работе!")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        # Действия при остановке
        await on_shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        raise
