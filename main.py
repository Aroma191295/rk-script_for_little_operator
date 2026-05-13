#!/usr/bin/env python3
"""
Скрипт для диагностики абонентов
Использует только стандартную библиотеку Python 3.10
"""

import sys
import os
import argparse

# Импорт модулей подключения
from core.telnet import TelnetClient
from core.ssh import SSHClient

# Импорт вендоров
from vendors.eltex_eth import EltexEthDiagnostic
# from vendors.cdata import CDataDiagnostic

# Список вендоров с диагностикой
VENDOR_CONFIG = {
    'eltex': {
        'class': EltexEthDiagnostic,
        'default_proto': 'telnet',
        'env_user': 'USER',
        'env_pass': 'PASS'
    },
    # 'c-data': {
    #     'class': CDataDiagnostic,
    #     'default_proto': 'ssh',
    #     'env_user': 'USER_SSH',
    #     'env_pass': 'PASS_SSH'
    # },
}

# Парсер .env файлов
def load_env_file():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_paths = [
        os.path.join(script_dir, '.env'),
        os.path.expanduser('~/.env')
    ]

    for filepath in env_paths:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            os.environ[key] = value
                break
            except Exception as e:
                print(f"⚠️ Ошибка чтения {filepath}: {e}")

def main():
    load_env_file()

    parser = argparse.ArgumentParser(
        description="🔧 Скрипт для диагностики абонентских портов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Примеры использования:
  python3 main.py 10.0.0.1 -v eltex -p gi1/0/23  (Подключится по Telnet с USER/PASS)
  python3 main.py 10.0.0.1 -v c-data -p Gi0/1       (Подключится по SSH с USER_SSH/PASS_SSH)
  python3 main.py 10.0.0.1 -p ssh              (Базовый SSH: возьмет дефолтные переменные)"""
    )
# Обязательные аргументы
    parser.add_argument("ip", help="IP адрес коммутатора")
# Не обязательные аргументы
    parser.add_argument(
        "-v", "--vendor",
        required=False,
        default=None,
        choices=VENDOR_CONFIG.keys(),
        help="Вендор оборудования (автоматически задает протокол и учетные данные)"
    )
    parser.add_argument(
        "-p", "--port",
        help="Номер порта для диагностики (например: gi1/0/1)"
    )
    parser.add_argument(
        "--proto",
        choices=['telnet', 'ssh'],
        help="Принудительно указать протокол (переопределяет настройку вендора)"
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    ip = args.ip
    vendor_name = args.vendor
    port = args.port

 # Приоритет: 1. Ручной флаг --proto -> 2. Дефолт вендора -> 3. Глобальный дефолт (Telnet)
    if args.proto:
        proto = args.proto
    elif vendor_name and 'default_proto' in VENDOR_CONFIG[vendor_name]:
        proto = VENDOR_CONFIG[vendor_name]['default_proto']
    else:
        proto = 'telnet'

 # Приоритет: 1. Дефолт вендора -> 2. Протокол
    if vendor_name:
        cfg = VENDOR_CONFIG[vendor_name]
        username = os.environ.get(cfg['env_user'])
        password = os.environ.get(cfg['env_pass'])
    else:
        if proto == 'ssh':
            username = os.environ.get('USER_SSH')
            password = os.environ.get('PASS_SSH')
        else:
            username = os.environ.get('USER')
            password = os.environ.get('PASS')
    if not password:
        print(f"❌ Пароль не найден!")
        if vendor_name:
            print(f"💡 Для вендора '{vendor_name}' задайте переменную {VENDOR_CONFIG[vendor_name]['env_pass']} в файле .env")
        else:
            print(f"💡 Задайте переменные USER/PASS или USER_SSH/PASS_SSH в файле .env")
        sys.exit(1)

    if vendor_name:
        print(f"🔌 Подключение к {ip} [{vendor_name.upper()}] через {proto.upper()}...")
    else:
        print(f"🔌 Подключение к {ip} через {proto.upper()} (базовый режим)...")

    print(f"👤 Пользователь: {username}")

    ClientClass = SSHClient if proto == 'ssh' else TelnetClient
    client = ClientClass(ip, username, password)

    try:
        if not client.connect():
            print("❌ Не удалось подключиться к коммутатору")
            sys.exit(1)
        print("✅ Подключение установлено")

        if not client.login():
            print("❌ Ошибка авторизации")
            sys.exit(1)
        print("✅ Авторизация успешна!\n")

        if vendor_name:
            DiagnosticClass = VENDOR_CONFIG[vendor_name]['class']
            diag = DiagnosticClass(client)

            if port:
                diag.analyze_port(port)
                print("-" * 70)
            else:
                print("ℹ️ Порт не указан, пропуск диагностики.")
        else:
            if port:
                print(f"⚠️ Порт {port} указан, но вендор не задан. Диагностика недоступна.")
            print("ℹ️ Режим базового подключения (без вендорной диагностики).")

        response = input("🎮 Перейти в интерактивный режим управления? (y/n): ").lower()
        if response in ['y', 'д']:
            client.interactive_mode()
        else:
            print("Завершение работы")

    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        client.disconnect()
        print("🔌 Соединение закрыто")

if __name__ == "__main__":
    main()
