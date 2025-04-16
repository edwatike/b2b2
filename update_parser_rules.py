#!/usr/bin/env python3
"""
Скрипт для обновления правил парсера.
Требует прав администратора (sudo).
"""

import os
import sys
import json
import argparse
import subprocess

def check_sudo():
    """Проверка, запущен ли скрипт с правами sudo"""
    if os.geteuid() != 0:
        print("ОШИБКА: Этот скрипт требует прав администратора.")
        print("Пожалуйста, запустите с sudo: sudo python3 update_parser_rules.py [опции]")
        sys.exit(1)

def update_rules(settings_file):
    """Обновление правил парсера из JSON файла"""
    try:
        # Проверяем права sudo
        check_sudo()
        
        # Проверяем существование файла
        if not os.path.exists(settings_file):
            print(f"ОШИБКА: Файл {settings_file} не найден.")
            sys.exit(1)
            
        # Загружаем настройки из JSON
        with open(settings_file, 'r', encoding='utf-8') as f:
            new_settings = json.load(f)
            
        # Проверяем структуру настроек
        required_sections = [
            "BROWSER_SETTINGS", 
            "PARSING_SETTINGS", 
            "LOCATIONS", 
            "SELECTORS", 
            "ANTI_DETECTION_SCRIPT", 
            "RESULT_PROCESSING", 
            "LOGGING", 
            "SECURITY"
        ]
        
        for section in required_sections:
            if section not in new_settings:
                print(f"ОШИБКА: В файле настроек отсутствует обязательный раздел {section}")
                sys.exit(1)
                
        # Создаем резервную копию текущих правил
        backup_file = "parser_rules_backup.py"
        subprocess.run(["cp", "parser_rules.py", backup_file], check=True)
        print(f"Создана резервная копия текущих правил: {backup_file}")
        
        # Генерируем новый файл правил
        with open("parser_rules.py", 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env python3\n')
            f.write('"""\n')
            f.write('ПРАВИЛА ПАРСЕРА - ИЗМЕНЕНИЕ ТОЛЬКО ЧЕРЕЗ SUDO!\n')
            f.write('Этот файл содержит все настройки и правила для парсера.\n')
            f.write('Изменение этих правил требует прав администратора.\n')
            f.write('"""\n\n')
            
            # Записываем каждую секцию
            for section, value in new_settings.items():
                f.write(f'# ===== {section} =====\n')
                if isinstance(value, dict):
                    f.write(f'{section} = {{\n')
                    for k, v in value.items():
                        if isinstance(v, str):
                            f.write(f'    "{k}": "{v}",\n')
                        else:
                            f.write(f'    "{k}": {v},\n')
                    f.write('}\n\n')
                elif isinstance(value, list):
                    f.write(f'{section} = [\n')
                    for item in value:
                        if isinstance(item, dict):
                            f.write('    {\n')
                            for k, v in item.items():
                                if isinstance(v, str):
                                    f.write(f'        "{k}": "{v}",\n')
                                else:
                                    f.write(f'        "{k}": {v},\n')
                            f.write('    },\n')
                        else:
                            f.write(f'    {item},\n')
                    f.write(']\n\n')
                else:
                    f.write(f'{section} = {value}\n\n')
                    
            # Добавляем функцию валидации
            f.write('''# ===== ВАЛИДАЦИЯ =====
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
''')
        
        # Устанавливаем правильные права доступа
        subprocess.run(["chmod", "644", "parser_rules.py"], check=True)
        
        print("Правила парсера успешно обновлены!")
        print("Для применения изменений перезапустите парсер.")
        
    except Exception as e:
        print(f"ОШИБКА при обновлении правил: {str(e)}")
        # Восстанавливаем резервную копию в случае ошибки
        if os.path.exists(backup_file):
            subprocess.run(["mv", backup_file, "parser_rules.py"], check=True)
            print("Восстановлена резервная копия правил.")
        sys.exit(1)

def create_template():
    """Создание шаблона настроек"""
    try:
        # Проверяем права sudo
        check_sudo()
        
        # Импортируем текущие правила
        import parser_rules as rules
        
        # Создаем шаблон на основе текущих правил
        template = {
            "BROWSER_SETTINGS": rules.BROWSER_SETTINGS,
            "PARSING_SETTINGS": rules.PARSING_SETTINGS,
            "LOCATIONS": rules.LOCATIONS,
            "SELECTORS": rules.SELECTORS,
            "ANTI_DETECTION_SCRIPT": rules.ANTI_DETECTION_SCRIPT,
            "RESULT_PROCESSING": rules.RESULT_PROCESSING,
            "LOGGING": rules.LOGGING,
            "SECURITY": rules.SECURITY
        }
        
        # Сохраняем шаблон в JSON
        with open("parser_rules_template.json", 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
            
        print("Шаблон настроек создан: parser_rules_template.json")
        print("Отредактируйте этот файл и используйте его для обновления правил.")
        
    except Exception as e:
        print(f"ОШИБКА при создании шаблона: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Обновление правил парсера (требуется sudo)")
    parser.add_argument("--settings", "-s", help="Путь к JSON файлу с настройками")
    parser.add_argument("--template", "-t", action="store_true", help="Создать шаблон настроек")
    
    args = parser.parse_args()
    
    if args.template:
        create_template()
    elif args.settings:
        update_rules(args.settings)
    else:
        parser.print_help() 