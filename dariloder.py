import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
import traceback
import logging

# Настройка логирования для скрытия сообщений TelegramConflictError
logging.basicConfig(level=logging.ERROR)
# Отключаем логи aiogram
aiogram_logger = logging.getLogger("aiogram")
aiogram_logger.setLevel(logging.CRITICAL)
# Отключаем логи для aiohttp
aiohttp_logger = logging.getLogger("aiohttp")
aiohttp_logger.setLevel(logging.CRITICAL)

# --- Настройки для aiogram-бота ---
# Проверяем формат токена: должен быть вида 123456789:AABBCCDDEEFFaabbccddeeff
# Текущий токен: "7956606366:AAFbvZ54ReZMlZnQHg4xfKNS2j640sMp_9o"
# Возможно, токен неверный. Исправляем формат, добавляя "AAA" после первой части, если нужно
tokenbot = "7956606366:AAFbvZ54ReZMlZnQHg4xfKNS2j640sMp_9o"
admin_ids = [-4880088369]  # ID группы для отправки и ожидания ответа

is_approved = False
approval_completed = False  # флаг для проверки завершения подтверждения
waiting_field = None
bot_instance = None  # глобальный экземпляр бота
bot_loop = None  # глобальный event loop

async def send_admin_message(text, reply_markup=None, photo=None):
    global bot_instance, admin_ids
    if bot_instance is None:
        raise Exception("Бот ещё не инициализирован")
    
    # Отправляем сообщение каждому администратору с повторными попытками
    for admin_id in admin_ids:
        # Делаем до 3 попыток отправки с задержками
        for attempt in range(3):
            try:
                if photo:
                    await bot_instance.send_photo(chat_id=admin_id, photo=photo, caption=text, reply_markup=reply_markup)
                else:
                    await bot_instance.send_message(chat_id=admin_id, text=text, reply_markup=reply_markup)
                # Если отправка успешна, выходим из цикла попыток
                break
            except Exception as e:
                print(f"Попытка {attempt+1}/3: Ошибка при отправке администратору {admin_id}: {e}")
                if attempt < 2:  # Если это не последняя попытка
                    # Добавляем экспоненциальную задержку перед следующей попыткой
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    print(f"Не удалось отправить сообщение администратору {admin_id} после 3 попыток")

async def start_handler(message: types.Message):
    if message.from_user.id in admin_ids:
        await message.answer(
            "Привет, админ! Для запуска используйте кнопки под сообщением.\n"
            "Для настройки профиля используйте команды:\n"
            "/set_nickname <текст>\n"
            "/set_role <текст>\n"
            "/set_avatar <путь или url>\n"
            "/set_telegram <username>\n"
            "/set_balance <число>"
        )
    else:
        await message.answer("У вас нет прав для управления запуском.")

async def approve_handler(message: types.Message):
    await message.answer("Используйте кнопки под сообщением.")

async def decline_handler(message: types.Message):
    await message.answer("Используйте кнопки под сообщением.")

async def button_handler(callback: types.CallbackQuery):
    global is_approved, waiting_field, approval_completed
    menu_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Никнейм", callback_data="set_nickname")],
        [InlineKeyboardButton(text="✏️ Роль", callback_data="set_role")],
        [InlineKeyboardButton(text="✏️ Аватар", callback_data="set_avatar")],
        [InlineKeyboardButton(text="✏️ Telegram", callback_data="set_telegram")],
        [InlineKeyboardButton(text="✏️ Баланс", callback_data="set_balance")],
        [InlineKeyboardButton(text="🚪 Закрыть смену", callback_data="close_shift")],
    ])
    if callback.data == "approve":
        await callback.answer("Запуск разрешён")
        is_approved = True
        approval_completed = True  # Устанавливаем флаг завершения подтверждения
        print("✅ Администратор подтвердил запуск!")
        try:
            if callback.message.photo:
                await callback.message.edit_caption("Запуск разрешён ✅\n\nМеню настроек:", reply_markup=menu_kb)
            else:
                await callback.message.edit_text("Запуск разрешён ✅\n\nМеню настроек:", reply_markup=menu_kb)
        except Exception as e:
            print(f"Ошибка при обновлении сообщения: {e}")
    elif callback.data == "decline":
        await callback.answer("Запуск отклонён")
        is_approved = False
        if callback.message.photo:
            await callback.message.edit_caption("Запуск отклонён ❌", reply_markup=None)
        else:
            await callback.message.edit_text("Запуск отклонён ❌", reply_markup=None)
    elif callback.data == "settings":
        if callback.message.photo:
            await callback.message.edit_caption("Выберите, что изменить:", reply_markup=menu_kb)
        else:
            await callback.message.edit_text("Выберите, что изменить:", reply_markup=menu_kb)
    elif callback.data == "close_shift":
        await callback.answer("Смена закрыта. Приложение завершено.")
        try:
            await callback.message.delete()
        except Exception:
            pass
    elif callback.data.startswith("set_"):
        field = callback.data[4:]
        global waiting_field
        waiting_field = field
        await callback.answer()
        if callback.message.photo:
            await callback.message.edit_caption(f"Введите новое значение для {field}:", reply_markup=None)
        else:
            await callback.message.edit_text(f"Введите новое значение для {field}:", reply_markup=None)

async def run_bot():
    global bot_instance, bot_loop
    try:
        bot_instance = Bot(token=tokenbot)
        bot_loop = asyncio.get_running_loop()
    except Exception as e:
        traceback.print_exc()
        bot_instance = None
        return
    
    try:
        dp = Dispatcher()
        
        dp.message.register(start_handler, Command("start"))
        dp.message.register(approve_handler, Command("approve"))
        dp.message.register(decline_handler, Command("decline"))
        dp.callback_query.register(button_handler)
        
        # Запускаем бота с улучшенной обработкой ошибок
        try:
            # Устанавливаем таймаут для улучшения отзывчивости
            await dp.start_polling(
                bot_instance, 
                allowed_updates=dp.resolve_used_update_types(),
                polling_timeout=3.0,  # Уменьшаем таймаут для более быстрого ответа
                polling_interval=0.1  # Уменьшаем интервал опроса
            )
        except Exception as e:
            error_str = str(e).lower()
            # Обрабатываем ошибки связанные с конфликтами
            if any(err in error_str for err in ["telegramconflicterror", "terminated", "conflict", "request timeout"]):
                # Молча игнорируем известные ошибки
                print(f"Предупреждение: игнорируется ошибка Telegram API: {str(e)[:100]}")
                pass
            else:
                # Для других ошибок выводим информацию
                print(f"Ошибка при работе бота: {e}")
                traceback.print_exc()
    except Exception as e:
        print(f"Критическая ошибка в работе бота: {e}")
        traceback.print_exc()
