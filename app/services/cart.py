"""Сервис для работы с корзиной"""
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Order, OrderItem, Dish, User, OrderStatus


class CartService:
    """Сервис для управления корзиной пользователя"""
    
    @staticmethod
    async def get_or_create_cart(session: AsyncSession, user_id: int) -> Order:
        """Получить или создать корзину пользователя"""
        # Ищем активную корзину
        result = await session.execute(
            select(Order)
            .where(and_(
                Order.user_id == user_id,
                Order.status == OrderStatus.CART.value
            ))
        )
        cart = result.scalar_one_or_none()
        
        if not cart:
            # Создаем новую корзину
            cart = Order(
                user_id=user_id,
                status=OrderStatus.CART.value,
                total_amount=0.0
            )
            session.add(cart)
            await session.flush()  # Получаем ID
        
        return cart
    
    @staticmethod
    async def get_cart_with_items(session: AsyncSession, user_id: int) -> Optional[Order]:
        """Получить корзину с товарами"""
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.dish)
            )
            .where(and_(
                Order.user_id == user_id,
                Order.status == OrderStatus.CART.value
            ))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def add_item_to_cart(
        session: AsyncSession, 
        user_id: int, 
        dish_id: int, 
        quantity: int
    ) -> OrderItem:
        """Добавить товар в корзину"""
        # Получаем блюдо
        dish = await session.get(Dish, dish_id)
        if not dish or not dish.is_available:
            raise ValueError("Блюдо недоступно")
        
        # Получаем или создаем корзину
        cart = await CartService.get_or_create_cart(session, user_id)
        
        # Проверяем, есть ли уже такое блюдо в корзине
        result = await session.execute(
            select(OrderItem)
            .where(and_(
                OrderItem.order_id == cart.id,
                OrderItem.dish_id == dish_id
            ))
        )
        existing_item = result.scalar_one_or_none()
        
        if existing_item:
            # Обновляем количество
            existing_item.quantity += quantity
            item = existing_item
        else:
            # Создаем новую позицию
            item = OrderItem(
                order_id=cart.id,
                dish_id=dish_id,
                quantity=quantity,
                price=dish.price
            )
            session.add(item)
        
        # Обновляем общую сумму корзины
        await CartService._update_cart_total(session, cart.id)
        
        return item
    
    @staticmethod
    async def update_item_quantity(
        session: AsyncSession,
        user_id: int,
        item_id: int,
        quantity: int
    ) -> bool:
        """Обновить количество товара в корзине"""
        if quantity <= 0:
            return await CartService.remove_item_from_cart(session, user_id, item_id)
        
        # Получаем позицию
        result = await session.execute(
            select(OrderItem)
            .join(Order)
            .where(and_(
                OrderItem.id == item_id,
                Order.user_id == user_id,
                Order.status == OrderStatus.CART.value
            ))
        )
        item = result.scalar_one_or_none()
        
        if item:
            item.quantity = quantity
            await CartService._update_cart_total(session, item.order_id)
            return True
        
        return False
    
    @staticmethod
    async def remove_item_from_cart(
        session: AsyncSession,
        user_id: int,
        item_id: int
    ) -> bool:
        """Удалить товар из корзины"""
        result = await session.execute(
            select(OrderItem)
            .join(Order)
            .where(and_(
                OrderItem.id == item_id,
                Order.user_id == user_id,
                Order.status == OrderStatus.CART.value
            ))
        )
        item = result.scalar_one_or_none()
        
        if item:
            order_id = item.order_id
            await session.delete(item)
            await CartService._update_cart_total(session, order_id)
            return True
        
        return False
    
    @staticmethod
    async def clear_cart(session: AsyncSession, user_id: int) -> bool:
        """Очистить корзину"""
        cart = await CartService.get_cart_with_items(session, user_id)
        if cart:
            # Удаляем все позиции
            for item in cart.items:
                await session.delete(item)
            
            # Обнуляем сумму
            cart.total_amount = 0.0
            return True
        
        return False
    
    @staticmethod
    async def get_cart_count(session: AsyncSession, user_id: int) -> int:
        """Получить количество товаров в корзине"""
        cart = await CartService.get_cart_with_items(session, user_id)
        if cart:
            return sum(item.quantity for item in cart.items)
        return 0
    
    @staticmethod
    async def _update_cart_total(session: AsyncSession, cart_id: int):
        """Обновить общую сумму корзины"""
        result = await session.execute(
            select(OrderItem)
            .where(OrderItem.order_id == cart_id)
        )
        items = result.scalars().all()
        
        total = sum(item.quantity * item.price for item in items)
        
        cart = await session.get(Order, cart_id)
        if cart:
            cart.total_amount = total
