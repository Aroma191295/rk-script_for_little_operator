script by tg@aroma191295

Переменные для входа в фаиле .env для проекта \
Требуется следующие переменные:
```
USER
PASS
USER_SSH
PASS_SSH
PASS_ENABLE
```

# Ветка проекта
```
rk-scripts_for_the_litle_operator/
│
├── main.py              # Точка входа. Сюда мы пишем логику "что сделать".
│
├── core/                # Папка с "движком"
│   ├── __init__.py      # Пустой файл, чтобы Python считал это пакетом
│   ├── telnet.py        # Пакет по подключению через telnet
│   ├── ssh.py           # Пакет по подключению через ssh
│   └── create_env.py    # Пакет по созданию .env если его нету
│
├── vendors/             # Папка со спецификой брендов
│   ├── __init__.py      # Пустой файл, чтобы Python считал это пакетом
│   ├── cdata.py         # WIP
│   ├── eltex_eth.py
│   ├── eltex_ltp.py     
│   ├── eltex_lte.py     # В планах
│   ├── zte320.py        
│   ├── zte610.py        
│   ├── snr.py           # В планах
│   ├── zyxel.py         # В планах
│   └── dlink.py         # В планах
│
└── quick_script/        # Папка с простыми скриптами состоящими из except
    ├── qq.exp           # Быстрый вход
    ├── eltex_eth.exp    # Вход и быстрая диагностика медных eltex 
    ├── ltp.exp          # Вход и быстрая диагностика LTP
    ├── cdata.exp        # Не работает
    └── zte320.exp       # Вход и быстрая диагностика ZTE320
```

# Как использовать
```
positional arguments:
  ip                    IP адрес коммутатора

options:
  -h, --help            show this help message and exit

  -v {eltex,zte320,ltp,ma4000,zte610}, --vendor {eltex,zte320,ltp,ma4000,zte610}
                        Вендор оборудования (автоматически задает протокол и учетные данные)

  -p PORT, --port PORT  Номер порта для диагностики

  --proto {telnet,ssh}, -P {telnet,ssh}
                        Принудительно указать протокол (переопределяет настройку вендора)
                        
  --debug               debug

Примеры использования:
    python3 main.py 10.0.0.1 -v eltex -p gi1/0/23
    python3 main.py 10.0.0.1 -v cdata
    python3 main.py 10.0.0.1 -P ssh
```