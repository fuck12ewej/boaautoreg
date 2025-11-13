import os
import json
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import getpass

# Глобальные переменные для хранения настроек
API_ID = None
API_HASH = None
PHONE = None
PASSWORD = None

# Имена сессий
SESSION_NAMES = [
    'userbot_session',
    'userbot_session_send_1753737189',
    'userbot_session_receive_1753737231'
]

def load_telegram_settings():
    """Загружает настройки Telegram из settings.json"""
    global API_ID, API_HASH, PHONE, PASSWORD
    
    try:
        with open('settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
            
        telegram_settings = settings.get('telegram_settings', {})
        
        API_ID = telegram_settings.get('api_id')
        API_HASH = telegram_settings.get('api_hash')
        PHONE = telegram_settings.get('phone')
        PASSWORD = telegram_settings.get('password')
        
        return True
    except Exception as e:
        print(f"Ошибка при загрузке настроек Telegram: {e}")
        return False

async def check_session(session_name):
    """Проверяет валидность сессии и при необходимости выполняет авторизацию"""
    global API_ID, API_HASH, PHONE, PASSWORD
    
    if not API_ID or not API_HASH or not PHONE:
        if not load_telegram_settings():
            print("Не удалось загрузить настройки Telegram")
            return False
    
    try:
        # Создаем клиент с указанным именем сессии
        client = TelegramClient(session_name, API_ID, API_HASH)
        
        # Пробуем подключиться
        await client.connect()
        
        # Проверяем, авторизован ли клиент
        if not await client.is_user_authorized():
            print(f"Сессия {session_name} не авторизована. Выполняем авторизацию...")
            
            # Отправляем код авторизации
            await client.send_code_request(PHONE)
            
            # Запрашиваем код у пользователя
            code = input(f"Введите код для авторизации сессии {session_name}: ")
            
            try:
                # Пытаемся войти с полученным кодом
                await client.sign_in(PHONE, code)
            except SessionPasswordNeededError:
                # Если включена двухфакторная аутентификация
                if PASSWORD:
                    await client.sign_in(password=PASSWORD)
                else:
                    # Если пароль не указан в настройках, запрашиваем у пользователя
                    password = getpass.getpass("Введите пароль двухфакторной аутентификации: ")
                    await client.sign_in(password=password)
            except PhoneCodeInvalidError:
                print("Неверный код. Авторизация не выполнена.")
                await client.disconnect()
                return False
                
            print(f"Авторизация сессии {session_name} успешно выполнена!")
        else:
            print(f"Сессия {session_name} уже авторизована.")
            
        # Отключаемся
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"Ошибка при проверке сессии {session_name}: {e}")
        return False

async def check_all_sessions():
    """Проверяет все сессии и выполняет авторизацию при необходимости"""
    results = {}
    
    for session_name in SESSION_NAMES:
        print(f"Проверка сессии {session_name}...")
        result = await check_session(session_name)
        results[session_name] = result
        
    return results

def validate_sessions():
    """Запускает проверку всех сессий"""
    print("Проверка сессий Telegram...")
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(check_all_sessions())
    
    all_valid = all(results.values())
    if all_valid:
        print("Все сессии успешно проверены и авторизованы!")
    else:
        print("Некоторые сессии не удалось авторизовать:")
        for session, result in results.items():
            if not result:
                print(f"  - {session}: Ошибка авторизации")
                
    return all_valid

if __name__ == "__main__":
    validate_sessions()