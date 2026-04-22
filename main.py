#!/usr/bin/env python3
"""
Скрипт для диагностики абонентов на коммутаторах Eltex через Telnet
Использует только стандартную библиотеку Python 3.10
"""

import sys
import os

# Импорт модулей
from core.telnet import TelnetClient
from core.ssh import SSHClient
from vendors.eltex import EltexDiagnostic

# Получение пароля
def get_password():
    for env_var in ['PASS', 'PASS_SSH']:
        password = os.environ.get(env_var)
        if password:
            return password
            
    pass_file = os.path.expanduser('~/.telnet_pass')
    if os.path.exists(pass_file):
        try:
            with open(pass_file, 'r') as f:
                return f.read().strip()
        except:
            pass
    return None

# Инструкция по использованию
def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 main.py <IP> <пользовательский порт>")
        print("\nПримеры:")
        print("  python3 main.py 10.0.0.1")
        print("  python3 main.py 10.0.0.1 gi1/0/1")
        print("  python3 main.py 10.0.0.1 \"GigabitEthernet 1/0/1\"")
        print("\nБез порта - только авторизация")
        sys.exit(1)
        
    ip = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Проверка переменных
    username = os.environ.get('USER', 'admin')
    password = get_password()
    
    if not password:
        print("❌ Один или несколько паролей не заданы!")
        sys.exit(1)
        
    print(f"🔌 Подключение к {ip} через Telnet...")
    print(f"👤 Пользователь: {username}")
    
    # Создаем подключение
    client = TelnetClient(ip, username, password)
    
    try:
        if not client.connect():
            print("❌ Не удалось подключиться к коммутатору")
            sys.exit(1)
        print("✅ Подключение установлено")
        
        if not client.login():
            print("❌ Ошибка авторизации")
            sys.exit(1)
        print("✅ Авторизация успешна!\n")
        
        # Передаем подключение вендорскому классу
        diag = EltexDiagnostic(client)
        
        if port:
            # Проводим анализ порта
            diag.analyze_port(port)
            
            print("-" * 70)
            response = input("🎮 Передать управление оператору? (y/n): ").lower()
            if response in ['y', 'д']:
                client.interactive_mode()
            else:
                print("Завершение работы")
        else:
            response = input("🎮 Перейти в интерактивный режим? (y/n): ").lower()
            if response in ['y', 'д']:
                client.interactive_mode()
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        client.disconnect()
        print("🔌 Соединение закрыто")
        
if __name__ == "__main__":
    main()
