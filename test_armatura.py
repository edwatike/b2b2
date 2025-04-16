import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from examples.parallel_simple_parser import ParallelSimpleParser
import asyncio
import logging

def main():
    # Инициализируем парсер с запросом
    parser = ParallelSimpleParser("нержавеющий порошок")
    
    # Запускаем парсер с 5 браузерами, каждый обрабатывает по 5 страниц
    parser.run(num_browsers=5, pages_per_browser=5)
    
    # Выводим статистику
    print("\nСтатистика парсинга:")
    print(f"Всего обработано страниц: 25")
    print(f"Найдено сайтов: {len(parser.results)}")
    
    # Выводим найденные сайты
    print("\nНайденные сайты:")
    for result in parser.results:
        print(f"\nURL: {result['url']}")
        print(f"Заголовок: {result['title']}")
        print(f"Сниппет: {result['snippet'][:200]}...")
        print("-" * 80)

if __name__ == "__main__":
    main() 