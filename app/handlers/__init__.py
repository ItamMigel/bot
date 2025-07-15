"""Регистрация всех обработчиков"""
from aiogram import Dispatcher
from . import common
from .user import menu, cart


def register_all_handlers(dp: Dispatcher):
    """Регистрация всех роутеров"""
    # Пользовательские обработчики (должны быть первыми)
    dp.include_router(menu.router)
    dp.include_router(cart.router)
    
    # Общие обработчики (должны быть последними)
    dp.include_router(common.router)
    
    # TODO: добавить остальные роутеры
    # dp.include_router(user.orders.router)
    # dp.include_router(admin.orders.router)
    # dp.include_router(admin.menu.router)
