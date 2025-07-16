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
                [{"text": "✅ Подтвердить оплату", "callback_data": f"admin_confirm_{order_id}"}],
                [{"text": "❌ Отклонить оплату", "callback_data": f"admin_reject_{order_id}"}]
            ])
        elif order.status == OrderStatus.CONFIRMED.value:
            keyboard.append([{"text": "🍽 Заказ готов", "callback_data": f"admin_ready_{order_id}"}])
        elif order.status == OrderStatus.READY.value:
            keyboard.append([{"text": "✅ Заказ выдан", "callback_data": f"admin_complete_{order_id}"}])
        
        # Кнопка отмены заказа (если он не завершен)
        if order.status not in [OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value]:
            keyboard.append([{"text": "🚫 Отменить заказ", "callback_data": f"admin_cancel_{order_id}"}])
        
        keyboard.append([{"text": "🔙 К заказам", "callback_data": "admin_pending_orders"}])
        
        await callback.message.edit_text(
            text,
            reply_markup={"inline_keyboard": keyboard},
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("admin_confirm_"))
async def confirm_payment(callback: CallbackQuery):
    """Подтвердить оплату заказа"""
    order_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.CONFIRMED.value)
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
                        f"✅ <b>Оплата подтверждена!</b>\n\n"
                        f"Ваш заказ #{order_id} принят в работу.\n"
                        f"Мы начали готовить ваш заказ!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass  # Игнорируем ошибки отправки
    
    await callback.answer("✅ Оплата подтверждена!")
    await show_order_details(callback)  # Обновляем отображение заказа


@router.callback_query(F.data.startswith("admin_reject_"))
async def reject_payment(callback: CallbackQuery):
    """Отклонить оплату заказа"""
    order_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.PENDING_PAYMENT.value)
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
                        f"❌ <b>Оплата не подтверждена</b>\n\n"
                        f"К сожалению, мы не смогли подтвердить оплату по заказу #{order_id}.\n"
                        f"Пожалуйста, проверьте данные и повторите оплату.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass  # Игнорируем ошибки отправки
    
    await callback.answer("❌ Оплата отклонена!")
    await show_order_details(callback)  # Обновляем отображение заказа


@router.callback_query(F.data.startswith("admin_ready_"))
async def mark_order_ready(callback: CallbackQuery):
    """Отметить заказ как готовый"""
    order_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        # Обновляем статус заказа
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.READY.value)
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
                        f"🍽 <b>Заказ готов!</b>\n\n"
                        f"Ваш заказ #{order_id} готов к выдаче.\n"
                        f"Приходите забирать! 😊",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass  # Игнорируем ошибки отправки
    
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


@router.callback_query(F.data == "admin_panel")
async def back_to_admin_panel(callback: CallbackQuery):
    """Вернуться к админ-панели"""
    await admin_panel(callback.message)


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Добро пожаловать в наш ресторан!\n\n"
        "Выберите, что хотите сделать:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
