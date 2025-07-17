"""Обработчики для работы с меню"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.utils import texts, UserStates
from app.keyboards.user import (
    get_categories_keyboard, get_dishes_keyboard, 
    get_dish_detail_keyboard, get_main_menu_keyboard
)
from app.database import async_session_maker, Category, Dish, User
from app.config import settings

router = Router()


@router.message(F.text == texts.BUTTON_MENU)
@router.callback_query(F.data == "menu")
async def show_menu(event: Message | CallbackQuery, state: FSMContext):
    """Показать главное меню с категориями"""
    await state.set_state(UserStates.BROWSING_MENU)
    
    async with async_session_maker() as session:
        # Получаем все активные категории
        result = await session.execute(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.sort_order)
        )
        categories = result.scalars().all()
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            texts.MENU_MESSAGE,
            reply_markup=get_categories_keyboard(categories)
        )
        await event.answer()
    else:
        await event.answer(
            texts.MENU_MESSAGE,
            reply_markup=get_categories_keyboard(categories)
        )


@router.callback_query(F.data.startswith("category_"))
async def show_category(callback: CallbackQuery, state: FSMContext):
    """Показать блюда в категории"""
    category_id = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        # Получаем категорию
        category = await session.get(Category, category_id)
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        
        # Получаем блюда в категории
        result = await session.execute(
            select(Dish)
            .where(Dish.category_id == category_id)
            .order_by(Dish.sort_order)
        )
        dishes = result.scalars().all()
    
    if not dishes:
        await callback.message.edit_text(
            f"📂 {category.name}\n\n{texts.NO_DISHES_IN_CATEGORY}",
            reply_markup=get_dishes_keyboard([], category_id)
        )
    else:
        message_text = texts.CATEGORY_MESSAGE.format(
            category_name=category.name,
            description=category.description or ""
        )
        
        await callback.message.edit_text(
            message_text,
            reply_markup=get_dishes_keyboard(dishes, category_id)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("dish_"))
async def show_dish(callback: CallbackQuery, state: FSMContext):
    """Показать детали блюда"""
    if callback.data == "dish_unavailable":
        await callback.answer("Блюдо временно недоступно", show_alert=True)
        return
        
    dish_id = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        # Получаем блюдо с категорией
        result = await session.execute(
            select(Dish)
            .options(selectinload(Dish.category))
            .where(Dish.id == dish_id)
        )
        dish = result.scalar_one_or_none()
        
        if not dish:
            await callback.answer("Блюдо не найдено", show_alert=True)
            return
    
    message_text = texts.DISH_MESSAGE.format(
        dish_name=dish.name,
        description=dish.description or "Описание отсутствует",
        price=dish.price
    )
    
    await callback.message.edit_text(
        message_text,
        reply_markup=get_dish_detail_keyboard(dish.id, dish.category_id, dish)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery, user: User):
    """Добавить блюдо в корзину"""
    # Парсим данные: add_to_cart_dish_id_quantity
    parts = callback.data.split("_")
    dish_id = int(parts[3])
    quantity = int(parts[4])
    
    async with async_session_maker() as session:
        try:
            from app.services.cart import CartService
            
            # Добавляем товар в корзину
            item = await CartService.add_item_to_cart(
                session, user.id, dish_id, quantity
            )
            await session.commit()
            
            # Получаем информацию о блюде для уведомления
            dish = await session.get(Dish, dish_id)
            if dish:
                total_price = dish.price * quantity
                await callback.answer(
                    f"✅ {dish.name} (x{quantity}) добавлено в корзину!\n"
                    f"💰 Сумма: {total_price} ₽"
                )
            else:
                await callback.answer("✅ Товар добавлен в корзину!")
                
        except ValueError as e:
            await callback.answer(f"❌ {str(e)}", show_alert=True)
        except Exception as e:
            await callback.answer("❌ Ошибка добавления в корзину", show_alert=True)


@router.callback_query(F.data.startswith("input_quantity_"))
async def request_quantity_input(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод количества для блюда"""
    # Парсим данные: input_quantity_dish_id_category_id
    parts = callback.data.split("_")
    dish_id = int(parts[2])
    category_id = int(parts[3])
    
    # Сохраняем данные в состоянии
    await state.update_data(
        dish_id=dish_id, 
        category_id=category_id,
        awaiting_quantity=True
    )
    await state.set_state(UserStates.ENTERING_QUANTITY)
    
    async with async_session_maker() as session:
        dish = await session.get(Dish, dish_id)
        if dish:
            from app.utils.helpers import format_price
            message = texts.INPUT_QUANTITY_MESSAGE.format(
                dish_name=dish.name,
                price=format_price(dish.price),
                max_quantity=settings.max_dish_quantity
            )
            await callback.message.edit_text(message)
        else:
            await callback.answer("❌ Блюдо не найдено", show_alert=True)
    
    await callback.answer()


@router.message(UserStates.ENTERING_QUANTITY)
async def process_quantity_input(message: Message, state: FSMContext, user: User):
    """Обработать введенное количество"""
    data = await state.get_data()
    dish_id = data.get("dish_id")
    category_id = data.get("category_id")
    
    # Проверяем, что это число
    try:
        quantity = int(message.text)
        if quantity < 1 or quantity > settings.max_dish_quantity:
            await message.answer(
                texts.INVALID_QUANTITY_MESSAGE.format(
                    max_quantity=settings.max_dish_quantity
                )
            )
            return
    except ValueError:
        await message.answer(
            texts.INVALID_QUANTITY_MESSAGE.format(
                max_quantity=settings.max_dish_quantity
            )
        )
        return
    
    # Добавляем в корзину
    async with async_session_maker() as session:
        try:
            from app.services.cart import CartService
            
            # Добавляем товар в корзину
            item = await CartService.add_item_to_cart(
                session, user.id, dish_id, quantity
            )
            await session.commit()
            
            # Получаем информацию о блюде для уведомления
            dish = await session.get(Dish, dish_id)
            if dish:
                from app.utils.helpers import format_price
                total_price = dish.price * quantity
                await message.answer(
                    f"✅ {dish.name} (x{quantity}) добавлено в корзину!\n"
                    f"💰 Сумма: {format_price(total_price)}"
                )
                
                # Возвращаемся к деталям блюда
                await message.answer(
                    texts.DISH_MESSAGE.format(
                        dish_name=dish.name,
                        description=dish.description,
                        price=format_price(dish.price)
                    ),
                    reply_markup=get_dish_detail_keyboard(dish.id, category_id, dish)
                )
            else:
                await message.answer("✅ Товар добавлен в корзину!")
                
        except ValueError as e:
            await message.answer(f"❌ {str(e)}")
        except Exception as e:
            await message.answer("❌ Ошибка добавления в корзину")
    
    # Очищаем состояние
    await state.clear()
    await state.set_state(UserStates.BROWSING_MENU)
