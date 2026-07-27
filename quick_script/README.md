Учётные данные берутся из `.env` в корне проекта (рядом с `main.py`).

| Скрипт | Переменные |
|--------|------------|
| `qq.exp` | `USER`/`PASS`, для `admin` — `PASS_SSH` |
| `eltex_eth.exp`, `ltp.exp`, `zte320.exp` | `USER`/`PASS` |
| `cdata.exp` | `USER_SSH`/`PASS_SSH` |

`qq.exp` — вход через telnet/ssh под своими данными или админом.
`eltex_eth.exp` - вход и первичная диагностика для коммутатора eltex.
`ltp.exp` - вход и первичная диагностика для OLT Eltex LTP.
`zte320.exp` - вход и первичная диагностика для OLT ZTE 320.
`cdata.exp` - вход и первичная диагностика для коммутатора OLT C-Data (пока не работает).

```
cat >> ~/.bash_aliases << EOF
alias zte320='<расположение файла>/zte320.exp'
alias qq='<расположение файла>/qq.exp telnet'
alias qq-ssh='<расположение файла>/qq.exp ssh'
alias ltp='<расположение файла>/ltp.exp'
alias eltex='<расположение файла>/eltex_eth.exp'
EOF
```
`chmod -r 700 <расположение_папки>/rk-script_for_little_operator/quick_script` - дать права на выполнение
`source ~/.bashrc` - перечитать файл с alias или просто перезапустить терминал
