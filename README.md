script by tg@aroma191295

Переменные для входа в фаиле .env для проекта \
Требуется следующие переменные:
```
USER
PASS
USER_SSH
PASS_SSH
```

Ветка проекта
```
scripts_for_the_litle_ones/
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
│   ├── eltex_ltp.py     # WIP
│   ├── eltex_ma.py      # В планах
│   ├── eltex_lte.py     # В планах
│   ├── zte320.py        # WIP
│   ├── zte610.py        # В планах
│   ├── snr.py           # В планах
│   ├── zyxel.py         # В планах
│   └── dlink.py         # В планах
│
└── quick_script/        # Папка с простыми скриптами состоящими из except
    ├── qq.exp
    ├── eltex_eth.exp
    ├── ltp.exp          
    ├── cdata.exp        # WIP
    └── zte320.exp

```

