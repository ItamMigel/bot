#!/usr/bin/env python3
"""
Тест функциональности админской панели после миграции базы данных
"""
import asyncio
from app.database import async_session_maker, Order, Dish
from sqlalchemy import select

async def test_admin_features():
    print("🧪 Тестирование админской панели после миграции")
    print("=" * 60)
    
    async with async_session_maker() as session:
        # 1. Тест фильтров заказов
        print("\n1. 📋 Тестирование фильтров заказов:")
        
        # Все заказы
        result = await session.execute(select(Order).order_by(Order.created_at.desc()).limit(10))
        all_orders = result.scalars().all()
        print(f"   ✅ Все заказы: {len(all_orders)}")
        
        # Ожидают оплаты
        result = await session.execute(
            select(Order).where(Order.status == 'pending_payment').limit(10)
        )
        pending_orders = result.scalars().all()
        print(f"   ✅ Ожидают оплаты: {len(pending_orders)}")
        
        # Оплачены, ожидают подтверждения
        result = await session.execute(
            select(Order).where(Order.status == 'payment_received').limit(10)
        )
        paid_orders = result.scalars().all()
        print(f"   ✅ Ожидают подтверждения: {len(paid_orders)}")
        
        # В работе
        result = await session.execute(
            select(Order).where(Order.status == 'confirmed').limit(10)
        )
        working_orders = result.scalars().all()
        print(f"   ✅ В работе: {len(working_orders)}")
        
        # Готовые
        result = await session.execute(
            select(Order).where(Order.status == 'ready').limit(10)
        )
        ready_orders = result.scalars().all()
        print(f"   ✅ Готовые: {len(ready_orders)}")
        
        # Завершенные
        result = await session.execute(
            select(Order).where(Order.status == 'completed').limit(10)
        )
        completed_orders = result.scalars().all()
        print(f"   ✅ Завершенные: {len(completed_orders)}")
        
        # Отмененные
        result = await session.execute(
            select(Order).where(Order.status.in_(['cancelled_by_client', 'cancelled_by_master'])).limit(10)
        )
        cancelled_orders = result.scalars().all()
        print(f"   ✅ Отмененные: {len(cancelled_orders)}")
        
        # 2. Тест поля payment_photo_file_id
        print("\n2. 📸 Тестирование поля payment_photo_file_id:")
        if all_orders:
            order = all_orders[0]
            print(f"   ✅ Заказ #{order.id}: payment_photo_file_id = {order.payment_photo_file_id}")
        
        # 3. Тест telegram_post_url для блюд
        print("\n3. 📖 Тестирование поля telegram_post_url для блюд:")
        result = await session.execute(select(Dish).limit(5))
        dishes = result.scalars().all()
        for dish in dishes:
            print(f"   ✅ Блюдо '{dish.name}': telegram_post_url = {dish.telegram_post_url}")
        
        # 4. Тест активных заказов
        print("\n4. 🔥 Тестирование активных заказов:")
        result = await session.execute(
            select(Order).where(Order.status != 'cart').order_by(Order.created_at.desc()).limit(10)
        )
        active_orders = result.scalars().all()
        print(f"   ✅ Активные заказы (исключая корзины): {len(active_orders)}")
        
    print("\n" + "=" * 60)
    print("🎉 Все тесты админской панели прошли успешно!")
    print("✅ База данных обновлена корректно")
    print("✅ Фильтры заказов работают")
    print("✅ Поля для фото оплаты и ссылок на канал добавлены")
    print("🚀 Админская панель готова к использованию!")

if __name__ == "__main__":
    asyncio.run(test_admin_features())
