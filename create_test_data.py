"""Скрипт для создания тестовых данных"""
import asyncio
from app.database import async_session_maker, Category, Dish


async def create_test_data():
    """Создаем тестовые данные для демонстрации"""
    async with async_session_maker() as session:
        # Создаем категории
        categories = [
            Category(
                name="🥗 Салаты",
                description="Свежие и полезные салаты на любой вкус",
                is_active=True,
                sort_order=1
            ),
            Category(
                name="🍲 Супы",
                description="Горячие домашние супы",
                is_active=True,
                sort_order=2
            ),
            Category(
                name="🍖 Горячие блюда",
                description="Сытные вторые блюда",
                is_active=True,
                sort_order=3
            ),
            Category(
                name="🥧 Выпечка",
                description="Домашняя выпечка и десерты",
                is_active=True,
                sort_order=4
            )
        ]
        
        session.add_all(categories)
        await session.flush()  # Получаем ID категорий
        
        # Создаем блюда
        dishes = [
            # Салаты
            Dish(
                name="Цезарь с курицей",
                description="Классический салат с курицей, сыром пармезан и сухариками",
                price=350.0,
                category_id=categories[0].id,
                is_available=True,
                sort_order=1
            ),
            Dish(
                name="Греческий салат",
                description="Свежие овощи с сыром фета и оливками",
                price=280.0,
                category_id=categories[0].id,
                is_available=True,
                sort_order=2
            ),
            
            # Супы
            Dish(
                name="Борщ украинский",
                description="Традиционный борщ со сметаной",
                price=250.0,
                category_id=categories[1].id,
                is_available=True,
                sort_order=1
            ),
            Dish(
                name="Солянка мясная",
                description="Насыщенная солянка с мясными деликатесами",
                price=300.0,
                category_id=categories[1].id,
                is_available=True,
                sort_order=2
            ),
            
            # Горячие блюда
            Dish(
                name="Котлеты по-киевски",
                description="Нежные котлеты с маслом и зеленью",
                price=450.0,
                category_id=categories[2].id,
                is_available=True,
                sort_order=1
            ),
            Dish(
                name="Плов узбекский",
                description="Ароматный плов с бараниной",
                price=380.0,
                category_id=categories[2].id,
                is_available=True,
                sort_order=2
            ),
            
            # Выпечка
            Dish(
                name="Шарлотка с яблоками",
                description="Домашняя шарлотка со свежими яблоками",
                price=180.0,
                category_id=categories[3].id,
                is_available=True,
                sort_order=1
            ),
            Dish(
                name="Наполеон",
                description="Классический торт Наполеон",
                price=250.0,
                category_id=categories[3].id,
                is_available=True,
                sort_order=2
            )
        ]
        
        session.add_all(dishes)
        await session.commit()
        
        print("✅ Тестовые данные созданы!")
        print(f"📂 Создано {len(categories)} категорий")
        print(f"🍽 Создано {len(dishes)} блюд")


if __name__ == "__main__":
    asyncio.run(create_test_data())
