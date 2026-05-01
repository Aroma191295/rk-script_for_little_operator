,,`script by tg@aroma191295

qq.sh - expect скрипт по входу через telnet и ssh под своими данными или админом.

PASS - это ваш пароль от Active Directory
PASS_SSH - пароль от админа

```
scripts_for_the_litle_ones/
│
├── main.py              # Точка входа. Сюда мы пишем логику "что сделать".
│
├── core/                # Папка с "движком"
│   ├── __init__.py      # Пустой файл, чтобы Python считал это пакетом
│   ├── telnet.py        # Пакет по подключению через telnet
│   └── ssh.py           # Пакет по подключению через ssh
│
├── vendors/             # Папка со спецификой брендов
│   ├── __init__.py      # Пустой файл, чтобы Python считал это пакетом
│   ├── eltex_eth.py
│   ├── eltex_ltp.py
│   ├── eltex_ma.py
│   ├── eltex_lte.py
│   ├── zte320.py
│   ├── zte610.py
│   ├── cdata.py
│   ├── snr.py
│   ├── zyxel.py
│   └── dlink.py
│
└── quick_script/        # Папка с простыми скриптами состоящими из except
    ├── qq.sh
    ├── zte.sh
    └── ltp.sh

```
