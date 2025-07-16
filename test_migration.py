"""
Простой тест для проверки основной функциональности бота после миграции
"""
import asyncio
import logging
from sqlalchemy import select
from app.database import async_session_maker, User, Order, OrderStatus
from app.services.order import OrderService
from app.services.cart import CartService

async def test_order_creation():
    """Тест создания заказа"""
    print("🧪 Тестирование создания заказа...")
    
    async with async_session_maker() as session:
        # Проверяем, что есть тестовый пользователь
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ Нет тестовых пользователей")
            return
        
        print(f"👤 Тестовый пользователь: {user.telegram_id}")
        
        # Получаем корзину пользователя
        cart = await CartService.get_cart_with_items(session, user.id)
        
        if not cart or not cart.items:
            print("🛒 Корзина пуста, добавим тестовое блюдо...")
            # Добавляем блюдо в корзину
            success = await CartService.add_to_cart(session, user.id, 1, 2)
            if success:
                await session.commit()
                cart = await CartService.get_cart_with_items(session, user.id)
                print(f"✅ Добавлено в корзину: {len(cart.items)} товаров")
            else:
                print("❌ Не удалось добавить в корзину")
                return
        
        print(f"🛒 В корзине: {len(cart.items)} товаров, сумма: {cart.total_amount} ₽")
        
        # Создаем заказ
        try:
            order = await OrderService.create_order_from_cart(
                session, user.id, payment_method="card"
            )
            await session.commit()
            
            if order:
                print(f"✅ Заказ #{order.id} создан успешно")
                print(f"   Сумма: {order.total_amount} ₽")
                print(f"   Способ оплаты: {order.payment_method}")
                print(f"   Статус: {order.status}")
                
                # Проверяем атрибуты
                if hasattr(order, 'payment_method') and hasattr(order, 'payment_screenshot'):
                    print("✅ Новые поля payment_method и payment_screenshot доступны")
                else:
                    print("❌ Новые поля недоступны")
                
            else:
                print("❌ Не удалось создать заказ")
                
        except Exception as e:
            print(f"❌ Ошибка создания заказа: {e}")
            import traceback
            traceback.print_exc()


async def test_order_details():
    """Тест получения деталей заказа"""
    print("\n🧪 Тестирование получения деталей заказа...")
    
    async with async_session_maker() as session:
        # Получаем любой заказ (не корзину)
        result = await session.execute(
            select(Order)
            .where(Order.status != OrderStatus.CART.value)
            .limit(1)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("❌ Нет заказов для тестирования")
            return
        
        try:
            # Получаем детали заказа
            order_details = await OrderService.get_order_details(session, order.id)
            
            if order_details:
                print(f"✅ Детали заказа #{order_details.id} получены")
                print(f"   Сумма: {order_details.total_amount} ₽")
                print(f"   Статус: {order_details.status}")
                print(f"   Позиций: {len(order_details.items)}")
                
                # Проверяем доступ к payment_method
                if hasattr(order_details, 'payment_method'):
                    print(f"   Способ оплаты: {order_details.payment_method}")
                else:
                    print("❌ Поле payment_method недоступно")
                    
            else:
                print("❌ Не удалось получить детали заказа")
                
        except Exception as e:
            print(f"❌ Ошибка получения деталей: {e}")
            import traceback
            traceback.print_exc()


async def main():
    print("🚀 Запуск тестов после миграции...\n")
    
    await test_order_creation()
    await test_order_details()
    
    print("\n✅ Тесты завершены!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
