"""Тексты сообщений для бота"""

# Основные команды
START_MESSAGE = """
🍽 Добро пожаловать в "Что Бы Приготовить"!

Здесь вы можете заказать вкусные домашние заготовки и блюда.

Выберите действие из меню ниже:
"""

HELP_MESSAGE = """
🆘 Помощь

Доступные команды:
• 🍽 Меню - просмотр всех блюд
• 🛒 Корзина - ваши выбранные товары  
• 📋 Заказы - история и текущие заказы
• ❓ Помощь - эта справка

Для заказа:
1. Выберите блюда из меню
2. Добавьте их в корзину
3. Оформите заказ
4. Оплатите и отправьте скриншот
5. Дождитесь подтверждения

По вопросам обращайтесь к администратору.
"""

# Меню
MENU_MESSAGE = "🍽 Меню блюд\n\nВыберите категорию:"
CATEGORY_MESSAGE = "📂 Категория: {category_name}\n\n{description}"
DISH_MESSAGE = """
🍽 {dish_name}

{description}

💰 Цена: {price} ₽

Количество порций для добавления в корзину:
"""

NO_DISHES_IN_CATEGORY = "В данной категории пока нет блюд."
DISH_ADDED_TO_CART = "✅ Блюдо добавлено в корзину!"
DISH_UPDATED_IN_CART = "✅ Количество в корзине обновлено!"

# Корзина
CART_EMPTY = "🛒 Ваша корзина пуста\n\nПерейдите в меню, чтобы добавить блюда."
CART_MESSAGE = """
🛒 Ваша корзина:

{cart_items}

💰 Общая сумма: {total_amount} ₽
"""

CART_ITEM_FORMAT = "• {dish_name} x{quantity} = {total_price} ₽"

# Заказы
NO_ORDERS = "📋 У вас пока нет заказов"
ORDERS_LIST_MESSAGE = "📋 Ваши заказы:"
ORDER_DETAILS_MESSAGE = """
📋 Заказ #{order_id}

📅 Дата: {created_at}
📊 Статус: {status}
💰 Сумма: {total_amount} ₽

🍽 Состав заказа:
{order_items}

{payment_info}
"""

ORDER_ITEM_FORMAT = "• {dish_name} x{quantity} = {total_price} ₽"

# Статусы заказов
ORDER_STATUSES = {
    "cart": "🛒 Корзина",
    "pending_payment": "⏳ Ожидает оплаты", 
    "payment_confirmation": "🔍 Проверка оплаты",
    "confirmed": "✅ Подтвержден",
    "ready": "🎉 Готов к выдаче",
    "completed": "✅ Завершен",
    "cancelled": "❌ Отменен"
}

# Оформление заказа
ORDER_CONFIRMATION = """
📋 Подтверждение заказа

{cart_items}

💰 Итого: {total_amount} ₽

Подтвердите заказ для перехода к оплате.
"""

PAYMENT_METHOD_MESSAGE = "💳 Выберите способ оплаты:"

PAYMENT_CARD_INFO = """
💳 Оплата картой

Переведите {amount} ₽ на карту:
{card_number}
{card_owner}

{instructions}

После перевода отправьте скриншот чека.
"""

PAYMENT_CASH_INFO = """
💵 Оплата наличными

Сумма к оплате: {amount} ₽

Оплата производится при получении заказа.
Ваш заказ отправлен на подтверждение.
"""

ORDER_CREATED = """
✅ Заказ создан!

Номер заказа: #{order_id}
Сумма: {total_amount} ₽

Статус заказа можно отслеживать в разделе "Мои заказы".
"""

PAYMENT_SCREENSHOT_PROMPT = """
📸 Отправьте скриншот оплаты

Загрузите изображение чека или скриншот перевода.
"""

PAYMENT_SCREENSHOT_RECEIVED = """
✅ Скриншот получен!

Ваш платеж отправлен на проверку администратору.
Как только оплата будет подтверждена, мы начнем готовить ваш заказ.
"""

# Ошибки
ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте еще раз."
INVALID_QUANTITY = "❌ Неверное количество. Введите число от 1 до 10."
INVALID_FILE_TYPE = "❌ Неподдерживаемый тип файла. Отправьте изображение."
FILE_TOO_LARGE = "❌ Файл слишком большой. Максимальный размер: 10 МБ."
MIN_ORDER_AMOUNT_ERROR = "❌ Минимальная сумма заказа: {min_amount} ₽"
NOT_AUTHORIZED = "❌ У вас нет прав для выполнения этого действия."

# Кнопки
BUTTON_MENU = "🍽 Меню"
BUTTON_CART = "🛒 Корзина"
BUTTON_ORDERS = "📋 Мои заказы" 
BUTTON_HELP = "❓ Помощь"
BUTTON_PROFILE = "👤 Профиль"

BUTTON_ADD_TO_CART = "➕ В корзину"
BUTTON_BACK = "⬅️ Назад"
BUTTON_MAIN_MENU = "🏠 Главное меню"

BUTTON_CHECKOUT = "💳 Оформить заказ"
BUTTON_CLEAR_CART = "🗑 Очистить корзину"
BUTTON_UPDATE_QUANTITY = "✏️ Изменить количество"
BUTTON_REMOVE_ITEM = "❌ Удалить"

BUTTON_CONFIRM_ORDER = "✅ Подтвердить заказ"
BUTTON_CANCEL_ORDER = "❌ Отменить"

BUTTON_PAY_CARD = "💳 Картой"
BUTTON_PAY_CASH = "💵 Наличными"

BUTTON_REPEAT_ORDER = "🔄 Повторить заказ"
BUTTON_ORDER_DETAILS = "📋 Подробнее"

# Админские сообщения
ADMIN_MAIN_MESSAGE = """
👨‍💼 Панель администратора

Выберите действие:
"""

NEW_ORDER_NOTIFICATION = """
🔔 Новый заказ #{order_id}

👤 Пользователь: {user_name}
💰 Сумма: {total_amount} ₽
📅 Дата: {created_at}

{order_items}
"""

PAYMENT_RECEIVED_NOTIFICATION = """
💰 Получен платеж

📋 Заказ: #{order_id}
💰 Сумма: {amount} ₽
👤 От: {user_name}

Проверьте и подтвердите оплату.
"""

# Кнопки админа
BUTTON_ADMIN_ORDERS = "📋 Заказы"
BUTTON_ADMIN_MENU = "🍽 Управление меню"
BUTTON_ADMIN_STATS = "📊 Статистика"
BUTTON_ADMIN_SETTINGS = "⚙️ Настройки"

BUTTON_CONFIRM_PAYMENT = "✅ Подтвердить оплату"
BUTTON_REJECT_PAYMENT = "❌ Отклонить"
BUTTON_CHANGE_STATUS = "📊 Изменить статус"
