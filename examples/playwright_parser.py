from playwright.sync_api import sync_playwright, TimeoutError
import json
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
import random

class PlaywrightParser:
    def __init__(self, query: str, num_pages: int = 10, fast_mode: bool = False):
        self.query = query
        self.num_pages = num_pages
        self.fast_mode = fast_mode
        self.results: List[Dict] = []
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def random_sleep(self, min_time: float = 1.0, max_time: float = 3.0) -> None:
        """Ожидание случайного времени между операциями"""
        if self.fast_mode:
            min_time /= 2
            max_time /= 2
        time.sleep(random.uniform(min_time, max_time))

    def process_page(self, page, start_index: int) -> List[Dict]:
        """Обработка одной страницы результатов с повторными попытками"""
        url = f"https://www.google.com/search?q={self.query}&start={start_index}"
        max_retries = 3
        current_try = 0
        
        while current_try < max_retries:
            try:
                self.logger.info(f"Попытка {current_try + 1} обработки страницы {start_index // 10 + 1}")
                
                # Увеличенный таймаут для навигации
                page.set_default_timeout(60000)  # 60 секунд
                page.goto(url, wait_until="networkidle")
                
                # Ждем загрузку результатов
                page.wait_for_selector('div.g', state="visible", timeout=60000)
                
                # Прокрутка для загрузки всех результатов
                page.evaluate("""
                    window.scrollTo(0, document.body.scrollHeight);
                    return new Promise(resolve => setTimeout(resolve, 2000));
                """)
                
                # Ждем стабилизации DOM
                page.wait_for_load_state("networkidle")
                
                # Извлечение результатов
                results = page.evaluate("""
                    () => {
                        const results = [];
                        document.querySelectorAll('div.g').forEach(el => {
                            const titleEl = el.querySelector('h3');
                            const linkEl = el.querySelector('a');
                            const snippetEl = el.querySelector('.VwiC3b');
                            
                            if (titleEl && linkEl && snippetEl) {
                                results.push({
                                    title: titleEl.innerText,
                                    url: linkEl.href,
                                    snippet: snippetEl.innerText
                                });
                            }
                        });
                        return results;
                    }
                """)
                
                self.logger.info(f"Найдено {len(results)} результатов на странице {start_index // 10 + 1}")
                return results
                
            except TimeoutError as e:
                self.logger.error(f"Таймаут при обработке страницы {start_index // 10 + 1}: {str(e)}")
                current_try += 1
                if current_try < max_retries:
                    self.random_sleep(3, 5)
                    continue
                raise
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке страницы {start_index // 10 + 1}: {str(e)}")
                current_try += 1
                if current_try < max_retries:
                    self.random_sleep(3, 5)
                    continue
                raise

    def search_google(self) -> List[Dict]:
        """Выполнение поиска в Google"""
        with sync_playwright() as p:
            # Настройка браузера
            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--start-maximized',
                    '--no-sandbox'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # Отключение WebDriver
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = context.new_page()
            self.logger.info("Браузер инициализирован с настройками стелс-режима")
            
            all_results = []
            
            try:
                for i in range(0, self.num_pages):
                    start_index = i * 10
                    page_results = self.process_page(page, start_index)
                    all_results.extend(page_results)
                    
                    # Сохраняем промежуточные результаты
                    self._save_results(all_results)
                    
                    if i < self.num_pages - 1:
                        self.random_sleep(2, 4)
                        
            except Exception as e:
                self.logger.error(f"Ошибка при выполнении поиска: {str(e)}")
            finally:
                browser.close()
                self.logger.info("Браузер закрыт")
            
            self.logger.info(f"Найдено {len(all_results)} результатов всего")
            return all_results

    def _save_results(self, results: List[Dict]) -> None:
        """Сохранение результатов в JSON файл"""
        if not os.path.exists('results'):
            os.makedirs('results')
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'results/results_{self.query}_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Сохранено {len(results)} результатов в {filename}")

if __name__ == "__main__":
    parser = PlaywrightParser("кирпич", num_pages=10, fast_mode=True)
    results = parser.search_google()
    logging.warning("Поиск завершен, но результаты не найдены" if not results else 
                   f"Поиск завершен, найдено {len(results)} результатов") 