from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, update, and_

from app.database import async_session_maker, Order, OrderItem, Dish, User, OrderStatus, PaymentStatus
from app.middlewares.admin import AdminMiddleware
from app.utils.texts import ADMIN_HELP, ORDER_STATUSES
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
        # Заказы ожидающие подтверждения оплаты
        result = await session.execute(
            select(Order)
            .where(Order.status == OrderStatus.PAYMENT_CONFIRMATION.value)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        
        if not orders:
            await callback.message.edit_text(
                "✅ Нет заказов ожидающих модерации",
                reply_markup={"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "admin_panel"}]]}
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
        
        keyboard.append([{"text": "🔙 Назад", "callback_data": "admin_panel"}])
        
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
    
    await callback.answer("🍽 Заказ отмечен как готовый!")
    await show_order_details(callback)  # Обновляем отображение заказа


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
                reply_markup={"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "admin_panel"}]]}
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
        
        keyboard.append([{"text": "🔙 Назад", "callback_data": "admin_panel"}])
        
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
            [{"text": "🔙 Назад", "callback_data": "admin_panel"}]
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
            select(Category).order_by(Category.order_index, Category.name)
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
                "text": f"📂 {category.name} ({'✅' if category.is_available else '❌'})",
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
            status = "✅ Доступна" if category.is_available else "❌ Скрыта"
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
            select(Category).order_by(Category.order_index, Category.name)
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
                    {"text": "➕ Добавить блюдо", "callback_data": f"add_dish_to_category_{category_id}"},
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
            {"text": "➕ Добавить блюдо", "callback_data": f"add_dish_to_category_{category_id}"}
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
                {"text": "✅ Показать" if not category.is_available else "❌ Скрыть", 
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
        
        status = "✅ Доступна" if category.is_available else "❌ Скрыта"
        
        await callback.message.edit_text(
            f"📂 <b>Категория: {category.name}</b>\n\n"
            f"📊 Статус: {status}\n"
            f"🔢 Порядок: {category.order_index}\n\n"
            "Выберите действие:",
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("edit_dish_"))
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
                {"text": "📝 Изменить цену", "callback_data": f"change_price_{dish_id}"},
                {"text": "📄 Изменить описание", "callback_data": f"change_description_{dish_id}"}
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
        category.is_available = not category.is_available
        await session.commit()
        
        status = "показана" if category.is_available else "скрыта"
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
