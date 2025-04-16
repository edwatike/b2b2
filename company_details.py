import re
from bs4 import BeautifulSoup
import json

def extract_company_details(html):
    """Извлечение реквизитов компании из HTML"""
    if not html:
        return None
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # Ищем ИНН (10 или 12 цифр)
    inn_pattern = r'\b\d{10}\b|\b\d{12}\b'
    inn_matches = re.findall(inn_pattern, html)
    inn = inn_matches[0] if inn_matches else None
    
    # Ищем ОГРН (13 цифр)
    ogrn_pattern = r'\b\d{13}\b'
    ogrn_matches = re.findall(ogrn_pattern, html)
    ogrn = ogrn_matches[0] if ogrn_matches else None
    
    # Ищем КПП (9 цифр)
    kpp_pattern = r'\b\d{9}\b'
    kpp_matches = re.findall(kpp_pattern, html)
    kpp = kpp_matches[0] if kpp_matches else None
    
    # Ищем email адреса
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = list(set(re.findall(email_pattern, html)))
    
    # Ищем телефоны
    phone_pattern = r'(?:\+7|8)[- _]?\(?[- _]?\d{3}[- _]?\)?[- _]?\d{3}[- _]?\d{2}[- _]?\d{2}'
    phones = list(set(re.findall(phone_pattern, html)))
    
    # Ищем название компании
    company_name = None
    # Проверяем мета-теги
    meta_title = soup.find('meta', property='og:site_name')
    if meta_title:
        company_name = meta_title.get('content')
    
    # Если не нашли в мета-тегах, ищем в заголовке
    if not company_name:
        title = soup.find('title')
        if title:
            company_name = title.text.strip()
    
    # Определяем, является ли сайт поставщиком
    is_supplier = False
    supplier_keywords = ['поставщик', 'оптовый', 'опт', 'производитель', 'производство']
    text = soup.get_text().lower()
    if any(keyword in text for keyword in supplier_keywords):
        is_supplier = True
    
    return {
        'has_inn_data': bool(inn or ogrn or kpp),
        'is_supplier_candidate': is_supplier,
        'inn': inn,
        'ogrn': ogrn,
        'kpp': kpp,
        'company_name': company_name,
        'emails': emails,
        'phones': phones
    }

def extract_domain(url):
    """Извлечение домена из URL"""
    if not url:
        return None
    # Удаляем протокол и www
    domain = re.sub(r'https?://(www\.)?', '', url)
    # Удаляем путь и параметры
    domain = domain.split('/')[0]
    return domain 