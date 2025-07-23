1. На пустой базе данных не работает кнопка "Все заказы" в меню пользователя.
2. В пункте "Помощь" я вижу системные теги, т.е. для пользователя текст отображается так: О🔥 <2️⃣ 💰 `<b>`Оплачен, ожидает подтверждения`</b>` - платеж получен, проверяю>Активные заказы:`</b>`
3. Во время создания имени для повторниго заказа выдает ошибку:
   2025-07-23 21:12:21,991 - aiogram.event - ERROR - Cause exception while process update id=178492897 by bot id=8079244795
   TypeError: process_custom_order_name.`<locals>`.`<lambda>`() got an unexpected keyword argument 'show_alert'
   Traceback (most recent call last):
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/dispatcher.py", line 309, in _process_update
   response = await self.feed_update(bot, update, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/dispatcher.py", line 158, in feed_update
   response = await self.update.wrap_outer_middleware(
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   ...<7 lines>...
   )
   ^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/middlewares/error.py", line 25, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/middlewares/user_context.py", line 56, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/fsm/middleware.py", line 42, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/telegram.py", line 121, in trigger
   return await wrapped_inner(event, kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/handler.py", line 43, in call
   return await wrapped()
   ^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/dispatcher.py", line 276, in _listen_update
   return await self.propagate_event(update_type=update_type, event=event, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 146, in propagate_event
   return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 141, in _wrapped
   return await self._propagate_event(
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   observer=observer, update_type=update_type, event=telegram_event, **data
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   )
   ^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 174, in _propagate_event
   response = await router.propagate_event(update_type=update_type, event=event, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 146, in propagate_event
   return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 141, in _wrapped
   return await self._propagate_event(
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   observer=observer, update_type=update_type, event=telegram_event, **data
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   )
   ^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 166, in _propagate_event
   response = await observer.trigger(event, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/telegram.py", line 121, in trigger
   return await wrapped_inner(event, kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/app/middlewares/auth.py", line 53, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/app/middlewares/admin.py", line 25, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/handler.py", line 43, in call
   return await wrapped()
   ^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/app/handlers/user/orders.py", line 395, in process_custom_order_name
   await _process_repeat_order(fake_callback, state, user, order_id, custom_name)
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/app/handlers/user/orders.py", line 432, in _process_repeat_order
   await callback_or_message.answer(error_text, show_alert=True)
   ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   TypeError: process_custom_order_name.`<locals>`.`<lambda>`() got an unexpected keyword argument 'show_alert'
4. Кнопка "пропустить" в этом окне также не работает:
   2025-07-23 21:13:17,101 - aiogram.event - ERROR - Cause exception while process update id=178492898 by bot id=8079244795
   ValueError: invalid literal for int() with base 10: 'skip'
   Traceback (most recent call last):
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/dispatcher.py", line 309, in _process_update
   response = await self.feed_update(bot, update, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/dispatcher.py", line 158, in feed_update
   response = await self.update.wrap_outer_middleware(
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   ...<7 lines>...
   )
   ^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/middlewares/error.py", line 25, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/middlewares/user_context.py", line 56, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/fsm/middleware.py", line 42, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/telegram.py", line 121, in trigger
   return await wrapped_inner(event, kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/handler.py", line 43, in call
   return await wrapped()
   ^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/dispatcher.py", line 276, in _listen_update
   return await self.propagate_event(update_type=update_type, event=event, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 146, in propagate_event
   return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 141, in _wrapped
   return await self._propagate_event(
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   observer=observer, update_type=update_type, event=telegram_event, **data
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   )
   ^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 174, in _propagate_event
   response = await router.propagate_event(update_type=update_type, event=event, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 146, in propagate_event
   return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 141, in _wrapped
   return await self._propagate_event(
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   observer=observer, update_type=update_type, event=telegram_event, **data
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   )
   ^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/router.py", line 166, in _propagate_event
   response = await observer.trigger(event, **kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/telegram.py", line 121, in trigger
   return await wrapped_inner(event, kwargs)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/app/middlewares/auth.py", line 53, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/app/middlewares/admin.py", line 25, in __call__
   return await handler(event, data)
   ^^^^^^^^^^^^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/venv/lib/python3.13/site-packages/aiogram/dispatcher/event/handler.py", line 43, in call
   return await wrapped()
   ^^^^^^^^^^^^^^^
   File "/Users/pavel/projects/test folder/copilot/chto_by_prigotovit_bot v.2/app/handlers/user/orders.py", line 342, in repeat_order_prompt_name
   order_id = int(callback.data.split("_")[2])
   ValueError: invalid literal for int() with base 10: 'skip'
5. Кнопка назад в этом меню так же не работает.
6. В меню создания блюда отсуствует поле для ссылки на пост.
7. Когда меняешь нащвание блюда все дальнейшие команды бот воспринимает как новые названия блюда и меняет старое название на команду, пример:

> Что бы приготовить?:
> ✏️ Изменение названия блюда

Текущее название: письки

Введите новое название:

> Pavel Sardak:
> фывфв

> Что бы приготовить?:
> 🍽 фывфв

💰 Цена: 200.0₽
📊 Статус: ✅ Доступно
📄 Описание: ыотадотфыв

Выберите действие:

> Pavel Sardak:
> 📋 Мои заказы

> Что бы приготовить?:
> ✅ Название блюда изменено!
> Было: фывфв
> Стало: 📋 Мои заказы
>
