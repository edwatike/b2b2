# Параллельный Парсер Google Search

Мощный парсер для Google Search с поддержкой параллельной обработки и защитой от обнаружения.

## Особенности

- Параллельная обработка с использованием нескольких браузеров
- Защита от обнаружения автоматизации
- Сохранение результатов в JSON и SQLite
- Настраиваемые правила парсинга (требуется sudo для изменений)
- Поддержка геолокации для разных регионов
- Расширенное логирование

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/parallel-google-parser.git
cd parallel-google-parser
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Для Linux/Mac
# или
.venv\Scripts\activate  # Для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Установите Playwright и браузеры:
```bash
playwright install chromium
```

## Использование

### Базовое использование

```python
from parallel_simple_parser import ParallelSimpleParser

# Инициализация парсера с запросом
parser = ParallelSimpleParser("ваш поисковый запрос")

# Запуск парсера с настройками по умолчанию
parser.run()
```

### Расширенное использование

```python
from parallel_simple_parser import ParallelSimpleParser

# Инициализация парсера
parser = ParallelSimpleParser("ваш поисковый запрос")

# Запуск с указанием количества браузеров и страниц
parser.run(num_browsers=4, pages_per_browser=5)
```

## Настройка правил парсинга

Правила парсинга хранятся в файле `parser_rules.py` и могут быть изменены только с правами администратора.

### Создание шаблона настроек

```bash
sudo python3 update_parser_rules.py --template
```

Это создаст файл `parser_rules_template.json`, который вы можете отредактировать.

### Обновление правил

```bash
sudo python3 update_parser_rules.py --settings parser_rules_template.json
```

## Структура проекта

- `parallel_simple_parser.py` - основной класс парсера
- `parser_rules.py` - настройки и правила парсинга (требуется sudo для изменений)
- `update_parser_rules.py` - скрипт для обновления правил (требуется sudo)
- `test_parser.py` - пример использования парсера
- `results/` - директория для сохранения результатов
- `search_results.db` - база данных SQLite с результатами

## Ограничения безопасности

- Максимальное количество браузеров: 10
- Максимальное количество страниц на браузер: 20
- Максимальное общее количество страниц: 100
- Ограничение запросов: 30 в минуту, 300 в час

## Логирование

Логи сохраняются в файл `parser.log` и выводятся в консоль.

## Лицензия

MIT 