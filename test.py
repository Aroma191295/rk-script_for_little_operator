#!/usr/bin/env python3
"""
Скрипт для диагностики абонентов на коммутаторах Eltex через Telnet
Использует только стандартную библиотеку Python 3.10
"""

import sys
import os

from core.telnet import TelnetClient
from vendors.eltex import EltexDiagnostic
        
def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 main.py <IP> [порт]")
        print("\nПримеры:")
        print("  python3 main.py 10.0.0.1")
        print("  python3 main.py 10.0.0.1 gi1/0/1")
        sys.exit(1)
        
    ip = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) > 2 else None
    
    # --- СБОР УЧЕТНЫХ ДАННЫХ ---
    # Основная пара
    user_primary = os.environ.get('USER')
    pass_primary = os.environ.get('PASS')
    
    # Резервная пара (admin и $PASS_SSH)
    user_fallback = 'admin'
    pass_fallback = os.environ.get('PASS_SSH')
    
    # Проверка: хотя бы один пароль должен быть задан
    if not pass_primary and not pass_fallback:
        print("❌ Ошибка: не заданы переменные окружения с паролями!")
        sys.exit(1)

    print(f"🔌 Подключение к {ip} через Telnet...")
    print(f"👤 Основной пользователь: {user_primary}")
    if pass_fallback:
        print(f"🔑 Резервный пользователь: {user_fallback}")
    
    # Передаем обе пары в клиент
    client = TelnetClient(
        ip=ip, 
        username=user_primary, 
        password=pass_primary or "", # Если PASS пуст, передаем пустую строку, чтобы скрипт дошел до fallback
        fallback_user=user_fallback if pass_fallback else None,
        fallback_pass=pass_fallback
    )
    
    try:
        if not client.connect():
            print("❌ Не удалось подключиться к коммутатору")
            sys.exit(1)
        print("✅ Подключение установлено")
        
        if not client.login():
            print("❌ Ошибка авторизации (ни основная, ни резервная пара не подошли)")
            sys.exit(1)
        print("✅ Авторизация успешна!\n")
        
        diag = EltexDiagnostic(client)
        
        if port:
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
        print(f"❌ Критическая ошибка: {e}")
    finally:
        client.disconnect()
        print("🔌 Соединение закрыто")
        
if __name__ == "__main__":
    main()
