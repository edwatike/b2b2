from datetime import datetime
import sqlite3
import json

def init_database():
    """Инициализация базы данных с расширенной структурой"""
    with sqlite3.connect('search_results.db') as conn:
        cursor = conn.cursor()
        
        # Создаем таблицу для сайтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parsed_sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                domain TEXT,
                title TEXT,
                raw_html TEXT,
                search_engine TEXT,
                search_keyword TEXT,
                parsed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                has_inn_data BOOLEAN DEFAULT FALSE,
                is_supplier_candidate BOOLEAN DEFAULT FALSE,
                inn TEXT,
                ogrn TEXT,
                kpp TEXT,
                company_name TEXT,
                emails TEXT,  -- JSON array
                phones TEXT,  -- JSON array
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу для связи ключевых слов с сайтами
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keyword_to_site (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT,
                site_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES parsed_sites(id),
                UNIQUE(keyword, site_id)
            )
        ''')
        
        # Создаем индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON parsed_sites(domain)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_keyword ON parsed_sites(search_keyword)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_at ON parsed_sites(parsed_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_keyword ON keyword_to_site(keyword)')
        
        conn.commit()

class ParsedSite:
    def __init__(self, url, domain, title, raw_html=None, search_engine='google', 
                 search_keyword=None, has_inn_data=False, is_supplier_candidate=False,
                 inn=None, ogrn=None, kpp=None, company_name=None, emails=None, phones=None):
        self.url = url
        self.domain = domain
        self.title = title
        self.raw_html = raw_html
        self.search_engine = search_engine
        self.search_keyword = search_keyword
        self.has_inn_data = has_inn_data
        self.is_supplier_candidate = is_supplier_candidate
        self.inn = inn
        self.ogrn = ogrn
        self.kpp = kpp
        self.company_name = company_name
        self.emails = json.dumps(emails) if emails else '[]'
        self.phones = json.dumps(phones) if phones else '[]'
        self.parsed_at = datetime.now()
    
    def save(self):
        """Сохранение сайта в базу данных"""
        with sqlite3.connect('search_results.db') as conn:
            cursor = conn.cursor()
            
            # Проверяем существование сайта
            cursor.execute('SELECT id FROM parsed_sites WHERE url = ?', (self.url,))
            existing = cursor.fetchone()
            
            if existing:
                site_id = existing[0]
                # Обновляем существующую запись
                cursor.execute('''
                    UPDATE parsed_sites 
                    SET title = ?, raw_html = ?, has_inn_data = ?, is_supplier_candidate = ?,
                        inn = ?, ogrn = ?, kpp = ?, company_name = ?, emails = ?, phones = ?,
                        parsed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (self.title, self.raw_html, self.has_inn_data, self.is_supplier_candidate,
                      self.inn, self.ogrn, self.kpp, self.company_name, self.emails, self.phones,
                      site_id))
            else:
                # Создаем новую запись
                cursor.execute('''
                    INSERT INTO parsed_sites (
                        url, domain, title, raw_html, search_engine, search_keyword,
                        has_inn_data, is_supplier_candidate, inn, ogrn, kpp,
                        company_name, emails, phones
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (self.url, self.domain, self.title, self.raw_html, self.search_engine,
                      self.search_keyword, self.has_inn_data, self.is_supplier_candidate,
                      self.inn, self.ogrn, self.kpp, self.company_name, self.emails, self.phones))
                site_id = cursor.lastrowid
            
            # Добавляем связь с ключевым словом
            if self.search_keyword:
                cursor.execute('''
                    INSERT OR IGNORE INTO keyword_to_site (keyword, site_id)
                    VALUES (?, ?)
                ''', (self.search_keyword, site_id))
            
            conn.commit()
            return site_id

    @staticmethod
    def get_recent_sites(limit=10):
        """Получение последних обработанных сайтов"""
        with sqlite3.connect('search_results.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM parsed_sites 
                ORDER BY parsed_at DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    @staticmethod
    def get_sites_by_keyword(keyword):
        """Получение сайтов по ключевому слову"""
        with sqlite3.connect('search_results.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.* FROM parsed_sites p
                JOIN keyword_to_site k ON p.id = k.site_id
                WHERE k.keyword = ?
                ORDER BY p.parsed_at DESC
            ''', (keyword,))
            return cursor.fetchall() 