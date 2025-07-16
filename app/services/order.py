"""Сервис для работы с заказами"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database.models import Order, OrderItem
from app.services.cart import CartService


class OrderService:
    """Сервис для работы с заказами"""
    
    @staticmethod
    async def create_order_from_cart(
        session, 
        user_id: int, 
        payment_method: str = "card"
    ) -> Optional[Order]:
        """Создать заказ из корзины пользователя"""
        try:
            # Получаем корзину с товарами
            cart = await CartService.get_cart_with_items(session, user_id)
            if not cart or not cart.items:
                return None
            
            # Создаем заказ
            order = Order(
                user_id=user_id,
                total_amount=cart.total_amount,
                status="pending_payment" if payment_method == "card" else "confirmed",
                payment_method=payment_method,
                created_at=datetime.utcnow()
            )
            session.add(order)
            await session.flush()  # Получаем ID заказа
            
            # Копируем товары из корзины в заказ
            for cart_item in cart.items:
                order_item = OrderItem(
                    order_id=order.id,
                    dish_id=cart_item.dish_id,
                    quantity=cart_item.quantity,
                    price=cart_item.dish.price
                )
                session.add(order_item)
            
            # Очищаем корзину после создания заказа
            await CartService.clear_cart(session, user_id)
            
            return order
            
        except Exception as e:
            print(f"Ошибка создания заказа: {e}")
            return None
    
    @staticmethod
    async def get_user_orders(session, user_id: int) -> List[Order]:
        """Получить все заказы пользователя"""
        try:
            result = await session.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            print(f"Ошибка получения заказов: {e}")
            return []
    
    @staticmethod
    async def get_order_by_id(session, order_id: int) -> Optional[Order]:
        """Получить заказ по ID"""
        try:
            result = await session.execute(
                select(Order).where(Order.id == order_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Ошибка получения заказа: {e}")
            return None
    
    @staticmethod
    async def get_order_details(session, order_id: int) -> Optional[Order]:
        """Получить детали заказа с товарами"""
        try:
            result = await session.execute(
                select(Order)
                .options(
                    selectinload(Order.items).selectinload(OrderItem.dish)
                )
                .where(Order.id == order_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Ошибка получения деталей заказа: {e}")
            return None
    
    @staticmethod
    async def update_order_status(
        session, 
        order_id: int, 
        new_status: str
    ) -> bool:
        """Обновить статус заказа"""
        try:
            order = await OrderService.get_order_by_id(session, order_id)
            if order:
                order.status = new_status
                order.updated_at = datetime.utcnow()
                return True
            return False
        except Exception as e:
            print(f"Ошибка обновления статуса заказа: {e}")
            return False
    
    @staticmethod
    async def update_payment_screenshot(
        session, 
        order_id: int, 
        screenshot_path: str
    ) -> bool:
        """Обновить скриншот оплаты заказа"""
        try:
            order = await OrderService.get_order_by_id(session, order_id)
            if order:
                order.payment_screenshot = screenshot_path
                order.status = "payment_confirmation"
                order.updated_at = datetime.utcnow()
                return True
            return False
        except Exception as e:
            print(f"Ошибка обновления скриншота: {e}")
            return False
    
    @staticmethod
    async def repeat_order(session, user_id: int, order_id: int) -> bool:
        """Повторить заказ (добавить товары в корзину)"""
        try:
            # Получаем детали заказа
            order = await OrderService.get_order_details(session, order_id)
            if not order or order.user_id != user_id:
                return False
            
            # Добавляем товары из заказа в корзину
            for order_item in order.items:
                if order_item.dish.is_available:  # Проверяем доступность блюда
                    await CartService.add_to_cart(
                        session, 
                        user_id, 
                        order_item.dish_id, 
                        order_item.quantity
                    )
            
            return True
            
        except Exception as e:
            print(f"Ошибка повторения заказа: {e}")
            return False
    
    @staticmethod
    async def get_all_orders(session, status: Optional[str] = None) -> List[Order]:
        """Получить все заказы (для админа)"""
        try:
            query = select(Order).options(
                selectinload(Order.user),
                selectinload(Order.items).selectinload(OrderItem.dish)
            )
            
            if status:
                query = query.where(Order.status == status)
            
            query = query.order_by(Order.created_at.desc())
            
            result = await session.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Ошибка получения всех заказов: {e}")
            return []
    
    @staticmethod
    async def get_orders_stats(session) -> dict:
        """Получить статистику заказов"""
        try:
            # Подсчет заказов по статусам
            from sqlalchemy import func
            
            result = await session.execute(
                select(Order.status, func.count(Order.id))
                .group_by(Order.status)
            )
            
            stats = dict(result.fetchall())
            
            # Общая сумма заказов
            total_result = await session.execute(
                select(func.sum(Order.total_amount))
                .where(Order.status.in_(["completed", "ready"]))
            )
            total_amount = total_result.scalar() or 0
            
            stats["total_amount"] = total_amount
            
            return stats
            
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}

    @staticmethod
    async def cancel_order(session, order_id: int, user_id: int) -> bool:
        """Отменить заказ"""
        try:
            # Получаем заказ
            result = await session.execute(
                select(Order)
                .where(and_(Order.id == order_id, Order.user_id == user_id))
            )
            order = result.scalar_one_or_none()
            
            if not order:
                return False
            
            # Проверяем, можно ли отменить заказ
            if order.status not in ["pending_payment", "payment_confirmation"]:
                return False
            
            # Отменяем заказ
            order.status = "cancelled"
            order.updated_at = datetime.utcnow()
            
            return True
            
        except Exception as e:
            print(f"Ошибка отмены заказа: {e}")
            return False
