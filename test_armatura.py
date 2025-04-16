import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from examples.parallel_simple_parser import ParallelSimpleParser
import asyncio
import logging

async def main():
    # Инициализация парсера с запросом
    parser = ParallelSimpleParser("арматура")
    
    # Настройка логирования для отслеживания процесса
    logging.basicConfig(level=logging.INFO)
    
    # Запуск парсера с 4 браузерами, каждый обрабатывает 5 страниц
    # Всего 20 страниц (4 * 5 = 20)
    results = await parser.run(num_browsers=4, pages_per_browser=5)
    
    # Подсчет уникальных доменов
    unique_domains = set()
    for result in results:
        if 'url' in result:
            try:
                from urllib.parse import urlparse
                domain = urlparse(result['url']).netloc
                unique_domains.add(domain)
            except:
                continue
    
    # Вывод статистики
    print(f"\nСтатистика парсинга:")
    print(f"Всего результатов: {len(results)}")
    print(f"Уникальных доменов: {len(unique_domains)}")
    print("\nПримеры доменов:")
    for domain in list(unique_domains)[:10]:
        print(f"- {domain}")

if __name__ == "__main__":
    asyncio.run(main()) 