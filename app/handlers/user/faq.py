"""Обработчики для FAQ и обратной связи"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.utils import texts, UserStates
from app.keyboards.user import get_main_menu_keyboard
from app.database import async_session_maker, User

router = Router()


@router.message(F.text == texts.BUTTON_FAQ)
@router.callback_query(F.data == "faq")
async def show_faq(event: Message | CallbackQuery, state: FSMContext):
    """Показать FAQ"""
    await state.set_state(UserStates.VIEWING_FAQ)
    
    # Создаем клавиатуру с вопросами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚚 Доставка", callback_data="faq_delivery")],
        [InlineKeyboardButton(text="💳 Оплата", callback_data="faq_payment")],
        [InlineKeyboardButton(text="📱 Как сделать заказ", callback_data="faq_order")],
        [InlineKeyboardButton(text="📊 Статусы заказов", callback_data="faq_statuses")],
        [InlineKeyboardButton(text="📞 Связаться с нами", callback_data="contact_us")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    if isinstance(event, Message):
        await event.answer(
            texts.FAQ_MAIN_MESSAGE,
            reply_markup=keyboard
        )
    else:
        await event.message.edit_text(
            texts.FAQ_MAIN_MESSAGE,
            reply_markup=keyboard
        )
        await event.answer()


@router.callback_query(F.data.startswith("faq_"))
async def show_faq_answer(callback: CallbackQuery, state: FSMContext):
    """Показать ответ на конкретный вопрос"""
    faq_type = callback.data.split("_")[1]
    
    # Получаем текст ответа
    faq_answers = {
        "delivery": texts.FAQ_DELIVERY,
        "payment": texts.FAQ_PAYMENT,
        "order": texts.FAQ_ORDER,
        "statuses": texts.FAQ_STATUSES
    }
    
    answer_text = faq_answers.get(faq_type, texts.FAQ_NOT_FOUND)
    
    # Клавиатура для возврата к FAQ
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
        [InlineKeyboardButton(text="📞 Связаться с нами", callback_data="contact_us")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        answer_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "contact_us")
async def show_contact_form(callback: CallbackQuery, state: FSMContext):
    """Показать форму обратной связи"""
    await state.set_state(UserStates.WRITING_FEEDBACK)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        texts.CONTACT_FORM_MESSAGE,
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(StateFilter(UserStates.WRITING_FEEDBACK))
async def receive_feedback(message: Message, state: FSMContext, user: User):
    """Получить сообщение обратной связи"""
    feedback_text = message.text.strip()
    
    if len(feedback_text) < 10:
        await message.answer(
            texts.FEEDBACK_TOO_SHORT,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")]
            ])
        )
        return
    
    # Сохраняем обращение (можно добавить в БД если нужно)
    await save_feedback(user, feedback_text)
    
    # Уведомляем администратора
    await notify_admin_feedback(user, feedback_text, message.bot)
    
    await message.answer(
        texts.FEEDBACK_RECEIVED,
        reply_markup=get_main_menu_keyboard()
    )
    
    await state.set_state(UserStates.MAIN_MENU)


async def save_feedback(user: User, feedback_text: str):
    """Сохранить обращение в лог (можно расширить для БД)"""
    logging.info(f"Feedback from user {user.telegram_id} ({user.first_name}): {feedback_text}")


async def notify_admin_feedback(user: User, feedback_text: str, bot=None):
    """Уведомить администратора о новом обращении"""
    try:
        from app.services.notifications import NotificationService
        if bot:
            await NotificationService.notify_feedback(bot, user, feedback_text)
        else:
            logging.info(f"Feedback from user {user.telegram_id}: {feedback_text}")
    except Exception as e:
        logging.error(f"Ошибка уведомления о feedback: {e}")
