#!/bin/bash

# Активируем виртуальную среду
source venv/bin/activate

# Проверяем наличие токена
if grep -q "YOUR_BOT_TOKEN_HERE" .env; then
    echo "❌ Ошибка: Необходимо установить токен бота в файле .env"
    echo "Откройте файл .env и замените YOUR_BOT_TOKEN_HERE на ваш токен от @BotFather"
    exit 1
fi

echo "🚀 Запуск бота..."
python3 app/main.py
