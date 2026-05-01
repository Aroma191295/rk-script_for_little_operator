#!/usr/bin/expect -f
# Использовать: ./ltp.exp <HOST> <USER_PORT>


# Проверяем количество аргументов
if {$argc < 2} {
    puts "Usage: $argv0 <HOST> <USER_PORT>"
    exit 1
}

set HOST [lindex $argv 0]
set USER_PORT [lindex $argv 1]

# Если хотите захардкодить, напишите: set USER "admin"
set USER $env(USER)
set PASS $env(PASS)
set timeout 10

# Запускаем telnet
spawn telnet $HOST

# Обрабатываем этап авторизации
expect {
    "login" { send "$USER\r"; exp_continue }
    "Password:" { send "$PASS\r" }
    timeout { puts "Таймаут при ожидании запроса пароля"; exit 1 }
}

expect -re {[#>]$}

# Список команд
set commands [list \
    "show interface ont $USER_PORT state" \
    "show interface ont $USER_PORT ports" \
    "show mac interface ont $USER_PORT" \
    "show interface ont $USER_PORT connections" \
    "show interface ont $USER_PORT laser" \
]

# Выполняем команды
foreach cmd $commands {
    send "$cmd\r"
    # Ждем приглашение после каждой команды
    expect -re {[#>]$}
}

# Передаем управление пользователю (остаемся в интерфейсе коммутатора)
interact
