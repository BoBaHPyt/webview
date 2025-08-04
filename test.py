import webview
import json
import urllib.parse
import sys
import os
import subprocess
import platform

class AutoTraderInstaller:
    def __init__(self):
        # Определяем путь к исполняемому файлу
        if getattr(sys, 'frozen', False):
            # Запущено как скомпилированный exe/pyinstaller
            self.executable_path = sys.executable
        else:
            # Запущено как Python скрипт
            self.executable_path = f'python3 "{os.path.abspath(sys.argv[0])}"' if platform.system() != 'Windows' else f'python "{os.path.abspath(sys.argv[0])}"'
        
        self.app_name = "AutoTrader"
        self.scheme = "autotrader"
        
    def is_frozen(self):
        """Проверяет, запущено ли приложение как скомпилированный файл"""
        return getattr(sys, 'frozen', False)
    
    def get_executable_command(self):
        """Возвращает команду для запуска приложения"""
        if self.is_frozen():
            # Для скомпилированного приложения
            return f'"{sys.executable}"' if ' ' in sys.executable else sys.executable
        else:
            # Для Python скрипта
            python_cmd = 'python' if platform.system() == 'Windows' else 'python3'
            return f'{python_cmd} {os.path.abspath(sys.argv[0])}'

class LinuxInstaller(AutoTraderInstaller):
    def __init__(self):
        super().__init__()
        self.desktop_dir = os.path.expanduser('~/.local/share/applications')
        self.desktop_file = os.path.join(self.desktop_dir, f'{self.scheme}.desktop')
    
    def create_desktop_file(self):
        """Создание .desktop файла для Linux"""
        desktop_content = f"""[Desktop Entry]
Name={self.app_name}
Exec={self.get_executable_command()} %u
Icon=web-browser
Terminal=false
Type=Application
MimeType=x-scheme-handler/{self.scheme};
StartupNotify=true
Categories=Network;WebBrowser;
"""
        
        # Создаем директорию если её нет
        os.makedirs(self.desktop_dir, exist_ok=True)
        
        # Записываем .desktop файл
        with open(self.desktop_file, 'w') as f:
            f.write(desktop_content)
        
        # Делаем файл исполняемым
        os.chmod(self.desktop_file, 0o755)
        
        return self.desktop_file
    
    def register_scheme_handler(self):
        """Регистрация обработчика URL-схемы"""
        try:
            # Регистрируем MIME тип
            subprocess.run(['xdg-mime', 'default', f'{self.scheme}.desktop', f'x-scheme-handler/{self.scheme}'], 
                          check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def update_desktop_database(self):
        """Обновление базы данных desktop файлов"""
        try:
            subprocess.run(['update-desktop-database', self.desktop_dir], 
                          check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # update-desktop-database может не быть установлен
            return True  # Продолжаем даже если команда не найдена
    
    def install(self):
        """Полная установка для Linux"""
        try:
            desktop_file = self.create_desktop_file()
            self.register_scheme_handler()
            self.update_desktop_database()
            
            print(f"✅ URL scheme handler installed for Linux!")
            print(f"📁 Desktop file: {desktop_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to install on Linux: {e}")
            return False

        
class WindowsInstaller(AutoTraderInstaller):
    def __init__(self):
        super().__init__()
        import winreg
        self.winreg = winreg
    
    def register_url_scheme(self):
        """Регистрация URL-схемы в реестре Windows"""
        try:
            # Путь к реестру для URL-схем
            key_path = f"Software\\Classes\\{self.scheme}"
            
            # Создаем основной ключ
            with self.winreg.CreateKey(self.winreg.HKEY_CURRENT_USER, key_path) as key:
                self.winreg.SetValue(key, "", self.winreg.REG_SZ, f"URL:{self.app_name} Protocol")
                self.winreg.SetValueEx(key, "URL Protocol", 0, self.winreg.REG_SZ, "")
            
            # Создаем ключ для команды
            command_path = key_path + "\\shell\\open\\command"
            with self.winreg.CreateKey(self.winreg.HKEY_CURRENT_USER, command_path) as key:
                command = f'"{self.get_executable_command()}" "%1"'
                self.winreg.SetValue(key, "", self.winreg.REG_SZ, command)
                
            return True
        except Exception as e:
            print(f"Registry error: {e}")
            return False
    
    def install(self):
        """Полная установка для Windows"""
        try:
            if self.register_url_scheme():
                print(f"✅ URL scheme handler installed for Windows!")
                print(f"🔧 Command: {self.get_executable_command()} \"%1\"")
                return True
            else:
                print("❌ Failed to register URL scheme in Windows registry")
                return False
        except Exception as e:
            print(f"❌ Failed to install on Windows: {e}")
            return False

        
class AutoTraderApp:
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    
    def __init__(self):
        self.window = None
        self.cookies = None
        self.target_url = None
        
    def parse_custom_url(self, url):
        """Парсинг кастомного URL"""
        if not url.startswith('autotrader://'):
            return url, None
            
        try:
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # Получаем куки
            cookies = query_params.get('cookies', [None])[0]
            if cookies:
                cookies = json.loads(cookies)
            
            # Формируем целевой URL
            target_url = f"https://{parsed.netloc}{parsed.path}"
            target_url = target_url.replace("https://https://", "https://")
            
            return target_url, cookies
        except Exception as e:
            print(f"Error parsing URL: {e}")
            return 'https://market.csgo.com', None
    
    def set_cookies(self):
        """Установка куков после загрузки страницы"""
        if self.cookies:
            for cookie in self.window.get_cookies():
                for cookie in cookie.values():
                    if self.cookies.get(cookie.key) == cookie.value:
                        del self.cookies[cookie.key]
            if self.cookies:
                js_code = ""
                for key, value in self.cookies.items():
                    js_code += f'document.cookie = "{key}={value}";'
                self.window.clear_cookies()
                self.window.evaluate_js(js_code)
                self.window.load_url(f"{self.target_url}?1")
    
    def start_app(self, initial_url=None):
        """Запуск приложения"""
        if initial_url and initial_url.startswith('autotrader://'):
            self.target_url, self.cookies = self.parse_custom_url(initial_url)
        else:
            self.target_url = 'https://market.csgo.com'
            self.cookies = None
        
        self.window = webview.create_window('AutoTrader App', self.target_url)
        
        if self.cookies:
            self.window.events.loaded += self.set_cookies
        
        webview.start(user_agent=self.USER_AGENT, ssl=True)

def get_installer():
    """Получение инсталлера для текущей ОС"""
    system = platform.system().lower()
    if system == 'linux':
        return LinuxInstaller()
    elif system == 'windows':
        return WindowsInstaller()
    else:
        raise NotImplementedError(f"Installation not supported for {system}")

def main():
    """Основная функция приложения"""
    # Проверяем команды установки
    if len(sys.argv) > 1:
        for argv in sys.argv:
            if argv.startswith('autotrader://'):
                # Запуск с URL-схемой
                app = AutoTraderApp()
                app.start_app(sys.argv[1])
                return
    try:
        installer = get_installer()
        if installer.install():
            print("🎉 Installation completed successfully!")
        else:
            print("⚠️  Installation completed with warnings.")
        return
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return

if __name__ == '__main__':
    main()
