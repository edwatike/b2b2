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
import undetected_chromedriver as uc
import threading
from concurrent.futures import ThreadPoolExecutor

class SimpleParser:
    def __init__(self, headless=False, parallel=False, num_browsers=2):
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
        self.parallel = parallel
        self.num_browsers = num_browsers
        self.all_results = []
        self.results_lock = threading.Lock()
        
        # Список городов России для эмуляции геолокации
        self.cities = [
            {"lat": 55.7558, "lng": 37.6173, "accuracy": 100},  # Москва
            {"lat": 59.9343, "lng": 30.3351, "accuracy": 100},  # Санкт-Петербург
            {"lat": 56.8519, "lng": 60.6122, "accuracy": 100},  # Екатеринбург
            {"lat": 55.0415, "lng": 82.9346, "accuracy": 100},  # Новосибирск
            {"lat": 58.5213, "lng": 31.2718, "accuracy": 100},  # Великий Новгород
        ]

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

    def set_random_geolocation(self):
        """Устанавливает случайную геолокацию из списка городов"""
        location = random.choice(self.cities)
        self.logger.info(f"Устанавливаем геолокацию: {location}")
        
        params = {
            "latitude": location["lat"],
            "longitude": location["lng"],
            "accuracy": location["accuracy"]
        }
        
        self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", params)

    def initialize(self, browser_id=0):
        """Initialize the Chrome driver with anti-detection measures"""
        options = uc.ChromeOptions()
        
        # Основные настройки для обхода блокировок
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-geolocation')
        options.add_argument('--no-sandbox')
        options.add_argument('--start-maximized')
        
        # Эмуляция реального браузера
        options.add_argument('--enable-javascript')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=ru-RU,ru')
        
        # Отключаем WebRTC для предотвращения утечки IP
        options.add_argument('--disable-webrtc')
        
        # Случайный User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Инициализируем драйвер
        self.driver = uc.Chrome(options=options)
        
        # Устанавливаем размер окна
        self.driver.set_window_size(1920, 1080)
        
        # Отключаем WebDriver через JavaScript
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Эмулируем плагины
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Эмулируем языки
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
                
                // Скрываем что это автоматизация
                window.chrome = {
                    runtime: {}
                };
            '''
        })
        
        # Устанавливаем случайную геолокацию
        self.set_random_geolocation()
        
        self.logger.info(f"Браузер {browser_id} инициализирован")

    def smooth_move_to_element(self, element):
        """Плавное перемещение курсора к элементу"""
        try:
            action = ActionChains(self.driver)
            # Получаем текущее положение курсора
            current_pos = self.driver.execute_script("return [window.screenX, window.screenY]")
            
            # Получаем положение элемента
            element_pos = element.location
            
            # Делаем несколько промежуточных шагов
            steps = 10
            for i in range(steps):
                x = current_pos[0] + (element_pos['x'] - current_pos[0]) * (i / steps)
                y = current_pos[1] + (element_pos['y'] - current_pos[1]) * (i / steps)
                action.move_by_offset(x, y)
                action.pause(random.uniform(0.1, 0.3))
            
            action.move_to_element(element)
            action.pause(random.uniform(0.2, 0.5))
            action.perform()
            return True
        except Exception as e:
            self.logger.warning(f"Ошибка при движении мыши: {str(e)}")
            return False

    def scroll_to_element(self, element):
        """Плавная прокрутка к элементу"""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                element
            )
            time.sleep(random.uniform(0.5, 1))
            return True
        except Exception as e:
            self.logger.warning(f"Ошибка при прокрутке: {str(e)}")
            return False

    def extract_results_xpath(self):
        """Извлекает результаты поиска с помощью XPath"""
        results = []
        try:
            # Ждем появления результатов поиска
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
            )
            
            # Делаем паузу для полной загрузки
            time.sleep(0.2)
            
            # Получаем все блоки с результатами
            search_results = self.driver.find_elements(By.CSS_SELECTOR, "#rso > div, #search .g")
            
            if not search_results:
                self.logger.warning("Не найдены результаты через основной селектор")
                return results
                
            self.logger.info(f"Найдено {len(search_results)} блоков с результатами")
            
            # Перебираем каждый результат
            for result in search_results:
                try:
                    # Ищем заголовок и ссылку разными способами
                    title_element = None
                    link_element = None
                    
                    # Способ 1
                    try:
                        link_element = result.find_element(By.CSS_SELECTOR, "a")
                        title_element = result.find_element(By.CSS_SELECTOR, "h3")
                    except:
                        pass
                    
                    # Способ 2
                    if not (title_element and link_element):
                        try:
                            link_element = result.find_element(By.CSS_SELECTOR, "div.yuRUbf > a")
                            title_element = link_element.find_element(By.CSS_SELECTOR, "h3")
                        except:
                            pass
                    
                    # Способ 3
                    if not (title_element and link_element):
                        try:
                            link_element = result.find_element(By.CSS_SELECTOR, "div[data-header-feature] a")
                            title_element = result.find_element(By.CSS_SELECTOR, "div[role='heading']")
                        except:
                            pass
                    
                    # Ищем описание
                    snippet_element = None
                    for selector in [
                        "div.VwiC3b", 
                        "[data-content-feature='1']",
                        "div.kb0PBd",
                        "div[style*='webkit-line-clamp']"
                    ]:
                        try:
                            snippet_element = result.find_element(By.CSS_SELECTOR, selector)
                            if snippet_element.text.strip():
                                break
                        except:
                            continue
                    
                    if title_element and link_element:
                        title = title_element.text.strip()
                        url = link_element.get_attribute('href')
                        snippet = snippet_element.text.strip() if snippet_element else ''
                        
                        if title and url and not url.startswith('https://www.google.com'):
                            result_data = {
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            }
                            
                            # Проверяем на дубликаты
                            if not any(r['url'] == url for r in results):
                                results.append(result_data)
                                self.logger.info(f"Добавлен результат: {title}")
                            
                except Exception as e:
                    continue
            
            self.logger.info(f"Успешно извлечено {len(results)} результатов")
            
        except Exception as e:
            self.logger.warning(f"Ошибка при извлечении результатов: {str(e)}")

        return results

    def go_to_next_page(self):
        """Переход на следующую страницу результатов"""
        try:
            next_button = self.driver.find_element(By.ID, "pnnext")
            if self.smooth_move_to_element(next_button):
                next_button.click()
                self.random_sleep(2, 4)
                return True
        except Exception as e:
            self.logger.warning(f"Не удалось перейти на следующую страницу: {str(e)}")
            return False

    def random_sleep(self, min_seconds=2, max_seconds=5):
        """Sleep for a random amount of time"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def handle_popups(self):
        """Обработка всех возможных всплывающих окон"""
        try:
            # Список возможных XPath для кнопки отклонения геолокации
            location_button_xpaths = [
                "//button[contains(text(), 'Не сейчас')]",
                "//button[contains(text(), 'Not now')]",
                "//button[contains(@aria-label, 'location')]",
                "//div[contains(@role, 'dialog')]//button[contains(., 'Не сейчас')]",
                "//div[contains(@role, 'dialog')]//button[contains(., 'Not now')]"
            ]
            
            for xpath in location_button_xpaths:
                try:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    self.logger.info(f"Найдена кнопка отклонения геолокации: {xpath}")
                    
                    # Используем JavaScript для клика
                    self.driver.execute_script("arguments[0].click();", button)
                    self.logger.info("Успешно отклонили запрос геолокации")
                    self.random_sleep(1, 2)
                    break
                except:
                    continue
            
            # Обработка других возможных попапов (cookies, уведомления и т.д.)
            popup_button_xpaths = [
                "//button[contains(., 'Принять все')]",
                "//button[contains(., 'Accept all')]",
                "//button[contains(@aria-label, 'Accept')]",
                "//div[contains(@role, 'dialog')]//button"
            ]
            
            for xpath in popup_button_xpaths:
                try:
                    button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    self.driver.execute_script("arguments[0].click();", button)
                    self.logger.info(f"Закрыт попап: {xpath}")
                    self.random_sleep(1, 2)
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Ошибка при обработке попапов: {str(e)}")

    def handle_location_dialog(self):
        """Мгновенное и агрессивное закрытие диалога геолокации"""
        try:
            # Блокируем геолокацию через CDP
            self.driver.execute_cdp_cmd('Browser.grantPermissions', {
                'origin': 'https://www.google.ru',
                'permissions': ['geolocation']
            })
            self.driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                'latitude': 0,
                'longitude': 0,
                'accuracy': 0
            })
            
            # Агрессивно отключаем геолокацию и закрываем диалог через JavaScript
            self.driver.execute_script("""
                // Полностью отключаем геолокацию
                navigator.geolocation = undefined;
                window.navigator.geolocation = undefined;
                
                // Блокируем все запросы геолокации
                Object.defineProperty(navigator, 'permissions', {
                    value: {
                        query: () => Promise.reject(new Error('Permissions denied'))
                    }
                });
                
                // Удаляем все диалоги и оверлеи
                function removeElements() {
                    [
                        '[role="dialog"]',
                        '.VfPpkd-z59Tgd',
                        '.VfPpkd-ksKsZd-XxIAqe',
                        '.uArJ5e',
                        '.xeeNA',
                        '.KxvlWc',
                        'div[aria-modal="true"]',
                        '.modal-dialog',
                        '.modal',
                        '[aria-label*="location"]',
                        '[class*="modal"]',
                        '[class*="dialog"]',
                        '[class*="popup"]'
                    ].forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            el.remove();
                        });
                    });
                    
                    // Удаляем затемнение
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                    
                    // Удаляем все элементы с position: fixed
                    document.querySelectorAll('*').forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.position === 'fixed') {
                            el.remove();
                        }
                    });
                }
                
                // Запускаем удаление сразу
                removeElements();
                
                // И через небольшую задержку для динамически добавленных элементов
                setTimeout(removeElements, 100);
                setTimeout(removeElements, 500);
                
                // Очищаем все таймеры
                for (let i = 0; i < 1000; i++) {
                    clearTimeout(i);
                    clearInterval(i);
                }
                
                // Блокируем создание новых диалогов
                const observer = new MutationObserver(removeElements);
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
            """)
            
            # Дополнительно пробуем кликнуть на кнопку через CDP
            self.driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mousePressed',
                'x': 100,
                'y': 100,
                'button': 'left',
                'clickCount': 1
            })
            
            return True
        except Exception as e:
            self.logger.warning(f"Ошибка при закрытии диалога геолокации: {str(e)}")
            return False

    def process_pages(self, query, start_page, end_page, browser_id):
        """Обработка диапазона страниц одним браузером"""
        try:
            self.logger.info(f"Браузер {browser_id}: Обработка страниц {start_page}-{end_page}")
            
            # Инициализируем браузер
            self.initialize(browser_id)
            
            # Открываем Google и сразу блокируем геолокацию
            self.driver.get('https://www.google.ru')
            self.handle_location_dialog()  # Моментально блокируем геолокацию
            
            # Ищем и заполняем поле поиска
            search_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            
            # Вводим текст с небольшой задержкой
            search_input.clear()
            for char in query:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.2))
            
            search_input.send_keys(Keys.RETURN)
            time.sleep(0.5)  # Ждём начала загрузки результатов
            
            # Ещё раз блокируем геолокацию
            self.handle_location_dialog()
            
            browser_results = []
            
            # Переходим на нужную страницу
            if start_page > 1:
                for page in range(1, start_page):
                    self.logger.info(f"Браузер {browser_id}: Переход на страницу {page+1}")
                    if not self.go_to_next_page():
                        self.logger.error(f"Браузер {browser_id}: Не удалось перейти на страницу {page+1}")
                        break
            
            # Обрабатываем страницы
            for page in range(start_page, end_page + 1):
                self.logger.info(f"Браузер {browser_id}: Обрабатываем страницу {page}")
                
                # Ждём загрузку результатов
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "rcnt"))
                )
                
                # Быстрая прокрутка до конца страницы
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.3)
                
                # Извлекаем результаты
                page_results = self.extract_results_xpath()
                
                if page_results:
                    browser_results.extend(page_results)
                    self.logger.info(f"Браузер {browser_id}: Найдено результатов на странице {page}: {len(page_results)}")
                
                # Переходим на следующую страницу, если это не последняя страница
                if page < end_page:
                    if not self.go_to_next_page():
                        self.logger.error(f"Браузер {browser_id}: Не удалось перейти на страницу {page+1}")
                        break
            
            # Добавляем результаты в общий список
            with self.results_lock:
                self.all_results.extend(browser_results)
                self.logger.info(f"Браузер {browser_id}: Добавлено {len(browser_results)} результатов. Всего: {len(self.all_results)}")
            
            return browser_results
            
        except Exception as e:
            self.logger.error(f"Браузер {browser_id}: Ошибка при обработке страниц: {str(e)}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info(f"Браузер {browser_id} закрыт")

    def search_google(self, query, num_pages=10):
        """Выполняет поиск в Google и собирает результаты с нескольких страниц"""
        start_time = time.time()
        
        if self.parallel and self.num_browsers > 1:
            self.logger.info(f"Запуск параллельного поиска с {self.num_browsers} браузерами")
            
            # Распределяем страницы между браузерами
            pages_per_browser = num_pages // self.num_browsers
            remaining_pages = num_pages % self.num_browsers
            
            # Создаем потоки для каждого браузера
            threads = []
            for i in range(self.num_browsers):
                start_page = i * pages_per_browser + 1
                end_page = start_page + pages_per_browser - 1
                
                # Добавляем оставшиеся страницы к последнему браузеру
                if i == self.num_browsers - 1:
                    end_page += remaining_pages
                
                # Создаем новый экземпляр парсера для каждого потока
                parser = SimpleParser(headless=self.headless, parallel=False)
                
                # Запускаем поток
                thread = threading.Thread(
                    target=parser.process_pages,
                    args=(query, start_page, end_page, i+1)
                )
                threads.append(thread)
                thread.start()
                
                # Добавляем задержку между запусками браузеров
                if i < self.num_browsers - 1:
                    time.sleep(5)
            
            # Ждем завершения всех потоков
            for thread in threads:
                thread.join()
            
            # Сохраняем результаты
            if self.all_results:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{self.results_dir}/results_{query.replace(' ', '_')}_{timestamp}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.all_results, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"Параллельный поиск завершен. Найдено результатов: {len(self.all_results)}. Сохранено в {filename}")
                self.logger.info(f"Время выполнения: {time.time() - start_time:.2f} секунд")
            else:
                self.logger.warning("Не удалось найти результаты")
                
            return self.all_results
            
        else:
            # Стандартный последовательный поиск
            try:
                self.logger.info(f"Начинаем поиск по запросу: {query}")
                
                # Открываем Google и сразу блокируем геолокацию
                self.driver.get('https://www.google.ru')
                this.handle_location_dialog()  # Моментально блокируем геолокацию
                
                # Ищем и заполняем поле поиска
                search_input = WebDriverWait(this.driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                
                # Вводим текст с небольшой задержкой
                search_input.clear()
                for char in query:
                    search_input.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.2))
                
                search_input.send_keys(Keys.RETURN)
                time.sleep(0.5)  # Ждём начала загрузки результатов
                
                # Ещё раз блокируем геолокацию
                this.handle_location_dialog()
                
                all_results = []
                current_page = 1
                
                while current_page <= num_pages:
                    this.logger.info(f"Обрабатываем страницу {current_page}")
                    
                    # Ждём загрузку результатов
                    WebDriverWait(this.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "rcnt"))
                    )
                    
                    # Быстрая прокрутка до конца страницы
                    this.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.3)
                    
                    # Извлекаем результаты
                    page_results = this.extract_results_xpath()
                    
                    if page_results:
                        all_results.extend(page_results)
                        this.logger.info(f"Найдено результатов на странице {current_page}: {len(page_results)}")
                        
                        if len(all_results) >= 100:
                            this.logger.info("Достигнут лимит результатов")
                            break
                    
                    if current_page < num_pages:
                        try:
                            # Прокручиваем страницу вниз для видимости кнопки
                            this.driver.execute_script("""
                                window.scrollTo({
                                    top: document.body.scrollHeight,
                                    behavior: 'instant'
                                });
                            """)
                            time.sleep(0.3)
                            
                            # Ищем кнопку "Следующая" разными способами
                            next_button = None
                            selectors = [
                                (By.ID, "pnnext"),
                                (By.CSS_SELECTOR, "#pnnext"),
                                (By.CSS_SELECTOR, "a.nBDE1b"),
                                (By.XPATH, "//span[text()='Следующая']/ancestor::a"),
                                (By.CSS_SELECTOR, "[aria-label='Следующая']")
                            ]
                            
                            for by, selector in selectors:
                                try:
                                    next_button = WebDriverWait(this.driver, 2).until(
                                        EC.element_to_be_clickable((by, selector))
                                    )
                                    if next_button:
                                        break
                                except:
                                    continue
                            
                            if next_button:
                                # Делаем кнопку видимой
                                this.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                                time.sleep(0.2)
                                
                                # Пробуем разные способы клика
                                try:
                                    # Способ 1: JavaScript клик
                                    this.driver.execute_script("arguments[0].click();", next_button)
                                except:
                                    try:
                                        # Способ 2: Обычный клик
                                        next_button.click()
                                    except:
                                        # Способ 3: Программный клик через href
                                        href = next_button.get_attribute('href')
                                        if href:
                                            this.driver.get(href)
                                
                                # Ждём начала загрузки новой страницы
                                time.sleep(0.5)
                                
                                # Проверяем, что страница действительно изменилась
                                try:
                                    WebDriverWait(this.driver, 5).until(
                                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                                    )
                                except:
                                    this.logger.warning("Страница не загрузилась, пробуем ещё раз")
                                    continue
                                
                                current_page += 1
                            else:
                                this.logger.warning("Кнопка следующей страницы не найдена")
                                break
                                
                        except Exception as e:
                            this.logger.warning(f"Не удалось перейти на следующую страницу: {str(e)}")
                            break
                
                # Сохраняем результаты
                if all_results:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{this.results_dir}/results_{query.replace(' ', '_')}_{timestamp}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(all_results, f, ensure_ascii=False, indent=2)
                    
                    this.logger.info(f"Поиск завершен. Найдено результатов: {len(all_results)}. Сохранено в {filename}")
                    this.logger.info(f"Время выполнения: {time.time() - start_time:.2f} секунд")
                else:
                    this.logger.warning("Не удалось найти результаты")
                    
                return all_results
                
            except Exception as e:
                this.logger.error(f"Ошибка при поиске: {str(e)}")
                return []

    def scroll_page_like_human(self, fast=False):
        """Имитирует человеческую прокрутку страницы"""
        try:
            # Получаем высоту страницы
            total_height = this.driver.execute_script("return document.body.scrollHeight")
            
            # Настройки скорости прокрутки
            if fast:
                scroll_step = random.randint(300, 600)  # Большие шаги
                pause_min, pause_max = 0.1, 0.3  # Короткие паузы
                back_scroll_chance = 0.1  # Меньше шанс прокрутки назад
            else:
                scroll_step = random.randint(100, 400)  # Обычные шаги
                pause_min, pause_max = 0.5, 2.0  # Обычные паузы
                back_scroll_chance = 0.2  # Обычный шанс прокрутки назад
            
            # Прокручиваем страницу
            current_height = 0
            while current_height < total_height:
                # Генерируем случайное расстояние прокрутки
                scroll_distance = random.randint(scroll_step // 2, scroll_step)
                current_height += scroll_distance
                
                # Прокручиваем с соответствующей скоростью
                this.driver.execute_script(
                    f"window.scrollTo({{top: {current_height}, behavior: '{'auto' if fast else 'smooth'}'}});"
                )
                
                # Случайная пауза между прокрутками
                time.sleep(random.uniform(pause_min, pause_max))
                
                # Иногда делаем небольшую прокрутку назад
                if random.random() < back_scroll_chance:
                    back_scroll = random.randint(50, 200)
                    current_height -= back_scroll
                    this.driver.execute_script(
                        f"window.scrollTo({{top: {current_height}, behavior: '{'auto' if fast else 'smooth'}'}});"
                    )
                    time.sleep(random.uniform(pause_min, pause_max / 2))
            
        except Exception as e:
            this.logger.warning(f"Ошибка при прокрутке страницы: {str(e)}")

    def take_screenshot(self, name):
        """Take a debug screenshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{this.screenshots_dir}/{name}_{timestamp}.png"
        this.driver.save_screenshot(filename)
        this.logger.info(f"Скриншот сохранен: {filename}")

    def close(self):
        """Close the browser and database connection"""
        if this.driver:
            this.driver.quit()
            this.logger.info("Браузер закрыт")
        
        if hasattr(this, 'conn'):
            this.conn.close()
            this.logger.info("Соединение с базой данных закрыто")

def main():
    # Запускаем парсер с поддержкой параллельной обработки
    parser = SimpleParser(headless=False, parallel=True, num_browsers=2)
    try:
        results = parser.search_google("кирпич", num_pages=10)
        print(f"Найдено результатов: {len(results)}")
        
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