from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update, and_

from app.database import async_session_maker, Order, OrderItem, Dish, User, OrderStatus, PaymentStatus
from app.middlewares.admin import AdminMiddleware
from app.utils.texts import ADMIN_HELP, ORDER_STATUSES
from app.utils.states import AdminStates
from app.keyboards.user import get_main_menu_keyboard
from app.services.order import OrderService

router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель"""
    keyboard = [
        [
            {"text": "📋 Заказы на модерации", "callback_data": "admin_pending_orders"},
            {"text": "📊 Все заказы", "callback_data": "admin_all_orders"}
        ],
        [
            {"text": "📈 Статистика", "callback_data": "admin_stats"},
            {"text": "⚙️ Управление меню", "callback_data": "admin_menu"}
        ],
        [
            {"text": "🔙 Главное меню", "callback_data": "main_menu"}
        ]
    ]
    
    admin_keyboard = {"inline_keyboard": keyboard}
    
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=admin_keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_pending_orders")
async def show_pending_orders(callback: CallbackQuery):
    """Показать заказы на модерации"""
    async with async_session_maker() as session:
        # Заказы ожидающие подтверждения оплаты или подтверждения админом
        result = await session.execute(
            select(Order)
            .where(Order.status.in_([
                OrderStatus.PAYMENT_CONFIRMATION.value,
                OrderStatus.PENDING_CONFIRMATION.value
            ]))
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        
        if not orders:
            await callback.message.edit_text(
                "✅ Нет заказов ожидающих модерации",
                reply_markup={"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}]]}
            )
            return
        
        text = "📋 <b>Заказы на модерации:</b>\n\n"
        keyboard = []
        
        for order in orders[:10]:  # Показываем первые 10
            # Получаем пользователя
            user_result = await session.execute(
                select(User).where(User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            username = f"@{user.username}" if user and user.username else f"ID: {user.telegram_id}" if user else "Неизвестен"
            
            text += (
                f"🔹 Заказ #{order.id}\n"
                f"👤 {username}\n"
                f"💰 {order.total_amount} ₽\n"
                f"⏰ {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            )
            
            keyboard.append([
                {"text": f"📋 Заказ #{order.id}", "callback_data": f"admin_order_{order.id}"}
            ])
        
        keyboard.append([{"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}])
        
        await callback.message.edit_text(
            text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("admin_order_"))
async def show_order_details(callback: CallbackQuery):
    """Показать детали заказа"""
    order_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        # Получаем заказ
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            await callback.answer("❌ Заказ не найден")
            return
        
        # Получаем пользователя
        user_result = await session.execute(
            select(User).where(User.id == order.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        # Получаем позиции заказа
        items_result = await session.execute(
            select(OrderItem, Dish)
            .join(Dish)
            .where(OrderItem.order_id == order_id)
        )
        order_items = items_result.all()
        
        username = f"@{user.username}" if user and user.username else f"ID: {user.telegram_id}" if user else "Неизвестен"
        
        text = (
            f"📋 <b>Заказ #{order.id}</b>\n\n"
            f"👤 <b>Клиент:</b> {username}\n"
            f"💰 <b>Сумма:</b> {order.total_amount} ₽\n"
            f"📅 <b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 <b>Статус:</b> {ORDER_STATUSES.get(order.status, order.status)}\n"
        )
        
        if order.payment_method:
            text += f"💳 <b>Способ оплаты:</b> {'Карта' if order.payment_method == 'card' else 'Наличные'}\n"
        
        if order.notes:
            text += f"📝 <b>Комментарий:</b> {order.notes}\n"
        
        text += "\n<b>Состав заказа:</b>\n"
        for item, dish in order_items:
            text += f"• {dish.name} x{item.quantity} = {item.total_price} ₽\n"
        
        keyboard = []
        
        # Кнопки действий в зависимости от статуса
        if order.status == OrderStatus.PAYMENT_CONFIRMATION.value:
            keyboard.extend([
                [{"text": "✅ Подтвердить оплату", "callback_data": f"confirm_payment_{order_id}"}],
                [{"text": "❌ Отклонить оплату", "callback_data": f"reject_payment_{order_id}"}]
            ])
        elif order.status == OrderStatus.PENDING_CONFIRMATION.value:
            keyboard.extend([
                [{"text": "✅ Подтвердить заказ", "callback_data": f"confirm_order_{order_id}"}],
                [{"text": "❌ Отклонить заказ", "callback_data": f"reject_order_{order_id}"}]
            ])
        elif order.status == OrderStatus.CONFIRMED.value:
            keyboard.append([{"text": "🍽 Заказ готов", "callback_data": f"set_status_{order_id}_ready"}])
        elif order.status == OrderStatus.READY.value:
            keyboard.append([{"text": "✅ Заказ выдан", "callback_data": f"set_status_{order_id}_completed"}])
        
        # Общая кнопка изменения статуса
        keyboard.append([{"text": "📊 Изменить статус", "callback_data": f"change_status_{order_id}"}])
        
        # Кнопка отмены заказа (если он не завершен)
        if order.status not in [OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value]:
            keyboard.append([{"text": "🚫 Отменить заказ", "callback_data": f"set_status_{order_id}_cancelled"}])
        
        keyboard.append([{"text": "🔙 К заказам", "callback_data": "admin_pending_orders"}])
        
        await callback.message.edit_text(
            text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_complete_"))
async def complete_order(callback: CallbackQuery):
    """Завершить заказ"""
    order_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.COMPLETED.value)
        )
        await session.commit()
    
    await callback.answer("✅ Заказ завершен!")
    await show_order_details(callback)  # Обновляем отображение заказа


@router.callback_query(F.data.startswith("admin_cancel_"))
async def cancel_order(callback: CallbackQuery):
    """Отменить заказ"""
    order_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.CANCELLED.value)
        )
        await session.commit()
        
        # Получаем заказ для уведомления
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            # Получаем пользователя для уведомления
            user_result = await session.execute(
                select(User).where(User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                try:
                    # Отправляем уведомление пользователю
                    await callback.bot.send_message(
                        user.telegram_id,
                        f"🚫 <b>Заказ отменен</b>\n\n"
                        f"К сожалению, ваш заказ #{order_id} был отменен.\n"
                        f"Если у вас есть вопросы, обратитесь к администратору.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass  # Игнорируем ошибки отправки
    
    await callback.answer("🚫 Заказ отменен!")
    await show_order_details(callback)  # Обновляем отображение заказа


@router.callback_query(F.data == "admin_all_orders")
async def show_all_orders(callback: CallbackQuery):
    """Показать все заказы"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Order)
            .where(Order.status != OrderStatus.CART.value)
            .order_by(Order.created_at.desc())
            .limit(20)
        )
        orders = result.scalars().all()
        
        if not orders:
            await callback.message.edit_text(
                "📋 Заказов пока нет",
                reply_markup={"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}]]}
            )
            return
        
        text = "📋 <b>Последние заказы:</b>\n\n"
        keyboard = []
        
        for order in orders:
            # Получаем пользователя
            user_result = await session.execute(
                select(User).where(User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            username = f"@{user.username}" if user and user.username else f"ID: {user.telegram_id}" if user else "Неизвестен"
            status_emoji = {
                OrderStatus.PENDING_PAYMENT.value: "⏳",
                OrderStatus.PAYMENT_CONFIRMATION.value: "🔍",
                OrderStatus.CONFIRMED.value: "✅",
                OrderStatus.READY.value: "🍽",
                OrderStatus.COMPLETED.value: "✅",
                OrderStatus.CANCELLED.value: "❌"
            }.get(order.status, "❓")
            
            text += (
                f"{status_emoji} Заказ #{order.id} | {order.total_amount} ₽\n"
                f"👤 {username} | {order.created_at.strftime('%d.%m %H:%M')}\n\n"
            )
            
            keyboard.append([
                {"text": f"📋 Заказ #{order.id}", "callback_data": f"admin_order_{order.id}"}
            ])
        
        keyboard.append([{"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}])
        
        await callback.message.edit_text(
            text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    async with async_session_maker() as session:
        # Общая статистика заказов
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Статистика за сегодня
        today_orders = await session.execute(
            select(func.count(Order.id), func.sum(Order.total_amount))
            .where(
                and_(
                    func.date(Order.created_at) == today,
                    Order.status.in_([
                        OrderStatus.CONFIRMED.value,
                        OrderStatus.READY.value,
                        OrderStatus.COMPLETED.value
                    ])
                )
            )
        )
        today_count, today_sum = today_orders.first()
        today_sum = today_sum or 0
        
        # Статистика за неделю
        week_orders = await session.execute(
            select(func.count(Order.id), func.sum(Order.total_amount))
            .where(
                and_(
                    func.date(Order.created_at) >= week_ago,
                    Order.status.in_([
                        OrderStatus.CONFIRMED.value,
                        OrderStatus.READY.value,
                        OrderStatus.COMPLETED.value
                    ])
                )
            )
        )
        week_count, week_sum = week_orders.first()
        week_sum = week_sum or 0
        
        # Статистика за месяц
        month_orders = await session.execute(
            select(func.count(Order.id), func.sum(Order.total_amount))
            .where(
                and_(
                    func.date(Order.created_at) >= month_ago,
                    Order.status.in_([
                        OrderStatus.CONFIRMED.value,
                        OrderStatus.READY.value,
                        OrderStatus.COMPLETED.value
                    ])
                )
            )
        )
        month_count, month_sum = month_orders.first()
        month_sum = month_sum or 0
        
        # Статистика по статусам
        pending_orders = await session.execute(
            select(func.count(Order.id))
            .where(Order.status == OrderStatus.PAYMENT_CONFIRMATION.value)
        )
        pending_count = pending_orders.scalar()
        
        text = (
            "📈 <b>Статистика заказов</b>\n\n"
            f"📅 <b>За сегодня:</b>\n"
            f"• Заказов: {today_count}\n"
            f"• Сумма: {today_sum} ₽\n\n"
            f"📊 <b>За неделю:</b>\n"
            f"• Заказов: {week_count}\n"
            f"• Сумма: {week_sum} ₽\n\n"
            f"📊 <b>За месяц:</b>\n"
            f"• Заказов: {month_count}\n"
            f"• Сумма: {month_sum} ₽\n\n"
            f"🔍 <b>На модерации:</b> {pending_count} заказов"
        )
        
        keyboard = [
            [{"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_menu")
async def show_menu_management(callback: CallbackQuery):
    """Показать управление меню"""
    keyboard = [
        [
            {"text": "📂 Категории", "callback_data": "admin_categories"},
            {"text": "🍽 Блюда", "callback_data": "admin_dishes"}
        ],
        [
            {"text": "➕ Добавить категорию", "callback_data": "add_category"},
            {"text": "➕ Добавить блюдо", "callback_data": "add_dish"}
        ],
        [
            {"text": "🔙 Назад в админ-панель", "callback_data": "back_to_admin_panel"}
        ]
    ]
    
    menu_keyboard = {"inline_keyboard": keyboard}
    
    await callback.message.edit_text(
        "⚙️ <b>Управление меню</b>\n\n"
        "Выберите действие:",
        reply_markup=menu_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_categories")
async def show_categories_list(callback: CallbackQuery):
    """Показать список категорий"""
    async with async_session_maker() as session:
        from app.database import Category
        
        result = await session.execute(
            select(Category).order_by(Category.sort_order, Category.name)
        )
        categories = result.scalars().all()
        
        if not categories:
            await callback.message.edit_text(
                "📂 <b>Категории</b>\n\n"
                "❌ Категории не найдены",
                reply_markup={"inline_keyboard": [[
                    {"text": "➕ Добавить категорию", "callback_data": "add_category"},
                    {"text": "🔙 Назад", "callback_data": "admin_menu"}
                ]]},
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        # Формируем список категорий
        keyboard = []
        for category in categories:
            keyboard.append([{
                "text": f"📂 {category.name} ({'✅' if category.is_active else '❌'})",
                "callback_data": f"edit_category_{category.id}"
            }])
        
        keyboard.append([
            {"text": "➕ Добавить категорию", "callback_data": "add_category"}
        ])
        keyboard.append([
            {"text": "🔙 Назад", "callback_data": "admin_menu"}
        ])
        
        categories_text = "📂 <b>Категории</b>\n\n"
        for category in categories:
            status = "✅ Доступна" if category.is_active else "❌ Скрыта"
            categories_text += f"• {category.name} - {status}\n"
        
        await callback.message.edit_text(
            categories_text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data == "admin_dishes")
async def show_dishes_list(callback: CallbackQuery):
    """Показать список блюд"""
    async with async_session_maker() as session:
        from app.database import Category
        
        result = await session.execute(
            select(Category).order_by(Category.sort_order, Category.name)
        )
        categories = result.scalars().all()
        
        if not categories:
            await callback.message.edit_text(
                "🍽 <b>Блюда</b>\n\n"
                "❌ Сначала создайте категории",
                reply_markup={"inline_keyboard": [[
                    {"text": "➕ Добавить категорию", "callback_data": "add_category"},
                    {"text": "🔙 Назад", "callback_data": "admin_menu"}
                ]]},
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        # Формируем список категорий для выбора
        keyboard = []
        for category in categories:
            keyboard.append([{
                "text": f"📂 {category.name}",
                "callback_data": f"dishes_in_category_{category.id}"
            }])
        
        keyboard.append([
            {"text": "➕ Добавить блюдо", "callback_data": "add_dish"}
        ])
        keyboard.append([
            {"text": "🔙 Назад", "callback_data": "admin_menu"}
        ])
        
        await callback.message.edit_text(
            "🍽 <b>Блюда по категориям</b>\n\n"
            "Выберите категорию:",
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("dishes_in_category_"))
async def show_dishes_in_category(callback: CallbackQuery):
    """Показать блюда в категории"""
    category_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Category
        
        # Получаем категорию
        category_result = await session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = category_result.scalar_one_or_none()
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Получаем блюда в категории
        dishes_result = await session.execute(
            select(Dish).where(Dish.category_id == category_id).order_by(Dish.name)
        )
        dishes = dishes_result.scalars().all()
        
        if not dishes:
            await callback.message.edit_text(
                f"🍽 <b>Блюда в категории \"{category.name}\"</b>\n\n"
                "❌ Блюда не найдены",
                reply_markup={"inline_keyboard": [[
                    {"text": "➕ Добавить блюдо", "callback_data": f"add_dish_{category_id}"},
                    {"text": "🔙 Назад", "callback_data": "admin_dishes"}
                ]]},
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        # Формируем список блюд
        keyboard = []
        for dish in dishes:
            keyboard.append([{
                "text": f"🍽 {dish.name} ({'✅' if dish.is_available else '❌'}) - {dish.price}₽",
                "callback_data": f"edit_dish_{dish.id}"
            }])
        
        keyboard.append([
            {"text": "➕ Добавить блюдо", "callback_data": f"add_dish_{category_id}"}
        ])
        keyboard.append([
            {"text": "🔙 Назад", "callback_data": "admin_dishes"}
        ])
        
        dishes_text = f"🍽 <b>Блюда в категории \"{category.name}\"</b>\n\n"
        for dish in dishes:
            status = "✅ Доступно" if dish.is_available else "❌ Скрыто"
            dishes_text += f"• {dish.name} - {dish.price}₽ ({status})\n"
        
        await callback.message.edit_text(
            dishes_text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("edit_category_"))
async def edit_category(callback: CallbackQuery):
    """Редактировать категорию"""
    category_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.database import Category
        
        result = await session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        keyboard = [
            [
                {"text": "✅ Показать" if not category.is_active else "❌ Скрыть", 
                 "callback_data": f"toggle_category_{category_id}"}
            ],
            [
                {"text": "📝 Переименовать", "callback_data": f"rename_category_{category_id}"},
                {"text": "🗑 Удалить", "callback_data": f"delete_category_{category_id}"}
            ],
            [
                {"text": "🔙 Назад", "callback_data": "admin_categories"}
            ]
        ]
        
        status = "✅ Доступна" if category.is_active else "❌ Скрыта"
        
        await callback.message.edit_text(
            f"📂 <b>Категория: {category.name}</b>\n\n"
            f"📊 Статус: {status}\n"
            f"🔢 Порядок: {category.sort_order}\n\n"
            "Выберите действие:",
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.regexp(r"^edit_dish_\d+$"))
async def edit_dish(callback: CallbackQuery):
    """Редактировать блюдо"""
    dish_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Dish).where(Dish.id == dish_id)
        )
        dish = result.scalar_one_or_none()
        
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        keyboard = [
            [
                {"text": "✅ Показать" if not dish.is_available else "❌ Скрыть", 
                 "callback_data": f"toggle_dish_{dish_id}"}
            ],
            [
                {"text": "� Изменить цену", "callback_data": f"edit_dish_price_{dish_id}"},
                {"text": "📄 Изменить описание", "callback_data": f"edit_dish_description_{dish_id}"}
            ],
            [
                {"text": "🗑 Удалить", "callback_data": f"delete_dish_{dish_id}"}
            ],
            [
                {"text": "🔙 Назад", "callback_data": f"dishes_in_category_{dish.category_id}"}
            ]
        ]
        
        status = "✅ Доступно" if dish.is_available else "❌ Скрыто"
        
        await callback.message.edit_text(
            f"🍽 <b>{dish.name}</b>\n\n"
            f"💰 Цена: {dish.price}₽\n"
            f"📊 Статус: {status}\n"
            f"📄 Описание: {dish.description or 'Не указано'}\n\n"
            "Выберите действие:",
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("toggle_category_"))
async def toggle_category_availability(callback: CallbackQuery):
    """Переключить доступность категории"""
    category_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.database import Category
        
        result = await session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Переключаем доступность
        category.is_active = not category.is_active
        await session.commit()
        
        status = "показана" if category.is_active else "скрыта"
        await callback.answer(f"✅ Категория {status}!", show_alert=True)
        
        # Обновляем отображение
        await edit_category(callback)


@router.callback_query(F.data.startswith("toggle_dish_"))
async def toggle_dish_availability(callback: CallbackQuery):
    """Переключить доступность блюда"""
    dish_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Dish).where(Dish.id == dish_id)
        )
        dish = result.scalar_one_or_none()
        
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        # Переключаем доступность
        dish.is_available = not dish.is_available
        await session.commit()
        
        status = "показано" if dish.is_available else "скрыто"
        await callback.answer(f"✅ Блюдо {status}!", show_alert=True)
        
        # Обновляем отображение
        await edit_dish(callback)


@router.callback_query(F.data == "back_to_admin_panel")
async def back_to_admin_panel(callback: CallbackQuery):
    """Вернуться в админ-панель"""
    keyboard = [
        [
            {"text": "📋 Заказы на модерации", "callback_data": "admin_pending_orders"},
            {"text": "📊 Все заказы", "callback_data": "admin_all_orders"}
        ],
        [
            {"text": "📈 Статистика", "callback_data": "admin_stats"},
            {"text": "⚙️ Управление меню", "callback_data": "admin_menu"}
        ],
        [
            {"text": "🔙 Главное меню", "callback_data": "main_menu"}
        ]
    ]
    
    admin_keyboard = {"inline_keyboard": keyboard}
    
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=admin_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: CallbackQuery):
    """Подтвердить оплату заказа"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status="confirmed")
        )
        
        if result.rowcount > 0:
            await session.commit()
            
            # Получаем заказ для уведомления пользователя
            order_result = await session.execute(
                select(Order, User)
                .join(User)
                .where(Order.id == order_id)
            )
            order, user = order_result.first()
            
            # Уведомляем пользователя об изменении статуса
            from app.services.notifications import NotificationService
            await NotificationService.notify_order_status_change(
                callback.bot, order, user, "payment_confirmation", "confirmed"
            )
            
            await callback.answer("✅ Оплата подтверждена!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка подтверждения", show_alert=True)
    
    # Обновляем список заказов
    await show_pending_orders(callback)


@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment(callback: CallbackQuery):
    """Отклонить оплату заказа"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status="cancelled")
        )
        
        if result.rowcount > 0:
            await session.commit()
            
            # Получаем заказ для уведомления пользователя
            order_result = await session.execute(
                select(Order, User)
                .join(User)
                .where(Order.id == order_id)
            )
            order, user = order_result.first()
            
            # Уведомляем пользователя об отклонении
            from app.services.notifications import NotificationService
            await NotificationService.notify_order_status_change(
                callback.bot, order, user, "payment_confirmation", "cancelled"
            )
            
            await callback.answer("❌ Оплата отклонена", show_alert=True)
        else:
            await callback.answer("❌ Ошибка отклонения", show_alert=True)
    
    # Обновляем список заказов
    await show_pending_orders(callback)


@router.callback_query(F.data.startswith("change_status_"))
async def change_order_status(callback: CallbackQuery):
    """Показать меню изменения статуса заказа"""
    order_id = int(callback.data.split("_")[2])
    
    # Клавиатура со статусами
    keyboard = [
        [{"text": "⏳ Подтвержден", "callback_data": f"set_status_{order_id}_confirmed"}],
        [{"text": "🍽 Готовится", "callback_data": f"set_status_{order_id}_ready"}],
        [{"text": "✅ Готов", "callback_data": f"set_status_{order_id}_completed"}],
        [{"text": "❌ Отменить", "callback_data": f"set_status_{order_id}_cancelled"}],
        [{"text": "🔙 Назад", "callback_data": "admin_all_orders"}]
    ]
    
    await callback.message.edit_text(
        f"📊 Изменение статуса заказа #{order_id}\n\n"
        "Выберите новый статус:",
        reply_markup={"inline_keyboard": keyboard}
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_status_"))
async def set_order_status(callback: CallbackQuery):
    """Установить новый статус заказа"""
    parts = callback.data.split("_")
    order_id = int(parts[2])
    new_status = parts[3]
    
    async with async_session_maker() as session:
        # Получаем текущий статус
        current_order = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = current_order.scalar_one_or_none()
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        old_status = order.status
        
        # Обновляем статус
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=new_status)
        )
        await session.commit()
        
        # Получаем пользователя для уведомления
        user_result = await session.execute(
            select(User).where(User.id == order.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            # Уведомляем пользователя об изменении статуса
            from app.services.notifications import NotificationService
            await NotificationService.notify_order_status_change(
                callback.bot, order, user, old_status, new_status
            )
            
        status_names = {
            "confirmed": "Подтвержден",
            "ready": "Готовится", 
            "completed": "Готов",
            "cancelled": "Отменен"
        }
        
        await callback.answer(
            f"✅ Статус изменен на: {status_names.get(new_status, new_status)}", 
            show_alert=True
        )
    
    # Возвращаемся к списку заказов
    await show_all_orders(callback)


@router.callback_query(F.data.startswith("confirm_order_"))
async def confirm_cash_order(callback: CallbackQuery):
    """Подтвердить заказ с оплатой наличными"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status="confirmed")
        )
        
        if result.rowcount > 0:
            await session.commit()
            
            # Получаем заказ для уведомления пользователя
            order_result = await session.execute(
                select(Order, User)
                .join(User)
                .where(Order.id == order_id)
            )
            order, user = order_result.first()
            
            # Уведомляем пользователя об изменении статуса
            from app.services.notifications import NotificationService
            await NotificationService.notify_order_status_change(
                callback.bot, order, user, "pending_confirmation", "confirmed"
            )
            
            await callback.answer("✅ Заказ подтвержден!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка подтверждения", show_alert=True)
    
    # Обновляем список заказов
    await show_pending_orders(callback)


@router.callback_query(F.data.startswith("reject_order_"))
async def reject_cash_order(callback: CallbackQuery):
    """Отклонить заказ с оплатой наличными"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status="cancelled")
        )
        
        if result.rowcount > 0:
            await session.commit()
            
            # Получаем заказ для уведомления пользователя
            order_result = await session.execute(
                select(Order, User)
                .join(User)
                .where(Order.id == order_id)
            )
            order, user = order_result.first()
            
            # Уведомляем пользователя об отклонении
            from app.services.notifications import NotificationService
            await NotificationService.notify_order_status_change(
                callback.bot, order, user, "pending_confirmation", "cancelled"
            )
            
            await callback.answer("❌ Заказ отклонен", show_alert=True)
        else:
            await callback.answer("❌ Ошибка отклонения", show_alert=True)
    
    # Обновляем список заказов
    await show_pending_orders(callback)


# === УПРАВЛЕНИЕ КАТЕГОРИЯМИ ===

@router.callback_query(F.data == "add_category")
async def add_category_start(callback: CallbackQuery, state: FSMContext):
    """Начать добавление новой категории"""
    await callback.message.edit_text(
        "📂 <b>Добавление новой категории</b>\n\n"
        "Введите название категории:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.ENTERING_CATEGORY_NAME)
    await callback.answer()


@router.message(StateFilter(AdminStates.ENTERING_CATEGORY_NAME))
async def handle_category_name_input(message: Message, state: FSMContext):
    """Обработать ввод названия категории (создание или переименование)"""
    category_name = message.text.strip()
    
    if len(category_name) < 2 or len(category_name) > 100:
        await message.answer(
            "❌ Название категории должно быть от 2 до 100 символов.\n"
            "Попробуйте еще раз:"
        )
        return
    
    data = await state.get_data()
    category_id = data.get("category_id")
    
    async with async_session_maker() as session:
        from app.database import Category
        
        if category_id:
            # Переименование существующей категории
            category = await session.get(Category, category_id)
            if not category:
                await message.answer("❌ Категория не найдена")
                await state.clear()
                return
            
            # Проверяем, что категория с таким именем не существует
            existing = await session.execute(
                select(Category).where(Category.name == category_name, Category.id != category_id)
            )
            if existing.scalar_one_or_none():
                await message.answer(
                    "❌ Категория с таким названием уже существует.\n"
                    "Введите другое название:"
                )
                return
            
            old_name = category.name
            category.name = category_name
            await session.commit()
            
            await message.answer(
                f"✅ Категория '{old_name}' переименована в '{category_name}'!",
                reply_markup={"inline_keyboard": [[
                    {"text": "📂 К списку категорий", "callback_data": "admin_categories"}
                ]]}
            )
        else:
            # Создание новой категории
            # Проверяем, что категория с таким именем не существует
            existing = await session.execute(
                select(Category).where(Category.name == category_name)
            )
            if existing.scalar_one_or_none():
                await message.answer(
                    "❌ Категория с таким названием уже существует.\n"
                    "Введите другое название:"
                )
                return
            
            # Создаем новую категорию
            new_category = Category(
                name=category_name,
                is_active=True,
                sort_order=0
            )
            session.add(new_category)
            await session.commit()
            
            await message.answer(
                f"✅ Категория '{category_name}' успешно добавлена!",
                reply_markup={"inline_keyboard": [[
                    {"text": "📂 К списку категорий", "callback_data": "admin_categories"}
                ]]}
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("rename_category_"))
async def rename_category_start(callback: CallbackQuery, state: FSMContext):
    """Начать переименование категории"""
    category_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.database import Category
        category = await session.get(Category, category_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"📂 <b>Переименование категории</b>\n\n"
            f"Текущее название: <b>{category.name}</b>\n\n"
            f"Введите новое название:",
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.ENTERING_CATEGORY_NAME)
        await state.update_data(category_id=category_id)
        await callback.answer()


@router.callback_query(F.data.startswith("delete_category_"))
async def delete_category_confirm(callback: CallbackQuery):
    """Подтвердить удаление категории"""
    category_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.database import Category, Dish
        
        category = await session.get(Category, category_id)
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Проверяем, есть ли блюда в категории
        dishes_result = await session.execute(
            select(Dish).where(Dish.category_id == category_id)
        )
        dishes_count = len(dishes_result.scalars().all())
        
        warning_text = ""
        if dishes_count > 0:
            warning_text = f"\n\n⚠️ В категории {dishes_count} блюд. Они также будут удалены!"
        
        await callback.message.edit_text(
            f"🗑 <b>Удаление категории</b>\n\n"
            f"Вы действительно хотите удалить категорию <b>'{category.name}'</b>?{warning_text}",
            reply_markup={"inline_keyboard": [
                [
                    {"text": "✅ Да, удалить", "callback_data": f"confirm_delete_category_{category_id}"},
                    {"text": "❌ Отмена", "callback_data": "admin_categories"}
                ]
            ]},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_category_"))
async def delete_category_execute(callback: CallbackQuery):
    """Выполнить удаление категории"""
    category_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Category, Dish
        
        category = await session.get(Category, category_id)
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        category_name = category.name
        
        # Сначала удаляем все блюда этой категории
        dishes_result = await session.execute(
            select(Dish).where(Dish.category_id == category_id)
        )
        dishes = dishes_result.scalars().all()
        
        # Удаляем каждое блюдо
        for dish in dishes:
            await session.delete(dish)
        
        # Теперь удаляем саму категорию
        await session.delete(category)
        await session.commit()
        
        dishes_count = len(dishes)
        dishes_text = f" и {dishes_count} блюд" if dishes_count > 0 else ""
        
        await callback.message.edit_text(
            f"✅ Категория '{category_name}'{dishes_text} успешно удалены!",
            reply_markup={"inline_keyboard": [[
                {"text": "📂 К списку категорий", "callback_data": "admin_categories"}
            ]]}
        )
        await callback.answer()


# === УПРАВЛЕНИЕ БЛЮДАМИ ===

@router.callback_query(F.data == "add_dish")
async def choose_category_for_dish(callback: CallbackQuery):
    """Выбрать категорию для нового блюда"""
    async with async_session_maker() as session:
        from app.database import Category
        
        categories_result = await session.execute(
            select(Category).where(Category.is_active == True).order_by(Category.sort_order, Category.name)
        )
        categories = categories_result.scalars().all()
        
        if not categories:
            await callback.answer("❌ Нет активных категорий", show_alert=True)
            return
        
        keyboard = []
        for category in categories:
            keyboard.append([{
                "text": f"📂 {category.name}",
                "callback_data": f"add_dish_{category.id}"
            }])
        
        keyboard.append([
            {"text": "🔙 Назад", "callback_data": "admin_menu"}
        ])
        
        await callback.message.edit_text(
            "🍽 <b>Добавление блюда</b>\n\n"
            "Выберите категорию для нового блюда:",
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("add_dish_"))
async def add_dish_start(callback: CallbackQuery, state: FSMContext):
    """Начать добавление нового блюда"""
    category_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.database import Category
        category = await session.get(Category, category_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"🍽 <b>Добавление нового блюда</b>\n\n"
            f"Категория: <b>{category.name}</b>\n\n"
            f"Введите название блюда:",
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.ENTERING_DISH_NAME)
        await state.update_data(category_id=category_id)
        await callback.answer()


@router.message(StateFilter(AdminStates.ENTERING_DISH_NAME))
async def add_dish_name(message: Message, state: FSMContext):
    """Получить название нового блюда"""
    dish_name = message.text.strip()
    
    if len(dish_name) < 2 or len(dish_name) > 150:
        await message.answer(
            "❌ Название блюда должно быть от 2 до 150 символов.\n"
            "Попробуйте еще раз:"
        )
        return
    
    await state.update_data(dish_name=dish_name)
    await state.set_state(AdminStates.ENTERING_DISH_PRICE)
    await message.answer(
        f"💰 Введите цену блюда '{dish_name}' (только число, например: 350):"
    )


@router.message(StateFilter(AdminStates.ENTERING_DISH_PRICE))
async def handle_dish_price_input(message: Message, state: FSMContext):
    """Обработать ввод цены блюда (создание или редактирование)"""
    try:
        new_price = float(message.text.strip())
        if new_price <= 0 or new_price > 100000:
            await message.answer(
                "❌ Цена должна быть положительным числом до 100000.\n"
                "Введите цену еще раз:"
            )
            return
    except ValueError:
        await message.answer(
            "❌ Неверный формат цены. Введите число (например: 350):"
        )
        return
    
    data = await state.get_data()
    dish_id = data.get("dish_id")
    
    if dish_id:
        # Редактирование существующего блюда
        async with async_session_maker() as session:
            from app.database import Dish
            
            dish = await session.get(Dish, dish_id)
            if not dish:
                await message.answer("❌ Блюдо не найдено")
                await state.clear()
                return
            
            old_price = dish.price
            dish.price = new_price
            await session.commit()
            
            await message.answer(
                f"✅ Цена блюда '{dish.name}' изменена с {old_price} ₽ на {new_price} ₽!",
                reply_markup={"inline_keyboard": [[
                    {"text": "🍽 К редактированию блюда", "callback_data": f"edit_dish_{dish_id}"}
                ]]}
            )
        await state.clear()
    else:
        # Создание нового блюда
        await state.update_data(dish_price=new_price)
        await state.set_state(AdminStates.ENTERING_DISH_DESCRIPTION)
        await message.answer(
            "📝 Введите описание блюда (или отправьте '-' чтобы пропустить):"
        )


@router.message(StateFilter(AdminStates.ENTERING_DISH_DESCRIPTION))
async def handle_dish_description_input(message: Message, state: FSMContext):
    """Обработать ввод описания блюда (создание или редактирование)"""
    new_description = message.text.strip()
    if new_description == "-":
        new_description = None
    elif len(new_description) > 500:
        await message.answer(
            "❌ Описание слишком длинное (максимум 500 символов).\n"
            "Введите описание еще раз:"
        )
        return
    
    data = await state.get_data()
    dish_id = data.get("dish_id")
    
    if dish_id:
        # Редактирование существующего блюда
        async with async_session_maker() as session:
            from app.database import Dish
            
            dish = await session.get(Dish, dish_id)
            if not dish:
                await message.answer("❌ Блюдо не найдено")
                await state.clear()
                return
            
            dish.description = new_description
            await session.commit()
            
            desc_text = new_description or "удалено"
            await message.answer(
                f"✅ Описание блюда '{dish.name}' изменено!\n"
                f"📝 Новое описание: {desc_text}",
                reply_markup={"inline_keyboard": [[
                    {"text": "🍽 К редактированию блюда", "callback_data": f"edit_dish_{dish_id}"}
                ]]}
            )
        await state.clear()
    else:
        # Создание нового блюда
        category_id = data.get("category_id")
        dish_name = data.get("dish_name")
        dish_price = data.get("dish_price")
        
        async with async_session_maker() as session:
            from app.database import Dish
            
            # Проверяем, что блюдо с таким именем не существует в этой категории
            existing = await session.execute(
                select(Dish).where(Dish.name == dish_name, Dish.category_id == category_id)
            )
            if existing.scalar_one_or_none():
                await message.answer(
                    "❌ Блюдо с таким названием уже существует в этой категории.\n"
                    "Введите другое название:"
                )
                await state.set_state(AdminStates.ENTERING_DISH_NAME)
                return
            
            # Создаем новое блюдо
            new_dish = Dish(
                name=dish_name,
                description=new_description,
                price=dish_price,
                category_id=category_id,
                is_available=True,
                sort_order=0
            )
            session.add(new_dish)
            await session.commit()
            
            await message.answer(
                f"✅ Блюдо '{dish_name}' успешно добавлено!\n"
                f"💰 Цена: {dish_price} ₽\n"
                f"📝 Описание: {new_description or 'не указано'}",
                reply_markup={"inline_keyboard": [[
                    {"text": f"🍽 К блюдам категории", "callback_data": f"dishes_in_category_{category_id}"}
                ]]}
            )
        await state.clear()


@router.callback_query(F.data.startswith("edit_dish_price_"))
async def edit_dish_price_start(callback: CallbackQuery, state: FSMContext):
    """Начать изменение цены блюда"""
    dish_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Dish
        dish = await session.get(Dish, dish_id)
        
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"💰 <b>Изменение цены блюда</b>\n\n"
            f"Блюдо: <b>{dish.name}</b>\n"
            f"Текущая цена: <b>{dish.price} ₽</b>\n\n"
            f"Введите новую цену:",
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.ENTERING_DISH_PRICE)
        await state.update_data(dish_id=dish_id)
        await callback.answer()


@router.callback_query(F.data.startswith("edit_dish_description_"))
async def edit_dish_description_start(callback: CallbackQuery, state: FSMContext):
    """Начать изменение описания блюда"""
    dish_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Dish
        dish = await session.get(Dish, dish_id)
        
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        current_desc = dish.description or "не указано"
        await callback.message.edit_text(
            f"📝 <b>Изменение описания блюда</b>\n\n"
            f"Блюдо: <b>{dish.name}</b>\n"
            f"Текущее описание: <b>{current_desc}</b>\n\n"
            f"Введите новое описание (или '-' чтобы удалить):",
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.ENTERING_DISH_DESCRIPTION)
        await state.update_data(dish_id=dish_id)
        await callback.answer()


@router.callback_query(F.data.startswith("delete_dish_"))
async def delete_dish_confirm(callback: CallbackQuery):
    """Подтвердить удаление блюда"""
    dish_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        from app.database import Dish
        
        dish = await session.get(Dish, dish_id)
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"🗑 <b>Удаление блюда</b>\n\n"
            f"Вы действительно хотите удалить блюдо <b>'{dish.name}'</b>?\n"
            f"💰 Цена: {dish.price} ₽",
            reply_markup={"inline_keyboard": [
                [
                    {"text": "✅ Да, удалить", "callback_data": f"confirm_delete_dish_{dish_id}"},
                    {"text": "❌ Отмена", "callback_data": f"edit_dish_{dish_id}"}
                ]
            ]},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_dish_"))
async def delete_dish_execute(callback: CallbackQuery):
    """Выполнить удаление блюда"""
    dish_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Dish, OrderItem
        
        dish = await session.get(Dish, dish_id)
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        dish_name = dish.name
        category_id = dish.category_id
        
        # Сначала удаляем все связанные order_items
        order_items_result = await session.execute(
            select(OrderItem).where(OrderItem.dish_id == dish_id)
        )
        order_items = order_items_result.scalars().all()
        
        # Удаляем каждый order_item
        for order_item in order_items:
            await session.delete(order_item)
        
        # Теперь удаляем само блюдо
        await session.delete(dish)
        await session.commit()
        
        await callback.message.edit_text(
            f"✅ Блюдо '{dish_name}' успешно удалено!",
            reply_markup={"inline_keyboard": [[
                {"text": "🍽 К блюдам категории", "callback_data": f"dishes_in_category_{category_id}"}
            ]]}
        )
        await callback.answer()
