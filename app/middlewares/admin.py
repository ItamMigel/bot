"""Middleware для проверки прав администратора"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.utils.helpers import is_admin


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("user")
        
        if user:
            # Проверяем, является ли пользователь админом
            data["is_admin"] = is_admin(user.telegram_id) or user.is_admin
        else:
            data["is_admin"] = False
        
        return await handler(event, data)
