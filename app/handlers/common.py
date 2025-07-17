"""Общие обработчики команд"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from app.utils import texts, UserStates
from app.keyboards.user import get_main_menu_keyboard
from app.database import User

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, user: User):
    """Обработчик команды /start"""
    await state.set_state(UserStates.MAIN_MENU)
    
    # Получаем количество товаров в корзине
    from app.services.cart import CartService
    from app.database import async_session_maker
    from app.config import settings
    
    async with async_session_maker() as session:
        cart_count = await CartService.get_cart_count(session, user.id)
    
    await message.answer(
        settings.welcome_message,
        reply_markup=get_main_menu_keyboard(cart_count)
    )


@router.message(Command("help"))
@router.message(F.text == texts.BUTTON_HELP)
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(texts.HELP_MESSAGE)


@router.message(F.text == texts.BUTTON_MAIN_MENU)
@router.callback_query(F.data == "main_menu")
async def main_menu(event: Message | CallbackQuery, state: FSMContext, user: User = None):
    """Возврат в главное меню"""
    await state.set_state(UserStates.MAIN_MENU)
    
    # Получаем количество товаров в корзине
    cart_count = 0
    if user:
        from app.services.cart import CartService
        from app.database import async_session_maker
        
        async with async_session_maker() as session:
            cart_count = await CartService.get_cart_count(session, user.id)
    
    if isinstance(event, CallbackQuery):
        from app.config import settings
        await event.message.edit_text(
            settings.welcome_message,
            reply_markup=None
        )
        await event.message.answer(
            "🏠 Главное меню",
            reply_markup=get_main_menu_keyboard(cart_count)
        )
        await event.answer()
    else:
        await event.answer(
            "🏠 Главное меню",
            reply_markup=get_main_menu_keyboard(cart_count)
        )


@router.message(StateFilter(None))
async def any_message(message: Message, state: FSMContext, user: User):
    """Обработчик любых сообщений в состоянии None"""
    logging.info(f"Получено сообщение от пользователя {user.id}: '{message.text}'")
    await state.set_state(UserStates.MAIN_MENU)
    
    # Получаем количество товаров в корзине
    from app.services.cart import CartService
    from app.database import async_session_maker
    
    async with async_session_maker() as session:
        cart_count = await CartService.get_cart_count(session, user.id)
    
    await message.answer(
        "👋 Добро пожаловать! Выберите действие:",
        reply_markup=get_main_menu_keyboard(cart_count)
    )


@router.message()
async def debug_all_messages(message: Message, state: FSMContext, user: User = None):
    """Отладочный обработчик всех сообщений (должен быть последним)"""
    current_state = await state.get_state()
    logging.info(f"Необработанное сообщение от пользователя {user.id if user else 'Unknown'}: '{message.text}', состояние: {current_state}")
    
    # Если пользователь не авторизован
    if not user:
        await message.answer("❌ Ошибка авторизации. Отправьте /start")
        return
    
    # Если состояние не установлено, направляем в главное меню
    if not current_state:
        await state.set_state(UserStates.MAIN_MENU)
    
    # Получаем количество товаров в корзине
    from app.services.cart import CartService
    from app.database import async_session_maker
    
    async with async_session_maker() as session:
        cart_count = await CartService.get_cart_count(session, user.id)
    
    await message.answer(
        "🤔 Не понял команду. Выберите действие из меню:",
        reply_markup=get_main_menu_keyboard(cart_count)
    )
