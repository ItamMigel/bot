"""Middleware для аутентификации пользователей"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, User


class AuthMiddleware(BaseMiddleware):
    """Middleware для создания/обновления пользователей в БД"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из события
        telegram_user: TgUser = data.get("event_from_user")
        
        if telegram_user:
            async with async_session_maker() as session:
                # Ищем пользователя в БД
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_user.id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    # Создаем нового пользователя
                    user = User(
                        telegram_id=telegram_user.id,
                        username=telegram_user.username,
                        first_name=telegram_user.first_name,
                        last_name=telegram_user.last_name,
                        is_admin=False  # Администраторы назначаются через настройки
                    )
                    session.add(user)
                else:
                    # Обновляем данные существующего пользователя
                    user.username = telegram_user.username
                    user.first_name = telegram_user.first_name
                    user.last_name = telegram_user.last_name
                
                await session.commit()
                await session.refresh(user)
                
                # Добавляем пользователя в данные для обработчика
                data["user"] = user
        
        return await handler(event, data)
