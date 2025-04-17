#!/usr/bin/env python3
"""
ПРАВИЛА ПАРСЕРА - ИЗМЕНЕНИЕ ТОЛЬКО ЧЕРЕЗ SUDO!
Этот файл содержит все настройки и правила для парсера.
Изменение этих правил требует прав администратора.
"""

# ===== ОБЩИЕ НАСТРОЙКИ =====
PARSER_VERSION = "1.0.0"
PARSER_NAME = "ParallelSimpleParser"
PARSER_AUTHOR = "System Administrator"
PARSER_CREATION_DATE = "2025-04-16"

# ===== НАСТРОЙКИ БРАУЗЕРА =====
BROWSER_SETTINGS = {
    "headless": True,
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "args": [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-blink-features=AutomationControlled',
        '--disable-extensions',
        '--disable-component-extensions-with-background-pages',
        '--disable-default-apps',
        '--disable-popup-blocking',
        '--disable-notifications',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-breakpad',
        '--disable-component-update',
        '--disable-domain-reliability',
        '--disable-sync'
    ]
}

# ===== НАСТРОЙКИ ПАРСИНГА =====
PARSING_SETTINGS = {
    "page_timeout": 90000,  # 90 секунд
    "max_retries": 3,
    "retry_delay": 5,  # секунды
    "delay_between_requests": (2, 4),  # Задержка между запросами в секундах
    "default_num_browsers": 2,
    "default_pages_per_browser": 5
}

# ===== ГЕОЛОКАЦИИ =====
LOCATIONS = [
    {'latitude': 55.7558, 'longitude': 37.6173, 'accuracy': 100},  # Москва
    {'latitude': 59.9343, 'longitude': 30.3351, 'accuracy': 100},  # Санкт-Петербург
    {'latitude': 56.8389, 'longitude': 60.6057, 'accuracy': 100},  # Екатеринбург
    {'latitude': 55.0084, 'longitude': 82.9357, 'accuracy': 100},  # Новосибирск
    {'latitude': 43.1332, 'longitude': 131.9113, 'accuracy': 100}  # Владивосток
]

# ===== СЕЛЕКТОРЫ =====
SELECTORS = {
    "search_container": "div#search",
    "result_items": "div.g, div[data-hveid]",
    "title": "h3",
    "link": "a",
    "snippet": "div.VwiC3b"
}

# ===== АНТИ-ДЕТЕКШН СКРИПТ =====
ANTI_DETECTION_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});
"""

# ===== ПРАВИЛА ОБРАБОТКИ РЕЗУЛЬТАТОВ =====
RESULT_PROCESSING = {
    "exclude_domains": ["google.com", "youtube.com"],
    "min_title_length": 3,
    "min_snippet_length": 10,
    "save_format": "json",
    "results_dir": "results"
}

# ===== ЛОГИРОВАНИЕ =====
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "file": "parser.log"
}

# ===== БЕЗОПАСНОСТЬ =====
SECURITY = {
    "require_sudo_for_changes": True,
    "max_concurrent_browsers": 10,
    "max_pages_per_browser": 20,
    "max_total_pages": 100,
    "rate_limit": {
        "requests_per_minute": 30,
        "requests_per_hour": 300
    }
}

# ===== ВАЛИДАЦИЯ =====
def validate_settings():
    """Проверка корректности настроек"""
    if PARSING_SETTINGS["page_timeout"] < 10000:
        raise ValueError("Page timeout must be at least 10 seconds")
    
    if PARSING_SETTINGS["max_retries"] < 1:
        raise ValueError("Max retries must be at least 1")
    
    if PARSING_SETTINGS["delay_between_requests"][0] < 1:
        raise ValueError("Minimum delay between requests must be at least 1 second")
    
    if PARSING_SETTINGS["default_num_browsers"] > SECURITY["max_concurrent_browsers"]:
        raise ValueError(f"Default number of browsers exceeds security limit of {SECURITY['max_concurrent_browsers']}")
    
    return True

# Проверяем настройки при импорте
validate_settings() 