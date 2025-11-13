import os
import subprocess
import tempfile
import urllib.request
import zipfile
import sys
import shutil

# 🔗 Прямая ссылка на архив (Dropbox)
APP_URL = "https://www.dropbox.com/scl/fi/mp1s1mppfofx0odrizjer/zip.zip?rlkey=yppoysk0bsczbeqx4q417x5eh&st=wfrjb215&dl=1"

# 📦 Зависимости
REQUIREMENTS = [
    "asyncio>=3.4.3",
    "aiohttp>=3.8.4",
    "httpx>=0.24.1",
    "requests>=2.28.2",
    "colorama>=0.4.6",
    "telethon>=1.28.5",
    "aiogram>=2.25.1",
    "cryptography>=41.0.3",
    "playwright>=1.38.0",
    "playwright-stealth>=1.0.5",
    "pyppeteer>=1.0.2",
    "psutil>=5.9.5",
    "python-dotenv>=1.0.0",
]

# 📁 Временная папка
temp_dir = tempfile.mkdtemp()

def is_python_installed():
    try:
        # Проверяем обе команды: python и py (на Windows)
        subprocess.check_output(["python", "--version"], stderr=subprocess.STDOUT)
        return True, "python"
    except:
        try:
            subprocess.check_output(["py", "--version"], stderr=subprocess.STDOUT)
            return True, "py"
        except:
            return False, None

def download_and_install_python():
    print("⏬ Скачиваем Python...")
    python_url = "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
    installer_path = os.path.join(temp_dir, "python-installer.exe")
    urllib.request.urlretrieve(python_url, installer_path)
    
    print("⚙️ Устанавливаем Python...")
    subprocess.run([installer_path, "/quiet", "InstallAllUsers=1", "PrependPath=1"], check=True)

def download_app():
    print("⏬ Скачиваем архив приложения...")
    app_path = os.path.join(temp_dir, "app.zip")
    try:
        urllib.request.urlretrieve(APP_URL, app_path)
        with zipfile.ZipFile(app_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        return True
    except Exception as e:
        print(f"❌ Ошибка при скачивании или распаковке: {e}")
        return False

def install_requirements(python_exec):
    print("📦 Устанавливаем pip и зависимости...")
    try:
        subprocess.run([python_exec, "-m", "ensurepip", "--upgrade"], check=True)
        subprocess.run([python_exec, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
        
        for pkg in REQUIREMENTS:
            print(f"📦 Устанавливаем: {pkg}")
            subprocess.run([python_exec, "-m", "pip", "install", pkg], check=True)

        # playwright browser install (важно!)
        subprocess.run([python_exec, "-m", "playwright", "install", "--with-deps"], check=True)
        return True
    except Exception as e:
        print(f"❌ Ошибка при установке зависимостей: {e}")
        return False

def find_main_py(root):
    for dirpath, _, filenames in os.walk(root):
        if "main.py" in filenames:
            return os.path.join(dirpath, "main.py")
    return None

def run_app(python_exec):
    main_path = find_main_py(temp_dir)
    if not main_path:
        print("❌ main.py не найден!")
        input("Нажмите Enter для выхода...")
        return

    print(f"🚀 Запускаем {main_path}...\n")
    # Запускаем приложение в интерактивном режиме
    try:
        subprocess.run([python_exec, main_path])
    except KeyboardInterrupt:
        print("\n⛔ Приложение остановлено пользователем.")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске приложения: {e}")
    
    input("\nНажмите Enter для выхода...")

# === Основной блок ===
try:
    print("🔍 Проверяем установку Python...")
    python_installed, python_exec = is_python_installed()
    if not python_installed:
        print("❌ Python не обнаружен, начинаем установку...")
        download_and_install_python()
        # После установки Python, проверяем снова
        python_installed, python_exec = is_python_installed()
        if not python_installed:
            print("❌ Не удалось установить Python! Нажмите Enter для выхода...")
            input()
            sys.exit(1)
    
    print(f"✅ Python обнаружен: {python_exec}")
    
    # Создаём новую директорию для приложения в текущей папке
    app_dir = os.path.join(os.getcwd(), "autoinator_app")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    
    if not download_app():
        input("❌ Не удалось скачать приложение. Нажмите Enter для выхода...")
        sys.exit(1)
    
    if not install_requirements(python_exec):
        input("❌ Не удалось установить зависимости. Нажмите Enter для выхода...")
        sys.exit(1)
    
    run_app(python_exec)

finally:
    print("🧹 Удаляем временные файлы...")
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Не удалось удалить временные файлы: {e}")
