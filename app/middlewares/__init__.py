"""Регистрация всех middleware"""
from aiogram import Dispatcher
from .auth import AuthMiddleware
from .admin import AdminMiddleware


def register_all_middlewares(dp: Dispatcher):
    """Регистрация всех middleware"""
    # Порядок важен - auth должен быть первым
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    dp.message.middleware(AdminMiddleware())
    dp.callback_query.middleware(AdminMiddleware())
