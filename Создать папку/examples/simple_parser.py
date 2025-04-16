import time
import random
import json
import os
import sqlite3
from datetime import datetime
import logging
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

class SimpleParser:
    def __init__(self, headless=False):
        self.results_dir = "results"
        self.screenshots_dir = "debug_screenshots"
        self.logs_dir = "logs"
        self.db_path = "parser_data.db"
        
        # Создаем все необходимые директории
        for directory in [self.results_dir, self.screenshots_dir, self.logs_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Создана директория: {directory}")
        
        self.setup_logging()
        self.setup_database()
        self.driver = None
        self.headless = headless
        
        # ... existing code ...

    def setup_logging(self):
        """Настройка расширенного логирования"""
        # Очищаем все существующие обработчики
        logging.getLogger().handlers = []
        
        # Настраиваем формат
        log_format = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        formatter = logging.Formatter(log_format)
        
        # Настраиваем файловый handler
        log_file = os.path.join(self.logs_dir, 'parser_debug.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Настраиваем консольный handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Настраиваем корневой logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Создаем и настраиваем logger для класса
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Включаем логирование Selenium
        selenium_logger = logging.getLogger('selenium')
        selenium_logger.setLevel(logging.DEBUG)
        
        # Включаем логирование urllib3
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.DEBUG)
        
        self.logger.debug("Логирование инициализировано")

    def setup_database(self):
        """Инициализация базы данных SQLite"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Создаем таблицу для хранения URL если её нет
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS parsed_urls (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    snippet TEXT,
                    query TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            self.logger.info("База данных инициализирована")
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации базы данных: {str(e)}")

    def is_url_parsed(self, url):
        """Проверяет, был ли URL уже обработан"""
        try:
            self.cursor.execute('SELECT url FROM parsed_urls WHERE url = ?', (url,))
            return bool(self.cursor.fetchone())
        except Exception as e:
            self.logger.warning(f"Ошибка при проверке URL в базе: {str(e)}")
            return False

    def save_to_database(self, result, query):
        """Сохраняет результат в базу данных"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO parsed_urls (url, title, snippet, query, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (result['url'], result['title'], result.get('snippet', ''), query))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.warning(f"Ошибка при сохранении в базу данных: {str(e)}")
            return False

    def extract_results_xpath(self):
        """Извлекает результаты поиска с помощью XPath"""
        results = []
        try:
            # ... existing code until the result processing ...
            
            # Перебираем каждый результат
            for result in search_results:
                try:
                    # ... existing code until result extraction ...
                    
                    if title and url and not url.startswith('https://www.google.com'):
                        # Проверяем, не обрабатывали ли мы уже этот URL
                        if not self.is_url_parsed(url):
                            result_data = {
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            }
                            
                            # Проверяем на дубликаты в текущих результатах
                            if not any(r['url'] == url for r in results):
                                results.append(result_data)
                                self.logger.info(f"Добавлен новый результат: {title}")
                        else:
                            self.logger.info(f"Пропущен уже обработанный URL: {url}")
                            
                except Exception as e:
                    continue
            
            self.logger.info(f"Успешно извлечено {len(results)} новых результатов")
            
        except Exception as e:
            self.logger.warning(f"Ошибка при извлечении результатов: {str(e)}")
            
        return results

    def handle_location_dialog(self, driver):
        """Закрывает диалоги геолокации и cookie различными способами."""
        self.logger.debug("Попытка закрыть диалоги")
        
        # Список селекторов для кнопок
        button_selectors = [
            ("xpath", "//button[contains(text(), 'Не сейчас')]"),
            ("xpath", "//button[contains(text(), 'Not now')]"),
            ("xpath", "//button[contains(text(), 'Reject all')]"),
            ("xpath", "//button[contains(text(), 'Отклонить все')]"),
            ("css selector", "button#W0wltc"),  # Кнопка "Отклонить все" по ID
            ("css selector", "button.tHlp8d"),  # Общий класс для кнопок Google
        ]
        
        for by, selector in button_selectors:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                button.click()
                self.logger.debug(f"Успешно нажата кнопка: {selector}")
                time.sleep(1)  # Небольшая пауза после нажатия
                return True
            except:
                continue
        
        # Если кнопки не найдены, пробуем JavaScript
        try:
            driver.execute_script("""
            // Отключаем геолокацию
            navigator.geolocation = undefined;
            
            // Удаляем возможные оверлеи
            document.querySelectorAll('[role="dialog"]').forEach(e => e.remove());
            document.querySelectorAll('.modal').forEach(e => e.remove());
            """)
            self.logger.debug("Применен JavaScript для закрытия диалогов")
            return True
        except:
            self.logger.debug("Не удалось закрыть диалоги")
            return False

    def search_google(self, query: str, num_pages: int = 10) -> List[Dict[str, str]]:
        """Выполняет поиск в Google и возвращает результаты."""
        try:
            self.logger.debug(f"Начало поиска. Запрос: {query}, Страниц: {num_pages}")
            if not self.driver:
                self.logger.error("Не удалось инициализировать браузер")
                return []

            # Открываем Google с повторными попытками
            for attempt in range(3):
                try:
                    self.logger.debug(f"Попытка {attempt + 1} открыть Google")
                    self.driver.get("https://www.google.com")
                    
                    # Ждем загрузки страницы
                    WebDriverWait(self.driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") in ["complete", "interactive"]
                    )
                    self.logger.debug(f"Состояние страницы: {self.driver.execute_script('return document.readyState')}")
                    
                    # Проверяем, что мы действительно на Google
                    self.logger.debug("Проверка элементов на странице:")
                    self.logger.debug(f"Title: {self.driver.title}")
                    self.logger.debug(f"URL: {self.driver.current_url}")
                    
                    if "google" in self.driver.current_url.lower():
                        break
                except Exception as e:
                    self.logger.error(f"Ошибка при открытии Google (попытка {attempt + 1}): {str(e)}")
                    if attempt == 2:  # Последняя попытка
                        raise
                    time.sleep(5)

            # Закрываем диалоги перед поиском
            self.handle_location_dialog(self.driver)

            # Ищем и заполняем поле поиска
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            
            # Снова закрываем возможные диалоги после поиска
            self.handle_location_dialog(self.driver)

            # Ждем загрузку результатов
            self.logger.debug("Ожидание загрузки результатов")
            time.sleep(5)
            
            # Обрабатываем каждую страницу
            results = []
            for page in range(num_pages):
                try:
                    self.logger.debug(f"Обработка страницы {page + 1}")
                    
                    # Ждем результаты поиска
                    self.logger.debug("Ожидание блока результатов")
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.ID, "search"))
                    )
                    
                    # Проверяем наличие капчи
                    if "sorry/index" in self.driver.current_url or "sorry.google.com" in self.driver.current_url:
                        self.logger.error("Обнаружена капча!")
                        break
                    
                    self.logger.debug("Ожидание полной загрузки результатов")
                    time.sleep(3)
                    
                    # Делаем скриншот
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"{self.screenshots_dir}/search_{query}_{page+1}_{timestamp}.png"
                    self.driver.save_screenshot(screenshot_path)
                    self.logger.debug(f"Сохранен скриншот: {screenshot_path}")
                    
                    # Получаем HTML страницы для отладки
                    page_source = self.driver.page_source
                    with open(f"logs/page_{page+1}_{timestamp}.html", "w", encoding="utf-8") as f:
                        f.write(page_source)
                    self.logger.debug(f"Сохранен HTML страницы {page + 1}")
                    
                    # Извлекаем результаты
                    search_results = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
                    self.logger.debug(f"Найдено {len(search_results)} блоков результатов")
                    
                    page_results = []
                    for idx, result in enumerate(search_results, 1):
                        try:
                            self.logger.debug(f"Обработка результата {idx}")
                            
                            # Извлекаем компоненты результата
                            title_element = result.find_element(By.CSS_SELECTOR, "h3")
                            link_element = result.find_element(By.CSS_SELECTOR, "a")
                            snippet_element = result.find_element(By.CSS_SELECTOR, "div.VwiC3b")
                            
                            result_data = {
                                "title": title_element.text,
                                "url": link_element.get_attribute("href"),
                                "snippet": snippet_element.text if snippet_element else ""
                            }
                            
                            self.logger.debug(f"Извлечен результат: {result_data['title'][:30]}...")
                            
                            if result_data["url"] and not result_data["url"].startswith("https://www.google.com"):
                                page_results.append(result_data)
                                
                        except Exception as e:
                            self.logger.warning(f"Ошибка при извлечении результата {idx}: {str(e)}", exc_info=True)
                            continue
                    
                    results.extend(page_results)
                    self.logger.info(f"Найдено {len(page_results)} результатов на странице {page + 1}")
                    
                    # Сохраняем промежуточные результаты
                    self._save_results(query, results)
                    
                    # Переход на следующую страницу
                    if page < num_pages - 1:
                        self.logger.debug("Поиск кнопки 'Следующая'")
                        next_button = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.ID, "pnnext"))
                        )
                        self.logger.debug("Клик по кнопке 'Следующая'")
                        self.driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(5)
                    
                except TimeoutException as e:
                    self.logger.error(f"Таймаут при обработке страницы {page + 1}: {str(e)}", exc_info=True)
                    break
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке страницы {page + 1}: {str(e)}", exc_info=True)
                    break
            
            return results
        
        except Exception as e:
            self.logger.error(f"Критическая ошибка при поиске: {str(e)}", exc_info=True)
            return []

    def _save_results(self, query: str, results: List[Dict]):
        """Сохраняет результаты в JSON файл"""
        try:
            if results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.results_dir}/results_{query}_{timestamp}.json"
                
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"Сохранено {len(results)} результатов в {filename}")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении результатов: {e}")

    def handle_dialogs(self):
        """Закрывает все возможные диалоговые окна"""
        try:
            # Список селекторов для кнопок закрытия диалогов
            dialog_buttons = [
                (By.XPATH, "//button[contains(text(), 'Не сейчас')]"),
                (By.XPATH, "//button[contains(text(), 'Not now')]"),
                (By.XPATH, "//button[contains(text(), 'Reject all')]"),
                (By.XPATH, "//button[contains(text(), 'Отклонить все')]"),
            ]
            
            for by, selector in dialog_buttons:
                try:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    button.click()
                    time.sleep(1)
                except:
                    continue
            
            # Закрываем диалоги через JavaScript
            self.driver.execute_script("""
                var dialogs = document.querySelectorAll('div[role="dialog"]');
                dialogs.forEach(function(dialog) {
                    dialog.remove();
                });
                
                var overlays = document.querySelectorAll('div[aria-modal="true"]');
                overlays.forEach(function(overlay) {
                    overlay.remove();
                });
            """)
            
        except Exception as e:
            self.logger.warning(f"Ошибка при закрытии диалогов: {str(e)}")

    def close(self):
        """Close the browser and database connection"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Браузер закрыт")
        
        if hasattr(self, 'conn'):
            self.conn.close()
            self.logger.info("Соединение с базой данных закрыто")

    def initialize(self):
        try:
            self.logger.debug("Начало инициализации браузера")
            
            # Создаем объект опций
            options = Options()
            options.page_load_strategy = 'eager'  # Ускоряем загрузку страниц
            
            # Основные опции безопасности
            chrome_options = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080',
                '--disable-notifications',
                '--disable-popup-blocking',
                '--disable-infobars',
                '--ignore-certificate-errors',
                '--disable-extensions'
            ]
            
            if self.headless:
                chrome_options.extend([
                    '--headless=new',
                    '--disable-gpu',
                    '--disable-software-rasterizer'
                ])
            
            for option in chrome_options:
                options.add_argument(option)
                self.logger.debug(f"Добавлена опция Chrome: {option}")
            
            # Установка фиксированного User-Agent
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            options.add_argument(f'--user-agent={user_agent}')
            self.logger.debug(f"Установлен User-Agent: {user_agent}")
            
            # Добавляем prefs для улучшения производительности
            prefs = {
                'profile.default_content_setting_values.notifications': 2,
                'profile.default_content_settings.popups': 0,
                'profile.password_manager_enabled': False,
                'credentials_enable_service': False,
                'profile.managed_default_content_settings.images': 1,
                'profile.default_content_setting_values.cookies': 1
            }
            options.add_experimental_option('prefs', prefs)
            
            # Скрываем автоматизацию
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.logger.debug("Создание экземпляра Chrome")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=service,
                options=options
            )
            
            # Увеличиваем таймауты
            self.driver.set_page_load_timeout(120)
            self.driver.implicitly_wait(20)
            self.logger.debug("Установлены таймауты: page_load=120s, implicit_wait=20s")
            
            # Устанавливаем размер окна
            self.driver.set_window_size(1920, 1080)
            self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width': 1920,
                'height': 1080,
                'deviceScaleFactor': 1,
                'mobile': False
            })
            self.logger.debug("Установлен размер окна: 1920x1080")
            
            # Отключаем геолокацию через CDP
            geo_params = {
                'latitude': 55.7558,
                'longitude': 37.6173,
                'accuracy': 100
            }
            self.driver.execute_cdp_cmd('Emulation.setGeolocationOverride', geo_params)
            self.logger.debug(f"Установлена геолокация: {geo_params}")
            
            # Расширенный скрипт для обхода обнаружения
            stealth_script = """
                // Скрываем webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Эмулируем плагины
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        }
                    ]
                });
                
                // Эмулируем window.chrome
                window.chrome = {
                    app: {
                        isInstalled: false,
                        InstallState: {
                            DISABLED: 'DISABLED',
                            INSTALLED: 'INSTALLED',
                            NOT_INSTALLED: 'NOT_INSTALLED'
                        },
                        RunningState: {
                            CANNOT_RUN: 'CANNOT_RUN',
                            READY_TO_RUN: 'READY_TO_RUN',
                            RUNNING: 'RUNNING'
                        }
                    },
                    runtime: {
                        OnInstalledReason: {
                            CHROME_UPDATE: 'chrome_update',
                            INSTALL: 'install',
                            SHARED_MODULE_UPDATE: 'shared_module_update',
                            UPDATE: 'update'
                        },
                        OnRestartRequiredReason: {
                            APP_UPDATE: 'app_update',
                            OS_UPDATE: 'os_update',
                            PERIODIC: 'periodic'
                        },
                        PlatformArch: {
                            ARM: 'arm',
                            ARM64: 'arm64',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformNaclArch: {
                            ARM: 'arm',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformOs: {
                            ANDROID: 'android',
                            CROS: 'cros',
                            LINUX: 'linux',
                            MAC: 'mac',
                            OPENBSD: 'openbsd',
                            WIN: 'win'
                        },
                        RequestUpdateCheckStatus: {
                            NO_UPDATE: 'no_update',
                            THROTTLED: 'throttled',
                            UPDATE_AVAILABLE: 'update_available'
                        }
                    }
                };
                
                // Эмулируем языки
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
                
                // Эмулируем платформу
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                
                // Эмулируем разрешение экрана
                Object.defineProperty(screen, 'width', { get: () => 1920 });
                Object.defineProperty(screen, 'height', { get: () => 1080 });
                Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
                Object.defineProperty(screen, 'availHeight', { get: () => 1080 });
                Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
                Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
            """
            self.driver.execute_script(stealth_script)
            self.logger.debug("Применен расширенный скрипт обхода обнаружения")
            
            # Проверяем успешность инициализации
            self.logger.info("Браузер успешно инициализирован")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации браузера: {str(e)}", exc_info=True)
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            return False

def main():
    parser = SimpleParser(headless=True)
    try:
        parser.initialize()
        results = parser.search_google("кирпич", num_pages=10)
        print(f"Найдено новых результатов: {len(results)}")
        
        # Выводим первые 5 результатов
        for i, result in enumerate(results[:5], 1):
            print(f"\nРезультат {i}:")
            print(f"Заголовок: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Описание: {result['snippet'][:100]}...")
            
    finally:
        parser.close()

if __name__ == "__main__":
    main() 