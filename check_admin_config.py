#!/usr/bin/env python3
"""
Скрипт для проверки настроек админ-панели
"""

import os
from dotenv import load_dotenv

def check_admin_config():
    """Проверить настройки администраторов"""
    print("🔍 Проверка настроек админ-панели")
    print("=" * 40)
    
    # Загружаем .env
    load_dotenv()
    
    # Проверяем BOT_TOKEN
    bot_token = os.getenv("BOT_TOKEN", "")
    if bot_token and bot_token != "your_bot_token_here":
        print("✅ BOT_TOKEN настроен")
    else:
        print("❌ BOT_TOKEN не настроен или использует значение по умолчанию")
        print("   Установите реальный токен бота в .env файле")
    
    # Проверяем ADMIN_IDS
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if admin_ids_str:
        try:
            admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
            print(f"✅ ADMIN_IDS настроены: {len(admin_ids)} администратор(ов)")
            for i, admin_id in enumerate(admin_ids, 1):
                print(f"   {i}. ID: {admin_id}")
        except ValueError:
            print("❌ ADMIN_IDS содержат некорректные значения")
            print(f"   Текущее значение: {admin_ids_str}")
            print("   Должно быть: числовые ID через запятую")
    else:
        print("❌ ADMIN_IDS не настроены")
        print("   Добавьте в .env: ADMIN_IDS=ваш_telegram_id")
    
    print("\n" + "=" * 40)
    
    # Инструкции
    if not admin_ids_str or not bot_token or bot_token == "your_bot_token_here":
        print("📋 Для настройки админ-панели:")
        print("1. Скопируйте .env.example в .env")
        print("2. Укажите реальный BOT_TOKEN")
        print("3. Укажите ваш Telegram ID в ADMIN_IDS")
        print("4. Перезапустите бота")
        print("5. Отправьте команду /admin боту")
    else:
        print("🎉 Настройки корректны!")
        print("📱 Для входа в админ-панель:")
        print("   • Отправьте команду /admin боту")
        print("   • Или нажмите кнопку 'Админ-панель' в главном меню")

if __name__ == "__main__":
    check_admin_config()
