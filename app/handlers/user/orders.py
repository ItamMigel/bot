"""Обработчики для работы с заказами пользователя"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.database import async_session_maker, Order, OrderItem, Dish, User, OrderStatus, PaymentStatus
from app.middlewares.admin import AdminMiddleware
from app.middlewares.auth import AuthMiddleware
from app.keyboards.user import (
    get_order_details_keyboard, get_orders_filter_keyboard
)

from app.utils import texts, UserStates
from app.utils.helpers import format_price, format_datetime
from app.keyboards.user import (
    get_main_menu_keyboard, get_payment_method_keyboard, 
    get_order_confirmation_keyboard, get_orders_keyboard,
    get_order_details_keyboard, get_orders_filter_keyboard
)
from app.database import async_session_maker, User, Order, OrderItem
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
        card_sber=settings.payment_card_sber,
        card_tinkoff=settings.payment_card_tinkoff,
        card_owner=settings.payment_card_owner,
        phone=settings.payment_phone,
        instructions=settings.payment_instructions
    )
    
    await callback.message.edit_text(payment_text, parse_mode="HTML")
    await callback.message.answer(texts.PAYMENT_SCREENSHOT_PROMPT)
    await callback.answer()
    await state.set_state(UserStates.UPLOADING_PAYMENT_SCREENSHOT)
    
    # Сохраняем ID заказа в состоянии
    await state.update_data(order_id=order.id)


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
    
    # Получаем file_id для повторного просмотра
    photo_file_id = message.photo[-1].file_id
    
    # Обновляем заказ
    async with async_session_maker() as session:
        from app.services.order import OrderService
        success = await OrderService.update_payment_screenshot(
            session, order_id, screenshot_path, photo_file_id
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
            
            # Уведомление о согласовании сроков доставки
            # await message.answer(texts.DELIVERY_TIMING_NOTICE)
            
            # Уведомляем администратора
            await notify_admin_payment_received(order, user, message.bot)
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


@router.callback_query(F.data.regexp(r"^cancel_order_\d+$"))
async def cancel_payment_order(callback: CallbackQuery, state: FSMContext, user: User):
    """Отменить заказ на этапе ожидания скриншота"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.services.order import OrderService
        
        # Получаем заказ для уведомления
        from sqlalchemy import select
        order_result = await session.execute(
            select(Order).where(Order.id == order_id, Order.user_id == user.id)
        )
        order = order_result.scalar_one_or_none()
        
        # Отменяем заказ
        success = await OrderService.cancel_order(session, order_id, user.id)
        await session.commit()
        
        if success:
            # Уведомляем администраторов об отмене
            if order:
                from app.services.notifications import NotificationService
                await NotificationService.notify_order_cancelled(callback.bot, order, user)
                
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
    
    await message.answer(
        "📋 Ваши заказы\n\nВыберите категорию:",
        reply_markup=get_orders_filter_keyboard()
    )


@router.callback_query(F.data.startswith("order_"))
async def show_order_details(callback: CallbackQuery, state: FSMContext, user: User):
    """Показать детали заказа"""
    order_id = int(callback.data.split("_")[1])
    
    # Очищаем состояние при переходе к деталям заказа
    await state.clear()
    
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
        
        # Добавляем пользовательское название если есть
        custom_name_line = ""
        if order.custom_name:
            custom_name_line = f"\n💾 Сохранено как: {order.custom_name}"
        
        order_text = texts.ORDER_DETAILS_MESSAGE.format(
            order_id=order.id,
            custom_name_line=custom_name_line,
            created_at=format_datetime(order.created_at),
            status=texts.ORDER_STATUSES.get(order.status, order.status),
            total_amount=format_price(order.total_amount),
            order_items="\n".join(order_items_text),
            payment_info=payment_info
        )
        
        # Можно ли повторить заказ (только завершенные заказы)
        can_repeat = order.status in [OrderStatus.COMPLETED.value]
        
        # Можно ли отменить заказ (только активные заказы)
        can_cancel = order.status in ["pending_payment", "payment_received"]
        
        await callback.message.edit_text(
            order_text,
            reply_markup=get_order_details_keyboard(order.id, can_repeat, can_cancel)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("repeat_order_"))
async def repeat_order_prompt_name(callback: CallbackQuery, state: FSMContext, user: User):
    """Предложить задать название для повторяемого заказа"""
    # Проверяем тип callback_data
    if callback.data.startswith("repeat_order_skip_"):
        # Это кнопка "пропустить"
        order_id = int(callback.data.split("_")[3])
        await _process_repeat_order(callback, state, user, order_id, custom_name=None)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    # Сохраняем order_id в состоянии
    await state.update_data(repeat_order_id=order_id)
    await state.set_state(UserStates.SETTING_CUSTOM_ORDER_NAME)
    
    await callback.message.edit_text(
        "📝 <b>Повторение заказа</b>\n\n"
        "Хотите задать название для этого заказа?\n"
        "Это поможет легко найти его в будущем.\n\n"
        "Отправьте название или нажмите 'Пропустить':",
        reply_markup={
            "inline_keyboard": [
                [{"text": "⏭ Пропустить", "callback_data": f"repeat_order_skip_{order_id}"}],
                [{"text": "🔙 Назад", "callback_data": f"order_{order_id}"}]
            ]
        },
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("repeat_order_skip_"))
async def repeat_order_skip_name(callback: CallbackQuery, state: FSMContext, user: User):
    """Повторить заказ без названия"""
    order_id = int(callback.data.split("_")[3])
    await _process_repeat_order(callback, state, user, order_id, custom_name=None)


@router.message(StateFilter(UserStates.SETTING_CUSTOM_ORDER_NAME))
async def process_custom_order_name(message: Message, state: FSMContext, user: User):
    """Обработка пользовательского названия заказа"""
    data = await state.get_data()
    order_id = data.get("repeat_order_id")
    
    if not order_id:
        await message.answer("❌ Ошибка: заказ не найден")
        await state.clear()
        return
    
    custom_name = message.text.strip()
    if len(custom_name) > 100:
        await message.answer("❌ Название слишком длинное. Максимум 100 символов.")
        return
    
    await _process_repeat_order(message, state, user, order_id, custom_name)


async def _process_repeat_order(callback_or_message, state: FSMContext, user: User, order_id: int, custom_name: str = None):
    """Внутренняя функция для повторения заказа"""
    async with async_session_maker() as session:
        from app.services.order import OrderService
        
        # Сохраняем название заказа если указано
        if custom_name:
            from sqlalchemy import update
            await session.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(custom_name=custom_name)
            )
            await session.commit()
        
        success = await OrderService.repeat_order(session, user.id, order_id)
        await session.commit()
        
        if success:
            message_text = "✅ Товары добавлены в корзину"
            if custom_name:
                message_text += f"\n📝 Заказ сохранен как: '{custom_name}'"
            
            await callback_or_message.answer(message_text)
            
            # Переходим к корзине
            from app.handlers.user.cart import show_cart
            await show_cart(callback_or_message, state, user)
        else:
            error_text = "❌ Ошибка при повторении заказа"
            if hasattr(callback_or_message, 'answer') and hasattr(callback_or_message.answer, '__code__') and 'show_alert' in callback_or_message.answer.__code__.co_varnames:
                await callback_or_message.answer(error_text, show_alert=True)
            else:
                await callback_or_message.answer(error_text)
    
    await state.clear()


async def notify_admin_new_order(order, user_obj=None, bot=None):
    """Уведомить администратора о новом заказе"""
    try:
        # Создаем новую сессию для получения полных данных заказа
        async with async_session_maker() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            # Получаем заказ с загруженными items и dish
            order_result = await session.execute(
                select(Order)
                .options(selectinload(Order.items).selectinload(OrderItem.dish))
                .where(Order.id == order.id)
            )
            full_order = order_result.scalar_one_or_none()
            
            if not full_order:
                logging.error(f"Заказ #{order.id} не найден в базе")
                return
            
            # Получаем пользователя если не передан
            if not user_obj:
                user_result = await session.execute(
                    select(User).where(User.id == full_order.user_id)
                )
                user_obj = user_result.scalar_one_or_none()
            
            if user_obj and bot:
                from app.services.notifications import NotificationService
                logging.info(f"Новый заказ #{full_order.id} от пользователя {user_obj.telegram_id}")
                await NotificationService.notify_new_order(bot, full_order, user_obj)
        
    except Exception as e:
        logging.error(f"Ошибка уведомления о новом заказе: {e}")


async def notify_admin_payment_received(order, user_obj=None, bot=None):
    """Уведомить администратора о получении оплаты"""
    try:
        # Создаем новую сессию для получения полных данных
        async with async_session_maker() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            # Получаем заказ с загруженными items
            order_result = await session.execute(
                select(Order)
                .options(selectinload(Order.items).selectinload(OrderItem.dish))
                .where(Order.id == order.id)
            )
            full_order = order_result.scalar_one_or_none()
            
            if not full_order:
                logging.error(f"Заказ #{order.id} не найден в базе")
                return
                
            # Получаем пользователя если не передан
            if not user_obj:
                user_result = await session.execute(
                    select(User).where(User.id == full_order.user_id)
                )
                user_obj = user_result.scalar_one_or_none()
            
            if user_obj and bot:
                from app.services.notifications import NotificationService
                logging.info(f"Получен платеж по заказу #{full_order.id}")
                await NotificationService.notify_payment_received(bot, full_order, user_obj)
        
    except Exception as e:
        logging.error(f"Ошибка уведомления о платеже: {e}")


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


@router.callback_query(F.data == "orders_active")
async def show_active_orders(callback: CallbackQuery, state: FSMContext, user: User):
    """Показать активные заказы"""
    async with async_session_maker() as session:
        from app.services.order import OrderService
        all_orders = await OrderService.get_user_orders(session, user.id)
        orders = [order for order in all_orders if order.is_active]
        
        if not orders:
            await callback.message.edit_text(
                "🔥 Активных заказов нет\n\nВсе ваши заказы завершены или отменены.",
                reply_markup=get_orders_filter_keyboard()
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            "🔥 Активные заказы:",
            reply_markup=get_orders_keyboard(orders, "active")
        )
        await callback.answer()


@router.callback_query(F.data == "orders_completed")
async def show_completed_orders(callback: CallbackQuery, state: FSMContext, user: User):
    """Показать завершенные заказы"""
    async with async_session_maker() as session:
        from app.services.order import OrderService
        all_orders = await OrderService.get_user_orders(session, user.id)
        orders = [order for order in all_orders if order.is_completed]
        
        if not orders:
            await callback.message.edit_text(
                "✅ Завершенных заказов нет\n\nВы еще не делали заказов или все они еще в процессе.",
                reply_markup=get_orders_filter_keyboard()
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            "✅ Завершенные заказы:",
            reply_markup=get_orders_keyboard(orders, "completed")
        )
        await callback.answer()


@router.callback_query(F.data == "orders_saved")
async def show_saved_orders(callback: CallbackQuery, state: FSMContext, user: User):
    """Показать сохраненные заказы"""
    async with async_session_maker() as session:
        from app.services.order import OrderService
        saved_orders = await OrderService.get_user_saved_orders(session, user.id)
        
        from app.keyboards.user import get_saved_orders_keyboard
        
        await callback.message.edit_text(
            "💾 Ваши сохраненные заказы:",
            reply_markup=get_saved_orders_keyboard(saved_orders)
        )
        await callback.answer()


@router.callback_query(F.data == "back_to_order_filters")
async def back_to_order_filters(callback: CallbackQuery, state: FSMContext, user: User):
    """Вернуться к фильтрам заказов"""
    await callback.message.edit_text(
        "📋 Ваши заказы\n\nВыберите категорию:",
        reply_markup=get_orders_filter_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("repeat_saved_order_"))
async def repeat_saved_order_directly(callback: CallbackQuery, state: FSMContext, user: User):
    """Быстро повторить сохраненный заказ (без запроса названия)"""
    order_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.services.order import OrderService
        
        # Проверяем, что заказ принадлежит пользователю и имеет custom_name
        order = await OrderService.get_order_details(session, order_id)
        if not order or order.user_id != user.id or not order.custom_name:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        success = await OrderService.repeat_order(session, user.id, order_id)
        await session.commit()
        
        if success:
            await callback.answer(f"✅ Заказ '{order.custom_name}' добавлен в корзину")
            
            # Переходим к корзине
            from app.handlers.user.cart import show_cart
            await show_cart(callback, state, user)
        else:
            await callback.answer("❌ Ошибка при повторении заказа", show_alert=True)


@router.callback_query(F.data == "orders_all")
async def show_all_orders(callback: CallbackQuery, state: FSMContext, user: User):
    """Показать все заказы"""
    async with async_session_maker() as session:
        from app.services.order import OrderService
        orders = await OrderService.get_user_orders(session, user.id)
        
        if not orders:
            await callback.message.edit_text(
                texts.NO_ORDERS,
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Назад", "callback_data": "back_to_orders"}],
                        [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
                    ]
                }
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            "📋 Все ваши заказы:",
            reply_markup=get_orders_keyboard(orders, "all")
        )
        await callback.answer()


@router.callback_query(F.data.regexp(r"^cancel_order_confirm_\d+$"))
async def confirm_cancel_order(callback: CallbackQuery, state: FSMContext, user: User):
    """Подтвердить отмену заказа"""
    order_id = int(callback.data.split("_")[3])
    
    # Показываем подтверждение
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да, отменить", 
                callback_data=f"cancel_order_final_{order_id}"
            ),
            InlineKeyboardButton(
                text="❌ Нет", 
                callback_data=f"order_details_{order_id}"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"❓ Вы действительно хотите отменить заказ #{order_id}?\n\n"
        f"Отменить можно только заказы в статусе 'Ожидает оплаты' или 'Оплачен, ожидает подтверждения'.",
        reply_markup=confirm_keyboard
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^cancel_order_final_\d+$"))
async def final_cancel_order(callback: CallbackQuery, state: FSMContext, user: User):
    """Финальная отмена заказа пользователем"""
    order_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.services.order import OrderService
        
        # Получаем заказ для уведомления
        from sqlalchemy import select
        order_result = await session.execute(
            select(Order).where(Order.id == order_id, Order.user_id == user.id)
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Проверяем, можно ли отменить заказ
        if order.status not in ["pending_payment", "payment_received"]:
            await callback.answer(
                "❌ Этот заказ нельзя отменить в текущем статусе", 
                show_alert=True
            )
            return
        
        # Отменяем заказ
        success = await OrderService.cancel_order(session, order_id, user.id)
        await session.commit()
        
        if success:
            # Уведомляем администраторов об отмене
            try:
                from app.config import settings
                if settings.notification_chat_id:
                    await callback.bot.send_message(
                        settings.notification_chat_id,
                        f"❌ Клиент отменил заказ #{order_id}\n\n"
                        f"👤 Пользователь: {user.first_name or 'Неизвестно'} "
                        f"(@{user.username or 'нет'})\n"
                        f"💰 Сумма: {order.total_amount} ₽\n"
                        f"📊 Был в статусе: {texts.ORDER_STATUSES.get(order.status, order.status)}"
                    )
            except Exception as e:
                print(f"Ошибка отправки уведомления админу: {e}")
                
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} отменён\n\n"
                f"Если была произведена оплата, я свяжусь с вами для возврата средств."
            )
            await callback.message.answer(
                "🏠 Добро пожаловать в главное меню!",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await callback.answer("❌ Ошибка при отмене заказа", show_alert=True)
    
    await state.set_state(UserStates.MAIN_MENU)


@router.callback_query(F.data == "no_action")
async def no_action_handler(callback: CallbackQuery):
    """Обработчик для неактивных кнопок"""
    await callback.answer("Это информационное сообщение", show_alert=False)
