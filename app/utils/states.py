from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """Состояния для пользователей"""
    # Главное меню
    MAIN_MENU = State()
    
    # Просмотр меню
    BROWSING_MENU = State()
    VIEWING_DISH = State()
    ADDING_TO_CART = State()
    ENTERING_QUANTITY = State()  # Новое состояние для ввода количества
    
    # Корзина
    VIEWING_CART = State()
    EDITING_CART_ITEM = State()
    
    # Оформление заказа
    CONFIRMING_ORDER = State()
    CHOOSING_PAYMENT = State()
    UPLOADING_PAYMENT_SCREENSHOT = State()
    ADDING_ORDER_NOTES = State()
    
    # Заказы
    VIEWING_ORDERS = State()
    VIEWING_ORDER_DETAILS = State()
    
    # FAQ и обратная связь
    VIEWING_FAQ = State()
    WRITING_FEEDBACK = State()
    
    # Профиль
    EDITING_PROFILE = State()
    ENTERING_PHONE = State()


class AdminStates(StatesGroup):
    """Состояния для администраторов"""
    # Главное меню админа
    ADMIN_MAIN = State()
    
    # Управление заказами
    MANAGING_ORDERS = State()
    VIEWING_ORDER_ADMIN = State()
    CHANGING_ORDER_STATUS = State()
    
    # Управление меню
    MANAGING_MENU = State()
    MANAGING_CATEGORIES = State()
    MANAGING_DISHES = State()
    
    # Создание/редактирование категории
    CREATING_CATEGORY = State()
    EDITING_CATEGORY = State()
    ENTERING_CATEGORY_NAME = State()
    ENTERING_CATEGORY_DESCRIPTION = State()
    UPLOADING_CATEGORY_IMAGE = State()
    
    # Создание/редактирование блюда
    CREATING_DISH = State()
    EDITING_DISH = State()
    ENTERING_DISH_NAME = State()
    ENTERING_DISH_DESCRIPTION = State()
    ENTERING_DISH_PRICE = State()
    ENTERING_DISH_LINK = State()  # Новое состояние для ввода ссылки на пост
    UPLOADING_DISH_IMAGE = State()
    CHOOSING_DISH_CATEGORY = State()
    
    # Статистика
    VIEWING_STATS = State()
    
    # Настройки
    ADMIN_SETTINGS = State()


class CommonStates(StatesGroup):
    """Общие состояния"""
    WAITING_FOR_INPUT = State()
    UPLOADING_FILE = State()
    CONFIRMING_ACTION = State()
