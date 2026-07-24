Учётные данные берутся из `.env` в корне проекта (рядом с `main.py`).
Fallback: `~/.env`.

| Скрипт | Переменные |
|--------|------------|
| `qq.exp` | `USER`/`PASS`, для `admin` — `PASS_SSH` |
| `eltex_eth.exp`, `ltp.exp`, `zte320.exp` | `USER`/`PASS` |
| `cdata.exp` | `USER_SSH`/`PASS_SSH` (+ опционально `PASS_ENABLE`) |

`.bash_aliases`:

```
alias zte320='<расположение_папки>/git/rk-script_for_little_operator/quick_script/zte320.exp'
alias ltp='<расположение_папки>/git/rk-script_for_little_operator/quick_script/ltp.exp'
alias qq='<расположение_папки>/git/rk-script_for_little_operator/quick_script/qq.exp telnet'
alias qq-ssh='<расположение_папки>/git/rk-script_for_little_operator/quick_script/qq.exp ssh'
alias eltex='<расположение_папки>/git/rk-script_for_little_operator/quick_script/eltex_eth.exp'
alias cdata='<расположение_папки>/git/rk-script_for_little_operator/quick_script/cdata.exp'
```

`qq.exp` — вход через telnet/ssh под своими данными или админом.
