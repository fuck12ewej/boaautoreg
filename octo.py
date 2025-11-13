import json
import traceback
import time
import asyncio
import aiohttp
import httpx
import pyppeteer
import random
import string
import re
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

# Добавляем пути для надежного импорта модулей
site_packages_path = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
if site_packages_path not in sys.path:
    sys.path.append(site_packages_path)

# Импортируем настройки для Telegram из main.py
try:
    # Попытка импортировать настройки из main.py
    import importlib.util
    main_spec = importlib.util.spec_from_file_location("main", os.path.join(os.path.dirname(__file__), "main.py"))
    main_module = importlib.util.module_from_spec(main_spec)
    main_spec.loader.exec_module(main_module)
    
    TG_BRO_GASPAR = getattr(main_module, 'TG_BRO_GASPAR', "@bro_gaspar")
    TG_BRO_GASPAR_USERNAME = getattr(main_module, 'TG_BRO_GASPAR_USERNAME', "bro_gaspar")
    
    print(f"✅ Импортированы настройки Telegram: {TG_BRO_GASPAR}, {TG_BRO_GASPAR_USERNAME}")
except Exception as e:
    # Значения по умолчанию в случае ошибки
    print(f"⚠️ Ошибка импорта из main.py: {e}")
    TG_BRO_GASPAR = "@bro_gaspar"
    TG_BRO_GASPAR_USERNAME = "bro_gaspar"
    print(f"✅ Используются значения по умолчанию: {TG_BRO_GASPAR}, {TG_BRO_GASPAR_USERNAME}")

# Флаг доступности Stealth режима
STEALTH_AVAILABLE = False

# Пробуем различные способы импорта playwright_stealth
try:
    # Способ 1: Прямой импорт
    import playwright_stealth
    from playwright_stealth import stealth
    STEALTH_AVAILABLE = True
    print("✅ playwright_stealth успешно импортирован")
except ImportError:
    try:
        # Способ 2: Пробуем установить через pip
        import subprocess
        print("⚠️ playwright_stealth не установлен. Пытаюсь установить...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "playwright-stealth"])
        
        # Пробуем импортировать после установки
        import playwright_stealth
        from playwright_stealth import stealth
        print("✅ playwright_stealth успешно установлен и импортирован")
        STEALTH_AVAILABLE = True
    except Exception:
        try:
            # Способ 3: Пробуем найти модуль по абсолютному пути
            import importlib.util
            stealth_path = os.path.join(site_packages_path, 'playwright_stealth', 'stealth.py')
            if os.path.exists(stealth_path):
                spec = importlib.util.spec_from_file_location("stealth_module", stealth_path)
                stealth_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(stealth_module)
                stealth = stealth_module
                print("✅ playwright_stealth импортирован через альтернативный путь")
                STEALTH_AVAILABLE = True
            else:
                print(f"⚠️ Файл {stealth_path} не найден")
                STEALTH_AVAILABLE = False
        except Exception as e:
            print(f"⚠️ Все попытки импорта playwright_stealth не удались: {e}")
            STEALTH_AVAILABLE = False
            
# -- Настройки для OctoBrowser
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = "58888"
BASE_URL = f"http://{LOCAL_HOST}:{LOCAL_PORT}"
API_URL = f"{BASE_URL}/api"
PROFILES_API_URL = f"{API_URL}/profiles"
PROFILES_ACTIVE_URL = f"{PROFILES_API_URL}/active"
PROFILES_START_URL = f"{PROFILES_API_URL}/start"  # URL для запуска профилей
PROFILES_UPDATE_URL = f"{PROFILES_API_URL}/update"

# Настройки для облачного API OctoBrowser
OCTO_WEB_API_URL = "https://app.octobrowser.net/api/v2/automation/profiles"
OCTO_API_TOKEN = ""  # API токен OctoBrowser

# Цвета для вывода в консоль
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️ {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️ {message}{Colors.ENDC}")

def print_header(message):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")

# Функция для проверки доступа к API OctoBrowser
async def check_api_access():
    print_header("Проверка доступа к API OctoBrowser")
    
    try:
        # Проверка доступа к локальному API
        print_info(f"Проверяю доступ к {PROFILES_ACTIVE_URL}...")
        local_access = False
        
        async with aiohttp.ClientSession() as session:
            async with session.get(PROFILES_ACTIVE_URL) as response:
                if response.status == 200:
                    print_success("Доступ к локальному API OctoBrowser: OK")
                    local_access = True
                else:
                    print_error(f"Ошибка доступа к локальному API: {response.status} {response.reason}")
        
        # Проверка доступа к облачному API
        print_info(f"Проверяю доступ к облачному API OctoBrowser...")
        cloud_access = False
        
        try:
            # Проверяем доступ к облачному API с помощью запроса GET
            headers = {
                "X-Octo-Api-Token": OCTO_API_TOKEN,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(OCTO_WEB_API_URL, headers=headers) as response:
                    if response.status in [200, 201, 204, 403]:  # 403 обычно означает, что сервер доступен, но требует авторизацию
                        print_success("Доступ к облачному API OctoBrowser: OK")
                        cloud_access = True
                    else:
                        print_error(f"Ошибка доступа к облачному API: {response.status} {response.reason}")
        except Exception as e:
            print_error(f"Ошибка при проверке доступа к облачному API: {e}")
        
        return cloud_access, local_access
    except Exception as e:
        print_error(f"Ошибка при проверке доступа к API: {e}")
        traceback.print_exc()
        return False, False

# Функция для получения списка активных профилей OctoBrowser
async def get_profiles():
    print_header("Получение списка активных профилей")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PROFILES_ACTIVE_URL) as response:
                if response.status != 200:
                    print_error(f"Ошибка при получении профилей: {response.status} {response.reason}")
                    return []
                
                profiles = await response.json()
                
                if isinstance(profiles, list):
                    print_success(f"Найдено {len(profiles)} активных профилей")
                    
                    # Выводим информацию о профилях
                    for i, profile in enumerate(profiles):
                        print_info(f"  {i+1}. {profile.get('title', 'Без имени')} (ID: {profile.get('uuid', 'Нет ID')})")
                    return profiles
                else:
                    print_warning(f"Неожиданный формат данных от API: {profiles}")
                    return []
    except Exception as e:
        print_error(f"Ошибка при получении списка профилей: {e}")
        traceback.print_exc()
        return []

# Функция для создания профиля через облачный API
async def create_profile(profile_name, os_name="win"):
    print_header(f"Создание профиля '{profile_name}' через облачный API")
    
    try:
        # Проверяем доступ к API
        cloud_access, local_access = await check_api_access()
        
        if not cloud_access:
            print_error("Облачный API OctoBrowser недоступен")
            print_error("Невозможно создать профиль без доступа к облачному API")
            return None
        
        if not local_access:
            print_warning("Локальный API OctoBrowser недоступен")
            print_warning("Профиль будет создан, но не будет доступен для запуска")
        
        # Настройка запроса к облачному API
        url = OCTO_WEB_API_URL
        headers = {
            "Content-Type": "application/json",
            "X-Octo-Api-Token": OCTO_API_TOKEN
        }
        
        # Формирование тела запроса с базовыми настройками
        data = {
            "title": profile_name,
            "fingerprint": {
                "os": os_name
            }
        }
        
        print_info("Отправляю запрос на создание профиля через облачный API...")
        print_info(f"URL: {url}")
        print_info(f"Payload: {data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                print(f"Статус ответа: {response.status}")
                text = await response.text()
                print(f"Ответ: {text}")
                
                if response.status in [200, 201]:
                    try:
                        result = await response.json()
                        if isinstance(result, dict) and 'data' in result and 'uuid' in result['data']:
                            print_success(f"Профиль создан! UUID: {result['data']['uuid']}")
                            return result['data']['uuid']
                        else:
                            print_error("Профиль не создан или UUID не найден в ответе")
                            return None
                    except Exception as e:
                        print_error(f"Ошибка при разборе JSON: {e}")
                        return None
                else:
                    print_error(f"Не удалось создать профиль: {response.status}")
                    return None
    except Exception as e:
        print_error(f"Ошибка при создании профиля: {e}")
        traceback.print_exc()
        return None

# Функция для парсинга строки прокси в словарь
def parse_proxy_string(proxy_string):
    parsed = urlparse(proxy_string)
    return {
        "type": parsed.scheme,
        "host": parsed.hostname,
        "port": int(parsed.port),
        "username": parsed.username or "",
        "password": parsed.password or ""
    }

# Функция для обновления прокси в профиле
async def update_proxy(profile_id, proxy_string):
    print_header(f"Обновление прокси для профиля {profile_id}")
    
    try:
        # Парсим строку прокси
        proxy_config = parse_proxy_string(proxy_string)
        
        print_info(f"Прокси для обновления: {proxy_string}")
        print_info(f"Тип: {proxy_config['type']}, Хост: {proxy_config['host']}, Порт: {proxy_config['port']}")
        
        # Проверяем доступ к API
        cloud_access, local_access = await check_api_access()
        
        if not cloud_access:
            print_error("Облачный API OctoBrowser недоступен")
            print_error("Невозможно обновить прокси без доступа к облачному API")
            return False
        
        # Настройка запроса к облачному API
        url = f"{OCTO_WEB_API_URL}/{profile_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Octo-Api-Token": OCTO_API_TOKEN
        }
        
        # Формирование тела запроса
        data = {
            "proxy": {
                "type": proxy_config['type'],
                "host": proxy_config['host'],
                "port": proxy_config['port'],
                "username": proxy_config['username'],
                "password": proxy_config['password']
            }
        }
        
        print_info("Отправляю запрос на обновление прокси через облачный API...")
        print_info(f"URL: {url}")
        print_info(f"Payload: {data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=data, headers=headers) as response:
                print(f"Статус ответа: {response.status}")
                text = await response.text()
                print(f"Ответ: {text}")
                
                if response.status in [200, 201, 204]:
                    print_success("Прокси обновлён успешно")
                    return True
                else:
                    print_error(f"Ошибка при обновлении прокси: {response.status}")
                    print_error(f"Ответ: {text}")
                    return False
    except Exception as e:
        print_error(f"Ошибка при обновлении прокси: {e}")
        traceback.print_exc()
        return False

# Функция для получения информации о профиле
async def get_profile_info(profile_id):
    print_header(f"Получение информации о профиле {profile_id}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{PROFILES_API_URL}/{profile_id}") as response:
                if response.status != 200:
                    print_error(f"Ошибка при получении информации о профиле: {response.status} {response.reason}")
                    return None
                
                profile = await response.json()
                print_success(f"Найден профиль: {profile.get('name', 'Без имени')}")
                return profile
    except Exception as e:
        print_error(f"Ошибка при получении информации о профиле: {e}")
        traceback.print_exc()
        return None

# Функция для запуска профиля OctoBrowser и получения WebSocket endpoint (по примеру test.py)
async def get_cdp(profile_id):
    """
    Запускает профиль OctoBrowser и возвращает WebSocket endpoint
    
    :param profile_id: UUID профиля для запуска
    :return: WebSocket endpoint для подключения к браузеру
    """
    print_header(f"Запуск профиля {profile_id} и получение WebSocket endpoint")
    
    try:
        async with httpx.AsyncClient() as client:
            # Запускаем профиль через локальный API
            payload = {
                "uuid": profile_id,
                "debug_port": True
            }
            
            print_info(f"Отправляю POST запрос к {PROFILES_START_URL}")
            response = await client.post(PROFILES_START_URL, json=payload)
            
            if response.status_code not in [200, 201]:
                print_error(f"Ошибка при запуске профиля: {response.status_code} {response.reason_phrase}")
                print_error(f"Ответ: {response.text}")
                return None
            
            start_data = response.json()
            print_success("Профиль запущен успешно")
            print_info(f"Ответ: {start_data}")
            
            # Получаем WebSocket endpoint для подключения к браузеру
            ws_endpoint = start_data.get('ws_endpoint')
            if not ws_endpoint:
                port = start_data.get('port')
                if not port:
                    print_error("Не удалось получить ws_endpoint или port из ответа")
                    return None
                ws_endpoint = f"ws://{LOCAL_HOST}:{port}"
            
            print_success(f"Получен WebSocket endpoint: {ws_endpoint}")
            return ws_endpoint
    
    except Exception as e:
        print_error(f"Ошибка при запуске профиля: {e}")
        traceback.print_exc()
        return None

# Обновленная функция для запуска профиля OctoBrowser (упрощенная версия)
async def start_profile(profile_id):
    """
    Запускает профиль OctoBrowser
    
    :param profile_id: UUID профиля для запуска
    :return: WebSocket endpoint для подключения или False при ошибке
    """
    print_header(f"Запуск профиля {profile_id}")
    
    try:
        # Проверяем доступ к API
        cloud_access, local_access = await check_api_access()
        if not local_access:
            print_error("Локальный API OctoBrowser недоступен")
            print_info(f"Убедитесь, что OctoBrowser запущен и доступен по адресу: {BASE_URL}")
            return False
        
        # Используем новую функцию для запуска профиля
        ws_endpoint = await get_cdp(profile_id)
        if not ws_endpoint:
            return False
        
        return ws_endpoint
    except Exception as e:
        print_error(f"Ошибка при запуске профиля: {e}")
        traceback.print_exc()
        return False

# Функция для остановки профиля
async def stop_profile(profile_id):
    print_info(f"Останавливаю профиль {profile_id}...")
    try:
        async with aiohttp.ClientSession() as session:
            stop_url = f"{PROFILES_API_URL}/stop"
            payload = {
                "uuid": profile_id
            }
            
            async with session.post(stop_url, json=payload) as response:
                if response.status == 200:
                    print_success(f"Профиль {profile_id} успешно остановлен")
                    return True
                else:
                    print_warning(f"Не удалось остановить профиль: {response.status}")
                    return False
    except Exception as e:
        print_warning(f"Ошибка при остановке профиля: {e}")
        return False

# Функция для открытия URL в браузере
async def open_url(port, url):
    print_header(f"Открытие URL: {url}")
    
    try:
        # Метод 1: Используем Chrome DevTools Protocol через /json/goto
        try:
            print_info("Метод 1: Используем Chrome DevTools Protocol...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{LOCAL_HOST}:{port}/json/goto",
                    json={"url": url},
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        print_success(f"Успешно открыта страница через CDP")
                        return True
        except Exception as e:
            print_warning(f"Не удалось открыть страницу через CDP: {e}")
        
        # Метод 2: Используем прямой запрос к браузеру
        try:
            print_info("Метод 2: Используем прямой запрос к браузеру...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{LOCAL_HOST}:{port}/json/new?{url}") as response:
                    if response.status == 200:
                        print_success(f"Успешно открыта страница через прямой запрос")
                        return True
        except Exception as e:
            print_warning(f"Не удалось открыть страницу через прямой запрос: {e}")
        
        # Метод 3: Используем OctoBrowser API
        try:
            print_info("Метод 3: Используем OctoBrowser API...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_URL}/profiles/{port}/goto",
                    json={"url": url},
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        print_success(f"Успешно открыта страница через OctoBrowser API")
                        return True
        except Exception as e:
            print_warning(f"Не удалось открыть страницу через OctoBrowser API: {e}")
        
        print_error("Все методы открытия URL не сработали")
        print_info(f"Пожалуйста, откройте URL вручную: {url}")
        return False
    except Exception as e:
        print_error(f"Ошибка при открытии URL: {e}")
        traceback.print_exc()
        print_info(f"Пожалуйста, откройте URL вручную: {url}")
        return False

# Функция для запуска профиля и открытия Yahoo
async def start_profile_with_yahoo(profile_id):
    port = await start_profile(profile_id)
    if port:
        # Даем браузеру время на полную загрузку
        print_info("Ожидание полной загрузки браузера...")
        for i in range(5):
            print(f"Ожидание {i+1}/5 секунд...", end="\r")
            await asyncio.sleep(1)
        print("\nБраузер должен быть загружен. Открываю Yahoo...")
        
        # Открываем страницу создания аккаунта Yahoo
        yahoo_url = "https://login.yahoo.com/account/create"
        success = await open_url(port, yahoo_url)
        
        if success:
            print_success("Профиль запущен и страница Yahoo открыта успешно!")
        else:
            print_warning("Профиль запущен, но страницу Yahoo нужно открыть вручную.")
            print_info(f"URL для открытия: {yahoo_url}")
            
        return True
    else:
        print_error("Не удалось запустить профиль или получить порт")
        print_info("Пожалуйста, запустите профиль вручную через интерфейс OctoBrowser")
        print_info("И откройте URL: https://login.yahoo.com/account/create")
        return False

# Функция для запуска профиля с использованием Playwright
async def start_profile_with_playwright(profile_id, url="https://login.yahoo.com/account/create"):
    print_header(f"Запуск профиля {profile_id} с использованием Playwright")
    
    try:
        # Проверяем доступ к API
        cloud_access, local_access = await check_api_access()
        if not local_access:
            print_error("Локальный API OctoBrowser недоступен")
            print_info(f"Убедитесь, что OctoBrowser запущен и доступен по адресу: {BASE_URL}")
            return False
        
        # Запускаем профиль через API
        payload = {
            "uuid": profile_id,
            "headless": False,
            "debug_port": True,
            "timeout": 120,
            "only_local": True
        }
        
        print_info("Запускаю профиль через API...")
        
        async with aiohttp.ClientSession() as session:
            start_url = PROFILES_START_URL
            print_info(f"POST запрос к {start_url}")
            
            async with session.post(start_url, json=payload) as response:
                if response.status not in [200, 201]:
                    print_error(f"Ошибка при запуске профиля: {response.status} {response.reason}")
                    error_text = await response.text()
                    print_error(f"Ответ: {error_text}")
                    return False
                
                start_data = await response.json()
                print_success("Профиль запущен успешно")
                print_info(f"Ответ: {start_data}")
                
                # Получаем WebSocket endpoint для подключения Playwright
                ws_endpoint = start_data.get('ws_endpoint')
                if not ws_endpoint:
                    port = start_data.get('port')
                    if not port:
                        print_error("Не удалось получить ws_endpoint или port из ответа")
                        return False
                    ws_endpoint = f"ws://{LOCAL_HOST}:{port}"
                
                print_info(f"WebSocket endpoint: {ws_endpoint}")
                
                # Подключаемся к браузеру через Playwright
                print_info("Подключаюсь к браузеру через Playwright...")
                playwright = await async_playwright().start()
                browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
                
                # Получаем первую вкладку или создаем новую
                if browser.contexts and browser.contexts[0].pages:
                    page = browser.contexts[0].pages[0]
                    print_info("Использую существующую вкладку")
                else:
                    print_info("Создаю новую вкладку")
                    context = await browser.new_context()
                    page = await context.new_page()
                
                # Переходим на указанный URL с увеличенным таймаутом
                print_info(f"Открываю URL: {url}")
                try:
                    await page.goto(url, wait_until='networkidle', timeout=60000)
                    print_success(f"Страница {url} открыта успешно")
                except Exception as e:
                    print_warning(f"Страница загружается медленно: {e}")
                    # Пробуем дождаться загрузки основных элементов
                    try:
                        await page.wait_for_load_state('domcontentloaded', timeout=30000)
                        print_success("Страница загружена (DOM готов)")
                    except:
                        print_warning("Продолжаю без ожидания полной загрузки")
                
                # Получаем заголовок страницы
                try:
                    title = await page.title()
                    print_info(f"Заголовок страницы: {title}")
                except:
                    print_warning("Не удалось получить заголовок страницы")
                
                # Не закрываем браузер, чтобы пользователь мог продолжить работу
                print_success("Браузер запущен и готов к использованию")
                print_info("Для закрытия браузера закройте окно OctoBrowser или нажмите Enter")
                
                # Возвращаем объекты для дальнейшего использования
                return {
                    "playwright": playwright,
                    "browser": browser,
                    "page": page,
                    "port": start_data.get('port')
                }
    except Exception as e:
        print_error(f"Ошибка при запуске профиля: {e}")
        traceback.print_exc()
        return False

# Функция для автоматизации действий на странице
async def automate_page(page_data, action_type=None):
    print_header("Автоматизация действий на странице")
    
    if not page_data or not isinstance(page_data, dict) or "page" not in page_data:
        print_error("Некорректные данные страницы")
        return False
    
    page = page_data["page"]
    
    try:
        if action_type == "yahoo_register":
            # Заполняем форму регистрации Yahoo
            print_info("Заполняю форму регистрации Yahoo...")
            
            # Ждем загрузки формы
            await page.wait_for_selector('input[name="firstName"]', timeout=5000)
            
            # Заполняем поля
            await page.fill('input[name="firstName"]', "Test")
            await page.fill('input[name="lastName"]', "User")
            await page.fill('input[name="yid"]', f"test_user_{int(time.time())}")
            await page.fill('input[name="password"]', "TestPassword123!")
            
            print_success("Форма заполнена")
            return True
        elif action_type == "screenshot":
            # Делаем скриншот
            screenshot_path = "screenshot.png"
            await page.screenshot(path=screenshot_path)
            print_success(f"Скриншот сохранен в {screenshot_path}")
            return True
        elif action_type == "get_html":
            # Получаем HTML страницы
            html = await page.content()
            print_info(f"HTML страницы (первые 500 символов):")
            print(html[:500] + "...")
            return html
        else:
            print_info("Доступные действия:")
            print_info("1. yahoo_register - заполнить форму регистрации Yahoo")
            print_info("2. screenshot - сделать скриншот")
            print_info("3. get_html - получить HTML страницы")
            return False
    except Exception as e:
        print_error(f"Ошибка при автоматизации: {e}")
        traceback.print_exc()
        return False

# Функция для настройки прокси в профиле
async def configure_profile_proxy(profile_id, proxy_data):
    """
    Настраивает прокси в профиле OctoBrowser
    
    :param profile_id: UUID профиля
    :param proxy_data: словарь с данными прокси (host, port, username, password)
    :return: True в случае успеха, False при ошибке
    """
    try:
        print_header(f"Настройка прокси для профиля {profile_id}")
        
        # Убедимся, что все необходимые данные присутствуют
        required_fields = ['host', 'port', 'username', 'password']
        for field in required_fields:
            if field not in proxy_data or not proxy_data[field]:
                print_error(f"Отсутствует обязательное поле '{field}' в данных прокси")
                return False
        
        # Форматируем строку прокси
        proxy_string = f"http://{proxy_data['username']}:{proxy_data['password']}@{proxy_data['host']}:{proxy_data['port']}"
        
        # Используем новую функцию для обновления прокси
        return await update_proxy(profile_id, proxy_string)
    
    except Exception as e:
        print_error(f"Ошибка при настройке прокси: {e}")
        traceback.print_exc()
        print_warning("Не удалось настроить прокси. Пожалуйста, настройте прокси вручную.")
        print_info(f"Данные для настройки прокси:")
        print_info(f"Тип: HTTP, Хост: {proxy_data.get('host', 'н/д')}, Порт: {proxy_data.get('port', 'н/д')}")
        print_info(f"Имя пользователя: {proxy_data.get('username', 'н/д')}, Пароль: {proxy_data.get('password', 'н/д')}")
        return False

# Функция для установки API токена Octo
def set_octo_api_token(token):
    """
    Устанавливает API токен для Octo Web API
    
    :param token: API токен для Octo Web API
    """
    global OCTO_API_TOKEN
    OCTO_API_TOKEN = token
    print_success(f"API токен Octo успешно установлен: {token[:5]}...{token[-5:]}")
    return True

# Функция для подключения к браузеру через pyppeteer (по примеру test.py)
async def connect_browser(profile_id, url=None):
    """
    Запускает профиль OctoBrowser и подключается к нему через pyppeteer
    
    :param profile_id: UUID профиля
    :param url: URL для перехода после подключения (опционально)
    :return: словарь с browser и page объектами или False при ошибке
    """
    print_header(f"Подключение к профилю {profile_id} через pyppeteer")
    
    try:
        # Получаем WebSocket endpoint для подключения
        ws_endpoint = await get_cdp(profile_id)
        if not ws_endpoint:
            print_error("Не удалось получить WebSocket endpoint для подключения")
            return False
        
        print_info(f"Подключаюсь к WebSocket endpoint: {ws_endpoint}")
        browser = await pyppeteer.launcher.connect(browserWSEndpoint=ws_endpoint)
        
        # Создаем новую страницу или используем существующую
        pages = await browser.pages()
        if pages:
            page = pages[0]
            print_info("Использую существующую страницу")
        else:
            page = await browser.newPage()
            print_info("Создана новая страница")
        
        # Если указан URL, переходим на него
        if url:
            print_info(f"Перехожу на URL: {url}")
            await page.goto(url)
            print_success(f"Страница {url} открыта успешно")
            
            # Получаем заголовок страницы
            title = await page.title()
            print_info(f"Заголовок страницы: {title}")
        
        print_success("Подключение к браузеру выполнено успешно")
        return {
            "browser": browser,
            "page": page,
            "ws_endpoint": ws_endpoint
        }
        
    except Exception as e:
        print_error(f"Ошибка при подключении к браузеру: {e}")
        traceback.print_exc()
        return False

async def start_profile_with_stealth_playwright(profile_id, url="https://login.yahoo.com/account/create"):
    """
    Запускает профиль OctoBrowser и подключается к нему через Playwright с применением stealth-режима
    
    :param profile_id: UUID профиля
    :param url: URL для перехода после подключения (опционально)
    :return: словарь с browser, page и playwright объектами или False при ошибке
    """
    print_header(f"Запуск профиля {profile_id} с использованием Playwright-stealth")
    
    try:
        # Проверяем доступ к API
        cloud_access, local_access = await check_api_access()
        if not local_access:
            print_error("Локальный API OctoBrowser недоступен")
            print_info(f"Убедитесь, что OctoBrowser запущен и доступен по адресу: {BASE_URL}")
            return False
        
        # Запускаем профиль через API
        payload = {
            "uuid": profile_id,
            "debug_port": True,
            "timeout": 120,
            "only_local": True
        }
        
        print_info("Запускаю профиль через API...")
        
        async with aiohttp.ClientSession() as session:
            start_url = PROFILES_START_URL
            print_info(f"POST запрос к {start_url}")
            
            async with session.post(start_url, json=payload) as response:
                if response.status not in [200, 201]:
                    print_error(f"Ошибка при запуске профиля: {response.status} {response.reason}")
                    error_text = await response.text()
                    print_error(f"Ответ: {error_text}")
                    return False
                
                start_data = await response.json()
                print_success("Профиль запущен успешно")
                print_info(f"Ответ: {start_data}")
                
                # Получаем WebSocket endpoint для подключения Playwright
                ws_endpoint = start_data.get('ws_endpoint')
                if not ws_endpoint:
                    port = start_data.get('port')
                    if not port:
                        print_error("Не удалось получить ws_endpoint или port из ответа")
                        return False
                    ws_endpoint = f"ws://{LOCAL_HOST}:{port}"
                
                print_info(f"WebSocket endpoint: {ws_endpoint}")
                
                # Подключаемся к браузеру через Playwright
                print_info("Подключаюсь к браузеру через Playwright с применением stealth-режима...")
                playwright = await async_playwright().start()
                browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
                
                # Получаем первую вкладку или создаем новую
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                if context.pages:
                    page = context.pages[0]
                    print_info("Использую существующую вкладку")
                else:
                    page = await context.new_page()
                    print_info("Создана новая вкладка")
                
                # Применяем улучшенный stealth-режим
                print_info("Применяю улучшенный антидетект режим...")
                
                # Применяем продвинутые настройки антидетекта
                await apply_advanced_stealth(page)
                
                # Применяем агрессивные методы обхода капчи Yahoo
                await apply_yahoo_captcha_bypass(page)
                
                # Применяем ультра-агрессивные методы обхода детекции
                await apply_ultra_aggressive_stealth(page)
                
                # Добавляем случайные движения мыши
                await add_random_mouse_movements(page)
                
                # Применяем стандартный stealth если доступен
                if STEALTH_AVAILABLE:
                    try:
                        stealth_instance = stealth.Stealth()
                        await stealth_instance.apply_stealth_async(page)
                        print_success("✓ Дополнительный stealth-режим активирован")
                    except Exception as e:
                        print_warning(f"⚠️ Дополнительный stealth не удался: {e}")
                
                print_success("✓ Улучшенный антидетект режим активирован")
                
                # Переходим на указанный URL с увеличенным таймаутом
                print_info(f"Открываю URL: {url}")
                try:
                    await page.goto(url, wait_until='networkidle', timeout=60000)
                    print_success(f"Страница {url} открыта успешно")
                    
                    # Проверяем, не попали ли мы на страницу reCAPTCHA (только после отправки формы)
                    recaptcha_result = await detect_recaptcha_and_handle(page, only_after_submit=True)
                    if recaptcha_result is False:
                        print_error("❌ Регистрация Yahoo не удалась, прекращаю работу")
                        return False
                    elif recaptcha_result is True:
                        print_success("✓ Регистрация Yahoo успешна, продолжаю автоматизацию")
                    # Убираем принудительный мониторинг на этапе загрузки страницы
                except Exception as e:
                    print_warning(f"Страница загружается медленно: {e}")
                    # Пробуем дождаться загрузки основных элементов
                    try:
                        await page.wait_for_load_state('domcontentloaded', timeout=30000)
                        print_success("Страница загружена (DOM готов)")
                    except:
                        print_warning("Продолжаю без ожидания полной загрузки")
                
                # Получаем заголовок страницы
                try:
                    title = await page.title()
                    print_info(f"Заголовок страницы: {title}")
                except:
                    print_warning("Не удалось получить заголовок страницы")
                
                # Не закрываем браузер, чтобы пользователь мог продолжить работу
                print_success("Браузер запущен и готов к использованию")
                
                # Возвращаем объекты для дальнейшего использования
                return {
                    "playwright": playwright,
                    "browser": browser,
                    "page": page,
                    "port": start_data.get('port')
                }
    except Exception as e:
        print_error(f"Ошибка при запуске профиля: {e}")
        traceback.print_exc()
        return False

def start_profile_with_stealth_playwright_sync(profile_id, url="https://login.yahoo.com/account/create"):
    """
    Запускает профиль OctoBrowser и подключается к нему через Playwright с применением stealth-режима (синхронная версия)
    
    :param profile_id: UUID профиля
    :param url: URL для перехода после подключения (опционально)
    :return: словарь с browser, page и playwright объектами или False при ошибке
    """
    print_header(f"Запуск профиля {profile_id} с использованием Playwright-stealth (синхронно)")
    
    try:
        # Проверяем доступ к API
        # Поскольку check_api_access асинхронный, используем простой синхронный запрос
        print_info(f"Проверяю доступ к API OctoBrowser...")
        
        # Запускаем профиль через API
        import requests
        
        payload = {
            "uuid": profile_id,
            "debug_port": True,
            "timeout": 120,
            "only_local": True
        }
        
        print_info("Запускаю профиль через API...")
        
        start_url = PROFILES_START_URL
        print_info(f"POST запрос к {start_url}")
        
        response = requests.post(start_url, json=payload)
        if response.status_code not in [200, 201]:
            print_error(f"Ошибка при запуске профиля: {response.status_code} {response.reason}")
            print_error(f"Ответ: {response.text}")
            return False
        
        start_data = response.json()
        print_success("Профиль запущен успешно")
        print_info(f"Ответ: {start_data}")
        
        # Получаем WebSocket endpoint для подключения Playwright
        ws_endpoint = start_data.get('ws_endpoint')
        if not ws_endpoint:
            port = start_data.get('port')
            if not port:
                print_error("Не удалось получить ws_endpoint или port из ответа")
                return False
            ws_endpoint = f"ws://{LOCAL_HOST}:{port}"
        
        print_info(f"WebSocket endpoint: {ws_endpoint}")
        
        # Подключаемся к браузеру через Playwright
        print_info("Подключаюсь к браузеру через Playwright с применением stealth-режима...")
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(ws_endpoint)
        
        # Получаем первую вкладку или создаем новую
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        if context.pages:
            page = context.pages[0]
            print_info("Использую существующую вкладку")
        else:
            page = context.new_page()
            print_info("Создана новая вкладка")
        
        # Применяем stealth-режим
        if STEALTH_AVAILABLE:
            print_info("Применяю stealth-режим для маскировки автоматизации...")
            try:
                # Создаем экземпляр класса Stealth и применяем его для страницы
                stealth_instance = stealth.Stealth()
                stealth_instance.apply_stealth_sync(page)
                print_success("Stealth-режим активирован")
            except Exception as e:
                print_warning(f"⚠️ Не удалось применить stealth-режим: {e}")
                # Пробуем альтернативный способ
                try:
                    page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined,
                        });
                    """)
                    print_success("Stealth-режим активирован (альтернативный способ)")
                except Exception as e2:
                    print_warning(f"⚠️ Альтернативный stealth также не удался: {e2}")
        else:
            print_warning("Stealth-режим недоступен - playwright_stealth не установлен")
        
        # Переходим на указанный URL с увеличенным таймаутом
        print_info(f"Открываю URL: {url}")
        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            print_success(f"Страница {url} открыта успешно")
        except Exception as e:
            print_warning(f"Страница загружается медленно: {e}")
            # Пробуем дождаться загрузки основных элементов
            try:
                page.wait_for_load_state('domcontentloaded', timeout=30000)
                print_success("Страница загружена (DOM готов)")
            except:
                print_warning("Продолжаю без ожидания полной загрузки")
        
        # Получаем заголовок страницы
        try:
            title = page.title()
            print_info(f"Заголовок страницы: {title}")
        except:
            print_warning("Не удалось получить заголовок страницы")
        
        # Не закрываем браузер, чтобы пользователь мог продолжить работу
        print_success("Браузер запущен и готов к использованию")
        
        # Возвращаем объекты для дальнейшего использования
        return {
            "playwright": playwright,
            "browser": browser,
            "page": page,
            "port": start_data.get('port')
        }
    except Exception as e:
        print_error(f"Ошибка при запуске профиля: {e}")
        traceback.print_exc()
        return False

async def automate_yahoo_registration(page, user_data):
    """
    Автоматизирует заполнение формы регистрации Yahoo на основе предоставленных данных
    
    :param page: Объект страницы из Playwright или Pyppeteer
    :param user_data: Строка с данными пользователя (имя, адрес, дата рождения, телефон)
    :return: словарь с созданными данными (email, password)
    """
    # Импортируем необходимые модули внутри функции для уверенности в их доступности
    import re
    import random
    import string
    import os
    import json
    import traceback
    from datetime import datetime
    
    print_header("Автоматизация заполнения формы регистрации Yahoo")
    
    try:
        # Применяем агрессивные методы обхода капчи перед загрузкой страницы
        print_info("🛡️ Применяю агрессивные методы обхода капчи Yahoo...")
        await apply_yahoo_captcha_bypass(page)
        
        # Применяем ультра-агрессивные методы обхода детекции
        print_info("🛡️ Применяю ультра-агрессивные методы обхода детекции...")
        await apply_ultra_aggressive_stealth(page)
        
        # НЕ запускаем мониторинг reCAPTCHA во время заполнения формы
        # Мониторинг будет только после нажатия кнопки отправки
        print_info("✓ Заполнение формы без мониторинга reCAPTCHA")
        monitor_task = None
        
        # Ждем загрузки страницы Yahoo (до 30 секунд)
        print_info("Ожидаю загрузки страницы Yahoo...")
        try:
            await page.wait_for_selector('#usernamereg-firstName', timeout=30000)
            print_success("Страница Yahoo загружена")
        except Exception as e:
            print_warning(f"Страница загружается медленно, продолжаю... ({e})")
            await asyncio.sleep(5)
        
        # Парсим данные пользователя
        lines = user_data.strip().split('\n')
        if len(lines) < 4:
            print_error("❌ Недостаточно данных пользователя")
            print_info("⚠️ Для работы Yahoo нужны минимум 5 строк данных:")
            print_info("1. Полное имя (Имя Фамилия)")
            print_info("2. Адрес (улица, дом)")
            print_info("3. Город, Штат, ZIP (например: New York, NY 10001)")
            print_info("4. Дата рождения (например: January 1, 1990)")
            print_info("5. Телефон (например: (555) 123-4567)")
            print_info("❗ SSN и DOB будут получены ПОСЛЕ успешной регистрации Yahoo")
            return None
            
        # Извлекаем имя и фамилию из первой строки
        full_name = lines[0].strip()
        name_parts = full_name.split()
        if len(name_parts) < 2:
            print_warning("⚠️ В полном имени должны быть имя и фамилия, добавляю фамилию автоматически")
            if len(name_parts) == 1:
                name_parts.append("User")  # Добавляем фамилию по умолчанию
            else:
                print_error("❌ Не удалось извлечь имя и фамилию")
                return None
            
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Извлекаем адрес из второй строки
        address = lines[1].strip() if len(lines) > 1 else ""
        
        # Извлекаем город, штат, ZIP из третьей строки
        city_state_zip = lines[2].strip() if len(lines) > 2 else ""
        
        # Извлекаем месяц и год рождения из четвертой строки
        dob_info = lines[3].strip() if len(lines) > 3 else ""
        month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)'
        year_pattern = r'(\d{4})'
        
        month_match = re.search(month_pattern, dob_info)
        year_match = re.search(year_pattern, dob_info)
        
        if not month_match or not year_match:
            print_error("Не удалось извлечь месяц и год рождения")
            return None
            
        birth_month = month_match.group(1)
        birth_year = year_match.group(1)
        
        # Извлекаем телефон из пятой строки
        phone = lines[4].strip() if len(lines) > 4 else ""
        
        # Генерируем случайный день от 1 до 28
        birth_day = str(random.randint(1, 28))
        
        # Создаем случайный email на основе имени и фамилии
        email_prefix = first_name[0].lower() + last_name[0].lower() if last_name else first_name[0].lower()
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = email_prefix + random_suffix
        
        # Генерируем случайный пароль
        password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=12))
        
        # Соотношение месяцев к значениям в селекте
        month_values = {
            "January": "1", "February": "2", "March": "3", "April": "4",
            "May": "5", "June": "6", "July": "7", "August": "8",
            "September": "9", "October": "10", "November": "11", "December": "12"
        }
        
        print_info(f"Заполняю форму данными: {first_name} {last_name}, {email}@yahoo.com, {birth_month} {birth_day} {birth_year}")
        
        # Заполняем форму с человеческим вводом и антидетект
        try:
            # Добавляем случайные движения мыши перед началом
            await add_random_mouse_movements(page)
            await wait_for_human_delay(1000, 2000)
            
            # НЕ проверяем reCAPTCHA на этапе заполнения формы
            # Проверка будет только после нажатия кнопки отправки
            print_info("✓ Продолжаю заполнение формы без проверки reCAPTCHA")
            
            # Имя
            await page.wait_for_selector('#usernamereg-firstName', timeout=10000)
            await humanize_typing(page, '#usernamereg-firstName', first_name, (150, 300))
            print_info("✓ Имя заполнено с человеческим вводом")
            await wait_for_human_delay(800, 1500)
            
            # Фамилия
            await page.wait_for_selector('#usernamereg-lastName', timeout=5000)
            await humanize_typing(page, '#usernamereg-lastName', last_name, (150, 300))
            print_info("✓ Фамилия заполнена с человеческим вводом")
            await wait_for_human_delay(800, 1500)
            
            # Email
            await page.wait_for_selector('#usernamereg-userId', timeout=5000)
            await humanize_typing(page, '#usernamereg-userId', email, (100, 250))
            print_info("✓ Email заполнен с человеческим вводом")
            await wait_for_human_delay(1000, 2000)
            
            # Пароль
            await page.wait_for_selector('#usernamereg-password', timeout=5000)
            await humanize_typing(page, '#usernamereg-password', password, (80, 200))
            print_info("✓ Пароль заполнен с человеческим вводом")
            await wait_for_human_delay(1000, 2000)
            
            # Месяц рождения
            await page.wait_for_selector('#usernamereg-month', timeout=5000)
            await page.selectOption('#usernamereg-month', month_values.get(birth_month, "1"))
            print_info("✓ Месяц рождения выбран")
            await wait_for_human_delay(500, 1000)
            
            # День рождения
            await page.wait_for_selector('#usernamereg-day', timeout=5000)
            await humanize_typing(page, '#usernamereg-day', birth_day, (100, 200))
            print_info("✓ День рождения заполнен с человеческим вводом")
            await wait_for_human_delay(500, 1000)
            
            # Год рождения
            await page.wait_for_selector('#usernamereg-year', timeout=5000)
            await humanize_typing(page, '#usernamereg-year', birth_year, (80, 150))
            print_info("✓ Год рождения заполнен с человеческим вводом")
            await wait_for_human_delay(1000, 2000)
            
            # Добавляем еще движения мыши перед отправкой
            await add_random_mouse_movements(page)
            await wait_for_human_delay(1500, 3000)
            
        except Exception as e:
            print_error(f"Ошибка при заполнении формы: {e}")
            print_info("Пробую альтернативный способ заполнения...")
            
            # Альтернативный способ - заполняем все поля сразу
            await asyncio.sleep(2)
            await page.evaluate(f"""
                document.getElementById('usernamereg-firstName').value = '{first_name}';
                document.getElementById('usernamereg-lastName').value = '{last_name}';
                document.getElementById('usernamereg-userId').value = '{email}';
                document.getElementById('usernamereg-password').value = '{password}';
                document.getElementById('usernamereg-month').value = '{month_values.get(birth_month, "1")}';
                document.getElementById('usernamereg-day').value = '{birth_day}';
                document.getElementById('usernamereg-year').value = '{birth_year}';
            """)
            print_info("✓ Форма заполнена альтернативным способом")
        
        print_success("Форма заполнена")
        
        # Нажимаем кнопку "Next" с ожиданием
        try:
            print_info("Нажимаю кнопку 'Next'")
            await page.wait_for_selector('#reg-submit-button', timeout=10000)
            await page.click('#reg-submit-button')
            print_success("Форма отправлена")
        except Exception as e:
            print_error(f"Ошибка при отправке формы: {e}")
            print_info("Пробую альтернативный способ отправки...")
            await page.evaluate("document.getElementById('reg-submit-button').click();")
            print_success("Форма отправлена альтернативным способом")
        
        # СРАЗУ ПОСЛЕ НАЖАТИЯ КНОПКИ ПОЛНОСТЬЮ ОТКЛЮЧАЕМ АВТОМАТИЗАЦИЮ
        print_warning("🛡️ ФОРМА ОТПРАВЛЕНА! ПОЛНОСТЬЮ ОТКЛЮЧАЮ АВТОМАТИЗАЦИЮ!")
        
        # Отменяем мониторинг reCAPTCHA (если он был запущен)
        if monitor_task:
            monitor_task.cancel()
        
        # Полностью отключаем все автоматические действия
        user_choice = await disable_all_automation_completely(page)
        
        if user_choice == "1":
            print_success("✓ Пользователь подтвердил успешную регистрацию!")
            
            # Форматирование данных для вывода в нужном формате
            registration_data = {
                "email": f"{email}@yahoo.com",
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
                "birth_month": birth_month,
                "birth_day": birth_day,
                "birth_year": birth_year,
                "address": address,
                "city_state_zip": city_state_zip,
                "phone": phone,
                "registration_success": True
            }
            
            # Вывод данных в нужном формате
            print_header("Данные успешной регистрации:")
            print(f"Email: {email}@yahoo.com")
            print(f"Пароль: {password}")
            print(f"Имя: {first_name} {last_name}")
            print(f"Дата рождения: {birth_month} {birth_day}, {birth_year}")
            
            # Отправка данных в Telegram
            print_info(f"Отправка данных в Telegram пользователю {TG_BRO_GASPAR}...")
            telegram_result = await send_yahoo_account_to_telegram(registration_data)
            
            if telegram_result:
                # Ожидаем ответ от Telegram
                print_info("Данные успешно отправлены. Ожидание ответа...")
                telegram_response = await wait_for_telegram_response(registration_data["email"])
                
                if telegram_response:
                    # Проверяем на "NF" или похожие ответы
                    if telegram_response.strip().upper() == "NF":
                        print_warning("Получен ответ NF - возвращаемся в главное меню")
                        return {"registration_success": False, "nf_response": True}
                    
                    print_success("Ответ от Telegram получен!")
                    
                    # Извлечение SSN и DOB из ответа
                    import re
                    ssn, dob = None, None
                    
                    # Извлечение SSN и DOB по шаблонам
                    ssn_pattern = r'(\d{3}-\d{2}-\d{4})'
                    dob_pattern = r'(\d{2}/\d{2}/\d{4})'
                    
                    ssn_match = re.search(ssn_pattern, telegram_response)
                    dob_match = re.search(dob_pattern, telegram_response)
                    
                    if ssn_match and dob_match:
                        ssn = ssn_match.group(1)
                        dob = dob_match.group(1)
                        print_success(f"Найдены SSN: {ssn} и DOB: {dob}")
                        
                        # Сохраняем полные данные в папку full/
                        try:
                            full_dir = os.path.join(os.path.dirname(__file__), 'full')
                            if not os.path.exists(full_dir):
                                os.makedirs(full_dir)
                            
                            # Создаем файл с полными данными
                            full_data = {
                                "name": f"{first_name} {last_name}",
                                "first_name": first_name,
                                "last_name": last_name,
                                "address": address,
                                "city_state_zip": city_state_zip,
                                "birth_month": birth_month,
                                "birth_day": birth_day,
                                "birth_year": birth_year,
                                "ssn": ssn,
                                "dob": dob,
                                "phone": phone,
                                "email": f"{email}@yahoo.com",
                                "password": password,
                                "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # Сохраняем в JSON файл
                            import json
                            json_file_path = os.path.join(full_dir, 'all_registrations.json')
                            
                            # Читаем существующие данные или создаем новый файл
                            existing_data = []
                            if os.path.exists(json_file_path):
                                try:
                                    with open(json_file_path, 'r', encoding='utf-8') as f:
                                        existing_data = json.load(f)
                                except:
                                    existing_data = []
                            
                            # Добавляем новые данные
                            existing_data.append(full_data)
                            
                            # Сохраняем обновленные данные
                            with open(json_file_path, 'w', encoding='utf-8') as f:
                                json.dump(existing_data, f, indent=2, ensure_ascii=False)
                            
                            print_success(f"✓ Данные сохранены в {json_file_path}")
                            
                        except Exception as e:
                            print_error(f"❌ Ошибка при сохранении данных: {e}")
                        
                        # Обновляем SSN и DOB в папке data/
                        try:
                            from main import update_user_data_with_ssn_dob
                            update_user_data_with_ssn_dob(ssn, dob)
                        except Exception as e:
                            print_error(f"❌ Ошибка при обновлении SSN/DOB: {e}")
                        
                        return {
                            "registration_success": True,
                            "email": f"{email}@yahoo.com",
                            "password": password,
                            "ssn": ssn,
                            "dob": dob,
                            "telegram_response": telegram_response
                        }
                    else:
                        print_warning("SSN и DOB не найдены в ответе Telegram")
                        return {
                            "registration_success": True,
                            "email": f"{email}@yahoo.com",
                            "password": password,
                            "telegram_response": telegram_response
                        }
                else:
                    print_warning("Ответ от Telegram не получен")
                    return {
                        "registration_success": True,
                        "email": f"{email}@yahoo.com",
                        "password": password
                    }
            else:
                print_warning("Не удалось отправить данные в Telegram")
                return {
                    "registration_success": True,
                    "email": f"{email}@yahoo.com",
                    "password": password
                }
        else:
            print_error("❌ Не удалось автоматизировать заполнение формы Yahoo")
            return {
                "registration_success": False,
                "error": "Пользователь сообщил о неудачной регистрации"
            }
    except Exception as e:
        print_error(f"Ошибка при автоматизации заполнения формы: {e}")
        traceback.print_exc()
        return None

async def send_yahoo_account_to_telegram(registration_data):
    """
    Отправляет данные о зарегистрированном Yahoo аккаунте в Telegram
    
    :param registration_data: Словарь с данными регистрации
    :return: True если сообщение отправлено успешно, иначе False
    """
    print_header("Отправка данных о Yahoo аккаунте в Telegram")
    
    try:
        # Импортируем необходимые модули
        from telethon import TelegramClient
        from telethon.tl.types import InputPeerUser, InputUser
        import sys
        import json
        
        # Получение настроек для Telegram
        TELEGRAM_API_ID = None
        TELEGRAM_API_HASH = None
        TELEGRAM_PHONE = None
        PASSWORD = None
        TG_BRO_GASPAR = None
        
        try:
            # Пытаемся загрузить настройки из settings.json
            with open(os.path.join(os.path.dirname(__file__), 'settings.json'), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if 'telegram_settings' in settings:
                    ts = settings['telegram_settings']
                    TELEGRAM_API_ID = ts.get('api_id')
                    TELEGRAM_API_HASH = ts.get('api_hash')
                    TELEGRAM_PHONE = ts.get('phone')
                    PASSWORD = ts.get('password')
        except Exception as e:
            print_warning(f"Не удалось загрузить настройки из файла: {e}")
            
        # Если не удалось загрузить из файла, используем hardcoded значения
        if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
            # Используем значения из main.py
            sys.path.insert(0, os.path.dirname(__file__))
            import main
            TELEGRAM_API_ID = getattr(main, 'TELEGRAM_API_ID', 25760818)
            TELEGRAM_API_HASH = getattr(main, 'TELEGRAM_API_HASH', '5e76ccb9e484ad531ab03110d27ec6fe')
            TELEGRAM_PHONE = getattr(main, 'TELEGRAM_PHONE', '+14129186337')
            PASSWORD = getattr(main, 'password', "^84z6E;V0?5/")
            TG_BRO_GASPAR = getattr(main, 'TG_BRO_GASPAR', '@bro_gaspar')
        
        print_info("Инициализация Telegram клиента...")
        
        # Создаем клиента Telethon с уникальным именем сессии
        session_name = f'userbot_session_send_{int(datetime.now().timestamp())}'
        client = TelegramClient(session_name, TELEGRAM_API_ID, TELEGRAM_API_HASH)
        
        # Запускаем клиента
        await client.start(phone=TELEGRAM_PHONE, password=PASSWORD)
        
        # Если клиент не авторизован, выходим
        if not await client.is_user_authorized():
            print_error("Ошибка авторизации в Telegram")
            return False
            
        print_success("Telegram клиент успешно авторизован")
        
        # Проверяем, что TG_BRO_GASPAR не None
        if TG_BRO_GASPAR is None:
            TG_BRO_GASPAR = "bro_gaspar"  # Значение по умолчанию
            print_warning("TG_BRO_GASPAR не найден, использую значение по умолчанию: bro_gaspar")
        
        print_info(f"Отправляю данные о регистрации пользователю {TG_BRO_GASPAR}...")
        
        # Получаем username пользователя без @
        target_username = TG_BRO_GASPAR.replace('@', '')
        
        # Формируем текст сообщения с данными регистрации в простом формате
        full_name = f"{registration_data['first_name']} {registration_data['last_name']}"
        birth_date = f"{registration_data['birth_month']} {registration_data['birth_year']}"
        
        message_text = (
            f"{full_name}\n"
            f"{registration_data.get('address', 'Адрес не указан')}\n"
            f"{registration_data.get('city_state_zip', 'Город не указан')}\n"
            f"{birth_date}\n"
            f"{registration_data.get('phone', 'Телефон не указан')}"
        )
        
        # Получаем имя пользователя без символа @
        if TG_BRO_GASPAR is None:
            TG_BRO_GASPAR = "@bro_gaspar"  # Значение по умолчанию
            print_warning("TG_BRO_GASPAR не найден, использую значение по умолчанию: @bro_gaspar")
        
        import main
        group_id = getattr(main, 'TELEGRAM_GROUP_ID', -4596462704)
        print_info(f"Отправка сообщения в группу {group_id}...")
        
        try:
            # Отправляем сообщение в группу
            await client.send_message(group_id, message_text)
            print_success(f"Сообщение успешно отправлено в группу {group_id}")
            

            
            await client.disconnect()
            return True
        except Exception as e:
            print_error(f"Ошибка при отправке сообщения: {e}")
            traceback.print_exc()
            await client.disconnect()
            return False
    except Exception as e:
        print_error(f"Ошибка при работе с Telegram API: {e}")
        traceback.print_exc()
        return False

async def wait_for_telegram_response(email, timeout=300):
    """
    Ожидает ответ от пользователя Telegram на сообщение о регистрации Yahoo аккаунта
    
    :param email: Email зарегистрированного аккаунта (для идентификации)
    :param timeout: Таймаут в секундах (по умолчанию 5 минут)
    :return: Текст ответа или None при ошибке/таймауте
    """
    print_header("Ожидание ответа от Telegram")
    
    try:
        # Импортируем необходимые модули
        from telethon import TelegramClient
        import asyncio
        import sys
        import json
        from datetime import timezone, datetime
        
        # Получение настроек для Telegram
        TELEGRAM_API_ID = None
        TELEGRAM_API_HASH = None
        TELEGRAM_PHONE = None
        PASSWORD = None
        TG_BRO_GASPAR = None
        
        try:
            # Пытаемся загрузить настройки из settings.json
            with open(os.path.join(os.path.dirname(__file__), 'settings.json'), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if 'telegram_settings' in settings:
                    ts = settings['telegram_settings']
                    TELEGRAM_API_ID = ts.get('api_id')
                    TELEGRAM_API_HASH = ts.get('api_hash')
                    TELEGRAM_PHONE = ts.get('phone')
                    PASSWORD = ts.get('password')
        except Exception as e:
            print_warning(f"Не удалось загрузить настройки из файла: {e}")
            
        # Если не удалось загрузить из файла, используем hardcoded значения
        if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
            # Используем значения из main.py
            sys.path.insert(0, os.path.dirname(__file__))
            import main
            TELEGRAM_API_ID = getattr(main, 'TELEGRAM_API_ID', 25760818)
            TELEGRAM_API_HASH = getattr(main, 'TELEGRAM_API_HASH', '5e76ccb9e484ad531ab03110d27ec6fe')
            TELEGRAM_PHONE = getattr(main, 'TELEGRAM_PHONE', '+14129186337')
            PASSWORD = getattr(main, 'password', "^84z6E;V0?5/")
            TG_BRO_GASPAR = getattr(main, 'TG_BRO_GASPAR_USERNAME', 'bro_gaspar')
        
        print_info("Инициализация Telegram клиента для получения ответа...")
        
        # Создаем клиента Telethon с уникальным именем сессии
        session_name = f'userbot_session_receive_{int(datetime.now().timestamp())}'
        client = TelegramClient(session_name, TELEGRAM_API_ID, TELEGRAM_API_HASH)
        
        # Запускаем клиента
        await client.start(phone=TELEGRAM_PHONE, password=PASSWORD)
        
        # Если клиент не авторизован, выходим
        if not await client.is_user_authorized():
            print_error("Ошибка авторизации в Telegram")
            return None
            
        print_success("Telegram клиент успешно авторизован")
        
        # Проверяем, что TG_BRO_GASPAR не None
        if TG_BRO_GASPAR is None:
            TG_BRO_GASPAR = "bro_gaspar"  # Значение по умолчанию
            print_warning("TG_BRO_GASPAR не найден, использую значение по умолчанию: bro_gaspar")
        
        print_info(f"Ожидаю ответ в группе...")
        
        # Используем ID группы вместо личного сообщения
        import main
        group_id = getattr(main, 'TELEGRAM_GROUP_ID', -4596462704)
        
        # Получаем диалог группы
        dialog = await client.get_entity(group_id)
        
        # Запоминаем время начала ожидания
        start_time = datetime.now()
        
        # Получаем ID последнего сообщения перед началом ожидания
        last_message_id = None
        async for message in client.iter_messages(dialog, limit=1):
            if message:
                last_message_id = message.id
                break
        
        print_info(f"Начинаю ожидание новых сообщений после ID: {last_message_id}")
        
        # Бесконечный цикл ожидания ответа
        while True:
            try:
                # Получаем новые сообщения от этого пользователя
                async for message in client.iter_messages(dialog, limit=10):
                    # Проверяем только новые сообщения от пользователя (не от нас)
                    if ((not message.out) and 
                        (last_message_id is None or message.id > last_message_id)):
                        
                        print_success(f"Получен новый ответ в группе: {message.text}")
                        
                        # Проверяем на "NF" или похожие ответы
                        response_text = message.text.strip().upper()
                        nf_keywords = ['NF', 'NOT FOUND', 'НЕ НАЙДЕНО', 'НЕТ ДАННЫХ', 'NO DATA', 'EMPTY']
                        
                        if any(keyword in response_text for keyword in nf_keywords):
                            print_warning(f"Получен ответ NF: {message.text}")
                            print_info("Возвращаемся в главное меню...")
                            
                            await client.disconnect()
                            return "NF"  # Специальный код для возврата в главное меню
                        
                        await client.disconnect()
                        return message.text
                        
            except Exception as e:
                print_warning(f"Ошибка при получении сообщений: {e}")
                print_info("Пробую альтернативный способ...")
                
                # Альтернативный способ - просто ждем и предлагаем ручной ввод
                print_info("Ожидаю ответ...")
                await asyncio.sleep(5)
                
                # Каждые 30 секунд предлагаем ручной ввод
                if int((datetime.now() - start_time).total_seconds()) % 30 == 0:
                    print_info("Можете ввести ответ вручную:")
                    manual_response = input("📱 Вставьте ответ от Telegram (с SSN и DOB): ")
                    if manual_response.strip():
                        await client.disconnect()
                        return manual_response.strip()
            
            # Ждем 5 секунд перед следующей проверкой
            print_info("Ожидаю ответ...")
            await asyncio.sleep(5)
        
        print_warning(f"Ожидание ответа в группе прервано")
        await client.disconnect()
        
        # Предложим пользователю ввести ответ вручную
        print_info("Можете ввести ответ вручную:")
        manual_response = input("📱 Вставьте ответ от Telegram (с SSN и DOB): ")
        
        if manual_response.strip():
            return manual_response.strip()
        else:
            return None
        
    except Exception as e:
        print_error(f"Ошибка при ожидании ответа от Telegram: {e}")
        traceback.print_exc()
        
        # Предложим пользователю ввести ответ вручную при ошибке
        print_info("Можете ввести ответ вручную из-за ошибки:")
        manual_response = input("📱 Вставьте ответ от Telegram (с SSN и DOB): ")
        
        if manual_response.strip():
            return manual_response.strip()
        else:
            return None

async def open_bank_of_america_with_playwright(profile_id):
    """
    Открывает страницу Bank of America в профиле OctoBrowser
    
    :param profile_id: UUID профиля
    :return: True если успешно, False при ошибке
    """
    print_header(f"Открытие Bank of America в профиле {profile_id}")
    
    try:
        # URL Bank of America
        boa_url = "https://www.bankofamerica.com/deposits/checking/advantage-safebalance-banking-account/before-you-apply/?offer_code=PSJ300CIS"
        
        print_info(f"Открываю Bank of America: {boa_url}")
        
        # Запускаем профиль с Bank of America
        result = await start_profile_with_stealth_playwright(profile_id, boa_url)
        
        if result:
            print_success("✓ Bank of America открыт в профиле")
            print_info("Браузер запущен с антидетект-защитой")
            print_info("Вы можете заполнить форму регистрации вручную")
            
            # Ждем, пока пользователь завершит работу
            input("Нажмите Enter для закрытия браузера...")
            
            # Закрываем браузер
            await result["browser"].close()
            await result["playwright"].stop()
            print_success("✓ Браузер закрыт")
            return True
        else:
            print_error("❌ Не удалось открыть Bank of America")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при открытии Bank of America: {e}")
        import traceback
        traceback.print_exc()
        return False

async def open_sms_pool_with_pyppeteer():
    """
    Открывает SMS Pool через Pyppeteer в отдельном браузере (не через OctoBrowser)
    
    :return: True если успешно, False при ошибке
    """
    print_header("Открытие SMS Pool через Pyppeteer")
    
    try:
        print_info("Запускаю браузер через Pyppeteer...")
        
        # Запускаем браузер через Pyppeteer
        browser = await pyppeteer.launch(
            headless=False,  # Показываем браузер
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        
        # Создаем новую страницу
        page = await browser.newPage()
        
        # Устанавливаем user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Устанавливаем размер окна
        await page.setViewport({'width': 1366, 'height': 768})
        
        print_info("Открываю SMS Pool...")
        
        # Переходим на SMS Pool
        await page.goto('https://www.smspool.net/login', {
            'waitUntil': 'networkidle2',
            'timeout': 30000
        })
        
        print_success("SMS Pool открыт в отдельном браузере")
        print_info("Браузер готов для работы с SMS Pool")
        
        # Ждем пользователя
        input("SMS Pool открыт. Нажмите Enter для закрытия браузера...")
        
        # Закрываем браузер
        await browser.close()
        print_success("Браузер закрыт")
        
        return True
        
    except Exception as e:
        print_error(f"Ошибка при открытии SMS Pool: {e}")
        traceback.print_exc()
        return False


async def start_profile_with_yahoo_registration(profile_id, user_data):
    """
    Запускает профиль OctoBrowser, открывает страницу регистрации Yahoo и автоматически заполняет форму
    
    :param profile_id: UUID профиля
    :param user_data: Строка с данными пользователя (имя, адрес, дата рождения, телефон)
    :return: словарь с browser, page и созданными данными или False при ошибке
    """
    print_header(f"Запуск профиля {profile_id} с автоматической регистрацией Yahoo")
    
    try:
        # Сначала спрашиваем пользователя о готовности запустить профиль
        print_info("❗ Настройте прокси в OctoBrowser вручную, если необходимо")
        input("Нажмите Enter для запуска профиля и начала автоматизации Yahoo...")
        
        # Запускаем профиль с использованием stealth-режима
        result = await start_profile_with_stealth_playwright(profile_id, "https://login.yahoo.com/account/create")
        if not result:
            print_error("Не удалось запустить профиль")
            return False
            
        # Ждем загрузки страницы
        print_info("Страница регистрации Yahoo открыта, ожидаю загрузки...")
        await asyncio.sleep(3)
        
        # Применяем дополнительные методы обхода капчи перед регистрацией
        print_info("🛡️ Применяю дополнительные методы обхода капчи...")
        await apply_yahoo_captcha_bypass(result["page"])
        await wait_for_human_delay(2000, 4000)
        
        # Автоматизируем заполнение формы
        registration_data = await automate_yahoo_registration(result["page"], user_data)
        if not registration_data:
            print_error("Не удалось автоматизировать заполнение формы")
            return False
            
        # Добавляем данные регистрации к результату
        result["registration_data"] = registration_data
        
        print_success("Регистрация Yahoo успешно автоматизирована")
        return result
        
    except Exception as e:
        print_error(f"Ошибка при запуске профиля с автоматической регистрацией: {e}")
        traceback.print_exc()
        return False

# Тестовая функция
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test-proxy":
        # Тестирование настройки прокси
        profile_id = input("Введите ID профиля: ").strip()
        host = input("Введите хост прокси: ").strip()
        port = input("Введите порт прокси: ").strip()
        username = input("Введите имя пользователя прокси: ").strip()
        password = input("Введите пароль прокси: ").strip()
        
        proxy_data = {
            "host": host,
            "port": port,
            "username": username,
            "password": password
        }
        
        print_header(f"Тестирование настройки прокси для профиля {profile_id}")
        asyncio.run(configure_profile_proxy(profile_id, proxy_data))
    elif len(sys.argv) > 1 and sys.argv[1] == "test-run":
        # Тестирование запуска профиля по примеру test.py
        profile_id = input("Введите ID профиля: ").strip()
        url = input("Введите URL для перехода (или оставьте пустым): ").strip() or "https://login.yahoo.com/account/create"
        
        async def test_run():
            browser_data = await connect_browser(profile_id, url)
            if browser_data:
                try:
                    page = browser_data["page"]
                    print_info("Ищу элемент на странице...")
                    values = await page.querySelector('input[name="firstName"]')
                    if values:
                        print_info(f'Найдено поле ввода имени пользователя на странице Yahoo')
                    else:
                        print_info('Элемент не найден, но браузер запущен успешно')
                    
                    input("Нажмите Enter для завершения работы...")
                finally:
                    # Закрываем браузер
                    await browser_data["browser"].close()
                    print_success("Браузер закрыт")
            
        asyncio.run(test_run())
    elif len(sys.argv) > 1 and sys.argv[1] == "launch-yahoo":
        # Автоматический запуск профиля с Yahoo без дополнительных вопросов
        if len(sys.argv) < 3:
            print_error("Необходимо указать ID профиля: python octo.py launch-yahoo <profile_id>")
            sys.exit(1)
            
        profile_id = sys.argv[2].strip()
        print_header(f"Запуск профиля {profile_id} с переходом на страницу Yahoo")
        
        async def auto_launch_yahoo():
            result = await start_profile_with_yahoo(profile_id)
            if result:
                input("Нажмите Enter для завершения работы...")
                await stop_profile(profile_id)
                    
        asyncio.run(auto_launch_yahoo())
    elif len(sys.argv) > 1 and sys.argv[1] == "stealth-launch-sync":
        # Запуск профиля с режимом маскировки автоматизации (синхронная версия для отладки)
        if len(sys.argv) < 3:
            print_error("Необходимо указать ID профиля: python octo.py stealth-launch-sync <profile_id>")
            sys.exit(1)
        
        profile_id = sys.argv[2].strip()
        url = sys.argv[3].strip() if len(sys.argv) > 3 else "https://login.yahoo.com/account/create"
        
        print_header(f"Запуск профиля {profile_id} в режиме stealth (синхронно)")
        result = start_profile_with_stealth_playwright_sync(profile_id, url)
        if result:
            try:
                    input("Нажмите Enter для завершения работы...")
            except KeyboardInterrupt:
                print("\nОстановлено пользователем")
    elif len(sys.argv) > 1 and sys.argv[1] == "stealth-launch":
        # Запуск профиля с режимом маскировки автоматизации (асинхронная версия)
        if len(sys.argv) < 3:
            print_error("Необходимо указать ID профиля: python octo.py stealth-launch <profile_id>")
            sys.exit(1)
        
        profile_id = sys.argv[2].strip()
        url = sys.argv[3].strip() if len(sys.argv) > 3 else "https://login.yahoo.com/account/create"
        
        async def stealth_launch():
            print_header(f"Запуск профиля {profile_id} в режиме stealth")
            result = await start_profile_with_stealth_playwright(profile_id, url)
            if result:
                try:
                    input("Нажмите Enter для завершения работы...")
                    await result["browser"].close()
                    print_success("Браузер закрыт")
                except KeyboardInterrupt:
                    print("\nОстановлено пользователем")
                    await result["browser"].close()
                    print_success("Браузер закрыт")
                
        asyncio.run(stealth_launch())
    elif len(sys.argv) > 1 and sys.argv[1] == "yahoo-register":
        # Запуск регистрации Yahoo с предоставленным профилем и данными пользователя
        if len(sys.argv) < 3:
            print_error("Необходимо указать ID профиля: python octo.py yahoo-register <profile_id>")
            sys.exit(1)
            
        profile_id = sys.argv[2].strip()
        
        # Пример данных пользователя
        user_data = """Sachiko Yatchak
944 E 20th St Los Angeles, CA 90011
United States
October 1959
(949) 867-9366"""

        print_header(f"Запуск профиля {profile_id} с автоматической регистрацией Yahoo")
        
        async def yahoo_register():
            result = await start_profile_with_yahoo_registration(profile_id, user_data)
            if result:
                input("Нажмите Enter для завершения работы...")
                await result["browser"].close()
                print_success("Браузер закрыт")
        
        asyncio.run(yahoo_register())
    elif len(sys.argv) > 1 and sys.argv[1] == "open-sms":
        # Открытие SMS Pool через Pyppeteer
        print_header("Открытие SMS Pool через Pyppeteer")
        
        async def open_sms():
            await open_sms_pool_with_pyppeteer()
        
        asyncio.run(open_sms())
    elif len(sys.argv) > 1 and sys.argv[1] == "test-telegram":
        # Тестирование функций отправки в Telegram и ожидания ответа
        print_header("Тестирование Telegram-интеграции")
        
        async def test_telegram():
            # Тестовые данные регистрации
            registration_data = {
                "email": "test@yahoo.com",
                "password": "Test123!@#",
                "first_name": "John",
                "last_name": "Doe",
                "birth_month": "January",
                "birth_day": "15",
                "birth_year": "1990",
                "registration_success": True
            }
            
            # Отправляем данные в Telegram
            print_info(f"Отправка тестовых данных в Telegram пользователю {TG_BRO_GASPAR}...")
            telegram_result = await send_yahoo_account_to_telegram(registration_data)
            
            if telegram_result:
                print_success("Данные успешно отправлены!")
                
                # Ожидаем ответ
                print_info("Ожидание ответа от Telegram (таймаут 120 сек)...")
                telegram_response = await wait_for_telegram_response(registration_data["email"], timeout=120)
                
                if telegram_response:
                    # Проверяем на "NF" или похожие ответы
                    if telegram_response.strip().upper() == "NF":
                        print_warning("Получен ответ NF - возвращаемся в главное меню")
                        return
                    
                    print_success(f"Получен ответ: {telegram_response}")
                    
                    # Извлечение SSN и DOB из ответа
                    ssn_pattern = r'(\d{3}-\d{2}-\d{4})'
                    dob_pattern = r'(\d{2}/\d{2}/\d{4})'
                    
                    ssn_match = re.search(ssn_pattern, telegram_response)
                    dob_match = re.search(dob_pattern, telegram_response)
                    
                    if ssn_match and dob_match:
                        ssn = ssn_match.group(1)
                        dob = dob_match.group(1)
                        print_success(f"Найдены SSN: {ssn} и DOB: {dob}")
                    else:
                        print_warning("Не удалось извлечь SSN и DOB из ответа")
                else:
                    print_warning("Ответ от Telegram не получен")
            else:
                print_error("Не удалось отправить данные в Telegram")
                
        asyncio.run(test_telegram())
    else:
        print_header("Инструменты для работы с OctoBrowser")
        print_info("Доступные команды:")
        print_info("python octo.py test-proxy - Тестирование настройки прокси для профиля")
        print_info("python octo.py test-run - Тестирование запуска профиля и доступа к странице")
        print_info("python octo.py launch-yahoo <profile_id> - Запуск профиля с переходом на страницу Yahoo")
        print_info("python octo.py stealth-launch <profile_id> [url] - Запуск профиля с маскировкой автоматизации")
        print_info("python octo.py stealth-launch-sync <profile_id> [url] - То же самое, но синхронная версия")
        print_info("python octo.py yahoo-register <profile_id> - Запуск автоматической регистрации Yahoo")
        print_info("python octo.py open-sms - Открытие SMS Pool через Pyppeteer")
        print_info("python octo.py test-telegram - Тестирование Telegram-интеграции")
        
        # Проверка доступа к API
        asyncio.run(check_api_access()) 

# Улучшенные настройки антидетекта
ADVANCED_STEALTH_SETTINGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "viewport": {"width": 1920, "height": 1080},
    "timezone_id": "America/New_York",
    "locale": "en-US",
    "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # NYC
    "permissions": ["geolocation", "notifications", "camera", "microphone"],
    "extra_http_headers": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
}

def get_random_user_agent():
    """Возвращает случайный User-Agent для лучшего антидетекта"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
    ]
    return random.choice(user_agents)

async def apply_advanced_stealth(page):
    """Применяет продвинутые настройки антидетекта"""
    try:
        print_info("Применяю продвинутые настройки антидетекта...")
        
        # Устанавливаем случайный User-Agent
        user_agent = get_random_user_agent()
        await page.set_extra_http_headers({"User-Agent": user_agent})
        print_info(f"User-Agent установлен: {user_agent[:50]}...")
        
        # Устанавливаем viewport
        await page.set_viewport_size(ADVANCED_STEALTH_SETTINGS["viewport"])
        print_info(f"Viewport установлен: {ADVANCED_STEALTH_SETTINGS['viewport']}")
        
        # Устанавливаем timezone и locale
        await page.add_init_script("""
            Object.defineProperty(Intl, 'DateTimeFormat', {
                get: function() {
                    return function(locale, options) {
                        return new Intl.DateTimeFormat(locale || 'en-US', options);
                    };
                }
            });
        """)
        
        # Скрываем webdriver
        await page.add_init_script("""
            // Сохраняем оригинальные функции для возможности восстановления
            window.originalNavigator = navigator;
            window.originalWebdriver = navigator.webdriver;
            window.originalFetch = window.fetch;
            window.originalXMLHttpRequest = XMLHttpRequest.prototype.open;
            window.originalGrecaptcha = window.grecaptcha;
            
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Скрываем автоматизацию
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Скрываем Chrome
            window.chrome = {
                runtime: {},
            };
            
            // Скрываем автоматизацию в window
            Object.defineProperty(window, 'navigator', {
                get: () => ({
                    ...navigator,
                    webdriver: undefined,
                    plugins: [1, 2, 3, 4, 5],
                    languages: ['en-US', 'en'],
                }),
            });
        """)
        
        # Добавляем случайные задержки
        await page.add_init_script("""
            // Переопределяем setTimeout для добавления случайных задержек
            const originalSetTimeout = window.setTimeout;
            window.setTimeout = function(fn, delay, ...args) {
                const randomDelay = delay + Math.random() * 100;
                return originalSetTimeout(fn, randomDelay, ...args);
            };
        """)
        
        # Скрываем автоматизацию в консоли
        await page.add_init_script("""
            // Скрываем автоматизацию в консоли
            const originalLog = console.log;
            console.log = function(...args) {
                const text = args.join(' ');
                if (text.includes('webdriver') || text.includes('automation')) {
                    return;
                }
                return originalLog.apply(console, args);
            };
        """)
        
        print_success("✓ Продвинутые настройки антидетекта применены")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при применении антидетекта: {e}")

async def humanize_typing(page, selector, text, delay_range=(100, 300)):
    """Имитирует человеческий ввод с случайными задержками"""
    try:
        element = await page.wait_for_selector(selector, timeout=5000)
        await element.click()
        await element.fill("")
        
        for char in text:
            await element.type(char, delay=random.randint(*delay_range))
            # Случайная пауза между символами
            if random.random() < 0.1:  # 10% шанс паузы
                await page.wait_for_timeout(random.randint(50, 200))
        
        print_success(f"✓ Текст введен с имитацией человеческого ввода: {text}")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при человеческом вводе: {e}")
        # Fallback к обычному вводу
        try:
            element = await page.wait_for_selector(selector, timeout=5000)
            await element.fill(text)
        except Exception as e2:
            print_error(f"❌ Ошибка при fallback вводе: {e2}")

async def add_random_mouse_movements(page):
    """Добавляет случайные движения мыши для имитации человека"""
    try:
        # Получаем размеры viewport
        viewport = await page.evaluate("""
            () => ({
                width: window.innerWidth,
                height: window.innerHeight
            })
        """)
        
        # Делаем несколько случайных движений мыши
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            await page.mouse.move(x, y)
            await page.wait_for_timeout(random.randint(50, 150))
        
        print_success("✓ Случайные движения мыши добавлены")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при добавлении движений мыши: {e}")

async def wait_for_human_delay(min_delay=1000, max_delay=3000):
    """Ждет случайное время для имитации человеческого поведения"""
    delay = random.randint(min_delay, max_delay)
    await asyncio.sleep(delay / 1000)
    print_info(f"⏱️ Человеческая задержка: {delay}ms")

async def bypass_captcha_advanced(page):
    """Продвинутый обход капчи с дополнительными антидетект мерами"""
    try:
        print_info("🛡️ Применяю продвинутые антидетект меры для обхода капчи...")
        
        # Добавляем скрипты для обхода детекции
        await page.add_init_script("""
            // Скрываем все признаки автоматизации
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Скрываем автоматизацию в window
            Object.defineProperty(window, 'navigator', {
                get: () => ({
                    ...navigator,
                    webdriver: undefined,
                    plugins: [1, 2, 3, 4, 5],
                    languages: ['en-US', 'en'],
                    hardwareConcurrency: 8,
                    deviceMemory: 8,
                }),
            });
            
            // Скрываем автоматизацию в document
            Object.defineProperty(document, 'hidden', {
                get: () => false,
            });
            
            // Скрываем автоматизацию в screen
            Object.defineProperty(screen, 'width', {
                get: () => 1920,
            });
            Object.defineProperty(screen, 'height', {
                get: () => 1080,
            });
            
            // Скрываем автоматизацию в console
            const originalLog = console.log;
            console.log = function(...args) {
                const text = args.join(' ');
                if (text.includes('webdriver') || text.includes('automation') || text.includes('selenium')) {
                    return;
                }
                return originalLog.apply(console, args);
            };
            
            // Скрываем автоматизацию в performance
            Object.defineProperty(performance, 'timing', {
                get: () => ({
                    navigationStart: Date.now() - Math.random() * 1000,
                    loadEventEnd: Date.now(),
                    domContentLoadedEventEnd: Date.now() - Math.random() * 100,
                }),
            });
        """)
        
        # Добавляем случайные движения мыши
        await add_random_mouse_movements(page)
        
        # Ждем случайное время
        await wait_for_human_delay(2000, 5000)
        
        print_success("✓ Продвинутые антидетект меры применены")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при применении антидетект мер: {e}")

async def create_stealth_profile(profile_name):
    """Создает профиль с максимальными настройками антидетекта"""
    try:
        print_header(f"Создание стелс профиля '{profile_name}' с максимальным антидетектом")
        
        # Создаем профиль с улучшенными настройками
        profile_id = await create_profile(profile_name, "win")
        
        if profile_id:
            print_success(f"✓ Стелс профиль создан: {profile_id}")
            return profile_id
        else:
            print_error("❌ Не удалось создать стелс профиль")
            return None
            
    except Exception as e:
        print_error(f"❌ Ошибка при создании стелс профиля: {e}")
        return None

async def apply_yahoo_captcha_bypass(page):
    """Применяет агрессивные методы обхода капчи Yahoo"""
    try:
        print_info("🛡️ Применяю агрессивные методы обхода капчи Yahoo...")
        
        # Блокируем reCAPTCHA и другие скрипты детекции
        await page.add_init_script("""
            // Сохраняем оригинальные функции для возможности восстановления
            if (!window.originalGrecaptcha) {
                window.originalGrecaptcha = window.grecaptcha;
            }
            if (!window.originalRecaptcha) {
                window.originalRecaptcha = window.recaptcha;
            }
            
            // Блокируем reCAPTCHA
            window.grecaptcha = undefined;
            window.recaptcha = undefined;
            
            // Блокируем Google Analytics и другие трекеры
            window.ga = undefined;
            window.gtag = undefined;
            window.dataLayer = undefined;
            
            // Скрываем все признаки автоматизации
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Скрываем автоматизацию в window
            Object.defineProperty(window, 'navigator', {
                get: () => ({
                    ...navigator,
                    webdriver: undefined,
                    plugins: [1, 2, 3, 4, 5],
                    languages: ['en-US', 'en'],
                    hardwareConcurrency: 8,
                    deviceMemory: 8,
                    maxTouchPoints: 0,
                    onLine: true,
                    cookieEnabled: true,
                    doNotTrack: null,
                }),
            });
            
            // Скрываем автоматизацию в document
            Object.defineProperty(document, 'hidden', {
                get: () => false,
            });
            
            // Скрываем автоматизацию в screen
            Object.defineProperty(screen, 'width', {
                get: () => 1920,
            });
            Object.defineProperty(screen, 'height', {
                get: () => 1080,
            });
            Object.defineProperty(screen, 'availWidth', {
                get: () => 1920,
            });
            Object.defineProperty(screen, 'availHeight', {
                get: () => 1040,
            });
            
            // Скрываем автоматизацию в console
            const originalLog = console.log;
            console.log = function(...args) {
                const text = args.join(' ');
                if (text.includes('webdriver') || text.includes('automation') || text.includes('selenium') || text.includes('recaptcha')) {
                    return;
                }
                return originalLog.apply(console, args);
            };
            
            // Скрываем автоматизацию в performance
            Object.defineProperty(performance, 'timing', {
                get: () => ({
                    navigationStart: Date.now() - Math.random() * 1000,
                    loadEventEnd: Date.now(),
                    domContentLoadedEventEnd: Date.now() - Math.random() * 100,
                }),
            });
            
            // Блокируем детекцию мыши
            const originalMouseEvent = window.MouseEvent;
            window.MouseEvent = function(type, init) {
                if (init && init.isTrusted === false) {
                    init.isTrusted = true;
                }
                return new originalMouseEvent(type, init);
            };
            
            // Блокируем детекцию клавиатуры
            const originalKeyboardEvent = window.KeyboardEvent;
            window.KeyboardEvent = function(type, init) {
                if (init && init.isTrusted === false) {
                    init.isTrusted = true;
                }
                return new originalKeyboardEvent(type, init);
            };
            
            // Скрываем автоматизацию в WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel(R) Iris(TM) Graphics 6100';
                }
                return getParameter.call(this, parameter);
            };
            
            // Скрываем автоматизацию в Canvas
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
                const result = originalToDataURL.call(this, type, quality);
                if (result.includes('data:image/png;base64,')) {
                    return result;
                }
                return result;
            };
            
            // Блокируем детекцию времени
            const originalDate = Date;
            Date = function(...args) {
                if (args.length === 0) {
                    return new originalDate(Date.now() + Math.random() * 100);
                }
                return new originalDate(...args);
            };
            Date.now = function() {
                return originalDate.now() + Math.random() * 100;
            };
            
            // Блокируем детекцию геолокации
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition = function(success, error, options) {
                    if (success) {
                        success({
                            coords: {
                                latitude: 40.7128,
                                longitude: -74.0060,
                                accuracy: 100,
                                altitude: null,
                                altitudeAccuracy: null,
                                heading: null,
                                speed: null
                            },
                            timestamp: Date.now()
                        });
                    }
                };
            }
            
            // Блокируем детекцию батареи
            if (navigator.getBattery) {
                navigator.getBattery = function() {
                    return Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 0.8
                    });
                };
            }
            
            // Блокируем детекцию медиа устройств
            if (navigator.mediaDevices) {
                navigator.mediaDevices.enumerateDevices = function() {
                    return Promise.resolve([]);
                };
            }
            
            // Скрываем автоматизацию в localStorage
            const originalSetItem = Storage.prototype.setItem;
            Storage.prototype.setItem = function(key, value) {
                if (key.includes('automation') || key.includes('webdriver')) {
                    return;
                }
                return originalSetItem.call(this, key, value);
            };
            
            // Блокируем детекцию в URL
            const originalPushState = history.pushState;
            history.pushState = function(state, title, url) {
                if (url && url.includes('recaptcha')) {
                    return;
                }
                return originalPushState.call(this, state, title, url);
            };
            
            // Блокируем детекцию в fetch
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                if (url && url.includes('recaptcha')) {
                    return Promise.resolve(new Response('{"success": true}', {
                        status: 200,
                        headers: {'Content-Type': 'application/json'}
                    }));
                }
                return originalFetch.call(this, url, options);
            };
            
            // Блокируем детекцию в XMLHttpRequest
            const originalOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
                if (url && url.includes('recaptcha')) {
                    this.readyState = 4;
                    this.status = 200;
                    this.responseText = '{"success": true}';
                    setTimeout(() => {
                        if (this.onreadystatechange) {
                            this.onreadystatechange();
                        }
                    }, 100);
                    return;
                }
                return originalOpen.call(this, method, url, async, user, password);
            };
        """)
        
        # Добавляем случайные движения мыши
        await add_random_mouse_movements(page)
        
        # Ждем случайное время
        await wait_for_human_delay(3000, 7000)
        
        print_success("✓ Агрессивные методы обхода капчи применены")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при применении методов обхода капчи: {e}")

async def detect_recaptcha_page(page):
    """Детектирует страницу reCAPTCHA Yahoo"""
    try:
        current_url = page.url
        if "login.yahoo.com/account/challenge/recaptcha" in current_url:
            print_warning("🛡️ Обнаружена страница reCAPTCHA Yahoo!")
            return True
        return False
    except Exception as e:
        print_warning(f"⚠️ Ошибка при детекции reCAPTCHA: {e}")
        return False

async def detect_recaptcha_and_handle(page, only_after_submit=False):
    """Детектирует reCAPTCHA и обрабатывает её"""
    try:
        current_url = page.url
        print_info(f"🔍 Проверяю URL: {current_url}")
        
        # Если флаг only_after_submit=True, то проверяем только после отправки формы
        if only_after_submit:
            print_info("🔍 Проверяю reCAPTCHA только после отправки формы...")
        
        # Проверяем различные варианты reCAPTCHA
        recaptcha_indicators = [
            "login.yahoo.com/account/challenge/recaptcha",
            "challenge/recaptcha",
            "recaptcha",
            "challenge"
        ]
        
        for indicator in recaptcha_indicators:
            if indicator in current_url:
                print_warning(f"🛡️ ОБНАРУЖЕНА reCAPTCHA! Индикатор: {indicator}")
                
                # Принудительно отключаем автоматизацию
                return await force_disable_automation_and_wait(page)
        
        # Дополнительная проверка по содержимому страницы (только если не только после отправки)
        if not only_after_submit:
            try:
                page_content = await page.content()
                if "recaptcha" in page_content.lower() or "challenge" in page_content.lower():
                    print_warning("🛡️ ОБНАРУЖЕНА reCAPTCHA в содержимом страницы!")
                    return await force_disable_automation_and_wait(page)
            except:
                pass
        
        return None  # reCAPTCHA не обнаружена
    except Exception as e:
        print_warning(f"⚠️ Ошибка при обработке reCAPTCHA: {e}")
        return False

async def disable_stealth_temporarily(page):
    """Временно отключает stealth режим для прохождения reCAPTCHA"""
    try:
        print_info("🔄 Временно отключаю stealth режим для reCAPTCHA...")
        
        # Удаляем все инжектированные скрипты stealth
        await page.add_init_script("""
            // Восстанавливаем оригинальные функции
            if (window.originalNavigator) {
                Object.defineProperty(window, 'navigator', {
                    get: () => window.originalNavigator,
                    configurable: true
                });
            }
            
            if (window.originalWebdriver) {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => window.originalWebdriver,
                    configurable: true
                });
            }
            
            // Восстанавливаем оригинальные fetch и XMLHttpRequest
            if (window.originalFetch) {
                window.fetch = window.originalFetch;
            }
            
            if (window.originalXMLHttpRequest) {
                XMLHttpRequest.prototype.open = window.originalXMLHttpRequest;
            }
            
            // Восстанавливаем reCAPTCHA
            if (window.originalGrecaptcha) {
                window.grecaptcha = window.originalGrecaptcha;
            }
            
            console.log('Stealth режим временно отключен для reCAPTCHA');
        """)
        
        print_success("✓ Stealth режим временно отключен")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при отключении stealth: {e}")

async def reenable_stealth_after_recaptcha(page):
    """Вновь включает stealth режим после прохождения reCAPTCHA"""
    try:
        print_info("🔄 Вновь включаю stealth режим...")
        
        # Применяем stealth заново
        await apply_advanced_stealth(page)
        await apply_yahoo_captcha_bypass(page)
        
        print_success("✓ Stealth режим восстановлен")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при восстановлении stealth: {e}")

async def wait_for_user_confirmation():
    """Ожидает подтверждения пользователя о регистрации Yahoo"""
    print("\n" + "="*60)
    print("🛡️ Обнаружена страница reCAPTCHA Yahoo!")
    print("📝 Автоматизация временно отключена.")
    print("="*60)
    print("Удалось зарегистрировать аккаунт yahoo.com?")
    print("1) Да, удалось")
    print("2) Нет, не удалось")
    print("="*60)
    
    while True:
        try:
            choice = input("Введите выбор (1 или 2): ").strip()
            if choice == "1":
                print_success("✓ Пользователь подтвердил успешную регистрацию Yahoo")
                return "1"
            elif choice == "2":
                print_warning("⚠️ ⚠️ Пользователь сообщил о неудачной регистрации")
                print_error("❌ ❌ Регистрация Yahoo не удалась")
                return "2"
            else:
                print_error("❌ Некорректный выбор. Введите 1 или 2.")
        except KeyboardInterrupt:
            print_warning("⚠️ Прерывание пользователем")
            return "2"
        except Exception as e:
            print_error(f"❌ Ошибка при вводе: {e}")
            return "2"

async def force_disable_automation_and_wait(page):
    """Принудительно отключает автоматизацию и ждет подтверждения пользователя"""
    try:
        print_warning("🛡️ ПРИНУДИТЕЛЬНО ОТКЛЮЧАЮ АВТОМАТИЗАЦИЮ!")
        
        # Отключаем stealth режим
        await disable_stealth_temporarily(page)
        
        # Останавливаем все автоматические действия
        print_info("⏸️ Все автоматические действия остановлены")
        print_info("🖱️ Управление передано пользователю")
        
        # Ждем подтверждения пользователя
        choice = await wait_for_user_confirmation()
        
        if choice == "1":
            print_success("✓ Пользователь подтвердил успешную регистрацию!")
            # Восстанавливаем stealth режим
            await reenable_stealth_after_recaptcha(page)
            return "1"
        else:
            print_warning("⚠️ Регистрация не удалась, прекращаю автоматизацию")
            return "2"
            
    except Exception as e:
        print_error(f"❌ Ошибка при принудительном отключении: {e}")
        return "2"

async def monitor_recaptcha_continuously(page):
    """Непрерывно мониторит reCAPTCHA и отключает автоматизацию"""
    try:
        while True:
            current_url = page.url
            if "login.yahoo.com/account/challenge/recaptcha" in current_url:
                print_warning("🛡️ ОБНАРУЖЕНА reCAPTCHA! ПРИНУДИТЕЛЬНО ОТКЛЮЧАЮ АВТОМАТИЗАЦИЮ!")
                return await force_disable_automation_and_wait(page)
            
            # Проверяем каждые 2 секунды
            await asyncio.sleep(2)
            
    except Exception as e:
        print_error(f"❌ Ошибка в мониторинге reCAPTCHA: {e}")
        return False

async def apply_ultra_aggressive_stealth(page):
    """Применяет ультра-агрессивные методы обхода детекции Yahoo"""
    try:
        print_info("🛡️ Применяю ультра-агрессивные методы обхода детекции...")
        
        # Блокируем ВСЕ скрипты детекции
        await page.add_init_script("""
            // Блокируем reCAPTCHA полностью
            window.grecaptcha = undefined;
            window.recaptcha = undefined;
            window.recaptchaReady = undefined;
            
            // Блокируем Google Analytics и все трекеры
            window.ga = undefined;
            window.gtag = undefined;
            window.dataLayer = undefined;
            window.google_tag_manager = undefined;
            
            // Блокируем все скрипты детекции
            window.fingerprint = undefined;
            window.botd = undefined;
            window.perfume = undefined;
            window.fpjs = undefined;
            
            // Скрываем ВСЕ признаки автоматизации
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // Скрываем автоматизацию в window
            Object.defineProperty(window, 'navigator', {
                get: () => ({
                    ...navigator,
                    webdriver: undefined,
                    plugins: [1, 2, 3, 4, 5],
                    languages: ['en-US', 'en'],
                    hardwareConcurrency: 8,
                    deviceMemory: 8,
                    maxTouchPoints: 0,
                    onLine: true,
                    cookieEnabled: true,
                    doNotTrack: null,
                    userAgent: navigator.userAgent.replace(/HeadlessChrome/, 'Chrome'),
                }),
                configurable: true
            });
            
            // Скрываем автоматизацию в document
            Object.defineProperty(document, 'hidden', {
                get: () => false,
                configurable: true
            });
            
            // Скрываем автоматизацию в screen
            Object.defineProperty(screen, 'width', {
                get: () => 1920,
                configurable: true
            });
            Object.defineProperty(screen, 'height', {
                get: () => 1080,
                configurable: true
            });
            Object.defineProperty(screen, 'availWidth', {
                get: () => 1920,
                configurable: true
            });
            Object.defineProperty(screen, 'availHeight', {
                get: () => 1040,
                configurable: true
            });
            
            // Блокируем детекцию мыши
            const originalMouseEvent = window.MouseEvent;
            window.MouseEvent = function(type, init) {
                if (init && init.isTrusted === false) {
                    init.isTrusted = true;
                }
                return new originalMouseEvent(type, init);
            };
            
            // Блокируем детекцию клавиатуры
            const originalKeyboardEvent = window.KeyboardEvent;
            window.KeyboardEvent = function(type, init) {
                if (init && init.isTrusted === false) {
                    init.isTrusted = true;
                }
                return new originalKeyboardEvent(type, init);
            };
            
            // Блокируем детекцию времени
            const originalDate = Date;
            Date = function(...args) {
                if (args.length === 0) {
                    return new originalDate(Date.now() + Math.random() * 100);
                }
                return new originalDate(...args);
            };
            Date.now = function() {
                return originalDate.now() + Math.random() * 100;
            };
            
            // Блокируем детекцию в performance
            Object.defineProperty(performance, 'timing', {
                get: () => ({
                    navigationStart: Date.now() - Math.random() * 1000,
                    loadEventEnd: Date.now(),
                    domContentLoadedEventEnd: Date.now() - Math.random() * 100,
                }),
                configurable: true
            });
            
            // Блокируем детекцию в console
            const originalLog = console.log;
            console.log = function(...args) {
                const text = args.join(' ');
                if (text.includes('webdriver') || text.includes('automation') || text.includes('selenium') || text.includes('recaptcha') || text.includes('bot')) {
                    return;
                }
                return originalLog.apply(console, args);
            };
            
            // Блокируем детекцию в localStorage
            const originalSetItem = Storage.prototype.setItem;
            Storage.prototype.setItem = function(key, value) {
                if (key.includes('automation') || key.includes('webdriver') || key.includes('bot')) {
                    return;
                }
                return originalSetItem.call(this, key, value);
            };
            
            // Блокируем детекцию в sessionStorage
            const originalSessionSetItem = sessionStorage.setItem;
            sessionStorage.setItem = function(key, value) {
                if (key.includes('automation') || key.includes('webdriver') || key.includes('bot')) {
                    return;
                }
                return originalSessionSetItem.call(this, key, value);
            };
            
            // Блокируем детекцию в cookies
            const originalCookie = document.cookie;
            Object.defineProperty(document, 'cookie', {
                get: function() {
                    return originalCookie;
                },
                set: function(value) {
                    if (value.includes('automation') || value.includes('webdriver') || value.includes('bot')) {
                        return;
                    }
                    originalCookie = value;
                },
                configurable: true
            });
            
            // Блокируем детекцию в fetch
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                if (url && (url.includes('recaptcha') || url.includes('captcha') || url.includes('bot'))) {
                    return Promise.resolve(new Response('{"success": true}', {
                        status: 200,
                        headers: {'Content-Type': 'application/json'}
                    }));
                }
                return originalFetch.call(this, url, options);
            };
            
            // Блокируем детекцию в XMLHttpRequest
            const originalOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
                if (url && (url.includes('recaptcha') || url.includes('captcha') || url.includes('bot'))) {
                    this.readyState = 4;
                    this.status = 200;
                    this.responseText = '{"success": true}';
                    setTimeout(() => {
                        if (this.onreadystatechange) {
                            this.onreadystatechange();
                        }
                    }, 100);
                    return;
                }
                return originalOpen.call(this, method, url, async, user, password);
            };
            
            // Блокируем детекцию в addEventListener
            const originalAddEventListener = EventTarget.prototype.addEventListener;
            EventTarget.prototype.addEventListener = function(type, listener, options) {
                if (type.includes('automation') || type.includes('bot')) {
                    return;
                }
                return originalAddEventListener.call(this, type, listener, options);
            };
            
            // Блокируем детекцию в removeEventListener
            const originalRemoveEventListener = EventTarget.prototype.removeEventListener;
            EventTarget.prototype.removeEventListener = function(type, listener, options) {
                if (type.includes('automation') || type.includes('bot')) {
                    return;
                }
                return originalRemoveEventListener.call(this, type, listener, options);
            };
            
            // Блокируем детекцию в setTimeout
            const originalSetTimeout = window.setTimeout;
            window.setTimeout = function(fn, delay, ...args) {
                const randomDelay = delay + Math.random() * 100;
                return originalSetTimeout(fn, randomDelay, ...args);
            };
            
            // Блокируем детекцию в setInterval
            const originalSetInterval = window.setInterval;
            window.setInterval = function(fn, delay, ...args) {
                const randomDelay = delay + Math.random() * 50;
                return originalSetInterval(fn, randomDelay, ...args);
            };
            
            console.log('Ultra-aggressive stealth applied');
        """)
        
        # Добавляем случайные движения мыши
        await add_random_mouse_movements(page)
        
        # Ждем случайное время
        await wait_for_human_delay(2000, 4000)
        
        print_success("✓ Ультра-агрессивные методы обхода детекции применены")
        
    except Exception as e:
        print_warning(f"⚠️ Ошибка при применении ультра-агрессивных методов: {e}")

async def disable_all_automation_completely(page):
    """
    Полностью отключает автоматизацию и ждет подтверждения от пользователя
    
    :param page: Объект страницы из Playwright
    :return: Строка "1" если пользователь подтвердил успешную регистрацию, "2" если нет
    """
    try:
        print_warning("🛡️ ПОЛНОСТЬЮ ОТКЛЮЧАЮ АВТОМАТИЗАЦИЮ!")
        
        # Отключаем stealth режим
        await disable_stealth_temporarily(page)
        
        # Ждем подтверждения от пользователя
        choice = await wait_for_user_confirmation()
        
        return choice  # Возвращаем "1" или "2" в зависимости от выбора пользователя
    except Exception as e:
        print_error(f"Ошибка при отключении автоматизации: {e}")
        return "2"

# Новая функция для открытия Bank of America в новой вкладке
async def open_bank_of_america_in_new_tab(browser, user_data):
    """
    Открывает Bank of America в новой вкладке существующего браузера
    
    :param browser: Объект браузера из Playwright
    :param user_data: Данные пользователя для автоматизации
    :return: Результат автоматизации
    """
    try:
        print_header("Открытие Bank of America в новой вкладке")
        
        # URL Bank of America - страница регистрации Advantage SafeBalance Banking
        boa_url = "https://www.bankofamerica.com/deposits/checking/advantage-safebalance-banking-account/before-you-apply/?offer_code=PSJ300CIS"
        
        # Создаем новую вкладку в том же контексте
        print_info("Создаю новую вкладку...")
        page = await browser.new_page()
        
        # Применяем улучшенный антидетект режим
        print_info("Применяю улучшенный антидетект режим...")
        await apply_advanced_stealth(page)
        
        # Переходим на страницу Bank of America
        print_info(f"Открываю URL: {boa_url}")
        await page.goto(boa_url, wait_until='networkidle', timeout=60000)
        print_success(f"Страница {boa_url} открыта успешно")
        
        # Получаем заголовок страницы
        title = await page.title()
        print_info(f"Заголовок страницы: {title}")
        
        # Bank of America автоматизация отключена по запросу пользователя
        print_info("Bank of America автоматизация отключена")
        registration_result = {"success": False, "disabled": True}
        
        return registration_result
    except Exception as e:
        print_error(f"Ошибка при открытии Bank of America в новой вкладке: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}