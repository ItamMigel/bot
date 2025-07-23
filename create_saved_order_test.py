"""Скрипт для создания тестового заказа с пользовательским названием"""
import asyncio
from sqlalchemy import update
from app.database import async_session_maker, Order, User, OrderStatus

async def create_test_saved_order():
    """Создаем тестовый заказ с пользовательским названием"""
    async with async_session_maker() as session:
        # Получаем первого пользователя
        user = await session.get(User, 1)
        if not user:
            print("Пользователь не найден")
            return
        
        # Получаем его последний завершенный заказ
        from sqlalchemy import select
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .where(Order.status == OrderStatus.COMPLETED.value)
            .order_by(Order.created_at.desc())
            .limit(1)
        )
        order = result.scalar_one_or_none()
        
        if order:
            # Добавляем пользовательское название
            await session.execute(
                update(Order)
                .where(Order.id == order.id)
                .values(custom_name="Мой любимый обед")
            )
            await session.commit()
            print(f"Добавлено название 'Мой любимый обед' к заказу #{order.id}")
        else:
            print("Завершенные заказы не найдены")

if __name__ == "__main__":
    asyncio.run(create_test_saved_order())
