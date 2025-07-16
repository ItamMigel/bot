"""Регистрация всех обработчиков"""
from aiogram import Dispatcher
from . import common
from .user import menu, cart, orders, faq
from .admin import admin_panel


def register_all_handlers(dp: Dispatcher):
    """Регистрация всех роутеров"""
    # Пользовательские обработчики (должны быть первыми)
    dp.include_router(menu.router)
    dp.include_router(cart.router)
    dp.include_router(orders.router)
    dp.include_router(faq.router)
    
    # Админ обработчики
    dp.include_router(admin_panel.router)
    
    # Общие обработчики (должны быть последними)
    dp.include_router(common.router)
