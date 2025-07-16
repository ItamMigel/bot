"""Сервис для отправки уведомлений администраторам"""
import logging
from typing import List
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from app.config import settings
from app.utils.helpers import get_user_display_name


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    @staticmethod
    async def notify_admins(bot: Bot, message: str, parse_mode: str = None):
        """Отправить сообщение всем администраторам"""
        if not settings.admin_ids:
            logging.warning("No admin IDs configured for notifications")
            return False
            
        sent_count = 0
        failed_count = 0
        
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode=parse_mode
                )
                sent_count += 1
                logging.info(f"Notification sent to admin {admin_id}")
                
            except TelegramBadRequest as e:
                failed_count += 1
                logging.error(f"Failed to send notification to admin {admin_id}: {e}")
            except Exception as e:
                failed_count += 1
                logging.error(f"Unexpected error sending to admin {admin_id}: {e}")
        
        logging.info(f"Notification stats: {sent_count} sent, {failed_count} failed")
        return sent_count > 0
    
    @staticmethod
    async def notify_user(bot: Bot, user_id: int, message: str, parse_mode: str = None):
        """Отправить сообщение пользователю"""
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode
            )
            logging.info(f"Notification sent to user {user_id}")
            return True
        except TelegramBadRequest as e:
            logging.error(f"Failed to send notification to user {user_id}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending to user {user_id}: {e}")
            return False
    
    @staticmethod
    async def notify_new_order(bot: Bot, order, user):
        """Уведомить о новом заказе"""
        from app.utils import texts
        from app.utils.helpers import format_price
        
        # Формируем список товаров
        items_text = []
        for item in order.items:
            items_text.append(f"• {item.dish.name} x{item.quantity}")
        
        message = texts.NEW_ORDER_NOTIFICATION.format(
            order_id=order.id,
            user_name=get_user_display_name(user),
            user_id=user.telegram_id,
            total_amount=format_price(order.total_amount),
            payment_method="💳 Карта" if order.payment_method == "card" else "💵 Наличные",
            order_items="\n".join(items_text)
        )
        
        return await NotificationService.notify_admins(bot, message)
    
    @staticmethod
    async def notify_payment_received(bot: Bot, order, user):
        """Уведомить о получении скриншота оплаты"""
        from app.utils import texts
        from app.utils.helpers import format_price
        
        message = texts.PAYMENT_RECEIVED_NOTIFICATION.format(
            order_id=order.id,
            amount=format_price(order.total_amount),
            user_name=get_user_display_name(user)
        )
        
        return await NotificationService.notify_admins(bot, message)
    
    @staticmethod
    async def notify_feedback(bot: Bot, user, feedback_text: str):
        """Уведомить о новом обращении"""
        from app.utils import texts
        
        message = texts.ADMIN_FEEDBACK_NOTIFICATION.format(
            user_id=user.telegram_id,
            user_name=get_user_display_name(user),
            username=f"@{user.username}" if user.username else "нет",
            feedback=feedback_text
        )
        
        return await NotificationService.notify_admins(bot, message)
    
    @staticmethod
    async def notify_order_status_change(bot: Bot, order, user, old_status: str, new_status: str):
        """Уведомить об изменении статуса заказа"""
        from app.utils import texts
        
        # Уведомляем пользователя об изменении статуса
        user_message = texts.ORDER_STATUS_CHANGED_USER.format(
            order_id=order.id,
            old_status=texts.ORDER_STATUSES.get(old_status, old_status),
            new_status=texts.ORDER_STATUSES.get(new_status, new_status)
        )
        
        return await NotificationService.notify_user(bot, user.telegram_id, user_message)
    
    @staticmethod
    async def notify_order_cancelled(bot: Bot, order, user):
        """Уведомить об отмене заказа"""
        from app.utils import texts
        from app.utils.helpers import format_price
        
        # Уведомляем пользователя об отмене
        user_message = f"❌ Ваш заказ #{order.id} на сумму {format_price(order.total_amount)} был отменен."
        
        # Уведомляем администраторов
        admin_message = f"❌ Заказ #{order.id} отменен пользователем {get_user_display_name(user)} (ID: {user.telegram_id})"
        
        user_result = await NotificationService.notify_user(bot, user.telegram_id, user_message)
        admin_result = await NotificationService.notify_admins(bot, admin_message)
        
        return user_result or admin_result
