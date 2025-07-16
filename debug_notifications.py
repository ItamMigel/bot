#!/usr/bin/env python3
"""
Диагностика уведомлений для админ-панели
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_notification_config():
    """Проверить конфигурацию уведомлений"""
    print("🔍 Диагностика уведомлений")
    print("=" * 50)
    
    # Загружаем .env
    load_dotenv()
    
    # Проверяем конфигурацию
    bot_token = os.getenv("BOT_TOKEN", "")
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    
    print(f"📋 Конфигурация:")
    print(f"   BOT_TOKEN: {'✅ Установлен' if bot_token and bot_token != 'your_bot_token_here' else '❌ Не установлен'}")
    print(f"   ADMIN_IDS: {admin_ids_str}")
    
    if not admin_ids_str:
        print("❌ ADMIN_IDS не настроены!")
        return False
    
    try:
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        print(f"   Найдено админов: {len(admin_ids)}")
        for i, admin_id in enumerate(admin_ids, 1):
            print(f"   {i}. ID: {admin_id}")
    except ValueError as e:
        print(f"❌ Ошибка в формате ADMIN_IDS: {e}")
        return False
    
    if not bot_token or bot_token == "your_bot_token_here":
        print("❌ BOT_TOKEN не настроен!")
        return False
    
    # Тестируем подключение к боту
    try:
        from app.config import settings
        from app.services.notifications import NotificationService
        from aiogram import Bot
        
        bot = Bot(token=settings.bot_token)
        
        # Проверяем информацию о боте
        bot_info = await bot.get_me()
        print(f"\n🤖 Информация о боте:")
        print(f"   Имя: {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   ID: {bot_info.id}")
        
        # Тестируем отправку уведомления
        print(f"\n📨 Тестируем отправку уведомления админам...")
        test_message = "🧪 Тест уведомлений. Если вы получили это сообщение, уведомления работают!"
        
        result = await NotificationService.notify_admins(bot, test_message)
        
        if result:
            print("✅ Тестовое уведомление отправлено успешно!")
        else:
            print("❌ Не удалось отправить тестовое уведомление")
        
        await bot.session.close()
        return result
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Убедитесь, что все зависимости установлены")
        return False
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    print("Запуск диагностики уведомлений...")
    print("Убедитесь, что .env файл настроен правильно\n")
    
    try:
        result = asyncio.run(test_notification_config())
        if result:
            print("\n🎉 Уведомления настроены корректно!")
        else:
            print("\n💥 Обнаружены проблемы с уведомлениями")
            print("Проверьте:")
            print("1. Правильность BOT_TOKEN")
            print("2. Правильность ADMIN_IDS")
            print("3. Что боты не заблокированы администраторами")
    except KeyboardInterrupt:
        print("\n⚠️ Диагностика прервана пользователем")
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
