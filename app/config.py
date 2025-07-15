from typing import List
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class Settings:
    """Настройки приложения"""
    
    def __init__(self):
        # Основные настройки бота
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")
        
        # Администраторы
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.admin_ids: List[int] = []
        if admin_ids_str:
            self.admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        
        # Настройки платежей
        self.payment_card_number: str = os.getenv("PAYMENT_CARD_NUMBER", "")
        self.payment_card_owner: str = os.getenv("PAYMENT_CARD_OWNER", "")
        self.payment_instructions: str = os.getenv(
            "PAYMENT_INSTRUCTIONS", 
            "Переведите сумму на карту и отправьте скриншот"
        )
        
        # Настройки уведомлений
        self.notification_chat_id: int = int(os.getenv("NOTIFICATION_CHAT_ID", "0"))
        
        # Настройки файлов
        self.upload_path: str = os.getenv("UPLOAD_PATH", "./uploads")
        self.max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
        
        # Настройки заказов
        self.min_order_amount: float = float(os.getenv("MIN_ORDER_AMOUNT", "500.0"))
        
        delivery_days_str = os.getenv("DELIVERY_DAYS", "1,2,3,4,5")
        self.delivery_days: List[int] = []
        if delivery_days_str:
            self.delivery_days = [int(x.strip()) for x in delivery_days_str.split(",") if x.strip()]
            
        # Создаем папку для загрузок
        os.makedirs(self.upload_path, exist_ok=True)


# Глобальный объект настроек
settings = Settings()
