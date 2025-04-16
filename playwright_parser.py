#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import time
import random
import json
import os
import logging
from datetime import datetime
import tempfile
import shutil
import atexit
import signal
from concurrent.futures import ThreadPoolExecutor
import threading
import sys
import sqlite3

class ParallelSimpleParser:
    def __init__(self, query):
        self.query = query
        self.results = []
        self.results_lock = threading.Lock()
        self.locations = [
            {'latitude': 55.7558, 'longitude': 37.6173, 'accuracy': 100},  # Москва
            {'latitude': 59.9343, 'longitude': 30.3351, 'accuracy': 100},  # Санкт-Петербург
            {'latitude': 56.8389, 'longitude': 60.6057, 'accuracy': 100},  # Екатеринбург
            {'latitude': 55.0084, 'longitude': 82.9357, 'accuracy': 100},  # Новосибирск
            {'latitude': 43.1332, 'longitude': 131.9113, 'accuracy': 100}  # Владивосток
        ]
        
        # Настройка логирования
        self.setup_logging()
        
        # Создаем временную директорию для профилей браузера
        self.temp_dir = tempfile.mkdtemp(prefix='browser_profiles_')
        atexit.register(self.cleanup)
        
        # Создаем директорию для результатов
        if not os.path.exists('results'):
            os.makedirs('results')
            
        # Инициализация базы данных
        self.init_database()
            
        # Настройка таймаутов и повторных попыток
        self.page_timeout = 60000  # 60 секунд
        self.max_retries = 3
        self.retry_delay = 5  # секунды
        self.delay_between_requests = (2, 4)  # Задержка между запросами в секундах

    def init_database(self):
        """Инициализация базы данных"""
        try:
            # Создаем подключение к базе данных
            with sqlite3.connect('search_results.db') as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу для результатов поиска
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS search_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT,
                        title TEXT,
                        url TEXT,
                        snippet TEXT,
                        page_num INTEGER,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Создаем индекс для быстрого поиска
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_query ON search_results(query)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON search_results(url)')
                
                conn.commit()
                logging.info("База данных успешно инициализирована")
        except Exception as e:
            logging.error(f"Ошибка при инициализации базы данных: {str(e)}")
            raise

    def save_to_database(self):
        """Сохранение результатов в базу данных"""
        try:
            with sqlite3.connect('search_results.db') as conn:
                cursor = conn.cursor()
                
                # Подготавливаем данные для вставки
                data_to_insert = [
                    (self.query, result['title'], result['url'], result['snippet'], result['page'])
                    for result in self.results
                ]
                
                # Вставляем данные
                cursor.executemany(
                    'INSERT INTO search_results (query, title, url, snippet, page_num) VALUES (?, ?, ?, ?, ?)',
                    data_to_insert
                )
                
                conn.commit()
                logging.info(f"Сохранено {len(data_to_insert)} результатов в базу данных")
                
                # Получаем статистику
                cursor.execute('SELECT COUNT(*) FROM search_results WHERE query = ?', (self.query,))
                total_results = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT url) FROM search_results WHERE query = ?', (self.query,))
                unique_urls = cursor.fetchone()[0]
                
                logging.info(f"Всего в базе для запроса '{self.query}': {total_results} результатов, {unique_urls} уникальных URL")
                
        except Exception as e:
            logging.error(f"Ошибка при сохранении в базу данных: {str(e)}")
            raise

    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('parser.log'),
                logging.StreamHandler()
            ]
        )

    def cleanup(self):
        """Очистка временных файлов при завершении"""
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    async def process_page(self, context, page_num):
        """Обработка одной страницы поиска"""
        retry_count = 0
        while retry_count < self.max_retries:
            page = None
            try:
                # Создаем новую страницу
                page = await context.new_page()
                
                # Устанавливаем случайную геолокацию
                location = random.choice(self.locations)
                await context.grant_permissions(['geolocation'])
                await context.set_geolocation(location)
                
                # Настраиваем расширенные заголовки
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                })
                
                # Загружаем страницу поиска
                url = f"https://www.google.com/search?q={self.query}&start={(page_num-1)*10}&hl=ru"
                logging.info(f"Загрузка страницы: {url}")
                
                # Добавляем случайную задержку перед запросом
                await asyncio.sleep(random.uniform(1, 3))
                
                # Увеличиваем время ожидания загрузки страницы
                await page.goto(url, wait_until='domcontentloaded', timeout=90000)
                
                # Ждем загрузку результатов с увеличенным таймаутом
                await page.wait_for_selector('div#search', timeout=90000)
                
                # Добавляем небольшую задержку для полной загрузки динамического контента
                await asyncio.sleep(random.uniform(2, 4))
                
                # Получаем все результаты с разными селекторами
                results = await page.query_selector_all('div.g, div[data-hveid]')
                logging.info(f"Найдено {len(results)} результатов на странице {page_num}")
                
                page_results = []
                for result in results:
                    try:
                        # Извлекаем данные с более точными селекторами
                        title_element = await result.query_selector('h3, div[role="heading"]')
                        link_element = await result.query_selector('a[href^="http"]')
                        snippet_element = await result.query_selector('div.VwiC3b, div.s, div[style="-webkit-line-clamp:2"]')
                        
                        if title_element and link_element:
                            title = await title_element.text_content()
                            link = await link_element.get_attribute('href')
                            snippet = ''
                            
                            if snippet_element:
                                snippet = await snippet_element.text_content()
                            
                            if title and link and not link.startswith('https://www.google.com'):
                                page_results.append({
                                    'title': title.strip(),
                                    'url': link,
                                    'snippet': snippet.strip(),
                                    'page': page_num
                                })
                                logging.info(f"Обработан результат: {title[:50]}...")
                                
                    except Exception as e:
                        logging.warning(f"Ошибка при обработке результата: {str(e)}")
                        continue
                
                # Добавляем результаты в общий список
                if page_results:
                    with self.results_lock:
                        self.results.extend(page_results)
                        logging.info(f"Добавлено {len(page_results)} результатов со страницы {page_num}")
                else:
                    logging.warning(f"Не найдено результатов на странице {page_num}")
                    # Сохраняем скриншот страницы для отладки
                    await page.screenshot(path=f'debug_page_{page_num}.png')
                
                # Закрываем страницу
                if page:
                    await page.close()
                
                return True
                
            except PlaywrightTimeoutError as e:
                retry_count += 1
                logging.error(f"Таймаут при обработке страницы {page_num} (попытка {retry_count}): {str(e)}")
                if retry_count == self.max_retries:
                    logging.error(f"Не удалось обработать страницу {page_num} после {self.max_retries} попыток")
                    return False
                if page:
                    await page.close()
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                retry_count += 1
                logging.error(f"Ошибка при обработке страницы {page_num} (попытка {retry_count}): {str(e)}")
                if retry_count == self.max_retries:
                    logging.error(f"Не удалось обработать страницу {page_num} после {self.max_retries} попыток")
                    return False
                if page:
                    await page.close()
                await asyncio.sleep(self.retry_delay)

    async def process_pages(self, browser_id, start_page, end_page):
        """Обработка диапазона страниц"""
        try:
            async with async_playwright() as p:
                # Запускаем браузер
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-blink-features=AutomationControlled'
                    ]
                )
                
                # Создаем новый контекст браузера
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                try:
                    for page in range(start_page, end_page + 1):
                        logging.info(f"Браузер {browser_id}: обработка страницы {page}")
                        if not await self.process_page(context, page):
                            logging.error(f"Браузер {browser_id}: ошибка при обработке страницы {page}")
                        await asyncio.sleep(random.uniform(*self.delay_between_requests))
                        
                finally:
                    await context.close()
                    await browser.close()
                    
        except Exception as e:
            logging.error(f"Критическая ошибка в браузере {browser_id}: {str(e)}")

    def worker(self, browser_id, start_page, end_page):
        """Рабочая функция для потока"""
        try:
            asyncio.run(self.process_pages(browser_id, start_page, end_page))
        except Exception as e:
            logging.error(f"Ошибка в потоке {browser_id}: {str(e)}")

    def run(self, num_browsers=2, pages_per_browser=5):
        """Запуск парсера с параллельной обработкой"""
        start_time = time.time()
        logging.info("=" * 50)
        logging.info(f"НАЧАЛО ПАРСИНГА: {self.query}")
        logging.info(f"Запуск парсера с {num_browsers} браузерами, по {pages_per_browser} страниц на браузер")
        logging.info(f"Общее количество страниц для обработки: {num_browsers * pages_per_browser}")
        logging.info("=" * 50)
        
        # Создаем пул потоков
        with ThreadPoolExecutor(max_workers=num_browsers) as executor:
            futures = []
            
            # Запускаем потоки
            for i in range(num_browsers):
                start_page = i * pages_per_browser + 1
                end_page = (i + 1) * pages_per_browser
                
                logging.info(f"Запуск браузера {i+1}/{num_browsers} для обработки страниц {start_page}-{end_page}")
                
                future = executor.submit(
                    self.worker,
                    i,
                    start_page,
                    end_page
                )
                futures.append(future)
            
            # Ожидаем завершения всех потоков
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Ошибка при выполнении потока: {str(e)}")
        
        # Сохранение результатов
        self.save_results()
        self.save_to_database()
        
        duration = time.time() - start_time
        logging.info("=" * 50)
        logging.info("ИТОГИ РАБОТЫ ПАРСЕРА:")
        logging.info(f"Ключевое слово: {self.query}")
        logging.info(f"Время выполнения: {duration:.2f} секунд")
        logging.info(f"Количество запущенных браузеров: {num_browsers}")
        logging.info(f"Страниц обработано на браузер: {pages_per_browser}")
        logging.info(f"Всего обработано страниц: {num_browsers * pages_per_browser}")
        logging.info(f"Найдено результатов: {len(self.results)}")
        logging.info(f"Средняя скорость: {len(self.results)/duration:.2f} результатов в секунду")
        logging.info("=" * 50)
        print(f"\nНайдено результатов: {len(self.results)}")
        print(f"Время выполнения: {duration:.2f} секунд")

    def save_results(self):
        """Сохранение результатов в JSON файл"""
        if not os.path.exists('results'):
            os.makedirs('results')
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'results/results_{self.query}_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
            
        logging.info(f"Результаты сохранены в файл: {filename}")

if __name__ == "__main__":
    # Устанавливаем обработчик сигналов для корректного завершения
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    # Запускаем парсер
    parser = ParallelSimpleParser("кирпич")
    parser.run(num_browsers=2, pages_per_browser=5) 