"""Клавиатуры для пользователей"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import List, Optional
from app.utils import texts


def get_main_menu_keyboard(cart_count: int = 0) -> ReplyKeyboardMarkup:
    """Основное меню пользователя"""
    builder = ReplyKeyboardBuilder()
    
    # Кнопка корзины с количеством товаров
    cart_text = texts.BUTTON_CART
    if cart_count > 0:
        cart_text += f" ({cart_count})"
    
    builder.row(
        KeyboardButton(text=texts.BUTTON_MENU),
        KeyboardButton(text=cart_text)
    )
    builder.row(
        KeyboardButton(text=texts.BUTTON_ORDERS),
        KeyboardButton(text=texts.BUTTON_FAQ)
    )
    builder.row(
        KeyboardButton(text=texts.BUTTON_HELP)
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_categories_keyboard(categories) -> InlineKeyboardMarkup:
    """Клавиатура с категориями блюд"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📂 {category.name}",
                callback_data=f"category_{category.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_MAIN_MENU,
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()


def get_dishes_keyboard(dishes, category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с блюдами категории"""
    builder = InlineKeyboardBuilder()
    
    for dish in dishes:
        # Показываем цену в названии кнопки
        dish_text = f"{dish.name} - {dish.price:.0f}₽"
        if not dish.is_available:
            dish_text += " (недоступно)"
            
        builder.row(
            InlineKeyboardButton(
                text=dish_text,
                callback_data=f"dish_{dish.id}" if dish.is_available else "dish_unavailable"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_BACK,
            callback_data="menu"
        ),
        InlineKeyboardButton(
            text=texts.BUTTON_MAIN_MENU,
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()


def get_dish_detail_keyboard(dish_id: int, category_id: int, dish=None) -> InlineKeyboardMarkup:
    """Клавиатура для деталей блюда"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки для выбора количества
    quantities = [1, 2, 3, 4, 5]
    quantity_buttons = []
    
    for qty in quantities:
        quantity_buttons.append(
            InlineKeyboardButton(
                text=str(qty),
                callback_data=f"add_to_cart_{dish_id}_{qty}"
            )
        )
    
    # Разбиваем на ряды по 3 кнопки
    for i in range(0, len(quantity_buttons), 3):
        builder.row(*quantity_buttons[i:i+3])
    
    # Добавляем кнопку для ввода произвольного количества
    builder.row(
        InlineKeyboardButton(
            text="✏️ Ввести количество",
            callback_data=f"input_quantity_{dish_id}_{category_id}"
        )
    )
    
    # Кнопка для ссылки на пост в канале (если есть)
    if dish and dish.telegram_post_url:
        builder.row(
            InlineKeyboardButton(
                text="📖 Подробнее в канале",
                url=dish.telegram_post_url
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_BACK,
            callback_data=f"category_{category_id}"
        ),
        InlineKeyboardButton(
            text=texts.BUTTON_MAIN_MENU,
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()


def get_cart_keyboard(cart_items) -> InlineKeyboardMarkup:
    """Клавиатура для корзины"""
    builder = InlineKeyboardBuilder()
    
    if cart_items:
        # Кнопки для каждого товара в корзине
        for item in cart_items:
            builder.row(
                InlineKeyboardButton(
                    text=f"✏️ {item.dish.name} (x{item.quantity})",
                    callback_data=f"edit_cart_item_{item.id}"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text=texts.BUTTON_CHECKOUT,
                callback_data="checkout"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=texts.BUTTON_CLEAR_CART,
                callback_data="clear_cart"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_MENU,
            callback_data="menu"
        ),
        InlineKeyboardButton(
            text=texts.BUTTON_MAIN_MENU,
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()


def get_cart_item_edit_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для редактирования позиции в корзине"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки изменения количества
    builder.row(
        InlineKeyboardButton(text="-", callback_data=f"cart_decrease_{item_id}"),
        InlineKeyboardButton(text="1", callback_data=f"cart_set_{item_id}_1"),
        InlineKeyboardButton(text="2", callback_data=f"cart_set_{item_id}_2"),
        InlineKeyboardButton(text="3", callback_data=f"cart_set_{item_id}_3"),
        InlineKeyboardButton(text="+", callback_data=f"cart_increase_{item_id}")
    )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_REMOVE_ITEM,
            callback_data=f"cart_remove_{item_id}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_BACK,
            callback_data="cart"
        )
    )
    
    return builder.as_markup()


def get_order_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заказа"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_CONFIRM_ORDER,
            callback_data="confirm_order"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_CANCEL_ORDER,
            callback_data="cart"
        )
    )
    
    return builder.as_markup()


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_PAY_CARD,
            callback_data="payment_card"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_BACK,
            callback_data="cart"
        )
    )
    
    return builder.as_markup()


def get_orders_filter_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора фильтра заказов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔥 Активные заказы",
            callback_data="orders_active"
        ),
        InlineKeyboardButton(
            text="✅ Завершенные",
            callback_data="orders_completed"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="📋 Все заказы",
            callback_data="orders_all"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_MAIN_MENU,
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()


def get_orders_keyboard(orders, filter_type="all") -> InlineKeyboardMarkup:
    """Клавиатура со списком заказов"""
    builder = InlineKeyboardBuilder()
    
    for order in orders:
        status_emoji = "🛒" if order.status == "cart" else "📋"
        if order.is_active:
            status_emoji = "🔥"
        elif order.is_completed:
            status_emoji = "✅"
            
        order_text = f"{status_emoji} Заказ #{order.id} - {order.total_amount:.0f}₽"
        
        builder.row(
            InlineKeyboardButton(
                text=order_text,
                callback_data=f"order_{order.id}"
            )
        )
    
    # Кнопки фильтров
    filter_buttons = []
    if filter_type != "active":
        filter_buttons.append(
            InlineKeyboardButton(
                text="🔥 Активные",
                callback_data="orders_active"
            )
        )
    if filter_type != "completed":
        filter_buttons.append(
            InlineKeyboardButton(
                text="✅ Завершенные", 
                callback_data="orders_completed"
            )
        )
    if filter_type != "all":
        filter_buttons.append(
            InlineKeyboardButton(
                text="📋 Все",
                callback_data="orders_all"
            )
        )
    
    if filter_buttons:
        builder.row(*filter_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_MAIN_MENU,
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()


def get_order_details_keyboard(order_id: int, can_repeat: bool = False, can_cancel: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для деталей заказа"""
    builder = InlineKeyboardBuilder()
    
    if can_repeat:
        builder.row(
            InlineKeyboardButton(
                text=texts.BUTTON_REPEAT_ORDER,
                callback_data=f"repeat_order_{order_id}"
            )
        )
    
    if can_cancel:
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить заказ",
                callback_data=f"cancel_order_confirm_{order_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=texts.BUTTON_BACK,
            callback_data="back_to_orders"
        ),
        InlineKeyboardButton(
            text=texts.BUTTON_MAIN_MENU,
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()


def get_confirm_action_keyboard(action: str, item_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Общая клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    
    confirm_callback = f"confirm_{action}"
    cancel_callback = f"cancel_{action}"
    
    if item_id:
        confirm_callback += f"_{item_id}"
        cancel_callback += f"_{item_id}"
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=confirm_callback),
        InlineKeyboardButton(text="❌ Нет", callback_data=cancel_callback)
    )
    
    return builder.as_markup()
