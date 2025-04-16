import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import time
import os
import shutil
import logging
import tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess
import requests
import random
import threading
import sys

class ParallelParser:
    def __init__(self, num_browsers=2, results_per_page=10, fast_mode=False):
        self.num_browsers = num_browsers
        self.results_per_page = results_per_page
        self.fast_mode = fast_mode
        self.temp_dirs = []
        self.browser_lock = threading.Lock()
        self.setup_dirs()
        self.setup_logging()
        
        # Города России для геолокации
        self.cities = [
            {"lat": 55.7558, "lon": 37.6173},  # Москва
            {"lat": 59.9343, "lon": 30.3351},  # Санкт-Петербург
            {"lat": 56.8519, "lon": 60.6122},  # Екатеринбург
            {"lat": 55.0415, "lon": 82.9346},  # Новосибирск
            {"lat": 56.3287, "lon": 44.002},   # Нижний Новгород
        ]
        
    def setup_dirs(self):
        """Создание директорий для результатов и очистка кэша ChromeDriver"""
        if not os.path.exists('results'):
            os.makedirs('results')
            
        # Очищаем директорию ChromeDriver
        chromedriver_dir = os.path.expanduser('~/.local/share/undetected_chromedriver')
        if os.path.exists(chromedriver_dir):
            try:
                shutil.rmtree(chromedriver_dir)
                logging.info(f"Очищаем директорию ChromeDriver: {chromedriver_dir}")
            except Exception as e:
                logging.warning(f"Не удалось очистить директорию ChromeDriver: {e}")

    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def get_chrome_version(self):
        """Получение версии установленного Chrome"""
        try:
            output = subprocess.check_output(['google-chrome', '--version'])
            version = output.decode('utf-8').strip().split()[-1].split('.')[0]
            logging.info(f"Установленная версия Chrome: {version}")
            return int(version)
        except Exception as e:
            logging.error(f"Ошибка при определении версии Chrome: {e}")
            return None

    def random_sleep(self, min_seconds=1, max_seconds=3):
        """Случайная пауза для имитации человеческого поведения"""
        if self.fast_mode:
            time.sleep(random.uniform(min_seconds/2, max_seconds/2))
        else:
            time.sleep(random.uniform(min_seconds, max_seconds))

    def initialize_browser(self, browser_num):
        """Инициализация браузера с правильной версией ChromeDriver"""
        max_attempts = 3
        current_attempt = 1
        
        while current_attempt <= max_attempts:
            try:
                logging.info(f"[Браузер {browser_num}] Попытка {current_attempt} инициализации...")
                
                # Создаем временную директорию для профиля
                temp_dir = tempfile.mkdtemp()
                self.temp_dirs.append(temp_dir)
                
                # Настройка опций Chrome
                options = uc.ChromeOptions()
                options.add_argument(f'--user-data-dir={temp_dir}')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-notifications')
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=IsolateOrigins,site-per-process')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                # Устанавливаем случайную геолокацию
                city = self.cities[browser_num % len(self.cities)]
                
                # Инициализация браузера с правильной версией
                with self.browser_lock:
                    chrome_version = self.get_chrome_version()
                    if not chrome_version:
                        raise Exception("Не удалось определить версию Chrome")
                    
                    driver = uc.Chrome(
                        options=options,
                        version_main=chrome_version,
                        driver_executable_path=None,
                        browser_executable_path=None,
                        use_subprocess=True
                    )
                
                # Устанавливаем геолокацию
                params = {
                    "latitude": city["lat"],
                    "longitude": city["lon"],
                    "accuracy": 100
                }
                driver.execute_cdp_cmd("Emulation.setGeolocationOverride", params)
                
                # Устанавливаем таймауты
                driver.set_page_load_timeout(30)
                driver.implicitly_wait(10)
                
                # Проверяем, что браузер не определяется как автоматизированный
                driver.get("https://bot.sannysoft.com/")
                self.random_sleep(2, 4)
                
                # Проверяем, что браузер работает
                if "Chrome" not in driver.title:
                    raise Exception("Браузер не загрузился корректно")
                
                return driver
                
            except Exception as e:
                logging.error(f"[Браузер {browser_num}] Ошибка при инициализации: {str(e)}")
                logging.error(f"[Браузер {browser_num}] Тип ошибки: {type(e).__name__}")
                
                if current_attempt < max_attempts:
                    wait_time = 5 * current_attempt
                    logging.warning(f"[Браузер {browser_num}] Попытка {current_attempt} не удалась, пробуем снова через {wait_time} секунд...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"[Браузер {browser_num}] Все попытки инициализации исчерпаны")
                    raise
                    
                current_attempt += 1
        
        return None

    def handle_location_dialog(self, driver):
        """Обработка диалога геолокации"""
        try:
            # Пробуем найти и закрыть диалог геолокации
            location_dialog = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Разрешить']"))
            )
            location_dialog.click()
            logging.info("Диалог геолокации обработан")
            return True
        except:
            # Если диалог не найден, пробуем через JavaScript
            try:
                driver.execute_script("""
                    var elements = document.querySelectorAll('button[aria-label="Разрешить"]');
                    for (var i = 0; i < elements.length; i++) {
                        elements[i].click();
                    }
                """)
                logging.info("Диалог геолокации обработан через JavaScript")
                return True
            except:
                logging.info("Диалог геолокации не найден")
                return False

    def process_page(self, url, browser_num):
        """Обработка одной страницы поиска"""
        driver = None
        start_time = time.time()
        try:
            driver = self.initialize_browser(browser_num)
            if not driver:
                return []
                
            # Открываем страницу
            driver.get(url)
            self.random_sleep(2, 4)
            
            # Обрабатываем диалог геолокации
            self.handle_location_dialog(driver)
            
            # Ждем появления результатов с несколькими селекторами
            selectors = [
                'div.g', 
                'div[data-hveid]', 
                'div[data-sokoban-container]',
                'div.yuRUbf'
            ]
            
            results = None
            for selector in selectors:
                try:
                    results = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if results:
                        logging.info(f"Найдены результаты с селектором: {selector}")
                        break
                except:
                    continue
            
            if not results:
                logging.warning(f"[Браузер {browser_num}] Не найдены результаты на странице")
                return []
            
            page_results = []
            for result in results:
                try:
                    # Пробуем разные селекторы для заголовка
                    title_selectors = ['h3', 'h3.r', 'div[role="heading"]']
                    title_elem = None
                    for selector in title_selectors:
                        try:
                            title_elem = result.find_element(By.CSS_SELECTOR, selector)
                            if title_elem and title_elem.text:
                                break
                        except:
                            continue
                    
                    # Пробуем разные селекторы для ссылки
                    link_selectors = ['a', 'a[href]', 'a[ping]']
                    link_elem = None
                    for selector in link_selectors:
                        try:
                            link_elem = result.find_element(By.CSS_SELECTOR, selector)
                            if link_elem and link_elem.get_attribute('href'):
                                break
                        except:
                            continue
                    
                    # Пробуем разные селекторы для описания
                    desc_selectors = ['div.VwiC3b', 'div[style="-webkit-line-clamp:2"]', 'div.s']
                    desc_elem = None
                    for selector in desc_selectors:
                        try:
                            desc_elem = result.find_element(By.CSS_SELECTOR, selector)
                            if desc_elem and desc_elem.text:
                                break
                        except:
                            continue
                    
                    if title_elem and link_elem:
                        page_results.append({
                            'title': title_elem.text,
                            'url': link_elem.get_attribute('href'),
                            'description': desc_elem.text if desc_elem else ""
                        })
                except Exception as e:
                    logging.warning(f"Ошибка при извлечении результата: {e}")
                    continue
            
            logging.info(f"[Браузер {browser_num}] Найдено {len(page_results)} результатов на странице")
            return page_results
            
        except Exception as e:
            logging.error(f"[Браузер {browser_num}] Ошибка при обработке страницы: {str(e)}")
            return []
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            logging.info(f"[Браузер {browser_num}] Время обработки: {time.time() - start_time:.2f} сек")

    def search_google(self, query, num_pages=10):
        """Параллельный поиск в Google"""
        all_results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        start_time = time.time()
        
        # Создаем пул потоков
        with ThreadPoolExecutor(max_workers=self.num_browsers) as executor:
            # Формируем список URL для каждой страницы
            urls = [
                f'https://www.google.com/search?q={query}&start={i * 10}'
                for i in range(num_pages)
            ]
            
            # Распределяем URL между браузерами
            futures = []
            for i, url in enumerate(urls):
                browser_num = i % self.num_browsers
                futures.append(
                    executor.submit(self.process_page, url, browser_num)
                )
                # Добавляем небольшую задержку между запусками браузеров
                if not self.fast_mode:
                    time.sleep(2)
            
            # Собираем результаты
            for future in futures:
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    logging.error(f"Ошибка при получении результатов: {e}")
        
        # Сохраняем результаты
        if all_results:
            filename = f'results/results_{query}_{timestamp}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            logging.info(f"Результаты сохранены в {filename}")
        else:
            logging.warning("Не удалось найти результаты")
        
        # Очищаем временные директории
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        logging.info(f"Общее время выполнения: {time.time() - start_time:.2f} сек")
        return all_results

if __name__ == "__main__":
    # Проверяем версию Chrome
    chrome_version = subprocess.check_output(['google-chrome', '--version']).decode('utf-8').strip().split()[-1].split('.')[0]
    logging.info(f"Установленная версия Chrome: {chrome_version}")
    
    # Запускаем парсер с меньшим количеством браузеров для начала
    parser = ParallelParser(num_browsers=2, fast_mode=True)
    results = parser.search_google("кирпич", num_pages=10)
    logging.warning("Поиск завершен, но результаты не найдены" if not results else 
                   f"Поиск завершен, найдено {len(results)} результатов") 