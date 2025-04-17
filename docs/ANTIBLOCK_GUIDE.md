# Руководство по обходу блокировок при веб-скрапинге

## Основные методы защиты от блокировок

### 1. Ротация User-Agent

```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]
```

### 2. Управление задержками

```python
import random
import asyncio

async def random_delay():
    # Случайная задержка от 2 до 5 секунд
    delay = random.uniform(2, 5)
    await asyncio.sleep(delay)
```

### 3. Использование прокси

```python
PROXY_LIST = [
    'http://proxy1.example.com:8080',
    'http://proxy2.example.com:8080',
    'socks5://proxy3.example.com:1080'
]
```

## Практические рекомендации

### 1. Эмуляция человеческого поведения

- Добавляйте случайные паузы между действиями
- Имитируйте движения мыши
- Выполняйте случайные скроллы страницы

```python
async def emulate_human_behavior(page):
    # Случайный скролл
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight * Math.random())')
    await asyncio.sleep(random.uniform(0.5, 2))
    
    # Имитация движения мыши
    await page.mouse.move(random.randint(100, 700), random.randint(100, 700))
```

### 2. Настройка браузера

```python
async def create_stealth_browser():
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--window-size=1920,1080',
            '--start-maximized'
        ]
    )
    return browser
```

### 3. Управление cookies и localStorage

```python
async def manage_browser_data(context):
    # Установка cookies
    await context.add_cookies([{
        'name': 'session_token',
        'value': 'random_value',
        'domain': '.example.com',
    }])
    
    # Очистка localStorage при необходимости
    await context.clear_local_storage()
```

## Продвинутые техники

### 1. Геолокация и часовой пояс

```python
browser_context = await browser.new_context(
    locale='en-US',
    timezone_id='America/New_York',
    geolocation={'latitude': 40.7128, 'longitude': -74.0060},
    permissions=['geolocation']
)
```

### 2. Fingerprint-спуфинг

```python
async def setup_fingerprint_spoofing(context):
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin' },
                { name: 'Chrome PDF Viewer' },
                { name: 'Native Client' }
            ]
        });
    """)
```

### 3. Распределение нагрузки

```python
async def distribute_load(urls, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    async def bounded_fetch(url):
        async with semaphore:
            return await fetch_url(url)
    return await asyncio.gather(*[bounded_fetch(url) for url in urls])
```

## Мониторинг и обработка блокировок

### 1. Детекция блокировок

```python
async def check_for_blocking(page):
    blocking_patterns = [
        'captcha',
        'unusual traffic',
        'blocked',
        'verify you are human'
    ]
    
    content = await page.content()
    for pattern in blocking_patterns:
        if pattern in content.lower():
            return True
    return False
```

### 2. Автоматическое восстановление

```python
async def handle_blocking(page, context):
    if await check_for_blocking(page):
        # Очистка cookies и кэша
        await context.clear_cookies()
        
        # Смена IP через прокси
        new_proxy = get_new_proxy()
        await context.route('**/*', lambda route: route.continue_(proxy={'server': new_proxy}))
        
        # Ожидание перед повторной попыткой
        await asyncio.sleep(random.uniform(30, 60))
        return True
    return False
```

## Пример использования всех техник

```python
async def scrape_with_protection(url):
    browser = await create_stealth_browser()
    context = await setup_protected_context(browser)
    page = await context.new_page()
    
    try:
        await page.goto(url)
        await emulate_human_behavior(page)
        
        if await check_for_blocking(page):
            if await handle_blocking(page, context):
                await page.reload()
        
        # Выполнение скрапинга
        data = await extract_data(page)
        
        await random_delay()
        return data
        
    finally:
        await browser.close()
```

## Рекомендации по настройке

1. **Настройка задержек:**
   - Минимальная задержка между запросами: 2-5 секунд
   - Увеличение задержки при обнаружении блокировки
   - Случайные интервалы между действиями

2. **Прокси-серверы:**
   - Использование разных типов прокси (HTTP, SOCKS5)
   - Ротация прокси каждые X запросов
   - Проверка прокси перед использованием

3. **Мониторинг:**
   - Логирование всех блокировок
   - Отслеживание успешности запросов
   - Анализ паттернов блокировок

## Заключение

При использовании всех описанных техник важно:
1. Комбинировать разные методы защиты
2. Регулярно обновлять User-Agent и прокси
3. Настраивать параметры под конкретный сайт
4. Мониторить эффективность защиты
5. Соблюдать robots.txt и условия использования сайтов 