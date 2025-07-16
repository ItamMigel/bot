# Исправление ошибок интерфейса бота

## Проблемы, которые были исправлены:

### 1. Ошибка с типом клавиатуры в админ-панели
**Проблема**: `ValidationError: Input should be a valid dictionary or instance of InlineKeyboardMarkup`

**Решение**: В функции `back_to_main_menu` заменил `edit_text` на `delete()` + `answer()`, так как `edit_text` требует `InlineKeyboardMarkup`, а `get_main_menu_keyboard()` возвращает `ReplyKeyboardMarkup`.

```python
# Было:
await callback.message.edit_text(
    text,
    reply_markup=get_main_menu_keyboard()  # ❌ ReplyKeyboardMarkup
)

# Стало:
await callback.message.delete()
await callback.message.answer(
    text,
    reply_markup=get_main_menu_keyboard()  # ✅ Работает с answer()
)
```

### 2. Ошибка сохранения скриншота
**Проблема**: `type object 'Bot' has no attribute 'get_current'`

**Решение**: Обновил функцию `save_payment_screenshot()` для передачи объекта бота как параметра:

```python
# Было:
bot = Bot.get_current()  # ❌ Не работает в новых версиях

# Стало:
async def save_payment_screenshot(photo, order_id: int, bot=None) -> str:
    if bot:
        await bot.download(photo, file_path)  # ✅ Используем переданный bot
```

И обновил вызов в `orders.py`:
```python
screenshot_path = await save_payment_screenshot(
    message.photo[-1], order_id, message.bot  # ✅ Передаем bot
)
```

### 3. Неработающие кнопки "Главное меню" и "Назад"

**Проблема**: Отсутствовали обработчики для callback_data.

**Решение**: 
- Добавлен обработчик `back_to_orders` в `orders.py`
- Исправлен callback_data в клавиатуре деталей заказа:

```python
# Было:
callback_data="orders"  # ❌ Нет обработчика

# Стало:
callback_data="back_to_orders"  # ✅ Есть обработчик
```

## Результат

✅ **Ошибки с клавиатурами исправлены**
✅ **Скриншоты сохраняются корректно**  
✅ **Кнопки "Главное меню" и "Назад" работают**
✅ **Бот запускается без ошибок**

## Тестирование

Проверьте следующие сценарии:
1. Переход в меню → выбор категории → кнопка "Главное меню"
2. Мои заказы → выбор заказа → кнопка "Назад" 
3. Оформление заказа → загрузка скриншота оплаты
4. Админ-панель → переходы между разделами

Все должно работать корректно! 🎉
