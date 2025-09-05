from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar, QLineEdit, QPushButton, QSizePolicy
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtNetwork import QNetworkCookie, QNetworkProxy
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from PyQt6.QtCore import QUrl
from http.cookies import SimpleCookie
import json
import urllib.parse
import sys
import os
import subprocess
import platform
import base64
import time


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


class CustomUserAgentInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, user_agent, parent=None):
        super().__init__(parent)
        self.user_agent = user_agent

    def interceptRequest(self, info):
        info.setHttpHeader(b"User-Agent", self.user_agent.encode())
        

class AutoTraderApp(QMainWindow):
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    #USER_AGENT = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/6.9.1 Chrome/130.0.0.0 Safari/537.36"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoTrader")
        self.setGeometry(100, 100, 800, 600)
        # --- Создание и настройка панели инструментов ---
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False) # Фиксируем панель
        self.addToolBar(self.toolbar)

        # --- Поле ввода URL ---
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Введите URL и нажмите Enter...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)

        # --- Кнопки закладок ---
        self.toolbar.addSeparator() # Разделитель

        btn_steam_inv = QPushButton("Steam (Инвентарь)")
        btn_steam_inv.clicked.connect(lambda: self.load_bookmark_url("https://steamcommunity.com/my/inventory/"))
        self.toolbar.addWidget(btn_steam_inv)

        btn_steam_market = QPushButton("Steam (ТП)")
        btn_steam_market.clicked.connect(lambda: self.load_bookmark_url("https://steamcommunity.com/market/"))
        self.toolbar.addWidget(btn_steam_market)

        btn_tm = QPushButton("TM")
        btn_tm.clicked.connect(lambda: self.load_bookmark_url("https://market.csgo.com/"))
        self.toolbar.addWidget(btn_tm)

        btn_buff = QPushButton("Buff")
        btn_buff.clicked.connect(lambda: self.load_bookmark_url("https://buff.163.com/"))
        self.toolbar.addWidget(btn_buff)

        # --- Веб-браузер ---
        self.profile = QWebEngineProfile.defaultProfile()
        self.interceptor = CustomUserAgentInterceptor(self.USER_AGENT, self)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.profile.setHttpUserAgent(self.USER_AGENT)
        self.browser = QWebEngineView(self.profile)
        self.cookie_store = self.profile.cookieStore()
        
        # Обновляем URL бар при переходе по страницам
        self.browser.urlChanged.connect(self.update_url_bar)

        self.setCentralWidget(self.browser)

        self.cookies = None
        self.proxy = None
        self.host = None
        self.target_url = None
        
    def update_url_bar(self, qurl: QUrl):
        """Обновляет текст в поле URL при изменении адреса страницы"""
        self.url_bar.setText(qurl.toString())
        self.url_bar.setCursorPosition(0) # Ставим курсор в начало

    def navigate_to_url(self):
        """Загружает страницу по адресу из поля ввода"""
        url = self.url_bar.text()
        if url:
            # Если URL не содержит схемы, добавляем https://
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            self.browser.load(QUrl(url))

    def load_bookmark_url(self, url: str):
        """Загружает заданный URL из закладки"""
        self.browser.load(QUrl(url))
        # URL бар обновится сам через сигнал urlChanged
        
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

            proxy = query_params.get('proxy', [None])[0]
            
            # Формируем целевой URL
            target_url = f"https://{parsed.netloc}{parsed.path}"
            target_url = target_url.replace("https://https://", "https://")
            return target_url, parsed.hostname, cookies, proxy
        except Exception as e:
            raise e
            print(f"Error parsing URL: {e}")
            return 'https://market.csgo.com', None
    
    def set_cookies(self):
        """Установка куков после загрузки страницы"""
        sc = SimpleCookie()
        for key, data in self.cookies.items():
            domain, value = data["domain"], data["value"]
            value = value.replace(" ", "+")
            #if "csgo.com" in domain or "dota2.net" in domain:
            #    continue
            sc[key] = base64.b64decode(value.encode()).decode()

            if domain.count(".") > 1:
                domain = "." + domain.split(".", 1)[1]
                
            sameSite = None
            if key == "d2mid":
                sameSite = "Lax"
            sc[key]['samesite'] = None
            sc[key]['secure'] = not bool(sameSite)
            sc[key]['httponly'] = True
            sc[key]['domain'] = domain

        contents = sc.output().encode('ascii')
        contents = contents.replace(b"Set-Cookie: ", b"")
        self.cookie_store.deleteAllCookies()
        for qt_cookie in QNetworkCookie.parseCookies(contents):
            self.cookie_store.setCookie(qt_cookie)#, QUrl(self.target_url))

    def set_proxy(self):
        scheme, addr = self.proxy.split("://")
        auth, addr = addr.split("@")
        user, password = auth.split(":")
        host, port = addr.split(":")

        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
        proxy.setHostName(host)
        proxy.setPort(int(port))
        proxy.setUser(user)
        proxy.setPassword(password)

        QNetworkProxy.setApplicationProxy(proxy)
        
    
    def start_app(self, initial_url=None):
        """Запуск приложения"""
        if initial_url and initial_url.startswith('autotrader://'):
            self.target_url, self.host, self.cookies, self.proxy = self.parse_custom_url(initial_url)
        else:
            self.target_url = 'https://market.csgo.com'
            self.cookies = None
            self.host = None

        self.set_cookies()
        #self.target_url = "http://127.0.0.1:8000"
        self.set_proxy()
        self.browser.load(QUrl(self.target_url))

        
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
    chromium_args = [
        f'--user-agent={AutoTraderApp.USER_AGENT}',
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-features=WebRtcHideLocalIpsWithMdns'  # Дополнительно для маскировки
    ]
    if len(sys.argv) > 1:
        for argv in sys.argv:
            if argv.startswith('autotrader://'):
                # Запуск с URL-схемой
                app = QApplication(["AutoTraderApp"] + chromium_args)
                window = AutoTraderApp()
                window.start_app(argv)
                window.show()
                app.exec()
                return

    # Установка обработчика URL-схемы
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
