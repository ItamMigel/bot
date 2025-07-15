"""Обработчики для работы с корзиной"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.utils import texts, UserStates
from app.utils.helpers import format_price
from app.keyboards.user import (
    get_cart_keyboard, get_cart_item_edit_keyboard, 
    get_main_menu_keyboard, get_confirm_action_keyboard
)
from app.database import async_session_maker, User
from app.services.cart import CartService

router = Router()


@router.message(F.text.contains("🛒"), StateFilter("*"))
@router.message(F.text == texts.BUTTON_CART, StateFilter("*"))
@router.callback_query(F.data == "cart")
async def show_cart(event: Message | CallbackQuery, state: FSMContext, user: User):
    """Показать корзину пользователя"""
    logging.info(f"Пользователь {user.id} открывает корзину, текст: {event.text if isinstance(event, Message) else 'callback'}")
    await state.set_state(UserStates.VIEWING_CART)
    
    async with async_session_maker() as session:
        cart = await CartService.get_cart_with_items(session, user.id)
        
        if not cart or not cart.items:
            # Пустая корзина
            message_text = texts.CART_EMPTY
            keyboard = get_cart_keyboard([])
        else:
            # Формируем список товаров
            cart_items_text = []
            for item in cart.items:
                item_text = texts.CART_ITEM_FORMAT.format(
                    dish_name=item.dish.name,
                    quantity=item.quantity,
                    total_price=format_price(item.total_price)
                )
                cart_items_text.append(item_text)
            
            message_text = texts.CART_MESSAGE.format(
                cart_items="\n".join(cart_items_text),
                total_amount=format_price(cart.total_amount)
            )
            keyboard = get_cart_keyboard(cart.items)
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(message_text, reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(message_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_cart_item_"))
async def edit_cart_item(callback: CallbackQuery, state: FSMContext):
    """Редактировать позицию в корзине"""
    item_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        # Здесь можно добавить получение информации о товаре
        # Пока просто показываем клавиатуру для редактирования
        pass
    
    await callback.message.edit_text(
        "✏️ Редактирование товара\n\nВыберите новое количество или удалите товар:",
        reply_markup=get_cart_item_edit_keyboard(item_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cart_increase_"))
async def increase_cart_item(callback: CallbackQuery, user: User):
    """Увеличить количество товара в корзине"""
    item_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        # Получаем текущее количество и увеличиваем на 1
        cart = await CartService.get_cart_with_items(session, user.id)
        if cart:
            for item in cart.items:
                if item.id == item_id:
                    new_quantity = item.quantity + 1
                    if new_quantity <= 10:  # Ограничение
                        await CartService.update_item_quantity(
                            session, user.id, item_id, new_quantity
                        )
                        await session.commit()
                        await callback.answer("✅ Количество увеличено")
                    else:
                        await callback.answer("❌ Максимальное количество: 10", show_alert=True)
                    break
        else:
            await callback.answer("❌ Товар не найден", show_alert=True)
    
    # Обновляем отображение корзины
    await show_cart(callback, None, user)


@router.callback_query(F.data.startswith("cart_decrease_"))
async def decrease_cart_item(callback: CallbackQuery, user: User):
    """Уменьшить количество товара в корзине"""
    item_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        cart = await CartService.get_cart_with_items(session, user.id)
        if cart:
            for item in cart.items:
                if item.id == item_id:
                    new_quantity = item.quantity - 1
                    if new_quantity > 0:
                        await CartService.update_item_quantity(
                            session, user.id, item_id, new_quantity
                        )
                        await session.commit()
                        await callback.answer("✅ Количество уменьшено")
                    else:
                        # Удаляем товар если количество стало 0
                        await CartService.remove_item_from_cart(session, user.id, item_id)
                        await session.commit()
                        await callback.answer("✅ Товар удален из корзины")
                    break
        else:
            await callback.answer("❌ Товар не найден", show_alert=True)
    
    # Обновляем отображение корзины
    await show_cart(callback, None, user)


@router.callback_query(F.data.startswith("cart_set_"))
async def set_cart_item_quantity(callback: CallbackQuery, user: User):
    """Установить определенное количество товара"""
    parts = callback.data.split("_")
    item_id = int(parts[2])
    quantity = int(parts[3])
    
    async with async_session_maker() as session:
        success = await CartService.update_item_quantity(
            session, user.id, item_id, quantity
        )
        if success:
            await session.commit()
            await callback.answer(f"✅ Количество установлено: {quantity}")
        else:
            await callback.answer("❌ Ошибка обновления", show_alert=True)
    
    # Обновляем отображение корзины
    await show_cart(callback, None, user)


@router.callback_query(F.data.startswith("cart_remove_"))
async def remove_cart_item(callback: CallbackQuery, user: User):
    """Удалить товар из корзины"""
    item_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        success = await CartService.remove_item_from_cart(session, user.id, item_id)
        if success:
            await session.commit()
            await callback.answer("✅ Товар удален из корзины")
        else:
            await callback.answer("❌ Товар не найден", show_alert=True)
    
    # Обновляем отображение корзины
    await show_cart(callback, None, user)


@router.callback_query(F.data == "clear_cart")
async def ask_clear_cart(callback: CallbackQuery):
    """Запросить подтверждение очистки корзины"""
    await callback.message.edit_text(
        "🗑 Очистить корзину?\n\nВсе товары будут удалены из корзины.",
        reply_markup=get_confirm_action_keyboard("clear_cart")
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_clear_cart")
async def clear_cart(callback: CallbackQuery, user: User):
    """Очистить корзину"""
    async with async_session_maker() as session:
        success = await CartService.clear_cart(session, user.id)
        if success:
            await session.commit()
            await callback.answer("✅ Корзина очищена")
        else:
            await callback.answer("❌ Корзина уже пуста")
    
    # Показываем пустую корзину
    await show_cart(callback, None, user)


@router.callback_query(F.data == "cancel_clear_cart")
async def cancel_clear_cart(callback: CallbackQuery, user: User):
    """Отменить очистку корзины"""
    await callback.answer("❌ Отменено")
    await show_cart(callback, None, user)


@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext, user: User):
    """Начать оформление заказа"""
    async with async_session_maker() as session:
        cart = await CartService.get_cart_with_items(session, user.id)
        
        if not cart or not cart.items:
            await callback.answer("❌ Корзина пуста", show_alert=True)
            return
        
        # Проверяем минимальную сумму заказа
        from app.config import settings
        if cart.total_amount < settings.min_order_amount:
            await callback.answer(
                f"❌ Минимальная сумма заказа: {settings.min_order_amount} ₽",
                show_alert=True
            )
            return
    
    # Переходим к оформлению заказа (будет реализовано в следующей итерации)
    await callback.message.edit_text(
        "🚧 Оформление заказа\n\nЭта функция будет реализована в следующей версии.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
    await state.set_state(UserStates.MAIN_MENU)
