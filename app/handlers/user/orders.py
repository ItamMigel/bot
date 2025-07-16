"""Обработчики для работы с заказами пользователя"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.utils import texts, UserStates
from app.utils.helpers import format_price
from app.keyboards.user import (
    get_main_menu_keyboard, get_payment_method_keyboard, 
    get_order_confirmation_keyboard, get_orders_keyboard,
    get_order_details_keyboard
)
from app.database import async_session_maker, User
from app.services.cart import CartService

router = Router()


@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext, user: User):
    """Начать оформление заказа"""
    async with async_session_maker() as session:
        cart = await CartService.get_cart_with_items(session, user.id)
        
        if not cart or not cart.items:
            await callback.answer("❌ Корзина пуста", show_alert=True)
            return
        
        # Проверяем минимальную сумму заказа
        from app.config import settings
        if cart.total_amount < settings.min_order_amount:
            await callback.answer(
                f"❌ Минимальная сумма заказа: {settings.min_order_amount} ₽",
                show_alert=True
            )
            return
    
    # Формируем список товаров для подтверждения
    cart_items_text = []
    for item in cart.items:
        item_text = texts.CART_ITEM_FORMAT.format(
            dish_name=item.dish.name,
            quantity=item.quantity,
            total_price=format_price(item.total_price)
        )
        cart_items_text.append(item_text)
    
    confirmation_text = texts.ORDER_CONFIRMATION.format(
        cart_items="\n".join(cart_items_text),
        total_amount=format_price(cart.total_amount)
    )
    
    await callback.message.edit_text(
        confirmation_text,
        reply_markup=get_order_confirmation_keyboard()
    )
    await callback.answer()
    await state.set_state(UserStates.CONFIRMING_ORDER)


@router.callback_query(F.data == "confirm_order", StateFilter(UserStates.CONFIRMING_ORDER))
async def confirm_order(callback: CallbackQuery, state: FSMContext, user: User):
    """Подтвердить заказ и перейти к выбору оплаты"""
    await callback.message.edit_text(
        texts.PAYMENT_METHOD_MESSAGE,
        reply_markup=get_payment_method_keyboard()
    )
    await callback.answer()
    await state.set_state(UserStates.CHOOSING_PAYMENT)


@router.callback_query(F.data == "payment_card", StateFilter(UserStates.CHOOSING_PAYMENT))
async def choose_card_payment(callback: CallbackQuery, state: FSMContext, user: User):
    """Выбрать оплату картой"""
    async with async_session_maker() as session:
        cart = await CartService.get_cart_with_items(session, user.id)
        
        if not cart or not cart.items:
            await callback.answer("❌ Корзина пуста", show_alert=True)
            return
        
        # Создаем заказ
        from app.services.order import OrderService
        order = await OrderService.create_order_from_cart(
            session, user.id, payment_method="card"
        )
        await session.commit()
        
        if not order:
            await callback.answer("❌ Ошибка создания заказа", show_alert=True)
            return
    
    # Показываем реквизиты для оплаты
    from app.config import settings
    payment_text = texts.PAYMENT_CARD_INFO.format(
        amount=format_price(order.total_amount),
        card_number=settings.payment_card_number,
        card_owner=settings.payment_card_owner,
        instructions=settings.payment_instructions
    )
    
    await callback.message.edit_text(payment_text)
    await callback.message.answer(texts.PAYMENT_SCREENSHOT_PROMPT)
    await callback.answer()
    await state.set_state(UserStates.UPLOADING_PAYMENT_SCREENSHOT)
    
    # Сохраняем ID заказа в состоянии
    await state.update_data(order_id=order.id)


@router.callback_query(F.data == "payment_cash", StateFilter(UserStates.CHOOSING_PAYMENT))
async def choose_cash_payment(callback: CallbackQuery, state: FSMContext, user: User):
    """Выбрать оплату наличными"""
    async with async_session_maker() as session:
        cart = await CartService.get_cart_with_items(session, user.id)
        
        if not cart or not cart.items:
            await callback.answer("❌ Корзина пуста", show_alert=True)
            return
        
        # Создаем заказ
        from app.services.order import OrderService
        order = await OrderService.create_order_from_cart(
            session, user.id, payment_method="cash"
        )
        await session.commit()
        
        if not order:
            await callback.answer("❌ Ошибка создания заказа", show_alert=True)
            return
    
    # Показываем информацию о заказе
    payment_text = texts.PAYMENT_CASH_INFO.format(
        amount=format_price(order.total_amount)
    )
    
    await callback.message.edit_text(payment_text)
    
    order_created_text = texts.ORDER_CREATED.format(
        order_id=order.id,
        total_amount=format_price(order.total_amount)
    )
    
    await callback.message.answer(
        order_created_text,
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
    await state.set_state(UserStates.MAIN_MENU)
    
    # Уведомляем администратора о новом заказе
    await notify_admin_new_order(order)


@router.message(
    F.content_type == ContentType.PHOTO, 
    StateFilter(UserStates.UPLOADING_PAYMENT_SCREENSHOT)
)
async def receive_payment_screenshot(message: Message, state: FSMContext, user: User):
    """Получить скриншот оплаты"""
    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await message.answer("❌ Ошибка: заказ не найден")
        return
    
    # Сохраняем файл скриншота
    from app.utils.helpers import save_payment_screenshot
    screenshot_path = await save_payment_screenshot(message.photo[-1], order_id, message.bot)
    
    # Обновляем заказ
    async with async_session_maker() as session:
        from app.services.order import OrderService
        success = await OrderService.update_payment_screenshot(
            session, order_id, screenshot_path
        )
        await session.commit()
        
        if success:
            order = await OrderService.get_order_by_id(session, order_id)
            await message.answer(texts.PAYMENT_SCREENSHOT_RECEIVED)
            
            order_created_text = texts.ORDER_CREATED.format(
                order_id=order.id,
                total_amount=format_price(order.total_amount)
            )
            
            await message.answer(
                order_created_text,
                reply_markup=get_main_menu_keyboard()
            )
            
            # Уведомляем администратора
            await notify_admin_payment_received(order)
        else:
            await message.answer("❌ Ошибка сохранения скриншота")
    
    await state.set_state(UserStates.MAIN_MENU)


@router.message(StateFilter(UserStates.UPLOADING_PAYMENT_SCREENSHOT))
async def handle_non_photo_while_waiting_screenshot(message: Message, state: FSMContext, user: User):
    """Обработка случаев, когда пользователь отправляет не фото в ожидании скриншота"""
    # Получаем ID заказа из состояния
    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await message.answer("❌ Ошибка: заказ не найден")
        await state.set_state(UserStates.MAIN_MENU)
        return
    
    # Создаем клавиатуру с вариантами действий
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📷 Отправить скриншот", 
                callback_data="retry_screenshot"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить заказ", 
                callback_data=f"cancel_order_{order_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Главное меню", 
                callback_data="main_menu"
            )
        ]
    ])
    
    await message.answer(
        texts.SCREENSHOT_REQUIRED,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "retry_screenshot", StateFilter(UserStates.UPLOADING_PAYMENT_SCREENSHOT))
async def retry_screenshot_upload(callback: CallbackQuery, state: FSMContext):
    """Повторная попытка загрузки скриншота"""
    await callback.message.edit_text(
        texts.SCREENSHOT_RETRY_MESSAGE
    )
    await callback.answer()
    # Состояние остается UPLOADING_PAYMENT_SCREENSHOT


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_payment_order(callback: CallbackQuery, state: FSMContext, user: User):
    """Отменить заказ на этапе ожидания скриншота"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.services.order import OrderService
        
        # Отменяем заказ
        success = await OrderService.cancel_order(session, order_id, user.id)
        await session.commit()
        
        if success:
            await callback.message.edit_text(
                texts.ORDER_CANCELLED.format(order_id=order_id)
            )
            await callback.message.answer(
                "🏠 Добро пожаловать в главное меню!",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                texts.ORDER_CANCEL_ERROR
            )
            await callback.message.answer(
                "🏠 Главное меню",
                reply_markup=get_main_menu_keyboard()
            )
    
    await callback.answer()
    await state.set_state(UserStates.MAIN_MENU)


@router.message(F.text == texts.BUTTON_ORDERS)
async def show_orders(message: Message, state: FSMContext, user: User):
    """Показать заказы пользователя"""
    await state.set_state(UserStates.VIEWING_ORDERS)
    
    async with async_session_maker() as session:
        from app.services.order import OrderService
        orders = await OrderService.get_user_orders(session, user.id)
        
        if not orders:
            await message.answer(
                texts.NO_ORDERS,
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        await message.answer(
            texts.ORDERS_LIST_MESSAGE,
            reply_markup=get_orders_keyboard(orders)
        )


@router.callback_query(F.data.startswith("order_"))
async def show_order_details(callback: CallbackQuery, state: FSMContext, user: User):
    """Показать детали заказа"""
    order_id = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        from app.services.order import OrderService
        order = await OrderService.get_order_details(session, order_id)
        
        if not order or order.user_id != user.id:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Формируем детали заказа
        order_items_text = []
        for item in order.items:
            item_text = texts.ORDER_ITEM_FORMAT.format(
                dish_name=item.dish.name,
                quantity=item.quantity,
                total_price=format_price(item.total_price)
            )
            order_items_text.append(item_text)
        
        # Информация об оплате
        payment_info = ""
        if order.payment_method == "card":
            if order.payment_screenshot:
                payment_info = "💳 Оплата картой (скриншот загружен)"
            else:
                payment_info = "💳 Оплата картой (ожидается скриншот)"
        else:
            payment_info = "💵 Оплата наличными при получении"
        
        order_text = texts.ORDER_DETAILS_MESSAGE.format(
            order_id=order.id,
            created_at=order.created_at.strftime("%d.%m.%Y %H:%M"),
            status=texts.ORDER_STATUSES.get(order.status, order.status),
            total_amount=format_price(order.total_amount),
            order_items="\n".join(order_items_text),
            payment_info=payment_info
        )
        
        # Можно ли повторить заказ
        can_repeat = order.status in ["completed", "ready"]
        
        await callback.message.edit_text(
            order_text,
            reply_markup=get_order_details_keyboard(order.id, can_repeat)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("repeat_order_"))
async def repeat_order(callback: CallbackQuery, state: FSMContext, user: User):
    """Повторить заказ"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.services.order import OrderService
        success = await OrderService.repeat_order(session, user.id, order_id)
        await session.commit()
        
        if success:
            await callback.answer("✅ Товары добавлены в корзину")
            
            # Переходим к корзине
            from app.handlers.user.cart import show_cart
            await show_cart(callback, state, user)
        else:
            await callback.answer("❌ Ошибка при повторении заказа", show_alert=True)


async def notify_admin_new_order(order):
    """Уведомить администратора о новом заказе"""
    # TODO: Реализовать отправку уведомления администратору
    logging.info(f"Новый заказ #{order.id} от пользователя {order.user_id}")


async def notify_admin_payment_received(order):
    """Уведомить администратора о получении оплаты"""
    # TODO: Реализовать отправку уведомления администратору
    logging.info(f"Получен платеж по заказу #{order.id}")


@router.callback_query(F.data == "back_to_orders")
async def back_to_orders(callback: CallbackQuery, state: FSMContext, user: User):
    """Вернуться к списку заказов"""
    async with async_session_maker() as session:
        from app.services.order import OrderService
        orders = await OrderService.get_user_orders(session, user.id)
        
        if not orders:
            await callback.message.edit_text(
                texts.NO_ORDERS,
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        await callback.message.edit_text(
            texts.ORDERS_LIST_MESSAGE,
            reply_markup=get_orders_keyboard(orders)
        )
        await callback.answer()
