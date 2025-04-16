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

class ParallelParser:
    def __init__(self, num_browsers=2, results_per_page=10):
        self.num_browsers = num_browsers
        self.results_per_page = results_per_page
        self.temp_dirs = []
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
            return version
        except Exception as e:
            logging.error(f"Ошибка при определении версии Chrome: {e}")
            return None

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
                
                # Устанавливаем случайную геолокацию
                city = self.cities[browser_num % len(self.cities)]
                
                # Инициализация браузера с правильной версией
                driver = uc.Chrome(
                    options=options,
                    version_main=int(self.get_chrome_version()),
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

    def process_page(self, url, browser_num):
        """Обработка одной страницы поиска"""
        driver = None
        try:
            driver = self.initialize_browser(browser_num)
            if not driver:
                return []
                
            # Открываем страницу
            driver.get(url)
            time.sleep(2)  # Даем время для загрузки
            
            # Ждем появления результатов
            results = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.g'))
            )
            
            page_results = []
            for result in results:
                try:
                    title_elem = result.find_element(By.CSS_SELECTOR, 'h3')
                    link_elem = result.find_element(By.CSS_SELECTOR, 'a')
                    desc_elem = result.find_element(By.CSS_SELECTOR, 'div.VwiC3b')
                    
                    page_results.append({
                        'title': title_elem.text,
                        'url': link_elem.get_attribute('href'),
                        'description': desc_elem.text
                    })
                except Exception as e:
                    logging.warning(f"Ошибка при извлечении результата: {e}")
                    continue
                    
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

    def search_google(self, query, num_pages=10):
        """Параллельный поиск в Google"""
        all_results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
        
        return all_results

if __name__ == "__main__":
    parser = ParallelParser(num_browsers=2)
    results = parser.search_google("кирпич", num_pages=10)
    logging.warning("Поиск завершен, но результаты не найдены" if not results else 
                   f"Поиск завершен, найдено {len(results)} результатов") 