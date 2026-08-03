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
from core.create_env import ensure_env_file

# Импорт вендоров
from vendors.eltex_eth import EltexEthDiagnostic
from vendors.zte320 import ZTE320Diagnostic
from vendors.cdata import CDataDiagnostic
from vendors.eltex_ltp import EltexLTPDiagnostic
from vendors.zte610 import ZTE610Diagnostic

# Список вендоров с диагностикой
VENDOR_CONFIG = {
    'eltex': {
        'class': EltexEthDiagnostic,
        'default_proto': 'telnet',
        'env_user': 'USER',
        'env_pass': 'PASS'
    },
    'zte320': {
        'class': ZTE320Diagnostic,
        'default_proto': 'telnet',
        'env_user': 'USER',
        'env_pass': 'PASS'
    },
    # 'cdata': {
    #     'class': CDataDiagnostic,
    #     'default_proto': 'ssh',
    #     'env_user': 'USER_SSH',
    #     'env_pass': 'PASS_SSH',
    # },
    'ltp': {
        'class': EltexLTPDiagnostic,
        'default_proto': 'telnet',
        'env_user': 'USER',
        'env_pass': 'PASS',
    },
    'ma4000': {
        'class': EltexLTPDiagnostic,
        'default_proto': 'telnet',
        'env_user': 'USER_SSH',
        'env_pass': 'PASS_SSH',
    },
    'zte610': {
        'class': ZTE610Diagnostic,
        'default_proto': 'ssh',
        'env_user': 'USER',
        'env_pass': 'PASS',
    },

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_env_file(script_dir)
    load_env_file()

    parser = argparse.ArgumentParser(
        description="""Перед запуском прочитайте readme
Скрипт для диагностики абонентских портов""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Примеры использования:
    python3 main.py 10.0.0.1 -v eltex -p gi1/0/23
    python3 main.py 10.0.0.1 -v cdata
    python3 main.py 10.0.0.1 -P ssh"""
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
        help="Номер порта для диагностики"
    )
    parser.add_argument(
        "--proto", "-P",
        choices=['telnet', 'ssh'],
        help="Принудительно указать протокол (переопределяет настройку вендора)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="debug"
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

 # Приоритет: 1. Дефолт вендора -> 2. Протокол -> 3. Глобальный дефолт (USER и PASS)
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
            
    if vendor_name:
        print(f"🔌 Подключение к {ip} [{vendor_name.upper()}] через {proto.upper()}...")
    else:
        print(f"🔌 Подключение к {ip} через {proto.upper()} (базовый режим)...")

    print(f"👤 Пользователь: {username}")

    enable_password = os.environ.get('PASS_ENABLE') or password

    if proto == 'ssh':
        client = SSHClient(
            ip, username, password,
            enable_password=enable_password,
            debug=args.debug,
        )
    else:
        client = TelnetClient(ip, username, password, debug=args.debug)

    if args.debug:
        print("🛠  DEBUG: сырой вывод команд включён\n")

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
            if vendor_name == 'cdata':
                diag = DiagnosticClass(client, debug=args.debug)
            else:
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

        if port and hasattr(diag, "interactive_menu"):
            diag.interactive_menu(port)
        else:
            response = input("🎮 Перейти в сырой CLI? (y/n): ").lower()
            if response in ["y", "н"]:
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
