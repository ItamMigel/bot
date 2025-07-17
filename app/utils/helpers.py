"""Вспомогательные функции"""
import os
import uuid
from datetime import datetime
from typing import Optional
from app.config import settings


def format_price(price: float) -> str:
    """Форматирование цены"""
    return f"{price:.0f} руб"


def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени"""
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt: datetime) -> str:
    """Форматирование даты"""
    return dt.strftime("%d.%m.%Y")


def get_user_display_name(user) -> str:
    """Получить отображаемое имя пользователя"""
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    else:
        return f"Пользователь {user.telegram_id}"


def generate_filename(original_filename: str) -> str:
    """Генерация уникального имени файла"""
    ext = os.path.splitext(original_filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


async def save_file(file_content: bytes, filename: str) -> str:
    """Сохранение файла на диск"""
    file_path = os.path.join(settings.upload_path, filename)
    
    # Создаем директорию если не существует
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    return file_path


def is_valid_image_type(filename: str) -> bool:
    """Проверка типа изображения"""
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ext = os.path.splitext(filename)[1].lower()
    return ext in valid_extensions


def get_file_size_mb(file_size: int) -> float:
    """Получить размер файла в МБ"""
    return file_size / (1024 * 1024)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста с многоточием"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_order_items(items) -> str:
    """Форматирование списка позиций заказа"""
    if not items:
        return "Нет позиций"
    
    formatted_items = []
    for item in items:
        formatted_items.append(
            f"• {item.dish.name} x{item.quantity} = {format_price(item.total_price)} ₽"
        )
    
    return "\n".join(formatted_items)


def calculate_cart_total(cart_items) -> float:
    """Вычисление общей суммы корзины"""
    return sum(item.total_price for item in cart_items)


def validate_phone_number(phone: str) -> bool:
    """Валидация номера телефона"""
    # Простая валидация - только цифры и знаки
    cleaned = ''.join(c for c in phone if c.isdigit() or c in '+-()')
    return len(cleaned) >= 10


def clean_phone_number(phone: str) -> str:
    """Очистка номера телефона"""
    return ''.join(c for c in phone if c.isdigit() or c == '+')


def get_order_status_emoji(status: str) -> str:
    """Получить эмодзи для статуса заказа"""
    status_emojis = {
        "cart": "🛒",
        "pending_payment": "⏳",
        "payment_received": "🔍", 
        "confirmed": "✅",
        "ready": "🎉",
        "completed": "✅",
        "cancelled": "❌"
    }
    return status_emojis.get(status, "❓")


def get_weekday_name(weekday: int) -> str:
    """Получить название дня недели по номеру (1-понедельник)"""
    weekdays = {
        1: "Понедельник",
        2: "Вторник", 
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье"
    }
    return weekdays.get(weekday, "Неизвестно")


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in settings.admin_ids


async def get_file_url(file_path: str) -> Optional[str]:
    """Получить URL файла для отображения"""
    if not file_path or not os.path.exists(file_path):
        return None
    
    # В реальном приложении здесь может быть логика
    # для получения URL из CDN или файлового сервера
    return file_path


async def save_payment_screenshot(photo, order_id: int, bot=None) -> str:
    """Сохранить скриншот оплаты"""
    try:
        # Создаем директорию для скриншотов если её нет
        screenshots_dir = os.path.join(settings.upload_path, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Генерируем уникальное имя файла
        filename = f"payment_{order_id}_{uuid.uuid4().hex}.jpg"
        file_path = os.path.join(screenshots_dir, filename)
        
        # Используем переданный bot объект
        if bot:
            await bot.download(photo, file_path)
        else:
            # Пробуем альтернативный способ
            file_info = await photo.get_file()
            file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    with open(file_path, 'wb') as f:
                        f.write(await resp.read())
        
        # Возвращаем относительный путь
        return f"screenshots/{filename}"
        
    except Exception as e:
        print(f"Ошибка сохранения скриншота: {e}")
        return ""
