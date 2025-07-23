from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update, and_
from datetime import datetime

from app.database import async_session_maker, Order, OrderItem, Dish, User, OrderStatus, PaymentStatus
from app.middlewares.admin import AdminMiddleware
from app.utils.texts import ADMIN_HELP, ORDER_STATUSES
from app.utils.states import AdminStates
from app.keyboards.user import get_main_menu_keyboard
from app.services.order import OrderService
from app.utils.helpers import format_datetime

router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель"""
    keyboard = [
        [
            {"text": "📋 Управление заказами", "callback_data": "admin_orders_menu"},
            {"text": "📊 Все заказы", "callback_data": "admin_all_orders"}
        ],
        [
            {"text": "📈 Статистика", "callback_data": "admin_stats"},
            {"text": "🍽 Управление меню", "callback_data": "admin_menu"}
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


@router.callback_query(F.data == "admin_orders_menu")
async def show_orders_menu(callback: CallbackQuery):
    """Показать меню управления заказами"""
    async with async_session_maker() as session:
        from sqlalchemy import func
        from app.database import Order
        
        # Подсчитываем заказы по статусам
        status_counts = {}
        for status in [
            OrderStatus.PENDING_PAYMENT.value,
            OrderStatus.PAYMENT_RECEIVED.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.READY.value,
            OrderStatus.COMPLETED.value
        ]:
            count = await session.execute(
                select(func.count(Order.id)).where(Order.status == status)
            )
            status_counts[status] = count.scalar() or 0
    
    text = "📋 <b>Управление заказами</b>\n\nВыберите фильтр:"
    
    keyboard = [
        [
            {"text": f"⏳ Ожидают оплаты ({status_counts.get(OrderStatus.PENDING_PAYMENT.value, 0)})", 
             "callback_data": f"filter_orders_{OrderStatus.PENDING_PAYMENT.value}"},
        ],
        [
            {"text": f"💰 Требуют подтверждения ({status_counts.get(OrderStatus.PAYMENT_RECEIVED.value, 0)})", 
             "callback_data": f"filter_orders_{OrderStatus.PAYMENT_RECEIVED.value}"},
        ],
        [
            {"text": f"👩‍🍳 В работе ({status_counts.get(OrderStatus.CONFIRMED.value, 0)})", 
             "callback_data": f"filter_orders_{OrderStatus.CONFIRMED.value}"},
        ],
        [
            {"text": f"🎉 Готовые ({status_counts.get(OrderStatus.READY.value, 0)})", 
             "callback_data": f"filter_orders_{OrderStatus.READY.value}"},
        ],
        [
            {"text": f"✅ Завершенные ({status_counts.get(OrderStatus.COMPLETED.value, 0)})", 
             "callback_data": f"filter_orders_{OrderStatus.COMPLETED.value}"},
        ],
        [
            {"text": "📊 Все заказы", "callback_data": "filter_orders_all"},
            {"text": "❌ Отмененные", "callback_data": "filter_orders_cancelled"}
        ],
        [
            {"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}
        ]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup={"inline_keyboard": keyboard},
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_orders_"))
async def show_filtered_orders(callback: CallbackQuery):
    """Показать заказы по выбранному фильтру"""
    # Правильно извлекаем filter_type - берем все после "filter_orders_"
    filter_type = callback.data.replace("filter_orders_", "")
    
    async with async_session_maker() as session:
        from sqlalchemy.orm import selectinload
        
        # Строим запрос в зависимости от фильтра
        query = select(Order).options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.dish)
        ).order_by(Order.created_at.desc()).limit(20)
        
        if filter_type == "all":
            title = "Все заказы"
        elif filter_type == "cancelled":
            title = "Отмененные заказы"
            query = query.where(Order.status.in_([
                OrderStatus.CANCELLED_BY_CLIENT.value,
                OrderStatus.CANCELLED_BY_MASTER.value
            ]))
        else:
            # Конкретный статус
            from app.utils.texts import ORDER_STATUSES
            title = f"Заказы: {ORDER_STATUSES.get(filter_type, filter_type)}"
            query = query.where(Order.status == filter_type)
        
        result = await session.execute(query)
        orders = result.scalars().all()
        
        if not orders:
            text = f"📋 <b>{title}</b>\n\n❌ Заказов не найдено"
        else:
            text = f"📋 <b>{title}</b>\n\n"
            
            for order in orders:
                from app.utils.helpers import format_price
                from app.utils.texts import ORDER_STATUSES
                
                status_text = ORDER_STATUSES.get(order.status, order.status)
                user_name = order.user.first_name or "Неизвестный"
                
                text += (
                    f"🔹 <b>#{order.id}</b> | {status_text}\n"
                    f"👤 {user_name} | 💰 {format_price(order.total_amount)}\n"
                    f"📅 {format_datetime(order.created_at).split()[1]}\n\n"
                )
        
        # Кнопки для пагинации и навигации
        keyboard = []
        
        # Кнопки заказов для детального просмотра
        if orders:
            order_buttons = []
            for i, order in enumerate(orders[:10]):  # Первые 10 заказов
                order_buttons.append(
                    {"text": f"#{order.id}", "callback_data": f"admin_order_{order.id}"}
                )
            
            # Разбиваем кнопки по 5 в ряд
            for i in range(0, len(order_buttons), 5):
                keyboard.append(order_buttons[i:i+5])
        
        keyboard.extend([
            [{"text": "🔄 Обновить", "callback_data": callback.data}],
            [{"text": "🔙 К фильтрам", "callback_data": "admin_orders_menu"}],
            [{"text": "🏠 Главное меню", "callback_data": "back_to_admin_panel"}]
        ])
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup={"inline_keyboard": keyboard},
                parse_mode="HTML"
            )
        except Exception as e:
            # Если сообщение не изменилось, просто отвечаем без алерта
            if "message is not modified" in str(e).lower():
                await callback.answer()
            else:
                await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
            return
    await callback.answer()


@router.callback_query(F.data == "admin_pending_orders")
async def show_pending_orders(callback: CallbackQuery):
    """Показать заказы на модерации"""
    async with async_session_maker() as session:
        # Заказы ожидающие подтверждения оплаты
        result = await session.execute(
            select(Order)
            .where(Order.status == OrderStatus.PAYMENT_RECEIVED.value)
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
                f"⏰ {format_datetime(order.created_at)}\n\n"
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
            f"📅 <b>Дата:</b> {format_datetime(order.created_at)}\n"
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
        if order.status == OrderStatus.PAYMENT_RECEIVED.value:
            keyboard.extend([
                [{"text": "✅ Подтвердить оплату", "callback_data": f"confirm_payment_{order_id}"}],
                [{"text": "❌ Отклонить оплату", "callback_data": f"reject_payment_{order_id}"}]
            ])
            # Кнопка для просмотра фото оплаты
            if order.payment_photo_file_id:
                keyboard.append([{"text": "🖼 Показать фото оплаты", "callback_data": f"show_payment_photo_{order_id}"}])
        elif order.status == OrderStatus.CONFIRMED.value:
            keyboard.append([{"text": "🍽 Заказ готов", "callback_data": f"set_ready_{order_id}"}])
        elif order.status == OrderStatus.READY.value:
            keyboard.append([{"text": "✅ Заказ выдан", "callback_data": f"set_completed_{order_id}"}])
        
        # Кнопка для просмотра фото оплаты (для всех статусов, если фото есть)
        if order.payment_photo_file_id and order.status != OrderStatus.PAYMENT_RECEIVED.value:
            keyboard.append([{"text": "🖼 Показать фото оплаты", "callback_data": f"show_payment_photo_{order_id}"}])
        
        # Общая кнопка изменения статуса
        keyboard.append([{"text": "📊 Изменить статус", "callback_data": f"change_status_{order_id}"}])
        
        # Кнопка отмены заказа (если он не завершен)
        if order.status not in [
            OrderStatus.COMPLETED.value, 
            OrderStatus.CANCELLED_BY_CLIENT.value,
            OrderStatus.CANCELLED_BY_MASTER.value
        ]:
            keyboard.append([{"text": "🚫 Отменить заказ", "callback_data": f"cancel_by_master_{order_id}"}])
        
        keyboard.append([{"text": "🔙 К заказам", "callback_data": "admin_orders_menu"}])
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup={"inline_keyboard": keyboard},
                parse_mode="HTML"
            )
        except Exception as e:
            # Если не можем редактировать текст (например, сообщение содержит фото),
            # удаляем старое сообщение и отправляем новое
            if "no text in the message to edit" in str(e).lower() or "message to edit not found" in str(e).lower():
                try:
                    await callback.message.delete()
                except:
                    pass  # Игнорируем ошибки удаления
                await callback.bot.send_message(
                    callback.from_user.id,
                    text,
                    reply_markup={"inline_keyboard": keyboard},
                    parse_mode="HTML"
                )
            elif "message is not modified" not in str(e).lower():
                await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
                return
    
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
            .values(status=OrderStatus.CANCELLED_BY_MASTER.value)
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
                OrderStatus.PAYMENT_RECEIVED.value: "🔍",
                OrderStatus.CONFIRMED.value: "✅",
                OrderStatus.READY.value: "🍽",
                OrderStatus.COMPLETED.value: "✅",
                OrderStatus.CANCELLED_BY_CLIENT.value: "❌",
                OrderStatus.CANCELLED_BY_MASTER.value: "❌"
            }.get(order.status, "❓")
            
            text += (
                f"{status_emoji} Заказ #{order.id} | {order.total_amount} ₽\n"
                f"👤 {username} | {format_datetime(order.created_at).split()[1]}\n\n"
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
async def show_stats_menu(callback: CallbackQuery):
    """Показать меню статистики"""
    text = "📈 <b>Статистика заказов</b>\n\nВыберите период для анализа:"
    
    keyboard = [
        [
            {"text": "📅 За сегодня", "callback_data": "stats_today"},
            {"text": "📊 За неделю", "callback_data": "stats_week"}
        ],
        [
            {"text": "📈 За месяц", "callback_data": "stats_month"},
            {"text": "📋 За квартал", "callback_data": "stats_quarter"}
        ],
        [
            {"text": "📊 За год", "callback_data": "stats_year"},
            {"text": "🎯 Произвольный период", "callback_data": "stats_custom"}
        ],
        [
            {"text": "👥 По пользователям", "callback_data": "stats_users"},
            {"text": "🍽 По блюдам", "callback_data": "stats_dishes"}
        ],
        [
            {"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}
        ]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup={"inline_keyboard": keyboard},
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stats_"))
async def show_detailed_stats(callback: CallbackQuery):
    """Показать детальную статистику по выбранному периоду"""
    period = callback.data.split("_")[1]
    
    async with async_session_maker() as session:
        from sqlalchemy import func, and_, desc
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Определяем период
        if period == "today":
            start_date = now.date()
            period_name = "за сегодня"
        elif period == "week":
            start_date = (now - timedelta(days=7)).date()
            period_name = "за неделю"
        elif period == "month":
            start_date = (now - timedelta(days=30)).date()
            period_name = "за месяц"
        elif period == "quarter":
            start_date = (now - timedelta(days=90)).date()
            period_name = "за квартал"
        elif period == "year":
            start_date = (now - timedelta(days=365)).date()
            period_name = "за год"
        elif period == "users":
            await show_users_stats(callback, session)
            return
        elif period == "dishes":
            await show_dishes_stats(callback, session)
            return
        else:
            await callback.answer("⚠️ Функция в разработке", show_alert=True)
            return
        
        # Статистика по периоду
        orders_query = select(func.count(Order.id), func.sum(Order.total_amount))
        if period != "today":
            orders_query = orders_query.where(func.date(Order.created_at) >= start_date)
        else:
            orders_query = orders_query.where(func.date(Order.created_at) == start_date)
        
        # Только завершенные заказы
        completed_orders = await session.execute(
            orders_query.where(
                Order.status.in_([
                    OrderStatus.CONFIRMED.value,
                    OrderStatus.READY.value,
                    OrderStatus.COMPLETED.value
                ])
            )
        )
        completed_count, completed_sum = completed_orders.first()
        completed_sum = completed_sum or 0
        
        # Все заказы за период
        all_orders = await session.execute(orders_query)
        total_count, total_sum = all_orders.first()
        total_sum = total_sum or 0
        
        # Статистика по статусам за период
        status_query = select(Order.status, func.count(Order.id))
        if period != "today":
            status_query = status_query.where(func.date(Order.created_at) >= start_date)
        else:
            status_query = status_query.where(func.date(Order.created_at) == start_date)
        
        status_stats = await session.execute(
            status_query.group_by(Order.status)
        )
        
        status_text = ""
        for status, count in status_stats:
            from app.utils.texts import ORDER_STATUSES
            status_text += f"• {ORDER_STATUSES.get(status, status)}: {count}\n"
        
        text = (
            f"📈 <b>Статистика {period_name}</b>\n\n"
            f"✅ <b>Завершенные заказы:</b>\n"
            f"• Количество: {completed_count}\n"
            f"• Сумма: {completed_sum} руб\n\n"
            f"📊 <b>Все заказы:</b>\n"
            f"• Количество: {total_count}\n"
            f"• Общая сумма: {total_sum} руб\n\n"
            f"📋 <b>По статусам:</b>\n{status_text}"
        )
        
        keyboard = [
            [{"text": "🔙 К выбору периода", "callback_data": "admin_stats"}],
            [{"text": "🏠 Главное меню", "callback_data": "back_to_admin_panel"}]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )
    await callback.answer()


async def show_users_stats(callback: CallbackQuery, session):
    """Показать статистику по пользователям"""
    from sqlalchemy import func, desc
    
    # Топ пользователей по количеству заказов
    users_orders = await session.execute(
        select(
            User.first_name,
            User.last_name,
            User.username,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_spent')
        )
        .join(Order, User.id == Order.user_id)
        .where(Order.status.in_([
            OrderStatus.CONFIRMED.value,
            OrderStatus.READY.value,
            OrderStatus.COMPLETED.value
        ]))
        .group_by(User.id)
        .order_by(desc('order_count'))
        .limit(10)
    )
    
    users_text = ""
    for i, (first_name, last_name, username, order_count, total_spent) in enumerate(users_orders, 1):
        name = f"{first_name or ''} {last_name or ''}".strip() or username or "Неизвестный"
        users_text += f"{i}. {name}\n   📦 {order_count} заказов, 💰 {total_spent or 0} руб\n\n"
    
    if not users_text:
        users_text = "Нет данных о завершенных заказах"
    
    text = (
        f"👥 <b>Топ-10 клиентов</b>\n\n"
        f"{users_text}"
    )
    
    keyboard = [
        [{"text": "🔙 К выбору периода", "callback_data": "admin_stats"}],
        [{"text": "🏠 Главное меню", "callback_data": "back_to_admin_panel"}]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup={"inline_keyboard": keyboard},
        parse_mode="HTML"
    )


async def show_dishes_stats(callback: CallbackQuery, session):
    """Показать статистику по блюдам"""
    from sqlalchemy import func, desc
    
    # Топ блюд по количеству заказов
    dishes_orders = await session.execute(
        select(
            Dish.name,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.quantity * OrderItem.price).label('total_revenue')
        )
        .join(OrderItem, Dish.id == OrderItem.dish_id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status.in_([
            OrderStatus.CONFIRMED.value,
            OrderStatus.READY.value,
            OrderStatus.COMPLETED.value
        ]))
        .group_by(Dish.id)
        .order_by(desc('total_quantity'))
        .limit(10)
    )
    
    dishes_text = ""
    for i, (name, total_quantity, order_count, total_revenue) in enumerate(dishes_orders, 1):
        dishes_text += f"{i}. {name}\n   🍽 {total_quantity} порций в {order_count} заказах\n   💰 {total_revenue or 0} руб\n\n"
    
    if not dishes_text:
        dishes_text = "Нет данных о проданных блюдах"
    
    text = (
        f"🍽 <b>Топ-10 блюд</b>\n\n"
        f"{dishes_text}"
    )
    
    keyboard = [
        [{"text": "🔙 К выбору периода", "callback_data": "admin_stats"}],
        [{"text": "🏠 Главное меню", "callback_data": "back_to_admin_panel"}]
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
                {"text": "✏️ Изменить название", "callback_data": f"edit_dish_name_{dish_id}"}
            ],
            [
                {"text": "💰 Изменить цену", "callback_data": f"edit_dish_price_{dish_id}"},
                {"text": "📄 Изменить описание", "callback_data": f"edit_dish_description_{dish_id}"}
            ],
            [
                {"text": "🔗 Изменить ссылку на пост", "callback_data": f"edit_dish_link_{dish_id}"}
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
            {"text": "📋 Управление заказами", "callback_data": "admin_orders_menu"},
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
            .values(status=OrderStatus.CONFIRMED.value)
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
                callback.bot, order, user, "payment_received", "confirmed"
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
            .values(status=OrderStatus.CANCELLED_BY_MASTER.value)
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
                callback.bot, order, user, "payment_received", "cancelled_by_master"
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
        [{"text": "🍽 Готов к выдаче", "callback_data": f"set_status_{order_id}_ready"}],
        [{"text": "✅ Заказ выдан", "callback_data": f"set_status_{order_id}_completed"}],
        [{"text": "❌ Отменить", "callback_data": f"set_status_{order_id}_cancelled_by_master"}],
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
            "cancelled_by_master": "Отменен"
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
            .values(status=OrderStatus.CANCELLED_BY_MASTER.value)
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
                callback.bot, order, user, "pending_confirmation", "cancelled_by_master"
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
    """Получить название нового блюда или изменить название существующего"""
    dish_name = message.text.strip()
    
    if len(dish_name) < 2 or len(dish_name) > 150:
        await message.answer(
            "❌ Название блюда должно быть от 2 до 150 символов.\n"
            "Попробуйте еще раз:"
        )
        return
    
    data = await state.get_data()
    dish_id = data.get("dish_id")
    
    if dish_id:
        # Редактирование существующего блюда - меняем только название
        async with async_session_maker() as session:
            from app.database import Dish
            
            dish = await session.get(Dish, dish_id)
            if not dish:
                await message.answer("❌ Блюдо не найдено")
                await state.clear()
                return
            
            # Проверяем, что блюдо с таким именем не существует в этой категории
            from sqlalchemy import select, and_
            existing_dish = await session.execute(
                select(Dish).where(
                    and_(
                        Dish.category_id == dish.category_id,
                        Dish.name == dish_name,
                        Dish.id != dish_id  # исключаем текущее блюдо
                    )
                )
            )
            if existing_dish.scalar_one_or_none():
                await message.answer(
                    "❌ Блюдо с таким названием уже существует в этой категории.\n"
                    "Введите другое название:"
                )
                return
            
            # Обновляем название
            old_name = dish.name
            dish.name = dish_name
            await session.commit()
            
            await message.answer(
                f"✅ Название блюда изменено!\n"
                f"Было: <b>{old_name}</b>\n"
                f"Стало: <b>{dish_name}</b>",
                parse_mode="HTML",
                reply_markup={"inline_keyboard": [[
                    {"text": "🍽 К редактированию блюда", "callback_data": f"edit_dish_{dish_id}"}
                ]]}
            )
            
            await state.clear()  # Очищаем состояние после успешного изменения
            
    else:
        # Создание нового блюда - продолжаем как раньше
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
        await state.update_data(dish_description=new_description)
        await state.set_state(AdminStates.ENTERING_DISH_LINK)
        await message.answer(
            "� Введите ссылку на пост в канале (или отправьте '-' чтобы пропустить):"
        )


@router.message(StateFilter(AdminStates.ENTERING_DISH_LINK))
async def handle_dish_link_input(message: Message, state: FSMContext):
    """Обработать ввод ссылки на пост о блюде"""
    new_link = message.text.strip()
    
    # Валидация ссылки
    if new_link == "-":
        new_link = None
    elif new_link and not (new_link.startswith("https://t.me/") or new_link.startswith("http://t.me/")):
        await message.answer(
            "❌ Неверный формат ссылки. Ссылка должна начинаться с https://t.me/\n"
            "Введите ссылку еще раз (или '-' для удаления):"
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
            
            dish.telegram_post_url = new_link
            await session.commit()
            
            link_text = new_link or "удалена"
            await message.answer(
                f"✅ Ссылка на пост для блюда '{dish.name}' изменена!\n"
                f"🔗 Новая ссылка: {link_text}",
                reply_markup={"inline_keyboard": [[
                    {"text": "🍽 К редактированию блюда", "callback_data": f"edit_dish_{dish_id}"}
                ]]}
            )
        await state.clear()
    else:
        # Создание нового блюда - завершаем процесс
        category_id = data.get("category_id")
        dish_name = data.get("dish_name")
        dish_price = data.get("dish_price")
        dish_description = data.get("dish_description")
        
        if not category_id or not dish_name or dish_price is None:
            await message.answer("❌ Ошибка: недостаточно данных для создания блюда")
            await state.clear()
            return
        
        # Создаем блюдо
        async with async_session_maker() as session:
            from app.database import Dish, Category
            
            # Проверяем категорию
            category = await session.get(Category, category_id)
            if not category:
                await message.answer("❌ Категория не найдена")
                await state.clear()
                return
            
            # Создаем новое блюдо
            new_dish = Dish(
                name=dish_name,
                price=dish_price,
                description=dish_description,
                category_id=category_id,
                telegram_post_url=new_link,
                is_available=True
            )
            session.add(new_dish)
            await session.commit()
            await session.refresh(new_dish)
            
            link_text = f"🔗 <b>Ссылка:</b> {new_link}\n" if new_link else ""
            await message.answer(
                f"✅ <b>Блюдо создано!</b>\n\n"
                f"📛 <b>Название:</b> {dish_name}\n"
                f"💰 <b>Цена:</b> {dish_price} ₽\n"
                f"� <b>Категория:</b> {category.name}\n"
                f"📝 <b>Описание:</b> {dish_description or 'не указано'}\n"
                f"{link_text}",
                parse_mode="HTML",
                reply_markup={"inline_keyboard": [[
                    {"text": "🍽 Редактировать блюдо", "callback_data": f"edit_dish_{new_dish.id}"},
                    {"text": "📂 К категории", "callback_data": f"dishes_in_category_{category_id}"}
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


@router.callback_query(F.data.startswith("edit_dish_name_"))
async def edit_dish_name_start(callback: CallbackQuery, state: FSMContext):
    """Начать изменение названия блюда"""
    dish_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Dish
        dish = await session.get(Dish, dish_id)
        
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"✏️ <b>Изменение названия блюда</b>\n\n"
            f"Текущее название: <b>{dish.name}</b>\n\n"
            f"Введите новое название:",
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.ENTERING_DISH_NAME)
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


@router.callback_query(F.data.startswith("edit_dish_link_"))
async def edit_dish_link_start(callback: CallbackQuery, state: FSMContext):
    """Начать изменение ссылки на пост о блюде"""
    dish_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Dish
        dish = await session.get(Dish, dish_id)
        
        if not dish:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
            return
        
        current_link = dish.telegram_post_url or "не указана"
        await callback.message.edit_text(
            f"🔗 <b>Изменение ссылки на пост</b>\n\n"
            f"Блюдо: <b>{dish.name}</b>\n"
            f"Текущая ссылка: <b>{current_link}</b>\n\n"
            f"Введите новую ссылку на пост в Telegram канале\n"
            f"(например: https://t.me/your_channel/123)\n"
            f"или '-' чтобы удалить:",
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.ENTERING_DISH_LINK)
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


@router.callback_query(F.data.startswith("set_ready_"))
async def set_order_ready(callback: CallbackQuery):
    """Установить статус заказа 'готов к выдаче'"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.READY.value)
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
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    f"🎉 Ваш заказ #{order.id} готов к выдаче!\n\n"
                    f"Можете забирать свой заказ на сумму {order.total_amount} ₽"
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
            
            await callback.answer("✅ Заказ готов к выдаче!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка изменения статуса", show_alert=True)


@router.callback_query(F.data.startswith("set_completed_"))
async def set_order_completed(callback: CallbackQuery):
    """Установить статус заказа 'выполнен'"""
    order_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(
                status=OrderStatus.COMPLETED.value,
                completed_at=datetime.utcnow()
            )
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
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    f"✅ Заказ #{order.id} успешно выполнен!\n\n"
                    f"Спасибо за заказ на сумму {order.total_amount} ₽\n"
                    f"Буду рада видеть вас снова! 😊"
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
            
            await callback.answer("✅ Заказ выполнен!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка изменения статуса", show_alert=True)


@router.callback_query(F.data.startswith("cancel_by_master_"))
async def cancel_order_by_master(callback: CallbackQuery):
    """Отменить заказ мастером"""
    order_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        result = await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.CANCELLED_BY_MASTER.value)
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
            
            # Уведомляем пользователя об отмене заказа
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    f"❌ К сожалению, заказ #{order.id} отменён.\n\n"
                    f"Сумма {order.total_amount} ₽ будет возвращена.\n"
                    f"Я свяжусь с вами для уточнения деталей."
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
            
            await callback.answer("❌ Заказ отменён!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка отмены заказа", show_alert=True)


@router.callback_query(F.data.startswith("show_payment_photo_"))
async def show_payment_photo(callback: CallbackQuery):
    """Показать фото подтверждения оплаты"""
    order_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        from app.database import Order
        order = await session.get(Order, order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        if not order.payment_photo_file_id:
            await callback.answer("❌ Фото оплаты не найдено", show_alert=True)
            return
        
        try:
            # Отправляем фото
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=order.payment_photo_file_id,
                caption=f"💰 Фото подтверждения оплаты\n📋 Заказ #{order.id}\n💳 Сумма: {order.total_amount} руб",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Назад к заказу", "callback_data": f"admin_order_{order_id}"}]
                    ]
                }
            )
            await callback.answer()
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            await callback.answer("❌ Ошибка загрузки фото", show_alert=True)
