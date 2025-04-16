#!/usr/bin/env python3
import logging
import sys
import argparse
from parallel_simple_parser import ParallelSimpleParser
import parser_rules as rules

# Configure logging
logging.basicConfig(
    level=getattr(logging, rules.LOGGING["level"]),
    format=rules.LOGGING["format"]
)

def main():
    # Создаем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Запуск парсера с указанным ключевым словом')
    parser.add_argument('query', nargs='?', default="python programming", 
                        help='Ключевое слово для поиска (по умолчанию: "python programming")')
    parser.add_argument('--browsers', type=int, default=2, 
                        help='Количество браузеров (по умолчанию: 2)')
    parser.add_argument('--pages', type=int, default=3, 
                        help='Количество страниц на браузер (по умолчанию: 3)')
    
    # Парсим аргументы
    args = parser.parse_args()
    
    # Инициализируем парсер с указанным ключевым словом
    parser = ParallelSimpleParser(args.query)
    
    # Запускаем парсер с указанными параметрами
    parser.run(num_browsers=args.browsers, pages_per_browser=args.pages)

if __name__ == "__main__":
    main()