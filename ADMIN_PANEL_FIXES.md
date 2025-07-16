# Bug Fixes - Admin Panel & Notifications

## 🐛 Исправленные проблемы

### 1. ❌ Ошибка уведомлений о новых заказах

**Проблема:** 
```
Parent instance <Order> is not bound to a Session; lazy load operation of attribute 'items' cannot proceed
```

**Причина:** Объект Order передавался в NotificationService без загруженных связанных объектов (items).

**Решение:**
- Переписал функции `notify_admin_new_order()` и `notify_admin_payment_received()`
- Добавил загрузку Order с items через `selectinload(Order.items).selectinload(OrderItem.dish)`
- Создание новой сессии БД внутри функции уведомлений

```python
# ✅ Исправленный код
async def notify_admin_new_order(order, user_obj=None, bot=None):
    async with async_session_maker() as session:
        # Получаем заказ с загруженными items и dish
        order_result = await session.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.dish))
            .where(Order.id == order.id)
        )
        full_order = order_result.scalar_one_or_none()
        
        if full_order and user_obj and bot:
            await NotificationService.notify_new_order(bot, full_order, user_obj)
```

### 2. ❌ Ошибка с кнопкой "Назад" в админ-панели

**Проблема:** 
```
TelegramBadRequest: message is not modified: specified new message content and reply markup are exactly the same
```

**Причина:** В функции `show_order_details` в конце были рекурсивные вызовы, которые создавали дублирование сообщений.

**Решение:**
- Удалил лишние строки кода в конце функции `show_order_details`
- Исправил callback_data в функции `show_pending_orders` с `"admin_panel"` на `"back_to_admin_panel"`

```python
# ❌ Было (в конце функции show_order_details):
await callback.answer("🍽 Заказ отмечен как готовый!")
await show_order_details(callback)  # Рекурсивный вызов!

# ✅ Стало:
await callback.answer()
```

```python
# ❌ Было:
keyboard.append([{"text": "🔙 Назад", "callback_data": "admin_panel"}])

# ✅ Стало:
keyboard.append([{"text": "🔙 Назад", "callback_data": "back_to_admin_panel"}])
```

## 🎯 Результат

### ✅ Уведомления теперь работают корректно:
- Админы получают уведомления о новых заказах (наличные и карта)
- Админы получают уведомления о скриншотах оплаты
- Пользователи получают уведомления об изменении статуса заказа

### ✅ Навигация в админ-панели исправлена:
- Кнопка "Назад" в списке заказов на модерации работает
- Кнопка "К заказам" в детальном просмотре заказа работает
- Нет дублирования сообщений
- Нет бесконечных циклов обновления

## 🧪 Тестирование

Для проверки исправлений:

1. **Тест уведомлений:**
   - Создайте заказ с оплатой наличными
   - Проверьте, что админ получил уведомление
   - Загрузите скриншот оплаты (для карты)
   - Проверьте уведомление о скриншоте

2. **Тест навигации админ-панели:**
   - Войдите в админ-панель `/admin`
   - Перейдите в "Заказы на модерации"
   - Откройте детали заказа
   - Используйте кнопки "Назад"/"К заказам"
   - Убедитесь в отсутствии ошибок

## 📝 Дополнительные улучшения

- Добавлен импорт `OrderItem` в `orders.py`
- Улучшена обработка ошибок в функциях уведомлений
- Добавлено логирование для диагностики проблем

## 🎉 Статус

**✅ Все проблемы исправлены!** 

Система уведомлений и админ-панель теперь работают стабильно.
