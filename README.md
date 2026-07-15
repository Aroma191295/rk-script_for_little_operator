script by tg@aroma191295

Переменные для входа требуется занести в фаил .env в корень проекта
Требуется занести следующие переменные:
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
│   ├── cdata.py
│   ├── eltex_eth.py
│   ├── eltex_ltp.py
│   ├── eltex_ma.py
│   ├── eltex_lte.py
│   ├── zte320.py
│   ├── zte610.py
│   ├── snr.py
│   ├── zyxel.py
│   └── dlink.py
│
└── quick_script/        # Папка с простыми скриптами состоящими из except
    ├── ltp.exp
    ├── qq.exp
    ├── eltex_eth.exp
    ├── ltp.exp
    ├── cdata.exp        #нужно доделать
    └── zte320.exp

```

