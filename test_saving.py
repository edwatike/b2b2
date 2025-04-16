import sqlite3
import json
from models import init_database, ParsedSite

def test_save_and_retrieve():
    """Тестирование сохранения и получения данных"""
    # Инициализируем базу данных
    init_database()
    
    # Создаем тестовый сайт
    test_site = ParsedSite(
        url="https://example.com",
        domain="example.com",
        title="Example Company",
        raw_html="<html>Test HTML</html>",
        search_engine="google",
        search_keyword="test query",
        has_inn_data=True,
        is_supplier_candidate=True,
        inn="1234567890",
        ogrn="1234567890123",
        kpp="123456789",
        company_name="Example Company LLC",
        emails=["test@example.com"],
        phones=["+7 (999) 123-45-67"]
    )
    
    # Сохраняем сайт
    site_id = test_site.save()
    print(f"✅ Сайт сохранен с ID: {site_id}")
    
    # Получаем последние сайты
    print("\nПоследние сохраненные сайты:")
    recent_sites = ParsedSite.get_recent_sites(5)
    for site in recent_sites:
        print(f"\nURL: {site[1]}")
        print(f"Домен: {site[2]}")
        print(f"Заголовок: {site[3]}")
        print(f"ИНН: {site[10]}")
        print(f"ОГРН: {site[11]}")
        print(f"Email: {site[13]}")
        print(f"Телефоны: {site[14]}")
        print("=" * 40)
    
    # Проверяем уникальность доменов
    with sqlite3.connect('search_results.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT domain, COUNT(*) as count 
            FROM parsed_sites 
            GROUP BY domain 
            HAVING count > 1
        ''')
        duplicates = cursor.fetchall()
        if duplicates:
            print("\n⚠️ Найдены дубликаты доменов:")
            for domain, count in duplicates:
                print(f"Домен {domain}: {count} записей")
        else:
            print("\n✅ Дубликатов доменов не найдено")
        
        # Проверяем связи ключевых слов
        cursor.execute('''
            SELECT k.keyword, COUNT(*) as count 
            FROM keyword_to_site k 
            GROUP BY k.keyword
        ''')
        keyword_stats = cursor.fetchall()
        print("\nСтатистика по ключевым словам:")
        for keyword, count in keyword_stats:
            print(f"Ключевое слово '{keyword}': {count} сайтов")

if __name__ == "__main__":
    test_save_and_retrieve() 