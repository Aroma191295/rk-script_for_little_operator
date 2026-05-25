#!/usr/bin/expect -f
# Использовать: ./eltex_eth.sh <HOST> <USER_PORT>

# Проверяем количество аргументов
if {$argc < 2} {
    puts "Usage: $argv0 <HOST> <USER_PORT>"
    exit 1
}

set HOST [lindex $argv 0]
set USER_PORT [lindex $argv 1]
set DELAY 1
set timeout 10

# Если хотите захардкодить, напишите: set USER "admin"
set USER $env(USER)
set PASS $env(PASS)

spawn telnet $HOST

expect {
    "User" { send "$USER\r"; exp_continue }
    "Password:" { send "$PASS\r" }
    timeout { puts "Нет ответа по таймауту"; exit 1 }
}

expect -re {[#>]$}

# Список команд
set commands [list \
    "terminal datadump" \
    "show interfaces status $USER_PORT" \
    "show running-config interfaces $USER_PORT" \
    "show interfaces counters $USER_PORT" \
    "no terminal datadump" \
    "show mac address-table interface $USER_PORT" \
    "show logging | include $USER_PORT" \
    ]

foreach cmd $commands {
    send "$cmd\r"
    expect -re {[#>]$}
    sleep $DELAY
}

interact
